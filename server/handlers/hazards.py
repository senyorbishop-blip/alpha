"""
server/handlers/hazards.py — Hazard zone helpers and handlers.
"""
import secrets
from server.handlers.common import (
    Session, User, manager,
    save_campaign_async,
    PX_PER_GRID, FT_PER_GRID,
    _safe_int, _safe_float,
    _refresh_map_documents,
    _broadcast_hazard_state,
    _broadcast_token_event,
    _sync_combatant_token_state,
    _token_center,
)
from server.handlers.conditions import (
    _prune_token_condition_timers,
    _set_token_condition_with_duration,
)


def _normalize_hazard_zone_payload(raw: dict | None, *, existing: dict | None = None) -> dict | None:
    raw = dict(raw or {})
    existing = dict(existing or {})
    trigger = str(raw.get('trigger', existing.get('trigger', 'enter')) or 'enter').strip().lower()
    if trigger not in {'enter', 'start_turn', 'end_turn', 'end_round'}:
        trigger = 'enter'
    effect = str(raw.get('effect', existing.get('effect', 'damage')) or 'damage').strip().lower()
    if effect not in {'damage', 'condition'}:
        effect = 'damage'
    save_type = str(raw.get('save') if 'save' in raw else existing.get('save', '')).strip().lower()
    if save_type not in {'', 'str', 'dex', 'con', 'int', 'wis', 'cha'}:
        save_type = ''
    condition = str(raw.get('condition', existing.get('condition', '')) or '').strip().lower()[:40]
    if effect == 'condition' and not condition:
        return None
    zone = {
        'id': str(raw.get('id', existing.get('id', '')) or '').strip()[:48],
        'name': str(raw.get('name', existing.get('name', 'Hazard Zone')) or 'Hazard Zone').strip()[:60],
        'map_context': str(raw.get('map_context', existing.get('map_context', 'world')) or 'world')[:80],
        'x': _safe_float(raw.get('x', existing.get('x', 0.0)), 0.0),
        'y': _safe_float(raw.get('y', existing.get('y', 0.0)), 0.0),
        'radius_ft': _safe_int(raw.get('radius_ft', raw.get('radius', existing.get('radius_ft', 15))), existing.get('radius_ft', 15) or 15, minimum=5, maximum=300),
        'trigger': trigger,
        'effect': effect,
        'dice_num': _safe_int(raw.get('dice_num', raw.get('diceCount', existing.get('dice_num', 1))), existing.get('dice_num', 1) or 1, minimum=1, maximum=50),
        'dice_sides': _safe_int(raw.get('dice_sides', raw.get('diceSides', existing.get('dice_sides', 6))), existing.get('dice_sides', 6) or 6, minimum=2, maximum=100),
        'flat_bonus': _safe_int(raw.get('flat_bonus', raw.get('flatBonus', existing.get('flat_bonus', 0))), existing.get('flat_bonus', 0) or 0, minimum=-100, maximum=1000),
        'save': save_type,
        'save_dc': _safe_int(raw.get('save_dc', raw.get('saveDc', existing.get('save_dc', 0))), existing.get('save_dc', 0) or 0, minimum=0, maximum=40),
        'save_half': bool(raw.get('save_half', existing.get('save_half', True))),
        'duration_sec': _safe_int(raw.get('duration_sec', raw.get('duration', existing.get('duration_sec', 0))), existing.get('duration_sec', 0) or 0, minimum=0, maximum=86400),
        'hidden_from_players': bool(raw.get('hidden_from_players', raw.get('hide_from_players', existing.get('hidden_from_players', False)))),
        'color': str(raw.get('color', existing.get('color', '#e67e22')) or '#e67e22')[:20],
        'icon': str(raw.get('icon', existing.get('icon', '')) or '').strip()[:8],
        'once_per_round': bool(raw.get('once_per_round', raw.get('oncePerRound', existing.get('once_per_round', False)))),
        'round_hits': dict(raw.get('round_hits', existing.get('round_hits', {})) or {}),
    }
    if effect == 'condition':
        zone['condition'] = condition
    if not zone['once_per_round']:
        zone['round_hits'] = {}
    return zone


