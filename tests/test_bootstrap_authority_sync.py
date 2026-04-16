from pathlib import Path


def test_play_connect_ws_syncs_authority_before_socket_connect():
    src = Path('client/templates/play.html').read_text(encoding='utf-8')
    connect_start = src.index('function connectWS() {')
    connect_end = src.index('function _buildWSMessage(msg) {', connect_start)
    body = src[connect_start:connect_end]
    assert "await syncSessionAuthority('ws_preconnect')" in body
    assert "window.AppWS.configure(window.AppRuntimeBridge.createWsConfig());" in body
    assert body.index("await syncSessionAuthority('ws_preconnect')") < body.index('window.AppWS.configure(window.AppRuntimeBridge.createWsConfig());')


def test_runtime_bridge_prefers_authoritative_identity_over_store_fallbacks():
    src = Path('client/static/js/core/runtime_bridge.js').read_text(encoding='utf-8')
    get_user_start = src.index('getUserId: function () {')
    get_user_end = src.index('},\n      getRole: function () {', get_user_start)
    get_user_body = src[get_user_start:get_user_end]
    assert "if (String(resolved || '').trim()) return resolved;" in get_user_body
    assert "if (String(fromQuery || '').trim()) return fromQuery;" in get_user_body

    get_role_start = src.index('getRole: function () {')
    get_role_end = src.index('},\n      getSocket: function () {', get_role_start)
    get_role_body = src[get_role_start:get_role_end]
    assert 'resolvedRole || fromQuery || fromGlobal || fromStore' in get_role_body
