import asyncio
from types import SimpleNamespace

from server.handlers import map_editor
from server.session import Session, User


def test_fog_paint_broadcasts_to_all_clients_including_dm_sender(monkeypatch):
    session = Session(id="fog-sync-1")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.fog_maps = {
        "world": {"enabled": True, "cols": 4, "rows": 4, "cells": "0" * 16}
    }

    broadcasts = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _save_campaign_async(_session):
        return True

    monkeypatch.setattr(map_editor, "manager", SimpleNamespace(broadcast=_broadcast))
    monkeypatch.setattr(map_editor, "save_campaign_async", _save_campaign_async)

    asyncio.run(
        map_editor.handle_fog_paint(
            {"map_ctx": "world", "reveal": True, "cells": [0, 5, 10]},
            session,
            dm,
        )
    )

    assert broadcasts, "fog paint should broadcast updates to connected clients"
    _session_id, message, exclude_user = broadcasts[-1]
    assert message["type"] == "fog_update"
    assert message["payload"]["map_ctx"] == "world"
    assert message["payload"]["cells"] == [0, 5, 10]
    assert exclude_user is None, "DM sender must still receive fog_update for multi-tab DM sync"
