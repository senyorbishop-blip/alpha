from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from server.handlers.ai_dm import (
    generate_npc_dialogue,
    generate_rules_answer,
    generate_scene_description,
    generate_session_recap,
)
from server.handlers.cartographer import generate_map
from server.handlers.inventory import generate_loot_preview
from server.integrations.service import get_integrations_status_payload


_ALLOWED_MAP_MODES = {"illustrated_overview", "tactical_grid", "hybrid"}
_ALLOWED_MAP_SCOPES = {"world", "region", "local_area", "settlement", "interior"}
_ALLOWED_GRID_TYPES = {"none", "square", "hex"}



def _tool_catalog(status: dict) -> list[dict[str, Any]]:
    cartographer = status.get("cartographer", {})
    narration = status.get("narration", {})
    image_provider = str(cartographer.get("image_provider") or "stub")
    anthropic_ready = bool(cartographer.get("anthropic_configured"))
    narration_ready = bool(
        narration.get("gemini_tts_configured")
        or narration.get("elevenlabs_configured")
        or narration.get("openai_tts_configured")
    )
    return [
        {
            "key": "generate_map",
            "label": "Generate map",
            "transport": "http",
            "available": image_provider != "stub",
            "provider_summary": {
                "image_provider": image_provider,
                "planning_provider": "anthropic" if anthropic_ready else "unconfigured",
            },
            "direct_access": {"kind": "panel", "target": "map_studio"},
            "fallback_note": "Map generation stays in stub mode until a real image provider is configured." if image_provider == "stub" else None,
        },
        {
            "key": "describe_scene",
            "label": "Describe scene",
            "transport": "http",
            "available": anthropic_ready,
            "provider_summary": {"primary": "anthropic"},
            "direct_access": {"kind": "toggle", "target": "ai-auto-narrate-toggle"},
            "fallback_note": "Scene description help requires Anthropic configuration." if not anthropic_ready else None,
        },
        {
            "key": "suggest_ambience",
            "label": "Suggest ambience",
            "transport": "http",
            "available": True,
            "provider_summary": {"primary": "heuristic"},
            "direct_access": {"kind": "panel", "target": "flyout-sound"},
            "fallback_note": None,
        },
        {
            "key": "ask_rules",
            "label": "Ask rules",
            "transport": "http",
            "available": anthropic_ready,
            "provider_summary": {"primary": "anthropic"},
            "direct_access": {"kind": "chat_hint", "target": "chat-input"},
            "fallback_note": "Rules help requires Anthropic configuration." if not anthropic_ready else None,
        },
        {
            "key": "draft_npc_line",
            "label": "Draft NPC line",
            "transport": "http",
            "available": anthropic_ready and narration_ready,
            "provider_summary": {
                "primary": "anthropic",
                "narration_provider": narration.get("effective_provider", "browser_fallback"),
            },
            "direct_access": {"kind": "context_action", "target": "ctx-npc-speak"},
            "fallback_note": "NPC speech drafting requires Anthropic; voice playback still uses the existing narration stack." if not anthropic_ready else None,
        },
        {
            "key": "suggest_encounter",
            "label": "Suggest encounter",
            "transport": "http",
            "available": True,
            "provider_summary": {"primary": "heuristic"},
            "direct_access": {"kind": "workspace", "target": "encounter_templates"},
            "fallback_note": None,
        },
        {
            "key": "suggest_loot",
            "label": "Suggest loot",
            "transport": "http",
            "available": True,
            "provider_summary": {"primary": "loot_tables"},
            "direct_access": {"kind": "workspace", "target": "party_loot_log"},
            "fallback_note": None,
        },
        {
            "key": "draft_session_recap",
            "label": "Draft session recap",
            "transport": "http",
            "available": anthropic_ready,
            "provider_summary": {"primary": "anthropic"},
            "direct_access": {"kind": "workspace", "target": "journal_entries"},
            "fallback_note": "Session recap drafting requires Anthropic configuration." if not anthropic_ready else None,
        },
    ]



