import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



def _play_html():
    with open(os.path.join(PROJECT_ROOT, 'client', 'templates', 'play.html'), 'r', encoding='utf-8') as f:
        return f.read()



def _cartographer_js():
    with open(os.path.join(PROJECT_ROOT, 'client', 'static', 'js', 'cartographer.js'), 'r', encoding='utf-8') as f:
        return f.read()



def _assistant_js():
    with open(os.path.join(PROJECT_ROOT, 'client', 'static', 'js', 'ui', 'dm_assistant.js'), 'r', encoding='utf-8') as f:
        return f.read()



def test_play_html_has_dm_assistant_rail_and_flyout():
    src = _play_html()
    assert 'rail-assistant-btn' in src
    assert 'flyout-assistant' in src
    assert 'dm-assistant-host' in src



def test_play_html_loads_dm_assistant_module_and_flyout_mapping():
    src = _play_html()
    assert '/static/js/ui/dm_assistant.js' in src
    assert "'flyout-assistant'" in src
    assert "'rail-assistant-btn'" in src



def test_play_html_initializes_dm_assistant_role():
    src = _play_html()
    assert "window.DMAssistant.setRole(ROLE)" in src



def test_play_html_uses_assistant_status_for_direct_panel_summaries():
    src = _play_html()
    assert '/api/assistant/status' in src
    assert 'Detailed provider and fallback guidance lives in DM Assistant.' in src
    assert "document.addEventListener('dm-assistant-status'" in src



def test_cartographer_status_copy_points_to_dm_assistant():
    src = _cartographer_js()
    assert '/api/assistant/status' in src
    assert 'Use DM Assistant for detailed provider readiness, fallback notes, and tool availability.' in src



def test_dm_assistant_js_includes_stage4_tools():
    src = _assistant_js()
    for label in ('Suggest encounter', 'Suggest loot', 'Draft session recap'):
        assert label in src
