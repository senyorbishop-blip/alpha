"""
server/handlers/viewer_powers.py — Viewer power system: definitions, profiles, and handlers.
"""
import time
import random
import secrets
import re
from server.map_logic import find_movement_blocker
from server.handlers.common import (
    Session, User, manager,
    save_campaign_async,
    PX_PER_GRID, FT_PER_GRID,
    _token_center, _token_map_context,
    _apply_damage, _apply_heal,
    _broadcast_token_visibility,
    _sync_combatant_token_state,
    _broadcast_combat,
)
from server.handlers.conditions import (
    _sanitize_condition_id,
    _set_token_condition,
    _prune_token_condition_timers,
    _broadcast_token_condition_state,
    _roll_simple,
)

VIEWER_BASE_POWER_DEFS = {
    "pebble_toss": {"name": "Pebble Toss", "kind": "single_damage", "dice": (1, 4), "amount": 0, "target_mode": "token", "approval_default": False, "description": "Deal 1d4 damage to one token.", "cooldown_sec": 0},
    "arcane_zap": {"name": "Arcane Zap", "kind": "single_damage", "dice": (1, 10), "amount": 0, "target_mode": "token", "approval_default": False, "description": "Deal 1d10 damage to one token.", "cooldown_sec": 0},
    "healing_spark": {"name": "Healing Spark", "kind": "single_heal", "dice": (1, 4), "amount": 0, "target_mode": "token", "approval_default": False, "description": "Restore 1d4 hit points to one token.", "cooldown_sec": 0},
    "battle_blessing": {"name": "Battle Blessing", "kind": "single_heal", "dice": (1, 8), "amount": 0, "target_mode": "token", "approval_default": False, "description": "Restore 1d8 hit points to one token.", "cooldown_sec": 0},
    "fireball": {"name": "Fireball", "kind": "area_damage", "dice": (4, 6), "amount": 0, "radius_ft": 15, "target_mode": "point", "approval_default": True, "save": "dex", "save_dc": 13, "save_half": True, "description": "15 ft burst, 4d6 fire damage; Dex save DC 13 for half damage.", "cooldown_sec": 90},
    "meteor_pop": {"name": "Meteor Pop", "kind": "area_damage", "dice": (4, 4), "amount": 0, "radius_ft": 10, "target_mode": "point", "approval_default": True, "save": "dex", "save_dc": 12, "save_half": True, "description": "10 ft burst, 4d4 damage; Dex save DC 12 for half damage.", "cooldown_sec": 45},
    "trip_hex": {"name": "Trip Hex", "kind": "single_status", "dice": (1, 1), "amount": 0, "target_mode": "token", "approval_default": False, "condition": "prone", "duration_sec": 30, "save": "str", "save_dc": 12, "save_negates": True, "description": "Knock one token prone for 30 seconds. STR save negates. Also deals an extra 1d6 damage on hit.", "cooldown_sec": 30},
    "flash_freeze": {"name": "Flash Freeze", "kind": "single_status", "dice": (1, 1), "amount": 0, "target_mode": "token", "approval_default": True, "condition": "restrained", "duration_sec": 20, "save": "dex", "save_dc": 12, "save_negates": True, "description": "Freeze one token in place for 20 seconds unless it passes a DEX save.", "cooldown_sec": 45},
    "goo_burst": {"name": "Goo Burst", "kind": "area_status", "dice": (1, 1), "amount": 0, "radius_ft": 10, "target_mode": "point", "approval_default": True, "condition": "restrained", "duration_sec": 20, "save": "dex", "save_dc": 13, "save_negates": True, "description": "10 ft burst that restrains creatures for 20 seconds unless they pass a Dex save. In combat this effectively slows movement.", "cooldown_sec": 75},
    "smoke_burst": {"name": "Smoke Burst", "kind": "area_status", "dice": (1, 1), "amount": 0, "radius_ft": 10, "target_mode": "point", "approval_default": True, "condition": "blinded", "duration_sec": 10, "save": "con", "save_dc": 12, "save_negates": True, "description": "10 ft burst that can blind targets briefly. CON save negates. Good for short vision denial.", "cooldown_sec": 45},
    "knockback": {"name": "Knockback", "kind": "knockback", "dice": (1, 1), "amount": 0, "radius_ft": 5, "target_mode": "point", "approval_default": False, "description": "Blast the nearest token one grid square away from the clicked point.", "cooldown_sec": 30},
    "give_potion": {"name": "Give Potion", "kind": "grant_item", "dice": (1, 1), "amount": 0, "target_mode": "token", "approval_default": False, "description": "Give the targeted player token a Potion of Minor Healing (heals 1d4).", "cooldown_sec": 0, "item_payload": {"name": "Potion of Minor Healing", "notes": "Heals 1d4 HP when used", "qty": 1}},
}
VIEWER_POWER_DEFS = VIEWER_BASE_POWER_DEFS
_ALLOWED_VIEWER_POWER_KINDS = {"single_damage", "single_heal", "area_damage", "single_status", "area_status", "knockback", "grant_item"}
_ALLOWED_SAVE_TYPES = {"", "str", "dex", "con", "int", "wis", "cha"}
_ALLOWED_AREA_SHAPES = {"burst", "cone", "line", "aura"}
_KNOCKBACK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

_FX_COLOR_FOR_KIND = {
    'single_heal': '#fbbf24',
    'area_damage': '#ef4444',
    'single_damage': '#ef4444',
    'single_status': '#a855f7',
    'area_status': '#a855f7',
    'knockback': '#f97316',
    'grant_item': '#fbbf24',
}


def _fx_color_for_kind(kind: str) -> str:
    return _FX_COLOR_FOR_KIND.get(kind, '#a855f7')


def _role(user: User) -> str:
    return str(getattr(user, 'role', '') or '').strip().lower()


