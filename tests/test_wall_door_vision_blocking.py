"""Tests for PR 7 — Wall and door vision blocking hardening.

Covers the server-authoritative LOS engine (server/visibility.py) and its
wiring into token visibility, combat visibility, fog reveal, and the
secret-door filtering choke point (server/session.py::filter_editor_props_for_role).
"""
import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.handlers.combat import is_token_visible_to_party, sync_combat_visibility
from server.session import Session, Token, User, filter_editor_props_for_role
from server.visibility import (
    apply_los_fog_reveal,
    has_los,
    player_vision_sources,
    token_blocked_by_los,
    vision_blockers,
)


def _viewer_token(**kwargs):
    base = dict(
        id="pc-1", name="Hero", x=0, y=0, width=50, height=50, color="#fff", shape="circle",
        owner_id="user-1", token_type="player", vision_enabled=True, vision_radius=30,
    )
    base.update(kwargs)
    return Token(**base)


def _npc_token(**kwargs):
    base = dict(
        id="npc-1", name="Goblin", x=200, y=0, width=50, height=50, color="#f00", shape="circle",
        owner_id=None, token_type="monster",
    )
    base.update(kwargs)
    return Token(**base)


# --- Wall LOS -----------------------------------------------------------

def test_wall_blocks_los_between_two_points():
    session = Session(id="s1")
    session.editor_walls = {"world": [{"x1": 100, "y1": -200, "x2": 100, "y2": 200}]}
    blockers = vision_blockers(session, "world")
    assert not has_los(0, 0, 200, 0, blockers)


def test_no_wall_allows_los():
    session = Session(id="s1")
    session.editor_walls = {"world": []}
    blockers = vision_blockers(session, "world")
    assert has_los(0, 0, 200, 0, blockers)


# --- Door LOS -------------------------------------------------------------

def test_closed_door_blocks_los():
    session = Session(id="s1")
    session.editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 100, "y": 0, "facing": "v",
        "state": "closed", "locked": False, "blocks_vision": True,
    }]}
    blockers = vision_blockers(session, "world")
    assert not has_los(0, 0, 200, 0, blockers)


def test_open_door_allows_los():
    session = Session(id="s1")
    session.editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 100, "y": 0, "facing": "v",
        "state": "open", "locked": False, "blocks_vision": True,
    }]}
    blockers = vision_blockers(session, "world")
    assert has_los(0, 0, 200, 0, blockers)


# --- Secret door ----------------------------------------------------------

def test_secret_undiscovered_door_still_blocks_los_server_side():
    session = Session(id="s1")
    session.editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 100, "y": 0, "facing": "v",
        "state": "closed", "locked": False, "blocks_vision": True,
        "secret": True, "revealed": False,
    }]}
    blockers = vision_blockers(session, "world")
    assert not has_los(0, 0, 200, 0, blockers)


def test_secret_undiscovered_door_excluded_from_player_prop_payload():
    editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 100, "y": 0, "facing": "v",
        "state": "closed", "locked": False, "blocks_vision": True,
        "secret": True, "revealed": False,
    }]}
    player_view = filter_editor_props_for_role(editor_props, "player")
    assert player_view["world"] == []

    dm_view = filter_editor_props_for_role(editor_props, "dm")
    assert len(dm_view["world"]) == 1
    assert dm_view["world"][0]["secret"] is True


def test_revealed_secret_door_visible_to_players():
    editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 100, "y": 0, "facing": "v",
        "state": "closed", "locked": False, "blocks_vision": True,
        "secret": True, "revealed": True,
    }]}
    player_view = filter_editor_props_for_role(editor_props, "player")
    assert len(player_view["world"]) == 1
    # secret/revealed metadata itself is stripped even once revealed; only
    # geometry/state is exposed.
    assert "secret" not in player_view["world"][0]
    assert "revealed" not in player_view["world"][0]


# --- Token visibility through LOS -----------------------------------------

def test_npc_blocked_by_wall_is_not_visible_to_party():
    session = Session(id="s1")
    viewer = _viewer_token()
    npc = _npc_token()
    session.tokens[viewer.id] = viewer
    session.tokens[npc.id] = npc
    session.editor_walls = {"world": [{"x1": 100, "y1": -200, "x2": 100, "y2": 200}]}
    assert token_blocked_by_los(session, npc) is True
    assert is_token_visible_to_party(session, npc) is False


