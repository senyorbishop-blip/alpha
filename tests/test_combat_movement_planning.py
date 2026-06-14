import pytest

from server.movement import resolve_movement, build_grid_path
from server.session import Session, Token, User
from server.handlers import combat as combat_handlers


def test_grid_movement_costs_and_modes():
    one = resolve_movement(from_x=0, from_y=0, to_x=50, to_y=0)
    assert one["finalCostFeet"] == 5
    six = resolve_movement(from_x=0, from_y=0, to_x=300, to_y=0)
    assert six["finalCostFeet"] == 30
    diag_default = resolve_movement(from_x=0, from_y=0, to_x=300, to_y=300, movement_mode="grid_5e_default")
    assert diag_default["finalCostFeet"] == 30
    diag_alt = resolve_movement(from_x=0, from_y=0, to_x=300, to_y=300, movement_mode="grid_5_10_5")
    assert diag_alt["finalCostFeet"] == 45
    difficult = resolve_movement(from_x=0, from_y=0, to_x=50, to_y=0, difficult_terrain=True)
    assert difficult["finalCostFeet"] == 10
    dashed = resolve_movement(from_x=0, from_y=0, to_x=600, to_y=0, speed_feet=30, bonus_feet=30)
    assert dashed["speedFeet"] == 60
    assert dashed["valid"] is True


class DummyManager:
    def __init__(self):
        self.sent = []
        self.broadcasts = []
    async def send_to(self, sid, uid, msg):
        self.sent.append((sid, uid, msg))
    async def broadcast(self, sid, msg):
        self.broadcasts.append((sid, msg))


@pytest.mark.anyio
async def test_preview_matches_commit_and_invalid_does_not_move(monkeypatch):
    dummy = DummyManager()
    monkeypatch.setattr(combat_handlers, "manager", dummy)
    async def _noop_save(session):
        return None
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _noop_save)
    s = Session(id="s")
    u = User(id="p1", name="P", role="player")
    t = Token(id="t1", name="Hero", x=0, y=0, width=50, height=50, color="#fff", shape="circle", owner_id="p1", speed=30)
    s.users[u.id] = u
    s.tokens[t.id] = t
    s.combat = {"active": True, "turn": 0, "round": 1, "combatants": [{"token_id": "t1", "owner_id": "p1", "name": "Hero", "speed": 30}]}
    combat_handlers._ensure_combat_movement_state(s, reset=True)
    path = build_grid_path({"x": 0, "y": 0}, {"x": 6, "y": 0})
    await combat_handlers.handle_combat_move_preview({"token_id": "t1", "to_x": 300, "to_y": 0, "path": path, "expected_cost_ft": 30}, s, u)
    assert t.x == 0 and t.y == 0
    assert dummy.sent[-1][2]["payload"]["resolver"]["finalCostFeet"] == 30
    await combat_handlers.handle_combat_move_commit({"token_id": "t1", "to_x": 300, "to_y": 0, "path": path, "expected_cost_ft": 30}, s, u)
    assert t.x == 300 and t.y == 0
    assert s.combat["movement"]["spent_ft"] == 30
    assert s.combat["movement"]["remaining_ft"] == 0
    await combat_handlers.handle_combat_move_commit({"token_id": "t1", "to_x": 350, "to_y": 0, "expected_cost_ft": 5}, s, u)
    assert t.x == 300 and t.y == 0
    assert dummy.sent[-1][2]["type"] == "token_move_denied"


@pytest.mark.anyio
async def test_not_your_turn_blocked_before_real_movement(monkeypatch):
    dummy = DummyManager()
    monkeypatch.setattr(combat_handlers, "manager", dummy)
    s = Session(id="s")
    u = User(id="p1", name="P", role="player")
    t = Token(id="t1", name="Hero", x=0, y=0, width=50, height=50, color="#fff", shape="circle", owner_id="p1", speed=30)
    s.users[u.id] = u
    s.tokens[t.id] = t
    s.combat = {"active": True, "turn": 0, "round": 1, "combatants": [{"token_id": "other", "owner_id": "p2", "name": "Other", "speed": 30}]}
    await combat_handlers.handle_combat_move_commit({"token_id": "t1", "to_x": 50, "to_y": 0, "expected_cost_ft": 5}, s, u)
    assert t.x == 0 and t.y == 0
    assert "Not your turn" in dummy.sent[-1][2]["payload"]["message"]
