from __future__ import annotations

from copy import deepcopy

from server.character.resolver import resolve_character_runtime
from server.character.schema import default_character_document


def _doc(*, class_id: str, level: int, scores: dict[str, int], equipment: list[dict] | None = None) -> dict:
    doc = default_character_document()
    doc["identity"]["name"] = f"Audit {class_id}"
    doc["species"] = {"id": "human", "name": "Human", "size": "medium", "speed": 30, "traits": [], "senses": []}
    doc["classes"] = [{"classId": class_id, "name": class_id.title(), "level": level}]
    doc["abilities"]["scores"].update(scores)
    doc["equipment"]["inventory"] = deepcopy(equipment or [])
    return doc


def _armor(name: str, *, base_ac: int, armor_type: str, dex_cap: int | None = None, equipped: bool = True) -> dict:
    row = {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "equipment_kind": "armor",
        "kind": "armor",
        "base_ac": base_ac,
        "armor_type": armor_type,
        "equipped": equipped,
    }
    if dex_cap is not None:
        row["dex_cap"] = dex_cap
    return row


def _shield(name: str = "Shield", *, equipped: bool = True, ac_bonus: int | None = 2) -> dict:
    row = {"id": name.lower().replace(" ", "-"), "name": name, "equipment_kind": "shield", "kind": "shield", "equipped": equipped}
    if ac_bonus is not None:
        row["ac_bonus"] = ac_bonus
    return row


def _audit(doc: dict) -> dict:
    return resolve_character_runtime(doc)["runtime"]["characterAudit"]


def test_level_1_fighter_chain_mail_and_shield_audit_matches_expected_ac_hp():
    audit = _audit(
        _doc(
            class_id="fighter",
            level=1,
            scores={"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 10},
            equipment=[_armor("Chain Mail", base_ac=16, armor_type="heavy"), _shield()],
        )
    )

    assert audit["ac"]["value"] == 18
    assert any("Base armour: Chain Mail = 16" in line for line in audit["ac"]["breakdown"])
    assert any("Shield: Shield = +2" in line for line in audit["ac"]["breakdown"])
    assert audit["hp"]["value"] == 12
    assert any("Level 1 Fighter hit die: 10 + Con +2 = 12" in line for line in audit["hp"]["breakdown"])
    assert audit["proficiencyBonus"]["value"] == 2


def test_level_5_bard_with_leather_armour_audit():
    audit = _audit(
        _doc(
            class_id="bard",
            level=5,
            scores={"str": 8, "dex": 16, "con": 14, "int": 10, "wis": 12, "cha": 16},
            equipment=[_armor("Leather Armour", base_ac=11, armor_type="light")],
        )
    )

    assert audit["ac"]["value"] == 14
    assert audit["hp"]["value"] == 38
    assert audit["initiative"]["value"] == 3
    assert audit["proficiencyBonus"]["value"] == 3


def test_level_8_bard_with_studded_leather_audit():
    audit = _audit(
        _doc(
            class_id="bard",
            level=8,
            scores={"str": 8, "dex": 16, "con": 14, "int": 10, "wis": 12, "cha": 16},
            equipment=[_armor("Studded Leather", base_ac=12, armor_type="light")],
        )
    )

    assert audit["ac"]["value"] == 15
    assert audit["hp"]["value"] == 59
    assert any("Levels 2-8 Bard average gain: 5 + Con +2 = 7 per level (49)" in line for line in audit["hp"]["breakdown"])


def test_level_8_bard_with_equipped_shield_audit_includes_shield_bonus():
    audit = _audit(
        _doc(
            class_id="bard",
            level=8,
            scores={"str": 8, "dex": 16, "con": 14, "int": 10, "wis": 12, "cha": 16},
            equipment=[_armor("Studded Leather", base_ac=12, armor_type="light"), _shield()],
        )
    )

    assert audit["ac"]["value"] == 17
    assert audit["equippedShield"]["name"] == "Shield"
    assert {bonus["type"] for bonus in audit["activeBonuses"]} >= {"shield_ac_bonus"}


def test_level_5_monk_unarmoured_audit_uses_wisdom_defense():
    audit = _audit(
        _doc(
            class_id="monk",
            level=5,
            scores={"str": 10, "dex": 16, "con": 12, "int": 10, "wis": 16, "cha": 8},
        )
    )

    assert audit["ac"]["value"] == 16
    assert audit["hp"]["value"] == 33
    assert any("Monk Unarmored Defense" in line for line in audit["ac"]["breakdown"])


def test_level_5_barbarian_unarmoured_audit_uses_constitution_defense():
    audit = _audit(
        _doc(
            class_id="barbarian",
            level=5,
            scores={"str": 16, "dex": 14, "con": 16, "int": 8, "wis": 10, "cha": 8},
        )
    )

    assert audit["ac"]["value"] == 15
    assert audit["hp"]["value"] == 55
    assert any("Barbarian Unarmored Defense" in line for line in audit["ac"]["breakdown"])


def test_spellcaster_audit_includes_spell_save_dc_and_spell_attack_bonus():
    audit = _audit(
        _doc(
            class_id="wizard",
            level=5,
            scores={"str": 8, "dex": 14, "con": 14, "int": 16, "wis": 12, "cha": 10},
        )
    )

    assert audit["spellSaveDC"]["value"] == 14
    assert audit["spellAttackBonus"]["value"] == 6
    assert any("8 + proficiency +3 + INT +3 = 14" in line for line in audit["spellSaveDC"]["breakdown"])


def test_character_audit_warns_for_unknown_or_missing_calculation_inputs():
    doc = _doc(
        class_id="mystery-class",
        level=3,
        scores={"str": 10, "dex": 14, "con": 12, "int": 10, "wis": 10, "cha": 10},
        equipment=[
            {"id": "odd-mail", "name": "Odd Mail", "equipment_kind": "armor", "kind": "armor", "equipped": True},
            _shield("Ancient Shield", ac_bonus=None),
            {"id": "custom-ring", "name": "Custom Ring", "equipment_kind": "gear", "kind": "gear", "equipped": True, "attuned": True, "category": "Magic Item", "custom": True},
        ],
    )
    doc["species"] = {"id": "", "name": "", "traits": []}
    doc["feats"] = [{"featId": "homebrew-feat", "name": "Homebrew Feat"}]
    doc["spellState"]["spellbookEntries"] = [{"id": "homebrew-spell", "name": "Homebrew Spell", "matchedNative": False}]

    audit = _audit(doc)
    warning_codes = {warning["code"] for warning in audit["warnings"]}

    assert "unknown_armor" in warning_codes
    assert "unknown_shield" in warning_codes
    assert "unknown_magic_item_bonus" in warning_codes
    assert "unknown_custom_dndbeyond_modifier" in warning_codes
    assert "missing_class_hit_die" in warning_codes
    assert "missing_species_race_feature" in warning_codes
    assert "missing_feat" in warning_codes
    assert "missing_spell" in warning_codes
    assert audit["missingData"]


def test_character_audit_warns_when_subclass_features_are_due_but_missing():
    audit = _audit(
        _doc(
            class_id="fighter",
            level=5,
            scores={"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 10},
            equipment=[_armor("Chain Mail", base_ac=16, armor_type="heavy")],
        )
    )

    assert any(warning["code"] == "missing_subclass_feature" for warning in audit["warnings"])
