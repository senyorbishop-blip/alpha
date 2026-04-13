from pathlib import Path


def test_encumbrance_bag_actions_use_window_sendws_fallback():
    source = Path("client/static/js/gameplay/encumbrance.js").read_text(encoding="utf-8")
    assert "typeof window.sendWS === 'function'" in source
    assert "type: 'bag_add_item'" in source
    assert "type: 'bag_remove_item'" in source
    assert "type: 'bag_destroy'" in source
