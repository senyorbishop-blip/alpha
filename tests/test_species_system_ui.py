from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_species_picker_and_legacy_import_field_exist():
    src = _play_html()
    assert 'id="cb-species"' in src
    assert 'handleSpeciesSelectionChanged()' in src
    assert 'id="cb-race-imported"' in src
    assert 'Imported Race (Legacy)' in src


def test_species_catalog_includes_required_builtins_and_fairy():
    src = _play_html()
    assert 'const BUILTIN_SPECIES_CATALOG = [' in src
    for name in [
        'Aasimar', 'Dragonborn', 'Dwarf', 'Elf', 'Gnome',
        'Goliath', 'Halfling', 'Human', 'Orc', 'Tiefling', 'Fairy',
    ]:
        assert f"species_name: '{name}'" in src


def test_species_summary_card_renders_core_fields():
    src = _play_html()
    assert 'id="cb-species-summary-card"' in src
    assert 'Species Summary' in src
    assert 'movement_speed' in src
    assert 'resistances' in src
    assert 'feature_summary' in src


def test_import_path_maps_legacy_race_to_species():
    src = _play_html()
    assert "extractSection(text, 'Species') || extractSection(text, 'Race')" in src
    assert 'data.importedRace = importedSpeciesText ||' in src
    assert 'data.species = importedSpeciesText || data.species ||' in src


def test_sync_path_applies_species_profile_to_runtime_state():
    src = _play_html()
    assert 'const speciesProfile = ensureSpeciesProfileForBookData(data);' in src
    assert '_charSheet.species = data.species || speciesProfile?.species_name' in src
    assert '_charSheet._speciesAutoSpeed' in src


def test_ddb_json_import_maps_race_into_species_fields():
    src = _play_html()
    assert "species: d.race?.fullName || d.race?.baseName || ''" in src
    assert "importedRace: d.race?.fullName || d.race?.baseName || ''" in src
    assert "race: d.race?.fullName || d.race?.baseName || ''" in src


def test_old_characters_without_species_get_safe_defaults():
    src = _play_html()
    assert "if (!char.species) char.species = char.race || char.book?.species || char.book?.race || '';" in src
    assert "if (!char.importedRace) char.importedRace = char.race || char.book?.importedRace || char.book?.race || '';" in src


def test_manual_species_change_refreshes_sheet_speed_and_summary():
    src = _play_html()
    assert "onchange=\"handleSpeciesSelectionChanged()\"" in src
    assert "const nextSpeed = parseInt(profile.movement_speed || 0, 10) || 0;" in src
    assert "if (speedEl && nextSpeed > 0) speedEl.value = String(nextSpeed);" in src


def test_species_speed_affects_derived_movement_and_tracks_auto_speed():
    src = _play_html()
    assert "const speciesGameplay = buildSpeciesGameplayState(speciesProfile, data);" in src
    assert "const speciesSpeed = parseInt(speciesProfile.movement_speed || 0, 10) || 0;" in src
    assert "_charSheet._speciesAutoSpeed = speciesSpeed || priorAuto || 0;" in src


def test_species_senses_are_stored_and_darkvision_is_derived_and_rendered():
    src = _play_html()
    assert "function parseDarkvisionRadiusFromSenses(sensesList = [])" in src
    assert "_charSheet.senses = sensesText;" in src
    assert "_charSheet.hasDarkvision = !!(speciesGameplay?.has_darkvision);" in src
    assert "_charSheet.darkvisionRadius = parseInt(speciesGameplay?.darkvision_radius || 0, 10) || 0;" in src
    assert "<label>Darkvision</label><strong>${heroDarkvision} ft</strong>" in src


def test_species_resistances_are_stored_and_rendered():
    src = _play_html()
    assert "_charSheet.resistances = resistancesText;" in src
    assert "<label>Resistances</label><strong>${escapeHtml(heroResistances || '—')}</strong>" in src


def test_species_active_and_limited_use_feature_metadata_surfaces_in_actions_hub():
    src = _play_html()
    assert "const activeTraits = Array.isArray(speciesGameplay?.active_traits) ? speciesGameplay.active_traits : [];" in src
    assert "const limitedTraits = Array.isArray(speciesGameplay?.resource_traits) ? speciesGameplay.resource_traits : [];" in src
    assert "id: `species_active_${idx}_${clean.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`," in src
    assert "resource: limitedTraits[idx] || ''" in src


def test_species_darkvision_syncs_into_token_payloads_for_visibility_state():
    src = _play_html()
    assert "payload.hasDarkvision = speciesHasDarkvision;" in src
    assert "payload.darkvisionRadius = speciesDarkvisionRadius;" in src
    assert "hasDarkvision: speciesHasDarkvision," in src
    assert "darkvisionRadius: speciesDarkvisionRadius," in src
