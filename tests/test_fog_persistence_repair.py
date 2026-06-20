import asyncio

from server.session import Session, User, Token, normalize_map_context_from_payload
from server.handlers import map_editor


def _dm():
    return User(id="dm", name="DM", role="dm")


def test_map_context_aliases_resolve_to_same_fog_entry(monkeypatch):
    session = Session(id="fog-alias")
    session.dm_map_context = "crypt"
    async def noop_async(*args, **kwargs):
        return None
    monkeypatch.setattr(map_editor, "save_campaign_async", noop_async)
    sent = []
    async def fake_broadcast(*args, **kwargs):
        sent.append(args[1])
    monkeypatch.setattr(map_editor.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(map_editor, "_broadcast_token_state_sync", noop_async)
    monkeypatch.setattr(map_editor, "run_combat_fog_sync", noop_async)

    for alias in ("map_ctx", "map_context", "dm_map_context"):
        asyncio.run(map_editor.handle_fog_toggle({alias: "crypt", "enabled": True}, session, _dm()))

    assert set(session.fog_maps) == {"crypt"}
    assert session.fog_maps["crypt"]["enabled"] is True
    assert session.fog_maps["crypt"]["revision"] == 3
    assert all(msg["payload"]["map_ctx"] == "crypt" for msg in sent)
    assert normalize_map_context_from_payload({"currentMap": "world"}) == "world"


def test_fog_toggle_persists_full_hidden_grid_before_paint(monkeypatch):
    session = Session(id="fog-toggle")
    saved = []
    async def save_async(s):
        saved.append(dict(s.fog_maps))
    async def noop_async(*args, **kwargs):
        return None
    monkeypatch.setattr(map_editor, "save_campaign_async", save_async)
    monkeypatch.setattr(map_editor.manager, "broadcast", noop_async)
    monkeypatch.setattr(map_editor, "_broadcast_token_state_sync", noop_async)
    monkeypatch.setattr(map_editor, "run_combat_fog_sync", noop_async)

    asyncio.run(map_editor.handle_fog_toggle({"map_context": "world", "enabled": True}, session, _dm()))

    entry = session.fog_maps["world"]
    assert entry["enabled"] is True
    assert entry["cells"] == "0" * (64 * 64)
    assert entry["revision"] == 1
    assert saved and saved[-1]["world"]["cells"] == entry["cells"]


def test_fog_paint_persists_revealed_cells_and_revision(monkeypatch):
    session = Session(id="fog-paint")
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}
    async def noop_async(*args, **kwargs):
        return None
    monkeypatch.setattr(map_editor, "save_campaign_async", noop_async)
    monkeypatch.setattr(map_editor.manager, "broadcast", noop_async)
    monkeypatch.setattr(map_editor, "_broadcast_token_state_sync", noop_async)
    monkeypatch.setattr(map_editor, "run_combat_fog_sync", noop_async)

    asyncio.run(map_editor.handle_fog_paint({"map_ctx": "world", "reveal": True, "cells": [0, 5, 15]}, session, _dm()))

    entry = session.fog_maps["world"]
    assert entry["cells"] == "1000010000000001"
    assert entry["revision"] == 1


def test_player_state_sync_has_active_fog_but_not_hidden_or_fogged_npcs():
    session = Session(id="fog-player")
    player = User(id="p1", name="P", role="player")
    session.users[player.id] = player
    session.set_subgroup_map_context("main", "world")
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}}
    session.tokens["hidden"] = Token(id="hidden", name="Hidden", x=0, y=0, width=40, height=40, color="#000", shape="circle", owner_id=None, hidden=True, map_context="world", token_type="monster")
    session.tokens["fogged"] = Token(id="fogged", name="Fogged", x=0, y=0, width=40, height=40, color="#000", shape="circle", owner_id=None, map_context="world", token_type="monster")

    state = session.to_state_dict_for_role("player", player.id)

    assert state["fog_maps"]["world"]["enabled"] is True
    assert state["fog_maps"]["world"]["cells"] == "0" * 16
    assert "hidden" not in state["tokens"]
    assert "fogged" not in state["tokens"]
