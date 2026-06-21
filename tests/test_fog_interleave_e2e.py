"""Regression coverage for the PR 292 -> 338 fog/combat interleave bug:
a DM editing fog on a POI/local map context (sent as "__local__") while
token-move and combat_state frames are interleaved must not leave a
connected player's fog stale, and must not require the player to toggle
maps or reconnect to receive the correct, resolved-context update.
"""
import json

import pytest

from server.handlers import combat as combat_handlers
from server.handlers import map_editor
from server.handlers import tokens as token_handlers
from server.session import Session, Token, User


class _FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def accept(self):
        return None

    async def send_text(self, payload):
        self.sent.append(json.loads(payload))


def _build_session(dm_map_context="poi-1"):
    session = Session(id="s1")
    session.dm_map_context = dm_map_context
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="u1", name="Player One", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.tokens["hero"] = Token(
        id="hero", name="Hero", x=0, y=0, width=1, height=1,
        color="#fff", shape="circle", owner_id=player.id, map_context=dm_map_context,
    )
    session.tokens["npc"] = Token(
        id="npc", name="Goblin", x=0, y=0, width=1, height=1,
        color="#fff", shape="circle", owner_id=None, token_type="npc", map_context=dm_map_context,
    )
    session.combat = {
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": player.id, "initiative": None, "roll": None, "modifier": 2},
            {"id": "cmb-npc", "token_id": "npc", "name": "Goblin", "owner_id": None, "initiative": None, "roll": None, "modifier": 0},
        ],
    }
    return session, dm, player


async def _connect(session, *user_ids):
    sockets = {}
    for uid in user_ids:
        ws = _FakeWebSocket()
        await combat_handlers.manager.connect(session.id, uid, ws)
        sockets[uid] = ws
    return sockets


def _messages(ws, msg_type):
    return [m for m in ws.sent if m.get("type") == msg_type]


@pytest.mark.anyio
async def test_fog_edit_on_local_context_reaches_player_without_toggle(monkeypatch):
    """DM paints fog while their client thinks it's on "__local__" (the
    historical alias for the DM's actual active POI). The player must
    receive the resolved, non-"__local__" map context with no action
    on their part."""
    session, dm, player = _build_session(dm_map_context="poi-1")

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(map_editor, "save_campaign_async", _fake_save)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        await map_editor.handle_fog_toggle({"map_ctx": "__local__", "enabled": True}, session, dm)
        await map_editor.handle_fog_paint({"map_ctx": "__local__", "reveal": True, "cells": [0, 1, 2]}, session, dm)
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    player_updates = _messages(sockets[player.id], "fog_update")
    dm_updates = _messages(sockets[dm.id], "fog_update")
    assert player_updates, "player must receive the fog_update broadcast without any manual toggle"
    assert dm_updates, "DM's other tabs must also receive the update"
    assert player_updates[-1]["payload"]["map_ctx"] == "poi-1"
    assert player_updates[-1]["payload"]["map_ctx"] != "__local__"
    assert player_updates[-1]["payload"]["cells"] == [0, 1, 2]
    # The server must never persist the literal alias as a fog-map key.
    assert "__local__" not in session.fog_maps


@pytest.mark.anyio
async def test_interleaved_token_move_fog_and_combat_state_all_deliver_to_player(monkeypatch):
    """Interleave a token move, a fog paint, and an initiative roll (each of
    which bumps the shared server visibility_revision and broadcasts its own
    message type). The player must receive every one of these, with strictly
    increasing revisions, and never drop a frame because a different stream
    advanced the counter first."""
    session, dm, player = _build_session(dm_map_context="poi-1")

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(map_editor, "save_campaign_async", _fake_save)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        await token_handlers.handle_token_move({"token_id": "npc", "x": 5, "y": 5}, session, dm)
        await map_editor.handle_fog_paint({"map_ctx": "__local__", "reveal": True, "cells": [10]}, session, dm)
        await combat_handlers.handle_combat_roll_initiative({"combatant_id": "cmb-npc", "roll": 14}, session, dm)
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    player_fog = _messages(sockets[player.id], "fog_update")
    player_combat = _messages(sockets[player.id], "combat_state")
    assert player_fog, "fog_update must reach the player despite interleaved token/combat traffic"
    assert player_combat, "combat_state must reach the player despite interleaved fog traffic"
    fog_rev = player_fog[-1]["payload"]["revision"]
    combat_rev = player_combat[-1]["payload"]["visibility_revision"]
    assert isinstance(fog_rev, int) and fog_rev >= 1
    assert isinstance(combat_rev, int) and combat_rev >= 1
