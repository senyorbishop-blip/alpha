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
    assert 'refreshSpellModalDamage();' in ACTIONS
    assert 'safeCastSpell(spellKey, castLevel)' in ACTIONS
    assert 'safeRollSpellDamage(spellKey, castLevel)' in ACTIONS
    assert 'safeRollSpellAttack(spellKey, castLevel)' in ACTIONS
    assert 'safeShowSpellSave(spellKey, castLevel)' in ACTIONS
    assert 'showLevelPicker = (baseLevel !== 0 && baseLevel !== null) || options.length > 1' in ACTIONS


def test_quick_bar_button_visibility_drag_persist_and_dm_player_roles():
    assert 'roleCanUseQuickBar = role === \'player\' || role === \'dm\'' in BAR
    assert 'if (toggle) toggle.hidden = true;' in BAR
    assert 'if (toggle && roleCanUseQuickBar) toggle.hidden = false;' in BAR
    assert 'buttonX' in BAR and 'buttonY' in BAR
    assert '_startToggleDrag' in BAR and '_dragToggle' in BAR and '_stopToggleDrag' in BAR
    assert 'suppressToggleClick' in BAR
    assert '_clampPoint' in BAR
    assert '_applyTogglePosition();' in BAR
    assert 'pointer-events:auto' in BAR
    assert ':focus-visible' in BAR
