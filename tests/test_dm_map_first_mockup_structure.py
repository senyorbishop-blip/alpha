from pathlib import Path

HTML = Path('client/templates/play.html')
SHELL_CSS = Path('client/static/css/dm-map-first-shell.css')
POLISH_CSS = Path('client/static/css/dm-map-first-polish.css')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_dm_shell_has_approved_grid_areas():
    css = read(SHELL_CSS) + read(POLISH_CSS)
    for area in ['"topbar topbar topbar"', '"rail map context"', '"rail quick context"']:
        assert area in css
    for selector in ['#topbar', '#sidebar-left.dm-map-first-rail', '#canvas-wrap.dm-map-first-map-stage', '#sidebar-right.dm-map-first-right-context', '#dm-map-first-quick-strip.dm-map-first-quick-strip']:
        assert selector in css


def test_map_stage_exists_central_and_right_context_does_not_contain_canvas():
    html = read(HTML)
    assert 'id="canvas-wrap" class="tool-select session-frame dm-map-first-map-stage" data-map-primary="true"' in html
    assert '<canvas id="map-canvas"></canvas>' in html
    right_start = html.index('<div id="sidebar-right" class="dm-map-first-right-context">')
    right_html = html[right_start:]
    assert '<canvas id="map-canvas"' not in right_html


def test_left_rail_modes_and_live_table_default():
    html = read(HTML)
    # The run/Live-Table button is the default-pressed mode. An onclick bridge
    # invocation now sits between aria-pressed and the closing bracket, so assert
    # the button is pressed and carries the Live Table label.
    assert 'data-dm-mode-button="run" aria-pressed="true"' in html
    assert '▶<span>Live Table</span>' in html
    for mode in ['run', 'combat', 'map-build', 'npc-monster', 'loot-shop', 'session-tools', 'viewer-powers', 'debug']:
        assert f'data-dm-mode-button="{mode}"' in html


def test_debug_hidden_by_default_and_only_dm_shell_shows_debug():
    html = read(HTML)
    css = read(SHELL_CSS) + read(POLISH_CSS)
    assert 'data-dm-mode="debug"' in html
    assert 'data-dm-debug-panel hidden' in html
    assert 'body.dm-map-first-active:not([data-debug-open="true"]) [data-dm-debug-panel]' in css


def test_player_and_viewer_do_not_render_dm_shell_or_rail():
    html = read(HTML)
    css = read(POLISH_CSS)
    assert "if (ROLE === 'dm')" in html
    assert "document.body.classList.add('dm-map-first-active');" in html
    assert 'body:not(.dm-map-first-active) #dm-live-mode-rail' in css
    assert 'body:not(.dm-map-first-active) #dm-map-first-quick-strip' in css


def test_bottom_quick_strip_and_legacy_more_fallback_exist():
    html = read(HTML)
    # Quick-strip core map tools. The strip was expanded during the map-first
    # polish pass (shapes/ping/map/dice added; the standalone "more" quick button
    # was dropped in favor of the dedicated legacy-tools fallback section below).
    for action in ['select', 'move', 'measure', 'draw', 'notes']:
        assert f'data-dm-quick-action="{action}"' in html
    # "More / Legacy Tools" access now lives in its own context section rather than
    # a quick-strip button, but it remains fully present.
    assert 'More / Legacy Tools' in html
    assert 'dm-legacy-tools-fallback' in html
    assert 'data-dm-context-section="legacy-tools-fallback"' in html
    assert 'dm-legacy-controls-shell' in html
