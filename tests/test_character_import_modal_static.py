from pathlib import Path


IMPORT_MODAL = Path("client/static/js/character/library/character_import_modal.js")


def _modal_source() -> str:
    return IMPORT_MODAL.read_text(encoding="utf-8")


def test_import_modal_uses_preview_then_commit_endpoints():
    source = _modal_source()

    assert "/api/character/import/ddb-id/preview" in source
    assert "/api/character/import/ddb-id/commit" in source
    assert "/api/character/import/json/preview" in source
    assert "/api/character/import/json/commit" in source
    assert "/api/character/import/pdf/preview" in source
    assert "/api/character/import/pdf/commit" in source

    assert "'/api/character/import/ddb-id'" not in source
    assert "'/api/character/import/json'" not in source
    assert "'/api/character/import/pdf'" not in source


def test_import_modal_review_blocks_save_until_resolution():
    source = _modal_source()

    assert "Save Imported Character" in source
    assert "Edit Before Saving" in source
    assert "Update Preview With Fixes" in source
    assert "data.requires_resolution" in source
    assert "saveBtn.style.display = hasBlocking ? 'none' : ''" in source
    assert "import_resolution" in source


def test_import_modal_posts_with_csrf_header():
    source = _modal_source()

    assert "X-CSRF-Token" in source
    assert "headers: withCsrfHeaders({ 'Content-Type': 'application/json' })" in source
    assert "headers: withCsrfHeaders()" in source


def test_import_modal_explains_quality_sources_and_failures():
    source = _modal_source()

    assert "Import quality:" in source
    assert "Excellent" in source
    assert "Good" in source
    assert "Partial" in source
    assert "Needs review" in source
    assert "D&D Beyond PDF" in source
    assert "JSON import gives best results" in source
    assert "PDF import may need review" in source
    assert "Private D&D Beyond character" in source
    assert "Invalid JSON" in source
    assert "PDF has no form fields" in source
    assert "Missing session_id" in source
    assert "Unsupported species" in source
    assert "Unsupported subclass" in source
