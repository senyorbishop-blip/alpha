import pytest

from server.handlers import combat as combat_handlers
from server.session import Session, Token, User


def _build_session():
    session = Session(id="s1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="u1", name="Player One", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.tokens["hero"] = Token(
        id="hero", name="Hero", x=0, y=0, width=1, height=1,
        color="#fff", shape="circle", owner_id=player.id,
    )
    session.tokens["npc"] = Token(
        id="npc", name="Goblin", x=0, y=0, width=1, height=1,
        color="#fff", shape="circle", owner_id=None, token_type="npc",
    )
    session.combat = {
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": player.id, "initiative": None, "roll": None, "modifier": 2},
            {"id": "cmb-npc", "token_id": "npc", "name": "Goblin", "owner_id": None, "initiative": None, "roll": None, "modifier": 0},
        ],
    }
    return session, dm, player


def _patch_io(monkeypatch, broadcast_calls, manager_broadcast_calls):
    async def _fake_broadcast_combat(session):
        broadcast_calls.append(dict(session.combat))

    async def _fake_manager_broadcast(*args, **kwargs):
        manager_broadcast_calls.append((args, kwargs))

    async def _fake_send_to(*args, **kwargs):
        return None

    async def _fake_save(*args, **kwargs):
        return True

    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _fake_broadcast_combat)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _fake_manager_broadcast)
    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)


@pytest.mark.anyio
async def test_roll_initiative_updates_combatant(monkeypatch):
    session, dm, player = _build_session()
    _patch_io(monkeypatch, [], [])

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 15}, session, player,
    )

    hero = next(c for c in session.combat["combatants"] if c["id"] == "cmb-hero")
    assert hero["roll"] == 15
    assert hero["modifier"] == 2
    assert hero["initiative"] == 17


@pytest.mark.anyio
async def test_roll_initiative_uses_canonical_broadcast_combat(monkeypatch):
    session, dm, player = _build_session()
    broadcast_calls = []
    manager_broadcast_calls = []
    _patch_io(monkeypatch, broadcast_calls, manager_broadcast_calls)

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 15}, session, player,
    )

    assert len(broadcast_calls) == 1
    # manager.broadcast should only be used for the log_entry, never for raw combat_state.
    assert all(
        (args[1].get("type") if len(args) > 1 else kwargs.get("message", {}).get("type")) != "combat_state"
        for args, kwargs in manager_broadcast_calls
    )


@pytest.mark.anyio
async def test_roll_initiative_increments_combat_revision(monkeypatch):
    session, dm, player = _build_session()
    _patch_io(monkeypatch, [], [])
    assert session.combat.get("revision") is None

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 15}, session, player,
    )
    assert session.combat["revision"] == 1

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-npc", "roll": 10}, session, dm,
    )
    assert session.combat["revision"] == 2


@pytest.mark.anyio
async def test_roll_initiative_sort_preserves_active_combatant(monkeypatch):
    session, dm, player = _build_session()
    _patch_io(monkeypatch, [], [])

    # Hero is currently active (turn 0). Goblin rolls higher initiative and
    # should move ahead in order, but turn index should still point at Hero.
    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-npc", "roll": 20}, dm and session, dm,
    )
    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 1}, session, player,
    )

    coms = session.combat["combatants"]
    current = coms[session.combat["turn"]]
    assert current["id"] == "cmb-hero"
    assert coms[0]["id"] == "cmb-npc"


@pytest.mark.anyio
async def test_player_can_only_roll_own_initiative(monkeypatch):
    session, dm, player = _build_session()
    sent_errors = []

    async def _fake_send_to(session_id, user_id, message):
        sent_errors.append(message)

    async def _fake_broadcast_combat(session):
        return None

    async def _fake_save(*args, **kwargs):
        return True

    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _fake_broadcast_combat)
    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _fake_broadcast_combat)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-npc", "roll": 11}, session, player,
    )

    npc = next(c for c in session.combat["combatants"] if c["id"] == "cmb-npc")
    assert npc["initiative"] is None
    assert sent_errors and sent_errors[0]["type"] == "error"


@pytest.mark.anyio
async def test_dm_can_roll_npc_initiative(monkeypatch):
    session, dm, player = _build_session()
    _patch_io(monkeypatch, [], [])

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-npc", "roll": 11}, session, dm,
    )

    npc = next(c for c in session.combat["combatants"] if c["id"] == "cmb-npc")
    assert npc["initiative"] == 11
