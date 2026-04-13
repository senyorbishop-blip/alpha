import asyncio


def test_interactable_inspect_returns_private_result(monkeypatch):
    from server.handlers.map_editor import handle_interactable_action
    from server.session import Session, User

    session = Session(id="INT001", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    session.users = {dm.id: dm, player.id: player, viewer.id: viewer}
    session.editor_props = {
        "world": [{
            "id": "prop-1",
            "kind": "statue",
            "name": "Ancient Statue",
            "x": 0,
            "y": 0,
            "w": 1,
            "h": 1,
            "interactable": {
                "enabled": True,
                "kind": "world_object",
                "prompt": "The stone is warm to the touch.",
                "actions": [{"id": "inspect", "label": "Inspect"}],
            },
        }]
    }

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    async def fake_save(_session):
        return True

    monkeypatch.setattr("server.handlers.map_editor.manager.send_to", fake_send_to)
    monkeypatch.setattr("server.handlers.map_editor.save_campaign_async", fake_save)

    asyncio.run(handle_interactable_action({
        "target_kind": "prop",
        "target_id": "prop-1",
        "map_context": "world",
        "action": "inspect",
    }, session, player))

    assert len(sent) == 1
    assert sent[0][1] == player.id
    assert sent[0][2]["type"] == "interactable_action_result"
    assert sent[0][2]["payload"]["message"] == "The stone is warm to the touch."


def test_interactable_mark_for_party_broadcasts_to_dm_and_players_only(monkeypatch):
    from server.handlers.map_editor import handle_interactable_action
    from server.session import Session, User

    session = Session(id="INT002", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player_a = User(id="player-a", name="Alice", role="player")
    player_b = User(id="player-b", name="Borin", role="player")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    session.users = {dm.id: dm, player_a.id: player_a, player_b.id: player_b, viewer.id: viewer}
    session.editor_props = {
        "world": [{
            "id": "prop-2",
            "kind": "bloodstain",
            "name": "Blood Trail",
            "x": 0,
            "y": 0,
            "w": 1,
            "h": 1,
            "interactable": {
                "enabled": True,
                "actions": [{"id": "mark_for_party", "label": "Mark for Party"}],
            },
        }]
    }

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    async def fake_save(_session):
        return True

    monkeypatch.setattr("server.handlers.map_editor.manager.send_to", fake_send_to)
    monkeypatch.setattr("server.handlers.map_editor.save_campaign_async", fake_save)

    asyncio.run(handle_interactable_action({
        "target_kind": "prop",
        "target_id": "prop-2",
        "map_context": "world",
        "action": "mark_for_party",
        "note": "Fresh tracks here.",
    }, session, player_a))

    event_targets = sorted(user_id for _, user_id, message in sent if message.get("type") == "interactable_action_event")
    result_targets = sorted(user_id for _, user_id, message in sent if message.get("type") == "interactable_action_result")

    assert event_targets == sorted([dm.id, player_a.id, player_b.id])
    assert result_targets == [player_a.id]
    assert viewer.id not in event_targets


def test_interactable_requires_token_presence_for_players(monkeypatch):
    from server.handlers.map_editor import handle_interactable_action
    from server.session import Session, User

    session = Session(id="INT003", dm_id="dm-user")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {player.id: player}
    session.editor_props = {
        "crypt": [{
            "id": "prop-3",
            "kind": "rubble",
            "name": "Suspicious Rubble",
            "x": 0,
            "y": 0,
            "w": 1,
            "h": 1,
            "interactable": {
                "enabled": True,
                "actions": [{"id": "interact", "label": "Interact"}],
                "permissions": {"requires_token": True},
            },
        }]
    }

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    monkeypatch.setattr("server.handlers.map_editor.manager.send_to", fake_send_to)

    asyncio.run(handle_interactable_action({
        "target_kind": "prop",
        "target_id": "prop-3",
        "map_context": "crypt",
        "action": "interact",
    }, session, player))

    assert sent[-1][2]["type"] == "error"
    assert "Move one of your tokens" in sent[-1][2]["payload"]["message"]


def test_interactable_skill_attempt_notifies_dm(monkeypatch):
    from server.handlers.map_editor import handle_interactable_action
    from server.session import POI, Session, Token, User

    session = Session(id="INT004", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.tokens = {
        "tok-1": Token(
            id="tok-1", name="Alice", x=0, y=0, width=50, height=50, color="#fff", shape="circle",
            owner_id=player.id, map_context="world"
        )
    }
    session.pois = {
        "poi-1": POI(
            id="poi-1",
            x=5,
            y=5,
            name="Shrine",
            interactable={
                "enabled": True,
                "actions": [{"id": "attempt_skill_action", "label": "Religion", "skill": "religion"}],
                "permissions": {"requires_token": True},
                "visibility": {"discovery_visibility": "private_player"},
                "discovery_hook": "shrine-clue",
            },
        )
    }

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    async def fake_save(_session):
        return True

    monkeypatch.setattr("server.handlers.map_editor.manager.send_to", fake_send_to)
    monkeypatch.setattr("server.handlers.map_editor.save_campaign_async", fake_save)

    asyncio.run(handle_interactable_action({
        "target_kind": "poi",
        "target_id": "poi-1",
        "action": "attempt_skill_action",
        "skill": "religion",
    }, session, player))

    assert any(user_id == dm.id and message.get("type") == "interactable_action_event" for _, user_id, message in sent)
    result = next(message for _, user_id, message in sent if user_id == player.id and message.get("type") == "interactable_action_result")
    assert result["payload"]["discovery_hook"] == "shrine-clue"
    assert result["payload"]["discovery_visibility"] == "private_player"


def test_player_state_includes_poi_interactable_without_dm_notes():
    from server.session import POI, Session, User

    session = Session(id="INT005", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.pois = {
        "poi-1": POI(
            id="poi-1",
            x=10,
            y=15,
            name="Shrine",
            dm_notes="Secret inscription",
            interactable={
                "enabled": True,
                "kind": "poi",
                "actions": [{"id": "inspect", "label": "Inspect"}],
            },
        )
    }

    player_state = session.to_state_dict_for_role("player", player.id)
    dm_state = session.to_state_dict_for_role("dm", dm.id)

    assert player_state["pois"]["poi-1"]["interactable"]["actions"][0]["id"] == "inspect"
    assert "dm_notes" not in player_state["pois"]["poi-1"]
    assert dm_state["pois"]["poi-1"]["dm_notes"] == "Secret inscription"


def test_interactable_state_transition_persists_and_updates_actions(monkeypatch):
    from server.handlers.map_editor import handle_interactable_action
    from server.persistence_schema import extract_persistable_campaign_state, normalize_persisted_campaign_data
    from server.session import Session, User

    session = Session(id="INT006", dm_id="dm-user")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {player.id: player}
    session.editor_props = {
        "world": [{
            "id": "prop-chest",
            "kind": "chest",
            "name": "Old Chest",
            "x": 0, "y": 0, "w": 1, "h": 1,
            "interactable": {
                "enabled": True,
                "current_state": "closed",
                "actions": [{"id": "inspect", "label": "Inspect"}],
                "states": {
                    "closed": {
                        "label_override": "Sealed Chest",
                        "available_actions": [{"id": "open", "label": "Open Chest"}],
                        "next_state_by_action": {"open": "opened"},
                        "world_state_flags": {"ruins.chest_opened": True},
                    },
                    "opened": {
                        "label_override": "Opened Chest",
                        "available_actions": [{"id": "loot", "label": "Loot Chest"}],
                        "next_state_by_action": {"loot": "looted"},
                    },
                    "looted": {
                        "label_override": "Looted Chest",
                        "available_actions": [{"id": "inspect", "label": "Inspect"}],
                    },
                },
            },
        }]
    }

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    async def fake_save(_session):
        return True

    async def fake_props_sync(_session):
        return True

    monkeypatch.setattr("server.handlers.map_editor.manager.send_to", fake_send_to)
    monkeypatch.setattr("server.handlers.map_editor.save_campaign_async", fake_save)
    monkeypatch.setattr("server.handlers.map_editor._broadcast_editor_props_state", fake_props_sync)

    asyncio.run(handle_interactable_action({
        "target_kind": "prop",
        "target_id": "prop-chest",
        "map_context": "world",
        "action": "open",
    }, session, player))

    interactable = session.editor_props["world"][0]["interactable"]
    assert interactable["current_state"] == "opened"
    assert session.world_state["world_state_flags"]["ruins.chest_opened"] is True
    persisted = extract_persistable_campaign_state(session)
    rehydrated = normalize_persisted_campaign_data(persisted)
    persisted_interactable = rehydrated["editor_props"]["world"][0]["interactable"]
    assert persisted_interactable["current_state"] == "opened"

    sent.clear()
    asyncio.run(handle_interactable_action({
        "target_kind": "prop",
        "target_id": "prop-chest",
        "map_context": "world",
        "action": "open",
    }, session, player))
    assert sent[-1][2]["type"] == "error"


def test_interactable_state_event_payload_respects_private_result(monkeypatch):
    from server.handlers.map_editor import handle_interactable_action
    from server.session import Session, User

    session = Session(id="INT007", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    session.users = {dm.id: dm, player.id: player, viewer.id: viewer}
    session.editor_props = {
        "world": [{
            "id": "prop-shrine",
            "kind": "statue",
            "name": "Shrine",
            "x": 0, "y": 0, "w": 1, "h": 1,
            "interactable": {
                "enabled": True,
                "current_state": "revealed",
                "states": {
                    "revealed": {
                        "available_actions": [{"id": "interact", "label": "Pray"}],
                        "handout_unlock_ids": ["h-1"],
                        "discovery_hook": "shrine-revelation",
                        "next_state": "exhausted",
                    },
                    "exhausted": {"available_actions": [{"id": "inspect", "label": "Inspect"}]},
                },
            },
        }]
    }

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    async def fake_save(_session):
        return True

    async def fake_props_sync(_session):
        return True

    monkeypatch.setattr("server.handlers.map_editor.manager.send_to", fake_send_to)
    monkeypatch.setattr("server.handlers.map_editor.save_campaign_async", fake_save)
    monkeypatch.setattr("server.handlers.map_editor._broadcast_editor_props_state", fake_props_sync)

    asyncio.run(handle_interactable_action({
        "target_kind": "prop",
        "target_id": "prop-shrine",
        "map_context": "world",
        "action": "interact",
    }, session, player))

    result_targets = [uid for _, uid, message in sent if message.get("type") == "interactable_action_result"]
    event_targets = [uid for _, uid, message in sent if message.get("type") == "interactable_action_event"]
    assert result_targets == [player.id]
    assert event_targets == []
    result_payload = next(message["payload"] for _, _, message in sent if message.get("type") == "interactable_action_result")
    assert result_payload["interactable_next_state"] == "exhausted"
    assert result_payload["handout_unlock_ids"] == ["h-1"]
    assert result_payload["discovery_hook"] == "shrine-revelation"
    assert result_payload.get("living_world_event_id")
