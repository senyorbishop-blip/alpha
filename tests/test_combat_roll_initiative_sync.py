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
    session.combat["turn_locked"] = True
    session.combat["turn_started"] = True
    _patch_io(monkeypatch, [], [])

    # Hero is currently active (turn 0) in an already-started round. Goblin rolls higher initiative and
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

@pytest.mark.anyio
async def test_roll_initiative_emits_dice_result_popup(monkeypatch):
    """Initiative must drive the shared dice_result popup path so the roll shows
    consistently for the DM and every player, with the correct roll/modifier/total."""
    session, dm, player = _build_session()
    broadcasts = []

    async def _fake_broadcast_combat(session):
        return None

    async def _fake_manager_broadcast(*args, **kwargs):
        # broadcast(session_id, message[, exclude_user])
        broadcasts.append(args[1] if len(args) > 1 else kwargs.get("message"))

    async def _fake_send_to(*args, **kwargs):
        return None

    async def _fake_save(*args, **kwargs):
        return True

    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _fake_broadcast_combat)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _fake_manager_broadcast)
    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 15, "modifier": 2, "roll_id": "rid-init-1"},
        session,
        player,
    )

    dice = [m for m in broadcasts if m and m.get("type") == "dice_result"]
    assert dice, "initiative roll must broadcast a dice_result popup event"
    p = dice[-1]["payload"]
    assert p["user_id"] == player.id
    assert p["user_name"] == player.name
    assert p["dice_type"] == 20
    assert p["quantity"] == 1
    assert p["rolls"] == [15]
    assert p["modifier"] == 2
    assert p["total"] == 17, "d20 roll + modifier must equal total"
    assert p["roll_label"] == "Hero initiative"
    assert p["combatant_id"] == "cmb-hero"
    assert p["token_id"] == "hero"
    assert p["roll_id"] == "rid-init-1"
    assert p["revision"] == session.combat["revision"]


@pytest.mark.anyio
async def test_roll_initiative_authoritative_value_matches_dice_result(monkeypatch):
    """The combat list initiative value must equal the dice_result total."""
    session, dm, player = _build_session()
    broadcasts = []

    async def _fake_broadcast_combat(session):
        return None

    async def _fake_manager_broadcast(*args, **kwargs):
        broadcasts.append(args[1] if len(args) > 1 else kwargs.get("message"))

    async def _fake_send_to(*args, **kwargs):
        return None

    async def _fake_save(*args, **kwargs):
        return True

    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _fake_broadcast_combat)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _fake_manager_broadcast)
    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-npc", "roll": 9, "modifier": 0, "roll_id": "rid-npc"},
        session,
        dm,
    )

    npc = next(c for c in session.combat["combatants"] if c["id"] == "cmb-npc")
    dice = [m for m in broadcasts if m and m.get("type") == "dice_result"][-1]["payload"]
    assert npc["initiative"] == dice["total"] == 9


@pytest.mark.anyio
async def test_combat_state_request_replies_to_requesting_user_with_current_state(monkeypatch):
    session, dm, player = _build_session()
    sent = []

    async def _fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))
        return True

    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)

    await combat_handlers.handle_combat_state_request({}, session, player)

    assert sent
    session_id, user_id, message = sent[-1]
    assert session_id == session.id
    assert user_id == player.id
    assert message["type"] == "combat_state"
    payload = message["payload"]
    assert payload["active"] is True
    assert payload["round"] == 1
    assert payload["turn"] == 0
    assert "combatants" in payload
    assert payload["combatants"][0]["initiative"] is None
    assert "visibility_revision" in payload

