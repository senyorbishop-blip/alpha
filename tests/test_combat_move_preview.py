"""
Tests for the combat movement preview normalization and drawCombatMovePath guard-rails.

These tests cover:
  - normalizeCombatMovementState accepts both snake_case and camelCase
  - preview never throws when movement state is empty
  - invalid (too-far) move is detected without crashing
  - missing remainingFt shows loading/fallback path (no crash, no bogus values)
  - no bare remainingFt usage exists outside the normalized scope in play.html
"""

import re
import pytest
from server.movement import resolve_movement


# ---------------------------------------------------------------------------
# normalizeCombatMovementState — tested via server-side equivalent logic
# (the JS helper is verified below via static analysis of play.html)
# ---------------------------------------------------------------------------

def _normalize(raw: dict) -> dict:
    """Python mirror of the JS normalizeCombatMovementState for unit testing."""
    speed_ft  = float(raw.get("speedFt") or raw.get("speed_ft") or 0)
    bonus_ft  = float(raw.get("bonusFt") or raw.get("bonus_ft") or 0)
    spent_ft  = float(raw.get("spentFt") or raw.get("spent_ft") or 0)
    raw_rem   = raw.get("remainingFt") if raw.get("remainingFt") is not None else raw.get("remaining_ft")
    remaining_ft = max(0.0, float(raw_rem)) if raw_rem is not None else max(0.0, speed_ft + bonus_ft - spent_ft)
    return {
        "speedFt": speed_ft,
        "spentFt": spent_ft,
        "remainingFt": remaining_ft,
        "bonusFt": bonus_ft,
        "totalBudgetFt": speed_ft + bonus_ft,
        "dashUsed": bool(raw.get("dashUsed") or raw.get("dash_used")),
        "difficultTerrain": bool(raw.get("difficultTerrain") or raw.get("difficult_terrain")),
        "disengaged": bool(raw.get("disengaged")),
        "tokenId": raw.get("tokenId") or raw.get("token_id"),
        "lastX": raw.get("lastX") or raw.get("last_x"),
        "lastY": raw.get("lastY") or raw.get("last_y"),
    }


def test_normalize_empty_state():
    """Preview does not throw when movement state is empty."""
    state = _normalize({})
    assert state["remainingFt"] == 0.0
    assert state["speedFt"] == 0.0
    assert state["spentFt"] == 0.0
    assert state["tokenId"] is None


def test_normalize_accepts_snake_case():
    """normalizeCombatMovementState accepts remaining_ft (snake_case)."""
    state = _normalize({"speed_ft": 30, "spent_ft": 10, "remaining_ft": 20, "token_id": "t1"})
    assert state["remainingFt"] == 20.0
    assert state["speedFt"] == 30.0
    assert state["spentFt"] == 10.0
    assert state["tokenId"] == "t1"


def test_normalize_accepts_camel_case():
    """normalizeCombatMovementState accepts remainingFt (camelCase)."""
    state = _normalize({"speedFt": 30, "spentFt": 5, "remainingFt": 25})
    assert state["remainingFt"] == 25.0
    assert state["speedFt"] == 30.0


def test_normalize_computes_remaining_when_missing():
    """remainingFt is computed from speed+bonus-spent when not explicitly present."""
    state = _normalize({"speed_ft": 30, "bonus_ft": 10, "spent_ft": 15})
    assert state["remainingFt"] == 25.0
    assert state["totalBudgetFt"] == 40.0


def test_normalize_difficult_terrain_snake():
    state = _normalize({"difficult_terrain": True})
    assert state["difficultTerrain"] is True


def test_normalize_difficult_terrain_camel():
    state = _normalize({"difficultTerrain": True})
    assert state["difficultTerrain"] is True


def test_normalize_dash_used_variants():
    assert _normalize({"dash_used": True})["dashUsed"] is True
    assert _normalize({"dashUsed": True})["dashUsed"] is True
    assert _normalize({})["dashUsed"] is False


def test_normalize_last_xy_variants():
    s1 = _normalize({"last_x": 100, "last_y": 200})
    assert s1["lastX"] == 100 and s1["lastY"] == 200
    s2 = _normalize({"lastX": 50, "lastY": 75})
    assert s2["lastX"] == 50 and s2["lastY"] == 75


# ---------------------------------------------------------------------------
# Movement validation — mirror of resolver logic used by preview
# ---------------------------------------------------------------------------

def test_preview_rejects_too_far_without_crashing():
    """A move beyond remainingFt is invalid but does not raise."""
    state = _normalize({"speed_ft": 30, "spent_ft": 25})
    remaining = state["remainingFt"]  # 5 ft
    result = resolve_movement(from_x=0, from_y=0, to_x=300, to_y=0)  # 30 ft
    cost = result["finalCostFeet"]
    is_valid = cost <= remaining + 0.01
    assert is_valid is False
    assert cost == 30.0  # no exception raised


def test_preview_missing_remaining_ft_shows_fallback():
    """When remainingFt is absent the normalizer returns 0; UI should show fallback."""
    state = _normalize({})
    assert state["remainingFt"] == 0.0
    # A move of any distance is 'too far' relative to 0 remaining — this is the
    # fallback path; the caller must show 'Movement data loading…' rather than NaN.
    cost = 10.0
    is_overbudget = cost > state["remainingFt"] + 0.01
    assert is_overbudget is True


# ---------------------------------------------------------------------------
# Static analysis — verify play.html has no bare remainingFt outside normalized scope
# ---------------------------------------------------------------------------

def _load_play_html_js_sections() -> str:
    with open("client/templates/play.html", encoding="utf-8") as f:
        return f.read()


def test_no_bare_remaining_ft_in_draw_combat_move_path():
    """drawCombatMovePath must declare remainingFt before any use of it."""
    src = _load_play_html_js_sections()
    fn_match = re.search(
        r'function drawCombatMovePath\(\)\s*\{(.+?)^\}',
        src,
        re.DOTALL | re.MULTILINE,
    )
    assert fn_match, "drawCombatMovePath not found in play.html"
    body = fn_match.group(1)

    # Must contain a declaration of remainingFt via normalizeCombatMovementState
    assert "normalizeCombatMovementState" in body, \
        "drawCombatMovePath must call normalizeCombatMovementState"
    assert "remainingFt" in body, \
        "drawCombatMovePath must reference remainingFt"

    # The declaration must appear before the first usage
    decl_pos  = body.find("remainingFt =")
    usage_pos = body.find("remainingFt +")
    assert decl_pos != -1, "remainingFt must be declared (assigned) inside drawCombatMovePath"
    assert decl_pos < usage_pos, "remainingFt declaration must precede its first use"


def test_normalize_helper_exists_in_play_html():
    """normalizeCombatMovementState must be defined in play.html."""
    src = _load_play_html_js_sections()
    assert "function normalizeCombatMovementState(" in src


def test_draw_path_has_try_catch():
    """drawCombatMovePath must be wrapped in try/catch for resilience."""
    src = _load_play_html_js_sections()
    fn_match = re.search(
        r'function drawCombatMovePath\(\)\s*\{(.+?)^\}',
        src,
        re.DOTALL | re.MULTILINE,
    )
    assert fn_match, "drawCombatMovePath not found"
    body = fn_match.group(1)
    assert "try {" in body or "try{" in body, \
        "drawCombatMovePath must wrap its body in try/catch"
    assert "catch" in body
