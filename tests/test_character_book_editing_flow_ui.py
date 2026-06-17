from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_identity_page_exposes_guided_setup_order_fields():
    src = _play_html()
    assert 'data-setup-step="1"><span>Class</span><input id="cb-class"' in src
    assert 'data-setup-step="2"><span>Subclass</span><input id="cb-subclass"' in src
    assert 'data-setup-step="3"><span>Species</span><select id="cb-species"' in src
    assert 'data-setup-step="4"><span>Background</span><input id="cb-background"' in src
    assert 'data-setup-step="5"><span>Level</span><input id="cb-level"' in src


def test_identity_page_includes_collapsible_story_and_legacy_group():
    src = _play_html()
    assert '<details class="sheet-book-collapsible" open>' in src
    assert '<summary>Story &amp; Legacy Details</summary>' in src
    assert 'id="cb-race-imported"' in src


def test_character_book_save_feedback_badge_and_states_exist():
    src = _play_html()
    assert 'id="cb-save-status" class="sheet-save-status"' in src
    assert "function setCharacterBookSaveState(state = 'saved')" in src
    assert "badge.textContent = state === 'dirty' ? 'Unsaved changes' : (state === 'saving' ? 'Saving…' : 'Saved');" in src


def test_character_profile_autosave_state_machine_guards_save_loops():
    src = _play_html()
    assert 'let isHydrating = false;' in src
    assert 'let isSaving = false;' in src
    assert 'let isDirty = false;' in src
    assert "let lastSavedHash = '';" in src
    assert "let currentDraftHash = '';" in src
    assert 'function getCharProfileDraftHash(profile)' in src
    assert "if (isHydrating || isSaving) return;" in src
    assert "if (!currentDraftHash || currentDraftHash === lastSavedHash)" in src
    assert "currentDraftHash === _lastCharProfileSavePayloadHash && (now - _lastCharProfileSaveAt) < 1500" in src


def test_character_profile_hydration_and_server_sync_do_not_mark_dirty_or_autosave():
    src = _play_html()
    assert 'const wasHydrating = isHydrating;' in src
    assert 'isHydrating = true;' in src
    assert "clearTimeout(_charProfileAutosaveTimer);" in src
    assert "clearTimeout(_charBookSyncTimer);" in src
    assert "markCharProfileClean(collectCurrentCharProfile({ profileId: profile.id, skipSideEffects: true }));" in src
    assert "if (isHydrating) return;" in src
    assert "if (activeFromServer)" in src
    assert "serverHash === currentDraftHash || serverHash === _lastCharProfileSavePayloadHash" in src


def test_character_profile_user_input_and_quick_panel_use_single_debounced_save_path():
    src = _play_html()
    assert "function markCharProfileDirty(source = 'user')" in src
    assert "if (isHydrating || source === 'hydrate' || source === 'render' || source === 'server') return false;" in src
    assert "markCharProfileDirty('user');" in src
    assert "saveCurrentCharProfile({ silent: true, trigger: 'autosave' });" in src
    assert "if (id.startsWith('cb-')) scheduleCharBookQuickPanelSync();" in src
    assert "if (id.startsWith('char-') || id.startsWith('cb-')) scheduleCharProfileAutosave();" in src


def test_mobile_edit_layout_avoids_horizontal_scroll_and_uses_larger_tap_targets():
    src = _play_html()
    assert '.sheet-page-scroll { overflow-x: hidden; }' in src
    assert '.sheet-page-tabs { flex-wrap: wrap; overflow-x: hidden; }' in src
    assert '.sheet-book-input, .sheet-book-textarea, .sheet-book-select { min-height: 40px; }' in src
    assert '.mini-btn { min-height: 38px; }' in src


def test_native_builder_abilities_step_supports_standard_array_and_point_buy():
    src = Path('client/static/js/character/builder/steps/step_abilities.js').read_text(encoding='utf-8')
    assert 'option value="standard_array"' in src
    assert 'option value="point_buy"' in src
    assert 'Remaining points:' in src


def test_native_builder_router_keeps_subclass_step_dynamic():
    src = Path('client/static/js/character/builder/builder_router.js').read_text(encoding='utf-8')
    assert 'function shouldIncludeSubclassStep(draft)' in src
    assert "if (step.id !== 'subclass') return true;" in src


