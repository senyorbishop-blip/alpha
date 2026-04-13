from pathlib import Path


def _read_play() -> str:
    return Path("client/templates/play.html").read_text(encoding="utf-8")


def test_guild_board_dm_prep_pack_controls_present():
    src = _read_play()
    assert "prep_pack_library_list" in src
    assert "prep_pack_import" in src
    assert "Prep Packs" in src
    assert "guildBoardImportPrepPack" in src


def test_play_page_handles_prep_pack_sync_messages():
    src = _read_play()
    assert "case 'prep_pack_library_sync':" in src
    assert "case 'prep_pack_import_result':" in src
