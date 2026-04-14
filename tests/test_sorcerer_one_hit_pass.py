import json

from server.character.progression import apply_levelup, build_levelup_preview
from server.character.service import resolve_runtime


def _load(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_sorcerer_unlock_ids_all_have_feature_definitions():
    sorcerer = _load('server/data/rules/5e2024/classes/sorcerer.json')
    defs = sorcerer.get('featureDefinitions') or {}
    unlock_ids = [
        unlock
        for row in sorcerer.get('progressionTable', [])
        for unlock in (row.get('unlockIds') or [])
    ]

    missing = [unlock for unlock in unlock_ids if unlock not in defs]
    assert not missing


def test_sorcerer_metamagic_choices_surface_on_unlock_levels_and_persist():
    doc = {
        'identity': {'name': 'Metra'},
        'classes': [{'classId': 'sorcerer', 'level': 2, 'subclassId': 'wild-magic'}],
        'abilities': {'scores': {'cha': 18, 'con': 14}},
        'spellState': {
            'known': ['fire-bolt', 'mage-hand', 'message', 'minor-illusion', 'magic-missile', 'shield'],
            'prepared': [],
        },
    }

    preview = build_levelup_preview(doc)
    metamagic = next((row for row in (preview.get('newFeatures') or []) if row.get('id') == 'sorcerer-l3-2'), None)
    assert metamagic is not None
    assert len(metamagic.get('choices') or []) >= 10

    cantrip_options = (preview.get('spellChoices') or {}).get('cantripOptions') or []
    levelled_options = (preview.get('spellChoices') or {}).get('levelledOptions') or []

    applied = apply_levelup(
        doc,
        choices={
            'featureChoices': {'sorcerer-l3-2': (metamagic.get('choices') or [])[0]['id']},
            'spellChoices': {
                'cantripAdds': [cantrip_options[0]['id']] if cantrip_options and (preview.get('spellChoices') or {}).get('cantripPicksRequired') else [],
                'levelledAdds': [levelled_options[0]['id']] if levelled_options and (preview.get('spellChoices') or {}).get('levelledPicksRequired') else [],
                'swap': {},
            },
        },
    )

    selected = applied['document']['classes'][0].get('selectedFeatures') or []
    picked = next((row for row in selected if row.get('id') == 'sorcerer-l3-2'), None)
    assert picked is not None
    assert picked.get('selectedChoice')


def test_sorcerer_subclass_progression_uses_level_three_entry_points():
    wild = _load('server/data/rules/5e2024/subclasses/wild-magic.json')
    draconic = _load('server/data/rules/5e2024/subclasses/draconic-bloodline.json')

    assert '3' in (wild.get('featureUnlocksByLevel') or {})
    assert '1' not in (wild.get('featureUnlocksByLevel') or {})
    assert '3' in (draconic.get('featureUnlocksByLevel') or {})
    assert '1' not in (draconic.get('featureUnlocksByLevel') or {})

    runtime = resolve_runtime(
        {
            'identity': {'name': 'Vyre'},
            'classes': [{'classId': 'sorcerer', 'level': 3, 'subclassId': 'draconic-bloodline'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']
    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    assert 'Dragon Ancestor' in features
    assert 'Draconic Resilience' in features


def test_sorcerer_ui_surfaces_resource_and_conversion_language():
    with open('client/static/js/character/tabs/actions_tab.js', 'r', encoding='utf-8') as f:
        actions_js = f.read().lower()
    with open('client/static/js/character/tabs/spells_tab.js', 'r', encoding='utf-8') as f:
        spells_js = f.read().lower()

    assert 'sorcerer combat surface' in actions_js
    assert 'flexible casting' in actions_js
    assert 'metamagic' in actions_js
    assert 'sorcery points' in spells_js
    assert 'sorcerer flow: cast from known spells' in spells_js
