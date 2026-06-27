"""Tests for throttled/coalesced outbound token_move sends during drag
(realtime sync tiny patch).

Dragging a token fires onMouseMove far more often than the server needs
token_move updates. The local token's x/y is mutated by the caller
immediately (see onMouseMove in play.html), while a throttled outbound trail
lets remote clients see movement before the guaranteed final commit. Only the
outbound websocket send is throttled/coalesced through the helpers extracted and exercised
here: scheduleTokenMoveSend, flushPendingTokenMove, flushAllPendingTokenMoves,
sendTokenMoveImmediately, clearPendingTokenMove, clearAllPendingTokenMoves.

These tests run the real helper code extracted from play.html in a node
harness with a fake timer, same approach as
test_token_move_revision_guard.py / test_token_movement_interpolation.py, so
we're testing the shipped code, not a re-implementation of it.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _throttle_helpers_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("// ── Token-move send throttling/coalescing during drag")
    end = src.index("// WebSocket", start)
    return src[start:end]


def _on_mouse_move_drag_block() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("// Stream a throttled trail of drag positions")
    end = src.index("}\n}", start) + 3
    return src[start:end]


def test_play_html_defines_throttle_helpers():
    snippet = _throttle_helpers_snippet()
    for name in [
        "function sendTokenMoveImmediately(",
        "function scheduleTokenMoveSend(",
        "function flushPendingTokenMove(",
        "function flushAllPendingTokenMoves(",
        "function clearPendingTokenMove(",
        "function clearAllPendingTokenMoves(",
    ]:
        assert name in snippet


def test_drag_move_handler_streams_throttled_remote_preview_without_direct_send():
    snippet = _on_mouse_move_drag_block()
    assert "Stream a throttled trail of drag positions" in snippet
    assert "scheduleTokenMoveSend(" in snippet
    assert "client_move_seq: nextTokenMoveClientSeq" in snippet
    assert "sendWS({ type: 'token_move'" not in snippet


def _run_node(script_body: str):
    """Runs `script_body` after the real throttle helpers, with a manual fake
    timer queue standing in for setTimeout/clearTimeout so tests can advance
    time deterministically instead of using real wall-clock waits.
    """
    fake_timers = """
let _fakeNow = 0;
let _fakeTimers = [];
let _nextTimerId = 1;
function setTimeout(fn, ms) {
  const id = _nextTimerId++;
  _fakeTimers.push({ id, fn, due: _fakeNow + (Number(ms) || 0) });
  return id;
}
function clearTimeout(id) {
  _fakeTimers = _fakeTimers.filter(t => t.id !== id);
}
function advanceTime(ms) {
  _fakeNow += ms;
  const due = _fakeTimers.filter(t => t.due <= _fakeNow);
  _fakeTimers = _fakeTimers.filter(t => t.due > _fakeNow);
  due.sort((a, b) => a.due - b.due);
  due.forEach(t => t.fn());
}
"""
    code = f"""
{fake_timers}
{_throttle_helpers_snippet()}

const sentMessages = [];
function sendWS(msg) {{ sentMessages.push(msg); }}

{script_body}
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def test_multiple_drag_moves_within_throttle_window_coalesce_to_latest():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 2, y: 2 });
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 3, y: 3 });
advanceTime(40);
console.log(JSON.stringify(sentMessages));
""")
    assert len(results) == 1
    assert results[0]["payload"] == {"token_id": "tok-1", "x": 3, "y": 3}


def test_drag_end_flushes_final_position_immediately_bypassing_timer():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
// Drag end happens before the throttle interval elapses.
flushPendingTokenMove('tok-1', { token_id: 'tok-1', x: 9, y: 9 });
console.log(JSON.stringify(sentMessages));
""")
    assert len(results) == 1
    assert results[0]["payload"] == {"token_id": "tok-1", "x": 9, "y": 9}


def test_drag_end_flush_does_not_duplicate_send_when_timer_later_fires():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
flushPendingTokenMove('tok-1', { token_id: 'tok-1', x: 9, y: 9 });
advanceTime(200); // pending timer (if not cleared) would have fired here
console.log(JSON.stringify(sentMessages));
""")
    assert len(results) == 1


def test_send_token_move_immediately_bypasses_throttle():
    results = _run_node("""
sendTokenMoveImmediately({ token_id: 'tok-1', x: 5, y: 5 });
console.log(JSON.stringify(sentMessages));
""")
    assert len(results) == 1
    assert results[0] == {"type": "token_move", "payload": {"token_id": "tok-1", "x": 5, "y": 5}}


def test_flush_all_pending_token_moves_sends_every_token_latest_payload():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 2, y: 2 });
scheduleTokenMoveSend('tok-2', { token_id: 'tok-2', x: 10, y: 10 });
flushAllPendingTokenMoves();
console.log(JSON.stringify(sentMessages));
""")
    by_id = {m["payload"]["token_id"]: m["payload"] for m in results}
    assert by_id["tok-1"] == {"token_id": "tok-1", "x": 2, "y": 2}
    assert by_id["tok-2"] == {"token_id": "tok-2", "x": 10, "y": 10}


def test_clear_pending_token_move_drops_without_sending():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
clearPendingTokenMove('tok-1');
advanceTime(200);
console.log(JSON.stringify(sentMessages));
""")
    assert results == []


def test_clear_all_pending_token_moves_drops_every_token_without_sending():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
scheduleTokenMoveSend('tok-2', { token_id: 'tok-2', x: 2, y: 2 });
clearAllPendingTokenMoves();
advanceTime(200);
console.log(JSON.stringify(sentMessages));
""")
    assert results == []


def test_different_tokens_throttle_independently():
    results = _run_node("""
scheduleTokenMoveSend('tok-1', { token_id: 'tok-1', x: 1, y: 1 });
advanceTime(40);
scheduleTokenMoveSend('tok-2', { token_id: 'tok-2', x: 2, y: 2 });
advanceTime(40);
console.log(JSON.stringify(sentMessages));
""")
    assert [m["payload"]["token_id"] for m in results] == ["tok-1", "tok-2"]


def test_fallback_sends_directly_when_settimeout_unavailable():
    # Simulate an environment without timer support: scheduleTokenMoveSend
    # must fall back to sending immediately rather than dropping the move.
    code = f"""
{_throttle_helpers_snippet()}
const sentMessages = [];
function sendWS(msg) {{ sentMessages.push(msg); }}
const setTimeout = undefined;
scheduleTokenMoveSend('tok-1', {{ token_id: 'tok-1', x: 7, y: 7 }});
console.log(JSON.stringify(sentMessages));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    results = json.loads(out)
    assert len(results) == 1
    assert results[0]["payload"] == {"token_id": "tok-1", "x": 7, "y": 7}


def test_local_token_position_mutation_is_not_part_of_throttle_path():
    # The throttle helpers only gate the outbound websocket send; they never
    # touch token x/y state themselves, so local drag movement (mutated
    # directly by the caller in onMouseMove) is never delayed by this code.
    snippet = _throttle_helpers_snippet()
    assert "tokens[" not in snippet
    assert ".x =" not in snippet
    assert ".y =" not in snippet
