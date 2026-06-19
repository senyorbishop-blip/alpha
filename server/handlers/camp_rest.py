"""
server/handlers/camp_rest.py — Camp / rest mode for downtime scenes.

The DM can open a camp/rest scene between combats.  Players choose a
downtime activity (cook, keep watch, tell story, etc.).  Selections are
broadcast to every connected user so the table can narrate around them.
The DM may restrict which activities are on offer and can end the scene
at any time.  No heavy mechanics — this is pure atmosphere and interaction.
"""
import time
from server.session import Session, User
from server.character.summon_runtime import prune_expired_temporary_summons
from server.handlers.common import (
    manager, save_campaign_async,
    _apply_heal, _broadcast_token_state_sync, _sync_combatant_token_state,
)

# Canonical activity definitions
CAMP_ACTIVITIES = {
    "cook":          {"label": "Cook",           "icon": "🍲", "description": "Prepare a hearty meal to restore spirits."},
    "keep_watch":    {"label": "Keep Watch",      "icon": "👁",  "description": "Stand guard and keep the camp safe through the night."},
    "tell_story":    {"label": "Tell Story",      "icon": "📖", "description": "Share a tale from your past around the fire."},
    "identify_item": {"label": "Identify Item",   "icon": "🔍", "description": "Study a mysterious item and uncover its properties."},
    "train":         {"label": "Train",           "icon": "⚔️",  "description": "Practice your combat or class techniques."},
    "pray":          {"label": "Pray",            "icon": "🙏", "description": "Commune with your deity or meditate in quiet."},
    "gamble":        {"label": "Gamble",          "icon": "🎲", "description": "Play dice or cards with fellow adventurers."},
    "bond_with_ally":{"label": "Bond with Ally",  "icon": "🤝", "description": "Strengthen a connection with a companion."},
}

ALL_ACTIVITY_IDS = list(CAMP_ACTIVITIES.keys())


def _safe_camp_rest(session: Session) -> dict:
    """Return the camp_rest dict, initialising if needed."""
    if not isinstance(session.camp_rest, dict):
        session.camp_rest = {
            "active": False,
            "label": "",
            "available_activities": [],
            "player_activities": {},
        }
    return session.camp_rest


async def _broadcast_camp_rest_state(session: Session):
    """Push the full camp_rest state to every connected user."""
    cr = _safe_camp_rest(session)
    payload = {
        "active": cr.get("active", False),
        "label": cr.get("label", ""),
        "available_activities": cr.get("available_activities", list(ALL_ACTIVITY_IDS)),
        "player_activities": dict(cr.get("player_activities") or {}),
        "activity_defs": CAMP_ACTIVITIES,
    }
    for uid in list(session.users.keys()):
        await manager.send_to(session.id, uid, {
            "type": "camp_rest_sync",
            "payload": payload,
        })


async def handle_camp_rest_start(payload: dict, session: Session, user: User):
    """DM opens a camp/rest scene."""
    if user.role != "dm":
        return

    label = str(payload.get("label") or "Making Camp").strip()[:120]
    raw_acts = payload.get("available_activities")
    if isinstance(raw_acts, list):
        available = [a for a in raw_acts if a in CAMP_ACTIVITIES]
    else:
        available = list(ALL_ACTIVITY_IDS)

    cr = _safe_camp_rest(session)
    cr["active"] = True
    cr["label"] = label
    cr["available_activities"] = available
    # Clear previous selections when starting a new scene
    cr["player_activities"] = {}

    session.add_log(f"Camp/rest scene started: {label}", "system", "DM")
    await _broadcast_camp_rest_state(session)
    await save_campaign_async(session)


async def handle_camp_rest_end(payload: dict, session: Session, user: User):
    """DM closes the camp/rest scene."""
    if user.role != "dm":
        return

    cr = _safe_camp_rest(session)
    cr["active"] = False
    cr["player_activities"] = {}

    session.add_log("Camp/rest scene ended.", "system", "DM")
    await _broadcast_camp_rest_state(session)
    await save_campaign_async(session)


async def handle_camp_rest_activity_select(payload: dict, session: Session, user: User):
    """A player (or the DM on behalf of a token) selects a downtime activity."""
    cr = _safe_camp_rest(session)
    if not cr.get("active"):
        await manager.send_to(session.id, user.id, {
            "type": "notification",
            "payload": {"message": "No active camp/rest scene.", "kind": "warning"},
        })
        return

    activity_id = str(payload.get("activity_id") or "").strip()
    if not activity_id or activity_id not in CAMP_ACTIVITIES:
        return

    # DM may restrict available activities
    available = cr.get("available_activities") or ALL_ACTIVITY_IDS
    if activity_id not in available:
        await manager.send_to(session.id, user.id, {
            "type": "notification",
            "payload": {"message": "That activity is not available at this camp.", "kind": "warning"},
        })
        return

    note = str(payload.get("note") or "").strip()[:200]
    player_activities = dict(cr.get("player_activities") or {})
    player_activities[user.id] = {
        "user_id": user.id,
        "user_name": user.name,
        "activity_id": activity_id,
        "note": note,
        "selected_at": time.time(),
    }
    cr["player_activities"] = player_activities

    act = CAMP_ACTIVITIES[activity_id]
    log_msg = f"{user.name} chose to {act['label'].lower()} during the rest."
    if note:
        log_msg += f' — "{note}"'
    session.add_log(log_msg, "camp_rest", user.name)

    await _broadcast_camp_rest_state(session)

    # Broadcast a chat-style log entry so everyone sees the narrative
    await manager.broadcast(session.id, {
        "type": "chat_message",
        "payload": {
            "user": user.name,
            "message": log_msg,
            "channel": "everyone",
            "msg_type": "camp_rest",
        },
    })


