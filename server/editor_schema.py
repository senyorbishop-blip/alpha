from __future__ import annotations

import copy
from typing import Any


MAX_CONTEXT_LEN = 80
MAX_ID_LEN = 64
MAX_NAME_LEN = 120
MAX_TEXT_LEN = 500
INTERACTABLE_ACTION_IDS = {"inspect", "interact", "mark_for_party", "ask_party", "attempt_skill_action", "open", "loot", "disable", "reveal", "exhaust"}
INTERACTABLE_STATES = {"closed", "opened", "looted", "disabled", "revealed", "exhausted"}



def _clone(value: Any) -> Any:
    return copy.deepcopy(value)



def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default



def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default



def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)



def _safe_ctx(value: Any) -> str:
    text = str(value or "world").strip()[:MAX_CONTEXT_LEN]
    return text or "world"



def _safe_id(value: Any, fallback: str) -> str:
    text = str(value or fallback).strip()[:MAX_ID_LEN]
    return text or fallback



def _safe_text(value: Any, fallback: str = "", limit: int = MAX_TEXT_LEN) -> str:
    text = str(value or fallback).strip()[:limit]
    return text or fallback



def _json_safe_extras(src: dict, reserved: set[str]) -> dict:
    extras = {}
    for key, value in src.items():
        if key in reserved or not isinstance(key, str):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            extras[key] = value
        elif isinstance(value, (list, dict)):
            extras[key] = _clone(value)
    return extras



def _clamp_float(value, default: float, minimum: float, maximum: float) -> float:
    try:
        num = float(value)
    except Exception:
        num = default
    return max(minimum, min(maximum, num))



# ── Canonical weather vocabulary (shared by map-settings + persistence) ──
# Keep this list in sync with WEATHER_PRESETS in client/templates/play.html.
VALID_WEATHER_TYPES = {
    "none", "rain", "heavy_rain", "storm", "snow", "blizzard",
    "fog", "ash", "sand", "arcane_storm", "aurora",
}
WEATHER_TYPE_ALIASES = {
    "stormy": "storm", "thunderstorm": "storm", "thunder": "storm",
    "sandstorm": "sand", "sand_storm": "sand", "dust": "sand",
    "snowy": "snow", "cloudy": "fog", "mist": "fog", "windy": "fog",
    "heavy rain": "heavy_rain", "heavyrain": "heavy_rain",
    "heavy-rain": "heavy_rain", "downpour": "heavy_rain",
    "embers": "ash", "magic": "arcane_storm", "magical": "arcane_storm",
    "arcane storm": "arcane_storm",
}


def canonical_weather_type(value: Any) -> str:
    """Map any legacy / saved / user weather type onto a known canonical key.

    Unknown types fall back to 'none' so old or malformed maps never break.
    """
    key = str(value if value is not None else "none").strip().lower().replace(" ", "_")
    key = WEATHER_TYPE_ALIASES.get(key, key)
    return key if key in VALID_WEATHER_TYPES else "none"


def normalize_weather_block(raw: Any) -> dict:
    """Canonical, backward-compatible weather shape for a single map context.

    Accepts both the legacy editor shape ({type, wind}) and the runtime shape
    ({weather_type, wind_speed, wind_angle}). Emits the snake_case superset used
    on the wire / in persistence, plus a legacy ``wind`` mirror for older readers.
    """
    w = dict(raw or {})
    canon = canonical_weather_type(w.get("type", w.get("weather_type", "none")))
    wind_speed = _clamp_float(
        w.get("wind_speed", w.get("windSpeed", w.get("wind", 0.2))), 0.2, 0.0, 1.0
    )
    return {
        "enabled": _coerce_bool(w.get("enabled"), False),
        "type": canon,
        # mirror canonical type under both names so either reader resolves it
        "weather_type": canon,
        "intensity": _clamp_float(w.get("intensity", 0.5), 0.5, 0.0, 1.0),
        "wind_speed": wind_speed,
        # legacy single-field readers still expect ``wind``
        "wind": wind_speed,
        "wind_angle": _clamp_float(w.get("wind_angle", w.get("windAngle", 0.0)), 0.0, 0.0, 360.0),
        "darkness": _clamp_float(w.get("darkness", 0.0), 0.0, 0.0, 1.0),
        "lightning_frequency": _clamp_float(
            w.get("lightning_frequency", w.get("lightningFrequency", 0.5)), 0.5, 0.0, 1.0
        ),
        "audio_linked": _coerce_bool(w.get("audio_linked", w.get("audioLinked", True)), True),
    }



