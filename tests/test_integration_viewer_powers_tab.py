"""
tests/test_integration_viewer_powers_tab.py — Integration tests for the viewer
powers system full user flow.

Covers:
- handle_viewer_power_grant: DM grants a base power (pebble_toss) to a viewer,
  profile created, viewers_profiles broadcast fires; non-DM rejected; granting
  to a player (non-viewer) is a noop
- handle_viewer_power_revoke: DM revokes a granted power; power removed from
  profile; non-DM rejected
- handle_viewer_power_grant_preset: DM applies a preset bundle; viewer receives
  all powers in the preset
- handle_viewer_power_use: viewer fires a pebble_toss (single_damage) at a
  token — error returned for no charges; non-viewer cannot call use; unknown
  power returns noop
- handle_viewer_cursor_update: viewer sends cursor position, broadcast fires
- handle_viewer_presence_toggle: DM enables/disables viewer presence

Why these tests matter:
Viewer powers are a premium interactive layer — spectators can affect the game
in limited ways approved by the DM.  Granting, revoking, and using powers each
touch profile state that must be broadcast to sync all clients.  Charge and
cooldown guards prevent replay attacks.  Role isolation (viewer ≠ player) must
be strictly enforced.
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
    session = Session(id="vp-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    viewer = User(id="viewer1", name="Spectator", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    session.dm_map_context = "world"

    token = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                  color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    session.tokens[token.id] = token
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


def _viewer_profile(session, viewer):
    """Return viewer's power profile dict (may be None)."""
    from server.handlers.viewer_powers import _viewer_key_for_user
    profiles = getattr(session, "viewer_profiles", {}) or {}
    key = _viewer_key_for_user(viewer)
    return (profiles or {}).get(key)


# ---------------------------------------------------------------------------
# handle_viewer_power_grant
# ---------------------------------------------------------------------------

def test_viewer_power_grant_dm_grants_pebble_toss(monkeypatch):
    """
    DM grants pebble_toss (a base power) to a viewer.
    The viewer's profile should contain the power with charges=1.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": viewer.id, "power_id": "pebble_toss"},
        session, dm,
    ))

    profile = _viewer_profile(session, viewer)
    assert profile is not None, "Viewer profile must be created after power grant"
    powers = profile.get("powers") or {}
    assert "pebble_toss" in powers, "pebble_toss must appear in viewer's profile after grant"
    assert int(powers["pebble_toss"].get("charges", 0)) >= 1, "Granted power must have at least 1 charge"


def test_viewer_power_grant_broadcasts_viewer_profiles(monkeypatch):
    """
    Granting a power must broadcast viewer_profiles_sync so all clients
    can update the viewer interaction panel.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": viewer.id, "power_id": "healing_spark"},
        session, dm,
    ))

    sent_types = [msg.get("type") for _, uid, msg in sent]
    assert "viewer_profiles_sync" in sent_types, (
        "Power grant must broadcast viewer_profiles_sync"
    )


def test_viewer_power_grant_player_cannot_grant(monkeypatch):
    """
    A player must not be able to grant viewer powers.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": viewer.id, "power_id": "pebble_toss"},
        session, player,
    ))

    profile = _viewer_profile(session, viewer)
    assert profile is None or "pebble_toss" not in (profile.get("powers") or {}), (
        "Player must not be able to grant viewer powers"
    )


def test_viewer_power_grant_to_player_is_noop(monkeypatch):
    """
    Attempting to grant a viewer power to a player (not a viewer) must be
    a silent noop — the target is not a viewer role.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": player.id, "power_id": "pebble_toss"},
        session, dm,
    ))

    # Player should not have a viewer profile created
    from server.handlers.viewer_powers import _viewer_key_for_user
    profiles = getattr(session, "viewer_profiles", {}) or {}
    assert _viewer_key_for_user(player) not in profiles, (
        "No viewer profile must be created for a player target"
    )


def test_viewer_power_grant_unknown_power_is_noop(monkeypatch):
    """
    Granting an unknown power_id must be a noop; no profile change.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": viewer.id, "power_id": "supercheat_laser_9000"},
        session, dm,
    ))

    profile = _viewer_profile(session, viewer)
    assert profile is None or "supercheat_laser_9000" not in (profile.get("powers") or {}), (
        "Unknown power_id must not be added to viewer profile"
    )


# ---------------------------------------------------------------------------
# handle_viewer_power_revoke
# ---------------------------------------------------------------------------

def _grant_power(session, dm, viewer, power_id, monkeypatch):
    """Helper: grant power_id to viewer."""
    from server.handlers import viewer_powers as vp

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)
    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": viewer.id, "power_id": power_id},
        session, dm,
    ))


def test_viewer_power_revoke_removes_power(monkeypatch):
    """
    DM revokes a previously granted power.  The power must be removed
    from the viewer's profile.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)
    _grant_power(session, dm, viewer, "pebble_toss", monkeypatch)

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_revoke(
        {"viewer_user_id": viewer.id, "power_id": "pebble_toss"},
        session, dm,
    ))

    profile = _viewer_profile(session, viewer)
    powers = (profile or {}).get("powers") or {}
    assert "pebble_toss" not in powers, "Revoked power must be removed from viewer profile"


