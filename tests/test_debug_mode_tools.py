from pathlib import Path

PLAY = Path('client/templates/play.html')
BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')
CSS = Path('client/static/css/dm-map-first-shell.css')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_debug_panel_is_hidden_by_default_and_closed_until_debug_mode():
    src = read(PLAY)
    css = read(CSS)
    bridge = read(BRIDGE)
    assert 'data-dm-debug-panel hidden' in src
    assert 'Debug diagnostics are closed by default' in src
    assert 'body.dm-map-first-active:not([data-debug-open="true"]) [data-dm-debug-panel]' in css
    assert 'body.dm-map-first-active:not([data-debug-open="true"]) #stream-readiness-panel' in css
    assert "safeRoot.body.dataset.debugOpen = activeMode === 'debug' ? 'true' : 'false';" in bridge


def test_debug_mode_exposes_readiness_and_diagnostics_tools():
    src = read(PLAY)
    bridge = read(BRIDGE)
    registry = read(REGISTRY)
    for tool in [
        'stream-readiness',
        'payload-warnings',
        'reconnect-warnings',
        'websocket-diagnostics',
        'sync-diagnostics',
        'visibility-checks',
        'dm-focus-testing-guidance',
    ]:
        assert f"id: '{tool}'" in bridge or f"'{tool}'" in registry
    assert 'id="stream-readiness-panel"' in src
    assert 'appendDebugDiagnostics' in bridge
    assert "mountId: 'stream-readiness-panel'" in bridge
    assert 'Payload warnings remain tracked' in bridge
    assert 'Reconnect warnings remain tracked' in bridge


def test_live_table_does_not_include_debug_readiness_panels():
    src = read(PLAY)
    live_start = src.index('data-dm-context-section="live-table"')
    live_end = src.index('data-dm-context-section="combat"')
    live_section = src[live_start:live_end]
    forbidden = [
        'stream-readiness-panel',
        'payload-warnings',
        'reconnect-warnings',
        'websocket-diagnostics',
        'sync-diagnostics',
        'visibility-checks',
    ]
    for token in forbidden:
        assert token not in live_section


def test_diagnostics_still_exist_but_are_dm_only():
    src = read(PLAY)
    assert "if (role !== 'dm') { panel.style.display = 'none'; return; }" in src
    assert "if (ROLE === 'dm')" in src
    assert "if (dmContextShell) dmContextShell.hidden = false;" in src
    assert 'id="dm-context-shell"' in src and 'data-dm-context-shell="true" hidden' in src
    assert "ROLE === 'player'" in src
    assert "ROLE === 'viewer'" in src
