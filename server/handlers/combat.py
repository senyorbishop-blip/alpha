"""
server/handlers/combat.py — Combat state management helpers and handlers.
"""
import time as _time
from server.session import normalize_profile_owner_key, assistant_dm_has_scope
from server.quest_progress import apply_objective_event, normalize_quest_payload_shape
from server.encumbrance import ENC_HEAVY

from server.handlers.common import (
    Session, User, manager,
    save_campaign_async,
    PX_PER_GRID, FT_PER_GRID,
    _safe_int,
    _broadcast_combat,
)


def _can_manage_combat(session: Session, user: User, *, full: bool = False) -> bool:
    if user.role == "dm":
        return True
    return assistant_dm_has_scope(session, user, "combat.manage_limited") and not full



def _owner_matches_user(owner_id, user: User) -> bool:
    owner = str(owner_id or "").strip()
    if not owner:
        return False
    if owner == str(user.id):
        return True
    owner_key = normalize_profile_owner_key(owner)
    if not owner_key:
        return False
    return owner_key == normalize_profile_owner_key(getattr(user, "name", ""))


def _has_encumbrance_attack_disadvantage(session: Session, attacker_owner_id: str) -> bool:
    """True when the attacking player is heavily encumbered."""
    owner_id = str(attacker_owner_id or "").strip()
    if not owner_id:
        return False
    cache = getattr(session, "_encumbrance_cache", {}) or {}
    entry = cache.get(owner_id)
    if not isinstance(entry, dict):
        return False
    return str(entry.get("state") or "").strip().lower() == ENC_HEAVY


def _combatant_token_ids(session: Session) -> set[str]:
    combat = getattr(session, "combat", None) or {}
    combatants = combat.get("combatants") or []
    ids = set()
    for combatant in combatants:
        token_id = str((combatant or {}).get("token_id") or "").strip()
        if token_id:
            ids.add(token_id)
    return ids


def _get_current_combatant(session: Session) -> dict | None:
    combat = getattr(session, "combat", None) or {}
    combatants = combat.get("combatants") or []
    if not combat.get("active") or not combatants:
        return None
    try:
        turn = int(combat.get("turn", 0) or 0)
    except Exception:
        turn = 0
    if turn < 0 or turn >= len(combatants):
        return None
    current = combatants[turn] or {}
    return current if isinstance(current, dict) else None


def _char_profile_speed(session: Session, owner_id: str) -> int:
    """Return the speed stored in the player's most-recent char profile, or 0."""
    try:
        user = (getattr(session, "users", {}) or {}).get(owner_id)
        if not user:
            return 0
        profiles_all = dict(getattr(session, "char_profiles", {}) or {})
        name_key = normalize_profile_owner_key(getattr(user, "name", ""))
        mine = list(profiles_all.get(name_key) or profiles_all.get(owner_id) or [])
        if not mine:
            return 0
        best = max(mine, key=lambda p: float(p.get("updated_at") or 0.0), default=None)
        if not best:
            return 0
        speed = int(best.get("speed") or 0)
        return max(0, speed)
    except Exception:
        return 0


def _token_speed_ft(session: Session, token, combatant: dict | None = None) -> int:
    def _safe_speed(value) -> int:
        try:
            return max(0, int(value))
        except Exception:
            return 0

    combatant_speed = None
    if isinstance(combatant, dict):
        combatant_speed = combatant.get("speed")
    token_speed = getattr(token, "speed", None) if token is not None else None

    combatant_speed_val = _safe_speed(combatant_speed)
    token_speed_val = _safe_speed(token_speed)

    # Combatants created before a character import/re-login can have stale 0 speed.
    # Prefer the live token speed if combatant speed is missing/zero and token speed is valid.
    base = combatant_speed_val
    if base <= 0 and token_speed_val > 0:
        base = token_speed_val
    # Apply encumbrance speed penalty for player-owned tokens
    owner_id = None
    if token is not None:
        owner_id = str(getattr(token, "owner_id", "") or "").strip()
    if not owner_id and isinstance(combatant, dict):
        owner_id = str((combatant or {}).get("owner_id") or "").strip()
    # Last fallback: read speed from the player's saved character profile
    if base <= 0 and owner_id:
        base = _char_profile_speed(session, owner_id)
    if owner_id:
        cache = getattr(session, "_encumbrance_cache", {}) or {}
        entry = cache.get(owner_id)
        if isinstance(entry, dict):
            penalty = int(entry.get("speed_penalty") or 0)
            if penalty <= -9999:
                return 0
            base = max(0, base + penalty)
    return base


