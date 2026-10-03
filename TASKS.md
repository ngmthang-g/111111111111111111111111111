# TASK BREAKDOWN — TLMTool 2.1.2 1:1

Mỗi task có acceptance riêng. Không đóng task chỉ vì source đã viết; runtime task phải có bằng chứng chạy thật.

| ID | Task | Deliverable | Trạng thái |
|---|---|---|---|
| T00 | Baseline / evidence lock | branch, source tree, knowledge/history, feature manifest | DONE |
| T01 | UI shell 1:1 | 11 tab visible, kích thước/caption/control/color baseline | IMPLEMENTED — WINDOWS VISUAL TEST PENDING |
| T02 | Start / quản lý cửa sổ | discover game, ẩn/hiện, grid 1..5, xếp chéo, đóng | IMPLEMENTED — RUNTIME UNTESTED |
| T03 | Login | game path/launch, account rows, scheduler, exact click/type/login sequence, after-login | PARTIAL — proxy/captcha/runtime proof pending |
| T04 | Native semantic bridge | x64 DLL, shared-memory protocol, per-PID attach, state/move/NPC/Train core; then expand command surface | CORE SOURCE IMPLEMENTED — WINDOWS BUILD/RUNTIME PENDING |
| T05 | Party | create team, invite burst, wait TeamID proof, after-party dispatch | TODO |
| T06 | Train | về thành, saved spot, filter/loot/heal/death/reconnect, sell/return/train | UI DONE / ENGINE TODO |
| T07 | Train LSV | enter/leave LSV, train spot, buff timer, death/heal/reconnect | UI DONE / ENGINE TODO |
| T08 | Phó Bản | team config + schedule + follow/pick/drop/buff + scenario execution | UI DONE / ENGINE TODO |
| T09 | Daily | Trừng ác + Tàng bảo đồ + heal/revive/reconnect + bulk controls | UI DONE / ENGINE TODO |
| T10 | Dồn vàng | return policy, receiver list, trade/session, sell/return/train | UI DONE / ENGINE TODO |
| T11 | Rao | up to 4 content slots/account, channel/interval, semantic chat send + echo | UI BASELINE DONE / ENGINE TODO |
| T12 | Tối ưu | CPU/GPU monitor, per-account profile buttons | CPU UI IMPLEMENTED / GAME PROFILE TODO |
| T13 | Info/update/package | info/free state, updater compatibility, Nuitka standalone build | PARTIAL |
| T14 | 1:1 verification | screenshot diff, control manifest, functional runtime matrix | TODO |

## T03 subtasks

- T03.1 choose/open game directory — implemented.
- T03.2 18 account rows — implemented.
- T03.3 password visibility — implemented.
- T03.4 exact login click sequence 613,302 -> 573,362 -> 684,506 with typing — implemented.
- T03.5 PrintWindow precondition/update-popup detection — pending.
- T03.6 captcha mode `Không/Tool` behavior — pending; must not auto-solve Captcha.
- T03.7 proxy/forwarder per account — pending.
- T03.8 scheduled close/open + after-login dispatch — scheduler implemented; completion proof pending.

## T04 subtasks

- T04.1 new clone wire protocol `Local\TLMToolClone_<PID>` — implemented.
- T04.2 x64 `WH_GETMESSAGE` bridge attach — implemented source.
- T04.3 read-only state snapshot — core source implemented.
- T04.4 Start/Stop AutoFight, move, mount, NPC — core source implemented.
- T04.5 Revive + bag/sell/treatment/loot primitives — pending port.
- T04.6 InputSync/internal click + direct trade/bag UI primitives — pending port.
- T04.7 Windows MSVC build proof — pending CI.
- T04.8 harmless per-PID live proof — pending runtime.

## Runtime acceptance rule

Every mutable workflow must follow:

`fresh snapshot -> guard -> max one mutable action -> state proof -> fresh snapshot`.

Timeout/request-sent is failure/unknown, never success proof.
