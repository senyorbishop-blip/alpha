import asyncio

from server.handlers import content
from server.session import Session, User


def test_session_quest_upsert_creates_binding_and_role_safe_visibility():
    session = Session(id="quest-publish")
    dm = User(id="dm1", name="DM", role="dm")
    player_a = User(id="p1", name="Alice", role="player")
    player_b = User(id="p2", name="Bob", role="player")
    viewer = User(id="v1", name="Vee", role="viewer")
    session.users = {dm.id: dm, player_a.id: player_a, player_b.id: player_b, viewer.id: viewer}

    sent = []

    async def _fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_upsert({
            "title": "Deliver Mage Supplies",
            "summary": "Escorted run from docks to arcane quarter.",
            "status": "available",
            "board_ids": ["board-harbor"],
            "linked_poi_ids": ["poi-harbor"],
            "linked_map_ids": ["world"],
            "linked_handout_ids": ["ho-1"],
            "linked_encounter_template_ids": ["enc-1"],
            "linked_npc_ids": ["npc-1"],
            "visibility": {
                "mode": "private_player",
                "roles": ["player", "viewer"],
                "player_ids": ["p1"],
            },
        }, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert len(session.session_quests) == 1
    quest = session.session_quests[0]
    assert quest["title"] == "Deliver Mage Supplies"
    assert quest["visibility"]["mode"] == "private_player"
    assert quest["visibility"]["player_ids"] == ["p1"]
    assert quest["linked_encounter_template_ids"] == ["enc-1"]
    assert session.quest_board_bindings == [{"board_id": "board-harbor", "quest_ids": [quest["id"]]}]

    player_msgs = [m for _, uid, m in sent if uid == "p1" and m.get("type") == "session_quests_sync"]
    assert player_msgs
    assert player_msgs[-1]["payload"]["session_quests"]

    other_player_msgs = [m for _, uid, m in sent if uid == "p2" and m.get("type") == "session_quests_sync"]
    assert other_player_msgs
    assert other_player_msgs[-1]["payload"]["session_quests"] == []

    viewer_msgs = [m for _, uid, m in sent if uid == "v1" and m.get("type") == "session_quests_sync"]
    assert viewer_msgs
    assert viewer_msgs[-1]["payload"]["session_quests"] == []


def test_session_quest_upsert_removes_board_binding_when_cleared():
    session = Session(id="quest-publish-update")
    dm = User(id="dm1", name="DM", role="dm")
    session.users = {dm.id: dm}
    existing = {
        "id": "sq-abc",
        "title": "Old Quest",
        "status": "available",
        "visibility": {"mode": "party_public", "roles": ["player", "viewer"], "player_ids": [], "hidden_objective_ids": []},
        "created_at": 1.0,
        "updated_at": 1.0,
    }
    session.session_quests = [existing]
    session.quest_board_bindings = [{"board_id": "board-1", "quest_ids": ["sq-abc"]}]

    async def _fake_send_to(_session_id, _user_id, _message):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_upsert({
            "id": "sq-abc",
            "title": "Old Quest",
            "status": "hidden",
            "board_ids": [],
        }, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert session.session_quests[0]["status"] == "hidden"
    assert session.quest_board_bindings == []