def _movement_squares_from_delta(dx: float, dy: float) -> float:
    sx = abs(float(dx or 0.0)) / PX_PER_GRID
    sy = abs(float(dy or 0.0)) / PX_PER_GRID
    diag = min(sx, sy)
    straight = max(sx, sy) - diag
    return straight + (diag * 2.0 - 1.0 if diag > 0 else 0.0)


def _movement_ft_between_positions(x1: float | None, y1: float | None, x2: float | None, y2: float | None) -> float:
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return 0.0
    squares = _movement_squares_from_delta(float(x2) - float(x1), float(y2) - float(y1))
    return round(squares * FT_PER_GRID, 2)


def _ensure_combat_movement_state(session: Session, *, reset: bool = False) -> dict:
    combat = getattr(session, "combat", None) or {}
    if not isinstance(combat, dict):
        combat = {"active": False, "turn": 0, "combatants": []}
        session.combat = combat
    if not combat.get("active"):
        combat["movement"] = {}
        return combat["movement"]
    current = _get_current_combatant(session)
    token_id = str((current or {}).get("token_id") or "").strip()
    if not token_id:
        combat["movement"] = {}
        return combat["movement"]
    token = session.tokens.get(token_id)
    existing = combat.get("movement")
    if not isinstance(existing, dict):
        existing = {}
    if reset or existing.get("token_id") != token_id:
        existing = {
            "token_id": token_id,
            "turn": int(combat.get("turn", 0) or 0),
            "spent_ft": 0.0,
            "speed_ft": _token_speed_ft(session, token, current),
            "remaining_ft": _token_speed_ft(session, token, current),
            "bonus_ft": 0.0,
            "dash_used": False,
            "difficult_terrain": False,
            "disengaged": False,
            "cost_multiplier": 1.0,
            "last_x": float(getattr(token, "x", 0.0) or 0.0) if token is not None else None,
            "last_y": float(getattr(token, "y", 0.0) or 0.0) if token is not None else None,
        }
    else:
        speed_ft = _token_speed_ft(session, token, current)
        spent_ft = float(existing.get("spent_ft", 0.0) or 0.0)
        bonus_ft = float(existing.get("bonus_ft", 0.0) or 0.0)
        existing["turn"] = int(combat.get("turn", 0) or 0)
        existing["speed_ft"] = speed_ft
        existing["bonus_ft"] = max(0.0, round(bonus_ft, 2))
        existing.setdefault("dash_used", bool(existing.get("bonus_ft")))
        existing.setdefault("difficult_terrain", False)
        existing.setdefault("disengaged", False)
        existing.setdefault("cost_multiplier", 1.0)
        total_budget_ft = _movement_total_budget_ft(existing)
        existing["remaining_ft"] = max(0.0, round(total_budget_ft - spent_ft, 2))
        if existing.get("last_x") is None and token is not None:
            existing["last_x"] = float(getattr(token, "x", 0.0) or 0.0)
        if existing.get("last_y") is None and token is not None:
            existing["last_y"] = float(getattr(token, "y", 0.0) or 0.0)
    combat["movement"] = existing
    session.combat = combat
    return existing


def _movement_total_budget_ft(move_state: dict | None) -> float:
    if not isinstance(move_state, dict):
        return 0.0
    speed_ft = float(move_state.get("speed_ft", 0.0) or 0.0)
    bonus_ft = float(move_state.get("bonus_ft", 0.0) or 0.0)
    return max(0.0, round(speed_ft + bonus_ft, 2))


def _movement_cost_multiplier(move_state: dict | None) -> float:
    if not isinstance(move_state, dict):
        return 1.0
    if move_state.get("difficult_terrain"):
        return 2.0
    try:
        mult = float(move_state.get("cost_multiplier", 1.0) or 1.0)
    except Exception:
        mult = 1.0
    return max(1.0, mult)


