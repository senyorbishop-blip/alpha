# Repository Architecture Map

This document describes the structure, ownership, and startup flow of this codebase for AI agents and developers.
Last updated during the audit/cleanup pass (March 2026).

---

## Quick Reference: Where to Edit Things

| What you want to change | Edit this file |
|---|---|
| Server request routing / WebSocket dispatch | `server/handlers/__init__.py` |
| Combat server logic | `server/handlers/combat.py` |
| Token server logic | `server/handlers/tokens.py` |
| Fog-of-war server logic | `server/handlers/map_editor.py` |
| Inventory server logic | `server/handlers/inventory.py` |
| Hazard zone server logic | `server/handlers/hazards.py` |
| Viewer powers server logic | `server/handlers/viewer_powers.py` |
| Condition effects server logic | `server/handlers/conditions.py` |
| Shared server utilities (_safe_int, _token_center, etc.) | `server/handlers/common.py` |
| Session persistence / restore | `server/restore.py` |
| Asset upload / manifest / pipeline | `server/users/assets.py`, `server/asset_pipeline.py` |
| Asset manifest endpoint | `main.py` (routes `/api/assets/*`) |
| Static manifest of built-in props/markers | `client/static/assets/manifest.json` |
| SVG props / markers generator | `tools/generate_prop_assets.py` |
| Play page (all client-side gameplay) | `client/templates/play.html` (inline JS) |
| Editor terrain styles | `client/static/js/editor/terrain_manifest.js` |
| Editor terrain rendering | `client/static/js/editor/terrain_renderer.js` |
| Asset library UI (flyout panel) | `client/static/js/ui/asset_library.js` |
| Editor side-panel (terrain/prop/wall buttons) | `client/static/js/ui/editor_panel.js` |
| Custom/user asset management (client) | `client/static/js/editor/assets.js` |
| Prop/marker/terrain asset initializer | `client/static/js/editor/asset_initializer.js` |
| 3-D dice physics | `client/static/js/dice/dice3d.js` |
| Combat FX animations | `client/static/js/render/combat_fx.js` |
| Map document serialisation | `client/static/js/editor/serialization.js` |

---

## Repository Layout

```
New-New/
├── main.py                         # FastAPI app: routes, WS, auth, asset API
├── server/
│   ├── handlers/                   # WebSocket message handlers (split by domain)
│   │   ├── __init__.py             # handle_message() dispatch table
│   │   ├── common.py               # Shared helpers: _safe_int, _token_center, etc.
│   │   ├── combat.py
│   │   ├── tokens.py
│   │   ├── map_editor.py
│   │   ├── inventory.py
│   │   ├── hazards.py
│   │   ├── viewer_powers.py
│   │   ├── conditions.py
│   │   └── content.py
│   ├── auth/                       # JWT auth, user models, routes
│   ├── campaigns/                  # Campaign claim logic
│   ├── users/                      # User-specific asset management
│   ├── utils/                      # PDF parser utility
│   ├── asset_pipeline.py           # Image validation, hashing, manifest entry builder
│   ├── config.py                   # App configuration constants
│   ├── constants.py                # Shared game constants
│   ├── connections.py              # WebSocket connection manager
│   ├── db.py                       # SQLite database helpers
│   ├── editor_schema.py            # Editor data schema validators
│   ├── map_document.py             # Map document structure helpers
│   ├── map_logic.py                # Map rendering logic helpers
│   ├── map_migrations.py           # Map schema migration helpers
│   ├── paths.py                    # File system path constants
│   ├── restore.py                  # Session restore from DB
│   ├── rules_content.py            # Game rules content data
│   ├── rules_db.py                 # Rules database helpers
│   ├── rules_engine.py             # Rules engine (combat, stats)
│   └── session.py                  # Session state management
├── client/
│   ├── templates/
│   │   ├── play.html               # Main play page (see below)
│   │   ├── campaigns.html          # Campaign list page
│   │   ├── casual-dnd-login.html   # Login page
│   │   ├── join.html               # Join session page
│   │   └── landing.html            # Landing page
│   └── static/
│       ├── assets/
│       │   ├── manifest.json       # Built-in asset manifest (source of truth)
│       │   ├── props/              # SVG prop assets
│       │   └── markers/            # SVG marker assets
│       ├── css/
│       │   └── session-theme.css   # Shared session CSS variables/base styles
│       ├── textures/world/         # World-map terrain textures
│       └── js/
│           ├── assets/
│           │   └── dnd_assets.js   # Built-in D&D asset manifest (window.DndAssets)
│           ├── core/               # (unloaded) Refactored env-injection core modules
│           ├── dice/
│           │   └── dice3d.js       # 3-D dice physics (ES module, loaded via importmap)
│           ├── editor/             # Editor modules (partially loaded — see below)
│           ├── gameplay/           # (unloaded) Refactored gameplay modules
│           ├── render/             # Render modules (combat_fx.js loaded; rest unloaded)
│           ├── state/              # (unloaded) State store module
│           └── ui/                 # UI modules (asset_library.js, editor_panel.js loaded)
├── tests/
│   └── test_refactor.py            # Python tests for server refactors
└── tools/
    └── generate_prop_assets.py     # Idempotent SVG + manifest generator
```

