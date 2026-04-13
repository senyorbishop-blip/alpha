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
