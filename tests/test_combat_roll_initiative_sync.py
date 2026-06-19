import json

import pytest

from server.handlers import combat as combat_handlers
from server.session import Session, Token, User


class _FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def accept(self):
        return None

    async def send_text(self, payload):
        self.sent.append(json.loads(payload))


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


async def _connect_real_sockets(session, *user_ids):
    sockets = {}
    for uid in user_ids:
        ws = _FakeWebSocket()
        await combat_handlers.manager.connect(session.id, uid, ws)
        sockets[uid] = ws
    return sockets


def _combat_state_messages(ws):
    return [m for m in ws.sent if m.get("type") == "combat_state"]


@pytest.mark.anyio
async def test_dm_npc_roll_reaches_dm_and_player_via_send_to(monkeypatch):
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect_real_sockets(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-npc", "roll": 11}, session, dm,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    dm_states = _combat_state_messages(sockets[dm.id])
    player_states = _combat_state_messages(sockets[player.id])
    assert dm_states, "DM (the roller) must receive the combat_state broadcast without refresh"
    assert player_states, "Other connected clients must also receive the combat_state broadcast"
    assert dm_states[-1]["payload"]["revision"] == session.combat["revision"]
    assert player_states[-1]["payload"]["revision"] == session.combat["revision"]


@pytest.mark.anyio
async def test_player_own_roll_reaches_player_and_dm_via_send_to(monkeypatch):
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect_real_sockets(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-hero", "roll": 15}, session, player,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    dm_states = _combat_state_messages(sockets[dm.id])
    player_states = _combat_state_messages(sockets[player.id])
    assert player_states, "The rolling player must receive the combat_state broadcast without refresh"
    assert dm_states, "DM must also receive the update"
    hero = next(c for c in player_states[-1]["payload"]["combatants"] if c["id"] == "cmb-hero")
    assert hero["initiative"] == 17


@pytest.mark.anyio
async def test_suspended_combatants_filtered_for_player_via_broadcast_combat(monkeypatch):
    session, dm, player = _build_session()
    session.combat["suspended_combatants"] = [{"id": "cmb-npc", "name": "Goblin", "suspended_reasons": ["fog"]}]
    session.combat["fog_suspended_combatants"] = [{"id": "cmb-npc", "name": "Goblin", "suspended_reasons": ["fog"]}]
    session.combat["hidden_suspended_combatants"] = []

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect_real_sockets(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-hero", "roll": 15}, session, player,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    dm_payload = _combat_state_messages(sockets[dm.id])[-1]["payload"]
    player_payload = _combat_state_messages(sockets[player.id])[-1]["payload"]
    assert "suspended_combatants" in dm_payload
    assert "suspended_combatants" not in player_payload
    assert "fog_suspended_combatants" not in player_payload
    assert "hidden_suspended_combatants" not in player_payload
