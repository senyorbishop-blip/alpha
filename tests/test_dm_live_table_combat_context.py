from pathlib import Path

PLAY = Path('client/templates/play.html')
BRIDGE = Path('client/static/js/ui/dm_panel_mode_bridge.js')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_live_table_context_contains_expected_live_session_markers():
    src = read(PLAY)
    assert 'data-dm-context-section="live-table"' in src
    for marker in [
        'selected-token-summary',
        'party-overview',
        'current-scene-notes',
        'compact-save-state',
    ]:
        assert f'data-dm-tool="{marker}"' in src


def test_combat_context_contains_expected_combat_markers():
    src = read(PLAY)
    assert 'data-dm-context-section="combat"' in src
    for marker in [
        'initiative-order',
        'current-turn',
        'hp-summary',
        'conditions',
        'action-usage',
        'movement-usage',
        'attack-roll-helpers',
        'damage-roll-helpers',
        'save-dc-helpers',
        'end-turn-controls',
    ]:
        assert f'data-dm-tool="{marker}"' in src


def test_switching_modes_hides_inactive_sections():
    bridge = read(BRIDGE)
    assert 'element.hidden = !isActive' in bridge
    assert "element.dataset.dmModeActive = String(isActive)" in bridge
    assert 'classList.toggle(MODE_INACTIVE_CLASS, !isActive)' in bridge
    assert "titleEl.textContent = activeConfig.label" in bridge


def test_loot_shop_context_contains_expected_economy_markers():
    src = read(PLAY)
    assert 'data-dm-context-section="loot-shop"' in src
    for marker in [
        'item-search',
        'loot-containers',
        'corpse-loot',
        'shop-setup',
        'grant-item',
        'grant-gold',
        'charges',
        'attunement',
        'party-inventory-adjustments',
    ]:
        assert f'data-dm-tool="{marker}"' in src


def test_session_tools_context_contains_expected_story_markers():
    src = read(PLAY)
    assert 'data-dm-context-section="session-tools"' in src
    for marker in [
        'quests',
        'handouts',
        'journal',
        'discoveries',
        'narration',
        'sound',
        'polls',
        'party-messages',
        'autosave-save-tools',
    ]:
        assert f'data-dm-tool="{marker}"' in src


def test_viewer_powers_context_contains_expected_dm_only_markers():
    src = read(PLAY)
    assert 'data-dm-context-section="viewer-powers"' in src
    assert 'aria-label="Viewer Powers DM tools" data-dm-only="true"' in src
    for marker in [
        'connected-viewers',
        'viewer-power-grants',
        'pending-approvals',
        'cooldowns',
        'target-selection',
        'approved-rejected-feedback',
    ]:
        assert f'data-dm-tool="{marker}"' in src


def test_combat_controls_still_exist_in_dom_with_existing_handlers():
    src = read(PLAY)
    for snippet in [
        'id="combat-pre"',
        'onclick="combatStart()"',
        'id="combat-controls"',
        'onclick="combatPrev()"',
        'onclick="combatNext()"',
        'onclick="combatClear()"',
        'id="combat-turn-summary"',
        'id="combat-list"',
        'id="combat-add-row"',
        'onclick="combatAddManual()"',
    ]:
        assert snippet in src


def test_live_table_controls_still_exist_in_dom_with_existing_handlers():
    src = read(PLAY)
    for snippet in [
        'id="selected-quick-panel"',
        'id="players-panel"',
        'id="party-status-panel"',
        'id="rtab-handouts"',
        'id="rail-journal-btn" onclick="toggleFlyout(\'flyout-journal\')"',
        'id="rail-sound-btn" onclick="toggleFlyout(\'flyout-sound\')"',
        'id="viewer-power-controls"',
        'id="item-library-modal"',
        'id="party-stash-widget"',
        'id="ctx-corpse-search"',
        'id="inventory-tools"',
        'id="party-treasury-widget"',
        'id="poll-dm-controls"',
        'id="save-btn"',
        'onclick="saveCampaign()"',
    ]:
        assert snippet in src


def test_player_viewer_screens_unchanged_dm_context_is_dm_only():
    src = read(PLAY)
    assert 'id="dm-context-shell"' in src and 'data-dm-context-shell="true" hidden' in src
    assert "if (ROLE === 'dm')" in src
    assert "if (dmContextShell) dmContextShell.hidden = false;" in src
    assert "ROLE === 'player'" in src
    assert "ROLE === 'viewer'" in src
