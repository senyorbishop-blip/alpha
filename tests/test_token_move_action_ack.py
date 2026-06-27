"""Tests for server action acknowledgements on the token_move mutation
stream (Realtime Sync Engine v1 — tiny patch).

Client may now send a `client_action_id` on a `token_move` payload. The
server preserves that id only for a sender-only `action_ack` message
(confirmed/denied/failed); it never broadcasts it to other clients, and it
never replaces the authoritative `token_moved` broadcast as the source of
truth for position.
"""
import pytest

from server.handlers import tokens as token_handlers
from server.session import Session, Token, User


def _build_session():
    session = Session(id="s-move-ack")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="player-1", name="Player", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    token = Token(
        id="tok-1", name="Hero", x=0, y=0, width=40, height=40,
        color="#fff", shape="circle", owner_id=player.id,
    )
    session.tokens[token.id] = token
    return session, dm, player, token


@pytest.fixture
def patched(monkeypatch):
    """Stub out the broadcast/IO helpers used by handle_token_move, but
    capture every manager.send_to call (this is how action_ack and
    token_move_denied are both delivered) and every _broadcast_token_event
    call (this is how the authoritative token_moved broadcast is delivered).
    """
    sent = []
    broadcasts = []

    async def _fake_send_to(sid, uid, msg):
        sent.append((sid, uid, msg))
        return True

    async def _capture_event(manager, sess, msg_type, payload, tok, exclude_user=None):
        broadcasts.append({"type": msg_type, "payload": payload, "exclude_user": exclude_user})

    async def _noop(*args, **kwargs):
        return None

    # Disable move coalescing so the token_moved broadcast is emitted
    # immediately (one per frame), exercising the legacy synchronous path these
    # assertions were written against. The coalescer reaches the broadcast via
    # server.handlers.common._broadcast_token_event (lazy import at flush time),
    # so the capture is patched there rather than on the tokens module.
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "0")
    monkeypatch.setattr(token_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr("server.handlers.common._broadcast_token_event", _capture_event)
    monkeypatch.setattr("server.handlers.durability.mark_session_dirty", lambda *a, **k: None)
    monkeypatch.setattr(token_handlers, "_broadcast_token_visibility", _noop)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "_process_scene_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "run_combat_fog_sync", _noop)

    return type("Patched", (), {"sent": sent, "broadcasts": broadcasts})()


def _acks(patched_obj, *, user_id=None):
    out = []
    for sid, uid, msg in patched_obj.sent:
        if msg.get("type") != "action_ack":
            continue
        if user_id is not None and uid != user_id:
            continue
        out.append(msg["payload"])
    return out


@pytest.mark.anyio
async def test_token_move_with_client_action_id_gets_confirmed_ack(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 10, "y": 10, "client_action_id": "abc-1"}, session, player
    )

    acks = _acks(patched, user_id=player.id)
    assert len(acks) == 1
    assert acks[0]["action"] == "token_move"
    assert acks[0]["client_action_id"] == "abc-1"
    assert acks[0]["status"] == "confirmed"


@pytest.mark.anyio
async def test_token_move_without_client_action_id_still_works(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move({"token_id": token.id, "x": 5, "y": 5}, session, player)

    assert token.x == 5 and token.y == 5
    # No client_action_id was sent, so no action_ack should be sent either —
    # this is the backward-compatibility contract for older clients.
    assert _acks(patched) == []
    assert len(patched.broadcasts) == 1
    assert patched.broadcasts[0]["type"] == "token_moved"


@pytest.mark.anyio
async def test_denied_token_move_sends_failed_action_ack(monkeypatch, patched):
    session, _dm, player, token = _build_session()

    class _Blocker:
        source = "a_wall"

    monkeypatch.setattr(token_handlers, "find_movement_blocker", lambda *a, **k: _Blocker())

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 99, "y": 99, "client_action_id": "abc-2"}, session, player
    )

    # Position must not have moved — the blocked move was rejected.
    assert token.x == 0 and token.y == 0
    assert patched.broadcasts == []

    acks = _acks(patched, user_id=player.id)
    assert len(acks) == 1
    assert acks[0]["status"] == "failed"
    assert acks[0]["client_action_id"] == "abc-2"
    assert "reason" in acks[0] and acks[0]["reason"]


@pytest.mark.anyio
async def test_client_action_id_not_leaked_in_token_moved_broadcast(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 12, "y": 14, "client_action_id": "secret-id"}, session, player
    )

    assert len(patched.broadcasts) == 1
    broadcast_payload = patched.broadcasts[0]["payload"]
    assert "client_action_id" not in broadcast_payload
    # The broadcast also excludes the mover's own connection (it gets the
    # ack instead), reinforcing that the id never reaches other recipients.
    assert patched.broadcasts[0]["exclude_user"] == player.id


