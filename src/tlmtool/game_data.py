from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MapRecord:
    map_id: int
    name: str
    res_name: str = ""
    level: int = 0
    map_type: str = ""


def _candidate_data_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "data" / "MAPS.csv",
        here.parent / "data" / "MAPS.csv",
        Path(sys.argv[0]).resolve().parent / "data" / "MAPS.csv",
        Path.cwd() / "data" / "MAPS.csv",
    ]


@lru_cache(maxsize=1)
def load_maps() -> tuple[MapRecord, ...]:
    path = next((p for p in _candidate_data_paths() if p.exists()), None)
    if path is None:
        return ()
    rows: list[MapRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                rows.append(
                    MapRecord(
                        map_id=int(row.get("MapID") or 0),
                        name=(row.get("Name") or "").strip(),
                        res_name=(row.get("ResName") or "").strip(),
                        level=int(row.get("Level") or 0),
                        map_type=(row.get("Type") or "").strip(),
                    )
                )
            except (TypeError, ValueError):
                continue
    return tuple(r for r in rows if r.map_id > 0 and r.name)


@lru_cache(maxsize=1)
def map_name_to_id() -> dict[str, int]:
    return {r.name: r.map_id for r in load_maps()}


@lru_cache(maxsize=1)
def map_id_to_name() -> dict[int, str]:
    return {r.map_id: r.name for r in load_maps()}


def map_names(include_instances: bool = False) -> list[str]:
    records = load_maps()
    if include_instances:
        return [r.name for r in records]
    # TLM coordinate editors primarily show ordinary city/faction/wild maps.
    return [r.name for r in records if not r.name.startswith(("Phó Bản-", "Phụ Bản-"))]
