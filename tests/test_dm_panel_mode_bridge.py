from pathlib import Path

BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')
EXPECTED_MODES = [
    'run',
    'combat',
    'map-build',
    'npc-monster',
    'loot-shop',
    'session-tools',
    'viewer-powers',
    'debug',
]


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_bridge_file_exists():
    assert BRIDGE.exists()


def test_bridge_exposes_expected_window_api():
    src = read(BRIDGE)
    assert 'window.AppUIDMPanelModeBridge' in src
    for api in [
        'listModes',
        'getModeConfig',
        'classifyElement',
        'registerPanelSection',
        'activateMode',
        'init',
    ]:
        assert api in src


def test_every_registry_mode_is_supported_by_bridge():
    bridge = read(BRIDGE)
    registry = read(REGISTRY)
    assert 'window.AppUIDMModeToolRegistry' in bridge
    for mode in EXPECTED_MODES:
        assert f"{mode}:" in registry or f"'{mode}':" in registry
        assert mode in bridge


def test_unknown_mode_falls_back_safely_to_live_table():
    src = read(BRIDGE)
    assert "const FALLBACK_MODE = 'run'" in src
    assert 'normalizeMode(modeId)' in src
    assert ': FALLBACK_MODE' in src
    assert 'getModeConfig(FALLBACK_MODE)' in src


def test_debug_is_closed_by_default():
    bridge = read(BRIDGE)
    registry = read(REGISTRY)
    assert 'closedByDefault: true' in registry
    assert "debug: { label: 'Debug', primaryTools: [], closedByDefault: true }" in bridge
    assert "const FALLBACK_MODE = 'run'" in bridge


def test_old_controls_are_preserved_not_deleted():
    src = read(BRIDGE)
    assert '.remove()' not in src
    assert 'removeChild' not in src
    assert 'replaceChildren' not in src
    assert 'element.hidden = !isActive' in src
    assert 'classList.toggle(MODE_INACTIVE_CLASS, !isActive)' in src
    assert 'dataset.dmModeActive' in src


def test_bridge_uses_dm_data_attributes_for_classification():
    src = read(BRIDGE)
    assert '[data-dm-mode], [data-dm-tool], [data-dm-section]' in src
    assert 'element.dataset.dmMode' in src
    assert 'element.dataset.dmTool' in src
    assert 'element.dataset.dmSection' in src
