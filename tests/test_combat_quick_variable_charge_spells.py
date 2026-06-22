import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_quick_actions(script: str):
    code = r'''
const fs = require('fs');
const vm = require('vm');
function makeNode(tag) {
  const node = { tagName:String(tag||'div').toUpperCase(), id:'', children:[], parentNode:null, attributes:{}, style:{}, disabled:false, value:'', _text:'', _html:'', _listeners:{},
    setAttribute(n,v){ this.attributes[n]=String(v); if(n==='id') this.id=String(v); }, getAttribute(n){ return this.attributes[n] || ''; },
    appendChild(c){ c.parentNode=this; this.children.push(c); if(c.id) document._byId[c.id]=c; return c; }, remove(){ if(this.parentNode) this.parentNode.children=this.parentNode.children.filter(x=>x!==this); if(this.id) delete document._byId[this.id]; },
    addEventListener(t,fn){ (this._listeners[t]||(this._listeners[t]=[])).push(fn); }, dispatchEvent(ev){ ev.target=ev.target||this; for(const fn of (this._listeners[ev.type]||[])) fn(ev); },
    closest(sel){ return matches(this, sel) ? this : null; }, querySelector(sel){ return walk(this).find(n=>matches(n,sel))||null; }, querySelectorAll(sel){ const parts=sel.split(',').map(s=>s.trim()); return walk(this).filter(n=>parts.some(p=>matches(n,p))); }
  };
  Object.defineProperty(node,'textContent',{ get(){return this._text;}, set(v){this._text=String(v==null?'':v);} });
  Object.defineProperty(node,'innerHTML',{ get(){return this._html;}, set(v){this._html=String(v==null?'':v); hydrate(this);} });
  return node;
}
function walk(root){ const out=[]; (function visit(n){ for(const c of n.children||[]){ out.push(c); visit(c); } })(root); return out; }
function matches(n, sel){ if(!n) return false; if(sel.startsWith('#')) return n.id===sel.slice(1); const attr=sel.match(/^\[([^\]]+)\]$/); if(attr) return Object.prototype.hasOwnProperty.call(n.attributes, attr[1]); const cls=sel.match(/^\.([a-zA-Z0-9_-]+)$/); if(cls) return String(n.attributes.class||'').split(/\s+/).includes(cls[1]); return n.tagName.toLowerCase()===sel.toLowerCase(); }
function textBetween(html, marker){ const idx=html.indexOf(marker); if(idx<0) return ''; const start=html.indexOf('>',idx)+1; const end=html.indexOf('<',start); return html.slice(start,end<0?undefined:end); }
function hydrate(root){ root.children=[]; const html=root._html||'';
  for (const id of ['combat-quick-spell-level','combat-quick-charge-cost']) if(html.includes('id="'+id+'"')) { const select=makeNode('select'); select.id=id; select.setAttribute('id', id); if(id==='combat-quick-charge-cost') select.setAttribute('data-cqa-charge-cost',''); const re=/<option value="([^"]+)"([^>]*)>([^<]*)<\/option>/g; let m; while((m=re.exec(html))){ const opt=makeNode('option'); opt.value=m[1]; opt.textContent=m[3]; opt.setAttribute('value', m[1]); if(m[2].includes('selected')) select.value=m[1]; select.appendChild(opt); } if(!select.value && select.children[0]) select.value=select.children[0].value; root.appendChild(select); document._byId[id]=select; }
  for (const attr of ['data-cqa-item-charges','data-cqa-selected-charge-cost','data-cqa-spell-details','data-cqa-damage-preview','data-cqa-slot-warning','data-cqa-cast','data-cqa-spell-damage']) if(html.includes(attr)) { const n=makeNode(attr.includes('cast')||attr.includes('damage')?'button':'div'); n.setAttribute(attr,''); n.textContent=textBetween(html, attr); if((attr==='data-cqa-cast'||attr==='data-cqa-spell-damage') && new RegExp(attr+'[^>]*disabled|disabled[^>]*'+attr).test(html)) n.disabled=true; root.appendChild(n); }
}
global.window=global; global.document={ _byId:{}, body:makeNode('body'), head:makeNode('head'), createElement:makeNode, getElementById(id){return this._byId[id]||null;}, addEventListener(){} };
global.localStorage={getItem(){return null}, setItem(){}}; global.ResizeObserver=function(){this.observe=function(){}};
global.AppSpellRuntime=require('./client/static/js/character/spell_runtime.js'); global.resolveSpellRuntime=global.AppSpellRuntime.resolveSpellRuntime;
global.getCombatSpellDamagePreview=(spell)=>spell.card&&spell.card.damage_dice||'8d6'; global._getCombatSpellCastOptions=()=>[{value:1,label:'1st',disabled:false}];
vm.runInThisContext(fs.readFileSync('./client/static/js/character/combat_quick_actions.js','utf8'));
''' + script
    out = subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def test_variable_charge_item_spell_renders_selector():
    data = run_quick_actions(r'''
const spell={id:'wand',name:'Variable Spell',sourceType:'item',quickBarVariableChargeCost:true,quickBarChargeCostMin:2,quickBarChargeCostMax:5,quickBarResourceState:{remaining:4},card:{name:'Variable Spell',level:3,damage_dice:'8d6'}};
global.CombatQuickActions.openSpellAction(spell);
const overlay=document.getElementById('combat-quick-action-modal');
console.log(JSON.stringify({hasSelector:!!document.getElementById('combat-quick-charge-cost'), charges:overlay.querySelector('[data-cqa-item-charges]').textContent, selected:overlay.querySelector('[data-cqa-selected-charge-cost]').textContent}));
''')
    assert data == {'hasSelector': True, 'charges': 'Source: Item • Charges 4 • Selected cost: 2', 'selected': '2'}