def _can_manage_current_turn_movement(session: Session, user: User) -> tuple[bool, str | None, dict | None, object | None]:
    combat = getattr(session, "combat", None) or {}
    if not combat.get("active"):
        return False, "Combat is not active.", None, None
    current = _get_current_combatant(session)
    token_id = str((current or {}).get("token_id") or "").strip()
    if not token_id:
        return False, "No active combatant.", current, None
    token = session.tokens.get(token_id)
    if user.role == "dm":
        return True, None, current, token
    owner_id = str(getattr(token, "owner_id", "") or (current or {}).get("owner_id") or "").strip()
    if not _owner_matches_user(owner_id, user):
        return False, "Only the active player can use that combat movement action.", current, token
    return True, None, current, token


async def _broadcast_combat_move_state(session: Session):
    move_state = _ensure_combat_movement_state(session)
    await manager.broadcast(session.id, {
        "type": "combat_move_state",
        "payload": move_state,
    })


async def _send_token_move_denied(session: Session, user: User, token, message: str):
    move_state = _ensure_combat_movement_state(session)
    await manager.send_to(session.id, user.id, {
        "type": "token_move_denied",
        "payload": {
            "token_id": getattr(token, "id", None),
            "x": getattr(token, "x", None),
            "y": getattr(token, "y", None),
            "message": str(message or "Movement blocked."),
            "movement": move_state,
        }
    })


async def _enforce_player_combat_movement(session: Session, user: User, token, new_x: float, new_y: float) -> bool:
    if user.role == "dm":
        return True
    combat = getattr(session, "combat", None) or {}
    if not combat.get("active"):
        return True
    token_ids = _combatant_token_ids(session)
    token_id = str(getattr(token, "id", "") or "")
    if token_id not in token_ids:
        return True
    current = _get_current_combatant(session)
    current_token_id = str((current or {}).get("token_id") or "").strip()
    if not current_token_id or current_token_id != token_id:
        await _send_token_move_denied(session, user, token, "It is not your turn to move that token.")
        return False
    move_state = _ensure_combat_movement_state(session)
    total_budget_ft = _movement_total_budget_ft(move_state)
    if total_budget_ft <= 0:
        return True
    segment_ft = _movement_ft_between_positions(move_state.get("last_x"), move_state.get("last_y"), new_x, new_y)
    if segment_ft <= 0:
        return True
    move_cost_ft = round(segment_ft * _movement_cost_multiplier(move_state), 2)
    spent_ft = float(move_state.get("spent_ft", 0.0) or 0.0)
    remaining_ft = max(0.0, round(total_budget_ft - spent_ft, 2))
    if move_cost_ft > (remaining_ft + 0.01):
        remaining_text = int(round(remaining_ft)) if abs(remaining_ft - round(remaining_ft)) < 0.05 else round(remaining_ft, 1)
        await _send_token_move_denied(session, user, token, f"Movement limit reached — {remaining_text} ft remaining this turn.")
        return False
    move_state["spent_ft"] = round(spent_ft + move_cost_ft, 2)
    move_state["remaining_ft"] = max(0.0, round(total_budget_ft - move_state["spent_ft"], 2))
    move_state["last_x"] = float(new_x)
    move_state["last_y"] = float(new_y)
    session.combat["movement"] = move_state
    return True


async def _advance_combat_turn(session: Session):
    """Advance to next turn, increment round when wrapping."""
    coms = session.combat.get("combatants", [])
    if not coms:
        return False
    prev_turn = session.combat.get("turn", 0)
    next_turn = (prev_turn + 1) % len(coms)
    session.combat["active"] = True
    session.combat["turn"] = next_turn
    if next_turn == 0 and prev_turn != 0:
        session.combat["round"] = session.combat.get("round", 1) + 1
    elif "round" not in session.combat:
        session.combat["round"] = 1
    _ensure_combat_movement_state(session, reset=True)
    return True


