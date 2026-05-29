from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_builder_currency_uses_manual_inputs_to_preserve_zero_and_caret_flow():
    src = _read("client/static/js/character/builder/steps/step_equipment.js")
    assert 'data-builder-equipment-currency' in src
    assert 'inputmode="numeric"' in src or "inputmode='numeric'" in src
    assert 'data-builder-path="equipment.currency.' not in src
    assert 'if (String(input.value || \'\') === \'0\'' in src
    assert 'commitCurrencySoon(260)' in src


def test_builder_equipment_exposes_library_bonus_item_picker():
    src = _read("client/static/js/character/builder/steps/step_equipment.js")
    assert "Library Bonus Items" in src
    assert "getLibraryEntries" in src
    assert "choices.libraryItems" in src
    assert "builder_item_library" in src
    assert "data-builder-library-search" in src


def test_play_page_publishes_item_library_to_character_builder():
    src = _read("client/templates/play.html")
    assert "window.CharacterBuilderItemLibrary" in src
    assert "function publishCharacterBuilderItemLibrary()" in src
    assert "srdItems: Array.isArray(_srdItems) ? _srdItems.slice() : []" in src
    assert "publishCharacterBuilderItemLibrary();" in src
