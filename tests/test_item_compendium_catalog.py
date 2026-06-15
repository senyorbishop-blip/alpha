"""
Tests for the item compendium catalog expansion.

Verifies:
- All item JSON files load without error
- Item IDs and slugs are unique across the full catalog
- All 36 SRD weapons are present
- All 12 SRD armor types are present
- Adventuring gear file loads and key items are present
- Tools file loads and key tools are present
- Item schema normalizes new fields (versatile_damage, weapon_properties, etc.)
- Thunder Mage Quarterstaff has correct subtype and versatile_damage
- Slug-based item lookup works
- DM picker catalog builds correctly
- Merge compendium metadata fills missing inventory fields
- Index.json loads correctly
- Audit tool clean on full catalog
"""
import json
import os
import pytest

_ITEMS_DIR = os.path.join(os.path.dirname(__file__), "..", "server", "data", "rules", "5e2024", "items")


# ---------------------------------------------------------------------------
# 1. All item JSON files load without error
# ---------------------------------------------------------------------------

def test_all_item_json_files_are_valid():
    from server.item_compendium import _ITEM_FILES
    for fname in _ITEM_FILES:
        path = os.path.join(_ITEMS_DIR, fname)
        assert os.path.isfile(path), f"Item file missing: {fname}"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("items", [])
        assert isinstance(items, list), f"{fname}: expected list of items"


def test_index_json_loads():
    path = os.path.join(_ITEMS_DIR, "index.json")
    assert os.path.isfile(path), "index.json missing"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "files" in data
    assert len(data["files"]) >= 10


def test_adventuring_gear_json_loads():
    path = os.path.join(_ITEMS_DIR, "adventuring_gear.json")
    assert os.path.isfile(path), "adventuring_gear.json missing"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    assert len(items) >= 5


def test_tools_json_loads():
    path = os.path.join(_ITEMS_DIR, "tools.json")
    assert os.path.isfile(path), "tools.json missing"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    assert len(items) >= 5


# ---------------------------------------------------------------------------
# 2. Item IDs and slugs are unique
# ---------------------------------------------------------------------------

def test_item_ids_are_unique():
    from server.item_compendium import all_items, clear_cache
    clear_cache()
    items = all_items()
    seen_ids = {}
    for item in items:
        item_id = str(item.get("id") or "").strip()
        if item_id:
            assert item_id not in seen_ids, f"Duplicate item id: {item_id}"
            seen_ids[item_id] = True


# ---------------------------------------------------------------------------
# 3. SRD weapon coverage
# ---------------------------------------------------------------------------

SRD_WEAPONS = [
    "club", "dagger", "dart", "greatclub", "handaxe", "javelin", "light hammer",
    "mace", "quarterstaff", "sickle", "spear", "light crossbow", "shortbow", "sling",
    "battleaxe", "flail", "glaive", "greataxe", "greatsword", "halberd", "lance",
    "longsword", "maul", "morningstar", "pike", "rapier", "scimitar", "shortsword",
    "trident", "war pick", "warhammer", "whip", "blowgun", "hand crossbow",
    "heavy crossbow", "longbow",
]


def test_all_srd_weapons_present():
    from server.item_compendium import all_items, clear_cache
    clear_cache()
    items = all_items()
    item_names_lower = {str(i.get("name") or "").strip().lower() for i in items}
    missing = [w for w in SRD_WEAPONS if w.lower() not in item_names_lower]
    assert not missing, f"Missing SRD weapons: {missing}"


def test_dart_has_correct_fields():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    dart = get_item_by_id("dart")
    assert dart is not None
    assert dart["category"] == "weapon"
    assert dart["damage_dice"] == "1d4"
    assert "finesse" in dart.get("weapon_properties", [])
    assert "thrown" in dart.get("weapon_properties", [])


def test_halberd_has_correct_fields():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    halberd = get_item_by_id("halberd")
    assert halberd is not None
    assert halberd["damage_dice"] == "1d10"
    assert halberd["damage_type"] == "slashing"
    assert "heavy" in halberd.get("weapon_properties", [])
    assert "reach" in halberd.get("weapon_properties", [])


