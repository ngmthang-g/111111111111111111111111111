# PROJECT KNOWLEDGE

## Project Identity
- Name: TLMTool 2.1.2 compatibility clone
- Repository: `ngmthang-g/111111111111111111111111111`
- Development branch: `tlm-clone-2.1.2`
- Target version/UI: TLMTool 2.1.2
- Platform: Windows x64
- Frontend: Python 3.10 + Tkinter
- Native: C++17 x64 semantic bridge
- Current runtime status: **BUILD PASS / RUNTIME UNTESTED**

## Evidence baseline
1. User-supplied TLMTool 2.1.2 distribution and screenshots.
2. User-supplied 12.4.2 source/binaries.
3. `ngmthang-g/clinent-game-than-long-DATA-2222` verified knowledge base.
4. Static strings/export inspection of supplied TLM binary.

## Product surface locked to 2.1.2
Visible tabs:
`▶, Login, Party, Train, Train LSV, Phó Bản, Daily, Dồn, Rao, Tối ưu, i`.

Developer/internal tabs found in binary are not added to the normal product surface because they are not visible in the supplied FREE 2.1.2 baseline screenshots.

## Architecture

```text
Tkinter UI/profile
 -> per-PID feature orchestrator
 -> immutable snapshot
 -> safety guard
 -> one-action gate
 -> TlmSemanticBridge.dll
 -> target game window thread
 -> semantic IL2CPP/Lua/UI action
 -> state proof
 -> rescan
```

Ordinary process/window arrangement and game launching remain external Win32 operations.

## Hard rules
- No raw live client pointer may cross into Python or be retained across scans/map transitions.
- One mutable action per PID.
- No fixed sleep counts as action success.
- Map transition blocks deep object access.
- Item `ID` (instance) != `ItemID` (template) != `Position`.
- Captcha means pause/manual path; no automatic bypass.
- No silent feature addition or deletion relative to 2.1.2 baseline.
- Build/CI pass must not be promoted to runtime pass.

## Known verified client facts used
- Train mode = `C_AutoModel.Train = 1`.
- Train starts semantically through `AutoFight_Main`.
- Bag site = 10; sell uses live item instance.
- Revive packet family/type is known.
- Dynamic `GameDialog.Selections` must be read at runtime; no global treatment selection ID.
- Party join/leave/invite packet semantics are known in DATA-2222.
- InputSync hidden-click method/lifecycle is statically solved for frozen client hash.

## TLM binary facts used
- Main app is Python 3.10/Nuitka + Tkinter/Pillow/psutil/win32/frida.
- `data/resources.dat` is a PE64 version/input/network hook library with MinHook exports.
- Login baseline click sequence observed in embedded source strings:
  `username (613,302) -> type -> password (573,362) -> type -> Login (684,506)`.
- TLM has memory/Lua helpers for chat, party, sell, dialog, movement and AutoFight.
- Main visible FREE state reports `Bản quyền FREE vĩnh viễn`.

## Current implementation state
### Implemented source
- 11 visible tabs and baseline controls.
- Start window discovery/layout/hide/show/close.
- game folder selection/launch.
- account table/scheduler/password toggle/login sequence.
- CPU monitor and TLM-compatible GPU N/A presentation when nvidia-smi path is absent.
- new x64 semantic bridge protocol and Python attach/client.
- core native bridge for state/movement/mount/NPC/Train plus TeamID/profile/vitals snapshot fields, create/leave/invite/join Party packets and normal revive.
- Train source core now includes saved coordinates, per-account scan, move/fight state proof, stop control and normal-revive return-to-spot. Sell/treatment/loot/reconnect remain explicitly pending.
- Party group workflow matching the recovered TLM order: leave old teams -> prove TeamID empty -> leader creates team -> invite burst -> membership proof -> optional after-party dispatch.
- TLM Start hide behavior corrected to off-screen (-2200,-2200) rather than SW_HIDE; tight stack is (0,0), diagonal stack is +50/+50.

### Build-confirmed
- GitHub Actions Windows x64 builds the native DLL and Nuitka standalone application successfully. First full green build: run `37111235479`, artifact `TLMTool-2.1.2-clone-windows-x64`.

### Not yet runtime-proven
Everything above that depends on a real frozen client. See `TASKS.md`.

## Failed/unsafe mechanisms to avoid
- CreateRemoteThread continuous gameplay worker as primary mutation engine.
- long queues based on stale bag/target snapshots.
- arbitrary direct mutable Unity/Lua calls from worker threads.
- fixed selection IDs for dynamic NPC dialogs.
- OCR/pixel scanning when semantic API already exposes the state.
- auto-solving Captcha.
