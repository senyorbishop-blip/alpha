import json

from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_anchor_class_feature_definitions_exist_for_paladin_rogue_warlock():
    paladin = _load('server/data/rules/5e2024/classes/paladin.json')
    rogue = _load('server/data/rules/5e2024/classes/rogue.json')
    warlock = _load('server/data/rules/5e2024/classes/warlock.json')

    assert 'paladin-sacred-oath-subclass' in paladin.get('featureDefinitions', {})
    assert 'rogue-roguish-archetype-subclass' in rogue.get('featureDefinitions', {})
    assert 'warlock-eldritch-patron-subclass' in warlock.get('featureDefinitions', {})


def test_anchor_paladin_runtime_has_oath_and_aura_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Astra'},
            'classes': [{'classId': 'paladin', 'level': 13, 'subclassId': 'oath-of-devotion'}],
            'abilities': {'scores': {'str': 18, 'cha': 18, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    oath = features.get('Sacred Oath (Subclass)')
    aura = next((row for name, row in features.items() if str(name).startswith('Aura of Protection')), None)
    sacred_weapon = features.get('Channel Divinity: Sacred Weapon')

    assert oath is not None
    assert 'devotion' in str(oath.get('description') or '').lower() or 'subclass gate' in str(oath.get('description') or '').lower()

    assert aura is not None
    assert 'formation' in str(aura.get('description') or '').lower() or 'position' in str(aura.get('description') or '').lower()

    assert sacred_weapon is not None
    assert sacred_weapon.get('resourceName') == 'Channel Divinity'
    assert sacred_weapon.get('type') == 'action'


def test_anchor_rogue_runtime_has_subclass_and_precision_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Shade'},
            'classes': [{'classId': 'rogue', 'level': 17, 'subclassId': 'arcane-trickster'}],
            'abilities': {'scores': {'dex': 18, 'int': 16, 'con': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    archetype = features.get('Roguish Archetype (Subclass)')
    sneak = features.get('Sneak Attack (9d6)')
    versatile = features.get('Versatile Trickster')

    assert archetype is not None
    assert 'arcane trickster' in str(archetype.get('description') or '').lower() or 'subclass gate' in str(archetype.get('description') or '').lower()

    assert sneak is not None
    assert 'positioning' in str(sneak.get('description') or '').lower() or 'precision' in str(sneak.get('description') or '').lower()

    assert versatile is not None
    assert versatile.get('type') == 'bonus action'
    assert 'mage hand' in str(versatile.get('description') or '').lower()


def test_anchor_warlock_runtime_has_patron_and_pact_depth():
    runtime = resolve_runtime(
        {
            'identity': {'name': 'Morrow'},
            'classes': [{'classId': 'warlock', 'level': 14, 'subclassId': 'fiend-patron'}],
            'abilities': {'scores': {'cha': 18, 'con': 14, 'dex': 14}},
        }
    )['runtime']

    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    patron = features.get('Eldritch Patron (Subclass)')
    pact = features.get('Pact Magic')
    hurl = features.get('Hurl Through Hell')

    assert patron is not None
    assert 'fiend' in str(patron.get('description') or '').lower() or 'generic arcane shell' in str(patron.get('description') or '').lower()

    assert pact is not None
    assert pact.get('resourceName') == 'Pact Slots'
    assert pact.get('trackUses') is True
    assert 'short rest' in str(pact.get('description') or '').lower()

    assert hurl is not None
    assert 'nightmare' in str(hurl.get('description') or '').lower() or 'iconic' in str(hurl.get('description') or '').lower()
