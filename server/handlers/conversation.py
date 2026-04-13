"""
server/handlers/conversation.py — NPC Conversation Mode handlers.

Lightweight social scene support: DM opens a conversation with a named NPC
token; players can set their approach tone, perform social actions, and join
an optional speak queue.  All state is broadcast as conversation_state so
every client stays in sync.  Freeform chat is never blocked.
"""
import time

from server.session import Session, User
from server.handlers.common import manager

_VALID_TONES = {
    "polite", "hostile", "deceptive", "charming",
    "cautious", "sympathetic", "neutral",
}
_VALID_ACTIONS = {
    "persuade", "intimidate", "deceive", "charm",
    "insight", "appeal", "threaten", "flatter",
}


def _cm(session: Session) -> dict:
    """Return the live conversation_mode dict, or an empty sentinel."""
    return getattr(session, "conversation_mode", None) or {}


async def _broadcast_state(session: Session) -> None:
    cm = _cm(session)
    payload = dict(cm) if cm else {"active": False}
    await manager.broadcast(session.id, {
        "type": "conversation_state",
        "payload": payload,
    })


# ── Entry / Exit ──────────────────────────────────────────────────────────────

async def handle_conversation_enter(payload: dict, session: Session, user: User):
    """DM starts conversation mode for a named NPC token."""
    if user.role != "dm":
        return
    npc_id   = str(payload.get("npc_id")   or "").strip()[:64]
    npc_name = str(payload.get("npc_name") or "Unknown").strip()[:80] or "Unknown"

    session.conversation_mode = {
        "active":       True,
        "npc_id":       npc_id,
        "npc_name":     npc_name,
        "participants": {},     # user_id → {name, tone, joined_at}
        "speak_queue":  [],     # ordered list of user_ids waiting to speak
        "reaction_cue": "",     # optional DM hint visible to all
        "started_at":   time.time(),
    }
    entry = session.add_log(
        f"Conversation with {npc_name} has begun.",
        msg_type="system",
        user_name="Scene",
    )
    await manager.broadcast(session.id, {"type": "log_entry", "payload": entry})
    await _broadcast_state(session)


async def handle_conversation_exit(payload: dict, session: Session, user: User):
    """DM ends conversation mode."""
    if user.role != "dm":
        return
    npc_name = _cm(session).get("npc_name", "the NPC")
    session.conversation_mode = {"active": False}
    entry = session.add_log(
        f"Conversation with {npc_name} has ended.",
        msg_type="system",
        user_name="Scene",
    )
    await manager.broadcast(session.id, {"type": "log_entry", "payload": entry})
    await _broadcast_state(session)


# ── Tone ─────────────────────────────────────────────────────────────────────

async def handle_conversation_set_tone(payload: dict, session: Session, user: User):
    """Any participant sets their approach tone."""
    cm = _cm(session)
    if not cm.get("active"):
        return
    tone = str(payload.get("tone") or "neutral").strip().lower()[:32]
    if tone not in _VALID_TONES:
        tone = "neutral"
    participants = cm.setdefault("participants", {})
    existing = participants.get(user.id, {})
    participants[user.id] = {
        "name":      user.name,
        "tone":      tone,
        "joined_at": existing.get("joined_at", time.time()),
    }
    await _broadcast_state(session)


# ── Social Actions ────────────────────────────────────────────────────────────

async def handle_conversation_social_action(payload: dict, session: Session, user: User):
    """Player performs a named social action (persuade, intimidate, etc.)."""
    cm = _cm(session)
    if not cm.get("active"):
        return
    action = str(payload.get("action") or "").strip().lower()[:32]
    if action not in _VALID_ACTIONS:
        return
    npc_name = cm.get("npc_name", "the NPC")
    entry = session.add_log(
        f"{user.name} attempts to {action.capitalize()} {npc_name}.",
        msg_type="conversation_action",
        user_name=user.name,
    )
    entry["action"]   = action
    entry["npc_name"] = npc_name
    await manager.broadcast(session.id, {"type": "conversation_action_log", "payload": entry})
    await manager.broadcast(session.id, {"type": "log_entry",              "payload": entry})


# ── Speak Queue ───────────────────────────────────────────────────────────────

async def handle_conversation_queue_join(payload: dict, session: Session, user: User):
    """Player raises their hand to speak next."""
    cm = _cm(session)
    if not cm.get("active"):
        return
    queue = cm.setdefault("speak_queue", [])
    if user.id not in queue:
        queue.append(user.id)
        # auto-register as participant with neutral tone if not yet present
        participants = cm.setdefault("participants", {})
        if user.id not in participants:
            participants[user.id] = {
                "name":      user.name,
                "tone":      "neutral",
                "joined_at": time.time(),
            }
    await _broadcast_state(session)


async def handle_conversation_queue_leave(payload: dict, session: Session, user: User):
    """Player withdraws from the speak queue."""
    cm = _cm(session)
    if not cm.get("active"):
        return
    queue = cm.get("speak_queue", [])
    if user.id in queue:
        queue.remove(user.id)
    await _broadcast_state(session)


async def handle_conversation_queue_advance(payload: dict, session: Session, user: User):
    """DM grants the floor to the next player in queue."""
    if user.role != "dm":
        return
    cm = _cm(session)
    if not cm.get("active"):
        return
    queue = cm.get("speak_queue", [])
    if queue:
        next_uid = queue.pop(0)
        next_user = session.users.get(next_uid)
        if next_user:
            entry = session.add_log(
                f"The floor goes to {next_user.name}.",
                msg_type="system",
                user_name="Scene",
            )
            await manager.broadcast(session.id, {"type": "log_entry", "payload": entry})
    await _broadcast_state(session)


# ── NPC Reaction Cue (DM only) ────────────────────────────────────────────────

async def handle_conversation_reaction_set(payload: dict, session: Session, user: User):
    """DM sets a short NPC reaction hint visible to all players."""
    if user.role != "dm":
        return
    cm = _cm(session)
    if not cm.get("active"):
        return
    cue = str(payload.get("reaction_cue") or "").strip()[:120]
    cm["reaction_cue"] = cue
    await _broadcast_state(session)