---

## play.html: The Client Runtime

`client/templates/play.html` is the single-page application for all gameplay. It is ~19,000 lines and contains:

- **All inline CSS** (~2,000 lines in a single `<style>` block) plus two linked external CSS files
- **All inline JS** (~16,000 lines in a single `<script>` block, ~705 top-level functions)
- **14 external JS modules** loaded via `<script src=...>` tags (listed below)
- **One ES-module** (`dice3d.js`) loaded via `<script type="module">`

### External JS modules loaded by play.html (in order)

| File | Exposes | Purpose |
|---|---|---|
| `editor/serialization.js` | `window.EditorMapDocument` | Map document read/write |
| `editor/terrain_manifest.js` | `window.EditorTerrainManifest` | Terrain type definitions |
| `assets/dnd_assets.js` | `window.DndAssets` | Built-in asset catalogue |
| `editor/asset_initializer.js` | `window.DndAssetInit`, `window.DndAssetCache` | Asset image preload |
| `editor/asset_renderer.js` | `window.AssetRenderer` | Prop/terrain canvas rendering |
| `editor/terrain_renderer.js` | `window.EditorTerrainRenderer` | Terrain tile rendering |
| `editor/placement_controller.js` | `window.PlacementController` | Prop drag-placement |
| `editor/shop_panel.js` | `window.ShopPanel` | Shop prop side panel |
| `editor/shop_view.js` | `window.ShopView` | Shop inventory overlay |
| `render/combat_fx.js` | `window.AppCombatFX` | Hit shake / attack result FX |
| `editor/assets.js` | `window.AppEditorAssets` | User asset upload/manifest |
| `ui/asset_library.js` | `window.AppUIAssetLibrary` | Asset library flyout UI |
| `ui/editor_panel.js` | `window.EditorPanel` | Editor sidebar panel |
| `core/runtime_bridge.js` | `window.AppRuntimeBridge` | **Live compatibility bridge** from modular boot into the inline `play.html` runtime |
| `core/boot_shell.js` | `window.AppBootShell` | **Live startup sequence owner** (`initUI` → `initCanvas` → `connectWS` → `syncSessionAuthority`), delegating behavior to `play.html` globals |
| `core/ws.js` | `window.AppWS` | Live WebSocket connect/send/queue wrapper |
| `core/message_dispatch.js` | `window.AppMessageDispatch` | **Live first-hop dispatcher only**; concrete handlers still live in `play.html` |
| `state/store.js` | `window.AppStateStore` / `window.AppStore` | **Live shell store** for session/user/socket state, not the full gameplay state authority |
| `render/boot.js` | `window.AppRenderBoot` | Live render bootstrap for canvas resize/input boot/loop start |
| `render/fog.js` | `window.AppFog` | Live fog shell helpers and fog overlay module |
| `render/vision.js` | `window.AppVision` | Live vision shell helpers and visibility/overlay module |
| `ui/tabs.js` | `window.AppUITabs` | Live right-sidebar tab/dropdown/badge controller |
| `ui/chat.js` | `window.AppUIChat` | Live chat compose/target UI controller |
| `ui/chat_log.js` | `window.AppUIChatLog` | Live chat log filter/render helper |
| `dice/dice3d.js` | `window.DicePhysics3D` | 3-D dice (ES module) |

