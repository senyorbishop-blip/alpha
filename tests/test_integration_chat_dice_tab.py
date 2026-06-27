"""
tests/test_integration_chat_dice_tab.py — Integration tests for the chat and
dice tab full user flow.

Tests cover:
- handle_chat_message: normal message broadcast, role-based visibility,
  empty message rejection
- handle_dice_roll: happy path rolls (d20, d6, d100), nat20/nat1 special-fx,
  private vs. public mode, modifier arithmetic
- handle_dice_special_fx: correct broadcast excluding sender
- Error path: unknown dice type ignored, invalid payload fields
"""
import asyncio
import sys
import os
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    from server.session import Session, User
    session = Session(id="chat-dice-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    viewer = User(id="viewer1", name="View", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    session.log = []
    return session, dm, player, viewer


def _fake_manager():
    broadcasts = []
    sent = []

    async def broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    m = SimpleNamespace(broadcast=broadcast, send_to=send_to)
    m._broadcasts = broadcasts
    m._sent = sent
    return m


# ---------------------------------------------------------------------------
# handle_chat_message
# ---------------------------------------------------------------------------

def test_chat_message_broadcasts_to_session(monkeypatch):
    """A normal chat message should be broadcast to all in the session."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_chat_message(
        {"message": "Hello everyone!"},
        session,
        player,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "chat_message" in types


def test_chat_message_payload_contains_user_info(monkeypatch):
    """Broadcast payload must include user name and role."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_chat_message(
        {"message": "Test message"},
        session,
        player,
    ))

    chat_broadcasts = [
        msg for _, msg, _ in mgr._broadcasts
        if msg["type"] == "chat_message"
    ]
    assert chat_broadcasts
    payload = chat_broadcasts[0]["payload"]
    assert payload.get("user_name") == "Alice"
    assert payload.get("role") == "player"


def test_chat_message_text_included_in_payload(monkeypatch):
    """The message text must be present in the broadcast payload."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_chat_message(
        {"message": "Unique-test-message-XYZ"},
        session,
        player,
    ))

    chat_broadcasts = [
        msg for _, msg, _ in mgr._broadcasts
        if msg["type"] == "chat_message"
    ]
    assert any("Unique-test-message-XYZ" in str(b["payload"]) for b in chat_broadcasts)


def test_chat_message_empty_text_not_broadcast(monkeypatch):
    """Empty or whitespace-only messages should not be broadcast."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_chat_message(
        {"message": "   "},
        session,
        player,
    ))

    chat_broadcasts = [
        msg for _, msg, _ in mgr._broadcasts
        if msg["type"] == "chat_message"
    ]
    assert len(chat_broadcasts) == 0


# ---------------------------------------------------------------------------
# handle_dice_roll
# ---------------------------------------------------------------------------

def test_dice_roll_table_visibility_broadcasts_result(monkeypatch):
    """A visibility="table" d20 roll should broadcast dice_result to everyone."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    # "table" is the explicit opt-in to show a roll to the whole table.
    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 20, "quantity": 1, "modifier": 0, "seed": 42,
         "visibility": "table"},
        session,
        player,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "dice_result" in types


def test_dice_roll_initiative_label_is_private(monkeypatch):
    """A bare "initiative"-labelled roll is no longer broadcast to everyone.

    The combat initiative tracker is synced separately via combat_state, so the
    big dice popup stays private to the roller.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 20, "quantity": 1, "modifier": 0, "seed": 42,
         "roll_label": "initiative"},
        session,
        player,
    ))

    broadcast_types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "dice_result" not in broadcast_types
    recipients = {uid for _, uid, msg in mgr._sent if msg["type"] == "dice_result"}
    assert recipients == {player.id}


def test_dice_roll_includes_sounds_in_payload(monkeypatch):
    """dice_result payload must include 'sounds' dict with roll and result keys."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 6, "quantity": 2, "modifier": 3, "seed": 1337},
        session,
        player,
    ))

    # Normal (non-initiative) rolls are private: delivered to the roller + DMs
    # via send_to, not broadcast to everyone.
    dice_msgs = [
        msg for _, uid, msg in mgr._sent
        if msg["type"] == "dice_result"
    ]
    assert dice_msgs
    payload = dice_msgs[0]["payload"]
    assert "sounds" in payload
    sounds = payload["sounds"]
    assert "roll" in sounds
    assert "result" in sounds


# ---------------------------------------------------------------------------
# Helper: find a Random seed that produces a specific d20 value
# ---------------------------------------------------------------------------

def _find_seed_for_d20(target: int) -> int | None:
    """Return the first seed 1..999 whose first randint(1,20) equals target."""
    import random
    for s in range(1, 1000):
        rng = random.Random(s)
        if rng.randint(1, 20) == target:
            return s
    return None  # pragma: no cover


def test_dice_roll_d20_nat20_broadcasts_special_fx(monkeypatch):
    """A natural 20 on a d20 should trigger a dice_special_fx broadcast."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    seed = _find_seed_for_d20(20)
    if seed is None:
        return  # pragma: no cover

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 20, "quantity": 1, "modifier": 0, "seed": seed},
        session,
        player,
    ))

    # A normal (private) roll delivers its special FX over the private channel
    # to the roller + DMs, not via a table-wide broadcast.
    types = [msg["type"] for _, _, msg in mgr._sent]
    assert "dice_special_fx" in types

    fx_msgs = [
        msg for _, _, msg in mgr._sent
        if msg["type"] == "dice_special_fx"
    ]
    assert fx_msgs[0]["payload"]["fx_type"] == "nat20"


