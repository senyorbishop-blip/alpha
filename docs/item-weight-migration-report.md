# Item Weight Migration Report — PR 2

**Branch:** `claude/new-session-ras567`
**Scope:** 5e2024 item library (`server/data/rules/5e2024/items/*.json`, 478 items)

---

## Before / After Counts

| Metric | Before | After |
|---|---|---|
| Items with authored `weight_lbs` | 246 | 478 |
| Items without `weight_lbs` | 232 | 0 |

---

## Weight Assignment Sources

| Source | Items assigned |
|---|---|
| Exact name match (`ITEM_WEIGHT_BY_NAME`) | 1 |
| Keyword substring match (`_KEYWORD_WEIGHTS`) | 53 |
| Category lookup (`ITEM_WEIGHT_BY_CATEGORY`) | 61 |
| Item-type lookup (`ITEM_WEIGHT_BY_TYPE`) | 5 |
| **Default fallback** (`DEFAULT_ITEM_WEIGHT = 0.5`) | **112** |

---

## Items Assigned Default Weight — Need Human Review

112 items could not be assigned a meaningful weight from the curated tables.
They received `weight_lbs: 0.5` (the `DEFAULT_ITEM_WEIGHT`). A human should
review each and supply an accurate weight directly in the item JSON.

These are mostly "wondrous" magic items (Ioun Stones, Tomes, Belts, Cloaks,
etc.) and homebrew items without a category in the weight tables.