### play.html: Script load order matters

```
play.html <style>          — CSS at top of file
play.html <script> (early) — script tags for external modules (lines ~3809–3822)
play.html <link> (css)     — editor_panel.css (line 3822)
play.html <script> (main)  — all inline JS (line 3823 onwards, ~16,000 lines)
play.html <script module>  — dice3d.js (ES module, last)
```

The inline JS depends on the external modules being loaded first. Do not reorder.

### play.html: How loaded external modules call back into play.html globals

`ui/editor_panel.js` uses a local `call(fn, ...args)` helper that calls `window[fn](...args)`.
This means the following global functions in play.html are called indirectly by `editor_panel.js`:

- `setEditorTerrain`
- `setEditorBrush`
- `setEditorWallTool`
- `setEditorFileAsset`
- `setEditorDndPropAsset`
- `setEditorLayerMode`
- `saveEditorMap`
- `clearEditorMap`

**Do not remove these functions from play.html** — they are called at runtime even though no direct reference appears in play.html itself.

---

### Runtime ownership status labels

Use these labels when deciding where to make changes:

- **Live** — directly loaded by `play.html` and active at runtime.
- **Compatibility** — loaded and active, but only as a bridge into legacy `play.html` globals/state.
- **Dormant** — present in the repo but not loaded by `play.html`; do not treat as runtime authority.
- **Fallback-only** — loaded or preserved only to support a live system's emergency/legacy path.

For Stage 0 cleanup work, prefer clarifying ownership before deleting anything.

## Stage 1 Runtime Ownership Lockdown (2026-03-27)

The table below is the current live ownership map for high-risk gameplay/runtime
subsystems. Treat this as the default source-of-truth index before changing
runtime behavior.

| Subsystem | Client live owner | Server live owner | Notes |
|---|---|---|---|
| Session boot | `client/templates/play.html` + `client/static/js/core/boot_shell.js` + `client/static/js/core/runtime_bridge.js` | `main.py` (page routes + app startup) | `boot_shell.js` is the ordered startup owner; `runtime_bridge.js` is compatibility/handoff into `play.html` runtime functions. |
| WebSocket connect/send/receive | `client/templates/play.html` + `client/static/js/core/ws.js` + `client/static/js/core/runtime_bridge.js` | `main.py` WebSocket endpoint + `server/handlers/__init__.py` dispatch | Client `core/ws.js` is live transport; gameplay state application still lands in `play.html`. |
| Client message dispatch | `client/static/js/core/message_dispatch.js` first-hop, then `client/templates/play.html` `handleLegacyMessage()` | `server/handlers/__init__.py` | `core/message_handlers.js` remains dormant unless loaded by `play.html`. |
| Token state + ownership | `client/templates/play.html` | `server/handlers/tokens.py` | Token sync/authority behavior is still inline-owned on client runtime path. |
| Map load/save/switching | `client/templates/play.html` + `client/static/js/editor/serialization.js` | `server/handlers/map_editor.py` + persistence in `server/restore.py`/`server/db.py` | `serialization.js` is authoritative serializer but depends on `play.html` runtime globals. |
| Fog/vision | `client/templates/play.html` + `client/static/js/render/fog.js` + `client/static/js/render/vision.js` | `server/handlers/map_editor.py` | Render helpers are live modules; final gameplay application authority remains `play.html`. |
| Combat | `client/templates/play.html` + `client/static/js/render/combat_fx.js` | `server/handlers/combat.py` | `client/static/js/gameplay/combat.js` is dormant and not runtime authority. |
| Dice | `client/templates/play.html` + `client/static/js/dice/dice3d.js` | `server/handlers/content.py` (`dice_roll`) | `play.html` still owns dice UI glue and WS result handling. |
| Narration/audio | `client/static/js/ui/sound_engine.js` + `client/static/js/ui/narration.js` + `client/templates/play.html` controls/glue | `server/handlers/sound.py`, `server/handlers/narration.py`, `server/handlers/tts_relay.py` | `client/static/ambient_engine.js` + `client/static/sfx_engine.js` are fallback/compatibility support while loaded. |
| Inventory/shop | `client/templates/play.html` + loaded editor/shop helpers | `server/handlers/inventory.py` | Do not route behavior into dormant gameplay modules. |
| Handouts/journal/discoveries | `client/templates/play.html` | `server/handlers/content.py` | Inline runtime remains client source of truth for apply/render flow. |
| DM assistant + map tools | `client/templates/play.html` + `client/static/js/ui/dm_assistant.js` + `client/static/js/cartographer.js` | `server/handlers/ai_dm.py`, `server/handlers/cartographer.py`, `server/assistant/routes.py` | Stage work should layer on live path first; do not replace direct feature paths yet. |