def test_dice_roll_d20_nat1_broadcasts_special_fx(monkeypatch):
    """A natural 1 on a d20 should trigger a dice_special_fx broadcast."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    seed = _find_seed_for_d20(1)
    if seed is None:
        return  # pragma: no cover

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 20, "quantity": 1, "modifier": 0, "seed": seed},
        session,
        player,
    ))

    # Private roll: special FX delivered to the roller + DMs over send_to.
    fx_msgs = [
        msg for _, _, msg in mgr._sent
        if msg["type"] == "dice_special_fx"
    ]
    assert fx_msgs
    assert fx_msgs[0]["payload"]["fx_type"] == "nat1"


def test_dice_roll_modifier_applied_to_total(monkeypatch):
    """Modifier should be added to the total in the result."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    # seed=7 with d6 qty=1 produces a deterministic roll
    import random
    seed = 7
    rng = random.Random(seed)
    expected_roll = rng.randint(1, 6)
    modifier = 5

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 6, "quantity": 1, "modifier": modifier, "seed": seed},
        session,
        player,
    ))

    # Private (non-initiative) roll: result delivered via send_to.
    dice_msgs = [
        msg for _, _, msg in mgr._sent
        if msg["type"] == "dice_result"
    ]
    assert dice_msgs
    payload = dice_msgs[0]["payload"]
    assert payload["total"] == expected_roll + modifier


def test_dice_roll_unknown_dice_type_ignored(monkeypatch):
    """An unknown dice type (e.g. d7) should not broadcast any result."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 7, "quantity": 1, "modifier": 0, "seed": 1},
        session,
        player,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "dice_result" not in types


def test_dice_roll_d100_percentile_result(monkeypatch):
    """Rolling d100 should broadcast with percentile_pairs in payload."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 100, "quantity": 1, "modifier": 0, "seed": 99},
        session,
        player,
    ))

    # Private (non-initiative) roll: result delivered via send_to.
    dice_msgs = [
        msg for _, _, msg in mgr._sent
        if msg["type"] == "dice_result"
    ]
    assert dice_msgs
    assert "percentile_pairs" in dice_msgs[0]["payload"]
    assert len(dice_msgs[0]["payload"]["percentile_pairs"]) == 1


def test_dice_roll_multi_quantity(monkeypatch):
    """Rolling multiple dice should produce a list of individual rolls."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_roll(
        {"dice_type": 6, "quantity": 4, "modifier": 0, "seed": 55},
        session,
        player,
    ))

    # Private (non-initiative) roll: result delivered via send_to.
    dice_msgs = [
        msg for _, _, msg in mgr._sent
        if msg["type"] == "dice_result"
    ]
    assert dice_msgs
    rolls = dice_msgs[0]["payload"]["rolls"]
    assert len(rolls) == 4
    assert all(1 <= r <= 6 for r in rolls)


# ---------------------------------------------------------------------------
# handle_dice_special_fx — direct invocation
# ---------------------------------------------------------------------------

def test_dice_special_fx_nat20_broadcast(monkeypatch):
    """handle_dice_special_fx should broadcast dice_special_fx excluding sender."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_special_fx(
        {"fx_type": "nat20", "result": 20, "user_id": player.id},
        session,
        player,
    ))

    fx_msgs = [
        (msg, exc) for _, msg, exc in mgr._broadcasts
        if msg["type"] == "dice_special_fx"
    ]
    assert fx_msgs
    _msg, exclude_user = fx_msgs[0]
    assert exclude_user == player.id


def test_dice_special_fx_invalid_type_not_broadcast(monkeypatch):
    """Unknown fx_type should produce no broadcast."""
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(ch, "manager", mgr)

    asyncio.run(ch.handle_dice_special_fx(
        {"fx_type": "critical_miss_blah", "result": 1, "user_id": player.id},
        session,
        player,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "dice_special_fx" not in types
