"""
tests/test_help_hub_ui.py — Tests for the Help Hub in onboarding.js

Covers:
- AppOnboarding includes all Help Hub topic keys
- All 8 guide categories exist in GUIDE_STEPS
- Help Hub has player / DM / viewer topic lists
- showHelpHub, showCombatHint, createHelpHubButton are exported
- player dashboard exposes Help and Combat Guide buttons
- character sheet Actions tab is renamed to "Combat / Actions"
- topbar help button now opens Help Hub
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# ── onboarding.js: public API ─────────────────────────────────────────────

def test_onboarding_exports_show_help_hub():
    src = _read("client/static/js/ui/onboarding.js")
    assert "showHelpHub" in src
    assert "window.AppOnboarding" in src
    assert "showHelpHub:         showHelpHub" in src


def test_onboarding_exports_show_combat_hint():
    src = _read("client/static/js/ui/onboarding.js")
    assert "showCombatHint" in src
    assert "showCombatHint:      showCombatHint" in src


def test_onboarding_exports_create_help_hub_button():
    src = _read("client/static/js/ui/onboarding.js")
    assert "createHelpHubButton" in src
    assert "createHelpHubButton:" in src


def test_onboarding_exports_guide_steps_and_hub_topics():
    src = _read("client/static/js/ui/onboarding.js")
    assert "GUIDE_STEPS" in src
    assert "HUB_TOPICS" in src
    assert "GUIDE_STEPS:         GUIDE_STEPS" in src
    assert "HUB_TOPICS:          HUB_TOPICS" in src


# ── onboarding.js: Guide definitions ─────────────────────────────────────

def test_onboarding_has_new_player_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "new_player:" in src
    assert "New Player: Getting Started" in src


def test_onboarding_has_returning_player_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "returning_player:" in src
    assert "Quick Refresh" in src


def test_onboarding_has_combat_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "combat_guide:" in src
    assert "Combat Quick Guide" in src


def test_onboarding_has_movement_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "movement_guide:" in src
    assert "Movement in Combat" in src


def test_onboarding_has_spells_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "spells_guide:" in src
    assert "Casting Spells" in src


def test_onboarding_has_inventory_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "inventory_guide:" in src
    assert "Your Inventory" in src


def test_onboarding_has_dm_controls_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "dm_controls_guide:" in src
    assert "DM Controls Overview" in src


def test_onboarding_has_viewer_powers_guide():
    src = _read("client/static/js/ui/onboarding.js")
    assert "viewer_powers_guide:" in src
    assert "Viewer Powers" in src


# ── onboarding.js: Hub topic lists per role ───────────────────────────────

def test_hub_topics_has_player_section():
    src = _read("client/static/js/ui/onboarding.js")
    assert "player: [" in src
    # Player hub should include combat and new_player
    player_section_start = src.index("var HUB_TOPICS")
    player_section = src[player_section_start:player_section_start + 1500]
    assert "new_player" in player_section
    assert "combat_guide" in player_section
    assert "movement_guide" in player_section
    assert "inventory_guide" in player_section
    assert "spells_guide" in player_section


def test_hub_topics_has_dm_section():
    src = _read("client/static/js/ui/onboarding.js")
    hub_section = src[src.index("var HUB_TOPICS"):src.index("var HUB_TOPICS") + 1500]
    assert "dm:" in hub_section
    assert "dm_controls_guide" in hub_section


def test_hub_topics_has_viewer_section():
    src = _read("client/static/js/ui/onboarding.js")
    hub_section = src[src.index("var HUB_TOPICS"):src.index("var HUB_TOPICS") + 1500]
    assert "viewer:" in hub_section
    assert "viewer_powers_guide" in hub_section


# ── onboarding.js: Hub rendering ─────────────────────────────────────────

def test_onboarding_renders_hub_grid():
    src = _read("client/static/js/ui/onboarding.js")
    assert "ob-hub-grid" in src
    assert "ob-hub-card" in src
    assert "Help Hub" in src


def test_onboarding_hub_links_guides():
    src = _read("client/static/js/ui/onboarding.js")
    assert "_showGuide" in src
    assert "GUIDE_STEPS[" in src


# ── player_shell.js: Dashboard buttons ────────────────────────────────────

def test_player_dashboard_has_help_hub_button():
    src = _read("client/static/js/ui/player_shell.js")
    assert 'data-player-dashboard-action="help"' in src
    assert "Help Hub" in src


def test_player_dashboard_has_combat_guide_button():
    src = _read("client/static/js/ui/player_shell.js")
    assert 'data-player-dashboard-action="combat-guide"' in src
    assert "Combat Guide" in src


def test_player_dashboard_combat_guide_calls_help_hub():
    src = _read("client/static/js/ui/player_shell.js")
    assert "AppOnboarding.showHelpHub" in src


# ── play.html: topbar help button ─────────────────────────────────────────

def test_topbar_help_button_calls_help_hub():
    src = _read("client/templates/play.html")
    assert "AppOnboarding.showHelpHub" in src
    assert "topbar-help-btn" in src
    # Should NOT use showWalkthrough for the topbar button anymore
    topbar_section = src[src.index("topbar-help-btn"):src.index("topbar-help-btn") + 300]
    assert "showHelpHub" in topbar_section
    assert "showWalkthrough" not in topbar_section


# ── play.html: character sheet Actions tab renamed ────────────────────────

def test_character_sheet_actions_tab_renamed_to_combat_actions():
    src = _read("client/templates/play.html")
    assert "Combat / Actions" in src
    # Old label should not appear as a standalone tab label
    # (The word "Actions" still appears in text elsewhere, but the tab button should say "Combat / Actions")
    assert 'id="cb-combat-tab"' in src


# ── play.html: combat tab help button ────────────────────────────────────

def test_combat_controls_header_has_help_button():
    src = _read("client/templates/play.html")
    # The combat-controls header should contain a help button
    controls_idx = src.index('id="combat-controls"')
    controls_section = src[controls_idx:controls_idx + 900]
    assert "showHelpHub" in controls_section
    assert "ob-help-btn" in controls_section


# ── play.html: combat hint bar HTML element ───────────────────────────────

def test_play_html_has_combat_hint_bar():
    src = _read("client/templates/play.html")
    assert 'id="combat-hint-bar"' in src
    assert "combat-hint-visible" in src
    assert "rtab-pane-combat" in src


# ── play.html: combat coach HTML element ─────────────────────────────────

def test_play_html_has_combat_coach():
    src = _read("client/templates/play.html")
    assert 'id="combat-coach"' in src
    assert "combat-coach" in src
    assert "Turn Checklist" in src or "coach-title" in src
