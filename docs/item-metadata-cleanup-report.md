# Item Metadata Cleanup Report — PR 1

**Branch:** `claude/new-session-ras567`
**Scope:** 5e2024 item library (`server/data/rules/5e2024/items/*.json`, 478 items)

---

## Before / After Counts

| Issue | Before | After |
|---|---|---|
| Attunement disagreements (`requires_attunement ≠ attunement.required`) | 1 | 0 |
| Contradictory recharge (`recharge_formula` set with `charges_max == 0`) | 68 | 0 |
| Filler granted_actions on uncharged items (`"Activate this item."`, `charges_max == 0`) | 67 | 0 |
| Scaffold passive notes (`"Starter magic item metadata."`) | 87 | 0 |
| Vorpal Sword in mundane_weapons.json | 1 | 0 |
| Homebrew items flagged as draft | 0 | 11 |

---

## Changes Made

### 1. Attunement authority unified
`item_schema.normalize_item_record` now derives `requires_attunement` from `attunement.required` (the nested object is canonical). Source data also synced so no disagreements remain at rest.

### 2. Vorpal Sword corrected
Moved from `mundane_weapons.json` → `legendary_magic_items.json`.
- `rarity`: `"common"` → `"legendary"`
- `requires_attunement`: `true` ✓
- `attunement.required`: `false` → `true` ✓
- `category`: `"weapon"` preserved per spec

### 3. Contradictory recharge cleared (68 items)
For every item with `charges_max == 0`, `recharge_formula` was cleared to `""` and `recharge_type` set to `"none"`.

### 4. Filler granted_actions stripped (67 items)
Removed `granted_actions` entries with `summary == "Activate this item."` only on items where `charges_max == 0`. These are provably inert (no charge to spend).

### 5. Scaffold passive notes stripped (87 items)
Removed `passive_effects` entries with `summary == "Starter magic item metadata."`.

### 6. Homebrew TODO items flagged as draft (11 items)
Added `"draft": true` to homebrew items containing TODO placeholder summaries. **No mechanics invented.** Items need human authoring.

---

## Items Requiring Human Review

### Charged items with generic "Activate this item." action (left unchanged, 31 items)

These have `charges_max > 0` so a real activation mechanic may exist — they were deliberately left for human review:

| File | ID | Name |
|---|---|---|
| legendary_magic_items.json | ring-of-three-wishes | Ring of Three Wishes |
| legendary_magic_items.json | rod-of-lordly-might | Rod of Lordly Might |
| rare_magic_items.json | helm-of-teleportation | Helm of Teleportation |
| rare_magic_items.json | horn-of-valhalla | Horn of Valhalla |
| rare_magic_items.json | necklace-of-fireballs | Necklace of Fireballs |
| rare_magic_items.json | ring-of-x-ray-vision | Ring of X-Ray Vision |
| rare_magic_items.json | rod-of-rulership | Rod of Rulership |
| rare_magic_items.json | staff-of-healing | Staff of Healing |
| rare_magic_items.json | staff-of-the-woodlands | Staff of the Woodlands |
| rare_magic_items.json | staff-of-withering | Staff of Withering |
| rare_magic_items.json | wand-of-enemy-detection | Wand of Enemy Detection |
| rare_magic_items.json | wand-of-fear | Wand of Fear |
| rare_magic_items.json | wand-of-fireballs | Wand of Fireballs |
| rare_magic_items.json | wand-of-lightning-bolts | Wand of Lightning Bolts |
| rare_magic_items.json | wand-of-paralysis | Wand of Paralysis |
| rare_magic_items.json | wand-of-wonder | Wand of Wonder |
| uncommon_magic_items.json | wand-of-magic-missiles | Wand of Magic Missiles |
| uncommon_magic_items.json | wand-of-web | Wand of Web |
| uncommon_magic_items.json | wand-of-secrets | Wand of Secrets |
| uncommon_magic_items.json | wand-of-the-war-mage-plus1 | Wand of the War Mage +1 |
| uncommon_magic_items.json | ring-of-jumping | Ring of Jumping |
| uncommon_magic_items.json | eyes-of-charming | Eyes of Charming |
| uncommon_magic_items.json | gem-of-brightness | Gem of Brightness |
| very_rare_magic_items.json | rod-of-absorption | Rod of Absorption |
| very_rare_magic_items.json | staff-of-fire | Staff of Fire |
| very_rare_magic_items.json | staff-of-frost | Staff of Frost |
| very_rare_magic_items.json | staff-of-power | Staff of Power |
| very_rare_magic_items.json | staff-of-striking | Staff of Striking |
| very_rare_magic_items.json | staff-of-thunder-and-lightning | Staff of Thunder and Lightning |
| very_rare_magic_items.json | thunder-mage-quarterstaff-plus-3 | Thunder Mage Quarterstaff, +3 |
| very_rare_magic_items.json | wand-of-polymorph | Wand of Polymorph |

### Homebrew draft items (need mechanic authoring, 11 items)

These items have `"draft": true` added. Each contains TODO placeholder summaries that need a human to write the real mechanics. **No new effects were invented.**

- `baron-s-signet-ring`
- `brosst-guard-captain-s-blade`
- `bruno-s-lucky-treat`
- `chaos-wheel-coin`
- `cultist-black-candle`
- `fireball-viewer-token`
- `guild-of-seagull-token`
- `prison-break-lockpick-set`
- `seagull-feather-cloak`
- `shadow-prisoner-s-shank`
- `shar-touched-amulet`

---

## Files Changed

- `server/item_schema.py` — normalizer guard: `requires_attunement` derived from `attunement.required`
- `server/data/rules/5e2024/items/mundane_weapons.json` — vorpal-sword removed
- `server/data/rules/5e2024/items/legendary_magic_items.json` — vorpal-sword added (corrected)
- `server/data/rules/5e2024/items/adventuring_gear.json` — recharge/filler/scaffold fixes
- `server/data/rules/5e2024/items/common_magic_items.json` — recharge/filler/scaffold fixes
- `server/data/rules/5e2024/items/homebrew_items.json` — draft flags added
- `server/data/rules/5e2024/items/mounts_vehicles.json` — scaffold fixes
- `server/data/rules/5e2024/items/rare_magic_items.json` — recharge/filler/scaffold fixes
- `server/data/rules/5e2024/items/tools.json` — scaffold fixes
- `server/data/rules/5e2024/items/trade_goods_materials.json` — scaffold fixes
- `server/data/rules/5e2024/items/uncommon_magic_items.json` — recharge/filler/scaffold fixes
- `server/data/rules/5e2024/items/very_rare_magic_items.json` — recharge/filler/scaffold fixes
- `scripts/clean_item_metadata.py` — idempotent cleanup script

---

## Validation

```
python scripts/clean_item_metadata.py --check  # exits 0: all acceptance checks pass
python3 -m pytest tests/test_item_schema_normalization.py tests/test_item_compendium_catalog.py \
  tests/test_item_library_seed_expansion.py tests/test_encumbrance_capacity_formula.py \
  tests/test_encumbrance_weight_hints.py -q
# → 89 passed
```

4 pre-existing test failures in `test_refactor.py` (unrelated to items) are unchanged.
