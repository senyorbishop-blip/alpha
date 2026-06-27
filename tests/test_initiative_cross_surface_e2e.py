"""Cross-client regression coverage for combat_state as the sole initiative
authority (PR 298 dual-path regression). A foreign client's initiative roll
must reach every other connected client through exactly one combat_state
broadcast, and a client that reconnects mid-encounter must pull correct
authoritative state with a single request/response — never a stale roster
patched in-place by a notification-only event.
"""
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
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": player.id, "initiative": 5, "roll": 5, "modifier": 0},
            {"id": "cmb-npc", "token_id": "npc", "name": "Goblin", "owner_id": None, "initiative": None, "roll": None, "modifier": 0},
        ],
    }
    return session, dm, player


async def _connect(session, *user_ids):
    sockets = {}
    for uid in user_ids:
        ws = _FakeWebSocket()
        await combat_handlers.manager.connect(session.id, uid, ws)
        sockets[uid] = ws
    return sockets


def _combat_states(ws):
    return [m for m in ws.sent if m.get("type") == "combat_state"]


def _initiative_notifications(ws):
    return [m for m in ws.sent if m.get("type") == "combat_initiative_rolled"]


@pytest.mark.anyio
async def test_foreign_npc_roll_reaches_every_client_in_one_broadcast(monkeypatch):
    """Client B (the DM) rolls initiative for an NPC. Client A (the player)
    must see the new order from the single resulting combat_state broadcast
    — no separate per-surface fetch, no stale roster."""
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-npc", "roll": 20}, session, dm,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    player_states = _combat_states(sockets[player.id])
    assert len(player_states) == 1, "exactly one combat_state broadcast must reach the player from a single roll"
    order = [c["id"] for c in player_states[-1]["payload"]["combatants"]]
    assert order == ["cmb-npc", "cmb-hero"], "goblin's 20 must outrank hero's locked-in 5 in the broadcast roster"
    assert player_states[-1]["payload"]["combatants"][0]["initiative"] == 20


@pytest.mark.anyio
async def test_initiative_rolled_notification_payload_cannot_carry_a_roster(monkeypatch):
    """combat_initiative_rolled is delivered privately to the roller alongside
    the table-wide combat_state, but its payload must be structurally
    notification-only (no combatants/turn/round) so that a client which only
    sees this message (e.g. the accompanying combat_state was dropped/reordered)
    has nothing in the payload it could use to mutate the roster. Non-roller
    clients must not receive the notification at all."""
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-npc", "roll": 20}, session, dm,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    # The DM is the roller, so only the DM receives the private notification.
    notifications = _initiative_notifications(sockets[dm.id])
    assert notifications, "the roller must still receive the notification for animation/log purposes"
    payload = notifications[-1]["payload"]
    assert "combatants" not in payload
    assert "turn" not in payload
    assert "round" not in payload
    # The non-rolling player must not see the roller's private popup/animation.
    assert not _initiative_notifications(sockets[player.id])


@pytest.mark.anyio
async def test_player_reconnect_mid_encounter_pulls_correct_state_exactly_once(monkeypatch):
    """A player who reconnects after missing a foreign roll must, on a single
    combat_state_request, receive the fully up-to-date authoritative roster
    — not a stale snapshot, and not more than one reply."""
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    # Player is offline while the DM rolls for the NPC.
    dm_ws = _FakeWebSocket()
    await combat_handlers.manager.connect(session.id, dm.id, dm_ws)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-npc", "roll": 20}, session, dm,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)

    # Player reconnects and issues a single resync request.
    player_ws = _FakeWebSocket()
    await combat_handlers.manager.connect(session.id, player.id, player_ws)
    try:
        await combat_handlers.handle_combat_state_request({}, session, player)
    finally:
        combat_handlers.manager.disconnect(session.id, player.id)

    states = _combat_states(player_ws)
    assert len(states) == 1, "a single combat_state_request must yield exactly one reply"
    order = [c["id"] for c in states[0]["payload"]["combatants"]]
    assert order == ["cmb-npc", "cmb-hero"]
    assert states[0]["payload"]["combatants"][0]["initiative"] == 20
