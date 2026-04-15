from collections import Counter
import re


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(name or "").lower())).strip()


def test_srd_mundane_seed_has_no_duplicate_ids_or_names():
    from server.rules_db import _SRD_MUNDANE

    ids = [item.get("id") for item in _SRD_MUNDANE]
    names = [item.get("name") for item in _SRD_MUNDANE]
    assert not [k for k, v in Counter(ids).items() if v > 1], "Duplicate item ids found in _SRD_MUNDANE"
    assert not [k for k, v in Counter(names).items() if v > 1], "Duplicate item names found in _SRD_MUNDANE"


def test_srd_mundane_seed_expansion_contains_crafting_materials_and_recipes():
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}

    # Bat-themed cloak support
    assert "seq_batwing_travel_cloak" in by_id

    # Core material/crafting scaffolding entries
    expected = {
        "seq_cured_hide_bundle",
        "seq_bone_shards",
        "seq_venom_sac",
        "seq_bloomsteel_ingot",
        "seq_sunleaf_bunch",
        "seq_spider_silk_spool",
        "seq_recipe_stitchleaf_salve",
        "seq_recipe_minor_vigor_tonic",
        "seq_tinkers_multitool",
        "seq_grapnel_spool",
        "seq_signal_beetle",
        "seq_cutlass",
        "seq_boarding_axe",
        "seq_smugglers_satchel",
        "seq_arc_battery",
        "seq_precision_gear_pack",
        "seq_recipe_grapnel_spool_launcher",
        "seq_recipe_stormshore_cloak",
    }
    missing = sorted(expected - set(by_id))
    assert not missing, f"Missing expected expanded economy entries: {missing}"

    # Validate categories used for the new economy layer are represented.
    categories = {str(item.get("category") or "") for item in _SRD_MUNDANE}
    assert "Material" in categories
    assert "Recipe" in categories
    assert "Consumable" in categories
    assert "Trinket" in categories


def test_magic_seed_scroll_expansion_has_spell_tiers_and_named_scrolls():
    from server.rules_db import _SRD_MAGIC_ITEMS

    by_id = {item.get("id"): item for item in _SRD_MAGIC_ITEMS}
    for idx in range(1, 10):
        assert f"mi_spell_scroll_{idx}" in by_id, f"Missing spell scroll tier {idx}"

    named_scroll_ids = {
        "mi_scroll_warding_tides",
        "mi_scroll_safe_harbor",
        "mi_scroll_warding_circle",
        "mi_scroll_far_path",
        "mi_scroll_voltaic_malfunction",
        "mi_scroll_blackwake_last_order",
    }
    missing_named = sorted(named_scroll_ids - set(by_id.keys()))
    assert not missing_named, f"Missing named/utility scroll additions: {missing_named}"


def test_new_srd_seed_entries_do_not_collide_with_existing_magic_item_names():
    from server.rules_db import _SRD_MUNDANE, _SRD_MAGIC_ITEMS

    magic_names = {_norm_name(item.get("name")) for item in _SRD_MAGIC_ITEMS}
    collisions = []
    for item in _SRD_MUNDANE:
        item_id = str(item.get("id") or "")
        if not item_id.startswith("seq_"):
            continue
        if item_id in {
            "seq_batwing_travel_cloak",
            "seq_stormwax_cloak",
            "seq_watcher_signet",
            "seq_moonthread_amulet",
            "seq_wayfinder_talisman",
            "seq_glowmoss_lantern",
        }:
            if _norm_name(item.get("name")) in magic_names:
                collisions.append(item.get("name"))
    assert not collisions, f"New custom gear should not duplicate existing magic item names: {collisions}"


# ── EXPANSION TESTS ────────────────────────────────────────────────────────────


