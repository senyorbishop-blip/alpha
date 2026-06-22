import asyncio

from server.handlers import camp_rest
from server.handlers import common as common_handlers
from server.handlers import inventory as inventory_handlers
from server.session import Session, Token, User, normalize_profile_owner_key


class CaptureManager:
    def __init__(self):
        self.sent = []
        self.broadcasts = []

    async def send_to(self, session_id, user_id, message):
        self.sent.append((session_id, user_id, message))

    async def broadcast(self, session_id, message):
        self.broadcasts.append((session_id, message))


async def _noop_save(_session):
    return None


def _token(token_id, owner_id, hp=3, max_hp=10, temp_hp=4):
    return Token(
        id=token_id,
        name=f"Token {token_id}",
        x=0,
        y=0,
        width=50,
        height=50,
        color="#fff",
        shape="circle",
        owner_id=owner_id,
        hp=hp,
        max_hp=max_hp,
        temp_hp=temp_hp,
    )


def _session():
    session = Session(id="rest-session")
    dm = User(id="dm", name="DM", role="dm")
    player = User(id="p1", name="Alice", role="player")
    other = User(id="p2", name="Bob", role="player")
    viewer = User(id="v1", name="Viewer", role="viewer")
    session.users = {u.id: u for u in (dm, player, other, viewer)}
    session.tokens = {
        "alice-1": _token("alice-1", "p1", hp=2, max_hp=12, temp_hp=5),
        "alice-2": _token("alice-2", "p1", hp=1, max_hp=9, temp_hp=0),
        "bob-1": _token("bob-1", "p2", hp=4, max_hp=11, temp_hp=3),
    }
    return session, player, other, dm, viewer


def _patch(monkeypatch):
    capture = CaptureManager()
    monkeypatch.setattr(camp_rest, "manager", capture)
    monkeypatch.setattr(common_handlers, "manager", capture)
    monkeypatch.setattr(inventory_handlers, "manager", capture)
    monkeypatch.setattr(camp_rest, "save_campaign_async", _noop_save)
    return capture


def _messages(capture, msg_type):
    return [m for _, _, m in capture.sent if m.get("type") == msg_type] + [m for _, m in capture.broadcasts if m.get("type") == msg_type]


def test_player_long_rest_restores_owned_token_hp_to_max_and_clears_temp_hp(monkeypatch):
    capture = _patch(monkeypatch)
    session, player, *_ = _session()

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "long", "token_id": "alice-1"}, session, player))

    assert session.tokens["alice-1"].hp == 12
    assert session.tokens["alice-1"].temp_hp == 0
    assert _messages(capture, "character_rest_applied")


def test_player_long_rest_broadcasts_tokens_sync(monkeypatch):
    capture = _patch(monkeypatch)
    session, player, *_ = _session()

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "long", "token_id": "alice-1"}, session, player))

    token_syncs = _messages(capture, "tokens_sync")
    assert token_syncs
    assert any("alice-1" in (msg["payload"].get("tokens") or {}) for msg in token_syncs)


def test_player_long_rest_refreshes_item_charges_and_broadcasts_inventory_if_changed(monkeypatch):
    capture = _patch(monkeypatch)
    session, player, *_ = _session()
    owner_key = normalize_profile_owner_key(player.name) or player.id
    session.player_inventories = {
        owner_key: [{
            "name": "Wand of Sparks",
            "qty": 1,
            "charges_max": 7,
            "charges_current": 2,
            "recharge_type": "long_rest",
            "granted_spells": [{"id": "spark", "name": "Spark", "charge_cost": 1, "consume_spell_slot": False}],
        }]
    }

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "long", "token_id": "alice-1"}, session, player))

    assert session.player_inventories[owner_key][0]["charges_current"] == 7
    assert _messages(capture, "player_inventory_sync")


def test_player_short_rest_without_hit_dice_does_not_heal_hp(monkeypatch):
    _patch(monkeypatch)
    session, player, *_ = _session()

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "short", "token_id": "alice-1"}, session, player))

    assert session.tokens["alice-1"].hp == 2


def test_player_short_rest_with_valid_token_id_applies_healing_only_to_that_token(monkeypatch):
    capture = _patch(monkeypatch)
    session, player, *_ = _session()

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "short", "token_id": "alice-2", "healed_amount": 5}, session, player))

    assert session.tokens["alice-2"].hp == 6
    assert session.tokens["alice-1"].hp == 2
    applied = _messages(capture, "character_rest_applied")
    assert applied[-1]["payload"]["token_id"] == "alice-2"


def test_player_cannot_rest_another_players_token(monkeypatch):
    capture = _patch(monkeypatch)
    session, player, *_ = _session()

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "long", "token_id": "bob-1"}, session, player))

    assert session.tokens["bob-1"].hp == 4
    assert session.tokens["bob-1"].temp_hp == 3
    assert not _messages(capture, "character_rest_applied")
    assert _messages(capture, "notification")


def test_non_player_roles_cannot_call_character_rest(monkeypatch):
    capture = _patch(monkeypatch)
    session, _player, _other, dm, viewer = _session()

    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "long", "token_id": "alice-1"}, session, dm))
    asyncio.run(camp_rest.handle_character_self_rest({"rest_type": "long", "token_id": "alice-1"}, session, viewer))

    assert session.tokens["alice-1"].hp == 2
    assert not capture.sent
    assert not capture.broadcasts
