# Frontend Modularization Notes

## Stage 1 — Boot extraction

Move only the page boot orchestration out of `play.html` while preserving the current inline gameplay logic, DOM ids/classes, and global function contracts.

### Live ownership after Stage 1

- `client/templates/play.html` remains the live source of truth for gameplay state, rendering, editor actions, fog, combat, and all remaining inline handlers.
- `client/static/js/core/boot_shell.js` owns ordered `DOMContentLoaded` startup sequencing (`initUI` → `initCanvas` → `connectWS` → `syncSessionAuthority`).
- `client/static/js/core/runtime_bridge.js` is compatibility/handoff glue that adapts store + `play.html` globals into modular boot/ws/message-dispatch env contracts.
- `client/static/js/state/store.js` remains shell/session/user/socket state ownership only and is not gameplay-domain authority.

## Stage 2 — WebSocket lifecycle + top-level message dispatch

Move the live connection lifecycle and the first incoming-message entrypoint into modules, while keeping the large inline message switch as the temporary legacy domain dispatcher.

### Live ownership after Stage 2

- `client/static/js/core/ws.js` is now the live owner of socket connect / reconnect / send / queue / flush behavior.
- `client/static/js/core/message_dispatch.js` is now the live owner of the first incoming-message handoff.
- `client/templates/play.html` still owns the legacy domain switch in `handleLegacyMessage()` and the concrete per-domain handlers it calls.

- `client/static/js/core/message_handlers.js` remains a dormant alternate router and is intentionally not loaded by `play.html` during Stage 1 cleanup.
- `client/static/js/core/runtime_bridge.js` now adapts both boot and WebSocket/message-dispatch contracts into the inline runtime.

## Stage 3 — Central store for boot/session/socket ownership

Introduce a live central store for runtime shell state before moving gameplay-domain collections and render systems.

### Live ownership after Stage 3

- `client/static/js/state/store.js` is now the live owner for session/user/socket shell state and the seed store for low-risk UI shell fields such as selected tool and selected die.
- `client/templates/play.html` initializes the store at startup, then reads initial shell values from it while preserving current globals for backward compatibility.
- `client/static/js/core/runtime_bridge.js` now reads session/user/socket state through the store first, then falls back to the inline globals.
- Gameplay collections such as `tokens`, `users`, `journalEntries`, combat state, fog maps, and editor layers still remain inline for now.

### Why this is safe

- The store currently owns only shell/runtime state with low coupling to the gameplay domains.
- Existing globals remain in place and continue to work.
- The bridge uses store-first reads without requiring a full domain rewrite.

## Stage 4 — Render bootstrap extraction

Move render bootstrap wiring out of `play.html` while keeping the draw loop, draw passes, and gameplay/render-domain logic inline.

### Live ownership after Stage 4

- `client/static/js/render/boot.js` is now the live owner of render bootstrap concerns: canvas resize wiring, fog-canvas creation, one-time pointer binding, and starting the animation loop.
- `client/templates/play.html` still owns `drawLoop()`, `drawFrame()`, pointer handlers, and the concrete double-click/gameplay behavior through env callbacks passed into the render bootstrap module.
- Existing `initCanvas()` / `resizeCanvas()` entrypoints remain as compatibility wrappers so boot and any legacy callers keep working.

### Why this is safe

- Render bootstrap is mostly setup glue and can be isolated without moving draw-domain logic.
- The module still calls the exact existing inline handlers via callbacks, so interaction behavior remains unchanged.
- Compatibility wrappers preserve the old function names while shifting live ownership to the module.

### Follow-up stages

## Stage 5 — Fog and vision shell extraction

Move fog/vision shell ownership onto the store-backed runtime shell and route the reusable fog/vision helpers through dedicated render modules while leaving draw-domain/gameplay data inline.

### Live ownership after Stage 5

- `client/static/js/render/fog.js` is now the live owner of fog shell helpers such as map-context selection, fog state loading, fog UI sync, paint batching, toggle/reveal/hide helpers, and fog overlay rendering.
- `client/static/js/render/vision.js` is now the live owner of vision shell helpers such as preview/fallback state interpretation, visibility checks, preview UI refresh, and the player-vision overlay.
- `client/templates/play.html` now provides compatibility env/state wrappers that feed the existing inline runtime into those modules, while keeping gameplay collections, LOS inputs, and draw orchestration inline.
- `client/static/js/state/store.js` now seeds fog and vision shell state so the runtime shell remains store-backed.