def test_npc_in_los_and_range_is_visible_to_party():
    session = Session(id="s1")
    viewer = _viewer_token()
    npc = _npc_token(x=50, y=0)
    session.tokens[viewer.id] = viewer
    session.tokens[npc.id] = npc
    session.editor_walls = {"world": [{"x1": 500, "y1": -200, "x2": 500, "y2": 200}]}
    assert token_blocked_by_los(session, npc) is False
    assert is_token_visible_to_party(session, npc) is True


def test_los_fails_open_with_no_blockers_or_sources():
    session = Session(id="s1")
    npc = _npc_token()
    session.tokens[npc.id] = npc
    # No walls/doors at all -> fails open (not blocked).
    assert token_blocked_by_los(session, npc) is False


def test_player_vision_sources_excludes_hidden_and_staged_tokens():
    session = Session(id="s1")
    hidden_pc = _viewer_token(id="pc-hidden", hidden=True)
    staged_pc = _viewer_token(id="pc-staged", staged=True)
    visible_pc = _viewer_token(id="pc-visible")
    session.tokens[hidden_pc.id] = hidden_pc
    session.tokens[staged_pc.id] = staged_pc
    session.tokens[visible_pc.id] = visible_pc
    sources = player_vision_sources(session, "world")
    assert {s["token_id"] for s in sources} == {"pc-visible"}


# --- Fog reveal via LOS ----------------------------------------------------

def test_apply_los_fog_reveal_only_adds_bits():
    session = Session(id="s1")
    viewer = _viewer_token(x=0, y=0, vision_radius=500)
    session.tokens[viewer.id] = viewer
    session.editor_walls = {"world": []}
    session.map_settings = {"world": {"width": 400, "height": 400}}
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}
    changed = apply_los_fog_reveal(session, "world")
    assert changed is True
    cells = session.fog_maps["world"]["cells"]
    assert "1" in cells
    # Re-running with the same geometry must never clear a bit that was set.
    apply_los_fog_reveal(session, "world")
    assert all(c == "1" for c in cells if c == "1")


def test_apply_los_fog_reveal_blocked_by_wall_does_not_reveal_far_side():
    session = Session(id="s1")
    viewer = _viewer_token(x=-150, y=0, vision_radius=500)
    session.tokens[viewer.id] = viewer
    session.editor_walls = {"world": [{"x1": 0, "y1": -200, "x2": 0, "y2": 200}]}
    session.map_settings = {"world": {"width": 400, "height": 400}}
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}
    apply_los_fog_reveal(session, "world")
    cells = session.fog_maps["world"]["cells"]
    cols = 4
    # The two right-most columns (far side of the wall from the viewer) must
    # stay unrevealed.
    for row in range(4):
        for col in (2, 3):
            assert cells[row * cols + col] == "0"


