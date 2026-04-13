from server.character.progression import build_levelup_preview, apply_levelup


def test_levelup_preview_includes_required_spell_picks_for_sorcerer_growth():
    document = {
        'identity': {'name': 'Bishop'},
        'classes': [{'classId': 'sorcerer', 'level': 3, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 20, 'con': 13}},
        'spellState': {
            'known': [
                'fire-bolt', 'mage-hand', 'message', 'minor-illusion',
                'magic-missile', 'shield', 'scorching-ray',
            ],
            'prepared': [],
        },
    }

    preview = build_levelup_preview(document)

    assert preview['nextLevel'] == 4
    assert isinstance(preview.get('spellChoices'), dict)
    assert preview['spellChoices']['mode'] == 'known'
    assert preview['spellChoices']['cantripPicksRequired'] == 1
    assert preview['spellChoices']['levelledPicksRequired'] == 1
    assert any(row['type'] == 'spell_cantrips' for row in preview['requiredChoices'])
    assert any(row['type'] == 'spell_levelled' for row in preview['requiredChoices'])
    assert any(option['id'] == 'friends' for option in preview['spellChoices']['cantripOptions'])
    assert any(option['id'] == 'misty-step' for option in preview['spellChoices']['levelledOptions'])


def test_apply_levelup_persists_required_spell_picks_for_sorcerer():
    document = {
        'identity': {'name': 'Bishop'},
        'classes': [{'classId': 'sorcerer', 'level': 3, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 20, 'con': 13}},
        'spellState': {
            'known': [
                'fire-bolt', 'mage-hand', 'message', 'minor-illusion',
                'magic-missile', 'shield', 'scorching-ray',
            ],
            'prepared': [],
        },
    }

    applied = apply_levelup(
        document,
        choices={
            'asiChoice': {'mode': 'plus2', 'ability': 'cha'},
            'spellChoices': {
                'cantripAdds': ['friends'],
                'levelledAdds': ['misty-step'],
                'swap': {},
            }
        },
    )
    native = applied['document']

    assert native['classes'][0]['level'] == 4
    assert 'friends' in native['spellState']['known']
    assert 'misty-step' in native['spellState']['known']
    assert applied['meta']['engine'] == 'character.levelup.apply.v3'


def test_levelup_preview_surfaces_optional_spell_swap_when_no_new_pick_is_required():
    document = {
        'identity': {'name': 'Bishop'},
        'classes': [{'classId': 'sorcerer', 'level': 4, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 20, 'con': 13}},
        'spellState': {
            'known': [
                'fire-bolt', 'mage-hand', 'message', 'minor-illusion', 'friends',
                'magic-missile', 'shield', 'scorching-ray', 'misty-step',
            ],
            'prepared': [],
        },
    }

    preview = build_levelup_preview(document)

    assert preview['nextLevel'] == 5
    assert isinstance(preview.get('spellChoices'), dict)
    assert preview['spellChoices']['swapAllowed'] is True
    assert preview['spellChoices']['cantripPicksRequired'] == 0
    assert preview['spellChoices']['levelledPicksRequired'] == 0
    assert preview['requiresChoices'] is False


def test_levelup_preview_caps_spell_options_to_new_highest_spell_tier():
    document = {
        'identity': {'name': 'Bishop'},
        'classes': [{'classId': 'sorcerer', 'level': 3, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 20, 'con': 13}},
        'spellState': {
            'known': [
                'fire-bolt', 'mage-hand', 'message', 'minor-illusion',
                'magic-missile', 'shield', 'scorching-ray',
            ],
            'prepared': [],
        },
    }

    preview = build_levelup_preview(document)
    spell_choices = preview['spellChoices']

    assert spell_choices['nextHighestSpellLevel'] == 2
    assert spell_choices['currentHighestSpellLevel'] == 2
    assert all(option['level'] <= 2 for option in spell_choices['levelledOptions'])


def test_apply_levelup_rejects_using_swap_for_newly_added_spell():
    document = {
        'identity': {'name': 'Bishop'},
        'classes': [{'classId': 'sorcerer', 'level': 3, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 20, 'con': 13}},
        'spellState': {
            'known': [
                'fire-bolt', 'mage-hand', 'message', 'minor-illusion',
                'magic-missile', 'shield', 'scorching-ray',
            ],
            'prepared': [],
        },
    }

    try:
        apply_levelup(
            document,
            choices={
                'asiChoice': {'mode': 'plus2', 'ability': 'cha'},
                'spellChoices': {
                    'cantripAdds': ['friends'],
                    'levelledAdds': ['misty-step'],
                    'swap': {'drop': 'shield', 'learn': 'misty-step'},
                }
            },
        )
        assert False, 'Expected level-up apply to reject duplicate swap learn.'
    except Exception as exc:
        assert 'optional swap' in str(exc).lower() or 'already picked' in str(exc).lower()


def test_levelup_preview_uses_spellbook_entries_as_current_spell_state_when_lists_are_empty():
    document = {
        'identity': {'name': 'Bishop'},
        'classes': [{'classId': 'sorcerer', 'level': 4, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 20, 'con': 13}},
        'spellState': {
            'known': [],
            'prepared': [],
            'spellbookEntries': [
                {'name': 'Fire Bolt'}, {'name': 'Mage Hand'}, {'name': 'Message'}, {'name': 'Minor Illusion'}, {'name': 'Friends'},
                {'name': 'Magic Missile'}, {'name': 'Shield'}, {'name': 'Scorching Ray'}, {'name': 'Misty Step'},
            ],
        },
    }

    preview = build_levelup_preview(document)

    assert preview['nextLevel'] == 5
    assert preview['spellChoices']['cantripPicksRequired'] == 0
    assert preview['spellChoices']['levelledPicksRequired'] == 0
    assert preview['spellChoices']['swapAllowed'] is True
