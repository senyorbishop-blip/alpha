# Role UI 5-Pass Audit — DM, Player, Viewer

Date: 2026-06-26

This audit is intentionally conservative. The local `client/templates/play.html` is present and non-blank, so removal decisions are based on the running local copy rather than any possibly stale GitHub rendering.

## Runtime sources of truth used

- Backend entry/authority: `main.py`, `server/pages/routes.py`, `server/handlers/__init__.py`, `server/handlers/combat.py`, `server/handlers/tokens.py`, `server/handlers/map_editor.py`, `server/handlers/inventory.py`, `server/handlers/viewer_powers.py`, `server/handlers/content.py`, `server/handlers/ws_permissions.py`.
- Frontend live authority: `client/templates/play.html`.
- Frontend live adapters/helpers: loaded scripts in `play.html`, especially `core/runtime_bridge.js`, `core/boot_shell.js`, `core/ws.js`, `core/message_dispatch.js`, `state/store.js`, `ui/tabs.js`, `ui/player_shell.js`, `ui/dm_map_first_shell.js`, `ui/dm_context_render.js`, `ui/dm_panel_mode_bridge.js`, character runtime/tab modules, editor modules, render modules, and audio/narration modules.
- Tests/guardrails reviewed: role-policy, viewer-power, combat, inventory, DM-context, player-event, character-runtime, and right-sidebar UI tests under `tests/`.

## PASS 1 — Runtime ownership and load-order audit

### Live route and boot path

1. `/dm`, `/player`, and `/viewer` render role-specific login targets, then redirect to `/campaigns`, `/player/characters`, or `/viewer/watch` respectively.
2. `/play` is the single live tabletop page for DM, Player, Viewer, and Assistant DM. `server/pages/routes.py` normalizes `role`, keeps `boot_scripts` empty to prevent duplicate core loading, and sends the normalized context into `play.html`.
3. `main.py` mounts static assets, includes page/API routers, and wires the WebSocket endpoint to `server.handlers.handle_message`.
4. `play.html` loads a large ordered script set before its inline runtime. The inline runtime still owns final client-side state application through compatibility globals and `handleLegacyMessage()`; `message_dispatch.js` is only a first-hop dispatcher.
5. `core/boot_shell.js` owns the shell startup sequence but delegates into `play.html` globals for `initUI`, `initCanvas`, `connectWS`, and session-authority sync.
6. `core/ws.js` owns WebSocket connect/send/queue mechanics. Server authority remains in `server/handlers/__init__.py` and the domain handlers.

### File status classification

| File / group | Status | Notes |
|---|---|---|
| `client/templates/play.html` | Live authority | Shared role page, inline DOM, role gates, globals, final message application. High risk. |
| `server/pages/routes.py` | Live authority | Page entry, role normalization, reconnect redirects. |
| `main.py` | Live authority | FastAPI app/router/static/WS entry. |
| `server/handlers/__init__.py` | Live authority | WS dispatch table. |
| `server/handlers/combat.py`, `tokens.py`, `map_editor.py`, `inventory.py`, `viewer_powers.py`, `content.py` | Live authority | Domain mutation and permission authority. |
| `server/handlers/ws_permissions.py` | Live authority | Shared role/message policy used by dispatch tests. |
| `core/runtime_bridge.js` | Live compatibility bridge | Connects modular boot to legacy globals. |
| `core/boot_shell.js` | Live compatibility bridge | Boot shell; delegates into legacy runtime. |
| `core/ws.js` | Loaded helper / live WS wrapper | Connection and queue mechanics. |
| `core/message_dispatch.js` | Live compatibility bridge | First-hop dispatch only. |
| `state/store.js` | Loaded helper | Shell/session/socket store, not full gameplay authority. |
| `ui/tabs.js` | Loaded helper / slice authority | Right-sidebar tab/dropdown visibility and badges. |
| `ui/chat.js`, `ui/chat_log.js` | Loaded helper / slice authority | Chat compose and chat-log rendering. |
| `ui/player_shell.js` | Loaded helper | Player dashboard and scoped event shell. |
| `ui/dm_map_first_shell.js`, `ui/dm_mode_tool_registry.js`, `ui/dm_context_render.js`, `ui/dm_panel_mode_bridge.js`, `ui/dm_map_first_bootstrap.js` | Loaded helpers / new DM UI adapters | New DM map-first UI; bridge to old controls, should not replace server authority. |
| Character runtime and tab modules loaded by `play.html` | Loaded helpers / slice authorities | Character book/sheet/actions/inventory/spells/features/quick-bar surfaces. |
| Editor modules loaded by `play.html` | Loaded helpers | Map/editor/shop/chest/assets helpers; some call back into `play.html` globals. |
| `render/boot.js`, `render/fog.js`, `render/vision.js`, `render/combat_fx.js` | Loaded helpers / slice authorities | Render boot/fog/vision/FX shells. |
| `client/static/js/gameplay/*` except loaded `encumbrance.js` | Dormant/reference only | Do not treat as live unless script-tagged. |
| Non-loaded `core/api.js`, `core/env_builders*.js`, `core/message_handlers.js` | Dormant/reference only | Not live replacements. |
| Legacy right tabs and left flyouts in `play.html` | Legacy but still called | Hidden/bridged by DM map-first shell; still necessary for unmigrated controls. |
| Debug/admin panels | Legacy/dev-only, still present | Must remain hidden by default and DM-only. |

