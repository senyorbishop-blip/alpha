# DM Assistant Stage 0 Plan

## Purpose

Stage 0 establishes the runtime ownership model and the first-pass contract for a unified DM Assistant without replacing existing AI-adjacent features.

The goal is to make later implementation work safer by documenting:

- which files are authoritative at runtime,
- which AI-related entry points already exist,
- which legacy/duplicate paths must remain during migration,
- and the thin assistant contract that Stage 1 should introduce.

## Runtime ownership for DM Assistant work

### Server authority

- `main.py` remains the HTTP/WebSocket entrypoint and route registration authority.
- `server/handlers/__init__.py` remains the live WebSocket dispatch authority.
- Existing AI behavior is split across:
  - `server/handlers/cartographer.py` for map generation pipeline,
  - `server/handlers/narration.py` for TTS narration generation/broadcast,
  - `server/handlers/ai_dm.py` for rules/NPC/scene helper flows,
  - `server/integrations/service.py` for provider readiness/status reporting.

### Client authority

- `client/templates/play.html` remains the live gameplay SPA and DM UI glue.
- `client/static/js/cartographer.js` remains the active Map Studio controller.
- `client/static/js/ui/narration.js` remains the active narration playback/presentation engine.
- Existing DM Assistant work should be layered into the live `play.html` runtime first, not built primarily in dormant refactor modules.

## Existing AI-adjacent entry points to preserve during migration

### Preserve as direct-access paths

These should keep working while the assistant layer matures:

- Map Studio / Cartographer flyout
- Narration controls in the sound panel
- Rules oracle chat shortcut
- NPC speech context action/modal
- Auto-describe fog reveal toggle

### Preserve as backend contracts

These routes/messages should remain valid during early assistant work:

- `POST /api/cartographer/generate`
- `POST /api/cartographer/generate-interior`
- `POST /api/narrate`
- `GET /api/integrations/status`
- WebSocket message types:
  - `narration_speak`
  - `narration_stop`
  - `ai_rules_oracle`
  - `ai_npc_speak`
  - `ai_describe_scene`
  - `generate_loot`

### Legacy/duplicate paths to keep but de-emphasize

- `POST /api/ai/generate-map` remains as a compatibility alias to cartographer generation.
- Provider/fallback status is currently duplicated between `play.html` and `client/static/js/cartographer.js`; later stages should centralize the richer explanation in the assistant surface.
- Dormant modular JS files under `client/static/js/core/`, `gameplay/`, `render/`, `state/`, and most of `ui/` should not become the primary implementation target unless the live page explicitly loads them.

## First-pass DM Assistant information architecture

### One assistant identity

The DM should see one coherent assistant surface:

- **DM Assistant** = a single entry point in the gameplay UI.
- Inside it, AI-adjacent capabilities appear as **tools/actions**, not as unrelated top-level features.

### Stage 1 tool set

The first integrated tool list should be:

- Generate map
- Describe scene
- Suggest ambience
- Ask rules
- Draft NPC line

These should reuse current backend/client behaviors where possible.

## Stage 1 thin contract

Stage 1 should introduce a thin assistant-oriented contract rather than a large agent framework.

### Assistant status response

Recommended shape:

```json
{
  "assistant": {
    "name": "DM Assistant",
    "entry_enabled": true,
    "tools": [
      {
        "key": "generate_map",
        "label": "Generate map",
        "transport": "http",
        "available": true,
        "direct_access": {
          "kind": "panel",
          "target": "map_studio"
        }
      }
    ],
    "providers": {
      "narration": {
        "effective_provider": "gemini_tts",
        "fallback": "browser_fallback"
      },
      "cartographer": {
        "image_provider": "openai",
        "planning_provider": "anthropic"
      }
    }
  }
}
```

Notes:

- This can be layered on top of the existing integrations status response.
- It should explicitly communicate availability and fallback behavior.
- It should not claim a tool is available if the underlying provider path is missing or in stub mode.

### Assistant action result envelope

Recommended frontend-facing result envelope:

```json
{
  "ok": true,
  "action": "ask_rules",
  "title": "Rules answer",
  "summary": "Opportunity attacks trigger when a hostile creature leaves your reach.",
  "content": {
    "text": "..."
  },
  "provider": {
    "primary": "anthropic",
    "fallback_used": false,
    "fallback_reason": null
  },
  "direct_passthrough": {
    "kind": "ws",
    "message_type": "ai_rules_oracle"
  }
}
```

Notes:

- Existing direct routes/messages can remain unchanged behind adapters.
- The assistant UI should consistently render loading, success, explicit fallback, and explicit error states.
- Failures should stay visible; the contract must not hide provider problems.

## Non-goals for Stage 0

Stage 0 does **not**:

- remove existing feature entry points,
- replace cartographer or narration internals,
- migrate runtime authority into dormant modules,
- or build a generalized agent framework.

## Exit criteria for Stage 0

Stage 0 is complete when:

- runtime ownership is documented clearly enough to avoid implementing against dormant code,
- compatibility constraints are written down,
- and Stage 1 has a concrete assistant status/action contract to implement.
