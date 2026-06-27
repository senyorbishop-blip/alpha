from server.character import (
    CHARACTER_SCHEMA_NAME,
    build_profile_library_entry,
    map_character_to_charbook,
    map_character_to_charsheet,
    default_character_document,
    default_runtime,
    get_builder_rules_catalog,
    resolve_runtime,
    validate_required_shape,
)


def test_default_character_document_has_required_foundation_fields():
    doc = default_character_document()

    assert doc["schema"] == CHARACTER_SCHEMA_NAME
    assert doc["schemaVersion"] >= 1
    assert doc["rulesMode"] == "casual"
    assert doc["sourceMode"] == "native"

    for key in (
        "ruleset",
        "contentPackVersion",
        "identity",
        "species",
        "background",
        "abilities",
        "classes",
        "feats",
        "talents",
        "awakening",
        "equipment",
        "spellState",
        "summons",
        "importMeta",
        "audit",
    ):
        assert key in doc

    assert validate_required_shape(doc) == []


def test_resolve_runtime_computes_level_and_proficiency_bonus():
    result = resolve_runtime(
        {
            "identity": {"name": "Kestrel"},
            "classes": [
                {"name": "Ranger", "level": 3},
                {"name": "Rogue", "level": 2},
            ],
            "species": {"name": "Elf", "speed": 35},
            "abilities": {"scores": {"con": 14}},
        }
    )

    runtime = result["runtime"]
    assert runtime["levelTotal"] == 5
    assert runtime["proficiencyBonus"] == 3
    assert runtime["speed"]["walk"] == 35
    assert runtime["hp"]["max"] == 45


