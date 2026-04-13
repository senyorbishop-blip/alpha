import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.restore import restore_session_from_db
from server.session import POI, Session, User


def _base_restore_payload() -> dict:
    return {
        "id": "RESTORE1",
        "name": "Campaign",
        "dm_name": "Dungeon Master",
        "player_invite": "PLAY001",
        "viewer_invite": "VIEW001",
        "created_at": 1.0,
        "updated_at": 1.0,
        "map_image_url": "/static/maps/world.png",
        "dm_id": "dm-1",
        "tokens": [],
        "logs": [],
        "players": [],
        "pois": [],
    }


def test_restore_invalid_dm_map_context_falls_back_to_world():
    payload = _base_restore_payload()
    payload["dm_map_context"] = "missing-poi"
    payload["dm_current_map_url"] = "/static/maps/ghost.png"
    payload["dm_nav_intent"] = 9

    restored, _ = restore_session_from_db(payload)

    assert restored.dm_map_context == "world"
    assert restored.dm_current_map_url is None
    assert restored.map_nav_version == 0
    assert restored.dm_nav_intent == 9


def test_restore_local_dm_map_context_prefers_poi_url():
    payload = _base_restore_payload()
    payload["dm_map_context"] = "poi-1"
    payload["dm_current_map_url"] = "/static/maps/stale.png"
    payload["pois"] = [{
        "id": "poi-1",
        "x": 10,
        "y": 20,
        "name": "Inn",
        "local_map_url": "/static/maps/inn.png",
    }]

    restored, _ = restore_session_from_db(payload)

    assert restored.dm_map_context == "poi-1"
    assert restored.dm_current_map_url == "/static/maps/inn.png"
    assert restored.map_nav_version == 1
    assert restored.dm_nav_intent == 1


def test_local_map_nav_ignores_stale_intent_and_normalizes_bad_context(monkeypatch):
    session = Session(id="NAV1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "poi-1"
    session.dm_current_map_url = "/static/maps/inn.png"
    session.dm_nav_intent = 5
    session.pois["poi-1"] = POI(id="poi-1", x=0, y=0, name="Inn", local_map_url="/static/maps/inn.png")

    sent = []
    broadcast = []

    async def _broadcast(*args, **kwargs):
        broadcast.append((args, kwargs))

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(broadcast=_broadcast, send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(map_editor.handle_local_map_nav({
        "dm_map_context": "world",
        "client_nav_intent": 4,
    }, session, dm))

    assert session.dm_map_context == "poi-1"
    assert session.dm_current_map_url == "/static/maps/inn.png"
    assert session.dm_nav_intent == 5
    assert not broadcast
    assert not sent

    asyncio.run(map_editor.handle_local_map_nav({
        "dm_map_context": "not-a-real-poi",
        "map_url": "/static/maps/wrong.png",
        "client_nav_intent": 6,
    }, session, dm))

    assert session.dm_map_context == "world"
    assert session.dm_current_map_url is None
    assert session.dm_nav_intent == 6
    assert session.map_nav_version == 1
    assert broadcast
    assert sent
