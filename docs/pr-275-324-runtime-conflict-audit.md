# PR #275-#324 Runtime Conflict Audit

Generated from local merge commits with `git diff <merge^1> <merge^2>` and hunk/function headers. This is an audit only; it intentionally does not fix runtime code.

## Source-of-truth files used

- `docs/repo-map.md`
- `docs/system-audit-20260320.md`
- `main.py`
- `client/templates/play.html`
- `server/handlers/__init__.py`
- Relevant focused frontend/backend files named below.

## Headline findings

- Player boot had overlapping ownership in `play.html`, `boot_shell.js`, `dm_assistant.js`, `cartographer.js`, `tts_client.js`, `sound_engine.js`, and `dice3d.js`; PR #317-#324 repeatedly made player boot lighter, which indicates the path was broken by DM-only/expensive startup work.
- Quick weapon damage has two active paths: the module path in `client/static/js/character/combat_quick_actions.js` and bridge/shim functions in `client/templates/play.html`; both export overlapping public names.
- Autosave recursion fixes landed after render and quick-pick changes; `renderPlayerActionsHub` and profile autosave/collection live in the same large runtime and must not be coupled further.
- Initiative has two competing update paths: full `combat_state`/`combatApplyState` and patch-style `combat_initiative_rolled`/`applyCombatInitiativeRolled`. PR #296-#323 repeatedly patched this area.
- Fog authority is mixed: server-side visibility/fog broadcasts exist, but client fog state/update functions and direct `requestCombatFogSyncDebounced` calls still initiate sync from multiple client events.

## Functions changed three or more times

| File | Function/header | PRs |
|---|---|---|
| `client/static/js/character/combat_quick_actions.js` | `<top-level>` | #276, #279, #283, #284, #287, #288, #290, #293 |
| `client/static/js/character/combat_quick_bar.js` | `<top-level>` | #280, #281, #284, #288, #317, #318, #319 |
| `client/static/js/character/combat_quick_selectors.js` | `<top-level>` | #280, #282, #284, #319, #320 |
| `client/static/js/core/message_dispatch.js` | `<top-level>` | #304, #310, #315 |
| `client/static/js/core/runtime_bridge.js` | `<top-level>` | #307, #310, #313 |
| `client/static/js/core/ws.js` | `<top-level>` | #307, #310, #313, #315, #316, #317 |
| `client/static/js/render/fog.js` | `<top-level>` | #285, #286, #323 |
| `client/static/js/render/vision.js` | `<top-level>` | #292, #293, #317 |
| `client/templates/play.html` | `<top-level>` | #277, #306, #307, #313, #316, #317 |
| `client/templates/play.html` | `_combatInitiativeSignature` | #301, #303, #311 |
| `client/templates/play.html` | `_executeCombatSpellCast` | #279, #280, #283, #284, #287, #293, #305, #306 |
| `client/templates/play.html` | `combatQuickRollSpellAttack` | #282, #283, #284, #293 |
| `client/templates/play.html` | `combatQuickRollWeaponDamage` | #282, #283, #288 |
| `client/templates/play.html` | `combatQuickShowSpellSave` | #279, #283, #284, #287, #305 |
| `client/templates/play.html` | `combatRollDeathSave` | #300, #307, #312, #313 |
| `client/templates/play.html` | `combatRollInitiative` | #298, #299, #300, #307 |
| `client/templates/play.html` | `executeCombatQuickBarSpell` | #281, #282, #283 |
| `client/templates/play.html` | `loadSavedDiscoveries` | #285, #286, #292, #293, #298, #302, #303, #304, #307, #312, #313, #319 |
| `client/templates/play.html` | `removeSpellAt` | #285, #291, #292, #296, #297, #298, #300, #302, #303, #315, #319 |
| `client/templates/play.html` | `togglePlayerActionsHub` | #289, #290, #297, #303, #310, #315, #319, #320 |
| `main.py` | `api_cartographer_generate_interior` | #307, #310, #313 |
| `server/handlers/__init__.py` | `from server.handlers.summons import (` | #285, #295, #300 |
| `server/handlers/combat.py` | `_current_combat_map_context` | #289, #290, #292, #293 |
| `server/handlers/combat.py` | `_sort_combatants_preserving_turn` | #285, #291, #292 |
| `server/handlers/combat.py` | `from server.encumbrance import ENC_HEAVY` | #292, #293, #310 |
| `server/handlers/combat.py` | `from server.movement import resolve_movement, normalize_movement_mode` | #291, #292, #295 |
| `server/handlers/combat.py` | `handle_combat_death_save` | #291, #292, #294, #295, #298, #300, #307, #308, #309, #310 |
| `server/handlers/combat.py` | `handle_combat_next` | #291, #292, #308, #309 |
| `server/handlers/combat.py` | `handle_combat_remove_combatant` | #285, #291, #292, #298 |
| `server/handlers/combat.py` | `sync_fogged_combatants` | #289, #291, #292 |
| `server/handlers/common.py` | `_sync_combatant_token_state` | #285, #289, #290, #292, #293, #302, #310, #311 |
| `server/handlers/map_editor.py` | `handle_door_lock_set` | #285, #292, #293 |
| `server/handlers/map_editor.py` | `handle_fog_toggle` | #285, #292, #293 |
| `server/handlers/tokens.py` | `_deny_player_single_token_limit` | #285, #292, #293 |
| `server/session.py` | `User` | #285, #289, #290, #292, #293 |
| `tests/test_combat_initiative_live_sync_client.py` | `_run` | #296, #297, #301 |
| `tests/test_combat_initiative_live_sync_client.py` | `test_initiative_roll_refreshes_token_and_party_surfaces_without_reload` | #299, #300, #302, #303 |
| `tests/test_combat_initiative_live_sync_client.py` | `test_lower_revision_with_changed_initiative_applies_with_warning` | #301, #302, #309 |
| `tests/test_combat_roll_initiative_sync.py` | `<top-level>` | #291, #292, #294, #295 |

