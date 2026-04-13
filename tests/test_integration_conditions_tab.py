"""
tests/test_integration_conditions_tab.py — Integration tests for the conditions
tab full user flow.

Covers:
- handle_token_condition: toggle condition on/off, DM-only & owner guards,
  missing token, missing condition, condition broadcast
- handle_mark_target: hunters_mark and hex applied outside combat, invalid mark
  kind error, hidden target error, viewer blocked

Why these tests matter:
Conditions (poisoned, prone, stunned, etc.) and combat marks (Hunter's Mark,
Hex) are applied during live play and must broadcast immediately to all clients.
Role guards ensure only the DM or the token's owner can toggle conditions.
An invalid mark kind or hidden target must return a typed error without crashing.
"""
import asyncio
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    from server.session import Session, User, Token
    session = Session(id="cond-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    viewer = User(id="viewer1", name="Watcher", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    session.dm_map_context = "world"

    token_player = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                         color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    token_npc = Token(id="tok2", name="Wolf", x=100, y=100, width=40, height=40,
                      color="#888", shape="circle", owner_id=None, hp=12, max_hp=12)
    token_hidden = Token(id="tok3", name="Shadow", x=200, y=200, width=40, height=40,
                         color="#222", shape="circle", owner_id=None, hp=8, max_hp=8)
    token_hidden.hidden = True
    session.tokens[token_player.id] = token_player
    session.tokens[token_npc.id] = token_npc
    session.tokens[token_hidden.id] = token_hidden
    return session, dm, player, viewer


def _patch_manager(monkeypatch):
    import server.handlers.common as common_mod
    broadcasts = []
    sent = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "broadcast", _broadcast)
    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)
    return broadcasts, sent


# ---------------------------------------------------------------------------
# handle_token_condition — DM toggles condition on NPC token
# ---------------------------------------------------------------------------

def test_token_condition_dm_applies_to_npc(monkeypatch):
    """
    DM can apply a condition to any token, including NPC tokens.
    The condition should appear in the token's conditions list and a
    token_condition_changed broadcast should fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok2", "condition": "poisoned"},
        session, dm,
    ))

    token = session.tokens["tok2"]
    assert "poisoned" in (token.conditions or []), (
        "DM-applied condition must appear in token.conditions"
    )


def test_token_condition_dm_toggles_off(monkeypatch):
    """
    Applying the same condition twice should remove it (toggle off).
    This is the expected UI interaction for the conditions tab.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    # Apply
    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok2", "condition": "prone"},
        session, dm,
    ))
    assert "prone" in (session.tokens["tok2"].conditions or [])

    # Toggle off
    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok2", "condition": "prone"},
        session, dm,
    ))
    assert "prone" not in (session.tokens["tok2"].conditions or []), (
        "Second application of same condition should remove it"
    )


def test_token_condition_player_owns_own_token(monkeypatch):
    """
    A player can apply a condition to their own token (e.g. self-inflicted
    disadvantage or prone from falling).
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok1", "condition": "prone"},
        session, player,
    ))
    assert "prone" in (session.tokens["tok1"].conditions or []), (
        "Player must be able to apply condition to their own token"
    )


def test_token_condition_player_cannot_apply_to_npc(monkeypatch):
    """
    A player must NOT be able to apply conditions to tokens they don't own
    (i.e. NPC tokens controlled by the DM).
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok2", "condition": "stunned"},
        session, player,
    ))
    assert "stunned" not in (session.tokens["tok2"].conditions or []), (
        "Player must not be able to apply conditions to NPC tokens"
    )


def test_token_condition_missing_token_is_noop(monkeypatch):
    """
    Referencing a non-existent token_id must not raise an exception —
    the handler should silently ignore the request.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    # Should not raise
    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "NONEXISTENT", "condition": "poisoned"},
        session, dm,
    ))


def test_token_condition_missing_condition_is_noop(monkeypatch):
    """
    Missing or empty condition field must not crash and must not add
    an empty condition to the token.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok1", "condition": ""},
        session, dm,
    ))
    token = session.tokens["tok1"]
    assert "" not in (token.conditions or []), "Empty condition string must be rejected"


def test_token_condition_broadcasts_to_session(monkeypatch):
    """
    Applying a condition must broadcast a token_condition_changed message
    to all users who can see the token.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok1", "condition": "blinded"},
        session, dm,
    ))

    all_types = [msg.get("type") for _, uid, msg in sent]
    assert "token_condition_changed" in all_types, (
        "Condition change must produce a token_condition_changed broadcast"
    )


# ---------------------------------------------------------------------------
# handle_mark_target — Hunter's Mark and Hex outside combat
# ---------------------------------------------------------------------------

def test_mark_target_hunters_mark_applied(monkeypatch):
    """
    Player applies Hunter's Mark to a visible, non-hidden NPC token.
    Should broadcast mark_target_result and persist condition on the token.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "hunters_mark", "target_token_id": "tok2"},
        session, player,
    ))

    types_broadcast = [msg.get("type") for _, msg, _ in broadcasts]
    assert "mark_target_result" in types_broadcast, (
        "Successful Hunter's Mark must broadcast mark_target_result"
    )

    token = session.tokens["tok2"]
    assert "hunters_mark" in (token.conditions or []), (
        "Hunter's Mark condition must appear on the target token"
    )


