#!/usr/bin/env python3
"""
Migration script: rebuilds the item compendium into the new rarity-split structure.

Reads all existing item files, applies:
  - Correct rarity values
  - slug, aliases, legacy_ids, dedupe_key identity fields
  - equip_slot corrections (rings: wondrous→ring, etc.)
  - Deduplication (thunder-mage-quarterstaff name collision)

Writes new files:
  mundane_weapons.json, mundane_armor_shields.json,
  adventuring_gear.json (updated), tools.json (updated),
  trade_goods_materials.json, mounts_vehicles.json,
  common_magic_items.json, uncommon_magic_items.json,
  rare_magic_items.json, very_rare_magic_items.json,
  legendary_magic_items.json, artifact_magic_items.json,
  homebrew_items.json

Usage: python tools/migrate_item_compendium.py [--dry-run]
"""
from __future__ import annotations
import json, os, re, sys, copy

ITEMS_DIR = os.path.join(os.path.dirname(__file__), "..", "server", "data", "rules", "5e2024", "items")
DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")[:120]

def dedupe_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.strip().lower())[:120]

def load_json(fname: str) -> list[dict]:
    path = os.path.join(ITEMS_DIR, fname)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("items", [])

def write_json(fname: str, category: str, items: list[dict]) -> None:
    path = os.path.join(ITEMS_DIR, fname)
    payload = {
        "item_schema_version": 2,
        "rules_version": "5e2024",
        "category": category,
        "description": f"Items from {category} bucket — open-compatible metadata and original summaries.",
        "items": items,
    }
    if DRY_RUN:
        print(f"  [dry-run] Would write {fname}: {len(items)} items")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {fname}: {len(items)} items")

def add_identity(item: dict, *, extra_aliases: list[str] | None = None, legacy: list[str] | None = None) -> dict:
    """Add slug, aliases, legacy_ids, dedupe_key to item in-place, return it."""
    item = copy.deepcopy(item)
    name = str(item.get("name") or "")
    item_id = str(item.get("id") or "")
    existing_aliases = list(item.get("aliases") or [])
    existing_legacy = list(item.get("legacy_ids") or [])

    slug = slugify(name)
    dk = dedupe_key(name)

    # Build aliases: include slug, underscore variant, Title Case variant
    alias_set = set(existing_aliases)
    alias_set.add(slug)
    alias_set.add(slugify(name).replace("-", "_"))
    if extra_aliases:
        alias_set.update(extra_aliases)
    alias_set.discard(item_id)
    alias_set.discard(name)

    legacy_set = set(existing_legacy)
    if legacy:
        legacy_set.update(legacy)
    legacy_set.discard(item_id)

    item["slug"] = item.get("slug") or slug
    item["aliases"] = sorted(alias_set)
    item["legacy_ids"] = sorted(legacy_set)
    item["dedupe_key"] = dk
    return item


# ---------------------------------------------------------------------------
# Rarity correction tables (SRD / open-compatible)
# ---------------------------------------------------------------------------

