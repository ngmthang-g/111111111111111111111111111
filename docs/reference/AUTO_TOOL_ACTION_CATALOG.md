# Auto Tool Action Catalog — exact semantic mutations for automation

Purpose: provide one compact lookup for **actions the Thần Long auto tool can issue semantically**. Future AI should consult this before searching UI buttons, packet names or native handlers.

This file contains only automation-relevant actions. It intentionally excludes unrelated client systems.

Evidence rule:

- **VERIFIED** = exact shipped Lua/native action or exact source-constructed payload is known.
- **SEMANTIC API VERIFIED** = the game uses the API, but no raw packet needs to be reproduced by the tool.
- **RUNTIME STATE REQUIRED** = action contract is known but current IDs/selection/shop state must be read fresh.

All external mutable calls still require the valid Unity/MainThread execution path. This catalog does not authorize arbitrary-thread invocation.

---

# 1. Auto Train start / stop

## Start Train

Status: **VERIFIED**.

```text
C_AutoModel.Train = 1
GUI.FindUI("AutoFight_Main"):StartAutoFight(C_AutoModel.Train)
```

Use this instead of opening AUTO -> clicking the visible `Đánh quái` settings tab.

## Stop / yield Train

Status: **VERIFIED**.

```text
GUI.FindUI("AutoFight_Main"):StartAutoFight(C_AutoModel.None)
```

Use before a higher-level flow takes movement/action ownership: Sell, explicit NPC travel, spot switching, etc.

Canonical source: `features/AUTO_TRAIN.md`.

---

# 2. Target / movement actions

## Select target

Status: **SEMANTIC API VERIFIED**.

```text
Game.SelectTarget(RoleID)
```

Proof: fresh `Game.SelectedTarget.RoleID` should equal the expected target.

## Chase target

Status: **SEMANTIC API VERIFIED**.

```text
Game.ChaseTarget(...)
```

Built-in combat/support uses it with calculated cast range.

## Move on current map

```text
Game.MoveTo(X,Y)
```

Status: **SEMANTIC API VERIFIED**.

## Route-aware travel

```text
Game.GoTo(MapID,X,Y,callback)
```

Cross-map built-in convention:

```text
Game.GoTo(MapID,-1,-1,...)
```

Travel proof:

```text
expected MapID + IsMapReady + valid position + distance<=tolerance
```

## Stop auto path

```text
Game.StopAutoPath()
```

Status: **SEMANTIC API VERIFIED**.

Canonical map source: `analysis/22_MAP_MINIMAP_RUNTIME.md`.

---

# 3. NPC route / interaction

## Resolve NPC position

Read-only:

```text
Game.GetNPCPosition(npcID)
```

## Built-in route helper

```text
GoToNPC(mapID,npcID)
```

Verified flow:

```text
if wrong map -> Game.GoTo(mapID,-1,-1)
 -> GetNPCPosition(npcID)
 -> Game.GoTo(mapID,npcX,npcY)
 -> Game.ClickNPC(npcID)
```

## Click/interact with NPC

```text
Game.ClickNPC(npcID)
```

Native analysis verifies this is a semantic interaction path, not a screen mouse click.

Do not invent fixed NPC X/Y when the runtime position API exists.

---

# 4. Skill actions

## General semantic cast

```text
Game.UseSkill(skillID)
```

Status: **SEMANTIC API VERIFIED** from shipped SkillBar.

## Targeted cast

```text
Game.RequestUsingSkillWithTarget(skillID, targetRoleID)
```

Status: **SEMANTIC API VERIFIED** from built-in combat/Nga My support.

## Positional cast

```text
Game.RequestUsingSkillWithPos(...)
```

Status: **SEMANTIC API VERIFIED** from built-in Auto Fight.

Before cast use:

```text
Game.HasSkill(skillID)
Game.CheckCondition(skillID)
Game.GetSkillCooldown(skillID)
Game.GetSkillLuaData(skillID) / GetSkillTemplateData(skillID)
```

Known Nga My identities:

```text
406 Phật Quang Phổ Chiếu
407 Xung Hư Dưỡng Khí
408 Khởi Tử Hồi Sinh
423 Kim Châm Độ Kiếp
424 Thanh Tâm Phổ Thiện Chú
```

Non-team beneficial-skill acceptance remains a runtime/server proof per intended skill/relationship.

---

# 5. Dynamic NPC GameDialog selection

Packet:

```text
CMD_SHOW_GAMEDIALOG = 100007
```

Status: **VERIFIED exact packet ID + payload construction**.

Runtime dialog data:

```text
Selections[selectionID] = visibleText
```

Submit:

```text
payload = selectionID:SelectedItemID
```

Common no-item form:

```text
actualSelectionID:-1
```

**RUNTIME STATE REQUIRED**: selection ID must come from the current dialog. Do not hardcode a global `Trị liệu` ID.

Use for:

- treatment/healer selections;
- NPC service choices;
- other server-driven dialog actions.

---

# 6. Auto Sell

## Open/shop-ready proof

Inbound shop packet:

```text
CMD_NPC_SHOP_DATA = 200034
```

The current `NPCShop` state supplies:

```text
NpcShopID
ShopID = CurrentShopData.ID
IsGuildShop
```

Do not sell before valid current shop state exists.

## Sell one current item instance

Packet:

```text
CMD_NPC_SHOP_SELL_REQUEST = 200036
```

Payload:

```text
itemInstanceID:NpcShopID:ShopID
```

Status: **VERIFIED exact request**.

Important:

```text
itemInstanceID = dbItemData.ID
```

not ItemID and not Position.

Before send:

