from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .model import GameWindow, LocalRoleSnapshot
from .winapi import WindowsApi
from .native_client import Command, RuntimeBridgeManager

log = logging.getLogger("tlmtool.backend")


class Action(str, Enum):
    LOGIN = "login"
    RELOAD = "reload"
    TRUNG_AC = "trung_ac"
    TANG_BAO_DO = "tang_bao_do"
    TOI_BO_DAU = "toi_bo_dau"
    TRI_LIEU = "tri_lieu"
    TRAIN = "train"
    TOI_CHO_TRAIN = "toi_cho_train"
    DANH = "danh"
    BAN_DO = "ban_do"
    TRAIN_LSV = "train_lsv"
    TOI_LSV = "toi_lsv"
    TOI_CHO_TRAIN_LSV = "toi_cho_train_lsv"
    ROI_LSV = "roi_lsv"
    DON_VANG = "don_vang"
    TOI_NOI_NHAN = "toi_noi_nhan"
    TOI_CHO_BAN = "toi_cho_ban"
    TOI_NOI_TRAIN = "toi_noi_train"
    THEO_DOI = "theo_doi"
    TOI_UU = "toi_uu"
    PARTY = "party"
    PHO_BAN = "pho_ban"
    RAO = "rao"


@dataclass(slots=True)
class ActionResult:
    ok: bool
    detail: str = ""


class PerPidGate:
    """One mutable action in flight per PID, matching DATA-2222 contract."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._busy: set[int] = set()

    def try_enter(self, pid: int) -> bool:
        with self._lock:
            if pid in self._busy:
                return False
            self._busy.add(pid)
            return True

    def leave(self, pid: int) -> None:
        with self._lock:
            self._busy.discard(pid)


class TlmBackend:
    """Facade used by all tabs.

    The public surface is deliberately limited to TLM 2.1.2 features. Native
    gameplay mutation is delegated to SemanticDriver. Window/layout/login-only
    operations remain ordinary Win32 operations.
    """

    def __init__(self, winapi: WindowsApi | None = None) -> None:
        self.winapi = winapi or WindowsApi()
        self.gate = PerPidGate()
        self.driver = SemanticDriver()
        self._listeners: list[Callable[[str], None]] = []

    def on_status(self, listener: Callable[[str], None]) -> None:
        self._listeners.append(listener)

    def status(self, text: str) -> None:
        log.info(text)
        for cb in tuple(self._listeners):
            try:
                cb(text)
            except Exception:
                log.exception("status listener")

    def windows(self) -> list[GameWindow]:
        return self.winapi.game_windows()

    def execute_all(self, action: Action) -> list[ActionResult]:
        windows = self.windows()
        if not windows:
            self.status("Không tìm thấy cửa sổ game, hãy mở game trước.")
            return []
        results = []
        for gw in windows:
            results.append(self.execute(gw, action))
        return results

    def execute(self, gw: GameWindow, action: Action) -> ActionResult:
        if not self.gate.try_enter(gw.pid):
            return ActionResult(False, "PID đang có một lệnh thay đổi trạng thái")
        try:
            if action == Action.RELOAD:
                return self.driver.reload(gw)
            return self.driver.invoke(gw, action)
        finally:
            self.gate.leave(gw.pid)

    def _semantic(self, gw: GameWindow, call: Callable[[], ActionResult]) -> ActionResult:
        if not self.gate.try_enter(gw.pid):
            return ActionResult(False, "PID đang có một lệnh thay đổi trạng thái")
        try:
            return call()
        finally:
            self.gate.leave(gw.pid)

    def start_path(self, gw: GameWindow, map_id: int, x: int, y: int) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.raw(gw, Command.START_PATH, int(map_id), int(x), int(y)))

    def stop_path(self, gw: GameWindow) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.raw(gw, Command.STOP_PATH))

    def start_auto_fight(self, gw: GameWindow) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.raw(gw, Command.START_AUTO_FIGHT))

    def stop_auto_fight(self, gw: GameWindow) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.raw(gw, Command.STOP_AUTO_FIGHT))

    def party_create(self, gw: GameWindow) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.party_create(gw))

    def party_leave(self, gw: GameWindow) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.party_leave(gw))

    def party_invite(self, gw: GameWindow, target_role_id: int) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.party_invite(gw, target_role_id))

    def party_join(self, gw: GameWindow, leader_role_id: int) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.party_join(gw, leader_role_id))

    def revive_normal(self, gw: GameWindow) -> ActionResult:
        return self._semantic(gw, lambda: self.driver.revive_normal(gw))


class SemanticDriver:
    """Windows semantic bridge adapter.

    The bridge is attached lazily per PID. Unsupported high-level workflows fail
    closed; feature tabs/orchestrators compose them from low-level semantic
    primitives instead of reporting a fake success.
    """

    def __init__(self) -> None:
        self._native = RuntimeBridgeManager() if os.name == "nt" else None
        self._load_error = "native bridge chỉ chạy trên Windows x64" if os.name != "nt" else "TlmSemanticBridge.dll chưa sẵn sàng"

    def read_snapshot(self, gw: GameWindow) -> LocalRoleSnapshot | None:
        if self._native is None:
            return None
        try:
            return self._native.read_snapshot(gw)
        except Exception as exc:
            self._load_error = str(exc)
            return None

    def raw(self, gw: GameWindow, command: int, a0: int = 0, a1: int = 0, a2: int = 0, timeout: float = 3.0) -> ActionResult:
        if self._native is None:
            return ActionResult(False, self._load_error)
        try:
            reply = self._native.raw(gw, command, a0, a1, a2, timeout)
            return ActionResult(reply.ok, reply.detail)
        except Exception as exc:
            self._load_error = str(exc)
            return ActionResult(False, str(exc))

    def invoke(self, gw: GameWindow, action: Action) -> ActionResult:
        mapping = {
            Action.TRAIN: (Command.START_AUTO_FIGHT, 0, 0, 0),
            Action.DANH: (Command.START_AUTO_FIGHT, 0, 0, 0),
            Action.TRAIN_LSV: (Command.START_AUTO_FIGHT, 0, 0, 0),
            Action.TOI_LSV: (Command.CLICK_TRAVEL, 17, 0, 0),
            Action.ROI_LSV: (Command.CLICK_TRAVEL, 18, 0, 0),
        }
        args = mapping.get(action)
        if not args:
            return ActionResult(False, f"Workflow {action.value} cần cấu hình/target cụ thể")
        return self.raw(gw, *args)

    def party_create(self, gw: GameWindow) -> ActionResult:
        return self.raw(gw, Command.PARTY_CREATE)

    def party_leave(self, gw: GameWindow) -> ActionResult:
        return self.raw(gw, Command.PARTY_LEAVE)

    def party_invite(self, gw: GameWindow, target_role_id: int) -> ActionResult:
        return self.raw(gw, Command.PARTY_INVITE, int(target_role_id))

    def party_join(self, gw: GameWindow, leader_role_id: int) -> ActionResult:
        return self.raw(gw, Command.PARTY_JOIN, int(leader_role_id))

    def revive_normal(self, gw: GameWindow) -> ActionResult:
        return self.raw(gw, Command.REVIVE_NORMAL)

    def reload(self, gw: GameWindow) -> ActionResult:
        # Reload is an account/login workflow in TLM, not a generic gameplay
        # mutation. Keep it feature-level so it can verify the actual login UI.
        return ActionResult(False, "Reload cần LoginTab account workflow")

    def close(self) -> None:
        if self._native is not None:
            self._native.close()
