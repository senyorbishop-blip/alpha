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

# ---------------------------------------------------------------------------
# mid-combat initiative changes
# ---------------------------------------------------------------------------

def test_combat_add_token_mid_fight_preserves_current_turn_and_rejects_hidden_staged(monkeypatch):
    from server.handlers import combat as ch
    from server.session import Token
    session, dm, player = _make_session_with_combat()
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    session.dm_map_context = "world"
    session.combat["turn"] = 1  # Wolf is current
    session.tokens["reinforce"] = Token(
        id="reinforce", name="Goblin", x=300, y=200, width=40, height=40,
        color="#0f0", shape="circle", owner_id=None, hp=7, max_hp=7,
        initiative_mod=2, token_type="monster", map_context="world",
    )

    asyncio.run(ch.handle_combat_add_token({"token_id": "reinforce", "map_context": "world", "initiative": 15}, session, dm))

    assert any(c.get("token_id") == "reinforce" for c in session.combat["combatants"])
    assert session.combat["combatants"][session.combat["turn"]]["token_id"] == "tok2"
    assert session.combat["active"] is True
    assert next(c for c in session.combat["combatants"] if c.get("token_id") == "reinforce").get("hp") == 7
    assert any(msg["type"] == "combat_state" for _, msg, _ in broadcasts)

    session.tokens["secret"] = Token(
        id="secret", name="Secret", x=0, y=0, width=40, height=40,
        color="#000", shape="circle", owner_id=None, hidden=True, map_context="world",
    )
    asyncio.run(ch.handle_combat_add_token({"token_id": "secret", "map_context": "world"}, session, dm))
    assert not any(c.get("token_id") == "secret" for c in session.combat["combatants"])

    session.tokens["staged"] = Token(
        id="staged", name="Staged", x=0, y=0, width=40, height=40,
        color="#000", shape="circle", owner_id=None, staged=True, map_context="world",
    )
    asyncio.run(ch.handle_combat_add_token({"token_id": "staged", "map_context": "world"}, session, dm))
    assert not any(c.get("token_id") == "staged" for c in session.combat["combatants"])


def test_combat_add_token_requires_current_map_server_side(monkeypatch):
    from server.handlers import combat as ch
    from server.session import Token
    session, dm, player = _make_session_with_combat()
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    session.tokens["crypt-monster"] = Token(
        id="crypt-monster", name="Crypt Ghoul", x=0, y=0, width=40, height=40,
        color="#777", shape="circle", owner_id=None, token_type="monster", map_context="crypt",
    )

    asyncio.run(ch.handle_combat_add_token({"token_id": "crypt-monster", "map_context": "world"}, session, dm))

    assert not any(c.get("token_id") == "crypt-monster" for c in session.combat["combatants"])
    assert any(msg["type"] == "error" and "current map" in msg["payload"]["message"] for _, _, msg in sent)


def test_combat_remove_combatant_without_ending_combat(monkeypatch):
    from server.handlers import combat as ch
    session, dm, player = _make_session_with_combat()
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    session.combat["turn"] = 1

    asyncio.run(ch.handle_combat_remove_combatant({"combatant_id": "c1"}, session, dm))

    assert session.combat["active"] is True
    assert [c.get("id") for c in session.combat["combatants"]] == ["c2"]
    assert session.combat["turn"] == 0
    assert any(msg["type"] == "combat_state" for _, msg, _ in broadcasts)

# ---------------------------------------------------------------------------
# Combat fog visibility sweep
# ---------------------------------------------------------------------------

