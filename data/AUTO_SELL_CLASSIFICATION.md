# Auto Sell Classification — compact automation lookup contract

Purpose: give future Auto Sell builders the **minimum item/equipment facts needed for safe keep/sell decisions** without loading the full 5,238 Items or 22,763 Equips tables.

Status: built only from VERIFIED runtime Lua + decrypted Config schema/statistics. This is a policy/input contract, not a claim that every large static row has already been uploaded to GitHub.

Canonical evidence:

- `analysis/20_BAG_GRID_SHOP_UI_RUNTIME.md`
- `analysis/28_STATIC_DATA_DATABASE_EXPANSION.md`
- `features/AUTO_SELL.md`
- `analysis/35_RUNTIME_SNAPSHOT_CONTRACT.md`

---

# 1. Identity — never mix these

For every live bag record:

```text
ID        = current live item instance/database ID
ItemID    = static template ID
Position  = current slot
Site      = current container
```

Bag site = `10`.

Sell request uses **ID**, not ItemID and not Position.

---

# 2. Runtime guards — action-time authority

Before a sell candidate is allowed:

```text
instance still exists in fresh BagSnapshot
AND Site == Bag
AND ItemID not in protected quest range
AND Game.IsItemSellable(ItemID) == true
AND user keep policy == false
```

Stock Lua explicitly blocks:

```text
40000000 <= ItemID < 50000000
```

because that range is treated as quest items in the shipped sell path.

Useful semantic runtime classification APIs:

```text
Game.GetItemType(ItemID)
Game.GetEquipType(ItemID)
Game.IsItemSellable(ItemID)
Game.IsItemThrowable(ItemID)
Game.GetItemBasePrice(ItemID)
Game.GetItemBuyPrice(ItemID)
Game.GetItemMaxStack(ItemID)
```

Runtime semantic guards take priority over an offline row for mutable actions.

---

# 3. Static Item fields useful to Auto Sell

From `Items.xml` the automation-relevant subset is:

```text
ID
Name
ItemLevel
RequireLevel
BasePrice
SellPrice
Throwable
Sellable
Bound
Stack
MaxUsageTimes
DurationHour
ScriptID
TypeDesc
IDFamily10M
ExtraHint
Description
```

Do not preload icon/cosmetic-only fields unless the UI needs them.

Verified source totals:

```text
Items total       = 5,238
Sellable=true     = 4,970
Sellable=false    = 268
Throwable=true    = 5,005
Throwable=false   = 233
```

These counts describe static templates, not the current bag.

---

# 4. Static equipment fields useful to Auto Sell

From `Equips.xml`, keep the automation subset:

```text
ID
Name
Type
TypeName
EquipPoint
EquipPositionName
IsWeaponPosition
Level
FactionID
BoundRule
BasePrice
SellPrice
Durability
Identifiable
Star
BuffID
SetID
BaseAttributes
ExtraHint
Description
```

## Exact weapon rule

```text
EquipPoint == 0  => Weapon
```

Frozen Config has **4,685 equipment templates** at `EquipPoint=0`.

Do **not** use:

```text
Type < 10
```

as a universal Weapon test. Additional weapon forms include Blade, Sickle and Zither outside that simplistic range.

---

# 5. Safe default candidate classification

A conservative default policy for a tool that wants to keep weapons could be represented as:

```text
if ItemID in quest-protected range:
    KEEP
else if !runtime IsItemSellable(ItemID):
    KEEP
else if user protected ItemID/instance/keyword rule matches:
    KEEP
else if runtime item type == Equip:
    if runtime GetEquipType(ItemID) == Weapon:
        KEEP
    else:
        evaluate equipment policy
else:
    evaluate non-equipment policy
```

Do not automatically sell every non-weapon item. That would include medicine, gems, materials, special items and other valuable categories.

---

# 6. Recommended policy dimensions

Only add dimensions the user actually wants.

## Equipment

Useful filters:

```text
EquipPoint / runtime EquipType
Level
Star
FactionID
SetID
BuffID
BasePrice / SellPrice
Bound state
Identifiable
```

Possible user rules:

```text
keep all Weapon
keep Star >= N
keep Level >= N
keep specific equipment slots
keep set items
keep protected ItemIDs
sell remaining sellable equipment
```

## Non-equipment

Useful filters:

```text
ItemType
Name / ItemID whitelist
Sellable
Throwable
Stack
BasePrice / SellPrice
Bound
ScriptID / TypeDesc where meaningful
```

Possible rules:

```text
keep Medicine
keep Gem
keep specific material IDs
keep high-value item templates
sell only explicit categories
```

The safest production default is **allowlist the sell categories**, not “sell everything except weapons”.

---

# 7. Static cache vs live snapshot

Recommended external model:

```text
StaticTemplateCache[ItemID]
    Name
    category fields
    static sell/throw/value/equip metadata

LiveItemSnapshot
    ID
    ItemID
    Site
    Position
    Quantity
    Bound
    Durability
```

Then:

```text
fresh live instance
 -> join static cache by ItemID if available
 -> re-check runtime semantic guards
 -> apply user policy
 -> choose ONE candidate
```

Never issue a sell action directly from a static list.

---

# 8. Sell action / proof

Exact request:

```text
CMD_NPC_SHOP_SELL_REQUEST = 200036
payload = itemInstanceID:NpcShopID:ShopID
```

Current `NpcShopID` and `ShopID` must come from the current live NPCShop transaction state.

After one request:

```text
WAIT RemoveItem(instanceID)
OR UpdateItemsList + fresh scan
OR consistent shop/money update
```

Then **rescan** and choose the next instance.

---

# 9. No 90-click fallback in semantic mode

The client already exposes:

- current bag items;
- live instance IDs;
- current free space;
- semantic sellability;
- shop identifiers;
- RemoveItem/UpdateItemsList lifecycle.

Therefore the production semantic loop should stop when a fresh policy scan has zero sell candidates or the configured free-space target is reached.

Blindly selling/clicking a fixed number of slots is only a legacy prototype fallback and should not be treated as the canonical design.

---

# 10. Large static data status

The schema/statistics above are VERIFIED, but the full large normalized Items/Equips CSV chunk sets are not currently present under `database/static/...`.

Until materialized:

- use runtime `GetItemType/GetEquipType/IsItemSellable` for current decisions;
- use the known Config schema/rules above;
- materialize only targeted static rows/categories when a concrete keep/sell policy needs them.

Do not fabricate a missing CSV record.