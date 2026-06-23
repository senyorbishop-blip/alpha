"""Tests for PR 6 — Fog visibility revision hardening.

Covers the parts of the fog/visibility revision contract that aren't already
exercised by ``test_fog_sync.py`` / ``test_combat_fog_sync.py`` /
``test_reconnect_snapshot_recovery.py``:

- fog_state/fog_update/local_map_enter/local_map_exit payloads now carry a
  ``source`` field, ``visibility_revision``, and ``map_mode``.
- world vs local fog stays independent (toggling/painting one map context
  never touches another context's revision or cells).
- the authoritative snapshot's fog block reports the correct per-map-context
  revision/visibility_revision and never leaks another map's fog as
  "current".
- fog changes that hide/reveal a token bump the session-wide
  visibility_revision (token/combat resync alignment).
"""
import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.session import POI, Session, Token, User


def _wire_manager(monkeypatch, sent=None, broadcasts=None):
    sent = sent if sent is not None else []
    broadcasts = broadcasts if broadcasts is not None else []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to, broadcast=_broadcast))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)
    return sent, broadcasts


def test_fog_toggle_payload_includes_source_and_visibility_revision(monkeypatch):
    session = Session(id="hardening-1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.fog_maps = {"world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16}}
    sent, _ = _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_fog_toggle({"map_ctx": "world", "enabled": True}, session, dm))

    payload = sent[-1][2]["payload"]
    assert payload["source"] == "fog_state"
    assert payload["map_mode"] == "world"
    assert "visibility_revision" in payload


def test_fog_paint_payload_includes_source_and_visibility_revision(monkeypatch):
    session = Session(id="hardening-2")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}
    sent, _ = _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_fog_paint({"map_ctx": "world", "reveal": True, "cells": [0]}, session, dm))

    payload = sent[-1][2]["payload"]
    assert payload["source"] == "fog_update"
    assert payload["map_mode"] == "world"
    assert "visibility_revision" in payload


def test_fog_toggle_bumps_only_target_context_revision(monkeypatch):
    """Toggling the local map's fog must not touch the world map's revision/cells."""
    session = Session(id="hardening-3")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.pois["poi-crypt"] = POI(id="poi-crypt", x=0, y=0, name="Crypt", map_context="world")
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "1" * 16, "revision": 5},
        "poi-crypt": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16, "revision": 2},
    }
    _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_fog_toggle({"map_ctx": "poi-crypt", "enabled": True}, session, dm))

    assert session.fog_maps["poi-crypt"]["revision"] == 3
    assert session.fog_maps["world"]["revision"] == 5
    assert session.fog_maps["world"]["cells"] == "1" * 16


def test_local_map_enter_fog_payload_carries_source_local_map_enter(monkeypatch):
    session = Session(id="hardening-4")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.pois["poi-keep"] = POI(
        id="poi-keep", x=0, y=0, name="Keep", map_context="world", local_map_url="/static/maps/keep.png",
    )
    session.fog_maps = {"poi-keep": {"enabled": True, "cols": 4, "rows": 4, "cells": "1" + "0" * 15}}
    _, broadcasts = _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_local_map_nav(
        {"poi_id": "poi-keep", "poi_name": "Keep", "map_url": "/static/maps/keep.png", "dm_map_context": "poi-keep"},
        session, dm,
    ))

    nav_payload = broadcasts[0][1]["payload"]
    assert nav_payload["source"] == "local_map_enter"
    assert nav_payload["map_mode"] == "local"


def test_local_map_exit_fog_payload_restores_world_with_source(monkeypatch):
    session = Session(id="hardening-5")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "poi-keep"
    session.pois["poi-keep"] = POI(id="poi-keep", x=0, y=0, name="Keep", map_context="world")
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "1" * 16},
        "poi-keep": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16},
    }
    _, broadcasts = _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_local_map_nav({"dm_map_context": "world"}, session, dm))

    nav_payload = broadcasts[0][1]["payload"]
    assert nav_payload["source"] == "local_map_exit"
    assert nav_payload["map_mode"] == "world"
    assert nav_payload["fog_cells"] == "1" * 16


def test_fog_toggle_hiding_npc_bumps_visibility_revision(monkeypatch):
    """Disabling fog reveal that hides a previously-visible NPC must bump
    session.visibility_revision so token/combat resync picks up the change."""
    session = Session(id="hardening-6")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "1" * 16}}
    npc = Token(
        id="npc-1", name="Goblin", x=0, y=0, width=20, height=20, color="#0f0",
        shape="circle", owner_id=None, token_type="npc", map_context="world",
    )
    session.tokens[npc.id] = npc
    before = session.visibility_revision
    _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_fog_paint({"map_ctx": "world", "reveal": False, "cells": list(range(16))}, session, dm))

    assert session.visibility_revision > before


def test_authoritative_snapshot_fog_block_matches_current_map_context_not_other_map():
    session = Session(id="hardening-7")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_map_context = "poi-keep"
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16, "revision": 9},
        "poi-keep": {"enabled": True, "cols": 4, "rows": 4, "cells": "1" * 16, "revision": 2},
    }

    msg = session.to_authoritative_snapshot_for_role(dm.role, dm.id, source="ws_connect")
    fog = msg["payload"]["fog"]

    assert fog["map_context"] == "poi-keep"
    assert fog["revision"] == 2
    assert fog["source"] == "reconnect"
    assert fog["explored"]["revealed_cells"] == 16


def test_authoritative_snapshot_fog_source_is_authoritative_snapshot_for_manual_refresh():
    session = Session(id="hardening-8")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16, "revision": 1}}

    msg = session.to_authoritative_snapshot_for_role(dm.role, dm.id, source="request_state")
    assert msg["payload"]["fog"]["source"] == "authoritative_snapshot"


def test_authoritative_snapshot_fog_block_has_los_placeholders():
    session = Session(id="hardening-9")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}

    msg = session.to_authoritative_snapshot_for_role(dm.role, dm.id, source="ws_connect")
    fog = msg["payload"]["fog"]

    assert fog["currently_visible"] is None
    assert fog["unseen"] is None
    assert fog["visibility_source"] == "manual_fog"
    assert fog["wall_revision"] == 0
    assert fog["door_revision"] == 0


def test_state_dict_includes_fog_source_for_dm_and_player():
    session = Session(id="hardening-10")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "1" * 16}}

    dm_state = session.to_state_dict_for_role("dm", dm.id)
    player_state = session.to_state_dict_for_role("player", player.id)

    assert dm_state["fog_source"] == "state_sync"
    assert player_state["fog_source"] == "state_sync"
