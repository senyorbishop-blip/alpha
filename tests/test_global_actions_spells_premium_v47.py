from pathlib import Path


def test_actions_and_spells_premium_strings_present():
    root = Path(__file__).resolve().parents[1]
    actions = (root / 'client/static/js/character/tabs/actions_tab.js').read_text()
    spells = (root / 'client/static/js/character/tabs/spells_tab.js').read_text()
    css = (root / 'client/static/css/character-sheet-premium.css').read_text()

    assert 'cs-action-lanes' in actions
    assert 'Usable now' in actions
    assert 'cs-spell-lanes' in spells
    assert 'Use now' in spells
    assert 'Stage 47: global actions + spells premium card pass' in css
