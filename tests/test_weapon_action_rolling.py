"""
Tests for weapon and item action rolling safety and correctness.

Covers:
- Missing bridge functions show toast and do not spend action
- Thunder Mage Quarterstaff / magic weapon bonus applies to attack and damage
- Action economy is only consumed after a successful roll
- Result popup stays visible 20 seconds with click-to-dismiss
- Results are logged to chat
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


# ── Bridge guard tests ────────────────────────────────────────────────────────

def test_missing_weapon_ui_bridge_shows_toast_not_silent_spend():
    """openCombatQuickBarWeaponAction must show a toast when CombatQuickActions is missing."""
    play = _read('client/templates/play.html')
    assert 'Weapon action UI is not loaded. No action spent.' in play


def test_missing_weapon_ui_bridge_logs_error():
    """openCombatQuickBarWeaponAction must log a clear error when the modal is unavailable."""
    play = _read('client/templates/play.html')
    assert 'CombatQuickActions modal not available' in play


def test_missing_weapon_ui_bridge_does_not_silently_call_attack():
    """openCombatQuickBarWeaponAction must NOT fall back to combatQuickWeaponAttack (which skips the modal)."""
    actions = _read('client/static/js/character/combat_quick_actions.js')
    fn_start = actions.index('function performOpenCombatQuickBarWeaponAction(')
    fn_end = actions.index('\n  function ', fn_start + 100) if '\n  function ' in actions[fn_start + 100:] else fn_start + 1000
    fn_body = actions[fn_start:fn_end]
    # The fallback path must NOT call combatQuickWeaponAttack
    assert 'return combatQuickWeaponAttack(id)' not in fn_body
    assert 'combatQuickWeaponAttack(id)' not in fn_body


def test_quick_bar_weapon_source_shows_toast_when_bridge_missing():
    """combat_quick_bar.js must not fall through to playerUseAction for weapon sources when bridge is missing."""
    src = _read('client/static/js/character/combat_quick_bar.js')
    assert 'openCombatQuickBarWeaponAction is missing. No action spent.' in src
    assert 'Weapon roll handler is not loaded. No action spent.' in src


def test_quick_bar_weapon_source_separated_from_playeruseaction_fallback():
    """Weapon source check must be a distinct branch, not merged with playerUseAction else-if."""
    src = _read('client/static/js/character/combat_quick_bar.js')
    weapon_guard_idx = src.index('/^(weapon|equip_only|system_unarmed|attack)$/i.test(actionSource)')
    playeruse_idx = src.index('playerUseAction(')
    # The weapon branch (with its own else for missing bridge) must come before playerUseAction
    assert weapon_guard_idx < playeruse_idx
    # The closing brace of the weapon branch and '} else if' must appear between them
    section = src[weapon_guard_idx:playeruse_idx]
    assert '} else if' in section


# ── Action economy timing tests ───────────────────────────────────────────────

def test_action_economy_spent_after_result_card_not_before():
    """combatQuickWeaponAttack must call _consumeActionEconomy AFTER _showCombatResultCard."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickWeaponAttack(')
    fn_body = play[fn_start:fn_start + 6000]
    result_card_pos = fn_body.find('_showCombatResultCard(')
    economy_pos = fn_body.find("_consumeActionEconomy('attack_within_action'")
    assert result_card_pos > 0, '_showCombatResultCard must be present in combatQuickWeaponAttack'
    assert economy_pos > 0, '_consumeActionEconomy must be present in combatQuickWeaponAttack'
    assert economy_pos > result_card_pos, \
        '_consumeActionEconomy must be called AFTER _showCombatResultCard'


def test_roll_error_caught_and_action_not_spent():
    """combatQuickWeaponAttack must wrap the roll in try/catch and not spend on failure."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickWeaponAttack(')
    fn_body = play[fn_start:fn_start + 6000]
    assert 'try {' in fn_body
    assert 'catch (err)' in fn_body
    assert 'no action spent' in fn_body.lower()


def test_roll_failure_shows_error_toast():
    """combatQuickWeaponAttack catch block must show a toast about the failure."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickWeaponAttack(')
    fn_body = play[fn_start:fn_start + 6000]
    assert 'Attack roll failed' in fn_body


# ── Result popup persistence tests ───────────────────────────────────────────

def test_combat_result_card_auto_hides_after_20_seconds():
    """_showCombatResultCard must use a 20-second auto-dismiss timer."""
    play = _read('client/templates/play.html')
    assert '_hideCombatResultCard, 20000' in play


def test_combat_result_card_has_click_to_dismiss():
    """_showCombatResultCard must attach a click-to-dismiss listener."""
    play = _read('client/templates/play.html')
    assert 'Click to dismiss' in play
    fn_start = play.index('function _showCombatResultCard(')
    fn_body = play[fn_start:fn_start + 3000]
    assert '_hideCombatResultCard' in fn_body
    assert "addEventListener('click'" in fn_body


