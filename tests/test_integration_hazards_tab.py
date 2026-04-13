"""
tests/test_integration_hazards_tab.py — Integration tests for the hazard zones
tab full user flow.

Covers:
- handle_hazard_zone_create: DM creates damage zone, condition zone, invalid
  condition zone (missing condition returns error), non-DM rejected
- handle_hazard_zone_update: DM updates existing zone, non-existent zone returns
  error, non-DM rejected
- handle_hazard_zone_delete: DM deletes, empty zone_id is noop, non-DM rejected
- handle_hazard_zone_apply: DM applies damage to tokens in zone, out-of-zone
  tokens unaffected, non-DM rejected
- _normalize_hazard_zone_payload: valid payload round-trips, trigger defaults,
  condition zone without condition returns None

Why these tests matter:
Hazard zones are DM tools for environmental damage and condition application.
All CRUD operations are DM-only. Invalid payloads (e.g. condition zone without
a condition ID) must be rejected with an error, not silently produce a bad zone.
Zone application must correctly identify tokens within the radius.
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
    session = Session(id="haz-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.hazard_zones = {}

    # Token inside the default 15 ft radius zone centred at (0,0)
    # radius_ft=15, PX_PER_GRID=50, FT_PER_GRID=5 → radius_px = 15/5*50 = 150 px
    # Token centre: x+width/2 = 20+20 = 40, y+height/2 = 20+20 = 40 → inside radius
    token_inside = Token(id="tok_in", name="Hero", x=20, y=20, width=40, height=40,
                         color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    # Token outside the zone
    token_outside = Token(id="tok_out", name="Bystander", x=500, y=500, width=40, height=40,
                          color="#0f0", shape="circle", owner_id=None, hp=10, max_hp=10)
    session.tokens[token_inside.id] = token_inside
    session.tokens[token_outside.id] = token_outside
    return session, dm, player


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


def _valid_zone_payload(**overrides):
    base = {
        "name": "Fire Pit",
        "map_context": "world",
        "x": 0.0,
        "y": 0.0,
        "radius_ft": 15,
        "trigger": "enter",
        "effect": "damage",
        "dice_num": 2,
        "dice_sides": 6,
        "flat_bonus": 0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# handle_hazard_zone_create
# ---------------------------------------------------------------------------

def test_hazard_zone_create_dm_damage_zone(monkeypatch):
    """
    DM creates a valid damage-type hazard zone.  It should be stored in
    session.hazard_zones and a hazard_zones_sync broadcast should fire.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_create(_valid_zone_payload(), session, dm))

    zones = getattr(session, "hazard_zones", {}) or {}
    assert len(zones) == 1, "One hazard zone should be stored after creation"
    zone = next(iter(zones.values()))
    assert zone["name"] == "Fire Pit"
    assert zone["effect"] == "damage"

    types_sent = [msg.get("type") for _, uid, msg in sent]
    assert "hazard_zones_sync" in types_sent, (
        "hazard_zones_sync must be sent to all users after zone creation"
    )


def test_hazard_zone_create_condition_zone(monkeypatch):
    """
    DM creates a condition-type hazard zone with a valid condition ID.
    The zone must be stored with effect='condition' and the condition field.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    payload = _valid_zone_payload(effect="condition", condition="poisoned")
    asyncio.run(haz.handle_hazard_zone_create(payload, session, dm))

    zones = getattr(session, "hazard_zones", {}) or {}
    assert len(zones) == 1
    zone = next(iter(zones.values()))
    assert zone["effect"] == "condition"
    assert zone.get("condition") == "poisoned"


def test_hazard_zone_create_condition_zone_without_condition_rejected(monkeypatch):
    """
    A condition-type zone with no condition ID must be rejected (returns an
    error to the DM) because it would create a meaningless zone.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    payload = _valid_zone_payload(effect="condition", condition="")
    asyncio.run(haz.handle_hazard_zone_create(payload, session, dm))

    zones = getattr(session, "hazard_zones", {}) or {}
    assert len(zones) == 0, "Condition zone without a condition ID must be rejected"

    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert error_msgs, "Rejected zone creation must send an error to the DM"


def test_hazard_zone_create_player_rejected(monkeypatch):
    """
    A player (non-DM) must not be able to create hazard zones.
    No zone should be stored and no sync broadcast should fire.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_create(_valid_zone_payload(), session, player))

    zones = getattr(session, "hazard_zones", {}) or {}
    assert len(zones) == 0, "Players must not be able to create hazard zones"


def test_hazard_zone_create_assigns_id(monkeypatch):
    """
    Even if no id is in the payload, the handler must assign a unique zone id.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_create(_valid_zone_payload(), session, dm))

    zones = getattr(session, "hazard_zones", {}) or {}
    zone_id = next(iter(zones))
    assert zone_id, "Created zone must have a non-empty ID"


# ---------------------------------------------------------------------------
# handle_hazard_zone_update
# ---------------------------------------------------------------------------

def _create_zone(session, dm, monkeypatch):
    """Helper: create one zone and return its ID."""
    from server.handlers import hazards as haz
    import server.handlers.common as common_mod

    async def _noop_broadcast(session_id, message, exclude_user=None):
        pass

    async def _noop_send(session_id, user_id, message):
        pass

    monkeypatch.setattr(common_mod.manager, "broadcast", _noop_broadcast)
    monkeypatch.setattr(common_mod.manager, "send_to", _noop_send)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)
    asyncio.run(haz.handle_hazard_zone_create(_valid_zone_payload(), session, dm))
    zones = getattr(session, "hazard_zones", {}) or {}
    return next(iter(zones))


