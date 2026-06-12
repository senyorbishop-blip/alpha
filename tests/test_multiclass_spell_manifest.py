from server.character.spell_compendium import (
    build_character_spell_manifest,
    build_multiclass_spell_context,
    validate_spell_selection,
)


def _card(manifest, spell_id):
    return next(card for card in manifest.get("cards") or [] if card.get("id") == spell_id)


def test_single_class_wizard_level_5_still_gets_third_level_spell_access():
    document = {
        "classes": [{"classId": "wizard", "level": 5, "subclassId": "evocation"}],
        "abilities": {"scores": {"int": 16}},
        "spellState": {"known": ["magic-missile", "fireball"], "prepared": ["magic-missile", "fireball"]},
    }

    manifest = build_character_spell_manifest(document)

    assert manifest["validation"]["ok"] is True
    assert manifest["limits"]["multiclass"] is False
    fireball = _card(manifest, "fireball")
    assert fireball["isAccessible"] is True
    assert fireball["sourceClass"] == "wizard"
    assert fireball["sourceType"] == "class"
    assert fireball["availableCastLevels"][-1] == 3


def test_cleric_wizard_multiclass_accepts_access_from_either_class():
    document = {
        "classes": [
            {"classId": "cleric", "level": 3, "subclassId": "life-domain"},
            {"classId": "wizard", "level": 2, "subclassId": "evocation"},
        ],
        "abilities": {"scores": {"wis": 16, "int": 16}},
        "spellState": {"known": ["magic-missile"], "prepared": ["bless", "magic-missile"]},
    }

    manifest = build_character_spell_manifest(document)
    validation = validate_spell_selection(
        class_id="cleric",
        class_level=3,
        abilities=document["abilities"],
        known=document["spellState"]["known"],
        prepared=document["spellState"]["prepared"],
        document=document,
        subclass_id="life-domain",
    )

    assert validation["ok"] is True
    assert manifest["limits"]["multiclass"] is True
    bless = _card(manifest, "bless")
    missile = _card(manifest, "magic-missile")
    assert bless["isAccessible"] is True
    assert missile["isAccessible"] is True
    assert {source["classId"] for source in missile["sourceClasses"]} >= {"cleric", "wizard"}


def test_warlock_multiclass_keeps_pact_slots_separate_from_combined_slots():
    document = {
        "classes": [
            {"classId": "warlock", "level": 3, "subclassId": "fiend-patron"},
            {"classId": "wizard", "level": 2},
        ],
        "abilities": {"scores": {"cha": 16, "int": 16}},
        "spellState": {"known": ["hex", "magic-missile"], "prepared": ["magic-missile"]},
    }

    context = build_multiclass_spell_context(document)
    manifest = build_character_spell_manifest(document)

    assert context["casterLevel"] == 2
    assert context["spellSlots"] == {"1st": 3}
    assert context["pactMagic"]["slots"] == {"2nd": 2}
    assert manifest["limits"]["spellSlots"] == {"1st": 3}
    assert manifest["limits"]["pactMagic"]["slots"] == {"2nd": 2}


def test_paladin_ranger_multiclass_uses_half_caster_combined_slots():
    document = {
        "classes": [
            {"classId": "paladin", "level": 3},
            {"classId": "ranger", "level": 2},
        ],
        "abilities": {"scores": {"cha": 14, "wis": 14}},
        "spellState": {"known": ["cure-wounds"], "prepared": ["bless", "cure-wounds"]},
    }

    context = build_multiclass_spell_context(document)
    manifest = build_character_spell_manifest(document)

    assert context["casterLevel"] == 2
    assert context["spellSlots"] == {"1st": 3}
    assert manifest["limits"]["spellSlots"] == {"1st": 3}
    assert _card(manifest, "cure-wounds")["isAccessible"] is True


def test_arcane_trickster_style_subclass_spell_access_remains_possible():
    document = {
        "classes": [{"classId": "rogue", "level": 3, "subclassId": "arcane-trickster"}],
        "abilities": {"scores": {"int": 16, "dex": 16}},
        "spellState": {"known": ["minor-illusion", "disguise-self"], "prepared": []},
    }

    manifest = build_character_spell_manifest(document)

    assert manifest["validation"]["ok"] is True
    disguise = _card(manifest, "disguise-self")
    assert disguise["isAccessible"] is True
    assert disguise["sourceClass"] == "rogue"
    assert disguise["sourceSubclass"] == "arcane-trickster"
    assert disguise["sourceType"] == "subclass"


def test_imported_multiclass_spellbook_entries_are_preserved_as_manifest_cards():
    document = {
        "classes": [
            {"classId": "cleric", "level": 1},
            {"classId": "wizard", "level": 1},
        ],
        "abilities": {"scores": {"wis": 14, "int": 14}},
        "spellState": {
            "known": [],
            "prepared": [],
            "spellbookEntries": [
                {"id": "shield", "name": "Shield", "sourceClass": "wizard", "source": "D&D Beyond"},
                {"id": "healing-word", "name": "Healing Word", "sourceClass": "cleric", "source": "D&D Beyond"},
            ],
        },
    }

    manifest = build_character_spell_manifest(document)

    assert "shield" in manifest["known"] or "shield" in manifest["prepared"]
    assert "healing-word" in manifest["known"] or "healing-word" in manifest["prepared"]
    shield = _card(manifest, "shield")
    healing_word = _card(manifest, "healing-word")
    assert any(source["sourceType"] == "imported_spellbook" for source in shield["sourceClasses"])
    assert any(source["sourceType"] == "imported_spellbook" for source in healing_word["sourceClasses"])
