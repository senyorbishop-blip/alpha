from pathlib import Path

BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')
RENDER = Path('client/static/js/ui/dm_context_render.js')
FIXES = Path('client/static/css/dm-map-first-fixes.css')
PLAY = Path('client/templates/play.html')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_map_first_css_hides_legacy_right_panels_and_combat_tracker():
    css = read(FIXES)
    for selector in [
        '#right-tab-bar',
        '.rtab-pane',
        '.rtab-panes',
        '.rtab-shell',
        '#right-panel-context',
        '#rtab-pane-combat',
        '#combat-list',
        '#combat-controls',
        '[data-legacy-combat-tracker]',
        '[data-selected-token-panel]',
    ]:
        assert selector in css
    assert 'body.dm-map-first-active:not(.dm-legacy-drawer-open)' in css
    assert '#dm-context-shell' in css


def test_map_first_does_not_force_hide_token_editor_modal():
    # The token editor (#token-editor) is a deliberately-opened centred modal,
    # not legacy right-panel chrome. It must NOT be in the map-first
    # display:none suppression block or the DM can never edit a token while in
    # map-first mode (the inline display:block loses to display:none !important).
    css = read(FIXES)
    assert '#token-editor' not in css, (
        '#token-editor must not be force-hidden by dm-map-first-fixes.css; it is a '
        'modal the DM opens via Edit Token.'
    )


def test_bridge_forces_legacy_panels_closed_after_activate_and_refresh():
    src = read(BRIDGE)
    assert 'function forceLegacyRightPanelsClosed' in src
    assert 'function ensureLegacyPanelObserver' in src
    assert 'new MutationObserver' not in src
    assert "window.__DISABLE_DM_MAP_FIRST_GUARD = true" in src
    assert 'window.__DM_MAP_FIRST_CAN_ENHANCE === true' in src
    assert 'new MutationObserver' not in src
    assert 'isDmMapFirstDisabled() || window.__DM_MAP_FIRST_CAN_ENHANCE !== true || isLegacyGuardDisabled()' in src
    assert "console.warn('[dm-panel-mode] activate skipped to preserve app boot'" in src
    assert 'forceLegacyRightPanelsClosed,' in src


def test_dm_token_selection_refreshes_new_context_without_legacy_drawer():
    src = read(PLAY)
    assert '_teTokenId = hit.id;' in src
    assert 'AppUIDMActions.selectToken(hit)' in src
    assert 'AppUIDMPanelModeBridge.refresh(document)' in src
    assert "document.body.classList.remove('dm-legacy-drawer-open')" in src
    assert 'AppUIDMPanelModeBridge.forceLegacyRightPanelsClosed(document)' in src


def test_combat_mode_exposes_clean_initiative_controls():
    src = read(RENDER)
    for label in [
        'Start Combat',
        'Roll Initiative',
        'Roll Selected Initiative',
        'Roll All Initiative',
        'Previous Turn',
        'Next / End Turn',
        'End Combat / Clear Combat',
        'Add Selected Token to Combat',
    ]:
        assert label in src


def test_roll_initiative_buttons_use_dm_action_bridge_not_switch_tab_only():
    src = read(RENDER)
    assert 'AppUIDMActions.rollInitiativeSelected()' in src
    assert 'AppUIDMActions.rollInitiativeAll()' in src
    assert 'combat_roll_initiative' in src
    assert 'sendCombatRollInitiative' in src


def test_old_combat_tracker_opens_only_through_compact_drawer_action():
    render = read(RENDER)
    bridge = read(BRIDGE)
    assert 'openCompactCombatDrawer' in render
    assert 'openCombatTracker: function () { return openLegacyDrawer(\'combat\'); }' in render
    assert 'dm-legacy-drawer-open' in render
    assert 'data-dm-compact-tab' in bridge
    assert 'switchRTab(\'' not in bridge.split('tabsEl.innerHTML', 1)[1].split(".join('')", 1)[0]


def test_player_and_viewer_paths_are_not_map_first_hardened():
    src = read(PLAY)
    assert "if (hitIsSelectable && ROLE === 'dm')" in src
    assert "if (ROLE !== 'dm' && _tokenOwnedByMe(tok))" in src
    assert "if (ROLE === 'player'" in src
    assert "ROLE === 'viewer'" in src
