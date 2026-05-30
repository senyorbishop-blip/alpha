from server.character.spell_compendium import (
    build_spell_limits_for_class,
    get_spell_by_id,
    list_spells,
    validate_spell_selection,
)


def test_spell_entry_is_deeply_normalized():
    spell = get_spell_by_id('magic-missile') or get_spell_by_id('magic_missile') or get_spell_by_id('magic missile')
    assert spell is not None
    assert spell['name']
    assert 'classes' in spell and isinstance(spell['classes'], list)
    assert 'classUnlockLevels' in spell and isinstance(spell['classUnlockLevels'], dict)
    assert 'rollButtonConfig' in spell and isinstance(spell['rollButtonConfig'], dict)
    assert 'fullPlayerDetailText' in spell


def test_class_spell_unlocks_are_exposed_on_library_rows():
    rows = list_spells(level=1, cls='Wizard')
    assert rows
    assert any('wizard' in row.get('classUnlockLevels', {}) for row in rows)


def test_prepared_spell_validation_blocks_cantrips_and_over_limit():
    result = validate_spell_selection(
        class_id='wizard',
        class_level=1,
        abilities={'scores': {'int': 16}},
        known=['fire-bolt', 'ray-of-frost', 'mage-hand', 'minor-illusion'],
        prepared=['fire-bolt'],
    )
    assert result['ok'] is False
    assert any('cantrip' in err.lower() for err in result['errors'])


def test_known_spell_validation_respects_known_limits_for_known_casters():
    limits = build_spell_limits_for_class('bard', 1, {'scores': {'cha': 16}})
    assert limits['spellsKnown'] == 4
    result = validate_spell_selection(
        class_id='bard',
        class_level=1,
        abilities={'scores': {'cha': 16}},
        known=['fire-bolt', 'light', 'vicious-mockery', 'friends', 'healing-word'],
        prepared=[],
    )
    assert result['ok'] is False
    assert any('limit exceeded' in err.lower() for err in result['errors'])


def test_open_spell_metadata_wins_over_placeholder_catalog_rows():
    spell = get_spell_by_id('hold-person')
    assert spell is not None
    assert spell['school'] == 'Enchantment'
    assert spell['range'] == '60 feet'
    assert spell['duration'] == 'Up to 1 minute'
    assert spell['savingThrow'] == 'WIS'
    assert spell['damageFormula'] == ''


def test_utility_spells_do_not_get_fake_attack_or_damage_data():
    spell = get_spell_by_id('guidance')
    assert spell is not None
    assert spell['attackType'] == ''
    assert spell['savingThrow'] == ''
    assert spell['damageFormula'] == ''
    assert spell['school'] == 'Divination'
    assert '+1d4' in (spell.get('effect') or '')


def test_stage4c_blink_uses_real_player_facing_metadata():
    spell = get_spell_by_id('blink')
    assert spell is not None
    assert spell['school'] == 'Transmutation'
    assert spell['range'] == 'Self'
    assert spell['duration'] == '1 minute'
    assert 'phase' in (spell.get('effect') or '').lower()
    assert 'wizard' in [c.lower() for c in spell.get('classes') or []]


def test_stage4c_call_lightning_is_not_placeholder_touch_abjuration_anymore():
    spell = get_spell_by_id('call-lightning')
    assert spell is not None
    assert spell['school'] == 'Conjuration'
    assert spell['range'] == '120 feet'
    assert spell['duration'] == 'Up to 10 minutes'
    assert spell['concentration'] is True
    assert spell['savingThrow'] == 'DEX'
    assert spell['damageFormula'] == '3d10'


def test_stage4c_hypnotic_pattern_and_slow_have_real_control_text():
    hypnotic = get_spell_by_id('hypnotic-pattern')
    slow = get_spell_by_id('slow')
    assert hypnotic is not None and slow is not None
    assert hypnotic['school'] == 'Illusion'
    assert hypnotic['savingThrow'] == 'WIS'
    assert 'incapac' in (hypnotic.get('fullPlayerDetailText') or '').lower()
    assert slow['school'] == 'Transmutation'
    assert slow['concentration'] is True
    assert 'sluggish' in (slow.get('fullPlayerDetailText') or '').lower()


