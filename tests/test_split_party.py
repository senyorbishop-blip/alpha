import asyncio

from server.session import Session, User, Token
from server.handlers import content


def _add_token(session: Session, token_id: str, map_context: str, *, hidden: bool = False):
    session.tokens[token_id] = Token(
        id=token_id,
        name=token_id,
        x=0,
        y=0,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=None,
        map_context=map_context,
        hidden=hidden,
    )


def test_split_party_assignment_and_context_filter_tokens():
    session = Session(id="SPLIT1")
    dm = User(id="dm1", name="DM", role="dm")
    p1 = User(id="p1", name="A", role="player")
    p2 = User(id="p2", name="B", role="player")
    session.users = {dm.id: dm, p1.id: p1, p2.id: p2}

    _add_token(session, "tok-world", "world")
    _add_token(session, "tok-a", "poi-a")
    _add_token(session, "tok-b", "poi-b")

    session.set_user_subgroup_id("p1", "alpha", actor_id="dm1")
    session.set_user_subgroup_id("p2", "beta", actor_id="dm1")
    session.set_subgroup_map_context("alpha", "poi-a", actor_id="dm1")
    session.set_subgroup_map_context("beta", "poi-b", actor_id="dm1")

    p1_state = session.to_state_dict_for_role("player", "p1")
    p2_state = session.to_state_dict_for_role("player", "p2")

    assert set(p1_state["tokens"].keys()) == {"tok-world", "tok-a"}
    assert set(p2_state["tokens"].keys()) == {"tok-world", "tok-b"}
    assert p1_state["user_subgroup_id"] == "alpha"
    assert p1_state["subgroup_map_context"] == "poi-a"


def test_single_party_default_still_sees_world_context():
    session = Session(id="SPLIT2")
    player = User(id="p1", name="Player", role="player")
    session.users[player.id] = player
    _add_token(session, "tok-world", "world")

    state = session.to_state_dict_for_role("player", "p1")

    assert "tok-world" in state["tokens"]
    assert state["user_subgroup_id"] == "main"
    assert state["subgroup_map_context"] == "world"


def test_single_party_players_follow_dm_map_context_for_visibility_filters():
    session = Session(id="SPLIT2B")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.dm_map_context = "poi-ship"
    _add_token(session, "tok-world", "world")
    _add_token(session, "tok-ship", "poi-ship")

    state = session.to_state_dict_for_role("player", "p1")

    assert set(state["tokens"].keys()) == {"tok-world", "tok-ship"}


def test_split_party_keeps_player_visibility_bound_to_assigned_subgroup():
    session = Session(id="SPLIT2C")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.dm_map_context = "poi-ship"
    session.set_user_subgroup_id("p1", "alpha", actor_id="dm1")
    session.set_subgroup_map_context("alpha", "poi-cave", actor_id="dm1")
    _add_token(session, "tok-world", "world")
    _add_token(session, "tok-cave", "poi-cave")
    _add_token(session, "tok-ship", "poi-ship")

    state = session.to_state_dict_for_role("player", "p1")

    assert set(state["tokens"].keys()) == {"tok-world", "tok-cave"}


def test_split_party_assign_handler_updates_users_and_emits_sync(monkeypatch):
    session = Session(id="SPLIT3")
    dm = User(id="dm1", name="DM", role="dm")
    p1 = User(id="p1", name="A", role="player")
    session.users = {dm.id: dm, p1.id: p1}

    sent = []

    async def _send_to(_sid, uid, message):
        sent.append((uid, message.get("type")))

    async def _save(_session):
        return None

    from types import SimpleNamespace
    monkeypatch.setattr(content, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(content, "save_campaign_async", _save)

    asyncio.run(content.handle_split_party_assign({"subgroup_id": "scouts", "user_ids": ["p1"]}, session, dm))

    assert session.get_user_subgroup_id("p1") == "scouts"
    assert any(msg_type == "split_party_sync" for _uid, msg_type in sent)
    assert any(uid == "p1" and msg_type == "state_sync" for uid, msg_type in sent)


def test_handout_subgroup_recipients_only_target_members(monkeypatch):
    session = Session(id="SPLIT4")
    dm = User(id="dm1", name="DM", role="dm")
    p1 = User(id="p1", name="A", role="player")
    p2 = User(id="p2", name="B", role="player")
    session.users = {dm.id: dm, p1.id: p1, p2.id: p2}
    session.set_user_subgroup_id("p1", "alpha", actor_id="dm1")
    session.set_user_subgroup_id("p2", "beta", actor_id="dm1")

    sent = []

    async def _send_to(_sid, uid, message):
        sent.append((uid, message.get("type"), dict(message.get("payload") or {})))

    async def _save(_session):
        return None

    from types import SimpleNamespace
    monkeypatch.setattr(content, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(content, "save_campaign_async", _save)

    asyncio.run(content.handle_send_handout({
        "title": "Scout Brief",
        "public_text": "Only alpha",
        "recipients": ["subgroup:alpha"],
    }, session, dm))

    received_users = [uid for uid, msg_type, _payload in sent if msg_type == "handout_received"]
    assert "p1" in received_users
    assert "p2" not in received_users
