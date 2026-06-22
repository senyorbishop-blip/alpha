from pathlib import Path

PLAY = Path('client/templates/play.html')
FOG = Path('client/static/js/render/fog.js')
STUB = Path('client/static/js/core/player_boot_stub.js')


def _slice(src: str, start: str, end: str) -> str:
    i = src.index(start)
    j = src.index(end, i)
    return src[i:j]


def test_state_sync_no_longer_runs_authority_redirect_path():
    src = PLAY.read_text(encoding='utf-8')
    block = _slice(src, "case 'state_sync': {", "// Full state load")
    assert "syncSessionAuthority('state_sync')" not in block
    assert 'Routine state_sync must not re-run authority redirect logic' in block


def test_play_and_player_stub_delegate_socket_creation_to_appws_only():
    play = PLAY.read_text(encoding='utf-8')
    stub = STUB.read_text(encoding='utf-8')
    assert 'new WebSocket(' not in play
    assert 'new WebSocket(' not in stub
    play_connect = _slice(play, 'function connectWS() {', 'function _buildWSMessage(msg) {')
    stub_connect = _slice(stub, 'function connectWS(){', 'function sendWS(msg)')
    assert 'window.AppWS.ensureConnected({ reason: \'boot\' })' in play_connect
    assert 'window.AppWS.ensureConnected({ reason: \'boot\' })' in stub_connect
    assert 'ws = window.AppWS.ensureConnected' not in play_connect
    assert 'ws = window.AppWS.ensureConnected' not in stub_connect
    assert 'wsReconnectTimer' not in play
    assert 'wsReconnectTimer' not in stub


def test_fog_apply_state_ignores_older_per_context_revision():
    src = FOG.read_text(encoding='utf-8')
    body = _slice(src, 'function fogApplyState(state, env, p) {', 'function fogApplyUpdate(state, env, p) {')
    assert 'const nextFogMaps = { ...(state.fogMaps || {}) };' in body
    assert 'incomingRevision < localRevision' in body
    assert 'fog_state ignored stale fog_map revision' in body
    assert 'state.fogMaps = nextFogMaps;' in body


def test_fog_apply_state_applies_equal_or_newer_revision():
    src = FOG.read_text(encoding='utf-8')
    body = _slice(src, 'function fogApplyState(state, env, p) {', 'function fogApplyUpdate(state, env, p) {')
    assert 'nextFogMaps[mapCtx] = { enabled: !!entry.enabled' in body
    assert 'revision: incomingRevision' in body
    assert body.index('if (localEntry && incomingRevision < localRevision)') < body.index('nextFogMaps[mapCtx] =')


def test_fog_apply_update_ignores_older_revision_but_keeps_first_update_enabled():
    src = FOG.read_text(encoding='utf-8')
    body = _slice(src, 'function fogApplyUpdate(state, env, p) {', 'function debugFog(state, env) {')
    assert 'incomingRevision < localRevision' in body
    assert 'fog_update ignored stale revision' in body
    assert 'entry.enabled = true;' in body
    assert 'entry.revision = Math.max(Number(entry.revision) || 0, incomingRevision);' in body
