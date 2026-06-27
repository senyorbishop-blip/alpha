"""
tests/test_combat_attention_ui.py — Tests for combat tab attention system

Covers:
- Combat tab glow CSS is defined
- YOUR TURN state CSS is defined
- _updateCombatTabAttention function exists
- combat-glow class is added/removed correctly
- YOUR TURN text appears only for active player combatant
- Glow clears when Combat tab is selected
- Dashboard combat button gets attention styling
- Character sheet Combat/Actions tab gets attention styling
- Viewer does NOT get player-only combat coach
- DM sees combat controls without player-only coach restrictions
- Movement denied messages include a help link
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _read_css() -> str:
    # CSS was extracted out of play.html into the dedicated stylesheet.
    return _read("client/static/css/play.css")


# ── CSS for glow states ────────────────────────────────────────────────────

def test_combat_glow_css_defined():
    src = _read_css()
    assert "combat-glow" in src
    assert "combat-pulse" in src


def test_combat_your_turn_css_defined():
    src = _read_css()
    assert "combat-your-turn" in src
    assert "combat-your-turn-pulse" in src
    assert "YOUR TURN" in src


def test_combat_your_turn_uses_accent_color():
    src = _read_css()
    your_turn_block_start = src.index("combat-your-turn {")
    your_turn_block = src[your_turn_block_start:your_turn_block_start + 300]
    assert "var(--accent)" in your_turn_block or "#00e5cc" in your_turn_block


def test_combat_glow_uses_danger_color():
    src = _read_css()
    glow_block_start = src.index("#rtab-combat.combat-glow {")
    glow_block = src[glow_block_start:glow_block_start + 200]
    # Should use red/danger color for generic combat glow
    assert "#e74c3c" in glow_block or "rgba(231,76,60" in glow_block


# ── JS functions ──────────────────────────────────────────────────────────

def test_update_combat_tab_attention_function_exists():
    src = _read("client/templates/play.html")
    assert "_updateCombatTabAttention" in src
    assert "function _updateCombatTabAttention" in src


def test_render_combat_coach_function_exists():
    src = _read("client/templates/play.html")
    assert "_renderCombatCoach" in src
    assert "function _renderCombatCoach" in src


def test_is_active_combat_tab_helper_exists():
    src = _read("client/templates/play.html")
    assert "_isActiveCombatTab" in src


def test_get_my_turn_combatant_helper_exists():
    src = _read("client/templates/play.html")
    assert "_getMyTurnCombatant" in src


# ── YOUR TURN only for active player ─────────────────────────────────────

def test_your_turn_only_when_my_token():
    src = _read("client/templates/play.html")
    update_fn_start = src.index("function _updateCombatTabAttention")
    update_fn = src[update_fn_start:update_fn_start + 800]
    # Should check isMyTurn AND ROLE === 'player' before adding your-turn class
    assert "isMyTurn" in update_fn
    assert "ROLE === 'player'" in update_fn
    assert "combat-your-turn" in update_fn


def test_your_turn_badge_set_on_own_combatant():
    src = _read("client/templates/play.html")
    # Find the badge update block (not the HTML element but the JS update)
    badge_idx = src.index("rtab-combat-badge")
    # Find the JS occurrence (further in the file)
    badge_js_idx = src.index("rtab-combat-badge", badge_idx + 500)
    badge_section = src[badge_js_idx:badge_js_idx + 1200]
    assert "_tokenOwnedByMe" in badge_section or "isMyBadgeTurn" in badge_section


# ── Glow clears when combat tab selected ─────────────────────────────────

def test_glow_cleared_on_combat_tab_switch():
    src = _read("client/templates/play.html")
    switch_fn_start = src.index("function switchRTab")
    switch_fn = src[switch_fn_start:switch_fn_start + 2500]
    assert "tab === 'combat'" in switch_fn
    assert "combat-glow" in switch_fn
    assert "classList.remove" in switch_fn


def test_glow_reapplied_when_leaving_combat_tab():
    src = _read("client/templates/play.html")
    switch_fn_start = src.index("function switchRTab")
    switch_fn = src[switch_fn_start:switch_fn_start + 2500]
    assert "_updateCombatTabAttention" in switch_fn


# ── Dashboard and sheet attention ─────────────────────────────────────────

def test_dashboard_combat_button_gets_attention_css():
    src = _read_css()
    assert "player-dashboard-btn--combat.combat-attention" in src
    assert "player-dashboard-btn--combat.your-turn-attention" in src


def test_dashboard_combat_button_has_attention_class_in_html():
    src = _read("client/static/js/ui/player_shell.js")
    assert "player-dashboard-btn--combat" in src


def test_sheet_combat_tab_gets_attention_css():
    src = _read_css()
    assert '.sheet-page-tab[data-page="combat"].combat-attention' in src
    assert '.sheet-page-tab[data-page="combat"].your-turn-attention' in src


def test_update_combat_attention_targets_dashboard_and_sheet():
    src = _read("client/templates/play.html")
    fn_start = src.index("function _updateCombatTabAttention")
    fn_body = src[fn_start:fn_start + 800]
    assert "player-dashboard-btn--combat" in fn_body
    assert "cb-combat-tab" in fn_body


# ── Combat ends clears all glow ───────────────────────────────────────────

def test_all_glow_cleared_on_combat_end():
    src = _read("client/templates/play.html")
    fn_start = src.index("function _updateCombatTabAttention")
    fn_body = src[fn_start:fn_start + 800]
    # When isActive is false, the else branch should not re-add glow
    assert "classList.remove('combat-glow', 'combat-your-turn'" in fn_body


# ── Viewer does not get player-only coach ─────────────────────────────────

def test_coach_only_shown_for_player_role():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 500]
    # Coach should bail out early if role is not player
    assert "ROLE === 'player'" in coach_fn or "isPlayer" in coach_fn
    assert "isPlayer" in coach_fn


def test_viewer_check_in_coach_prevents_coach():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 500]
    # Either early return or guard
    assert "if (!isPlayer" in coach_fn or "if (ROLE !== 'player'" in coach_fn or "isPlayer = ROLE" in coach_fn


# ── DM sees combat controls without player restrictions ───────────────────

def test_dm_can_see_combat_controls_regardless_of_coach():
    src = _read("client/templates/play.html")
    # combat-pre (start combat) is DM-only — must still be present
    assert 'id="combat-pre"' in src
    assert "combatStart()" in src
    # DM next/prev buttons must still exist
    assert "combatNext()" in src
    assert "combatPrev()" in src
    # Coach is player-only and won't block DM view
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 200]
    assert "ROLE === 'player'" in coach_fn or "isPlayer" in coach_fn


# ── Movement denied messages include help link ────────────────────────────

def test_movement_denied_includes_help_link():
    src = _read("client/templates/play.html")
    assert "_moveDeniedHelpLink" in src
    assert "move-denied-help" in src
    # The function must be called inside getCombatMoveRestrictionForToken
    deny_fn_start = src.index("function getCombatMoveRestrictionForToken")
    deny_fn = src[deny_fn_start:deny_fn_start + 1000]
    assert "_moveDeniedHelpLink" in deny_fn


def test_movement_denied_covers_speed_zero_case():
    src = _read("client/templates/play.html")
    deny_fn_start = src.index("function getCombatMoveRestrictionForToken")
    deny_fn = src[deny_fn_start:deny_fn_start + 1000]
    assert "no movement speed" in deny_fn or "speed <= 0" in deny_fn


def test_movement_denied_covers_no_movement_remaining():
    src = _read("client/templates/play.html")
    deny_fn_start = src.index("function getCombatMoveRestrictionForToken")
    deny_fn = src[deny_fn_start:deny_fn_start + 1500]
    assert "No movement left" in deny_fn or "no movement left" in deny_fn.lower()


def test_movement_denied_covers_not_your_turn():
    src = _read("client/templates/play.html")
    deny_fn_start = src.index("function getCombatMoveRestrictionForToken")
    deny_fn = src[deny_fn_start:deny_fn_start + 1000]
    assert "not your turn" in deny_fn.lower()


# ── Contextual hints for combat start / player turn ──────────────────────

def test_combat_start_hint_fires():
    src = _read("client/templates/play.html")
    attention_fn_start = src.index("function _updateCombatTabAttention")
    attention_fn = src[attention_fn_start:attention_fn_start + 2000]
    assert "Combat has started" in attention_fn
    assert "showCombatHint" in attention_fn


def test_player_turn_hint_fires():
    src = _read("client/templates/play.html")
    attention_fn_start = src.index("function _updateCombatTabAttention")
    attention_fn = src[attention_fn_start:attention_fn_start + 2000]
    assert "Your turn" in attention_fn
    assert "showCombatHint" in attention_fn


def test_hints_only_fire_for_player_role():
    src = _read("client/templates/play.html")
    attention_fn_start = src.index("function _updateCombatTabAttention")
    attention_fn = src[attention_fn_start:attention_fn_start + 2000]
    # The hints block must be guarded by ROLE === 'player'
    assert "ROLE === 'player'" in attention_fn
    assert "showCombatHint" in attention_fn
    # hints must come after the ROLE guard
    role_guard_idx = attention_fn.index("Contextual hints")
    hint_block = attention_fn[role_guard_idx:]
    assert "showCombatHint" in hint_block
