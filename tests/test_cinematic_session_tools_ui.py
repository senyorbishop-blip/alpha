import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_play_html() -> str:
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        return f.read()


def _read_play_css() -> str:
    css_path = os.path.join(PROJECT_ROOT, "client", "static", "css", "play.css")
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()


def test_play_page_exposes_session_event_overlay_shell():
    src = _read_play_html()
    assert 'id="session-event-overlay"' in src
    assert "id=\"session-event-kicker\"" in src
    assert "id=\"session-event-title\"" in src
    assert "id=\"session-event-subtitle\"" in src
    assert "function showSessionEventOverlay(opts = {})" in src
    assert "function showCinematicMoment(kind = 'default', payload = {})" in src
    assert "function _sessionEventPreset(kind = 'default', payload = {})" in src
    assert "function dismissSessionEventOverlay()" in src


def test_session_event_overlay_is_triggered_by_live_presentation_events():
    src = _read_play_html()
    assert "case 'encounter_spawn_result': {" in src
    assert "case 'handout_received': {" in src
    assert "case 'narration_speak': {" in src
    assert "case 'session_event_notice': {" in src
    assert src.count("showCinematicMoment(") >= 7
    assert "showCinematicMoment(bossReveal ? 'boss_reveal' : 'encounter_intro'" in src
    assert "showCinematicMoment('handout_reveal'" in src
    assert "showCinematicMoment('narration_subtitle'" in src
    assert "showCinematicMoment('location_title'" in src
    assert "showCinematicMoment('campaign_event'" in src
    assert "showCinematicMoment('quest_update'" in src


def test_play_page_supports_narration_hook_surface():
    src = _read_play_html()
    assert "case 'narration_hook': {" in src
    assert "_narrationManager.showHook" in src


def test_session_event_overlay_uses_short_non_blocking_lifecycle():
    src = _read_play_html()
    assert "Math.max(1400, Math.min(6000" in src
    assert "_sessionEventDismissTimer = setTimeout(dismissSessionEventOverlay, duration);" in src
    # Overlay styling was extracted from play.html into play.css.
    css = _read_play_css()
    assert "#session-event-overlay.open" in css
    assert "pointer-events: auto;" in css
    assert "#session-event-overlay[data-cinematic=\"true\"]" in css
