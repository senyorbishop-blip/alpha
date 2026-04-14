from server.rules_db import _SRD_MUNDANE


def test_tinker_and_pirate_item_families_present_in_srd_seed():
    by_id = {row.get("id"): row for row in _SRD_MUNDANE}
    required_ids = {
        "seq_tinkers_multitool",
        "seq_grapnel_spool",
        "seq_signal_beetle",
        "seq_flash_device",
        "seq_cutlass",
        "seq_boarding_axe",
        "seq_captains_spyglass",
        "seq_smugglers_satchel",
        "seq_tidecharm",
    }
    missing = sorted(required_ids - set(by_id.keys()))
    assert not missing, f"Missing expected tinker/pirate seed entries: {missing}"


def test_new_family_materials_and_recipes_are_seeded():
    by_id = {row.get("id"): row for row in _SRD_MUNDANE}
    material_ids = {
        "seq_arc_battery",
        "seq_clockwork_spring_set",
        "seq_precision_gear_pack",
        "seq_coral_inlay",
        "seq_tarred_rope_bundle",
    }
    recipe_ids = {
        "seq_recipe_flash_prism_capsule",
        "seq_recipe_stormshore_cloak",
        "seq_recipe_grapnel_spool_launcher",
        "seq_recipe_smugglers_satchel",
    }
    assert not sorted(material_ids - set(by_id.keys()))
    assert not sorted(recipe_ids - set(by_id.keys()))