def test_stage4c_water_exploration_spells_have_real_ritual_and_duration_data():
    breathing = get_spell_by_id('water-breathing')
    walk = get_spell_by_id('water-walk')
    assert breathing is not None and walk is not None
    assert breathing['ritual'] is True
    assert breathing['duration'] == '24 hours'
    assert breathing['range'] == '30 feet'
    assert walk['ritual'] is True
    assert walk['duration'] == '1 hour'
    assert 'solid ground' in (walk.get('fullPlayerDetailText') or '').lower()



def test_stage4d_all_4th_and_5th_level_spells_have_player_facing_text():
    for level in (4, 5):
        rows = list_spells(level=level)
        assert rows
        for row in rows:
            detail = (row.get("fullPlayerDetailText") or "").lower()
            assert "spell data entry for the 5e2024 rules catalog" not in detail
            assert len(detail.strip()) > 80


def test_stage4d_arcane_eye_and_wall_of_force_have_real_metadata():
    eye = get_spell_by_id('arcane-eye')
    wall = get_spell_by_id('wall-of-force')
    assert eye is not None and wall is not None
    assert eye['school'] == 'Divination'
    assert eye['range'] == '30 feet'
    assert eye['duration'] == 'Up to 1 hour'
    assert eye['concentration'] is True
    assert 'scouting eye' in (eye.get('effect') or '').lower()
    assert wall['school'] == 'Evocation'
    assert wall['range'] == '120 feet'
    assert wall['duration'] == 'Up to 10 minutes'
    assert wall['concentration'] is True
    assert 'barrier' in ((wall.get('effect') or '') + ' ' + (wall.get('fullPlayerDetailText') or '')).lower()


def test_stage4d_cloudkill_and_greater_restoration_cover_damage_and_support_lanes():
    cloudkill = get_spell_by_id('cloudkill')
    restoration = get_spell_by_id('greater-restoration')
    assert cloudkill is not None and restoration is not None
    assert cloudkill['savingThrow'] == 'CON'
    assert cloudkill['damageFormula'] == '5d8'
    assert cloudkill['concentration'] is True
    assert 'poison cloud' in ((cloudkill.get('effect') or '') + ' ' + (cloudkill.get('fullPlayerDetailText') or '')).lower()
    assert restoration['attackType'] == ''
    assert restoration['savingThrow'] == ''
    assert restoration['damageFormula'] == ''
    assert 'severe condition' in (restoration.get('effect') or '').lower()


def test_stage4e_all_6th_to_9th_level_spells_have_authored_player_facing_text():
    for level in (6, 7, 8, 9):
        rows = list_spells(level=level)
        assert rows
        for row in rows:
            detail = (row.get("fullPlayerDetailText") or "").lower()
            assert "spell data entry for the 5e2024 rules catalog" not in detail
            assert len(detail.strip()) > 120
            assert row.get("effect")
            assert not str(row.get("effect") or "").startswith("Level ")


def test_stage4e_marquee_high_level_spells_have_real_effects_and_details():
    heal = get_spell_by_id('heal')
    forcecage = get_spell_by_id('forcecage')
    maze = get_spell_by_id('maze')
    gate = get_spell_by_id('gate')
    time_stop = get_spell_by_id('time-stop')
    mass_heal = get_spell_by_id('mass-heal')
    assert all([heal, forcecage, maze, gate, time_stop, mass_heal])

    assert heal['healingFormula'] == '70 hit points'
    assert 'condition' in ((heal.get('effect') or '') + ' ' + (heal.get('fullPlayerDetailText') or '')).lower()

    assert 'prison' in ((forcecage.get('effect') or '') + ' ' + (forcecage.get('fullPlayerDetailText') or '')).lower()
    assert forcecage['concentration'] is False

    assert 'labyrinth' in ((maze.get('effect') or '') + ' ' + (maze.get('fullPlayerDetailText') or '')).lower()
    assert maze['concentration'] is True

    assert 'portal' in ((gate.get('effect') or '') + ' ' + (gate.get('fullPlayerDetailText') or '')).lower()
    assert gate['concentration'] is True

    assert 'normal flow of turns' in (time_stop.get('fullPlayerDetailText') or '').lower()
    assert 'setup' in (time_stop.get('fullPlayerDetailText') or '').lower()

    assert mass_heal['healingFormula'] == 'Up to 700 hit points divided among creatures'
    assert 'reset button' in (mass_heal.get('fullPlayerDetailText') or '').lower()