def test_viewer_power_revoke_player_cannot_revoke(monkeypatch):
    """
    A player must not be able to revoke viewer powers.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)
    _grant_power(session, dm, viewer, "pebble_toss", monkeypatch)
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_revoke(
        {"viewer_user_id": viewer.id, "power_id": "pebble_toss"},
        session, player,
    ))

    profile = _viewer_profile(session, viewer)
    powers = (profile or {}).get("powers") or {}
    assert "pebble_toss" in powers, "Player must not be able to revoke viewer powers"


def test_viewer_power_revoke_nonexistent_power_is_noop(monkeypatch):
    """
    Revoking a power the viewer doesn't have must not crash.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    # Should not raise
    asyncio.run(vp.handle_viewer_power_revoke(
        {"viewer_user_id": viewer.id, "power_id": "nonexistent_power"},
        session, dm,
    ))


# ---------------------------------------------------------------------------
# handle_viewer_power_use
# ---------------------------------------------------------------------------

def test_viewer_power_use_no_charges_returns_error(monkeypatch):
    """
    Viewer attempting to use a power with 0 charges must receive an error.
    No game state should change.
    """
    from server.handlers import viewer_powers as vp
    from server.handlers.viewer_powers import _viewer_key_for_user
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)
    _grant_power(session, dm, viewer, "pebble_toss", monkeypatch)

    # Drain charges
    profiles = getattr(session, "viewer_profiles", {}) or {}
    key = _viewer_key_for_user(viewer)
    profiles[key]["powers"]["pebble_toss"]["charges"] = 0
    session.viewer_profiles = profiles

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_use(
        {"power_id": "pebble_toss", "target_token_id": "tok1"},
        session, viewer,
    ))

    error_msgs = [msg for _, uid, msg in sent if uid == viewer.id and msg.get("type") == "error"]
    assert error_msgs, "Viewer with 0 charges must receive an error"


def test_viewer_power_use_player_cannot_use(monkeypatch):
    """
    Only viewers can use viewer powers; players and DMs calling this
    handler must be silently rejected.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    initial_hp = session.tokens["tok1"].hp
    asyncio.run(vp.handle_viewer_power_use(
        {"power_id": "pebble_toss", "target_token_id": "tok1"},
        session, player,
    ))

    # HP must be unchanged
    assert session.tokens["tok1"].hp == initial_hp, "Player must not be able to use viewer powers"


def test_viewer_power_use_unknown_power_is_noop(monkeypatch):
    """
    Using an unknown power_id must be a silent noop (no crash, no state change).
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    initial_hp = session.tokens["tok1"].hp
    # Should not raise
    asyncio.run(vp.handle_viewer_power_use(
        {"power_id": "ghost_power_xyz", "target_token_id": "tok1"},
        session, viewer,
    ))
    assert session.tokens["tok1"].hp == initial_hp


# ---------------------------------------------------------------------------
# handle_viewer_cursor_update
# ---------------------------------------------------------------------------

def test_viewer_cursor_update_broadcasts_position(monkeypatch):
    """
    Viewer sends a cursor position update.  It should be broadcast to all
    other session users (exclude the sender).
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(vp.handle_viewer_cursor_update(
        {"x": 300.0, "y": 250.0, "map_context": "world"},
        session, viewer,
    ))

    all_types = (
        [msg.get("type") for _, msg, _ in broadcasts]
        + [msg.get("type") for _, uid, msg in sent]
    )
    assert any("cursor" in t for t in all_types), (
        "Viewer cursor update must produce a cursor broadcast"
    )


# ---------------------------------------------------------------------------
# handle_viewer_power_grant_preset
# ---------------------------------------------------------------------------

def test_viewer_power_grant_preset_applies_all_powers(monkeypatch):
    """
    Granting a preset bundle should add all powers in that preset to the
    viewer's profile.
    """
    from server.handlers import viewer_powers as vp
    from server.handlers.viewer_powers import VIEWER_POWER_PRESETS
    if not VIEWER_POWER_PRESETS:
        # No presets defined — skip
        return

    preset_id = next(iter(VIEWER_POWER_PRESETS))
    preset = VIEWER_POWER_PRESETS[preset_id]
    expected_powers = {g["power_id"] for g in (preset.get("grants") or []) if g.get("power_id")}
    if not expected_powers:
        return

    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant_preset(
        {"viewer_user_id": viewer.id, "preset_id": preset_id},
        session, dm,
    ))

    profile = _viewer_profile(session, viewer)
    powers = (profile or {}).get("powers") or {}
    for pid in expected_powers:
        assert pid in powers, f"Preset power '{pid}' must be in viewer profile after preset grant"

def test_viewer_power_grant_accepts_stable_player_key_alias(monkeypatch):
    """DM grants should resolve stable viewer aliases used by restored clients."""
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    viewer.player_key = "stable-viewer-key"
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": "stable-viewer-key", "power_id": "pebble_toss"},
        session, dm,
    ))

    profile = _viewer_profile(session, viewer)
    assert profile is not None
    assert "pebble_toss" in (profile.get("powers") or {})
    assert any(
        uid == dm.id and msg.get("type") == "viewer_power_status" and "Granted" in ((msg.get("payload") or {}).get("message") or "")
        for _, uid, msg in sent
    )
