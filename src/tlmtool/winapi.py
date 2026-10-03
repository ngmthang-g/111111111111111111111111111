from __future__ import annotations

import ctypes
import os
import subprocess
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import psutil

from .model import GameWindow

GAME_EXE = "Thần Long  Mobile.exe"


@dataclass(slots=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


class WindowsApi:
    SW_HIDE = 0
    SW_SHOW = 5
    SW_RESTORE = 9
    WM_CLOSE = 0x0010
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010

    def __init__(self) -> None:
        self.available = os.name == "nt"
        self.user32 = ctypes.windll.user32 if self.available else None
        if self.available:
            self._enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def _process_name(self, pid: int) -> str:
        try:
            return psutil.Process(pid).name()
        except (psutil.Error, OSError):
            return ""

    def game_windows(self, include_hidden: bool = True) -> list[GameWindow]:
        """Enumerate top-level game windows.

        TLM's "Ẩn hết" keeps windows discoverable so "Xem trước"/"Tách rời"
        can restore them later.  Therefore hidden windows must not disappear
        from the discovery set.  Callers that explicitly need visible-only
        windows can pass include_hidden=False.
        """
        if not self.available:
            return []
        found: list[GameWindow] = []

        @self._enum_proc
        def cb(hwnd: int, _lparam: int) -> bool:
            if not self.user32.IsWindow(hwnd):
                return True
            if not include_hidden and not self.user32.IsWindowVisible(hwnd):
                return True
            # Ignore owned helper/tool windows from the game process.  The game
            # client itself is an unowned top-level window.
            if self.user32.GetWindow(hwnd, 4):  # GW_OWNER
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(max(1, length + 1))
            self.user32.GetWindowTextW(hwnd, title, len(title))
            pid = wintypes.DWORD()
            tid = self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pname = self._process_name(pid.value)
            if pname.casefold() == GAME_EXE.casefold():
                found.append(GameWindow(pid.value, int(hwnd), int(tid), title.value, pname))
            return True

        self.user32.EnumWindows(cb, 0)
        found.sort(key=lambda w: (w.pid, w.hwnd))
        return found

    def is_window(self, hwnd: int) -> bool:
        return bool(self.available and hwnd and self.user32.IsWindow(hwnd))

    def is_visible(self, hwnd: int) -> bool:
        return bool(self.available and hwnd and self.user32.IsWindowVisible(hwnd))

    def is_hung(self, hwnd: int) -> bool:
        return bool(self.available and hwnd and self.user32.IsHungAppWindow(hwnd))

    def activate(self, hwnd: int) -> bool:
        if not self.is_window(hwnd):
            return False
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindow(hwnd, self.SW_RESTORE)
        else:
            self.user32.ShowWindow(hwnd, self.SW_SHOW)
        return bool(self.user32.SetForegroundWindow(hwnd))

    def show(self, hwnd: int, visible: bool) -> None:
        if self.available and hwnd:
            if visible and self.user32.IsIconic(hwnd):
                self.user32.ShowWindow(hwnd, self.SW_RESTORE)
            else:
                self.user32.ShowWindow(hwnd, self.SW_SHOW if visible else self.SW_HIDE)

    def close(self, hwnd: int) -> None:
        if self.available and hwnd:
            self.user32.PostMessageW(hwnd, self.WM_CLOSE, 0, 0)

    def move(self, hwnd: int, x: int, y: int, w: int, h: int) -> None:
        if self.available and hwnd:
            self.user32.SetWindowPos(hwnd, 0, x, y, w, h, self.SWP_NOZORDER | self.SWP_NOACTIVATE)

    def client_rect(self, hwnd: int) -> Rect | None:
        if not self.available or not hwnd:
            return None
        r = wintypes.RECT()
        if not self.user32.GetClientRect(hwnd, ctypes.byref(r)):
            return None
        return Rect(r.left, r.top, r.right, r.bottom)

    def screen_size(self) -> tuple[int, int]:
        if not self.available:
            return (1920, 1080)
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

    def arrange_grid(self, windows: Iterable[GameWindow], columns: int, diagonal: bool = False) -> None:
        items = list(windows)
        if not items:
            return
        columns = max(1, min(5, columns))
        sw, sh = self.screen_size()
        if diagonal:
            width, height = min(960, sw - 40), min(640, sh - 80)
            for i, gw in enumerate(items):
                self.move(gw.hwnd, 18 * i, 18 * i, width, height)
            return
        rows = (len(items) + columns - 1) // columns
        width = max(320, sw // columns)
        height = max(240, sh // max(1, rows))
        for i, gw in enumerate(items):
            col, row = i % columns, i // columns
            self.move(gw.hwnd, col * width, row * height, width, height)

    def launch_game(self, directory: str) -> subprocess.Popen | None:
        root = Path(directory)
        exe = root / GAME_EXE
        if not exe.exists():
            # Some distributions place executable one level under Game/.
            alt = root / "Game" / GAME_EXE
            exe = alt if alt.exists() else exe
        if not exe.exists():
            return None
        return subprocess.Popen([str(exe)], cwd=str(exe.parent))


    def scaled_click(self, hwnd: int, x: int, y: int, master_w: int = 1280, master_h: int = 720) -> bool:
        rect = self.client_rect(hwnd)
        if not rect or rect.width <= 0 or rect.height <= 0:
            return False
        return self.send_click(hwnd, int(rect.width * x / master_w), int(rect.height * y / master_h))

    def send_key(self, hwnd: int, vk: int, down: bool = True) -> None:
        if not self.available or not hwnd:
            return
        msg = 0x0100 if down else 0x0101
        self.user32.PostMessageW(hwnd, msg, vk, 0)

    def select_all(self, hwnd: int) -> None:
        VK_CONTROL, VK_A = 0x11, 0x41
        self.send_key(hwnd, VK_CONTROL, True); self.send_key(hwnd, VK_A, True); self.send_key(hwnd, VK_A, False); self.send_key(hwnd, VK_CONTROL, False)

    def type_text(self, hwnd: int, text: str) -> None:
        if not self.available or not hwnd:
            return
        WM_CHAR = 0x0102
        for ch in text:
            self.user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)

    def send_click(self, hwnd: int, client_x: int, client_y: int) -> bool:
        """Best-effort background click fallback for login-only UI operations.

        Gameplay automation should use semantic/native backend; this is limited to
        the observed TLM login click sequence and ordinary launcher/UI controls.
        """
        if not self.available or not hwnd:
            return False
        WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0200, 0x0201, 0x0202, 0x0001
        lparam = (client_y & 0xFFFF) << 16 | (client_x & 0xFFFF)
        self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        self.user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        self.user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
        return True
