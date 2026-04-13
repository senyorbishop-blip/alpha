from pathlib import Path


def test_levelup_modal_has_deeper_choice_and_spell_guidance():
    text = Path('client/static/js/character/library/character_levelup_modal.js').read_text(encoding='utf-8')
    for marker in [
        'Barbarian Choice Coach',
        'Prepared Caster Guidance',
        'Spellbook Guidance',
        'Known Spell Guidance',
        'Learned Spell Guidance',
        'What this means for your character',
        'Use this step to choose the upgrades that actually change how your turns feel.',
        'Pick the version that best matches the way this character already fights, supports, or survives.',
    ]:
        assert marker in text
