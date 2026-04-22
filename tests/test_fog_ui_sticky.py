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
    assert "if (enabled && !isManualFogEditingAllowed()) enabled = false;" in play_src
    assert "if (enabled && !manualAllowed) enabled = false;" in fog_module_src


def test_toolbar_canvas_close_respects_fog_editing_mode():
    src = _read('client/static/js/ui/toolbar.js')
    assert "const fogFlyoutOpen = env.document.getElementById('flyout-fog')?.classList.contains('open');" in src
    assert "if (fogFlyoutOpen && env.ROLE === 'dm' && !!env.fogEnabled && (fogMode === 'manual' || fogMode === 'hybrid')) return;" in src


def test_fog_ui_shows_context_and_disables_manual_tools_in_non_manual_modes():
    src = _read('client/templates/play.html')
    fog_src = _read('client/static/js/render/fog.js')
    assert "id=\"fog-map-context-text\"" in src
    assert "id=\"fog-visibility-model-text\"" in src
    assert "chk.disabled = !(manualAllowed && canEdit);" in src
    assert "toolsDiv.style.display = fogEnabled && manualAllowed && canEdit ? 'flex' : 'none';" in src
    assert "if (fogEnabled && isManualFogEditingAllowed() && canCurrentUserEditFog()" in src
    assert "chk.disabled = !(manualAllowed && canEdit);" in fog_src
    assert "Editing: ${_fogContextLabel(state, env)}" in fog_src


def test_fog_module_uses_authoritative_map_context_source():
    fog_src = _read('client/static/js/render/fog.js')
    play_src = _read('client/templates/play.html')
    assert "if (env && typeof env.getCurrentMapContext === 'function')" in fog_src
    assert "return String(env.getCurrentMapContext() || 'world');" in fog_src
    assert "getCurrentMapContext: _getCurrentMapContext," in play_src


def test_fog_update_applies_payload_by_map_ctx_without_stale_current_poi_assumptions():
    fog_src = _read('client/static/js/render/fog.js')
    play_src = _read('client/templates/play.html')
    assert "function fogApplyUpdate(state, env, p) {" in fog_src
    assert "const updCtx = String((p && p.map_ctx) || 'world');" in fog_src
    assert "const activeCtx = fogCurrentCtx(env);" in fog_src
    assert "window.AppFog.fogApplyUpdate(state, __createFogModuleEnv(), p);" in play_src
    assert "const activeFogCtx = _getCurrentMapContext();" in play_src
