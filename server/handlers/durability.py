"""
server/handlers/durability.py — Debounced, per-session durability save.

Historically only the DM's socket drove saves, on a coarse 60s timer, so a hard
crash (OOM / kill -9 / power loss) could lose up to 60s of play. This module
adds a per-session debounced save driven by *any* state mutation (not just the
DM's socket): ``mark_session_dirty(session)`` schedules a single
``save_campaign_async`` to run ``DURABILITY_DEBOUNCE_MS`` (default 2000ms) after
the most recent call, shrinking the crash-loss window from ~60s to ~2s.

The 60s autosave and the DM-disconnect save stay in place as backstops — this
is additive.
"""
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_DEBOUNCE_MS = 2000
_DEBOUNCE_MIN_MS = 250
_DEBOUNCE_MAX_MS = 30000

# Keyed by session.id → the single pending debounced save task for that session.
_pending_saves: dict[str, asyncio.Task] = {}


def _debounce_ms() -> int:
    raw = os.environ.get("DURABILITY_DEBOUNCE_MS")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_DEBOUNCE_MS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_DEBOUNCE_MS
    return max(_DEBOUNCE_MIN_MS, min(_DEBOUNCE_MAX_MS, value))


async def _debounced_save(session, sid: str, delay_ms: int) -> None:
    try:
        await asyncio.sleep(delay_ms / 1000.0)
    except asyncio.CancelledError:
        return
    # Only clear our slot if it still points at this task; a re-schedule during
    # the sleep would have replaced it (and cancelled us) already.
    if _pending_saves.get(sid) is asyncio.current_task():
        _pending_saves.pop(sid, None)
    try:
        from server.db import save_campaign_async
        await save_campaign_async(session)
    except Exception as exc:
        # A failed save must not crash the task or the request — log like the
        # existing autosave does and move on.
        logger.error("[DURABILITY] debounced save failed for session %s: %s", sid, exc)


def mark_session_dirty(session) -> None:
    """Schedule (or reschedule) a debounced save for ``session``.

    Repeated calls within the window reset the timer (debounce, not throttle),
    so a burst of mutations coalesces into a single save. Never more than one
    pending save task per session. Fires regardless of which role mutated state.
    """
    sid = str(getattr(session, "id", "") or "")
    if not sid:
        return
    try:
        loop_running = asyncio.get_running_loop()
    except RuntimeError:
        loop_running = None
    if loop_running is None:
        # No event loop (e.g. called from sync test setup) — nothing to schedule.
        return
    existing = _pending_saves.get(sid)
    if existing is not None and not existing.done():
        existing.cancel()
    _pending_saves[sid] = asyncio.create_task(_debounced_save(session, sid, _debounce_ms()))


def cancel_session_durability(session_id) -> None:
    """Cancel and clear any pending debounced save for a session (teardown)."""
    sid = str(session_id or "")
    task = _pending_saves.pop(sid, None)
    if task is not None and not task.done():
        task.cancel()


async def flush_session_durability(session) -> None:
    """Cancel the pending debounce and run one final synchronously-awaited save.

    Call on clean teardown so the last debounce window isn't lost. Wrapped so a
    save failure can't crash the disconnect path.
    """
    sid = str(getattr(session, "id", "") or "")
    cancel_session_durability(sid)
    try:
        from server.db import save_campaign_async
        await save_campaign_async(session)
    except Exception as exc:
        logger.error("[DURABILITY] final teardown save failed for session %s: %s", sid, exc)
