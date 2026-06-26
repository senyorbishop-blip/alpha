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


def test_play_page_loads_polish_css_after_dm_shell():
    src = read(PLAY)
    shell = 'href="/static/css/dm-map-first-shell.css"'
    polish = 'href="/static/css/dm-map-first-polish.css"'
    assert polish in src
    assert src.rfind(shell) < src.rfind(polish)


def test_polished_map_first_active_mode_styling_exists():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert 'body.dm-map-first-active .dm-live-mode-rail .dm-map-first-mode-button[aria-pressed="true"]' in css
    assert 'body.dm-map-first-active .dm-live-mode-rail .dm-map-first-mode-button[data-dm-mode-active="true"]' in css
    assert ':focus-visible' in css


def test_polished_right_context_width_uses_map_first_tokens():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert 'body.dm-map-first-active #sidebar-right.dm-map-first-right-context' in css
    assert 'width: var(--mf-right-context-width' in css
    assert 'max-width: var(--mf-right-context-width' in css


def test_polished_rail_width_uses_map_first_tokens():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert 'body.dm-map-first-active #sidebar-left.dm-map-first-rail' in css
    assert 'width: var(--mf-left-rail-width' in css
    assert '--mf-left-rail-width' in css


def test_polished_map_stage_still_uses_minmax_zero_one_fraction():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert 'minmax(0, 1fr)' in css
    assert 'grid-template-columns: var(--mf-left-rail-width' in css


def test_polished_debug_hidden_styling_still_exists():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert '[data-dm-debug-panel][hidden]' in css
    assert 'display: none !important;' in css


def test_polished_responsive_css_exists():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert '@media (max-width: 1100px)' in css
    assert '@media (max-width: 900px)' in css
    assert '@media (max-width: 680px)' in css
    assert '@media (prefers-reduced-motion: reduce)' in css


def test_polished_overlay_passthrough_is_limited_to_passive_overlays():
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert 'body.dm-map-first-active #display-overlay-shell' in css
    assert 'body.dm-map-first-active #scene-description-overlay' in css
    assert 'body.dm-map-first-active #display-overlay-exit' in css
    assert 'body.dm-map-first-active #roll-visual-portal {' not in css
from pathlib import Path

PLAY = Path('client/templates/play.html')
REGISTRY = Path('client/static/js/ui/dm_mode_tool_registry.js')
BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')

EXPECTED_MODE_TOOLS = {
    'run': [
        'selected-token-summary', 'party-overview', 'current-scene-notes',
        'handout-shortcuts', 'journal-shortcuts', 'narration-shortcuts',
        'viewer-power-shortcuts', 'compact-save-state',
    ],
    'combat': [
        'initiative-order', 'current-turn', 'hp-summary', 'conditions',
        'action-usage', 'movement-usage', 'attack-roll-helpers',
        'damage-roll-helpers', 'save-dc-helpers', 'end-turn-controls',
    ],
    'map-build': [
        'terrain-tools', 'fog-tools', 'wall-tools', 'door-tools',
        'reveal-hide-tools', 'token-layer', 'prop-layer',
        'lighting-weather-tools', 'asset-library', 'map-save-apply',
    ],
    'npc-monster': [
        'bestiary-search', 'spawn-token', 'creature-hp-ac-speed',
        'visibility-state', 'initiative-modifier', 'conditions',
        'creature-notes', 'creature-quick-actions',
    ],
    'loot-shop': [
        'item-search', 'loot-containers', 'corpse-loot', 'shop-setup',
        'grant-item', 'grant-gold', 'charges', 'attunement',
        'party-inventory-adjustments',
    ],
    'session-tools': [
        'quests', 'handouts', 'journal', 'discoveries', 'narration',
        'sound', 'polls', 'party-messages', 'autosave-save-tools',
    ],
    'viewer-powers': [
        'connected-viewers', 'viewer-power-grants', 'pending-approvals',
        'cooldowns', 'target-selection', 'approved-rejected-feedback',
    ],
    'debug': [
        'stream-readiness', 'payload-warnings', 'reconnect-warnings',
        'websocket-diagnostics', 'sync-diagnostics', 'visibility-checks',
        'dm-focus-testing-guidance', 'development-only-hints',
    ],
}


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_dm_audit_all_expected_tool_markers_have_mode_homes():
    play = _read(PLAY)
    registry = _read(REGISTRY)
    for mode, tools in EXPECTED_MODE_TOOLS.items():
        assert f"data-dm-mode=\"{mode}\"" in play or f"{mode}: Object.freeze" in registry or f"'{mode}': Object.freeze" in registry
        for tool in tools:
            assert f"data-dm-tool=\"{tool}\"" in play, f"missing marker for {mode}:{tool}"
            assert f"'{tool}'" in registry, f"missing registry entry for {mode}:{tool}"


