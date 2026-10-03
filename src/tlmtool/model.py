from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RuntimeStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    READY = "READY"
    BUSY = "BUSY"
    PAUSED_CAPTCHA = "PAUSED_CAPTCHA"
    DEAD = "DEAD"
    LOADING = "LOADING"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class GameWindow:
    pid: int
    hwnd: int
    thread_id: int
    title: str
    process_name: str


@dataclass(frozen=True, slots=True)
class LocalRoleSnapshot:
    pid: int
    captured_ms: int
    valid_mask: int = 0
    world_generation: int = 0
    role_id: int = 0
    name: str = ""
    level: int = 0
    faction_id: int = 0
    team_id: int = 0
    hp: int = 0
    max_hp: int = 0
    mp: int = 0
    max_mp: int = 0
    map_id: int = 0
    x: int = 0
    y: int = 0
    is_dead: bool = False
    is_riding: bool = False
    auto_pathing: bool = False
    auto_fight: bool = False
    free_bag_space: int = -1
    waiting_change_map: bool = False
    is_moving: bool = False
    is_busy: bool = False
    is_progress: bool = False
    map_ready: bool = False
    captcha_active: bool = False
    selected_target_role_id: int = 0

    @property
    def hp_percent(self) -> float:
        return (self.hp * 100.0 / self.max_hp) if self.max_hp > 0 else 0.0


@dataclass(frozen=True, slots=True)
class BagItemSnapshot:
    instance_id: int
    item_id: int
    site: int
    position: int
    quantity: int
    bound: bool
    throwable: bool
    sellable: bool
    is_equip: bool
    is_weapon: bool
    name: str = ""
    item_type: str = ""
    equip_type: str = ""


@dataclass(frozen=True, slots=True)
class AccountConfig:
    enabled: bool = False
    username: str = ""
    password: str = ""
    captcha_mode: str = "Không"
    proxy: str = ""


@dataclass(slots=True)
class PartyGroup:
    leader: str = ""
    members: list[str] = field(default_factory=lambda: ["" for _ in range(6)])


@dataclass(slots=True)
class SavedCoordinate:
    name: str = "Tọa độ 1"
    map_name: str = "Đại Lý"
    map_id: int = 0
    x: int = 0
    y: int = 0
    apply: str = "Train"


@dataclass(slots=True)
class RuntimeAccount:
    pid: int
    role_name: str = ""
    snapshot: Optional[LocalRoleSnapshot] = None
    status: RuntimeStatus = RuntimeStatus.UNKNOWN
    last_error: str = ""