## PR file/function matrix

### PR #275

- `client/static/js/character/spell_runtime.js`: `<top-level>`
- `client/static/js/character/tabs/spells_tab.js`: `_spellAttackSaveLabel`
- `tests/test_spell_scaling_and_dice_consistency.py`: `vm.runInThisContext(fs.readFileSync('./client/static/js/character/tabs/spells_ta`

### PR #276

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/static/js/character/spell_runtime.js`: `<top-level>`
- `tests/test_spell_scaling_and_dice_consistency.py`: `console.log(JSON.stringify({expr: global.SpellsTab.__test.spellRollExpressionFor`

### PR #277

- `client/static/js/ui/onboarding.js`: `<top-level>`
- `client/static/js/ui/tabs.js`: `<top-level>`
- `client/templates/play.html`: `<top-level>`, `drawTokenBadgeRows`

### PR #278

- `client/templates/play.html`: `inspectInventoryItem`
- `server/character/import_normalizer.py`: `_range_from_definition`, `_normalize_pdf_skills`, `_parse_pdf_equipment_line`
- `server/utils/pdf_parser.py`: `import re`
- `tests/test_character_import_normalizer.py`: `test_imported_barbarian_rage_marks_matched_when_native_exists`

### PR #279

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/templates/play.html`: `_combatQuickSlug`, `combatQuickShowSpellSave`, `_executeCombatSpellCast`
- `tests/test_combat_quick_weapon_bridge_ui.py`: `<top-level>`

### PR #280

- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/static/js/character/combat_quick_selectors.js`: `<top-level>`
- `client/static/js/character/tabs/actions_tab.js`: `<top-level>`
- `client/templates/play.html`: `_extractActionLines`, `_resolveSummonActionEntryById`, `_getCombatQuickSpells`, `_executeCombatSpellCast`
- `server/handlers/inventory.py`: `handle_inventory_use_item_action`, `_build_item_spell_cards`

### PR #281

- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/templates/play.html`: `executeCombatQuickBarSpell`
- `tests/test_combat_quick_weapon_bridge_ui.py`: `test_combat_quick_bar_passes_full_action_object_to_weapon_bridge`, `test_find_combat_weapon_is_a_shared_lookup_supporting_objects_ids_and_names`

### PR #282

- `client/static/js/character/combat_quick_selectors.js`: `<top-level>`
- `client/static/js/character/runtime/character_sheet_runtime.js`: `_csrItemIsAttuned`, `_csrNormalizeRuntimeRuntime`
- `client/templates/play.html`: `executeCombatQuickBarSpell`, `_combatQuickSpellBaseLevel`, `combatQuickRollSpellAttack`, `combatQuickRollWeaponDamage`, `window.resolveSpellCast = resolveSpellCast;`
- `server/handlers/inventory.py`: `_EQUIPMENT_META_KEYS = (`, `_ITEM_RECHARGE_TYPES = {"long_rest", "dawn", "daily", "none"}`, `handle_inventory_use_item_action`, `_build_item_spell_cards`

### PR #283

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/templates/play.html`: `getCombatQuickBarSpells`, `executeCombatQuickBarSpell`, `combatQuickRollSpellAttack`, `combatQuickShowSpellSave`, `combatQuickRollWeaponDamage`, `_executeCombatSpellCast`, `resolveWeaponRuntime`, `window.findCombatSpell = findCombatSpell;`
- `tests/test_refactor.py`: `import inspect`, `test_combat_roster_survives_stacked_combat_tools_with_internal_scroll`

### PR #284

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/static/js/character/combat_quick_selectors.js`: `<top-level>`
- `client/templates/play.html`: `_consumeInventoryAttackResources`, `performExecuteCombatQuickBarSpell`, `_parseSpellLevelFromSection`, `combatQuickRollSpellAttack`, `combatQuickShowSpellSave`, `_executeCombatSpellCast`, `guardQuickActionBridge`, `combatQuickCastSpellBridge`

### PR #285

- `client/static/js/render/fog.js`: `<top-level>`
- `client/templates/play.html`: `const _PING_STACK_HARD_CAP = 28;`, `let _combatRound = 1;`, `loadSavedDiscoveries`, `fogPaintAt`, `removeSpellAt`
- `server/handlers/__init__.py`: `from server.handlers.tokens import (`, `from server.handlers.summons import (`
- `server/handlers/combat.py`: `_has_encumbrance_attack_disadvantage`, `_sort_combatants_preserving_turn`, `handle_combat_remove_combatant`
- `server/handlers/common.py`: `_sync_combatant_token_state`
- `server/handlers/map_editor.py`: `from server.session import filter_editor_props_for_role`, `handle_door_lock_set`, `handle_fog_toggle`
- `server/handlers/tokens.py`: `from server.handlers.conditions import (`, `_deny_player_single_token_limit`, `handle_token_move`, `handle_token_placed`, `handle_token_send_to_staging`
- `server/persistence_schema.py`: `_clamp_float`
- `server/session.py`: `User`
- `tests/test_combat_fog_sync.py`: `<top-level>`

### PR #286

- `client/static/js/render/fog.js`: `<top-level>`
- `client/templates/play.html`: `_combatFogVisibleNpcHash`, `dmCompanionNudgeHp`, `placeBeastMasterCompanionToken`, `loadSavedDiscoveries`, `quickPanelOpenTokenEditor`, `fogPaintAt`
- `server/handlers/combat.py`: `run_combat_fog_sync`
- `tests/test_combat_fog_sync.py`: `test_hidden_npc_in_fog_keeps_multiple_suspension_reasons_until_clear`
- `tests/test_combat_fog_sync_client.py`: `<top-level>`

### PR #287

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/templates/play.html`: `_canUseVersatileAttackMode`, `_combatQuickSlug`, `getCombatSpellDamagePreview`, `combatQuickShowSpellSave`, `_executeCombatSpellCast`
- `tests/test_combat_quick_bar_ui.py`: `test_combat_quick_spell_upcast_options_scale_damage_by_slot_level`

### PR #288

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/templates/play.html`: `combatQuickRollWeaponDamage`
- `tests/test_combat_quick_weapon_bridge_ui.py`: `test_open_combat_quick_bar_weapon_action_bridges_to_combat_quick_actions`, `test_find_combat_weapon_is_a_shared_lookup_supporting_objects_ids_and_names`, `test_used_this_turn_weapon_still_opens_modal_with_explanation`
- `tests/test_weapon_action_rolling.py`: `test_crit_formula_doubles_weapon_dice`

### PR #289

- `client/templates/play.html`: `togglePlayerActionsHub`, `renderCombat`
- `server/handlers/combat.py`: `_current_combat_map_context`, `_token_occupied_fog_indices`, `_ensure_suspended_lists`, `_adjust_turn_after_removal`, `sync_fogged_combatants`
- `server/handlers/common.py`: `_sync_combatant_token_state`
- `server/session.py`: `User`
- `tests/test_integration_combat_tab.py`: `test_combat_remove_combatant_without_ending_combat`

### PR #290

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/templates/play.html`: `renderImportedItemDetailRows`, `renderImportedItemCharges`, `useInventoryItemActionFromInspect`, `renderInventoryEquipmentSummary`, `normalizePlayerInventoryEntry`, `_consumeInventoryAttackResources`, `togglePlayerActionsHub`, `renderCombat`
- `server/data/rules/5e2024/items/very_rare_magic_items.json`: `<top-level>`
- `server/handlers/combat.py`: `_current_combat_map_context`, `_token_occupied_fog_indices`, `_ensure_suspended_lists`, `_adjust_turn_after_removal`, `sync_combat_visibility`
- `server/handlers/common.py`: `_sync_combatant_token_state`
- `server/handlers/inventory.py`: `from server.handlers.common import (`, `_build_known_item_runtime`, `_looks_like_creature_inventory_entry`
- `server/item_compendium.py`: `filter_items`, `_LIVE_STATE_KEYS = frozenset({`
- `server/session.py`: `User`
- `tests/test_integration_combat_tab.py`: `test_combat_add_token_requires_current_map_server_side`
- `tests/test_item_compendium_catalog.py`: `test_thunder_staff_has_correct_bonus`
- `tests/test_item_spell_system.py`: `test_item_compendium_loads_rods`

### PR #291

- `client/templates/play.html`: `removeSpellAt`
- `server/handlers/combat.py`: `from server.movement import resolve_movement, normalize_movement_mode`, `sync_fogged_combatants`, `_sort_combatants_preserving_turn`, `handle_combat_add_token`, `handle_combat_remove_combatant`, `handle_combat_update`, `handle_combat_next`, `handle_combat_death_save`
- `tests/test_combat_initiative_live_sync_client.py`: `<top-level>`
- `tests/test_combat_roll_initiative_sync.py`: `<top-level>`

### PR #292

- `client/static/js/render/vision.js`: `<top-level>`
- `client/templates/play.html`: `let _combatRound = 1;`, `_isRectVisibleToPlayer`, `loadSavedDiscoveries`, `removeSpellAt`
- `server/handlers/combat.py`: `from server.encumbrance import ENC_HEAVY`, `from server.movement import resolve_movement, normalize_movement_mode`, `_combat_fog_mode`, `_current_combat_map_context`, `sync_fogged_combatants`, `_sort_combatants_preserving_turn`, `handle_combat_add_token`, `handle_combat_remove_combatant`, `handle_combat_update`, `handle_combat_next`, `handle_combat_death_save`
- `server/handlers/common.py`: `_is_dm_token`, `_can_user_see_token`, `_broadcast_token_event`, `_visible_tokens_payload_for_user`, `_sanitize_save_bonuses`, `_sync_combatant_token_state`
- `server/handlers/map_editor.py`: `handle_door_lock_set`, `handle_fog_toggle`
- `server/handlers/tokens.py`: `_deny_player_single_token_limit`
- `server/session.py`: `User`
- `tests/test_combat_initiative_live_sync_client.py`: `<top-level>`
- `tests/test_combat_roll_initiative_sync.py`: `<top-level>`
- `tests/test_unit_utility_functions.py`: `test_is_dm_token_with_owner`, `test_can_user_see_token_dm_always_sees`, `test_can_user_see_token_player_cannot_see_hidden`, `test_can_user_see_token_player_sees_visible`

### PR #293

- `client/static/js/character/combat_quick_actions.js`: `<top-level>`
- `client/static/js/render/vision.js`: `<top-level>`
- `client/templates/play.html`: `let _combat = { active: false, turn: 0, combatants: [], movement: null, selected`, `_isRectVisibleToPlayer`, `loadSavedDiscoveries`, `performExecuteCombatQuickBarSpell`, `combatQuickRollSpellAttack`, `_combatQuickCriticalFormula`, `_executeCombatSpellCast`, `guardQuickActionBridge`, `combatQuickCastSpellBridge`
- `server/handlers/camp_rest.py`: `handle_camp_rest_clear_activity`
- `server/handlers/combat.py`: `from server.encumbrance import ENC_HEAVY`, `_combat_fog_mode`, `_current_combat_map_context`
- `server/handlers/common.py`: `_is_dm_token`, `_can_user_see_token`, `_broadcast_token_event`, `_visible_tokens_payload_for_user`, `_sanitize_save_bonuses`, `_sync_combatant_token_state`
- `server/handlers/inventory.py`: `_ITEM_ACTION_ACTIVATION_TYPES = {"action", "bonus_action", "reaction", "free", "`, `_recompute_equipment_effects`
- `server/handlers/map_editor.py`: `handle_door_lock_set`, `handle_fog_toggle`
- `server/handlers/tokens.py`: `_deny_player_single_token_limit`
- `server/session.py`: `User`
- `tests/test_combat_quick_weapon_bridge_ui.py`: `test_combat_quick_bar_passes_full_action_object_to_weapon_bridge`, `test_open_weapon_action_passes_full_card_object_to_roll_helpers`
- `tests/test_item_spell_system.py`: `test_string_granted_spell_generates_card`
- `tests/test_quick_action_spell_upcast_and_bar.py`: `test_quick_actions_use_shared_resolve_spell_cast_payload_and_selected_slot`
- `tests/test_unit_utility_functions.py`: `test_is_dm_token_with_owner`, `test_can_user_see_token_dm_always_sees`, `test_can_user_see_token_player_cannot_see_hidden`, `test_can_user_see_token_player_sees_visible`
- `tests/test_weapon_action_rolling.py`: `test_missing_weapon_ui_bridge_logs_error`, `test_quick_bar_weapon_source_separated_from_playeruseaction_fallback`, `test_action_economy_spent_after_result_card_not_before`, `test_roll_error_caught_and_action_not_spent`, `test_combat_result_card_has_click_to_dismiss`, `test_spell_attack_roll_shows_combat_result_card`, `test_spell_damage_roll_shows_combat_result_card`, `test_weapon_attack_result_logged_to_chat`, `test_resolve_weapon_runtime_applies_magic_bonus`, `test_crit_formula_doubles_weapon_dice`

### PR #294

- `server/handlers/combat.py`: `server/handlers/combat.py — Combat state management helpers and handlers.`, `from server.handlers.common import (`, `handle_combat_death_save`
- `tests/test_combat_roll_initiative_sync.py`: `<top-level>`, `from server.session import Session, Token, User`, `test_dm_can_roll_npc_initiative`

### PR #295

- `client/static/js/character/character_sheet_container.js`: `<top-level>`, `_renderExtrasTab`, `_renderOverviewPanel`
- `client/templates/play.html`: `stepCharacterBookPage`, `_restoreNativeResourcesForRest`
- `server/handlers/__init__.py`: `from server.handlers.ai_dm import (`, `from server.handlers.summons import (`
- `server/handlers/camp_rest.py`: `handle_camp_rest_spend_hit_die`
- `server/handlers/combat.py`: `server/handlers/combat.py — Combat state management helpers and handlers.`, `from server.movement import resolve_movement, normalize_movement_mode`, `handle_combat_death_save`
- `tests/test_combat_roll_initiative_sync.py`: `<top-level>`, `from server.session import Session, Token, User`, `test_player_can_only_roll_own_initiative`

### PR #296

- `client/templates/play.html`: `removeSpellAt`
- `tests/test_combat_initiative_live_sync_client.py`: `_run`, `refreshRightPanelContextUI`, `test_equal_revision_with_different_payload_still_applies`

### PR #297

- `client/templates/play.html`: `removeSpellAt`, `_isActiveCombatTab`, `_safeActionEconomyCount`, `_getExtraAttackTotalFromSheet`, `togglePlayerActionsHub`
- `tests/test_combat_initiative_live_sync_client.py`: `_run`, `refreshRightPanelContextUI`, `test_stale_lower_revision_is_ignored`
- `tests/test_refactor.py`: `test_combat_coach_can_be_collapsed_by_players`

### PR #298

- `client/templates/play.html`: `let _playerActionsDensity = 'comfortable';`, `loadSavedDiscoveries`, `removeSpellAt`, `_findMyActiveCombatant`, `_getExtraAttackTotalFromSheet`, `_combatTokenPayload`, `combatRollInitiative`
- `server/handlers/combat.py`: `import time as _time`, `handle_combat_remove_combatant`, `handle_combat_prev`, `handle_combat_death_save`
- `tests/test_integration_combat_tab.py`: `test_combat_visibility_sweep_is_idempotent_without_duplicates`

### PR #299

- `client/templates/play.html`: `combatRollInitiative`
- `tests/test_combat_initiative_live_sync_client.py`: `console.log(JSON.stringify({{ calls, combat: _combat }}));`, `test_initiative_roll_refreshes_token_and_party_surfaces_without_reload`

### PR #300

- `client/templates/play.html`: `removeSpellAt`, `combatRollDeathSave`, `combatRollInitiative`
- `server/handlers/__init__.py`: `from server.handlers.tokens import (`, `from server.handlers.summons import (`
- `server/handlers/combat.py`: `handle_combat_death_save`
- `tests/test_combat_initiative_live_sync_client.py`: `PLAY = ROOT / "client/templates/play.html"`, `_updateCombatTabAttention`, `let _combatRound = 1;`, `console.log(JSON.stringify({{ calls, combat: _combat }}));`, `renderCombat`, `_sortCombatants`, `test_dm_npc_initiative_roll_updates_player_panel_without_refresh`, `test_initiative_roll_refreshes_token_and_party_surfaces_without_reload`, `test_initiative_event_preserves_current_turn_after_resort`
- `tests/test_combat_roll_initiative_sync.py`: `test_suspended_combatants_filtered_for_player_via_broadcast_combat`
- `tests/test_refactor.py`: `test_play_html_initiative_roll_preserves_raw_d20_display`

### PR #301

- `client/templates/play.html`: `_tokenBadgeTruncateText`, `layoutTokenBadges`, `_combatInitiativeSignature`
- `tests/test_combat_initiative_live_sync_client.py`: `_run`, `drawFrame`, `test_equal_revision_with_different_payload_still_applies`, `test_lower_revision_with_changed_initiative_applies_with_warning`

### PR #302

- `client/templates/play.html`: `layoutTokenBadges`, `loadSavedDiscoveries`, `removeSpellAt`
- `server/handlers/common.py`: `_sync_combatant_token_state`
- `tests/test_combat_initiative_live_sync_client.py`: `test_initiative_roll_refreshes_token_and_party_surfaces_without_reload`, `test_lower_revision_with_changed_initiative_applies_with_warning`

### PR #303

- `client/templates/play.html`: `let _combat = { active: false, turn: 0, combatants: [], movement: null, selected`, `loadSavedDiscoveries`, `removeSpellAt`, `_combatInitiativeSignature`, `togglePlayerActionsHub`
- `tests/test_combat_initiative_live_sync_client.py`: `let _combatRound = 1;`, `_sortCombatants`, `test_initiative_roll_refreshes_token_and_party_surfaces_without_reload`

### PR #304

- `client/static/js/core/message_dispatch.js`: `<top-level>`
- `client/templates/play.html`: `let _clientNavIntent = (_runtimeStore && _runtimeStore.get) ? (_runtimeStore.get`, `safeClientCall`, `drawLoop`, `_buildBlankMapImage`, `renderHazardZones`, `loadSavedDiscoveries`, `fogHideAll`
- `tests/test_refactor.py`: `test_quick_action_bridges_are_guarded_and_non_recursive`

### PR #305

- `client/templates/play.html`: `combatQuickShowSpellSave`, `_executeCombatSpellCast`
- `tests/test_refactor.py`: `test_player_map_render_and_image_loading_are_coalesced`

### PR #306

- `client/templates/play.html`: `<top-level>`, `__createLegacyRenderBootEnv`, `getCanvasPointer`, `_confirmPendingMoveConfirm`, `onMouseDown`, `refreshCharSummary`, `handleSpeciesSelectionChanged`, `buildCharacterBookSeedData`, `performCombatQuickRollSpellDamage`, `_executeCombatSpellCast`
- `tests/test_refactor.py`: `test_message_dispatch_has_stack_overflow_diagnostics_and_depth_guard`
- `tests/test_token_hover_stats_ui.py`: `<top-level>`

### PR #307

- `client/static/js/core/runtime_bridge.js`: `<top-level>`
- `client/static/js/core/ws.js`: `<top-level>`
- `client/templates/play.html`: `<top-level>`, `__createLegacyRenderBootEnv`, `getMouseWorld`, `_confirmPendingMoveConfirm`, `onMouseDown`, `refreshCharSummary`, `loadSavedDiscoveries`, `handleSpeciesSelectionChanged`, `seedCharacterBookFromCurrentState`, `combatRollDeathSave`, `combatRollInitiative`
- `main.py`: `api_cartographer_generate_interior`
- `server/handlers/combat.py`: `handle_combat_death_save`
- `tests/test_combat_initiative_dice_popup_client.py`: `<top-level>`
- `tests/test_combat_roll_initiative_sync.py`: `test_player_own_roll_reaches_player_and_dm_via_send_to`
- `tests/test_token_hover_stats_ui.py`: `<top-level>`
- `tests/test_ws_heartbeat_pong_client.py`: `<top-level>`
- `tests/test_ws_heartbeat_server.py`: `<top-level>`

### PR #308

- `server/handlers/combat.py`: `_handle_combat_move_plan`, `_combatant_from_token`, `handle_combat_next`, `handle_combat_death_save`
- `tests/test_combat_initiative_live_sync_client.py`: `test_token_badge_renderer_reads_initiative_from_combatant_state`
- `tests/test_combat_roll_initiative_sync.py`: `test_roll_initiative_increments_combat_revision`, `test_combat_state_request_replies_to_requesting_user_with_current_stat`

### PR #309

- `client/templates/play.html`: `_rollExpressionAndResolveDice`
- `server/handlers/combat.py`: `_handle_combat_move_plan`, `_combatant_from_token`, `handle_combat_next`, `handle_combat_death_save`
- `tests/test_combat_initiative_live_sync_client.py`: `test_lower_revision_with_changed_initiative_applies_with_warning`
- `tests/test_combat_roll_initiative_sync.py`: `test_roll_initiative_increments_combat_revision`, `test_roll_initiative_authoritative_value_matches_dice_result`

### PR #310

- `client/static/js/core/message_dispatch.js`: `<top-level>`
- `client/static/js/core/runtime_bridge.js`: `<top-level>`
- `client/static/js/core/ws.js`: `<top-level>`
- `client/templates/play.html`: `togglePlayerActionsHub`
- `main.py`: `api_cartographer_generate_interior`
- `server/connections.py`: `import json`, `from typing import Dict, Set, Optional`, `from fastapi import WebSocket`
- `server/handlers/combat.py`: `from server.encumbrance import ENC_HEAVY`, `handle_combat_death_save`, `handle_combat_roll_initiative`
- `server/handlers/common.py`: `_sync_combatant_token_state`
- `tests/test_combat_roll_initiative_sync.py`: `test_mid_combat_initialized_reroll_preserves_locked_active_turn`

### PR #311

- `client/templates/play.html`: `handleCombatStateLive`, `_combatInitiativeSignature`
- `server/handlers/common.py`: `_sync_combatant_token_state`
- `tests/test_combat_fog_sync.py`: `<top-level>`, `test_hidden_npc_combatant_moves_to_suspended_and_restores_when_unhidden`
- `tests/test_combat_initiative_live_sync_client.py`: `test_actual_incoming_dispatch_combat_state_from_self_roll_applies`, `test_token_badge_renderer_reads_initiative_from_combatant_state`, `sendWS`, `_renderCombatRoster(list, roster, true);`

### PR #312

- `client/templates/play.html`: `loadSavedDiscoveries`, `combatRollDeathSave`, `let _combatInitiativeResyncTimer = null;`
- `tests/test_combat_initiative_live_sync_client.py`: `_run_initiative_event`, `renderCombat`, `test_actual_incoming_dispatch_dm_npc_roll_updates_dm_client`

### PR #313

- `client/static/js/core/runtime_bridge.js`: `<top-level>`
- `client/static/js/core/ws.js`: `<top-level>`
- `client/templates/play.html`: `<top-level>`, `loadSavedDiscoveries`, `fogSaveCurrentMap`, `fogFlushBatch`, `forceCombatStateUISync`, `combatRollDeathSave`
- `main.py`: `api_cartographer_generate_interior`
- `server/handlers/combat.py`: `handle_combat_prev`
- `tests/test_ws_reconnect_regression.py`: `<top-level>`

### PR #314

- `main.py`: `api_ai_generate_map`
- `server/connections.py`: `import logging`, `logger = logging.getLogger(__name__)`
- `tests/test_ws_heartbeat_server.py`: `test_last_seen_not_updated_on_undecodable_frame`
- `tests/test_ws_lifecycle_hardening.py`: `test_ws_core_installs_lifecycle_and_stale_socket_guards`
- `tests/test_ws_reconnect_regression.py`: `test_ws_core_logs_version_and_ping_pong_flow`

### PR #315

- `client/static/js/core/message_dispatch.js`: `<top-level>`
- `client/static/js/core/ws.js`: `<top-level>`
- `client/templates/play.html`: `removeSpellAt`, `_isAccidentalEmptyCombatState`, `togglePlayerActionsHub`
- `tests/test_combat_initiative_live_sync_client.py`: `setTimeout`, `_renderSuspendedCombatants(list);`

### PR #316

- `client/static/js/core/ws.js`: `<top-level>`
- `client/templates/play.html`: `<top-level>`, `refreshRoleBadge`
- `tests/test_play_nav_guard_no_reload.py`: `<top-level>`
- `tests/test_ws_reconnect_regression.py`: `COMBAT = ROOT / "server/handlers/combat.py"`, `test_server_logs_pong_and_updates_last_seen_for_any_frame`

### PR #317

- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/static/js/core/boot_shell.js`: `<top-level>`
- `client/static/js/core/diagnostics.js`: `<top-level>`
- `client/static/js/core/ws.js`: `<top-level>`
- `client/static/js/dice/dice3d.js`: `_playSettlePulse`
- `client/static/js/render/vision.js`: `<top-level>`
- `client/static/js/ui/sound_engine.js`: `window.SoundEngine = SoundEngine;`
- `client/templates/play.html`: `<top-level>`, `window.addEventListener('unhandledrejection', (ev) => {`, `drawLoop`

### PR #318

- `client/static/js/cartographer.js`: `<top-level>`
- `client/static/js/character/character_sheet_container.js`: `_renderOverviewPanel`
- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/static/js/core/diagnostics.js`: `<top-level>`
- `client/static/js/dice/dice3d.js`: `_playSettlePulse`
- `client/static/tts_client.js`: `_wsSend`
- `client/templates/play.html`: `_playerVolChange`, `refreshIntegrationStatus`, `dmNarrationStop`

### PR #319

- `client/static/js/character/combat_quick_bar.js`: `<top-level>`
- `client/static/js/character/combat_quick_selectors.js`: `<top-level>`
- `client/templates/play.html`: `let _mapImageLoadingUrl = null;`, `requestRenderFrame`, `let _lastFrame = 0;`, `let _bootRenderLogged = false;`, `_partyStatusFallbackVitalsForUser`, `cancelViewerPowerTargeting`, `loadSavedDiscoveries`, `createNewCharProfileId`, `getCharProfileDraftHash`, `markCharProfileClean`, `setInventoryLayoutMode`, `__syncRightTabRegistry`, `removeSpellAt`, `_isAccidentalEmptyCombatState`, `_normalizeCombatRoster`, `playerInspectSpell`, `togglePlayerActionsHub`

### PR #320

- `client/static/js/character/combat_quick_selectors.js`: `<top-level>`
- `client/templates/play.html`: `__logReentry`, `_syncLoadedProfileToOwnedToken`, `togglePlayerActionsHub`
- `tests/test_combat_initiative_live_sync_client.py`: `ROOT = Path(__file__).resolve().parents[1]`, `global.window = global;`, `setTimeout`
- `tests/test_player_combat_regressions.py`: `<top-level>`
- `tests/test_quick_action_customize_picker_filter.py`: `sel.writeQuickPicks(['spell:fireball::cast-5']);`

### PR #321

- `tests/test_combat_quick_bar_ui.py`: `test_combat_quick_spell_upcast_options_scale_damage_by_slot_level`
- `tests/test_player_actions_hub_ui.py`: `_read`, `test_player_actions_hub_is_mobile_first`

### PR #322

- `client/templates/play.html`: `_initiativeResultRoll`
- `server/handlers/map_editor.py`: `_fog_state_payload_for_context`
- `tests/test_combat_initiative_live_sync_client.py`: `test_initiative_patch_updates_self_and_other_client_without_source_filter`
- `tests/test_fog_sync.py`: `test_fog_paint_accepts_map_context_alias_and_isolates_world_from_poi`, `test_fog_broadcast_only_reaches_users_with_map_visibility`

### PR #323

- `client/static/js/render/fog.js`: `<top-level>`
- `client/templates/play.html`: `markCharProfileClean`, `_initiativeResultRoll`, `_combatQuickNormalizeWeapon`
- `tests/test_combat_initiative_live_sync_client.py`: `console.log(JSON.stringify({{ before, rows, combat: _combat }}));`
- `tests/test_combat_quick_bar_ui.py`: `test_quick_weapon_modal_accepts_staff_like_items_and_magic_actions`
- `tests/test_fog_sync.py`: `test_map_grid_resize_rescales_tokens_props_and_syncs`
- `tests/test_fog_ui_sticky.py`: `test_fog_module_uses_authoritative_map_context_source`
- `tests/test_player_actions_hub_ui.py`: `test_player_weapon_action_execution_accepts_runtime_id_name_and_slug_fallbac`
- `tests/test_player_combat_regressions.py`: `console.log(JSON.stringify({`

### PR #324

- `client/static/js/ui/dm_assistant.js`: `<top-level>`
- `client/templates/play.html`: `_playerVolChange`, `let __charProfileAutosaveDeferredForRender = false;`, `__deferCharProfileAutosaveUntilRenderUnwinds`
- `tests/test_player_boot_regression.py`: `<top-level>`

## Required checks

- Duplicate definitions/exports: current tree has duplicate `normalizeWeaponDamage` and `rollQuickWeaponDamage` definitions in `play.html` and `combat_quick_actions.js`, plus duplicate public exports for `openCombatQuickBarWeaponAction`; `findCombatWeapon` is defined/exported in `play.html` and consumed as shared lookup by the module path.
- Render functions mutating/saving state: `renderPlayerActionsHub` was repeatedly edited near quick-pick/profile work and should remain render-only; PR #319/#320/#324 show autosave/render recursion risk around profile sync and dirty tracking.
- Player boot calling DM-only endpoints: current `cartographer.js` and `dm_assistant.js` both fetch `/api/assistant/status`; `cartographer.js` includes a DM-only guard, and `dm_assistant.js` is DM UI, so the safe cleanup is to enforce role/host gating before any status fetch.
- Initiative source of truth: not single; both server `combat_state` responses/broadcasts and client initiative patch handlers update the same combat state.
- Fog authority: mixed server/client; server computes visible recipients and combat visibility, while client fog module applies local state and requests sync debounced from several events.
- Quick weapon damage active paths: more than one; the loaded module owns quick-action weapon rolling, but `play.html` keeps compatibility bridge functions and damage helpers.

## Smallest safe cleanup PR proposal

Do not combine boot, combat, fog, and quick actions. Start with a narrow player-boot cleanup: add tests/guards proving DM-only assistant/cartographer status fetches do not run for player/viewer boot, and leave combat/fog/quick-action code untouched. This reduces runtime breakage risk without changing gameplay authority.
