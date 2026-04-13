import asyncio

from server.living_world_events import consume_world_event, emit_world_event, normalize_world_event_envelope
from server.persistence_schema import extract_persistable_campaign_state, normalize_persisted_campaign_data
from server.session import Session, User


def test_recent_events_persist_in_world_state_roundtrip():
    session = Session(id="evt-persist", dm_id="dm-1")
    event = emit_world_event(session, "guild_rank_changed", {
        "source": "test",
        "actor_user_id": "dm-1",
        "guild_rank_id": "trusted",
        "summary": "Guild rank promoted to Trusted",
    })
    consume_world_event(session, event, {"summary_messages": ["Guild rank promoted."]})

    extracted = extract_persistable_campaign_state(session)
    normalized = normalize_persisted_campaign_data({"world_state": extracted.get("world_state")})

    recent = normalized["world_state"].get("recent_events") or []
    assert len(recent) == 1
    assert recent[0]["event_type"] == "guild_rank_changed"
    assert recent[0]["summary"] == "Guild rank promoted to Trusted"


def test_quest_completion_triggers_handout_unlock_and_faction_reaction_summary(monkeypatch):
    from server.handlers.content import handle_session_quest_turn_in

    session = Session(id="evt-quest", dm_id="dm-1")
    dm = User(id="dm-1", name="Dungeon Master", role="dm")
    player = User(id="p-1", name="Ari", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.handouts = [{"id": "h-001", "title": "Letter", "public_text": "Read me", "recipients": "all"}]
    session.session_quests = [{
        "id": "q-001",
        "title": "Bandit Trouble",
        "status": "ready_to_turn_in",
        "visibility": {"mode": "party_public", "roles": ["player"], "player_ids": [], "hidden_objective_ids": []},
        "reward_bundle": {
            "gold": 0,
            "handout_unlock_ids": ["h-001"],
            "reputation": [{"id": "guild", "name": "Guild", "delta": 2}],
        },
    }]

    async def _noop(*_args, **_kwargs):
        return True

    monkeypatch.setattr("server.handlers.content.save_campaign_async", _noop)
    monkeypatch.setattr("server.handlers.content.manager.send_to", _noop)
    monkeypatch.setattr("server.handlers.content.manager.broadcast", _noop)
    monkeypatch.setattr("server.handlers.content._broadcast_session_quests", _noop)
    monkeypatch.setattr("server.handlers.content._broadcast_poll_state", _noop)

    asyncio.run(handle_session_quest_turn_in({"quest_id": "q-001", "apply_rewards": True}, session, dm))

    world_state = dict(session.world_state or {})
    assert "h-001" in (world_state.get("unlocked_handout_ids") or [])
    assert world_state.get("faction_reputation", {}).get("guild", {}).get("reputation") == 2
    assert any(event.get("event_type") == "quest_completed" for event in (world_state.get("recent_events") or []))
    assert any("Faction reputation changed" in msg for msg in (world_state.get("event_messages") or []))


def test_discovery_event_appends_visible_recent_entry(monkeypatch):
    from server.handlers.content import handle_discovery_trigger

    session = Session(id="evt-discovery", dm_id="dm-1")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="p-1", name="Ari", role="player")
    session.users = {dm.id: dm, player.id: player}

    async def _noop(*_args, **_kwargs):
        return True

    monkeypatch.setattr("server.handlers.content.save_campaign_async", _noop)
    monkeypatch.setattr("server.handlers.content.manager.send_to", _noop)

    payload = {"id": "disc-1", "title": "Ancient Sigil", "body": "You find a hidden rune.", "visibility": "party_public"}
    asyncio.run(handle_discovery_trigger(payload, session, dm))

    recent = session.world_state.get("recent_events") or []
    assert any(row.get("event_type") == "discovery_unlocked" for row in recent)
    assert any("Ancient Sigil" in str(row.get("summary") or "") for row in recent)


def test_guild_and_faction_events_produce_normalized_summary():
    session = Session(id="evt-summary")
    event = normalize_world_event_envelope("faction_reputation_changed", {
        "summary": "Faction standings updated",
        "source": "test",
    })
    reaction = consume_world_event(session, event, {
        "faction_reputation_changes": [{"id": "council", "name": "Council", "delta": 3}],
        "summary_messages": ["Council reputation increased."],
        "refresh_quest_ids": ["q-council"],
    })

    assert reaction["event_type"] == "faction_reputation_changed"
    assert "faction_reputation" in reaction["applied"]
    assert "summary_messages" in reaction["applied"]
    guild_event = emit_world_event(session, "guild_rank_changed", {"summary": "Guild rank advanced"})
    assert guild_event["event_type"] == "guild_rank_changed"