RARITY_OVERRIDES: dict[str, str] = {
    # Potions
    "potion-of-healing": "common",
    "potion-of-greater-healing": "uncommon",
    "potion-of-superior-healing": "rare",
    "potion-of-supreme-healing": "very_rare",
    "potion-of-climbing": "common",
    "potion-of-resistance": "uncommon",
    "potion-of-animal-friendship": "uncommon",
    "potion-of-growth": "uncommon",
    "potion-of-giant-strength": "uncommon",
    "potion-of-invisibility": "very_rare",
    "potion-of-speed": "very_rare",
    "potion-of-flying": "very_rare",
    "potion-of-water-breathing": "uncommon",
    "antitoxin": "common",
    "acid-vial": "common",
    "alchemist-s-fire": "common",
    "basic-poison": "common",

    # Scrolls
    "spell-scroll-cantrip": "common",
    "spell-scroll-1st-level": "common",
    "spell-scroll-2nd-level": "uncommon",
    "spell-scroll-3rd-level": "uncommon",
    "spell-scroll-4th-level": "rare",
    "spell-scroll-5th-level": "rare",
    "spell-scroll-6th-level": "very_rare",
    "spell-scroll-7th-level": "very_rare",
    "spell-scroll-8th-level": "very_rare",
    "spell-scroll-9th-level": "legendary",
    "scroll-of-protection": "uncommon",

    # Wands
    "wand-of-magic-missiles": "uncommon",
    "wand-of-web": "uncommon",
    "wand-of-fireballs": "rare",
    "wand-of-lightning-bolts": "rare",
    "wand-of-secrets": "uncommon",
    "wand-of-enemy-detection": "rare",
    "wand-of-fear": "rare",
    "wand-of-paralysis": "rare",
    "wand-of-polymorph": "very_rare",
    "wand-of-wonder": "rare",
    "wand-of-the-war-mage-plus1": "uncommon",
    "wand-of-the-war-mage-plus2": "rare",
    "wand-of-the-war-mage-plus3": "very_rare",

    # Staffs
    "staff": "common",
    "quarterstaff-plus1": "uncommon",
    "quarterstaff-plus2": "rare",
    "quarterstaff-plus3": "very_rare",
    "staff-of-healing": "rare",
    "staff-of-fire": "very_rare",
    "staff-of-frost": "very_rare",
    "staff-of-power": "very_rare",
    "staff-of-striking": "very_rare",
    "staff-of-thunder-and-lightning": "very_rare",
    "staff-of-the-woodlands": "rare",
    "staff-of-withering": "rare",
    "thunder-mage-quarterstaff-plus-3": "very_rare",

    # Rods
    "immovable-rod": "uncommon",
    "rod-of-absorption": "very_rare",
    "rod-of-alertness": "very_rare",
    "rod-of-lordly-might": "legendary",
    "rod-of-rulership": "rare",
    "rod-of-security": "very_rare",
    "rod-of-the-pact-keeper-plus1": "uncommon",
    "rod-of-the-pact-keeper-plus2": "rare",
    "rod-of-the-pact-keeper-plus3": "very_rare",

    # Rings
    "ring-of-protection": "rare",
    "ring-of-resistance": "rare",
    "ring-of-free-action": "rare",
    "ring-of-feather-falling": "rare",
    "ring-of-invisibility": "legendary",
    "ring-of-jumping": "uncommon",
    "ring-of-mind-shielding": "uncommon",
    "ring-of-regeneration": "very_rare",
    "ring-of-spell-storing": "rare",
    "ring-of-swimming": "uncommon",
    "ring-of-telekinesis": "very_rare",
    "ring-of-three-wishes": "legendary",
    "ring-of-warmth": "uncommon",
    "ring-of-water-walking": "uncommon",
    "ring-of-x-ray-vision": "rare",

    # Wondrous (SRD)
    "amulet-of-health": "rare",
    "bag-of-holding": "uncommon",
    "boots-of-elvenkind": "uncommon",
    "boots-of-levitation": "rare",
    "boots-of-speed": "rare",
    "boots-of-striding-and-springing": "uncommon",
    "boots-of-the-winterlands": "uncommon",
    "bracers-of-archery": "uncommon",
    "bracers-of-defense": "rare",
    "brooch-of-shielding": "uncommon",
    "broom-of-flying": "uncommon",
    "cloak-of-elvenkind": "uncommon",
    "cloak-of-protection": "uncommon",
    "cloak-of-the-bat": "rare",
    "cloak-of-the-manta-ray": "uncommon",
    "decanter-of-endless-water": "uncommon",
    "deck-of-illusions": "uncommon",
    "dust-of-disappearance": "uncommon",
    "dust-of-dryness": "uncommon",
    "dust-of-sneezing-and-choking": "uncommon",
    "eyes-of-charming": "uncommon",
    "eyes-of-minute-seeing": "uncommon",
    "eyes-of-the-eagle": "uncommon",
    "gauntlets-of-ogre-power": "uncommon",
    "gem-of-brightness": "uncommon",
    "gloves-of-missile-snaring": "uncommon",
    "gloves-of-swimming-and-climbing": "uncommon",
    "goggles-of-night": "uncommon",
    "handy-haversack": "rare",
    "hat-of-disguise": "uncommon",
    "headband-of-intellect": "uncommon",
    "helm-of-comprehending-languages": "uncommon",
    "helm-of-telepathy": "uncommon",
    "helm-of-teleportation": "rare",
    "horn-of-blasting": "rare",
    "horn-of-valhalla": "rare",
    "instrument-of-the-bards": "rare",
    "javelin-of-lightning-wondrous": "uncommon",
    "medallion-of-thoughts": "uncommon",
    "necklace-of-adaptation": "uncommon",
    "necklace-of-fireballs": "rare",
    "periapt-of-health": "uncommon",
    "periapt-of-proof-against-poison": "rare",
    "periapt-of-wound-closure": "uncommon",
    "portable-hole": "rare",
    "robe-of-useful-items": "uncommon",
    "robe-of-the-archmagi": "legendary",
    "slippers-of-spider-climbing": "uncommon",
    "stone-of-good-luck": "uncommon",
    "wings-of-flying": "rare",
}