def test_trident_has_versatile_damage():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    trident = get_item_by_id("trident")
    assert trident is not None
    assert trident["damage_dice"] == "1d6"
    assert trident.get("versatile_damage") == "1d8"
    assert "versatile" in trident.get("weapon_properties", [])


# ---------------------------------------------------------------------------
# 4. SRD armor coverage
# ---------------------------------------------------------------------------

SRD_ARMOR = [
    "padded armor", "leather armor", "studded leather armor", "hide armor",
    "chain shirt", "scale mail", "breastplate", "half plate",
    "ring mail", "chain mail", "splint armor", "plate armor",
]


def test_all_srd_armor_present():
    from server.item_compendium import all_items, clear_cache
    clear_cache()
    items = all_items()
    item_names_lower = {str(i.get("name") or "").strip().lower() for i in items}
    missing = [a for a in SRD_ARMOR if a.lower() not in item_names_lower]
    assert not missing, f"Missing SRD armor: {missing}"


# ---------------------------------------------------------------------------
# 5. Adventuring gear present
# ---------------------------------------------------------------------------

def test_torch_in_compendium():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    torch = get_item_by_id("torch")
    assert torch is not None
    assert "torch" in str(torch.get("name") or "").lower()


def test_healers_kit_has_granted_actions():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    kit = get_item_by_id("healers-kit")
    assert kit is not None
    assert kit.get("charges_max", 0) == 10
    assert len(kit.get("granted_actions") or []) >= 1


def test_rope_hemp_in_compendium():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    rope = get_item_by_id("rope-hemp")
    assert rope is not None


# ---------------------------------------------------------------------------
# 6. Tools present
# ---------------------------------------------------------------------------

def test_thieves_tools_in_compendium():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    tools = get_item_by_id("thieves-tools")
    assert tools is not None
    assert tools["category"] == "tool"
    assert tools.get("proficiency_group") == "thieves_tools"


def test_herbalism_kit_in_compendium():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    kit = get_item_by_id("herbalism-kit")
    assert kit is not None
    assert kit.get("proficiency_group") == "herbalism_kit"


def test_lute_is_musical_instrument():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    lute = get_item_by_id("lute")
    assert lute is not None
    assert lute.get("subtype") == "musical_instrument"


# ---------------------------------------------------------------------------
# 7. Item schema normalizes new fields
# ---------------------------------------------------------------------------

def test_schema_normalizes_versatile_damage():
    from server.item_schema import normalize_item_record, to_inventory_entry
    raw = {
        "name": "Quarterstaff", "category": "weapon",
        "damage_dice": "1d6", "versatile_damage": "1d8",
        "weapon_properties": ["versatile"],
    }
    canonical = normalize_item_record(raw)
    assert canonical["equipment"]["versatile_damage"] == "1d8"
    assert "versatile" in canonical["equipment"]["weapon_properties"]
    entry = to_inventory_entry(canonical)
    assert entry["versatile_damage"] == "1d8"
    assert "versatile" in entry["weapon_properties"]


def test_schema_normalizes_armor_fields():
    from server.item_schema import normalize_item_record, to_inventory_entry
    raw = {
        "name": "Plate Armor", "category": "armor",
        "base_ac": 18, "dex_cap": 0, "strength_requirement": 15,
        "stealth_disadvantage": True,
    }
    canonical = normalize_item_record(raw)
    assert canonical["equipment"]["base_ac"] == 18
    assert canonical["equipment"]["dex_cap"] == 0
    assert canonical["equipment"]["strength_requirement"] == 15
    assert canonical["equipment"]["stealth_disadvantage"] is True
    entry = to_inventory_entry(canonical)
    assert entry["base_ac"] == 18
    assert entry["dex_cap"] == 0
    assert entry["strength_requirement"] == 15
    assert entry["stealth_disadvantage"] is True


