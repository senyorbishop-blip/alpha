import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def node_eval(script: str):
    code = f"const rt=require('./client/static/js/character/spell_runtime.js');\n{script}"
    out = subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True)
    return json.loads(out)

def resolve(card, opts=None):
    return node_eval(f"console.log(JSON.stringify(rt.resolveSpellRuntime({json.dumps(card)}, {json.dumps(opts or {})})))")

def test_fireball_scaling_and_save_only_buttons():
    third = resolve({'id':'fireball','name':'Fireball'}, {'castLevel':3,'saveDc':15})
    ninth = resolve({'id':'fireball','name':'Fireball'}, {'castLevel':9,'saveDc':15})
    assert third['finalDamageFormula'] == '8d6'
    assert ninth['finalDamageFormula'] == '14d6'
    assert ninth['finalDamageFormula'] != '6d6'
    assert not ninth['requiresAttackRoll']
    assert ninth['saveAbility'] == 'DEX'
    assert ninth['saveDc'] == '15'

def test_cure_wounds_healing_scales_and_no_damage():
    first = resolve({'id':'cure-wounds','name':'Cure Wounds'}, {'castLevel':1})
    fifth = resolve({'id':'cure-wounds','name':'Cure Wounds'}, {'castLevel':5})
    assert first['finalHealingFormula'] == '1d8 + spellcasting modifier'
    assert fifth['finalHealingFormula'] == '5d8 + spellcasting modifier'
    assert fifth['finalDamageFormula'] == ''
    assert fifth['healingType'] == 'healing'

def test_darts_rays_and_attacks():
    mm1 = resolve({'id':'magic-missile','name':'Magic Missile'}, {'castLevel':1})
    mm9 = resolve({'id':'magic-missile','name':'Magic Missile'}, {'castLevel':9})
    assert '3 darts' in mm1['displayFormula']
    assert '11 darts' in mm9['displayFormula']
    assert not mm9['requiresAttackRoll']
    sr2 = resolve({'id':'scorching-ray','name':'Scorching Ray'}, {'castLevel':2})
    sr5 = resolve({'id':'scorching-ray','name':'Scorching Ray'}, {'castLevel':5})
    assert '3 rays' in sr2['displayFormula']
    assert '6 rays' in sr5['displayFormula']
    assert sr5['requiresAttackRoll']

def test_cantrip_and_utility_behaviour():
    fb1 = resolve({'id':'fire-bolt','name':'Fire Bolt'}, {'characterLevel':1})
    fb17 = resolve({'id':'fire-bolt','name':'Fire Bolt'}, {'characterLevel':17})
    assert fb1['finalDamageFormula'] == '1d10'
    assert fb17['finalDamageFormula'] == '4d10'
    assert fb17['castLevel'] == 0
    assert not fb17['consumesSpellSlot']
    assert fb17['requiresAttackRoll']
    for spell in ['counterspell','shield','detect-magic','misty-step']:
        r = resolve({'id':spell,'name':spell})
        assert r['finalDamageFormula'] == ''
        assert not r['requiresAttackRoll']

def test_unknown_level_and_missing_formula_safe():
    unknown = resolve({'id':'homebrew','name':'Homebrew Spell'})
    assert 'Unknown spell level' in unknown['warnings']
    assert unknown['baseLevel'] is None
    missing = resolve({'id':'mystery-bolt','name':'Mystery Bolt','level':1,'damageType':'fire'})
    assert missing['finalDamageFormula'] == ''


def test_every_compendium_spell_resolves_without_crashing():
    script = """
const fs=require('fs'), path=require('path');
const dir='server/data/rules/5e2024/spells';
let spells=[];
for (const file of fs.readdirSync(dir)) if (file.endsWith('.json')) {
 const data=JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
 spells=spells.concat(data.spells||[]);
}
const out=spells.map(s=>rt.resolveSpellRuntime(s, {characterLevel:17, castLevel:s.level||s.spell_level||0}));
console.log(JSON.stringify({count:out.length, bad:out.filter(r=>((r.damageType||r.healingType)&&!r.displayFormula&&!r.warnings.length)).length, saveAttack:out.filter(r=>r.saveAbility&&r.requiresAttackRoll).length, attacks:out.filter(r=>r.requiresAttackRoll).length}));
"""
    result = node_eval(script)
    assert result['count'] > 100
    assert result['bad'] == 0
    assert result['saveAttack'] == 0