async def handle_camp_rest_update_activities(payload: dict, session: Session, user: User):
    """DM updates the list of available activities mid-scene."""
    if user.role != "dm":
        return

    raw_acts = payload.get("available_activities")
    if not isinstance(raw_acts, list):
        return

    available = [a for a in raw_acts if a in CAMP_ACTIVITIES]
    cr = _safe_camp_rest(session)
    cr["available_activities"] = available
    await _broadcast_camp_rest_state(session)
    await save_campaign_async(session)


async def handle_camp_rest_clear_activity(payload: dict, session: Session, user: User):
    """Remove a player's activity selection (DM can clear any; players clear their own)."""
    target_user_id = str(payload.get("user_id") or user.id)
    if user.role != "dm" and target_user_id != user.id:
        return

    cr = _safe_camp_rest(session)
    player_activities = dict(cr.get("player_activities") or {})
    player_activities.pop(target_user_id, None)
    cr["player_activities"] = player_activities
    await _broadcast_camp_rest_state(session)


async def handle_camp_rest_take_rest(payload: dict, session: Session, user: User):
    """DM triggers a short or long rest, applying HP and resource recovery."""
    if user.role != "dm":
        await manager.send_to(session.id, user.id, {
            "type": "notification",
            "payload": {"message": "Only the DM can trigger a rest.", "kind": "warning"},
        })
        return

    rest_type = str(payload.get("rest_type") or "long").strip().lower()
    if rest_type not in ("short", "long"):
        rest_type = "long"

    healed_tokens = []
    removed_temp_summon_tokens: list[str] = []
    item_recharge_updates = []

    if rest_type == "long":
        # Long rest (5e): all player tokens restored to full HP, temp HP cleared.
        # Spell slots are reset client-side when they receive the event.
        for tid, token in list(session.tokens.items()):
            owner = getattr(token, "owner_id", None)
            if not owner:
                continue  # Skip DM-owned tokens
            max_hp = getattr(token, "max_hp", None)
            if max_hp is None:
                continue
            old_hp = int(getattr(token, "hp") or 0)
            token.hp = int(max_hp)
            token.temp_hp = 0
            _sync_combatant_token_state(session, token, previous_hp=old_hp)
            healed_tokens.append({
                "token_id": tid,
                "name": getattr(token, "name", "Unknown"),
                "hp": token.hp,
                "max_hp": int(max_hp),
            })

        from server.handlers.inventory import refresh_item_charges_for_rest
        for uid, session_user in list((getattr(session, "users", {}) or {}).items()):
            if getattr(session_user, "role", "") != "player":
                continue
            updated = refresh_item_charges_for_rest(session, session_user, "long")
            if updated:
                item_recharge_updates.append({
                    "user_id": uid,
                    "user_name": getattr(session_user, "name", "Player"),
                    "items": updated,
                })

        log_msg = "🌙 Long rest — all party members restored to full HP. Spell slots refreshed."
        rest_label = "Long Rest"

    else:
        # Short rest (5e): no automatic HP recovery — players spend hit dice.
        # Broadcast the event so each client can show the hit dice UI.
        from server.handlers.inventory import refresh_item_charges_for_rest
        for uid, session_user in list((getattr(session, "users", {}) or {}).items()):
            if getattr(session_user, "role", "") != "player":
                continue
            updated = refresh_item_charges_for_rest(session, session_user, "short")
            if updated:
                item_recharge_updates.append({
                    "user_id": uid,
                    "user_name": getattr(session_user, "name", "Player"),
                    "items": updated,
                })

        log_msg = "☀ Short rest — party may spend hit dice to recover HP."
        rest_label = "Short Rest"

    profiles = dict(getattr(session, "char_profiles", {}) or {})
    for owner_key, rows in list(profiles.items()):
        if not isinstance(rows, list):
            continue
        bucket = list(rows)
        changed = False
        for idx, row in enumerate(bucket):
            if not isinstance(row, dict):
                continue
            native = row.get("nativeCharacter") if isinstance(row.get("nativeCharacter"), dict) else {}
            removed = prune_expired_temporary_summons(native, rest_type=rest_type)
            if not removed:
                continue
            changed = True
            row["nativeCharacter"] = native
            bucket[idx] = row
            for entry in removed:
                tok_id = str(entry.get("tokenId") or "").strip()
                if tok_id and tok_id in (session.tokens or {}):
                    session.tokens.pop(tok_id, None)
                    removed_temp_summon_tokens.append(tok_id)
                    await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": tok_id}})
        if changed:
            profiles[owner_key] = bucket
    session.char_profiles = profiles

    session.add_log(log_msg, "camp_rest", "DM")

    # Sync token state across all clients if HP changed
    if healed_tokens:
        await _broadcast_token_state_sync(session)

    # Broadcast rest result so clients can update spell slots / show hit dice UI
    await manager.broadcast(session.id, {
        "type": "camp_rest_rest_applied",
        "payload": {
            "rest_type": rest_type,
            "label": rest_label,
            "healed_tokens": healed_tokens,
            "item_recharge_updates": item_recharge_updates,
            "message": log_msg,
            "removed_temp_summon_tokens": removed_temp_summon_tokens,
        },
    })

    if rest_type == "long" or item_recharge_updates:
        from server.handlers.inventory import _broadcast_inventory_state
        await _broadcast_inventory_state(session)

    await manager.broadcast(session.id, {
        "type": "chat_message",
        "payload": {
            "user": "DM",
            "message": log_msg,
            "channel": "everyone",
            "msg_type": "camp_rest",
        },
    })

    await save_campaign_async(session)


