import json

from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_anchor_class_feature_definitions_exist_for_cleric_fighter_wizard():
    cleric = _load('server/data/rules/5e2024/classes/cleric.json')
    fighter = _load('server/data/rules/5e2024/classes/fighter.json')
    wizard = _load('server/data/rules/5e2024/classes/wizard.json')

    assert 'cleric-divine-domain-subclass' in cleric.get('featureDefinitions', {})
    assert 'fighter-martial-archetype-subclass' in fighter.get('featureDefinitions', {})
    assert 'wizard-arcane-tradition-subclass' in wizard.get('featureDefinitions', {})


def test_anchor_cleric_runtime_has_richer_domain_and_channel_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Vey'},
            'classes': [{'classId': 'cleric', 'level': 17, 'subclassId': 'trickery-domain'}],
            'abilities': {'scores': {'wis': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    domain = features.get('Divine Domain (Subclass)')
    invoke = features.get('Invoke Duplicity')
    turn_undead = features.get('Turn Undead')

    assert domain is not None
    assert 'identity shift' in str(domain.get('description') or '').lower() or 'subclass gate' in str(domain.get('description') or '').lower()

    assert invoke is not None
    assert invoke.get('resourceName') == 'Channel Divinity'
    assert invoke.get('type') == 'action'
    assert 'battlefield misdirection' in str(invoke.get('description') or '').lower() or 'duplicate' in str(invoke.get('description') or '').lower()

    assert turn_undead is not None
    assert turn_undead.get('save') == 'Wisdom save'
    assert any(row.get('name') == 'Turn Undead' for row in (runtime.get('actions') or []))


def test_anchor_fighter_runtime_has_subclass_and_resource_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Boros'},
            'classes': [{'classId': 'fighter', 'level': 15, 'subclassId': 'battlemaster'}],
            'abilities': {'scores': {'str': 18, 'dex': 14, 'con': 16}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    archetype = features.get('Martial Archetype (Subclass)')
    superiority = features.get('Combat Superiority')
    relentless = features.get('Relentless')

    assert archetype is not None
    assert 'battle master' in str(archetype.get('description') or '').lower() or 'subclass gate' in str(archetype.get('description') or '').lower()

    assert superiority is not None
    assert superiority.get('resourceName') == 'Superiority Dice'
    assert superiority.get('trackUses') is True
    assert 'maneuver' in str(superiority.get('description') or '').lower()

    assert relentless is not None
    assert relentless.get('resourceName') == 'Superiority Dice'
    assert 'fight dry' in str(relentless.get('description') or '').lower() or 'tactical fuel' in str(relentless.get('description') or '').lower()


def test_anchor_wizard_runtime_has_school_identity_and_portent_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Quill'},
            'classes': [{'classId': 'wizard', 'level': 14, 'subclassId': 'diviner'}],
            'abilities': {'scores': {'int': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    tradition = features.get('Arcane Tradition (Subclass)')
    portent = features.get('Portent')
    formulas = features.get('Cantrip Formulas')

    assert tradition is not None
    assert 'abjurer' in str(tradition.get('description') or '').lower() or 'diviner' in str(tradition.get('description') or '').lower() or 'illusionist' in str(tradition.get('description') or '').lower()

    assert portent is not None
    assert portent.get('resourceName') == 'Portent'
    assert portent.get('trackUses') is True
    assert 'stored' in str(portent.get('description') or '').lower() or 'future' in str(portent.get('description') or '').lower()

    assert formulas is not None
    assert 'cantrips are used constantly' in str(formulas.get('description') or '').lower() or 'at-will level' in str(formulas.get('description') or '').lower()
