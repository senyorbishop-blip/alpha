"""
tests/test_combat_coach_ui.py — Tests for the Combat Coach checklist

Covers:
- Coach checklist HTML element is present in play.html
- Coach checklist CSS is defined
- _renderCombatCoach renders Move/Action/Bonus/Reaction/End Turn
- Class-specific hints are present for major classes
- Coach uses existing class-specific data from actions_tab.js surface
- Coach shows "End Turn" as final step
- DM still sees combat controls without coach restrictions
- Viewer does not see player-only combat controls
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _read_css() -> str:
    # CSS was extracted out of play.html into the dedicated stylesheet.
    return _read("client/static/css/play.css")


# ── HTML element ──────────────────────────────────────────────────────────

def test_combat_coach_html_element_present():
    src = _read("client/templates/play.html")
    assert 'id="combat-coach"' in src


def test_combat_coach_is_inside_combat_tab_pane():
    src = _read("client/templates/play.html")
    combat_pane_start = src.index('id="rtab-pane-combat"')
    combat_pane = src[combat_pane_start:combat_pane_start + 1000]
    assert 'id="combat-coach"' in combat_pane


# ── CSS ───────────────────────────────────────────────────────────────────

def test_coach_css_defined():
    src = _read_css()
    assert "#combat-coach {" in src
    assert ".coach-title {" in src
    assert ".coach-item {" in src


def test_coach_done_class_defined():
    src = _read_css()
    assert ".coach-item.done {" in src


def test_coach_class_hint_css_defined():
    src = _read_css()
    assert ".coach-class-hint {" in src


# ── Checklist items ───────────────────────────────────────────────────────

def test_coach_includes_move_step():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "Move" in coach_fn


def test_coach_includes_action_step():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "'Action'" in coach_fn or "label: 'Action'" in coach_fn


def test_coach_includes_bonus_action_step():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "Bonus Action" in coach_fn


def test_coach_includes_reaction_reminder():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "Reaction" in coach_fn


def test_coach_includes_end_turn_as_final_step():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "End Turn" in coach_fn


# ── Class-specific hints ──────────────────────────────────────────────────

def test_coach_has_barbarian_class_hint():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "barbarian" in coach_fn.lower()
    assert "Rage" in coach_fn


def test_coach_has_fighter_class_hint():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "fighter" in coach_fn.lower()
    assert "Action Surge" in coach_fn


def test_coach_has_rogue_class_hint():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "rogue" in coach_fn.lower()
    assert "Sneak Attack" in coach_fn


def test_coach_has_paladin_class_hint():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "paladin" in coach_fn.lower()
    assert "Divine Smite" in coach_fn


def test_coach_has_wizard_class_hint():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "wizard" in coach_fn.lower()
    assert "concentration" in coach_fn.lower()


def test_coach_has_warlock_class_hint():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "warlock" in coach_fn.lower()
    assert "Eldritch Blast" in coach_fn


# ── Role isolation ────────────────────────────────────────────────────────

def test_coach_only_shows_for_player_role():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 600]
    # Must check ROLE or isPlayer and return early for non-players
    assert "ROLE === 'player'" in coach_fn or "isPlayer" in coach_fn
    assert "return" in coach_fn  # early return / bail


def test_dm_controls_still_present():
    """DM combat controls exist independently of the coach."""
    src = _read("client/templates/play.html")
    assert "combatStart()" in src
    assert "combatNext()" in src
    assert "combatPrev()" in src
    assert "combatEndTurn()" in src
    assert "combatClear()" in src


def test_viewer_cannot_access_end_turn_button():
    """End Turn is guarded for player/DM only."""
    src = _read("client/templates/play.html")
    # End Turn rendering uses canEndTurn guard which checks player or DM
    assert "canEndTurn" in src
    # The guard checks ROLE === 'dm' or canPlayerAct
    end_turn_area = src[src.index("canEndTurn"):src.index("canEndTurn") + 300]
    assert "ROLE === 'dm'" in end_turn_area or "canPlayerAct" in end_turn_area


# ── Help link from coach ──────────────────────────────────────────────────

def test_coach_links_to_help_hub():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 5000]
    assert "showHelpHub" in coach_fn


# ── Movement summary in coach ─────────────────────────────────────────────

def test_coach_shows_movement_remaining():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    assert "remaining" in coach_fn.lower()
    assert "ft" in coach_fn


def test_coach_uses_server_movement_state():
    src = _read("client/templates/play.html")
    coach_fn_start = src.index("function _renderCombatCoach")
    coach_fn = src[coach_fn_start:coach_fn_start + 4000]
    # Must read from _combat.movement
    assert "_combat" in coach_fn
    assert "spent_ft" in coach_fn or "spentFt" in coach_fn
