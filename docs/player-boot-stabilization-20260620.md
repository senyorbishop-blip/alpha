# Player Boot Stabilization Audit — 2026-06-20

## Runtime sources of truth used

- `docs/repo-map.md`
- `docs/system-audit-20260320.md`
- `docs/pr-275-324-runtime-conflict-audit.md`
- `main.py`
- `client/templates/play.html`
- `client/static/tts_client.js`
- `client/static/js/ui/dm_assistant.js`
- `client/static/js/cartographer.js`
- `client/static/js/character/combat_quick_actions.js`
- `client/static/js/character/combat_quick_bar.js`
- `client/static/js/character/combat_quick_selectors.js`
- `client/static/js/render/fog.js`
- `client/static/js/core/ws.js`
- `client/static/js/core/runtime_bridge.js`
- `client/static/js/core/message_dispatch.js`
- `server/handlers/__init__.py`
- `server/handlers/combat.py`
- `server/handlers/common.py`
- `server/handlers/map_editor.py`
- `server/handlers/tokens.py`
- `server/session.py`

## PR #275-#324 conflict matrix summary

The detailed matrix lives in `docs/pr-275-324-runtime-conflict-audit.md`. The highest-risk repeated-change clusters were:

- Player boot: PR #317-#324 changed `boot_shell.js`, `diagnostics.js`, `ws.js`, `dice3d.js`, `sound_engine.js`, `cartographer.js`, `tts_client.js`, `dm_assistant.js`, and `play.html` boot/init code.
- Quick actions and weapon damage: PR #276, #279-#284, #287-#288, #290, #293, and #323 changed overlapping quick-action selectors, bar rendering, action bridges, spell action helpers, and weapon damage helpers.
- Autosave/profile save: PR #319, #320, #323, and #324 changed quick-pick migration, profile dirty/clean handling, render depth guards, and autosave deferral.
- Initiative: PR #296-#323 repeatedly changed `combatRollInitiative`, `combat_initiative_rolled` handling, combat-state repainting, and server combat revision logic.
- Fog/token visibility: PR #285-#286, #289-#293, #311, #322-#323 changed client fog apply paths and server visibility/broadcast helpers.

## Regression isolation result

- `34e3d2813381d04ebb6e72990fb794caf7f09ace` (before PR #323): player scripts parsed; player boot was already in the recently-lightened boot sequence from PR #318; audit risk remained around shared DOM checks for TTS metadata and overlapping combat/fog/initiative ownership.
- `77f4a31d925804ee7e01ba3038b709598474edd8` (after PR #323): player scripts parsed; PR #323 touched fog, initiative result patching, and quick weapon normalization, making it a plausible first regression point for combat/fog/quick-action symptoms but not the TTS metadata endpoint calls.
- `e4e1ebbc0485afb0a3cc5340da50b3f50eafeb9b` (after PR #324): player scripts parsed and autosave deferral was improved; player boot still had one root endpoint leak in `tts_client.js` because it treated the shared narration select element as proof of a DM boot.

## Root cause fixed here

`client/static/tts_client.js` initialized TTS metadata for any page that contained `#narration-voice-preset`. The play page shares that DOM across roles, so players could still fetch `/api/tts/voices` and `/api/tts/warmup-phrases` even though these are DM narration-panel metadata calls. The fix gates those calls on `ROLE` or the query-string role instead of element presence.

## Ownership conclusions

- Quick Actions: the loaded `combat_quick_actions.js`/`combat_quick_bar.js`/`combat_quick_selectors.js` path is active, while `play.html` still keeps compatibility bridges and helper exports. This remains overlapping ownership and should not be broadened in this stabilization patch.
- Autosave: render and selector paths must remain side-effect free; tests now guard quick selectors, weapon damage, and state-sync autosave deferral.
- Initiative: ownership remains mixed. The recommended source of truth is authoritative `combat_state`; `combat_initiative_rolled`/dice-result local patchers should be notification/optimistic repaint only and must reconcile back to `combat_state`.
- Fog: ownership remains mixed. Server filtering and visibility revisions are authoritative for recipients/visibility, while the client applies the active map's fog state and requests sync. The safe rule is to keep server visibility authoritative and make client apply paths role-agnostic for received fog.
- Player boot: DM assistant and cartographer are now role-gated, sound preloads are DM-only and interaction/idle deferred, and this patch fixes the remaining TTS metadata role leak.

## Manual browser smoke checklist

1. Open `/play?role=player` and confirm there are no top-level `ReferenceError` or `SyntaxError` console errors.
2. Confirm WebSocket connects, sends `request_state`, and remains open after state sync.
3. Confirm the player boot network log does not call `/api/assistant/status`, `/api/tts/voices`, `/api/tts/warmup-phrases`, or eager `/static/sounds/*.ogg` preloads.
4. Confirm state sync does not trigger `scheduleCharProfileSave` recursion or an autosave deferral loop.
5. Confirm quick-action weapon damage opens/rolls and does not trigger profile autosave.
6. Confirm the active player map receives/render fog updates from the DM.
7. Confirm initiative UI updates from authoritative `combat_state` and local initiative notifications reconcile without double-applying stale order.
