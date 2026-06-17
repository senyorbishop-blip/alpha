from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = (ROOT / 'client/templates/play.html').read_text(encoding='utf-8')
ACTIONS = (ROOT / 'client/static/js/character/combat_quick_actions.js').read_text(encoding='utf-8')
BAR = (ROOT / 'client/static/js/character/combat_quick_bar.js').read_text(encoding='utf-8')
RUNTIME = (ROOT / 'client/static/js/character/spell_runtime.js').read_text(encoding='utf-8')


def test_quick_actions_use_shared_resolve_spell_cast_payload_and_selected_slot():
    assert 'function resolveSpellCast(spell, characterRuntime, options = {})' in PLAY
    assert "actionSource: 'quick_actions'" in PLAY
    assert 'const resolvedCast = resolveSpellCast(spell, _charSheet || {}, { castLevel: slotLevel, slotLevel' in PLAY
    assert 'resolvedCast.formulaUsed' in PLAY
    assert 'roll_payload: resolvedCast.rollPayload' in PLAY
    for key in ['spellId', 'spellName', 'baseLevel', 'castLevel', 'slotLevel', 'formulaUsed', 'scalingApplied', 'consumedSlotLevel']:
        assert key in PLAY
    assert 'global.resolveSpellCast = global.resolveSpellCast || resolveSpellCast;' in RUNTIME
    assert 'resolveSpellCast:         resolveSpellCast' in RUNTIME


def test_quick_action_modal_level_picker_updates_preview_and_passes_cast_level():
    assert 'id="combat-quick-spell-level"' in ACTIONS
    assert "actionSource: 'quick_actions_preview'" in ACTIONS
    assert 'const resolved = global.resolveSpellCast(spell, global._charSheet || {}, {' in ACTIONS
    assert 'refreshSpellModalDamage();' in ACTIONS
    assert 'safeCastSpell(spellKey, castLevel)' in ACTIONS
    assert 'safeRollSpellDamage(spellKey, castLevel)' in ACTIONS
    assert 'safeRollSpellAttack(spellKey, castLevel)' in ACTIONS
    assert 'safeShowSpellSave(spellKey, castLevel)' in ACTIONS
    assert 'showLevelPicker = (baseLevel !== 0 && baseLevel !== null) || options.length > 1' in ACTIONS


def test_quick_action_damage_roll_uses_resolved_cast_level_payload_and_spends_selected_slot():
    assert "const resolvedCast = resolveSpellCast(spell, _charSheet || {}, { castLevel: slotLevel, slotLevel" in PLAY
    assert "const expr = resolvedCast.formulaUsed || _getCombatSpellDamageExpression(spell, slotLevel);" in PLAY
    assert "const slotSpend = _consumeSpellSlotLevel(resolvedCast.consumedSlotLevel);" in PLAY
    assert "roll_payload: resolvedCast.rollPayload" in PLAY
    assert "_combatQuickSpellCastLevelLabel(resolvedCast.castLevel)" in PLAY
    assert "spellId: rollPayload.spellId" in PLAY
    assert "damageParts" in PLAY and "healingParts" in PLAY


def test_fireball_quick_action_and_full_spells_share_runtime_formula():
    import json
    import subprocess

    script = """
const rt=require('./client/static/js/character/spell_runtime.js');
const expected = {3:'8d6',4:'9d6',8:'13d6',9:'14d6'};
const rows = {};
for (const level of [3,4,8,9]) {
  const quick = rt.resolveSpellCast({id:'fireball', name:'Fireball'}, {}, {castLevel: level, slotLevel: level, actionSource:'quick_actions'});
  const full = rt.resolveSpellRuntime({id:'fireball', name:'Fireball'}, {castLevel: level});
  rows[level] = {quick: quick.formulaUsed, full: full.finalDamageFormula, castLevel: quick.castLevel, slotLevel: quick.slotLevel};
}
console.log(JSON.stringify(rows));
"""
    rows = json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, timeout=30))
    for level, formula in {"3": "8d6", "4": "9d6", "8": "13d6", "9": "14d6"}.items():
        assert rows[level]["quick"] == formula
        assert rows[level]["full"] == formula
        assert rows[level]["castLevel"] == int(level)
        assert rows[level]["slotLevel"] == int(level)


def test_quick_bar_button_visibility_drag_persist_and_player_role():
    assert "roleCanUseQuickBar = role === 'player'" in BAR
    assert 'if (toggle) toggle.hidden = true;' in BAR
    assert 'if (toggle && roleCanUseQuickBar) toggle.hidden = false;' in BAR
    assert 'buttonX' in BAR and 'buttonY' in BAR
    assert '_startToggleDrag' in BAR and '_dragToggle' in BAR and '_stopToggleDrag' in BAR
    assert 'suppressToggleClick' in BAR
    assert '_clampPoint' in BAR
    assert '_applyTogglePosition();' in BAR
    assert 'pointer-events:auto' in BAR
    assert ':focus-visible' in BAR