def test_dm_audit_existing_controls_gained_stable_markers_without_handler_changes():
    play = _read(PLAY)
    expected_fragments = [
        'id="rail-editor-btn" data-dm-tool="terrain-tools" data-help="dm-map-editor" onclick="toggleFlyout(\'flyout-editor\')"',
        'id="rail-fog-btn" data-dm-tool="fog-tools" data-help="dm-fog" onclick="toggleFlyout(\'flyout-fog\')"',
        'id="rail-sound-btn" data-dm-tool="narration-shortcuts" onclick="toggleFlyout(\'flyout-sound\')"',
        'id="rail-perm-btn" data-dm-tool="viewer-power-shortcuts" onclick="toggleFlyout(\'flyout-perm\')"',
        'id="editor-wall-tool-door" data-dm-tool="door-tools"',
        'id="editor-save-btn" data-dm-tool="map-save-apply"',
    ]
    for fragment in expected_fragments:
        assert fragment in play


def test_dm_audit_more_legacy_tools_preserves_unmigrated_controls():
    play = _read(PLAY)
    assert 'data-dm-context-section="legacy-tools-fallback"' in play
    assert 'More / Legacy Tools' in play
    assert 'Existing tools remain in the left rail flyouts and legacy right tabs until a later migration.' in play


def test_dm_audit_debug_hidden_by_default_and_explicitly_closed():
    play = _read(PLAY)
    registry = _read(REGISTRY)
    bridge = _read(BRIDGE)
    assert 'data-dm-context-section="debug" aria-label="Debug DM tools" data-dm-debug-panel hidden' in play
    assert 'closedByDefault: true' in registry
    assert "activeMode === 'debug' ? 'true' : 'false'" in bridge


def test_dm_audit_map_first_shell_keeps_map_central_after_mode_switches():
    play = _read(PLAY)
    bridge = _read(BRIDGE)
    css = _read(Path('client/static/css/dm-map-first-polish.css'))
    assert '<span class="dm-context-map-note">Map remains primary</span>' in play
    assert "buttons.forEach((button) => {" in bridge
    assert 'grid-template-columns: var(--mf-left-rail-width' in css
    assert 'minmax(0, 1fr)' in css


def test_npc_monster_compact_adapter_reuses_existing_bestiary_and_token_handlers():
    src = read(BRIDGE)
    assert "dm-compact-bestiary-search" in src
    assert "doc.getElementById('bestiary-search')" in src
    assert "existing.dispatchEvent(new Event('input', { bubbles: true }))" in src
    assert "beginBestiarySpawn" in src
    assert "switchRTab('bestiary')" in src
    assert "toggleFlyout('flyout-token')" in src
    assert "switchRTab('combat')" in src


def test_npc_monster_visible_panel_hides_registry_audit_rows_by_default():
    bridge = read(BRIDGE)
    css = read(Path('client/static/css/dm-map-first-polish.css'))
    assert "appendNpcMonsterPanel(doc, section)" in bridge
    assert "appendTextElement" not in bridge
    assert "section.dataset.dmModeHelp = definition.description" in bridge
    assert "marker.hidden = true" in bridge
    assert "body.dm-map-first-active .dm-context-marker-grid" in css
    assert "clip-path: inset(50%) !important" in css
    assert "body.dm-map-first-active .dm-npc-compact-panel" in css
    assert "body.dm-map-first-active #right-panel-context" in css
    assert "display: none !important" in css


