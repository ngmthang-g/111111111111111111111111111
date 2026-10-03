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
        self.gdi32 = ctypes.windll.gdi32 if self.available else None
        if self.available:
            self._enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            # TLM pixel.py uses PrintWindow(flag=2) so covered/off-screen game
            # windows can still be sampled. Explicit pointer-sized return types
            # avoid Win64 handle truncation.
            self.user32.GetWindowDC.argtypes = [wintypes.HWND]
            self.user32.GetWindowDC.restype = wintypes.HDC
            self.user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
            self.user32.ReleaseDC.restype = ctypes.c_int
            self.user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
            self.user32.PrintWindow.restype = wintypes.BOOL
            self.gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
            self.gdi32.CreateCompatibleDC.restype = wintypes.HDC
            self.gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
            self.gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
            self.gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
            self.gdi32.SelectObject.restype = wintypes.HGDIOBJ
            self.gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
            self.gdi32.GetPixel.restype = wintypes.COLORREF
            self.gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
            self.gdi32.DeleteObject.restype = wintypes.BOOL
            self.gdi32.DeleteDC.argtypes = [wintypes.HDC]
            self.gdi32.DeleteDC.restype = wintypes.BOOL

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

    def window_rect(self, hwnd: int) -> Rect | None:
        if not self.available or not hwnd:
            return None
        r = wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return None
        return Rect(r.left, r.top, r.right, r.bottom)

    def move_keep_size(self, hwnd: int, x: int, y: int) -> bool:
        if not self.available or not hwnd:
            return False
        rect = self.window_rect(hwnd)
        if not rect:
            return False
        return bool(self.user32.SetWindowPos(
            hwnd, 0, x, y, rect.width, rect.height,
            self.SWP_NOZORDER | self.SWP_NOACTIVATE,
        ))

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


    @staticmethod
    def _colorref_to_rgb(value: int) -> tuple[int, int, int]:
        return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF

    @staticmethod
    def color_compare(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: float = 0.0) -> bool:
        """Match TLM pixel.py percentage tolerance, channel by channel."""
        tol = max(0.0, float(tolerance))
        for got, want in zip(actual, expected):
            high = max(int(got), int(want))
            if high == 0:
                continue
            if abs(int(got) - int(want)) * 100.0 / high > tol:
                return False
        return True

    def printwindow_pixel(self, hwnd: int, client_x: int, client_y: int) -> tuple[int, int, int] | None:
        """Read one CLIENT-coordinate pixel using TLM's PrintWindow(flag=2) model.

        TLM captures the whole window, then converts client coordinates to the
        bitmap's frame-relative coordinates before sampling. This keeps pixel
        checks working when the game window is covered or moved off-screen.
        """
        if not self.available or not self.is_window(hwnd):
            return None
        wr = wintypes.RECT()
        cr = wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(wr)):
            return None
        if not self.user32.GetClientRect(hwnd, ctypes.byref(cr)):
            return None
        point = wintypes.POINT(0, 0)
        if not self.user32.ClientToScreen(hwnd, ctypes.byref(point)):
            return None
        width = max(1, int(wr.right - wr.left))
        height = max(1, int(wr.bottom - wr.top))
        px = int(client_x) + int(point.x - wr.left)
        py = int(client_y) + int(point.y - wr.top)
        if px < 0 or py < 0 or px >= width or py >= height:
            return None

        window_dc = self.user32.GetWindowDC(hwnd)
        if not window_dc:
            return None
        memory_dc = self.gdi32.CreateCompatibleDC(window_dc)
        bitmap = self.gdi32.CreateCompatibleBitmap(window_dc, width, height) if memory_dc else None
        old = None
        try:
            if not memory_dc or not bitmap:
                return None
            old = self.gdi32.SelectObject(memory_dc, bitmap)
            if not self.user32.PrintWindow(hwnd, memory_dc, 2):
                return None
            color = int(self.gdi32.GetPixel(memory_dc, px, py))
            if color == 0xFFFFFFFF:
                return None
            return self._colorref_to_rgb(color)
        finally:
            if memory_dc and old:
                self.gdi32.SelectObject(memory_dc, old)
            if bitmap:
                self.gdi32.DeleteObject(bitmap)
            if memory_dc:
                self.gdi32.DeleteDC(memory_dc)
            self.user32.ReleaseDC(hwnd, window_dc)

    def check_pixel(self, hwnd: int, client_x: int, client_y: int,
                    expected: tuple[int, int, int], tolerance: float = 0.0) -> bool:
        actual = self.printwindow_pixel(hwnd, client_x, client_y)
        return actual is not None and self.color_compare(actual, expected, tolerance)

    def wait_pixel(self, hwnd: int, client_x: int, client_y: int,
                   expected: tuple[int, int, int], timeout: float,
                   tolerance: float = 0.0, interval: float = 0.05,
                   cancel: object | None = None) -> bool:
        deadline = __import__("time").monotonic() + max(0.0, float(timeout))
        while __import__("time").monotonic() <= deadline:
            if cancel is not None and getattr(cancel, "is_set", lambda: False)():
                return False
            if self.check_pixel(hwnd, client_x, client_y, expected, tolerance):
                return True
            __import__("time").sleep(max(0.01, float(interval)))
        return False

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
