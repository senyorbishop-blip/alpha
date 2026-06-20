import pytest

from server.handlers import combat as combat_handlers
from server.handlers import tokens as token_handlers
from server.session import Session, Token, User, normalize_profile_owner_key


def _build_player_session(owner_id: str):
    session = Session(id="s-owner")
    player = User(id="user-123", name="Test Player", role="player")
    session.users[player.id] = player
    token = Token(
        id="tok1",
        name="Hero",
        x=100,
        y=100,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=owner_id,
        speed=30,
    )
    session.tokens[token.id] = token
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{"token_id": token.id, "owner_id": owner_id, "speed": 30}],
    }
    return session, player, token


def test_combat_allows_turn_actions_for_legacy_owner_key():
    owner_key = normalize_profile_owner_key("Test Player")
    session, player, _ = _build_player_session(owner_key)

    allowed, message = combat_handlers._can_act_current_turn(session, player)
    assert allowed is True
    assert message is None


@pytest.mark.anyio
async def test_token_move_allows_legacy_owner_key(monkeypatch):
    owner_key = normalize_profile_owner_key("Test Player")
    session, player, token = _build_player_session(owner_key)

    sent = []

    async def _noop(*args, **kwargs):
        return None

    async def _capture(*args, **kwargs):
        sent.append((args, kwargs))

    monkeypatch.setattr(token_handlers.manager, "send_to", _capture)
    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_token_visibility", _noop)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_combat_move_state", _noop)

    await token_handlers.handle_token_move({"token_id": token.id, "x": 120, "y": 130}, session, player)

    assert token.x == 120
    assert token.y == 130
    assert sent == []


@pytest.mark.anyio
async def test_token_edit_allows_legacy_owner_key(monkeypatch):
    owner_key = normalize_profile_owner_key("Test Player")
    session, player, token = _build_player_session(owner_key)

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers, "_broadcast_token_visibility", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_token_state_sync", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_combat", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)

    await token_handlers.handle_token_edit(
        {"token_id": token.id, "notes": "Updated by legacy owner key"},
        session,
        player,
    )

    assert token.notes == "Updated by legacy owner key"


@pytest.mark.anyio
async def test_token_hp_update_allows_legacy_owner_key(monkeypatch):
    owner_key = normalize_profile_owner_key("Test Player")
    session, player, token = _build_player_session(owner_key)
    token.hp = 12
    token.max_hp = 18

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_combat", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)

    await token_handlers.handle_token_hp_update(
        {"token_id": token.id, "hp": 9, "max_hp": 21},
        session,
        player,
    )

    assert token.hp == 9
    assert token.max_hp == 21


def test_state_snapshot_relinks_legacy_owner_key_without_dropping_owner():
    session = Session(id="s-owner-relink")
    player = User(id="p1", name="Legacy Hero", role="player")
    session.users[player.id] = player
    token = Token(
        id="tok-relink",
        name="Legacy Token",
        x=0,
        y=0,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=normalize_profile_owner_key(player.name),
    )
    session.tokens[token.id] = token

    state = session.to_state_dict_for_role("player", player.id)
    snap_owner = state["tokens"][token.id]["owner_id"]

    assert snap_owner == player.id
    assert session.tokens[token.id].owner_id == player.id


def test_state_snapshot_keeps_unresolved_owner_for_future_reconnect():
    session = Session(id="s-owner-unresolved")
    player = User(id="p1", name="Current Player", role="player")
    session.users[player.id] = player
    token = Token(
        id="tok-legacy",
        name="Legacy Token",
        x=0,
        y=0,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id="old_player_identity_key",
    )
    session.tokens[token.id] = token

    state = session.to_state_dict_for_role("player", player.id)
    snap_owner = state["tokens"][token.id]["owner_id"]

    assert snap_owner == "old_player_identity_key"
    assert session.tokens[token.id].owner_id == "old_player_identity_key"
