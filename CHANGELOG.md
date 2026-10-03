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
