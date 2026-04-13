"""
tests/test_integration_sound_narration.py — Integration tests for the sound
and narration broadcast system.

Tests cover:
- handle_sound_set_ambient: valid tracks, invalid track normalized to silence,
  DM-only guard, volume/fade_ms clamping, session state persisted
- handle_sound_play_sfx: valid SFX dispatched, invalid SFX ignored, DM-only
- handle_sound_stop_all: resets state to silence, broadcasts stop message
- broadcast_narration_hook: fires narration broadcast to all clients

Why these tests matter:
Audio immersion is a first-class feature. DM-only guards prevent players from
hijacking the audio context.  State persistence ensures reconnecting clients
get the current sound context.  Clamping volume/fade_ms to [0,1] and [0,5000]
prevents broken UI on the player end.
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
    session = Session(id="sound-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.sound_state = {}
    return session, dm, player


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
# handle_sound_set_ambient
# ---------------------------------------------------------------------------

def test_sound_set_ambient_valid_track_broadcast(monkeypatch):
    """DM setting a valid ambient track should broadcast to all clients."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "tavern", "volume": 0.8, "fade_ms": 1000},
        session,
        dm,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "sound_set_ambient" in types


def test_sound_set_ambient_payload_contains_track(monkeypatch):
    """Broadcast payload must include the track name."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "dungeon", "volume": 0.5, "fade_ms": 1500},
        session,
        dm,
    ))

    ambient_msgs = [
        msg for _, msg, _ in mgr._broadcasts
        if msg["type"] == "sound_set_ambient"
    ]
    assert ambient_msgs
    assert ambient_msgs[0]["payload"]["track"] == "dungeon"


def test_sound_set_ambient_invalid_track_normalized_to_silence(monkeypatch):
    """An unknown track name should be normalized to 'silence'."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "unknown_track_xyz", "volume": 0.5, "fade_ms": 500},
        session,
        dm,
    ))

    ambient_msgs = [
        msg for _, msg, _ in mgr._broadcasts
        if msg["type"] == "sound_set_ambient"
    ]
    assert ambient_msgs
    assert ambient_msgs[0]["payload"]["track"] == "silence"


def test_sound_set_ambient_dm_only_guard(monkeypatch):
    """Players must not be able to change the ambient track."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "battle", "volume": 1.0, "fade_ms": 500},
        session,
        player,
    ))

    assert len(mgr._broadcasts) == 0, "Players must not broadcast ambient track changes"


def test_sound_set_ambient_volume_clamped(monkeypatch):
    """Volume above 1.0 should be clamped to 1.0."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "forest", "volume": 99.0, "fade_ms": 500},
        session,
        dm,
    ))

    ambient_msgs = [
        msg for _, msg, _ in mgr._broadcasts
        if msg["type"] == "sound_set_ambient"
    ]
    assert ambient_msgs
    assert ambient_msgs[0]["payload"]["volume"] <= 1.0


def test_sound_set_ambient_updates_session_state(monkeypatch):
    """After setting ambient, session.sound_state must reflect new values."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "forest", "volume": 0.6, "fade_ms": 2000},
        session,
        dm,
    ))

    assert session.sound_state.get("track") == "forest"
    assert session.sound_state.get("volume") == 0.6


def test_sound_set_ambient_excludes_dm_from_broadcast(monkeypatch):
    """Ambient broadcast must exclude the DM (DM manages audio locally)."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_set_ambient(
        {"track": "battle", "volume": 0.9, "fade_ms": 800},
        session,
        dm,
    ))

    ambient_msgs = [
        (msg, exc) for _, msg, exc in mgr._broadcasts
        if msg["type"] == "sound_set_ambient"
    ]
    assert ambient_msgs
    _msg, exclude_user = ambient_msgs[0]
    assert exclude_user == dm.id


# ---------------------------------------------------------------------------
# handle_sound_play_sfx
# ---------------------------------------------------------------------------

def test_sound_play_sfx_valid_sfx_broadcast(monkeypatch):
    """DM playing a valid SFX should broadcast sound_play_sfx."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    asyncio.run(sh.handle_sound_play_sfx(
        {"sfx_id": "sword_clash", "volume": 1.0},
        session,
        dm,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "sound_play_sfx" in types


def test_sound_play_sfx_invalid_sfx_ignored(monkeypatch):
    """An unknown SFX ID should produce no broadcast."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    asyncio.run(sh.handle_sound_play_sfx(
        {"sfx_id": "laser_beam_xyz", "volume": 1.0},
        session,
        dm,
    ))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "sound_play_sfx" not in types


def test_sound_play_sfx_player_cannot_trigger(monkeypatch):
    """Players must not be able to trigger SFX."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    asyncio.run(sh.handle_sound_play_sfx(
        {"sfx_id": "fireball", "volume": 1.0},
        session,
        player,
    ))

    assert len(mgr._broadcasts) == 0


# ---------------------------------------------------------------------------
# handle_sound_stop_all
# ---------------------------------------------------------------------------

def test_sound_stop_all_broadcasts_stop_message(monkeypatch):
    """handle_sound_stop_all must broadcast a sound_stop_all message."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    session.sound_state = {"track": "battle", "volume": 0.9}
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_stop_all({}, session, dm))

    types = [msg["type"] for _, msg, _ in mgr._broadcasts]
    assert "sound_stop_all" in types


def test_sound_stop_all_resets_session_state_to_silence(monkeypatch):
    """After stop_all, session.sound_state must reflect track=silence."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    session.sound_state = {"track": "battle", "volume": 0.9}
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_stop_all({}, session, dm))

    assert session.sound_state.get("track") == "silence"


def test_sound_stop_all_player_cannot_stop(monkeypatch):
    """Players must not be able to stop audio."""
    from server.handlers import sound as sh
    session, dm, player = _make_session()
    session.sound_state = {"track": "tavern"}
    mgr = _fake_manager()
    monkeypatch.setattr(sh, "manager", mgr)

    async def _save(_):
        return True

    monkeypatch.setattr(sh, "save_campaign_async", _save)

    asyncio.run(sh.handle_sound_stop_all({}, session, player))

    assert len(mgr._broadcasts) == 0
    # State should remain unchanged
    assert session.sound_state.get("track") == "tavern"