def test_profile_entry_mapper_keeps_legacy_and_native_shapes_together():
    entry = build_profile_library_entry(
        {
            "identity": {"characterId": "char-1", "name": "Mira"},
            "species": {"name": "Human", "speed": 30},
            "background": {"name": "Sage"},
            "classes": [{"name": "Wizard", "level": 4, "subclass": "Evocation"}],
            "abilities": {
                "scores": {"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 13, "cha": 10}
            },
        }
    )

    assert entry["id"] == "char-1"
    assert entry["charBook"]["className"] == "Wizard"
    assert entry["charSheet"]["classes"][0]["subclass"] == "Evocation"
    assert "nativeCharacter" in entry
    assert "nativeRuntime" in entry


def test_default_runtime_exists_for_downstream_mapping_contracts():
    runtime = default_runtime()
    assert runtime["levelTotal"] == 1
    assert runtime["proficiencyBonus"] == 2
    assert isinstance(runtime["spellAccess"], dict)
    assert runtime["pendingTalentGrants"] == []


def test_export_mapper_provides_safe_defaults_for_legacy_shapes():
    char_sheet = map_character_to_charsheet({}, {})
    char_book = map_character_to_charbook({}, {})

    assert char_sheet["name"] == ""
    assert char_sheet["level"] == 1
    assert char_sheet["hp"]["max"] == 1
    assert char_sheet["speed"]["walk"] == 30

    assert char_book["className"] == ""
    assert char_book["subclass"] == ""
    assert char_book["abilities"]["str"]["score"] == 10
    assert char_book["spells"]["slots"] == {}


def test_profile_save_payload_preserves_portrait_avatar_and_token_image_fields():
    from server.character.service import build_profile_upsert_payload

    payload = build_profile_upsert_payload(
        {
            "identity": {
                "characterId": "portrait-hero",
                "name": "Portrait Hero",
                "portraitUrl": "https://example.com/avatar.png",
                "tokenImageUrl": "https://example.com/token.png",
            },
            "ruleset": "casual-dnd-5e-compatible",
            "spellState": {},
            "classes": [{"name": "Fighter", "level": 1}],
        },
        profile_id="portrait-hero",
    )

    assert payload["nativeCharacter"]["identity"]["portraitUrl"].endswith("avatar.png")
    assert payload["nativeCharacter"]["identity"]["tokenImageUrl"].endswith("token.png")
    assert payload["charSheet"]["avatarUrl"].endswith("avatar.png")
    assert payload["charSheet"]["tokenImageUrl"].endswith("token.png")
    assert payload["charBook"]["avatarUrl"].endswith("avatar.png")
    assert payload["charBook"]["tokenImageUrl"].endswith("token.png")


def test_export_mapper_uses_runtime_spell_and_resource_placeholders():
    document = {
        "identity": {"name": "Nyx"},
        "classes": [{"name": "Sorcerer", "subclass": "Wild Magic", "level": 2}],
        "abilities": {"scores": {"cha": 16}},
    }
    runtime = {
        "levelTotal": 2,
        "proficiencyBonus": 2,
        "hp": {"max": 12, "current": 9, "temp": 0},
        "ac": 13,
        "speed": {"walk": 30},
        "resources": [{"id": "sorcery_points", "current": 2, "max": 2}],
        "spellAccess": {
            "slots": {"1": {"max": 3, "used": 1}},
            "known": ["magic_missile"],
            "prepared": [],
        },
    }

    char_book = map_character_to_charbook(document, runtime)
    char_sheet = map_character_to_charsheet(document, runtime)

    assert char_book["name"] == "Nyx"
    assert char_book["className"] == "Sorcerer"
    assert char_book["subclass"] == "Wild Magic"
    assert char_book["resources"][0]["id"] == "sorcery_points"
    assert char_book["spells"]["slots"]["1"]["max"] == 3
    assert char_sheet["spellAccess"]["known"] == ["magic_missile"]


def test_builder_rules_catalog_loads_minimal_playable_slice():
    catalog = get_builder_rules_catalog()

    assert catalog["rulesetId"] == "5e2024"
    assert "fighter" in catalog["classesById"]
    assert "wizard" in catalog["classesById"]
    assert "human" in catalog["speciesById"]
    assert "wood-elf" in catalog["speciesById"]
    assert "fighter-bulwark-stance" in catalog["talentsById"]
    assert "wizard-arcane-frugality" in catalog["talentsById"]
    assert "fighter-warborn-paragon" in catalog["awakeningsById"]
    assert "wizard-astral-lucid" in catalog["awakeningsById"]


def test_builder_rules_catalog_subclasses_are_mapped_by_class():
    catalog = get_builder_rules_catalog()

    fighter_subclasses = {row["id"] for row in catalog["subclassesByClass"]["fighter"]}
    wizard_subclasses = {row["id"] for row in catalog["subclassesByClass"]["wizard"]}

    assert "champion" in fighter_subclasses
    assert "evoker" in wizard_subclasses


def test_builder_rules_catalog_awakenings_are_mapped_by_class():
    catalog = get_builder_rules_catalog()

    fighter_awakenings = {row["id"] for row in catalog["awakeningsByClass"]["fighter"]}
    wizard_awakenings = {row["id"] for row in catalog["awakeningsByClass"]["wizard"]}

    assert "fighter-warborn-paragon" in fighter_awakenings
    assert "wizard-astral-lucid" in wizard_awakenings


def test_resolver_populates_runtime_class_display_from_subclass_id():
    result = resolve_runtime(
        {
            "identity": {"name": "Bran"},
            "classes": [{"classId": "fighter", "level": 3, "subclassId": "champion"}],
        }
    )
    runtime = result["runtime"]
    canonical = result["document"]

    assert runtime["classDisplay"]["classId"] == "fighter"
    assert runtime["classDisplay"]["subclassId"] == "champion"
    assert runtime["classDisplay"]["subclassName"] == "Champion"
    assert runtime["classDisplay"]["subclassUnlockLevel"] == 3
    assert runtime["classDisplay"]["subclassUnlocked"] is True
    assert canonical["classes"][0]["subclass"] == "Champion"


def test_resolver_keeps_subclass_locked_when_below_unlock_level():
    result = resolve_runtime(
        {
            "identity": {"name": "Aria"},
            "classes": [{"classId": "fighter", "level": 1, "subclassId": "champion"}],
        }
    )
    runtime = result["runtime"]
    assert runtime["classDisplay"]["subclassUnlocked"] is False


def test_resolver_applies_native_talent_metadata_without_overriding_class_progression():
    result = resolve_runtime(
        {
            "identity": {"name": "Tamsin"},
            "classes": [{"classId": "fighter", "level": 3, "subclassId": "champion"}],
            "talents": [{"talentId": "fighter-bulwark-stance"}],
        }
    )
    runtime = result["runtime"]

    assert runtime["classDisplay"]["subclassId"] == "champion"
    assert runtime["talents"][0]["id"] == "fighter-bulwark-stance"
    assert runtime["talentGrants"][0]["source"] == "casualdnd_talent"
    assert "talent:bulwark" in runtime["derivedTags"]
    assert any(grant["type"] == "resource_bonus" for grant in runtime["pendingTalentGrants"])


def test_resolver_only_accepts_casualdnd_talent_sources(monkeypatch):
    from server.character import talent_engine

    def fake_catalog():
        return {
            "talentsById": {
                "fighter-foreign-talent": {
                    "id": "fighter-foreign-talent",
                    "displayName": "Foreign Talent",
                    "classRestrictions": ["fighter"],
                    "minimumLevel": 1,
                    "grants": [{"type": "derived_tag", "value": "talent:foreign"}],
                    "tags": [],
                    "source": "third_party",
                }
            }
        }

    monkeypatch.setattr(talent_engine, "load_rules_catalog", fake_catalog)

    result = resolve_runtime(
        {
            "classes": [{"classId": "fighter", "level": 2}],
            "talents": [{"talentId": "fighter-foreign-talent"}],
        }
    )
    runtime = result["runtime"]
    assert runtime["talents"] == []
    assert runtime["talentGrants"] == []


def test_native_builder_fighter_level_one_uses_hit_die_plus_con_for_hp():
    result = resolve_runtime(
        {
            "identity": {"name": "Kara"},
            "classes": [{"classId": "fighter", "level": 1}],
            "abilities": {"scores": {"con": 14}},
        }
    )
    runtime = result["runtime"]
    # Fighter d10 full die at level 1 + CON mod +2 = 12
    assert runtime["hp"]["max"] == 12
    assert runtime["hp"]["current"] == 12
    assert runtime["hp"]["temp"] == 0
    assert runtime["ac"] >= 10


def test_native_builder_spellcaster_level_one_uses_runtime_hp_without_fallback_lock():
    result = resolve_runtime(
        {
            "identity": {"name": "Mira"},
            "classes": [{"classId": "wizard", "level": 1}],
            "abilities": {"scores": {"con": 12}},
        }
    )
    runtime = result["runtime"]
    # Wizard d6 full die at level 1 + CON mod +1 = 7
    assert runtime["hp"]["max"] == 7
    assert runtime["hp"]["current"] == 7
    assert runtime["hp"]["temp"] == 0


def test_runtime_hp_ignores_noncanonical_legacy_hp_root_fields():
    result = resolve_runtime(
        {
            "identity": {"name": "Nyx"},
            "classes": [{"classId": "fighter", "level": 2}],
            "abilities": {"scores": {"con": 14}},
            "hp": {"max": 24, "current": 17, "temp": 5},
        }
    )
    runtime = result["runtime"]
    # Fighter level 2 CON 14: d10 (full at lvl1) + d10_avg (lvl2) + 2+2 CON = 10+6+4 = 20
    # Legacy doc.hp fields must NOT override native computed max.
    assert runtime["hp"]["max"] == 20
    assert runtime["hp"]["current"] == 20
    assert runtime["hp"]["temp"] == 0

def test_resolver_exposes_awakening_layer_without_replacing_subclass():
    result = resolve_runtime(
        {
            "classes": [{"classId": "fighter", "level": 15, "subclassId": "champion"}],
            "awakening": {"pathId": "fighter-warborn-paragon", "stage": 2},
        }
    )

    runtime = result["runtime"]
    assert runtime["classDisplay"]["subclassId"] == "champion"
    assert runtime["awakening"]["unlocked"] is True
    assert runtime["awakening"]["pathId"] == "fighter-warborn-paragon"
    assert any(row["id"] == "fighter-warborn-iron-mind" for row in runtime["passives"])
    assert any(row["id"] == "fighter-warborn-battle-surge" for row in runtime["actions"])
    assert any(row["id"] == "paragon_resolve" for row in runtime["resources"])


def test_default_character_document_has_identity_presentation_and_spellbook_extensions():
    doc = default_character_document()

    assert "presentation" in doc
    assert doc["identity"]["portraitUrl"] == ""
    assert doc["identity"]["tokenImageUrl"] == ""
    assert doc["presentation"]["portraitFrame"] == "classic"
    assert isinstance(doc["presentation"]["tokenDisplay"], dict)
    assert "spellbookEntries" in doc["spellState"]


def test_resolver_computes_passive_perception_ac_and_hit_dice_slice():
    result = resolve_runtime(
        {
            "classes": [{"classId": "fighter", "level": 3}],
            "species": {"speed": 30, "senses": [{"type": "darkvision", "range": 60}]},
            "abilities": {"scores": {"dex": 14, "wis": 12, "con": 14}},
        }
    )

    runtime = result["runtime"]
    assert runtime["ac"] == 12
    assert runtime["senses"]["passivePerception"] == 11
    assert runtime["senses"]["darkvision"] == 60
    assert runtime["hp"]["max"] >= 24
    assert runtime["hp"]["hitDice"][0]["count"] == 3


def test_export_mapper_preserves_portrait_and_token_display_compatibility_fields():
    document = {
        "identity": {
            "name": "Iris",
            "portraitUrl": "https://example.com/portrait.png",
            "tokenImageUrl": "https://example.com/token.png",
        },
        "presentation": {
            "portraitFrame": "rune",
            "tokenDisplay": {"accentColor": "#ff00aa"},
        },
    }

    char_sheet = map_character_to_charsheet(document, {})
    char_book = map_character_to_charbook(document, {})

    assert char_sheet["avatarUrl"].endswith("portrait.png")
    assert char_sheet["tokenImageUrl"].endswith("token.png")
    assert char_sheet["portraitFrame"] == "rune"
    assert char_book["avatarUrl"].endswith("portrait.png")
    assert char_book["tokenDisplay"]["accentColor"] == "#ff00aa"


def test_charbook_includes_proficiency_bonus_from_runtime():
    runtime = {
        "levelTotal": 5,
        "proficiencyBonus": 3,
        "hp": {"max": 40, "current": 40, "temp": 0},
        "ac": 14,
        "speed": {"walk": 30},
    }
    char_book = map_character_to_charbook({}, runtime)
    assert char_book["proficiencyBonus"] == 3


def test_charbook_proficiency_bonus_defaults_to_2_when_runtime_absent():
    char_book = map_character_to_charbook({}, {})
    assert char_book["proficiencyBonus"] == 2


def test_charbook_includes_temp_hp_from_runtime():
    runtime = {
        "hp": {"max": 20, "current": 15, "temp": 5},
        "speed": {"walk": 30},
    }
    char_book = map_character_to_charbook({}, runtime)
    assert char_book["tempHp"] == 5
    assert char_book["maxHp"] == 20
    assert char_book["currentHp"] == 15


def test_charbook_temp_hp_defaults_to_zero_when_absent():
    char_book = map_character_to_charbook({}, {})
    assert char_book["tempHp"] == 0


def test_charbook_includes_feats_from_document():
    document = {
        "feats": ["alert", "war_caster", "tough"],
    }
    char_book = map_character_to_charbook(document, {})
    assert char_book["feats"] == ["alert", "war_caster", "tough"]


def test_charbook_feats_defaults_to_empty_list_when_absent():
    char_book = map_character_to_charbook({}, {})
    assert char_book["feats"] == []


def test_charbook_includes_equipment_currency_from_document():
    document = {
        "equipment": {
            "currency": {"cp": 5, "sp": 12, "ep": 0, "gp": 50, "pp": 2},
        }
    }
    char_book = map_character_to_charbook(document, {})
    assert char_book["currency"]["cp"] == 5
    assert char_book["currency"]["sp"] == 12
    assert char_book["currency"]["gp"] == 50
    assert char_book["currency"]["pp"] == 2


def test_charbook_currency_defaults_to_zero_when_absent():
    char_book = map_character_to_charbook({}, {})
    for coin in ("cp", "sp", "ep", "gp", "pp"):
        assert char_book["currency"][coin] == 0


def test_charbook_spells_known_falls_back_to_document_spellstate_when_runtime_absent():
    document = {
        "spellState": {
            "known": ["fireball", "magic_missile"],
            "prepared": ["fireball"],
        }
    }
    # Runtime has no spellAccess — charBook must use document fallback.
    char_book = map_character_to_charbook(document, {})
    assert char_book["spells"]["known"] == ["fireball", "magic_missile"]
    assert char_book["spells"]["prepared"] == ["fireball"]


def test_charbook_spells_known_prefers_runtime_spellaccess_over_document():
    document = {
        "spellState": {
            "known": ["fireball"],
        }
    }
    runtime = {
        "spellAccess": {
            "slots": {},
            "known": ["fireball", "lightning_bolt"],
            "prepared": [],
        }
    }
    char_book = map_character_to_charbook(document, runtime)
    # Runtime known list should win (may include derived/resolved additions).
    assert "lightning_bolt" in char_book["spells"]["known"]


def test_charbook_token_image_url_falls_back_to_portrait_url():
    document = {
        "identity": {
            "portraitUrl": "https://example.com/portrait.png",
            "tokenImageUrl": "",
        }
    }
    char_book = map_character_to_charbook(document, {})
    assert char_book["tokenImageUrl"].endswith("portrait.png")


def test_charbook_token_image_url_uses_explicit_token_url_when_set():
    document = {
        "identity": {
            "portraitUrl": "https://example.com/portrait.png",
            "tokenImageUrl": "https://example.com/token.png",
        }
    }
    char_book = map_character_to_charbook(document, {})
    assert char_book["tokenImageUrl"].endswith("token.png")


def test_charbook_full_pipeline_preserves_all_required_fields():
    """End-to-end: resolve_runtime → map_character_to_charbook covers all audited fields."""
    result = resolve_runtime(
        {
            "identity": {
                "name": "Theron",
                "portraitUrl": "https://example.com/theron.png",
            },
            "species": {"name": "Half-Elf", "speed": 30},
            "background": {"name": "Outlander"},
            "classes": [{"classId": "fighter", "level": 4, "subclassId": "champion"}],
            "abilities": {
                "scores": {"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8}
            },
            "feats": ["alert", "tough"],
            "equipment": {
                "currency": {"cp": 0, "sp": 5, "ep": 0, "gp": 20, "pp": 0}
            },
            "spellState": {"known": [], "prepared": []},
        }
    )
    canonical = result["document"]
    runtime = result["runtime"]
    char_book = map_character_to_charbook(canonical, runtime)

    assert char_book["name"] == "Theron"
    assert char_book["species"] == "Half-Elf"
    assert char_book["background"] == "Outlander"
    assert char_book["className"] == "Fighter"
    assert char_book["subclass"] == "Champion"
    assert char_book["level"] == 4
    # Level 4 → proficiency bonus = 2 (levels 1-4: +2 per 5e rules); assert via runtime too.
    assert char_book["proficiencyBonus"] == runtime["proficiencyBonus"]
    assert char_book["ac"] == 12
    assert char_book["maxHp"] >= 1
    assert char_book["currentHp"] >= 0
    assert char_book["tempHp"] == 0
    assert char_book["abilities"]["str"]["score"] == 16
    assert char_book["abilities"]["dex"]["score"] == 14
    assert char_book["feats"] == ["alert", "tough"]
    assert char_book["currency"]["sp"] == 5
    assert char_book["currency"]["gp"] == 20
    assert char_book["avatarUrl"].endswith("theron.png")

def test_builder_rules_catalog_generates_feature_definitions_for_sparse_class_rows():
    catalog = get_builder_rules_catalog()
    monk = catalog["classesById"]["monk"]

    feature_defs = monk.get("featureDefinitions") or {}
    assert feature_defs, "Monk should expose generated feature definitions"
    assert any("Martial Arts" == row.get("displayName") for row in feature_defs.values())
    assert any("Stunning Strike" == row.get("displayName") for row in feature_defs.values())
    assert monk.get("featuresByLevel"), "Monk should expose level-grouped feature rows"


def test_resolver_populates_native_runtime_actions_passives_and_resources_from_class_data():
    result = resolve_runtime(
        {
            "identity": {"name": "Rurik"},
            "classes": [{"classId": "fighter", "level": 2}],
            "abilities": {"scores": {"str": 16, "dex": 12, "con": 14}},
        }
    )

    runtime = result["runtime"]

    action_names = {row.get("name") for row in runtime.get("bonusActions") or []}
    passive_names = {row.get("name") for row in runtime.get("passives") or []}
    resource_names = {row.get("name") for row in runtime.get("resources") or []}

    assert "Second Wind" in action_names
    assert "Fighting Style" in passive_names
    assert "Action Surge" in resource_names
    assert runtime.get("classFeatures"), "Resolver should emit classFeatures for downstream UI"


def test_native_hp_level3_sorcerer_uses_full_die_at_level_one():
    result = resolve_runtime(
        {
            "identity": {"name": "Lyra"},
            "classes": [{"classId": "sorcerer", "level": 3}],
            "abilities": {"scores": {"con": 10}},
        }
    )
    runtime = result["runtime"]
    # Sorcerer d6: level1=6, level2=avg4, level3=avg4, CON mod=0
    # Total = 6+4+4 = 14, NOT the broken 12 from all-average formula
    assert runtime["hp"]["max"] == 14
    assert runtime["hp"]["current"] == runtime["hp"]["max"]
    assert runtime["hp"]["temp"] == 0


def test_native_hp_level1_fighter_con14():
    result = resolve_runtime(
        {
            "classes": [{"classId": "fighter", "level": 1}],
            "abilities": {"scores": {"con": 14}},
        }
    )
    runtime = result["runtime"]
    # Fighter d10 full die at level 1 + CON +2 = 12
    assert runtime["hp"]["max"] == 12
    assert runtime["hp"]["current"] == 12


def test_native_hp_level1_wizard_con12():
    result = resolve_runtime(
        {
            "classes": [{"classId": "wizard", "level": 1}],
            "abilities": {"scores": {"con": 12}},
        }
    )
    runtime = result["runtime"]
    # Wizard d6 full die + CON +1 = 7
    assert runtime["hp"]["max"] == 7
    assert runtime["hp"]["current"] == 7


def test_native_hp_current_equals_max_on_fresh_creation():
    result = resolve_runtime(
        {
            "classes": [{"classId": "fighter", "level": 1}],
            "abilities": {"scores": {"con": 10}},
        }
    )
    runtime = result["runtime"]
    # Fresh character: currentHp must equal maxHp
    assert runtime["hp"]["current"] == runtime["hp"]["max"]


def test_native_hp_legacy_fallback_42_cannot_override_native_runtime():
    result = resolve_runtime(
        {
            "classes": [{"classId": "wizard", "level": 1}],
            "abilities": {"scores": {"con": 10}},
            "maxHP": 42,
            "maxHp": 42,
            "hp": {"max": 42, "current": 42, "temp": 0},
        }
    )
    runtime = result["runtime"]
    # Wizard d6 CON 10 = 6; legacy fields must not override native computation
    assert runtime["hp"]["max"] == 6
    assert runtime["hp"]["current"] == 6


def test_schema_preserves_pdf_import_source_mode():
    doc = default_character_document()
    doc["sourceMode"] = "dndbeyond_pdf"

    normalized = resolve_runtime(doc)["document"]

    assert normalized["sourceMode"] == "dndbeyond_pdf"


def test_imported_ac_hp_survive_normalize_round_trip():
    """A D&D Beyond PDF import must not lose its imported AC/HP or selected mode
    when the document is re-normalized (e.g. reopened or synced). Regression for
    AC 'revoking back' to the calculated value for PDF importers."""
    doc = default_character_document()
    doc["sourceMode"] = "pdf"
    doc["classes"] = [{"classId": "wizard", "name": "Wizard", "level": 1}]
    doc["abilities"]["scores"] = {"str": 10, "dex": 14, "con": 10, "int": 16, "wis": 12, "cha": 10}
    # Imported sheet had armour/bonuses Alpha cannot recompute, so imported AC/HP
    # differ from the native calculation.
    doc["ac"] = 18
    doc["importedAc"] = 18
    doc["maxHP"] = 30
    doc["importedMaxHp"] = 30
    doc["importedCurrentHp"] = 30

    normalized = resolve_runtime(doc)["document"]

    assert normalized["importedAc"] == 18
    assert normalized["importedMaxHp"] == 30
    runtime = resolve_runtime(normalized)["runtime"]["characterSheetRuntime"]
    assert runtime["ac"]["value"] == 18
    assert runtime["hp"]["max"] == 30


def test_approved_imported_mode_persists_through_normalize():
    """Once a player/DM approves the imported AC/HP, the selected mode and
    manual overrides must survive normalization regardless of source mode."""
    doc = default_character_document()
    doc["sourceMode"] = "pdf"
    doc["acSelectedMode"] = "imported_pdf"
    doc["ac"] = 17
    doc["importedAc"] = 17
    doc["hpManualOverride"] = 25

    normalized = resolve_runtime(doc)["document"]

    assert normalized["acSelectedMode"] == "imported_pdf"
    assert normalized["hpManualOverride"] == 25
