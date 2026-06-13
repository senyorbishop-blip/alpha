"""Tests for spell catalog completeness requirements."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest


def test_spell_catalog_loads():
    from server.character.spell_compendium import get_spell_list
    spells = get_spell_list()
    assert len(spells) > 50, "Spell catalog should have more than 50 spells"


def test_all_spells_have_id_name_level():
    from server.character.spell_compendium import get_spell_list
    spells = get_spell_list()
    for spell in spells:
        assert spell.get("id"), f"Spell missing id: {spell}"
        assert spell.get("name"), f"Spell missing name: {spell.get('id')}"
        assert isinstance(spell.get("level"), int), \
            f"Spell {spell.get('id')} level must be int, got {type(spell.get('level'))}"


def test_cantrip_is_only_explicit_level_zero():
    from server.character.spell_compendium import get_spell_list
    spells = get_spell_list()
    for spell in spells:
        level = spell.get("level")
        assert level is not None, f"Spell {spell.get('id')} has None level"
        assert isinstance(level, int), f"Spell {spell.get('id')} level must be int"
        if level == 0:
            tags = spell.get("tags") or []
            resource = (spell.get("resourceUsage") or {}).get("kind")
            assert "cantrip" in tags or resource == "cantrip", \
                f"Level-0 spell {spell.get('id')} should be tagged as cantrip"
        else:
            assert 1 <= level <= 9, f"Spell {spell.get('id')} level {level} out of range"


def test_no_spell_has_missing_level_shows_as_cantrip():
    from server.character.spell_compendium import get_spell_list
    spells = get_spell_list()
    cantrips = [s for s in spells if s.get("level") == 0]
    non_cantrips = [s for s in spells if s.get("level") != 0]
    assert len(cantrips) >= 5, "Should have at least 5 cantrips"
    assert len(non_cantrips) > 20, "Should have at least 20 non-cantrip spells"


def test_unknown_spell_level_not_treated_as_cantrip_in_quick_actions():
    """_levelLabel(null) must return 'Unknown spell level', not 'Cantrip'."""
    import re
    with open("client/static/js/character/combat_quick_actions.js") as f:
        src = f.read()
    assert "Unknown spell level" in src, "Must have 'Unknown spell level' label"
    # Find the _levelLabel function
    label_fn = re.search(r"function _levelLabel\(level\)\s*\{(.+?)\}", src, re.DOTALL)
    assert label_fn, "_levelLabel function must exist"
    body = label_fn.group(1)
    # Must have null/undefined check that returns 'Unknown spell level'
    assert "Unknown spell level" in body, "_levelLabel body must have 'Unknown spell level'"
    # The null/undefined check must happen (return 'Unknown') before any 'Cantrip' label is returned
    # Find the return statement for unknown level vs return for cantrip
    unknown_return = re.search(r"return ['\"]Unknown spell level['\"]", body)
    cantrip_return = re.search(r"return.*Cantrip", body)
    assert unknown_return, "Must return 'Unknown spell level' somewhere in _levelLabel"
    assert cantrip_return, "Must return 'Cantrip' for level 0"
    assert unknown_return.start() < cantrip_return.start(), \
        "null/unknown check must come before cantrip return in _levelLabel"


def test_spell_level_fallback_not_zero_in_play_html():
    """In play.html spell library render, missing level must not default to 0."""
    with open("client/templates/play.html") as f:
        src = f.read()
    # The fixed pattern uses null instead of ?? 0
    buggy = "s.spell_level ?? 0)"
    assert buggy not in src, "Must not default spell_level to 0 (Cantrip) when level unknown"