def _point_in_hazard_zone(token, zone: dict) -> bool:
    tx, ty = _token_center(token)
    zx = float(zone.get('x', 0.0) or 0.0)
    zy = float(zone.get('y', 0.0) or 0.0)
    radius_px = float(zone.get('radius_ft', 15) or 15) / FT_PER_GRID * PX_PER_GRID
    dx = tx - zx
    dy = ty - zy
    return (dx * dx + dy * dy) <= (radius_px * radius_px)


def _roll_zone_damage(zone: dict) -> tuple[int, list[int]]:
    import secrets as _secrets
    num = _safe_int(zone.get('dice_num'), 1, minimum=1, maximum=50)
    sides = _safe_int(zone.get('dice_sides'), 6, minimum=2, maximum=100)
    rolls = [_secrets.randbelow(sides) + 1 for _ in range(num)]
    total = sum(rolls) + _safe_int(zone.get('flat_bonus'), 0)
    return max(0, total), rolls


def _hazard_round_key(session: Session, *, round_number: int | None = None) -> str | None:
    combat = getattr(session, 'combat', {}) or {}
    if not combat.get('active'):
        return None
    if round_number is None:
        round_number = _safe_int(combat.get('round'), 1, minimum=1, maximum=999999)
    return str(max(1, int(round_number or 1)))


def _hazard_can_apply_this_round(session: Session, zone: dict, token, *, round_number: int | None = None) -> bool:
    if not bool(zone.get('once_per_round')):
        return True
    round_key = _hazard_round_key(session, round_number=round_number)
    if round_key is None:
        return True
    token_id = str(getattr(token, 'id', '') or '')
    if not token_id:
        return True
    round_hits = dict(zone.get('round_hits') or {})
    return str(round_hits.get(token_id) or '') != round_key


def _record_hazard_round_hit(session: Session, zone: dict, token, *, round_number: int | None = None) -> bool:
    if not bool(zone.get('once_per_round')):
        return False
    round_key = _hazard_round_key(session, round_number=round_number)
    token_id = str(getattr(token, 'id', '') or '')
    if round_key is None or not token_id:
        return False
    round_hits = dict(zone.get('round_hits') or {})
    if str(round_hits.get(token_id) or '') == round_key:
        return False
    round_hits[token_id] = round_key
    zone['round_hits'] = round_hits
    return True


