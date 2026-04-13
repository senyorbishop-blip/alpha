from server.character.spell_compendium import (
    build_character_spell_manifest,
    get_subclass_spell_grants,
    validate_spell_selection,
)
from server.character.progression import build_levelup_preview


def test_trickery_domain_gets_always_prepared_bonus_spells_at_level_one():
    document = {
        'classes': [{'classId': 'cleric', 'level': 1, 'subclassId': 'trickery-domain'}],
        'abilities': {'scores': {'wis': 16}},
        'spellState': {'known': [], 'prepared': []},
    }
    grants = get_subclass_spell_grants(document, class_id='cleric', class_level=1)
    assert 'charm-person' in grants['alwaysPrepared']
    assert 'disguise-self' in grants['alwaysPrepared']


def test_validate_spell_selection_merges_bonus_prepared_without_counting_against_limit():
    document = {
        'classes': [{'classId': 'cleric', 'level': 1, 'subclassId': 'trickery-domain'}],
        'abilities': {'scores': {'wis': 16}},
        'spellState': {'known': [], 'prepared': ['bless', 'cure-wounds', 'healing-word', 'sanctuary']},
    }
    result = validate_spell_selection(
        class_id='cleric',
        class_level=1,
        abilities=document['abilities'],
        known=[],
        prepared=document['spellState']['prepared'],
        document=document,
    )
    assert result['ok'] is True
    assert 'charm-person' in result['prepared']
    assert 'disguise-self' in result['prepared']


def test_devotion_preview_surfaces_subclass_spell_unlocks_on_subclass_level():
    document = {
        'classes': [{'classId': 'paladin', 'level': 2, 'subclassId': 'oath-of-devotion'}],
        'abilities': {'scores': {'cha': 16, 'str': 16}},
        'spellState': {'known': [], 'prepared': []},
    }
    preview = build_levelup_preview(document)
    assert preview['nextLevel'] == 3
    assert isinstance(preview['spellChoices'], dict)
    grants = preview['spellChoices'].get('subclassSpellGrants') or {}
    unlocked = [row for row in grants.get('unlockedSpells') or [] if row.get('unlockLevel') == 3]
    assert unlocked
    unlocked_names = {spell['name'] for row in unlocked for spell in row.get('spells') or []}
    assert 'Protection from Evil and Good' in unlocked_names
    assert 'Sanctuary' in unlocked_names


def test_warlock_manifest_marks_patron_bonus_spells_known():
    document = {
        'classes': [{'classId': 'warlock', 'level': 1, 'subclassId': 'fiend-patron'}],
        'abilities': {'scores': {'cha': 16}},
        'spellState': {'known': ['hex'], 'prepared': []},
    }
    manifest = build_character_spell_manifest(document)
    known_ids = set(manifest['known'])
    assert 'burning-hands' in known_ids
    assert 'command' in known_ids