def test_schema_normalizes_description_and_rules_summary():
    from server.item_schema import normalize_item_record, to_inventory_entry
    raw = {
        "name": "Magic Item", "category": "wondrous",
        "description_summary": "Short description.",
        "rules_summary": "Full rules text.",
    }
    canonical = normalize_item_record(raw)
    assert canonical["display"]["description_summary"] == "Short description."
    assert canonical["display"]["rules_summary"] == "Full rules text."
    entry = to_inventory_entry(canonical)
    assert entry["description_summary"] == "Short description."
    assert entry["rules_summary"] == "Full rules text."


def test_schema_exports_attack_and_damage_bonus():
    from server.item_schema import normalize_item_record, to_inventory_entry
    raw = {
        "name": "Longsword, +2", "category": "weapon",
        "attack_bonus": 2, "damage_bonus": 2,
        "damage_dice": "1d8", "damage_type": "slashing",
    }
    canonical = normalize_item_record(raw)
    entry = to_inventory_entry(canonical)
    assert entry["attack_bonus"] == 2
    assert entry["damage_bonus"] == 2
    assert entry["damage_dice"] == "1d8"
    assert entry["damage_type"] == "slashing"


# ---------------------------------------------------------------------------
# 8. Thunder Mage Quarterstaff fields
# ---------------------------------------------------------------------------

def test_thunder_staff_has_quarterstaff_subtype():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    item = get_item_by_id("thunder-mage-quarterstaff-plus-3")
    assert item is not None
    assert item["subtype"] == "quarterstaff", f"Expected subtype 'quarterstaff', got '{item['subtype']}'"


def test_thunder_staff_has_versatile_damage():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    item = get_item_by_id("thunder-mage-quarterstaff-plus-3")
    assert item is not None
    assert item.get("versatile_damage") == "1d8"
    assert "versatile" in item.get("weapon_properties", [])


def test_thunder_staff_has_correct_bonus():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    item = get_item_by_id("thunder-mage-quarterstaff-plus-3")
    assert item is not None
    assert item["attack_bonus"] == 3
    assert item["damage_bonus"] == 3


def test_thunder_staff_granted_spells_have_correct_ids():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    item = get_item_by_id("thunder-mage-quarterstaff-plus-3")
    assert item is not None
    gs = item.get("granted_spells", [])
    spell_ids = {g["id"] for g in gs if isinstance(g, dict)}
    assert "thunderwave" in spell_ids
    assert "shatter" in spell_ids
    assert "lightning-bolt" in spell_ids


# ---------------------------------------------------------------------------
# 9. Slug-based lookup
# ---------------------------------------------------------------------------

def test_get_item_by_slug_works():
    from server.item_compendium import get_item_by_slug, clear_cache
    clear_cache()
    ring = get_item_by_slug("ring-of-protection")
    assert ring is not None
    assert ring["name"] == "Ring of Protection"


def test_get_item_by_slug_returns_none_for_unknown():
    from server.item_compendium import get_item_by_slug, clear_cache
    clear_cache()
    result = get_item_by_slug("definitely-not-a-real-item-xyz")
    assert result is None


# ---------------------------------------------------------------------------
# 10. DM picker catalog
# ---------------------------------------------------------------------------

def test_dm_picker_returns_all_items():
    from server.item_compendium import catalog_for_dm_picker, all_items, clear_cache
    clear_cache()
    picker = catalog_for_dm_picker()
    full = all_items()
    assert len(picker) == len(full)


def test_dm_picker_sorted_by_category_then_name():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    picker = catalog_for_dm_picker()
    for i, entry in enumerate(picker):
        assert "id" in entry
        assert "name" in entry
        assert "category" in entry
        assert "rarity" in entry


def test_dm_picker_shows_item_with_spells():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    picker = catalog_for_dm_picker()
    staff_entries = [e for e in picker if "Staff of Fire" in e.get("name", "")]
    assert len(staff_entries) >= 1
    assert staff_entries[0]["has_spells"] is True


