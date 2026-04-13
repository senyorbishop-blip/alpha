from server.character.rules_catalog import load_rules_catalog
from server.character.spell_compendium import list_spells, get_subclass_spell_grants, build_spell_limits_for_class


def test_tinker_exists_with_full_progression_and_subclasses():
    catalog = load_rules_catalog()
    classes = {row["id"]: row for row in catalog["classes"]}
    assert "tinker" in classes
    tinker = classes["tinker"]
    assert tinker["subclassLevel"] == 3
    assert tinker["spellcastingType"] == "half"
    assert len(tinker.get("progressionTable") or []) == 20

    subclass_ids = {row["id"] for row in catalog["subclasses"] if row.get("classId") == "tinker"}
    assert {"artillerist", "alchemist", "mechanist", "saboteur"} <= subclass_ids


def test_tinker_spell_list_and_subclass_grants_are_available():
    rows = list_spells(cls="tinker")
    ids = {row["id"] for row in rows}
    assert "mending" in ids
    assert "shield" in ids
    assert "revivify" in ids

    grants = get_subclass_spell_grants({"classes": [{"classId": "tinker", "subclassId": "artillerist", "level": 5}]}, class_id="tinker", class_level=5)
    assert "shield" in grants["alwaysKnown"]
    assert "scorching-ray" in grants["alwaysKnown"]


def test_tinker_spell_limits_expose_known_spells_and_slots():
    limits = build_spell_limits_for_class("tinker", 9, {"scores": {"int": 18}})
    assert limits["spellcastingAbility"] == "int"
    assert limits["spellsKnown"] == 9
    assert limits["spellSlots"]["3rd"] == 2
