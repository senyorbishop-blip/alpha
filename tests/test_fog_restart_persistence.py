"""Restart/reload fog persistence guardrails.

These tests exercise the full DB serialization path (``_safe_fog_json`` ->
JSON -> ``normalize_persisted_campaign_data`` -> ``restore_session_from_db``)
to prove that revealed/hidden fog state, ``revision`` and ``updated_at`` all
survive a server restart, including on maps larger than the default 64x64 grid.
"""
import json

from server.db import _safe_fog_json
from server.persistence_schema import (
    extract_persistable_campaign_state,
    normalize_persisted_campaign_data,
)
from server.restore import restore_session_from_db
from server.session import Session, User, _sessions
from server.sessions.service import session_fog_debug_response


def _restore_through_db(session):
    """Round-trip a session's fog_maps through the real DB serializer."""
    persisted = extract_persistable_campaign_state(session)
    # Emulate the campaigns-row write/read for fog_maps specifically.
    fog_json = _safe_fog_json(persisted["fog_maps"])
    persisted["fog_maps"] = json.loads(fog_json)
    data = {
        "id": session.id,
        "name": getattr(session, "name", "Campaign"),
        "dm_name": "DM",
        "player_invite": session.player_invite,
        "viewer_invite": session.viewer_invite,
        "created_at": getattr(session, "created_at", 0.0),
        "map_image_url": None,
        "dm_map_context": getattr(session, "dm_map_context", "world"),
        "dm_current_map_url": None,
        "dm_id": getattr(session, "dm_id", "dm"),
        "tokens": [],
        "players": [],
        "pois": [],
        "logs": [],
        **normalize_persisted_campaign_data(persisted),
    }
    restored, _ = restore_session_from_db(data)
    return restored


def test_fog_revision_and_updated_at_survive_restart():
    session = Session(id="fog-restart-rev")
    session.fog_maps = {
        "world": {
            "enabled": True,
            "cols": 4,
            "rows": 4,
            "cells": "1000000000000001",
            "revision": 7,
            "updated_at": 1234.5,
            "map_context": "world",
        }
    }
    restored = _restore_through_db(session)
    entry = restored.to_state_dict()["fog_maps"]["world"]
    assert entry["revision"] == 7
    assert entry["updated_at"] == 1234.5
    assert entry["enabled"] is True


def test_revealed_and_hidden_cells_survive_restart():
    session = Session(id="fog-restart-cells")
    session.fog_maps = {
        "world": {
            "enabled": True,
            "cols": 4,
            "rows": 4,
            # cell 0 + 15 revealed, the rest hidden
            "cells": "1000000000000001",
            "revision": 1,
        }
    }
    restored = _restore_through_db(session)
    cells = restored.to_state_dict()["fog_maps"]["world"]["cells"]
    assert cells[0] == "1"  # revealed stays revealed
    assert cells[15] == "1"
    assert cells[1] == "0"  # hidden stays hidden
    assert cells.count("1") == 2


def test_large_map_fog_cells_are_not_truncated_on_restart():
    session = Session(id="fog-restart-big")
    cols = rows = 100  # 10000 cells, well past the legacy 4096 cap
    cells = ["0"] * (cols * rows)
    cells[9999] = "1"  # reveal the very last cell
    session.fog_maps = {
        "world": {
            "enabled": True,
            "cols": cols,
            "rows": rows,
            "cells": "".join(cells),
            "revision": 3,
        }
    }
    restored = _restore_through_db(session)
    entry = restored.to_state_dict()["fog_maps"]["world"]
    assert len(entry["cells"]) == cols * rows
    assert entry["cells"][9999] == "1"


def test_fog_debug_endpoint_is_dm_only_and_summarizes_maps():
    session = Session(id="fog-debug-endpoint")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="pl-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_map_context = "world"
    session.fog_maps = {
        "world": {
            "enabled": True,
            "cols": 4,
            "rows": 4,
            "cells": "1000000000000001",
            "revision": 4,
            "updated_at": 99.0,
        }
    }
    _sessions[session.id] = session
    try:
        # Non-DM is forbidden.
        denied = session_fog_debug_response(session.id, player.id)
        assert denied.status_code == 403

        # Missing/unknown user is forbidden.
        anon = session_fog_debug_response(session.id, "")
        assert anon.status_code == 403

        ok = session_fog_debug_response(session.id, dm.id)
        assert ok.status_code == 200
        body = json.loads(ok.body)
        assert body["keys"] == ["world"]
        assert body["active_map_context"] == "world"
        world = body["fog_maps"]["world"]
        assert world["enabled"] is True
        assert world["cols"] == 4 and world["rows"] == 4
        assert world["cells_length"] == 16
        assert world["revealed_count"] == 2
        assert world["revision"] == 4
        assert world["updated_at"] == 99.0
    finally:
        _sessions.pop(session.id, None)
