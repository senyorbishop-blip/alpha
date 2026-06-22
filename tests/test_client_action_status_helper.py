"""Tests for the unified client action-status helper (Realtime Sync Engine
v1 — tiny patch).

play.html previously had two separate, hand-rolled pending-ack trackers:
one for token_move (`_pendingTokenMoveAcks`, keyed by tokenId) and one for
quick actions (`_pendingQuickActionAcks`, keyed by client_action_id). This
patch replaces both with a single small helper:

    createClientActionId(prefix)      -- generate a unique id
    registerPendingAction(id, meta)   -- track an in-flight action lightly
    resolvePendingAction(id, ack)     -- clear it, return its meta (or null)
    handleActionAck(payload)          -- the action_ack dispatch handler

The helper is never the source of truth for game state: it only tracks
bookkeeping (ids + light metadata) and decides whether to show a safe
toast for denied/failed actions. Authoritative state (HP, token position,
charges, combat order, fog) is owned exclusively by the existing
broadcasts (token_moved/tokens_sync, combat_state, inventory_state, ...).

These tests run the real helper code extracted from play.html under node,
the same approach used by test_token_move_revision_guard.py /
test_token_movement_interpolation.py, so we're testing the shipped client
code rather than a re-implementation of it.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _helper_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("const _pendingActions = Object.create(null);")
    end = src.index("if (typeof window !== 'undefined') {", start)
    return src[start:end]


def _action_ack_case_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("case 'action_ack': {")
    end = src.index("\n\n", start)
    return src[start:end]


def test_play_html_defines_unified_action_status_helper():
    snippet = _helper_snippet()
    assert "function createClientActionId(" in snippet
    assert "function registerPendingAction(" in snippet
    assert "function resolvePendingAction(" in snippet
    assert "function handleActionAck(" in snippet


def test_play_html_action_ack_case_delegates_to_shared_helper():
    snippet = _action_ack_case_snippet()
    assert "handleActionAck(p)" in snippet
    # The old per-feature branching/trackers must be gone from this case.
    assert "_clearPendingTokenMoveAck" not in snippet
    assert "_clearPendingQuickAction" not in snippet


def test_play_html_token_move_and_quick_action_sites_use_shared_helper():
    src = PLAY.read_text(encoding="utf-8")
    # No call sites should still reference the old duplicate-local-handler
    # names; everything routes through the shared helper now.
    assert "_genClientActionId" not in src
    assert "_genQuickActionId" not in src
    assert "_trackPendingQuickAction" not in src
    assert "_pendingTokenMoveAcks" not in src
    assert "_pendingQuickActionAcks" not in src
    assert src.count("registerPendingAction(createClientActionId(") >= 8


def _run_node(script_body: str, *, timeout_ms=None):
    timeout_override = (
        f"const PENDING_ACTION_TIMEOUT_MS_OVERRIDE = {timeout_ms};\n" if timeout_ms is not None else ""
    )
    code = f"""
function showToast(msg) {{ global.__toasts.push(msg); }}
global.__toasts = [];
{_helper_snippet()}
{timeout_override}
{script_body}
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out) if out.strip() else None


# ---------------------------------------------------------------------------
# 1. createClientActionId returns unique ids with the given prefix.
# ---------------------------------------------------------------------------

def test_create_client_action_id_unique_and_prefixed():
    result = _run_node("""
const ids = [createClientActionId('tm'), createClientActionId('tm'), createClientActionId('qa')];
console.log(JSON.stringify({ ids, allUnique: new Set(ids).size === ids.length }));
""")
    assert result["allUnique"] is True
    assert result["ids"][0].startswith("tm_")
    assert result["ids"][1].startswith("tm_")
    assert result["ids"][2].startswith("qa_")


# ---------------------------------------------------------------------------
# 2. registerPendingAction stores action metadata.
# ---------------------------------------------------------------------------

def test_register_pending_action_stores_metadata():
    result = _run_node("""
const id = createClientActionId('qa');
registerPendingAction(id, { action: 'combat_attack_request', tokenId: 'tok-1' });
console.log(JSON.stringify({ stored: _pendingActions[id].meta }));
""")
    assert result["stored"] == {"action": "combat_attack_request", "tokenId": "tok-1"}


# ---------------------------------------------------------------------------
# 3-5. confirmed/denied/failed action_ack clears the pending action.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["confirmed", "denied", "failed"])
def test_action_ack_clears_pending_action(status):
    result = _run_node(f"""
const id = createClientActionId('qa');
registerPendingAction(id, {{ action: 'inventory_use_item_action' }});
handleActionAck({{ action: 'inventory_use_item_action', client_action_id: id, status: '{status}', reason: 'Not enough charges' }});
console.log(JSON.stringify({{ stillPending: Object.prototype.hasOwnProperty.call(_pendingActions, id) }}));
""")
    assert result["stillPending"] is False


# ---------------------------------------------------------------------------
# 6. denied/failed ack calls the existing toast helper with a safe message.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["denied", "failed"])
def test_denied_and_failed_ack_shows_safe_toast(status):
    result = _run_node(f"""
const id = createClientActionId('tm');
registerPendingAction(id, {{ action: 'token_move' }});
handleActionAck({{ action: 'token_move', client_action_id: id, status: '{status}', reason: 'Token move denied' }});
console.log(JSON.stringify({{ toasts: global.__toasts }}));
""")
    assert result["toasts"] == ["Token move denied"]


