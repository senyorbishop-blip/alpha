import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.session import POI, Session, User


def test_fog_paint_broadcasts_to_all_clients_including_dm_sender(monkeypatch):
    session = Session(id="fog-sync-1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}
    }

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_paint(
            {"map_ctx": "world", "reveal": True, "cells": [0, 5, 10]},
            session,
            dm,
        )
    )

    assert sent, "fog paint should deliver updates to connected clients"
    _session_id, user_id, message = sent[-1]
    assert message["type"] == "fog_update"
    assert message["payload"]["map_ctx"] == "world"
    assert message["payload"]["cells"] == [0, 5, 10]
    assert user_id == dm.id, "DM sender must still receive fog_update for multi-tab DM sync"


def test_fog_toggle_uses_payload_map_context_not_dm_context(monkeypatch):
    session = Session(id="fog-sync-2")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.pois["poi-crypt"] = POI(id="poi-crypt", x=0, y=0, name="Crypt", map_context="world")
    session.set_user_subgroup_id(player.id, "alpha", actor_id=dm.id)
    session.set_subgroup_map_context("alpha", "poi-crypt", actor_id=dm.id)
    session.fog_maps = {
        "world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16},
        "poi-crypt": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16},
    }

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_toggle(
            {"map_ctx": "poi-crypt", "enabled": True},
            session,
            dm,
        )
    )

    assert session.fog_maps["poi-crypt"]["enabled"] is True
    assert session.fog_maps["world"]["enabled"] is False
    assert {uid for _, uid, _ in sent} == {dm.id, player.id}


def test_fog_paint_accepts_map_context_alias_and_isolates_world_from_poi(monkeypatch):
    session = Session(id="fog-sync-3")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.pois["poi-inn"] = POI(id="poi-inn", x=0, y=0, name="Inn", map_context="world")
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16},
        "poi-inn": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16},
    }

    async def _send_to(*_args, **_kwargs):
        return True

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_paint(
            {"map_context": "poi-inn", "reveal": True, "cells": [1, 2]},
            session,
            dm,
        )
    )

    assert session.fog_maps["poi-inn"]["cells"][1] == "1"
    assert session.fog_maps["poi-inn"]["cells"][2] == "1"
    assert session.fog_maps["world"]["cells"] == "0" * 16


def test_fog_broadcast_only_reaches_users_with_map_visibility(monkeypatch):
    session = Session(id="fog-sync-4")
    dm = User(id="dm-1", name="DM", role="dm")
    player_world = User(id="pl-world", name="World", role="player")
    player_poi = User(id="pl-poi", name="POI", role="player")
    session.users[dm.id] = dm
    session.users[player_world.id] = player_world
    session.users[player_poi.id] = player_poi
    session.dm_id = dm.id
    session.dm_map_context = "poi-cave"
    session.pois["poi-cave"] = POI(id="poi-cave", x=0, y=0, name="Cave", map_context="world")
    session.set_user_subgroup_id(player_world.id, "alpha", actor_id=dm.id)
    session.set_subgroup_map_context("alpha", "world", actor_id=dm.id)
    session.set_user_subgroup_id(player_poi.id, "beta", actor_id=dm.id)
    session.set_subgroup_map_context("beta", "poi-cave", actor_id=dm.id)
    session.fog_maps = {"poi-cave": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_paint(
            {"map_ctx": "poi-cave", "reveal": True, "cells": [0]},
            session,
            dm,
        )
    )

    recipients = {uid for _, uid, _ in sent}
    assert dm.id in recipients
    assert player_poi.id in recipients
    assert player_world.id not in recipients