async def _apply_hazard_zone_to_token(session: Session, zone: dict, token, *, reason: str = 'trigger', round_number: int | None = None) -> tuple[bool, str | None, bool]:
    # Lazy import to avoid circular dependency: hazards -> viewer_powers -> combat -> hazards
    from server.handlers.viewer_powers import _token_save_bonus

    if not zone or not token:
        return False, None, False
    if not _hazard_can_apply_this_round(session, zone, token, round_number=round_number):
        return False, None, False
    _prune_token_condition_timers(token)
    save_type = str(zone.get('save') or '').strip().lower()
    dc = _safe_int(zone.get('save_dc'), 0, minimum=0, maximum=40)
    save_bonus = _token_save_bonus(session, token, save_type) if save_type else 0
    save_roll = None
    saved = False
    if save_type and dc > 0:
        import secrets as _secrets
        save_roll = _secrets.randbelow(20) + 1 + save_bonus
        saved = save_roll >= dc
    changed = False
    state_changed = False
    msg = None
    token_name = str(getattr(token, 'name', 'Token') or 'Token')
    zone_name = str(zone.get('name') or 'hazard zone')
    if str(zone.get('effect') or 'damage') == 'condition':
        cond = str(zone.get('condition') or '').strip().lower()
        if not cond:
            return False, None, False
        if saved:
            msg = f"{token_name} resisted {zone_name} on {reason.replace('_', ' ')}."
        else:
            changed = _set_token_condition_with_duration(token, cond, _safe_int(zone.get('duration_sec'), 0, minimum=0, maximum=86400))
            dur = _safe_int(zone.get('duration_sec'), 0, minimum=0, maximum=86400)
            msg = f"{token_name} gained {cond} from {zone_name} on {reason.replace('_', ' ')}" + (f" for {dur}s." if dur > 0 else ".")
    else:
        total, rolls = _roll_zone_damage(zone)
        applied = total
        if saved:
            applied = total // 2 if bool(zone.get('save_half', True)) else 0
        if applied:
            previous_hp = getattr(token, 'hp', None)
            if previous_hp is None and getattr(token, 'max_hp', None) is not None:
                token.hp = int(getattr(token, 'max_hp', 0) or 0)
                previous_hp = token.hp
            if previous_hp is not None:
                token.hp = max(0, int(previous_hp or 0) - int(applied))
                changed = True
                _sync_combatant_token_state(session, token, previous_hp=previous_hp)
        roll_text = f" [{'+'.join(str(r) for r in rolls)}" + (f" + {int(zone.get('flat_bonus') or 0)}" if int(zone.get('flat_bonus') or 0) else '') + "]"
        msg = f"{token_name} took {applied} damage from {zone_name} on {reason.replace('_', ' ')}{roll_text}"
        if save_type and dc > 0:
            msg += f" ({save_type.upper()} save {'passed' if saved else 'failed'}" + (f" {save_roll}" if save_roll is not None else '') + f" vs DC {dc})."
        else:
            msg += "."
    if msg:
        state_changed = _record_hazard_round_hit(session, zone, token, round_number=round_number) or state_changed
    if changed:
        await _broadcast_token_event(manager, session, 'token_updated', {'token': token.to_dict()}, token)
    if msg:
        session.add_log(msg, 'system', 'Hazard')
        await manager.broadcast(session.id, {'type': 'chat_message', 'payload': {'log': session.log[-1], 'role': 'system'}})
    return changed, msg, state_changed


async def _process_hazard_triggers_for_token(session: Session, token, *, trigger: str, old_x: float | None = None, old_y: float | None = None, round_number: int | None = None):
    changed = False
    state_changed = False
    for zone in list((getattr(session, 'hazard_zones', None) or {}).values()):
        if not isinstance(zone, dict):
            continue
        if str(zone.get('trigger') or '') != trigger:
            continue
        if str(zone.get('map_context') or 'world') != str(getattr(token, 'map_context', 'world') or 'world'):
            continue
        inside_now = _point_in_hazard_zone(token, zone)
        if trigger == 'enter':
            if old_x is None or old_y is None:
                continue
            temp = type('OldPos', (), {'x': old_x, 'y': old_y, 'width': getattr(token, 'width', 0), 'height': getattr(token, 'height', 0)})()
            inside_before = _point_in_hazard_zone(temp, zone)
            if inside_before or not inside_now:
                continue
        else:
            if not inside_now:
                continue
        applied, _, zone_state_changed = await _apply_hazard_zone_to_token(session, zone, token, reason=trigger, round_number=round_number)
        changed = changed or applied
        state_changed = state_changed or zone_state_changed
    if changed or state_changed:
        await save_campaign_async(session)


async def _process_current_start_turn_hazards(session: Session):
    from server.handlers.combat import _get_current_combatant
    current = _get_current_combatant(session)
    token_id = str((current or {}).get('token_id') or '').strip()
    token = session.tokens.get(token_id) if token_id else None
    if token is None:
        return
    await _process_hazard_triggers_for_token(session, token, trigger='start_turn')