def assistant_status_payload() -> dict:
    status = get_integrations_status_payload()
    return {
        "assistant": {
            "name": "DM Assistant",
            "identity": "dm_assistant",
            "entry_enabled": True,
            "tools": _tool_catalog(status),
            "providers": {
                "narration": status.get("narration", {}),
                "cartographer": status.get("cartographer", {}),
            },
            "notes": [
                "This is a Stage 1 unification layer over existing tools.",
                "Direct feature access remains available while the assistant surface matures.",
            ],
        }
    }



def assistant_status_response() -> JSONResponse:
    return JSONResponse(assistant_status_payload())



def _error_response(action: str, message: str, *, provider: dict | None = None, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        {
            "ok": False,
            "action": action,
            "error": message,
            "provider": provider or None,
        },
        status_code=status_code,
    )



def _sanitize_map_request(body: dict) -> dict:
    return {
        "description": str(body.get("description") or "")[:800],
        "map_scope": body.get("map_scope", "interior") if body.get("map_scope") in _ALLOWED_MAP_SCOPES else "interior",
        "output_mode": body.get("output_mode", "illustrated_overview") if body.get("output_mode") in _ALLOWED_MAP_MODES else "illustrated_overview",
        "terrain_preset": str(body.get("terrain_preset") or "")[:64],
        "build_preset": str(body.get("build_preset") or "")[:64],
        "interior_preset": str(body.get("interior_preset") or "")[:64],
        "image_style": str(body.get("image_style") or "atlas")[:32],
        "grid_type": body.get("grid_type", "square") if body.get("grid_type") in _ALLOWED_GRID_TYPES else "square",
        "grid_scale": str(body.get("grid_scale") or "5ft")[:16],
        "dimensions_preset": str(body.get("dimensions_preset") or "medium")[:16],
        "grid_width": int(body["grid_width"]) if body.get("grid_width") else None,
        "grid_height": int(body["grid_height"]) if body.get("grid_height") else None,
        "pixel_export_size": min(4096, max(512, int(body.get("pixel_export_size") or 2048))),
        "detail_density": str(body.get("detail_density") or "medium")[:16],
        "poi_density": str(body.get("poi_density") or "medium")[:16],
    }





def suggest_encounter_payload(body: dict) -> dict:
    terrain = str(body.get("terrain_type") or body.get("terrain") or "wilderness").strip().lower() or "wilderness"
    objective = str(body.get("objective") or "hold the line").strip() or "hold the line"
    difficulty = str(body.get("difficulty") or "medium").strip().lower() or "medium"
    level = max(1, min(20, int(body.get("party_level") or 5)))
    party_size = max(1, min(8, int(body.get("party_size") or 4)))

    families = {
        "forest": ["bandit scouts", "wolf pack", "blighted treants"],
        "crypt": ["skeleton honor guard", "restless spirits", "ghoul scavengers"],
        "dungeon": ["cult enforcers", "ooze ambushers", "hobgoblin patrol"],
        "coastal": ["sahuagin raiders", "smuggler crew", "harpy flock"],
        "tavern": ["brawling mercenaries", "spy ring agents", "thieves' guild collectors"],
    }
    pool = next((choices for key, choices in families.items() if key in terrain), ["bandit skirmishers", "animated hazards", "cult fanatics"])
    suggested = pool[:2] if difficulty == "easy" else pool[:3]
    pacing = {
        "easy": "fast pressure with an obvious way out",
        "medium": "sustained pressure with one tactical twist",
        "hard": "multi-angle pressure with a reinforcement or hazard beat",
        "deadly": "overwhelming pressure that should telegraph risk before commitment",
    }.get(difficulty, "sustained pressure with one tactical twist")
    return {
        "ok": True,
        "action": "suggest_encounter",
        "title": "Encounter suggestion",
        "summary": f"Level {level} {difficulty} encounter seed for {party_size} adventurers.",
        "content": {
            "terrain_type": terrain,
            "objective": objective,
            "party_level": level,
            "party_size": party_size,
            "difficulty": difficulty,
            "enemy_groups": suggested,
            "pacing": pacing,
            "set_piece": f"Use the environment to support the objective: {objective}.",
        },
        "provider": {
            "primary": "heuristic",
            "fallback_used": False,
            "fallback_reason": None,
        },
        "direct_passthrough": {
            "kind": "workspace",
            "target": "encounter_templates",
        },
    }