| File | ID | Name | Category |
|---|---|---|---|
| artifact_magic_items.json | eye-of-vecna | Eye of Vecna | wondrous |
| artifact_magic_items.json | hand-of-vecna | Hand of Vecna | wondrous |
| artifact_magic_items.json | orb-of-dragonkind | Orb of Dragonkind | wondrous |
| homebrew_items.json | athkatla-smuggler-s-coin | Athkatla Smuggler's Coin | wondrous |
| homebrew_items.json | baron-s-ledger-key | Baron's Ledger Key | wondrous |
| homebrew_items.json | candle-of-shar-s-whisper | Candle of Shar's Whisper | wondrous |
| homebrew_items.json | map-fragment-of-brosst | Map Fragment of Brosst | wondrous |
| homebrew_items.json | prison-warden-s-manacles | Prison Warden's Manacles | wondrous |
| homebrew_items.json | seagull-guild-banner | Seagull Guild Banner | wondrous |
| legendary_magic_items.json | apparatus-of-kwalish | Apparatus of Kwalish | wondrous |
| legendary_magic_items.json | belt-of-cloud-giant-strength | Belt of Cloud Giant Strength | wondrous |
| legendary_magic_items.json | belt-of-storm-giant-strength | Belt of Storm Giant Strength | wondrous |
| legendary_magic_items.json | cloak-of-invisibility | Cloak of Invisibility | wondrous |
| legendary_magic_items.json | crystal-ball-of-mind-reading | Crystal Ball of Mind Reading | wondrous |
| legendary_magic_items.json | crystal-ball-of-telepathy | Crystal Ball of Telepathy | wondrous |
| legendary_magic_items.json | cubic-gate | Cubic Gate | wondrous |
| legendary_magic_items.json | deck-of-many-things | Deck of Many Things | wondrous |
| legendary_magic_items.json | efreeti-chain | Efreeti Chain | armor |
| legendary_magic_items.json | ioun-stone-greater-absorption | Ioun Stone Greater Absorption | wondrous |
| legendary_magic_items.json | ioun-stone-mastery | Ioun Stone Mastery | wondrous |
| legendary_magic_items.json | iron-flask | Iron Flask | wondrous |
| legendary_magic_items.json | robe-of-the-archmagi | Robe of the Archmagi | wondrous |
| legendary_magic_items.json | sovereign-glue | Sovereign Glue | wondrous |
| legendary_magic_items.json | sphere-of-annihilation | Sphere of Annihilation | wondrous |
| legendary_magic_items.json | talisman-of-pure-good | Talisman of Pure Good | wondrous |
| legendary_magic_items.json | talisman-of-the-sphere | Talisman of the Sphere | wondrous |
| legendary_magic_items.json | talisman-of-ultimate-evil | Talisman of Ultimate Evil | wondrous |
| legendary_magic_items.json | universal-solvent | Universal Solvent | wondrous |
| legendary_magic_items.json | well-of-many-worlds | Well of Many Worlds | wondrous |
| rare_magic_items.json | belt-of-dwarvenkind | Belt of Dwarvenkind | wondrous |
| rare_magic_items.json | boots-of-levitation | Boots of Levitation | wondrous |
| rare_magic_items.json | boots-of-speed | Boots of Speed | wondrous |
| rare_magic_items.json | bracers-of-defense | Bracers of Defense | wondrous |
| rare_magic_items.json | brazier-of-commanding-fire-elementals | Brazier of Commanding Fire Elementals | wondrous |
| rare_magic_items.json | cape-of-the-mountebank | Cape of the Mountebank | wondrous |
| rare_magic_items.json | censer-of-controlling-air-elementals | Censer of Controlling Air Elementals | wondrous |
| rare_magic_items.json | chime-of-opening | Chime of Opening | wondrous |
| rare_magic_items.json | cloak-of-displacement | Cloak of Displacement | wondrous |
| rare_magic_items.json | cloak-of-the-bat | Cloak of the Bat | wondrous |
| rare_magic_items.json | dimensional-shackles | Dimensional Shackles | wondrous |
| rare_magic_items.json | folding-boat | Folding Boat | wondrous |
| rare_magic_items.json | gem-of-seeing | Gem of Seeing | wondrous |
| rare_magic_items.json | handy-haversack | Handy Haversack | wondrous |
| rare_magic_items.json | helm-of-teleportation | Helm of Teleportation | wondrous |
| rare_magic_items.json | horn-of-blasting | Horn of Blasting | wondrous |
| rare_magic_items.json | horn-of-valhalla | Horn of Valhalla | wondrous |
| rare_magic_items.json | instant-fortress | Instant Fortress | wondrous |
| rare_magic_items.json | instrument-of-the-bards | Instrument of the Bards | wondrous |
| rare_magic_items.json | ioun-stone-protection | Ioun Stone Protection | wondrous |
| rare_magic_items.json | necklace-of-fireballs | Necklace of Fireballs | wondrous |
| rare_magic_items.json | periapt-of-proof-against-poison | Periapt of Proof against Poison | wondrous |
| rare_magic_items.json | portable-hole | Portable Hole | wondrous |
| rare_magic_items.json | robe-of-eyes | Robe of Eyes | wondrous |
| rare_magic_items.json | stone-of-controlling-earth-elementals | Stone of Controlling Earth Elementals | wondrous |
| rare_magic_items.json | wings-of-flying | Wings of Flying | wondrous |
| uncommon_magic_items.json | boots-of-elvenkind | Boots of Elvenkind | wondrous |
| uncommon_magic_items.json | boots-of-striding-and-springing | Boots of Striding and Springing | wondrous |
| uncommon_magic_items.json | boots-of-the-winterlands | Boots of the Winterlands | wondrous |
| uncommon_magic_items.json | bracers-of-archery | Bracers of Archery | wondrous |
| uncommon_magic_items.json | broom-of-flying | Broom of Flying | wondrous |
| uncommon_magic_items.json | cloak-of-elvenkind | Cloak of Elvenkind | wondrous |
| uncommon_magic_items.json | cloak-of-protection | Cloak of Protection | wondrous |
| uncommon_magic_items.json | cloak-of-the-manta-ray | Cloak of the Manta Ray | wondrous |
| uncommon_magic_items.json | decanter-of-endless-water | Decanter of Endless Water | wondrous |
| uncommon_magic_items.json | deck-of-illusions | Deck of Illusions | wondrous |
| uncommon_magic_items.json | dust-of-disappearance | Dust of Disappearance | wondrous |
| uncommon_magic_items.json | dust-of-dryness | Dust of Dryness | wondrous |
| uncommon_magic_items.json | dust-of-sneezing-and-choking | Dust of Sneezing and Choking | wondrous |
| uncommon_magic_items.json | eyes-of-charming | Eyes of Charming | wondrous |
| uncommon_magic_items.json | eyes-of-minute-seeing | Eyes of Minute Seeing | wondrous |
| uncommon_magic_items.json | eyes-of-the-eagle | Eyes of the Eagle | wondrous |
| uncommon_magic_items.json | gauntlets-of-ogre-power | Gauntlets of Ogre Power | wondrous |
| uncommon_magic_items.json | gem-of-brightness | Gem of Brightness | wondrous |
| uncommon_magic_items.json | gloves-of-missile-snaring | Gloves of Missile Snaring | wondrous |
| uncommon_magic_items.json | gloves-of-swimming-and-climbing | Gloves of Swimming and Climbing | wondrous |
| uncommon_magic_items.json | goggles-of-night | Goggles of Night | wondrous |
| uncommon_magic_items.json | hat-of-disguise | Hat of Disguise | wondrous |
| uncommon_magic_items.json | headband-of-intellect | Headband of Intellect | wondrous |
| uncommon_magic_items.json | helm-of-comprehending-languages | Helm of Comprehending Languages | wondrous |
| uncommon_magic_items.json | helm-of-telepathy | Helm of Telepathy | wondrous |
| uncommon_magic_items.json | medallion-of-thoughts | Medallion of Thoughts | wondrous |
| uncommon_magic_items.json | necklace-of-adaptation | Necklace of Adaptation | wondrous |
| uncommon_magic_items.json | periapt-of-health | Periapt of Health | wondrous |
| uncommon_magic_items.json | periapt-of-wound-closure | Periapt of Wound Closure | wondrous |
| uncommon_magic_items.json | robe-of-useful-items | Robe of Useful Items | wondrous |
| uncommon_magic_items.json | slippers-of-spider-climbing | Slippers of Spider Climbing | wondrous |
| uncommon_magic_items.json | stone-of-good-luck | Stone of Good Luck | wondrous |
| very_rare_magic_items.json | belt-of-fire-giant-strength | Belt of Fire Giant Strength | wondrous |
| very_rare_magic_items.json | belt-of-frost-giant-strength | Belt of Frost Giant Strength | wondrous |
| very_rare_magic_items.json | candle-of-invocation | Candle of Invocation | wondrous |
| very_rare_magic_items.json | carpet-of-flying | Carpet of Flying | wondrous |
| very_rare_magic_items.json | cloak-of-arachnida | Cloak of Arachnida | wondrous |
| very_rare_magic_items.json | crystal-ball | Crystal Ball | wondrous |
| very_rare_magic_items.json | efreeti-bottle | Efreeti Bottle | wondrous |
| very_rare_magic_items.json | figurine-of-wondrous-power | Figurine of Wondrous Power | wondrous |
| very_rare_magic_items.json | helm-of-brilliance | Helm of Brilliance | wondrous |
| very_rare_magic_items.json | horseshoes-of-a-zephyr | Horseshoes of a Zephyr | wondrous |
| very_rare_magic_items.json | ioun-stone-absorption | Ioun Stone Absorption | wondrous |
| very_rare_magic_items.json | ioun-stone-agility | Ioun Stone Agility | wondrous |
| very_rare_magic_items.json | ioun-stone-fortitude | Ioun Stone Fortitude | wondrous |
| very_rare_magic_items.json | ioun-stone-insight | Ioun Stone Insight | wondrous |
| very_rare_magic_items.json | ioun-stone-intellect | Ioun Stone Intellect | wondrous |
| very_rare_magic_items.json | ioun-stone-leadership | Ioun Stone Leadership | wondrous |
| very_rare_magic_items.json | ioun-stone-strength | Ioun Stone Strength | wondrous |
| very_rare_magic_items.json | manual-of-bodily-health | Manual of Bodily Health | wondrous |
| very_rare_magic_items.json | manual-of-gainful-exercise | Manual of Gainful Exercise | wondrous |
| very_rare_magic_items.json | manual-of-golems | Manual of Golems | wondrous |
| very_rare_magic_items.json | manual-of-quickness-of-action | Manual of Quickness of Action | wondrous |
| very_rare_magic_items.json | mirror-of-life-trapping | Mirror of Life Trapping | wondrous |
| very_rare_magic_items.json | tome-of-clear-thought | Tome of Clear Thought | wondrous |
| very_rare_magic_items.json | tome-of-leadership-and-influence | Tome of Leadership and Influence | wondrous |
| very_rare_magic_items.json | tome-of-understanding | Tome of Understanding | wondrous |