def test_srd_mundane_expansion_contains_new_material_ids():
    """New mat_ material IDs added in the expansion must be present."""
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}
    expected_materials = {
        "mat_silver_ingot",
        "mat_adamantine_shard",
        "mat_darkwood_plank",
        "mat_deepmoss_herb",
        "mat_brimstone_crystal",
        "mat_copper_wire_spool",
        "mat_sea_oak_plank",
        "mat_saltpetre_pouch",
        "mat_wyvern_scale",
        "mat_leyline_dust",
    }
    missing = sorted(expected_materials - set(by_id))
    assert not missing, f"Missing new expansion material IDs: {missing}"


def test_srd_mundane_expansion_contains_pirate_gear():
    """Pirate-flavored gear added in the expansion must be present."""
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}
    expected_pirate = {
        "seq_corsair_vest",
        "seq_nav_chart",
        "seq_anchor_spike",
        "seq_pirates_medallion",
        "seq_rum_flask",
        "seq_tide_lantern",
        "seq_boarding_shield",
        "seq_tidewatch_compass",
    }
    missing = sorted(expected_pirate - set(by_id))
    assert not missing, f"Missing pirate gear expansion IDs: {missing}"


def test_srd_mundane_expansion_contains_tinker_gear():
    """Tinker-flavored gear added in the expansion must be present."""
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}
    expected_tinker = {
        "seq_mechanical_notebook",
        "seq_lens_array",
        "seq_spark_coil",
        "seq_clockwork_key",
        "seq_field_forge_kit",
        "seq_tinker_goggles_basic",
        "seq_circuit_paste",
    }
    missing = sorted(expected_tinker - set(by_id))
    assert not missing, f"Missing tinker gear expansion IDs: {missing}"


def test_srd_mundane_expansion_contains_field_medicine_consumables():
    """Field-medicine consumables added in the expansion must be present."""
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}
    expected_medicine = {
        "seq_antitoxin_salve",
        "seq_fever_break_draught",
        "seq_numbing_poultice",
        "seq_healing_salve_minor",
        "seq_smelling_salts",
        "seq_cold_salt_pack",
    }
    missing = sorted(expected_medicine - set(by_id))
    assert not missing, f"Missing field-medicine consumable expansion IDs: {missing}"


def test_srd_mundane_expansion_contains_adventuring_gear():
    """General adventuring gear added in the expansion must be present."""
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}
    expected_gear = {
        "seq_everlit_torch",
        "seq_glowstone",
        "seq_camouflage_netting",
        "seq_tripwire_set",
        "seq_campfire_kit",
        "seq_navigation_journal",
        "seq_waterproof_satchel",
        "seq_medical_splint",
        "seq_grapple_line_kit",
    }
    missing = sorted(expected_gear - set(by_id))
    assert not missing, f"Missing adventuring gear expansion IDs: {missing}"


def test_srd_mundane_expansion_contains_new_recipe_scrolls():
    """Recipe scroll items for new craftables must be present."""
    from server.rules_db import _SRD_MUNDANE

    by_id = {item.get("id"): item for item in _SRD_MUNDANE}
    expected_recipes = {
        "seq_recipe_iron_buckler",
        "seq_recipe_scaled_vest",
        "seq_recipe_fever_break_draught",
        "seq_recipe_numbing_poultice",
        "seq_recipe_recurve_bow",
        "seq_recipe_arc_lantern",
        "seq_recipe_seafarers_amulet",
        "seq_recipe_corsair_vest",
        "seq_recipe_tar_caulk_kit",
        "seq_recipe_winter_wrap",
        "seq_recipe_clockwork_sentry",
        "seq_recipe_padded_surcoat",
    }
    missing = sorted(expected_recipes - set(by_id))
    assert not missing, f"Missing new recipe scroll IDs: {missing}"