async def handle_combat_update(payload: dict, session: Session, user: User):
    """DM sets full combatant list (add/remove/reorder/edit initiative)."""
    if user.role != "dm":
        return
    # Lazy import to avoid circular dependency: combat -> hazards -> viewer_powers -> combat
    from server.handlers.hazards import _process_current_start_turn_hazards
    was_active = bool((session.combat or {}).get("active"))
    session.combat["combatants"] = payload.get("combatants", [])
    session.combat["active"] = payload.get("active", session.combat.get("active", False))
    session.combat["turn"] = payload.get("turn", session.combat.get("turn", 0))
    session.combat["round"] = payload.get("round", session.combat.get("round", 1))
    if session.combat.get("active"):
        _ensure_combat_movement_state(session, reset=True)
    else:
        session.combat["movement"] = {}
    await _process_current_start_turn_hazards(session)
    await save_campaign_async(session)
    await _broadcast_combat(session)
    # Auto-trigger ambient sound on combat start
    if not was_active and session.combat.get("active"):
        sound_state = getattr(session, "sound_state", None) or {}
        sound_state["pre_combat_track"] = sound_state.get("track", "silence")
        sound_state["track"] = "battle"
        sound_state["volume"] = sound_state.get("volume", 0.7)
        sound_state["fade_ms"] = 1500
        session.sound_state = sound_state
        await manager.broadcast(session.id, {
            "type": "sound_set_ambient",
            "payload": {"track": "battle", "volume": sound_state["volume"], "fade_ms": 1500},
        })


async def handle_combat_next(payload: dict, session: Session, user: User):
    """Advance to next turn, increment round when wrapping."""
    if not _can_manage_combat(session, user):
        return
    # Lazy imports to avoid circular dependency: combat -> hazards -> viewer_powers -> combat
    from server.handlers.hazards import (
        _process_current_end_turn_hazards,
        _process_current_start_turn_hazards,
        _process_end_round_hazards,
    )
    prev_round = _safe_int((getattr(session, 'combat', {}) or {}).get('round'), 1, minimum=1, maximum=999999)
    await _process_current_end_turn_hazards(session, round_number=prev_round)
    advanced = await _advance_combat_turn(session)
    if not advanced:
        return
    new_round = _safe_int((getattr(session, 'combat', {}) or {}).get('round'), prev_round, minimum=1, maximum=999999)
    if new_round > prev_round:
        await _process_end_round_hazards(session, round_number=prev_round)
    await _process_current_start_turn_hazards(session)
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_prev(payload: dict, session: Session, user: User):
    """Go back one turn, decrement round when wrapping."""
    if not _can_manage_combat(session, user):
        return
    coms = session.combat.get("combatants", [])
    if not coms:
        return
    prev_turn = session.combat.get("turn", 0)
    prev_round = session.combat.get("round", 1)
    new_turn = (prev_turn - 1) % len(coms)
    session.combat["active"] = True
    session.combat["turn"] = new_turn
    if new_turn == len(coms) - 1 and prev_turn == 0:
        session.combat["round"] = max(1, prev_round - 1)
    _ensure_combat_movement_state(session, reset=True)
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_clear(payload: dict, session: Session, user: User):
    """End combat."""
    if user.role != "dm":
        return
    # Auto-restore ambient track that was playing before combat started
    sound_state = getattr(session, "sound_state", None) or {}
    pre_combat = sound_state.get("pre_combat_track", "silence")
    session.combat = {"active": False, "turn": 0, "combatants": [], "movement": {}}
    event = {
        "event_type": "clear_encounter",
        "target_id": str(payload.get("encounter_id") or payload.get("encounter_template_id") or "").strip(),
    }
    quests = list(getattr(session, "session_quests", []) or [])
    for idx, quest in enumerate(quests):
        entry = normalize_quest_payload_shape(dict(quest or {}))
        if apply_objective_event(entry, event):
            quests[idx] = entry
    session.session_quests = quests
    await save_campaign_async(session)
    await _broadcast_combat(session)
    if sound_state.get("track") == "battle":
        sound_state["track"] = pre_combat
        sound_state.pop("pre_combat_track", None)
        sound_state["fade_ms"] = 2000
        session.sound_state = sound_state
        await manager.broadcast(session.id, {
            "type": "sound_set_ambient",
            "payload": {"track": pre_combat, "volume": sound_state.get("volume", 0.7), "fade_ms": 2000},
        })