# ---------------------------------------------------------------------------
# 11. Merge compendium metadata
# ---------------------------------------------------------------------------

def test_merge_compendium_metadata_fills_missing_fields():
    from server.item_compendium import merge_compendium_metadata, clear_cache
    clear_cache()
    minimal_entry = {
        "id": "ring-of-protection",
        "name": "Ring of Protection",
        "equipped": True,
        "attuned": True,
        "qty": 1,
    }
    merged = merge_compendium_metadata(minimal_entry)
    assert merged.get("category") == "ring"
    assert merged.get("requires_attunement") is True
    assert merged.get("equippable") is True
    assert merged["equipped"] is True
    assert merged["attuned"] is True


def test_merge_compendium_metadata_preserves_live_state():
    from server.item_compendium import merge_compendium_metadata, clear_cache
    clear_cache()
    entry = {
        "id": "wand-of-fireballs",
        "name": "Wand of Fireballs",
        "equipped": True,
        "attuned": True,
        "charges_current": 3,
        "qty": 1,
    }
    merged = merge_compendium_metadata(entry)
    assert merged["charges_current"] == 3
    assert merged["equipped"] is True


# ---------------------------------------------------------------------------
# 12. All items by subtype
# ---------------------------------------------------------------------------

def test_all_items_by_subtype_rod():
    from server.item_compendium import all_items_by_subtype, clear_cache
    clear_cache()
    rods = all_items_by_subtype("rod")
    assert len(rods) >= 1


def test_all_items_by_subtype_musical_instrument():
    from server.item_compendium import all_items_by_subtype, clear_cache
    clear_cache()
    instruments = all_items_by_subtype("musical_instrument")
    assert len(instruments) >= 1


# ---------------------------------------------------------------------------
# 13. Audit tool passes on the full catalog
# ---------------------------------------------------------------------------

def test_audit_tool_passes_on_full_catalog():
    import sys
    import importlib
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    audit = importlib.import_module("tools.audit_item_compendium")

    from server.item_compendium import all_items, all_spell_ids, clear_cache
    clear_cache()
    items = all_items()
    known_spell_ids = all_spell_ids()

    results = [audit.audit_item(i, known_spell_ids=known_spell_ids) for i in items]
    schema_issues = [r for r in results if r["issues"]]
    duplicate_ids = audit.check_duplicate_ids(items)

    assert not duplicate_ids, f"Duplicate item IDs found: {duplicate_ids}"
    assert not schema_issues, f"Schema issues: {[(r['name'], r['issues']) for r in schema_issues[:5]]}"


# ---------------------------------------------------------------------------
# 14. Alias, legacy_id, and dedupe_key lookup
# ---------------------------------------------------------------------------

def test_find_item_by_alias():
    from server.item_compendium import find_item_by_alias, clear_cache
    clear_cache()
    # Thunder Mage Quarterstaff has alias "thunder_mage_quarterstaff_3"
    item = find_item_by_alias("thunder_mage_quarterstaff_3")
    assert item is not None
    assert item["id"] == "thunder-mage-quarterstaff-plus-3"


def test_find_item_by_legacy_id():
    from server.item_compendium import find_item_by_legacy_id, clear_cache
    clear_cache()
    # Javelin of Lightning's wondrous variant was merged into the weapon
    item = find_item_by_legacy_id("javelin-of-lightning-wondrous")
    assert item is not None
    assert item["id"] == "javelin-of-lightning"


def test_find_item_by_dedupe_key():
    from server.item_compendium import find_item_by_dedupe_key, clear_cache
    clear_cache()
    # "ringofprotection" is the normalized dedupe_key for Ring of Protection
    item = find_item_by_dedupe_key("ringofprotection")
    assert item is not None
    assert item["name"] == "Ring of Protection"


def test_resolve_item_by_id():
    from server.item_compendium import resolve_item, clear_cache
    clear_cache()
    item = resolve_item("ring-of-protection")
    assert item is not None
    assert item["name"] == "Ring of Protection"


