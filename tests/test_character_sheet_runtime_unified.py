import json
import subprocess
import textwrap
from pathlib import Path


def _run_runtime(doc):
    script = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');
        const ctx = {{ window: {{}}, console }};
        ctx.global = ctx.window;
        ctx.window.window = ctx.window;
        vm.createContext(ctx);
        vm.runInContext(fs.readFileSync('client/static/js/character/spell_runtime.js', 'utf8'), ctx);
        vm.runInContext(fs.readFileSync('client/static/js/character/runtime/character_sheet_runtime.js', 'utf8'), ctx);
        const runtime = ctx.window.buildCharacterSheetRuntime({json.dumps(doc)});
        ctx.window.spendCharacterSheetResource(runtime, 'sorcery_points', 2);
        const afterSpend = runtime.resources.find((r) => r.id === 'sorcery_points').current;
        ctx.window.resetCharacterSheetResources(runtime, 'long');
        const afterLongRest = runtime.resources.find((r) => r.id === 'sorcery_points').current;
        console.log(JSON.stringify({{ runtime, afterSpend, afterLongRest }}));
        """
    )
    result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def _bishop_doc():
    return {
        'name': 'Bishop',
        'className': 'Sorcerer',
        'subclass': 'Wild Magic',
        'level': 19,
        'totalLevel': 19,
        'spellSaveDc': 19,
        'spellAttack': '+11',
        'ac': 15,
        'speed': 30,
        'features': [
            {'name': 'Font of Magic', 'source': 'Sorcerer'},
            {'name': 'Quickened Spell', 'source': 'Sorcerer'},
            {'name': 'Wild Magic Surge', 'source': 'imported', 'needsReview': False},
        ],
        'spells': [{'name': 'Fire Bolt'}, {'name': 'Scorching Ray'}, {'name': 'Fireball'}],
        'inventory': [{'name': 'Thunder Mage Quarterstaff', 'type': 'weapon', 'source': 'item', 'damage': '1d6 bludgeoning + thunder'}],
    }


def test_build_character_sheet_runtime_returns_major_sections_and_shared_surface_contract():
    rt = _run_runtime(_bishop_doc())['runtime']
    for key in ['identity', 'abilities', 'saves', 'skills', 'senses', 'defenses', 'conditions', 'hp', 'ac', 'speed', 'initiative', 'proficiencyBonus', 'resources', 'actions', 'bonusActions', 'reactions', 'limitedUseActions', 'attacks', 'spells', 'features', 'traits', 'feats', 'background', 'inventory', 'warnings', 'needsReview']:
        assert key in rt
    src = Path('client/static/js/character/character_sheet_container.js').read_text(encoding='utf-8')
    assert 'charData.characterSheetRuntime = sheetRuntime;' in src
    assert 'charData.nativeResources = sheetRuntime.resources;' in src
    assert 'charData.rulesSpellbook = sheetRuntime.spells;' in src


def test_bishop_sorcerer_resources_features_actions_spells_and_import_dedupe():
    rt = _run_runtime(_bishop_doc())['runtime']
    resources = {r['id']: r for r in rt['resources']}
    assert resources['sorcery_points']['max'] == 19
    assert 'metamagic' in resources['sorcery_points']['linkedFeatures']
    assert resources['tides_of_chaos']['max'] == 1
    features = {f['name']: f for f in rt['features']}
    assert 'Font of Magic' in features
    assert 'Wild Magic Surge' in features
    assert 'Tides of Chaos' in features
    assert list(f['name'] for f in rt['features']).count('Wild Magic Surge') == 1
    quickened = next(a for a in rt['bonusActions'] if a['name'] == 'Quickened Spell / Metamagic')
    assert quickened['resourceCost'] == {'resourceId': 'sorcery_points', 'amount': 2}
    assert quickened['featureModifiers'][0]['type'] == 'spell_action_economy'
    assert any(a['name'] == 'Flexible Casting: Create Spell Slot' for a in rt['bonusActions'])


def test_spell_and_weapon_runtime_resolution_and_resource_updates():
    payload = _run_runtime(_bishop_doc())
    rt = payload['runtime']
    spells = {s['name']: s for s in rt['spells']}
    assert spells['Fire Bolt']['attackType'] == 'ranged-spell'
    assert spells['Scorching Ray']['attackType'] == 'ranged-spell'
    assert spells['Scorching Ray']['level'] == 2
    assert spells['Scorching Ray']['scaling']['upcastLevels'] == list(range(2, 10))
    assert spells['Fireball']['saveAbility'] == 'DEX'
    assert spells['Fireball']['level'] == 3
    assert spells['Fireball']['scaling']['upcastLevels'] == list(range(3, 10))
    attacks = {a['name']: a for a in rt['attacks']}
    assert attacks['Thunder Mage Quarterstaff']['source'] == 'item'
    assert 'Unarmed Strike' in attacks
    assert payload['afterSpend'] == 17
    assert payload['afterLongRest'] == 19
