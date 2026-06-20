"""Regression coverage for the in-play navigation guard.

These tests defend the fix for the "page reloads back to /play during normal
play" bug. The browser was hard-refreshing (window.location.replace to
/play?...&returning=1) whenever authority/role drift was detected, which tore
down the live websocket and reset the combat tab + fog display. The websocket
heartbeat/pong path was a red herring — the page itself was navigating.

The required behaviour:
  1. A websocket close must NOT hard-refresh the page; it reconnects in-place.
  2. Reconnect happens via AppWS/ws.js (no location reload).
  3. Authority/session refresh must not redirect to /play when already on /play
     for the same session + user.
  4. Only initial login/join navigates to /play.
  5. Reconnect pulls state_sync/combat_state over the socket, not a page reload.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"
WS = ROOT / "client/static/js/core/ws.js"
BRIDGE = ROOT / "client/static/js/core/runtime_bridge.js"


def _read(path):
    return path.read_text(encoding="utf-8")


def _slice(src, start_marker, end_marker):
    start = src.index(start_marker)
    end = src.index(end_marker, start + len(start_marker))
    return src[start:end]


# ---------------------------------------------------------------------------
# 1. websocket close triggers reconnect, not a location reload
# ---------------------------------------------------------------------------
def test_websocket_close_reconnects_in_place_without_location_reload():
    src = _read(WS)
    onclose = _slice(src, "socket.onclose = (event) => {", "socket.onerror = ()")
    # The close handler must log the reason and recover via scheduleReconnect.
    assert "console.info('[WS] close reason'," in onclose
    assert "scheduleReconnect();" in onclose
    # It must never hard-refresh or navigate the page on close.
    assert "location.reload" not in onclose
    assert "location.href" not in onclose
    assert "location.replace" not in onclose
    assert "location.assign" not in onclose

    # Reconnect is performed in-place by re-opening the socket, not by reloading.
    schedule = _slice(src, "function scheduleReconnect() {", "function installLifecycleHooks(")
    assert "console.info('[WS] reconnect in-place');" in schedule
    assert "connectWS();" in schedule
    assert "location.reload" not in schedule


# ---------------------------------------------------------------------------
# 2. request_state does not navigate to /play
# ---------------------------------------------------------------------------
def test_request_state_on_reconnect_does_not_navigate_to_play():
    src = _read(BRIDGE)
    onopen = _slice(src, "onOpen: function () {", "onClose: function")
    # Reconnect requests authoritative state over the socket.
    assert "type: 'request_state'" in onopen
    assert "reason: 'reconnect'" in onopen
    # And it does so without navigating anywhere.
    assert "location.href" not in onopen
    assert "location.replace" not in onopen
    assert "location.reload" not in onopen
    assert "location.assign" not in onopen
    assert "/play" not in onopen


# ---------------------------------------------------------------------------
# 3. authority refresh does not navigate to /play (same session/user)
# ---------------------------------------------------------------------------
def test_authority_refresh_does_not_navigate_to_play():
    src = _read(PLAY)
    fn = _slice(src, "function _redirectToResolvedAuthority(reason = '') {", "let _bigScreenDisplayMode")
    # The NAV GUARD short-circuits before any navigation when we are on /play
    # with the same session + user, refreshing authority state in place.
    assert "[NAV GUARD] blocked duplicate /play reload" in fn
    assert "console.info('[AUTH] authority refreshed without navigation'," in fn
    # The in-place branch returns false (no navigation) after refreshing the badge.
    guard = _slice(fn, "if (onPlay && urlSessionId === targetSessionId && urlUserId === resolvedUserId) {", "const next = new URL(")
    assert "refreshRoleBadge();" in guard
    assert "return false;" in guard
    assert "window.location.replace" not in guard


# ---------------------------------------------------------------------------
# 4. same session/user /play URL is ignored as duplicate
# ---------------------------------------------------------------------------
def test_same_session_user_play_url_is_ignored_as_duplicate():
    src = _read(PLAY)
    fn = _slice(src, "function _redirectToResolvedAuthority(reason = '') {", "let _bigScreenDisplayMode")
    # The guard keys off being on /play and matching the URL session_id/user_id.
    assert "const onPlay = String(window.location.pathname || '') === '/play';" in fn
    assert "urlParams.get('session_id')" in fn
    assert "urlParams.get('user_id')" in fn
    assert "if (onPlay && urlSessionId === targetSessionId && urlUserId === resolvedUserId) {" in fn
    # The duplicate-reload block sits BEFORE the URL build + location.replace, so
    # a matching session/user can never reach the navigation.
    assert fn.index("[NAV GUARD] blocked duplicate /play reload") < fn.index("window.location.replace")


# ---------------------------------------------------------------------------
# 5. combat/fog state survives reconnect without a hard reload
# ---------------------------------------------------------------------------
def test_combat_and_fog_state_recovered_over_socket_on_reconnect():
    src = _read(BRIDGE)
    onopen = _slice(src, "onOpen: function () {", "onClose: function")
    # Combat is pulled authoritatively after reconnect (no reload needed).
    assert "type: 'combat_state_request'" in onopen
    assert onopen.index("type: 'request_state'") < onopen.index("type: 'combat_state_request'")
    # DM fog preview is re-applied in place rather than via a page refresh.
    assert "reapplyDmFogPreviewAfterReconnect" in onopen

    # The websocket close path that precedes reconnect must not reload the page,
    # so combat/fog UI is never destroyed by a navigation.
    ws_src = _read(WS)
    onclose = _slice(ws_src, "socket.onclose = (event) => {", "socket.onerror = ()")
    assert "location.reload" not in onclose
    assert "location.replace" not in onclose


# ---------------------------------------------------------------------------
# Guard against re-introducing an in-play /play hard reload anywhere new.
# ---------------------------------------------------------------------------
def test_only_authority_redirect_uses_location_replace_in_play_html():
    src = _read(PLAY)
    # The single sanctioned location.replace lives in _redirectToResolvedAuthority,
    # gated behind the NAV GUARD. Assert there is exactly one occurrence.
    assert src.count("window.location.replace") == 1
