import json
import re

from server.character.progression import build_levelup_preview
from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_ranger_progression_uses_authored_unlock_ids_without_generic_placeholders():
    ranger = _load('server/data/rules/5e2024/classes/ranger.json')
    for row in ranger.get('progressionTable') or []:
        for unlock_id in row.get('unlockIds') or []:
            assert not re.match(r'^ranger-l\\d', str(unlock_id)), unlock_id


def test_ranger_levelup_preview_surfaces_hunter_branch_choices_from_subclass_unlocks():
    preview = build_levelup_preview(
        {
            'identity': {'name': 'Rook'},
            'classes': [{'classId': 'ranger', 'level': 2, 'subclassId': 'hunter'}],
            'abilities': {'scores': {'dex': 16, 'wis': 14, 'con': 14}},
        }
    )

    assert preview.get('nextLevel') == 3
    features = {row.get('id'): row for row in (preview.get('newFeatures') or []) if isinstance(row, dict)}
    prey = features.get('hunter-hunters-prey')

    assert prey is not None
    assert len(prey.get('choices') or []) == 3

    required = {row.get('id') for row in (preview.get('requiredChoices') or []) if row.get('type') == 'feature_choice'}
    assert 'hunter-hunters-prey' in required


def test_ranger_levelup_preview_surfaces_beast_master_companion_choice_options():
    preview = build_levelup_preview(
        {
            'identity': {'name': 'Ash'},
            'classes': [{'classId': 'ranger', 'level': 2, 'subclassId': 'beast-master'}],
            'abilities': {'scores': {'dex': 16, 'wis': 16, 'con': 14}},
        }
    )

    features = {row.get('id'): row for row in (preview.get('newFeatures') or []) if isinstance(row, dict)}
    companion = features.get('beast-master-rangers-companion')
    assert companion is not None
    choices = companion.get('choices') or []
    assert len(choices) == 3
    assert {row.get('id') for row in choices} == {
        'primal-beast-land',
        'primal-beast-sea',
        'primal-beast-sky',
    }


def test_ranger_selected_feature_choices_render_human_choice_name_in_runtime():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Kestrel'},
            'classes': [
                {
                    'classId': 'ranger',
                    'level': 11,
                    'subclassId': 'hunter',
                    'selectedFeatures': [
                        {'id': 'hunter-hunters-prey', 'displayName': "Hunter's Prey", 'selectedChoice': 'horde-breaker'},
                    ],
                }
            ],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    selected = next((row for name, row in features.items() if name and "Hunter's Prey — Horde Breaker" in name), None)

    assert selected is not None
    assert selected.get('isSubclass') is True
    assert 'extra attack against a different nearby creature' in str(selected.get('description') or '').lower()


def test_actions_tab_has_ranger_custom_combat_surface_and_subclass_cards():
    src = _load_text('client/static/js/character/tabs/actions_tab.js')
    assert "Ranger Combat Surface" in src
    assert "Dread Ambusher Opener" in src
    assert "Companion Command" in src


def _load_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
