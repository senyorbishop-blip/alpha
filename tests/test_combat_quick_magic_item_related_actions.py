import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _node_eval(script: str):
    code = r'''
const fs = require('fs');
const vm = require('vm');
global.window = global;
global.document = {
  addEventListener() {},
  getElementById() { return null; },
  createElement() { return { addEventListener(){}, appendChild(){}, querySelector(){return null}, setAttribute(){}, style:{}, classList:{add(){}, remove(){}} }; },
  body: { appendChild(){} }
};
global.addEventListener = function(){};
global.console = console;
const calls = [];
global.__calls = calls;
global.rollQuickWeaponAttack = (ctx) => calls.push(['attack', ctx && ctx.name]);
global.rollQuickWeaponDamage = (ctx) => calls.push(['damage', ctx && ctx.name]);
global.rollQuickWeaponCriticalDamage = (ctx) => calls.push(['crit', ctx && ctx.name]);
global.combatQuickRollSpellAttack = (spell, lvl) => calls.push(['spellAttack', spell && spell.name, lvl]);
global.combatQuickRollSpellDamage = (spell, lvl) => calls.push(['spellDamage', spell && spell.name, lvl]);
global.combatQuickShowSpellSave = (spell, lvl) => calls.push(['spellSave', spell && spell.name, lvl]);
global.combatQuickCastSpell = (spell, lvl) => calls.push(['spellCast', spell && spell.name, lvl]);
global.playerUseAction = (source, id) => calls.push(['use', source, id]);
global.openSpellAction = (spell) => calls.push(['openSpellGlobal', spell && spell.name]);
global.showToast = (msg) => calls.push(['toast', msg]);
global.sendWS = (msg) => calls.push(['sendWS', msg && msg.payload && msg.payload.message]);
vm.runInThisContext(fs.readFileSync('./client/static/js/character/combat_quick_actions.js', 'utf8'));
''' + script
    out = subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def test_related_action_attack_button_dispatches_attack_not_use():
    data = _node_eval(r'''
const action = { id:'wand-bolt', name:'Wand Bolt', source:'item_action', attack_bonus:'+7', damage_formula:'1d10', damage_type:'force' };
global.CombatQuickActions.__test.useRelatedMagicAction(action, 'attack');
console.log(JSON.stringify(global.__calls));
''')
    assert data[0] == ['attack', 'Wand Bolt']
    assert not any(call[0] == 'use' for call in data)


def test_related_action_damage_button_dispatches_damage_not_use():
    data = _node_eval(r'''
const action = { id:'wand-bolt', name:'Wand Bolt', source:'item_action', attack_bonus:'+7', damage_formula:'1d10', damage_type:'force' };
global.CombatQuickActions.__test.useRelatedMagicAction(action, 'damage');
console.log(JSON.stringify(global.__calls));
''')
    assert data[0] == ['damage', 'Wand Bolt']
    assert not any(call[0] == 'use' for call in data)


def test_related_action_save_button_dispatches_save_not_use():
    data = _node_eval(r'''
const action = { id:'wand-fear', name:'Wand Fear', source:'item_action', quickBarSaveText:'DC 15 WIS', save_dc:15, save_ability:'wis' };
global.CombatQuickActions.__test.useRelatedMagicAction(action, 'save');
console.log(JSON.stringify(global.__calls));
''')
    assert ['toast', 'Wand Fear: DC 15 WIS'] in data
    assert any(call[0] == 'sendWS' and 'Wand Fear' in call[1] and 'DC 15 WIS' in call[1] for call in data)
    assert not any(call[0] == 'use' for call in data)


def test_related_use_button_still_uses_opens_or_casts():
    data = _node_eval(r'''
const action = { id:'wand-open', name:'Wand Open', source:'item_action' };
global.CombatQuickActions.__test.useRelatedMagicAction(action, 'use');
console.log(JSON.stringify(global.__calls));
''')
    assert data == [['use', 'item_action', 'wand-open']]


def test_item_granted_spell_related_rolls_keep_spell_bridges():
    data = _node_eval(r'''
const spell = { id:'item_spell_fireball', name:'Fireball', source:'item', sourceType:'item', quickBarType:'spell', spellId:'fireball', baseLevel:3, level:3 };
global.CombatQuickActions.__test.useRelatedMagicAction(spell, 'attack');
global.CombatQuickActions.__test.useRelatedMagicAction(spell, 'damage');
global.CombatQuickActions.__test.useRelatedMagicAction(spell, 'save');
console.log(JSON.stringify(global.__calls.map(c => c[0])));
''')
    assert data == ['spellAttack', 'spellDamage', 'spellSave']
