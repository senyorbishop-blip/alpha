import json
from pathlib import Path


def _load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def test_fighter_progression_unlock_ids_are_authored_feature_ids():
    fighter = _load('server/data/rules/5e2024/classes/fighter.json')
    progression = fighter.get('progressionTable') or []
    expected_by_level = {
        str(int(row.get('level'))): [str(v) for v in (row.get('unlockIds') or []) if str(v)]
        for row in progression
        if isinstance(row, dict) and row.get('level')
    }

    assert fighter.get('levelUnlockIds') == expected_by_level

    summary = fighter.get('progressionSummary') or []
    for row in summary:
        level_key = str(int(row.get('level')))
        assert row.get('unlockIds') == expected_by_level[level_key]


def test_fighter_runtime_surfaces_core_resources_and_martial_scalers():
    fighter = _load('server/data/rules/5e2024/classes/fighter.json')
    level_row = next(
        row for row in (fighter.get('progressionTable') or [])
        if isinstance(row, dict) and int(row.get('level') or 0) == 17
    )
    mechanics = level_row.get('classMechanics') or {}
    assert mechanics.get('extraAttacks') == 3
    assert mechanics.get('weaponMasteryCount') == 5
    assert mechanics.get('secondWindUses') == 1

    feature_catalog_src = Path('server/character/feature_catalog.py').read_text(encoding='utf-8')
    assert '"secondWindUses": {"id": "second_wind"' in feature_catalog_src
    assert '"second_wind": "Regain all uses on a short or long rest."' in feature_catalog_src


def test_fighter_actions_tab_contains_subclass_surfaces():
    src = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8').lower()
    assert 'fighter combat surface' in src
    assert 'maneuver save dc' in src
    assert 'war magic / weapon bond cadence should be visible' in src
    assert 'improved critical pressure' in src


def test_subclass_builder_has_fighter_identity_overrides():
    src = Path('client/static/js/character/builder/steps/step_subclass.js').read_text(encoding='utf-8').lower()
    assert 'champion' in src and 'crit pressure' in src
    assert 'battlemaster' in src and 'superiority dice' in src
    assert "'eldritch-knight'" in src and 'weapon + spell weave' in src
