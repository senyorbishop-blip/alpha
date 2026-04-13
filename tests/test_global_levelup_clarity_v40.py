from pathlib import Path


def test_levelup_modal_has_global_class_guides_and_review_layout():
    text = Path('client/static/js/character/library/character_levelup_modal.js').read_text(encoding='utf-8')
    for marker in [
        'Barbarian Level-Up Focus',
        'Bard Level-Up Focus',
        'Cleric Level-Up Focus',
        'Druid Level-Up Focus',
        'Fighter Level-Up Focus',
        'Monk Level-Up Focus',
        'Paladin Level-Up Focus',
        'Ranger Level-Up Focus',
        'Rogue Level-Up Focus',
        'Sorcerer Level-Up Focus',
        'Warlock Level-Up Focus',
        'Wizard Level-Up Focus',
        'Tinker Level-Up Focus',
        'Pirate Level-Up Focus',
        'Choices still tracked',
        'Automatic gains',
        'Spell plan',
        'Guided Flow',
    ]:
        assert marker in text
