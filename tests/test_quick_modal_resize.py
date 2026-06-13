"""Tests for quick spell modal resize/localStorage/scroll behavior."""
import os


def _read(path):
    with open(path) as f:
        return f.read()


def test_quick_modal_has_resize_css():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "resize:both" in src or "resize: both" in src, \
        "cqa-panel must have resize:both CSS"


def test_quick_modal_has_vertical_scroll():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "overflow-y:auto" in src or "overflow-y: auto" in src, \
        "cqa-panel must have overflow-y:auto"


def test_quick_modal_has_horizontal_scroll():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "overflow-x:auto" in src or "overflow-x: auto" in src, \
        "cqa-panel must have overflow-x:auto"


def test_quick_modal_has_min_dimensions():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "min-width" in src, "cqa-panel must have min-width"
    assert "min-height" in src, "cqa-panel must have min-height"


def test_quick_modal_has_max_dimensions():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "max-width" in src, "cqa-panel must have max-width"
    assert "max-height" in src, "cqa-panel must have max-height"


def test_quick_modal_uses_localStorage():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "localStorage" in src, "Modal must use localStorage for size persistence"
    assert "cqa_modal_size" in src, "Must use a recognizable localStorage key"


def test_quick_modal_uses_resize_observer():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "ResizeObserver" in src, "Must use ResizeObserver to detect size changes"


def test_apply_saved_size_function_exists():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "_applySavedPanelSize" in src, "Must have _applySavedPanelSize helper"


def test_watch_panel_resize_function_exists():
    src = _read("client/static/js/character/combat_quick_actions.js")
    assert "_watchPanelResize" in src, "Must have _watchPanelResize helper"
