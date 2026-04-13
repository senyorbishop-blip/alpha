from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

GRID_SIZE = 50.0


@dataclass
class Blocker:
    x1: float
    y1: float
    x2: float
    y2: float
    blocks_movement: bool = True
    blocks_vision: bool = True
    source: str = "wall"


def _ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)


def segments_intersect(a1x: float, a1y: float, a2x: float, a2y: float,
                       b1x: float, b1y: float, b2x: float, b2y: float) -> bool:
    return (_ccw(a1x, a1y, b1x, b1y, b2x, b2y) != _ccw(a2x, a2y, b1x, b1y, b2x, b2y)
            and _ccw(a1x, a1y, a2x, a2y, b1x, b1y) != _ccw(a1x, a1y, a2x, a2y, b2x, b2y))


def normalize_wall(raw: dict) -> Optional[Blocker]:
    if not isinstance(raw, dict):
        return None
    try:
        x1 = float(raw.get('x1'))
        y1 = float(raw.get('y1'))
        x2 = float(raw.get('x2'))
        y2 = float(raw.get('y2'))
    except Exception:
        return None
    if x1 == x2 and y1 == y2:
        return None
    return Blocker(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        blocks_movement=bool(raw.get('blocks_movement', True)),
        blocks_vision=bool(raw.get('blocks_vision', True)),
        source=str(raw.get('kind') or 'wall'),
    )


def door_blocker(raw: dict) -> Optional[Blocker]:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get('kind') or '').strip().lower()
    if kind not in {'door', 'opening'}:
        return None
    if kind == 'opening':
        return None
    state = str(raw.get('state') or 'closed').strip().lower()
    if state == 'open':
        return None
    facing = 'v' if str(raw.get('facing') or 'h').strip().lower().startswith('v') else 'h'
    x = float(raw.get('x', 0))
    y = float(raw.get('y', 0))
    blocks_movement = bool(raw.get('blocks_movement', True))
    blocks_vision = bool(raw.get('blocks_vision', True))
    source = 'locked_door' if bool(raw.get('locked', False)) else 'door'
    if facing == 'v':
        return Blocker(x1=x, y1=y, x2=x, y2=y + GRID_SIZE,
                       blocks_movement=blocks_movement, blocks_vision=blocks_vision, source=source)
    return Blocker(x1=x, y1=y, x2=x + GRID_SIZE, y2=y,
                   blocks_movement=blocks_movement, blocks_vision=blocks_vision, source=source)


def collect_map_blockers(session, map_ctx: str) -> List[Blocker]:
    blockers: List[Blocker] = []
    for raw in list((getattr(session, 'editor_walls', {}) or {}).get(map_ctx) or []):
        wall = normalize_wall(raw)
        if wall:
            blockers.append(wall)
    for raw in list((getattr(session, 'editor_props', {}) or {}).get(map_ctx) or []):
        door = door_blocker(raw)
        if door:
            blockers.append(door)
    return blockers


def find_movement_blocker(session, map_ctx: str, old_x: float, old_y: float, new_x: float, new_y: float) -> Optional[Blocker]:
    for blocker in collect_map_blockers(session, map_ctx):
        if not blocker.blocks_movement:
            continue
        if segments_intersect(old_x, old_y, new_x, new_y, blocker.x1, blocker.y1, blocker.x2, blocker.y2):
            return blocker
    return None
