from pathlib import Path


def test_levelup_modal_has_richer_option_picker_copy():
    text = Path('client/static/js/character/library/character_levelup_modal.js').read_text(encoding='utf-8')
    for marker in [
        'Subclass options',
        'Compare the ',
        'Pick now, unlock later:',
        'Fantasy',
        'Best fit now',
        'Unlocks later',
        'lvlup-option-card',
        'life domain',
        'battle master',
        'archery',
    ]:
        assert marker in text