### Why this is safe

- Fog/vision shell state is narrower and lower-risk than moving the entire draw loop or gameplay collections.
- The dedicated modules are invoked through compatibility wrappers, so existing callers and DOM wiring continue to work.
- Inline gameplay state still remains the source of truth for tokens, walls, props, and map assets.

### Follow-up stages

## Stage 6 — Right-sidebar tab UI extraction

Move a narrow interactive UI domain out of `play.html` by making the right-sidebar tab controller modular while keeping tab-specific panes and their domain renderers inline.

### Live ownership after Stage 6

- `client/static/js/ui/tabs.js` is now the live owner of right-sidebar tab switching, dropdown open/close behavior, and unread-log badge updates.
- `client/templates/play.html` now provides a compatibility env for tab state, role-aware callbacks, and pane-specific hooks such as shop, bestiary, and spell-library refreshes.
- `client/static/js/state/store.js` remains the shell owner for the active right-tab and unread-log values, which are now kept in sync by the modular tab controller.

### Why this is safe

- The tab controller is a narrow UI slice with limited coupling compared with full gameplay systems.
- Tab-specific content still renders through the existing inline functions, so domain behavior does not need to move yet.
- Compatibility wrappers preserve the existing global function names and click handlers while shifting live tab orchestration into the module.

### Follow-up stages

## Stage 7 — Chat compose UI extraction

Move the chat compose controller out of `play.html` while keeping message transport and log storage behavior unchanged.

### Live ownership after Stage 7

- `client/static/js/ui/chat.js` is now the live owner of chat target visibility, whisper-target rendering, and chat send behavior for everyone/viewers/whisper/oracle flows.
- `client/templates/play.html` now provides a compatibility env exposing role, user list, sender identity, and `sendWS()` so the modular chat controller can reuse the existing runtime.

### P7 guardrails

- `client/templates/play.html` must stay thin and must not reintroduce inline chat compose functions or inline `<script>` blocks.
- `client/static/js/ui/chat.js` owns the public `window.AppUIChat` contract: `init`, `updateChatTargetVisibility`, `renderChatTargets`, and `sendChat`.
- Any future chat-compose work must update the focused P7 tests in `tests/test_p7_play_html_decomposition.py` so ownership does not drift back into the template.

## Stage 8 — Chat log rendering extraction

Move the visible chat-log rendering rules out of `play.html` so chat feed filtering and badge bumps are modular, while the broader message pipeline stays unchanged.

### Live ownership after Stage 8

- `client/static/js/ui/chat_log.js` is now the live owner of presence-log filtering and visible chat-log entry rendering, including viewer/whisper channel tags.
- `client/templates/play.html` now delegates `isPresenceLogEntry()` and `addLogEntry()` through compatibility wrappers, while the existing WS handlers still decide when a log entry should be emitted.

### P8 guardrails

- `client/templates/play.html` must not reintroduce `addLogEntry()`, `isPresenceLogEntry()`, or `AppUIChatLog` ownership.
- `client/static/js/ui/chat_log.js` owns the public `window.AppUIChatLog` contract: `isPresenceLogEntry` and `addLogEntry`.
- The chat-log module must continue to filter presence spam, render only chat entries, preserve viewer/whisper channel tags, and escape role/user/message text before inserting HTML.
- Any future chat-log work must update `tests/test_p8_chat_log_rendering.py` in the same patch so feed-rendering ownership does not drift back into the template.

1. Move gameplay systems and UI domains out one slice at a time until the inline legacy dispatcher and global state can be retired.

- `client/static/js/gameplay/combat.js` remains a dormant alternate combat module until `play.html` explicitly loads and adopts it.

- `client/static/js/editor/serialization.js` remains the authoritative map serializer, while `editor/state.js` and `editor/runtime.js` stay dormant until `play.html` explicitly loads them.

- Stage 5 expectation: when ownership changes, update both the script-load docs and the focused `tests/` guardrails in the same patch so runtime boundaries do not drift.