## PASS 2 — Old UI to new UI migration matrix

| Role | Old UI element or function | Old file/function/selector | New UI location | New file/function/selector | Status | WS/API message | Backend authority | Test coverage | Manual QA |
|---|---|---|---|---|---|---|---|---|---|
| DM | Map controls | `play.html`, editor flyouts, `#ep-flyout-host`, terrain/wall/fog controls | Map-first left rail and Map Build mode | `dm_context_render.js`, `dm_panel_mode_bridge.js`, `data-dm-tool="terrain-tools"/"fog-tools"/"wall-tools"` | Connected via bridge; legacy still required | `editor_*`, `fog_*`, `map_settings_save` | `map_editor.py` | Existing static DM-context tests; missing browser QA | Toggle terrain/fog/walls/doors and save map. |
| DM | Token select/move/edit | `play.html` canvas handlers, token flyout, token edit modal | Map-first token context/right context | `play.html` token selection refresh + DM context | Partially connected; legacy edit modal remains | `token_move`, `token_edit`, `token_hp_update`, `token_condition` | `tokens.py`, `combat.py` | Existing token integration tests; static token-selection guard | Select/move/edit token as DM and verify no stale legacy drawer unless requested. |
| DM | NPC/monster spawning | `#rtab-pane-bestiary`, `bestiaryPlaceCreatureAt`, spawn buttons | NPC/Monster mode compact adapter | `dm_panel_mode_bridge.js`, `dm_context_render.js`, `AppUIDMActions.addCombatant/openNpcTools` | Connected via legacy bestiary bridge | Creature spawn API + `token_created` | `server/creatures/*`, `tokens.py` | DM context tests | Spawn from bestiary onto map. |
| DM | Combat tracker | `#rtab-pane-combat`, `combatStart/Next/Prev/Clear` | Combat mode right context | `dm_context_render.js`, `AppUIDMActions.*` | Connected; old tracker kept as drawer | `combat_update`, `combat_next`, `combat_prev`, `combat_clear` | `combat.py` | DM context, combat UI/integration tests | Start, turn cycle, clear. |
| DM | Start combat | `combatStart()` | Combat mode button | `AppUIDMActions.startCombat()` | Connected | `combat_update` | `combat.py` | Static bridge tests | Click Start Combat. |
| DM | Add selected token to combat | `combatAddTokenToInitiative()` | Combat mode button | `AppUIDMActions.addSelectedToCombat()` | Connected | `combat_add_token` | `combat.py` | Static bridge tests | Select token, add to combat. |
| DM | Roll initiative | `combatRollInitiative()` | Combat mode buttons | `rollInitiativeSelected/All` | Connected | `combat_roll_initiative` | `combat.py` | Static backend contract test | Roll selected/all. |
| DM | Previous turn | `combatPrev()` | Combat mode button | `AppUIDMActions.previousTurn()` | Connected | `combat_prev` | `combat.py` | Static bridge tests | Previous turn. |
| DM | Next/end turn | `combatNext()`, `combatEndTurn()` | Combat mode button | `AppUIDMActions.nextTurn()` | Connected | `combat_next`, `combat_end_turn` | `combat.py` | Combat UI tests | Next/end turn as DM. |
| DM | End combat/clear combat | `combatClear()` | Combat mode button | `AppUIDMActions.endCombat()` | Connected | `combat_clear` | `combat.py` | Static bridge tests | Clear combat. |
| DM | HP/AC/conditions | Token edit/combat panes | Combat and token context | Character/token runtime + `dm_context_render.js` | Partially connected; keep legacy modal | `token_hp_update`, `token_condition` | `tokens.py`, `conditions.py` | Token/condition tests | Edit HP/conditions and check sync. |
| DM | Fog of war | Fog flyout/buttons | Map Build mode / left rail | `data-dm-tool="fog-tools"`, `render/fog.js` | Connected; legacy required | `fog_toggle`, `fog_paint` | `map_editor.py` | Static guardrails | Paint/reveal/hide fog. |
| DM | Walls/doors | Editor wall tools | Map Build mode | wall/door markers and old controls | Connected; legacy required | `editor_walls_save`, `door_toggle`, `door_lock_set` | `map_editor.py` | Static guardrails | Draw wall, toggle door. |
| DM | Lighting/torches | Map/settings/editor props | Map Build mode | `lighting-weather-tools` marker | Partially connected; legacy required | map/weather/prop messages | `map_editor.py` | Missing focused tests | Place/toggle light/torch. |
| DM | Shops/chests/loot | Shop/chest views and inventory pane | Loot/Shop mode | `dm_context_render.js`, shop/chest helpers | Partially connected; legacy required | `open_shop`, `dm_configure_shop`, loot/inventory messages | `inventory.py` | Inventory integration tests | Configure shop, loot chest. |
| DM | Bestiary/library | Bestiary right tab | NPC/Monster mode and library dropdown | compact adapter + `#rtab-dropdown-library` | Connected; legacy right tab required | Creature API, `token_create` | creatures routes, `tokens.py` | Static tests | Search/spawn. |
| DM | Handouts/journal | Handout/journal tabs/forms | Session Tools mode/library | `data-dm-tool="handouts"/"journal"` | Partially connected; legacy required | `journal_*`, handout/content messages | `content.py` | Some player-event tests | Create handout/journal. |
| DM | Viewer powers approval/granting | Permission flyout/viewer powers pane | Viewer Powers mode | `AppUIDMActions.openViewerPowers/approve/reject` | Connected to legacy panel | `viewer_power_*` | `viewer_powers.py` | Integration viewer-power tests | Grant, use, approve/deny if needed. |
| DM | Debug/admin panels | Debug/right diagnostics | Debug mode only | hidden `data-dm-debug-panel` | Hidden/dev-only; keep temporarily | diagnostics/state messages | mixed | Static debug-hidden tests | Verify hidden outside debug. |
| DM | Right context panel | Old right tabs | Map-first right context + controlled legacy drawer | `dm_context_render.js`, `dm-legacy-drawer-open` | Connected with drawer adapter | n/a | n/a | Static drawer tests | Token click should update context not open old panel. |
| DM | Bottom quick strip | Old scattered buttons | Map-first quick actions | `dm_map_first_shell.js`, `dm_context_render.js` | Partially connected | mixed | mixed | Missing focused browser test | Click all visible quick actions. |
| DM | Left mode rail | Old flyouts | New left rail modes | `dm_map_first_shell.js`, `dm_panel_mode_bridge.js` | Connected | n/a | n/a | Static mode tests | Switch every mode. |
| Player | Login/character selection | `/player`, `/player/characters` | Same pre-play gateway | `server/pages/routes.py`, character templates | Connected | REST session/join | pages/session/character routes | Route tests | Login/select character. |
| Player | Character sheet/book | `play.html` sheet roots | Character book shell | `ui/character_book.js`, `character_sheet_runtime.js`, `character_sheet_container.js` | Connected; legacy root hidden | character/profile/inventory sync | character service, tokens/inventory | Character UI tests | Open book and tabs. |
| Player | Actions tab | Legacy combat/actions area | Character book Actions tab | `character/tabs/actions_tab.js` | Connected | dice/combat/inventory quick messages | combat/content/inventory | Quick-action tests | Attack/action cards. |
| Player | Quick actions | Old combat quick functions | Quick bar/modal | `combat_quick_*` modules + play bridges | Connected via legacy bridge | `combat_attack_request`, `dice_roll`, `inventory_cast_item_spell` | `combat.py`, `content.py`, `inventory.py` | Quick-action tests | Weapon, spell attack/save. |
| Player | Weapon attacks | Legacy local functions | Quick weapon modal | `combat_quick_actions.js` | Connected | `combat_attack_request`, `dice_roll` | `combat.py`, `content.py` | Quick-action tests | Roll attack/damage. |
| Player | Spell attacks | Legacy spell helpers | Quick spell modal/spells tab | `combat_quick_actions.js`, `spells_tab.js` | Connected | `combat_attack_request`, `dice_roll` | `combat.py`, `content.py` | Spell quick tests | Cast attack spell. |
| Player | Spell save/DC flow | Legacy save display | Quick spell modal | `combatQuickShowSpellSave` bridge | Connected | chat/dice/combat notices | `combat.py`, `content.py` | Character runtime tests | Cast save spell. |
| Player | Inventory | Old inventory pane | Character book Inventory tab | `inventory_tab.js` | Connected | inventory equip/use/info messages | `inventory.py` | Inventory integration tests | Equip/use/info. |
| Player | HP/AC sync | Token and sheet roots | Character book combat strip | `mapper_to_play.js`, sheet runtime | Connected; high-risk | `char_hp_update`, `token_hp_update` | `tokens.py`, character service | Mapper tests | Damage/heal and reconnect. |
| Player | Rest buttons | Legacy sheet actions | Character book/actions surfaces | play bridge + character UI | Partially connected | character/profile/inventory sync | character service/content | Missing focused role UI test | Short/long rest. |
| Player | Token ownership | Canvas token interactions | Same canvas + player shell | `play.html`, `player_shell.js` | Connected; server enforced | `token_move`, `combat_move_*` | `tokens.py`, `combat.py`, `ws_permissions.py` | Permission/token tests | Move owned vs unowned. |
| Player | Movement limits | Combat movement UI | Same live path | `play.html` + combat handlers | Connected | `combat_move_preview/commit` | `combat.py` | Movement tests | Move during own turn only. |
| Player | Combat turn permissions | Combat pane/end-turn | Character/player controls | `play.html`, tabs, quick actions | Connected | `combat_end_turn`, action economy | `combat.py`, `ws_permissions.py` | Combat UI/policy tests | Active vs inactive player. |
| Player | Chat/whispers | Inline chat | `ui/chat.js`, `ui/chat_log.js` | Connected | `chat_message` | `content.py`, WS policy | P7/P8 tests | Whisper and public chat. |
| Player | Dice roll display | Legacy log/3D dice | Chat log + dice module | `dice3d.js`, `chat_log.js` | Connected | `dice_roll`, `dice_special_fx` | `content.py` | Dice/quick tests | Roll dice and view display. |
| Viewer | Entry/watch flow | `/viewer`, `/viewer/watch` | Same viewer gateway | `server/pages/routes.py`, `viewer-entry.html` | Connected | session join/viewer | pages/session routes | Route/login tests | Enter invite as viewer. |
| Viewer | Viewer panel | Legacy viewer section | Viewer panel in play shell | `play.html` inline viewer UI | Connected but not yet extracted | `viewer_profiles_sync`, presence | `viewer_powers.py` | Viewer-power tests | Open viewer panel. |
| Viewer | Viewer roster/presence | User list/presence | Same play runtime | `play.html`, content handlers | Connected | presence/state sync | `content.py`, `viewer_powers.py` | Player-event tests | Join/leave viewer. |
| Viewer | Viewer powers list | Inline viewer powers | Same viewer panel | `play.html` | Connected; client inline remains | `viewer_power_use` | `viewer_powers.py` | Integration tests | Use granted power. |
| Viewer | Grant/revoke visibility | DM permissions panel | Viewer Powers DM mode | `dm_context_render.js` -> legacy panel | Connected | `viewer_power_grant/revoke` | `viewer_powers.py` | Integration tests | DM grant/revoke. |
| Viewer | Pending approval flow | Legacy pending approvals | Viewer Powers DM mode | `approve/reject` bridge | Connected if power requires approval | `viewer_power_approval_decision` | `viewer_powers.py` | Integration coverage partial | Use approval power, approve/deny. |
| Viewer | Cooldowns/charges | Legacy profile state | Same viewer panel | inline + server profile | Connected; server enforced | `viewer_power_use` | `viewer_powers.py` | Integration tests | Exhaust charges/cooldown. |
| Viewer | Targeting/cursor/map click | Canvas cursor/target state | Same viewer runtime | `play.html` | Connected | `viewer_cursor_update`, `viewer_power_use` | `viewer_powers.py` | Cursor integration tests | Click target/use power. |
| Viewer | FX/audio display | Legacy FX/audio | render/audio helpers | `combat_fx.js`, sound/narration modules | Connected | fx/audio/narration messages | `sound.py`, `narration.py`, `viewer_powers.py` | Audio/viewer tests partial | Observe FX/audio. |
| Viewer | Role-restricted visibility | Role gates/tabs | Reduced tab shell | `tabs.js`, `play.html` role gates | Connected; server enforced | all denied non-viewer-safe messages | `ws_permissions.py`, handlers | Policy tests | Confirm no DM/player controls visible. |

