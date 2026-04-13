from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_player_dashboard_prioritizes_character_actions_and_core_play_controls():
    src = _read("client/static/js/ui/player_shell.js")
    assert "Start here" in src
    assert "Active quest focus" in src
    assert "No active quests yet." in src
    assert 'data-player-dashboard-action="token"' in src
    assert 'data-player-dashboard-action="spells"' in src
    assert 'data-player-dashboard-action="inventory"' in src
    assert 'data-player-dashboard-action="rolls"' in src
    assert 'data-player-dashboard-action="map"' in src
    assert "switchRightTab?.('spelllib')" in src
    assert "toggleFlyout?.('flyout-dice')" in src
    assert "switchRightTab?.('party')" in src
    assert "getSessionQuests" in src


def test_player_role_shell_uses_tab_registry_visibility_contract_for_library_tabs():
    tabs_src = _read("client/static/js/ui/tabs.js")
    play_src = _read("client/templates/play.html")

    # Behavior contract: players can access spell library but not DM-only shop/bestiary tabs.
    assert "id: 'shop'" in tabs_src
    assert "id: 'bestiary'" in tabs_src
    assert "id: 'spelllib'" in tabs_src
    assert "isVisible: (env) => canUseDmLibraryTabs(env)" in tabs_src
    assert "id: 'spelllib', label: 'Spells'" in tabs_src
    assert "isVisible: (env) => canUsePlayerTabs(env)" in tabs_src

    # User-visible mounts still exist and are wired through data attributes.
    assert 'id="rtab-dropdown-library"' in play_src
    assert 'id="rtab-shop"' in play_src
    assert 'id="rtab-bestiary"' in play_src
    assert 'id="rtab-spelllib"' in play_src
    assert 'data-rtab-target="shop"' in play_src
    assert 'data-rtab-target="bestiary"' in play_src
    assert 'data-rtab-target="spelllib"' in play_src


def test_play_template_exposes_player_dashboard_onboarding_styles_and_quest_empty_state():
    play_src = _read("client/templates/play.html")
    assert ".player-dashboard-start" in play_src
    assert ".player-dashboard-quest-spotlight" in play_src
    assert ".player-dashboard-moments" in play_src
    assert ".player-dashboard-moment[data-moment-type=\"discovery\"]" in play_src
    assert ".player-dashboard-moment[data-moment-type=\"handout\"]" in play_src
    assert "getSessionQuests: () => Array.isArray(_sessionQuests) ? _sessionQuests.slice() : []" in play_src
