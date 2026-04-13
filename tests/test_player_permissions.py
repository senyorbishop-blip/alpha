import asyncio


def test_user_role_is_normalized_for_legacy_uppercase_values():
    from server.session import Session, User

    session = Session(id="VIEWROLE", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="DM")
    viewer = User(id="viewer-a", name="Eyes", role="VIEWER")
    viewer.player_key = "viewer-key"
    session.users = {dm.id: dm, viewer.id: viewer}
    session.viewer_profiles = {
        "viewer-key": {
            "viewer_key": "viewer-key",
            "user_id": viewer.id,
            "name": "Eyes",
            "powers": {"fireball": {"power_id": "fireball", "charges": 1}},
        }
    }

    state = session.to_state_dict_for_role(viewer.role, viewer.id)

    assert viewer.role == "viewer"
    assert dm.role == "dm"
    assert "viewer-key" in state.get("viewer_profiles", {})


def test_private_discovery_only_reaches_target_player(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="DISC123", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player_a = User(id="player-a", name="Alice", role="player")
    player_b = User(id="player-b", name="Borin", role="player")
    session.users = {dm.id: dm, player_a.id: player_a, player_b.id: player_b}

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    monkeypatch.setattr(content.manager, "send_to", fake_send_to)
    monkeypatch.setattr(content, "manager", content.manager)

    asyncio.run(content.handle_discovery_trigger({
        "title": "Hidden Lever",
        "body": "You notice a hidden lever tucked behind the cracked relief.",
        "kind": "clue",
        "visibility": "private_player",
        "target_user_id": player_a.id,
    }, session, dm))

    delivery_targets = [user_id for _, user_id, msg in sent if msg.get("type") == "discovery_card"]
    assert delivery_targets == [player_a.id]
    assert any(user_id == dm.id and msg.get("type") == "discovery_card_pending" for _, user_id, msg in sent)


def test_viewer_emote_accepts_legacy_uppercase_role(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="EMOTE01", dm_id="dm-user")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    viewer.role = "VIEWER"
    session.users = {viewer.id: viewer}
    sent = []

    async def fake_broadcast(session_id, message, exclude_user=None):
        sent.append((session_id, message, exclude_user))

    monkeypatch.setattr(content.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(content, "manager", content.manager)

    asyncio.run(content.handle_viewer_emote({"emote": "🔥"}, session, viewer))

    assert sent
    assert sent[0][1]["type"] == "viewer_emote"
    assert sent[0][1]["payload"]["user_id"] == viewer.id


def test_chat_message_rejects_viewer_role_including_legacy_uppercase(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="CHATVIEW", dm_id="dm-user")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    viewer.role = "VIEWER"
    session.users = {viewer.id: viewer}
    sent = []

    async def fake_broadcast(session_id, message, exclude_user=None):
        sent.append(("broadcast", session_id, message, exclude_user))

    async def fake_send_to(session_id, user_id, message):
        sent.append(("send_to", session_id, user_id, message))
        return True

    monkeypatch.setattr(content.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(content.manager, "send_to", fake_send_to)
    monkeypatch.setattr(content, "manager", content.manager)

    asyncio.run(content.handle_chat_message({"message": "hello world"}, session, viewer))
    asyncio.run(content.handle_chat_message({"message": "hello viewers", "channel": "viewers"}, session, viewer))
    asyncio.run(content.handle_chat_message({"message": "hello whisper", "channel": "whisper", "target_user_id": "dm-user"}, session, viewer))

    assert sent == []


def test_party_public_discovery_reaches_dm_and_players(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="DISC124", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player_a = User(id="player-a", name="Alice", role="player")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    session.users = {dm.id: dm, player_a.id: player_a, viewer.id: viewer}

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    monkeypatch.setattr(content.manager, "send_to", fake_send_to)
    monkeypatch.setattr(content, "manager", content.manager)

    asyncio.run(content.handle_discovery_trigger({
        "title": "Blood Trail",
        "body": "A dark trail disappears behind the collapsed statue.",
        "kind": "observation",
        "visibility": "party_public",
    }, session, dm))

    delivery_targets = sorted(user_id for _, user_id, msg in sent if msg.get("type") == "discovery_card")
    assert delivery_targets == sorted([dm.id, player_a.id])


def test_state_sync_filters_private_discoveries_by_player_and_viewer():
    from server.session import Session, User

    session = Session(id="DISC125", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player_a = User(id="player-a", name="Alice", role="player")
    player_b = User(id="player-b", name="Borin", role="player")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    session.users = {dm.id: dm, player_a.id: player_a, player_b.id: player_b, viewer.id: viewer}
    session.discovery_cards = [
        {
            "id": "disc-private",
            "title": "Private Clue",
            "body": "Only Alice should see this.",
            "visibility": "private_player",
            "target_user_id": player_a.id,
            "acknowledged_by": [],
            "meta": {"scope": "discovery_card", "audience": "player", "ui_channel": "discovery_card"},
        },
        {
            "id": "disc-party",
            "title": "Shared Find",
            "body": "Everyone in the party can see this.",
            "visibility": "party_public",
            "target_user_id": "",
            "acknowledged_by": [],
            "meta": {"scope": "discovery_card", "audience": "party", "ui_channel": "discovery_card"},
        },
    ]

    dm_state = session.to_state_dict_for_role("dm", dm.id)
    player_a_state = session.to_state_dict_for_role("player", player_a.id)
    player_b_state = session.to_state_dict_for_role("player", player_b.id)
    viewer_state = session.to_state_dict_for_role("viewer", viewer.id)

    assert {card["id"] for card in dm_state["discovery_cards"]} == {"disc-private", "disc-party"}
    assert {card["id"] for card in player_a_state["discovery_cards"]} == {"disc-private", "disc-party"}
    assert {card["id"] for card in player_b_state["discovery_cards"]} == {"disc-party"}
    assert viewer_state["discovery_cards"] == []


def test_discovery_acknowledge_hides_card_from_reconnecting_player(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="DISC126", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.discovery_cards = [{
        "id": "disc-ack",
        "title": "Whisper",
        "body": "A soft voice brushes past your ear.",
        "visibility": "private_player",
        "target_user_id": player.id,
        "acknowledged_by": [],
        "meta": {"scope": "discovery_card", "audience": "player", "ui_channel": "discovery_card"},
    }]

    async def fake_save(_session):
        return True

    monkeypatch.setattr(content, "save_campaign_async", fake_save)

    asyncio.run(content.handle_discovery_acknowledge({"id": "disc-ack"}, session, player))

    player_state = session.to_state_dict_for_role("player", player.id)
    dm_state = session.to_state_dict_for_role("dm", dm.id)
    assert player_state["discovery_cards"] == []
    assert dm_state["discovery_cards"][0]["acknowledged_by"] == [player.id]


def test_private_story_hooks_only_sync_to_target_player_and_dm():
    from server.session import Session, User

    session = Session(id="HOOK125", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player_a = User(id="player-a", name="Alice", role="player")
    player_b = User(id="player-b", name="Borin", role="player")
    viewer = User(id="viewer-a", name="Eyes", role="viewer")
    session.users = {dm.id: dm, player_a.id: player_a, player_b.id: player_b, viewer.id: viewer}
    session.private_story_hooks = [
        {
            "id": "hook-a",
            "title": "Recognize the Crest",
            "body": "You recognize this family crest immediately.",
            "kind": "prompt",
            "status": "active",
            "target_user_id": player_a.id,
        },
        {
            "id": "hook-b",
            "title": "Protect the Cleric",
            "body": "Protect the cleric, but do not say why.",
            "kind": "objective",
            "status": "resolved",
            "target_user_id": player_b.id,
        },
    ]

    dm_state = session.to_state_dict_for_role("dm", dm.id)
    player_a_state = session.to_state_dict_for_role("player", player_a.id)
    player_b_state = session.to_state_dict_for_role("player", player_b.id)
    viewer_state = session.to_state_dict_for_role("viewer", viewer.id)

    assert {entry["id"] for entry in dm_state["private_story_hooks"]} == {"hook-a", "hook-b"}
    assert [entry["id"] for entry in player_a_state["private_story_hooks"]] == ["hook-a"]
    assert [entry["id"] for entry in player_b_state["private_story_hooks"]] == ["hook-b"]
    assert viewer_state["private_story_hooks"] == []


def test_private_story_hook_without_target_is_dm_only():
    from server.session import Session, User

    session = Session(id="HOOK126", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.private_story_hooks = [{
        "id": "hook-orphan",
        "title": "Do not leak",
        "body": "Missing target should never leak to players.",
        "kind": "prompt",
        "status": "active",
        "target_user_id": "",
    }]

    dm_state = session.to_state_dict_for_role("dm", dm.id)
    player_state = session.to_state_dict_for_role("player", player.id)

    assert [entry["id"] for entry in dm_state["private_story_hooks"]] == ["hook-orphan"]
    assert player_state["private_story_hooks"] == []


def test_player_spell_library_sync_only_returns_granted_spells(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="TEST123", dm_id="dm-user")
    player = User(id="player-user", name="Alice", role="player")
    session.users[player.id] = player

    sent = {}

    async def fake_send_to(session_id, user_id, message):
      sent["session_id"] = session_id
      sent["user_id"] = user_id
      sent["message"] = message

    monkeypatch.setattr(content.manager, "send_to", fake_send_to)
    monkeypatch.setattr(content, "manager", content.manager)

    import server.rules_db as rules_db

    monkeypatch.setattr(rules_db, "get_spell_library", lambda session_id: [{"id": "fireball"}])
    monkeypatch.setattr(rules_db, "get_granted_spells_for_user", lambda session_id, user_id: [{"id": "grant-1", "spell_id": "magic-missile", "spell_source": "srd"}])
    monkeypatch.setattr(rules_db, "get_granted_spell_library_for_user", lambda session_id, user_id: [{"id": "magic-missile", "name": "Magic Missile", "grant_id": "grant-1", "spell_source": "srd"}])

    asyncio.run(content.handle_get_spell_library({}, session, player))

    payload = sent["message"]["payload"]
    assert sent["session_id"] == session.id
    assert sent["user_id"] == player.id
    assert payload["library"] == []
    assert payload["grants"] == [{"id": "grant-1", "spell_id": "magic-missile", "spell_source": "srd"}]
    assert payload["player_spells"] == [{"id": "magic-missile", "name": "Magic Missile", "grant_id": "grant-1", "spell_source": "srd"}]


def test_bestiary_list_requires_dm(monkeypatch):
    from server.creatures import service

    class FakeRequest:
        def __init__(self):
            self.cookies = {}
            self.headers = {}

    monkeypatch.setattr(service, "get_request_user", lambda request: {"id": "player-user", "role": "player"})

    response = asyncio.run(service.list_creatures_response(FakeRequest(), owner_id="player-user"))

    assert response.status_code == 403
    assert b"DM only" in response.body


def test_bestiary_list_allows_authenticated_session_dm_via_session_authority(monkeypatch):
    from server.creatures import service
    from server.session import Session

    class FakeRequest:
        def __init__(self):
            self.cookies = {}
            self.headers = {}

    request = FakeRequest()
    session = Session(id="TEST123", dm_id="auth_dm_user")
    async def fake_seed_library(owner_user_id):
        return None

    monkeypatch.setattr(service, "get_request_user", lambda req: {"id": "auth_dm_user", "role": "dm"})
    monkeypatch.setattr(service, "get_or_restore_session", lambda session_id: session if session_id == "TEST123" else None)
    monkeypatch.setattr(service, "request_has_dm_access", lambda req, live_session, fallback_user_id="": live_session is session)
    monkeypatch.setattr(service, "seed_library_for_owner", fake_seed_library)
    monkeypatch.setattr(service, "get_creatures", lambda owner_user_id, **filters: [{"id": "creature-1", "owner_user_id": owner_user_id}])

    response = asyncio.run(service.list_creatures_response(request, owner_id="ignored-owner", session_id="test123"))

    assert response.status_code == 200
    assert b"creature-1" in response.body


def test_bestiary_list_allows_join_link_dm_session_authority(monkeypatch):
    from server.creatures import service
    from server.session import Session

    class FakeRequest:
        def __init__(self):
            self.cookies = {}
            self.headers = {}

    request = FakeRequest()
    session = Session(id="TEST123", dm_id="dm-link-user")
    async def fake_seed_library(owner_user_id):
        return None

    monkeypatch.setattr(service, "get_request_user", lambda req: None)
    monkeypatch.setattr(service, "get_or_restore_session", lambda session_id: session if session_id == "TEST123" else None)
    monkeypatch.setattr(service, "request_has_dm_access", lambda req, live_session, fallback_user_id="": live_session is session and fallback_user_id == "dm-link-user")
    monkeypatch.setattr(service, "seed_library_for_owner", fake_seed_library)
    monkeypatch.setattr(service, "get_creatures", lambda owner_user_id, **filters: [{"id": "creature-join-link", "owner_user_id": owner_user_id}])

    response = asyncio.run(service.list_creatures_response(request, owner_id="dm-link-user", session_id="test123"))

    assert response.status_code == 200
    assert b"creature-join-link" in response.body



def test_player_can_save_and_unsave_visible_discovery(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    session = Session(id="DISC127", dm_id="dm-user")
    dm = User(id="dm-user", name="DM", role="dm")
    player = User(id="player-a", name="Alice", role="player")
    session.users = {dm.id: dm, player.id: player}
    session.discovery_cards = [{
        "id": "disc-save",
        "title": "Loose Flagstone",
        "body": "A slight draft rises from below.",
        "visibility": "private_player",
        "target_user_id": player.id,
        "can_save": True,
        "saved_by": [],
        "acknowledged_by": [],
        "meta": {"scope": "discovery_card", "audience": "player", "ui_channel": "discovery_card"},
    }]

    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    async def fake_save(_session):
        return True

    monkeypatch.setattr(content.manager, "send_to", fake_send_to)
    monkeypatch.setattr(content, "manager", content.manager)
    monkeypatch.setattr(content, "save_campaign_async", fake_save)

    asyncio.run(content.handle_discovery_save({"id": "disc-save"}, session, player))
    assert session.discovery_cards[0]["saved_by"] == [player.id]
    assert session.to_state_dict_for_role("player", player.id)["saved_discoveries"][0]["id"] == "disc-save"
    assert sent[-1][2]["type"] == "discovery_saved"

    asyncio.run(content.handle_discovery_unsave({"id": "disc-save"}, session, player))
    assert session.discovery_cards[0]["saved_by"] == []
    assert session.to_state_dict_for_role("player", player.id)["saved_discoveries"] == []
    assert sent[-1][2]["type"] == "discovery_unsaved"