async def _process_current_end_turn_hazards(session: Session, *, round_number: int | None = None):
    from server.handlers.combat import _get_current_combatant
    current = _get_current_combatant(session)
    token_id = str((current or {}).get('token_id') or '').strip()
    token = session.tokens.get(token_id) if token_id else None
    if token is None:
        return
    await _process_hazard_triggers_for_token(session, token, trigger='end_turn', round_number=round_number)


async def _process_end_round_hazards(session: Session, *, round_number: int | None = None):
    combatants = list((getattr(session, 'combat', {}) or {}).get('combatants') or [])
    seen = set()
    for entry in combatants:
        token_id = str((entry or {}).get('token_id') or '').strip()
        if not token_id or token_id in seen:
            continue
        seen.add(token_id)
        token = session.tokens.get(token_id)
        if token is None:
            continue
        await _process_hazard_triggers_for_token(session, token, trigger='end_round', round_number=round_number)


async def handle_hazard_zone_create(payload: dict, session: Session, user: User):
    if user.role != 'dm':
        return
    zone = _normalize_hazard_zone_payload(payload)
    if not zone:
        await manager.send_to(session.id, user.id, {'type': 'error', 'payload': {'message': 'Invalid hazard zone.'}})
        return
    zone['id'] = zone.get('id') or secrets.token_hex(6)
    session.hazard_zones = dict(getattr(session, 'hazard_zones', {}) or {})
    session.hazard_zones[zone['id']] = zone
    _refresh_map_documents(session, str(zone.get('map_context') or 'world'))
    await save_campaign_async(session)
    await _broadcast_hazard_state(session)


async def handle_hazard_zone_update(payload: dict, session: Session, user: User):
    if user.role != 'dm':
        return
    payload = dict(payload or {})
    zone_id = str(payload.get('zone_id') or payload.get('id') or '').strip()
    zones = dict(getattr(session, 'hazard_zones', {}) or {})
    existing = dict(zones.get(zone_id) or {})
    if not zone_id or not existing:
        await manager.send_to(session.id, user.id, {'type': 'error', 'payload': {'message': 'Hazard zone not found.'}})
        return
    payload['id'] = zone_id
    zone = _normalize_hazard_zone_payload(payload, existing=existing)
    if not zone:
        await manager.send_to(session.id, user.id, {'type': 'error', 'payload': {'message': 'Invalid hazard zone update.'}})
        return
    zones[zone_id] = zone
    session.hazard_zones = zones
    _refresh_map_documents(session, str(zone.get('map_context') or 'world'))
    await save_campaign_async(session)
    await _broadcast_hazard_state(session)


async def handle_hazard_zone_delete(payload: dict, session: Session, user: User):
    if user.role != 'dm':
        return
    zone_id = str(payload.get('zone_id') or payload.get('id') or '').strip()
    if not zone_id:
        return
    zones = dict(getattr(session, 'hazard_zones', {}) or {})
    if zone_id in zones:
        existing = dict(zones.get(zone_id) or {})
        zones.pop(zone_id, None)
        session.hazard_zones = zones
        _refresh_map_documents(session, str(existing.get('map_context') or 'world'))
        await save_campaign_async(session)
        await _broadcast_hazard_state(session)


async def handle_hazard_zone_apply(payload: dict, session: Session, user: User):
    if user.role != 'dm':
        return
    zone_id = str(payload.get('zone_id') or payload.get('id') or '').strip()
    zone = dict((getattr(session, 'hazard_zones', {}) or {}).get(zone_id) or {})
    if not zone:
        return
    any_changed = False
    for token in list((session.tokens or {}).values()):
        if str(getattr(token, 'map_context', 'world') or 'world') != str(zone.get('map_context') or 'world'):
            continue
        if not _point_in_hazard_zone(token, zone):
            continue
        changed, _, _ = await _apply_hazard_zone_to_token(session, zone, token, reason='manual')
        any_changed = any_changed or changed
    if any_changed:
        await save_campaign_async(session)
