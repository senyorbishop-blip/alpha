import asyncio

from server.handlers import content
from server.session import Session, User


def _quest(quest_id: str, mode: str, **overrides):
    base = {
        "id": quest_id,
        "title": f"Quest {quest_id}",
        "status": "active",
        "objective_list": [
            {"id": "obj-public", "title": "Talk to the guildmaster", "status": "active"},
            {"id": "obj-hidden", "title": "Secret objective", "status": "active"},
        ],
        "progress": {"objective_status": {"obj-public": "active", "obj-hidden": "active"}},
        "visibility": {"mode": mode, "roles": [], "player_ids": [], "hidden_objective_ids": []},
    }
    base.update(overrides)
    return base


def test_player_only_gets_visible_session_quests():
    session = Session(id="s-quest")
    session.session_quests = [
        _quest("q-dm", "dm_only"),
        _quest("q-party", "party_public"),
        _quest("q-private", "private_player", visibility={"mode": "private_player", "player_ids": ["p1"], "roles": [], "hidden_objective_ids": []}),
    ]

    state = session.to_state_dict_for_role("player", "p1")
    ids = {entry["id"] for entry in state["session_quests"]}
    assert "q-party" in ids
    assert "q-private" in ids
    assert "q-dm" not in ids


def test_hidden_objective_ids_are_removed_for_players():
    session = Session(id="s-quest-hidden")
    session.session_quests = [
        _quest(
            "q-visibility",
            "party_public",
            visibility={
                "mode": "party_public",
                "roles": [],
                "player_ids": [],
                "hidden_objective_ids": ["obj-hidden"],
            },
        )
    ]

    state = session.to_state_dict_for_role("player", "p1")
    assert len(state["session_quests"]) == 1
    objectives = state["session_quests"][0]["objective_list"]
    assert [obj["id"] for obj in objectives] == ["obj-public"]
    assert state["session_quests"][0]["progress"]["objective_status"] == {"obj-public": "active"}


def test_hidden_locked_quests_are_not_visible_to_players():
    session = Session(id="s-quest-hidden-locked")
    session.session_quests = [
        _quest("q-hidden", "hidden_locked", status="available", description="Secret", linked_handout_ids=["h-secret"])
    ]
    state = session.to_state_dict_for_role("player", "p1")
    assert state["session_quests"] == []


def test_accepting_from_board_updates_quest_state_and_emits_summary():
    session = Session(id="s-quest-accept")
    session.users["dm1"] = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.users[player.id] = player
    session.session_quests = [{
        "id": "q-board",
        "title": "Board Contract",
        "status": "available",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "linked_handout_ids": ["h-board-1", "h-board-2"],
    }]

    sent = []

    async def _fake_send_to(_session_id, _user_id, message):
        sent.append(message)

    async def _fake_broadcast(_session_id, message):
        sent.append(message)

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_broadcast = content.manager.broadcast
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.manager.broadcast = _fake_broadcast
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_accept({"quest_id": "q-board"}, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.manager.broadcast = original_broadcast
        content.save_campaign_async = original_save

    accepted = next(q for q in session.session_quests if q["id"] == "q-board")
    assert accepted["status"] == "accepted"
    accept_result = next(msg for msg in sent if msg.get("type") == "session_quest_accept_result")
    assert accept_result["payload"]["quest"]["status"] == "accepted"
    notice = next(msg for msg in sent if msg.get("type") == "session_event_notice")
    assert notice["payload"]["scope"] == "quest_accept"
    assert notice["payload"]["linked_handout_ids"] == ["h-board-1", "h-board-2"]
