# Runtime Ownership Map

Stage 0 audit document for the live Alpha D&D VTT runtime. This file is intentionally conservative: it maps the systems that are already in production paths and calls out legacy or compatibility surfaces that future stages should preserve unless tests prove they are unused.

## Audit baseline

- `main.py` is the FastAPI application entrypoint. It owns startup, data directory initialization, static mounts, router registration, and the live WebSocket endpoint wiring into `server.handlers.handle_message`.
- `server/pages/routes.py` owns the public HTML page routes for DM login, Player login/character flows, Viewer watch entry, and `/play`.
- `client/templates/play.html` remains the highest-risk live browser surface. It still owns most play-page DOM, inline CSS, role-sensitive UI state, global helpers, and the final client-side message application path through `handleLegacyMessage()`.
- Loaded modules under `client/static/js/core/`, `client/static/js/ui/`, `client/static/js/render/`, `client/static/js/editor/`, and `client/static/js/character/` should be treated as adapters or slice-specific authorities only when `play.html` actually loads them.
- `server/handlers/__init__.py` is the authoritative WebSocket message dispatch table for live gameplay messages. Domain logic then lands in `server/handlers/*.py`.
- Dormant-looking modules must not be promoted into canonical runtime ownership without first wiring them into `play.html` and preserving compatibility with existing globals.

## Systems

### System: DM live play

- **Current main files:**
  - `client/templates/play.html`
  - `server/pages/routes.py`
  - `main.py`
  - `client/static/js/core/runtime_bridge.js`
  - `client/static/js/core/boot_shell.js`
  - `client/static/js/core/ws.js`
  - `client/static/js/core/message_dispatch.js`
  - `client/static/js/state/store.js`
  - `client/static/js/ui/tabs.js`
  - `client/static/js/ui/chat.js`
  - `client/static/js/ui/chat_log.js`
  - `client/static/js/ui/panel_controls.js`
  - `client/static/js/ui/dm_assistant.js`
- **What it controls:** DM entry into the live tabletop, role-specific panels, map/editor controls, chat/log surfaces, combat controls, content panels, live WebSocket send/apply glue, and most legacy global state used by loaded modules.
- **Canonical / Legacy / Compatibility:** Canonical runtime remains `play.html` plus the loaded shell modules. `runtime_bridge.js`, `boot_shell.js`, `ws.js`, and `message_dispatch.js` are compatibility-oriented live adapters; `message_dispatch.js` is a first-hop dispatcher, not the final message authority.
- **Risks:** Small UI changes can break DM/player/viewer parity because many functions are still global and indirectly called. Reordering script tags or moving logic out of `play.html` can break boot, WebSocket message handling, editor callbacks, or role gating.
- **Recommended future refactor path:** Extract one narrow vertical slice at a time into a loaded module, keep the `play.html` compatibility shim until callers are traced, add targeted tests for the slice, then remove legacy glue only after proving it is no longer called.

### System: Player live play

- **Current main files:**
  - `server/pages/routes.py`
  - `client/templates/player-characters.html`
  - `client/templates/character-creation.html`
  - `client/templates/play.html`
  - `client/static/js/ui/player_shell.js`
  - `client/static/js/character/runtime/mapper_to_play.js`
  - `client/static/js/character/runtime/character_book_runtime.js`
  - `client/static/js/character/runtime/character_sheet_runtime.js`
  - `client/static/js/core/ws.js`
  - `server/handlers/tokens.py`
  - `server/handlers/combat.py`
  - `server/handlers/inventory.py`
- **What it controls:** Player login target, character selection/creation gateway, player entry into `/play`, owned-token actions, character runtime mapping, sheet display, inventory actions, chat, and turn/permission-sensitive combat behavior.
- **Canonical / Legacy / Compatibility:** Player live session behavior is canonical in `play.html` plus loaded player/character runtime modules and backend handlers. Some similarly named gameplay modules are reference or partial migration surfaces unless script-tagged by `play.html`.
- **Risks:** Player flows are role-sensitive. Token ownership, single-active-token rules, combat-turn movement, and inventory updates depend on both client state and backend enforcement. Editing only dormant client files will not change the live player path.
- **Recommended future refactor path:** Keep backend permission enforcement in `server/handlers/*.py`, move player UI behavior out of `play.html` only behind loaded adapters, and validate with both DM and Player browser sessions.

### System: Viewer/spectator entry

- **Current main files:**
  - `server/pages/routes.py`
  - `client/templates/viewer-entry.html`
  - `client/templates/play.html`
  - `server/handlers/viewer_powers.py`
  - `server/handlers/tokens.py`
  - `server/handlers/content.py`
