# CHANGELOG

## [2.1.2-clone.0] - 2026-10-03

### Requested
- Rebuild TLMTool 2.1.2 1:1 from supplied TLM distribution, report, DATA-2222 and 12.4.2 source.
- No user-visible feature additions or omissions.
- Split work into small auditable tasks.

### Added / Changed
- Initialized Python 3.10/Tkinter frontend with all 11 visible TLM tabs.
- Implemented Start window management and visible quick-control matrix.
- Implemented Login screen baseline, account grid, scheduler and recovered click/type sequence.
- Implemented baseline UI for Party, Train, Train LSV, Phó Bản, Daily, Dồn, Rao and Tối ưu.
- Added per-PID one-action gate.
- Added new clone-native shared-memory protocol.
- Implemented the first clone-native semantic bridge slice from the user-provided 12.4.2 donor knowledge: state, movement, mount, NPC and Train start/stop.
- Added Python native bridge attach/client using `WH_GETMESSAGE`.

### Build
- Python source: syntax compile PASS in Linux analysis environment.
- Windows x64 native DLL: RUNTIME/BUILD UNTESTED until Windows CI runs.

### Runtime
- Status: **RUNTIME UNTESTED**.
- No real game-client behavior is marked pass yet.

### Next
- Finish Login proxy/update-popup/captcha-manual path.
- Runtime-build/attach proof for bridge.
- Implement Party then Train engines in task order.


### Continued implementation — 2026-10-03
- Fixed the native bridge source regression caused by literal newline escapes.
- CI now builds TlmSemanticBridge.dll and the Nuitka Windows standalone distribution successfully.
- Corrected Start window hiding to TLM's off-screen move behavior and corrected tight/diagonal stacking semantics.
- Expanded Login to the recovered 100-row scrolling model, captcha mode selector, batch launch/login proof and after-login dispatch.
- Extended snapshots with TeamID/profile/vitals fields.
- Added exact create/leave/invite/join Party packet primitives and normal revive type=1.
- Rebuilt Party groups with six account selectors, leader-at-first-slot semantics, concurrent group creation and TeamID state proof.

Runtime remains **UNTESTED** against the frozen game client; build success is not promoted to runtime success.
