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
    assert 'function openCombatQuickBarWeaponAction(action)' in play
    assert 'return window.CombatQuickActions.openWeaponAction(action);' in play
    # combat_quick_actions.js also installs its own explicit bridge so the
    # quick bar can reach the modal even if play.html's copy is unavailable.
    assert 'global.openCombatQuickBarWeaponAction = function (action)' in actions
    assert 'global.CombatQuickActions.openWeaponAction(action)' in actions


def test_open_weapon_action_passes_full_card_object_to_roll_helpers():
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert 'safeWeaponAttack(card, mode);' in actions
    assert 'safeWeaponDamage(card, mode, false);' in actions
    assert 'safeWeaponDamage(card, mode, true);' in actions
    # The fragile id/name-only key must be gone.
    assert 'const weaponKey = card.id || card.name;' not in actions


def test_combat_quick_weapon_attack_and_damage_accept_full_objects():
    play = _read('client/templates/play.html')
    assert 'function combatQuickWeaponAttack(actionOrId, mode = \'base\')' in play
    assert 'function combatQuickRollWeaponDamage(actionOrId, mode = \'base\', critical = false)' in play
    assert 'const card = findCombatWeapon(actionOrId);' in play
    assert 'bonus = Number(card.attack_bonus_value ?? 0);' in play
    assert "_consumeActionEconomy('attack_within_action', { action_id: card.id || card.name });" in play


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
    assert 'const usedThisTurn = !!((actionOrId && typeof actionOrId === \'object\' && actionOrId.quickBarUsedThisTurn) || card.quickBarUsedThisTurn);' in actions
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
    assert 'function safeWeaponAttack(cardOrIdOrName, mode) {' in actions
    assert "if (_requireBridge('combatQuickWeaponAttack')) global.combatQuickWeaponAttack(cardOrIdOrName, mode);" in actions