async def handle_combat_dash(payload: dict, session: Session, user: User):
    allowed, message, current, token = _can_manage_current_turn_movement(session, user)
    if not allowed:
        if message:
            await manager.send_to(session.id, user.id, {"type": "token_move_denied", "payload": {"message": message, "movement": _ensure_combat_movement_state(session)}})
        return
    move_state = _ensure_combat_movement_state(session)
    if move_state.get("dash_used"):
        await manager.send_to(session.id, user.id, {"type": "token_move_denied", "payload": {"message": "Dash is already active for this turn.", "movement": move_state}})
        return
    speed_ft = float(move_state.get("speed_ft", 0.0) or 0.0)
    if speed_ft <= 0:
        await manager.send_to(session.id, user.id, {"type": "token_move_denied", "payload": {"message": "This token has no speed set.", "movement": move_state}})
        return
    move_state["bonus_ft"] = round(float(move_state.get("bonus_ft", 0.0) or 0.0) + speed_ft, 2)
    move_state["dash_used"] = True
    move_state["remaining_ft"] = max(0.0, round(_movement_total_budget_ft(move_state) - float(move_state.get("spent_ft", 0.0) or 0.0), 2))
    session.combat["movement"] = move_state
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_toggle_difficult_terrain(payload: dict, session: Session, user: User):
    allowed, message, current, token = _can_manage_current_turn_movement(session, user)
    if not allowed:
        if message:
            await manager.send_to(session.id, user.id, {"type": "token_move_denied", "payload": {"message": message, "movement": _ensure_combat_movement_state(session)}})
        return
    move_state = _ensure_combat_movement_state(session)
    enabled = payload.get("enabled")
    if enabled is None:
        enabled = not bool(move_state.get("difficult_terrain"))
    move_state["difficult_terrain"] = bool(enabled)
    move_state["cost_multiplier"] = 2.0 if move_state["difficult_terrain"] else 1.0
    move_state["remaining_ft"] = max(0.0, round(_movement_total_budget_ft(move_state) - float(move_state.get("spent_ft", 0.0) or 0.0), 2))
    session.combat["movement"] = move_state
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_reset_movement(payload: dict, session: Session, user: User):
    if not _can_manage_combat(session, user):
        return
    move_state = _ensure_combat_movement_state(session)
    token_id = str(move_state.get("token_id") or "")
    token = session.tokens.get(token_id) if token_id else None
    move_state["spent_ft"] = 0.0
    move_state["remaining_ft"] = _movement_total_budget_ft(move_state)
    move_state["last_x"] = float(getattr(token, "x", 0.0) or 0.0) if token is not None else None
    move_state["last_y"] = float(getattr(token, "y", 0.0) or 0.0) if token is not None else None
    session.combat["movement"] = move_state
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_toggle_disengage(payload: dict, session: Session, user: User):
    allowed, message, current, token = _can_manage_current_turn_movement(session, user)
    if not allowed:
        if message:
            await manager.send_to(session.id, user.id, {"type": "token_move_denied", "payload": {"message": message, "movement": _ensure_combat_movement_state(session)}})
        return
    move_state = _ensure_combat_movement_state(session)
    enabled = payload.get("enabled")
    if enabled is None:
        enabled = not bool(move_state.get("disengaged"))
    move_state["disengaged"] = bool(enabled)
    session.combat["movement"] = move_state
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_end_turn(payload: dict, session: Session, user: User):
    combat = getattr(session, "combat", None) or {}
    if not combat.get("active"):
        return
    if user.role != "dm":
        current = _get_current_combatant(session)
        token_id = str((current or {}).get("token_id") or "").strip()
        token = session.tokens.get(token_id) if token_id else None
        owner_id = str(getattr(token, "owner_id", "") or (current or {}).get("owner_id") or "").strip()
        if not _owner_matches_user(owner_id, user):
            await manager.send_to(session.id, user.id, {"type": "token_move_denied", "payload": {"message": "Only the active player can end this turn.", "movement": _ensure_combat_movement_state(session)}})
            return
    advanced = await _advance_combat_turn(session)
    if not advanced:
        return
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_death_save(payload: dict, session: Session, user: User):
    import random

    combat = getattr(session, "combat", None) or {}
    if not combat.get("active"):
        return
    current = _get_current_combatant(session)
    token_id = str((current or {}).get("token_id") or "").strip()
    token = session.tokens.get(token_id) if token_id else None
    if not current or not token:
        return
    owner_id = str(getattr(token, "owner_id", "") or (current or {}).get("owner_id") or "").strip()
    if user.role != "dm" and not _owner_matches_user(owner_id, user):
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": "Only the active player can roll that death save."}
        })
        return
    hp_value = getattr(token, "hp", None)
    if hp_value is None or int(hp_value or 0) > 0:
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": "That creature is not at 0 HP."}
        })
        return

    existing = current.get("death_saves") if isinstance(current.get("death_saves"), dict) else None
    death_saves = dict(existing or {"successes": 0, "fails": 0, "stable": False, "dead": False})
    if death_saves.get("dead"):
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": f"{token.name} is already dead."}
        })
        return

    roll = random.randint(1, 20)
    if roll == 1:
        death_saves["fails"] = min(3, int(death_saves.get("fails", 0) or 0) + 2)
    elif roll >= 10:
        death_saves["successes"] = min(3, int(death_saves.get("successes", 0) or 0) + 1)
    else:
        death_saves["fails"] = min(3, int(death_saves.get("fails", 0) or 0) + 1)

    recovered = False
    dead = False
    if roll >= 10:
        recovered = True
        token.hp = 1
        current["hp"] = 1
        current.pop("death_saves", None)
    elif int(death_saves.get("fails", 0) or 0) >= 3:
        dead = True
        death_saves["dead"] = True
        current["death_saves"] = death_saves
    else:
        current["death_saves"] = death_saves

    detail = f"{token.name} death save {roll}: {int(death_saves.get('successes', 0) or 0)} success / {int(death_saves.get('fails', 0) or 0)} fail"
    if recovered:
        detail += " • recovers to 1 HP"
    elif dead:
        detail += " • dead"
    log_entry = session.add_log(detail, "dice", user.name)
    await manager.broadcast(session.id, {
        "type": "dice_result",
        "payload": {
            "user_id": user.id,
            "user_name": user.name,
            "dice_type": 20,
            "quantity": 1,
            "rolls": [roll],
            "total": roll,
            "modifier": 0,
            "roll_label": f"{token.name} death save",
            "log": log_entry,
        }
    })
    if recovered:
        from server.handlers.common import _broadcast_token_event
        await _broadcast_token_event(manager, session, "token_hp_updated", {
            "token_id": token.id,
            "hp": token.hp,
            "maxHp": token.max_hp,
            "hidden_hp": token.hidden_hp,
            "log": None,
        }, token)
        # Auto-generate a party memory for a dramatic survival moment
        from server.handlers.content import add_auto_party_memory, _broadcast_party_memory_state
        add_auto_party_memory(session, f"{token.name} survived on 1 HP.")
        await _broadcast_party_memory_state(session)
    await save_campaign_async(session)
    await _broadcast_combat(session)


