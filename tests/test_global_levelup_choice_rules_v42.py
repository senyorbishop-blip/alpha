from pathlib import Path


def test_levelup_modal_has_choice_rule_guidance():
    text = Path('client/static/js/character/library/character_levelup_modal.js').read_text(encoding='utf-8')
    for marker in [
        'Choice Rules',
        'Subclass Choice Rule',
        'Fighting Style Rule',
        'Maneuver Choice Rule',
        'Invocation Choice Rule',
        'Metamagic Choice Rule',
        'Spell Swap Rule',
        'Spell Pick Rule',
        'This is a subclass-defining choice. Expect it to shape the rest of the build.',
        'These rules explain what kind of choice you are making now and what to look for before you confirm.',
    ]:
        assert marker in text
