"""Regression coverage for the level-19 Sorcerer "Bishop" import bug.

D&D Beyond / PDF imports of a level 19 Sorcerer can legitimately show 18
known spells and 9 cantrips (e.g. via feats, species, or magic items that
grant additional spells on top of the class list). The app previously
clamped every Sorcerer to the (buggy) internal table of 14 known spells /
6 cantrips, silently disagreeing with the source data and blocking saves.

These tests pin down the fixed behaviour: the internal class table is
still used as a baseline, but an imported character's real spell/cantrip
counts are always preserved (never clamped down), item-granted spells
never count against the class known/cantrip limit, and feat/species
granted spells are tracked separately from the class allotment.
"""
from server.character.spell_compendium import (
    build_spell_limits_for_class,
    resolve_spell_learning_limits,
    validate_spell_selection,
    repair_spell_state_for_document,
    build_character_spell_manifest,
)

CANTRIPS = [
    'acid-splash', 'blade-ward', 'booming-blade', 'chill-touch',
    'control-flames', 'create-bonfire', 'dancing-lights', 'druidcraft',
    'eldritch-blast',
]
LEVELLED = [
    'alarm', 'animal-friendship', 'armor-of-agathys', 'arms-of-hadar',
    'bane', 'bless', 'burning-hands', 'catapult', 'cause-fear',
    'chaos-bolt', 'charm-person', 'chromatic-orb', 'color-spray',
    'command', 'comprehend-languages', 'create-or-destroy-water',
    'cure-wounds', 'meteor-swarm',
]
ITEM_SPELL = 'misty-step'
FEAT_SPELL = 'guidance'


def _bishop_document(*, sorcery_class_id='sorcerer'):
    return {
        'identity': {'name': 'Bishop'},
        'importMeta': {'origin': 'dndbeyond', 'sourceType': 'dndbeyond'},
        'sourceMode': 'dndbeyond',
        'classes': [{'classId': sorcery_class_id, 'level': 19, 'subclassId': 'draconic-bloodline'}],
        'abilities': {'scores': {'cha': 22, 'con': 16}},
        'feats': [
            {'id': 'bishop-feat-1', 'name': 'Magic Initiate', 'spellIds': [FEAT_SPELL]},
        ],
        'equipment': {
            'inventory': [
                {'id': 'ring-of-spell-storing', 'name': 'Ring of Spell Storing', 'spellIds': [ITEM_SPELL]},
            ],
        },
        'spellState': {
            'known': CANTRIPS + LEVELLED + [ITEM_SPELL, FEAT_SPELL],
            'prepared': [],
        },
    }


def test_imported_known_count_is_not_reduced_to_fourteen():
    document = _bishop_document()
    resolved = resolve_spell_learning_limits(document, class_id='sorcerer', class_level=19)
    assert resolved['classKnownCount'] == len(LEVELLED)
    assert resolved['knownSpellLimit'] >= len(LEVELLED)
    assert resolved['knownSpellLimit'] != 14


def test_imported_cantrip_count_is_not_reduced_to_six():
    document = _bishop_document()
    resolved = resolve_spell_learning_limits(document, class_id='sorcerer', class_level=19)
    assert resolved['classCantripCount'] == len(CANTRIPS)
    assert resolved['cantripLimit'] >= len(CANTRIPS)
    assert resolved['cantripLimit'] != 6


def test_item_spells_counted_separately_from_class_known_spells():
    document = _bishop_document()
    resolved = resolve_spell_learning_limits(document, class_id='sorcerer', class_level=19)
    # The item-granted spell (a leveled spell, misty-step) must not inflate
    # (or be blamed for inflating) the class known-spell count.
    assert resolved['classKnownCount'] == len(LEVELLED)
    assert resolved['grantedSpellCount'] == 0


def test_feat_granted_spells_counted_separately():
    document = _bishop_document()
    resolved = resolve_spell_learning_limits(document, class_id='sorcerer', class_level=19)
    assert resolved['grantedCantripCount'] == 1
    assert resolved['classCantripCount'] == len(CANTRIPS)


def test_warning_emitted_when_imported_count_exceeds_internal_table():
    document = _bishop_document()
    resolved = resolve_spell_learning_limits(document, class_id='sorcerer', class_level=19)
    codes = {w.get('code') for w in resolved['warnings']}
    assert 'imported_known_count_preserved' in codes
    assert 'imported_cantrip_count_preserved' in codes
    messages = ' '.join(w.get('message', '') for w in resolved['warnings'])
    assert 'Preserved' in messages


def test_builder_and_sheet_use_same_resolved_limits():
    document = _bishop_document()
    sheet_limits = build_spell_limits_for_class('sorcerer', 19, document.get('abilities'), document=document, subclass_id='draconic-bloodline')
    builder_limits = build_spell_limits_for_class('sorcerer', 19, document.get('abilities'), document=document, subclass_id='draconic-bloodline')
    assert sheet_limits['spellsKnown'] == builder_limits['spellsKnown']
    assert sheet_limits['cantripsKnown'] == builder_limits['cantripsKnown']
    assert sheet_limits['spellsKnown'] >= len(LEVELLED)
    assert sheet_limits['cantripsKnown'] >= len(CANTRIPS)


def test_validate_spell_selection_does_not_block_imported_overage():
    document = _bishop_document()
    spell_state = document['spellState']
    validation = validate_spell_selection(
        class_id='sorcerer',
        class_level=19,
        abilities=document.get('abilities'),
        known=spell_state['known'],
        prepared=spell_state['prepared'],
        document=document,
        subclass_id='draconic-bloodline',
    )
    assert validation['ok'] is True, validation['errors']


def test_repair_does_not_delete_imported_spells_for_count_overage():
    document = _bishop_document()
    repaired = repair_spell_state_for_document(document, class_id='sorcerer', class_level=19, subclass_id='draconic-bloodline')
    known_after = repaired.get('known') or []
    for spell_id in CANTRIPS + LEVELLED:
        assert spell_id in known_after


def test_ninth_level_spell_remains_available_in_manifest():
    document = _bishop_document()
    manifest = build_character_spell_manifest(document)
    known_ids = set(manifest.get('known') or [])
    assert 'meteor-swarm' in known_ids


def test_manifest_limits_expose_warnings_for_sheet_and_quick_actions():
    document = _bishop_document()
    manifest = build_character_spell_manifest(document)
    limits = manifest.get('limits') or {}
    learning = limits.get('spellLearningLimits') or {}
    assert learning.get('importedKnownCount') == len(LEVELLED)
    assert learning.get('importedCantripCount') == len(CANTRIPS)
    assert learning.get('warnings')
