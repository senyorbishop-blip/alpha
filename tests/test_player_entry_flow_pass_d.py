from pathlib import Path


def test_player_character_roster_create_button_owned_by_join_gateway_only():
    src = Path("client/templates/player-characters.html").read_text(encoding="utf-8")
    assert "createNativeBtn: els.createBtn," in src
    assert "els.createBtn.addEventListener('click'" not in src


def test_join_gateway_hides_session_duplicate_for_library_profile():
    src = Path("client/static/js/character/gateway/join_gateway.js").read_text(encoding="utf-8")
    assert "const libraryProfileIds = new Set" in src
    assert "if (libraryId && libraryProfileIds.has(libraryId)) return false;" in src
    assert "if (key && libraryNameKeys.has(key)) return false;" in src


def test_player_roster_preserves_session_token_library_identity():
    src = Path("client/templates/player-characters.html").read_text(encoding="utf-8")
    assert "libraryId: String(t.libraryId || t.library_id || t.profile_id || '').trim()" in src
    assert "characterId: String(t.characterId || t.character_id || '').trim()" in src
