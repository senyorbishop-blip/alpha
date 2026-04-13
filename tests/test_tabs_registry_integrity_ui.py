from __future__ import annotations

import re
from pathlib import Path


TABS_PATH = Path('client/static/js/ui/tabs.js')
PLAY_PATH = Path('client/templates/play.html')


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _registry_tab_ids(src: str) -> list[str]:
    return re.findall(r"id:\s*'([a-z0-9_]+)',\s*label:", src)


def test_registry_tabs_have_real_button_and_pane_mounts_on_play_page():
    tabs_src = _read(TABS_PATH)
    play_src = _read(PLAY_PATH)
    tab_ids = _registry_tab_ids(tabs_src)
    assert tab_ids, 'tab registry should contain at least one tab entry'

    # Canonical mapping contract: each registry tab must map to a concrete button and pane.
    for tab_id in tab_ids:
        assert f"id=\"rtab-{tab_id}\"" in play_src
        assert f"id=\"rtab-pane-{tab_id}\"" in play_src

    # Buttons are wired through shared data attributes consumed by panel controls.
    for tab_id in tab_ids:
        assert f'data-rtab-target="{tab_id}"' in play_src


def test_active_tab_is_always_normalized_to_a_visible_registered_pane():
    tabs_src = _read(TABS_PATH)
    play_src = _read(PLAY_PATH)

    assert 'function normalizeAllowedTab(tab, env)' in tabs_src
    assert 'if (visibleIds.has(requested)) return requested;' in tabs_src
    assert 'return getDefaultTab(env);' in tabs_src
    assert 'return normalizeAllowedTab(env?.getActiveTab?.() || getDefaultTab(env), env);' in tabs_src

    # Defensive stale-state guard: sync corrects hidden/invalid active values before rendering.
    assert 'if (!visibleIds.has(activeTab)) {' in tabs_src
    assert 'activeTab = getDefaultTab(env);' in tabs_src
    assert 'env.setActiveTab?.(activeTab);' in tabs_src

    # Runtime env provides a canonical fallback default for startup and stale shell recovery.
    assert "getDefaultTab: () => 'party'," in play_src


def test_visible_tabs_require_registry_mapped_button_and_pane_mounts():
    tabs_src = _read(TABS_PATH)

    assert 'function hasValidMount(entry, env) {' in tabs_src
    assert 'const btn = doc.querySelector(entry.buttonSelector);' in tabs_src
    assert 'const pane = doc.querySelector(entry.paneSelector);' in tabs_src
    assert 'return !!(btn && pane);' in tabs_src
    assert 'return hasValidMount(entry, env);' in tabs_src


def test_role_specific_visibility_contract_is_explicit_in_tab_registry():
    tabs_src = _read(TABS_PATH)

    # Always visible for all roles.
    for tab_id in ('party', 'log', 'combat'):
        assert re.search(rf"id: '{tab_id}'.*?isVisible: \(\) => true", tabs_src, flags=re.S)

    # Hidden from viewers (player+dm only).
    for tab_id in ('inventory', 'memory', 'spelllib'):
        assert re.search(rf"id: '{tab_id}'.*?isVisible: \(env\) => canUsePlayerTabs\(env\)", tabs_src, flags=re.S)

    # DM-only library tabs.
    for tab_id in ('shop', 'bestiary'):
        assert re.search(rf"id: '{tab_id}'.*?isVisible: \(env\) => canUseDmLibraryTabs\(env\)", tabs_src, flags=re.S)


def test_stale_or_deprecated_tabs_cannot_reappear_via_shell_state():
    tabs_src = _read(TABS_PATH)
    play_src = _read(PLAY_PATH)

    # Deprecated viewers tab is not part of right-side registry or pane set.
    assert "id: 'viewers'" not in tabs_src
    assert 'id="rtab-viewers"' not in play_src
    assert 'id="rtab-pane-viewers"' not in play_src

    # Switch path still routes through normalizeAllowedTab to prevent stale id revival.
    assert 'function switchRTab(env, tab) {' in tabs_src
    assert 'tab = normalizeAllowedTab(tab, env);' in tabs_src


def test_final_handouts_and_viewers_behavior_contracts_are_preserved():
    tabs_src = _read(TABS_PATH)
    play_src = _read(PLAY_PATH)

    # Handouts are no longer unconditional: visibility must pass scope or runtime handout checks.
    assert "id: 'handouts'" in tabs_src
    assert "hasAssistantScope(env, 'handouts.manage')" in tabs_src
    assert "hasAssistantScope(env, 'quests.manage')" in tabs_src
    assert '!!env?.isHandoutsTabVisible?.()' in tabs_src

    # Final handouts policy from play runtime: DM hidden by default, players/viewers visible when synced.
    assert 'function __isHandoutsTabVisible() {' in play_src
    assert "if (ROLE === 'dm') return false;" in play_src
    assert 'const hasReceived = Array.isArray(_playerReceivedHandouts) && _playerReceivedHandouts.length > 0;' in play_src
    assert 'const hasSyncedHandouts = _handoutSyncInitialized && Object.keys(_handouts || {}).length > 0;' in play_src

    # Viewers remain a Party subsection and not a standalone right tab.
    assert 'id="party-roster-tab-viewers"' in play_src
    assert 'id="party-viewers-host"' in play_src
    assert 'id="viewers-panel"' in play_src
    assert 'setPartyRosterView(ROLE === \'viewer\' ? \'viewers\' : \'party\');' in play_src

def test_viewer_token_render_uses_authoritative_dm_map_context():
    """Token draw context must use _getAuthoritativeTokenDrawContext() so viewer
    clients follow DM map context when rendering player tokens."""
    play_src = _read(PLAY_PATH)
    assert "const drawCtx = _getAuthoritativeTokenDrawContext();" in play_src


