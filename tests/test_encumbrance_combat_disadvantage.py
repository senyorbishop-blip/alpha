import pytest

from server.handlers import combat as combat_handlers
from server.session import Session, Token, User


def _build_session_with_pending_attack_state():
    session = Session(id="s1")
    player = User(id="u1", name="Player One", role="player")
    target_owner = User(id="u2", name="Target Player", role="player")
    session.users[player.id] = player
    session.users[target_owner.id] = target_owner
    session.tokens["attacker"] = Token(
        id="attacker",
        name="Attacker",
        x=0,
        y=0,
        width=1,
        height=1,
        color="#fff",
        shape="circle",
        owner_id=player.id,
    )
    session.tokens["target"] = Token(
        id="target",
        name="Target",
        x=2,
        y=2,
        width=1,
        height=1,
        color="#fff",
        shape="circle",
        owner_id=target_owner.id,
    )
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{"token_id": "attacker", "owner_id": player.id}],
        "pending_attack": None,
    }
    return session, player


def test_has_encumbrance_attack_disadvantage_true_for_heavy_state():
    session = Session(id="s1")
    session._encumbrance_cache = {"u1": {"state": "heavily_encumbered"}}
    assert combat_handlers._has_encumbrance_attack_disadvantage(session, "u1") is True


def test_has_encumbrance_attack_disadvantage_false_for_other_states():
    session = Session(id="s1")
    session._encumbrance_cache = {"u1": {"state": "encumbered"}}
    assert combat_handlers._has_encumbrance_attack_disadvantage(session, "u1") is False


@pytest.mark.anyio
async def test_attack_request_marks_pending_attack_with_disadvantage(monkeypatch):
    session, player = _build_session_with_pending_attack_state()
    session._encumbrance_cache = {"u1": {"state": "heavily_encumbered"}}

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _noop)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _noop)
    monkeypatch.setattr(combat_handlers.manager, "send_to", _noop)

    await combat_handlers.handle_combat_attack_request(
        {"target_id": "target", "attack_kind": "weapon"},
        session,
        player,
    )

    pending = dict(session.combat.get("pending_attack") or {})
    assert pending.get("disadvantage") is True
    assert pending.get("disadvantage_reason") == "heavily_encumbered"