def normalize_map_settings(raw: dict | None) -> dict:
    src = dict(raw or {})
    weather = dict(src.get('weather') or {})
    vision = dict(src.get('vision') or {})
    lighting = dict(src.get('lighting') or {})
    world = dict(src.get('world') or {})
    grid = dict(src.get('grid') or {})
    editor_mode = str(src.get('editor_mode') or 'tactical').lower()
    if editor_mode not in {'world', 'tactical'}:
        editor_mode = 'tactical'
    return {
        'fog_player_alpha': _clamp_float(src.get('fog_player_alpha', 1.0), 1.0, 0.0, 1.0),
        'fog_dm_alpha': _clamp_float(src.get('fog_dm_alpha', 0.66), 0.66, 0.0, 1.0),
        'editor_mode': editor_mode,
        'world': {
            'show_grid': bool(world.get('show_grid', False)),
            'terrain_opacity': _clamp_float(world.get('terrain_opacity', 0.82), 0.82, 0.35, 1.0),
            'allow_player_ping': bool(world.get('allow_player_ping', True)),
        },
        'grid': {
            'size_px': int(_clamp_float(grid.get('size_px', 64), 64, 16, 256)),
        },
        'weather': normalize_weather_block(weather),
        'vision': {
            'enabled': bool(vision.get('enabled', True)),
            'door_blocks_vision_when_closed': bool(vision.get('door_blocks_vision_when_closed', True)),
            'wall_blocks_vision': bool(vision.get('wall_blocks_vision', True)),
        },
        'lighting': {
            'enabled': bool(lighting.get('enabled', False)),
            'ambient': _clamp_float(lighting.get('ambient', 0.15), 0.15, 0.0, 1.0),
        },
    }



def normalize_terrain_cells(raw: Any) -> dict:
    src = raw if isinstance(raw, dict) else {}
    cells = {}
    for key, value in src.items():
        if value in (None, "", False):
            continue
        safe_key = str(key).strip()[:64]
        if not safe_key:
            continue
        if isinstance(value, str):
            safe_value = value.strip()[:64]
            if safe_value:
                cells[safe_key] = safe_value
        elif isinstance(value, (int, float)):
            cells[safe_key] = str(int(value))
        elif value is True:
            cells[safe_key] = "1"
    return cells



