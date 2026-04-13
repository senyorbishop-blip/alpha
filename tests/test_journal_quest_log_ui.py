from pathlib import Path


def _play_html() -> str:
    return Path("client/templates/play.html").read_text(encoding="utf-8")


def test_journal_includes_integrated_quest_log_container():
    src = _play_html()
    assert 'id="journal-quest-log"' in src
    assert 'id="journal-campaign-hub"' in src
    assert "data-cat=\"campaign_hub\"" in src
    assert "function renderCampaignHub(search)" in src
    assert "function renderJournalQuestLog(search)" in src
    assert "const shouldShowQuestLog = !_journalFormOpen && !_journalViewId && _journalCatFilter === 'quest';" in src
    assert "const shouldShowCampaignHub = !_journalFormOpen && !_journalViewId && _journalCatFilter === 'campaign_hub';" in src


def test_quest_log_renders_required_sections_and_fields():
    src = _play_html()
    assert "Failed / Expired" in src
    assert "Hidden / Locked" in src
    assert "Personal" in src
    assert "Party" in src
    assert "Rewards:" in src
    assert "Handouts:" in src
    assert "Map refs:" in src
    assert "function questTurnInAction(questId, applyRewards = false)" in src
    assert "session_quest_turn_in" in src
    assert "openQuestLinkedHandout" in src
    assert "openQuestLinkedJournal" in src
    assert "journal-link-chip-btn" in src


def test_narrative_discoverability_cues_exist_for_quests_handouts_and_hub():
    src = _play_html()
    assert "id=\"journal-cat-cue-quest\"" in src
    assert "id=\"journal-cat-cue-hub\"" in src
    assert "function _renderNarrativeCueBadges()" in src
    assert "function openJournalQuestFocus()" in src
    assert "function openPlayerHandoutsTab()" in src
    assert "function openCampaignHubFocus()" in src
    assert "Narrative Radar" in src


def test_campaign_hub_uses_existing_role_safe_data_paths():
    src = _play_html()
    assert "const quests = (_sessionQuests || []).filter((quest) => _journalQuestCanView(quest));" in src
    assert "if (ROLE === 'dm') return allPois;" in src
    assert "return allPois.filter((poi) => poi.revealed_to_players !== false);" in src
    assert "Recent World Changes" in src


def test_player_companion_quest_tracker_uses_large_action_buttons():
    src = _play_html()
    assert "player-companion-grid" in src
    assert "Quest Tracker" in src
    assert "Mark Complete" in src
    assert "Mark Active" in src
    assert "player-companion-quest-btn" in src
    assert "Open Full Quest Log" in src
