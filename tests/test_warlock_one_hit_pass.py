import json

from server.character.progression import build_levelup_preview
from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_warlock_progression_uses_authored_unlock_ids_without_placeholders():
    warlock = _load('server/data/rules/5e2024/classes/warlock.json')
    for row in warlock.get('progressionTable') or []:
        for unlock_id in row.get('unlockIds') or []:
            assert not str(unlock_id).startswith('warlock-l'), unlock_id


def test_warlock_runtime_surfaces_pact_magic_identity():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Nyx'},
            'classes': [{'classId': 'warlock', 'level': 9, 'subclassId': 'archfey-patron'}],
            'abilities': {'scores': {'cha': 18, 'con': 14, 'dex': 14}},
        }
    )['runtime']

    spell_access = runtime.get('spellAccess') or {}
    pact = spell_access.get('pactMagic') or {}
    assert pact.get('enabled') is True
    assert pact.get('slotCount') == 2
    assert pact.get('slotLevel') == 5
    assert 'short' in str(pact.get('recoveryType') or '').lower()

    resources = {row.get('id'): row for row in (runtime.get('resources') or []) if isinstance(row, dict)}
    assert 'pact_slots' in resources
    assert 'slot level 5' in str(resources['pact_slots'].get('summary') or '').lower()


def test_warlock_levelup_preview_requires_real_invocation_and_boon_choices():
    preview = build_levelup_preview(
        {
            'identity': {'name': 'Morrow'},
            'classes': [{'classId': 'warlock', 'level': 2, 'subclassId': 'fiend-patron'}],
            'abilities': {'scores': {'cha': 16, 'con': 14}},
        }
    )

    assert preview.get('nextLevel') == 3
    feature_rows = {row.get('id'): row for row in (preview.get('newFeatures') or []) if isinstance(row, dict)}

    pact_boon = feature_rows.get('warlock-pact-boon')
    invocation_pick = feature_rows.get('warlock-eldritch-invocation-choice-l3')

    assert pact_boon is not None
    assert len(pact_boon.get('choices') or []) >= 3

    assert invocation_pick is not None
    assert len(invocation_pick.get('choices') or []) >= 3

    required = [row for row in (preview.get('requiredChoices') or []) if row.get('type') == 'feature_choice']
    required_ids = {row.get('id') for row in required}
    assert 'warlock-pact-boon' in required_ids
    assert 'warlock-eldritch-invocation-choice-l3' in required_ids