@pytest.mark.anyio
async def test_success_ack_includes_token_id_and_visibility_revision(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 7, "y": 8, "client_action_id": "abc-3"}, session, player
    )

    acks = _acks(patched, user_id=player.id)
    assert len(acks) == 1
    ack = acks[0]
    assert ack["token_id"] == token.id
    assert isinstance(ack["visibility_revision"], int) and ack["visibility_revision"] > 0
    assert ack["visibility_revision"] == session.visibility_revision


@pytest.mark.anyio
async def test_invalid_move_missing_token_sends_safe_failed_reason(patched):
    session, _dm, player, _token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": "no-such-token", "x": 1, "y": 1, "client_action_id": "abc-4"}, session, player
    )

    acks = _acks(patched, user_id=player.id)
    assert len(acks) == 1
    assert acks[0]["status"] == "failed"
    assert acks[0]["client_action_id"] == "abc-4"
    reason = acks[0]["reason"]
    assert isinstance(reason, str) and reason
    # Safe reason: no internal details/identifiers leaked.
    assert "no-such-token" not in reason
    assert patched.broadcasts == []


@pytest.mark.anyio
async def test_unauthorized_move_sends_failed_ack(patched):
    session, _dm, _player, token = _build_session()
    other_player = User(id="player-2", name="Other", role="player")
    session.users[other_player.id] = other_player

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 1, "y": 1, "client_action_id": "abc-5"}, session, other_player
    )

    assert token.x == 0 and token.y == 0
    acks = _acks(patched, user_id=other_player.id)
    assert len(acks) == 1
    assert acks[0]["status"] == "failed"
    assert acks[0]["client_action_id"] == "abc-5"
    assert patched.broadcasts == []


@pytest.mark.anyio
async def test_action_ack_does_not_replace_authoritative_token_moved_broadcast(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 3, "y": 4, "client_action_id": "abc-6"}, session, player
    )

    # Both must happen: the sender-only ack AND the authoritative broadcast.
    assert len(_acks(patched, user_id=player.id)) == 1
    assert len(patched.broadcasts) == 1
    assert patched.broadcasts[0]["type"] == "token_moved"
    assert patched.broadcasts[0]["payload"]["x"] == 3
    assert patched.broadcasts[0]["payload"]["y"] == 4

@pytest.mark.anyio
async def test_rapid_token_moves_with_sequences_do_not_regress_final_position(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 10, "y": 10, "final": True, "client_move_seq": 1, "client_action_id": "seq-1"},
        session,
        player,
    )
    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 20, "y": 20, "final": True, "client_move_seq": 2, "client_action_id": "seq-2"},
        session,
        player,
    )

    assert token.x == 20 and token.y == 20
    assert len(patched.broadcasts) == 2
    assert patched.broadcasts[-1]["payload"]["x"] == 20
    assert patched.broadcasts[-1]["payload"]["y"] == 20


@pytest.mark.anyio
async def test_stale_token_move_sequence_is_ignored_server_side(patched):
    session, _dm, player, token = _build_session()

    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 20, "y": 20, "final": True, "client_move_seq": 2, "client_action_id": "seq-new"},
        session,
        player,
    )
    await token_handlers.handle_token_move(
        {"token_id": token.id, "x": 5, "y": 5, "final": True, "client_move_seq": 1, "client_action_id": "seq-old"},
        session,
        player,
    )

    assert token.x == 20 and token.y == 20
    assert len(patched.broadcasts) == 1
    stale_acks = [ack for ack in _acks(patched, user_id=player.id) if ack["client_action_id"] == "seq-old"]
    assert stale_acks and stale_acks[0]["status"] == "stale"


@pytest.mark.anyio
async def test_fog_hidden_npc_visibility_updates_immediately_after_committed_move(monkeypatch):
    session, dm, _player, _hero = _build_session()
    npc = Token(id="npc-1", name="Goblin", x=0, y=0, width=40, height=40, color="#0f0", shape="circle", owner_id=None, token_type="npc")
    session.tokens[npc.id] = npc
    visibility_calls = []

    async def _fake_event(manager, sess, msg_type, payload, tok, exclude_user=None):
        return 1

    async def _capture_visibility(sess, tok, msg_type="token_hidden_changed"):
        visibility_calls.append({"token_id": tok.id, "msg_type": msg_type, "x": tok.x, "y": tok.y})

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "0")
    monkeypatch.setattr("server.handlers.common._broadcast_token_event", _fake_event)
    monkeypatch.setattr("server.handlers.durability.mark_session_dirty", lambda *a, **k: None)
    monkeypatch.setattr(token_handlers, "_broadcast_token_visibility", _capture_visibility)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "_process_scene_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "run_combat_fog_sync", _noop)

    await token_handlers.handle_token_move(
        {"token_id": npc.id, "x": 50, "y": 50, "final": True, "client_move_seq": 1, "client_action_id": "npc-move"},
        session,
        dm,
    )

    assert visibility_calls == [{"token_id": npc.id, "msg_type": "token_hidden_changed", "x": 50.0, "y": 50.0}]