def test_native_builder_router_subclass_step_safe_default_when_catalog_null():
    src = Path('client/static/js/character/builder/builder_router.js').read_text(encoding='utf-8')
    # When catalog is not loaded, the step must be included as a safe default
    assert 'if (!catalog) return true;' in src


def test_native_builder_router_subclass_step_checks_subclasses_by_class():
    src = Path('client/static/js/character/builder/builder_router.js').read_text(encoding='utf-8')
    # Must verify at least one subclass exists for the class before showing the step
    assert 'subclassesByClass' in src
    assert "if (!Array.isArray(byClass[key]) || byClass[key].length === 0) return false;" in src


def test_native_builder_router_exports_clear_subclass_from_draft():
    src = Path('client/static/js/character/builder/builder_router.js').read_text(encoding='utf-8')
    # clearSubclassFromDraft must be defined, clear the right fields, and be exported
    assert 'function clearSubclassFromDraft(draft)' in src
    assert "draft.class.subclassId = '';" in src
    assert "draft.class.subclass = '';" in src
    assert 'clearSubclassFromDraft,' in src


def test_native_builder_router_clears_subclass_when_step_skipped():
    src = Path('client/static/js/character/builder/builder_router.js').read_text(encoding='utf-8')
    # getStepOrder must call clearSubclassFromDraft when the subclass step is excluded
    assert "if (!order.includes('subclass'))" in src
    assert 'clearSubclassFromDraft(draft)' in src


def test_character_book_defaults_to_live_sheet_page_on_open():
    src = Path('client/static/js/ui/character_book.js').read_text(encoding='utf-8')
    assert "function openCharacterBook(env, page = 'premiumsheet')" in src
    assert "|| 'premiumsheet';" in src


def test_native_builder_progression_tracks_asi_choices_by_level():
    src = Path('client/static/js/character/builder/steps/step_progression.js').read_text(encoding='utf-8')
    assert 'Level-by-Level ASI / Feat Choices' in src
    assert 'data-builder-asi-level' in src
    assert 'asiChoicesByLevel' in src
    assert 'writeAsiChoice(context, levelKey' in src
    assert 'For higher-level starts, work down this list like D&amp;D Beyond' in src
    assert 'hasPerLevelChoices' in src


def test_native_builder_progression_does_not_block_before_subclass_step():
    src = Path('client/static/js/character/builder/builder_validators.js').read_text(encoding='utf-8')
    assert "pending.filter(function (item) { return item && item.type === 'asi'; })" in src
    assert 'Choose your subclass to resolve required progression choices.' not in src


def test_builder_state_defaults_level_asi_choice_map():
    src = Path('client/static/js/character/builder/builder_state.js').read_text(encoding='utf-8')
    assert 'asiChoicesByLevel: {}' in src
    assert 'draft.progression.asiChoicesByLevel = {}' in src


def test_builder_service_reads_feats_from_level_asi_choice_map():
    src = Path('server/character/service.py').read_text(encoding='utf-8')
    assert 'asi_choices_by_level = progression.get("asiChoicesByLevel")' in src
    assert 'progression_choice_state.get("asiChoicesByLevel")' in src


def test_character_book_uses_single_modal_mode_and_cleanup_contract():
    src = Path('client/static/js/ui/character_book.js').read_text(encoding='utf-8')
    assert "VALID_SHEET_MODES = new Set(['closed', 'live_play_sheet', 'edit_sheet', 'import_review', 'level_up'])" in src
    assert 'function closeAllCharacterSheetSurfaces(env, nextMode = \'closed\')' in src
    assert "closeAllCharacterSheetSurfaces(env, 'closed');" in src
    assert 'modeForCharacterBookPage(page)' in src
    assert 'cleanupCharacterSheetSurfaces: closeAllCharacterSheetSurfaces' in src
    assert "doc.querySelectorAll('#char-sheet-panel.open, #char-sheet-panel.active')" in src


