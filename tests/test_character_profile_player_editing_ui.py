from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_character_panel_exposes_save_as_new_profile_action_for_players():
    src = _read("client/templates/play.html")
    assert "saveCurrentCharProfileAsNew()" in src
    assert "Save as New Character" in src


def test_player_character_updates_send_token_name_edits():
    src = _read("client/templates/play.html")
    assert "token_id: updateTokId," in src
    assert "token_id: myTok.id," in src
    assert "name: (selectedClass && selectedClass.icon ? selectedClass.icon + ' ' : 'P ') + name," in src


def test_character_profile_loading_uses_safe_draft_override_and_token_sync_hooks():
    src = _read("client/templates/play.html")
    assert "function _shouldUseLocalDraftForProfile(serverProfile, draftProfile)" in src
    assert "if (_shouldUseLocalDraftForProfile(profile, draft))" in src
    assert "function _syncLoadedProfileToOwnedToken(profile)" in src
    assert "_pendingLoadedCharacterTokenSeed" in src