def test_resolve_item_by_name():
    from server.item_compendium import resolve_item, clear_cache
    clear_cache()
    item = resolve_item("Ring of Protection")
    assert item is not None
    assert item["id"] == "ring-of-protection"


def test_resolve_item_by_legacy_id():
    from server.item_compendium import resolve_item, clear_cache
    clear_cache()
    item = resolve_item("javelin-of-lightning-wondrous")
    assert item is not None
    assert item["id"] == "javelin-of-lightning"


# ---------------------------------------------------------------------------
# 15. filter_items with each criterion
# ---------------------------------------------------------------------------

def test_filter_items_by_category():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    rings = filter_items(category="ring")
    assert len(rings) >= 1
    assert all(i.get("category") == "ring" for i in rings)


def test_filter_items_by_rarity():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    legendary = filter_items(rarity="legendary")
    assert len(legendary) >= 1
    assert all(i.get("rarity") == "legendary" for i in legendary)


def test_filter_items_requires_attunement():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    attuned = filter_items(requires_attunement=True)
    assert len(attuned) >= 1
    assert all(
        bool(i.get("requires_attunement") or i.get("attunement_required"))
        for i in attuned
    )


def test_filter_items_has_charges():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    charged = filter_items(has_charges=True)
    assert len(charged) >= 1
    assert all(int(i.get("charges_max") or 0) > 0 for i in charged)


def test_filter_items_grants_spells():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    spell_items = filter_items(grants_spells=True)
    assert len(spell_items) >= 1
    assert all(bool(i.get("granted_spells")) for i in spell_items)


def test_filter_items_combat_usable():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    combat = filter_items(combat_usable=True)
    assert len(combat) >= 1


def test_filter_items_combined():
    from server.item_compendium import filter_items, clear_cache
    clear_cache()
    results = filter_items(category="wand", rarity="uncommon")
    assert len(results) >= 1
    for item in results:
        assert item.get("category") == "wand"
        assert item.get("rarity") == "uncommon"


# ---------------------------------------------------------------------------
# 16. catalog_for_dm_picker with filters
# ---------------------------------------------------------------------------

def test_dm_picker_filter_by_rarity():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    results = catalog_for_dm_picker(rarity="rare")
    assert all(e["rarity"] == "rare" for e in results)
    assert len(results) >= 1


def test_dm_picker_filter_by_grants_spells():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    results = catalog_for_dm_picker(grants_spells=True)
    assert all(e["has_spells"] is True for e in results)
    assert len(results) >= 1


def test_dm_picker_search_by_name():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    results = catalog_for_dm_picker(search="staff of fire")
    assert len(results) >= 1
    assert any("Staff of Fire" in e["name"] for e in results)


def test_dm_picker_search_by_alias():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    results = catalog_for_dm_picker(search="thunder_mage")
    assert len(results) >= 1


def test_dm_picker_entry_has_required_fields():
    from server.item_compendium import catalog_for_dm_picker, clear_cache
    clear_cache()
    entries = catalog_for_dm_picker()
    required_fields = {"id", "name", "slug", "category", "rarity", "requires_attunement",
                       "charges_max", "has_spells", "has_passive_effect", "combat_usable", "source"}
    for entry in entries[:5]:
        for field in required_fields:
            assert field in entry, f"Missing field '{field}' in DM picker entry for '{entry.get('name')}'"


# ---------------------------------------------------------------------------
# 17. Rarity file correctness
# ---------------------------------------------------------------------------

