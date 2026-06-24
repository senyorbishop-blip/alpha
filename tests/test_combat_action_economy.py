import pytest

from server.session import Session, Token, User
from server.handlers import combat as combat_handlers
from server.handlers.common import _combat_state_payload_for_user


class DummyManager:
    def __init__(self):
        self.sent = []
        self.broadcasts = []
    async def send_to(self, sid, uid, msg):
        self.sent.append((sid, uid, msg))
        return True
    async def broadcast(self, sid, msg):
        self.broadcasts.append((sid, msg))
        return True
    def get_session_connections(self, sid):
        return {}


@pytest.fixture
def combat_session(monkeypatch):
    dummy = DummyManager()
    monkeypatch.setattr(combat_handlers, "manager", dummy)
    async def _noop_save(session):
        return None
    async def _noop_broadcast(session):
        return None
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _noop_save)
    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _noop_broadcast)
    s = Session(id="s")
    player = User(id="p1", name="Player", role="player")
    dm = User(id="dm", name="DM", role="dm")
    other = User(id="p2", name="Other", role="player")
    s.users[player.id] = player
    s.users[dm.id] = dm
    s.users[other.id] = other
    t1 = Token(id="t1", name="Hero", x=0, y=0, width=50, height=50, color="#fff", shape="circle", owner_id="p1", speed=30)
    t2 = Token(id="t2", name="Ally", x=50, y=0, width=50, height=50, color="#fff", shape="circle", owner_id="p2", speed=30)
    s.tokens[t1.id] = t1
    s.tokens[t2.id] = t2
    s.combat = {"active": True, "turn": 0, "round": 1, "combatants": [
        {"id": "c1", "token_id": "t1", "owner_id": "p1", "name": "Hero", "speed": 30},
        {"id": "c2", "token_id": "t2", "owner_id": "p2", "name": "Ally", "speed": 30},
    ]}
    combat_handlers._sync_action_economy_roster(s)
    combat_handlers._reset_action_economy_for_turn_start(s)
    return s, player, dm, other, dummy


@pytest.mark.anyio
async def test_player_cannot_spend_two_actions_same_turn(combat_session):
    s, player, _dm, _other, dummy = combat_session
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "action"}, s, player)
    assert s.combat["combat_action_economy"]["t1"]["action_used"] is True
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "action"}, s, player)
    assert dummy.sent[-1][2]["type"] == "error"
    assert "already spent" in dummy.sent[-1][2]["payload"]["message"]


@pytest.mark.anyio
async def test_bonus_action_tracked_separately(combat_session):
    s, player, _dm, _other, _dummy = combat_session
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "bonus_action"}, s, player)
    entry = s.combat["combat_action_economy"]["t1"]
    assert entry["bonus_action_used"] is True
    assert entry["action_used"] is False


@pytest.mark.anyio
async def test_reaction_tracked_separately(combat_session):
    s, player, _dm, _other, _dummy = combat_session
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "reaction"}, s, player)
    entry = s.combat["combat_action_economy"]["t1"]
    assert entry["reaction_used"] is True
    assert entry["action_used"] is False
    assert entry["bonus_action_used"] is False


@pytest.mark.anyio
async def test_turn_advance_resets_new_active_fields(combat_session):
    s, player, dm, _other, _dummy = combat_session
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "action"}, s, player)
    s.combat["combat_action_economy"]["t2"].update({"action_used": True, "bonus_action_used": True, "reaction_used": True})
    await combat_handlers.handle_combat_next({}, s, dm)
    assert s.combat["turn"] == 1
    entry = s.combat["combat_action_economy"]["t2"]
    assert entry["action_used"] is False
    assert entry["bonus_action_used"] is False
    assert entry["reaction_used"] is False
    assert s.combat["combat_action_economy"]["t1"]["action_used"] is True


@pytest.mark.anyio
async def test_dm_override_and_reset_work(combat_session):
    s, player, dm, _other, _dummy = combat_session
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "action"}, s, player)
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "action_type": "action", "override": True}, s, dm)
    assert s.combat["combat_action_economy"]["t1"]["action_used"] is True
    await combat_handlers.handle_combat_action_economy_use({"token_id": "t1", "reset": True}, s, dm)
    assert s.combat["combat_action_economy"]["t1"]["action_used"] is False


def test_reconnect_payload_preserves_action_economy(combat_session):
    s, player, _dm, _other, _dummy = combat_session
    ok, reason, _entry = combat_handlers._mark_action_economy(s, "t1", "ready_action", note="Shoot first", combatant=s.combat["combatants"][0])
    assert ok, reason
    payload = _combat_state_payload_for_user(s, player)
    assert payload["combat_action_economy"]["t1"]["action_used"] is True
    assert payload["combat_action_economy"]["t1"]["ready_action"]["note"] == "Shoot first"
