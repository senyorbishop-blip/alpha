from pathlib import Path

PLAY = Path('client/templates/play.html')
CSS = Path('client/static/css/play.css')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_dm_mode_rail_exists():
    src = read(PLAY)
    assert 'id="dm-live-mode-rail"' in src
    assert 'data-dm-rail-shell="true"' in src
    assert 'class="dm-map-first-rail"' in src


def test_all_dm_mode_buttons_exist():
    src = read(PLAY)
    for mode in [
        'run',
        'combat',
        'map-build',
        'npc-monster',
        'loot-shop',
        'session-tools',
        'viewer-powers',
        'debug',
    ]:
        assert f'data-dm-mode-button="{mode}"' in src


def test_live_table_is_default_active_mode_and_debug_not_default():
    src = read(PLAY)
    assert 'data-dm-mode-button="run" aria-pressed="true"' in src
    assert 'data-dm-mode-button="debug" aria-pressed="false"' in src
    assert "const FALLBACK_MODE = 'run'" in read(Path('client/static/js/ui/dm_panel_mode_bridge.js'))


def test_debug_panel_is_hidden_by_default():
    src = read(PLAY)
    assert 'data-dm-debug-panel hidden' in src
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert '.dm-map-first-shell:not([data-debug-open="true"]) [data-dm-debug-panel]' in css


def test_map_container_still_exists_and_remains_primary():
    src = read(PLAY)
    css = read(CSS)
    assert 'id="canvas-wrap"' in src
    assert 'id="map-canvas"' in src
    assert 'data-map-primary="true"' in src
    assert 'grid-template-columns: 86px minmax(0, 1fr)' in css


def test_player_viewer_do_not_show_dm_rail():
    src = read(PLAY)
    assert 'if (ROLE === \'dm\')' in src
    assert "if (dmRailShell) dmRailShell.hidden = false;" in src
    assert 'id="dm-live-mode-rail"' in src and 'hidden>' in src
    assert "ROLE === 'player'" in src
    assert "ROLE === 'viewer'" in src