async def handle_camp_rest_spend_hit_die(payload: dict, session: Session, user: User):
    """Player spends a hit die during a short rest — applies healing to their token."""
    cr = _safe_camp_rest(session)
    if not cr.get("active"):
        return

    heal_amount = int(payload.get("heal_amount") or 0)
    if heal_amount <= 0:
        return

    # Find the player's token
    token = None
    for tid, tok in list(session.tokens.items()):
        owner = getattr(tok, "owner_id", None)
        if owner and str(owner) == str(user.id):
            token = tok
            break

    if token is None:
        await manager.send_to(session.id, user.id, {
            "type": "notification",
            "payload": {"message": "Could not find your token to apply healing.", "kind": "warning"},
        })
        return

    actual = _apply_heal(token, heal_amount)
    _sync_combatant_token_state(session, token)
    await _broadcast_token_state_sync(session)

    token_name = getattr(token, "name", user.name)
    log_msg = f"☀ {token_name} spends a hit die and recovers {actual} HP ({token.hp}/{token.max_hp})."
    session.add_log(log_msg, "camp_rest", user.name)
    await manager.broadcast(session.id, {
        "type": "chat_message",
        "payload": {"user": user.name, "message": log_msg, "channel": "everyone", "msg_type": "camp_rest"},
    })
    # Notify the player of the result
    await manager.send_to(session.id, user.id, {
        "type": "camp_rest_hit_die_result",
        "payload": {"heal_amount": actual, "new_hp": token.hp, "max_hp": token.max_hp},
    })
    await save_campaign_async(session)


async def handle_character_self_rest(payload: dict, session: Session, user: User):
    """A player rests their own character from the character sheet.

    Unlike `camp_rest_take_rest` (DM-triggered, party-wide), this lets a
    player take a short or long rest individually. HP/spell slot/resource
    state is already applied client-side (mirroring how char_hp_update and
    token_hp_update work elsewhere); this handler covers the parts that
    must be authoritative on the server: item charge recharge, and logging
    the rest to chat/journal so the DM and table see it.
    """
    if user.role != "player":
        return

    rest_type = str(payload.get("rest_type") or "long").strip().lower()
    if rest_type not in ("short", "long"):
        rest_type = "long"
    hit_dice_spent = max(0, int(payload.get("hit_dice_spent") or 0))

    from server.handlers.inventory import refresh_item_charges_for_rest
    updated_items = refresh_item_charges_for_rest(session, user, rest_type)

    char_name = str(payload.get("character_name") or user.name or "A character").strip()
    if rest_type == "long":
        log_msg = f"🌙 {char_name} completed a Long Rest."
    elif hit_dice_spent > 0:
        plural = "" if hit_dice_spent == 1 else "s"
        log_msg = f"☀ {char_name} completed a Short Rest and spent {hit_dice_spent} hit die{plural}."
    else:
        log_msg = f"☀ {char_name} completed a Short Rest."

    session.add_log(log_msg, "rest", user.name)
    await manager.broadcast(session.id, {
        "type": "chat_message",
        "payload": {"user": user.name, "message": log_msg, "channel": "everyone", "msg_type": "character_rest"},
    })

    if updated_items:
        from server.handlers.inventory import _broadcast_inventory_state
        await _broadcast_inventory_state(session)

    await manager.send_to(session.id, user.id, {
        "type": "character_rest_applied",
        "payload": {"rest_type": rest_type, "message": log_msg, "items": updated_items},
    })

    await save_campaign_async(session)
