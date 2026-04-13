# Play UX Stage 0 Baseline — 2026-03-23

This document records the live runtime ownership and UX-risk baseline for the
play experience before the focused polish pass. It is intentionally practical:
it identifies the files that are truly live today, the duplicate or legacy
paths that must be preserved during the pass, and the highest-risk surfaces to
validate after each stage.

---

## Goal of Stage 0

Stage 0 does **not** redesign the UI. Its purpose is to prevent the UX pass
from editing dormant modules or breaking compatibility glue that is still
required at runtime.

---

## Live runtime source of truth

### Server/runtime boot

- `main.py` remains the application entrypoint for startup, static mounts,
  routers, and WebSocket session boot.
- `server/handlers/__init__.py` remains the authoritative WebSocket dispatch
  table for live play messages.

### Live play page

- `client/templates/play.html` is still the final authority for:
  - play-page DOM structure
  - most visual surface definitions
  - gameplay state globals
  - the final client-side WebSocket message application path
  - inline combat, inventory, journal, shop, and many modal/flyout handlers

### Live compatibility shell

- `client/static/js/core/boot_shell.js` is live, but primarily bootstraps the
  page by delegating into `play.html`.
- `client/static/js/core/runtime_bridge.js` is live, but acts as a
  compatibility bridge between modular shells and `play.html` globals/state.
- `client/static/js/core/ws.js` is the live WebSocket transport layer.
- `client/static/js/core/message_dispatch.js` is only the **first-hop**
  dispatcher. Concrete message handling still lands in `play.html`.

### Live modular UI helpers

These files are active and should be treated as runtime-owned helpers for the
play-page UX pass:

- `client/static/js/ui/tabs.js`
- `client/static/js/ui/chat.js`
- `client/static/js/ui/chat_log.js`
- `client/static/js/ui/editor_panel.js`
- `client/static/js/ui/asset_library.js`
- `client/static/js/ui/sound_engine.js`
- `client/static/js/ui/narration.js`
- `client/static/js/cartographer.js`
- `client/static/js/map-library.js`

### Shared styling

- `client/static/css/session-theme.css` is live shared session chrome.
- `client/templates/play.html` still contains a large inline `<style>` block,
  so CSS ownership is split between the external session theme and inline page
  rules.

---

## Runtime surfaces included in the UX pass

The focused UX pass should treat the following as in-scope live surfaces:

- top bar / invite / connection status
- left rail and flyout panels
- right-tab panes and dropdowns
- editor flyout and asset library
- narration and sound controls
- combat panel
- map studio / map library surfaces
- inventory / loot / shop surfaces
- modal overlays and empty/loading/error states

---

## DM workflow Stage 0 baseline

The current DM workflow implementation should be read with the following
runtime boundaries before adding encounter or scene-running features:

### Live DM workflow source-of-truth files

- `client/templates/play.html`
  - live Bestiary tab DOM, filters, modal actions, and single-creature spawn UI
  - live combat-start, initiative, targeting, and condition UI
  - live handout/journal sync application and local-map navigation glue
- `server/creatures/service.py`
  - authoritative bestiary spawn validation and token creation path
- `server/handlers/combat.py`
  - authoritative combat lifecycle, movement budget, and battle-audio switching
- `server/handlers/tokens.py`
  - authoritative token create/edit/visibility/condition handlers
- `server/handlers/content.py`
  - authoritative journal and handout persistence + broadcast path
- `server/handlers/map_editor.py`
  - authoritative fog, map-settings, prop, and local-map scene-state handlers
- `server/session.py`
  - authoritative in-memory campaign/session shape for persisted DM state
- `server/db.py`
  - authoritative campaign persistence and normalization path for new DM data

### Existing DM building blocks already present

These should be reused rather than replaced:

- bestiary search/filter/create/variant flow
- REST-backed creature spawn onto the current `map_context`
- combat bootstrap from current-map tokens
- token hidden/condition state sync
- journal entries with optional `poi_id`
- handout persistence and recipient filtering
- per-map fog / props / walls / settings / weather persistence
- local-map enter/exit and “bring everyone here” navigation sync

### Stage 0 implementation guardrails for the DM workflow

- Do **not** revive `session.library_entries` as a new creature source; that
  field remains backward-compatibility only while the live creature library is
  the DB-backed `/api/library/creatures` path.
- Do **not** build a parallel client-only encounter or scene state store in a
  dormant module when the live flow still runs through `play.html`.
- Treat `client/static/js/gameplay/combat.js` as a draft/reference module, not
  the runtime authority for combat changes, unless a later wiring pass proves
  otherwise.
- Treat `client/static/js/editor/runtime.js` as dormant; use `play.html` plus
  the existing server editor/map handlers for live scene-state work.

### First workflow slice to implement after Stage 0

Keep the first shipped DM workflow slice narrow and integrated:

1. encounter template draft/save/load from the existing bestiary
2. one-click spawn of the drafted group onto the current map
3. optional “start combat from this spawn group” shortcut
4. lightweight scene preset save/apply for current-map fog + ambience + map
   settings + token visibility, with later linkage into journal/handout flows

This keeps the next stage focused on one strong prep/run loop instead of
introducing a second DM subsystem with overlapping state ownership.

---

## Duplicate, legacy, or dormant paths

### Must preserve during the UX pass

- Hidden editor compatibility DOM in `play.html` under the editor flyout.
  These elements still satisfy legacy ID lookups used by the live editor
  panel/runtime glue.
- `play.html` global functions indirectly invoked by `ui/editor_panel.js`
  (`setEditorTerrain`, `setEditorBrush`, `setEditorWallTool`,
  `setEditorFileAsset`, `setEditorDndPropAsset`, `setEditorLayerMode`,
  `saveEditorMap`, `clearEditorMap`).
- Fallback audio support paths (`client/static/ambient_engine.js`,
  `client/static/sfx_engine.js`) while they are still loaded.

### Do not treat as runtime authority for this pass

These modules are present but dormant unless `play.html` explicitly loads them:

- `client/static/js/core/message_handlers.js`
- `client/static/js/editor/runtime.js`
- `client/static/js/editor/state.js`
- `client/static/js/editor/coordinator.js`
- `client/static/js/gameplay/combat.js`
- most files under `client/static/js/gameplay/`
- most files under `client/static/js/editor/` that are not directly loaded
- most files under `client/static/js/render/` beyond the explicitly loaded
  bridge/shell files

### Practical Stage 0 rule

If a UX issue is visible on the play page, check `play.html` first before
editing a similarly named file in `client/static/js/gameplay/`,
`client/static/js/editor/`, or `client/static/js/ui/`.

---

## High-risk UX surfaces

These areas currently have the highest density, inconsistency, or coupling risk:

1. **Left rail + flyouts**
   - mixes primary tools, DM-only controls, and administrative surfaces
   - weak distinction between high-frequency and secondary actions

2. **Editor flyout**
   - large feature surface with live module + hidden compatibility DOM
   - brittle due to legacy IDs and indirect global callbacks

3. **Right-tab pane system**
   - shared shell, but content ownership is mixed across inline and modular code

4. **Narration / sound**
   - strong candidate for state-message polish
   - must preserve live `sound_engine.js` / `narration.js` ownership

5. **Combat**
   - inline live implementation
   - role-sensitive controls and disabled-state logic

6. **Map Studio / Library**
   - active custom surface with fetch/upload/generate/discover flows
   - particularly sensitive to loading/error-state clarity

7. **Inventory / loot / shop**
   - feature-rich inline surfaces with multiple empty-state branches

---

## Planned edit targets for the later UX pass

### Primary files

- `client/templates/play.html`
- `client/static/css/session-theme.css`

### Likely supporting files

- `client/static/js/ui/editor_panel.js`
- `client/static/js/ui/asset_library.js`
- `client/static/js/ui/tabs.js`
- `client/static/js/ui/chat.js`
- `client/static/js/ui/chat_log.js`
- `client/static/js/ui/sound_engine.js`
- `client/static/js/ui/narration.js`
- `client/static/js/cartographer.js`
- `client/static/js/map-library.js`

### Server files only if client messaging proves insufficient

- `main.py`
- `server/handlers/__init__.py`
- specific files under `server/handlers/` only when the client needs new
  explicit runtime state to present clearer UX feedback

---

## Regression checklist for every later stage

### Boot and visibility

- Play page still boots through the current shell path.
- DM-only controls still appear only for DMs.
- Player character surface still opens and remains usable.
- Viewer restrictions still behave as before.

### Core panel behavior

- Left-rail flyouts still open/close correctly.
- Right-tab switching still works.
- Editor panel still mounts and syncs.
- Asset library still initializes and renders.

### Live-play features

- Combat controls still render and remain role-correct.
- Narration preview / broadcast / stop still work.
- Sound controls still update volume and ambient state.
- Map Studio discover / generate / library flows still work.
- Inventory / loot / shop surfaces still render and update.

### State messaging

- WebSocket connected / disconnected / expired states remain understandable.
- Empty states remain visible and readable.
- Upload and provider failures show actionable feedback.

---

## Validation baseline to run after each implementation stage

### Automated

- `pytest tests/test_refactor.py`
- `pytest tests/test_audio_broadcast.py`
- `pytest tests/test_map_library_init.py`

### Manual

- Open play page as DM and verify:
  - top bar renders correctly
  - left rail opens major flyouts
  - right tabs still switch
  - combat pane still works
  - narration/sound state is understandable
  - map library remains usable

---

## Stage 0 completion criteria

Stage 0 is complete when:

- the live runtime ownership is explicit
- dormant modules are clearly separated from live ones
- the later UX pass has a bounded edit list
- the highest-risk regressions are identified before visual changes begin