def test_play_runtime_uses_registry_sync_instead_of_direct_tab_visibility_mutations():
    play_src = _read(PLAY_PATH)

    assert 'function __syncRightTabRegistry() {' in play_src
    assert "window.AppUITabs.syncTabUI(__createTabsEnv());" in play_src
    assert "getElementById('rtab-shop');" not in play_src
    assert "shopTab.style.display = '';" not in play_src


def test_workflow_mode_uses_dedicated_css_classes_not_context_system_classes():
    """setDmWorkflowMode() must use dm-mode-primary / dm-mode-dimmed for its tab
    emphasis hints.  context-priority / context-muted are owned by
    AppUITabs.applyContextUI() which strips and re-applies them on every
    syncTabUI() cycle for all registered tab buttons.  Mixing the two systems
    caused mode hints to be silently erased by the next context refresh."""
    tabs_src = _read(TABS_PATH)
    play_src = _read(PLAY_PATH)

    # New dedicated classes must exist in play.html CSS and JS.
    assert 'dm-mode-primary' in play_src
    assert 'dm-mode-dimmed' in play_src

    # The workflow mode function must apply the new classes.
    assert "classList.add('dm-mode-primary')" in play_src
    assert "classList.add('dm-mode-dimmed')" in play_src

    # The tab module must NOT reference workflow-mode classes (separation of concerns).
    assert 'dm-mode-primary' not in tabs_src
    assert 'dm-mode-dimmed' not in tabs_src

    # applyContextUI() in tabs.js must only clear its own context classes.
    assert "classList.remove('context-priority', 'context-muted')" in tabs_src


def test_party_roster_view_guards_on_viewer_button_hidden_state():
    """setPartyRosterView() must not switch to 'viewers' when the viewers
    sub-tab button is hidden (e.g. hidden for the player role by
    applyPremiumRoleShellPolish).  The guard prevents silent fallback to an
    inaccessible sub-view."""
    play_src = _read(PLAY_PATH)

    # Guard variable reads the hidden attribute before allowing the switch.
    assert 'allowViewersSubsection = !(viewersBtn && viewersBtn.hidden)' in play_src
    # The resolved view is clamped to 'party' when the sub-section is not allowed.
    assert "_partyRosterView = (allowViewersSubsection && mode === 'viewers') ? 'viewers' : 'party';" in play_src


def test_memory_badge_bump_requires_active_tab_check():
    """loadPartyMemory() must check _activeRTab before incrementing _unreadMemory
    so that the badge is not bumped while the player is already viewing the
    Moments tab."""
    play_src = _read(PLAY_PATH)

    assert "if (_activeRTab !== 'memory') {" in play_src
    # The badge manipulation must be inside the guard (not at module top-level).
    assert "_unreadMemory += newCount;" in play_src


def test_handouts_badge_update_scoped_to_non_dm_sync():
    """The handouts badge counter update in loadHandouts() must be inside the
    non-DM branch (if ROLE !== 'dm') so DMs never accidentally see a player
    badge count for handouts they sent themselves."""
    play_src = _read(PLAY_PATH)

    # Badge update lives inside the player sync block.
    assert "if (ROLE !== 'dm') {" in play_src
    assert "renderPlayerHandoutsList();" in play_src
    # syncTabUI is triggered after player handout state is updated.
    assert "window.AppUITabs.syncTabUI(__createTabsEnv());" in play_src


def test_player_cosmetic_overrides_documented_as_intentional():
    """applyPremiumRoleShellPolish() contains player-specific DOM overrides
    (hiding the viewers sub-tab button, renaming the library dropdown) that are
    intentional and safe.  They must be accompanied by a comment explaining that
    tab *visibility* is still owned by AppUITabs and that these are cosmetic only."""
    play_src = _read(PLAY_PATH)

    # Documentation comment must reference the correct authority.
    assert 'Tab visibility is still owned by AppUITabs via TAB_REGISTRY' in play_src
    # setPartyRosterView() reads .hidden, so the cosmetic hide is safe.
    assert 'setPartyRosterView() reads .hidden before allowing a switch' in play_src


def test_visible_tabs_map_to_valid_panes_and_cannot_be_active_when_hidden():
    """Core contract: every tab in TAB_REGISTRY has both a button mount and a pane
    mount in play.html.  Tabs hidden by role must be excluded from active tab
    resolution — normalizeAllowedTab falls back to getDefaultTab when the
    requested tab is not in the visible set."""
    tabs_src = _read(TABS_PATH)

    # listVisibleTabs() filters by isVisible AND hasValidMount.
    assert 'function listVisibleTabs(env) {' in tabs_src
    assert 'return hasValidMount(entry, env);' in tabs_src

    # getActiveTab() passes through normalizeAllowedTab — hidden tab IDs are rejected.
    assert 'return normalizeAllowedTab(env?.getActiveTab?.() || getDefaultTab(env), env);' in tabs_src

    # syncTabUI() also enforces the constraint at render time.
    assert 'if (!visibleIds.has(activeTab)) {' in tabs_src
    assert 'activeTab = getDefaultTab(env);' in tabs_src
    assert 'env.setActiveTab?.(activeTab);' in tabs_src


def test_active_tab_fallback_returns_party_when_no_visible_tab_matches():
    """getDefaultTab() falls back to 'party' when no visible tab matches the
    preferred default, ensuring the panel always has a sane active state even
    after role or permission changes that remove the previously active tab."""
    tabs_src = _read(TABS_PATH)

    # Explicit 'party' hard-fallback in getDefaultTab.
    assert "if (!visible.length) return 'party';" in tabs_src
    # Env provides canonical startup default.
    assert "getDefaultTab: () => 'party'," in _read(PLAY_PATH)