def _normalize_viewer_power_def(power_id: str, raw: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get('kind') or '').strip().lower()
    if kind not in _ALLOWED_VIEWER_POWER_KINDS:
        return None
    try:
        dice_num = max(1, min(20, int((raw.get('dice') or [1, 4])[0] if isinstance(raw.get('dice'), (list, tuple)) else raw.get('dice_num', 1))))
        dice_sides = max(2, min(100, int((raw.get('dice') or [1, 4])[1] if isinstance(raw.get('dice'), (list, tuple)) and len(raw.get('dice') or []) > 1 else raw.get('dice_sides', 4))))
    except Exception:
        dice_num, dice_sides = 1, 4
    area_shape = str(raw.get('area_shape') or raw.get('shape') or 'burst').strip().lower()
    if area_shape not in _ALLOWED_AREA_SHAPES:
        area_shape = 'burst'
    is_area = kind in {'area_damage', 'area_status', 'knockback'}
    target_mode = 'point' if is_area and area_shape != 'aura' else 'token'
    save_type = str(raw.get('save') or '').strip().lower()
    if save_type not in _ALLOWED_SAVE_TYPES:
        save_type = ''
    radius_ft = max(5, min(120, int(raw.get('radius_ft', 15) or 15))) if is_area else 0
    line_width_ft = max(5, min(60, int(raw.get('line_width_ft', raw.get('width_ft', 5)) or 5))) if is_area else 0
    cone_angle_deg = max(15, min(180, int(raw.get('cone_angle_deg', 60) or 60))) if is_area else 0
    cooldown_sec = max(0, min(86400, int(raw.get('cooldown_sec', 0) or 0)))
    condition = str(raw.get('condition') or '').strip().lower()[:50]
    duration_sec = max(0, min(86400, int(raw.get('duration_sec', raw.get('duration', 0)) or 0)))
    item_payload = {}
    if kind == 'grant_item':
        raw_item = dict(raw.get('item_payload') or {})
        item_name = str(raw_item.get('name') or '').strip()[:80]
        if item_name:
            item_payload = {
                'name': item_name,
                'notes': str(raw_item.get('notes') or '').strip()[:160],
                'qty': max(1, min(99, int(raw_item.get('qty', 1) or 1))),
            }
    return {
        'name': str(raw.get('name') or power_id).strip()[:60] or power_id,
        'kind': kind,
        'dice': (dice_num, dice_sides),
        'amount': max(-99, min(999, int(raw.get('amount', 0) or 0))),
        'target_mode': target_mode,
        'approval_default': bool(raw.get('approval_default', kind == 'area_damage')),
        'description': str(raw.get('description') or '').strip()[:220] or 'Custom viewer power',
        'radius_ft': radius_ft,
        'area_shape': area_shape,
        'line_width_ft': line_width_ft,
        'cone_angle_deg': cone_angle_deg,
        'save': save_type,
        'save_dc': max(0, min(30, int(raw.get('save_dc', 0) or 0))),
        'save_half': bool(raw.get('save_half', True)),
        'save_negates': bool(raw.get('save_negates', True)),
        'condition': condition,
        'duration_sec': duration_sec,
        'cooldown_sec': cooldown_sec,
        'item_payload': item_payload,
        'custom': True,
    }


def _viewer_power_defs(session: Session) -> dict:
    defs = {k: dict(v) for k, v in VIEWER_BASE_POWER_DEFS.items()}
    raw_catalog = dict(getattr(session, 'viewer_power_catalog', {}) or {})
    clean_catalog = {}
    for power_id, raw in raw_catalog.items():
        pid = str(power_id or '').strip()[:64].lower()
        if not pid or pid in defs:
            continue
        norm = _normalize_viewer_power_def(pid, raw)
        if norm:
            clean_catalog[pid] = norm
    if clean_catalog != raw_catalog:
        session.viewer_power_catalog = clean_catalog
    defs.update(clean_catalog)
    return defs


VIEWER_POWER_PRESETS = {
    "support_pack": {
        "name": "Support Pack",
        "grants": [
            {"power_id": "healing_spark", "charges": 1, "requires_approval": False},
            {"power_id": "battle_blessing", "charges": 1, "requires_approval": False},
        ],
    },
    "chaos_pack": {
        "name": "Chaos Pack",
        "grants": [
            {"power_id": "pebble_toss", "charges": 1, "requires_approval": False},
            {"power_id": "arcane_zap", "charges": 1, "requires_approval": False},
            {"power_id": "fireball", "charges": 1, "requires_approval": True},
        ],
    },
    "boss_pack": {
        "name": "Boss Fight Pack",
        "grants": [
            {"power_id": "arcane_zap", "charges": 1, "requires_approval": False},
            {"power_id": "battle_blessing", "charges": 1, "requires_approval": False},
            {"power_id": "flash_freeze", "charges": 1, "requires_approval": True},
            {"power_id": "meteor_pop", "charges": 1, "requires_approval": True},
        ],
    },
}


def _viewer_key_for_user(user: User) -> str:
    key = str(getattr(user, 'player_key', '') or '').strip()[:64]
    return key or f'user:{user.id}'


def _viewer_key_aliases(user: User) -> list[str]:
    aliases: list[str] = []
    canonical = _viewer_key_for_user(user)
    for candidate in (
        canonical,
        f"user:{getattr(user, 'id', '')}",
        str(getattr(user, 'id', '') or '').strip()[:64],
    ):
        key = str(candidate or '').strip()[:64]
        if key and key not in aliases:
            aliases.append(key)
    return aliases


def _resolve_viewer_profile_key(session: Session, user: User) -> str:
    """Return canonical viewer profile key for user, migrating legacy key shapes."""
    profiles = _get_viewer_profiles(session)
    canonical = _viewer_key_for_user(user)
    if canonical in profiles:
        return canonical
    for alias in _viewer_key_aliases(user):
        if alias in profiles:
            profile = _normalize_viewer_profile(session, user, profiles.get(alias))
            profiles.pop(alias, None)
            profiles[canonical] = profile
            session.viewer_profiles = profiles
            return canonical
    return canonical


def _get_viewer_profiles(session: Session) -> dict:
    return dict(getattr(session, 'viewer_profiles', {}) or {})


def _normalize_viewer_profile(session: Session, user: User, raw: dict | None = None) -> dict:
    raw = dict(raw or {})
    defs = _viewer_power_defs(session)
    powers = raw.get('powers') if isinstance(raw.get('powers'), dict) else {}
    norm_powers = {}
    for power_id, entry in powers.items():
        if power_id not in defs or not isinstance(entry, dict):
            continue
        norm_powers[power_id] = {
            'power_id': power_id,
            'charges': max(0, min(999, int(entry.get('charges', 0) or 0))),
            'enabled': bool(entry.get('enabled', True)),
            'requires_approval': bool(entry.get('requires_approval', defs.get(power_id, {}).get('approval_default', False))),
            'cooldown_sec': max(0, min(86400, int(entry.get('cooldown_sec', defs.get(power_id, {}).get('cooldown_sec', 0)) or 0))),
            'cooldown_until': max(0.0, float(entry.get('cooldown_until', 0.0) or 0.0)),
        }
    return {
        'viewer_key': _viewer_key_for_user(user),
        'user_id': user.id,
        'name': str(user.name or 'Viewer')[:40],
        'powers': norm_powers,
    }


async def _broadcast_viewer_profiles(session: Session):
    profiles = _get_viewer_profiles(session)
    for uid, u in (session.users or {}).items():
        user_role = _role(u)
        if user_role == 'dm':
            payload = profiles
        elif user_role == 'viewer':
            key = _viewer_key_for_user(u)
            payload = {key: profiles.get(key) or _normalize_viewer_profile(session, u)}
        else:
            payload = {}
        await manager.send_to(session.id, uid, {
            'type': 'viewer_profiles_sync',
            'payload': {'viewer_profiles': payload}
        })


def _viewer_catalog_payload(session: Session) -> dict:
    return _viewer_power_defs(session)


