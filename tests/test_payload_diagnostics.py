import logging

from server.payload_diagnostics import (
    PAYLOAD_WARN_BYTES,
    build_payload_size_report,
    log_payload_size_diagnostic,
    payload_byte_size,
)
from server.session import Session, Token, User


def _sample_session():
    session = Session(id="payload-test", dm_id="dm-1")
    dm = User(id="dm-1", name="Dungeon Master", role="dm")
    player = User(id="player-1", name="Player One", role="player")
    viewer = User(id="viewer-1", name="Viewer One", role="viewer")
    session.users = {u.id: u for u in (dm, player, viewer)}
    session.fog_maps = {
        "world": {
            "enabled": True,
            "cols": 8,
            "rows": 8,
            "cells": "0" * 64,
            "revision": 2,
            "updated_at": 1.0,
            "map_context": "world",
        }
    }
    session.tokens = {
        "visible-pc": Token(
            id="visible-pc",
            name="Visible Hero",
            x=1,
            y=1,
            width=1,
            height=1,
            color="#fff",
            shape="circle",
            owner_id="player-1",
            map_context="world",
            notes="public-ish player notes",
        ),
        "hidden-npc": Token(
            id="hidden-npc",
            name="SECRET_HIDDEN_TOKEN_NAME",
            x=3,
            y=3,
            width=1,
            height=1,
            color="#000",
            shape="circle",
            owner_id=None,
            hidden=True,
            token_type="monster",
            map_context="world",
            notes="PRIVATE_DM_ONLY_TOKEN_NOTES",
        ),
    }
    session.item_library_entries = [
        {"id": f"item-{idx}", "name": f"Sample Item {idx}", "description": "x" * 120}
        for idx in range(10)
    ]
    session.combat = {
        "active": True,
        "turn": 0,
        "revision": 3,
        "combatants": [
            {"id": "c1", "name": "Visible Hero", "token_id": "visible-pc", "initiative": 12, "map_context": "world"},
            {"id": "c2", "name": "SECRET_HIDDEN_TOKEN_NAME", "token_id": "hidden-npc", "initiative": 9, "map_context": "world"},
        ],
    }
    session.player_inventories = {"player-1": [{"id": "sword", "name": "Sword", "qty": 1}]}
    session.active_char_profiles = {"player-1": "profile-1"}
    session.char_profiles = {"player one": [{"id": "profile-1", "name": "Hero"}]}
    return session


def test_payload_size_calculator_for_sample_session_roles():
    report = build_payload_size_report(_sample_session())

    assert set(report["roles"]) == {"dm", "player", "viewer"}
    for role in ("dm", "player", "viewer"):
        messages = report["roles"][role]["messages"]
        assert messages["state_sync"] > 0
        assert messages["authoritative_snapshot"] > 0


def test_no_hidden_or_private_strings_in_diagnostic_logs(caplog):
    session = _sample_session()
    message = {"type": "state_sync", "payload": session.to_state_dict_for_role("dm", "dm-1")}
    size = payload_byte_size(message)

    with caplog.at_level(logging.DEBUG):
        log_payload_size_diagnostic(
            logging.getLogger("test.payload_diag"),
            session_id=session.id,
            recipient_user_id="dm-1",
            recipient_role="dm",
            message_type="state_sync",
            byte_size=size,
        )

    text = caplog.text
    assert "message_type=state_sync" in text
    assert "session_id=payload-test" in text
    assert "recipient_user_id=dm-1" in text
    assert "recipient_role=dm" in text
    assert "SECRET_HIDDEN_TOKEN_NAME" not in text
    assert "PRIVATE_DM_ONLY_TOKEN_NOTES" not in text


def test_viewer_state_payload_smaller_than_dm_payload():
    session = _sample_session()
    dm_size = payload_byte_size({"type": "state_sync", "payload": session.to_state_dict_for_role("dm", "dm-1")})
    viewer_size = payload_byte_size({"type": "state_sync", "payload": session.to_state_dict_for_role("viewer", "viewer-1")})

    assert viewer_size < dm_size


def test_payload_diagnostic_warns_above_existing_warning_threshold(caplog):
    with caplog.at_level(logging.WARNING):
        log_payload_size_diagnostic(
            logging.getLogger("test.payload_diag.threshold"),
            session_id="payload-test",
            recipient_user_id="viewer-1",
            recipient_role="viewer",
            message_type="fog_state",
            byte_size=PAYLOAD_WARN_BYTES + 1,
        )

    assert "message_type=fog_state" in caplog.text
    assert "byte_size=131073" in caplog.text
    assert "warn_threshold_bytes=131072" in caplog.text
