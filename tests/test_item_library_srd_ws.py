import asyncio

from server.item_library_srd import clear_srd_items_snapshot_cache, get_srd_items_payload, get_srd_items_version


class _FakeManager:
    def __init__(self):
        self.sent = []

    async def send_to(self, session_id, user_id, message):
        self.sent.append((session_id, user_id, message))


def test_srd_items_version_is_stable_and_payload_matches(monkeypatch):
    import server.rules_db as rules_db

    clear_srd_items_snapshot_cache()
    monkeypatch.setattr(rules_db, "get_all_srd_items", lambda: [
        {"id": "b", "name": "Beta", "category": "Gear"},
        {"id": "a", "name": "Alpha", "category": "Gear"},
    ])

    first = get_srd_items_version()
    second = get_srd_items_version()
    payload = get_srd_items_payload()

    assert first == second
    assert payload["srd_items_version"] == first
    assert payload["srd_items"] == [
        {"id": "b", "name": "Beta", "category": "Gear"},
        {"id": "a", "name": "Alpha", "category": "Gear"},
    ]
    clear_srd_items_snapshot_cache()


def test_srd_items_request_responds_only_to_requesting_user(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    fake_manager = _FakeManager()
    monkeypatch.setattr(content, "manager", fake_manager)
    monkeypatch.setattr("server.item_library_srd.get_srd_items_payload", lambda: {
        "srd_items": [{"id": "rope", "name": "Rope"}],
        "srd_items_version": "abc123",
    })

    session = Session(id="sess")
    dm = User(id="dm", name="DM", role="dm")
    player = User(id="player", name="Player", role="player")
    session.users = {"dm": dm, "player": player}

    asyncio.run(content.handle_srd_items_request({}, session, player))

    assert fake_manager.sent == [("sess", "player", {
        "type": "srd_items_response",
        "payload": {"srd_items": [{"id": "rope", "name": "Rope"}], "srd_items_version": "abc123"},
    })]


def test_item_library_broadcast_sends_entries_and_version_without_full_srd(monkeypatch):
    from server.handlers import content
    from server.session import Session, User

    fake_manager = _FakeManager()
    monkeypatch.setattr(content, "manager", fake_manager)
    monkeypatch.setattr("server.item_library_srd.get_srd_items_version", lambda: "v1")

    session = Session(id="sess")
    session.item_library_entries = [{"id": "custom", "name": "Custom Blade"}]
    session.users = {
        "dm": User(id="dm", name="DM", role="dm"),
        "player": User(id="player", name="Player", role="player"),
    }

    asyncio.run(content._broadcast_item_library_state(session))

    assert len(fake_manager.sent) == 2
    for _, _, message in fake_manager.sent:
        assert message["type"] == "item_library_sync"
        assert message["payload"]["entries"] == [{"id": "custom", "name": "Custom Blade"}]
        assert message["payload"]["srd_items_version"] == "v1"
        assert "srd_items" not in message["payload"]


def test_play_page_uses_versioned_srd_cache_and_requests_stale_cache():
    src = open("client/templates/play.html", encoding="utf-8").read()

    assert "case 'item_library_sync'" in src
    assert "srd_items_version" in src
    assert "loadCachedSrdItems(version)" in src
    assert "requestSrdItems(version)" in src
    assert "sendWS({ type: 'srd_items_request'" in src
    assert "case 'srd_items_response'" in src
    assert "applySrdItemsPayload(p.srd_items, version)" in src
    assert "SRD_ITEMS_CACHE_PREFIX" in src
