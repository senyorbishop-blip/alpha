from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_dm_companion_topbar_toggle_and_panel_mount_exist():
    src = _play_html()
    assert 'id="dm-companion-btn"' in src
    assert 'id="dm-companion-panel"' in src
    assert 'function toggleDmCompanionMode()' in src


def test_dm_companion_mode_is_dm_guarded_and_viewport_scoped():
    src = _play_html()
    assert "function _hasDmCompanionAccess()" in src
    assert "return ROLE === 'dm';" in src
    assert "function _isDmCompanionViewport()" in src
    assert "<= 1200" in src


def test_dm_companion_focuses_live_controls_not_full_desktop_panels():
    src = _play_html()
    assert "sendWS({ type: 'combat_next'" in src
    assert "sendWS({ type: 'token_hp_update'" in src
    assert "sendWS({ type: 'toggle_hidden'" in src
    assert "sendWS({ type: 'send_handout'" in src
    assert "sendWS({ type: 'narration_speak'" in src


def test_dm_companion_can_return_to_world_map_using_existing_nav_path():
    src = _play_html()
    assert 'function dmCompanionReturnWorld()' in src
    assert 'closeLocalMap();' in src