def suggest_loot_payload(body: dict) -> dict:
    dungeon_level = max(1, min(20, int(body.get("dungeon_level") or body.get("party_level") or 5)))
    preview = generate_loot_preview(dungeon_level)
    return {
        "ok": True,
        "action": "suggest_loot",
        "title": "Loot suggestion",
        "summary": f"Suggested loot for dungeon level {preview['dungeon_level']}: {preview['gold']} gp and {len(preview['items'])} item(s).",
        "content": preview,
        "provider": {
            "primary": "loot_tables",
            "fallback_used": False,
            "fallback_reason": None,
        },
        "direct_passthrough": {
            "kind": "workspace",
            "target": "party_loot_log",
        },
    }

def suggest_ambience_payload(body: dict) -> dict:
    terrain = str(body.get("terrain_type") or body.get("terrain") or "").strip().lower()
    weather = str(body.get("weather") or "").strip().lower()
    scene = str(body.get("scene") or "").strip().lower()
    current_track = str(body.get("current_track") or "silence").strip().lower() or "silence"

    recommended = "tavern"
    reason_bits: list[str] = []
    sfx: list[str] = []

    if any(key in terrain for key in ("forest", "swamp", "wild", "wood")):
        recommended = "forest"
        reason_bits.append("terrain reads as wilderness/forest")
        sfx.extend(["door", "thunder"] if weather in {"stormy", "rain"} else ["gasp"])
    elif any(key in terrain for key in ("dungeon", "crypt", "cave", "underdark", "sewer")):
        recommended = "dungeon"
        reason_bits.append("terrain reads as underground or ruin exploration")
        sfx.extend(["door", "trap"])
    elif any(key in terrain for key in ("battle", "war", "fortress")) or "combat" in scene:
        recommended = "battle"
        reason_bits.append("scene suggests active combat pressure")
        sfx.extend(["clash", "fireball"])
    elif any(key in terrain for key in ("tavern", "inn", "town", "market", "harbor")):
        recommended = "tavern"
        reason_bits.append("terrain reads as social/settlement space")
        sfx.extend(["door", "gasp"])

    if weather in {"stormy", "rain"} and recommended != "battle":
        reason_bits.append("weather suggests a heavier atmosphere")
    if current_track == recommended:
        reason_bits.append("current track already matches the scene well")

    return {
        "ok": True,
        "action": "suggest_ambience",
        "title": "Ambience suggestion",
        "summary": f"Recommended ambient track: {recommended}.",
        "content": {
            "recommended_track": recommended,
            "current_track": current_track,
            "suggested_sfx": sfx[:3],
            "reasoning": reason_bits or ["default social/exploration ambience recommendation"],
        },
        "provider": {
            "primary": "heuristic",
            "fallback_used": False,
            "fallback_reason": None,
        },
        "direct_passthrough": {
            "kind": "ui",
            "target": "flyout-sound",
            "action": "dmSoundSetTrack",
        },
    }


