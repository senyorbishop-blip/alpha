import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.session import POI, Session, Token, User
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


def test_fog_broadcast_reaches_all_participants_even_when_visibility_metadata_lags(monkeypatch):
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
    assert player_world.id in recipients


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
    assert side_player.id in recipients


def test_fog_broadcast_includes_player_with_token_presence_when_subgroup_context_is_stale(monkeypatch):
    session = Session(id="fog-sync-token-presence")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "poi-prison"
    session.pois["poi-prison"] = POI(id="poi-prison", x=0, y=0, name="Prison", map_context="world")
    # Simulate stale split-party metadata (player still marked world) even
    # though their live token is already on the DM scene map.
    session.set_user_subgroup_id(player.id, "alpha", actor_id=dm.id)
    session.set_subgroup_map_context("alpha", "world", actor_id=dm.id)
    session.tokens["tok-player"] = Token(
        id="tok-player",
        name="Player",
        x=0,
        y=0,
        width=64,
        height=64,
        color="#ffffff",
        shape="circle",
        owner_id=player.id,
        map_context="poi-prison",
    )
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
    assert player.id in recipients


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


def test_local_map_enter_includes_destination_fog_snapshot(monkeypatch):
    session = Session(id="fog-sync-nav")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.pois["poi-keep"] = POI(
        id="poi-keep",
        x=0,
        y=0,
        name="Keep",
        map_context="world",
        local_map_url="/static/maps/keep.png",
    )
    session.fog_maps = {
        "poi-keep": {"enabled": True, "cols": 4, "rows": 4, "cells": "1010000000000000"},
    }

    broadcasts = []
    sent = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(broadcast=_broadcast, send_to=_send_to))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_local_map_nav(
            {
                "poi_id": "poi-keep",
                "poi_name": "Keep",
                "map_url": "/static/maps/keep.png",
                "dm_map_context": "poi-keep",
            },
            session,
            dm,
        )
    )

    assert session.dm_map_context == "poi-keep"
    assert broadcasts, "players should receive the local-map navigation broadcast"
    nav_payload = broadcasts[0][1]["payload"]
    assert broadcasts[0][1]["type"] == "local_map_enter"
    assert nav_payload["map_ctx"] == "poi-keep"
    assert nav_payload["fog_enabled"] is True
    assert nav_payload["fog_cols"] == 4
    assert nav_payload["fog_rows"] == 4
    assert nav_payload["fog_cells"] == "1010000000000000"
    assert sent and sent[0][2]["payload"]["fog_cells"] == "1010000000000000"


def test_client_fog_update_promotes_stale_entry_to_enabled():
    module_src = open("client/static/js/render/fog.js", encoding="utf-8").read()
    play_src = open("client/templates/play.html", encoding="utf-8").read()

    assert "entry.enabled = true;" in module_src
    assert "entry.enabled = true;" in play_src
    assert "if (p.map_ctx !== undefined) fogApplyState(p);" in play_src


def test_map_grid_resize_rescales_tokens_props_and_syncs(monkeypatch):
    session = Session(id="grid-sync-1")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.map_settings = {"world": {"grid": {"size_px": 64}}}
    session.tokens["tok-1"] = Token(
        id="tok-1", name="Ogre", x=128, y=64, width=128, height=128,
        color="#fff", shape="circle", owner_id=None, map_context="world",
    )
    session.tokens["tok-local"] = Token(
        id="tok-local", name="Crypt Bat", x=128, y=64, width=64, height=64,
        color="#fff", shape="circle", owner_id=None, map_context="poi-crypt",
    )
    session.editor_props = {
        "world": [{"id": "prop-1", "kind": "crate", "x": 192, "y": 64, "w": 2, "h": 1}],
        "poi-crypt": [{"id": "prop-2", "kind": "crate", "x": 192, "y": 64, "w": 1, "h": 1}],
    }

    sent = []
    token_sync_calls = []

    class _Manager:
        async def broadcast(self, session_id, message):
            sent.append(("broadcast", session_id, None, message))

        async def send_to(self, session_id, user_id, message):
            sent.append(("send_to", session_id, user_id, message))

    async def _save_campaign_async(_session):
        return True

    async def _token_sync(_session):
        token_sync_calls.append(_session.id)

    monkeypatch.setattr(map_editor, "manager", _Manager())
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)
    monkeypatch.setattr(map_editor, "_broadcast_token_state_sync", _token_sync)

    asyncio.run(
        map_editor.handle_map_settings_save(
            {"map_context": "world", "settings": {"grid": {"size_px": 32}}},
            session,
            dm,
        )
    )

    assert session.map_settings["world"]["grid"]["size_px"] == 32
    assert session.tokens["tok-1"].x == 64
    assert session.tokens["tok-1"].y == 32
    assert session.tokens["tok-1"].width == 64
    assert session.tokens["tok-1"].height == 64
    assert session.tokens["tok-local"].x == 128, "other map token must not be rescaled"
    assert session.editor_props["world"][0]["x"] == 96
    assert session.editor_props["world"][0]["y"] == 32
    assert session.editor_props["world"][0]["w"] == 2, "prop footprint squares stay stable"
    assert session.editor_props["poi-crypt"][0]["x"] == 192, "other map prop must not be rescaled"
    assert token_sync_calls == [session.id]
    message_types = [entry[3].get("type") for entry in sent]
    assert "map_settings_sync" in message_types
    assert "editor_props_sync" in message_types


def test_client_fog_update_promotes_alias_context_and_repaints_active_map():
    src = open("client/static/js/render/fog.js", encoding="utf-8").read()
    body = src[src.index("function fogApplyUpdate"):src.index("window.AppFog =")]
    assert "p.map_ctx || p.map_context || p.dm_map_context" in body
    assert "entry.enabled = true" in body
    assert "fogLoadMap(state, env, activeCtx)" in body