# Fix equip_slot for rings (should be "ring" not "wondrous")
EQUIP_SLOT_OVERRIDES: dict[str, str] = {
    "ring-of-protection": "ring",
    "ring-of-resistance": "ring",
    "ring-of-free-action": "ring",
    "ring-of-feather-falling": "ring",
    "ring-of-invisibility": "ring",
    "ring-of-jumping": "ring",
    "ring-of-mind-shielding": "ring",
    "ring-of-regeneration": "ring",
    "ring-of-spell-storing": "ring",
    "ring-of-swimming": "ring",
    "ring-of-telekinesis": "ring",
    "ring-of-three-wishes": "ring",
    "ring-of-warmth": "ring",
    "ring-of-water-walking": "ring",
    "ring-of-x-ray-vision": "ring",
    # Wondrous specific slots
    "amulet-of-health": "neck",
    "bag-of-holding": "trinket",
    "boots-of-elvenkind": "feet",
    "boots-of-levitation": "feet",
    "boots-of-speed": "feet",
    "boots-of-striding-and-springing": "feet",
    "boots-of-the-winterlands": "feet",
    "bracers-of-archery": "hands",
    "bracers-of-defense": "hands",
    "brooch-of-shielding": "neck",
    "broom-of-flying": "trinket",
    "cloak-of-elvenkind": "cloak",
    "cloak-of-protection": "cloak",
    "cloak-of-the-bat": "cloak",
    "cloak-of-the-manta-ray": "cloak",
    "decanter-of-endless-water": "trinket",
    "deck-of-illusions": "trinket",
    "dust-of-disappearance": "trinket",
    "dust-of-dryness": "trinket",
    "dust-of-sneezing-and-choking": "trinket",
    "eyes-of-charming": "head",
    "eyes-of-minute-seeing": "head",
    "eyes-of-the-eagle": "head",
    "gauntlets-of-ogre-power": "hands",
    "gem-of-brightness": "trinket",
    "gloves-of-missile-snaring": "hands",
    "gloves-of-swimming-and-climbing": "hands",
    "goggles-of-night": "head",
    "handy-haversack": "trinket",
    "hat-of-disguise": "head",
    "headband-of-intellect": "head",
    "helm-of-comprehending-languages": "head",
    "helm-of-telepathy": "head",
    "helm-of-teleportation": "head",
    "horn-of-blasting": "trinket",
    "horn-of-valhalla": "trinket",
    "instrument-of-the-bards": "trinket",
    "javelin-of-lightning-wondrous": "trinket",
    "medallion-of-thoughts": "neck",
    "necklace-of-adaptation": "neck",
    "necklace-of-fireballs": "neck",
    "periapt-of-health": "neck",
    "periapt-of-proof-against-poison": "neck",
    "periapt-of-wound-closure": "neck",
    "portable-hole": "trinket",
    "robe-of-useful-items": "armor",
    "robe-of-the-archmagi": "armor",
    "slippers-of-spider-climbing": "feet",
    "stone-of-good-luck": "trinket",
    "wings-of-flying": "trinket",
}