## Unloaded External JS Modules (Not used by play.html)

The following modules exist in `client/static/js/` but are **not loaded** by any page. They represent
an **incomplete refactoring** toward dependency-injection architecture (all accept an `env` object).
They are NOT dead in the sense that they were intentionally written, but they are not connected to
the app. Do not confuse them with the loaded modules above.

```
core/api.js              — window.AppEnvBuilders (fetch abstraction)
core/env_builders.js     — window.AppEnvBuilders (env factory)
core/env_builders_gameplay.js — window.AppEnvBuildersGameplay
core/errors.js           — error helpers
core/message_handlers.js — window.AppMessageHandlers (dormant alternate WS router; not loaded by play.html)
core/utils.js            — utility helpers
core/ws.js               — window.AppWS (WebSocket wrapper)
editor/coordinator.js    — window.AppEditorCoordinator
editor/inspector.js      — window.AppEditorInspector
editor/interactions.js   — window.AppEditorInteractions
editor/panels.js         — window.AppEditorPanels
editor/poi_tools.js      — window.AppEditorPoi
editor/prop_tools.js     — window.AppEditorProps
editor/runtime.js        — window.AppEditorRuntime
editor/state.js          — window.AppEditorState
editor/wall_tools.js     — window.AppEditorWalls
gameplay/combat.js       — window.AppGameplayCombat
gameplay/conditions.js   — window.AppGameplayConditions
gameplay/hazards.js      — window.AppGameplayHazards
gameplay/inventory.js    — window.AppGameplayInventory
gameplay/viewer_powers.js — window.AppGameplayViewer
render/boot.js           — render bootstrap
render/camera.js         — window.AppRenderCamera
render/fog.js            — window.AppFog
render/grid.js           — window.AppGrid
render/input.js          — window.AppInput
render/pointer_orchestrator.js — window.AppPointerOrchestrator
render/ruler.js          — window.AppRenderRuler
render/terrain_cache.js  — window.AppTerrainCache
render/token_interactions.js — window.AppTokenInteractions
render/vision.js         — window.AppVision
state/store.js           — window.AppStateStore
ui/character_book.js     — window.AppUICharacterBook
ui/chat.js               — window.AppUIChat
ui/chat_history.js       — window.AppUIChatHistory
ui/chat_log.js           — window.AppUIChatLog
ui/context_menu.js       — window.AppUIContextMenu
ui/forms.js              — window.AppUIForms
ui/item_library.js       — window.AppUIItemLibrary
ui/item_library_actions.js — window.AppUIItemLibraryActions
ui/item_library_picker.js — window.AppUIItemLibraryPicker
ui/modal_actions.js      — window.AppUIModalActions
ui/modals.js             — window.AppUIModals
ui/notifications.js      — window.AppUINotifications
ui/panels.js             — window.AppUIPanels
ui/player_shell.js       — window.AppUIPlayerShell
ui/spell_form.js         — window.AppUISpellForm
ui/spell_rules.js        — window.AppUISpellRules
ui/tabs.js               — window.AppUITabs
ui/toolbar.js            — window.AppUIToolbar
ui/world_controls.js     — window.AppUIWorldControls
auth.js                  — auth helpers (used by non-play pages)
campaign-claim.js        — window.CampaignClaim (used by campaigns.html)
user-assets.js           — user asset helpers
```

---

## DM Assistant Stage 0 ownership note

The planned unified DM Assistant should currently be implemented against the **live** runtime surfaces below:

- `main.py` for HTTP route registration and compatibility aliases
- `server/handlers/__init__.py` for live WebSocket dispatch
- `client/templates/play.html` for the visible DM entry surface and UI glue
- `client/static/js/cartographer.js` for Map Studio behavior
- `client/static/js/ui/narration.js` for narration playback/presentation

