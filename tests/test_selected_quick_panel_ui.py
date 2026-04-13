from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_selected_quick_panel_mount_and_slots_exist():
    src = _play_html()
    assert 'id="selected-quick-panel"' in src
    assert 'id="selected-quick-preview"' in src
    assert 'id="selected-quick-meta"' in src
    assert 'id="selected-quick-actions"' in src


def test_selected_quick_panel_runtime_helpers_exist():
    src = _play_html()
    assert 'function refreshSelectedQuickPanel()' in src
    assert 'function quickPanelOpenTokenEditor()' in src
    assert 'function quickPanelDeleteHoveredWall()' in src
    assert "refreshSelectedQuickPanel();" in src


def test_selected_quick_panel_surfaces_token_prop_poi_and_wall_states():
    src = _play_html()
    assert "kicker.textContent = 'Selected Token';" in src
    assert "kicker.textContent = isDoor ? 'Selected Door' : 'Selected Object';" in src
    assert "kicker.textContent = 'Selected POI';" in src
    assert "kicker.textContent = 'Selected Wall';" in src