def test_apply_los_fog_reveal_noop_when_fog_disabled():
    session = Session(id="s1")
    viewer = _viewer_token(vision_radius=500)
    session.tokens[viewer.id] = viewer
    session.editor_walls = {"world": []}
    session.fog_maps = {"world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16}}
    assert apply_los_fog_reveal(session, "world") is False


# --- Combat visibility alignment ------------------------------------------

def test_sync_combat_visibility_suspends_npc_blocked_by_wall():
    session = Session(id="s1")
    viewer = _viewer_token()
    npc = _npc_token()
    session.tokens[viewer.id] = viewer
    session.tokens[npc.id] = npc
    session.editor_walls = {"world": [{"x1": 100, "y1": -200, "x2": 100, "y2": 200}]}
    session.combat = {
        "active": True,
        "combatants": [{"token_id": npc.id, "id": "c1", "name": npc.name, "map_context": "world"}],
        "turn": 0,
        "suspended_combatants": [],
        "fog_suspended_combatants": [],
        "hidden_suspended_combatants": [],
    }
    result = sync_combat_visibility(session, map_context="world", reason="test")
    assert result["changed"] is True
    assert session.combat["combatants"] == []
    suspended = session.combat["suspended_combatants"]
    assert len(suspended) == 1
    assert "los" in suspended[0]["suspended_reasons"]


def test_sync_combat_visibility_restores_npc_once_wall_removed():
    session = Session(id="s1")
    viewer = _viewer_token()
    npc = _npc_token()
    session.tokens[viewer.id] = viewer
    session.tokens[npc.id] = npc
    session.editor_walls = {"world": [{"x1": 100, "y1": -200, "x2": 100, "y2": 200}]}
    session.combat = {
        "active": True,
        "combatants": [{"token_id": npc.id, "id": "c1", "name": npc.name, "map_context": "world"}],
        "turn": 0,
        "suspended_combatants": [],
        "fog_suspended_combatants": [],
        "hidden_suspended_combatants": [],
    }
    sync_combat_visibility(session, map_context="world", reason="test")
    assert session.combat["combatants"] == []

    session.editor_walls = {"world": []}
    result = sync_combat_visibility(session, map_context="world", reason="test")
    assert result["changed"] is True
    assert [c["token_id"] for c in session.combat["combatants"]] == [npc.id]
    assert session.combat["suspended_combatants"] == []


# --- Revision bumps on wall/door mutation handlers -------------------------

def _wire_manager(monkeypatch):
    sent, broadcasts = [], []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _save_campaign_async(_session):
        return True

    async def _refresh_token_state_sync(_session):
        return None

    async def _run_combat_fog_sync(_session, reason="sync", map_context=None):
        return {"changed": False}

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(send_to=_send_to, broadcast=_broadcast))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)
    monkeypatch.setattr(map_editor, "_broadcast_token_state_sync", _refresh_token_state_sync)
    monkeypatch.setattr(map_editor, "run_combat_fog_sync", _run_combat_fog_sync)
    return sent, broadcasts


def test_wall_save_bumps_wall_and_visibility_revision(monkeypatch):
    session = Session(id="s1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_editor_walls_save(
        {"map_context": "world", "walls": [{"x1": 0, "y1": 0, "x2": 100, "y2": 0}]}, session, dm,
    ))

    assert session.wall_revision == 1
    assert session.visibility_revision == 1


def test_door_toggle_bumps_door_and_visibility_revision(monkeypatch):
    session = Session(id="s1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 0, "y": 0, "facing": "v",
        "state": "closed", "locked": False, "blocks_vision": True,
    }]}
    _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_door_toggle({"map_context": "world", "prop_id": "door-1"}, session, dm))

    assert session.door_revision == 1
    assert session.visibility_revision == 1
    assert session.editor_props["world"][0]["state"] == "open"


def test_door_lock_set_bumps_door_and_visibility_revision(monkeypatch):
    session = Session(id="s1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 0, "y": 0, "facing": "v",
        "state": "open", "locked": False, "blocks_vision": True,
    }]}
    _wire_manager(monkeypatch)

    asyncio.run(map_editor.handle_door_lock_set({"map_context": "world", "prop_id": "door-1", "locked": True}, session, dm))

    assert session.door_revision == 1
    assert session.visibility_revision == 1
    assert session.editor_props["world"][0]["locked"] is True
    assert session.editor_props["world"][0]["state"] == "closed"


# --- Authoritative snapshot v2 fields --------------------------------------

def test_authoritative_snapshot_includes_wall_door_visibility_fields():
    session = Session(id="s1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.editor_props = {"world": [{
        "id": "door-1", "kind": "door", "x": 0, "y": 0, "facing": "v",
        "state": "closed", "locked": False, "blocks_vision": True,
        "secret": True, "revealed": False,
    }]}
    session.wall_revision = 3
    session.door_revision = 5

    dm_snapshot = session.to_authoritative_snapshot_for_role("dm", dm.id)["payload"]
    assert dm_snapshot["map"]["wall_revision"] == 3
    assert dm_snapshot["map"]["door_revision"] == 5
    assert dm_snapshot["fog"]["visibility_source"] == "manual_fog_plus_wall_door_los"
    assert len(dm_snapshot["map"]["doors"]) == 1

    player = User(id="p-1", name="Player", role="player")
    session.users[player.id] = player
    player_snapshot = session.to_authoritative_snapshot_for_role("player", player.id)["payload"]
    # Secret/undiscovered door must not be summarized for a player role.
    assert player_snapshot["map"]["doors"] == []