def apply_corrections(item: dict) -> dict:
    item = copy.deepcopy(item)
    item_id = str(item.get("id") or "")
    if item_id in RARITY_OVERRIDES:
        item["rarity"] = RARITY_OVERRIDES[item_id]
    if item_id in EQUIP_SLOT_OVERRIDES:
        item["equip_slot"] = EQUIP_SLOT_OVERRIDES[item_id]
    return add_identity(item)


# ---------------------------------------------------------------------------
# Load all existing items
# ---------------------------------------------------------------------------

print("Loading existing item files...")
weapons_raw = load_json("weapons.json")
armor_raw = load_json("armor.json")
shields_raw = load_json("shields.json")
adv_gear_raw = load_json("adventuring_gear.json")
tools_raw = load_json("tools.json")
potions_raw = load_json("potions.json")
scrolls_raw = load_json("scrolls.json")
wands_raw = load_json("wands.json")
staffs_raw = load_json("staffs.json")
rods_raw = load_json("rods.json")
rings_raw = load_json("rings.json")
wondrous_raw = load_json("wondrous.json")
homebrew_raw = load_json("homebrew.json")

print(f"  weapons: {len(weapons_raw)}, armor: {len(armor_raw)}, shields: {len(shields_raw)}")
print(f"  gear: {len(adv_gear_raw)}, tools: {len(tools_raw)}")
print(f"  potions: {len(potions_raw)}, scrolls: {len(scrolls_raw)}, wands: {len(wands_raw)}")
print(f"  staffs: {len(staffs_raw)}, rods: {len(rods_raw)}, rings: {len(rings_raw)}")
print(f"  wondrous: {len(wondrous_raw)}, homebrew: {len(homebrew_raw)}")

# ---------------------------------------------------------------------------
# Dedup detection: thunder-mage-quarterstaff name collision
# ---------------------------------------------------------------------------
DUPLICATES_FOUND: list[dict] = []
DUPLICATES_MERGED: list[str] = []

# The homebrew "thunder-mage-quarterstaff-plus3-homebrew" has the same name as
# "thunder-mage-quarterstaff-plus-3" in staffs.  The canonical record is the
# staffs version (which has actual spells).  We record the homebrew one as a
# legacy_id so inventory entries still resolve.
THUNDER_HB_ID = "thunder-mage-quarterstaff-plus3-homebrew"
THUNDER_CANON_ID = "thunder-mage-quarterstaff-plus-3"

homebrew_filtered = []
for item in homebrew_raw:
    if item.get("id") == THUNDER_HB_ID:
        DUPLICATES_FOUND.append(item)
        print(f"  DUPLICATE: {THUNDER_HB_ID} (same name as {THUNDER_CANON_ID}) — merging into canonical")
    else:
        homebrew_filtered.append(item)

# Apply legacy_id to canonical thunder staff in staffs list
staffs_updated = []
for item in staffs_raw:
    if item.get("id") == THUNDER_CANON_ID:
        item = copy.deepcopy(item)
        existing_legacy = list(item.get("legacy_ids") or [])
        existing_legacy.append(THUNDER_HB_ID)
        item["legacy_ids"] = existing_legacy
        DUPLICATES_MERGED.append(THUNDER_CANON_ID)
        print(f"  MERGED: added legacy_id {THUNDER_HB_ID} to {THUNDER_CANON_ID}")
    staffs_updated.append(item)
staffs_raw = staffs_updated

# ---------------------------------------------------------------------------
# 1. mundane_weapons.json
# ---------------------------------------------------------------------------
print("\nBuilding mundane_weapons.json...")
mundane_weapons = [apply_corrections(i) for i in weapons_raw]
# The plain "staff" weapon from staffs is actually a mundane weapon too
# But it's in the staffs file. Leave it there - it has magic metadata anyway.
write_json("mundane_weapons.json", "mundane_weapons", mundane_weapons)

# ---------------------------------------------------------------------------
# 2. mundane_armor_shields.json
# ---------------------------------------------------------------------------
print("\nBuilding mundane_armor_shields.json...")
mundane_armor = [apply_corrections(i) for i in armor_raw + shields_raw]
write_json("mundane_armor_shields.json", "mundane_armor_shields", mundane_armor)