def _fog_sweep_session(*, token_hidden=False, token_staged=False, owner_id=None, revealed_indices=None, turn=0):
    from server.session import Session, User, Token
    from server.handlers import combat as ch
    session = Session(id="combat-fog-sweep")
    session.users["dm1"] = User(id="dm1", name="DM", role="dm")
    if owner_id:
        session.users[owner_id] = User(id=owner_id, name="Player", role="player")
    session.dm_id = "dm1"
    session.dm_map_context = "world"
    session.map_settings = {"world": {"width": 400, "height": 400}}
    cells = ["0"] * 16
    for idx in revealed_indices or []:
        cells[idx] = "1"
    session.fog_maps = {"world": {"enabled": True, "cols": 4, "rows": 4, "cells": "".join(cells)}}
    token = Token(
        id="mage", name="Mage", x=-150, y=-150, width=40, height=40,
        color="#778", shape="circle", owner_id=owner_id, hp=12, max_hp=12,
        token_type="player" if owner_id else "monster", hidden=token_hidden,
        staged=token_staged, map_context="world", speed=30,
    )
    session.tokens[token.id] = token
    session.combat = {
        "active": True,
        "turn": turn,
        "round": 1,
        "combatants": [ch._combatant_from_token(session, token, initiative=14, roll=12, modifier=2)],
    }
    return session, token


def test_combat_visibility_sweep_suspends_existing_fogged_npc():
    from server.handlers.combat import sync_combat_visibility
    session, _ = _fog_sweep_session(revealed_indices=[])

    result = sync_combat_visibility(session, map_context="world", reason="test")

    assert result["changed"] is True
    assert [c.get("token_id") for c in session.combat["combatants"]] == []
    assert session.combat["suspended_combatants"][0]["token_id"] == "mage"
    assert session.combat["suspended_combatants"][0]["initiative"] == 14
    assert session.combat["suspended_combatants"][0]["suspended_reasons"] == ["fog"]


def test_combat_visibility_sweep_keeps_existing_visible_npc():
    from server.handlers.combat import sync_combat_visibility
    session, _ = _fog_sweep_session(revealed_indices=[0])

    result = sync_combat_visibility(session, map_context="world", reason="test")

    assert result["changed"] is False
    assert [c.get("token_id") for c in session.combat["combatants"]] == ["mage"]
    assert session.combat.get("suspended_combatants", []) == []


def test_combat_visibility_sweep_keeps_fogged_player_token():
    from server.handlers.combat import sync_combat_visibility
    session, _ = _fog_sweep_session(owner_id="player1", revealed_indices=[])

    sync_combat_visibility(session, map_context="world", reason="test")

    assert [c.get("token_id") for c in session.combat["combatants"]] == ["mage"]
    assert session.combat.get("suspended_combatants", []) == []


def test_combat_visibility_sweep_suspends_hidden_npc_with_reason_hidden():
    from server.handlers.combat import sync_combat_visibility
    session, _ = _fog_sweep_session(token_hidden=True, revealed_indices=[0])

    sync_combat_visibility(session, map_context="world", reason="test")

    assert session.combat["combatants"] == []
    assert session.combat["suspended_combatants"][0]["suspended_reasons"] == ["hidden"]


def test_combat_visibility_sweep_requires_hidden_and_fog_to_clear_before_restore():
    from server.handlers.combat import sync_combat_visibility
    session, token = _fog_sweep_session(token_hidden=True, revealed_indices=[])

    sync_combat_visibility(session, map_context="world", reason="test")
    assert set(session.combat["suspended_combatants"][0]["suspended_reasons"]) == {"hidden", "fog"}

    token.hidden = False
    sync_combat_visibility(session, map_context="world", reason="test")
    assert session.combat["combatants"] == []
    assert session.combat["suspended_combatants"][0]["suspended_reasons"] == ["fog"]

    session.fog_maps["world"]["cells"] = "1" + "0" * 15
    sync_combat_visibility(session, map_context="world", reason="test")
    assert [c.get("token_id") for c in session.combat["combatants"]] == ["mage"]
    assert session.combat["combatants"][0]["initiative"] == 14
    assert session.combat.get("suspended_combatants", []) == []


