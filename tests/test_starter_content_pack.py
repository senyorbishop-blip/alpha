"""Stage 8 – Starter Content Pack tests.

Covers:
- All 5 canonical materials present in _SRD_MUNDANE with correct fields
- All 5 professions seeded and accessible via DB helpers
- All 3 starter recipes seeded with canonical mat_ material names
- Seed runs idempotently (no duplicate rows on repeated calls)
- Recipes reference mat_ item display names (not legacy seq_ names)
- Batwing Cloak is bat-themed and uses Bat Wing Membrane
- Recipe rarities and durations are balanced for starter play
- Profession → shop-type compatibility is correct
- Entries appear correctly when listed (UI representation)
"""

import json

import pytest

from server.rules_db import _SRD_MUNDANE, get_all_srd_items, init_srd_items_table

# ── Constants ─────────────────────────────────────────────────────────────────

REQUIRED_MATERIAL_IDS = {
    "mat_iron_ingot",
    "mat_cured_hide",
    "mat_bat_wing_membrane",
    "mat_shadow_resin",
    "mat_glass_vial",
}

REQUIRED_PROFESSION_IDS = {
    "blacksmithing",
    "leatherworking",
    "alchemy",
    "woodworking",
    "tailoring",
}

REQUIRED_RECIPE_IDS = {
    "rec_minor_healing_draught",
    "rec_leather_patch_kit",
    "rec_batwing_cloak",
}