# ---------------------------------------------------------------------------
# 3. adventuring_gear.json — update existing items with identity fields
# ---------------------------------------------------------------------------
print("\nUpdating adventuring_gear.json...")
adv_gear_updated = [apply_corrections(i) for i in adv_gear_raw]
write_json("adventuring_gear.json", "adventuring_gear", adv_gear_updated)

# ---------------------------------------------------------------------------
# 4. tools.json — update existing items with identity fields
# ---------------------------------------------------------------------------
print("\nUpdating tools.json...")
tools_updated = [apply_corrections(i) for i in tools_raw]
write_json("tools.json", "tools", tools_updated)

# ---------------------------------------------------------------------------
# 5. trade_goods_materials.json — new file with basic trade goods
# ---------------------------------------------------------------------------
print("\nBuilding trade_goods_materials.json...")
trade_goods = [
    {
        "id": "gold-piece", "name": "Gold Piece", "item_schema_version": 2,
        "category": "material", "subtype": "currency", "rarity": "common",
        "slug": "gold-piece", "aliases": ["gp", "gold_piece", "gold"],
        "legacy_ids": [], "dedupe_key": "goldpiece",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0.02, "price_gp": 1, "source": "starter_compendium",
        "description_summary": "Standard gold currency (1 gp = 10 sp = 100 cp).",
        "stack_limit": 9999,
    },
    {
        "id": "silver-piece", "name": "Silver Piece", "item_schema_version": 2,
        "category": "material", "subtype": "currency", "rarity": "common",
        "slug": "silver-piece", "aliases": ["sp", "silver_piece", "silver"],
        "legacy_ids": [], "dedupe_key": "silverpiece",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0.02, "price_sp": 1, "source": "starter_compendium",
        "description_summary": "Standard silver currency (10 sp = 1 gp).",
        "stack_limit": 9999,
    },
    {
        "id": "copper-piece", "name": "Copper Piece", "item_schema_version": 2,
        "category": "material", "subtype": "currency", "rarity": "common",
        "slug": "copper-piece", "aliases": ["cp", "copper_piece", "copper"],
        "legacy_ids": [], "dedupe_key": "copperpiece",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0.02, "price_cp": 1, "source": "starter_compendium",
        "description_summary": "Standard copper currency (100 cp = 1 gp).",
        "stack_limit": 9999,
    },
    {
        "id": "iron-ingot", "name": "Iron Ingot", "item_schema_version": 2,
        "category": "material", "subtype": "metal", "rarity": "common",
        "slug": "iron-ingot", "aliases": ["iron_ingot", "iron-bar"],
        "legacy_ids": [], "dedupe_key": "ironingot",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 1.0, "price_gp": 1, "source": "starter_compendium",
        "description_summary": "A bar of refined iron, used in smithing.",
        "stack_limit": 99,
    },
    {
        "id": "steel-ingot", "name": "Steel Ingot", "item_schema_version": 2,
        "category": "material", "subtype": "metal", "rarity": "common",
        "slug": "steel-ingot", "aliases": ["steel_ingot", "steel-bar"],
        "legacy_ids": [], "dedupe_key": "steelingot",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 1.0, "price_gp": 2, "source": "starter_compendium",
        "description_summary": "A bar of refined steel, prized by weaponsmiths.",
        "stack_limit": 99,
    },
    {
        "id": "mithral-ingot", "name": "Mithral Ingot", "item_schema_version": 2,
        "category": "material", "subtype": "metal", "rarity": "uncommon",
        "slug": "mithral-ingot", "aliases": ["mithral_ingot", "mithral-bar"],
        "legacy_ids": [], "dedupe_key": "mithralingot",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0.5, "price_gp": 500, "source": "starter_compendium",
        "description_summary": "Rare, light metal used in mithral armor and weapons.",
        "stack_limit": 20,
    },
    {
        "id": "adamantine-ingot", "name": "Adamantine Ingot", "item_schema_version": 2,
        "category": "material", "subtype": "metal", "rarity": "rare",
        "slug": "adamantine-ingot", "aliases": ["adamantine_ingot", "adamantine-bar"],
        "legacy_ids": [], "dedupe_key": "adamantineingot",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 1.0, "price_gp": 5000, "source": "starter_compendium",
        "description_summary": "Incredibly hard black metal, used to craft adamantine gear.",
        "stack_limit": 10,
    },
    {
        "id": "cloth-bolt", "name": "Cloth Bolt", "item_schema_version": 2,
        "category": "material", "subtype": "textile", "rarity": "common",
        "slug": "cloth-bolt", "aliases": ["cloth_bolt", "fabric"],
        "legacy_ids": [], "dedupe_key": "clothbolt",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 5.0, "price_gp": 1, "source": "starter_compendium",
        "description_summary": "A bolt of cloth suitable for making clothes and light goods.",
        "stack_limit": 20,
    },
    {
        "id": "animal-hide", "name": "Animal Hide", "item_schema_version": 2,
        "category": "material", "subtype": "leather", "rarity": "common",
        "slug": "animal-hide", "aliases": ["animal_hide", "raw-hide", "raw_hide"],
        "legacy_ids": [], "dedupe_key": "animalhide",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 3.0, "price_gp": 1, "source": "starter_compendium",
        "description_summary": "Raw hide from a beast, used in leatherworking.",
        "stack_limit": 20,
    },
    {
        "id": "arcane-dust", "name": "Arcane Dust", "item_schema_version": 2,
        "category": "material", "subtype": "reagent", "rarity": "uncommon",
        "slug": "arcane-dust", "aliases": ["arcane_dust", "spell-dust"],
        "legacy_ids": [], "dedupe_key": "arcanedust",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": True, "consumed_on_use": False,
        "weight_lbs": 0.1, "price_gp": 25, "source": "starter_compendium",
        "description_summary": "Glittering dust of residual magic, used in enchanting and ritual crafting.",
        "stack_limit": 99,
    },
]
write_json("trade_goods_materials.json", "trade_goods_materials", trade_goods)

