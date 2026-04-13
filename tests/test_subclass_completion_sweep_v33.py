import json

from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_subclass_completion_definitions_exist_for_barbarian_bard_monk():
    barbarian = _load('server/data/rules/5e2024/classes/barbarian.json')
    bard = _load('server/data/rules/5e2024/classes/bard.json')
    monk = _load('server/data/rules/5e2024/classes/monk.json')

    assert 'barbarian-rage' in barbarian.get('featureDefinitions', {})
    assert 'bard-spellcasting' in bard.get('featureDefinitions', {})
    assert 'monk-martial-arts' in monk.get('featureDefinitions', {})
    assert 'unlockIds' in barbarian.get('progressionTable', [])[0]
    assert 'unlockIds' in bard.get('progressionTable', [])[0]
    assert 'unlockIds' in monk.get('progressionTable', [])[0]


def test_barbarian_runtime_has_path_and_rage_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Brakka'},
            'classes': [{'classId': 'barbarian', 'level': 14, 'subclassId': 'world-tree'}],
            'abilities': {'scores': {'str': 18, 'dex': 14, 'con': 16}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    path = features.get('Primal Path (Subclass)')
    rage = features.get('Rage')
    roots = features.get('Battering Roots')

    assert path is not None
    assert 'subclass gate' in str(path.get('description') or '').lower() or 'build' in str(path.get('description') or '').lower()
    assert rage is not None
    assert rage.get('resourceName') == 'Rage'
    assert rage.get('trackUses') is True
    assert roots is not None
    assert 'root' in str(roots.get('description') or '').lower() or 'tree' in str(roots.get('description') or '').lower()


def test_bard_runtime_has_college_and_inspiration_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Lyric'},
            'classes': [{'classId': 'bard', 'level': 14, 'subclassId': 'college-of-glamour'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    college = features.get('Bard College (Subclass)')
    inspiration = features.get('Bardic Inspiration (d10)') or features.get('Bardic Inspiration (d8)') or features.get('Bardic Inspiration (d12)')
    mantle = features.get('Mantle of Inspiration')

    assert college is not None
    assert 'subclass gate' in str(college.get('description') or '').lower() or 'college' in str(college.get('description') or '').lower()
    assert inspiration is not None
    assert inspiration.get('resourceName') == 'Bardic Inspiration'
    assert inspiration.get('trackUses') is True
    assert mantle is not None
    assert 'inspiration' in str(mantle.get('description') or '').lower() or 'majesty' in str(mantle.get('description') or '').lower()


def test_monk_runtime_has_tradition_and_focus_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Shade'},
            'classes': [{'classId': 'monk', 'level': 17, 'subclassId': 'way-of-shadow'}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}
    tradition = features.get('Monastic Tradition (Subclass)')
    focus = features.get("Monk's Focus (Discipline Points)")
    step = features.get('Shadow Step')

    assert tradition is not None
    assert 'subclass gate' in str(tradition.get('description') or '').lower() or 'tradition' in str(tradition.get('description') or '').lower()
    assert focus is not None
    assert focus.get('resourceName') == 'Focus Points'
    assert focus.get('trackUses') is True
    assert step is not None
    assert 'shadow' in str(step.get('description') or '').lower() or 'teleport' in str(step.get('description') or '').lower()