async def assistant_action_payload(body: dict) -> dict:
    action = str(body.get("action") or "").strip()
    if not action:
        raise ValueError("action is required")

    if action == "ask_rules":
        result = await generate_rules_answer(question=str(body.get("question") or ""))
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Rules help is unavailable.")
        return {
            "ok": True,
            "action": action,
            "title": "Rules answer",
            "summary": result["text"],
            "content": {"text": result["text"], "question": str(body.get("question") or "")},
            "provider": result["provider"],
            "direct_passthrough": {"kind": "ws", "message_type": "ai_rules_oracle"},
        }

    if action == "draft_npc_line":
        result = await generate_npc_dialogue(
            token_name=str(body.get("token_name") or "NPC"),
            token_notes=str(body.get("token_notes") or ""),
            player_message=str(body.get("player_message") or ""),
            campaign_tone=str(body.get("campaign_tone") or "heroic"),
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "NPC speech assistant is unavailable.")
        return {
            "ok": True,
            "action": action,
            "title": "NPC line draft",
            "summary": result["text"],
            "content": {"text": result["text"], "token_name": str(body.get("token_name") or "NPC")},
            "provider": result["provider"],
            "direct_passthrough": {"kind": "ws", "message_type": "ai_npc_speak"},
        }

    if action == "describe_scene":
        props = body.get("revealed_props") or []
        if not isinstance(props, list):
            props = []
        result = await generate_scene_description(
            terrain_type=str(body.get("terrain_type") or "dungeon"),
            revealed_props=props,
            region_label=str(body.get("region_label") or ""),
            campaign_tone=str(body.get("campaign_tone") or "heroic"),
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Scene description help is unavailable.")
        return {
            "ok": True,
            "action": action,
            "title": "Scene description",
            "summary": result["text"],
            "content": {"text": result["text"], "terrain_type": str(body.get("terrain_type") or "dungeon")},
            "provider": result["provider"],
            "direct_passthrough": {"kind": "ws", "message_type": "ai_describe_scene"},
        }

    if action == "suggest_ambience":
        return suggest_ambience_payload(body)

    if action == "suggest_encounter":
        return suggest_encounter_payload(body)

    if action == "suggest_loot":
        return suggest_loot_payload(body)

    if action == "draft_session_recap":
        result = await generate_session_recap(notes=str(body.get("notes") or ""), style=str(body.get("style") or "dramatic"))
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Session recap drafting is unavailable.")
        return {
            "ok": True,
            "action": action,
            "title": "Session recap draft",
            "summary": result["text"].splitlines()[0][:220],
            "content": {"text": result["text"], "style": str(body.get("style") or "dramatic")},
            "provider": result["provider"],
            "direct_passthrough": {"kind": "workspace", "target": "journal_entries"},
        }

    if action == "generate_map":
        request_data = _sanitize_map_request(body)
        result = await generate_map(request_data)
        image = result.get("image") or {}
        plan = result.get("plan") or {}
        return {
            "ok": True,
            "action": action,
            "title": str(plan.get("title") or body.get("title") or "Generated map"),
            "summary": str(plan.get("summary") or "Map generation completed."),
            "content": {
                "result_id": result.get("result_id"),
                "image": image,
                "plan": plan,
                "editor_import": result.get("editor_import") or {},
            },
            "provider": {
                "primary": image.get("provider") or "stub",
                "planning_provider": "anthropic",
                "fallback_used": bool(image.get("stub", False)),
                "fallback_reason": "image_provider_stub" if image.get("stub", False) else None,
            },
            "direct_passthrough": {"kind": "http", "endpoint": "/api/cartographer/generate"},
        }

    raise ValueError(f"Unsupported assistant action: {action}")


async def assistant_action_response(body: dict) -> JSONResponse:
    action = str(body.get("action") or "").strip()
    try:
        payload = await assistant_action_payload(body)
        return JSONResponse(payload)
    except ValueError as exc:
        return _error_response(action or "unknown", str(exc), status_code=400)
    except RuntimeError as exc:
        provider = None
        if action in {"ask_rules", "draft_npc_line", "describe_scene", "draft_session_recap"}:
            provider = {"primary": "anthropic", "fallback_used": False, "fallback_reason": "anthropic_unavailable"}
        return _error_response(action or "unknown", str(exc), provider=provider, status_code=503)
    except Exception as exc:
        return _error_response(action or "unknown", f"Assistant action failed: {exc}", status_code=500)
