# Audio / Narration / Dice Audit — 2026-03-20

## Root causes

### Ambient sound
- `client/static/assets/audio/` only contained `README.md`; there were no actual loop files, so the client always fell through to procedural audio.
- `client/templates/play.html` still embedded an older sound engine bootstrap path, which made it harder to verify the real active code path.
- Asset selection and decode failures were not logged with exact paths, so stale caches and missing files looked like “bad audio” instead of an asset pipeline failure.

### Storyteller narration
- The app had two narration implementations: the modular `client/static/js/ui/narration.js` and an older inline stub in `play.html`.
- Server responses did not clearly expose whether ElevenLabs or browser fallback was used, and there was no recent-clip cache.
- Browser fallback voice selection was not strongly differentiated per preset and could sound too similar.

### 3D dice
- The dice tray depended on a hybrid architecture: inline UI control in `play.html`, a large custom `dice3d.js`, CDN import-map loading for Three.js, and a legacy Matter.js runtime path.
- The overlay could open before the render path proved healthy, which produced “blank success” states.
- The previous implementation carried far more moving parts than necessary for the current app and was brittle during startup / first-frame rendering.

## Cleanup summary
- Removed the legacy inline sound/narration implementation block from `play.html` and left the modular JS files as the single authority.
- Removed the Matter.js runtime dependency from `play.html`; the dice system no longer mixes custom animation with a second physics engine.
- Replaced the oversized custom dice runtime with a smaller deterministic Three.js presentation pipeline that guarantees visible dice, a first frame, and deterministic result orientation.

## Patch notes
- Added manifest-based ambient audio loading with versioned asset paths, decode diagnostics, and explicit fallback logging.
- Added startup-generated emergency ambient loop assets (`forest`, `tavern`, `dungeon`, `battle`) so the app no longer defaults to procedural-only playback in a fresh checkout while keeping binary files out of the repo diff.
- Added ElevenLabs provider / cache / fallback metadata end-to-end, including preview caching and stronger preset-specific fallback voice hints.
- Rebuilt the 3D dice system around a deterministic Three.js tray animation with premium lighting, shadowed materials, multi-die support, settle callbacks, and visible final-value badges.

## New / changed assets and env
- New asset manifest: `client/static/assets/audio/manifest.json`
- Startup-generated loop assets (materialised automatically by `server/ambient_audio.py` when missing):
  - `client/static/assets/audio/forest_loop_v20260320.wav`
  - `client/static/assets/audio/tavern_loop_v20260320.wav`
  - `client/static/assets/audio/dungeon_loop_v20260320.wav`
  - `client/static/assets/audio/battle_loop_v20260320.wav`
- Optional ElevenLabs overrides now support per-preset model + voice tuning through existing `ELEVENLABS_VOICE_*` vars plus optional `ELEVENLABS_MODEL_*` vars.

## Manual QA checklist
- Start the app, open the sound panel, and switch between forest / tavern / dungeon / battle while watching the console for requested track, resolved asset path, and fallback status.
- Trigger narration preview for all four presets both with and without `ELEVENLABS_API_KEY`; confirm the console clearly reports `elevenlabs` vs `browser_fallback`.
- Roll d4, d6, d8, d10, d12, d20, and d100 at quantities 1 and 4; verify the dice tray shows visible dice immediately, settles, and the popup matches the dice result.


## Stage 0 ownership clarification (2026-03-23)

This audit remains directionally correct, but the repo should currently be read with the following runtime-ownership nuance:

- `client/templates/play.html` still owns the live UI glue, global runtime variables, and the final client-side message application path.
- `client/static/js/ui/sound_engine.js` and `client/static/js/ui/narration.js` are the active audio/narration engines.
- `client/static/js/core/message_dispatch.js` is live only as a first-hop handoff into `play.html`'s legacy `handleLegacyMessage()` path.
- `client/static/js/core/message_handlers.js` is not the live message application path unless and until `play.html` explicitly loads it.
- `client/static/ambient_engine.js` and `client/static/sfx_engine.js` should be treated as compatibility/fallback support while `play.html` still loads them, not as separate feature authorities.

Practical implication for cleanup: document and narrow ownership first, then remove stale paths only after confirming they are not loaded or indirectly required.


## Stage 2 ownership clarification (2026-03-23)

For the current runtime, read the March 20 sound/narration cleanup with this narrower ownership model:

- `client/static/js/ui/sound_engine.js` is the live audio authority used by `play.html`.
- `client/static/js/ui/narration.js` is the live narration authority used by `play.html`.
- `client/templates/play.html` still owns the visible controls, preview/broadcast hooks, and WebSocket-facing glue.
- `client/static/ambient_engine.js` and `client/static/sfx_engine.js` are still loaded, but should be treated as fallback/compatibility support rather than separate top-level feature owners.

Practical implication for cleanup: preserve the current player/DM behavior first, and only remove procedural references after confirming `sound_engine.js` no longer depends on them for fallback playback.



## DM Assistant Stage 0 clarification (2026-03-23)

For the upcoming unified DM Assistant work, read the current AI-adjacent runtime as follows:

- `client/templates/play.html` still owns the live DM-facing entry points, button wiring, and message/result presentation for narration, NPC speech, scene-description triggers, and provider messaging.
- `client/static/js/cartographer.js` is the active Map Studio controller and should be reused rather than replaced in the first assistant slice.
- `client/static/js/ui/narration.js` remains the active narration playback layer and should stay the presentation authority for spoken output.
- `server/handlers/ai_dm.py`, `server/handlers/narration.py`, and `server/handlers/cartographer.py` are separate working capabilities today; the assistant should unify their presentation/discoverability before attempting deeper backend consolidation.
- Preserve current direct feature access while introducing the assistant layer so DM workflows do not regress during migration.

Practical implication for Stage 1: add a thin assistant-oriented status/action layer and a unified UI surface first; do not begin by deleting existing routes, message types, or direct panels.
