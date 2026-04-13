from pathlib import Path


def _read_play() -> str:
    return Path("client/templates/play.html").read_text(encoding="utf-8")


def test_guild_board_dm_library_controls_present():
    src = _read_play()
    assert "quest_template_library_list" in src
    assert "quest_template_import" in src
    assert "Premade Quest Library" in src
    assert "guildBoardImportTemplate" in src


def test_play_page_handles_quest_template_sync_messages():
    src = _read_play()
    assert "case 'quest_template_library_sync':" in src
    assert "case 'session_quests_sync':" in src
    assert "case 'quest_template_import_result':" in src
