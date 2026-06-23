"""
server/visibility.py — Server-authoritative wall/door line-of-sight engine.

PR 7 (wall/door vision blocking hardening). This module is the single source
of truth for "what can a token see" once walls and doors are involved. It is
deliberately a simple grid/segment model rather than a full polygon LOS
solver:

  * Walls and closed doors are line segments (server/map_logic.py already
    normalizes both into a single ``Blocker`` list for movement blocking —
    we reuse the exact same list here, filtered to ``blocks_vision``).
  * A "viewer" is a player-owned, non-hidden, non-staged token with
    ``vision_enabled`` and a positive vision radius (bright/dim/darkvision,
    same fields the client vision preview already reads).
  * Line of sight from a viewer to a point is a single segment-intersection
    test against every vision-blocking segment. A closed door's segment is
    only present in the blocker list while it is closed (``door_blocker`` in
    map_logic.py already drops open doors), so an open door is transparent
    and a closed one — secret or not — blocks sight exactly like a wall.
  * Secret-door *metadata* (existence/position to non-DM roles) is filtered
    separately in ``filter_editor_props_for_role`` (server/session.py); this
    module always uses the real geometry, so a secret door still blocks
    sight server-side even though players are never told it's there.

This intentionally mirrors client/static/js/render/vision.js's preview
algorithm (same radius-in-feet -> px conversion, same segment intersection
test) so DM/player preview and server truth agree whenever there's nothing
stale in flight — but the server result here is the one that actually gates
token/fog/combat visibility.
"""
from __future__ import annotations

from typing import Iterable

from server.map_logic import Blocker, collect_map_blockers, segments_intersect

FT_PER_GRID = 5.0
PX_PER_GRID = 50.0


def vision_blockers(session, map_ctx: str) -> list[Blocker]:
    """Vision-blocking segments for a map: walls + closed doors with blocks_vision=True."""
    return [b for b in collect_map_blockers(session, map_ctx) if b.blocks_vision]


def has_los(x1: float, y1: float, x2: float, y2: float, blockers: Iterable[Blocker]) -> bool:
    for b in blockers:
        if segments_intersect(x1, y1, x2, y2, b.x1, b.y1, b.x2, b.y2):
            return False
    return True


def _token_map_ctx(token) -> str:
    return str(getattr(token, "map_context", "world") or "world")


def _token_center(token) -> tuple[float, float]:
    x = float(getattr(token, "x", 0.0) or 0.0)
    y = float(getattr(token, "y", 0.0) or 0.0)
    w = float(getattr(token, "width", PX_PER_GRID) or PX_PER_GRID)
    h = float(getattr(token, "height", PX_PER_GRID) or PX_PER_GRID)
    return x + w / 2.0, y + h / 2.0


def vision_radius_ft(token) -> float:
    """Same "usable radius" computation the client vision preview uses."""
    if not bool(getattr(token, "vision_enabled", False)):
        return 0.0
    base = float(getattr(token, "vision_radius", 0) or 0)
    bright = float(getattr(token, "bright_radius", 0) or 0)
    dark = float(getattr(token, "darkvision_radius", 0) or 0) if bool(getattr(token, "has_darkvision", False)) else 0.0
    return max(base, bright, dark, 0.0)


def vision_radius_px(token) -> float:
    return (vision_radius_ft(token) / FT_PER_GRID) * PX_PER_GRID


def _is_player_vision_source(token) -> bool:
    """Lazy import to dodge a common.py <-> visibility.py import cycle."""
    from server.handlers.common import is_player_owned_token
    if token is None or bool(getattr(token, "hidden", False)) or bool(getattr(token, "staged", False)):
        return False
    if not is_player_owned_token(token):
        return False
    return vision_radius_px(token) > 0


def player_vision_sources(session, map_ctx: str) -> list[dict]:
    """Player-owned vision sources on a given map: [{x, y, radius_px, token_id}]."""
    sources = []
    for token in (getattr(session, "tokens", {}) or {}).values():
        if _token_map_ctx(token) != map_ctx or not _is_player_vision_source(token):
            continue
        x, y = _token_center(token)
        sources.append({"x": x, "y": y, "radius_px": vision_radius_px(token), "token_id": str(getattr(token, "id", "") or "")})
    return sources


def point_visible_from_sources(x: float, y: float, sources: list[dict], blockers: list[Blocker]) -> bool:
    for src in sources:
        dx = x - src["x"]
        dy = y - src["y"]
        reach = src["radius_px"]
        if dx * dx + dy * dy > reach * reach:
            continue
        if has_los(src["x"], src["y"], x, y, blockers):
            return True
    return False


