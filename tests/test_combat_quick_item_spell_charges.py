import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_quick_actions(script: str):
    code = r'''
const fs = require('fs');
const vm = require('vm');

function makeNode(tag) {
  const node = {
    tagName: String(tag || 'div').toUpperCase(),
    id: '',
    children: [],
    parentNode: null,
    attributes: {},
    style: {},
    disabled: false,
    value: '',
    _text: '',
    _html: '',
    setAttribute(name, value) { this.attributes[name] = String(value); if (name === 'id') this.id = String(value); },
    getAttribute(name) { return this.attributes[name] || ''; },
    appendChild(child) { child.parentNode = this; this.children.push(child); if (child.id) document._byId[child.id] = child; return child; },
    remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(c => c !== this); if (this.id) delete document._byId[this.id]; },
    addEventListener() {},
    closest(selector) { return matches(this, selector) ? this : null; },
    querySelector(selector) { return walk(this).find(n => matches(n, selector)) || null; },
    querySelectorAll(selector) { const parts = selector.split(',').map(s => s.trim()); return walk(this).filter(n => parts.some(p => matches(n, p))); },
  };
  Object.defineProperty(node, 'textContent', { get() { return this._text; }, set(v) { this._text = String(v == null ? '' : v); } });
  Object.defineProperty(node, 'innerHTML', { get() { return this._html; }, set(v) { this._html = String(v == null ? '' : v); hydrate(this); } });
  return node;
}
function walk(root) { const out = []; (function visit(n){ for (const c of n.children || []) { out.push(c); visit(c); } })(root); return out; }
function matches(node, selector) {
  if (!node) return false;
  if (selector.startsWith('#')) return node.id === selector.slice(1);
  const attr = selector.match(/^\[([^\]]+)\]$/);
  if (attr) return Object.prototype.hasOwnProperty.call(node.attributes, attr[1]);
  return false;
}
function textBetween(html, marker) {
  const idx = html.indexOf(marker);
  if (idx < 0) return '';
  const start = html.indexOf('>', idx) + 1;
  const end = html.indexOf('<', start);
  return html.slice(start, end < 0 ? undefined : end);
}
function hydrate(root) {
  root.children = [];
  const html = root._html || '';
  if (html.includes('id="combat-quick-spell-level"')) {
    const select = makeNode('select');
    select.id = 'combat-quick-spell-level';
    select.value = (html.match(/<option value="([^"]+)"[^>]*selected/) || html.match(/<option value="([^"]+)"/i) || ['', ''])[1];
    root.appendChild(select);
    document._byId[select.id] = select;
  }
  for (const attr of ['data-cqa-spell-details', 'data-cqa-damage-preview', 'data-cqa-slot-warning', 'data-cqa-cast', 'data-cqa-spell-damage']) {
    if (html.includes(attr)) {
      const n = makeNode(attr.includes('button') || attr.includes('cast') || attr.includes('damage') ? 'button' : 'div');
      n.setAttribute(attr, '');
      if (attr === 'data-cqa-slot-warning') n.textContent = textBetween(html, attr);
      if (attr === 'data-cqa-damage-preview') n.textContent = textBetween(html, attr);
      if ((attr === 'data-cqa-cast' || attr === 'data-cqa-spell-damage') && new RegExp(attr + '[^>]*disabled|disabled[^>]*' + attr).test(html)) n.disabled = true;
      root.appendChild(n);
    }
  }
}

global.window = global;
global.document = {
  _byId: {},
  body: makeNode('body'),
  head: makeNode('head'),
  createElement(tag) { return makeNode(tag); },
  getElementById(id) { return this._byId[id] || null; },
  addEventListener() {},
};
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.ResizeObserver = function(){ this.observe = function(){}; };
global.AppSpellRuntime = require('./client/static/js/character/spell_runtime.js');
global.resolveSpellRuntime = global.AppSpellRuntime.resolveSpellRuntime;
global.getCombatSpellDamagePreview = function(spell, level) { return spell.damage || (spell.card && spell.card.damage_dice) || (Number(level) > 0 ? (level + 'd6') : '1d10'); };
global._getCombatSpellCastOptions = function(spell) {
  global.__spellCastOptionsCalls = (global.__spellCastOptionsCalls || 0) + 1;
  if (spell && spell.name === 'Class Spell') return [{value: 1, label: '1st (1/2 slots)', disabled: false}];
  if (spell && spell.name === 'Cantrip') return [{value: 0, label: 'Cantrip', disabled: false}];
  return [{value: 3, label: '3rd (0/0 slots)', disabled: true}];
};
vm.runInThisContext(fs.readFileSync('./client/static/js/character/combat_quick_actions.js', 'utf8'));
''' + script
    out = subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def test_item_granted_spell_with_enough_charges_remains_enabled_after_refresh():
    data = run_quick_actions(r'''
const spell = {id:'wand-fireball', name:'Item Fireball', sourceType:'item', chargeCost:2, quickBarResourceState:{remaining:3}, card:{name:'Fireball', level:3, damage_dice:'8d6'}};
global.CombatQuickActions.openSpellAction(spell);
global.__spellCastOptionsCalls = 0;
global.CombatQuickActions.refreshSpellModalDamage();
const overlay = document.getElementById('combat-quick-action-modal');
console.log(JSON.stringify({
  calls: global.__spellCastOptionsCalls || 0,
  castDisabled: overlay.querySelector('[data-cqa-cast]').disabled,
  damageDisabled: overlay.querySelector('[data-cqa-spell-damage]').disabled,
  warning: overlay.querySelector('[data-cqa-slot-warning]').textContent,
  preview: overlay.querySelector('[data-cqa-damage-preview]').textContent
}));
''')
    assert data == {'calls': 0, 'castDisabled': False, 'damageDisabled': False, 'warning': '', 'preview': '8d6'}


