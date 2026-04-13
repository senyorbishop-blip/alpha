"""
server/handlers/sound.py — Ambient sound engine WS handlers.

DM-only commands that broadcast sound control messages to all connected clients.
"""
from server.handlers.common import Session, User, manager, _safe_float
from server.db import save_campaign_async

_VALID_TRACKS = {"silence", "tavern", "dungeon", "forest", "battle"}
_VALID_SFX = {
    "sword_clash", "fireball", "door_creak", "thunder",
    "heal_chime", "trap_click", "crowd_gasp",
}


async def handle_sound_set_ambient(payload: dict, session: Session, user: User):
    """DM sets the ambient track for all players."""
    if user.role != "dm":
        return
    track = str(payload.get("track") or "silence").strip().lower()
    if track not in _VALID_TRACKS:
        track = "silence"
    volume = _safe_float(payload.get("volume", 0.7), 0.7, minimum=0.0, maximum=1.0)
    fade_ms = int(max(0, min(5000, int(payload.get("fade_ms", 1500) or 1500))))

    sound_state = getattr(session, "sound_state", None) or {}
    sound_state["track"] = track
    sound_state["volume"] = volume
    sound_state["fade_ms"] = fade_ms
    session.sound_state = sound_state

    # exclude_user: DM plays locally via AudioManager so no echo needed
    await manager.broadcast(session.id, {
        "type": "sound_set_ambient",
        "payload": {"track": track, "volume": volume, "fade_ms": fade_ms},
    }, exclude_user=user.id)
    await save_campaign_async(session)


async def handle_sound_play_sfx(payload: dict, session: Session, user: User):
    """DM triggers a one-shot SFX for all players."""
    if user.role != "dm":
        return
    sfx_id = str(payload.get("sfx_id") or "").strip().lower()
    if sfx_id not in _VALID_SFX:
        return
    volume = _safe_float(payload.get("volume", 1.0), 1.0, minimum=0.0, maximum=1.0)

    # exclude_user: DM plays locally via AudioManager so no echo needed
    await manager.broadcast(session.id, {
        "type": "sound_play_sfx",
        "payload": {"sfx_id": sfx_id, "volume": volume},
    }, exclude_user=user.id)


async def handle_sound_stop_all(payload: dict, session: Session, user: User):
    """DM stops all audio for all players."""
    if user.role != "dm":
        return
    sound_state = getattr(session, "sound_state", None) or {}
    sound_state["track"] = "silence"
    sound_state["volume"] = 0.7
    sound_state["fade_ms"] = 800
    session.sound_state = sound_state

    # exclude_user: DM stops locally via AudioManager so no echo needed
    await manager.broadcast(session.id, {
        "type": "sound_stop_all",
        "payload": {},
    }, exclude_user=user.id)
    await save_campaign_async(session)
