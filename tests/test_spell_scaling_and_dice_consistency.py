"""
Regression coverage for the spell-scaling and dice-result-consistency fixes:

  A. Cast-level scaling must apply everywhere (Spells tab virtual rows,
     Quick Actions damage preview/roll/cast, cantrip character-level scaling)
     even when imported spell-library data carries stale/absent scaling
     metadata (e.g. an explicit `scaling_type: "none"`).
  B. The dice result shown in the combat result card / chat log must always
     match the value the dice visual pipeline actually resolves to — there
     is exactly one awaitable roll pipeline (AppDice.rollExpressionAndResolve)
     that forces the 3D dice to land on the authoritative roll and only
     resolves once they have settled.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = (ROOT / 'client/templates/play.html').read_text(encoding='utf-8')


def node_eval(script: str) -> object:
    code = "const rt=require('./client/static/js/character/spell_runtime.js');\n" + script
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)



def test_resolve_spell_runtime_virtual_fireball_row_uses_base_level_before_display_level():
    data = node_eval(r'''
const row = {name:'Fireball', baseLevel:3, spell_level:3, level:4, castLevel:4, slotLevel:4, isVirtualCastRow:true};
const r4 = rt.resolveSpellRuntime(row, {castLevel: row.castLevel, slotLevel: row.slotLevel});
const r5 = rt.resolveSpellRuntime(Object.assign({}, row, {level:5, castLevel:5, slotLevel:5}), {castLevel: 5, slotLevel: 5});
console.log(JSON.stringify({r4: r4.finalDamageFormula, r5: r5.finalDamageFormula, base4: r4.baseLevel, cast4: r4.castLevel}));
''')
    assert data == {'r4': '9d6', 'r5': '10d6', 'base4': 3, 'cast4': 4}


def test_build_castable_spell_rows_virtual_rows_keep_level_as_base_level():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'fireball', name:'Fireball', baseLevel:3, source:'Wizard', sourceType:'class', usesSpellSlot:true}];
const built = rt.buildCastableSpellRows(character, known, []);
const bad = built.rows.filter(r => r.isVirtualCastRow && r.level !== r.baseLevel).map(r => ({level:r.level, baseLevel:r.baseLevel, castLevel:r.castLevel}));
const row4 = built.rows.find(r => r.name === 'Fireball' && r.castLevel === 4);
console.log(JSON.stringify({bad, row4: {level: row4.level, baseLevel: row4.baseLevel, castLevel: row4.castLevel, damagePreview: row4.damagePreview}}));
''')
    assert data['bad'] == []
    assert data['row4'] == {'level': 3, 'baseLevel': 3, 'castLevel': 4, 'damagePreview': '9d6'}


def spells_tab_eval(script: str) -> object:
    code = r'''
const fs = require('fs');
const vm = require('vm');
global.window = global;
global.document = { addEventListener() {}, createElement() { return { className:'', innerHTML:'', appendChild(){}, querySelector(){return null}, querySelectorAll(){return []}, addEventListener(){}, setAttribute(){}, getAttribute(){return ''}, classList:{add(){},remove(){},contains(){return false}} }; }, querySelector(){return null}, querySelectorAll(){return []}, getElementById(){return null} };
global.AppSpellRuntime = require('./client/static/js/character/spell_runtime.js');
vm.runInThisContext(fs.readFileSync('./client/static/js/character/tabs/spells_tab.js', 'utf8'));
''' + script
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def test_spells_tab_spell_roll_expression_for_virtual_fireball_level_4_returns_9d6():
    data = spells_tab_eval(r'''
const spell = {name:'Fireball', baseLevel:3, spell_level:3, level:4, castLevel:4, slotLevel:4, isVirtualCastRow:true};
const expr = global.SpellsTab.__test.spellRollExpressionForLevel(spell, 4, {level: 19});
console.log(JSON.stringify({expr}));
''')
    assert data['expr'] == '9d6'


def test_spells_tab_visual_dice_pipeline_uses_resolved_result_without_fallback_roll():
    data = spells_tab_eval(r'''
let fallbackRolls = 0;
let center = null;
let local = null;
global._rollDiceExpr = () => { fallbackRolls += 1; return {expression:'10d6', rolls:[1], total:1}; };
global._showCombatResultCard = (payload) => { center = payload; };
global._dicePreviewMetaFromExpr = () => ({diceType:6, qty:9, modifier:0});
global.AppDice = {
  rollExpressionAndResolve: async (expr) => ({expression:expr, rolls:[1,2,3,4,5,6,1,2,3,4], total:31, modifier:0, diceType:6, qty:10}),
  showLocalResult: (payload) => { local = payload; }
};
(async () => {
  const rolled = await global.SpellsTab.__test.rollSpellFromUi({name:'Fireball', baseLevel:3, spell_level:3, level:3, castLevel:5, slotLevel:5, isVirtualCastRow:true, damagePreview:'10d6'}, {charData:{level:19}});
  console.log(JSON.stringify({rolled, fallbackRolls, centerTotal:center && center.damage, centerRolls:center && center.damageRolls, localWasDuplicated:!!local}));
})();
''')
    assert data['rolled']['total'] == 31
    assert data['rolled']['expr'] == '10d6'
    assert data['fallbackRolls'] == 0
    assert data['centerTotal'] == 31
    assert data['centerRolls'] == [1,2,3,4,5,6,1,2,3,4]
    assert data['localWasDuplicated'] is False


def test_spells_tab_fallback_dice_pipeline_reuses_single_roll_result_for_both_cards():
    data = spells_tab_eval(r'''
let fallbackRolls = 0;
let center = null;
let local = null;
global._rollDiceExpr = () => { fallbackRolls += 1; return {expression:'9d6', rolls:[2,2,2,2,2,2,2,2,2], total:18}; };
global._showCombatResultCard = (payload) => { center = payload; };
global._dicePreviewMetaFromExpr = () => ({diceType:6, qty:9, modifier:0});
global.AppDice = { showLocalResult: (payload) => { local = payload; } };
(async () => {
  const rolled = await global.SpellsTab.__test.rollSpellFromUi({name:'Fireball', baseLevel:3, spell_level:3, level:3, castLevel:4, isVirtualCastRow:true, damagePreview:'9d6'}, {charData:{level:19}});
  console.log(JSON.stringify({rolled, fallbackRolls, centerTotal:center && center.damage, centerRolls:center && center.damageRolls, localTotal:local && local.total, localRolls:local && local.rolls}));
})();
''')
    assert data['rolled']['total'] == 18
    assert data['fallbackRolls'] == 1
    assert data['centerTotal'] == 18
    assert data['localTotal'] == 18
    assert data['centerRolls'] == data['localRolls']


# ---------------------------------------------------------------------------
# A.1 / A.3 — virtual cast rows scale at the section's slot level even when
# imported library data has scaling_type: 'none'.
# ---------------------------------------------------------------------------

def test_fireball_virtual_row_scales_despite_imported_scaling_type_none():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'fireball', name:'Fireball', baseLevel:3, source:'Wizard', sourceType:'class', usesSpellSlot:true}];
const library = [{id:'fireball', name:'Fireball', level:3, scaling_type:'none', damageFormula:'8d6'}];
const built = rt.buildCastableSpellRows(character, known, library);
const row3 = built.rows.find(r => r.name==='Fireball' && r.castLevel===3);
const row5 = built.rows.find(r => r.name==='Fireball' && r.castLevel===5);
console.log(JSON.stringify({row3: row3.damagePreview, row5: row5.damagePreview, baseLevel5: row5.baseLevel, castLevel5: row5.castLevel, displaySectionLevel5: row5.displaySectionLevel}));
''')
    assert data['row3'] == '8d6'
    assert data['row5'] == '10d6', f"Fireball under 5th Spells should roll 10d6, got {data['row5']}"
    assert data['baseLevel5'] == 3
    assert data['castLevel5'] == 5
    assert data['displaySectionLevel5'] == 5


def test_lightning_bolt_virtual_row_scales_despite_imported_scaling_type_none():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'lightning-bolt', name:'Lightning Bolt', baseLevel:3, source:'Wizard', sourceType:'class', usesSpellSlot:true}];
const library = [{id:'lightning-bolt', name:'Lightning Bolt', level:3, scaling_type:'none', damageFormula:'8d6'}];
const built = rt.buildCastableSpellRows(character, known, library);
const row5 = built.rows.find(r => r.name==='Lightning Bolt' && r.castLevel===5);
console.log(JSON.stringify({row5: row5.damagePreview}));
''')
    assert data['row5'] == '10d6'


def test_call_lightning_virtual_row_scales_despite_imported_scaling_type_none():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'call-lightning', name:'Call Lightning', baseLevel:3, source:'Druid', sourceType:'class', usesSpellSlot:true}];
const library = [{id:'call-lightning', name:'Call Lightning', level:3, scaling_type:'none', damageFormula:'3d10'}];
const built = rt.buildCastableSpellRows(character, known, library);
const row5 = built.rows.find(r => r.name==='Call Lightning' && r.castLevel===5);
console.log(JSON.stringify({row5: row5.damagePreview}));
''')
    assert data['row5'] == '5d10', f"Call Lightning under 5th Spells should roll 5d10, got {data['row5']}"


def test_scorching_ray_virtual_row_at_5th_six_rays_and_normalizes_to_12d6():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'scorching-ray', name:'Scorching Ray', baseLevel:2, source:'Sorcerer', sourceType:'class', usesSpellSlot:true}];
const built = rt.buildCastableSpellRows(character, known, []);
const row5 = built.rows.find(r => r.name==='Scorching Ray' && r.castLevel===5);
console.log(JSON.stringify({preview: row5.damagePreview, normalized: rt.normalizeRollableFormula(row5.damagePreview)}));
''')
    assert data['preview'] == '6 rays × 2d6'
    assert data['normalized'] == '12d6'


# ---------------------------------------------------------------------------
# A.6 — cantrips scale by the actual character level, even for virtual rows
# generated by the Spells tab (buildCastableSpellRows), not just the
# Quick Actions / roll-button paths that already passed characterLevel.
# ---------------------------------------------------------------------------

def test_fire_bolt_virtual_row_scales_by_character_level():
    for char_level, expected in [(1, '1d10'), (5, '2d10'), (11, '3d10'), (17, '4d10')]:
        data = node_eval(rf'''
const character = {{totalLevel: {char_level}, spellSlots: [0,4,3,3,3,3,2,1,1,1]}};
const known = [{{spellId:'fire-bolt', name:'Fire Bolt', baseLevel:0, source:'Wizard', sourceType:'class', usesSpellSlot:false}}];
const built = rt.buildCastableSpellRows(character, known, []);
const row = built.rows.find(r => r.name==='Fire Bolt');
console.log(JSON.stringify({{preview: row.damagePreview}}));
''')
        assert data['preview'] == expected, f"Fire Bolt at character level {char_level}: expected {expected}, got {data['preview']}"


# ---------------------------------------------------------------------------
# A.8 — a virtual cast row under "5th Spells" must roll using castLevel 5,
# not baseLevel 3 — confirmed via resolveSpellCast fed the row's own card
# (which carries baseLevel/spell_level == 3) and castLevel == 5.
# ---------------------------------------------------------------------------

def test_virtual_row_resolves_with_cast_level_not_base_level():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'fireball', name:'Fireball', baseLevel:3, source:'Wizard', sourceType:'class', usesSpellSlot:true}];
const built = rt.buildCastableSpellRows(character, known, []);
const row5 = built.rows.find(r => r.name==='Fireball' && r.castLevel===5);
const cast = rt.resolveSpellCast(row5.card, character, {castLevel: row5.castLevel, slotLevel: row5.slotLevel});
console.log(JSON.stringify({cardSpellLevel: row5.card.spell_level, cardLevel: row5.card.level, castLevel: cast.castLevel, formula: cast.formulaUsed}));
''')
    assert data['cardSpellLevel'] == 3
    assert data['cardLevel'] == 3
    assert data['castLevel'] == 5
    assert data['formula'] == '10d6'


# ---------------------------------------------------------------------------
# A.2 — builtin canonical level wins over a conflicting imported card level
# for known spells with a built-in definition.
# ---------------------------------------------------------------------------

def test_builtin_base_level_wins_over_conflicting_imported_card_level():
    data = node_eval(r'''
const character = {level: 19, totalLevel: 19, spellSlots: [0,4,3,3,3,3,2,1,1,1]};
const known = [{spellId:'fireball', name:'Fireball', source:'Wizard', sourceType:'class', usesSpellSlot:true}];
const library = [{id:'fireball', name:'Fireball', level:5, damageFormula:'8d6'}];
const built = rt.buildCastableSpellRows(character, known, library);
const row = built.rows.find(r => r.name==='Fireball' && r.castLevel===3);
console.log(JSON.stringify({found: !!row, baseLevel: row && row.baseLevel}));
''')
    assert data['found'], 'Fireball should still generate a 3rd-level row from its canonical builtin level'
    assert data['baseLevel'] == 3


# ---------------------------------------------------------------------------
# B — single dice-roll pipeline: AppDice.rollExpressionAndResolve exists,
# forces the visual dice to land on the authoritative roll, and resolves
# only after the dice settle. Quick Actions cast/damage flows route through
# it instead of synchronously showing a precomputed result before landing.
# ---------------------------------------------------------------------------

def test_app_dice_has_awaitable_roll_expression_and_resolve_api():
    assert 'rollExpressionAndResolve(expr, meta = {}) {' in PLAY
    assert 'function _rollExpressionAndResolveDice(expr, meta = {}) {' in PLAY
    # Forces the 3D dice to land on the authoritative computed roll.
    assert 'const targetResults = _expandDiceVisualResults(result.rolls, diceType);' in PLAY
    # Resolves the promise only from the settle callback (or timeout fallback),
    # never synchronously before the animation completes.
    assert 'onSettledResult: () => finish(),' in PLAY


def test_rolldiceexpr_fallback_preserved_for_headless_no_visual_mode():
    # _rollDiceExpr must remain available as the synchronous fallback engine.
    assert 'function _rollDiceExpr(expr) {' in PLAY
    assert 'const result = typeof _rollDiceExpr === \'function\' ? _rollDiceExpr(expr) : null;' in PLAY
    assert "if (!_diceWantsVisuals(mode) || meta.visualDisabled) {" in PLAY


def test_quick_action_damage_roll_uses_awaitable_pipeline_not_synchronous_card():
    assert 'return window.AppDice.rollExpressionAndResolve(expr, {' in PLAY
    # Result card + chat log must be built from the resolved settle payload,
    # not from a precomputed result shown before the dice land.
    assert '}).then((result) => {' in PLAY


def test_cast_spell_flow_awaits_dice_settle_before_showing_result():
    assert 'async function _executeCombatSpellCast(spell, slotLevel) {' in PLAY
    assert 'spellRoll = await window.AppDice.rollExpressionAndResolve(effectiveExpr, {' in PLAY


# ---------------------------------------------------------------------------
# A.4 — spell drawer must show the resolved (cast-level-scaled) formula,
# not the raw unscaled card formula.
# ---------------------------------------------------------------------------

def test_spell_drawer_combat_rows_prefer_resolved_formula():
    spells_tab = (ROOT / 'client/static/js/character/tabs/spells_tab.js').read_text(encoding='utf-8')
    assert "const resolvedFormula = spell.damagePreview || spell.healingPreview || spell.damageFormula || spell.healingFormula || '—';" in spells_tab
