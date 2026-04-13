import asyncio

from server.handlers import content
from server.session import Session, User, get_player_gold_for_user


def _dm_player_session():
    session = Session(id="quest-progress")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Alice", role="player")
    session.users = {dm.id: dm, player.id: player}
    return session, dm, player


def test_session_quest_upsert_normalizes_objectives_and_progress():
    session, dm, _ = _dm_player_session()

    sent = []

    async def _fake_send_to(_session_id, _user_id, message):
        sent.append(message)

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_upsert({
            "title": "Recover the Sigil",
            "status": "available",
            "objective_list": [
                {"id": "obj-visit", "title": "Visit the ruins", "type": "visit_poi", "target_id": "poi-ruins"},
                {"id": "obj-return", "title": "Return to guild board", "type": "return_to_board"},
            ],
        }, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    quest = session.session_quests[0]
    assert quest["objective_list"][0]["type"] == "visit_poi"
    assert quest["progress"]["total_objectives"] == 2
    assert quest["progress"]["objective_status"]["obj-visit"] == "pending"


def test_event_progress_advances_objectives_and_lifecycle():
    session, dm, player = _dm_player_session()
    session.session_quests = [{
        "id": "sq-1",
        "title": "Scout then Report",
        "status": "available",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "objective_list": [
            {"id": "obj-visit", "title": "Visit ruins", "type": "visit_poi", "target_id": "poi-ruins"},
            {"id": "obj-return", "title": "Return to board", "type": "return_to_board"},
        ],
    }]

    async def _fake_send_to(_session_id, _user_id, _message):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_objective_event({"quest_id": "sq-1", "event_type": "visit_poi", "target_id": "poi-ruins"}, session, player))
        assert session.session_quests[0]["status"] in {"active", "ready_to_turn_in"}
        asyncio.run(content.handle_session_quest_objective_event({"quest_id": "sq-1", "event_type": "return_to_board"}, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert session.session_quests[0]["status"] == "ready_to_turn_in"
    assert session.session_quests[0]["progress"]["completed_objectives"] == 2


def test_turn_in_player_submission_creates_pending_dm_approval_request():
    session, dm, player = _dm_player_session()
    session.session_quests = [{
        "id": "sq-turnin-1",
        "title": "Return with proof",
        "status": "ready_to_turn_in",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "reward_bundle": {"gold": 75, "distribution": "party"},
        "objective_list": [{"id": "obj-1", "title": "Done", "status": "completed", "type": "manual"}],
    }]

    async def _fake_send_to(_session_id, _user_id, _message):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_turn_in({"quest_id": "sq-turnin-1", "apply_rewards": False}, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    quest = session.session_quests[0]
    assert quest["status"] == "ready_to_turn_in"
    assert quest["reward_state"]["status"] == "awaiting_dm_approval"
    assert quest["reward_state"]["requested_outcome"] == "completed"
    assert quest["turn_in_request"]["status"] == "pending"
    assert quest["turn_in_request"]["outcome"] == "completed"


def test_turn_in_apply_rewards_grants_party_gold_and_personal_item():
    session, dm, player = _dm_player_session()
    player_b = User(id="p2", name="Bob", role="player")
    session.users[player_b.id] = player_b
    session.session_quests = [{
        "id": "sq-turnin-2",
        "title": "Guild Contract",
        "status": "ready_to_turn_in",
        "visibility": {"mode": "private_player", "roles": ["player"], "player_ids": ["p1"], "hidden_objective_ids": []},
        "reward_bundle": {
            "gold": 101,
            "distribution": "party",
            "items": [{"name": "Healing Potion", "qty": 2}],
        },
        "objective_list": [{"id": "obj-1", "title": "Done", "status": "completed", "type": "manual"}],
    }]

    async def _fake_send_to(_session_id, _user_id, _message):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    async def _fake_broadcast(_session_id, _message, exclude_user=None):
        return None

    original_send_to = content.manager.send_to
    original_broadcast = content.manager.broadcast
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.manager.broadcast = _fake_broadcast
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_turn_in({"quest_id": "sq-turnin-2", "apply_rewards": True}, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.manager.broadcast = original_broadcast
        content.save_campaign_async = original_save

    quest = session.session_quests[0]
    assert quest["status"] == "rewards_granted"
    assert quest["reward_state"]["status"] == "granted"
    # 101 gp split across 2 players = 50 gp 5 sp each.
    assert get_player_gold_for_user(session, "p1") == 5050
    assert get_player_gold_for_user(session, "p2") == 5050
    stash = (session.player_inventories or {}).get("__party_stash__", [])
    assert stash
    assert stash[0]["name"] == "Healing Potion"
    rep_state = ((session.world_state or {}).get("faction_reputation") or {})
    assert rep_state == {}


def test_turn_in_apply_rewards_applies_faction_reputation_to_world_state():
    session, dm, _ = _dm_player_session()
    session.session_quests = [{
        "id": "sq-turnin-rep-1",
        "title": "Lantern Accord",
        "status": "ready_to_turn_in",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "reward_bundle": {
            "reputation": [
                {"id": "iron-lantern", "name": "Iron Lantern", "tag": "guild", "delta": 3},
                {"id": "ashen-claw", "name": "Ashen Claw", "tag": "tribe", "delta": -2},
            ],
        },
        "objective_list": [{"id": "obj-1", "title": "Done", "status": "completed", "type": "manual"}],
    }]

    async def _fake_send_to(_session_id, _user_id, _message):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    async def _fake_broadcast(_session_id, _message, exclude_user=None):
        return None

    original_send_to = content.manager.send_to
    original_broadcast = content.manager.broadcast
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.manager.broadcast = _fake_broadcast
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_turn_in({"quest_id": "sq-turnin-rep-1", "apply_rewards": True}, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.manager.broadcast = original_broadcast
        content.save_campaign_async = original_save

    rep_state = ((session.world_state or {}).get("faction_reputation") or {})
    assert rep_state["iron-lantern"]["reputation"] == 3
    assert rep_state["iron-lantern"]["tier_label"] == "Neutral"
    assert rep_state["ashen-claw"]["reputation"] == -2


def test_dm_override_can_advance_and_fail_quest():
    session, dm, _ = _dm_player_session()
    session.session_quests = [{
        "id": "sq-2",
        "title": "Manual Override Quest",
        "status": "active",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "objective_list": [
            {"id": "obj-1", "title": "Talk to NPC", "type": "talk_npc"},
        ],
    }]

    async def _fake_send_to(_session_id, _user_id, _message):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_progress_override({
            "quest_id": "sq-2",
            "action": "advance_objective",
            "objective_id": "obj-1",
        }, session, dm))
        assert session.session_quests[0]["status"] == "ready_to_turn_in"
        asyncio.run(content.handle_session_quest_progress_override({
            "quest_id": "sq-2",
            "action": "fail_quest",
        }, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert session.session_quests[0]["status"] == "failed"


def test_session_quest_sync_includes_premium_progression_snapshot():
    session, dm, _ = _dm_player_session()
    session.session_quests = [{
        "id": "sq-sync-1",
        "title": "Iron Contract",
        "status": "completed",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "reward_bundle": {"reputation": {"Iron Lantern": 4}},
        "objective_list": [{"id": "obj-1", "title": "Done", "status": "completed", "type": "manual"}],
    }]

    sent = []

    async def _fake_send_to(_session_id, _user_id, message):
        sent.append(message)

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_progress_override({
            "quest_id": "sq-sync-1",
            "action": "set_status",
            "status": "completed",
        }, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    sync_payloads = [msg.get("payload", {}) for msg in sent if msg.get("type") == "session_quests_sync"]
    assert sync_payloads
    progression = sync_payloads[-1].get("premium_progression") or {}
    assert progression.get("guild_rank", {}).get("completed_quests") == 1
    assert (progression.get("faction_reputation") or [{}])[0].get("faction") == "Iron Lantern"


def test_session_quest_sync_hides_dm_only_faction_rows_from_players():
    session, dm, player = _dm_player_session()
    session.world_state = {
        "faction_reputation": {
            "public-faction": {"id": "public-faction", "name": "Public Faction", "reputation": 6, "visibility": "party"},
            "dm-faction": {"id": "dm-faction", "name": "DM Secret", "reputation": 9, "visibility": "dm_only"},
        }
    }
    session.session_quests = [{
        "id": "sq-sync-hide-1",
        "title": "Visibility Pass",
        "status": "active",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "objective_list": [{"id": "obj-1", "title": "Done", "status": "pending", "type": "manual"}],
    }]

    sent = []

    async def _fake_send_to(_session_id, user_id, message):
        sent.append((user_id, message))

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_session_quest_progress_override({
            "quest_id": "sq-sync-hide-1",
            "action": "set_status",
            "status": "active",
        }, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    dm_payload = [m for uid, m in sent if uid == dm.id and m.get("type") == "session_quests_sync"][-1]["payload"]
    player_payload = [m for uid, m in sent if uid == player.id and m.get("type") == "session_quests_sync"][-1]["payload"]
    dm_factions = [row.get("id") for row in (dm_payload.get("premium_progression") or {}).get("faction_reputation") or []]
    player_factions = [row.get("id") for row in (player_payload.get("premium_progression") or {}).get("faction_reputation") or []]
    assert "dm-faction" in dm_factions
    assert "dm-faction" not in player_factions