Do **not** treat dormant dependency-injection modules under `client/static/js/core/`, `gameplay/`, `render/`, `state/`, or unloaded `ui/` modules as the primary DM Assistant implementation target unless `play.html` is explicitly updated to load them.

During early assistant work, preserve the current direct entry points for Map Studio, narration, rules oracle, NPC speech, and fog auto-description while the unified surface matures.

---

## Single Source of Truth Map

| Responsibility | Source of truth |
|---|---|
| **Play page bootstrapping** | `client/static/js/core/boot_shell.js` (ordered startup owner) + `client/static/js/core/runtime_bridge.js` (**compatibility layer**), delegating to `play.html` entrypoints |
| **WebSocket connection** | `client/static/js/core/ws.js`, configured by `runtime_bridge.js` and consumed by `play.html` |
| **WebSocket message dispatch (client)** | `client/static/js/core/message_dispatch.js` (**first hop only**) handing off into `play.html` `handleLegacyMessage()` |
| **Client shell state (session/user/socket/tool/dice/fog/vision)** | `client/static/js/state/store.js` (**shell state only**), initialized from and mirrored back to `play.html` globals |
| **Gameplay state variables (client)** | `play.html` inline globals (`tokens`, `cam`, `users`, combat/editor runtime state, etc.) |
| **Render bootstrap (resize/bind/start loop)** | `client/static/js/render/boot.js`, via `play.html` compatibility wrappers |
| **Fog shell helpers** | `client/static/js/render/fog.js`, via `play.html` compatibility wrappers |
| **Vision shell helpers** | `client/static/js/render/vision.js`, via `play.html` compatibility wrappers |
| **Right sidebar tabs/dropdowns** | `client/static/js/ui/tabs.js`, via `play.html` compatibility wrappers |
| **Chat compose / whisper target UI** | `client/static/js/ui/chat.js`, via `play.html` compatibility wrappers |
| **Visible chat log rendering** | `client/static/js/ui/chat_log.js`, via `play.html` compatibility wrappers |
| **Rendering loop** | `play.html` inline `drawFrame()` / `drawLoop()` |
| **Grid drawing** | `play.html` inline `drawGrid()` |
| **Token rendering** | `play.html` inline `drawTokens()` |
| **Vision rendering** | `play.html` inline `drawPlayerVisionOverlay()` |
| **Fog of war state & paint** | `play.html` inline (`fogPaintAt`, `fogApplyState`, etc.) |
| **Combat state** | `play.html` inline `combatApplyState()`, `renderCombat()` |
| **Spell markers** | `play.html` inline (`drawSpellMarkers`, `lockSpell`, etc.) |
| **Editor terrain cells** | `play.html` inline (`drawEditorTerrainCell`, etc.) |
| **Editor terrain textures** | `editor/terrain_renderer.js` (`window.EditorTerrainRenderer`) |
| **Editor terrain manifest** | `editor/terrain_manifest.js` (`window.EditorTerrainManifest`) |
| **Editor prop/marker/image placement** | `play.html` inline (`buildEditorPropItem`, `findEditorPropIndexAt`, etc.) |
| **Prop/terrain asset catalogue** | `assets/dnd_assets.js` (`window.DndAssets`) |
| **Asset image preloading** | `editor/asset_initializer.js` (`window.DndAssetInit`) |
| **Asset canvas rendering** | `editor/asset_renderer.js` (`window.AssetRenderer`) |
| **User/custom asset upload & manifest** | `editor/assets.js` (`window.AppEditorAssets`) |
| **Asset library flyout UI** | `ui/asset_library.js` (`window.AppUIAssetLibrary`) |
| **Editor panel sidebar** | `ui/editor_panel.js` (`window.EditorPanel`) |
| **Map document serialisation** | `editor/serialization.js` (`window.EditorMapDocument`) |
| **Shop prop UI** | `editor/shop_panel.js` / `editor/shop_view.js` |
| **Combat FX (hit shake, attack result)** | `render/combat_fx.js` (`window.AppCombatFX`) |
| **3-D dice physics** | `dice/dice3d.js` (`window.DicePhysics3D`) |
| **Dice animation entry point** | `play.html` inline `showDiceAnimation()` — routes to 3-D or 2-D fallback |
| **Dice result ingestion** | `play.html` inline `fillDiceResult()` — routes to 3-D or 2-D fallback |
| **Dice overlay cleanup** | `play.html` inline `closeDiceOverlay()` |
| **Dice WS message (client)** | `play.html` inline `dice_result` switch-case |
| **Dice WS message (server)** | `server/handlers/content.py` `handle_dice_roll()` |
| **Character sheet parse / import** | `play.html` inline (`parseDDBCharacter`, `autoFillCharacterBookFromPaste`, etc.) |
| **Inventory UI** | `play.html` inline (`renderInventoryPanel`, `applyPlayerInventoryState`, etc.) |
| **Hazard zone UI** | `play.html` inline (`populateHazardForm`, `beginHazardPlacement`, etc.) |
| **Item library UI** | `play.html` inline (`renderItemLibraryList`, `openItemLibraryModal`, etc.) |
| **Chat UI** | `play.html` inline (`sendChat`, `addLogEntry`, etc.) |
| **Journal / Library** | `play.html` inline (`initJournalUI`, `initLibraryUI`, etc.) |
| **Viewer powers UI** | `play.html` inline (`viewerPowerDefs`, `showViewerFx`, etc.) |
| **Static built-in asset manifest** | `client/static/assets/manifest.json` |
| **Server WebSocket dispatch** | `server/handlers/__init__.py` (`handle_message()`) |
| **Server combat logic** | `server/handlers/combat.py` |
| **Server token logic** | `server/handlers/tokens.py` |
| **Server map/fog logic** | `server/handlers/map_editor.py` |
| **Server session restore** | `server/restore.py` |
| **Server asset pipeline** | `server/asset_pipeline.py` |
| **Bestiary / Creature Library REST API** | `main.py` (GET/POST/PUT/DELETE `/api/library/creatures`, `/variant`, `/spawn`) |
| **Bestiary DB helpers** | `server/db.py` (`create_creature`, `get_creatures`, `seed_srd_for_user`, etc.) |
| **SRD monster seed data** | `server/srd_bestiary.py` (83 SRD 5.1 monsters, CR 0–30) |
| **Bestiary panel UI** | `play.html` inline (`bestiaryLoad`, `openBestiaryStatModal`, `bestiarySpeak`, `bestiaryPlaceCreatureAt`, etc.) |
| **App startup** | `main.py` |