def test_magic_item_expansion_contains_new_scrolls():
    """New utility, protection, and named scrolls must be present."""
    from server.rules_db import _SRD_MAGIC_ITEMS

    by_id = {item.get("id"): item for item in _SRD_MAGIC_ITEMS}
    expected_new_scrolls = {
        "mi_scroll_mending_field",
        "mi_scroll_farspeech",
        "mi_scroll_iron_ward",
        "mi_scroll_fog_bank",
        "mi_scroll_swift_step",
        "mi_scroll_stone_ward",
        "mi_scroll_shadow_step",
        "mi_scroll_tidal_force",
        "mi_scroll_circuit_interrupt",
        "mi_scroll_speak_with_dead",
        "mi_scroll_ritual_ward_fire",
        "mi_scroll_calm_waters",
        "mi_scroll_veil_of_storms",
        "mi_scroll_cursed_recall",
        "mi_scroll_unwritten_command",
    }
    missing = sorted(expected_new_scrolls - set(by_id))
    assert not missing, f"Missing new scroll expansion IDs: {missing}"


def test_magic_item_expansion_contains_chase_items():
    """Named chase items (pirate + tinker) must be present."""
    from server.rules_db import _SRD_MAGIC_ITEMS

    by_id = {item.get("id"): item for item in _SRD_MAGIC_ITEMS}
    expected_chase = {
        "mi_ring_trickster",
        "mi_voltaic_bracer",
        "mi_amulet_deep_sea",
        "mi_corsair_coat",
        "mi_artificers_monocle",
    }
    missing = sorted(expected_chase - set(by_id))
    assert not missing, f"Missing named chase item expansion IDs: {missing}"


def test_magic_item_expansion_contains_new_potions():
    """New resistance potions and special oils must be present."""
    from server.rules_db import _SRD_MAGIC_ITEMS

    by_id = {item.get("id"): item for item in _SRD_MAGIC_ITEMS}
    expected_potions = {
        "mi_potion_resist_thunder",
        "mi_potion_resist_psychic",
        "mi_oil_slipperiness",
        "mi_oil_sharpness",
        "mi_philter_love",
    }
    missing = sorted(expected_potions - set(by_id))
    assert not missing, f"Missing new potion/oil expansion IDs: {missing}"


def test_magic_items_no_duplicate_ids():
    """_SRD_MAGIC_ITEMS must have no duplicate IDs."""
    from server.rules_db import _SRD_MAGIC_ITEMS

    ids = [item.get("id") for item in _SRD_MAGIC_ITEMS]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    assert not dupes, f"Duplicate IDs in _SRD_MAGIC_ITEMS: {dupes}"


def test_crafting_recipe_expansion_has_new_professions():
    """New recipes cover blacksmithing, leatherworking, woodworking, tinkering, jeweling."""
    from server.db import _seed_crafting_recipes
    import json
    import sqlite3

    # Build an in-memory DB with the crafting_recipes table
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE crafting_recipes (
            id TEXT PRIMARY KEY, name TEXT, result_item_json TEXT,
            requires_professions_json TEXT, requires_materials_json TEXT,
            fee_units INTEGER, duration_seconds INTEGER,
            station_shop_types_json TEXT, tags_json TEXT, rarity TEXT,
            created_at REAL DEFAULT 0
        )"""
    )
    _seed_crafting_recipes(conn)
    rows = conn.execute("SELECT id, requires_professions_json FROM crafting_recipes").fetchall()
    conn.close()

    recipe_ids = {row["id"] for row in rows}
    expected_new = {
        "rec_iron_buckler",
        "rec_throwing_axe_bundle",
        "rec_boarding_shield",
        "rec_scaled_vest",
        "rec_corsair_vest",
        "rec_fever_break_draught",
        "rec_antitoxin_brew",
        "rec_numbing_poultice",
        "rec_travel_tonic",
        "rec_recurve_bow",
        "rec_iron_spike_bundle",
        "rec_padded_surcoat",
        "rec_winter_wrap",
        "rec_arc_lantern",
        "rec_clockwork_sentry",
        "rec_tar_caulk_kit",
        "rec_signal_beacon",
        "rec_seafarers_amulet",
        "rec_resonance_focus",
    }
    missing = sorted(expected_new - recipe_ids)
    assert not missing, f"Missing new expansion recipe IDs: {missing}"
