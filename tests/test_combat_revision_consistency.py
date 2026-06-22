import pytest

from server.session import Session, Token, User
from server.handlers import combat as combat_handlers


def _make_session_with_active_combatant(*, token_id="t1", owner_id="p1", speed=30, hp=10, max_hp=10):
    s = Session(id="s")
    u = User(id=owner_id, name="P", role="player")
    t = Token(
        id=token_id, name="Hero", x=0, y=0, width=50, height=50,
        color="#fff", shape="circle", owner_id=owner_id, speed=speed,
        hp=hp, max_hp=max_hp,
    )
    s.users[u.id] = u
    s.tokens[t.id] = t
    s.combat = {
        "active": True,
        "turn": 0,
        "round": 1,
        "revision": 0,
        "combatants": [
            {"token_id": token_id, "owner_id": owner_id, "name": "Hero", "speed": speed, "hp": hp, "max_hp": max_hp},
        ],
    }
    combat_handlers._ensure_combat_movement_state(s, reset=True)
    s.combat["revision"] = 0
    return s, u, t


@pytest.fixture
def patched(monkeypatch):
    """Stub out IO (websocket sends and save-to-disk) without breaking the
    module-level `manager` reference shared by combat.py and common.py."""
    sent = []
    broadcasts = []

    async def _fake_send_to(sid, uid, msg):
        sent.append((sid, uid, msg))
        return True

    async def _fake_broadcast(sid, msg):
        broadcasts.append((sid, msg))

    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _fake_broadcast)
    monkeypatch.setattr(combat_handlers.manager, "get_session_connections", lambda sid: {})

    async def _noop_save(session):
        return None

    monkeypatch.setattr(combat_handlers, "save_campaign_async", _noop_save)
    return type("Patched", (), {"sent": sent, "broadcasts": broadcasts})()


@pytest.mark.anyio
async def test_dash_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_dash({}, s, u)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_disengage_toggle_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_toggle_disengage({"enabled": True}, s, u)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_difficult_terrain_toggle_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_toggle_difficult_terrain({"enabled": True}, s, u)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_reset_movement_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    dm = User(id="dm1", name="DM", role="dm")
    s.users[dm.id] = dm
    await combat_handlers.handle_combat_dash({}, s, u)
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_reset_movement({}, s, dm)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_death_save_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant(hp=0, max_hp=10)
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_death_save({}, s, u)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_select_target_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    target = Token(id="t2", name="Target", x=10, y=10, width=50, height=50, color="#000", shape="circle", owner_id=None)
    s.tokens[target.id] = target
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_select_target({"target_id": "t2"}, s, u)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_move_preview_does_not_bump_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_move_preview(
        {"token_id": "t1", "to_x": 30, "to_y": 0, "expected_cost_ft": 3}, s, u
    )
    assert s.combat.get("revision") == before


@pytest.mark.anyio
async def test_end_turn_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    other = User(id="p2", name="P2", role="player")
    s.users[other.id] = other
    s.combat["combatants"].append({"token_id": "t-other", "owner_id": "p2", "name": "Other", "speed": 30})
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_end_turn({}, s, u)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_broadcast_combat_state_payload_includes_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    await combat_handlers.handle_combat_dash({}, s, u)
    patched.broadcasts.clear()
    await combat_handlers._broadcast_combat(s)
    state_broadcasts = [m for sid, m in patched.broadcasts if m.get("type") == "combat_state"]
    assert state_broadcasts, "expected a combat_state broadcast"
    assert state_broadcasts[-1]["payload"]["revision"] == s.combat.get("revision")


@pytest.mark.anyio
async def test_move_commit_advances_combat_revision_when_persisted(patched):
    s, u, t = _make_session_with_active_combatant()
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_move_commit(
        {"token_id": "t1", "to_x": 30, "to_y": 0, "expected_cost_ft": 5}, s, u
    )
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_clear_combat_advances_combat_revision(patched):
    s, u, t = _make_session_with_active_combatant()
    dm = User(id="dm1", name="DM", role="dm")
    s.users[dm.id] = dm
    before = s.combat.get("revision")
    await combat_handlers.handle_combat_clear({}, s, dm)
    assert s.combat.get("revision") == before + 1


@pytest.mark.anyio
async def test_repeated_mutations_produce_monotonically_increasing_revisions(patched):
    s, u, t = _make_session_with_active_combatant()
    dm = User(id="dm1", name="DM", role="dm")
    s.users[dm.id] = dm
    revisions = [s.combat.get("revision")]
    await combat_handlers.handle_combat_dash({}, s, u)
    revisions.append(s.combat.get("revision"))
    await combat_handlers.handle_combat_toggle_difficult_terrain({"enabled": True}, s, u)
    revisions.append(s.combat.get("revision"))
    await combat_handlers.handle_combat_toggle_disengage({"enabled": True}, s, u)
    revisions.append(s.combat.get("revision"))
    await combat_handlers.handle_combat_reset_movement({}, s, dm)
    revisions.append(s.combat.get("revision"))
    assert revisions == sorted(revisions)
    assert len(set(revisions)) == len(revisions)
