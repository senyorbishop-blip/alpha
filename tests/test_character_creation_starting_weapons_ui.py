from pathlib import Path


def test_character_creation_builder_maps_starting_weapon_damage_fields():
    src = Path("client/templates/character-creation.html").read_text(encoding="utf-8")
    assert "const STARTER_WEAPON_STATS = {" in src
    assert "function starterWeaponStatsForName(name) {" in src
    assert "const weaponStats = starterWeaponStatsForName(parsed.name);" in src
    assert "item.damage_dice = String(weaponStats.damage_dice || '').trim();" in src
    assert "item.damage_type = String(weaponStats.damage_type || '').trim();" in src


def test_character_creation_identity_uses_gender_label_and_supports_nonbinary():
    src = Path("client/templates/character-creation.html").read_text(encoding="utf-8")
    assert "<label>Gender</label><select class=\"select\" id=\"hero-gender\">" in src
    assert "{ id: 'nonbinary', label: 'Nonbinary', pronouns: 'They / Them' }" in src
    assert "gender: state.hero.gender," in src


def test_character_creation_background_step_no_longer_duplicates_notes_textarea():
    src = Path("client/templates/character-creation.html").read_text(encoding="utf-8")
    assert "<label>Background Notes</label><textarea class=\"textarea\" id=\"hero-notes\"" not in src
    assert "<label>Player Notes (syncs to character notes)</label><textarea class=\"textarea\" id=\"hero-notes\"" in src


def test_character_creation_starts_with_import_or_build_method():
    src = Path("client/templates/character-creation.html").read_text(encoding="utf-8")
    assert "{ key: 'start', title: 'Start Method'" in src
    assert "Build from scratch" in src
    assert "Import from D&D Beyond ID" in src
    assert "Upload JSON file" in src
    assert "Paste JSON" in src
    assert "Upload PDF" in src
    assert "CharacterImportModal.open" in src
    assert "location.href = getRosterUrl(profileId);" in src


def test_character_import_modal_uses_preview_then_commit_flow():
    src = Path("client/static/js/character/library/character_import_modal.js").read_text(encoding="utf-8")
    assert "/api/character/import/ddb-id/preview" in src
    assert "/api/character/import/json/preview" in src
    assert "/api/character/import/pdf/preview" in src
    assert "/api/character/import/json/commit" in src
    assert "/api/character/import/pdf/commit" in src
    assert "Continue to Play" in src
    assert "Edit Before Saving" in src