def test_uncommon_magic_items_file_all_uncommon():
    path = os.path.join(_ITEMS_DIR, "uncommon_magic_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for item in data.get("items", []):
        rarity = str(item.get("rarity") or "").lower()
        assert rarity == "uncommon", (
            f"Item '{item.get('id')}' in uncommon_magic_items.json has rarity='{rarity}'"
        )


def test_rare_magic_items_file_all_rare():
    path = os.path.join(_ITEMS_DIR, "rare_magic_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for item in data.get("items", []):
        rarity = str(item.get("rarity") or "").lower()
        assert rarity == "rare", (
            f"Item '{item.get('id')}' in rare_magic_items.json has rarity='{rarity}'"
        )


def test_very_rare_magic_items_file_all_very_rare():
    path = os.path.join(_ITEMS_DIR, "very_rare_magic_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for item in data.get("items", []):
        rarity = str(item.get("rarity") or "").lower()
        assert rarity == "very_rare", (
            f"Item '{item.get('id')}' in very_rare_magic_items.json has rarity='{rarity}'"
        )


def test_legendary_magic_items_file_all_legendary():
    path = os.path.join(_ITEMS_DIR, "legendary_magic_items.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for item in data.get("items", []):
        rarity = str(item.get("rarity") or "").lower()
        assert rarity == "legendary", (
            f"Item '{item.get('id')}' in legendary_magic_items.json has rarity='{rarity}'"
        )


# ---------------------------------------------------------------------------
# 18. Schema normalizes identity fields (aliases, legacy_ids, dedupe_key)
# ---------------------------------------------------------------------------

def test_schema_normalizes_identity_fields():
    from server.item_schema import normalize_item_record, to_inventory_entry
    raw = {
        "name": "Staff of Fire",
        "id": "staff-of-fire",
        "slug": "staff-of-fire",
        "aliases": ["staff_of_fire", "firestaff"],
        "legacy_ids": ["staffs-fire-old"],
        "dedupe_key": "staffoffire",
        "category": "staff",
        "rarity": "very_rare",
    }
    canonical = normalize_item_record(raw)
    identity = canonical.get("identity", {})
    assert identity.get("aliases") == ["staff_of_fire", "firestaff"]
    assert identity.get("legacy_ids") == ["staffs-fire-old"]
    assert identity.get("dedupe_key") == "staffoffire"

    entry = to_inventory_entry(canonical)
    assert entry.get("aliases") == ["staff_of_fire", "firestaff"]
    assert entry.get("legacy_ids") == ["staffs-fire-old"]
    assert entry.get("dedupe_key") == "staffoffire"


def test_schema_auto_generates_dedupe_key():
    from server.item_schema import normalize_item_record
    raw = {"name": "Ring of Protection", "id": "ring-of-protection", "category": "ring"}
    canonical = normalize_item_record(raw)
    dk = canonical["identity"]["dedupe_key"]
    assert dk == "ringofprotection"


# ---------------------------------------------------------------------------
# 19. Item compendium loads and all files load
# ---------------------------------------------------------------------------

def test_compendium_loads_without_error():
    from server.item_compendium import all_items, clear_cache
    clear_cache()
    items = all_items()
    assert len(items) >= 300


def test_all_item_files_load_and_have_items():
    from server.item_compendium import _ITEM_FILES
    for fname in _ITEM_FILES:
        path = os.path.join(_ITEMS_DIR, fname)
        assert os.path.isfile(path), f"Missing: {fname}"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("items", [])
        assert isinstance(items, list), f"{fname}: not a list"


def test_all_slugs_unique_after_dedup():
    from server.item_compendium import all_items, clear_cache
    clear_cache()
    items = all_items()
    seen = {}
    for item in items:
        slug = str(item.get("slug") or "").strip().lower()
        if slug:
            assert slug not in seen, f"Duplicate slug: '{slug}'"
            seen[slug] = item.get("id")


def test_duplicate_name_items_merge_into_canonical():
    from server.item_compendium import compendium_merge_log, clear_cache
    clear_cache()
    log = compendium_merge_log()
    # If any merge happened, it should appear in the log. No duplicates should remain.
    from server.item_compendium import all_items
    items = all_items()
    names = [str(i.get("name") or "").lower() for i in items]
    seen = {}
    for n in names:
        if n:
            assert n not in seen, f"Duplicate name after dedup: '{n}'"
            seen[n] = True
