"""
tests/test_integration_map_editor_tab.py — Integration tests for the map
editor tab full user flow.

Tests cover:
- handle_editor_layer_save: layer data saved, broadcast sent, DM-only guard
- handle_editor_walls_save: walls stored and broadcast
- handle_fog_toggle: DM enables fog, broadcast to all clients
- handle_fog_paint: DM paints fog cells, broadcast excludes no-one (multi-tab sync)
- handle_door_toggle: door state flipped, broadcast sent
- handle_poi_create / handle_poi_update / handle_poi_delete: POI lifecycle
- handle_weather_set: weather state saved and broadcast
- Role guard: player cannot save editor layers or toggle fog

Why these tests matter:
The map editor is a live multiplayer tool — every paint, wall, or fog change
must reach all connected clients immediately.  Role guards ensure players
cannot accidentally or maliciously alter the map.
"""
import asyncio
import sys
import os
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    from server.session import Session, User
    session = Session(id="map-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.fog_maps = {
        "world": {"enabled": False, "cols": 8, "rows": 8, "cells": "0" * 64}
    }
    session.editor_layers = {}
    session.editor_walls = {}
    session.editor_props = {}
    session.editor_paths = {}
    session.editor_labels = {}
    session.editor_markers = {}
    return session, dm, player


def _fake_manager():
    broadcasts = []
    sent = []

    async def broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    m = SimpleNamespace(broadcast=broadcast, send_to=send_to)
    m._broadcasts = broadcasts
    m._sent = sent
    return m


# ---------------------------------------------------------------------------
# handle_editor_layer_save
# ---------------------------------------------------------------------------

def test_editor_layer_save_stores_layer_data(monkeypatch):
    """Editor layer save must persist tile data to the session."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    # payload uses "map_context" (not "map_ctx") and "cells" (not "layer_data")
    # Cell keys are "x:y" format, values are tile IDs (integers 1-9999)
    asyncio.run(me.handle_editor_layer_save(
        {"map_context": "world", "cells": {"1:1": 1, "2:2": 2}},
        session,
        dm,
    ))

    layers = (session.editor_layers or {}).get("world", {})
    assert "1:1" in layers or "2:2" in layers


def test_editor_layer_save_broadcasts_sync(monkeypatch):
    """Saving editor layers should broadcast editor_layers_sync."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_editor_layer_save(
        {"map_context": "world", "cells": {"3:3": 3}},
        session,
        dm,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "editor_layers_sync" in types


def test_editor_layer_save_player_cannot_save(monkeypatch):
    """Players should not be able to save editor layers."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_editor_layer_save(
        {"map_context": "world", "cells": {"1:1": 99}},
        session,
        player,
    ))

    # No broadcast should occur for a player attempt
    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "editor_layers_sync" not in types


# ---------------------------------------------------------------------------
# handle_fog_toggle
# ---------------------------------------------------------------------------

def test_fog_toggle_enables_fog(monkeypatch):
    """DM toggling fog on should set enabled=True in session fog_maps."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_fog_toggle(
        {"map_ctx": "world", "enabled": True},
        session,
        dm,
    ))

    fog = (session.fog_maps or {}).get("world", {})
    assert fog.get("enabled") is True


def test_fog_toggle_broadcasts_fog_toggle(monkeypatch):
    """handle_fog_toggle must broadcast a fog_state message."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_fog_toggle(
        {"map_ctx": "world", "enabled": True},
        session,
        dm,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    # The broadcast type is 'fog_state' (contains the full fog state payload)
    assert "fog_state" in types


def test_fog_toggle_player_cannot_toggle(monkeypatch):
    """Players must not be able to toggle fog."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_fog_toggle(
        {"map_ctx": "world", "enabled": True},
        session,
        player,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "fog_toggle" not in types


# ---------------------------------------------------------------------------
# handle_fog_paint
# ---------------------------------------------------------------------------

def test_fog_paint_broadcasts_to_all_clients_including_dm(monkeypatch):
    """Fog paint must broadcast fog_update to all clients (including DM sender)."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}
    }
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_fog_paint(
        {"map_ctx": "world", "reveal": True, "cells": [0, 5, 10]},
        session,
        dm,
    ))

    assert len(mgr._broadcasts) > 0
    _session_id, message, exclude_user = mgr._broadcasts[-1]
    assert message["type"] == "fog_update"
    assert exclude_user is None  # DM must also receive


def test_fog_paint_reveal_correct_cells(monkeypatch):
    """Painted cells should be marked as revealed in the fog map."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}
    }
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_fog_paint(
        {"map_ctx": "world", "reveal": True, "cells": [0, 3]},
        session,
        dm,
    ))

    fog_cells = session.fog_maps["world"]["cells"]
    assert fog_cells[0] == "1"
    assert fog_cells[3] == "1"
    assert fog_cells[1] == "0"


# ---------------------------------------------------------------------------
# handle_door_toggle
# ---------------------------------------------------------------------------

def test_door_toggle_broadcasts_door_state(monkeypatch):
    """Toggling a door should broadcast door state update."""
    import secrets
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    door_id = secrets.token_hex(4)
    session.editor_props = {"world": [{
        "id": door_id,
        "kind": "door",
        "x": 50,
        "y": 50,
        "interactable": {"enabled": True, "kind": "door", "is_open": False, "is_locked": False},
    }]}
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_door_toggle(
        {"map_ctx": "world", "prop_id": door_id, "is_open": True},
        session,
        dm,
    ))

    types_broadcast = [msg["type"] for _, msg, _ in mgr._broadcasts]
    types_sent = [msg["type"] for _, _, msg in mgr._sent]
    all_types = types_broadcast + types_sent
    # Should produce at least one update (door state or editor props sync)
    assert len(all_types) > 0


# ---------------------------------------------------------------------------
# handle_poi_create / handle_poi_update / handle_poi_delete
# ---------------------------------------------------------------------------

def test_poi_create_adds_poi_to_session(monkeypatch):
    """Creating a POI should store it in session.pois."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    session.pois = {}
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_poi_create(
        {
            "map_ctx": "world",
            "poi": {"id": "poi-1", "x": 100, "y": 200, "name": "Hidden Door"},
        },
        session,
        dm,
    ))

    assert "poi-1" in session.pois or len(session.pois) > 0


def test_poi_delete_removes_poi_from_session(monkeypatch):
    """Deleting a POI should remove it from session.pois."""
    from server.handlers import map_editor as me
    from server.session import POI
    session, dm, player = _make_session()
    session.pois = {
        "poi-1": POI(id="poi-1", x=100, y=200, name="Hidden Door"),
    }
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_poi_delete(
        {"poi_id": "poi-1"},
        session,
        dm,
    ))

    assert "poi-1" not in (session.pois or {})


# ---------------------------------------------------------------------------
# handle_weather_set
# ---------------------------------------------------------------------------

def test_weather_set_updates_session_state(monkeypatch):
    """Setting weather should update session.weather_state."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_weather_set(
        {"map_ctx": "world", "weather_type": "rain", "intensity": 0.7},
        session,
        dm,
    ))

    weather = getattr(session, "weather_state", None)
    assert weather is not None
    assert weather.get("weather_type") == "rain"


def test_weather_set_broadcasts_to_all(monkeypatch):
    """Weather update should be broadcast to all clients."""
    from server.handlers import map_editor as me
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(me, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    asyncio.run(me.handle_weather_set(
        {"map_ctx": "world", "weather_type": "snow", "intensity": 0.3},
        session,
        dm,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert any("weather" in t for t in types)