## PASS 3 — Role permission and state-sync review

- UI visibility: `tabs.js` hides player/library tabs from viewers and DM library tabs from non-DMs; DM map-first activation is gated by `ROLE === 'dm'` in `play.html`.
- Click/use permission: New DM context actions call existing legacy global functions instead of bypassing handlers. Player quick actions call play-runtime bridges. Viewer powers call viewer-specific messages only.
- Backend enforcement: `server/handlers/ws_permissions.py` and domain handlers prevent viewers from sending token/chat/player messages, prevent players from using DM editor/admin messages, and keep viewer grant/revoke DM-only.
- Server confirmation: Most live mutation flows still rely on server broadcast/session sync. This must remain; new UI adapters must not apply authoritative state locally except as preview.
- Reconnect/session sync: `/play` reconnect redirects resolve authenticated session member identity and role; this specifically guards against DM becoming Player or stale URL role hydration.
- Risk notes retained: token visibility/fog, viewer power approval/cooldown/charges, combat drawer re-open, stale quick action spell/weapon logic, HP/AC divergence, and debug panels remain high-risk and require manual multi-browser QA before deletion.

## PASS 4 — Legacy removal decision

### Safe deletions now

None. No broad old UI code should be deleted in this pass because significant legacy DOM/functions are still loaded, bridged, or called indirectly by loaded modules and inline handlers.

