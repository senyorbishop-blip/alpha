"""server/handlers/ai_dm.py — AI Dungeon Master handlers.

Three async handlers that use Claude to generate in-character NPC dialogue,
answer D&D 5e rules questions, and describe fog-revealed scenes.

All Claude calls use direct HTTP (httpx) — no SDK dependency required.
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

from server.handlers.ai_rate_limit import AiGateResult, check_ai_gate
from server.handlers.common import Session, User, manager
from server.handlers.narration import handle_narration_speak

logger = logging.getLogger(__name__)

_CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
_CLAUDE_MODEL = "claude-sonnet-4-5"
_AI_DM_TIMEOUT = 15.0


def _get_anthropic_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def ai_dm_provider_state() -> dict:
    configured = bool(_get_anthropic_key())
    return {
        "provider": "anthropic",
        "model": _CLAUDE_MODEL,
        "configured": configured,
        "fallback_used": False,
        "fallback_reason": None if configured else "anthropic_key_missing",
    }


async def _send_ai_status(session: Session, user: User, action: str, gate: AiGateResult) -> None:
    """Send a typed AI status response to the requester only."""
    payload = {
        "kind": gate.kind,
        "action": action,
        "message": gate.message,
        "retry_after_seconds": gate.retry_after_seconds,
    }
    await manager.send_to(session.id, user.id, {"type": "ai_status", "payload": payload})


async def _guard_ai_request(session: Session, user: User, action: str) -> bool:
    gate = check_ai_gate(session, user, action)
    if gate.allowed:
        return True
    await _send_ai_status(session, user, action, gate)
    logger.info(
        "[AI DM] blocked request",
        extra={
            "action": action,
            "kind": gate.kind,
            "session_id": getattr(session, "id", None),
            "user_id": getattr(user, "id", None),
            "user_role": getattr(user, "role", None),
        },
    )
    return False


async def _call_claude(
    system: str,
    user_msg: str,
    timeout: float = _AI_DM_TIMEOUT,
    max_tokens: int = 256,
) -> str | None:
    """Call Claude and return the text response, or None on failure."""
    api_key = _get_anthropic_key()
    if not api_key:
        logger.warning("[AI DM] ANTHROPIC_API_KEY not set — skipping Claude call")
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                _CLAUDE_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": _CLAUDE_MODEL,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            )
        if r.status_code != 200:
            logger.error(
                "[AI DM] Claude API error %d: %.300s%s",
                r.status_code,
                r.text,
                "…" if len(r.text) > 300 else "",
            )
            return None
        content = r.json().get("content", [])
        return "".join(
            block.get("text", "") for block in content if block.get("type") == "text"
        ).strip()
    except asyncio.TimeoutError:
        logger.warning("[AI DM] Claude request timed out after %.0fs", timeout)
        return None
    except Exception as exc:
        logger.error("[AI DM] Claude request failed: %s", exc)
        return None


async def generate_npc_dialogue(
    *,
    token_name: str,
    token_notes: str = "",
    player_message: str = "",
    campaign_tone: str = "heroic",
) -> dict:
    token_name = str(token_name or "Someone").strip() or "Someone"
    token_notes = str(token_notes or "").strip()
    player_message = str(player_message or "").strip()
    campaign_tone = str(campaign_tone or "heroic").strip() or "heroic"

    system_prompt = (
        f"You are {token_name}, a character in a D&D 5e campaign. "
        f"Tone: {campaign_tone}. "
        f"Notes: {token_notes}. "
        "Stay in character. Max 2-3 sentences. No stage directions."
    )
    dialogue = await _call_claude(system_prompt, player_message or "Speak briefly.", timeout=_AI_DM_TIMEOUT)
    provider = ai_dm_provider_state()
    if not dialogue:
        provider["fallback_reason"] = provider.get("fallback_reason") or "anthropic_unavailable"
        return {
            "ok": False,
            "text": None,
            "error": "NPC speech assistant is unavailable right now.",
            "provider": provider,
        }
    provider["fallback_reason"] = None
    return {"ok": True, "text": dialogue, "error": None, "provider": provider}


async def generate_rules_answer(*, question: str) -> dict:
    question = str(question or "").strip()
    if not question:
        return {
            "ok": False,
            "text": None,
            "error": "A rules question is required.",
            "provider": ai_dm_provider_state(),
        }
    system_prompt = (
        "You are a precise D&D 5e rules expert. "
        "Answer in max 3 sentences. "
        "State the rule, source (PHB/DMG/MM/SRD), and one practical example. "
        "If unclear, say so."
    )
    answer = await _call_claude(system_prompt, question, timeout=20.0, max_tokens=300)
    provider = ai_dm_provider_state()
    if not answer:
        provider["fallback_reason"] = provider.get("fallback_reason") or "anthropic_unavailable"
        return {
            "ok": False,
            "text": None,
            "error": "Rules help is unavailable right now.",
            "provider": provider,
        }
    provider["fallback_reason"] = None
    return {"ok": True, "text": answer, "error": None, "provider": provider}


async def generate_scene_description(
    *,
    terrain_type: str = "dungeon",
    revealed_props: list[str] | None = None,
    region_label: str = "",
    campaign_tone: str = "heroic",
) -> dict:
    props = [str(p).strip() for p in (revealed_props or []) if str(p).strip()]
    terrain_type = str(terrain_type or "dungeon").strip() or "dungeon"
    region_label = str(region_label or "").strip()
    campaign_tone = str(campaign_tone or "heroic").strip() or "heroic"
    props_text = ", ".join(props[:10]) if props else "none"
    system_prompt = (
        "You are a dramatic D&D narrator. "
        "2 vivid sentences describing this scene. "
        f"Terrain: {terrain_type}. "
        f"Notable: {props_text}. "
        f"Tone: {campaign_tone}. "
        "Do NOT start with 'You see'."
    )
    user_msg = f"Describe the scene{' in ' + region_label if region_label else ''}."
    description = await _call_claude(system_prompt, user_msg, timeout=20.0)
    provider = ai_dm_provider_state()
    if not description:
        provider["fallback_reason"] = provider.get("fallback_reason") or "anthropic_unavailable"
        return {
            "ok": False,
            "text": None,
            "error": "Scene description help is unavailable right now.",
            "provider": provider,
        }
    return {"ok": True, "text": description, "error": None, "provider": provider}


async def generate_session_recap(*, notes: str, style: str = "dramatic") -> dict:
    notes = str(notes or "").strip()
    style = str(style or "dramatic").strip() or "dramatic"
    if not notes:
        return {
            "ok": False,
            "text": None,
            "error": "Recap notes are required.",
            "provider": ai_dm_provider_state(),
        }
    system_prompt = (
        "You are a D&D campaign chronicler. "
        f"Write a concise {style} session recap in 1 short paragraph followed by 3 bullet highlights. "
        "Preserve named NPCs, locations, and unresolved hooks."
    )
    recap = await _call_claude(system_prompt, notes, timeout=20.0, max_tokens=350)
    provider = ai_dm_provider_state()
    if not recap:
        provider["fallback_reason"] = provider.get("fallback_reason") or "anthropic_unavailable"
        return {
            "ok": False,
            "text": None,
            "error": "Session recap drafting is unavailable right now.",
            "provider": provider,
        }
    provider["fallback_reason"] = None
    return {"ok": True, "text": recap, "error": None, "provider": provider}


async def handle_ai_npc_speak(payload: dict, session: Session, user: User) -> None:
    """Generate in-character NPC dialogue and broadcast as TTS + speech bubble.

    Default role policy: DM/assistant-DM only. Override with
    AI_DM_NPC_SPEAK_ALLOWED_ROLES for controlled self-host deployments.
    """
    if not await _guard_ai_request(session, user, "ai_npc_speak"):
        return

    token_id = str(payload.get("token_id", "")).strip()
    token_name = str(payload.get("token_name", "Someone")).strip() or "Someone"
    voice_preset = str(payload.get("voice_preset", "deep_narrator")).strip()

    result = await generate_npc_dialogue(
        token_name=token_name,
        token_notes=str(payload.get("token_notes", "")).strip(),
        player_message=str(payload.get("player_message", "")).strip(),
        campaign_tone=str(payload.get("campaign_tone", "heroic")).strip(),
    )
    dialogue = result.get("text")
    if not dialogue:
        await manager.broadcast(session.id, {
            "type": "chat_message",
            "payload": {
                "message": f"The {token_name} says nothing.",
                "user": "System",
                "role": "system",
            },
        })
        return

    await manager.broadcast(session.id, {
        "type": "narration_speak",
        "payload": {
            "text": dialogue,
            "voice_preset": voice_preset,
            "policy": "replace_current",
        },
    })
    await manager.broadcast(session.id, {
        "type": "npc_speaks",
        "payload": {
            "token_id": token_id,
            "token_name": token_name,
            "dialogue": dialogue,
        },
    })


async def handle_ai_rules_oracle(payload: dict, session: Session, user: User) -> None:
    """Answer a D&D 5e rules question and broadcast as a chat message."""
    question = str(payload.get("question", "")).strip()
    asker_name = str(payload.get("asker_name", "Someone")).strip() or "Someone"
    if not question:
        return
    if not await _guard_ai_request(session, user, "ai_rules_oracle"):
        return

    result = await generate_rules_answer(question=question)
    answer = result.get("text") or "The oracle is silent — the answer could not be retrieved."
    await manager.broadcast(session.id, {
        "type": "rules_oracle",
        "payload": {
            "question": question,
            "answer": answer,
            "asker_name": asker_name,
        },
    })


async def handle_ai_describe_scene(payload: dict, session: Session, user: User) -> None:
    """DM only: generate a vivid scene description and broadcast as TTS + overlay."""
    if not await _guard_ai_request(session, user, "ai_describe_scene"):
        return

    revealed_props = payload.get("revealed_props", [])
    if not isinstance(revealed_props, list):
        revealed_props = []

    result = await generate_scene_description(
        terrain_type=str(payload.get("terrain_type", "dungeon")).strip(),
        revealed_props=revealed_props,
        region_label=str(payload.get("region_label", "")).strip(),
        campaign_tone=str(payload.get("campaign_tone", "heroic")).strip(),
    )
    description = result.get("text")
    if not description:
        return

    await handle_narration_speak(
        {"text": description, "voice_preset": "deep_narrator", "policy": "replace_current"},
        session,
        user,
    )
    await manager.broadcast(session.id, {
        "type": "scene_description",
        "payload": {
            "description": description,
            "terrain_type": str(payload.get("terrain_type", "dungeon")).strip() or "dungeon",
        },
    })