async def handle_combat_roll_initiative(payload: dict, session: Session, user: User):
    """Player or DM rolls initiative for a combatant. Rolls d20 + modifier, updates list.

    DMs can roll for any combatant. Players may only roll for their own combatant.
    Assistant DMs with combat.manage_limited scope can roll for any combatant.
    """
    combatant_id = str(payload.get("combatant_id") or "").strip()
    token_id = str(payload.get("token_id") or "").strip()
    roll = _safe_int(payload.get("roll"), 0, minimum=1, maximum=20)

    coms = session.combat.get("combatants", [])
    target_combatant = None
    for c in coms:
        if combatant_id and str(c.get("id") or "") == combatant_id:
            target_combatant = c
            break
        if token_id and str(c.get("token_id") or "") == token_id:
            target_combatant = c
            break
    if target_combatant is None:
        return

    modifier = _safe_int(payload.get("modifier"), _safe_int(target_combatant.get("modifier"), 0, minimum=-99, maximum=99), minimum=-99, maximum=99)
    total = roll + modifier

    # Role check: DM and assistant DMs with combat scope can roll for anyone.
    # Players may only roll initiative for their own combatant.
    if not _can_manage_combat(session, user):
        combatant_owner_id = str((target_combatant or {}).get("owner_id") or "").strip()
        combatant_token_id = str((target_combatant or {}).get("token_id") or "").strip()
        token = session.tokens.get(combatant_token_id) if combatant_token_id else None
        token_owner_id = str(getattr(token, "owner_id", "") or "").strip()
        owner_id = combatant_owner_id or token_owner_id
        if not _owner_matches_user(owner_id, user):
            await manager.send_to(session.id, user.id, {
                "type": "error",
                "payload": {"message": "You may only roll initiative for your own character."}
            })
            return

    target_combatant["initiative"] = total
    target_combatant["roll"] = roll
    target_combatant["modifier"] = modifier

    current_id = None
    old_turn = session.combat.get("turn", 0)
    if 0 <= old_turn < len(coms):
        current_id = coms[old_turn].get("id")
    coms.sort(key=lambda x: (x.get("initiative") if x.get("initiative") is not None else -99), reverse=True)
    session.combat["combatants"] = coms
    if current_id:
        for i, c in enumerate(coms):
            if c.get("id") == current_id:
                session.combat["turn"] = i
                break
    _ensure_combat_movement_state(session, reset=True)
    await save_campaign_async(session)

    await manager.broadcast(session.id, {
        "type": "combat_state",
        "payload": session.combat,
    })
    log_entry = session.add_log(
        f"🎲 {user.name} initiative: {roll} + {modifier:+d} = {total}",
        "dice", user.name
    )
    await manager.broadcast(session.id, {"type": "log_entry", "payload": {"log": log_entry}})


