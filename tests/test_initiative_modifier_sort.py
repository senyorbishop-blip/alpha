"""Regression coverage for modifier-inclusive initiative ordering.

This is the bug that survived from the early initiative PRs: a rolled
initiative must rank by (d20 roll + modifier), the highest total must move to
the top of the roster, and that authoritative order must reach EVERY connected
client live in a single combat_state broadcast (the roller included) — never
only after a manual refresh.

The sibling file test_initiative_cross_surface_e2e.py proves a flat d20 roll
reaches every client. These tests specifically pin the *modifier* behaviour:
a low roll with a high modifier must out-rank a higher raw roll, including when
the modifier is not in the payload but stored on the combatant (the usual case
for a player rolling for their own character token).
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
    # Hero already has a locked-in flat 18 (roll 18, no modifier).
    # Goblin carries a +5 initiative modifier and has not rolled yet.
    session.combat = {
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": player.id, "initiative": 18, "roll": 18, "modifier": 0},
            {"id": "cmb-npc", "token_id": "npc", "name": "Goblin", "owner_id": None, "initiative": None, "roll": None, "modifier": 5},
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


def _order_and_top(state_msg):
    coms = state_msg["payload"]["combatants"]
    return [c["id"] for c in coms], coms[0]


@pytest.mark.anyio
async def test_modifier_can_outrank_a_higher_raw_roll(monkeypatch):
    """DM rolls 15 for the Goblin. 15 + 5 = 20 must beat the Hero's flat 18,
    so the Goblin moves to the top of the broadcast roster for both clients."""
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-npc", "roll": 15, "modifier": 5}, session, dm,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    # Server roster total reflects roll + modifier.
    npc = next(c for c in session.combat["combatants"] if c["id"] == "cmb-npc")
    assert npc["initiative"] == 20
    assert npc["roll"] == 15
    assert npc["modifier"] == 5

    # Both clients receive exactly one authoritative combat_state with the
    # modifier-boosted Goblin on top.
    for who, ws in (("player", sockets[player.id]), ("dm", sockets[dm.id])):
        states = _combat_states(ws)
        assert len(states) == 1, f"{who} must get exactly one combat_state from one roll"
        order, top = _order_and_top(states[-1])
        assert order == ["cmb-npc", "cmb-hero"], f"{who} roster: 20 must outrank 18"
        assert top["initiative"] == 20


@pytest.mark.anyio
async def test_player_rolling_own_character_uses_stored_modifier(monkeypatch):
    """A player rolls for their own character token and the payload carries no
    modifier. The combatant's stored modifier must still be applied, and the
    total (roll + stored modifier) must rank the roster for every client."""
    session, dm, player = _build_session()
    # Give the Hero a +4 stored modifier and clear the locked-in initiative so
    # the player is rolling fresh. Goblin sits at a flat 19.
    hero = next(c for c in session.combat["combatants"] if c["id"] == "cmb-hero")
    hero["initiative"] = None
    hero["roll"] = None
    hero["modifier"] = 4
    goblin = next(c for c in session.combat["combatants"] if c["id"] == "cmb-npc")
    goblin["initiative"] = 19
    goblin["roll"] = 19
    goblin["modifier"] = 0

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        # Player sends roll only — NO modifier in the payload.
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-hero", "roll": 17}, session, player,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    hero = next(c for c in session.combat["combatants"] if c["id"] == "cmb-hero")
    assert hero["initiative"] == 21, "17 + stored modifier 4 must total 21"

    for who, ws in (("player", sockets[player.id]), ("dm", sockets[dm.id])):
        states = _combat_states(ws)
        assert len(states) == 1, f"{who} must get exactly one combat_state"
        order, top = _order_and_top(states[-1])
        assert order == ["cmb-hero", "cmb-npc"], f"{who} roster: hero 21 must outrank goblin 19"
        assert top["initiative"] == 21


@pytest.mark.anyio
async def test_equal_totals_keep_both_combatants_and_do_not_drop_a_row(monkeypatch):
    """A tie on total initiative must not drop or duplicate a combatant; both
    rows survive and the rolled total is stored."""
    session, dm, player = _build_session()
    # Hero flat 20; Goblin rolls 15 + 5 = 20 (a tie).
    hero = next(c for c in session.combat["combatants"] if c["id"] == "cmb-hero")
    hero["initiative"] = 20
    hero["roll"] = 20
    hero["modifier"] = 0

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    sockets = await _connect(session, dm.id, player.id)
    try:
        await combat_handlers.handle_combat_roll_initiative(
            {"combatant_id": "cmb-npc", "roll": 15, "modifier": 5}, session, dm,
        )
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    states = _combat_states(sockets[player.id])
    assert len(states) == 1
    order, _top = _order_and_top(states[-1])
    assert set(order) == {"cmb-hero", "cmb-npc"}
    assert len(order) == 2, "a tie must not drop or duplicate a combatant"
    npc = next(c for c in states[-1]["payload"]["combatants"] if c["id"] == "cmb-npc")
    assert npc["initiative"] == 20
