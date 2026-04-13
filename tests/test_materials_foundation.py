"""Stage 2 – Materials Foundation tests.

Covers:
- Starter material definitions exist in _SRD_MUNDANE with correct fields
- Materials sync to client with intact weight and tags (get_all_srd_items round-trip)
- stack_limit is present on material rows
- Materials can be added to player inventory with weight preserved
- Encumbrance correctly accounts for material weight
- Encumbrance category fallback works for "Material" category
- Existing non-material items are unaffected by the changes
"""

import asyncio

import pytest

from server import encumbrance
from server.rules_db import _SRD_MUNDANE, get_all_srd_items, init_srd_items_table
from server.session import Session, User


# ── Starter material IDs required by spec ────────────────────────────────────

REQUIRED_MATERIAL_IDS = {
    "mat_iron_ingot",
    "mat_cured_hide",
    "mat_bat_wing_membrane",
    "mat_shadow_resin",
    "mat_glass_vial",
}


def test_starter_materials_in_srd_mundane():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    missing = REQUIRED_MATERIAL_IDS - set(by_id)
    assert not missing, f"Missing starter materials in _SRD_MUNDANE: {missing}"


def test_starter_materials_have_material_category():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        assert by_id[mid]["category"] == "Material", f"{mid} must have category='Material'"


def test_starter_materials_have_explicit_weight():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        weight = by_id[mid].get("weight")
        assert weight is not None, f"{mid} missing weight"
        assert float(weight) >= 0, f"{mid} weight must be non-negative"


def test_starter_materials_have_stack_limit():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        sl = by_id[mid].get("stack_limit")
        assert sl is not None, f"{mid} missing stack_limit"
        assert int(sl) >= 1, f"{mid} stack_limit must be >= 1"


def test_starter_materials_have_tags():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        tags = str(by_id[mid].get("tags") or "")
        assert "material" in tags, f"{mid} tags must include 'material'"


def test_mat_iron_ingot_is_metal():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    tags = by_id["mat_iron_ingot"]["tags"]
    assert "metal" in tags


def test_mat_cured_hide_is_leather():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    tags = by_id["mat_cured_hide"]["tags"]
    assert "leather" in tags


def test_mat_bat_wing_membrane_is_beast_and_occult():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    tags = by_id["mat_bat_wing_membrane"]["tags"]
    assert "beast" in tags
    assert "occult" in tags


def test_mat_shadow_resin_is_occult_and_alchemy():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    tags = by_id["mat_shadow_resin"]["tags"]
    assert "occult" in tags
    assert "alchemy" in tags


def test_mat_glass_vial_is_alchemy():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    tags = by_id["mat_glass_vial"]["tags"]
    assert "alchemy" in tags


# ── DB round-trip: weight and stack_limit survive INSERT / SELECT ─────────────

def test_srd_items_table_returns_materials_with_weight(tmp_path, monkeypatch):
    """init_srd_items_table + get_all_srd_items returns material rows with weight."""
    import server.db as _sdb
    import server.rules_db as rdb

    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(_sdb, "DB_PATH", db_file)
    # Stub out the magic_items seeder – that table only exists in production.
    monkeypatch.setattr(rdb, "_seed_srd_items_from_magic_items", lambda: None)

    init_srd_items_table()
    rows = get_all_srd_items()
    by_id = {r["id"]: r for r in rows}

    for mid in REQUIRED_MATERIAL_IDS:
        assert mid in by_id, f"Missing {mid} after DB seed"
        row = by_id[mid]
        assert row["category"] == "Material"
        assert isinstance(row["weight"], (int, float))
        assert row["weight"] >= 0
        assert row.get("stack_limit", 1) >= 1
        tags = str(row.get("tags") or "")
        assert "material" in tags


# ── Encumbrance: material weight flows through get_item_weight ────────────────

def test_encumbrance_uses_explicit_weight_lbs_for_material():
    item = {"name": "Iron Ingot", "category": "Material", "weight_lbs": 1.0}
    assert encumbrance.get_item_weight(item) == 1.0


def test_encumbrance_category_fallback_for_material():
    """Items with category='Material' but no explicit weight use the fallback."""
    item = {"name": "Unknown Stuff", "category": "Material"}
    weight = encumbrance.get_item_weight(item)
    assert weight == encumbrance.ITEM_WEIGHT_BY_CATEGORY["material"]
    assert weight > 0