### Keep temporarily as compatibility bridge

- `play.html` inline globals for boot, canvas, token, combat, editor, fog, inventory, character, viewer powers, chat wrappers, and message application.
- Legacy right tabs (`party`, `inventory`, `log`, `memory`, `combat`, `shop`, `bestiary`, `spelllib`, `handouts`) because new DM UI opens them through a controlled drawer and Player/Viewer still depend on role-visible subsets.
- Left rail flyouts for editor/fog/sound/permissions/token tools because DM map-first modes still bridge to them.
- Editor-panel callback globals (`setEditorTerrain`, `setEditorBrush`, `setEditorWallTool`, `setEditorFileAsset`, `setEditorDndPropAsset`, `setEditorLayerMode`, `saveEditorMap`, `clearEditorMap`).
- Viewer power inline rendering/application until a loaded viewer panel module owns it with tests.
- Character quick-action legacy bridge functions until the quick bar no longer calls them.

### Move into new UI adapter later

- Viewer panel rendering.
- HP/AC/conditions token context details.
- Loot/shop/chest compact DM context actions.
- Lighting/torch/weather controls.
- Rest buttons and character resource refresh UI.

### Hide behind debug/dev only

- Debug/admin/diagnostics panels should remain hidden by default and reachable only through explicit DM debug mode or development hooks.

