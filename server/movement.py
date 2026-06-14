"""Shared grid movement resolver for combat movement preview and commit."""
from __future__ import annotations

from math import hypot

PX_PER_GRID = 50.0
FT_PER_GRID = 5.0
VALID_MOVEMENT_MODES = {"grid_5e_default", "grid_5_10_5", "euclidean"}


def normalize_movement_mode(mode: str | None) -> str:
    mode = str(mode or "").strip().lower()
    return mode if mode in VALID_MOVEMENT_MODES else "grid_5e_default"


def _safe_px_per_grid(grid_size_px) -> float:
    try:
        v = float(grid_size_px)
        return v if v >= 10.0 else PX_PER_GRID
    except Exception:
        return PX_PER_GRID


def center_to_grid(x: float, y: float, width: float = PX_PER_GRID, height: float = PX_PER_GRID, *, grid_size_px: float = PX_PER_GRID) -> dict:
    px = _safe_px_per_grid(grid_size_px)
    cx = float(x or 0.0) + float(width or px) / 2.0
    cy = float(y or 0.0) + float(height or px) / 2.0
    return {"x": int(round(cx / px - 0.5)), "y": int(round(cy / px - 0.5))}


def grid_to_top_left(cell: dict, width: float = PX_PER_GRID, height: float = PX_PER_GRID, *, grid_size_px: float = PX_PER_GRID) -> dict:
    px = _safe_px_per_grid(grid_size_px)
    gx = int((cell or {}).get("x") or 0)
    gy = int((cell or {}).get("y") or 0)
    return {"x": gx * px + (px - float(width or px)) / 2.0, "y": gy * px + (px - float(height or px)) / 2.0}


def build_grid_path(from_grid: dict, to_grid: dict) -> list[dict]:
    x0, y0 = int(from_grid.get("x") or 0), int(from_grid.get("y") or 0)
    x1, y1 = int(to_grid.get("x") or 0), int(to_grid.get("y") or 0)
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps <= 0:
        return [{"x": x0, "y": y0}]
    path = []
    for i in range(steps + 1):
        path.append({"x": int(round(x0 + dx * i / steps)), "y": int(round(y0 + dy * i / steps))})
    dedup = []
    for cell in path:
        if not dedup or dedup[-1] != cell:
            dedup.append(cell)
    return dedup


def movement_squares_for_path(path: list[dict], mode: str = "grid_5e_default") -> float:
    mode = normalize_movement_mode(mode)
    total = 0.0
    diagonal_index = 0
    for prev, cur in zip(path, path[1:]):
        dx = abs(int(cur.get("x") or 0) - int(prev.get("x") or 0))
        dy = abs(int(cur.get("y") or 0) - int(prev.get("y") or 0))
        if dx == 0 and dy == 0:
            continue
        if mode == "euclidean":
            total += hypot(dx, dy)
        elif dx and dy:
            diagonal_index += 1
            total += 2.0 if mode == "grid_5_10_5" and diagonal_index % 2 == 0 else 1.0
        else:
            total += max(dx, dy)
    return round(total, 4)


def resolve_movement(*, from_x: float, from_y: float, to_x: float, to_y: float, token_width: float = PX_PER_GRID,
                     token_height: float = PX_PER_GRID, path: list[dict] | None = None, movement_mode: str = "grid_5e_default",
                     speed_feet: float = 30.0, spent_feet: float = 0.0, bonus_feet: float = 0.0,
                     difficult_terrain: bool = False, cost_multiplier: float | None = None,
                     grid_size_px: float = PX_PER_GRID) -> dict:
    mode = normalize_movement_mode(movement_mode)
    px = _safe_px_per_grid(grid_size_px)
    from_grid = center_to_grid(from_x, from_y, token_width, token_height, grid_size_px=px)
    to_grid = center_to_grid(to_x, to_y, token_width, token_height, grid_size_px=px)
    resolved_path = path if isinstance(path, list) and path else build_grid_path(from_grid, to_grid)
    clean_path = [{"x": int((p or {}).get("x") or 0), "y": int((p or {}).get("y") or 0)} for p in resolved_path]
    squares = movement_squares_for_path(clean_path, mode)
    base_feet = round(squares * FT_PER_GRID, 2)
    multiplier = 2.0 if difficult_terrain else float(cost_multiplier if cost_multiplier is not None else 1.0 or 1.0)
    multiplier = max(1.0, multiplier)
    final_cost = round(base_feet * multiplier, 2)
    speed = max(0.0, round(float(speed_feet or 0.0) + float(bonus_feet or 0.0), 2))
    spent = max(0.0, round(float(spent_feet or 0.0), 2))
    remaining = max(0.0, round(speed - spent, 2))
    valid = final_cost <= remaining + 0.01
    reason = "valid"
    if final_cost > 0 and not valid:
        reason = f"Too far: {final_cost:g} ft, only {remaining:g} ft available"
    if difficult_terrain and valid:
        reason = "Difficult terrain: cost doubled"
    return {"fromGrid": from_grid, "toGrid": to_grid, "path": clean_path, "squares": squares,
            "baseFeet": base_feet, "costMultiplier": multiplier, "finalCostFeet": final_cost,
            "speedFeet": speed, "spentFeet": spent, "remainingFeet": remaining,
            "valid": valid, "reason": reason, "movementMode": mode}