def test_build_character_spell_manifest_falls_back_to_spellbook_entries_when_spell_state_is_empty():
    from server.character.spell_compendium import build_character_spell_manifest

    document = {
        'classes': [{'classId': 'sorcerer', 'level': 4, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 18}},
        'spellState': {
            'known': [],
            'prepared': [],
            'spellbookEntries': [
                {'name': 'Fire Bolt'},
                {'name': 'Mage Hand'},
                {'name': 'Message'},
                {'name': 'Minor Illusion'},
                {'name': 'Magic Missile'},
                {'name': 'Shield'},
                {'name': 'Scorching Ray'},
                {'name': 'Misty Step'},
            ],
        },
    }

    manifest = build_character_spell_manifest(document)

    assert 'fire-bolt' in manifest['known']
    assert 'misty-step' in manifest['known']
    assert any(card['id'] == 'fire-bolt' and card['isKnown'] for card in manifest['cards'])
    assert any(card['id'] == 'misty-step' and card['isKnown'] for card in manifest['cards'])


def test_build_character_spell_manifest_cards_include_cast_level_context():
    from server.character.spell_compendium import build_character_spell_manifest

    document = {
        'classes': [{'classId': 'sorcerer', 'level': 5, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 18}},
        'spellState': {
            'known': ['fire-bolt', 'magic-missile', 'misty-step', 'shield', 'scorching-ray', 'mage-hand'],
            'prepared': [],
        },
    }

    manifest = build_character_spell_manifest(document)
    missile = next(row for row in manifest['cards'] if row['id'] == 'magic-missile')

    assert missile['selectionMode'] == 'known'
    assert missile['highestAvailableSlot'] == 3
    assert missile['availableCastLevels'] == [1, 2, 3]


def test_wizard_spellbook_limit_is_separate_from_prepared_limit():
    from server.character.spell_compendium import build_spell_limits_for_class, validate_spell_selection

    abilities = {"scores": {"int": 16}}
    limits = build_spell_limits_for_class("wizard", 1, abilities)

    assert limits["spellbookSpells"] == 6
    assert limits["preparedLimit"] == 4

    validation = validate_spell_selection(
        class_id="wizard",
        class_level=1,
        abilities=abilities,
        known=["burning-hands", "charm-person", "detect-magic", "disguise-self", "find-familiar", "identify"],
        prepared=["burning-hands", "detect-magic"],
        document={"classes": [{"classId": "wizard", "level": 1}], "spellState": {}},
    )

    assert validation["ok"] is True
    assert len([sid for sid in validation["known"] if sid in {"burning-hands", "charm-person", "detect-magic", "disguise-self", "find-familiar", "identify"}]) == 6


def test_wizard_cannot_prepare_spell_missing_from_spellbook():
    from server.character.spell_compendium import validate_spell_selection

    validation = validate_spell_selection(
        class_id="wizard",
        class_level=1,
        abilities={"scores": {"int": 16}},
        known=["burning-hands"],
        prepared=["burning-hands", "find-familiar"],
        document={"classes": [{"classId": "wizard", "level": 1}], "spellState": {}},
    )

    assert validation["ok"] is False
    assert any("cannot be prepared because it is not known" in err for err in validation["errors"])