---

## Dead Code Found During Audit (March 2026)

### Removed in this pass
- `importDDBCharacter()` — legacy stub (redirected to `importDDBJson`); never called, removed.
- `/* DM activity CSS removed */` — stale CSS comment, removed.
- `@dimforge/rapier3d-compat` importmap entry — declared in play.html `<script type="importmap">` but never imported by `dice3d.js` or any other file; removed.
- `env.flashRollButton()` call in `message_handlers.js` — `flashRollButton` is not defined anywhere; the actual flash behaviour lives inline in play.html's `dice_result` handler; the dead call removed from unloaded module.
- Stale comment `// (3-D dice bridge logic is now inline...)` at end of play.html — removed.

### Known dead functions in play.html (not removed — too risky without browser testing)

The following functions are defined in `play.html` but never called from `play.html` itself,
from any loaded external module, or from any HTML event attribute. They reference HTML elements
that no longer exist in the template, or they are orphaned helpers.

| Function | Line | Notes |
|---|---|---|
| `addDMNotif` | ~13349 | DM notification helper, no caller found |
| `addEditorLabelPrompt` | ~6270 | Label creation prompt, no caller found |
| `clearClientRuntimeError` | ~4102 | Error banner clear, never called |
| `createHazardZoneAtView` | ~13637 | Hazard creation helper, no caller found |
| `currentWorldEditorBaseTerrain` | ~4543 | Returns world base terrain, no caller found |
| `deleteEditorLabelModalItem` | ~6136 | Label delete, no caller found |
| `dominantTerrainAround` | ~7930 | Terrain blend helper, no caller found |
| `drawTaperedRiverPath` | ~7301 | River path renderer, no caller found |
| `extractBonus` | ~15723 | Character import helper, no caller found |
| `markerGlyphForKind` | ~7487 | Returns marker glyph, no caller found |
| `saveEditorLabelModal` | ~6116 | Label save, no caller found |
| `saveEditorWeatherSettings` | ~18319 | References non-existent HTML elements |
| `setEditorBlendStrength` | ~6003 | References non-existent HTML element |
| `setEditorChestHidden` | ~5954 | Sets variable; checkbox exists but has no event listener |
| `setEditorForestDensity` | ~6008 | References non-existent HTML element |
| `setEditorMapMode` | ~4586 | References non-existent map-mode HTML element |
| `setEditorMountainDirection` | ~6013 | References non-existent HTML element |
| `showEditorMarkerLinkHelp` | ~6031 | No caller found |
| `toggleShowVisionFallbackBanner` | ~8809 | No caller found |
| `updateEditorMapStyleReadout` | ~4549 | References non-existent HTML element |