def test_mark_target_hex_applied(monkeypatch):
    """
    Player applies Hex to a visible NPC token. Both the mark_target_result
    broadcast and the hex condition on the token must be present.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "hex", "target_token_id": "tok2"},
        session, player,
    ))

    types_broadcast = [msg.get("type") for _, msg, _ in broadcasts]
    assert "mark_target_result" in types_broadcast
    assert "hex" in (session.tokens["tok2"].conditions or [])


def test_mark_target_invalid_kind_returns_error(monkeypatch):
    """
    Sending an invalid mark_kind should return an error to the user,
    not apply any condition.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "death_curse", "target_token_id": "tok2"},
        session, player,
    ))

    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert error_msgs, "Invalid mark_kind must produce an error response"
    # No condition should be applied
    token = session.tokens["tok2"]
    assert "death_curse" not in (token.conditions or [])


def test_mark_target_hidden_token_returns_error(monkeypatch):
    """
    Targeting a hidden token (not visible to players) must return an error
    to the player rather than applying the mark.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "hunters_mark", "target_token_id": "tok3"},
        session, player,
    ))

    error_msgs = [msg for _, uid, msg in sent if uid == player.id and msg.get("type") == "error"]
    assert error_msgs, "Targeting a hidden token must return an error to the player"


def test_mark_target_viewer_cannot_mark(monkeypatch):
    """
    Viewers are receive-only; they must not be able to place marks.
    No condition should be applied and no success broadcast should fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "hunters_mark", "target_token_id": "tok2"},
        session, viewer,
    ))

    success_types = [msg.get("type") for _, msg, _ in broadcasts]
    assert "mark_target_result" not in success_types, (
        "Viewers must not be able to apply marks"
    )
    assert "hunters_mark" not in (session.tokens["tok2"].conditions or [])


def test_mark_target_dm_can_apply_from_any_role(monkeypatch):
    """
    DM can always apply Hunter's Mark regardless of combat state.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "hunters_mark", "target_token_id": "tok1"},
        session, dm,
    ))

    types_broadcast = [msg.get("type") for _, msg, _ in broadcasts]
    assert "mark_target_result" in types_broadcast


# ---------------------------------------------------------------------------
# _set_token_condition / _clear_token_condition helper unit tests
# ---------------------------------------------------------------------------

def test_set_condition_adds_to_list():
    """_set_token_condition appends to token.conditions."""
    from server.handlers.conditions import _set_token_condition
    from server.session import Token
    token = Token(id="x1", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    token.conditions = []
    _set_token_condition(token, "stunned", 0)
    assert "stunned" in token.conditions


def test_set_condition_is_idempotent():
    """Adding the same condition twice must not duplicate it."""
    from server.handlers.conditions import _set_token_condition
    from server.session import Token
    token = Token(id="x2", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    token.conditions = []
    _set_token_condition(token, "poisoned", 0)
    _set_token_condition(token, "poisoned", 0)
    assert token.conditions.count("poisoned") == 1


def test_clear_condition_removes_it():
    """_clear_token_condition must remove the condition."""
    from server.handlers.conditions import _set_token_condition, _clear_token_condition
    from server.session import Token
    token = Token(id="x3", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    token.conditions = []
    _set_token_condition(token, "blinded", 0)
    _clear_token_condition(token, "blinded")
    assert "blinded" not in token.conditions


def test_clear_condition_nonexistent_is_noop():
    """Clearing a condition that was never applied must not raise."""
    from server.handlers.conditions import _clear_token_condition
    from server.session import Token
    token = Token(id="x4", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    token.conditions = []
    # Should not raise
    _clear_token_condition(token, "invisible")


def test_set_condition_with_duration_stores_timer():
    """Applying a timed condition must store a future expiry in condition_timers."""
    import time
    from server.handlers.conditions import _set_token_condition
    from server.session import Token
    token = Token(id="x5", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    token.conditions = []
    token.condition_timers = {}
    _set_token_condition(token, "restrained", 30)
    assert "restrained" in token.condition_timers
    assert token.condition_timers["restrained"] > time.time()


def test_prune_removes_expired_condition():
    """Expired timers and their conditions must be pruned."""
    import time
    from server.handlers.conditions import _prune_token_condition_timers
    from server.session import Token
    token = Token(id="x6", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    # Set an already-expired timer
    token.conditions = ["poisoned"]
    token.condition_timers = {"poisoned": time.time() - 10}
    _prune_token_condition_timers(token)
    assert "poisoned" not in (token.conditions or []), (
        "Expired conditions must be pruned"
    )


def test_prune_keeps_future_condition():
    """Conditions whose timers have not yet expired must be kept."""
    import time
    from server.handlers.conditions import _prune_token_condition_timers
    from server.session import Token
    token = Token(id="x7", name="T", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    token.conditions = ["stunned"]
    token.condition_timers = {"stunned": time.time() + 60}
    _prune_token_condition_timers(token)
    assert "stunned" in (token.conditions or []), (
        "Non-expired conditions must survive pruning"
    )
