from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_features_playbook_covers_live_classes_including_custom():
    src = _read("client/static/js/character/tabs/features_tab.js")
    for key in [
        "barbarian",
        "bard",
        "cleric",
        "druid",
        "fighter",
        "monk",
        "paladin",
        "ranger",
        "rogue",
        "sorcerer",
        "warlock",
        "wizard",
        "tinker",
        "pirate",
    ]:
        assert f"{key}: {{" in src


def test_actions_tab_surfaces_barbarian_and_wizard_loops():
    src = _read("client/static/js/character/tabs/actions_tab.js")
    assert "Barbarian Combat Surface" in src
    assert "Wizard Combat Surface" in src
    for snippet in [
        "name: 'Rage'",
        "name: 'Reckless Attack'",
        "name: 'Arcane Recovery'",
        "name: 'Ritual Casting'",
    ]:
        assert snippet in src


def test_spells_tab_has_class_spell_model_hints():
    src = _read("client/static/js/character/tabs/spells_tab.js")
    assert "function _classSpellModelInsights(" in src
    for snippet in [
        "Warlock flow: use at-will cantrips between pact-slot spikes",
        "Druid flow: prepared spellcasting and Wild Shape are separate lanes",
        "Cleric flow: prepared spells handle most turns",
        "Wizard flow: prepare your daily toolkit from your spellbook",
        "Half-caster flow: slot tiers arrive slower than full casters",
        "Tinker flow: treat specialty spells as part of your gadget loop",
    ]:
        assert snippet in src
