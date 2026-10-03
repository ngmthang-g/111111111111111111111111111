# Nga My support/healing skill reference

Status: **VERIFIED from frozen `Skills.xml` + AutoHp Lua/UI cross-check.**

Use actual Config SkillID/name as source of truth. Do not trust legacy Lua variable names when they conflict with Config and visible UI text.

| ID | Name | Type | Style | TargetType | CastRange | AttackRadius | ProgressTime ms | RequireLevel | RequireWeapon | Property | Built-in AutoHp |
|---:|---|---|---|---|---:|---:|---:|---:|---|---|---|
| 406 | Phật Quang Phổ Chiếu | Active | MultipleTargetsBuff | SelfAndAlly | 15 | 7 | 3000 | 40 | true | `emei_foguangpuzhao` | yes |
| 407 | Xung Hư Dưỡng Khí | Active | SingleTargetBuff | PeacePlayer | 15 | 0 | 3000 | 20 | false | `emei_zhongxuyangqi` | yes, legacy key misnamed KimChamDoKiep |
| 408 | Khởi Tử Hồi Sinh | Active | SingleTargetBuff | PeacePlayer | 3 | 0 | 10000 | 30 | false | `emei_qisihuansheng` | yes, revive support |
| 423 | Kim Châm Độ Kiếp | Active | SingleTargetBuff | PeacePlayer | 15 | 0 | 0 | 1 | false | `emei_jinzhendujie` | no built-in AutoHp fallback found |
| 424 | Thanh Tâm Phổ Thiện Chú | Active | SingleTargetBuff | PeacePlayer | 15 | 0 | 1000 | 45 | false | `emei_qingxinputianzhou` | yes |

## Critical naming mismatch

`Global_Constants.lua` contains:

`C_NMBuff.KIMCHAMDOKIEP = 407`

but:

- `Skills.xml` ID 407 = **Xung Hư Dưỡng Khí**;
- `AutoHp_Layout.xml` toggle `TogKimChamDoKiep` visibly says `Sử dụng [Xung hư dưỡng khí]`;
- `Skills.xml` ID 423 = **Kim Châm Độ Kiếp**.

Therefore 407 must be treated as Xung Hư Dưỡng Khí in new code/docs.

## Built-in AutoHp fallback

The built-in function chooses:

`406 -> 424 -> 407`

subject to user toggle + `Game.CheckCondition`.

This is a donor policy, not a requirement for an external tool. The user may explicitly configure 424 first or choose 423 if it is learned/usable.

## Recommended runtime validation before cast

- `Game.HasSkill(skillID)` when available/appropriate;
- `Game.CheckCondition(skillID)`;
- `Game.GetSkillCooldown(skillID)` ready;
- target type/HP/death eligibility;
- actual cast range;
- valid Unity/main-thread action path.

## Timeout guidance

ProgressTime differs significantly:

- 423 has 0 ms configured progress;
- 424 has 1000 ms;
- 406/407 have 3000 ms;
- 408 has 10000 ms.

Do not use one fixed delay for all support skills.
