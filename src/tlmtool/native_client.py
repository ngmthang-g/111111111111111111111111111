from __future__ import annotations

import ctypes
import os
import threading
import time
from ctypes import wintypes
from pathlib import Path

from .model import GameWindow, LocalRoleSnapshot

MAGIC = 0x324D4C54
PROTOCOL = 0x00020102
WAKE = 0x8000 + 0x531
WH_GETMESSAGE = 3


class Snapshot(ctypes.Structure):
    # Keep this field order exactly synchronized with native/include/protocol.h.
    _fields_ = [
        ("validMask", ctypes.c_uint32),
        ("roleID", ctypes.c_int32), ("teamID", ctypes.c_int32),
        ("level", ctypes.c_int32), ("factionID", ctypes.c_int32),
        ("hp", ctypes.c_int32), ("maxHP", ctypes.c_int32),
        ("mapID", ctypes.c_int32), ("x", ctypes.c_int32), ("y", ctypes.c_int32),
        ("riding", ctypes.c_int32), ("autoPathing", ctypes.c_int32),
        ("mapReady", ctypes.c_int32), ("waitingChangeMap", ctypes.c_int32),
        ("dead", ctypes.c_int32), ("autoFight", ctypes.c_int32),
        ("freeBagSpace", ctypes.c_int32),
        ("characterName", ctypes.c_wchar * 64),
    ]


class Request(ctypes.Structure):
    _fields_ = [("command", ctypes.c_uint32), ("arg0", ctypes.c_int32), ("arg1", ctypes.c_int32), ("arg2", ctypes.c_int32)]


class BagItemSnapshot(ctypes.Structure):
    _fields_ = [
        ("instanceID", ctypes.c_int64), ("itemID", ctypes.c_int32), ("site", ctypes.c_int32),
        ("position", ctypes.c_int32), ("quantity", ctypes.c_int32), ("bound", ctypes.c_int32),
        ("throwable", ctypes.c_int32), ("sellable", ctypes.c_int32), ("isEquip", ctypes.c_int32),
        ("isWeapon", ctypes.c_int32), ("itemTypeCode", ctypes.c_int32), ("equipTypeCode", ctypes.c_int32),
        ("name", ctypes.c_wchar * 96), ("itemType", ctypes.c_wchar * 32), ("equipType", ctypes.c_wchar * 32),
    ]


class BagPageSnapshot(ctypes.Structure):
    _fields_ = [("totalCount", ctypes.c_int32), ("pageStart", ctypes.c_int32), ("pageCount", ctypes.c_int32),
                ("freeBagSpace", ctypes.c_int32), ("items", BagItemSnapshot * 20)]


class Response(ctypes.Structure):
    _fields_ = [
        ("ok", ctypes.c_int32), ("resultCode", ctypes.c_int32), ("value0", ctypes.c_int32),
        ("value1", ctypes.c_int32), ("value64_0", ctypes.c_int64), ("value64_1", ctypes.c_int64),
        ("snapshot", Snapshot), ("bagPage", BagPageSnapshot), ("detail", ctypes.c_wchar * 512),
    ]


class SharedBlock(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32), ("protocolVersion", ctypes.c_uint32), ("targetPid", ctypes.c_uint32),
        ("targetWindowThreadId", ctypes.c_uint32), ("requestSeq", ctypes.c_long), ("completedSeq", ctypes.c_long),
        ("bridgeLoaded", ctypes.c_long), ("bridgeBusy", ctypes.c_long), ("request", Request), ("response", Response),
    ]


