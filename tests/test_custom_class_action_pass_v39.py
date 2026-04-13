from pathlib import Path


def test_actions_tab_includes_custom_class_action_registry():
    text = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    assert 'const CUSTOM_CLASS_ACTIONS = {' in text
    assert 'Quick Deployment' in text
    assert 'Overclocked Device' in text
    assert 'Dirty Fighting' in text
    assert 'Boarding Action' in text


def test_actions_tab_builds_custom_class_action_cards():
    text = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    assert 'function _buildCustomClassActionCards(charData)' in text
    assert 'const custom = _buildCustomClassActionCards(charData);' in text


def test_actions_tab_uses_custom_labels_for_swagger_and_gadgets():
    text = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    assert "return 'Spend Swagger';" in text
    assert "return 'Use Device';" in text


def test_actions_tab_has_better_use_toast_fallback():
    text = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    assert 'triggered' in text
