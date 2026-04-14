import json

from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_paladin_progression_uses_non_placeholder_unlock_ids_and_full_spell_slots():
    paladin = _load('server/data/rules/5e2024/classes/paladin.json')

    for row in paladin.get('progressionTable') or []:
        for unlock_id in row.get('unlockIds') or []:
            assert '-l' not in unlock_id or unlock_id.startswith('paladin-lay-on-hands')
            assert not unlock_id.startswith('paladin-l4-')
            assert not unlock_id.startswith('paladin-l6-')
            assert not unlock_id.startswith('paladin-l10-')
            assert not unlock_id.startswith('paladin-l20-')

    slots = paladin.get('spellSlots') or {}
    for lvl in range(2, 21):
        assert str(lvl) in slots
        assert isinstance(slots[str(lvl)], dict)


def test_paladin_runtime_surfaces_channel_divinity_lay_on_hands_and_aura_scaling():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Astra'},
            'classes': [{'classId': 'paladin', 'level': 18, 'subclassId': 'oath-of-vengeance'}],
            'abilities': {'scores': {'str': 18, 'cha': 18, 'con': 16}},
        }
    )['runtime']

    resources = {str(row.get('name') or '').lower(): row for row in (runtime.get('resources') or [])}
    assert 'lay on hands' in resources
    assert resources['lay on hands'].get('max') == 90

    assert 'channel divinity' in resources
    assert resources['channel divinity'].get('max') == 2

    assert runtime.get('classMechanics', {}).get('auraRangeFeet') == 30


def test_oath_of_the_ancients_no_longer_contains_vow_of_enmity():
    ancients = _load('server/data/rules/5e2024/subclasses/oath-of-the-ancients.json')
    feature_ids = {row.get('id') for row in (ancients.get('features') or [])}
    assert 'ancients-vow-of-enmity' not in feature_ids
    assert 'ancients-turn-the-faithless' in feature_ids