def test_weapon_damage_roll_shows_combat_result_card():
    """combatQuickRollWeaponDamage must call _showCombatResultCard so result stays 20s."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickRollWeaponDamage(')
    fn_end = play.index('\nfunction ', fn_start + 100)
    fn_body = play[fn_start:fn_end]
    assert '_showCombatResultCard(' in fn_body


def test_spell_attack_roll_shows_combat_result_card():
    """combatQuickRollSpellAttack must call _showCombatResultCard so result stays 20s."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function combatQuickRollSpellAttack(')
    fn_end = play.index('\nfunction ', fn_start + 100)
    fn_body = play[fn_start:fn_end]
    assert '_showCombatResultCard(' in fn_body


def test_spell_damage_roll_shows_combat_result_card():
    """combatQuickRollSpellDamage must call _showCombatResultCard so result stays 20s."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickRollSpellDamage(')
    fn_end = play.index('\nfunction ', fn_start + 100)
    fn_body = play[fn_start:fn_end]
    assert '_showCombatResultCard(' in fn_body


# ── Chat log tests ────────────────────────────────────────────────────────────

def test_weapon_attack_result_logged_to_chat():
    """combatQuickWeaponAttack must send a chat_message after rolling."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickWeaponAttack(')
    fn_body = play[fn_start:fn_start + 6000]
    assert "sendWS({ type: 'chat_message'" in fn_body


def test_weapon_damage_result_logged_to_chat():
    """combatQuickRollWeaponDamage must send a chat_message after rolling."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickRollWeaponDamage(')
    fn_end = play.index('\nfunction ', fn_start + 100)
    fn_body = play[fn_start:fn_end]
    assert "sendWS({ type: 'chat_message'" in fn_body


# ── Magic weapon bonus tests ──────────────────────────────────────────────────

def test_magic_weapon_bonus_included_in_attack_bonus_value():
    """_buildEquippedInventoryAttackCard must add magic_bonus to attack_bonus_value."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function _buildEquippedInventoryAttackCard(')
    fn_body = play[fn_start:fn_start + 3000]
    assert 'magicBonus' in fn_body
    assert 'attackBonusValue = prof + abilityMod + magicBonus' in fn_body


def test_magic_weapon_bonus_included_in_damage_formula():
    """_buildEquippedInventoryAttackCard must add magic_bonus to damage formula modifier."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function _buildEquippedInventoryAttackCard(')
    fn_body = play[fn_start:fn_start + 3000]
    assert 'abilityMod + magicBonus' in fn_body


def test_magic_weapon_bonus_preserved_on_card():
    """_buildEquippedInventoryAttackCard must preserve magic_bonus field on the returned card."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function _buildEquippedInventoryAttackCard(')
    fn_end = play.index('\nfunction ', fn_start + 100)
    fn_body = play[fn_start:fn_end]
    assert 'magic_bonus: magicBonus' in fn_body


def test_resolve_weapon_runtime_applies_magic_bonus():
    """resolveWeaponRuntime must extract magic_bonus and include it in the return value."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function resolveWeaponRuntime(')
    fn_body = play[fn_start:fn_start + 2000]
    assert 'magicBonus' in fn_body
    assert 'magic_bonus' in fn_body


# ── Critical hit tests ────────────────────────────────────────────────────────

def test_crit_formula_doubles_weapon_dice():
    """Critical damage must double weapon dice (chunk.qty * 2) with flat modifier added once."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickWeaponAttack(')
    fn_body = play[fn_start:fn_start + 6000]
    assert 'chunk.qty * 2' in fn_body


def test_crit_formula_doubles_dice_in_standalone_roll():
    """combatQuickRollWeaponDamage crit path must also double dice."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function performCombatQuickRollWeaponDamage(')
    fn_end = play.index('\nfunction ', fn_start + 100)
    fn_body = play[fn_start:fn_end]
    assert '_combatQuickCriticalFormula(displayedFormula)' in fn_body
    crit_start = play.index('function _combatQuickCriticalFormula(')
    crit_body = play[crit_start:crit_start + 500]
    assert '* 2' in crit_body


# ── Resolver field completeness test ─────────────────────────────────────────

def test_resolve_weapon_runtime_returns_all_required_fields():
    """resolveWeaponRuntime must return all spec-required fields."""
    play = _read('client/templates/play.html')
    fn_start = play.index('function resolveWeaponRuntime(')
    fn_end = play.index('\nwindow.resolveWeaponRuntime', fn_start)
    fn_body = play[fn_start:fn_end]
    for field in [
        'weaponId', 'name', 'attackBonus', 'damageFormula', 'versatileDamageFormula',
        'criticalDamageFormula', 'damageType', 'properties', 'costsAttackSwing',
        'source', 'warnings',
    ]:
        assert field in fn_body, f'resolveWeaponRuntime missing required field: {field}'