```text
40000000 <= ItemID < 50000000 -> reject
Game.IsItemSellable(ItemID) must be true
user keep policy must allow sale
```

After send:

```text
wait RemoveItem(instanceID)
OR UpdateItemsList + fresh BagSnapshot
OR consistent shop/money proof
 -> rescan bag
```

Never execute a stale precomputed 90-slot sell list.

Canonical classification: `database/AUTO_SELL_CLASSIFICATION.md`.

---

# 7. Bag / item actions

## Sort bag

Packet:

```text
CMD_BAG_SORT = 100006
```

Bag payload:

```text
10
```

because `C_ItemSite.Bag = 10`.

## General item action

Packet:

```text
CMD_ITEM_ACTION = 100005
```

Verified forms:

```text
Equip   -> 1:instanceID
Use     -> 3:instanceID
Abandon -> 4:instanceID
Move    -> 5:instanceID:destinationSite
Split   -> 8:instanceID:quantity
```

Do not use destructive actions without explicit user policy/guards.

## Storage move

Verified:

```text
C_ItemAction.Move = 5
payload = 5:itemInstanceID:destinationSite
```

Known sites:

```text
Bag = 10
Storage pages = 11..15
```

---

# 8. Loot / item pack pickup

Status: **SEMANTIC API VERIFIED**.

Discovery:

```text
Game.GetNearbyItemPack(...)
Game.GetNearestItemPack(...)
```

Built-in action path uses:

```text
Game.HasPath(...)
Game.MoveToEx(...)
Game.ClickToObject(...)
Game.PickUpItemFromItemPack(itemPackID,slotIndex,UsingAuto)
```

Observed built-in pick-all:

```text
Game.PickUpItemFromItemPack(itemPackID,-1,1)
```

Proof from fresh pack/bag state; do not assume elapsed time means pickup succeeded.

---

# 9. Revive / Đầu thai

Packet:

```text
CMD_REVIVE_DATA = 200063
```

Exact types:

```text
1 = normal / Đầu thai
2 = newbie revive
3 = skill revive
```

Status: **VERIFIED exact request semantics**.

Use type 2 only when `IsEnableReviveNewbie` is true.
Use type 3 only when `IsEnableBySkill` is true.

Completion proof:

```text
local role alive
AND Revival state cleared
AND map ready
AND valid position
```

---

# 10. Team / Party actions

## Leave current team

Packet:

```text
CMD_TEAM_ACTION = 200057
```

Action:

```text
C_TeamAction.LeaveTeam = 4
payload = 4:selfRoleID
```

Status: **VERIFIED**.

## Request to join selected target's team

Packet:

```text
CMD_OTHER_ROLE_COMMAND = 200051
```

Command:

```text
C_OtherRoleCommand.TeamRequestJoin = 9
payload = 9:targetRoleID
```

Status: **VERIFIED exact source-constructed request**.

This is the preferred known request-to-join route when a candidate RoleID is already available.

Do not confuse it with the separate enum value `C_TeamAction.RequestJoin=7`.

## Invite selected target to local team

```text
CMD_OTHER_ROLE_COMMAND = 200051
C_OtherRoleCommand.TeamInviter = 5
payload = 5:targetRoleID
```

Status: **VERIFIED**.

## Party state proof

After join/invite/leave request:

```text
Game.RoleData.TeamID
C_TeamData
UpdateTeamData event/state
```

Request sent is not proof of acceptance.

Use per-RoleID anti-spam cooldowns.

---

# 11. Follow teammate

Built-in entry:

```text
GUI.FindUI("AutoFight_Main"):TurnOnFollowTarget(RoleID)
```

Status: **VERIFIED semantic action**.

Nearby teammate:

```text
GetNearTeammates -> current Position -> Game.MoveTo
```

Out of AOI/cross-map fallback:

```text
C_TeamData member MapID/PosX/PosY -> Game.GoTo
```

---

# 12. MainThread dispatch boundary

Internal dispatcher is VERIFIED:

```text
MainThread.Execute(System.Action)
 -> ConcurrentQueue<Action>
 -> Unity Update
 -> DoExecuteWorks
 -> Action.Invoke
```

External tool still needs one live proof that it can construct/root a valid managed Action and observe a harmless callback.

Do not replace this with a production arbitrary-thread direct Unity/Lua action call.

---

# 13. Action-time common guards

Before any mutable action, revalidate:

```text
PID alive/current
fresh snapshot/world generation
map ready if world action
local role alive unless revive action
Captcha/manual pause absent
progress/busy state compatible
current target/item/NPC/dialog/shop identity still valid
ActionGate free
```

Never issue an action solely because an old scan said it was valid.

---

# 14. Result proof hierarchy

Prefer concrete semantic result evidence:

```text
selected target identity
HP/death change
skill cooldown/progress transition
MapID/MapReady/position
GameDialog generation/change
NPCShop current state
RemoveItem / UpdateItemsList / money update
TeamID / C_TeamData update
Revival cleared + alive
item-pack disappearance / bag update
```

A timeout is a failure guard, not a success state.

---

# 15. Exact packet IDs used by this catalog

From `database/PACKET_IDS.csv`:

```text
100005 CMD_ITEM_ACTION
100006 CMD_BAG_SORT
100007 CMD_SHOW_GAMEDIALOG
200034 CMD_NPC_SHOP_DATA
200036 CMD_NPC_SHOP_SELL_REQUEST
200051 CMD_OTHER_ROLE_COMMAND
200057 CMD_TEAM_ACTION
200063 CMD_REVIVE_DATA
```

Do not infer an unknown payload merely because another packet name exists in the 169-command catalog.