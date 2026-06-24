"""Token movement performance guardrails.

This module centralises the decision for when an individual token move should
run the expensive follow-up work: per-user visibility rebuilds, hazard scans,
scene triggers, LOS fog reveal, and combat fog sync.

The goal is to keep drag movement responsive while still forcing the heavy work
when a token changes grid cell/map context, finishes a drag, or enough time has
passed since the last heavy movement pass.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

_DEFAULT_GRID_PX = 50.0
_DEFAULT_HEAVY_INTERVAL_SECONDS = 0.12
_DEFAULT_MIN_HEAVY_DISTANCE_PX = 3.0


@dataclass(frozen=True)
class TokenMovePerfDecision:
    run_heavy_work: bool
    reason: str
    old_cell: tuple[int, int]
    new_cell: tuple[int, int]
    distance_px: float


def _env_float(name: str, default: float, minimum: float) -> float:
    try:
        value = float(str(os.environ.get(name, default)).strip())
    except Exception:
        value = default
    return max(minimum, value)


def token_move_grid_px() -> float:
    return _env_float("TOKEN_MOVE_GRID_PX", _DEFAULT_GRID_PX, 1.0)


def token_move_heavy_interval_seconds() -> float:
    return _env_float("TOKEN_MOVE_HEAVY_INTERVAL_SECONDS", _DEFAULT_HEAVY_INTERVAL_SECONDS, 0.01)


def token_move_min_heavy_distance_px() -> float:
    return _env_float("TOKEN_MOVE_MIN_HEAVY_DISTANCE_PX", _DEFAULT_MIN_HEAVY_DISTANCE_PX, 0.0)


def _cell_for(x: float, y: float, grid_px: float) -> tuple[int, int]:
    return (int(float(x or 0.0) // grid_px), int(float(y or 0.0) // grid_px))


def _distance(old_x: float, old_y: float, new_x: float, new_y: float) -> float:
    dx = float(new_x or 0.0) - float(old_x or 0.0)
    dy = float(new_y or 0.0) - float(old_y or 0.0)
    return (dx * dx + dy * dy) ** 0.5


def _runtime(session) -> dict:
    runtime = getattr(session, "_token_move_perf_runtime", None)
    if not isinstance(runtime, dict):
        runtime = {}
        setattr(session, "_token_move_perf_runtime", runtime)
    return runtime


def _runtime_key(token, map_context: str | None = None) -> str:
    token_id = str(getattr(token, "id", "") or "")
    map_ctx = str(map_context or getattr(token, "map_context", "world") or "world")
    return f"{map_ctx}:{token_id}"


def decide_token_move_heavy_work(
    session,
    token,
    *,
    old_x: float,
    old_y: float,
    new_x: float,
    new_y: float,
    payload: dict | None = None,
    now: float | None = None,
) -> TokenMovePerfDecision:
    """Decide whether a move should run expensive follow-up work.

    Rules:
    - Always run for explicit final/drag-end moves.
    - Always run when the token crosses a grid cell.
    - Always run when map context changes.
    - Skip tiny same-cell movement under the configured distance threshold.
    - Otherwise throttle heavy work per token/map context.
    """
    payload = payload if isinstance(payload, dict) else {}
    now = float(time.time() if now is None else now)
    grid_px = token_move_grid_px()
    old_cell = _cell_for(old_x, old_y, grid_px)
    new_cell = _cell_for(new_x, new_y, grid_px)
    distance = _distance(old_x, old_y, new_x, new_y)

    if bool(payload.get("final") or payload.get("drag_end") or payload.get("commit")):
        return TokenMovePerfDecision(True, "final_move", old_cell, new_cell, distance)

    old_map_context = str(payload.get("old_map_context") or getattr(token, "map_context", "world") or "world")
    new_map_context = str(payload.get("map_context") or getattr(token, "map_context", "world") or "world")
    if old_map_context != new_map_context:
        return TokenMovePerfDecision(True, "map_context_changed", old_cell, new_cell, distance)

    if old_cell != new_cell:
        return TokenMovePerfDecision(True, "grid_cell_changed", old_cell, new_cell, distance)

    if distance < token_move_min_heavy_distance_px():
        return TokenMovePerfDecision(False, "tiny_same_cell_move", old_cell, new_cell, distance)

    runtime = _runtime(session)
    key = _runtime_key(token, new_map_context)
    last_at = float(runtime.get(key) or 0.0)
    if last_at and (now - last_at) < token_move_heavy_interval_seconds():
        return TokenMovePerfDecision(False, "throttled_same_cell_move", old_cell, new_cell, distance)

    return TokenMovePerfDecision(True, "interval_elapsed", old_cell, new_cell, distance)


def mark_token_move_heavy_work_ran(session, token, *, map_context: str | None = None, now: float | None = None) -> None:
    runtime = _runtime(session)
    runtime[_runtime_key(token, map_context)] = float(time.time() if now is None else now)
