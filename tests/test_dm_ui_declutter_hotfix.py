import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_dm_ui_declutter_injects_hidden_stream_readiness_chrome():
    import sitecustomize

    html = '<html><head><title>Play</title></head><body><div id="stream-readiness-panel">Stream readiness</div></body></html>'
    patched = sitecustomize._inject_dm_ui_declutter(html)

    assert 'dm-live-ui-declutter-hotfix' in patched
    assert '#stream-readiness-panel' in patched
    assert 'display: none !important' in patched
    assert 'window.showDMStreamReadiness' in patched
    assert 'window.hideDMStreamReadiness' in patched


def test_dm_ui_declutter_hides_dm_focus_guidance_text():
    import sitecustomize

    html = '<html><body><div>DM focus: Prep in Library, run live flow in Combat, drive storytelling through Journal/Sound.</div></body></html>'
    patched = sitecustomize._inject_dm_ui_declutter(html)

    assert 'DM focus: Prep in Library' in patched
    assert 'DM focus:' in patched
    assert 'hideDmClutter' in patched
    assert 'DM focus: Prep in Library' in patched
    assert 'display' in patched


def test_dm_ui_declutter_is_idempotent():
    import sitecustomize

    html = '<html><head></head><body></body></html>'
    once = sitecustomize._inject_dm_ui_declutter(html)
    twice = sitecustomize._inject_dm_ui_declutter(once)

    assert once == twice
    assert once.count('dm-live-ui-declutter-hotfix') == 1
