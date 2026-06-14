from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_actions_tab_renders_turn_economy_tracker_and_core_counters():
    src = _play_html()
    assert 'function buildTurnEconomyState(character = _charSheet, combatState = _combat, turnState = null)' in src
    assert 'turn-economy-tracker' in src
    for label in ['Action', 'Attacks', 'Bonus Action', 'Reaction', 'Movement', 'Spell Cast']:
        assert label in src
    assert 'Waiting for your turn' in src


def test_turn_economy_model_tracks_extra_attack_movement_spellcasting_and_resources():
    src = _play_html()
    assert 'attackAction: { maxSwings, usedSwings, remainingSwings' in src
    assert 'Fighter Extra Attack' in src
    assert 'movement: { speed: speed + bonusFt' in src
    assert 'speed_ft' in src and 'spent_ft' in src and 'remaining_ft' in src
    assert 'dash_used' in src and 'difficult_terrain' in src and 'disengaged' in src
    assert 'bonusActionSpellAvailable' in src
    assert 'Quickened Spell / Metamagic' in src
    assert 'Sorcery Points' in src
    assert 'normalSpellCastUsed' in src


def test_action_usage_reduces_correct_economy_and_resets_correctly():
    src = _play_html()
    assert "_consumeActionEconomy('attack_within_action', { action_id: attackId })" in src
    assert 'state.attacks_within_action_used = used;' in src
    assert 'if (used >= state.attacks_within_action_total)' in src
    assert 'state.actions_used = Math.min(state.actions_total' in src
    assert "_consumeActionEconomy('bonus_action', { action_id: id })" in src
    assert "_consumeActionEconomy('reaction', { action_id: id })" in src
    assert "_playerActionEconomyRuntime = { turn_key: '', state: null, action_surge_armed: false, usage: {} }" in src


def test_action_usage_is_keyed_by_session_round_turn_character_and_action():
    src = _play_html()
    for needle in ['session_id:', 'combat_round:', 'combat_turn:', 'character_id:', 'action_id: actionId']:
        assert needle in src
    assert '_playerActionEconomyRuntime.usage[usageKey][actionId]' in src
    assert 'Used this turn' in src


def test_action_panel_layout_density_sections_and_no_nested_scroll_traps():
    src = _play_html()
    for section in ['Recommended', 'Attacks', 'Bonus Actions', 'Reactions', 'Class Features', 'Item Actions', 'Item Spells', 'Spells', 'Passives']:
        assert section in src
    assert 'setPlayerActionsDensity' in src
    assert "localStorage.setItem('combat_actions_density'" in src
    assert "localStorage.getItem('combat_actions_density'" in src
    assert 'density-compact' in src and 'density-comfortable' in src and 'density-expanded' in src
    assert 'Open Full Combat Sheet' in src
    assert 'function openFullCombatSheet()' in src
    assert '.player-action-list {' in src
    assert 'max-height: none;' in src
    assert 'overflow: visible;' in src


def test_spell_and_item_economy_rules_do_not_treat_all_spell_attacks_as_weapon_attacks():
    src = _play_html()
    assert "else _consumeActionEconomy('action', { action_id: spellId, normal_spell_cast: true })" in src
    assert "_consumeActionEconomy('attack_within_action', { action_id: attackId })" in src
    assert "activation === 'bonus_action'" in src
    assert "activation === 'reaction'" in src
    assert "source: 'item_spell'" in src
    assert 'Costs Action or spell casting time' in src


def test_quick_bar_compatibility_and_combat_tab_glow_remain_present():
    src = _play_html()
    assert 'CombatQuickBar.render' in src
    assert 'CombatQuickSelectors.selectQuickActions' in src
    assert '#rtab-combat.combat-glow' in src
    assert '#rtab-combat.combat-your-turn::after' in src
    assert "content: 'YOUR TURN'" in src
