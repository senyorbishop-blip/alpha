from pathlib import Path


def _play_html() -> str:
    return Path("client/templates/play.html").read_text(encoding="utf-8")


def _dnd_assets() -> str:
    return Path("client/static/js/assets/dnd_assets.js").read_text(encoding="utf-8")


def test_guild_board_asset_is_available_in_prop_manifest():
    src = _dnd_assets()
    assert "id: 'guild_board'" in src
    assert "label: 'Guild Board'" in src
    assert "tags: ['quest','board']" in src


def test_guild_board_prop_interaction_uses_existing_prop_popup_loop():
    src = _play_html()
    assert "function isGuildBoardProp(item)" in src
    assert "actions.push({ id: 'open_quest_board'" in src
    assert "function openGuildBoardFromProp(item)" in src
    assert "id=\"guild-board-modal\"" in src
    assert "guildBoardTrackQuest" in src


def test_guild_board_cards_show_progression_states_and_metadata():
    src = _play_html()
    assert "function _guildBoardQuestState(quest)" in src
    assert "return 'available';" in src
    assert "return 'accepted / in progress';" in src
    assert "return 'completed';" in src
    assert "return 'locked';" in src
    assert "return 'hidden until unlocked';" in src
    assert "Req faction:" in src
    assert "Req rank:" in src
    assert "Linked handouts:" in src


def test_single_prop_overrides_are_versioned_and_cover_aliases():
    src = _dnd_assets()
    assert "const PROP_IMAGE_VERSION = '20260401'" in src
    assert "guildboard: '/vtt_single_props/guild_board.png'" in src
    assert "quest_board: '/vtt_single_props/guild_board.png'" in src
    assert "shop_front: '/vtt_single_props/shop_stall.png'" in src
    assert "_versionedPropPath" in src