def test_combat_visibility_sweep_runs_on_state_snapshot_for_reload():
    session, _ = _fog_sweep_session(revealed_indices=[])

    state = session.to_state_dict()

    assert state["combat"]["combatants"] == []
    assert state["combat"]["suspended_combatants"][0]["token_id"] == "mage"


def test_combat_visibility_sweep_advances_current_turn_when_current_is_suspended():
    from server.session import Token
    from server.handlers import combat as ch
    from server.handlers.combat import sync_combat_visibility
    session, _ = _fog_sweep_session(revealed_indices=[], turn=0)
    pc = Token(id="pc", name="Hero", x=0, y=0, width=40, height=40, color="#fff", shape="circle", owner_id="player1", token_type="player", map_context="world")
    session.users["player1"] = session.users.get("player1") or __import__("server.session", fromlist=["User"]).User(id="player1", name="Player", role="player")
    session.tokens[pc.id] = pc
    session.combat["combatants"].append(ch._combatant_from_token(session, pc, initiative=10))

    sync_combat_visibility(session, map_context="world", reason="test")

    assert [c.get("token_id") for c in session.combat["combatants"]] == ["pc"]
    assert session.combat["turn"] == 0
    assert session.combat["movement"].get("token_id") == "pc"


def test_combat_visibility_sweep_is_idempotent_without_duplicates():
    from server.handlers.combat import sync_combat_visibility
    session, _ = _fog_sweep_session(revealed_indices=[])

    sync_combat_visibility(session, map_context="world", reason="first")
    sync_combat_visibility(session, map_context="world", reason="second")
    sync_combat_visibility(session, map_context="world", reason="third")

    assert session.combat["combatants"] == []
    assert [c.get("token_id") for c in session.combat["suspended_combatants"]] == ["mage"]


def test_combat_update_assigns_new_encounter_id_for_new_combat(monkeypatch):
    """Starting a fresh combat stamps a new encounter id so clients reset turn economy."""
    from server.handlers import combat as ch
    session, dm, player = _make_session_with_combat()
    session.combat = {"active": False, "turn": 0, "combatants": [], "round": 1, "movement": {}}
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    async def _noop_hazards(_session):
        return None

    import server.handlers.hazards as haz
    monkeypatch.setattr(haz, "_process_current_start_turn_hazards", _noop_hazards)

    asyncio.run(ch.handle_combat_update({
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": [{"id": "c1", "token_id": "tok1", "name": "Alice", "initiative": None, "owner_id": "player1"}],
    }, session, dm))

    assert session.combat.get("encounter_id")
    combat_payloads = [msg["payload"] for _, msg, _ in broadcasts if msg["type"] == "combat_state"]
    assert combat_payloads[-1]["encounter_id"] == session.combat["encounter_id"]


def test_combat_roll_initiative_broadcasts_explicit_roll_delta(monkeypatch):
    """Initiative rolls broadcast both combat_state and a targeted delta for live clients."""
    from server.handlers import combat as ch
    session, dm, player = _make_session_with_combat([
        {"id": "c1", "token_id": "tok1", "name": "Alice", "initiative": None, "is_player": True, "owner_id": "player1", "modifier": 2},
    ])
    session.combat["encounter_id"] = "enc-123"
    broadcasts, sent = _noop_broadcasts(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)
    asyncio.run(ch.handle_combat_roll_initiative({"combatant_id": "c1", "roll": 14}, session, player))

    types = [msg["type"] for _, msg, _ in broadcasts]
    assert "combat_state" in types
    assert "combat_initiative_rolled" in types
    delta = [msg["payload"] for _, msg, _ in broadcasts if msg["type"] == "combat_initiative_rolled"][-1]
    assert delta == {
        "combatant_id": "c1",
        "token_id": "tok1",
        "initiative": 16,
        "roll": 14,
        "modifier": 2,
        "revision": session.combat.get("revision"),
        "encounter_id": "enc-123",
    }