def test_item_granted_spell_with_insufficient_charges_disables_and_warns():
    data = run_quick_actions(r'''
const spell = {id:'wand-fireball', name:'Item Fireball', sourceType:'item', chargeCost:4, quickBarResourceState:{remaining:1}, card:{name:'Fireball', level:3, damage_dice:'8d6'}};
global.CombatQuickActions.openSpellAction(spell);
global.CombatQuickActions.refreshSpellModalDamage();
const overlay = document.getElementById('combat-quick-action-modal');
console.log(JSON.stringify({
  castDisabled: overlay.querySelector('[data-cqa-cast]').disabled,
  damageDisabled: overlay.querySelector('[data-cqa-spell-damage]').disabled,
  warning: overlay.querySelector('[data-cqa-slot-warning]').textContent,
  preview: overlay.querySelector('[data-cqa-damage-preview]').textContent
}));
''')
    assert data == {'castDisabled': True, 'damageDisabled': True, 'warning': 'Not enough item charges', 'preview': '8d6'}


def test_class_spell_still_uses_spell_slots():
    data = run_quick_actions(r'''
const spell = {id:'class-spell', name:'Class Spell', card:{name:'Class Spell', level:1, damage_dice:'1d6'}};
global.__spellCastOptionsCalls = 0;
global.CombatQuickActions.openSpellAction(spell);
global.CombatQuickActions.refreshSpellModalDamage();
const overlay = document.getElementById('combat-quick-action-modal');
console.log(JSON.stringify({
  calls: global.__spellCastOptionsCalls || 0,
  hasPicker: !!document.getElementById('combat-quick-spell-level'),
  castDisabled: overlay.querySelector('[data-cqa-cast]').disabled,
  warning: overlay.querySelector('[data-cqa-slot-warning]').textContent
}));
''')
    assert data['calls'] >= 2
    assert data['hasPicker'] is True
    assert data['castDisabled'] is False
    assert data['warning'] == ''


def test_cantrip_still_works():
    data = run_quick_actions(r'''
const spell = {id:'cantrip', name:'Cantrip', card:{name:'Cantrip', level:0, damage_dice:'1d10'}};
global.CombatQuickActions.openSpellAction(spell);
global.CombatQuickActions.refreshSpellModalDamage();
const overlay = document.getElementById('combat-quick-action-modal');
console.log(JSON.stringify({
  hasPicker: !!document.getElementById('combat-quick-spell-level'),
  castDisabled: overlay.querySelector('[data-cqa-cast]').disabled,
  damageDisabled: overlay.querySelector('[data-cqa-spell-damage]').disabled,
  warning: overlay.querySelector('[data-cqa-slot-warning]').textContent
}));
''')
    assert data == {'hasPicker': False, 'castDisabled': False, 'damageDisabled': False, 'warning': ''}


def test_refresh_slots_does_not_create_or_require_slot_picker_for_item_spells():
    data = run_quick_actions(r'''
const spell = {id:'wand-fireball', name:'Item Fireball', sourceType:'item', chargeCost:1, quickBarResourceState:{remaining:1}, card:{name:'Fireball', level:3, damage_dice:'8d6'}};
global.CombatQuickActions.openSpellAction(spell);
global.__spellCastOptionsCalls = 0;
global.CombatQuickActions.refreshSpellModalSlots();
const overlay = document.getElementById('combat-quick-action-modal');
console.log(JSON.stringify({
  calls: global.__spellCastOptionsCalls || 0,
  hasPicker: !!document.getElementById('combat-quick-spell-level'),
  castDisabled: overlay.querySelector('[data-cqa-cast]').disabled,
  damageDisabled: overlay.querySelector('[data-cqa-spell-damage]').disabled,
  warning: overlay.querySelector('[data-cqa-slot-warning]').textContent
}));
''')
    assert data == {'calls': 0, 'hasPicker': False, 'castDisabled': False, 'damageDisabled': False, 'warning': ''}