# ---------------------------------------------------------------------------
# 6. mounts_vehicles.json — new file with basic mounts
# ---------------------------------------------------------------------------
print("\nBuilding mounts_vehicles.json...")
mounts = [
    {
        "id": "riding-horse", "name": "Riding Horse", "item_schema_version": 2,
        "category": "misc", "subtype": "mount", "rarity": "common",
        "slug": "riding-horse", "aliases": ["riding_horse", "horse"],
        "legacy_ids": [], "dedupe_key": "ridinghorse",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0, "price_gp": 75, "source": "starter_compendium",
        "description_summary": "A well-trained riding horse; speed 60 ft. Carries up to 480 lb.",
    },
    {
        "id": "draft-horse", "name": "Draft Horse", "item_schema_version": 2,
        "category": "misc", "subtype": "mount", "rarity": "common",
        "slug": "draft-horse", "aliases": ["draft_horse", "workhorse"],
        "legacy_ids": [], "dedupe_key": "drafthorse",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0, "price_gp": 50, "source": "starter_compendium",
        "description_summary": "A heavy work horse; speed 40 ft. Carries up to 540 lb.",
    },
    {
        "id": "warhorse", "name": "Warhorse", "item_schema_version": 2,
        "category": "misc", "subtype": "mount", "rarity": "common",
        "slug": "warhorse", "aliases": ["war_horse", "destrier"],
        "legacy_ids": [], "dedupe_key": "warhorse",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0, "price_gp": 400, "source": "starter_compendium",
        "description_summary": "A combat-trained horse; speed 60 ft. Carries up to 540 lb.",
    },
    {
        "id": "mule", "name": "Mule", "item_schema_version": 2,
        "category": "misc", "subtype": "mount", "rarity": "common",
        "slug": "mule", "aliases": ["pack_mule"],
        "legacy_ids": [], "dedupe_key": "mule",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 0, "price_gp": 8, "source": "starter_compendium",
        "description_summary": "A sturdy pack animal; speed 40 ft. Carries up to 420 lb.",
    },
    {
        "id": "cart", "name": "Cart", "item_schema_version": 2,
        "category": "misc", "subtype": "vehicle", "rarity": "common",
        "slug": "cart", "aliases": ["wagon", "handcart"],
        "legacy_ids": [], "dedupe_key": "cart",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 200, "price_gp": 15, "source": "starter_compendium",
        "description_summary": "A two-wheeled cart for transporting goods. Requires a draft animal.",
    },
    {
        "id": "rowboat", "name": "Rowboat", "item_schema_version": 2,
        "category": "misc", "subtype": "vehicle", "rarity": "common",
        "slug": "rowboat", "aliases": ["row_boat", "dinghy"],
        "legacy_ids": [], "dedupe_key": "rowboat",
        "requires_attunement": False, "equippable": False, "equip_slot": "",
        "charges_max": 0, "recharge_type": "none",
        "passive_effects": [], "granted_spells": [], "granted_actions": [],
        "consumable": False, "consumed_on_use": False,
        "weight_lbs": 100, "price_gp": 50, "source": "starter_compendium",
        "description_summary": "A small wooden rowboat. Speed: 1½ mph (oars).",
    },
]
write_json("mounts_vehicles.json", "mounts_vehicles", mounts)

