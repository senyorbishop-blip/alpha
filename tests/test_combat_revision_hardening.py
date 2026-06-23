import pytest

from server.session import Session, Token, User
from server.handlers import combat as combat_handlers
from server.handlers.common import _combat_state_payload_for_user


def _token(id, name, *, hidden=False, owner_id=None, token_type="monster"):
    return Token(id=id, name=name, x=0, y=0, width=50, height=50, color="#999", shape="circle", hidden=hidden, owner_id=owner_id, token_type=token_type, hp=7, max_hp=10, speed=30, map_context="world")


def _session():
    s = Session(id="combat-hardening")
    s.users["dm"] = User(id="dm", name="DM", role="dm")
    s.users["p1"] = User(id="p1", name="Player", role="player")
    s.users["v1"] = User(id="v1", name="Viewer", role="viewer")
    hero = _token("hero", "Bishop", owner_id="p1", token_type="player")
    guard = _token("guard", "Guard")
    hidden = _token("hidden", "Secret Assassin", hidden=True)
    s.tokens = {t.id: t for t in (hero, guard, hidden)}
    s.combat = {
        "active": True,
        "turn": 0,
        "round": 1,
        "revision": 3,
        "updated_at": 123.0,
        "combatants": [
            {"id": "c-hero", "token_id": "hero", "name": "Bishop", "initiative": 15, "owner_id": "p1"},
            {"id": "c-guard", "token_id": "guard", "name": "Guard", "initiative": 12},
            {"id": "c-hidden", "token_id": "hidden", "name": "Secret Assassin", "initiative": 20},
        ],
    }
    s.visibility_revision = 9
    return s


@pytest.fixture
def patched(monkeypatch):
    sent = []
    async def fake_send_to(sid, uid, msg):
        sent.append((sid, uid, msg)); return True
    monkeypatch.setattr(combat_handlers.manager, "send_to", fake_send_to)
    monkeypatch.setattr(combat_handlers.manager, "get_session_connections", lambda sid: {})
    async def noop_save(session): return None
    monkeypatch.setattr(combat_handlers, "save_campaign_async", noop_save)
    return sent


@pytest.mark.anyio
async def test_turn_mutations_and_state_request_include_revisions(patched):
    s = _session(); dm = s.users["dm"]
    before = s.combat["revision"]
    await combat_handlers.handle_combat_next({}, s, dm)
    assert s.combat["revision"] == before + 1
    await combat_handlers.handle_combat_prev({}, s, dm)
    assert s.combat["revision"] == before + 2
    await combat_handlers.handle_combat_state_request({}, s, dm)
    payload = patched[-1][2]["payload"]
    assert payload["revision"] == s.combat["revision"]
    assert payload["active"] is True
    assert "updated_at" in payload
    assert payload["visibility_revision"] >= 9


@pytest.mark.anyio
async def test_clear_combat_newer_inactive_revision(patched):
    s = _session(); dm = s.users["dm"]
    before = s.combat["revision"]
    await combat_handlers.handle_combat_clear({}, s, dm)
    assert s.combat["revision"] == before + 1
    assert s.combat["active"] is False
    assert s.combat["updated_at"] > 0


def test_role_filtered_combat_payloads_and_snapshot_do_not_leak_hidden_npc():
    s = _session()
    dm_payload = _combat_state_payload_for_user(s, s.users["dm"], s.visibility_revision)
    player_payload = _combat_state_payload_for_user(s, s.users["p1"], s.visibility_revision)
    viewer_payload = _combat_state_payload_for_user(s, s.users["v1"], s.visibility_revision)
    assert {c["token_id"] for c in dm_payload["combatants"]} == {"hero", "guard", "hidden"}
    assert {c["token_id"] for c in player_payload["combatants"]} == {"hero", "guard"}
    assert {c["token_id"] for c in viewer_payload["combatants"]} == {"hero", "guard"}
    assert "Secret Assassin" not in str(player_payload)
    assert "Secret Assassin" not in str(viewer_payload)
    snap = s.to_authoritative_snapshot_for_role("player", "p1", source="test")
    combat = snap["payload"]["combat"]
    assert combat["active"] is True
    assert combat["revision"] == s.combat["revision"]
    assert combat["visibility_revision"] == s.visibility_revision
    assert "Secret Assassin" not in str(combat)