class Command:
    READ_STATE=1; TOGGLE_RIDE=2; START_PATH=3; STOP_PATH=4; CLICK_NPC=5; CONFIRM_MAP=6; REVIVE=7
    START_AUTO_FIGHT=8; STOP_AUTO_FIGHT=9; BEGIN_SELL=10; ADVANCE_SELL=11; SELL_NEXT=12; CLOSE_SELL=13
    CLICK_INTERNAL=14; BEGIN_TREATMENT=15; ADVANCE_TREATMENT=16; CLOSE_TREATMENT=17; READ_CURRENCY=18
    READ_BAG_PAGE=19; DROP_BAG_ITEM=20; SELL_BAG_ITEM=21; SELECT_TARGET=22; CLICK_TRAVEL=23
    CONFIRM_TRAVEL=24; TEST_OPEN_BAG=25; CLICK_INTERNAL_RAW=26; DRAG_INTERNAL=27; PROBE_LOOT=28
    PICK_NEAREST_LOOT=29; PROBE_UI_DIRECT=32; INVOKE_UI_DIRECT=33
    PARTY_LEAVE=34; PARTY_INVITE=35; PARTY_JOIN=36; REVIVE_NORMAL=37; PARTY_CREATE=38


class BridgeReply:
    __slots__ = ("ok","detail","result_code","value0","value1","value64_0","value64_1","snapshot","bag")
    def __init__(self, r: Response):
        self.ok=bool(r.ok); self.detail=str(r.detail); self.result_code=int(r.resultCode); self.value0=int(r.value0); self.value1=int(r.value1)
        self.value64_0=int(r.value64_0); self.value64_1=int(r.value64_1); self.snapshot=r.snapshot; self.bag=r.bagPage


