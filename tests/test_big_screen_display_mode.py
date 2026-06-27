from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def test_play_page_has_intentional_big_screen_toggle_and_mode_class():
    src = _read('client/templates/play.html')
    assert 'id="player-display-toggle-btn"' in src
    assert 'function setBigScreenDisplayMode(enabled, opts = {})' in src
    assert "document.body.classList.toggle('big-screen-display-mode', _bigScreenDisplayMode);" in src
    assert "DISPLAY_MODE_PARAM === 'player'" in src


def test_big_screen_mode_hides_dm_shell_surfaces_and_uses_player_safe_overlay():
    src = _read('client/templates/play.html')
    # Big-screen surface-hiding styling was extracted from play.html into play.css.
    css = _read('client/static/css/play.css')
    assert 'body.big-screen-display-mode #sidebar-left' in css
    assert 'body.big-screen-display-mode #sidebar-right' in css
    assert 'body.big-screen-display-mode .flyout' in css
    assert 'id="display-overlay-exit"' in src
    assert "if (_bigScreenDisplayMode && ROLE === 'dm')" in src
    assert "if (tok.hidden) return false;" in src
    assert "hp: tok?.hidden_hp ? 'HP Hidden'" in src
