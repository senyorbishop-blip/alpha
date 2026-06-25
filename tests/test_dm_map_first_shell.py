from pathlib import Path

DOC = Path('docs/ui-dm-map-first-shell.md')
CSS = Path('client/static/css/dm-map-first-shell.css')
JS = Path('client/static/js/ui/dm_map_first_shell.js')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_dm_shell_scaffold_files_exist():
    assert DOC.exists()
    assert CSS.exists()
    assert JS.exists()
    assert REGISTRY.exists()


def test_dm_shell_documents_map_first_layout():
    text = read(DOC)
    for phrase in [
        'The map remains the largest element',
        'left mode rail',
        'right context panel',
        'bottom quick strip',
        'no full `play.html` rewrite',
    ]:
        assert phrase in text


def test_live_table_replaces_run_game_as_user_facing_label():
    doc = read(DOC)
    js = read(JS)
    assert 'Live Table' in doc
    assert "label: 'Live Table'" in js
    assert "id: 'run'" in js
    assert 'run-game' in js


def test_dm_shell_modes_cover_all_core_dm_sections():
    text = read(JS)
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
        assert mode in text


def test_dm_shell_context_covers_all_major_tools():
    text = read(JS)
    for tool in [
        'selected-token',
        'party-overview',
        'initiative',
        'movement-used',
        'fog',
        'walls',
        'doors',
        'lighting-weather',
        'bestiary',
        'loot-containers',
        'shops',
        'journal',
        'sound',
        'connected-viewers',
        'approvals',
        'sync-diagnostics',
    ]:
        assert tool in text


def test_dm_mode_tool_registry_maps_tools_without_losing_functions():
    registry = read(REGISTRY)
    required = [
        'Live Table',
        'selected-token-summary',
        'party-overview',
        'current-scene-notes',
        'initiative-order',
        'fog-tools',
        'wall-tools',
        'door-tools',
        'bestiary-search',
        'shop-setup',
        'viewer-power-grants',
        'pending-approvals',
        'stream-readiness',
        'websocket-diagnostics',
    ]
    for phrase in required:
        assert phrase in registry


def test_dm_shell_css_keeps_map_as_primary_region():
    css = read(CSS)
    assert 'grid-template-areas' in css
    assert '"rail map context"' in css
    assert 'minmax(0, 1fr)' in css
    assert '.dm-map-first-map-stage' in css
    assert '.dm-map-first-right-context' in css
    assert '.dm-map-first-quick-strip' in css


def test_debug_panel_is_hidden_unless_opened():
    css = read(CSS)
    assert '[data-dm-debug-panel]' in css
    assert 'data-debug-open="true"' in css
    assert 'display: none !important' in css
    registry = read(REGISTRY)
    assert 'closedByDefault: true' in registry