- **What it controls:** Viewer login/watch entry, spectator join flow, visible roster presence, viewer-specific panels, viewer power grants/usage, viewer cursors, and role-filtered token/map visibility.
- **Canonical / Legacy / Compatibility:** Viewer entry page is canonical for `/viewer/watch`; live spectator behavior after joining is canonical in `play.html` with backend authority in `viewer_powers.py` and role filtering in token/content handlers.
- **Risks:** Viewers intentionally have restricted visibility and permissions. Changes can accidentally grant Player/DM capabilities, hide viewers from roster sync, or bypass approval/cooldown logic for powers.
- **Recommended future refactor path:** Keep viewer permissions server-side, add client adapters for viewer panels only after preserving current `play.html` globals, and test DM + Viewer together for roster, grants, pending approvals, and power FX.

### System: Character creation/import

- **Current main files:**
  - `client/templates/character-creation.html`
  - `client/templates/player-characters.html`
  - `client/static/js/character/library/character_import_modal.js`
  - `client/static/js/character/library/character_library_panel.js`
  - `client/static/js/character/builder/*.js`
  - `client/static/js/character/builder/steps/*.js`
  - `server/character/routes.py`
  - `server/character/import_normalizer.py`
  - `server/character/service.py`
  - `server/character/schema.py`
  - `server/character/resolver.py`
- **What it controls:** Character library routes, import modal behavior, native builder steps, validation/normalization, persistence API, and conversion from imported/native data into runtime-ready character records.
- **Canonical / Legacy / Compatibility:** Character creation/import has more modular ownership than live play. The templates and loaded builder/library modules are canonical for the pre-play flow; server `character` modules are canonical for validation, import normalization, and persistence.
- **Risks:** Imported legacy sheets and native builder output must both resolve into the runtime format expected by `/play`. Changes can break existing characters even when the builder UI still works.
- **Recommended future refactor path:** Keep normalization centralized in `server/character/import_normalizer.py` and `server/character/service.py`; add focused tests for imported legacy documents and native builder roundtrips before changing runtime mapping.

### System: Character sheet rendering

- **Current main files:**
  - `client/templates/play.html`
  - `client/static/js/character/runtime/character_sheet_runtime.js`
  - `client/static/js/character/runtime/character_book_runtime.js`
  - `client/static/js/character/runtime/mapper_to_play.js`
  - `client/static/js/ui/character_book.js`
  - `client/static/js/character/character_sheet_container.js`
  - `client/static/js/character/tabs/actions_tab.js`
  - `client/static/js/character/tabs/inventory_tab.js`
  - `client/static/js/character/tabs/spells_tab.js`
  - `client/static/js/character/tabs/features_tab.js`
  - `client/static/css/character-sheet-premium.css`
- **What it controls:** In-session character book/sheet presentation, HP/AC/stat surfaces, actions/spells/features/inventory tabs, and mapping from server character documents into play-page UI structures.
- **Canonical / Legacy / Compatibility:** Loaded character runtime and tab modules are slice-specific live authorities, but `play.html` still owns the page shell, modal containers, role context, and several global callbacks.
- **Risks:** Sheet display is tightly coupled to tokens, inventory, encumbrance, HP sync, and combat UI. A sheet-only change can regress token-linked HP/AC or action availability.
- **Recommended future refactor path:** Treat runtime mapping as the boundary. Add tests around mapper output and tab rendering contracts before moving additional sheet state out of `play.html`.

### System: Inventory system

- **Current main files:**
  - `client/templates/play.html`
  - `client/static/js/character/tabs/inventory_tab.js`
  - `client/static/js/gameplay/encumbrance.js`
  - `client/static/js/editor/shop_panel.js`
  - `client/static/js/editor/shop_view.js`
  - `client/static/js/editor/chest_view.js`
  - `server/handlers/inventory.py`
  - `server/handlers/__init__.py`
  - `server/character/service.py`
- **What it controls:** Player inventory display/actions, add/remove/transfer/equip/use flows, loot/chest/shop interactions, gold/stash/treasury behavior, crafting/profession actions, sell offers, and encumbrance updates.
- **Canonical / Legacy / Compatibility:** Backend authority is `server/handlers/inventory.py` via dispatch entries in `server/handlers/__init__.py`. Frontend authority is split between `play.html`, loaded shop/chest helpers, `inventory_tab.js`, and loaded encumbrance support.
- **Risks:** Inventory changes can affect character sheet rendering, encumbrance, shops, props/chests, and multiplayer sync. Some UI behavior still lives inline in `play.html`, so changing `client/static/js/gameplay/inventory.js` alone is not a live fix unless it is wired in.
- **Recommended future refactor path:** Keep server-side inventory mutation canonical, add focused tests for each WS message family, and move only one UI inventory surface at a time behind a loaded adapter.

### System: Viewer powers

- **Current main files:**
  - `client/templates/play.html`
  - `server/handlers/viewer_powers.py`
  - `server/handlers/__init__.py`
  - `tests/test_integration_viewer_powers_tab.py`