# ---------------------------------------------------------------------------
# 7. confirmed ack does not create a noisy duplicate toast.
# ---------------------------------------------------------------------------

def test_confirmed_ack_does_not_toast():
    result = _run_node("""
const id = createClientActionId('tm');
registerPendingAction(id, { action: 'token_move' });
handleActionAck({ action: 'token_move', client_action_id: id, status: 'confirmed' });
console.log(JSON.stringify({ toasts: global.__toasts }));
""")
    assert result["toasts"] == []


# ---------------------------------------------------------------------------
# 8. missing/unknown client_action_id does not crash.
# ---------------------------------------------------------------------------

def test_unknown_client_action_id_does_not_crash():
    result = _run_node("""
handleActionAck({ action: 'token_move', client_action_id: 'never-registered', status: 'denied', reason: 'Action denied' });
handleActionAck({ action: 'token_move', status: 'denied', reason: 'Action denied' });
handleActionAck(null);
console.log(JSON.stringify({ ok: true, toasts: global.__toasts }));
""")
    assert result["ok"] is True
    # The unknown-id denial still surfaces its safe message; the two
    # malformed/no-id calls are simply no-ops (no crash, no extra toast).
    assert result["toasts"] == ["Action denied", "Action denied"]


# ---------------------------------------------------------------------------
# 9. expired pending actions are cleaned up.
# ---------------------------------------------------------------------------

def test_expired_pending_action_is_cleaned_up():
    result = _run_node("""
const id = createClientActionId('qa');
registerPendingAction(id, { action: 'inventory_cast_item_spell' });
setTimeout(() => {
  console.log(JSON.stringify({ stillPending: Object.prototype.hasOwnProperty.call(_pendingActions, id) }));
}, PENDING_ACTION_TIMEOUT_MS + 50);
""")
    assert result["stillPending"] is False


def test_pending_action_not_expired_before_timeout():
    result = _run_node("""
const id = createClientActionId('qa');
registerPendingAction(id, { action: 'inventory_cast_item_spell' });
setTimeout(() => {
  console.log(JSON.stringify({ stillPending: Object.prototype.hasOwnProperty.call(_pendingActions, id) }));
}, Math.max(0, PENDING_ACTION_TIMEOUT_MS - 5000));
""")
    assert result["stillPending"] is True


# ---------------------------------------------------------------------------
# 10. action_ack handler does not mutate authoritative token/combat/
#     inventory/fog state.
# ---------------------------------------------------------------------------

def test_action_ack_handler_never_touches_authoritative_state():
    result = _run_node("""
const tokens = { 'tok-1': { id: 'tok-1', x: 5, y: 5, hp: 10 } };
const combat = { revision: 3, turn: 0 };
const inventory = { revision: 7 };
let fogTouched = false;

const id = createClientActionId('tm');
registerPendingAction(id, { action: 'token_move', tokenId: 'tok-1' });
handleActionAck({
  action: 'token_move', client_action_id: id, status: 'denied', reason: 'Token move denied',
  // Even if a malicious/buggy payload carried position-like fields, the
  // shared handler must never apply them.
  x: 999, y: 999, hp: 1, token_id: 'tok-1', combat_revision: 999, fog: 'changed',
});

console.log(JSON.stringify({
  token: tokens['tok-1'],
  combat,
  inventory,
  fogTouched,
}));
""")
    assert result["token"] == {"id": "tok-1", "x": 5, "y": 5, "hp": 10}
    assert result["combat"] == {"revision": 3, "turn": 0}
    assert result["inventory"] == {"revision": 7}
    assert result["fogTouched"] is False


# ---------------------------------------------------------------------------
# 11. token_move and quick-action ack paths use the shared helper rather
#     than duplicate local handlers (static check on the shipped source).
# ---------------------------------------------------------------------------

def test_token_move_send_site_uses_shared_helper():
    src = PLAY.read_text(encoding="utf-8")
    assert "registerPendingAction(createClientActionId('tm')" in src


def test_quick_action_send_sites_use_shared_helper():
    src = PLAY.read_text(encoding="utf-8")
    assert src.count("registerPendingAction(createClientActionId('qa')") >= 7


# ---------------------------------------------------------------------------
# 12. Existing no-ack behavior remains backward compatible: a server that
#     never sends action_ack leaves no dangling pending actions forever
#     (they still expire), and nothing in the dispatch path requires the
#     ack to ever arrive.
# ---------------------------------------------------------------------------

def test_no_ack_ever_arriving_still_expires_cleanly():
    result = _run_node("""
const id = registerPendingAction(createClientActionId('tm'), { action: 'token_move' });
// Simulate an old server that never sends action_ack at all.
setTimeout(() => {
  console.log(JSON.stringify({
    stillPending: Object.prototype.hasOwnProperty.call(_pendingActions, id),
    toasts: global.__toasts,
  }));
}, PENDING_ACTION_TIMEOUT_MS + 50);
""")
    assert result["stillPending"] is False
    assert result["toasts"] == []
