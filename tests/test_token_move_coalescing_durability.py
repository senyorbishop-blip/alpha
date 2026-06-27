"""Tests for token-move coalescing + debounced per-session durability.

Covers the eight verification points of the stability patch:

  1. Coalescing collapses a burst into one final broadcast (state mutation stays
     synchronous).
  2. Revision monotonicity under coalescing — one bump per flush, on the final
     position.
  3. MOVE_COALESCE_WINDOW_MS=0 reproduces the legacy one-broadcast-per-frame
     behavior.
  4. No late send after teardown (cancel_session_flushes ran).
  5. Movement enforcement stays synchronous — a denied move never reaches the
     coalescer, so no broadcast slips out.
  6. Debounced persist fires on a non-DM mutation, with no DM autosave loop.
  7. Debounce coalesces many mutations into a single save.
  8. Crash-window bound — after a mutation + debounce flush the persisted
     snapshot reflects that mutation.
"""
import asyncio

import pytest

from server.handlers import tokens as token_handlers
from server.handlers import move_coalescer
from server.handlers import durability
from server.session import Session, Token, User


def _build_session():
    session = Session(id="s-coalesce")
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


def _patch_move_path(monkeypatch):
    """Stub the side IO of handle_token_move and capture every send_to.

    Uses the REAL _broadcast_token_event so the authoritative revision bumps
    actually happen (tests assert on them); only the network send and the
    optional heavy-work tail are stubbed. Returns the captured sends list.
    """
    sends = []

    async def _fake_send_to(sid, uid, msg):
        sends.append({"session_id": sid, "user_id": uid, "type": msg.get("type"), "payload": msg.get("payload")})
        return True

    class _NoHeavy:
        run_heavy_work = False

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(token_handlers, "find_movement_blocker", lambda *a, **k: None)
    monkeypatch.setattr(token_handlers, "decide_token_move_heavy_work", lambda *a, **k: _NoHeavy())
    # Durability is exercised in its own tests; keep it inert here so move tests
    # don't schedule background save tasks.
    monkeypatch.setattr("server.handlers.durability.mark_session_dirty", lambda *a, **k: None)
    return sends


def _token_moved(sends):
    return [s for s in sends if s["type"] == "token_moved"]


# ---------------------------------------------------------------------------
# 1. Coalescing collapses a burst.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_burst_collapses_to_single_final_broadcast(monkeypatch):
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "200")
    session, _dm, player, token = _build_session()
    sends = _patch_move_path(monkeypatch)

    for i in range(1, 13):  # 12-frame drag
        await token_handlers.handle_token_move(
            {"token_id": token.id, "x": i * 10, "y": i * 5}, session, player
        )
        # State mutation is synchronous: token.x/y equal the final position of
        # THIS frame immediately, before any broadcast has gone out.
        assert token.x == i * 10 and token.y == i * 5

    # Still inside the window — nothing flushed yet.
    assert _token_moved(sends) == []

    await asyncio.sleep(0.3)  # let the single flush fire

    moved = _token_moved(sends)
    assert len(moved) == 1
    assert moved[0]["payload"]["x"] == 120
    assert moved[0]["payload"]["y"] == 60
    move_coalescer.cancel_session_flushes(session.id)


# ---------------------------------------------------------------------------
# 2. Revision monotonicity under coalescing.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_revision_advances_by_exactly_one_per_flush(monkeypatch):
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "100")
    session, _dm, player, token = _build_session()
    sends = _patch_move_path(monkeypatch)

    vis_before = int(session.visibility_revision)
    tsr_before = int(session.token_state_revision)

    for i in range(1, 6):  # 5 frames in one window
        await token_handlers.handle_token_move(
            {"token_id": token.id, "x": i, "y": i}, session, player
        )
    await asyncio.sleep(0.2)

    # A coalesced burst of N frames advances each counter by exactly 1.
    assert session.visibility_revision == vis_before + 1
    assert session.token_state_revision == tsr_before + 1

    moved = _token_moved(sends)
    assert len(moved) == 1
    first_vis = moved[0]["payload"]["visibility_revision"]
    first_tsr = moved[0]["payload"]["token_state_revision"]

    # A second burst flushes with strictly greater revisions than the first.
    for i in range(10, 13):
        await token_handlers.handle_token_move(
            {"token_id": token.id, "x": i, "y": i}, session, player
        )
    await asyncio.sleep(0.2)

    moved = _token_moved(sends)
    assert len(moved) == 2
    assert moved[1]["payload"]["visibility_revision"] > first_vis
    assert moved[1]["payload"]["token_state_revision"] > first_tsr
    move_coalescer.cancel_session_flushes(session.id)


# ---------------------------------------------------------------------------
# 3. Disabled window = legacy behavior.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_disabled_window_broadcasts_every_frame(monkeypatch):
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "0")
    session, _dm, player, token = _build_session()
    sends = _patch_move_path(monkeypatch)

    for i in range(1, 6):
        await token_handlers.handle_token_move(
            {"token_id": token.id, "x": i * 3, "y": i * 3}, session, player
        )

    # No sleep: with the window disabled each frame broadcasts immediately.
    moved = _token_moved(sends)
    assert len(moved) == 5
    assert moved[-1]["payload"]["x"] == 15 and moved[-1]["payload"]["y"] == 15


