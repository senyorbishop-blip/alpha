import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def _read(path):
    with open(os.path.join(PROJECT_ROOT, path), 'r', encoding='utf-8') as f:
        return f.read()


def test_play_html_pins_fog_flyout_while_editing():
    src = _read('client/templates/play.html')
    assert 'function isFogFlyoutPinnedForEditing() {' in src
    assert "if (isFogFlyoutPinnedForEditing()) return;" in src
    assert "return !!fogEnabled && (mode === 'manual' || mode === 'hybrid');" in src


def test_fog_toggle_payload_includes_authoritative_map_context():
    play_src = _read('client/templates/play.html')
    fog_module_src = _read('client/static/js/render/fog.js')
    assert "sendWS({ type: 'fog_toggle', payload: { enabled, map_ctx: fogMapCtx, map_context: fogMapCtx } });" in play_src
    assert "map_ctx: state.fogMapCtx" in fog_module_src
    assert "map_context: state.fogMapCtx" in fog_module_src


def test_toolbar_canvas_close_respects_fog_editing_mode():
    src = _read('client/static/js/ui/toolbar.js')
    assert "const fogFlyoutOpen = env.document.getElementById('flyout-fog')?.classList.contains('open');" in src
    assert "if (fogFlyoutOpen && env.ROLE === 'dm' && !!env.fogEnabled && (fogMode === 'manual' || fogMode === 'hybrid')) return;" in src