def test_encumbrance_material_weight_adds_to_carried_total():
    inventory_items = [
        {"name": "Iron Ingot", "category": "Material", "weight_lbs": 1.0, "qty": 3},
        {"name": "Glass Vial", "category": "Material", "weight_lbs": 0.1, "qty": 10},
    ]
    total = encumbrance.get_total_carried_weight(inventory_items, gold_units=0)
    # 3 * 1.0 + 10 * 0.1 = 4.0
    assert abs(total - 4.0) < 0.01


def test_encumbrance_existing_gear_unaffected():
    """Non-material items continue to resolve weight as before."""
    sword = {"name": "Longsword", "category": "Weapon"}
    w = encumbrance.get_item_weight(sword)
    # Longsword is in ITEM_WEIGHT_BY_NAME (3 lbs) or keyword match
    assert w > 0


# ── Inventory normalization: weight_lbs is in _INVENTORY_META_KEYS ───────────

def test_inventory_meta_keys_includes_weight_lbs():
    """weight_lbs must be in _INVENTORY_META_KEYS so it survives normalization."""
    import re
    source_path = __import__("pathlib").Path(__file__).parent.parent / "server" / "handlers" / "inventory.py"
    source = source_path.read_text(encoding="utf-8")
    # Find the _INVENTORY_META_KEYS tuple definition and confirm weight_lbs is in it.
    match = re.search(r"_INVENTORY_META_KEYS\s*=\s*\(([^)]+)\)", source, re.DOTALL)
    assert match, "_INVENTORY_META_KEYS tuple not found in inventory.py"
    keys_text = match.group(1)
    assert '"weight_lbs"' in keys_text or "'weight_lbs'" in keys_text, \
        "weight_lbs must be in _INVENTORY_META_KEYS to survive inventory normalization"


def test_inventory_meta_keys_includes_category():
    """category must be in _INVENTORY_META_KEYS so Material label is preserved."""
    import re
    source_path = __import__("pathlib").Path(__file__).parent.parent / "server" / "handlers" / "inventory.py"
    source = source_path.read_text(encoding="utf-8")
    match = re.search(r"_INVENTORY_META_KEYS\s*=\s*\(([^)]+)\)", source, re.DOTALL)
    assert match, "_INVENTORY_META_KEYS tuple not found"
    keys_text = match.group(1)
    assert '"category"' in keys_text or "'category'" in keys_text, \
        "category must be in _INVENTORY_META_KEYS"


# ── Chest storage: material in chest prop has intact weight via encumbrance ───

def test_chest_material_item_weight_via_encumbrance():
    """When a material is taken from a chest and added to inventory its
    weight_lbs flows into the encumbrance calculation."""
    # Simulate the item dict that would exist in inventory after taking from chest
    taken_item = {
        "name": "Shadow Resin",
        "qty": 2,
        "category": "Material",
        "rarity": "Rare",
        "weight_lbs": 0.5,
    }
    # get_item_weight uses explicit weight_lbs first
    assert encumbrance.get_item_weight(taken_item) == 0.5
    # Total carried = 2 * 0.5 = 1.0
    total = encumbrance.get_total_carried_weight([taken_item], gold_units=0)
    assert abs(total - 1.0) < 0.01


# ── Shop stock: material weight preserved when item_data is decoded ───────────

def test_shop_item_data_can_carry_material_weight():
    """Shop items store extra metadata in item_data JSON.
    Verify that material weight round-trips through JSON."""
    import json

    item_data = {"weight_lbs": 0.1, "category": "Material", "tags": "material,alchemy"}
    encoded = json.dumps(item_data)
    decoded = json.loads(encoded)
    assert decoded["weight_lbs"] == 0.1
    assert decoded["category"] == "Material"


# ── Existing items: non-material SRD items unaffected ────────────────────────

def test_existing_weapon_items_in_srd_mundane_unaffected():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    longsword = by_id.get("seq_longsword")
    assert longsword is not None
    assert longsword["category"] == "Weapon"
    assert longsword["weight"] == 3


def test_existing_armor_items_in_srd_mundane_unaffected():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    plate = by_id.get("seq_plate")
    assert plate is not None
    assert plate["category"] == "Armor"
    assert plate["weight"] == 65


def test_encumbrance_material_category_does_not_break_other_categories():
    assert "material" in encumbrance.ITEM_WEIGHT_BY_CATEGORY
    assert "gear" in encumbrance.ITEM_WEIGHT_BY_CATEGORY
    assert "weapon" in encumbrance.ITEM_WEIGHT_BY_CATEGORY
    assert "potion" in encumbrance.ITEM_WEIGHT_BY_CATEGORY
