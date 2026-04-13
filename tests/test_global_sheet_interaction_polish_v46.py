from pathlib import Path


def test_sheet_interaction_polish_markers_present():
    root = Path(__file__).resolve().parents[1]
    actions_js = (root / 'client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    spells_js = (root / 'client/static/js/character/tabs/spells_tab.js').read_text(encoding='utf-8')
    features_js = (root / 'client/static/js/character/tabs/features_tab.js').read_text(encoding='utf-8')
    sheet_js = (root / 'client/static/js/character/character_sheet_container.js').read_text(encoding='utf-8')
    css = (root / 'client/static/css/character-sheet-premium.css').read_text(encoding='utf-8')

    assert 'data-map-panel-open=\"combat\"' in actions_js
    assert 'data-map-panel-open="spelllib"' in spells_js
    assert 'openMapPanelFromSheet' in sheet_js
    assert 'cs-row-pulse' in css
    assert "querySelectorAll('.cs-feature-item.open')" in features_js
