"""
server/handlers/conditions.py — Token condition management helpers.
"""
import time
from server.handlers.common import (
    Session, manager, _broadcast_token_event,
)


def _sanitize_condition_id(cond: str) -> str:
    cond = str(cond or '').strip().lower()[:50]
    return cond


def _set_token_condition(token, condition: str, duration_sec: int = 0) -> bool:
    cond = _sanitize_condition_id(condition)
    if not cond:
        return False
    if not isinstance(getattr(token, 'conditions', None), list):
        token.conditions = []
    if not isinstance(getattr(token, 'condition_timers', None), dict):
        token.condition_timers = {}
    changed = False
    if cond not in token.conditions:
        token.conditions.append(cond)
        changed = True
    expiry = 0.0
    if int(duration_sec or 0) > 0:
        expiry = time.time() + int(duration_sec)
        if float(token.condition_timers.get(cond, 0) or 0) != float(expiry):
            token.condition_timers[cond] = expiry
            changed = True
    else:
        if cond in token.condition_timers:
            token.condition_timers.pop(cond, None)
            changed = True
    return changed


def _set_token_condition_with_duration(token, condition: str, duration_sec: int = 0) -> bool:
    """Thin wrapper over _set_token_condition that accepts a duration argument."""
    return _set_token_condition(token, condition, duration_sec)


def _clear_token_condition(token, condition: str) -> bool:
    cond = _sanitize_condition_id(condition)
    changed = False
    if not isinstance(getattr(token, 'conditions', None), list):
        token.conditions = []
    if cond in token.conditions:
        token.conditions.remove(cond)
        changed = True
    if isinstance(getattr(token, 'condition_timers', None), dict) and cond in token.condition_timers:
        token.condition_timers.pop(cond, None)
        changed = True
    return changed


def _prune_token_condition_timers(token) -> bool:
    now = time.time()
    timers = getattr(token, 'condition_timers', None)
    if not isinstance(timers, dict) or not timers:
        token.condition_timers = {}
        return False
    changed = False
    for cond, expiry in list(timers.items()):
        try:
            expiry_val = float(expiry or 0)
        except Exception:
            expiry_val = 0
        if expiry_val <= now:
            timers.pop(cond, None)
            if isinstance(getattr(token, 'conditions', None), list) and cond in token.conditions:
                token.conditions.remove(cond)
            changed = True
    token.condition_timers = timers
    return changed


async def _broadcast_token_condition_state(session: Session, token):
    await _broadcast_token_event(manager, session, 'token_condition_changed', {
        'token_id': token.id,
        'conditions': list(getattr(token, 'conditions', []) or []),
        'condition_timers': dict(getattr(token, 'condition_timers', {}) or {}),
    }, token)


def _roll_simple(num: int, sides: int, bonus: int = 0) -> tuple[int, list[int]]:
    import random
    rolls = [random.randint(1, max(2, int(sides or 2))) for _ in range(max(1, int(num or 1)))]
    return sum(rolls) + int(bonus or 0), rolls