**Recommended next step:** Review each function above and either:
1. Delete the function if it is confirmed dead (no future feature needs it)
2. Wire up the missing HTML element and event listener if it should be active

---

## Unloaded Module Architecture (Env-Injection Pattern)

The `core/`, `gameplay/`, `render/` (most), `state/`, and most `ui/` modules were written as a
**planned refactoring** toward explicit dependency injection via an `env` object. These modules
have NOT been connected to `play.html`. Until they are wired up:

- They are loaded by **no page** and produce no runtime effect.
- They do NOT conflict with play.html's inline code (different scope).
- They ARE a maintenance trap: code in them may drift from play.html's inline versions.

**Recommended next step (major refactor):** Either:
1. Wire up the env-injection architecture: create an `env` object in `play.html`, load the
   modules, and migrate inline code to delegate to the modules.
2. Or: decide the inline architecture is permanent and remove the unloaded modules to prevent
   drift. This would reduce the codebase by ~50 files.

---

## AI Agent Guidelines

### When adding a feature:
- New **server-side** game logic → add to the appropriate `server/handlers/*.py` module.
- New **client-side UI** that lives in the play panel → add to `play.html` inline JS section.
- New **editor component** (prop/terrain/marker) → check if a loaded external module handles it
  before adding to `play.html`.

### Things to avoid:
- Do NOT add event handlers or DOM queries to **unloaded** external modules. They have no effect.
- Do NOT create new global functions in `play.html` with the same name as functions in unloaded
  modules — this causes invisible drift.
- Do NOT reorder the `<script>` tags in `play.html` — the inline JS depends on external modules
  being loaded first.
- Do NOT use `window.AppGameplayCombat`, `window.AppFog`, `window.AppMessageHandlers` etc. from
  `play.html` — these modules are not loaded.
- DO use `window.AppEditorAssets`, `window.AppUIAssetLibrary`, `window.EditorPanel`,
  `window.AppCombatFX`, `window.DndAssets`, `window.AssetRenderer` etc. — these ARE loaded.

### When editing play.html:
- The inline `<script>` block starts at line ~3823 and ends at line ~19449.
- Functions are grouped in sections separated by `═══` banner comments.
- State variables are at the top of the script block.
- `AppBootShell.runDOMContentLoaded()` is the live DOMContentLoaded startup entry point.
- The render loop is `drawFrame()` called via `requestAnimationFrame`.

### When editing server handlers:
- Add new message types to the dispatch table in `server/handlers/__init__.py`.
- Keep shared utilities in `server/handlers/common.py`.
- Do NOT duplicate `_safe_int` or `_token_center` — they exist exactly once in `common.py`.


## Stage 0 clarification: what is truly live today

To reduce future architectural drift, treat the current runtime as:

1. **`play.html` is still the final client authority** for concrete gameplay behavior and state application.
2. **`core/runtime_bridge.js`, `core/boot_shell.js`, `core/message_dispatch.js`, and `state/store.js` are live**, but mostly as shell/compatibility infrastructure around `play.html`.
3. **`core/message_handlers.js` and most `gameplay/`, `editor/`, `render/`, and `ui/` refactor modules remain dormant unless explicitly loaded by `play.html`.**
4. **`client/static/js/ui/sound_engine.js` and `client/static/js/ui/narration.js` are the live feature engines** for audio/narration, while `play.html` still owns the UI glue and WebSocket-facing event hooks.
5. **`client/static/ambient_engine.js` and `client/static/sfx_engine.js` should currently be treated as fallback/compatibility modules**, not peer runtime authorities, unless a future audit proves otherwise.

