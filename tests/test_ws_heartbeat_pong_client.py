"""Heartbeat ping/pong handling in the websocket core (client/static/js/core/ws.js).

These tests load the real ws.js module into a minimal Node sandbox and drive the
socket.onmessage handler directly, asserting the transport-layer heartbeat reply
behavior that prevents false "Heartbeat timeout" disconnects during active play.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "client/static/js/core/ws.js"


def _run(harness_js: str) -> dict:
    src = WS.read_text(encoding="utf-8")
    code = f"""
const sends = [];
const dispatched = [];
class FakeSocket {{
  constructor() {{ this.readyState = 1; this.onopen = null; this.onclose = null; this.onerror = null; this.onmessage = null; }}
  send(data) {{ sends.push(JSON.parse(data)); }}
  close() {{ this.readyState = 3; }}
}}
const WebSocketCtor = function () {{ return new FakeSocket(); }};
WebSocketCtor.CONNECTING = 0; WebSocketCtor.OPEN = 1; WebSocketCtor.CLOSING = 2; WebSocketCtor.CLOSED = 3;
const win = {{
  WebSocket: WebSocketCtor,
  location: {{ protocol: 'http:', host: 'localhost' }},
  setTimeout: () => 0,
  clearTimeout: () => {{}},
  addEventListener: () => {{}},
  sessionStorage: {{ getItem: () => '' }},
  console: console,
}};
win.window = win;
const window = win;
{src}
let _socketRef = null;
window.AppWS.configure({{
  getSessionId: () => 's1',
  getUserId: () => 'u1',
  getRole: () => 'dm',
  getSocket: () => _socketRef,
  setSocket: (v) => {{ _socketRef = v; }},
  getReconnectTimer: () => null,
  setReconnectTimer: () => {{}},
  getPendingMessages: () => [],
  setPendingMessages: () => {{}},
  getQueuedEditorTypes: () => new Set(),
  onMessage: (m) => {{ dispatched.push(m); }},
  onOpen: () => {{}},
  onClose: () => {{}},
}});
const sock = window.AppWS.connectWS();
{harness_js}
console.log(JSON.stringify({{ sends, dispatched }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def test_client_replies_pong_to_server_ping():
    result = _run("sock.onmessage({ data: JSON.stringify({ type: 'ping' }) });")
    assert result["sends"] == [{"type": "pong"}], "client must immediately reply pong to a ping"


def test_ping_is_not_passed_to_gameplay_dispatch():
    result = _run("sock.onmessage({ data: JSON.stringify({ type: 'ping' }) });")
    assert result["dispatched"] == [], "heartbeat ping must never reach gameplay dispatch"


def test_normal_message_is_dispatched_and_does_not_emit_pong():
    result = _run(
        "sock.onmessage({ data: JSON.stringify({ type: 'combat_state', payload: { revision: 3 } }) });"
    )
    assert result["sends"] == [], "non-ping frames must not emit a pong"
    assert len(result["dispatched"]) == 1
    assert result["dispatched"][0]["type"] == "combat_state"


def test_pong_not_queued_when_socket_is_closed():
    # A ping that arrives as the socket is closing must not attempt a send.
    result = _run(
        "sock.readyState = 3; sock.onmessage({ data: JSON.stringify({ type: 'ping' }) });"
    )
    assert result["sends"] == [], "must not send/queue a pong on a non-open socket"
    assert result["dispatched"] == []


def test_core_intercepts_ping_before_dispatch_source_guard():
    src = WS.read_text(encoding="utf-8")
    # The pong reply must live in the transport layer and short-circuit dispatch.
    assert "function sendPong(socket)" in src
    assert "if (msg && msg.type === 'ping') {" in src
    ping_idx = src.index("if (msg && msg.type === 'ping') {")
    dispatch_idx = src.index("config.onMessage(msg);", ping_idx)
    assert ping_idx < dispatch_idx, "ping must be handled before config.onMessage dispatch"