# Canonical display names of the mat_ items (used by recipe material-matching)
MAT_DISPLAY_NAMES = {
    "mat_iron_ingot": "Iron Ingot",
    "mat_cured_hide": "Cured Hide",
    "mat_bat_wing_membrane": "Bat Wing Membrane",
    "mat_shadow_resin": "Shadow Resin",
    "mat_glass_vial": "Glass Vial",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_tmp_db(tmp_path, monkeypatch):
    """Point DB at a temp file and return the path."""
    import server.db as _sdb
    import server.rules_db as rdb

    db_file = str(tmp_path / "stage8_test.db")
    monkeypatch.setattr(_sdb, "DB_PATH", db_file)
    monkeypatch.setattr(rdb, "_seed_srd_items_from_magic_items", lambda: None)
    return db_file


def _seed_all(tmp_path, monkeypatch):
    """Init full DB (professions + recipes + srd_items) and return helpers."""
    import server.db as _sdb
    import server.rules_db as rdb

    _setup_tmp_db(tmp_path, monkeypatch)
    _sdb.init_db()
    init_srd_items_table()
    return _sdb


# ── Material definitions ───────────────────────────────────────────────────────

def test_all_five_canonical_materials_in_srd_mundane():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    missing = REQUIRED_MATERIAL_IDS - set(by_id)
    assert not missing, f"Missing canonical materials: {missing}"


def test_materials_have_material_category():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        assert by_id[mid]["category"] == "Material", f"{mid} must have category='Material'"


def test_materials_have_sensible_weights():
    """All starter materials must have explicit, non-negative weight."""
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    expected_max = {
        "mat_iron_ingot": 5.0,
        "mat_cured_hide": 5.0,
        "mat_bat_wing_membrane": 1.0,
        "mat_shadow_resin": 2.0,
        "mat_glass_vial": 0.5,
    }
    for mid in REQUIRED_MATERIAL_IDS:
        w = float(by_id[mid].get("weight", -1))
        assert w >= 0, f"{mid} must have non-negative weight"
        assert w <= expected_max[mid], f"{mid} weight {w} exceeds expected max {expected_max[mid]}"


def test_materials_have_stack_limit():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        sl = by_id[mid].get("stack_limit")
        assert sl is not None, f"{mid} missing stack_limit"
        assert int(sl) >= 1, f"{mid} stack_limit must be >= 1"


def test_materials_have_player_facing_descriptions():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        desc = str(by_id[mid].get("description") or "")
        assert len(desc) >= 20, f"{mid} description too short for player-facing display"


def test_material_tags_are_correct():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    tag_requirements = {
        "mat_iron_ingot": ["material", "metal"],
        "mat_cured_hide": ["material", "leather"],
        "mat_bat_wing_membrane": ["material", "beast", "occult"],
        "mat_shadow_resin": ["material", "occult", "alchemy"],
        "mat_glass_vial": ["material", "alchemy"],
    }
    for mid, required_tags in tag_requirements.items():
        tags = str(by_id[mid].get("tags") or "")
        for tag in required_tags:
            assert tag in tags, f"{mid} must include tag '{tag}' (got: {tags!r})"


def test_material_rarities_are_sensible():
    """Rare or higher materials are used for the premium recipe; common/uncommon for basics."""
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    # mat_shadow_resin is explicitly Rare (used in uncommon Batwing Cloak)
    assert by_id["mat_shadow_resin"]["rarity"] in ("Rare", "Very Rare", "Legendary"), \
        "Shadow Resin must be Rare or higher"
    # mat_bat_wing_membrane is an Uncommon beast material
    assert by_id["mat_bat_wing_membrane"]["rarity"] in ("Uncommon", "Rare"), \
        "Bat Wing Membrane must be Uncommon or Rare"
    # Basics are Common
    for mid in ("mat_iron_ingot", "mat_cured_hide", "mat_glass_vial"):
        assert by_id[mid]["rarity"] == "Common", f"{mid} must be Common rarity"


def test_material_default_prices_are_set():
    by_id = {item["id"]: item for item in _SRD_MUNDANE}
    for mid in REQUIRED_MATERIAL_IDS:
        price = str(by_id[mid].get("default_price") or "")
        assert price.strip(), f"{mid} must have a non-empty default_price"


# ── Materials round-trip through DB ──────────────────────────────────────────

def test_materials_survive_db_seed(tmp_path, monkeypatch):
    _setup_tmp_db(tmp_path, monkeypatch)
    init_srd_items_table()
    rows = get_all_srd_items()
    by_id = {r["id"]: r for r in rows}
    for mid in REQUIRED_MATERIAL_IDS:
        assert mid in by_id, f"{mid} missing after DB seed"
        row = by_id[mid]
        assert row["category"] == "Material"
        assert row["weight"] >= 0
        assert row.get("stack_limit", 1) >= 1
        assert "material" in str(row.get("tags") or "")


# ── Profession definitions ────────────────────────────────────────────────────

def test_all_five_professions_seeded(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    professions = sdb.list_professions()
    seeded_ids = {p["id"] for p in professions}
    missing = REQUIRED_PROFESSION_IDS - seeded_ids
    assert not missing, f"Missing professions after seed: {missing}"


def test_professions_have_descriptions(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    for prof in sdb.list_professions():
        if prof["id"] not in REQUIRED_PROFESSION_IDS:
            continue
        desc = str(prof.get("description") or "")
        assert len(desc) >= 10, f"Profession {prof['id']} needs a player-facing description"


def test_profession_shop_type_compatibility(tmp_path, monkeypatch):
    """Each profession must be taught by at least one valid shop type."""
    valid_shop_types = {"blacksmith", "alchemist", "general", "magic", "black_market"}
    sdb = _seed_all(tmp_path, monkeypatch)
    for prof in sdb.list_professions():
        if prof["id"] not in REQUIRED_PROFESSION_IDS:
            continue
        taught_by = prof.get("taught_by_shop_types_json") or []
        assert len(taught_by) >= 1, f"Profession {prof['id']} has no teaching shops"
        for shop_type in taught_by:
            assert shop_type in valid_shop_types, \
                f"Profession {prof['id']} references unknown shop type '{shop_type}'"


def test_blacksmithing_taught_at_blacksmith(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    prof = sdb.get_profession_by_id("blacksmithing")
    assert prof is not None
    assert "blacksmith" in (prof.get("taught_by_shop_types_json") or [])


def test_alchemy_taught_at_alchemist_and_magic(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    prof = sdb.get_profession_by_id("alchemy")
    assert prof is not None
    taught = prof.get("taught_by_shop_types_json") or []
    assert "alchemist" in taught or "magic" in taught, \
        "Alchemy must be taught at alchemist or magic shops"


def test_tailoring_is_supported(tmp_path, monkeypatch):
    """Tailoring must be present since Batwing Cloak requires it."""
    sdb = _seed_all(tmp_path, monkeypatch)
    prof = sdb.get_profession_by_id("tailoring")
    assert prof is not None, "Tailoring profession must be seeded"
    assert prof["name"] == "Tailoring"


# ── Recipe definitions ────────────────────────────────────────────────────────

def test_all_three_recipes_seeded(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    recipes = sdb.list_crafting_recipes()
    seeded_ids = {r["id"] for r in recipes}
    missing = REQUIRED_RECIPE_IDS - seeded_ids
    assert not missing, f"Missing recipes after seed: {missing}"


def test_recipe_minor_healing_draught_uses_glass_vial(tmp_path, monkeypatch):
    """Minor Healing Draught must require Glass Vial (canonical mat_glass_vial)."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_minor_healing_draught")
    assert recipe is not None
    mat_names = [m["name"].lower() for m in (recipe.get("requires_materials_json") or [])]
    assert "glass vial" in mat_names, \
        f"rec_minor_healing_draught must use 'Glass Vial'; got materials: {mat_names}"


def test_recipe_leather_patch_kit_uses_cured_hide(tmp_path, monkeypatch):
    """Leather Patch Kit must require Cured Hide (canonical mat_cured_hide)."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_leather_patch_kit")
    assert recipe is not None
    mat_names = [m["name"].lower() for m in (recipe.get("requires_materials_json") or [])]
    assert "cured hide" in mat_names, \
        f"rec_leather_patch_kit must use 'Cured Hide'; got materials: {mat_names}"


def test_recipe_leather_patch_kit_uses_iron_ingot(tmp_path, monkeypatch):
    """Leather Patch Kit must require Iron Ingot (canonical mat_iron_ingot)."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_leather_patch_kit")
    assert recipe is not None
    mat_names = [m["name"].lower() for m in (recipe.get("requires_materials_json") or [])]
    assert "iron ingot" in mat_names, \
        f"rec_leather_patch_kit must use 'Iron Ingot'; got materials: {mat_names}"


def test_recipe_batwing_cloak_uses_bat_wing_membrane(tmp_path, monkeypatch):
    """Batwing Cloak must use Bat Wing Membrane — it's a bat-themed item."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert recipe is not None
    mat_names = [m["name"].lower() for m in (recipe.get("requires_materials_json") or [])]
    assert "bat wing membrane" in mat_names, \
        f"rec_batwing_cloak must use 'Bat Wing Membrane'; got materials: {mat_names}"


def test_recipe_batwing_cloak_uses_shadow_resin(tmp_path, monkeypatch):
    """Batwing Cloak must use Shadow Resin (canonical mat_shadow_resin)."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert recipe is not None
    mat_names = [m["name"].lower() for m in (recipe.get("requires_materials_json") or [])]
    assert "shadow resin" in mat_names, \
        f"rec_batwing_cloak must use 'Shadow Resin'; got materials: {mat_names}"


def test_recipe_batwing_cloak_uses_cured_hide(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert recipe is not None
    mat_names = [m["name"].lower() for m in (recipe.get("requires_materials_json") or [])]
    assert "cured hide" in mat_names, \
        f"rec_batwing_cloak must use 'Cured Hide'; got materials: {mat_names}"


def test_recipe_batwing_cloak_is_bat_tagged(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert recipe is not None
    tags = recipe.get("tags_json") or []
    assert any("bat" in t.lower() for t in tags), \
        f"rec_batwing_cloak must have a bat-related tag; got tags: {tags}"


def test_recipe_rarities_are_correct(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    draught = sdb.get_crafting_recipe("rec_minor_healing_draught")
    patch_kit = sdb.get_crafting_recipe("rec_leather_patch_kit")
    cloak = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert draught["rarity"] == "common", "Minor Healing Draught must be common rarity"
    assert patch_kit["rarity"] == "common", "Leather Patch Kit must be common rarity"
    assert cloak["rarity"] == "uncommon", "Batwing Cloak must be uncommon rarity"


def test_recipe_result_items_have_descriptions(tmp_path, monkeypatch):
    """Every result_item_json must carry a player-facing notes field."""
    sdb = _seed_all(tmp_path, monkeypatch)
    for rid in REQUIRED_RECIPE_IDS:
        recipe = sdb.get_crafting_recipe(rid)
        assert recipe is not None
        result = recipe.get("result_item_json") or {}
        notes = str(result.get("notes") or "")
        assert len(notes) >= 20, f"{rid} result_item notes too short: {notes!r}"


def test_recipe_durations_are_starter_balanced(tmp_path, monkeypatch):
    """Common recipes complete in <= 3 min; uncommon in <= 10 min."""
    sdb = _seed_all(tmp_path, monkeypatch)
    common_limit = 3 * 60      # 180 seconds
    uncommon_limit = 10 * 60   # 600 seconds
    for rid in REQUIRED_RECIPE_IDS:
        recipe = sdb.get_crafting_recipe(rid)
        duration = int(recipe.get("duration_seconds") or 0)
        assert duration > 0, f"{rid} must have a positive duration"
        if recipe["rarity"] == "common":
            assert duration <= common_limit, \
                f"{rid} (common) duration {duration}s exceeds starter limit of {common_limit}s"
        elif recipe["rarity"] == "uncommon":
            assert duration <= uncommon_limit, \
                f"{rid} (uncommon) duration {duration}s exceeds starter limit of {uncommon_limit}s"


def test_recipe_fees_are_positive(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    for rid in REQUIRED_RECIPE_IDS:
        recipe = sdb.get_crafting_recipe(rid)
        assert int(recipe.get("fee_units") or 0) > 0, f"{rid} must have a positive fee_units"


def test_recipe_station_shop_types_are_valid(tmp_path, monkeypatch):
    valid_shop_types = {"blacksmith", "alchemist", "general", "magic", "black_market"}
    sdb = _seed_all(tmp_path, monkeypatch)
    for rid in REQUIRED_RECIPE_IDS:
        recipe = sdb.get_crafting_recipe(rid)
        stations = recipe.get("station_shop_types_json") or []
        assert len(stations) >= 1, f"{rid} must list at least one station shop type"
        for st in stations:
            assert st in valid_shop_types, f"{rid} references unknown shop type '{st}'"


def test_recipe_professions_reference_seeded_professions(tmp_path, monkeypatch):
    """Every profession required by a recipe must be in the seeded catalog."""
    sdb = _seed_all(tmp_path, monkeypatch)
    catalog_ids = {p["id"] for p in sdb.list_professions()}
    for rid in REQUIRED_RECIPE_IDS:
        recipe = sdb.get_crafting_recipe(rid)
        for pid in (recipe.get("requires_professions_json") or []):
            assert pid in catalog_ids, \
                f"{rid} requires profession '{pid}' which is not seeded in catalog"


# ── Healing draught station compatibility ─────────────────────────────────────

def test_minor_healing_draught_craftable_at_alchemist(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_minor_healing_draught")
    assert "alchemist" in (recipe.get("station_shop_types_json") or [])


def test_leather_patch_kit_craftable_at_blacksmith(tmp_path, monkeypatch):
    """Leather Patch Kit should be craftable at a blacksmith (iron rivets access)."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_leather_patch_kit")
    assert "blacksmith" in (recipe.get("station_shop_types_json") or [])


def test_batwing_cloak_craftable_at_magic_shop(tmp_path, monkeypatch):
    """Batwing Cloak needs shadow resin treatment — magic shop access is required."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert "magic" in (recipe.get("station_shop_types_json") or [])


# ── Idempotency: duplicate seeding produces no extra rows ─────────────────────

def test_seed_professions_idempotent(tmp_path, monkeypatch):
    """Seeding professions twice must not create duplicate rows."""
    import server.db as sdb
    _setup_tmp_db(tmp_path, monkeypatch)
    sdb.init_db()
    count_after_first = len(sdb.list_professions())

    # Seed again via a direct connection
    import server.db as _sdb
    from server.db import _seed_professions
    with _sdb.get_conn() as conn:
        _seed_professions(conn)
        conn.commit()

    count_after_second = len(sdb.list_professions())
    assert count_after_first == count_after_second, (
        f"Seeding professions twice changed count: "
        f"{count_after_first} → {count_after_second}"
    )


def test_seed_recipes_idempotent(tmp_path, monkeypatch):
    """Seeding recipes twice must not create duplicate rows."""
    import server.db as sdb
    _setup_tmp_db(tmp_path, monkeypatch)
    sdb.init_db()
    count_after_first = len(sdb.list_crafting_recipes())

    from server.db import _seed_crafting_recipes
    with sdb.get_conn() as conn:
        _seed_crafting_recipes(conn)
        conn.commit()

    count_after_second = len(sdb.list_crafting_recipes())
    assert count_after_first == count_after_second, (
        f"Seeding recipes twice changed count: "
        f"{count_after_first} → {count_after_second}"
    )


def test_seed_materials_idempotent(tmp_path, monkeypatch):
    """Seeding srd_items twice must not create duplicate material rows."""
    _setup_tmp_db(tmp_path, monkeypatch)
    init_srd_items_table()
    count_after_first = len(get_all_srd_items())

    init_srd_items_table()
    count_after_second = len(get_all_srd_items())
    assert count_after_first == count_after_second, (
        f"Seeding srd_items twice changed count: "
        f"{count_after_first} → {count_after_second}"
    )


def test_no_duplicate_material_ids_in_srd_mundane():
    """No material ID may appear more than once in _SRD_MUNDANE."""
    ids = [item["id"] for item in _SRD_MUNDANE]
    seen, dupes = set(), set()
    for item_id in ids:
        if item_id in seen:
            dupes.add(item_id)
        seen.add(item_id)
    assert not dupes, f"Duplicate IDs in _SRD_MUNDANE: {dupes}"


# ── UI representation: list helpers return well-formed dicts ─────────────────

def test_list_professions_returns_correct_shape(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    for prof in sdb.list_professions():
        assert "id" in prof
        assert "name" in prof
        assert isinstance(prof.get("taught_by_shop_types_json"), list)
        assert isinstance(prof.get("tool_hints_json"), list)


def test_list_crafting_recipes_returns_correct_shape(tmp_path, monkeypatch):
    sdb = _seed_all(tmp_path, monkeypatch)
    for recipe in sdb.list_crafting_recipes():
        assert "id" in recipe
        assert "name" in recipe
        assert isinstance(recipe.get("requires_professions_json"), list)
        assert isinstance(recipe.get("requires_materials_json"), list)
        assert isinstance(recipe.get("station_shop_types_json"), list)
        assert isinstance(recipe.get("tags_json"), list)
        assert isinstance(recipe.get("result_item_json"), dict)


def test_get_crafting_recipe_returns_decoded_json_fields(tmp_path, monkeypatch):
    """get_crafting_recipe must return Python lists/dicts, not raw JSON strings."""
    sdb = _seed_all(tmp_path, monkeypatch)
    recipe = sdb.get_crafting_recipe("rec_batwing_cloak")
    assert isinstance(recipe["requires_professions_json"], list)
    assert isinstance(recipe["requires_materials_json"], list)
    assert isinstance(recipe["result_item_json"], dict)
    # result_item_json must have a name
    assert recipe["result_item_json"].get("name") == "Batwing Cloak"