# ---------------------------------------------------------------------------
# 4. No late send after teardown.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_no_late_send_after_teardown(monkeypatch):
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "200")
    session, _dm, player, token = _build_session()
    sends = _patch_move_path(monkeypatch)

    await token_handlers.handle_token_move({"token_id": token.id, "x": 99, "y": 99}, session, player)
    assert _token_moved(sends) == []  # still pending

    # Session torn down before the window elapses — cancel pending flushes.
    move_coalescer.cancel_session_flushes(session.id)

    await asyncio.sleep(0.3)  # well past the window
    # The flush must NOT have fired against the dead session.
    assert _token_moved(sends) == []


# ---------------------------------------------------------------------------
# 5. Movement enforcement still synchronous — invalid move never broadcasts.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_denied_combat_move_emits_no_broadcast(monkeypatch):
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "200")
    session, _dm, player, token = _build_session()
    sends = _patch_move_path(monkeypatch)

    denied = []

    async def _deny(sess, usr, tok, new_x, new_y, *, client_action_id=None):
        # Mirror the real enforcement deny path: send token_move_denied and
        # refuse the move. handle_token_move must early-return BEFORE coalescing.
        denied.append((new_x, new_y))
        return False

    monkeypatch.setattr(token_handlers, "_enforce_player_combat_movement", _deny)

    await token_handlers.handle_token_move({"token_id": token.id, "x": 500, "y": 500}, session, player)

    # Position unchanged (mutation comes only after enforcement passes) ...
    assert token.x == 0 and token.y == 0
    assert denied == [(500.0, 500.0)]

    await asyncio.sleep(0.3)
    # ... and no token_moved broadcast slipped out via the coalescer.
    assert _token_moved(sends) == []


# ---------------------------------------------------------------------------
# 6 / 7 / 8. Debounced durability.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_debounced_save_fires_on_mutation(monkeypatch):
    # Non-DM mutation, no DM autosave loop running — mark_session_dirty alone
    # must drive a save within ~the debounce window.
    monkeypatch.setenv("DURABILITY_DEBOUNCE_MS", "250")
    session, _dm, _player, _token = _build_session()

    calls = []

    async def _spy_save(sess):
        calls.append(sess.id)
        return True

    monkeypatch.setattr("server.db.save_campaign_async", _spy_save)

    durability.mark_session_dirty(session)
    assert calls == []  # nothing yet — debounced, not immediate
    await asyncio.sleep(0.5)
    assert calls == [session.id]
    durability.cancel_session_durability(session.id)


@pytest.mark.anyio
async def test_debounce_coalesces_many_mutations_into_one_save(monkeypatch):
    monkeypatch.setenv("DURABILITY_DEBOUNCE_MS", "250")
    session, _dm, _player, _token = _build_session()

    calls = []

    async def _spy_save(sess):
        calls.append(sess.id)
        return True

    monkeypatch.setattr("server.db.save_campaign_async", _spy_save)

    for _ in range(10):  # ten mutations inside one window
        durability.mark_session_dirty(session)
    await asyncio.sleep(0.5)
    # Debounce (not throttle): exactly one save, not ten.
    assert calls == [session.id]
    durability.cancel_session_durability(session.id)


@pytest.mark.anyio
async def test_persisted_snapshot_reflects_latest_mutation(monkeypatch):
    # Crash-window bound (logical): the debounce-flushed save observes the
    # mutated state, demonstrating ~debounce-window loss rather than ~60s.
    monkeypatch.setenv("DURABILITY_DEBOUNCE_MS", "250")
    session, _dm, _player, token = _build_session()

    snapshots = []

    async def _spy_save(sess):
        tok = sess.tokens[token.id]
        snapshots.append((tok.x, tok.y))
        return True

    monkeypatch.setattr("server.db.save_campaign_async", _spy_save)

    token.x, token.y = 321, 654
    durability.mark_session_dirty(session)
    await asyncio.sleep(0.5)

    assert snapshots == [(321, 654)]
    durability.cancel_session_durability(session.id)


@pytest.mark.anyio
async def test_flush_session_durability_runs_final_save(monkeypatch):
    monkeypatch.setenv("DURABILITY_DEBOUNCE_MS", "5000")  # long; teardown must not wait
    session, _dm, _player, _token = _build_session()

    calls = []

    async def _spy_save(sess):
        calls.append(sess.id)
        return True

    monkeypatch.setattr("server.db.save_campaign_async", _spy_save)

    durability.mark_session_dirty(session)  # schedules a far-future debounced save
    await durability.flush_session_durability(session)  # cancels it + saves now
    assert calls == [session.id]
    # The pending debounce was cancelled, so no second save lands later.
    await asyncio.sleep(0.1)
    assert calls == [session.id]


# ---------------------------------------------------------------------------
# Wiring: the move flush is the "state changed" signal for durability.
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_move_flush_marks_session_dirty(monkeypatch):
    monkeypatch.setenv("MOVE_COALESCE_WINDOW_MS", "100")
    session, _dm, player, token = _build_session()

    sends = []

    async def _fake_send_to(sid, uid, msg):
        sends.append(msg.get("type"))
        return True

    class _NoHeavy:
        run_heavy_work = False

    dirty = []
    monkeypatch.setattr(token_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(token_handlers, "find_movement_blocker", lambda *a, **k: None)
    monkeypatch.setattr(token_handlers, "decide_token_move_heavy_work", lambda *a, **k: _NoHeavy())
    monkeypatch.setattr("server.handlers.durability.mark_session_dirty", lambda sess: dirty.append(sess.id))

    await token_handlers.handle_token_move({"token_id": token.id, "x": 7, "y": 7}, session, player)
    assert dirty == []  # not until the flush
    await asyncio.sleep(0.2)
    assert dirty == [session.id]
    move_coalescer.cancel_session_flushes(session.id)
