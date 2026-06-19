"""
server/handlers/common.py — Shared imports, constants, and utility functions
used across all handler sub-modules.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)
from server.session import (
    Session, User, build_token_runtime_payload,
)
from server.db import save_campaign_async
from server.connections import manager
from server.editor_schema import normalize_map_settings
from server.map_document import refresh_session_map_documents

PX_PER_GRID = 50.0
FT_PER_GRID = 5.0


def _is_dm_token(token) -> bool:
    """True if token was created by DM (no owner)."""
    return not getattr(token, "owner_id", None)


def _can_user_see_token(token, user) -> bool:
    if not user:
        return False
    if user.role == "dm":
        return True
    return not getattr(token, "hidden", False)


def _is_token_visible_to_user(session: Session, token, user: User) -> bool:
    if not _can_user_see_token(token, user):
        return False
    role = str(getattr(user, "role", "") or "").strip().lower() or "viewer"
    if role == "dm":
        return True
    visible_contexts = session.visible_map_contexts_for_user(getattr(user, "id", ""))
    token_ctx = str(getattr(token, "map_context", "world") or "world")
    return token_ctx in visible_contexts


async def _broadcast_token_event(manager, session, msg_type: str, payload: dict, token,
                                  exclude_user: str = None):
    """Broadcast a token event to everyone who can currently see the token."""
    for uid, u in session.users.items():
        if uid == exclude_user:
            continue
        if _is_token_visible_to_user(session, token, u):
            await manager.send_to(session.id, uid, {"type": msg_type, "payload": payload})


def _visible_tokens_payload_for_user(session: Session, user: User) -> dict:
    role = str(getattr(user, "role", "") or "").strip().lower() or "viewer"
    visible_contexts = session.visible_map_contexts_for_user(getattr(user, "id", "")) if role != "dm" else set()
    tokens = {}
    for tid, token in (session.tokens or {}).items():
        if role == "dm":
            tokens[tid] = build_token_runtime_payload(session, token)
            continue
        if getattr(token, "hidden", False):
            continue
        token_ctx = str(getattr(token, "map_context", "world") or "world")
        if token_ctx not in visible_contexts:
            continue
        tokens[tid] = build_token_runtime_payload(session, token)
    return tokens


async def _broadcast_token_state_sync(session: Session):
    """Send an authoritative token snapshot to every connected client."""
    for uid, u in (session.users or {}).items():
        await manager.send_to(session.id, uid, {
            "type": "tokens_sync",
            "payload": {
                "tokens": _visible_tokens_payload_for_user(session, u),
                "corpse_states": dict(getattr(session, "corpse_states", {}) or {}),
                "dm_map_context": str(getattr(session, "dm_map_context", "world") or "world"),
                "map_nav_version": int(getattr(session, "map_nav_version", 0) or 0),
            },
        })


def _visible_hazard_zones_for_user(session: Session, user: User) -> dict:
    zones = {}
    for zid, zone in (getattr(session, 'hazard_zones', None) or {}).items():
        if not isinstance(zone, dict):
            continue
        if user.role != 'dm' and bool(zone.get('hidden_from_players')):
            continue
        zones[str(zid)] = dict(zone)
    return zones


async def _broadcast_hazard_state(session: Session):
    for uid, u in (session.users or {}).items():
        await manager.send_to(session.id, uid, {
            'type': 'hazard_zones_sync',
            'payload': {'hazard_zones': _visible_hazard_zones_for_user(session, u)}
        })


def _safe_int(value, default=0, *, minimum=None, maximum=None):
    try:
        out = int(value)
    except Exception:
        out = default
    if minimum is not None and out < minimum:
        out = minimum
    if maximum is not None and out > maximum:
        out = maximum
    return out


def _safe_float(value, default=0.0, *, minimum=None, maximum=None):
    try:
        out = float(value)
    except Exception:
        out = default
    if minimum is not None and out < minimum:
        out = minimum
    if maximum is not None and out > maximum:
        out = maximum
    return out


def _refresh_map_documents(session: Session, map_context: str | None = None) -> None:
    try:
        refresh_session_map_documents(session, map_context)
    except Exception as exc:
        logger.error("[MAPDOC] refresh failed for %s: %s", getattr(session, 'id', 'unknown'), exc)


def _sanitize_token_vision_payload(raw: dict | None, *, owner_id: str | None = None, token_type: str | None = None, existing: Any = None) -> dict:
    raw = dict(raw or {})
    existing_enabled = bool(getattr(existing, 'vision_enabled', False)) if existing is not None else False
    existing_radius = _safe_int(getattr(existing, 'vision_radius', 0) if existing is not None else 0, 0, minimum=0, maximum=1000)
    existing_bright = _safe_int(getattr(existing, 'bright_radius', 0) if existing is not None else 0, 0, minimum=0, maximum=1000)
    existing_dim = _safe_int(getattr(existing, 'dim_radius', 0) if existing is not None else 0, 0, minimum=0, maximum=1000)
    existing_dark = bool(getattr(existing, 'has_darkvision', False)) if existing is not None else False
    existing_dark_radius = _safe_int(getattr(existing, 'darkvision_radius', 0) if existing is not None else 0, 0, minimum=0, maximum=1000)

    is_player_owned = bool(str(owner_id or '').strip())
    token_kind = str(token_type or '').strip().lower()
    default_enabled = is_player_owned or token_kind == 'player'
    default_radius = 60 if default_enabled else 0

    enabled = bool(raw.get('visionEnabled', raw.get('vision_enabled', existing_enabled if existing is not None else default_enabled)))
    radius = _safe_int(raw.get('visionRadius', raw.get('vision_radius', existing_radius if existing is not None else default_radius)), existing_radius if existing is not None else default_radius, minimum=0, maximum=1000)
    bright = _safe_int(raw.get('brightRadius', raw.get('bright_radius', existing_bright if existing is not None else 0)), existing_bright if existing is not None else 0, minimum=0, maximum=1000)
    dim = _safe_int(raw.get('dimRadius', raw.get('dim_radius', existing_dim if existing is not None else 0)), existing_dim if existing is not None else 0, minimum=0, maximum=1000)
    has_dark = bool(raw.get('hasDarkvision', raw.get('has_darkvision', existing_dark if existing is not None else False)))
    dark_radius = _safe_int(raw.get('darkvisionRadius', raw.get('darkvision_radius', existing_dark_radius if existing is not None else 0)), existing_dark_radius if existing is not None else 0, minimum=0, maximum=1000)

    if not enabled:
        radius = 0
        bright = 0
        dim = 0
        if not has_dark:
            dark_radius = 0
    else:
        if radius == 0 and bright == 0 and dim == 0:
            radius = default_radius or 60
        if bright == 0 and dim == 0:
            bright = radius
        if dim == 0:
            dim = max(radius, bright)
        radius = max(radius, bright, dim)
        bright = min(bright, radius)
        dim = max(bright, min(dim, radius))
    if not has_dark:
        dark_radius = 0

    return {
        'vision_enabled': bool(enabled),
        'vision_radius': int(radius),
        'bright_radius': int(bright),
        'dim_radius': int(dim),
        'has_darkvision': bool(has_dark),
        'darkvision_radius': int(dark_radius),
    }


def _token_center(token) -> tuple[float, float]:
    return (float(getattr(token, 'x', 0.0) or 0.0) + float(getattr(token, 'width', 0.0) or 0.0) / 2.0,
            float(getattr(token, 'y', 0.0) or 0.0) + float(getattr(token, 'height', 0.0) or 0.0) / 2.0)


def _token_map_context(token) -> str:
    return str(getattr(token, 'map_context', 'world') or 'world')


def _apply_damage(token, amount: int) -> int:
    if getattr(token, 'hp', None) is None:
        return 0
    dmg = max(0, int(amount or 0))
    temp_hp = max(0, int(getattr(token, 'temp_hp', 0) or 0))
    absorbed = min(temp_hp, dmg)
    token.temp_hp = temp_hp - absorbed
    real = dmg - absorbed
    token.hp = max(0, int(token.hp or 0) - real)
    return dmg


def _apply_heal(token, amount: int) -> int:
    """Apply healing to a token. Restores HP up to max_hp; any excess converts to temp HP."""
    if getattr(token, 'hp', None) is None:
        return 0
    heal = max(0, int(amount or 0))
    max_hp = getattr(token, 'max_hp', None)
    if max_hp is None:
        token.hp = int(token.hp or 0) + heal
        return heal
    current_hp = int(token.hp or 0)
    max_hp_int = int(max_hp or 0)
    headroom = max(0, max_hp_int - current_hp)
    actual = min(heal, headroom)
    overflow = heal - actual
    token.hp = current_hp + actual
    # Overflow healing beyond max HP is stored as temporary HP (not added to max_hp)
    if overflow > 0:
        token.temp_hp = max(0, int(getattr(token, 'temp_hp', 0) or 0)) + overflow
    return heal


def _sanitize_save_bonuses(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    safe = {}
    for key in ("str", "dex", "con", "int", "wis", "cha"):
        value = raw.get(key, raw.get(key.upper(), raw.get(key.capitalize())))
        if value is None or str(value).strip() == '':
            continue
        try:
            safe[key] = int(value)
        except Exception:
            continue
    return safe


async def _broadcast_token_visibility(session, token, msg_type: str = "token_hidden_changed"):
    """Send token visibility/update state per user when a token is edited or hidden/revealed."""
    token_payload = build_token_runtime_payload(session, token)
    for uid, u in session.users.items():
        if _is_token_visible_to_user(session, token, u):
            await manager.send_to(session.id, uid, {"type": msg_type, "payload": token_payload})
        elif str(getattr(u, "role", "") or "").strip().lower() != "dm" and token.hidden:
            await manager.send_to(session.id, uid, {
                "type": "token_removed_hidden",
                "payload": {"id": token.id}
            })


def _get_combatant_by_token_id(session: Session, token_id: str) -> dict | None:
    combat = getattr(session, "combat", None) or {}
    for combatant in list(combat.get("combatants") or []):
        if str((combatant or {}).get("token_id") or "") == str(token_id or ""):
            return combatant
    return None


def _sync_combatant_token_state(session: Session, token, *, previous_hp: int | None = None) -> bool:
    if token is None:
        return False
    combatant = _get_combatant_by_token_id(session, getattr(token, "id", ""))
    if not combatant:
        return False
    changed = False
    token_hp = getattr(token, "hp", None)
    token_max_hp = getattr(token, "max_hp", None)
    if combatant.get("hp") != token_hp:
        combatant["hp"] = token_hp
        changed = True
    if combatant.get("max_hp") != token_max_hp:
        combatant["max_hp"] = token_max_hp
        changed = True
    if getattr(token, "speed", None) is not None and combatant.get("speed") != getattr(token, "speed", None):
        combatant["speed"] = getattr(token, "speed", None)
        changed = True
    if getattr(token, "owner_id", None) and combatant.get("owner_id") != getattr(token, "owner_id", None):
        combatant["owner_id"] = getattr(token, "owner_id", None)
        changed = True
    is_player = bool(getattr(token, "owner_id", None) or combatant.get("is_player"))
    if is_player:
        if token_hp is not None and token_hp <= 0:
            existing = combatant.get("death_saves") if isinstance(combatant.get("death_saves"), dict) else None
            just_dropped = previous_hp is None or previous_hp > 0
            if not existing or just_dropped:
                combatant["death_saves"] = {"successes": 0, "fails": 0, "stable": False, "dead": False}
                changed = True
        else:
            if combatant.pop("death_saves", None) is not None:
                changed = True
    elif combatant.pop("death_saves", None) is not None:
        changed = True
    return changed


async def _broadcast_combat(session):
    connections = manager.get_session_connections(session.id)
    dead_payload = None
    if not connections:
        await manager.broadcast(session.id, {"type": "combat_state", "payload": session.combat})
        return
    for uid in list(connections.keys()):
        user = (getattr(session, "users", {}) or {}).get(uid)
        payload = session.combat
        if not user or getattr(user, "role", "") != "dm":
            payload = dict(session.combat or {})
            payload.pop("suspended_combatants", None)
            payload.pop("fog_suspended_combatants", None)
            payload.pop("hidden_suspended_combatants", None)
        await manager.send_to(session.id, uid, {"type": "combat_state", "payload": payload})


# ---------------------------------------------------------------------------
# Canonical permission guards
#
# Usage pattern (in any handler):
#
#   async def handle_foo(payload, session, user):
#       if not await require_dm(session, user):
#           return
#       # ... DM-only logic ...
#
# These guards always send an "error" message to the requesting user so the
# client can display feedback instead of silently ignoring the action.
# ---------------------------------------------------------------------------

async def send_error(session: Session, user_id: str, message: str) -> None:
    """Send a typed error message to a single user.

    Prefer this over ad-hoc ``manager.send_to(…)`` calls so all permission
    denials have a consistent ``{"type": "error", …}`` shape on the wire.
    """
    await manager.send_to(session.id, user_id, {
        "type": "error",
        "payload": {"message": message},
    })


async def require_dm(session: Session, user: User, *, message: str = "Only the DM can do this.") -> bool:
    """Guard: return ``True`` when *user* is the DM, otherwise send an error.

    Returns ``False`` (with a feedback message) when the check fails so the
    caller can do a simple early-return::

        if not await require_dm(session, user):
            return
    """
    if user.role == "dm":
        return True
    await send_error(session, user.id, message)
    return False


async def require_role(session: Session, user: User, *roles: str, message: str = "You don't have permission to do this.") -> bool:
    """Guard: return ``True`` when ``user.role`` is in *roles*, otherwise send an error.

    Example — allow DM and player, block viewer::

        if not await require_role(session, user, "dm", "player"):
            return
    """
    if user.role in roles:
        return True
    await send_error(session, user.id, message)
    return False
