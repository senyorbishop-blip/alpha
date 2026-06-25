from pathlib import Path

PLAY = Path('client/templates/play.html')
BOOTSTRAP = Path('client/static/js/ui/dm_map_first_bootstrap.js')
SHELL_CSS = Path('client/static/css/dm-map-first-shell.css')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_live_play_page_references_map_first_assets_in_safe_order():
    src = read(PLAY)
    expected = [
        '/static/css/map-first-ui-tokens.css',
        '/static/css/dm-map-first-shell.css',
        '/static/js/ui/dm_map_first_shell.js',
        '/static/js/ui/dm_mode_tool_registry.js',
        '/static/js/ui/dm_panel_mode_bridge.js',
        '/static/js/ui/dm_map_first_bootstrap.js',
    ]
    for asset in expected:
        assert asset in src
    assert src.index('/static/css/play.css') < src.index('/static/css/map-first-ui-tokens.css')
    assert src.index('/static/js/ui/dm_map_first_shell.js') < src.index('/static/js/ui/dm_mode_tool_registry.js')
    assert src.index('/static/js/ui/dm_mode_tool_registry.js') < src.index('/static/js/ui/dm_panel_mode_bridge.js')
    assert src.index('/static/js/ui/dm_panel_mode_bridge.js') < src.index('/static/js/ui/dm_map_first_bootstrap.js')


def test_bootstrap_exists_and_calls_bridge_init_for_dm_only():
    src = read(BOOTSTRAP)
    assert BOOTSTRAP.exists()
    assert 'window.AppUIDMMapFirstBootstrap' in src
    assert "getBootRole() === 'dm'" in src
    assert 'if (!isDmRole()) return null;' in src
    assert 'bridge.init(root)' in src


def test_bootstrap_fails_safely_without_dm_root_or_bridge():
    src = read(BOOTSTRAP)
    assert 'try {' in src
    assert 'catch (err)' in src
    assert 'return null;' in src
    assert 'if (!hasDmOnlyAnchor(root)) return null;' in src
    assert "if (!bridge || typeof bridge.init !== 'function') return null;" in src


def test_bootstrap_does_not_initialize_for_player_or_viewer_only_markup():
    src = read(BOOTSTRAP)
    assert 'window.__PLAY_BOOT_ROLE' in src
    assert 'roleFromUrl()' in src
    assert "getBootRole() === 'dm'" in src
    assert 'if (!isDmRole()) return null;' in src
    assert "'player'" not in src
    assert "'viewer'" not in src


def test_debug_remains_hidden_by_default():
    css = read(SHELL_CSS)
    assert '.dm-map-first-shell:not([data-debug-open="true"]) [data-dm-debug-panel]' in css
    assert 'display: none !important' in css
    assert 'data-debug-open="true"' in css
