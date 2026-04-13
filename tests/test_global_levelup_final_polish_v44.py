from pathlib import Path


def test_levelup_modal_contains_final_polish_markers():
    text = Path('client/static/js/character/library/character_levelup_modal.js').read_text()
    assert 'lvlup-selected-chip' in text
    assert 'What changes immediately after confirm' in text
    assert 'lvlup-confirm-grid' in text
    assert 'lvlup-step-button' in text
