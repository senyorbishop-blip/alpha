from pathlib import Path


def test_player_character_roster_create_button_owned_by_join_gateway_only():
    src = Path("client/templates/player-characters.html").read_text(encoding="utf-8")
    assert "createNativeBtn: els.createBtn," in src
    assert "els.createBtn.addEventListener('click'" not in src