# ── Combat attack / spell flow ─────────────────────────────────────────────


def _can_act_current_turn(session: Session, user: User) -> tuple[bool, str | None]:
    """Return (allowed, error_message). True if user is DM or owns the active combatant."""
    combat = getattr(session, "combat", None) or {}
    if not combat.get("active"):
        return False, "Combat is not active."
    current = _get_current_combatant(session)
    if not current:
        return False, "No active combatant."
    if user.role == "dm":
        return True, None
    token_id = str((current or {}).get("token_id") or "").strip()
    token = session.tokens.get(token_id) if token_id else None
    owner_id = str(getattr(token, "owner_id", "") or (current or {}).get("owner_id") or "").strip()
    if not _owner_matches_user(owner_id, user):
        return False, "Only the active combatant can do that."
    return True, None


async def handle_combat_select_target(payload: dict, session: Session, user: User):
    """Store the chosen target token on the combat state and broadcast."""
    allowed, message = _can_act_current_turn(session, user)
    if not allowed:
        if message:
            await manager.send_to(session.id, user.id, {
                "type": "error", "payload": {"message": message}
            })
        return
    target_id = str(payload.get("target_id") or "").strip()
    if target_id and target_id not in session.tokens:
        await manager.send_to(session.id, user.id, {
            "type": "error", "payload": {"message": "Target token not found."}
        })
        return
    session.combat["selected_target_id"] = target_id
    await _broadcast_combat(session)