async def _broadcast_viewer_power_catalog(session: Session):
    payload = {'viewer_power_catalog': _viewer_catalog_payload(session)}
    await manager.broadcast(session.id, {'type': 'viewer_power_catalog_sync', 'payload': payload})


def _get_or_create_viewer_profile(session: Session, user: User) -> tuple[dict, dict, str]:
    profiles = _get_viewer_profiles(session)
    key = _resolve_viewer_profile_key(session, user)
    profiles = _get_viewer_profiles(session)
    profile = _normalize_viewer_profile(session, user, profiles.get(key))
    profiles[key] = profile
    session.viewer_profiles = profiles
    return profiles, profile, key


def _consume_viewer_power(session: Session, viewer_key: str, power_id: str) -> bool:
    """Consume a viewer power charge.
    The power is always removed entirely so it disappears from the viewer's UI until the DM grants another.
    """
    profiles = _get_viewer_profiles(session)
    profile = dict(profiles.get(viewer_key) or {})
    powers = dict(profile.get('powers') or {})
    if power_id not in powers:
        return False
    powers.pop(power_id, None)
    profile['powers'] = powers
    profiles[viewer_key] = profile
    session.viewer_profiles = profiles
    return True


def _viewer_has_pending_power_request(session: Session, viewer_key: str, power_id: str) -> bool:
    for entry in (_get_pending_viewer_actions(session) or {}).values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get('viewer_key') or '') != viewer_key:
            continue
        if str(entry.get('power_id') or '') != power_id:
            continue
        return True
    return False


def _get_pending_viewer_actions(session: Session) -> dict:
    return dict(getattr(session, 'viewer_pending_actions', {}) or {})


async def _broadcast_viewer_pending(session: Session):
    pending = _get_pending_viewer_actions(session)
    for uid, u in (session.users or {}).items():
        if getattr(u, 'role', '') == 'dm':
            payload = pending
        elif getattr(u, 'role', '') == 'viewer':
            key = _viewer_key_for_user(u)
            payload = {pid: entry for pid, entry in pending.items() if str((entry or {}).get('viewer_key') or '') == key}
        else:
            payload = {}
        await manager.send_to(session.id, uid, {'type': 'viewer_pending_sync', 'payload': {'viewer_pending_actions': payload}})


def _next_pending_viewer_action_id(session: Session) -> str:
    existing = _get_pending_viewer_actions(session)
    while True:
        pid = f"vp_{secrets.token_hex(4)}"
        if pid not in existing:
            return pid


def _build_target_descriptor(session: Session, power: dict, payload: dict):
    target_token_id = str(payload.get('target_token_id') or '').strip()
    source_token_id = str(payload.get('source_token_id') or '').strip()
    point = payload.get('target_point') if isinstance(payload.get('target_point'), dict) else None
    if power.get('target_mode') == 'point':
        if point:
            try:
                x = float(point.get('x')); y = float(point.get('y'))
            except Exception:
                return None, 'Choose a valid point on the map.'
            map_context = str(point.get('map_context') or getattr(session, 'dm_map_context', 'world') or 'world')[:80]
            target = {'mode': 'point', 'x': x, 'y': y, 'map_context': map_context}
            if power.get('kind') == 'knockback' and target_token_id:
                token = (session.tokens or {}).get(target_token_id)
                if token and not getattr(token, 'hidden', False) and not getattr(token, 'staged', False) and _token_map_context(token) == map_context:
                    target['token_id'] = token.id
            if source_token_id:
                source_token = (session.tokens or {}).get(source_token_id)
                if source_token and not getattr(source_token, 'hidden', False) and not getattr(source_token, 'staged', False) and _token_map_context(source_token) == map_context:
                    target['source_token_id'] = source_token.id
            return target, None
        if target_token_id:
            token = (session.tokens or {}).get(target_token_id)
            if token and not getattr(token, 'hidden', False):
                cx = float(getattr(token, 'x', 0) or 0) + float(getattr(token, 'width', 0) or 0) / 2.0
                cy = float(getattr(token, 'y', 0) or 0) + float(getattr(token, 'height', 0) or 0) / 2.0
                return {'mode': 'point', 'x': cx, 'y': cy, 'map_context': _token_map_context(token), 'source_token_id': token.id}, None
        return None, 'Choose a point on the map.'
    if not target_token_id:
        return None, 'Choose a target token.'
    token = (session.tokens or {}).get(target_token_id)
    if not token or getattr(token, 'hidden', False):
        return None, 'Choose a visible target token.'
    return {'mode': 'token', 'token_id': token.id, 'map_context': _token_map_context(token)}, None


def _resolve_target_token(session: Session, target):
    if not isinstance(target, dict):
        return None
    token_id = str(target.get('token_id') or '').strip()
    token = (session.tokens or {}).get(token_id)
    if not token or getattr(token, 'hidden', False):
        return None
    return token


def _get_char_book_for_token(session: Session, token):
    # Lazy import to avoid circular dependency: viewer_powers -> content -> common
    from server.handlers.content import _get_char_profiles_for_user
    owner_id = str(getattr(token, 'owner_id', '') or '').strip()
    if not owner_id:
        return {}
    user = (session.users or {}).get(owner_id)
    if not user:
        return {}
    profiles, _, mine = _get_char_profiles_for_user(session, user)
    if not mine:
        return {}
    profile = sorted(mine, key=lambda e: float((e or {}).get('updated_at', 0) or 0), reverse=True)[0]
    return dict((profile or {}).get('charBook') or {})


def _token_save_bonus(session: Session, token, save_type: str) -> int:
    save_type = str(save_type or '').strip().lower()
    if not save_type:
        return 0
    raw_bonus = getattr(token, 'save_bonuses', None) or {}
    if isinstance(raw_bonus, dict):
        for key in (save_type, save_type.upper(), save_type.capitalize()):
            if key in raw_bonus:
                try:
                    return int(raw_bonus.get(key) or 0)
                except Exception:
                    break
    book = _get_char_book_for_token(session, token)
    saves = dict(book.get('savingThrows') or {})
    lookup = {
        'str': 'Strength', 'dex': 'Dexterity', 'con': 'Constitution',
        'int': 'Intelligence', 'wis': 'Wisdom', 'cha': 'Charisma',
    }
    raw = saves.get(lookup.get(save_type, ''))
    if raw is not None and str(raw).strip() != '':
        m = re.search(r'([+\-]?\d+)', str(raw))
        if m:
            return int(m.group(1))
    if save_type == 'dex':
        try:
            return int(getattr(token, 'initiative_mod', 0) or 0)
        except Exception:
            return 0
    abilities = dict(book.get('abilityScores') or {})
    ab_lookup = {'str': 'STR', 'dex': 'DEX', 'con': 'CON', 'int': 'INT', 'wis': 'WIS', 'cha': 'CHA'}
    raw_score = abilities.get(ab_lookup.get(save_type, ''))
    try:
        score = int(raw_score)
        return (score - 10) // 2
    except Exception:
        return 0


