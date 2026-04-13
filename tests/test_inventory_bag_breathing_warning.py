from server.handlers import inventory as inventory_handlers


def test_looks_like_creature_inventory_entry_detects_creature_names():
    assert inventory_handlers._looks_like_creature_inventory_entry({"name": "Wolf Pup"}) is True
    assert inventory_handlers._looks_like_creature_inventory_entry({"notes": "Small familiar in a pouch"}) is True


def test_looks_like_creature_inventory_entry_ignores_regular_gear():
    assert inventory_handlers._looks_like_creature_inventory_entry({"name": "Rope (50 ft)"}) is False
    assert inventory_handlers._looks_like_creature_inventory_entry({"name": "Healing Potion"}) is False
