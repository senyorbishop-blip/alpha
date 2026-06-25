from pathlib import Path

PLAY = Path('client/templates/play.html')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')
BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_map_build_mode_includes_fog_walls_doors_and_reveal_markers():
    src = read(BRIDGE)
    registry = read(REGISTRY)
    assert "mode: 'map-build'" in src
    for marker in ['fog-tools', 'wall-tools', 'door-tools', 'reveal-hide-tools']:
        assert marker in src
        assert marker in registry
    assert "markerName: 'mapBuildMarkers'" in src


def test_npc_monster_mode_includes_bestiary_spawn_and_visibility_markers():
    src = read(BRIDGE)
    registry = read(REGISTRY)
    assert "mode: 'npc-monster'" in src
    for marker in ['bestiary-search', 'spawn-token', 'visibility-state']:
        assert marker in src
        assert marker in registry
    assert "markerName: 'npcMonsterMarkers'" in src


def test_live_table_context_keeps_setup_and_debug_tools_out():
    src = read(BRIDGE)
    registry = read(REGISTRY)
    assert "mode: 'run'" in src
    for marker in ['wall-editor', 'fog-brush', 'shop-editor', 'debug-diagnostics']:
        assert marker in src
        assert marker in registry
    assert "markerName: 'liveTableCleanMarkers'" in src


def test_existing_map_edit_controls_remain_in_dom():
    src = read(PLAY)
    for control_id in [
        'ep-flyout-host',
        'editor-layer-terrain',
        'editor-layer-walls',
        'editor-wall-tool-door',
        'editor-save-btn',
        'fog-btn-reveal',
        'fog-btn-hide',
        'fog-tool-brush',
    ]:
        assert f'id="{control_id}"' in src


def test_existing_spawn_controls_remain_in_dom():
    src = read(PLAY)
    for control_id in ['rtab-pane-bestiary', 'bestiary-search', 'bsm-spawn-btn', 'te-hidden', 'te-monster-quick-wrap']:
        assert f'id="{control_id}"' in src
    assert 'function bestiaryPlaceCreatureAt(worldX, worldY)' in src


def test_player_and_viewer_screens_remain_unchanged_by_dm_mode_bridge():
    src = read(PLAY)
    bridge = read(BRIDGE)
    assert "if (ROLE === 'dm')" in src
    assert "window.AppUIDMPanelModeBridge.init(document);" in src
    assert "document.body.classList.add('dm-map-first-active');" in src
    assert 'dm-context-shell' in src and 'hidden' in src
    assert 'element.hidden = !isActive' in bridge
    assert 'removeChild' not in bridge and '.remove()' not in bridge


def test_polished_map_first_active_mode_styling_exists():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert 'body.dm-map-first-active .dm-live-mode-rail .dm-map-first-mode-button[aria-pressed="true"]' in css
    assert 'body.dm-map-first-active .dm-live-mode-rail .dm-map-first-mode-button[data-dm-mode-active="true"]' in css
    assert ':focus-visible' in css


def test_polished_right_context_width_uses_map_first_tokens():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert 'body.dm-map-first-active #sidebar-right.dm-map-first-right-context' in css
    assert 'width: var(--mf-right-context-width' in css
    assert 'max-width: var(--mf-right-context-width' in css


def test_polished_rail_width_uses_map_first_tokens():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert 'body.dm-map-first-active #sidebar-left.dm-map-first-rail' in css
    assert 'width: var(--mf-left-rail-width' in css
    assert '--mf-left-rail-width' in css


def test_polished_map_stage_still_uses_minmax_zero_one_fraction():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert 'minmax(0, 1fr)' in css
    assert 'grid-template-columns: var(--mf-left-rail-width' in css


def test_polished_debug_hidden_styling_still_exists():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert '[data-dm-debug-panel][hidden]' in css
    assert 'display: none !important;' in css


def test_polished_responsive_css_exists():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert '@media (max-width: 1100px)' in css
    assert '@media (max-width: 900px)' in css
    assert '@media (max-width: 680px)' in css
    assert '@media (prefers-reduced-motion: reduce)' in css


def test_polished_overlay_passthrough_is_limited_to_passive_overlays():
    css = read(Path('client/static/css/dm-map-first-shell.css'))
    assert 'body.dm-map-first-active #display-overlay-shell' in css
    assert 'body.dm-map-first-active #scene-description-overlay' in css
    assert 'body.dm-map-first-active #display-overlay-exit' in css
    assert 'body.dm-map-first-active #roll-visual-portal {' not in css