def token_blocked_by_los(session, token, map_context: str | None = None) -> bool:
    """True if a token is outside line-of-sight of every player vision source.

    Fails open (returns False = "not blocked") whenever there is nothing to
    meaningfully gate against — no vision-blocking geometry on the map, or no
    player vision source positioned on it — so maps without walls/doors or
    without vision-enabled tokens behave exactly as they did before PR 7.
    """
    if token is None:
        return False
    map_ctx = str(map_context or _token_map_ctx(token))
    blockers = vision_blockers(session, map_ctx)
    if not blockers:
        return False
    sources = player_vision_sources(session, map_ctx)
    if not sources:
        return False
    tx, ty = _token_center(token)
    return not point_visible_from_sources(tx, ty, sources, blockers)


def _map_dimensions(session, map_ctx: str) -> tuple[float, float]:
    settings = getattr(session, "map_settings", None) or {}
    ctx_settings = settings.get(map_ctx) if isinstance(settings.get(map_ctx), dict) else {}
    mw = float(ctx_settings.get("width") or ctx_settings.get("map_width") or 4096)
    mh = float(ctx_settings.get("height") or ctx_settings.get("map_height") or 4096)
    return mw, mh


def _cell_center(col: int, row: int, cols: int, rows: int, mw: float, mh: float) -> tuple[float, float]:
    cw = mw / cols
    ch = mh / rows
    return -mw / 2.0 + (col + 0.5) * cw, -mh / 2.0 + (row + 0.5) * ch


def compute_visible_cell_indices(session, map_ctx: str, cols: int, rows: int) -> set[int]:
    """Cell indices (row * cols + col) currently visible to any player vision source.

    Uses the same world-coordinate convention as
    server/handlers/common.py::_token_occupied_fog_indices (map drawn from
    (-w/2,-h/2) to (w/2,h/2)) so the result lines up with the existing fog
    grid without needing a second coordinate system.
    """
    blockers = vision_blockers(session, map_ctx)
    sources = player_vision_sources(session, map_ctx)
    if not sources or cols <= 0 or rows <= 0:
        return set()
    mw, mh = _map_dimensions(session, map_ctx)
    cw = mw / cols
    ch = mh / rows
    visible: set[int] = set()
    for src in sources:
        radius_px = src["radius_px"]
        if radius_px <= 0:
            continue
        min_col = max(0, int((src["x"] - radius_px + mw / 2.0) / cw))
        max_col = min(cols - 1, int((src["x"] + radius_px + mw / 2.0) / cw))
        min_row = max(0, int((src["y"] - radius_px + mh / 2.0) / ch))
        max_row = min(rows - 1, int((src["y"] + radius_px + mh / 2.0) / ch))
        radius_sq = radius_px * radius_px
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                idx = row * cols + col
                if idx in visible:
                    continue
                cx, cy = _cell_center(col, row, cols, rows, mw, mh)
                dx, dy = cx - src["x"], cy - src["y"]
                if dx * dx + dy * dy > radius_sq:
                    continue
                if has_los(src["x"], src["y"], cx, cy, blockers):
                    visible.add(idx)
    return visible


def apply_los_fog_reveal(session, map_ctx: str) -> bool:
    """Reveal (never hide) fog cells inside current player LOS for a map.

    Returns True if any previously-unrevealed cell was newly revealed. This
    only ever adds to the existing manual-paint fog bitstring — it never
    competes with or overwrites the DM's manual fog tools.
    """
    fog_maps = getattr(session, "fog_maps", None) or {}
    entry = fog_maps.get(map_ctx)
    if not isinstance(entry, dict) or not entry.get("enabled", False):
        return False
    try:
        cols = int(entry.get("cols") or 0)
        rows = int(entry.get("rows") or 0)
    except Exception:
        return False
    if cols <= 0 or rows <= 0:
        return False
    total = cols * rows
    cells = str(entry.get("cells") or "")
    if len(cells) != total:
        cells = cells[:total].ljust(total, "0")
    visible_indices = compute_visible_cell_indices(session, map_ctx, cols, rows)
    if not visible_indices:
        return False
    arr = list(cells)
    changed = False
    for idx in visible_indices:
        if 0 <= idx < total and arr[idx] != "1":
            arr[idx] = "1"
            changed = True
    if changed:
        entry["cells"] = "".join(arr)
    return changed