def normalize_wall(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    wall = {
        "id": _safe_id(raw.get("id"), f"wall-{index + 1}"),
        "x1": _coerce_float(raw.get("x1"), 0.0),
        "y1": _coerce_float(raw.get("y1"), 0.0),
        "x2": _coerce_float(raw.get("x2"), 0.0),
        "y2": _coerce_float(raw.get("y2"), 0.0),
        "door": _coerce_bool(raw.get("door"), False),
        "open": _coerce_bool(raw.get("open"), False),
        "secret": _coerce_bool(raw.get("secret"), False),
        "blocks_movement": _coerce_bool(raw.get("blocks_movement"), True),
        "blocks_vision": _coerce_bool(raw.get("blocks_vision"), True),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    wall.update(_json_safe_extras(raw, set(wall.keys())))
    return wall



def normalize_prop(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    prop = {
        "id": _safe_id(raw.get("id"), f"prop-{index + 1}"),
        "kind": _safe_text(raw.get("kind"), "prop", 40),
        "name": _safe_text(raw.get("name"), "", MAX_NAME_LEN),
        "x": _coerce_float(raw.get("x"), 0.0),
        "y": _coerce_float(raw.get("y"), 0.0),
        "width": max(0.0, _coerce_float(raw.get("width"), 0.0)),
        "height": max(0.0, _coerce_float(raw.get("height"), 0.0)),
        "rotation": _coerce_float(raw.get("rotation"), 0.0),
        "scale": max(0.0, _coerce_float(raw.get("scale"), 1.0)),
        "visible": _coerce_bool(raw.get("visible"), True),
        "locked": _coerce_bool(raw.get("locked"), False),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    prop.update(_json_safe_extras(raw, set(prop.keys())))
    interactable = prop.get("interactable")
    if isinstance(interactable, dict):
        enabled = _coerce_bool(interactable.get("enabled"), False)
        actions = []
        seen = set()
        for action in interactable.get("actions") or []:
            if isinstance(action, dict):
                action_id = _safe_text(action.get("id"), "", 40).lower()
                if not action_id or action_id in seen or action_id not in INTERACTABLE_ACTION_IDS:
                    continue
                row = {
                    "id": action_id,
                    "label": _safe_text(action.get("label"), action_id.replace("_", " ").title(), 80),
                }
                skill = _safe_text(action.get("skill"), "", 40).lower()
                if skill:
                    row["skill"] = skill
                seen.add(action_id)
                actions.append(row)
            else:
                action_id = _safe_text(action, "", 40).lower()
                if not action_id or action_id in seen or action_id not in INTERACTABLE_ACTION_IDS:
                    continue
                seen.add(action_id)
                actions.append({"id": action_id, "label": action_id.replace("_", " ").title()})
        permissions = interactable.get("permissions") if isinstance(interactable.get("permissions"), dict) else {}
        visibility = interactable.get("visibility") if isinstance(interactable.get("visibility"), dict) else {}
        states_src = interactable.get("states") if isinstance(interactable.get("states"), dict) else {}
        states = {}
        for state_id, state_raw in states_src.items():
            clean_state = _safe_text(state_id, "", 32).lower()
            if clean_state not in INTERACTABLE_STATES or not isinstance(state_raw, dict):
                continue
            state_actions = []
            state_seen = set()
            for action in state_raw.get("available_actions") or []:
                if isinstance(action, dict):
                    action_id = _safe_text(action.get("id"), "", 40).lower()
                    if not action_id or action_id in state_seen or action_id not in INTERACTABLE_ACTION_IDS:
                        continue
                    row = {
                        "id": action_id,
                        "label": _safe_text(action.get("label"), action_id.replace("_", " ").title(), 80),
                    }
                    skill = _safe_text(action.get("skill"), "", 40).lower()
                    if skill:
                        row["skill"] = skill
                    state_seen.add(action_id)
                    state_actions.append(row)
                else:
                    action_id = _safe_text(action, "", 40).lower()
                    if not action_id or action_id in state_seen or action_id not in INTERACTABLE_ACTION_IDS:
                        continue
                    state_seen.add(action_id)
                    state_actions.append({"id": action_id, "label": action_id.replace("_", " ").title()})
            next_state_by_action = {}
            for action_id, next_state in dict(state_raw.get("next_state_by_action") or {}).items():
                clean_action = _safe_text(action_id, "", 40).lower()
                clean_next = _safe_text(next_state, "", 32).lower()
                if clean_action in INTERACTABLE_ACTION_IDS and clean_next in INTERACTABLE_STATES:
                    next_state_by_action[clean_action] = clean_next
            states[clean_state] = {
                "label_override": _safe_text(state_raw.get("label_override"), "", 120),
                "asset_key_override": _safe_text(state_raw.get("asset_key_override") or state_raw.get("art_override"), "", 120),
                "available_actions": state_actions,
                "one_time_flags": [_safe_text(v, "", 80) for v in list(state_raw.get("one_time_flags") or [])[:30] if _safe_text(v, "", 80)],
                "world_state_flags": {
                    _safe_text(k, "", 80): v for k, v in dict(state_raw.get("world_state_flags") or {}).items() if _safe_text(k, "", 80)
                },
                "discovery_hook": _safe_text(state_raw.get("discovery_hook"), "", 80),
                "discovery_visibility": _safe_text(state_raw.get("discovery_visibility"), "", 32).lower(),
                "handout_unlock_ids": [_safe_text(v, "", 80) for v in list(state_raw.get("handout_unlock_ids") or [])[:30] if _safe_text(v, "", 80)],
                "next_state": _safe_text(state_raw.get("next_state"), "", 32).lower(),
                "next_state_by_action": next_state_by_action,
            }

        interactable_doc = {
            "enabled": enabled or bool(actions),
            "id": _safe_text(interactable.get("id"), "", 48),
            "kind": _safe_text(interactable.get("kind"), "", 40).lower(),
            "prompt": _safe_text(interactable.get("prompt") or interactable.get("prompt_text"), "", 240),
            "actions": actions,
            "permissions": {
                "dm_only": _coerce_bool(permissions.get("dm_only"), False),
                "requires_token": _coerce_bool(permissions.get("requires_token"), False),
                "allow_players": _coerce_bool(permissions.get("allow_players"), True),
                "allow_viewers": _coerce_bool(permissions.get("allow_viewers"), False),
            },
            "visibility": {
                "mode": _safe_text(visibility.get("mode"), "public", 24).lower(),
                "discovery_visibility": _safe_text(visibility.get("discovery_visibility"), "", 32).lower(),
            },
            "discovery_hook": _safe_text(interactable.get("discovery_hook"), "", 80),
        }
        if states:
            interactable_doc["states"] = states
            current_state = _safe_text(interactable.get("current_state") or interactable.get("state"), "", 32).lower()
            if current_state in INTERACTABLE_STATES:
                interactable_doc["current_state"] = current_state
            used_flags = sorted({_safe_text(v, "", 80) for v in list(interactable.get("used_one_time_flags") or [])[:80] if _safe_text(v, "", 80)})
            if used_flags:
                interactable_doc["used_one_time_flags"] = used_flags
        prop["interactable"] = interactable_doc
    return prop



def normalize_path(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    points = []
    for point in raw.get("points") or []:
        if not isinstance(point, dict):
            continue
        points.append({"x": _coerce_float(point.get("x"), 0.0), "y": _coerce_float(point.get("y"), 0.0)})
    path = {
        "id": _safe_id(raw.get("id"), f"path-{index + 1}"),
        "points": points,
        "color": _safe_text(raw.get("color"), "#ffffff", 32),
        "width": max(0.0, _coerce_float(raw.get("width"), 2.0)),
        "closed": _coerce_bool(raw.get("closed"), False),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    path.update(_json_safe_extras(raw, set(path.keys())))
    return path



def normalize_label(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    label = {
        "id": _safe_id(raw.get("id"), f"label-{index + 1}"),
        "text": _safe_text(raw.get("text"), "", 240),
        "x": _coerce_float(raw.get("x"), 0.0),
        "y": _coerce_float(raw.get("y"), 0.0),
        "font_size": max(1, _coerce_int(raw.get("font_size"), 16)),
        "color": _safe_text(raw.get("color"), "#ffffff", 32),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    label.update(_json_safe_extras(raw, set(label.keys())))
    return label



def normalize_marker(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    marker = {
        "id": _safe_id(raw.get("id"), f"marker-{index + 1}"),
        "kind": _safe_text(raw.get("kind"), "marker", 40),
        "label": _safe_text(raw.get("label"), "", MAX_NAME_LEN),
        "x": _coerce_float(raw.get("x"), 0.0),
        "y": _coerce_float(raw.get("y"), 0.0),
        "color": _safe_text(raw.get("color"), "#ffffff", 32),
        "visible": _coerce_bool(raw.get("visible"), True),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    marker.update(_json_safe_extras(raw, set(marker.keys())))
    return marker



def normalize_light(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    light = {
        "id": _safe_id(raw.get("id"), f"light-{index + 1}"),
        "x": _coerce_float(raw.get("x"), 0.0),
        "y": _coerce_float(raw.get("y"), 0.0),
        "radius": max(0.0, _coerce_float(raw.get("radius"), 0.0)),
        "intensity": _clamp_float(raw.get("intensity", 1.0), 1.0, 0.0, 1.0),
        "color": _safe_text(raw.get("color"), "#ffffff", 32),
        "enabled": _coerce_bool(raw.get("enabled"), True),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    light.update(_json_safe_extras(raw, set(light.keys())))
    return light



def normalize_hazard(raw: Any, *, index: int = 0, map_context: str = "world") -> dict | None:
    if not isinstance(raw, dict):
        return None
    hazard = {
        "id": _safe_id(raw.get("id"), f"hazard-{index + 1}"),
        "name": _safe_text(raw.get("name"), "Hazard", MAX_NAME_LEN),
        "shape": _safe_text(raw.get("shape"), "rect", 24),
        "x": _coerce_float(raw.get("x"), 0.0),
        "y": _coerce_float(raw.get("y"), 0.0),
        "width": max(0.0, _coerce_float(raw.get("width"), 0.0)),
        "height": max(0.0, _coerce_float(raw.get("height"), 0.0)),
        "radius": max(0.0, _coerce_float(raw.get("radius"), 0.0)),
        "color": _safe_text(raw.get("color"), "#ff0000", 32),
        "visible": _coerce_bool(raw.get("visible"), True),
        "map_context": _safe_ctx(raw.get("map_context") or map_context),
    }
    hazard.update(_json_safe_extras(raw, set(hazard.keys())))
    return hazard



def normalize_map_asset_bundle(raw: Any) -> dict:
    src = raw if isinstance(raw, dict) else {}
    background_layers = []
    for entry in src.get("background_layers") or []:
        if not isinstance(entry, dict):
            continue
        background_layers.append(
            {
                **_json_safe_extras(entry, {"id", "url", "opacity", "visible"}),
                "id": _safe_id(entry.get("id"), f"bg-{len(background_layers) + 1}"),
                "url": _safe_text(entry.get("url"), "", 400),
                "opacity": _clamp_float(entry.get("opacity", 1.0), 1.0, 0.0, 1.0),
                "visible": _coerce_bool(entry.get("visible"), True),
            }
        )
    return {
        "background_url": _safe_text(src.get("background_url"), "", 400) or None,
        "background_layers": background_layers,
    }



def normalize_grid(raw: Any, *, tile_size_px: int = 50, feet_per_tile: int = 5) -> dict:
    src = raw if isinstance(raw, dict) else {}
    return {
        "tile_size_px": max(1, _coerce_int(src.get("tile_size_px"), tile_size_px)),
        "feet_per_tile": max(1, _coerce_int(src.get("feet_per_tile"), feet_per_tile)),
        "snap": _coerce_bool(src.get("snap"), True),
    }
