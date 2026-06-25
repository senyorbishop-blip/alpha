from pathlib import Path

PLAY_HTML = Path('client/templates/play.html').read_text(encoding='utf-8')
WS_JS = Path('client/static/js/core/ws.js').read_text(encoding='utf-8')
DISPATCH_JS = Path('client/static/js/core/message_dispatch.js').read_text(encoding='utf-8')
CHECKLIST = Path('docs/before-stream-checklist.md').read_text(encoding='utf-8')


def test_dm_only_stream_readiness_panel_contract():
    assert 'id="stream-readiness-panel"' in PLAY_HTML
    assert "if (role !== 'dm') { panel.style.display = 'none'; return; }" in PLAY_HTML
    assert 'connectedPlayers' in PLAY_HTML
    assert 'connectedViewers' in PLAY_HTML
    assert 'Payload warnings' in PLAY_HTML
    assert 'Reconnect warnings' in PLAY_HTML
    assert 'Session ${escapeHtml(String(SESSION_ID' in PLAY_HTML


def test_friendly_live_failure_diagnostics_are_wired():
    required = [
        'Quick Actions are unavailable right now',
        'Spell/action details are missing',
        'Rest sync failed',
        'Token move rejected by the server.',
        'Reconnect snapshot failed',
        'Viewer power rejected by the server.',
        'Player setup needed: choose or create an active character',
    ]
    for text in required:
        assert text in PLAY_HTML
    assert "reportClientRuntimeError('Quick Actions unavailable', err)" in PLAY_HTML


def test_live_debug_logs_are_gated_and_redacted():
    assert 'window.__LIVE_DEBUG__ = window.__LIVE_DEBUG__ === true;' in PLAY_HTML
    assert '_redactClientLogPayload(payload || {})' in PLAY_HTML
    assert "localStorage.getItem('dnd_live_debug') === '1'" in WS_JS
    assert "localStorage.getItem('dnd_live_debug') === '1'" in DISPATCH_JS
    assert 'dispatchDebugLog(\'[message_dispatch] combat_state\'' in DISPATCH_JS
    assert 'wsDebugLog(`[WS] received combat_state revision=' in WS_JS
    assert 'activeIndex' in DISPATCH_JS
    assert 'order,' not in DISPATCH_JS


def test_before_stream_checklist_covers_manual_release_pass():
    for phrase in [
        'Start the app',
        'Open one Player test browser',
        'Open one Viewer test browser',
        'Run the smoke test',
        'payload warning count',
        'Reconnect check',
        'Quick Actions check',
        'Fog and hidden-token safety',
        'Rest check',
        'OBS / browser performance',
    ]:
        assert phrase in CHECKLIST
