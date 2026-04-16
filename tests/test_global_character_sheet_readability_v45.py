from pathlib import Path


def test_v45_readability_markers_present():
    base = Path(__file__).resolve().parents[1]
    features = (base / "client/static/js/character/tabs/features_tab.js").read_text()
    actions = (base / "client/static/js/character/tabs/actions_tab.js").read_text()
    spells = (base / "client/static/js/character/tabs/spells_tab.js").read_text()
    css = (base / "client/static/css/character-sheet-premium.css").read_text()

    assert "short rules summary" in features
    assert "cs-action-kicker" in actions
    assert "cs-spell-kicker" in spells
    assert "Stage 45: global character sheet readability polish" in css
