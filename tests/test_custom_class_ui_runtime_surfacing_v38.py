from pathlib import Path


def test_features_tab_has_custom_class_guides():
    text = Path('client/static/js/character/tabs/features_tab.js').read_text(encoding='utf-8')
    assert 'Tinker Surface Guide' in text
    assert 'Pirate Surface Guide' in text
    assert '_renderCustomClassGuide' in text


def test_actions_tab_surfaces_custom_resources_and_callouts():
    text = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    assert 'Tinker Combat Surface' in text
    assert 'Pirate Combat Surface' in text
    assert '_featureResourceRows' in text
    assert text.count("${_renderResourceSection(resources)}") == 1


def test_levelup_modal_has_custom_class_focus_guides():
    text = Path('client/static/js/character/library/character_levelup_modal.js').read_text(encoding='utf-8')
    assert 'Tinker Level-Up Focus' in text
    assert 'Pirate Level-Up Focus' in text
    assert 'classGuide(preview)' in text
