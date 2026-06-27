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
    assert 'id="stream-readiness-panel" data-dm-mode="debug" data-dm-tool="stream-readiness" data-dm-debug-panel hidden' in src
    assert 'data-dm-debug-panel hidden' in src
    assert 'Debug diagnostics are hidden by default' in src or 'Debug diagnostics are closed by default' in src
    assert 'body.dm-map-first-active:not([data-debug-open="true"]) [data-dm-debug-panel]' in css
    assert 'body.dm-map-first-active:not([data-debug-open="true"]) #stream-readiness-panel' in css
    assert "safeRoot.body.dataset.debugOpen = activeMode === 'debug' ? 'true' : 'false';" in bridge
    assert "window.renderStreamReadinessPanel();" in bridge


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
    assert "if (role !== 'dm') { panel.style.display = 'none'; panel.hidden = true; return; }" in src
    assert "if (!debugOpen) { panel.style.display = 'none'; panel.hidden = true; return; }" in src
    assert "if (ROLE === 'dm')" in src
    assert "if (dmContextShell) dmContextShell.hidden = false;" in src
    assert 'id="dm-context-shell"' in src and 'data-dm-context-shell="true" hidden' in src
    assert "ROLE === 'player'" in src
    assert "ROLE === 'viewer'" in src


def test_player_and_viewer_cannot_open_dm_debug_tools():
    src = read(PLAY)
    assert 'data-dm-mode-button="debug"' in src
    assert 'id="dm-live-mode-rail"' in src and 'data-dm-rail-shell="true" hidden' in src
    assert "if (ROLE === 'dm')" in src
    dm_block_start = src.index("// Show DM-only rail buttons and flyout panels")
    dm_block = src[dm_block_start:dm_block_start + 2200]
    assert "if (dmRailShell) dmRailShell.hidden = false;" in dm_block
    assert "if (dmContextShell) dmContextShell.hidden = false;" in dm_block
    # The bridge init is deferred to the DM-only map-first bootstrap and is no
    # longer called inline during core boot. The boot shell only unhides DM shells
    # for DMs; the actual mode bridge init runs later via the bootstrap.
    assert "Do not call AppUIDMPanelModeBridge.init() during core boot." in dm_block
    assert "window.AppUIDMMapFirstBootstrap.init()" in src
    assert "role !== 'dm'" in src


def test_stream_readiness_is_not_rendered_until_debug_is_open():
    src = read(PLAY)
    render_start = src.index('function renderStreamReadinessPanel()')
    render_end = src.index('function buildClientLiveStateSummary', render_start)
    render_block = src[render_start:render_end]
    assert "document.body.dataset.debugOpen === 'true'" in render_block
    assert "if (!debugOpen)" in render_block
    assert "panel.style.display = 'block';" in render_block