def _resolve_save(save_dc: int, save_bonus: int) -> tuple[int, bool]:
    import random
    roll = random.randint(1, 20)
    total = roll + int(save_bonus or 0)
    return total, total >= int(save_dc or 0)


def _distance_point_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    ab_len_sq = (abx * abx) + (aby * aby)
    if ab_len_sq <= 0.0001:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * abx + (py - ay) * aby) / ab_len_sq
    t = max(0.0, min(1.0, t))
    nx = ax + (abx * t)
    ny = ay + (aby * t)
    return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5


def _area_origin_for_target(session: Session, target: dict) -> tuple[float, float] | None:
    source_token_id = str((target or {}).get('source_token_id') or '').strip()
    if source_token_id:
        token = (session.tokens or {}).get(source_token_id)
        if token and not getattr(token, 'hidden', False):
            return _token_center(token)
    return None


def _target_token_in_area(session: Session, power: dict, target: dict, cand) -> bool:
    shape = str(power.get('area_shape') or 'burst').strip().lower()
    cx, cy = _token_center(cand)
    tx = float((target or {}).get('x', 0) or 0)
    ty = float((target or {}).get('y', 0) or 0)
    if shape == 'burst':
        radius_px = (float(power.get('radius_ft', 15)) / FT_PER_GRID) * PX_PER_GRID
        return (((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5) <= radius_px
    if shape == 'aura':
        radius_px = (float(power.get('radius_ft', 15)) / FT_PER_GRID) * PX_PER_GRID
        return (((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5) <= radius_px
    origin = _area_origin_for_target(session, target)
    if origin is None:
        origin = (tx, ty)
    ox, oy = origin
    dx = tx - ox
    dy = ty - oy
    length_px = max(1.0, (float(power.get('radius_ft', 15)) / FT_PER_GRID) * PX_PER_GRID)
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= 0.0001:
        return False
    ux = dx / dist
    uy = dy / dist
    relx = cx - ox
    rely = cy - oy
    forward = relx * ux + rely * uy
    if forward < 0 or forward > length_px:
        return False
    if shape == 'line':
        width_px = max(PX_PER_GRID * 0.5, (float(power.get('line_width_ft', 5)) / FT_PER_GRID) * PX_PER_GRID)
        return _distance_point_to_segment(cx, cy, ox, oy, ox + ux * length_px, oy + uy * length_px) <= (width_px / 2.0)
    if shape == 'cone':
        half_angle = max(0.1, float(power.get('cone_angle_deg', 60) or 60) / 2.0)
        cand_dist = ((relx * relx) + (rely * rely)) ** 0.5
        if cand_dist <= 0.0001 or cand_dist > length_px:
            return False
        cosang = max(-1.0, min(1.0, forward / cand_dist))
        import math
        ang = math.degrees(math.acos(cosang))
        return ang <= half_angle
    return False


def _viewer_power_shape_label(power: dict) -> str:
    shape = str(power.get('area_shape') or 'burst').strip().lower()
    size_ft = int(power.get('radius_ft', 15) or 15)
    if shape == 'cone':
        return f"{size_ft} ft cone"
    if shape == 'line':
        width_ft = int(power.get('line_width_ft', 5) or 5)
        return f"{size_ft} ft line ({width_ft} ft wide)"
    if shape == 'aura':
        return f"{size_ft} ft aura"
    return f"{size_ft} ft burst"


def _ordered_knockback_dirs(token_cx: float, token_cy: float, origin_x: float | None, origin_y: float | None) -> list[tuple[int, int]]:
    """Prefer directions that move away from the origin point, then fall back to cardinal order."""
    dirs = list(_KNOCKBACK_DIRS)
    if origin_x is None or origin_y is None:
        random.shuffle(dirs)
        return dirs
    away_x = token_cx - float(origin_x)
    away_y = token_cy - float(origin_y)
    if abs(away_x) <= 0.0001 and abs(away_y) <= 0.0001:
        random.shuffle(dirs)
        return dirs
    return sorted(dirs, key=lambda d: ((d[0] * away_x) + (d[1] * away_y), 1 if d[0] else 0), reverse=True)


async def _resolve_viewer_power(session: Session, actor_name: str, power_id: str, target: dict):
    power = _viewer_power_defs(session).get(power_id)
    if not power:
        return None, 'That viewer power is unavailable.'
    total, rolls = _roll_simple(power['dice'][0], power['dice'][1], power.get('amount', 0))
    affected = []
    combat_dirty = False
    if power['kind'] == 'single_damage':
        token = _resolve_target_token(session, target)
        if not token:
            return None, 'Choose a visible target token.'
        previous_hp = getattr(token, 'hp', None)
        _apply_damage(token, total)
        combat_dirty = _sync_combatant_token_state(session, token, previous_hp=previous_hp) or combat_dirty
        affected = [token]
        tcx, tcy = _token_center(token)
        fx_kind = 'lightning_strike' if power_id == 'arcane_zap' else 'projectile'
        await _broadcast_viewer_fx(session, fx_kind, {'x': tcx, 'y': tcy, 'x1': tcx - 280, 'y1': tcy - 180, 'x2': tcx, 'y2': tcy, 'token_id': token.id, 'label': f"-{total}", 'color': '#ff8a65'})
        msg = f"{actor_name} used {power['name']} on {token.name} for {total} damage ({'+'.join(map(str, rolls))})."
    elif power['kind'] == 'single_heal':
        token = _resolve_target_token(session, target)
        if not token:
            return None, 'Choose a visible target token.'
        previous_hp = getattr(token, 'hp', None)
        _apply_heal(token, total)
        combat_dirty = _sync_combatant_token_state(session, token, previous_hp=previous_hp) or combat_dirty
        affected = [token]
        tcx, tcy = _token_center(token)
        await _broadcast_viewer_fx(session, 'healing_spark', {'x': tcx, 'y': tcy, 'token_id': token.id, 'label': f"+{total}", 'amount': total})
        msg = f"{actor_name} used {power['name']} on {token.name} for {total} healing ({'+'.join(map(str, rolls))})."
    elif power['kind'] in {'area_damage', 'area_status'}:
        map_context = str((target or {}).get('map_context') or getattr(session, 'dm_map_context', 'world') or 'world')
        shape = str(power.get('area_shape') or 'burst').strip().lower()
        if shape == 'aura':
            token = _resolve_target_token(session, target)
            if not token:
                return None, 'Choose a visible target token.'
            cx, cy = _token_center(token)
            target = {**dict(target or {}), 'x': cx, 'y': cy, 'map_context': _token_map_context(token), 'source_token_id': token.id}
            map_context = _token_map_context(token)
        else:
            try:
                cx = float((target or {}).get('x'))
                cy = float((target or {}).get('y'))
            except Exception:
                return None, 'Choose a point on the map.'
        size_px = (float(power.get('radius_ft', 15)) / FT_PER_GRID) * PX_PER_GRID
        save_dc = int(power.get('save_dc', 0) or 0)
        save_type = str(power.get('save') or '').strip().lower()
        origin = _area_origin_for_target(session, target)
        source_x = (origin[0] if origin else cx) - max(size_px * 1.2, 140.0)
        source_y = (origin[1] if origin else cy) - max(size_px * 1.4, 180.0)
        await _broadcast_viewer_fx(session, 'projectile', {'x1': source_x, 'y1': source_y, 'x2': cx, 'y2': cy, 'label': power['name'], 'color': '#ff9a5c'})
        hit_summaries = []
        for cand in (session.tokens or {}).values():
            if getattr(cand, 'hidden', False):
                continue
            if _prune_token_condition_timers(cand):
                await _broadcast_token_condition_state(session, cand)
            if _token_map_context(cand) != map_context:
                continue
            if not _target_token_in_area(session, power, target, cand):
                continue
            saved = False
            save_total = None
            if save_type:
                save_bonus = _token_save_bonus(session, cand, save_type)
                save_total, saved = _resolve_save(save_dc, save_bonus)
            if power['kind'] == 'area_damage':
                applied = total
                if saved and power.get('save_half'):
                    applied = total // 2
                previous_hp = getattr(cand, 'hp', None)
                _apply_damage(cand, applied)
                combat_dirty = _sync_combatant_token_state(session, cand, previous_hp=previous_hp) or combat_dirty
                tcx, tcy = _token_center(cand)
                await _broadcast_viewer_fx(session, 'damage_number', {'x': tcx, 'y': tcy, 'token_id': cand.id, 'label': f"-{applied}", 'color': '#ff8a65'})
                hit_summaries.append(f"{cand.name} ({'save ' + str(save_total) + ' → ' if save_total is not None else ''}{applied} dmg{' half' if saved and power.get('save_half') else ''})")
            else:
                cond = _sanitize_condition_id(power.get('condition'))
                if not cond:
                    continue
                if not (saved and power.get('save_negates')):
                    _set_token_condition(cand, cond, int(power.get('duration_sec', 0) or 0))
                hit_summaries.append(f"{cand.name} ({'save ' + str(save_total) + ' → ' if save_total is not None else ''}{'no effect' if saved and power.get('save_negates') else cond})")
                await _broadcast_token_condition_state(session, cand)
            affected.append(cand)
        await _broadcast_viewer_fx(session, 'area_shape', {'x': cx, 'y': cy, 'radius': size_px, 'label': power['name'], 'area_shape': shape, 'line_width_px': (float(power.get('line_width_ft', 5)) / FT_PER_GRID) * PX_PER_GRID, 'cone_angle_deg': float(power.get('cone_angle_deg', 60) or 60), 'origin_x': origin[0] if origin else cx, 'origin_y': origin[1] if origin else cy})
        names = ', '.join(hit_summaries[:4]) + ('…' if len(hit_summaries) > 4 else '')
        if power['kind'] == 'area_damage':
            save_text = f" {save_type.upper()} save DC {save_dc} for half" if save_type and save_dc else ''
            msg = f"{actor_name} cast {power['name']} for {total} damage in a {_viewer_power_shape_label(power)} ({'+'.join(map(str, rolls))}){save_text}, hitting {names or 'no one'}."
        else:
            cond = _sanitize_condition_id(power.get('condition')) or 'status'
            duration_text = f" for {int(power.get('duration_sec', 0) or 0)}s" if int(power.get('duration_sec', 0) or 0) > 0 else ''
            save_text = f" {save_type.upper()} save DC {save_dc} negates" if save_type and save_dc else ''
            msg = f"{actor_name} unleashed {power['name']} in a {_viewer_power_shape_label(power)}, applying {cond}{duration_text}{save_text} to {names or 'no one'}."
    elif power['kind'] == 'single_status':
        token = _resolve_target_token(session, target)
        if not token:
            return None, 'Choose a visible target token.'
        _prune_token_condition_timers(token)
        cond = _sanitize_condition_id(power.get('condition'))
        if not cond:
            return None, 'This viewer power has no condition set.'
        save_dc = int(power.get('save_dc', 0) or 0)
        save_type = str(power.get('save') or '').strip().lower()
        save_total = None
        saved = False
        if save_type:
            save_bonus = _token_save_bonus(session, token, save_type)
            save_total, saved = _resolve_save(save_dc, save_bonus)
        duration_text = f" for {int(power.get('duration_sec', 0) or 0)}s" if int(power.get('duration_sec', 0) or 0) > 0 else ''
        save_text = f" {save_type.upper()} save {save_total} negated it" if save_total is not None and saved and power.get('save_negates') else ''
        if not (saved and power.get('save_negates')):
            _set_token_condition(token, cond, int(power.get('duration_sec', 0) or 0))
        if power_id == 'trip_hex' and not (saved and power.get('save_negates')):
            bonus_dmg, bonus_rolls = _roll_simple(1, 6, 0)
            previous_hp = getattr(token, 'hp', None)
            _apply_damage(token, bonus_dmg)
            combat_dirty = _sync_combatant_token_state(session, token, previous_hp=previous_hp) or combat_dirty
            tcx, tcy = _token_center(token)
            await _broadcast_viewer_fx(session, 'damage_number', {'x': tcx, 'y': tcy, 'token_id': token.id, 'label': f"-{bonus_dmg}", 'color': '#ff8a65'})
            msg = f"{actor_name} used {power['name']} on {token.name}, applying {cond}{duration_text} and dealing {bonus_dmg} bonus damage ({'+'.join(map(str, bonus_rolls))}){save_text}."
        else:
            msg = f"{actor_name} used {power['name']} on {token.name}, applying {cond}{duration_text}{save_text}."
        affected = [token]
        tcx, tcy = _token_center(token)
        await _broadcast_viewer_fx(session, 'projectile', {'x': tcx, 'y': tcy, 'x1': tcx - 280, 'y1': tcy - 280, 'x2': tcx, 'y2': tcy, 'token_id': token.id, 'label': power['name'], 'color': '#c084fc'})
        await _broadcast_token_condition_state(session, token)
    elif power['kind'] == 'knockback':
        # Support both point-targeting (find nearest token) and token-targeting (use token_id)
        knock_origin_x = None
        knock_origin_y = None
        source_token_id = str((target or {}).get('source_token_id') or '').strip()
        if source_token_id:
            source_token = (session.tokens or {}).get(source_token_id)
            if source_token and not getattr(source_token, 'hidden', False):
                knock_origin_x, knock_origin_y = _token_center(source_token)
        token = _resolve_target_token(session, target)
        if not token:
            # Point-targeting: find nearest non-hidden token to the clicked point
            try:
                tx = float((target or {}).get('x', 0) or 0)
                ty = float((target or {}).get('y', 0) or 0)
                knock_origin_x = tx
                knock_origin_y = ty
            except Exception:
                return None, 'Choose a point on the map.'
            map_context = str((target or {}).get('map_context') or getattr(session, 'dm_map_context', 'world') or 'world')
            best_dist = float('inf')
            for cand in (session.tokens or {}).values():
                if getattr(cand, 'staged', False):
                    continue
                if getattr(cand, 'hidden', False):
                    continue
                if _token_map_context(cand) != map_context:
                    continue
                cx, cy = _token_center(cand)
                dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    token = cand
        if not token:
            return None, 'No visible token found near that point.'
        push = float(PX_PER_GRID)
        old_x = float(getattr(token, 'x', 0) or 0)
        old_y = float(getattr(token, 'y', 0) or 0)
        cx, cy = _token_center(token)
        map_context = _token_map_context(token)
        new_x, new_y = old_x, old_y
        dirs = _ordered_knockback_dirs(cx, cy, knock_origin_x, knock_origin_y)
        for ux, uy in dirs:
            cand_x = old_x + (ux * push)
            cand_y = old_y + (uy * push)
            try:
                old_cx, old_cy = cx, cy
                new_cx = old_cx + (ux * push)
                new_cy = old_cy + (uy * push)
                blocker = find_movement_blocker(session, map_context, old_cx, old_cy, new_cx, new_cy)
                if blocker:
                    continue
            except Exception:
                pass
            new_x, new_y = cand_x, cand_y
            break
        old_cx, old_cy = _token_center(token)
        token.x = new_x
        token.y = new_y
        tcx, tcy = _token_center(token)
        await _broadcast_viewer_fx(session, 'knockback', {'x': tcx, 'y': tcy, 'x1': old_cx, 'y1': old_cy, 'x2': tcx, 'y2': tcy, 'token_id': token.id, 'label': power['name']})
        affected = [token]
        msg = f"{actor_name} used {power['name']}, blasting {token.name} back."
    elif power['kind'] == 'grant_item':
        token = _resolve_target_token(session, target)
        if not token:
            return None, 'Choose a visible target token.'
        owner_id = str(getattr(token, 'owner_id', '') or '').strip()
        if not owner_id:
            return None, 'That token does not belong to a player.'
        target_user = (session.users or {}).get(owner_id)
        if not target_user or getattr(target_user, 'role', '') != 'player':
            return None, "That token's owner is not a connected player."
        item_payload = dict(power.get('item_payload') or {})
        item_name = str(item_payload.get('name') or 'Potion of Minor Healing').strip()
        if not item_name:
            return None, 'No item configured for this power.'
        raw_entry = {
            'name': item_name,
            'notes': str(item_payload.get('notes') or '').strip(),
        }
        qty = max(1, int(item_payload.get('qty', 1) or 1))
        from server.handlers.inventory import _add_item_to_player_inventory, _broadcast_inventory_state
        _add_item_to_player_inventory(session, target_user, raw_entry, qty, source_name=f'Viewer: {actor_name}')
        await _broadcast_inventory_state(session)
        tcx, tcy = _token_center(token)
        await _broadcast_viewer_fx(session, 'item_gift', {'x': tcx, 'y': tcy, 'token_id': token.id, 'label': item_name})
        affected = [token]
        msg = f"{actor_name} gave {token.name} a {item_name} (×{qty})."
    else:
        return None, 'Unsupported viewer power.'
    log = session.add_log(msg, 'system', actor_name)
    for t in affected:
        await _broadcast_token_visibility(session, t, 'token_updated')
    if combat_dirty:
        await _broadcast_combat(session)
    await manager.broadcast(session.id, {'type': 'chat_message', 'payload': {'log': log, 'role': 'viewer', 'user_name': actor_name}})
    await save_campaign_async(session)
    return affected, msg


async def _broadcast_viewer_fx(session: Session, effect_type: str, payload: dict):
    await manager.broadcast(session.id, {'type': 'viewer_fx', 'payload': {'effect': effect_type, **payload}})


def _viewer_power_fx_payload(power_def: dict, power_id: str, power_name: str, viewer_name: str, target: dict | None, result: list | tuple | None, msg: str, approval_status: str) -> dict:
    kind = str((power_def or {}).get('kind') or '')
    targets = []
    if isinstance(result, (list, tuple)):
        for tok in result:
            try:
                targets.append({'token_id': str(getattr(tok, 'id', '') or ''), 'name': str(getattr(tok, 'name', '') or 'Target')[:80]})
            except Exception:
                pass
    payload = {
        'power_id': power_id,
        'power_name': power_name,
        'viewer_name': viewer_name,
        'kind': kind,
        'fx_color': _fx_color_for_kind(kind),
        'approval_status': approval_status,
        'targets': targets,
        'target_count': len(targets),
        'recap_text': str(msg or '').strip()[:500],
    }
    tp = _extract_target_point(target or {}, result)
    if tp:
        payload['target_point'] = tp
    radius_ft = (power_def or {}).get('radius_ft')
    if radius_ft is not None:
        payload['radius_ft'] = float(radius_ft)
    condition = str((power_def or {}).get('condition') or '').strip()
    if condition:
        payload['condition'] = condition
    if kind == 'grant_item':
        item = dict((power_def or {}).get('item_payload') or {})
        payload['item_name'] = str(item.get('name') or 'Gift')[:120]
    return payload


def _extract_target_point(target: dict | None, result: list | tuple | None) -> dict | None:
    """Extract {x, y} from target descriptor or first affected token."""
    t = target or {}
    try:
        x = float(t.get('x'))
        y = float(t.get('y'))
        return {'x': x, 'y': y}
    except Exception:
        pass
    if isinstance(result, (list, tuple)) and result:
        tok = result[0]
        try:
            cx = float(getattr(tok, 'x', 0) or 0) + float(getattr(tok, 'width', 0) or 0) / 2.0
            cy = float(getattr(tok, 'y', 0) or 0) + float(getattr(tok, 'height', 0) or 0) / 2.0
            return {'x': cx, 'y': cy}
        except Exception:
            pass
    return None


async def handle_viewer_power_create(payload: dict, session: Session, user: User):
    if _role(user) != 'dm':
        return
    power_id = str(payload.get('power_id') or '').strip().lower()[:64]
    if not re.fullmatch(r'[a-z0-9_\-]{3,64}', power_id or ''):
        return
    if power_id in VIEWER_BASE_POWER_DEFS:
        return
    catalog = dict(getattr(session, 'viewer_power_catalog', {}) or {})
    existing = catalog.get(power_id) if isinstance(catalog.get(power_id), dict) else {}
    raw = {
        'name': str(payload.get('name') or existing.get('name') or power_id),
        'kind': str(payload.get('kind') or existing.get('kind') or 'single_damage'),
        'dice_num': payload.get('dice_num', existing.get('dice_num', (existing.get('dice') or [1, 4])[0] if isinstance(existing.get('dice'), (list, tuple)) else 1)),
        'dice_sides': payload.get('dice_sides', existing.get('dice_sides', (existing.get('dice') or [1, 4])[1] if isinstance(existing.get('dice'), (list, tuple)) and len(existing.get('dice') or []) > 1 else 4)),
        'amount': payload.get('amount', existing.get('amount', 0)),
        'radius_ft': payload.get('radius_ft', existing.get('radius_ft', 15)),
        'area_shape': payload.get('area_shape', existing.get('area_shape', existing.get('shape', 'burst'))),
        'line_width_ft': payload.get('line_width_ft', existing.get('line_width_ft', existing.get('width_ft', 5))),
        'cone_angle_deg': payload.get('cone_angle_deg', existing.get('cone_angle_deg', 60)),
        'save': payload.get('save', existing.get('save', '')),
        'save_dc': payload.get('save_dc', existing.get('save_dc', 0)),
        'save_half': payload.get('save_half', existing.get('save_half', True)),
        'cooldown_sec': payload.get('cooldown_sec', existing.get('cooldown_sec', 0)),
        'approval_default': payload.get('approval_default', existing.get('approval_default', False)),
        'description': payload.get('description', existing.get('description', 'Custom viewer power')),
        'condition': payload.get('condition', existing.get('condition', '')),
        'duration_sec': payload.get('duration_sec', existing.get('duration_sec', existing.get('duration', 0))),
        'save_negates': payload.get('save_negates', existing.get('save_negates', True)),
    }
    norm = _normalize_viewer_power_def(power_id, raw)
    if not norm:
        return
    catalog[power_id] = norm
    session.viewer_power_catalog = catalog
    await _broadcast_viewer_power_catalog(session)
    await _broadcast_viewer_profiles(session)
    await save_campaign_async(session)


async def handle_viewer_power_grant(payload: dict, session: Session, user: User):
    if _role(user) != 'dm':
        return
    viewer_user_id = str(payload.get('viewer_user_id') or '').strip()
    power_id = str(payload.get('power_id') or '').strip()
    charges = 1
    defs = _viewer_power_defs(session)
    requires_approval = bool(payload.get('requires_approval', defs.get(power_id, {}).get('approval_default', False)))
    viewer = (session.users or {}).get(viewer_user_id)
    if not viewer or _role(viewer) != 'viewer' or power_id not in defs:
        return
    profiles, profile, _ = _get_or_create_viewer_profile(session, viewer)
    powers = dict(profile.get('powers') or {})
    powers[power_id] = {'power_id': power_id, 'charges': charges, 'enabled': True, 'requires_approval': requires_approval, 'cooldown_sec': max(0, min(86400, int(payload.get('cooldown_sec', defs.get(power_id, {}).get('cooldown_sec', 0)) or 0))), 'cooldown_until': 0.0}
    profile['powers'] = powers
    profiles[_viewer_key_for_user(viewer)] = profile
    session.viewer_profiles = profiles
    await _broadcast_viewer_profiles(session)
    await save_campaign_async(session)


async def handle_viewer_power_grant_preset(payload: dict, session: Session, user: User):
    if _role(user) != 'dm':
        return
    viewer_user_id = str(payload.get('viewer_user_id') or '').strip()
    preset_id = str(payload.get('preset_id') or '').strip()
    viewer = (session.users or {}).get(viewer_user_id)
    preset = VIEWER_POWER_PRESETS.get(preset_id)
    if not viewer or _role(viewer) != 'viewer' or not preset:
        return
    defs = _viewer_power_defs(session)
    profiles, profile, _ = _get_or_create_viewer_profile(session, viewer)
    powers = dict(profile.get('powers') or {})
    for grant in list(preset.get('grants') or []):
        power_id = str((grant or {}).get('power_id') or '').strip()
        defs = _viewer_power_defs(session)
        if power_id not in defs:
            continue
        powers[power_id] = {
            'power_id': power_id,
            'charges': 1,
            'enabled': True,
            'requires_approval': bool((grant or {}).get('requires_approval', defs.get(power_id, {}).get('approval_default', False))),
            'cooldown_sec': max(0, min(86400, int((grant or {}).get('cooldown_sec', defs.get(power_id, {}).get('cooldown_sec', 0)) or 0))),
            'cooldown_until': 0.0,
        }
    profile['powers'] = powers
    profiles[_viewer_key_for_user(viewer)] = profile
    session.viewer_profiles = profiles
    await _broadcast_viewer_profiles(session)
    await save_campaign_async(session)


async def handle_viewer_power_revoke(payload: dict, session: Session, user: User):
    if _role(user) != 'dm':
        return
    viewer_user_id = str(payload.get('viewer_user_id') or '').strip()
    power_id = str(payload.get('power_id') or '').strip()
    viewer = (session.users or {}).get(viewer_user_id)
    if not viewer or _role(viewer) != 'viewer':
        return
    profiles, profile, _ = _get_or_create_viewer_profile(session, viewer)
    powers = dict(profile.get('powers') or {})
    if power_id in powers:
        powers.pop(power_id, None)
        profile['powers'] = powers
        profiles[_viewer_key_for_user(viewer)] = profile
        session.viewer_profiles = profiles
        await _broadcast_viewer_profiles(session)
        await save_campaign_async(session)


async def handle_viewer_power_use(payload: dict, session: Session, user: User):
    if _role(user) != 'viewer':
        return
    power_id = str(payload.get('power_id') or '').strip()
    defs = _viewer_power_defs(session)
    if power_id not in defs:
        return
    profiles, profile, viewer_key = _get_or_create_viewer_profile(session, user)
    powers = dict(profile.get('powers') or {})
    power_state = dict(powers.get(power_id) or {})
    if not power_state or not power_state.get('enabled', True) or int(power_state.get('charges', 0) or 0) <= 0:
        await manager.send_to(session.id, user.id, {'type': 'error', 'payload': {'message': 'That viewer power is unavailable.'}})
        return
    target, err = _build_target_descriptor(session, defs[power_id], payload)
    if err:
        await manager.send_to(session.id, user.id, {'type': 'error', 'payload': {'message': err}})
        return
    power_def = defs.get(power_id) or {}
    now = time.time()
    cooldown_until = float(power_state.get('cooldown_until', 0.0) or 0.0)
    if cooldown_until > now:
        secs = int(max(1, round(cooldown_until - now)))
        await manager.send_to(session.id, user.id, {'type': 'viewer_power_status', 'payload': {'kind': 'cooldown', 'message': f"{power_def.get('name', power_id)} is on cooldown for {secs}s."}})
        return
    if bool(power_state.get('requires_approval', False)):
        if _viewer_has_pending_power_request(session, viewer_key, power_id):
            await manager.send_to(session.id, user.id, {'type': 'viewer_power_status', 'payload': {'kind': 'queued', 'message': f"{power_def.get('name', power_id)} is already waiting for DM approval."}})
            return
        pending = _get_pending_viewer_actions(session)
        pending_id = _next_pending_viewer_action_id(session)
        pending[pending_id] = {'id': pending_id, 'viewer_key': viewer_key, 'viewer_user_id': user.id, 'viewer_name': str(user.name or 'Viewer')[:40], 'power_id': power_id, 'power_name': power_def.get('name', power_id), 'target': target, 'created_at': time.time()}
        session.viewer_pending_actions = pending
        await _broadcast_viewer_pending(session)
        await manager.send_to(session.id, user.id, {'type': 'viewer_power_status', 'payload': {'kind': 'queued', 'message': f"{power_def.get('name', power_id)} is waiting for DM approval."}})
        return
    _consume_viewer_power(session, viewer_key, power_id)
    result, err = await _resolve_viewer_power(session, user.name, power_id, target)
    if result is None:
        await manager.send_to(session.id, user.id, {'type': 'error', 'payload': {'message': err}})
        await _broadcast_viewer_profiles(session)
        await save_campaign_async(session)
        return
    await _broadcast_viewer_profiles(session)
    await save_campaign_async(session)
    power_name = power_def.get('name', power_id)
    status_msg = f"{power_name} was used! It has been removed until the DM grants it again."
    await manager.send_to(session.id, user.id, {'type': 'viewer_power_status', 'payload': {'kind': 'used', 'message': status_msg}})
    # Broadcast visual FX announcement / recap to all clients.
    fx_payload = _viewer_power_fx_payload(
        power_def, power_id, power_name, str(user.name or 'Viewer')[:40], target, result, err or '', 'auto_approved'
    )
    await manager.broadcast(session.id, {'type': 'viewer_power_fx', 'payload': fx_payload})


async def handle_viewer_power_pending_decision(payload: dict, session: Session, user: User):
    if _role(user) != 'dm':
        return
    pending_id = str(payload.get('pending_id') or '').strip()
    approve = bool(payload.get('approve'))
    pending = _get_pending_viewer_actions(session)
    entry = dict(pending.get(pending_id) or {})
    if not entry:
        return
    viewer_user = (session.users or {}).get(str(entry.get('viewer_user_id') or '').strip())
    viewer_key = str(entry.get('viewer_key') or '').strip()
    profiles = _get_viewer_profiles(session)
    profile = dict(profiles.get(viewer_key) or {})
    powers = dict(profile.get('powers') or {})
    power_id = str(entry.get('power_id') or '').strip()
    power_state = dict(powers.get(power_id) or {})
    if not approve:
        # Rejection: remove pending request but keep the viewer's power charge.
        pending.pop(pending_id, None); session.viewer_pending_actions = pending
        await _broadcast_viewer_pending(session)
        # Broadcast profiles so viewer UI can reconcile any optimistic removal.
        await _broadcast_viewer_profiles(session)
        await save_campaign_async(session)
        if viewer_user: await manager.send_to(session.id, viewer_user.id, {'type': 'viewer_power_status', 'payload': {'kind': 'rejected', 'message': f"{entry.get('power_name') or 'That power'} was declined by the DM."}})
        return
    if not power_state or int(power_state.get('charges', 0) or 0) <= 0:
        pending.pop(pending_id, None); session.viewer_pending_actions = pending
        await _broadcast_viewer_pending(session)
        if viewer_user: await manager.send_to(session.id, viewer_user.id, {'type': 'error', 'payload': {'message': 'That viewer power no longer has any charges left.'}})
        return
    defs = _viewer_power_defs(session)
    power_def = defs.get(power_id) or {}
    _consume_viewer_power(session, viewer_key, power_id)
    result, err = await _resolve_viewer_power(session, str(entry.get('viewer_name') or 'Viewer'), power_id, entry.get('target') or {})
    pending.pop(pending_id, None); session.viewer_pending_actions = pending
    await _broadcast_viewer_pending(session)
    if result is None:
        if viewer_user: await manager.send_to(session.id, viewer_user.id, {'type': 'error', 'payload': {'message': err}})
        await _broadcast_viewer_profiles(session)
        await save_campaign_async(session)
        return
    await _broadcast_viewer_profiles(session)
    await save_campaign_async(session)
    power_name = entry.get('power_name') or power_id
    approved_msg = f"{power_name} was approved and used! It has been removed until the DM grants it again."
    if viewer_user: await manager.send_to(session.id, viewer_user.id, {'type': 'viewer_power_status', 'payload': {'kind': 'approved', 'message': approved_msg}})
    # Broadcast visual FX announcement / recap to all clients.
    viewer_name = str(entry.get('viewer_name') or 'Viewer')[:40]
    fx_payload = _viewer_power_fx_payload(
        power_def, power_id, power_name, viewer_name, entry.get('target') or {}, result, err or '', 'dm_approved'
    )
    await manager.broadcast(session.id, {'type': 'viewer_power_fx', 'payload': fx_payload})


# ── Viewer cursor ghost markers ──────────────────────────────────────────────

# Per-session rate-limit tracking: {session_id: {user_id: last_ts}}
_viewer_cursor_rate: dict = {}

_VIEWER_CURSOR_MIN_INTERVAL = 0.1  # 10 updates/sec max


async def handle_viewer_cursor_update(payload: dict, session: Session, user: User):
    """Viewer → server: broadcast cursor position to DM (and players if enabled)."""
    if _role(user) != 'viewer':
        return

    # Rate-limit to 10 updates/sec per viewer
    now = time.time()
    session_rates = _viewer_cursor_rate.setdefault(session.id, {})
    last = session_rates.get(user.id, 0.0)
    if now - last < _VIEWER_CURSOR_MIN_INTERVAL:
        return
    session_rates[user.id] = now

    x = float(payload.get('x') or 0)
    y = float(payload.get('y') or 0)
    map_context = str(payload.get('map_context') or 'world')[:64]

    sync_payload = {
        'type': 'viewer_cursor_sync',
        'payload': {
            'user_id': user.id,
            'name': user.name,
            'x': x,
            'y': y,
            'map_context': map_context,
        },
    }

    # Always send to DM
    for uid, u in session.users.items():
        if _role(u) == 'dm':
            await manager.send_to(session.id, uid, sync_payload)

    # Optionally broadcast to players too
    if getattr(session, 'show_viewer_presence', False):
        for uid, u in session.users.items():
            if _role(u) == 'player':
                await manager.send_to(session.id, uid, sync_payload)


async def handle_viewer_presence_toggle(payload: dict, session: Session, user: User):
    """DM → server: toggle whether viewer ghost markers are visible to players."""
    if _role(user) != 'dm':
        return

    enabled = bool(payload.get('enabled', not getattr(session, 'show_viewer_presence', False)))
    session.show_viewer_presence = enabled
    await save_campaign_async(session)

    # Notify all connected users of the new setting
    sync_msg = {
        'type': 'viewer_presence_sync',
        'payload': {'show_viewer_presence': enabled},
    }
    await manager.broadcast(session.id, sync_msg)
