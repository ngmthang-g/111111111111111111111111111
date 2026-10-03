from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import psutil


@dataclass(frozen=True, slots=True)
class CpuGpuSample:
    cpu: float
    gpu: float | None


class MonitorService:
    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, callback: Callable[[CpuGpuSample], None]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def worker() -> None:
            psutil.cpu_percent(None)
            while not self._stop.wait(self.interval):
                cpu = psutil.cpu_percent(None)
                # TLM reports N/A when nvidia-smi is unavailable. Keep that exact
                # visible behavior rather than inventing another GPU backend.
                callback(CpuGpuSample(cpu=cpu, gpu=None))

        self._thread = threading.Thread(target=worker, name="tlm-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


class DailyScheduleService:
    """Minute-resolution open/close schedule used by Login tab."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_key: tuple[int, int, int, int, str] | None = None

    def start(self, close_hm: tuple[int, int], open_hm: tuple[int, int], on_close: Callable[[], None], on_open: Callable[[], None]) -> None:
        self.stop()
        self._stop = threading.Event()

        def worker() -> None:
            while not self._stop.wait(1.0):
                now = datetime.now()
                key = (now.year, now.month, now.day, now.hour, f"{now.minute:02d}")
                if (now.hour, now.minute) == close_hm and key != self._last_key:
                    self._last_key = key
                    on_close()
                elif (now.hour, now.minute) == open_hm and key != self._last_key:
                    self._last_key = key
                    on_open()

        self._thread = threading.Thread(target=worker, name="tlm-login-schedule", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
