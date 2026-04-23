import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.session import POI, Session, User
from server.persistence_schema import extract_persistable_campaign_state
from server.restore import restore_session_from_db


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


def test_fog_toggle_local_alias_uses_dm_map_context(monkeypatch):
    session = Session(id="fog-sync-2b")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "poi-crypt"
    session.pois["poi-crypt"] = POI(id="poi-crypt", x=0, y=0, name="Crypt", map_context="world")
    session.fog_maps = {
        "world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16},
        "poi-crypt": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16},
    }

    async def _send_to(*_args, **_kwargs):
        return True

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_toggle(
            {"map_ctx": "__local__", "enabled": True},
            session,
            dm,
        )
    )

    assert session.fog_maps["poi-crypt"]["enabled"] is True
    assert session.fog_maps["world"]["enabled"] is False


def test_fog_toggle_accepts_runtime_dm_scene_context_even_if_not_yet_indexed(monkeypatch):
    session = Session(id="fog-sync-2c")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "DC759816D739"
    session.fog_maps = {
        "world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16},
        "DC759816D739": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16},
    }

    async def _send_to(*_args, **_kwargs):
        return True

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_toggle(
            {"map_ctx": "DC759816D739", "enabled": True},
            session,
            dm,
        )
    )

    assert session.fog_maps["DC759816D739"]["enabled"] is True
    assert session.fog_maps["world"]["enabled"] is False


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


def test_fog_broadcast_includes_main_party_player_when_split_party_metadata_exists(monkeypatch):
    session = Session(id="fog-sync-main-follow-dm")
    dm = User(id="dm-1", name="DM", role="dm")
    main_player = User(id="pl-main", name="Main", role="player")
    side_player = User(id="pl-side", name="Side", role="player")
    session.users[dm.id] = dm
    session.users[main_player.id] = main_player
    session.users[side_player.id] = side_player
    session.dm_id = dm.id
    session.dm_map_context = "poi-prison"
    session.pois["poi-prison"] = POI(id="poi-prison", x=0, y=0, name="Prison", map_context="world")
    # Split-party metadata exists (side group assigned), but main party still
    # follows the DM context.
    session.set_user_subgroup_id(side_player.id, "beta", actor_id=dm.id)
    session.set_subgroup_map_context("beta", "world", actor_id=dm.id)
    session.fog_maps = {"poi-prison": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_toggle(
            {"map_ctx": "poi-prison", "enabled": True},
            session,
            dm,
        )
    )

    recipients = {uid for _, uid, _ in sent}
    assert dm.id in recipients
    assert main_player.id in recipients
    assert side_player.id not in recipients


def test_fog_maps_persist_across_restore_and_stay_isolated_per_context():
    session = Session(id="fog-sync-5")
    session.name = "Fog Restore"
    session.player_invite = "player-code"
    session.viewer_invite = "viewer-code"
    session.created_at = 123.0
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "poi-a"
    session.pois["poi-a"] = POI(id="poi-a", x=0, y=0, name="A", map_context="world")
    session.pois["poi-b"] = POI(id="poi-b", x=1, y=1, name="B", map_context="world")
    session.set_user_subgroup_id(player.id, "alpha", actor_id=dm.id)
    session.set_subgroup_map_context("alpha", "poi-a", actor_id=dm.id)
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "1000000000000000"},
        "poi-a": {"enabled": True, "cols": 4, "rows": 4, "cells": "0100000000000000"},
        "poi-b": {"enabled": True, "cols": 4, "rows": 4, "cells": "0010000000000000"},
    }

    persisted = extract_persistable_campaign_state(session)
    data = {
        "id": session.id,
        "name": session.name,
        "dm_name": dm.name,
        "player_invite": session.player_invite,
        "viewer_invite": session.viewer_invite,
        "created_at": session.created_at,
        "map_image_url": None,
        "dm_map_context": session.dm_map_context,
        "dm_current_map_url": None,
        "dm_id": dm.id,
        "tokens": [],
        "players": [{"id": player.id, "name": player.name, "role": player.role}],
        "pois": [poi.to_dict(include_dm_notes=True) for poi in session.pois.values()],
        "logs": [],
        **persisted,
    }

    restored, _ = restore_session_from_db(data)
    assert restored.fog_maps["world"]["cells"][0] == "1"
    assert restored.fog_maps["poi-a"]["cells"][1] == "1"
    assert restored.fog_maps["poi-b"]["cells"][2] == "1"
    assert restored.fog_maps["poi-a"]["cells"][2] == "0"
    assert restored.fog_maps["poi-b"]["cells"][1] == "0"

    dm_view = restored.to_state_dict_for_role("dm", dm.id)
    assert "world" in dm_view["fog_maps"]
    assert "poi-a" in dm_view["fog_maps"]
    assert "poi-b" in dm_view["fog_maps"]
