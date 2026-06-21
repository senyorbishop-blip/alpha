"""Guard tests for the exact regression patterns that have re-broken this
runtime before (PR 285/292/298/322/333/335/339). These are cheap source/AST
checks; behavioral coverage lives in the test_*_e2e.py / test_combat_repaint_*
/ test_quick_action_render_purity.py files alongside this one.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"
WS_JS = ROOT / "client/static/js/core/ws.js"
MAP_EDITOR_PY = ROOT / "server/handlers/map_editor.py"
COMMON_PY = ROOT / "server/handlers/common.py"

PLAY_SRC = PLAY.read_text(encoding="utf-8")
WS_SRC = WS_JS.read_text(encoding="utf-8")
MAP_EDITOR_SRC = MAP_EDITOR_PY.read_text(encoding="utf-8")
COMMON_SRC = COMMON_PY.read_text(encoding="utf-8")


# ── G1: quick-action bridges have exactly one public assignment each ────────

def test_quick_action_bridges_have_exactly_one_public_assignment():
    names = [
        "combatQuickCastSpell",
        "combatQuickRollSpellDamage",
        "openCombatQuickBarWeaponAction",
        "rollQuickWeaponDamage",
    ]
    for name in names:
        window_assignments = re.findall(rf"window\.{name}\s*=", PLAY_SRC)
        assert len(window_assignments) <= 1, f"{name} has more than one window.* assignment in play.html"
        # A second plain (non-bridge) top-level declaration must not exist.
        plain_decls = re.findall(rf"(?<!Bridge)\bfunction {name}\(", PLAY_SRC)
        bridge_decls = re.findall(rf"function {name}Bridge\(", PLAY_SRC)
        # rollQuickWeaponDamage is itself a plain internal helper (no public
        # window.* re-implementation besides the bridge for the *combat*
        # variant); guard against more than one declaration total.
        assert len(plain_decls) + len(bridge_decls) <= 2, (
            f"{name} appears to have multiple competing declarations: "
            f"plain={plain_decls} bridge={bridge_decls}"
        )
    for name in ["combatQuickCastSpell", "combatQuickRollSpellDamage", "openCombatQuickBarWeaponAction"]:
        assert f"guardQuickActionBridge('{name}'" in PLAY_SRC, f"{name} bridge must route through guardQuickActionBridge"


# ── G2: per-stream visibility gate, no re-introduced bare scalar gate ───────

def test_visibility_gate_is_per_stream_not_a_shared_scalar():
    assert "_lastVisibilityRevisionByStream" in PLAY_SRC
    # The bare scalar must not exist as a standalone gating variable anymore.
    assert re.search(r"\blet\s+_lastVisibilityRevision\s*=", PLAY_SRC) is None
    assert re.search(r"\bvar\s+_lastVisibilityRevision\s*=", PLAY_SRC) is None


# ── G3: fog server contract ──────────────────────────────────────────────────

def _function_body(src: str, signature: str) -> str:
    start = src.index(signature)
    # Find the end of the function by matching brace depth from the opening brace.
    brace_start = src.index("{", start)
    depth = 0
    i = brace_start
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    raise AssertionError(f"could not find end of function body for {signature!r}")


def test_broadcast_fog_to_visible_users_is_per_user_send_to():
    start = MAP_EDITOR_SRC.index("async def _broadcast_fog_to_visible_users")
    end = MAP_EDITOR_SRC.index("\ndef ", start + 1)
    next_async = MAP_EDITOR_SRC.find("\nasync def ", start + 1)
    if next_async != -1 and next_async < end:
        end = next_async
    body = MAP_EDITOR_SRC[start:end]
    assert "send_to" in body
    assert "manager.broadcast(" not in body.split("else:")[0]


def test_resolve_fog_map_context_has_local_alias_branch():
    start = MAP_EDITOR_SRC.index("def _resolve_fog_map_context")
    end = MAP_EDITOR_SRC.index("\ndef ", start + 1)
    body = MAP_EDITOR_SRC[start:end]
    assert '"__local__"' in body
    assert 'return "__local__"' not in body


# ── G4: combat broadcast strips suspended lists for non-DM ──────────────────

def test_broadcast_combat_uses_send_to_and_strips_suspended_for_non_dm():
    start = COMMON_SRC.index("async def _broadcast_combat")
    end = COMMON_SRC.find("\n\n\n", start)
    body = COMMON_SRC[start:end]
    assert "send_to" in body
    assert "_combat_state_payload_for_user" in body

    payload_fn_start = COMMON_SRC.index("def _combat_state_payload_for_user")
    payload_fn_end = COMMON_SRC.index("\ndef ", payload_fn_start + 1)
    payload_body = COMMON_SRC[payload_fn_start:payload_fn_end]
    assert 'payload.pop("suspended_combatants"' in payload_body
    assert 'payload.pop("fog_suspended_combatants"' in payload_body
    assert 'payload.pop("hidden_suspended_combatants"' in payload_body


# ── G5: combat_initiative_rolled handler must not mutate the roster ─────────

def test_combat_initiative_rolled_handler_does_not_mutate_roster():
    start = PLAY_SRC.index("function applyInitiativeResultToCombatState(result)")
    end = PLAY_SRC.index("function applyCombatInitiativeRolled", start)
    body = PLAY_SRC[start:end]
    forbidden = ["_sortCombatants(", "_combat.combatants =", "_combat.turn =", "_combat.round ="]
    for token in forbidden:
        assert token not in body, f"{token!r} must not appear in applyInitiativeResultToCombatState"


# ── G6: single WebSocket owner ───────────────────────────────────────────────

def test_ws_js_has_single_socket_owner_machinery():
    assert WS_SRC.count("new WebSocket(") <= 1
    assert "function requestInitialStateOnce" in WS_SRC
    assert "function wasReplacedByNewerConnection" in WS_SRC