---

## Files Changed

- `server/encumbrance.py` — `get_item_weight` docstring updated: authored `weight_lbs` marked as primary source; in-code lookup tables labeled as legacy fallbacks for unmigrated/user-imported items
- `server/data/rules/5e2024/items/artifact_magic_items.json` — weights migrated
- `server/data/rules/5e2024/items/common_magic_items.json` — weights migrated
- `server/data/rules/5e2024/items/homebrew_items.json` — weights migrated
- `server/data/rules/5e2024/items/legendary_magic_items.json` — weights migrated
- `server/data/rules/5e2024/items/rare_magic_items.json` — weights migrated
- `server/data/rules/5e2024/items/uncommon_magic_items.json` — weights migrated
- `server/data/rules/5e2024/items/very_rare_magic_items.json` — weights migrated
- `scripts/migrate_item_weights.py` — idempotent migration script

---

## Validation

```
python scripts/migrate_item_weights.py --check  # exits 0: 478/478 items have weight_lbs
python3 -m pytest tests/test_encumbrance_capacity_formula.py \
  tests/test_encumbrance_weight_hints.py tests/test_encumbrance_combat_disadvantage.py \
  tests/test_encumbrance_ws_bridge.py -q
# → 9 passed
```

29 pre-existing test failures (all unrelated to encumbrance/weight) are unchanged.