If a change affects live gameplay behavior, start by checking whether the behavior is actually implemented in `play.html` before editing a similarly named modular file.





### Stage 5 checkpoint: script-load guardrails for audited ownership

The current `play.html` script-load boundary for the audited areas is:

| Area | Loaded by `play.html` | Intentionally not loaded by `play.html` |
|---|---|---|
| WS first-hop dispatch | `core/message_dispatch.js` | `core/message_handlers.js` |
| Render bootstrap | `render/boot.js` | n/a |
| Fog / vision shell helpers | `render/fog.js`, `render/vision.js` | n/a |
| Audio / narration | `ui/sound_engine.js`, `ui/narration.js`, plus fallback `ambient_engine.js` / `sfx_engine.js` | n/a |
| Combat | inline `play.html` combat block | `gameplay/combat.js` |
| Character sticky notes | `character/sticky_notes.js` plus `play.html` profile glue | n/a |
| Editor serialization | `editor/serialization.js` | `editor/runtime.js`, `editor/state.js` |

When changing ownership in one of these areas, update both the docs and the script-load tests in `tests/` in the same patch so the repo map and test suite stay aligned.

### Stage 4 clarification: render bootstrap ownership

For render bootstrap, the current live client ownership is:

- `client/static/js/render/boot.js` → authoritative `AppRenderBoot` setup for canvas resize wiring, fog-canvas creation, one-time pointer binding, and starting the animation loop
- `client/templates/play.html` → compatibility `initCanvas()` / `resizeCanvas()` wrappers plus the live `drawLoop()`, `drawFrame()`, and gameplay/pointer handlers passed into the render boot env

Until a later migration moves more render-domain logic, prefer updating `render/boot.js` for setup/bootstrap behavior and `play.html` for concrete draw or interaction behavior.

### Stage 4 clarification: editor serialization vs runtime ownership

For editor persistence, the current live client ownership is:

- `client/static/js/editor/serialization.js` → authoritative `EditorMapDocument` serializer/normalizer
- `client/templates/play.html` → live editor runtime state, save/apply hooks, and global layer collections
- `client/static/js/editor/state.js` + `client/static/js/editor/runtime.js` → dormant alternate modules; not loaded by `play.html`

Until a future migration explicitly wires the editor runtime modules into the page, prefer updating `serialization.js` for map document shape changes and `play.html` for live editor state/save-flow changes.

### Stage 3 clarification: live combat path

For combat, the current live client ownership is:

- `client/templates/play.html` → live combat state application, rendering, and button/action handlers
- `server/handlers/combat.py` → live server combat authority
- `client/static/js/gameplay/combat.js` → dormant alternate module; not loaded by `play.html`

Until a future migration explicitly wires `gameplay/combat.js` into the page, prefer updating the inline combat block in `play.html` for behavior fixes and treat the modular file as a non-authoritative draft.

### Stage 2 clarification: live sound and narration path

For audio and narration, the current live client ownership is:

- `client/static/js/ui/sound_engine.js` → live `SoundEngine` / `AudioManager` authority
- `client/static/js/ui/narration.js` → live `NarrationManager` authority
- `client/templates/play.html` → UI controls, WebSocket send/receive hooks, and boot glue
- `client/static/ambient_engine.js` + `client/static/sfx_engine.js` → compatibility/fallback support only while still loaded

If behavior differs between `sound_engine.js` and the procedural files, treat `sound_engine.js` plus the `play.html` glue as the intended runtime path and review the procedural files only as fallback support.

### Stage 1 clarification: live incoming-message path

For WebSocket messages, the current live client path is:

`AppWS.connectWS()` → `AppMessageDispatch.handleIncoming()` → `play.html` `handleLegacyMessage()`

`core/message_handlers.js` is **not** part of that runtime path today. Treat it as a dormant alternate router until `play.html` explicitly loads and adopts it.

### Stage 0 UX baseline pointer

For the focused premium-play UX pass, including the current DM workflow pass,
use `docs/play-ux-stage0-20260323.md` as the practical baseline for:

- live runtime ownership
- UX surfaces currently in scope
- duplicate / dormant paths to avoid editing by mistake
- staged regression checks for later UX polish work
- DM workflow source-of-truth files and first-slice guardrails
