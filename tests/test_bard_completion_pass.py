import json

from server.character.progression import build_levelup_preview
from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_bard_unlock_ids_use_authored_feature_ids_consistently():
    bard = _load('server/data/rules/5e2024/classes/bard.json')
    by_level = {str(int(row.get('level'))): row for row in bard.get('progressionTable', []) if isinstance(row, dict) and row.get('level')}

    for level, unlock_ids in (bard.get('levelUnlockIds') or {}).items():
        table_unlocks = list((by_level.get(str(level), {}) or {}).get('unlockIds') or [])
        assert unlock_ids == table_unlocks

    summary_rows = bard.get('progressionSummary') or []
    for row in summary_rows:
        level = str(int(row.get('level')))
        assert list(row.get('unlockIds') or []) == list((by_level.get(level, {}) or {}).get('unlockIds') or [])


def test_bard_runtime_tracks_inspiration_die_uses_and_refresh():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Lyric'},
            'classes': [{'classId': 'bard', 'level': 5, 'subclassId': 'college-of-lore'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    bardic = next((row for row in (runtime.get('resources') or []) if str(row.get('id') or '') == 'bardic_inspiration'), {})
    assert bardic
    assert bardic.get('max') == 4
    assert bardic.get('current') == 4
    assert 'D8' in str(bardic.get('summary') or '').upper()
    assert 'short or long rest' in str(bardic.get('recovery') or '').lower()


def test_bard_levelup_preview_exposes_magical_secrets_as_real_pick_flow():
    preview = build_levelup_preview(
        {
            'identity': {'name': 'Lyric'},
            'classes': [{'classId': 'bard', 'level': 6, 'subclassId': 'college-of-lore'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
            'spellState': {'known': [], 'prepared': []},
        }
    )

    spell_choices = preview.get('spellChoices') or {}
    assert spell_choices.get('magicalSecretsPicksRequired') == 1
    options = spell_choices.get('magicalSecretOptions') or []
    assert options
    assert any(option.get('unlockLevel') is None for option in options)
