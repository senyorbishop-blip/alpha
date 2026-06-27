from server.handlers.tokens import _persist_token_hp_to_owned_profiles
from server.session import Session, Token, User


def test_token_hp_persists_to_active_owned_native_profile():
    session = Session(id="sess")
    player = User(id="p1", name="Bishop", role="player")
    session.users[player.id] = player
    session.active_char_profiles[player.id] = "profile-1"
    session.char_profiles = {
        player.id: [
            {
                "id": "profile-1",
                "name": "Bishop",
                "nativeRuntime": {"hp": {"current": 74, "max": 74}, "combat": {"currentHP": 74, "maxHP": 74}},
                "charBook": {"currentHp": 74, "maxHp": 74},
                "charSheet": {"hp": {"current": 74, "max": 74}},
                "curhp": 74,
                "hp": 74,
            }
        ]
    }
    token = Token(id="tok", name="Bishop", x=0, y=0, width=50, height=50, color="#fff", shape="circle", owner_id=player.id, hp=103, max_hp=103, temp_hp=5)

    assert _persist_token_hp_to_owned_profiles(session, token) is True
    profile = session.char_profiles[player.id][0]
    assert profile["curhp"] == 103
    assert profile["hp"] == 103
    assert profile["tempHp"] == 5
    assert profile["nativeRuntime"]["hp"] == {"current": 103, "max": 103, "temp": 5}
    assert profile["nativeRuntime"]["combat"]["currentHP"] == 103
    assert profile["nativeRuntime"]["combat"]["maxHP"] == 103
    assert profile["charBook"]["currentHp"] == 103
    assert profile["charSheet"]["hp"]["current"] == 103
