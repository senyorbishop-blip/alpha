from server.handlers.common import build_live_state_debug_summary
from server.session import Session, Token, User


def _token(token_id, *, hidden=False, token_type="monster"):
    return Token(
        id=token_id,
        name=f"Secret {token_id}",
        x=0,
        y=0,
        width=50,
        height=50,
        color="#000",
        shape="circle",
        owner_id=None,
        hidden=hidden,
        token_type=token_type,
    )


def test_live_state_debug_summary_does_not_leak_hidden_token_payload_details():
    session = Session(id="s1")
    session.users = {"p1": User(id="p1", name="Player", role="player")}
    session.tokens = {"hidden-npc": _token("hidden-npc", hidden=True)}

    summary = build_live_state_debug_summary(session, "p1", "player", {"tokens": {}})

    assert summary["hidden_tokens_filtered"] == 1
    assert "Secret hidden-npc" not in repr(summary)
    assert "hidden-npc" not in repr(summary)


def test_live_state_debug_summary_includes_revision_fields():
    session = Session(id="s1")
    session.users = {"dm": User(id="dm", name="DM", role="dm")}
    session.combat = {"active": True, "revision": 7}
    session.visibility_revision = 11
    session.inventory_revision = 13
    session.map_nav_version = 17
    session.fog_maps = {"world": {"map_context": "world", "revision": 19}}

    summary = build_live_state_debug_summary(session, "dm", "dm", {"tokens": {}, "combat": session.combat})

    assert summary["combat_active"] is True
    assert summary["combat_revision"] == 7
    assert summary["visibility_revision"] == 11
    assert summary["inventory_revision"] == 13
    assert summary["map_nav_version"] == 17
    assert summary["fog_revision"] == 19


def test_player_summary_counts_fog_hidden_tokens_without_leaking_details():
    session = Session(id="s1")
    session.users = {"p1": User(id="p1", name="Player", role="player")}
    session.tokens = {"fogged-npc": _token("fogged-npc", token_type="monster")}
    session.fog_maps = {"world": {"enabled": True, "cols": 2, "rows": 2, "cells": "0000", "revision": 3, "map_context": "world"}}

    summary = build_live_state_debug_summary(session, "p1", "player", {"tokens": {}, "fog_maps": session.fog_maps})

    assert summary["fog_hidden_tokens_filtered"] == 1
    assert "Secret fogged-npc" not in repr(summary)
    assert "fogged-npc" not in repr(summary)
