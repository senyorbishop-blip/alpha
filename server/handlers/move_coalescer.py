"""
server/handlers/move_coalescer.py — Per-session, per-token coalescing of
high-frequency ``token_moved`` broadcasts.

Dragging a token fires dozens of ``token_moved`` messages per second, each
doing a full revision bump + recipient fan-out. This module collapses repeated
moves of the *same* token into a single outbound broadcast per
``COALESCE_WINDOW_MS`` window, carrying only the final position, with the
revision bumps (``bump_visibility_revision`` + ``_stamp_token_revision``)
happening exactly once at flush time.

Only ``token_moved`` goes through here. One-off token events
(token_placed/token_hp_updated/combat/doors/…) still broadcast immediately.

The synchronous parts of ``handle_token_move`` — validation, combat movement
enforcement, the ``token.x``/``token.y`` mutation, and the mover's own ack —
are unchanged and stay immediate. Only the fan-out broadcast to other
recipients is deferred.

Setting ``MOVE_COALESCE_WINDOW_MS=0`` disables coalescing entirely and
reproduces the legacy immediate-broadcast behavior (one broadcast per frame),
which keeps existing tests/debug deterministic.
"""
import asyncio
import logging
import os

from server.connections import manager

logger = logging.getLogger(__name__)

DEFAULT_COALESCE_WINDOW_MS = 50
_WINDOW_MIN_MS = 0
_WINDOW_MAX_MS = 500


def _coalesce_window_ms() -> int:
    """Resolve the coalescing window (ms) from env, clamped to [0, 500].

    0 disables coalescing → send immediately (legacy behavior).
    """
    raw = os.environ.get("MOVE_COALESCE_WINDOW_MS")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_COALESCE_WINDOW_MS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_COALESCE_WINDOW_MS
    return max(_WINDOW_MIN_MS, min(_WINDOW_MAX_MS, value))


class _PendingMove:
    __slots__ = ("session", "token", "payload_factory", "exclude_user")

    def __init__(self, session, token, payload_factory, exclude_user):
        self.session = session
        self.token = token
        self.payload_factory = payload_factory
        self.exclude_user = exclude_user


# Keyed by (session_id, token_id). Last-write-wins: a newer frame for the same
# key overwrites the pending payload so only the final position is broadcast.
_pending: dict[tuple[str, str], _PendingMove] = {}
_flush_tasks: dict[tuple[str, str], asyncio.Task] = {}


async def _emit_move_broadcast(pending: _PendingMove) -> int:
    """Bump revisions once and fan out a single ``token_moved`` broadcast.

    Both the visibility-revision bump and the token-state-revision bump
    (the latter inside ``_broadcast_token_event``) happen here, on the final
    position, so a coalesced burst of N frames advances each counter by exactly
    one. ``mark_session_dirty`` is fired here too — the flush is the natural
    "state changed" signal for the debounced durability save.
    """
    # Lazy imports avoid a circular import (common -> … and durability) at
    # module load while keeping the hot path cheap after first use.
    from server.handlers.common import _broadcast_token_event, bump_visibility_revision
    from server.handlers.durability import mark_session_dirty

    session = pending.session
    token = pending.token
    bump_visibility_revision(session)
    token_state_revision = await _broadcast_token_event(
        manager, session, "token_moved", pending.payload_factory(), token,
        exclude_user=pending.exclude_user,
    )
    mark_session_dirty(session)
    return token_state_revision


async def _delayed_flush(key: tuple[str, str], window_ms: int) -> None:
    try:
        await asyncio.sleep(window_ms / 1000.0)
    except asyncio.CancelledError:
        return
    pending = _pending.pop(key, None)
    _flush_tasks.pop(key, None)
    if pending is None:
        return
    try:
        await _emit_move_broadcast(pending)
    except Exception as exc:  # never let a flush crash the loop
        logger.error("[MOVE COALESCE] flush failed for %s: %s", key, exc)


async def schedule_token_move_flush(session, token, payload_factory, *, exclude_user=None):
    """Coalesce a ``token_moved`` broadcast for ``token``.

    ``payload_factory`` is a zero-arg callable returning the broadcast payload
    dict; it is invoked at flush time so it captures the token's *final*
    position. Stores/overwrites the latest pending move for
    ``(session.id, token.id)`` (last-write-wins) and, if no flush is already
    pending for that key, schedules one ~``MOVE_COALESCE_WINDOW_MS`` later.

    With the window disabled (``MOVE_COALESCE_WINDOW_MS=0``) this sends
    immediately, exactly like the legacy code path.

    Returns the broadcast's ``token_state_revision`` when sent immediately
    (disabled window), otherwise ``None`` because the real bump has not happened
    yet — callers must not report a revision that was never broadcast.
    """
    window_ms = _coalesce_window_ms()
    pending = _PendingMove(session, token, payload_factory, exclude_user)
    if window_ms <= 0:
        return await _emit_move_broadcast(pending)

    key = (str(getattr(session, "id", "")), str(getattr(token, "id", "")))
    _pending[key] = pending
    if key not in _flush_tasks:
        _flush_tasks[key] = asyncio.create_task(_delayed_flush(key, window_ms))
    return None


def cancel_session_flushes(session_id) -> None:
    """Cancel and clear every pending move flush for a session.

    MUST be called on session teardown so no late send fires against a dead
    session and no flush task leaks. Safe to call when nothing is pending.
    """
    sid = str(session_id or "")
    for key in [k for k in _flush_tasks if k[0] == sid]:
        task = _flush_tasks.pop(key, None)
        if task is not None and not task.done():
            task.cancel()
    for key in [k for k in _pending if k[0] == sid]:
        _pending.pop(key, None)