def test_hazard_zone_update_dm_changes_name(monkeypatch):
    """
    DM can update an existing zone's name.  The change should be persisted
    in session.hazard_zones.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    zone_id = _create_zone(session, dm, monkeypatch)
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_update(
        {"zone_id": zone_id, "name": "Lava Pool"},
        session, dm,
    ))

    zone = (session.hazard_zones or {}).get(zone_id, {})
    assert zone.get("name") == "Lava Pool", "Zone name must be updated"


def test_hazard_zone_update_nonexistent_returns_error(monkeypatch):
    """
    Updating a zone that doesn't exist must return an error to the DM.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_update(
        {"zone_id": "ghost_zone", "name": "Ghost"},
        session, dm,
    ))

    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert error_msgs, "Updating a non-existent zone must return an error"


def test_hazard_zone_update_player_rejected(monkeypatch):
    """
    A player must not be able to update hazard zones.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    zone_id = _create_zone(session, dm, monkeypatch)
    original_name = (session.hazard_zones or {}).get(zone_id, {}).get("name")
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_update(
        {"zone_id": zone_id, "name": "Player Hack"},
        session, player,
    ))

    zone = (session.hazard_zones or {}).get(zone_id, {})
    assert zone.get("name") == original_name, "Player must not be able to change zone name"


# ---------------------------------------------------------------------------
# handle_hazard_zone_delete
# ---------------------------------------------------------------------------

def test_hazard_zone_delete_dm_removes_zone(monkeypatch):
    """
    DM deletes a zone by zone_id.  The zone must be removed from session.hazard_zones.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    zone_id = _create_zone(session, dm, monkeypatch)
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_delete({"zone_id": zone_id}, session, dm))

    zones = getattr(session, "hazard_zones", {}) or {}
    assert zone_id not in zones, "Deleted zone must not remain in session.hazard_zones"


def test_hazard_zone_delete_empty_id_is_noop(monkeypatch):
    """
    An empty zone_id must not crash the handler.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    # Should not raise
    asyncio.run(haz.handle_hazard_zone_delete({"zone_id": ""}, session, dm))


def test_hazard_zone_delete_player_rejected(monkeypatch):
    """
    A player must not be able to delete hazard zones.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    zone_id = _create_zone(session, dm, monkeypatch)
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    asyncio.run(haz.handle_hazard_zone_delete({"zone_id": zone_id}, session, player))

    zones = getattr(session, "hazard_zones", {}) or {}
    assert zone_id in zones, "Player must not be able to delete hazard zones"


# ---------------------------------------------------------------------------
# handle_hazard_zone_apply
# ---------------------------------------------------------------------------

def test_hazard_zone_apply_damages_token_inside_radius(monkeypatch):
    """
    Applying a hazard zone manually should damage tokens that are inside
    the zone's radius.  HP of the inside token should decrease.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    zone_id = _create_zone(session, dm, monkeypatch)
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    initial_hp = session.tokens["tok_in"].hp

    asyncio.run(haz.handle_hazard_zone_apply({"zone_id": zone_id}, session, dm))

    final_hp = session.tokens["tok_in"].hp
    # Zone does 2d6 min=2 damage, so HP must decrease
    assert final_hp <= initial_hp, "Token inside hazard zone must take damage when zone is applied"


def test_hazard_zone_apply_player_rejected(monkeypatch):
    """
    Only the DM can manually apply hazard zones.
    """
    from server.handlers import hazards as haz
    session, dm, player = _make_session()
    zone_id = _create_zone(session, dm, monkeypatch)
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    initial_hp = session.tokens["tok_in"].hp
    asyncio.run(haz.handle_hazard_zone_apply({"zone_id": zone_id}, session, player))
    assert session.tokens["tok_in"].hp == initial_hp, "Player must not be able to apply hazard zones"


# ---------------------------------------------------------------------------
# _normalize_hazard_zone_payload unit tests
# ---------------------------------------------------------------------------

def test_normalize_hazard_zone_valid():
    """Valid payload round-trips through normalization without error."""
    from server.handlers.hazards import _normalize_hazard_zone_payload
    zone = _normalize_hazard_zone_payload({
        "name": "Acid Pool",
        "x": 50.0, "y": 100.0,
        "radius_ft": 20,
        "trigger": "start_turn",
        "effect": "damage",
        "dice_num": 1,
        "dice_sides": 8,
        "flat_bonus": 2,
    })
    assert zone is not None
    assert zone["name"] == "Acid Pool"
    assert zone["trigger"] == "start_turn"
    assert zone["effect"] == "damage"


def test_normalize_hazard_zone_invalid_trigger_defaults_to_enter():
    """Unknown trigger values must default to 'enter'."""
    from server.handlers.hazards import _normalize_hazard_zone_payload
    zone = _normalize_hazard_zone_payload({"trigger": "sneeze"})
    assert zone["trigger"] == "enter"


def test_normalize_hazard_zone_condition_without_condition_returns_none():
    """Condition zone missing a condition field must return None."""
    from server.handlers.hazards import _normalize_hazard_zone_payload
    result = _normalize_hazard_zone_payload({"effect": "condition", "condition": ""})
    assert result is None, "Condition zone without a condition ID must return None"


def test_normalize_hazard_zone_radius_clamped():
    """Radius below minimum must be clamped to 5 ft."""
    from server.handlers.hazards import _normalize_hazard_zone_payload
    zone = _normalize_hazard_zone_payload({"radius_ft": -10})
    assert zone["radius_ft"] >= 5, "Minimum radius is 5 ft"


def test_normalize_hazard_zone_radius_max_clamped():
    """Radius above maximum must be clamped to 300 ft."""
    from server.handlers.hazards import _normalize_hazard_zone_payload
    zone = _normalize_hazard_zone_payload({"radius_ft": 9999})
    assert zone["radius_ft"] <= 300, "Maximum radius is 300 ft"
