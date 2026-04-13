import pytest

from server.session import Session, User, assistant_dm_has_scope
from server.handlers import content as content_handlers
from server.handlers import narration as narration_handlers
from server.handlers import map_editor as map_editor_handlers


@pytest.mark.anyio
async def test_dm_can_assign_assistant_dm_scopes_and_role(monkeypatch):
    session = Session(id="ASDM1", dm_id="dm1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Alex", role="player")
    session.users = {dm.id: dm, player.id: player}

    events = []

    async def _broadcast(_sid, msg, **_kwargs):
        events.append(msg)

    async def _save(_session):
        return True

    monkeypatch.setattr(content_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(content_handlers, "save_campaign_async", _save)

    await content_handlers.handle_assistant_dm_permissions_set(
        {
            "user_id": player.id,
            "enabled": True,
            "scopes": ["maps.fog", "narration.broadcast"],
            "map_contexts": ["world"],
            "token_ids": [],
        },
        session,
        dm,
    )

    assert player.role == "assistant_dm"
    assert assistant_dm_has_scope(session, player, "maps.fog", map_ctx="world")
    assert not assistant_dm_has_scope(session, player, "maps.fog", map_ctx="dungeon")
    assert events and events[-1]["type"] == "assistant_dm_permissions_sync"


@pytest.mark.anyio
async def test_narration_requires_scope_for_assistant_dm(monkeypatch):
    session = Session(id="ASDM2", dm_id="dm1")
    dm = User(id="dm1", name="DM", role="dm")
    assistant = User(id="a1", name="Aria", role="assistant_dm")
    session.users = {dm.id: dm, assistant.id: assistant}
    session.world_state = {
        "assistant_dm": {
            "users": {
                assistant.id: {
                    "enabled": True,
                    "scopes": ["narration.broadcast"],
                    "map_contexts": [],
                    "token_ids": [],
                }
            }
        }
    }

    sent = []

    async def _broadcast(_sid, msg, **_kwargs):
        sent.append(msg)

    async def _fake_tts(**_kwargs):
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "test"}

    monkeypatch.setattr(narration_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(narration_handlers, "_generate_tts", _fake_tts)

    await narration_handlers.handle_narration_speak({"text": "Hello"}, session, assistant)
    assert sent and sent[-1]["type"] == "narration_speak"


@pytest.mark.anyio
async def test_fog_paint_enforces_map_scope(monkeypatch):
    session = Session(id="ASDM3", dm_id="dm1")
    dm = User(id="dm1", name="DM", role="dm")
    assistant = User(id="a1", name="Aria", role="assistant_dm")
    session.users = {dm.id: dm, assistant.id: assistant}
    session.fog_maps = {"world": {"enabled": True, "cols": 64, "rows": 64, "cells": "0" * (64 * 64)}}
    session.world_state = {
        "assistant_dm": {
            "users": {
                assistant.id: {
                    "enabled": True,
                    "scopes": ["maps.fog"],
                    "map_contexts": ["world"],
                    "token_ids": [],
                }
            }
        }
    }

    updates = []

    async def _broadcast(_sid, msg, **_kwargs):
        updates.append(msg)

    async def _save(_session):
        return True

    monkeypatch.setattr(map_editor_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(map_editor_handlers, "save_campaign_async", _save)

    await map_editor_handlers.handle_fog_paint({"map_ctx": "world", "cells": [1, 2], "reveal": True}, session, assistant)
    assert updates and updates[-1]["type"] == "fog_update"

    updates.clear()
    await map_editor_handlers.handle_fog_paint({"map_ctx": "other", "cells": [1], "reveal": True}, session, assistant)
    assert updates == []


def test_role_normalization_accepts_assistant_dm():
    user = User(id="u1", name="Helper", role="ASSISTANT_DM")
    assert user.role == "assistant_dm"
