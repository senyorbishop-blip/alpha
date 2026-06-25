import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_dm_live_ui_chrome_css_hides_stream_readiness_panel():
    import sitecustomize

    html = '<html><head><title>Play</title></head><body><div id="stream-readiness-panel">Stream readiness</div></body></html>'
    patched = sitecustomize.inject_dm_live_ui_chrome_css(html)

    assert 'dm-live-ui-chrome-css-hotfix' in patched
    assert '#stream-readiness-panel' in patched
    assert 'display:none!important' in patched
    assert 'visibility:hidden!important' in patched


def test_dm_live_ui_chrome_css_hides_dm_focus_hint_selectors():
    import sitecustomize

    html = '<html><body><div id="dm-mode-hint">DM focus: Prep in Library, run live flow in Combat.</div></body></html>'
    patched = sitecustomize.inject_dm_live_ui_chrome_css(html)

    assert '#dm-mode-hint' in patched
    assert '.dm-focus-card' in patched
    assert '.dm-focus-note' in patched
    assert 'dm-live-ui-chrome-css-hotfix' in patched


def test_dm_live_ui_chrome_css_injection_is_idempotent():
    import sitecustomize

    html = '<html><head></head><body></body></html>'
    once = sitecustomize.inject_dm_live_ui_chrome_css(html)
    twice = sitecustomize.inject_dm_live_ui_chrome_css(once)

    assert once == twice
    assert once.count('dm-live-ui-chrome-css-hotfix') == 2  # marker comment plus style id