def test_live_play_sheet_hides_legacy_roots_and_edit_hides_premium_root():
    src = Path('client/static/js/ui/character_book.js').read_text(encoding='utf-8')
    assert "const premiumRoot = doc.getElementById('cs-premium-mount');" in src
    assert "const oldRoots = [doc.getElementById('sheet-body')].filter(Boolean);" in src
    assert "setRootInactive(premiumRoot, mode !== 'live_play_sheet', 'block');" in src
    assert "oldRoots.forEach(root => setRootInactive(root, true));" in src
    assert "setRootInactive(pageEl, !isActive, 'flex');" in src
    assert "root.hidden = isInactive;" in src
    assert "root.style.display = isInactive ? 'none' : activeDisplay;" in src
    assert "root.style.pointerEvents = isInactive ? 'none' : 'auto';" in src


def test_character_sheet_css_prevents_inactive_roots_bleeding_through():
    src = _play_html()
    assert '#char-sheet-panel[hidden]' in src
    assert '#char-sheet-panel[data-sheet-mode="closed"]' in src
    assert '#char-book-pages .sheet-page[hidden]' in src
    assert '#char-book-pages .sheet-page.sheet-root-inactive' in src
    assert '#cs-premium-mount[hidden]' in src
    assert '#sheet-body[hidden]' in src
    assert '#cs-premium-mount.sheet-root-inactive' in src
    assert '#sheet-body.sheet-root-inactive' in src
    assert 'pointer-events:none !important;' in src
    assert 'visibility:hidden !important;' in src
    assert 'z-index: 15600;' in src


def test_escape_closes_active_character_sheet_modal():
    src = _play_html()
    assert "if (document.getElementById('char-sheet-panel')?.classList.contains('open'))" in src
    assert 'closeCharacterBook();' in src
    assert 'return;' in src


def test_character_sheet_surface_cleanup_contract_covers_requested_openings():
    book = Path('client/static/js/ui/character_book.js').read_text(encoding='utf-8')
    runtime = Path('client/static/js/character/runtime/character_book_runtime.js').read_text(encoding='utf-8')
    play = _play_html()
    assert "function closeAllCharacterSheetSurfaces(env, nextMode = 'closed')" in book
    assert "doc.querySelectorAll('.character-sheet-backdrop, .char-sheet-backdrop, .sheet-modal-backdrop').forEach(node => node.remove())" in book
    assert "doc.querySelectorAll('.character-sheet-modal.active')" in book
    assert "setRootInactive(premiumRoot, mode !== 'live_play_sheet', 'block');" in book
    assert "oldRoots.forEach(root => setRootInactive(root, true));" in book
    assert "panel.style.zIndex = mode === 'closed' ? '' : '15600';" in book
    assert 'global.closeAllCharacterSheetSurfaces = closeAllCharacterSheetSurfaces;' in runtime
    assert "if (typeof closeAllCharacterSheetSurfaces === 'function') closeAllCharacterSheetSurfaces();" in play


def test_inactive_character_sheet_roots_are_hidden_inert_and_noninteractive():
    src = Path('client/static/js/ui/character_book.js').read_text(encoding='utf-8')
    assert "root.setAttribute('aria-hidden', isInactive ? 'true' : 'false');" in src
    assert "if ('inert' in root) root.inert = isInactive;" in src
    assert 'root.hidden = isInactive;' in src
    assert "root.classList.remove('active', 'open');" in src
    assert "root.style.visibility = isInactive ? 'hidden' : 'visible';" in src
    assert "root.style.pointerEvents = isInactive ? 'none' : 'auto';" in src


def test_live_and_edit_modes_do_not_allow_legacy_overview_bleed_or_duplicate_active_roots():
    src = Path('client/static/js/ui/character_book.js').read_text(encoding='utf-8')
    assert "mode === 'live_play_sheet' ? 'premiumsheet'" in src
    assert "mode === 'edit_sheet' ? (env.getActiveCharBookPage && env.getActiveCharBookPage()) || 'identity'" in src
    assert "setRootInactive(premiumRoot, mode !== 'live_play_sheet', 'block');" in src
    assert "oldRoots.forEach(root => setRootInactive(root, true));" in src
    assert "doc.querySelectorAll('#char-sheet-panel.open, #char-sheet-panel.active')" in src
    assert "if (node !== panel || idx > 0) setRootInactive(node, true);" in src