def test_creature_spawn_route_contract_remains_unchanged():
    routes = read(Path('server/creatures/routes.py'))
    service = read(Path('server/creatures/service.py'))
    assert '@router.get("/api/library/creatures")' in routes
    assert '@router.post("/api/library/creatures/{creature_id}/spawn")' in routes
    assert 'return await spawn_creature_response(creature_id, request, body)' in routes
    for field in ['session_id', 'user_id', 'map_context', 'grid_size_px', 'gridSizePx']:
        assert field in service
    assert '"from_bestiary": True' in service
    assert '"token_created"' in service


def test_rich_dm_context_uses_action_bridge_instead_of_hidden_switch_tabs():
    src = read(Path('client/static/js/ui/dm_context_render.js'))
    assert 'window.AppUIDMActions = Actions' in src
    assert 'openLegacyDrawer(tab)' in src
    visible = src[src.index('var RENDER = {'):]
    assert 'onclick="switchRTab' not in visible
    assert 'onclick="toggleFlyout' not in visible
    assert 'AppUIDMActions.openCombatTracker()' in visible
    assert 'AppUIDMActions.openViewerPowers()' in visible


def test_rich_combat_mode_exposes_real_encounter_controls():
    src = read(Path('client/static/js/ui/dm_context_render.js'))
    for label, action in [
        ('Start Combat', 'AppUIDMActions.startCombat()'),
        ('Previous Turn', 'AppUIDMActions.previousTurn()'),
        ('End / Next Turn', 'AppUIDMActions.nextTurn()'),
        ('End Combat', 'AppUIDMActions.endCombat()'),
        ('Roll Initiative', 'AppUIDMActions.rollInitiative()'),
        ('Add Combatant', 'AppUIDMActions.addCombatant()'),
        ('Add Selected Token', 'AppUIDMActions.addSelectedTokenToCombat()'),
        ('Open Tracker', 'AppUIDMActions.openCombatTracker()'),
    ]:
        assert label in src
        assert action in src
    for fn in ['combatStart', 'combatPrev', 'combatNext', 'combatClear', 'combatRollInitiative', 'combatAddManual']:
        assert f"callGlobal('{fn}'" in src


def test_rich_viewer_powers_mode_exposes_grants_approvals_cooldowns_and_settings():
    src = read(Path('client/static/js/ui/dm_context_render.js'))
    for label, action in [
        ('Grant Power', 'AppUIDMActions.openViewerPowers()'),
        ('Pending Approvals', 'AppUIDMActions.openViewerPowers()'),
        ('Approve Pending', 'AppUIDMActions.approveViewerPower()'),
        ('Reject Pending', 'AppUIDMActions.rejectViewerPower()'),
        ('Cooldowns / Settings', 'AppUIDMActions.openViewerPowerSettings()'),
        ('Target Selection', 'AppUIDMActions.openViewerPowers()'),
    ]:
        assert label in src
        assert action in src
    for fn in ['grantViewerPower', 'grantViewerPowerPreset', 'decideViewerPending']:
        assert f"callGlobal('{fn}'" in src


def test_map_first_hidden_right_tabs_have_controlled_legacy_drawer_adapter():
    css = read(Path('client/static/css/dm-map-first-fixes.css'))
    js = read(Path('client/static/js/ui/dm_context_render.js'))
    assert 'body.dm-map-first-active #right-tab-bar,' in css
    assert 'body.dm-map-first-active.dm-legacy-drawer-open #sidebar-right .rtab-shell' in css
    assert "document.body.classList.add('dm-legacy-drawer-open')" in js
    assert 'body.dm-map-first-active.dm-legacy-drawer-open #right-tab-bar' in css
