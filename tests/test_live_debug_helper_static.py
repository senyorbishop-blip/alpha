from pathlib import Path


def test_client_live_debug_helper_defaults_disabled_and_guards_console_logging():
    source = Path("client/templates/play.html").read_text()
    assert "window.__LIVE_DEBUG__ = window.__LIVE_DEBUG__ === true" in source
    assert "function liveDebugLog(label, payload)" in source
    assert "if (!window.__LIVE_DEBUG__) return false" in source
    assert "console.debug('[live_state]'" in source
