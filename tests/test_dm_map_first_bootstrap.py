from pathlib import Path

PLAY = Path('client/templates/play.html')
BOOTSTRAP = Path('client/static/js/ui/dm_map_first_bootstrap.js')
SHELL_CSS = Path('client/static/css/dm-map-first-shell.css')
POLISH_CSS = Path('client/static/css/dm-map-first-polish.css')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')


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
    # The base stylesheet can be preceded by token defaults, but the final map-first
    # shell stylesheet must still layer after play.css for runtime overrides.
    assert src.index('/static/css/play.css') < src.rindex('/static/css/map-first-ui-tokens.css')
    assert src.rindex('/static/css/map-first-ui-tokens.css') < src.rindex('/static/css/dm-map-first-shell.css')
    # The runtime bootstrap block at the end of play.html owns the active map-first
    # boot order; earlier compatibility loads must not be treated as the ordering source.
    assert src.rindex('/static/js/ui/dm_map_first_shell.js') < src.rindex('/static/js/ui/dm_mode_tool_registry.js')
    assert src.rindex('/static/js/ui/dm_mode_tool_registry.js') < src.rindex('/static/js/ui/dm_panel_mode_bridge.js')
    assert src.rindex('/static/js/ui/dm_panel_mode_bridge.js') < src.rindex('/static/js/ui/dm_map_first_bootstrap.js')


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



def test_dm_map_first_has_emergency_kill_switch_and_deferred_boot():
    play = read(PLAY)
    bootstrap = read(BOOTSTRAP)
    assert 'disable_dm_map_first' in play
    assert 'disableDmMapFirst' in play
    assert 'window.__DISABLE_DM_MAP_FIRST' in play
    assert 'Do not call AppUIDMPanelModeBridge.init() during core boot.' in play
    assert 'window.AppUIDMMapFirstBootstrap.init()' in play
    assert play.index("console.info('[play-boot] connectWS start'") < play.index("console.info('[dm-map-first] init start'")
    assert 'disable_dm_map_first' in bootstrap
    assert 'disableDmMapFirst' in bootstrap
    assert 'initialized: false, disabled: true' in bootstrap

def test_debug_remains_hidden_by_default():
    css = read(SHELL_CSS)
    assert '.dm-map-first-shell:not([data-debug-open="true"]) [data-dm-debug-panel]' in css
    assert 'display: none !important' in css
    assert 'data-debug-open="true"' in css


def test_final_polish_keeps_dm_rail_active_styling_obvious():
    css = read(POLISH_CSS)
    assert 'body.dm-map-first-active .dm-live-mode-rail .dm-map-first-mode-button[aria-pressed="true"]' in css
    assert 'body.dm-map-first-active .dm-live-mode-rail .dm-map-first-mode-button[data-dm-mode-active="true"]' in css
    assert 'rgba(212, 166, 55, 0.72)' in css
    assert 'box-shadow: 0 0 0 1px rgba(212, 166, 55, 0.18) inset' in css


def test_final_polish_context_panel_width_is_controlled_and_internal_scrolls():
    css = read(POLISH_CSS)
    assert 'body.dm-map-first-active #sidebar-right.dm-map-first-right-context' in css
    assert 'width: var(--mf-right-context-width, clamp(18rem, 23vw, 25rem))' in css
    assert 'max-width: var(--mf-right-context-width, clamp(18rem, 23vw, 25rem))' in css
    assert 'overflow: hidden' in css
    assert 'body.dm-map-first-active .dm-map-first-context-body' in css
    assert 'overflow-y: auto' in css
    assert 'overflow-x: hidden' in css


def test_final_polish_map_stage_remains_minmax_and_rail_does_not_squeeze_map():
    css = read(POLISH_CSS)
    assert 'grid-template-columns: var(--mf-left-rail-width, 4.75rem) minmax(0, 1fr) var(--mf-right-context-width, clamp(18rem, 23vw, 25rem))' in css
    assert 'body.dm-map-first-active #canvas-wrap.dm-map-first-map-stage[data-map-primary="true"]' in css
    assert 'min-width: 0' in css
    assert '--mf-left-rail-width: 4.35rem' in css
    assert '--mf-left-rail-width: 3.65rem' in css


def test_final_polish_dm_shell_does_not_apply_to_player_or_viewer():
    src = read(PLAY)
    css = read(POLISH_CSS)
    assert "if (ROLE === 'dm')" in src
    assert "document.body.classList.add('dm-map-first-active')" in src
    assert "ROLE === 'player'" not in src[src.index("document.body.classList.add('dm-map-first-active')") - 80:src.index("document.body.classList.add('dm-map-first-active')") + 120]
    assert "ROLE === 'viewer'" not in src[src.index("document.body.classList.add('dm-map-first-active')") - 80:src.index("document.body.classList.add('dm-map-first-active')") + 120]
    assert 'body.dm-map-first-active' in css
    assert 'body:not(.dm-map-first-active) #dm-live-mode-rail' in css


def test_final_polish_more_legacy_tools_and_debug_hidden_remain_available():
    src = read(PLAY)
    css = read(POLISH_CSS)
    assert 'More / Legacy Tools' in src
    assert 'dm-legacy-tools-fallback' in src
    # The standalone "more" quick-strip button was dropped; legacy-tool access now
    # lives in its dedicated context section, which remains available.
    assert 'data-dm-context-section="legacy-tools-fallback"' in src
    assert 'data-dm-debug-panel hidden' in src
    assert 'body.dm-map-first-active:not([data-debug-open="true"]) [data-dm-debug-panel]' in css
    assert 'display: none !important' in css


def test_final_polish_quick_strip_is_clean_and_does_not_block_map_interaction():
    css = read(POLISH_CSS)
    assert 'body.dm-map-first-active #dm-map-first-quick-strip.dm-map-first-quick-strip' in css
    assert 'pointer-events: none' in css
    assert 'body.dm-map-first-active #dm-map-first-quick-strip .dm-map-first-quick-action' in css
    assert 'pointer-events: auto' in css
    assert 'max-width: min(36rem, calc(100% - 1.5rem))' in css


def test_final_polish_expected_dm_tool_markers_remain_registered():
    src = read(PLAY) + read(REGISTRY)
    expected = [
        'selected-token-summary', 'party-overview', 'current-scene-notes',
        'initiative-order', 'current-turn', 'action-usage', 'movement-usage',
        'terrain-tools', 'fog-tools', 'wall-tools', 'door-tools', 'asset-library',
        'bestiary-search', 'spawn-token', 'creature-hp-ac-speed',
        'item-search', 'loot-containers', 'shop-setup', 'grant-item', 'grant-gold',
        'quests', 'handouts', 'journal', 'narration', 'sound', 'polls',
        'connected-viewers', 'viewer-power-grants', 'pending-approvals',
    ]
    for marker in expected:
        assert marker in src


def test_final_polish_has_focus_responsive_and_reduced_motion_rules():
    css = read(POLISH_CSS)
    assert ':focus-visible' in css
    assert '@media (max-width: 1100px)' in css
    assert '@media (max-width: 900px)' in css
    assert '@media (max-width: 680px)' in css
    assert '@media (prefers-reduced-motion: reduce)' in css