- **What it controls:** Viewer power catalog, DM grants/revokes, presets/custom powers, viewer profile sync, pending approvals, use/cooldown/charge consumption, cursor/presence updates, and visible power FX.
- **Canonical / Legacy / Compatibility:** Server authority is `viewer_powers.py`; client rendering/application is still inline in `play.html`. Any `client/static/js/gameplay/viewer_powers.js` work should be treated as dormant/reference unless the play page loads it in a later stage.
- **Risks:** Approval defaults, cooldowns, power charges, and role visibility are easy to desync between DM and Viewer. Viewer power UI also touches token targeting and FX/audio surfaces.
- **Recommended future refactor path:** Preserve `viewer_powers.py` as the mutation authority, extract client panel rendering only after adding integration coverage for DM grant, Viewer use, DM approval, and roster visibility.

### System: Combat handling

- **Current main files:**
  - `client/templates/play.html`
  - `server/handlers/combat.py`
  - `server/handlers/tokens.py`
  - `server/handlers/conditions.py`
  - `server/handlers/__init__.py`
  - `client/static/js/render/combat_fx.js`
  - `tests/test_integration_combat_tab.py`
  - `tests/test_player_permissions.py`
- **What it controls:** Combat start/update/turn order, initiative, next/previous/clear, movement budgets, dash/disengage/difficult terrain toggles, target selection, attack request/override flow, death saves, token HP/conditions, and combat FX.
- **Canonical / Legacy / Compatibility:** Backend authority is `server/handlers/combat.py` and token/condition handlers. Client combat UI/application remains primarily in `play.html`; `combat_fx.js` is a loaded presentation helper. `client/static/js/gameplay/combat.js` should not be assumed live unless explicitly wired.
- **Risks:** Combat is highly multiplayer-sensitive. DM, active Player, inactive Player, and Viewer permissions differ, and token movement/HP changes must stay synchronized.
- **Recommended future refactor path:** Keep turn/permission enforcement server-side, extract read-only combat presentation before mutation controls, and run DM + Player + Viewer manual QA for every combat-stage change.

### System: WebSocket message handling

- **Current main files:**
  - `main.py`
  - `server/handlers/__init__.py`
  - `server/handlers/*.py`
  - `client/templates/play.html`
  - `client/static/js/core/ws.js`
  - `client/static/js/core/message_dispatch.js`
  - `client/static/js/core/runtime_bridge.js`
  - `client/static/js/state/store.js`
- **What it controls:** Live WebSocket connection setup, message send helpers, reconnect/state sync, server dispatch to domain handlers, and first-hop client dispatch into `play.html`'s legacy message application path.
- **Canonical / Legacy / Compatibility:** `main.py` owns the WebSocket endpoint; `server/handlers/__init__.py` owns server dispatch; `ws.js` owns the browser transport; `message_dispatch.js` is a compatibility first-hop; `play.html` remains the final client message application authority.
- **Risks:** Message type changes must be made in all three layers: client send/apply path, server endpoint/dispatch, and domain handler. Bypassing `handleLegacyMessage()` can silently drop state updates.
- **Recommended future refactor path:** Add new messages through the existing dispatch table, document payload contracts, then migrate client handlers one message family at a time behind a loaded module and compatibility shim.

### System: CSS/layout for the play screen

- **Current main files:**
  - `client/templates/play.html`
  - `client/static/css/session-theme.css`
  - `client/static/css/spotlight.css`
  - `client/static/css/character-sheet-premium.css`
  - `client/static/js/ui/editor_panel.css`
- **What it controls:** Top bar, role badge, play shell, side panels/flyouts, right-tab layout, map viewport, modals, character sheet styling, spotlight UI, and editor panel presentation.
- **Canonical / Legacy / Compatibility:** Layout ownership is split. `play.html` contains a large inline style block and is canonical for many page-specific rules; external CSS files are live for shared session theme, spotlight, character sheet, and editor panel slices.
- **Risks:** Inline styles and external CSS can override each other. Layout tweaks may affect all roles, mobile/player-shell behavior, and modal stacking.
- **Recommended future refactor path:** Move styles out only by component/slice, preserve existing selectors during migration, add visual/manual QA notes, and avoid broad CSS resets or global selector rewrites.

## Future placement guidance

- Put new backend live-game mutations in the relevant `server/handlers/*.py` file and register the message type in `server/handlers/__init__.py`.
- Put new HTTP/page APIs in the relevant router package (`server/pages`, `server/character`, `server/sessions`, `server/maps`, etc.) and register only from `main.py` when necessary.
- Put new play-page client behavior in a small loaded module only when `play.html` is updated to load it in the correct order and still exposes compatibility hooks for existing callers.
- Prefer adapters around `play.html` globals over rewrites until the old callers are traced.
- Add or update focused tests for the specific message family or UI contract being changed, then use `docs/manual-qa-live-session.md` for role-based smoke validation.

## Stage 0 outcome

1. **What changed:** Added this audit map to document runtime ownership and safe future placement for live-session systems.
2. **Files changed:** `docs/runtime-ownership-map.md`.
3. **How to test it:** Review this map before feature work, run targeted tests for any touched subsystem, and use `docs/manual-qa-live-session.md` for manual live-session smoke checks.
4. **Risks / follow-up work:** This is a documentation snapshot. Future stages should keep it updated when ownership moves from `play.html` into loaded modules.