def test_variable_charge_options_are_bounded_by_min_max_and_remaining():
    data = run_quick_actions(r'''
const spell={id:'wand',name:'Variable Spell',sourceType:'item',quickBarVariableChargeCost:true,quickBarChargeCostMin:2,quickBarChargeCostMax:6,quickBarResourceState:{remaining:4},card:{name:'Variable Spell',level:3,damage_dice:'8d6'}};
global.CombatQuickActions.openSpellAction(spell);
const select=document.getElementById('combat-quick-charge-cost');
console.log(JSON.stringify({values:select.children.map(o=>o.value), disabled:document.getElementById('combat-quick-action-modal').querySelector('[data-cqa-cast]').disabled}));
''')
    assert data == {'values': ['2', '3', '4'], 'disabled': False}


def test_selected_charge_cost_is_passed_to_cast_bridge_payload():
    data = run_quick_actions(r'''
const spell={id:'wand',name:'Variable Spell',sourceType:'item',quickBarVariableChargeCost:true,quickBarChargeCostMin:1,quickBarChargeCostMax:5,quickBarResourceState:{remaining:5},card:{name:'Variable Spell',level:3,damage_dice:'8d6'}};
let call=null; global.combatQuickCastSpell=(spellArg, level, options)=>{ call={name:spellArg.name, level, chargeCost:options&&options.chargeCost}; };
global.CombatQuickActions.openSpellAction(spell);
const select=document.getElementById('combat-quick-charge-cost'); select.value='4'; select.dispatchEvent({type:'change', stopPropagation(){}});
const overlay=document.getElementById('combat-quick-action-modal'); overlay.dispatchEvent({type:'click', target: overlay.querySelector('[data-cqa-cast]'), preventDefault(){}, stopPropagation(){}});
console.log(JSON.stringify(call));
''')
    assert data == {'name': 'Variable Spell', 'level': 3, 'chargeCost': 4}


def test_fixed_charge_spell_still_works_without_charge_selector():
    data = run_quick_actions(r'''
const spell={id:'wand',name:'Fixed Spell',sourceType:'item',chargeCost:2,quickBarResourceState:{remaining:3},card:{name:'Fixed Spell',level:3,damage_dice:'8d6'}};
let call=null; global.combatQuickCastSpell=(spellArg, level, options)=>{ call={level, hasOptions:!!options}; };
global.CombatQuickActions.openSpellAction(spell);
const overlay=document.getElementById('combat-quick-action-modal'); overlay.dispatchEvent({type:'click', target: overlay.querySelector('[data-cqa-cast]'), preventDefault(){}, stopPropagation(){}});
console.log(JSON.stringify({hasSelector:!!document.getElementById('combat-quick-charge-cost'), call}));
''')
    assert data == {'hasSelector': False, 'call': {'level': 3, 'hasOptions': False}}


def test_class_spell_does_not_show_charge_ui():
    data = run_quick_actions(r'''
const spell={id:'class',name:'Class Spell',card:{name:'Class Spell',level:1,damage_dice:'1d6'}};
global.CombatQuickActions.openSpellAction(spell);
console.log(JSON.stringify({hasChargeSelector:!!document.getElementById('combat-quick-charge-cost'), hasChargeLine:!!document.getElementById('combat-quick-action-modal').querySelector('[data-cqa-item-charges]'), hasSlotSelector:!!document.getElementById('combat-quick-spell-level')}));
''')
    assert data == {'hasChargeSelector': False, 'hasChargeLine': False, 'hasSlotSelector': True}