## PASS 5 — Regression test and manual QA plan

### Automated guardrails added in this pass

- Static audit tests now verify this report exists, records the local `play.html` source-of-truth warning, says there are no safe deletions, preserves legacy bridge language, and covers required DM/Player/Viewer matrix entries.
- Static load-order/role-shell tests verify the live play page loads DM, Player, Viewer/character, and WS bridge scripts in the expected order and preserves known role visibility gates.

### Manual QA still required

The environment was not driven with three browser sessions in this pass. Before deleting any old UI, perform the full checklist:

1. Open one DM browser, one Player browser, and one Viewer browser.
2. Confirm each role lands in the correct UI.
3. Click every visible button in each role and verify no dead buttons.
4. Verify no old panel unexpectedly opens and no duplicate controls appear.
5. Verify role-restricted controls are hidden and blocked server-side.
6. Run combat from start to end.
7. Spawn an NPC from bestiary.
8. Move player token in and out of fog.
9. Use quick weapon attack.
10. Use quick spell attack and save spell.
11. Use inventory item.
12. Use short rest and long rest.
13. Grant viewer power.
14. Viewer uses power.
15. DM approves/denies if required.
16. Reconnect all three roles and confirm state is still correct.

## Missing new UI connections / evidence gaps

- Lighting/torches/weather need focused tests and browser verification.
- Rest buttons need focused player UI tests and browser verification.
- Viewer panel extraction needs a dedicated loaded module and tests before inline removal.
- Loot/shop/chest compact context actions need stronger automated UI coverage.
- Manual DM/Player/Viewer multi-browser QA evidence is still missing.

## Minimal implementation decision

Only documentation and focused static guardrails were added. No backend gameplay logic was rewritten, no old UI was deleted, and no WebSocket/server authority was moved.
