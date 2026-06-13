"""Tests for prepared caster (Druid/Cleric/Paladin) import spell filtering."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest


def _make_ddb_payload(class_name, prepared_spells, known_spells):
    class_level_spells = []
    for name in prepared_spells:
        class_level_spells.append({"definition": {"name": name}, "prepared": True, "alwaysPrepared": False})
    for name in known_spells:
        class_level_spells.append({"definition": {"name": name}, "prepared": False, "alwaysPrepared": False})
    return {
        "data": {
            "id": f"test-{class_name.lower()}-1",
            "name": f"Test {class_name}",
            "classes": [{"definition": {"name": class_name}, "level": 3}],
            "stats": [{"id": i, "value": 10} for i in range(1, 7)],
            "bonusStats": [], "overrideStats": [],
            "spells": {"1": class_level_spells},
            "currencies": {},
            "race": {"baseName": "Human", "fullName": "Human", "weightSpeeds": {"normal": {"walk": 30}}},
            "background": {"definition": {"name": "Acolyte"}},
        }
    }


def test_druid_prepared_spells_in_prepared_list():
    from server.character.import_normalizer import normalize_ddb_json_payload
    payload = _make_ddb_payload("Druid", ["Cure Wounds", "Entangle"], ["Faerie Fire"])
    result = normalize_ddb_json_payload(payload)
    spell_state = result["document"].get("spellState", {})
    prepared = [p.lower() for p in spell_state.get("prepared", [])]
    assert any("cure" in p or "entangle" in p for p in prepared), \
        f"Prepared spells should be in prepared list; got: {prepared}"


def test_druid_all_spells_preserved_in_spellbook_entries():
    from server.character.import_normalizer import normalize_ddb_json_payload
    payload = _make_ddb_payload("Druid", ["Cure Wounds"], ["Faerie Fire"])
    result = normalize_ddb_json_payload(payload)
    spell_state = result["document"].get("spellState", {})
    entries = spell_state.get("spellbookEntries", [])
    all_names = [str(e.get("name") or "").lower() for e in entries]
    assert any("cure" in n or "faerie" in n for n in all_names), \
        f"All imported spells should be preserved in spellbookEntries; got: {all_names}"


def test_sorcerer_known_caster_all_spells_in_known():
    from server.character.import_normalizer import normalize_ddb_json_payload
    payload = _make_ddb_payload("Sorcerer", [], ["Burning Hands", "Chromatic Orb"])
    result = normalize_ddb_json_payload(payload)
    spell_state = result["document"].get("spellState", {})
    known = spell_state.get("known", [])
    assert len(known) >= 1, f"Known caster should have spells in known list; got: {known}"


def test_rules_engine_prepared_flag_in_spell_card():
    """rules_engine.enrich_spellbook must propagate the prepared flag to cards."""
    from server.rules_engine import enrich_spellbook
    character = {
        "book": {"spellAbility": "WIS", "spellAttack": "+5", "spellSaveDc": "13"},
        "classes": [{"name": "Druid", "level": 3}],
        "stats": [10, 10, 10, 10, 14, 10],
        "spellbookEntries": [
            {"name": "Cure Wounds", "prepared": True, "id": "cure-wounds"},
            {"name": "Entangle", "prepared": False, "id": "entangle"},
        ],
    }
    from server.character.spell_compendium import get_spell_list
    official = []
    for s in get_spell_list():
        if s.get("name") in {"Cure Wounds", "Entangle"}:
            official.append({
                "id": s["id"], "name": s["name"], "spell_level": s["level"],
                "school": s.get("school",""), "base_damage_formula": s.get("damageFormula",""),
                "base_effect_text": s.get("description",""), "scaling_type": "none",
                "scaling_data": {}, "tags": [], "class_lists": [],
            })
    result = enrich_spellbook(character, official, [])
    cards = result.get("spell_cards", [])
    cure_card = next((c for c in cards if "cure" in (c.get("name") or "").lower()), None)
    if cure_card:
        assert cure_card.get("prepared") is True, \
            f"Cure Wounds should be prepared=True; got {cure_card.get('prepared')}"
    meta = result.get("spellcasting", {})
    assert "isPreparedCaster" in meta, "spellcasting meta must include isPreparedCaster"
    assert meta.get("isPreparedCaster") is True, "Druid is a prepared caster"


def test_spellcasting_meta_has_prepared_caster_flag():
    """_spellcasting_meta must return isPreparedCaster and preparedSpellIds."""
    from server.rules_engine import _spellcasting_meta
    character = {
        "classes": [{"name": "Druid", "level": 3}],
        "book": {"spellAbility": "WIS", "spellAttack": "+5", "spellSaveDc": "13"},
        "stats": [10, 10, 10, 10, 14, 10],
        "spellbookEntries": [
            {"name": "Cure Wounds", "prepared": True, "id": "cure-wounds"},
        ],
    }
    meta = _spellcasting_meta(character)
    assert meta.get("isPreparedCaster") is True
    assert "preparedSpellIds" in meta
    assert isinstance(meta["preparedSpellIds"], list)


def test_prepared_caster_filter_in_play_html():
    """play.html _getCombatQuickSpells must filter non-prepared spells for prepared casters."""
    with open("client/templates/play.html") as f:
        src = f.read()
    assert "_cqaIsPreparedCaster" in src, "Must have prepared caster check in _getCombatQuickSpells"
    assert "isPreparedCaster" in src, "Must reference isPreparedCaster from rulesMeta"
    assert "preparedSpellIds" in src, "Must use preparedSpellIds for filter"
