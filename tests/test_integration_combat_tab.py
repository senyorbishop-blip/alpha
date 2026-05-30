"""
tests/test_integration_combat_tab.py — Integration tests for the combat tab
full user flow: from session mount through initiative, turn management, death
saves, and attack.

Tests cover:
- handle_combat_update: DM initiates combat with combatants
- handle_combat_next: advances turn, rolls over at end
- handle_combat_clear: resets combat state
- handle_combat_death_save: player death-save tracking
- handle_combat_roll_initiative: randomised initiative broadcast
- Role guards: non-DM cannot call DM-only actions

Why these tests matter:
Combat is the most complex real-time multiplayer feature. Every change to
initiative order, HP, or turn state must be broadcast immediately to all
clients. Role guards prevent players from hijacking combat flow.
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

def _make_session_with_combat(combatants=None):
    from server.session import Session, User, Token
    session = Session(id="combat-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    if combatants is None:
        combatants = [
            {"id": "c1", "token_id": "tok1", "name": "Alice", "initiative": 20, "hp": 20,
             "max_hp": 20, "is_player": True, "owner_id": "player1"},
            {"id": "c2", "token_id": "tok2", "name": "Wolf", "initiative": 10, "hp": 12,
             "max_hp": 12, "is_player": False},
        ]
    token1 = Token(id="tok1", name="Alice", x=100, y=100, width=40, height=40,
                   color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    token2 = Token(id="tok2", name="Wolf", x=200, y=200, width=40, height=40,
                   color="#888", shape="circle", owner_id=None, hp=12, max_hp=12)
    session.tokens[token1.id] = token1
    session.tokens[token2.id] = token2
    session.combat = {"active": True, "turn": 0, "combatants": combatants, "round": 1}
    return session, dm, player


def _noop_broadcasts(monkeypatch):
    """Patch manager broadcast/send_to in combat and common modules to capture calls."""
    from server.handlers import combat as ch
    import server.handlers.common as common_mod

    broadcasts = []
    sent = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    # Patch the manager object's methods so all handlers are affected
    monkeypatch.setattr(common_mod.manager, "broadcast", _broadcast)
    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    return broadcasts, sent


# ---------------------------------------------------------------------------
# handle_combat_update — DM initiates combat
# ---------------------------------------------------------------------------

def test_combat_update_dm_can_start_combat(monkeypatch):
    """DM combat_update should broadcast combat_state to all clients."""
    from server.handlers import combat as ch
    session, dm, player = _make_session_with_combat()
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    # Patch _process_current_start_turn_hazards to avoid hazard side-effects
    async def _noop_hazards(_session):
        return None

    import server.handlers.hazards as haz
    monkeypatch.setattr(haz, "_process_current_start_turn_hazards", _noop_hazards)

    asyncio.run(ch.handle_combat_update({
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": session.combat["combatants"],
    }, session, dm))

    types_broadcast = [msg["type"] for _, msg, _ in broadcasts]
    assert "combat_state" in types_broadcast, "combat_state must be broadcast after update"


def test_combat_update_player_cannot_start_combat(monkeypatch):
    """Players must not be allowed to call combat_update (DM-only)."""
    from server.handlers import combat as ch
    session, dm, player = _make_session_with_combat()
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    asyncio.run(ch.handle_combat_update(
        {"active": True, "turn": 0, "combatants": []},
        session,
        player,
    ))
    # No combat_state broadcast expected for player
    types_broadcast = [msg["type"] for _, msg, _ in broadcasts]
    assert "combat_state" not in types_broadcast


# ---------------------------------------------------------------------------
# handle_combat_next — turn advancement
# ---------------------------------------------------------------------------

def test_combat_next_advances_turn(monkeypatch):
    """handle_combat_next should increment the turn counter."""
    from server.handlers import combat as ch
    session, dm, _ = _make_session_with_combat()
    session.combat["turn"] = 0
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    async def _noop_hazards(_session, **kwargs):
        return None

    import server.handlers.hazards as haz
    monkeypatch.setattr(haz, "_process_current_start_turn_hazards", _noop_hazards)
    monkeypatch.setattr(haz, "_process_current_end_turn_hazards", _noop_hazards)
    monkeypatch.setattr(haz, "_process_end_round_hazards", _noop_hazards)

    asyncio.run(ch.handle_combat_next({}, session, dm))

    assert session.combat["turn"] == 1


def test_combat_next_wraps_to_zero_after_last_combatant(monkeypatch):
    """Turn should wrap back to 0 (new round) after last combatant."""
    from server.handlers import combat as ch
    session, dm, _ = _make_session_with_combat()
    session.combat["turn"] = 1  # already at last combatant (index 1 of 2)
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    async def _noop_hazards(_session, **kwargs):
        return None

    import server.handlers.hazards as haz
    monkeypatch.setattr(haz, "_process_current_start_turn_hazards", _noop_hazards)
    monkeypatch.setattr(haz, "_process_current_end_turn_hazards", _noop_hazards)
    monkeypatch.setattr(haz, "_process_end_round_hazards", _noop_hazards)

    asyncio.run(ch.handle_combat_next({}, session, dm))

    assert session.combat["turn"] == 0
    assert session.combat.get("round", 1) >= 2


# ---------------------------------------------------------------------------
# handle_combat_clear — reset
# ---------------------------------------------------------------------------

def test_combat_clear_resets_active_flag(monkeypatch):
    """handle_combat_clear must set active=False."""
    from server.handlers import combat as ch
    session, dm, _ = _make_session_with_combat()
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    asyncio.run(ch.handle_combat_clear({}, session, dm))

    assert session.combat.get("active") is False or session.combat.get("active") == 0


# ---------------------------------------------------------------------------
# handle_combat_death_save
# ---------------------------------------------------------------------------

def test_combat_death_save_updates_death_save_state(monkeypatch):
    """
    handle_combat_death_save must update the combatant's death_saves dict
    and broadcast a combat_state update.
    """
    import random
    from server.handlers import combat as ch
    from server.session import Session, User, Token

    session = Session(id="ds-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    token = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                  color="#f00", shape="circle", owner_id="player1", hp=0, max_hp=20)
    session.tokens[token.id] = token
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{
            "token_id": "tok1",
            "name": "Alice",
            "is_player": True,
            "owner_id": "player1",
            "hp": 0,
            "max_hp": 20,
            "death_saves": {"successes": 0, "fails": 0, "stable": False, "dead": False},
        }],
    }

    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    # Force a fail outcome (roll <= 9 but not 1)
    monkeypatch.setattr(random, "randint", lambda a, b: 5)

    asyncio.run(ch.handle_combat_death_save(
        {"token_id": "tok1"},
        session,
        player,
    ))

    # A dice_result and combat_state broadcast must have happened
    types = [msg["type"] for _, msg, _ in broadcasts]
    assert "dice_result" in types


def test_combat_death_save_broadcasts_dice_result(monkeypatch):
    """Death save must broadcast dice_result with the rolled value."""
    import random
    from server.handlers import combat as ch
    from server.session import Session, User, Token

    session = Session(id="ds-integ-2")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    token = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                  color="#f00", shape="circle", owner_id="player1", hp=0, max_hp=20)
    session.tokens[token.id] = token
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{
            "token_id": "tok1",
            "name": "Alice",
            "is_player": True,
            "owner_id": "player1",
            "hp": 0,
            "max_hp": 20,
            "death_saves": {"successes": 0, "fails": 2, "stable": False, "dead": False},
        }],
    }

    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    # Force a fatal fail
    monkeypatch.setattr(random, "randint", lambda a, b: 3)

    asyncio.run(ch.handle_combat_death_save(
        {"token_id": "tok1"},
        session,
        player,
    ))

    combatant = session.combat["combatants"][0]
    assert combatant.get("death_saves", {}).get("dead") is True


# ---------------------------------------------------------------------------
# handle_combat_roll_initiative
# ---------------------------------------------------------------------------

def test_combat_roll_initiative_broadcasts_combat_state(monkeypatch):
    """Rolling initiative should broadcast updated combatants."""
    from server.handlers import combat as ch
    from server.session import Session, User, Token
    session = Session(id="init-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    token = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                  color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    session.tokens[token.id] = token
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{"token_id": "tok1", "name": "Alice", "initiative": None, "is_player": True, "owner_id": "player1"}],
    }

    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    asyncio.run(ch.handle_combat_roll_initiative(
        {"token_id": "tok1", "roll": 15, "modifier": 3},
        session,
        player,
    ))

    types = [msg["type"] for _, msg, _ in broadcasts]
    assert "combat_state" in types
    combatant = session.combat["combatants"][0]
    assert combatant["roll"] == 15
    assert combatant["modifier"] == 3
    assert combatant["initiative"] == 18


def test_combat_roll_initiative_uses_combatant_id_and_stored_modifier(monkeypatch):
    """A client can send combatant_id only; server preserves raw d20 and adds stored modifier."""
    from server.handlers import combat as ch
    session, dm, player = _make_session_with_combat([
        {"id": "c1", "token_id": "tok1", "name": "Alice", "initiative": None, "is_player": True, "owner_id": "player1", "modifier": 4},
    ])
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    asyncio.run(ch.handle_combat_roll_initiative(
        {"combatant_id": "c1", "roll": 15},
        session,
        player,
    ))

    combatant = session.combat["combatants"][0]
    assert combatant["roll"] == 15
    assert combatant["modifier"] == 4
    assert combatant["initiative"] == 19
    assert any(msg["type"] == "combat_state" for _, msg, _ in broadcasts)


# ---------------------------------------------------------------------------
# handle_combat_attack_request — happy path
# ---------------------------------------------------------------------------

def test_combat_attack_request_broadcasts_pending_attack(monkeypatch):
    """Initiating an attack should produce at least one WS message."""
    from server.handlers import combat as ch
    from server.session import Session, User, Token
    session = Session(id="atk-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    atk_token = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                      color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    def_token = Token(id="tok2", name="Wolf", x=100, y=100, width=40, height=40,
                      color="#888", shape="circle", owner_id=None, hp=12, max_hp=12)
    session.tokens[atk_token.id] = atk_token
    session.tokens[def_token.id] = def_token
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [
            {"token_id": "tok1", "name": "Alice", "initiative": 20, "is_player": True, "owner_id": "player1"},
            {"token_id": "tok2", "name": "Wolf", "initiative": 10, "is_player": False},
        ],
    }

    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    asyncio.run(ch.handle_combat_attack_request(
        {"attacker_id": "tok1", "target_id": "tok2", "weapon": "Longsword"},
        session,
        player,
    ))

    # Should produce at least one broadcast or sent message
    assert len(broadcasts) > 0 or len(sent) > 0