@pytest.mark.anyio
async def test_initial_setup_roll_sorts_and_sets_highest_turn(monkeypatch):
    session, dm, player = _build_session()
    session.tokens["mage"] = Token(id="mage", name="Mage", x=0, y=0, width=1, height=1, color="#fff", shape="circle", owner_id=None, token_type="npc")
    session.combat["combatants"] = [
        {"id": "cmb-guard", "token_id": "npc", "name": "Guard", "owner_id": None, "initiative": None, "roll": None, "modifier": 0},
        {"id": "cmb-bishop", "token_id": "hero", "name": "Bishop", "owner_id": player.id, "initiative": None, "roll": None, "modifier": 0},
        {"id": "cmb-mage", "token_id": "mage", "name": "Mage", "owner_id": None, "initiative": None, "roll": None, "modifier": 0},
    ]
    broadcasts = []
    _patch_io(monkeypatch, broadcasts, [])

    await combat_handlers.handle_combat_roll_initiative({"combatant_id": "cmb-guard", "roll": 6}, session, dm)
    await combat_handlers.handle_combat_roll_initiative({"combatant_id": "cmb-bishop", "roll": 14}, session, dm)

    assert [c["id"] for c in session.combat["combatants"]][:2] == ["cmb-bishop", "cmb-guard"]
    assert session.combat["turn"] == 0
    assert session.combat["combatants"][session.combat["turn"]]["id"] == "cmb-bishop"
    assert broadcasts[-1]["combatants"][0]["initiative"] == 14
    assert broadcasts[-1]["turn"] == 0


@pytest.mark.anyio
async def test_mid_combat_initialized_reroll_preserves_locked_active_turn(monkeypatch):
    session, dm, player = _build_session()
    session.combat.update({"turn": 1, "turn_locked": True, "turn_started": True})
    session.combat["combatants"] = [
        {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": player.id, "initiative": 12, "roll": 10, "modifier": 2},
        {"id": "cmb-npc", "token_id": "npc", "name": "Goblin", "owner_id": None, "initiative": 8, "roll": 8, "modifier": 0},
    ]
    _patch_io(monkeypatch, [], [])

    await combat_handlers.handle_combat_roll_initiative({"combatant_id": "cmb-hero", "roll": 1, "modifier": 0}, session, dm)

    assert [c["id"] for c in session.combat["combatants"]] == ["cmb-npc", "cmb-hero"]
    assert session.combat["combatants"][session.combat["turn"]]["id"] == "cmb-npc"

@pytest.mark.anyio
async def test_broadcast_combat_counts_only_successful_send_to(monkeypatch):
    session, dm, player = _build_session()
    calls = []

    async def _fake_send_to(session_id, user_id, message):
        calls.append((user_id, message))
        return user_id == dm.id

    monkeypatch.setattr(combat_handlers.manager, "get_session_connections", lambda session_id: {dm.id: object(), player.id: object()})
    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)

    result = await combat_handlers._broadcast_combat(session)

    assert result["sent_to"] == [dm.id]
    assert result["failed"] == [player.id]
    assert [uid for uid, _ in calls] == [dm.id, player.id]


@pytest.mark.anyio
async def test_replacing_same_user_socket_closes_old_and_new_receives_combat_state(monkeypatch):
    session, dm, player = _build_session()

    async def _fake_save(*args, **kwargs):
        return True
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)

    old_ws = _FakeWebSocket()
    old_ws.closed = []
    async def _close(code=1000, reason=""):
        old_ws.closed.append({"code": code, "reason": reason})
    old_ws.close = _close

    new_ws = _FakeWebSocket()
    await combat_handlers.manager.connect(session.id, dm.id, old_ws, role=dm.role)
    await combat_handlers.manager.connect(session.id, dm.id, new_ws, role=dm.role)
    await combat_handlers.manager.connect(session.id, player.id, _FakeWebSocket(), role=player.role)
    try:
        await combat_handlers.handle_combat_roll_initiative({"combatant_id": "cmb-npc", "roll": 18}, session, dm)
    finally:
        combat_handlers.manager.disconnect(session.id, dm.id)
        combat_handlers.manager.disconnect(session.id, player.id)

    assert old_ws.closed and old_ws.closed[-1]["code"] == 1001
    assert not _combat_state_messages(old_ws), "replaced stale tab must not receive future combat_state"
    assert _combat_state_messages(new_ws), "new visible socket must receive combat_state"
