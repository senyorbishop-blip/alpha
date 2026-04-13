"""
server/handlers/tts_relay.py — WebSocket relay handlers for GPU TTS.

New message types added by the TTS system:

  tts_narration        (DM → server → all players)
    Carries pre-generated WAV as base64, relayed verbatim to every
    connected client so players can play it locally via AudioContext.

  tts_narration_stop   (DM → server → all players)
    Signals all clients to immediately stop any playing TTS audio.

  player_audio_ready   (player → server)
    Sent by a player after they click the audio-unlock overlay.
    Server records readiness and notifies the DM panel.

These handlers are intentionally additive — they do not touch the
existing narration_speak / narration_stop handlers.
"""

from __future__ import annotations

import logging

from server.session import Session, User
from server.handlers.common import manager

logger = logging.getLogger("tts_relay")

# Per-session set of player IDs whose AudioContext is unlocked.
# Stored in-process RAM only; reset on server restart (acceptable).
_audio_ready: dict[str, set[str]] = {}   # session_id → {user_id, ...}


def _mark_ready(session_id: str, user_id: str) -> None:
    _audio_ready.setdefault(session_id, set()).add(user_id)


def _is_ready(session_id: str, user_id: str) -> bool:
    return user_id in _audio_ready.get(session_id, set())


def _ready_set(session_id: str) -> set[str]:
    return _audio_ready.get(session_id, set())


# ---------------------------------------------------------------------------
# tts_narration — relay pre-generated audio from DM to all players
# ---------------------------------------------------------------------------

async def handle_tts_narration(payload: dict, session: Session, user: User) -> None:
    """
    Relay a TTS narration audio blob to all connected clients.

    Expected payload from DM client:
      {
        "audio_b64":    str,   # base64-encoded WAV
        "voice_preset": str,   # preset ID (for client-side display)
        "duration_ms":  int,   # total audio duration in ms
        "text":         str,   # optional: for overlay text reveal
        "mode":         str    # "replace" | "queue"
      }
    """
    if user.role != "dm":
        await manager.send_to(session.id, user.id, {
            "type":    "error",
            "payload": {"message": "Only the DM can broadcast TTS narration"},
        })
        return

    audio_b64    = payload.get("audio_b64", "")
    voice_preset = payload.get("voice_preset", "grand_narrator")
    duration_ms  = int(payload.get("duration_ms", 0))
    text         = payload.get("text", "")
    mode         = payload.get("mode", "replace")

    if not audio_b64:
        logger.warning("[TTS relay] tts_narration received with empty audio_b64")
        return

    logger.info(
        f"[TTS relay] broadcasting tts_narration  preset={voice_preset}  "
        f"duration_ms={duration_ms}  text_chars={len(text)}  mode={mode}"
    )

    broadcast_payload = {
        "type": "tts_narration",
        "payload": {
            "audio_b64":    audio_b64,
            "voice_preset": voice_preset,
            "duration_ms":  duration_ms,
            "text":         text,
            "mode":         mode,
        },
    }

    # Broadcast to all clients (DM receives their own copy for confirmation)
    await manager.broadcast(session.id, broadcast_payload)


# ---------------------------------------------------------------------------
# tts_narration_stop — relay stop signal to all players
# ---------------------------------------------------------------------------

async def handle_tts_narration_stop(payload: dict, session: Session, user: User) -> None:
    """Broadcast a stop signal so all clients halt TTS playback immediately."""
    if user.role != "dm":
        return
    logger.info("[TTS relay] broadcasting tts_narration_stop")
    await manager.broadcast(session.id, {
        "type": "tts_narration_stop",
        "payload": {},
    })


# ---------------------------------------------------------------------------
# player_audio_ready — player confirms AudioContext is unlocked
# ---------------------------------------------------------------------------

async def handle_player_audio_ready(payload: dict, session: Session, user: User) -> None:
    """
    Record that this player's AudioContext is now unlocked.
    Notify the DM so the panel indicator updates.
    """
    _mark_ready(session.id, user.id)
    display_name = getattr(user, "display_name", None) or user.id
    logger.info(f"[TTS relay] player audio ready: {display_name} ({user.id})")

    # Tell the DM which players are audio-ready (send directly to DM user)
    dm_id = getattr(session, "dm_id", None)
    if dm_id:
        await manager.send_to(session.id, dm_id, {
            "type": "player_audio_ready",
            "payload": {
                "user_id":      user.id,
                "display_name": display_name,
                "ready":        True,
            },
        })