async def handle_combat_attack_request(payload: dict, session: Session, user: User):
    """Player (or DM) submits an attack/spell request for DM resolution.

    Stores a ``pending_attack`` on the combat dict and broadcasts so the DM
    sees the Succeed / Fail prompt. Prevents duplicate submissions.
    """
    allowed, message = _can_act_current_turn(session, user)
    if not allowed:
        if message:
            await manager.send_to(session.id, user.id, {
                "type": "error", "payload": {"message": message}
            })
        return

    # Prevent duplicate submission while one is already pending.
    if session.combat.get("pending_attack"):
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": "An attack is already waiting for DM resolution."}
        })
        return

    target_id = str(payload.get("target_id") or "").strip()
    target_token = session.tokens.get(target_id) if target_id else None
    if not target_token:
        await manager.send_to(session.id, user.id, {
            "type": "error", "payload": {"message": "No valid target selected."}
        })
        return

    attack_kind = str(payload.get("attack_kind") or "weapon").strip().lower()
    if attack_kind not in ("weapon", "spell"):
        attack_kind = "weapon"

    current = _get_current_combatant(session) or {}
    attacker_token_id = str(current.get("token_id") or "").strip()
    attacker_token = session.tokens.get(attacker_token_id) if attacker_token_id else None
    attacker_name = str(getattr(attacker_token, "name", None) or current.get("name") or user.name)
    attacker_owner_id = str(getattr(attacker_token, "owner_id", None) or current.get("owner_id") or user.id or "").strip()
    target_name = str(getattr(target_token, "name", None) or "Target")
    has_disadvantage = _has_encumbrance_attack_disadvantage(session, attacker_owner_id)
    disadvantage_reason = "heavily_encumbered" if has_disadvantage else ""

    spell_name = str(payload.get("spell_name") or "").strip()
    spell_id = str(payload.get("spell_id") or "").strip()

    session.combat["pending_attack"] = {
        "attacker_user_id": str(user.id),
        "attacker_token_id": attacker_token_id,
        "attacker_name": attacker_name,
        "target_token_id": target_id,
        "target_name": target_name,
        "attack_kind": attack_kind,
        "spell_name": spell_name,
        "spell_id": spell_id,
        "disadvantage": has_disadvantage,
        "disadvantage_reason": disadvantage_reason,
        "submitted_at": _time.time(),
    }

    action_label = spell_name if (attack_kind == "spell" and spell_name) else attack_kind
    if has_disadvantage:
        action_label = f"{action_label} · DISADVANTAGE"
    log_entry = session.add_log(
        f"{'✨' if attack_kind == 'spell' else '⚔'} {attacker_name} → {target_name} ({action_label}) — awaiting DM",
        "system", user.name
    )
    await _broadcast_combat(session)
    await manager.broadcast(session.id, {"type": "log_entry", "payload": {"log": log_entry}})


async def handle_combat_attack_override(payload: dict, session: Session, user: User):
    """DM resolves a pending attack as hit or miss and broadcasts the result animation."""
    if user.role != "dm":
        await manager.send_to(session.id, user.id, {
            "type": "error", "payload": {"message": "Only the DM can resolve attacks."}
        })
        return

    # Atomically pop the pending attack to prevent double-trigger.
    pending = session.combat.pop("pending_attack", None)
    if not pending:
        await manager.send_to(session.id, user.id, {
            "type": "error", "payload": {"message": "No pending attack to resolve."}
        })
        return

    result = str(payload.get("result") or "miss").strip().lower()
    if result not in ("hit", "miss"):
        result = "miss"

    target_token_id = str(pending.get("target_token_id") or "").strip()
    attack_kind = str(pending.get("attack_kind") or "weapon")
    attacker_name = str(pending.get("attacker_name") or "Attacker")
    target_name = str(pending.get("target_name") or "Target")

    attacker_user_id = str(pending.get("attacker_user_id") or "")
    attacker_token_id_out = str(pending.get("attacker_token_id") or "")
    spell_name_out = str(pending.get("spell_name") or "")
    spell_id_out = str(pending.get("spell_id") or "")
    has_disadvantage = bool(pending.get("disadvantage"))
    disadvantage_reason = str(pending.get("disadvantage_reason") or "")

    # Broadcast the visual result to every connected client.
    await manager.broadcast(session.id, {
        "type": "combat_attack_result",
        "payload": {
            "result": result,
            "target_token_id": target_token_id,
            "attack_kind": attack_kind,
            "attacker_name": attacker_name,
            "target_name": target_name,
            "attacker_user_id": attacker_user_id,
            "attacker_token_id": attacker_token_id_out,
            "spell_name": spell_name_out,
            "spell_id": spell_id_out,
            "disadvantage": has_disadvantage,
            "disadvantage_reason": disadvantage_reason,
        },
    })

    outcome_text = "hit" if result == "hit" else "missed"
    log_entry = session.add_log(
        f"{'⚔' if attack_kind == 'weapon' else '✨'} {attacker_name} {outcome_text} {target_name} ({attack_kind})",
        "system", user.name
    )
    await manager.broadcast(session.id, {"type": "log_entry", "payload": {"log": log_entry}})

    # Broadcast updated combat state (pending_attack now cleared).
    await _broadcast_combat(session)