class BridgeSession:
    def __init__(self, game: GameWindow, dll_path: Path) -> None:
        if os.name != "nt": raise RuntimeError("Windows only")
        self.game=game; self.dll_path=dll_path; self._lock=threading.RLock(); self._seq=0
        self.kernel32=ctypes.windll.kernel32; self.user32=ctypes.windll.user32
        # Explicit Win64 signatures: ctypes defaults to c_int and would truncate HMODULE/FARPROC/HHOOK on x64.
        self.kernel32.CreateFileMappingW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.LPCWSTR]
        self.kernel32.CreateFileMappingW.restype=wintypes.HANDLE
        self.kernel32.MapViewOfFile.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t]
        self.kernel32.MapViewOfFile.restype=ctypes.c_void_p
        self.kernel32.UnmapViewOfFile.argtypes=[ctypes.c_void_p]; self.kernel32.UnmapViewOfFile.restype=wintypes.BOOL
        self.kernel32.CloseHandle.argtypes=[wintypes.HANDLE]; self.kernel32.CloseHandle.restype=wintypes.BOOL
        self.kernel32.LoadLibraryW.argtypes=[wintypes.LPCWSTR]; self.kernel32.LoadLibraryW.restype=ctypes.c_void_p
        self.kernel32.GetProcAddress.argtypes=[ctypes.c_void_p,ctypes.c_char_p]; self.kernel32.GetProcAddress.restype=ctypes.c_void_p
        self.kernel32.FreeLibrary.argtypes=[ctypes.c_void_p]; self.kernel32.FreeLibrary.restype=wintypes.BOOL
        self.user32.SetWindowsHookExW.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD]
        self.user32.SetWindowsHookExW.restype=ctypes.c_void_p
        self.user32.UnhookWindowsHookEx.argtypes=[ctypes.c_void_p]; self.user32.UnhookWindowsHookEx.restype=wintypes.BOOL
        self.user32.PostThreadMessageW.argtypes=[wintypes.DWORD,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        self.user32.PostThreadMessageW.restype=wintypes.BOOL
        name=f"Local\\TLMToolClone_{game.pid}"
        INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
        PAGE_READWRITE=0x04; FILE_MAP_ALL_ACCESS=0xF001F
        self.mapping=self.kernel32.CreateFileMappingW(INVALID_HANDLE_VALUE,None,PAGE_READWRITE,0,ctypes.sizeof(SharedBlock),name)
        if not self.mapping: raise ctypes.WinError()
        self.view=self.kernel32.MapViewOfFile(self.mapping,FILE_MAP_ALL_ACCESS,0,0,ctypes.sizeof(SharedBlock))
        if not self.view: raise ctypes.WinError()
        self.shared=ctypes.cast(self.view,ctypes.POINTER(SharedBlock)).contents
        ctypes.memset(self.view,0,ctypes.sizeof(SharedBlock))
        self.shared.magic=MAGIC; self.shared.protocolVersion=PROTOCOL; self.shared.targetPid=game.pid; self.shared.targetWindowThreadId=game.thread_id
        if not dll_path.exists(): raise FileNotFoundError(dll_path)
        self.local_module=self.kernel32.LoadLibraryW(str(dll_path))
        if not self.local_module: raise ctypes.WinError()
        proc=self.kernel32.GetProcAddress(self.local_module,b"TlmGetMessageHook")
        if not proc: raise RuntimeError("TlmGetMessageHook export missing")
        self.hook=self.user32.SetWindowsHookExW(WH_GETMESSAGE,proc,self.local_module,game.thread_id)
        if not self.hook: raise ctypes.WinError()
        self.user32.PostThreadMessageW(game.thread_id,WAKE,0,0)
        deadline=time.monotonic()+3.0
        while not self.shared.bridgeLoaded and time.monotonic()<deadline: time.sleep(0.02)
        if not self.shared.bridgeLoaded: raise RuntimeError("bridge did not load into game window thread")

    def close(self) -> None:
        try:
            if getattr(self,"hook",None): self.user32.UnhookWindowsHookEx(self.hook)
        finally:
            if getattr(self,"view",None): self.kernel32.UnmapViewOfFile(self.view)
            if getattr(self,"mapping",None): self.kernel32.CloseHandle(self.mapping)
            if getattr(self,"local_module",None): self.kernel32.FreeLibrary(self.local_module)
        self.hook=None; self.view=None; self.mapping=None; self.local_module=None

    def request(self, command:int, arg0:int=0, arg1:int=0, arg2:int=0, timeout:float=3.0) -> BridgeReply:
        with self._lock:
            self._seq+=1; seq=self._seq
            self.shared.request=Request(command,arg0,arg1,arg2)
            self.shared.response=Response()
            self.shared.requestSeq=seq
            self.user32.PostThreadMessageW(self.game.thread_id,WAKE,0,0)
            deadline=time.monotonic()+timeout
            while self.shared.completedSeq != seq and time.monotonic()<deadline: time.sleep(0.005)
            if self.shared.completedSeq != seq: raise TimeoutError(f"bridge timeout cmd={command}")
            return BridgeReply(self.shared.response)


class RuntimeBridgeManager:
    def __init__(self, dll_path: Path | None = None) -> None:
        base=Path(__file__).resolve().parent
        self.dll_path=dll_path or (base / "TlmSemanticBridge.dll")
        self.sessions:dict[int,BridgeSession]={}; self._lock=threading.RLock()

    def _session(self, gw:GameWindow) -> BridgeSession:
        with self._lock:
            old=self.sessions.get(gw.pid)
            if old and old.game.thread_id==gw.thread_id: return old
            if old:
                try:old.close()
                except Exception:pass
            s=BridgeSession(gw,self.dll_path);self.sessions[gw.pid]=s;return s

    def raw(self, gw:GameWindow, command:int, a0:int=0,a1:int=0,a2:int=0,timeout:float=3.0)->BridgeReply:
        return self._session(gw).request(command,a0,a1,a2,timeout)

    def read_snapshot(self, gw:GameWindow) -> LocalRoleSnapshot | None:
        r=self.raw(gw,Command.READ_STATE)
        if not r.ok:return None
        s=r.snapshot
        return LocalRoleSnapshot(
            pid=gw.pid, captured_ms=int(time.time()*1000), valid_mask=int(s.validMask),
            role_id=s.roleID, name=str(s.characterName),
            level=s.level, faction_id=s.factionID, team_id=s.teamID,
            hp=s.hp, max_hp=s.maxHP,
            map_id=s.mapID, x=s.x, y=s.y,
            is_dead=bool(s.dead), is_riding=bool(s.riding),
            auto_pathing=bool(s.autoPathing), auto_fight=bool(s.autoFight),
            free_bag_space=int(s.freeBagSpace),
            waiting_change_map=bool(s.waitingChangeMap),
            map_ready=bool(s.mapReady),
        )

    def close(self)->None:
        with self._lock:
            for s in self.sessions.values():
                try:s.close()
                except Exception:pass
            self.sessions.clear()
