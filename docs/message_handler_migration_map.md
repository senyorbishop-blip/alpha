# Message Handler Migration Map

Migrating the WebSocket message-handling section out of the
`client/templates/play.html` monolith into the already-extracted module
`client/static/js/core/message_handlers.js` (`window.AppMessageHandlers`).

## Current wiring (before migration)

Live inbound message path:

```
AppWS.onMessage(msg)
  -> AppRuntimeBridge.createMessageDispatchEnv()         (runtime_bridge.js: reportClientRuntimeError + handleLegacyMessage only)
  -> AppMessageDispatch.handleIncoming(msg, env)         (message_dispatch.js)
       -> tryHandleCombatMessage(msg, env)               (lazy-loads gameplay/combat_messages.js for 6 combat types)
       -> env.handleLegacyMessage(msg)                   (play.html: THE LIVE 152-case switch)
            -> AppMessageDispatch.handleLegacyDomainMessage(msg, __createLegacyMessageShellEnv())
               (first-hop shell: journal/party_memory/handout/story-hook/encounter/quest/prep-pack syncs)
            -> switch (msg.type) { ... 152 cases ... }    (the live source of truth)
```

`__createLegacyMessageShellEnv()` (play.html) currently exposes only the
journal/quest/prep-pack dependencies used by `handleLegacyDomainMessage`.

`message_handlers.js` (`window.AppMessageHandlers`, ~58 `handleXxx(payload, env)`
functions) is **not loaded** by play.html and **nothing calls it**.

## KEY FINDING — the module has drifted from the live inline code

`message_handlers.js` is a *stale* extraction. For the large majority of message
types, the module handler is an **older / simplified** copy that no longer
matches the current inline `case` body. Wiring those through would silently drop
behavior the inline code has since gained (revision counters, stale-payload
guards, `applyAuthoritativeTokenEvent` wrappers, token interpolation,
player-scoped-event gating, emote/party-status panel refreshes, friendly error
mapping, audio/spotlight side-effects, etc.).

