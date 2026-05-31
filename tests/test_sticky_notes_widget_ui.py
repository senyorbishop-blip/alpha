from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_play_page_loads_sticky_notes_widget_after_character_sheet():
    play = read("client/templates/play.html")
    assert "/static/js/character/sticky_notes.js" in play
    assert play.index("/static/js/character/character_sheet_container.js") < play.index("/static/js/character/sticky_notes.js")
    assert "window.openCharacterStickyNotes" in play
    assert "characterNotes:" in play


def test_sticky_notes_widget_supports_autosave_position_and_hotkey_isolation():
    sticky = read("client/static/js/character/sticky_notes.js")
    for expected in [
        "SAVE_DEBOUNCE_MS",
        "Saving…",
        "Save failed",
        "widget_position",
        "widget_size",
        "data-sticky-drag-handle",
        "data-sticky-resize-handle",
        "stopInputHotkeys",
        "saveCurrentCharProfile({ silent: true, stickyNotes: true })",
    ]:
        assert expected in sticky


def test_character_notes_tab_opens_sticky_notes_and_reads_canonical_notes():
    sheet = read("client/static/js/character/character_sheet_container.js")
    assert "Open Sticky Notes" in sheet
    assert "characterNotes" in sheet
    assert "sticky.private" in sheet
    assert "sticky.session" in sheet
