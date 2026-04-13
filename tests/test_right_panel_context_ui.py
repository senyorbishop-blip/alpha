from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def _tabs_js() -> str:
    return Path('client/static/js/ui/tabs.js').read_text(encoding='utf-8')


def test_right_panel_context_mount_exists():
    src = _play_html()
    assert 'id="right-panel-context"' in src
    assert 'id="right-panel-context-chip"' in src
    assert 'id="right-panel-context-detail"' in src


def test_play_html_exposes_context_env_for_live_tabs_module():
    src = _play_html()
    assert 'function __getRightPanelContextState()' in src
    assert 'shouldAutoFocusContext: () => __shouldAutoFocusRightPanelContext()' in src
    assert 'noteManualTabSwitch: () => __noteManualRightPanelTabSwitch()' in src


def test_tabs_module_applies_context_priority_and_auto_focus_hooks():
    src = _tabs_js()
    assert 'function applyContextUI(env)' in src
    assert "btn.classList.remove('context-priority', 'context-muted');" in src
    assert 'env?.shouldAutoFocusContext?.()' in src
    assert 'env.markContextAutoFocus?.(context);' in src
