from server.character.progression import build_levelup_preview
from server.character.rules_catalog import load_rules_catalog
from server.character.service import resolve_runtime


def test_barbarian_levelup_uses_authored_unlock_ids_for_preview():
    preview = build_levelup_preview(
        {
            'identity': {'name': 'Rurik'},
            'classes': [{'classId': 'barbarian', 'level': 1}],
            'abilities': {'scores': {'str': 16, 'dex': 14, 'con': 16}},
        }
    )

    names = [str(row.get('displayName') or '') for row in (preview.get('newFeatures') or [])]
    assert 'Reckless Attack' in names
    assert 'Danger Sense' in names
    for row in (preview.get('newFeatures') or []):
        row_id = str(row.get('id') or '')
        assert not row_id.startswith('barbarian-l2-')


def test_world_tree_branches_is_reaction_typed():
    catalog = load_rules_catalog()
    subclasses_by_id = catalog.get('subclassesById') if isinstance(catalog.get('subclassesById'), dict) else {}
    world_tree = subclasses_by_id.get('world-tree') if isinstance(subclasses_by_id, dict) else {}
    feature_defs = world_tree.get('featureDefinitions') if isinstance(world_tree, dict) else {}
    branches = feature_defs.get('world-tree-branches-of-the-tree') if isinstance(feature_defs, dict) else {}

    assert branches.get('type') == 'reaction'
    assert branches.get('section') == 'Reactions'


def test_barbarian_runtime_exposes_rage_resource_and_mechanics():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Brakka'},
            'classes': [{'classId': 'barbarian', 'level': 9, 'subclassId': 'berserker'}],
            'abilities': {'scores': {'str': 18, 'dex': 14, 'con': 16}},
        }
    )['runtime']

    resources = runtime.get('resources') if isinstance(runtime.get('resources'), list) else []
    rage = next((row for row in resources if str(row.get('id') or '') == 'rage_uses'), None)
    assert rage is not None
    assert int(rage.get('max') or 0) >= 4

    class_mechanics = runtime.get('classMechanics') if isinstance(runtime.get('classMechanics'), dict) else {}
    assert int(class_mechanics.get('rageDamageBonus') or 0) == 3
    assert int(class_mechanics.get('extraAttacks') or 0) == 2
