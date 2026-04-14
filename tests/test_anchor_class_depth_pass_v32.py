import json

from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_anchor_class_feature_definitions_exist_for_druid_sorcerer_ranger():
    druid = _load('server/data/rules/5e2024/classes/druid.json')
    sorcerer = _load('server/data/rules/5e2024/classes/sorcerer.json')
    ranger = _load('server/data/rules/5e2024/classes/ranger.json')

    assert 'druid-l3-1' in druid.get('featureDefinitions', {})
    assert 'sorcerer-l3-1' in sorcerer.get('featureDefinitions', {})
    assert 'ranger-conclave-subclass' in ranger.get('featureDefinitions', {})
    assert 'unlockIds' in druid.get('progressionTable', [])[0]
    assert 'unlockIds' in sorcerer.get('progressionTable', [])[0]
    assert 'unlockIds' in ranger.get('progressionTable', [])[0]


def test_anchor_druid_runtime_has_circle_and_shape_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Ashfern'},
            'classes': [{'classId': 'druid', 'level': 14, 'subclassId': 'circle-of-the-moon'}],
            'abilities': {'scores': {'wis': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    circle = features.get('Druid Circle (Subclass)')
    wild_shape = features.get('Wild Shape')
    elemental = features.get('Elemental Wild Shape')

    assert circle is not None
    assert 'subclass gate' in str(circle.get('description') or '').lower() or 'shapechanger' in str(circle.get('description') or '').lower()

    assert wild_shape is not None
    assert wild_shape.get('resourceName') == 'Wild Shape'
    assert wild_shape.get('trackUses') is True
    assert 'shape' in str(wild_shape.get('description') or '').lower()

    assert elemental is not None
    assert elemental.get('resourceName') == 'Wild Shape'
    assert 'elemental' in str(elemental.get('description') or '').lower()


def test_anchor_sorcerer_runtime_has_origin_and_sorcery_point_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Vesper'},
            'classes': [{'classId': 'sorcerer', 'level': 18, 'subclassId': 'wild-magic'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    origin = features.get('Sorcerous Origin (Subclass)')
    font = features.get('Font of Magic')
    bend = features.get('Bend Luck')

    assert origin is not None
    assert 'wild magic' in str(origin.get('description') or '').lower() or 'draconic' in str(origin.get('description') or '').lower()

    assert font is not None
    assert font.get('resourceName') == 'Sorcery Points'
    assert font.get('trackUses') is True

    assert bend is not None
    assert bend.get('type') == 'reaction'
    assert bend.get('resourceName') == 'Sorcery Points'
    assert 'fate' in str(bend.get('description') or '').lower() or 'chaos' in str(bend.get('description') or '').lower()


def test_anchor_ranger_runtime_has_conclave_and_hunt_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Rook'},
            'classes': [{'classId': 'ranger', 'level': 15, 'subclassId': 'gloom-stalker'}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    conclave = features.get('Ranger Conclave (Subclass)')
    foe = features.get('Favored Enemy')
    dread = features.get('Dread Ambusher')
    dodge = features.get('Shadowy Dodge')

    assert conclave is not None
    assert 'stalker' in str(conclave.get('description') or '').lower() or 'subclass gate' in str(conclave.get('description') or '').lower()

    assert foe is not None
    assert 'hunter' in str(foe.get('description') or '').lower() or 'tracking' in str(foe.get('description') or '').lower()

    assert dread is not None
    assert 'opening heartbeat' in str(dread.get('description') or '').lower() or 'first-round' in str(dread.get('description') or '').lower()

    assert dodge is not None
    assert dodge.get('type') == 'reaction'
    assert 'shadow' in str(dodge.get('description') or '').lower() or 'elusive' in str(dodge.get('description') or '').lower()