# ---------------------------------------------------------------------------
# Now distribute magic items into rarity buckets
# ---------------------------------------------------------------------------

def sort_into_rarity(items: list[dict], *, source: str = "") -> dict[str, list[dict]]:
    """Return {rarity_bucket: [items]}."""
    buckets: dict[str, list] = {
        "common": [], "uncommon": [], "rare": [],
        "very_rare": [], "legendary": [], "artifact": [],
    }
    for item in items:
        item = apply_corrections(item)
        if source:
            item["source"] = source
        rarity = item.get("rarity", "common")
        bucket = buckets.get(rarity, buckets["common"])
        bucket.append(item)
    return buckets

# Pool all magic item sources
# Note: the plain "staff" (id="staff") is common rarity and goes in common_magic
# The non-magic consumables from potions file go in common
# Keep them separate conceptually but lump common together
all_magic_sources = (
    potions_raw + scrolls_raw + wands_raw +
    staffs_raw + rods_raw + rings_raw + wondrous_raw
)

print("\nDistributing magic items into rarity buckets...")
buckets = sort_into_rarity(all_magic_sources, source="srd_compendium")

for rarity, items in buckets.items():
    print(f"  {rarity}: {len(items)} items")

# ---------------------------------------------------------------------------
# 7–12. Rarity-split magic item files
# ---------------------------------------------------------------------------
print("\nWriting rarity-split magic item files...")
write_json("common_magic_items.json", "common_magic_items", buckets["common"])
write_json("uncommon_magic_items.json", "uncommon_magic_items", buckets["uncommon"])
write_json("rare_magic_items.json", "rare_magic_items", buckets["rare"])
write_json("very_rare_magic_items.json", "very_rare_magic_items", buckets["very_rare"])
write_json("legendary_magic_items.json", "legendary_magic_items", buckets["legendary"])
write_json("artifact_magic_items.json", "artifact_magic_items", buckets["artifact"])

# ---------------------------------------------------------------------------
# 13. homebrew_items.json (without the duplicate Thunder Mage Quarterstaff)
# ---------------------------------------------------------------------------
print("\nBuilding homebrew_items.json...")
homebrew_final = [apply_corrections(i) for i in homebrew_filtered]
# Set source properly for homebrew
for item in homebrew_final:
    item["source"] = "homebrew"
write_json("homebrew_items.json", "homebrew", homebrew_final)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total_new = (
    len(mundane_weapons) + len(mundane_armor) +
    len(adv_gear_updated) + len(tools_updated) +
    len(trade_goods) + len(mounts) +
    sum(len(v) for v in buckets.values()) +
    len(homebrew_final)
)

print(f"\nMigration complete!")
print(f"  Duplicates found:  {len(DUPLICATES_FOUND)}")
print(f"  Duplicates merged: {len(DUPLICATES_MERGED)}")
print(f"  Total items in new structure: {total_new}")
print(f"  Files to DELETE (old): weapons.json, armor.json, shields.json, potions.json,")
print(f"                         scrolls.json, wands.json, staffs.json, rods.json,")
print(f"                         rings.json, wondrous.json, homebrew.json")
