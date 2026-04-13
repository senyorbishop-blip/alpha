from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_dm_workflow_mode_switch_markup_exists():
    src = _play_html()
    assert 'id="dm-mode-switch"' in src
    assert "id=\"dm-mode-prep-btn\"" in src
    assert "id=\"dm-mode-live-btn\"" in src
    assert 'function setDmWorkflowMode(mode, opts = {})' in src
    assert "document.getElementById('dm-mode-prep-btn')" in src
    assert "document.getElementById('dm-mode-live-btn')" in src


def test_dm_workflow_mode_handler_prioritizes_prep_vs_live_tools():
    src = _play_html()
    assert 'function setDmWorkflowMode(mode, opts = {})' in src
    assert "// Keep all DM rail controls visible in both modes; mode is now emphasis only." in src
    assert "'rail-editor-btn'," in src
    assert "'rail-fog-btn'," in src
    assert "'rail-assistant-btn'," in src
    assert "document.body.dataset.dmWorkflowMode = nextMode;" in src


def test_dm_workflow_mode_visual_priority_hooks_exist():
    src = _play_html()
    assert ".rtab.context-priority" in src
    assert ".rtab.context-muted" in src
    assert "livePriorityTabs = ['rtab-combat', 'rtab-party', 'rtab-handouts'];" in src
    assert "prepPriorityTabs = ['rtab-dropdown-library', 'rtab-memory'];" in src
