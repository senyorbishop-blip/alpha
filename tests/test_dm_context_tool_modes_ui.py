from pathlib import Path

PLAY = Path('client/templates/play.html')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')
BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_map_build_mode_includes_fog_walls_doors_and_reveal_markers():
    src = read(PLAY)
    registry = read(REGISTRY)
    assert 'data-dm-mode="map-build"' in src
    for marker in ['fog-tools', 'wall-tools', 'door-tools', 'reveal-hide-tools']:
        assert marker in src
        assert marker in registry
    assert 'data-map-build-markers="fog-tools wall-tools door-tools reveal-hide-tools' in src


def test_npc_monster_mode_includes_bestiary_spawn_and_visibility_markers():
    src = read(PLAY)
    registry = read(REGISTRY)
    assert 'data-dm-mode="npc-monster"' in src
    for marker in ['bestiary-search', 'spawn-token', 'visibility-state']:
        assert marker in src
        assert marker in registry
    assert 'data-npc-monster-markers="bestiary-search spawn-token visibility-state' in src


def test_live_table_context_keeps_setup_and_debug_tools_out():
    src = read(PLAY)
    registry = read(REGISTRY)
    assert 'data-dm-mode="run"' in src
    for marker in ['wall-editor', 'fog-brush', 'shop-editor', 'debug-diagnostics']:
        assert marker in src
        assert marker in registry
    assert 'data-live-table-clean-markers="wall-editor fog-brush shop-editor debug-diagnostics"' in src


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
