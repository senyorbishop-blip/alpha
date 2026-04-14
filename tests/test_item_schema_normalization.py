from server.item_schema import (
    normalize_item_record,
    normalize_magic_item_row,
    normalize_srd_item_row,
    normalize_shop_item_row,
    normalize_crafted_result_row,
    to_inventory_entry,
)


def test_legacy_inventory_item_normalizes_with_defaults():
    canonical = normalize_item_record({"name": "Old Rope", "qty": 0, "rarity": "mystery"}, source_type="inventory")
    assert canonical["identity"]["name"] == "Old Rope"
    assert canonical["identity"]["rarity"] == "common"
    assert canonical["economy"]["quantity"] == 1


def test_magic_item_and_srd_rows_normalize_to_structured_shape():
    magic = normalize_magic_item_row({
        "id": "mi_scroll_1",
        "name": "Spell Scroll (1st Level)",
        "item_type": "scroll",
        "rarity": "common",
        "effect": "Cast the inscribed spell.",
    })
    srd = normalize_srd_item_row({
        "id": "seq_longsword",
        "name": "Longsword",
        "category": "Weapon",
        "rarity": "Common",
        "default_qty": 1,
    })
    assert magic["identity"]["source_type"] == "magic_item"
    assert magic["identity"]["category"] == "scroll"
    assert magic["scroll"]["spell_level"] == 1
    assert srd["identity"]["source_type"] == "srd_item"
    assert srd["identity"]["category"] == "weapon"


def test_shop_and_craft_payloads_normalize_and_keep_image_fields():
    shop = normalize_shop_item_row({
        "id": "shop-item-1",
        "item_name": "Pirate Compass",
        "item_type": "trinket",
        "description": "Keeps bearings in storms.",
        "price_gp": 12,
        "quantity": 2,
        "item_data": {"image_key": "pirate/compass", "tags": ["pirate_gear"]},
    })
    crafted = normalize_crafted_result_row({
        "id": "crafted_tinker",
        "name": "Tinker Spring Coil",
        "category": "Material",
        "item_type": "tinker_device",
        "profession_tags": ["tinker"],
        "recipe_tags": ["clockwork"],
    }, recipe_id="rec_tinker_01")

    assert shop["identity"]["source_type"] == "shop_item"
    assert shop["display"]["image_key"] == "pirate/compass"
    assert crafted["identity"]["source_type"] == "craft_result"
    assert crafted["crafting"]["profession_tags"] == ["tinker"]


def test_to_inventory_entry_keeps_scroll_first_class_fields():
    canonical = normalize_item_record({
        "id": "mi_spell_scroll_2",
        "name": "Spell Scroll (2nd Level)",
        "item_type": "scroll",
        "rarity": "uncommon",
    }, source_type="loot")
    entry = to_inventory_entry(canonical, notes="Unidentified", source_label="Loot")
    assert entry["item_type"] == "scroll"
    assert entry["consumable"] is True
    assert entry["scroll_data"]["spell_level"] == 2
    assert entry["item_schema"]["identity"]["source_type"] == "loot"
