from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
from typing import Any


class SettingsStore:
    """INI persistence matching TLM's user-visible settings model.

    Secrets are intentionally not logged. Password persistence is kept in the same
    account record contract but isolated here so it can be replaced by Windows DPAPI
    without touching UI/feature code.
    """

    def __init__(self, root: Path | None = None) -> None:
        base = root or Path(os.getenv("APPDATA", Path.home())) / "TLMTool"
        self.root = base
        self.path = base / "settings.ini"
        self.root.mkdir(parents=True, exist_ok=True)
        self.cfg = configparser.ConfigParser(interpolation=None)
        self.cfg.optionxform = str
        if self.path.exists():
            self.cfg.read(self.path, encoding="utf-8")

    def get(self, section: str, key: str, default: str = "") -> str:
        return self.cfg.get(section, key, fallback=default)

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        try:
            return self.cfg.getboolean(section, key, fallback=default)
        except ValueError:
            return default

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        try:
            return self.cfg.getint(section, key, fallback=default)
        except ValueError:
            return default

    def set(self, section: str, key: str, value: Any) -> None:
        if not self.cfg.has_section(section):
            self.cfg.add_section(section)
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value, ensure_ascii=False)
        self.cfg.set(section, key, str(value))

    def get_json(self, section: str, key: str, default: Any) -> Any:
        raw = self.get(section, key, "")
        if not raw:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            self.cfg.write(f)
        tmp.replace(self.path)
