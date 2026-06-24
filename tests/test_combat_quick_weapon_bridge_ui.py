from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_combat_quick_bar_passes_full_action_object_to_weapon_bridge():
    bar = _read('client/static/js/character/combat_quick_bar.js')
    assert "global.openCombatQuickBarWeaponAction(action)" in bar
    assert "/^(weapon|equip_only|system_unarmed|attack)$/i.test(actionSource)" in bar
    assert "openCombatQuickBarWeaponAction is missing. No action spent." in bar


def test_open_combat_quick_bar_weapon_action_bridges_to_combat_quick_actions():
    play = _read('client/templates/play.html')
    actions = _read('client/static/js/character/combat_quick_actions.js')
    # play.html no longer declares its own bare openCombatQuickBarWeaponAction —
    # that name is reserved for the public window bridge installed below, and the
    # implementation lives in performOpenCombatQuickBarWeaponAction instead.
    assert 'function openCombatQuickBarWeaponAction(action)' not in play
    assert 'function performOpenCombatQuickBarWeaponAction(action)' in play
    assert 'return window.CombatQuickActions.openWeaponAction(action);' in play
    # combat_quick_actions.js also installs its own explicit bridge so the
    # quick bar can reach the modal even if play.html's copy is unavailable.
    assert 'global.openCombatQuickBarWeaponAction = function openCombatQuickBarWeaponActionBridge(action)' in actions
    assert 'global.CombatQuickActions.openWeaponAction(action)' in actions


def test_open_weapon_action_passes_full_card_object_to_roll_helpers():
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert 'rollQuickWeaponAttack(_ctxForMode(weaponContext, mode));' in actions
    assert 'rollQuickWeaponDamage(_ctxForMode(weaponContext, mode));' in actions
    assert 'rollQuickWeaponCriticalDamage(_ctxForMode(weaponContext, mode));' in actions
    # The fragile id/name-only key must be gone.
    assert 'const weaponKey = card.id || card.name;' not in actions


def test_combat_quick_weapon_attack_and_damage_accept_full_objects():
    play = _read('client/templates/play.html')
    # The actual implementations are named performCombatQuick* so the public
    # window.combatQuick* bridges (registered separately) never recurse into
    # themselves when calling the "real" implementation.
    assert 'function performCombatQuickWeaponAttack(actionOrId, mode = \'base\')' in play
    assert 'function performCombatQuickRollWeaponDamage(actionOrId, mode = \'base\', critical = false)' in play
    assert 'const card = findCombatWeapon(actionOrId);' in play
    assert 'bonus = Number(card.attack_bonus_value ?? 0);' in play
    assert "_consumeActionEconomy('attack_within_action', { action_id: card.id || card.name });" in play
    # The public bridges must call the perform* implementation, not themselves.
    assert "guardQuickActionBridge('combatQuickWeaponAttack', () => performCombatQuickWeaponAttack(actionOrId, mode))" in play
    assert "guardQuickActionBridge('combatQuickRollWeaponDamage', () => performCombatQuickRollWeaponDamage(actionOrId, mode, critical))" in play


def test_find_combat_weapon_is_a_shared_lookup_supporting_objects_ids_and_names():
    play = _read('client/templates/play.html')
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert 'function findCombatWeapon(input)' in play
    assert 'window.findCombatWeapon = findCombatWeapon;' in play
    assert '_getUnifiedQuickAttackCards' in play
    assert 'model.primaryActions || []' in play
    assert 'model.bonusActions || []' in play
    assert 'model.reactions || []' in play
    assert '_combatQuickWeaponMatchKeys' in play
    # combat_quick_actions.js should prefer the shared lookup over its local one.
    assert 'global.findCombatWeapon(actionOrId)' in actions


def test_used_this_turn_weapon_still_opens_modal_with_explanation():
    actions = _read('client/static/js/character/combat_quick_actions.js')
    bar = _read('client/static/js/character/combat_quick_bar.js')
    assert 'const usedThisTurn = weaponContext.usedThisTurn;' in actions
    assert 'function normalizeWeaponModalContext(card, actionOrId)' in actions
    assert 'Used this turn — attack roll is disabled' in actions
    assert "(usedThisTurn ? 'disabled title=\"Used this turn\"' : '')" in actions
    # is-used must not be conflated with is-disabled in the quick bar tile click guard.
    assert "if (!tile || tile.disabled || tile.classList.contains('is-disabled')) return;" in bar
    assert "classes.push('is-used');" in bar
    assert "function _actionMatchKeys(action)" in bar
    assert "action && action.itemId" in bar
    assert "action && action.actionId" in bar


def test_missing_weapon_bridge_shows_toast_and_does_not_spend_action():
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert "function _requireBridge(name) {" in actions
    assert "const msg = 'Quick action is not wired: ' + name + ' missing.';" in actions
    assert "if (typeof global.showToast === 'function') global.showToast(msg);" in actions
    assert 'function rollQuickWeaponAttack(ctx) {' in actions
    assert "if (_requireBridge('rollQuickWeaponAttack')) return global.rollQuickWeaponAttack(ctx);" in actions


def test_weapon_pipeline_installs_scoped_first_text_fallback_and_canonical_id():
    play = _read('client/templates/play.html')
    actions = _read('client/static/js/character/combat_quick_actions.js')
    selectors = _read('client/static/js/character/combat_quick_selectors.js')
    assert 'function _combatQuickCanonicalWeaponActionId(obj)' in play
    assert 'window._firstText = window._firstText || firstText;' in play
    assert 'action_id: id' in play
    assert 'combatCardId: id' in play
    assert 'const canonicalId = (typeof global._combatQuickCanonicalWeaponActionId === \'function\')' in actions
    assert 'id: canonicalId' in actions
    assert 'actionId: canonicalId' in actions
    assert 'action_id: canonicalId' in actions
    assert 'const actionId = (typeof global._combatQuickCanonicalWeaponActionId === \'function\')' in selectors
    assert 'quickBarPickKey: \'action:\' + String(actionId)' in selectors


def test_weapon_missing_metadata_errors_include_action_id_and_item_name():
    play = _read('client/templates/play.html')
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert 'Weapon attack not found for action ' in play
    assert 'Missing weapon damage metadata' in play
    assert "const actionId = firstText(card.action_id, card.actionId, card.id" in play
    assert "`${card.name || 'Weapon'} (${actionId}) has no damage formula" in play
    assert '[CombatQuickActions] Weapon damage metadata missing for modal.' in actions


def test_weapon_attack_uses_canonical_action_id_for_roll_and_usage():
    play = _read('client/templates/play.html')
    fn_start = play.index('async function performCombatQuickWeaponAttack(')
    fn_body = play[fn_start:fn_start + 5000]
    assert "const actionKey = String(card.action_id || card.id || card.name" in fn_body
    assert "const actionId = _generateAttackActionId(card.action_id || card.id || 'weapon-attack');" in fn_body
    assert "const attackId = card.action_id || card.id || card.name;" in fn_body
    assert "_consumeActionEconomy('attack_within_action', { action_id: card.action_id || card.id || card.name });" in fn_body