Per the migration invariant ("a message must produce the exact same result after
migration as before") only handlers whose module twin is a **verified behavior
equivalent** of the inline case are migrated. Everything else is left inline with
the divergence noted below.

## Mapping table

Legend — parity: ✅ equivalent (migrate) · ⚠️ divergent (leave inline) ·
💀 no inline twin / not on the wire (dead).

| message type | inline case? | module handler | env deps used | parity | status |
|---|---|---|---|---|---|
| char_profiles_sync | yes | handleCharProfilesSync | loadCharProfiles | ✅ LOW (module reads `char_profiles \|\| profiles`; server sends `profiles`) | migrated |
| editor_layers_sync | yes | handleEditorLayersSync | setEditorLayersAll, preserveDirtyEditorContextInSync, shouldReloadEditorLayerFromSync, ensureEditorLayerLoaded | ✅ LOW | migrated |
| editor_world_sync | yes | handleEditorWorldSync | setEditor{Paths,Labels,Markers,Lights}All, ensureEditor{Paths,Labels,Markers}Loaded, refreshEditorWeatherControls, refreshEditorMapStyleControls, drawFrame | ✅ LOW | migrated |
| viewer_pending_sync | yes | handleViewerPendingSync | setViewerPendingActions, renderViewerPanel | ✅ LOW | migrated |
| viewer_fx | yes | handleViewerFx | showViewerFx | ✅ LOW | migrated |
| permission_granted | yes | handlePermissionGranted | getToken, addLogEntry, getUserId, showToast | ✅ LOW | migrated |
| journal_sync | yes | handleJournalSync | loadJournalEntries | ✅ (already routed via handleLegacyDomainMessage's journal_sync case) | left inline (already shelled) |
| library_sync | **no** | handleLibrarySync | loadLibraryEntries | 💀 server never emits `library_sync` (only `item_library_sync`) | flagged dead |
| spell_marker_saved | **no** | handleSpellMarkerSaved | setCtxSpellMarker, drawFrame | 💀 not emitted by server | flagged dead |
| spell_marker_cleared | **no** | handleSpellMarkerCleared | setCtxSpellMarker, drawFrame | 💀 not emitted by server | flagged dead |
| state_sync | yes | handleStateSync | (40+) | ⚠️ HIGH — inline is a bespoke ~290-line handler with stale guards, authoritative map-nav, char-sheet welcome-back; module is a simplified reimplementation | left inline |
| tokens_sync | yes | handleTokensSync | applyAuthoritativeTokenSync | ⚠️ HIGH — inline adds `_isStaleVisibilityPayload` guard, `applyAuthoritativeTokenSnapshot`, map-context apply, corpse_states | left inline |
| player_inventory_sync | yes | handlePlayerInventorySync | applyInventoryPayload(4 setters)+render | ⚠️ inline uses stale guard + single `applyPlayerInventoryState(p)` + `applyQuickActionsSync` | left inline |
| editor_walls_sync | yes | handleEditorWallsSync | setEditorWallsAll… | ⚠️ module omits `_wallRevision`/`_visibilityRevision` bumps + liveDebugLog | left inline |
| editor_props_sync | yes | handleEditorPropsSync | setEditorPropsAll… | ⚠️ module omits `_doorRevision`/`_visibilityRevision` bumps + liveDebugLog | left inline |
| map_settings_sync | yes | handleMapSettingsSync | setMapSettingsAll… | ⚠️ module omits applyGridSizeFromSettings, ping-permission UI, `_syncFogUI` | left inline |
| fog_state | yes | handleFogState | fogApplyState | ⚠️ inline uses `applyAuthoritativeFogState` + liveDebugLog + drawFrame; module path differs | left inline |
| fog_update | yes | handleFogUpdate | applyFogUpdate | ⚠️ same divergence as fog_state | left inline |
| poi_created | yes | handlePoiCreated | resolvePoiPayload… | ⚠️ inline role-splits `poi_dm`/`poi` + pending map upload/blank-map/pin logic | left inline |
| poi_updated | yes | handlePoiUpdated | resolvePoiPayload… | ⚠️ inline uses `_currentPoi`, ScenePersistence logging, loadMapImage | left inline |
| poi_deleted | yes | handlePoiDeleted | deletePoi, isPoiPopupOpenFor, poiPopupClose | ⚠️ bridgeable, but kept with the rest of the POI cluster (low value) | left inline |
| local_map_enter | yes | handleLocalMapEnter | enterLocalMap… | ⚠️ inline integrates applyAuthoritativeMapContext + fog + token snapshot | left inline |
| local_map_exit | yes | handleLocalMapExit | exitLocalMap… | ⚠️ same integration as local_map_enter | left inline |
| bring_all_to_map | yes | handleBringAllToMap | enterLocalMap, showToast | ⚠️ inline calls inline `handleLocalMapEnter`; module reimplements | left inline |
| viewer_profiles_sync | yes | handleViewerProfilesSync | setViewerProfiles, renderViewerPanel | ⚠️ module omits `_startViewerCooldownTimer()` | left inline |
| viewer_power_catalog_sync | yes | handleViewerPowerCatalogSync | setViewerPowerCatalog, renderViewerPanel | ⚠️ module omits `assistantDmPermissions` update | left inline |
| hazard_zones_sync | yes | handleHazardZonesSync | setHazardZones, renderHazardZones, drawFrame | ⚠️ module omits `_hazardEditZoneId` reset | left inline |
| viewer_power_status | yes | handleViewerPowerStatus | showToast | ⚠️ module omits `_streamFriendlyDiagnostic` on reject | left inline |
| error | yes | handleErrorMessage | showToast | ⚠️ module omits friendly-message mapping + `_streamFriendlyDiagnostic` | left inline |
| item_library_sync | yes | handleItemLibrarySync | loadItemLibraryEntries | ⚠️ module omits srd_items handling + `publishCharacterBuilderItemLibrary` | left inline |
| chat_message | yes | handleChatMessage | addLogEntry, showToast… | ⚠️ module omits whisper channel + `channel` field | left inline |
| user_joined | yes | handleUserJoined | getUsers, render… | ⚠️ module keys by `user.id` not `handle`; omits buildStagingArea, AppUIChat env, refreshPrivateStoryHookPlayerDropdown | left inline |
| user_left | yes | handleUserLeft | getUsers, render… | ⚠️ same divergence as user_joined | left inline |
| map_changed | yes | handleMapChanged | setWorldMapLayers, loadMapImage… | ⚠️ inline uses context guard + console logging; module uses world_map_layers branch | left inline |
| map_ping | yes | handleMapPing | addPing | ⚠️ inline passes mode/user_name/user_role/map_context; module passes x/y/color only | left inline |
| ruler_shown | yes | handleRulerShown | showRemoteRuler | ⚠️ no `showRemoteRuler` inline; inline mutates `ruler.*` + timeout | left inline |
| token_image_updated | yes | handleTokenImageUpdated | getToken, preloadTokenImage, drawFrame | ⚠️ module also sets imageFit/zoom/offsets (inline does not) — diverges both directions | left inline |
| token_created | yes | handleTokenCreated | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent`, uses `_currentPoi`, renderTokenEmotePanel | left inline |
| token_placed | yes | handleTokenPlaced | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent` + renderTokenEmotePanel | left inline |
| token_moved | yes | handleTokenMoved | (many) | ⚠️ inline adds stale guard, drag-active guard, token interpolation, snap heuristics | left inline |
| token_move_denied | yes | handleTokenMoveDenied | setCombatMovement, renderCombat | ⚠️ combat-intercepted; inline uses `_clearCombatMovePlan` + `forceCombatStateUISync` | left inline |
| token_hidden_changed | yes | handleTokenHiddenChanged | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent`, `_currentPoi`, emote panel | left inline |
| token_sent_to_staging | yes | handleTokenSentToStaging | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent` + emote panel | left inline |
| token_removed_hidden | yes | handleTokenRemovedHidden | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent` + emote panel | left inline |
| token_deleted | yes | handleTokenDeleted | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent` + clearPendingTokenMove + renderPartyStatusPanel | left inline |
| token_hp_updated | yes | handleTokenHpUpdated | (many) | ⚠️ inline wraps in `applyAuthoritativeTokenEvent`, corpse_state, back-up toast, party panel | left inline |
| token_edited | yes | handleTokenEdited | getLiveToken, getStagingToken, cacheTokenByContext | ⚠️ marginal; token mutation kept inline for safety | left inline |
| token_condition_changed | yes | handleTokenConditionChanged | (several) | ⚠️ inline uses `_condTarget`/`_renderCondGrid` + renderPartyStatusPanel | left inline |
| combat_move_state | yes | handleCombatMoveState | setCombatMovement, renderCombat | ⚠️ combat-intercepted; inline uses `_clearCombatMovePlan` + `forceCombatStateUISync` | left inline |
| combat_attack_result | yes | handleCombatAttackResult | addLogEntry, showCombatAttackResult | ⚠️ combat-intercepted; inline shows result card + spotlight + damage modal | left inline |
| combat_state | yes | handleCombatState | combatApplyState | ⚠️ combat-intercepted; inline uses `handleCombatStateLive` | left inline |
| char_hp_update | yes | handleCharHpUpdate | findTokenByOwnerId… | ⚠️ inline updates ALL owned tokens + `_charSheet` + refreshCharSummary + party panel | left inline |
| dice_result | yes | handleDiceResult | addLogEntry, appDiceSync… | ⚠️ inline adds initiative apply, ready-queue, broadcast audio, spotlight | left inline |
| prop_action_result | yes | handlePropActionResult | showToast, refreshPropInventoryModal | ⚠️ inline gates on `__handlePlayerScopedUiEvent` + ChestView | left inline |
| inventory_action_result | yes | handleInventoryActionResult | showToast, renderInventoryPanel | ⚠️ inline gates on `__handlePlayerScopedUiEvent` + setInventoryActionFeedback | left inline |
| spell_marker_add | yes | handleSpellMarkerAdd | getSpellMarkers, setSpellMarkers | ⚠️ module pushes a `{...payload}` copy into a fresh array; inline ref-pushes into the global — kept inline to preserve reference semantics | left inline |
| spell_marker_remove | yes | handleSpellMarkerRemove | getSpellMarkers, setSpellMarkers | ⚠️ kept inline with spell_marker_add cluster | left inline |
| spell_marker_clear | yes | handleSpellMarkerClear | setSpellMarkers | ⚠️ kept inline with spell_marker_add cluster | left inline |

### Combat-intercepted note

`combat_state`, `combat_attack_result`, `combat_move_state`, `token_move_denied`,
`combat_move_preview_result`, `combat_initiative_rolled` are routed to
`gameplay/combat_messages.js` (`AppCombatMessages`) **before** `handleLegacyMessage`
in `handleIncoming`. They are out of scope for this `AppMessageHandlers`
migration and stay on the existing combat path.

## Migrated handlers (live path = AppMessageHandlers)

These 6 types are now delegated by `AppMessageDispatch.handleLegacyDomainMessage`
to `window.AppMessageHandlers.*`; their inline `case` blocks have been removed
from `handleLegacyMessage`:

- char_profiles_sync → handleCharProfilesSync
- editor_layers_sync → handleEditorLayersSync
- editor_world_sync → handleEditorWorldSync
- viewer_pending_sync → handleViewerPendingSync
- viewer_fx → handleViewerFx
- permission_granted → handlePermissionGranted
