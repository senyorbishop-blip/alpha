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
    }
    missing = sorted(expected - set(by_id))
    assert not missing, f"Missing expected expanded economy entries: {missing}"

    # Validate categories used for the new economy layer are represented.
    categories = {str(item.get("category") or "") for item in _SRD_MUNDANE}
    assert "Material" in categories
    assert "Recipe" in categories
    assert "Consumable" in categories


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
