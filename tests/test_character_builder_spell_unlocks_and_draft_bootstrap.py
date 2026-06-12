from pathlib import Path

from server.character.routes import _builder_class_spell_pool, _fallback_highest_unlocked_spell_level


def test_warlock_fallback_unlock_level_reports_leveled_spells():
    pool = _builder_class_spell_pool().get("warlock", set())
    assert pool, "Expected class spell pool metadata for warlock."
    # Warlock must not render as cantrips-only at low levels in the builder.
    assert _fallback_highest_unlocked_spell_level("warlock", 1, pool) >= 1
    assert _fallback_highest_unlocked_spell_level("warlock", 5, pool) >= 2


def test_builder_state_does_not_autoload_persisted_draft_without_opt_in():
    src = Path("client/static/js/character/builder/builder_state.js").read_text(encoding="utf-8")
    assert "loadPersistedDraft: false" in src
    assert "createOpts.loadPersistedDraft ? loadPersistedDraft() : null" in src


def test_builder_state_exposes_import_replace_draft_mapping_contract():
    src = Path("client/static/js/character/builder/builder_state.js").read_text(encoding="utf-8")

    assert "canonicalDocumentToDraft" in src
    assert "replaceDraft(nextDraft, opts)" in src
    assert "routeTo === 'review_or_first_missing'" in src
    assert "draft.importMeta = clone(importMeta)" in src
    assert "draft.sourceMode = String(doc.sourceMode" in src
    assert "draft.spellbook =" in src
    assert "draft.equipment =" in src
    assert "draft.compatibility" in src


def test_import_modal_and_gateway_open_builder_before_saving():
    modal_src = Path("client/static/js/character/library/character_import_modal.js").read_text(encoding="utf-8")
    gateway_src = Path("client/static/js/character/gateway/join_gateway.js").read_text(encoding="utf-8")

    assert "onEditBeforeSave" in modal_src
    assert "openBuilderForPendingPreview" in modal_src
    assert "cfg.onEditBeforeSave(doc, pendingPreview)" in modal_src
    assert "openImportedDocumentInBuilder" in gateway_src
    assert "builderState.replaceDraft(importedDocument" in gateway_src
    assert "routeTo: 'review_or_first_missing'" in gateway_src
    assert "/api/character/save" in gateway_src


def test_import_modal_summary_counts_canonical_spell_state_fields_before_legacy_fallback():
    modal_src = Path("client/static/js/character/library/character_import_modal.js").read_text(encoding="utf-8")

    assert "countDocumentSpells(importMeta, spellState)" in modal_src
    assert "importMeta.importedSpells" in modal_src
    assert "spellState.known" in modal_src
    assert "spellState.prepared" in modal_src
    assert "spellState.spellbookEntries" in modal_src
    assert "spellState.knownSpells" in modal_src
    assert "spellState.preparedSpells" in modal_src
    assert "spellState.spells" in modal_src
    assert "if (currentCount > 0) return currentCount" in modal_src
    assert "new Set()" in modal_src


def test_import_modal_spell_review_distinguishes_imported_only_from_missing():
    modal_src = Path("client/static/js/character/library/character_import_modal.js").read_text(encoding="utf-8")

    assert "Imported-only spells may need DM review" in modal_src
    assert "Matched spells are ready for native rolling" in modal_src
    assert "reviewData.spellsImportedOnly" in modal_src
    assert "No imported-only spells reported." in modal_src
