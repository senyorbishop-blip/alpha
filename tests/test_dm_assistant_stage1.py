import asyncio

from server.assistant import service as assistant_service
from server.integrations import service as integrations_service



def test_integrations_status_payload_matches_response_shape():
    payload = integrations_service.get_integrations_status_payload()
    assert "narration" in payload
    assert "cartographer" in payload
    assert "effective_provider" in payload["narration"]
    assert "image_provider" in payload["cartographer"]



def test_assistant_status_payload_has_expected_tools(monkeypatch):
    monkeypatch.setattr(
        assistant_service,
        "get_integrations_status_payload",
        lambda: {
            "narration": {
                "gemini_tts_configured": False,
                "elevenlabs_configured": True,
                "openai_tts_configured": False,
                "effective_provider": "elevenlabs",
            },
            "cartographer": {
                "image_provider": "openai",
                "openai_configured": True,
                "replicate_configured": False,
                "stability_configured": False,
                "stability_deprecated": True,
                "anthropic_configured": True,
            },
        },
    )
    payload = assistant_service.assistant_status_payload()
    assistant = payload["assistant"]
    assert assistant["name"] == "DM Assistant"
    keys = {tool["key"] for tool in assistant["tools"]}
    assert keys == {
        "generate_map",
        "describe_scene",
        "suggest_ambience",
        "ask_rules",
        "draft_npc_line",
        "suggest_encounter",
        "suggest_loot",
        "draft_session_recap",
    }
    ask_rules = next(tool for tool in assistant["tools"] if tool["key"] == "ask_rules")
    assert ask_rules["available"] is True



def test_suggest_ambience_payload_prefers_dungeon_for_underground_scene():
    payload = assistant_service.suggest_ambience_payload(
        {"terrain_type": "crypt", "scene": "exploration", "current_track": "silence"}
    )
    assert payload["ok"] is True
    assert payload["content"]["recommended_track"] == "dungeon"
    assert payload["provider"]["primary"] == "heuristic"



def test_suggest_encounter_payload_returns_enemy_groups():
    payload = assistant_service.suggest_encounter_payload(
        {"terrain_type": "forest", "party_level": 5, "party_size": 4, "difficulty": "hard", "objective": "protect the caravan"}
    )
    assert payload["ok"] is True
    assert payload["content"]["enemy_groups"]
    assert payload["provider"]["primary"] == "heuristic"



def test_suggest_loot_payload_uses_loot_preview(monkeypatch):
    monkeypatch.setattr(
        assistant_service,
        "generate_loot_preview",
        lambda dungeon_level: {"dungeon_level": dungeon_level, "gold": 42, "items": [{"id": "gem", "name": "Moon Gem"}]},
    )
    payload = assistant_service.suggest_loot_payload({"dungeon_level": 7})
    assert payload["ok"] is True
    assert payload["content"]["gold"] == 42
    assert payload["provider"]["primary"] == "loot_tables"



def test_assistant_action_payload_rules_success(monkeypatch):
    async def _fake_rules_answer(*, question: str):
        return {
            "ok": True,
            "text": f"Rule answer for: {question}",
            "error": None,
            "provider": {"provider": "anthropic", "fallback_used": False, "fallback_reason": None},
        }

    monkeypatch.setattr(assistant_service, "generate_rules_answer", _fake_rules_answer)
    payload = asyncio.run(assistant_service.assistant_action_payload({"action": "ask_rules", "question": "What triggers an OA?"}))
    assert payload["ok"] is True
    assert payload["action"] == "ask_rules"
    assert payload["direct_passthrough"]["message_type"] == "ai_rules_oracle"



def test_assistant_action_response_rules_provider_failure(monkeypatch):
    async def _fake_rules_answer(*, question: str):
        return {
            "ok": False,
            "text": None,
            "error": "Rules help is unavailable right now.",
            "provider": {"provider": "anthropic", "fallback_used": False, "fallback_reason": "anthropic_unavailable"},
        }

    monkeypatch.setattr(assistant_service, "generate_rules_answer", _fake_rules_answer)
    response = asyncio.run(assistant_service.assistant_action_response({"action": "ask_rules", "question": "Test?"}))
    assert response.status_code == 503
    assert b'"ok":false' in response.body
    assert b'"fallback_reason":"anthropic_unavailable"' in response.body



def test_assistant_action_payload_generate_map(monkeypatch):
    async def _fake_generate_map(request_data):
        return {
            "result_id": "map-123",
            "plan": {"title": "Ruined Keep", "summary": "A compact ruined keep."},
            "image": {"provider": "openai", "url": "/static/maps/keep.png", "stub": False},
            "editor_import": {"grid_type": "square"},
        }

    monkeypatch.setattr(assistant_service, "generate_map", _fake_generate_map)
    payload = asyncio.run(
        assistant_service.assistant_action_payload(
            {"action": "generate_map", "description": "ruined keep", "map_scope": "interior"}
        )
    )
    assert payload["ok"] is True
    assert payload["content"]["result_id"] == "map-123"
    assert payload["provider"]["primary"] == "openai"



def test_assistant_action_payload_session_recap(monkeypatch):
    async def _fake_recap(*, notes: str, style: str = "dramatic"):
        return {
            "ok": True,
            "text": f"Recap ({style}): {notes}",
            "error": None,
            "provider": {"provider": "anthropic", "fallback_used": False, "fallback_reason": None},
        }

    monkeypatch.setattr(assistant_service, "generate_session_recap", _fake_recap)
    payload = asyncio.run(
        assistant_service.assistant_action_payload(
            {"action": "draft_session_recap", "notes": "We crossed the marsh.", "style": "heroic"}
        )
    )
    assert payload["ok"] is True
    assert payload["action"] == "draft_session_recap"
    assert payload["content"]["style"] == "heroic"
