from collections import Counter

from server.rules_content import OPEN_5E_SPELLS


def _get_spell(spell_id: str) -> dict:
    for spell in OPEN_5E_SPELLS:
        if spell.get("id") == spell_id:
            return spell
    raise KeyError(spell_id)


def test_spell_catalog_count_expanded_beyond_previous_baseline():
    assert len(OPEN_5E_SPELLS) >= 168


def test_class_list_counts_are_deeper_for_primary_casters_and_support_lists():
    counts = Counter()
    for spell in OPEN_5E_SPELLS:
        for class_name in spell.get("class_lists") or []:
            counts[class_name] += 1

    assert counts["Wizard"] >= 86
    assert counts["Sorcerer"] >= 69
    assert counts["Druid"] >= 62
    assert counts["Bard"] >= 59
    assert counts["Cleric"] >= 58
    assert counts["Ranger"] >= 35
    assert counts["Warlock"] >= 37


def test_new_wizard_and_arcane_support_spells_are_present():
    identify = _get_spell("spell_identify")
    familiar = _get_spell("spell_find_familiar")
    chromatic_orb = _get_spell("spell_chromatic_orb")
    telekinesis = _get_spell("spell_telekinesis")

    assert identify.get("ritual") is True
    assert identify.get("class_lists") == ["Wizard", "Bard", "Artificer"]
    assert familiar.get("ritual") is True
    assert familiar.get("class_lists") == ["Wizard"]
    assert chromatic_orb.get("attack_type") == "ranged_spell_attack"
    assert "Wizard" in (telekinesis.get("class_lists") or [])


def test_new_divine_and_primal_depth_spells_are_present():
    moonbeam = _get_spell("spell_moonbeam")
    call_lightning = _get_spell("spell_call_lightning")
    commune = _get_spell("spell_commune")
    greater_restoration = _get_spell("spell_greater_restoration")

    assert moonbeam.get("concentration") is True
    assert moonbeam.get("save_ability") == "con"
    assert call_lightning.get("damage_type") == "lightning"
    assert commune.get("ritual") is True
    assert "Cleric" in (commune.get("class_lists") or [])
    assert "Druid" in (greater_restoration.get("class_lists") or [])


def test_new_stealth_social_and_party_support_spells_are_present():
    faerie_fire = _get_spell("spell_faerie_fire")
    friends = _get_spell("spell_friends")
    tiny_hut = _get_spell("spell_leomunds_tiny_hut")
    seeming = _get_spell("spell_seeming")

    assert faerie_fire.get("concentration") is True
    assert "Bard" in (faerie_fire.get("class_lists") or [])
    assert "Warlock" in (friends.get("class_lists") or [])
    assert tiny_hut.get("ritual") is True
    assert "Wizard" in (tiny_hut.get("class_lists") or [])
    assert "Bard" in (seeming.get("class_lists") or [])
