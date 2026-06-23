"""
server/handlers/common.py — Shared imports, constants, and utility functions
used across all handler sub-modules.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)
from server.session import (
    Session, User, build_token_runtime_payload, normalize_map_context,
)
from server.db import save_campaign_async
from server.connections import manager
from server.editor_schema import normalize_map_settings
from server.map_document import refresh_session_map_documents

PX_PER_GRID = 50.0
FT_PER_GRID = 5.0


async def _send_action_ack(session: Session, user: User, *, action: str, client_action_id, status: str, **extra):
    """Send a sender-only acknowledgement for a server-authoritative action.

    No-ops if the client didn't send a client_action_id, so older clients
    that never opt in to acks see no behavior change. This is never the
    source of truth — the authoritative broadcast (e.g. token_moved) is
    sent separately, regardless of whether an ack is also sent.
    """
    cid = str(client_action_id or "").strip()
    if not cid:
        return
    payload = {"action": action, "client_action_id": cid, "status": status}
    payload.update(extra)
    await manager.send_to(session.id, user.id, {"type": "action_ack", "payload": payload})


def _is_dm_token(token) -> bool:
    """True if token was created by DM (no owner)."""
    return not getattr(token, "owner_id", None)


def is_player_owned_token(token) -> bool:
    return bool(getattr(token, "owner_id", None)) or bool(getattr(token, "is_player", False)) or str(getattr(token, "token_type", "") or "").lower() in {"player", "pc", "character"}


def is_npc_or_monster_token(token) -> bool:
    if token is None or is_player_owned_token(token):
        return False
    values = {
        str(getattr(token, "token_type", "") or "").lower(),
        str(getattr(token, "creature_type", "") or "").lower(),
        str(getattr(token, "monster_type", "") or "").lower(),
        str(getattr(token, "faction", "") or "").lower(),
    }
    return bool(values & {"npc", "monster", "hostile", "creature", "enemy", "foe", "beast", "undead", "fiend", "construct"})


def _token_occupied_fog_indices(session: Session, token, entry: dict) -> set[int]:
    """Return the fog-cell indices touched by the token's full footprint.

    Fog cells live in the same world-coordinate space as the client fog
    painter: the map image is drawn from ``(-width/2, -height/2)`` to
    ``(width/2, height/2)``.  We compute the token's pixel bounding box
    (covering tiny through gargantuan/custom sizes via token.width/height)
    and return every cell the box overlaps, not just the corners — so a
    large token's edge touching fog is detected even though its corners
    might land on the same revealed cell as its centre.
    """
    cols = _safe_int(entry.get("cols"), 64, minimum=1, maximum=512)
    rows = _safe_int(entry.get("rows"), 64, minimum=1, maximum=512)
    settings = getattr(session, "map_settings", None) or {}
    ctx_settings = settings.get(_token_map_context(token)) if isinstance(settings.get(_token_map_context(token)), dict) else {}
    mw = float(ctx_settings.get("width") or ctx_settings.get("map_width") or 4096)
    mh = float(ctx_settings.get("height") or ctx_settings.get("map_height") or 4096)
    x = float(getattr(token, "x", 0) or 0)
    y = float(getattr(token, "y", 0) or 0)
    w = max(1.0, float(getattr(token, "width", PX_PER_GRID) or PX_PER_GRID))
    h = max(1.0, float(getattr(token, "height", PX_PER_GRID) or PX_PER_GRID))

    def cell_for(px: float, py: float):
        col = int((px + mw / 2) / mw * cols)
        row = int((py + mh / 2) / mh * rows)
        if 0 <= col < cols and 0 <= row < rows:
            return col, row
        return None

    points = [
        (x + w / 2, y + h / 2),  # centre (token.x/y is the top-left corner)
        (x, y),
        (x + w, y),
        (x, y + h),
        (x + w, y + h),
    ]
    cells = [cell for cell in (cell_for(px, py) for px, py in points) if cell is not None]
    if not cells:
        return set()
    min_col = max(0, min(col for col, _ in cells))
    max_col = min(cols - 1, max(col for col, _ in cells))
    min_row = max(0, min(row for _, row in cells))
    max_row = min(rows - 1, max(row for _, row in cells))
    return {row * cols + col for row in range(min_row, max_row + 1) for col in range(min_col, max_col + 1)}


def is_token_touching_unrevealed_fog(session: Session, token, map_context: str | None = None) -> bool:
    """True as soon as any part of the token's footprint sits on unrevealed fog.

    This is intentionally the inverse of "fully inside revealed fog" — a
    token must be hidden the instant any edge of its footprint crosses into
    unrevealed territory, not only once the whole token (or its centre) is
    buried in fog.
    """
    if token is None:
        return False
    ctx = normalize_map_context(map_context or _token_map_context(token))
    fog_maps = getattr(session, "fog_maps", None) or {}
    entry = (fog_maps.get(ctx) or {})
    if not entry:
        for key, candidate in fog_maps.items():
            if normalize_map_context(key) == ctx:
                entry = candidate or {}
                break
    if not entry.get("enabled", False):
        return False
    raw_cells = entry.get("cells")
    cells = raw_cells if isinstance(raw_cells, str) else "".join("1" if int(v or 0) else "0" for v in (raw_cells or []))
    footprint = _token_occupied_fog_indices(session, token, entry) if cells else set()
    if not cells or not footprint:
        touching = True  # fail closed: fog enabled but no usable data/footprint means unrevealed
    else:
        touching = any(not (0 <= i < len(cells) and cells[i] == "1") for i in footprint)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("[fog visibility] %s", {
            "tokenName": getattr(token, "name", None),
            "tokenId": getattr(token, "id", None),
            "tokenX": getattr(token, "x", None),
            "tokenY": getattr(token, "y", None),
            "tokenWidth": getattr(token, "width", None),
            "tokenHeight": getattr(token, "height", None),
            "mapContext": ctx,
            "footprintCells": sorted(footprint) if footprint else [],
            "footprintTouchesUnrevealedFog": touching,
            "hidden": bool(getattr(token, "hidden", False)),
        })
    return touching


def _can_user_see_token(session: Session, token, user) -> bool:
    if not user:
        return False
    if user.role == "dm":
        return True
    if getattr(token, "hidden", False):
        return False
    if is_npc_or_monster_token(token) and is_token_touching_unrevealed_fog(session, token):
        return False
    return True


def _is_token_visible_to_user(session: Session, token, user: User) -> bool:
    if not _can_user_see_token(session, token, user):
        return False
    role = str(getattr(user, "role", "") or "").strip().lower() or "viewer"
    if role == "dm":
        return True
    visible_contexts = session.visible_map_contexts_for_user(getattr(user, "id", ""))
    token_ctx = normalize_map_context(getattr(token, "map_context", "world"))
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
        if not _can_user_see_token(session, token, user):
            continue
        token_ctx = normalize_map_context(getattr(token, "map_context", "world"))
        if token_ctx not in visible_contexts:
            continue
        tokens[tid] = build_token_runtime_payload(session, token)
    return tokens


def build_live_state_debug_summary(session: Session, user_id: str, role: str | None, state_payload: dict | None = None) -> dict:
    """Build a safe, structured reconnect/state diagnostic summary.

    The summary intentionally includes only counts, ids, revisions, and booleans.
    It never returns hidden token payloads or token names, so it is safe to emit
    for player/viewer reconnect diagnostics.
    """
    payload = state_payload if isinstance(state_payload, dict) else {}
    resolved_role = str(role or "").strip().lower() or "viewer"
    user = (getattr(session, "users", {}) or {}).get(user_id)
    if user is not None:
        resolved_role = str(getattr(user, "role", resolved_role) or resolved_role).strip().lower() or resolved_role

    sent_tokens = payload.get("tokens") if isinstance(payload.get("tokens"), dict) else {}
    all_tokens = getattr(session, "tokens", {}) or {}
    hidden_filtered = 0
    fog_filtered = 0
    if resolved_role != "dm":
        visible_ids = {str(tid) for tid in sent_tokens.keys()}
        for tid, token in all_tokens.items():
            tid_s = str(tid)
            if tid_s in visible_ids:
                continue
            if bool(getattr(token, "hidden", False)):
                hidden_filtered += 1
                continue
            if is_npc_or_monster_token(token) and is_token_touching_unrevealed_fog(session, token):
                fog_filtered += 1

    combat = payload.get("combat") if isinstance(payload.get("combat"), dict) else (getattr(session, "combat", {}) or {})
    map_ctx = str(payload.get("dm_map_context") or getattr(session, "dm_map_context", "world") or "world")
    fog_maps = payload.get("fog_maps") if isinstance(payload.get("fog_maps"), dict) else (getattr(session, "fog_maps", {}) or {})
    fog_entry = fog_maps.get(map_ctx) or fog_maps.get("world") or {}
    active_profiles = getattr(session, "active_char_profiles", {}) or {}
    return {
        "session_id": str(getattr(session, "id", "") or ""),
        "user_id": str(user_id or ""),
        "role": str(role or resolved_role or "viewer"),
        "resolved_role": resolved_role,
        "map_context": map_ctx,
        "map_mode": "world" if map_ctx == "world" else ("local" if map_ctx else "unknown"),
        "map_nav_version": _safe_int(payload.get("map_nav_version", getattr(session, "map_nav_version", 0)), 0, minimum=0),
        "token_count_sent": len(sent_tokens),
        "hidden_tokens_filtered": hidden_filtered,
        "fog_hidden_tokens_filtered": fog_filtered,
        "combat_active": bool(combat.get("active")) if isinstance(combat, dict) else False,
        "combat_revision": _safe_int((combat or {}).get("revision"), 0, minimum=0) if isinstance(combat, dict) else 0,
        "visibility_revision": _safe_int(payload.get("visibility_revision", getattr(session, "visibility_revision", 0)), 0, minimum=0),
        "inventory_revision": _safe_int(payload.get("inventory_revision", getattr(session, "inventory_revision", 0)), 0, minimum=0),
        "active_profile_id": str(active_profiles.get(user_id) or payload.get("active_profile_id") or ""),
        "fog_context": str((fog_entry or {}).get("map_context") or map_ctx or "world"),
        "fog_revision": _safe_int((fog_entry or {}).get("revision"), 0, minimum=0) if isinstance(fog_entry, dict) else 0,
    }


def bump_visibility_revision(session: Session) -> int:
    """Increment the session-wide visibility revision counter.

    Call this whenever fog, hidden state, or token position changes in a
    way that can affect what players are allowed to see, so clients can
    discard stale tokens_sync/combat_state payloads that raced behind a
    newer one.
    """
    next_rev = int(getattr(session, "visibility_revision", 0) or 0) + 1
    session.visibility_revision = next_rev
    return next_rev


def bump_inventory_revision(session: Session) -> int:
    """Increment the session-wide inventory revision counter.

    Call this exactly once per real server-authoritative inventory/item
    mutation (add/remove/equip/unequip/transfer/stash/charge spend/rest
    recharge/etc.) so clients can discard a stale `player_inventory_sync`
    payload that raced behind a newer one (e.g. across a brief
    disconnect/reconnect with queued-message flush).
    """
    next_rev = int(getattr(session, "inventory_revision", 0) or 0) + 1
    session.inventory_revision = next_rev
    return next_rev


async def _broadcast_token_state_sync(session: Session):
    """Send an authoritative token snapshot to every connected client."""
    revision = bump_visibility_revision(session)
    for uid, u in (session.users or {}).items():
        payload = {
            "tokens": _visible_tokens_payload_for_user(session, u),
            "corpse_states": dict(getattr(session, "corpse_states", {}) or {}),
            "dm_map_context": str(getattr(session, "dm_map_context", "world") or "world"),
            "map_nav_version": int(getattr(session, "map_nav_version", 0) or 0),
            "visibility_revision": revision,
        }
        logger.info("[live_state] tokens_sync %s", build_live_state_debug_summary(session, uid, getattr(u, "role", "unknown"), payload))
        await manager.send_to(session.id, uid, {
            "type": "tokens_sync",
            "payload": payload,
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
    """Send token visibility/update state per user when a token is edited, moved, or hidden/revealed.

    Covers both directions of a visibility flip: a user who can now see the
    token gets the full payload (so it appears even if they never had it,
    e.g. it just walked out of fog); a user who can no longer see it gets a
    removal notice (token went hidden, staged, or behind unrevealed fog).
    """
    bump_visibility_revision(session)
    token_payload = build_token_runtime_payload(session, token)
    for uid, u in session.users.items():
        if _is_token_visible_to_user(session, token, u):
            await manager.send_to(session.id, uid, {"type": msg_type, "payload": token_payload})
        elif str(getattr(u, "role", "") or "").strip().lower() != "dm":
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


def _combat_state_payload_for_user(session: Session, user: User | None, visibility_revision: int | None = None) -> dict:
    payload = dict(getattr(session, "combat", None) or {})
    if not user or getattr(user, "role", "") != "dm":
        visible_combatants = []
        for combatant in payload.get("combatants") or []:
            if not isinstance(combatant, dict):
                continue
            token_id = str(combatant.get("token_id") or "")
            token = (getattr(session, "tokens", {}) or {}).get(token_id) if token_id else None
            if token is not None and is_npc_or_monster_token(token):
                map_context = str(combatant.get("map_context") or _token_map_context(token) or getattr(session, "dm_map_context", "world") or "world")
                if bool(getattr(token, "hidden", False)) or bool(getattr(token, "staged", False)) or is_token_touching_unrevealed_fog(session, token, map_context):
                    continue
            visible_combatants.append(combatant)
        payload["combatants"] = visible_combatants
        payload["turn"] = _safe_int(payload.get("turn"), 0, minimum=0, maximum=max(0, len(visible_combatants) - 1))
        payload.pop("suspended_combatants", None)
        payload.pop("fog_suspended_combatants", None)
        payload.pop("hidden_suspended_combatants", None)
    if visibility_revision is not None:
        payload["visibility_revision"] = visibility_revision
    return payload


def _combat_payload_debug_summary(payload: dict) -> dict:
    combatants = payload.get("combatants") if isinstance(payload, dict) else []
    if not isinstance(combatants, list):
        combatants = []
    turn = _safe_int(payload.get("turn"), 0, minimum=0, maximum=max(0, len(combatants) - 1)) if isinstance(payload, dict) else 0
    current = combatants[turn] if 0 <= turn < len(combatants) else None
    return {
        "revision": payload.get("revision") if isinstance(payload, dict) else None,
        "order": [f"{(c or {}).get('name') or (c or {}).get('id') or (c or {}).get('token_id') or '?'}:{(c or {}).get('initiative', '--')}" for c in combatants],
        "turn": turn,
        "current": (current or {}).get("name") if isinstance(current, dict) else None,
    }


async def _broadcast_combat(session):
    revision = bump_visibility_revision(session)
    connections = manager.get_session_connections(session.id)
    sent_to = []
    failed = []
    attempted = []
    for uid in list(connections.keys()):
        user = (getattr(session, "users", {}) or {}).get(uid)
        role = getattr(user, "role", "unknown") if user else "unknown"
        payload = _combat_state_payload_for_user(session, user, revision)
        summary = _combat_payload_debug_summary(payload)
        attempted.append({"user_id": uid, "role": role})
        ok = await manager.send_to(session.id, uid, {"type": "combat_state", "payload": payload})
        log_data = {**summary, "session_id": session.id, "user_id": uid, "role": role, "send_to_success": bool(ok)}
        if ok:
            sent_to.append(uid)
            logger.info("[combat initiative sync] delivered %s", log_data)
        else:
            failed.append(uid)
            logger.warning("[combat initiative sync] failed_send %s", log_data)
    if not connections:
        payload = dict(getattr(session, "combat", None) or {})
        payload["visibility_revision"] = revision
        summary = _combat_payload_debug_summary(payload)
        logger.info("[combat initiative sync] no active sockets %s", {**summary, "session_id": session.id, "sent_to": []})
        await manager.broadcast(session.id, {"type": "combat_state", "payload": payload})
    logger.info(
        "[combat initiative sync] broadcast_complete revision=%s attempted=%s sent_to=%s failed=%s",
        (getattr(session, "combat", None) or {}).get("revision"),
        attempted,
        sent_to,
        failed,
    )
    return {"attempted": [entry["user_id"] for entry in attempted], "sent_to": sent_to, "failed": failed, "visibility_revision": revision}


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
