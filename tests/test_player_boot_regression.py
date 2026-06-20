import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _play_src() -> str:
    return PLAY.read_text(encoding="utf-8")


def test_player_page_loaded_scripts_have_no_top_level_syntax_errors():
    """Boot smoke: every classic script loaded by play.html must parse cleanly."""
    src = _play_src()
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', src)
    checked = []
    for url in scripts:
        static_url = url.split("?", 1)[0]
        if not static_url.startswith("/static/") or not static_url.endswith(".js"):
            continue
        path = ROOT / "client/static" / static_url[len("/static/"):]
        assert path.exists(), f"play.html references missing script {static_url}"
        subprocess.run(["node", "--check", str(path)], cwd=ROOT, check=True, text=True, capture_output=True, timeout=30)
        checked.append(static_url)
    assert "/static/js/render/fog.js" in checked
    assert "/static/js/ui/dm_assistant.js" in checked

    inline_scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', src, re.S)
    main_inline = max(inline_scripts, key=len)
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
        handle.write(main_inline)
        temp_path = handle.name
    subprocess.run(["node", "--check", temp_path], cwd=ROOT, check=True, text=True, capture_output=True, timeout=30)


def test_player_boot_does_not_eagerly_call_dm_only_or_heavy_endpoints():
    play = _play_src()
    assistant_init = play[play.index("(function _integrationStatusInit()"):play.index("// ═══════════════════════════════════════════════════════════════════", play.index("(function _integrationStatusInit()"))]
    assert "String(ROLE || '').toLowerCase() === 'dm'" in assistant_init
    assert "if (!_isDmBoot || _safeOff) return;" in assistant_init

    preload = play[play.index("(function _schedulePreloadSounds()"):play.index("/* ── UI click sounds", play.index("(function _schedulePreloadSounds()"))]
    assert "if (String(ROLE || '').toLowerCase() !== 'dm') return;" in preload
    assert "SFX_KEYS.forEach" in preload
    assert "AMBIENT_KEYS.forEach" in preload

    assistant = (ROOT / "client/static/js/ui/dm_assistant.js").read_text(encoding="utf-8")
    mount = assistant[assistant.index("mount() {"):assistant.index("setRole(role)")]
    assert "role !== 'dm'" in mount
    assert "this.refreshStatus();" in mount


def test_tts_client_metadata_fetches_are_dm_role_gated():
    tts = (ROOT / "client/static/tts_client.js").read_text(encoding="utf-8")
    init = tts[tts.index("async function _init()"):tts.index("if (document.readyState === 'loading')", tts.index("async function _init()"))]
    assert "document.getElementById('narration-voice-preset') !== null" not in init
    assert "new URLSearchParams(window.location.search || '').get('role')" in init
    assert "const isDM = role === 'dm';" in init
    assert "await _populateVoiceDropdown();" in init
    assert "await _renderWarmupPhrases();" in init


def test_player_boot_no_tts_metadata_fetches_under_player_role():
    script = r"""
global.window = global;
window.location = { search: '?role=player' };
window.ROLE = 'player';
const calls = [];
global.fetch = (url) => { calls.push(String(url)); return Promise.resolve({ ok: true, json: async () => ({ grouped: {}, phrases: [] }) }); };
global.console = { warn: () => {}, error: () => {}, info: () => {}, debug: () => {}, log: console.log };
global.document = {
  readyState: 'complete',
  head: { appendChild: () => {} },
  body: { appendChild: () => {} },
  createElement: (tag) => ({
    tagName: tag, style: {}, className: '', textContent: '', innerHTML: '',
    appendChild: () => {}, addEventListener: () => {}, remove: () => {},
    setAttribute: () => {}, querySelector: () => null, querySelectorAll: () => [],
  }),
  getElementById: (id) => ({
    id, style: {}, value: '', textContent: '', innerHTML: '',
    appendChild: () => {}, addEventListener: () => {}, remove: () => {},
    querySelector: () => null, querySelectorAll: () => [],
  }),
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener: () => {},
};
global.Audio = function () { return { addEventListener: () => {}, play: () => Promise.resolve(), pause: () => {} }; };
global.CustomEvent = function CustomEvent(type, init) { return { type, detail: init && init.detail }; };
require('./client/static/tts_client.js');
Promise.resolve().then(() => Promise.resolve()).then(() => {
  console.log(JSON.stringify({ calls }));
});
"""
    result = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, timeout=30)
    data = __import__('json').loads(result.strip().splitlines()[-1])
    assert not any('/api/tts/voices' in call for call in data['calls'])
    assert not any('/api/tts/warmup-phrases' in call for call in data['calls'])


def test_autosave_render_deferral_is_bounded_not_recursive_reschedule():
    play = _play_src()
    guard = play[play.index("function __deferCharProfileAutosaveUntilRenderUnwinds"):play.index("function scheduleCharProfileAutosave")]
    assert "attempts < 12" in guard
    assert "Date.now() - startedAt < 1000" in guard
    assert "setTimeout(run, 16)" in guard
    assert "setTimeout(() => __deferCharProfileAutosaveUntilRenderUnwinds" not in guard
    assert "autosave defer abandoned" in guard


def test_player_state_sync_boot_autosave_deferral_does_not_loop():
    snippet_src = _play_src()
    start = snippet_src.index("function __isCharProfileRenderStackActive")
    end = snippet_src.index("function scheduleCharBookQuickPanelSync")
    autosave_guard = snippet_src[start:end]
    depth_start = snippet_src.index("function __enterDepth(name")
    depth_end = snippet_src.index("function __enablePlayerUiSafeMode")
    depth_guard = snippet_src[depth_start:depth_end]
    script = r'''
global.window = global;
window.__depths = { renderPlayerActionsHub: 1, selectQuickActions: 1, scheduleCharProfileSave: 0, markCharProfileDirty: 0 };
window.__debugTrace = [];
global.traceEnter = () => {};
global.__debugSnapshot = (e) => e || {};
global.console = { error: () => {}, warn: () => {}, info: () => {}, debug: () => {}, log: console.log };
''' + depth_guard + r'''
let ROLE = 'player';
let isApplyingRemoteState = false;
let isHydrating = false;
let isSaving = false;
let _charSheet = { name: 'Player' };
let charProfiles = [];
let _charProfileAutosaveTimer = null;
let marked = 0;
let saved = 0;
let timers = 0;
window.__safeMode = {};
window.__combatApplyStateActive = false;
window.__stateSyncApplying = true;
global.document = { getElementById: () => ({ value: 'Player' }) };
const queuedTimers = [];
global.setTimeout = (fn, ms) => { timers += 1; queuedTimers.push({ fn, ms }); return timers; };
global.clearTimeout = () => {};
function __isRemoteStateOrCombatApplying() { return !!window.__stateSyncApplying; }
function markCharProfileDirty() { marked += 1; return true; }
function saveCurrentCharProfile() { saved += 1; }
''' + autosave_guard + r'''
scheduleCharProfileAutosave('state_sync_boot');
Promise.resolve().then(() => {
  window.__depths.renderPlayerActionsHub = 0;
  window.__depths.selectQuickActions = 0;
  window.__stateSyncApplying = false;
  while (queuedTimers.length) queuedTimers.shift().fn();
  return Promise.resolve();
}).then(() => {
  console.log(JSON.stringify({ marked, saved, timers, depth: window.__depths.scheduleCharProfileSave }));
});
'''
    result = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, timeout=30)
    assert result.strip().endswith('{"marked":0,"saved":0,"timers":0,"depth":0}')


from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient
from server.pages.routes import build_router


def _rendered_play(role="player", extra=""):
    app = FastAPI()
    templates = Jinja2Templates(directory=str(ROOT / "client/templates"))
    app.include_router(build_router(templates, "", 8000))
    with TestClient(app) as client:
        resp = client.get(f"/play?session_id=s1&user_id=u1&role={role}{extra}")
    assert resp.status_code == 200
    return resp.text


def _script_srcs(html):
    return re.findall(r'<script[^>]+src="([^"]+)"', html)


def test_rendered_player_manifest_excludes_dm_editor_audio_dice_preloads():
    html = _rendered_play("player")
    forbidden = [
        "dm_assistant.js", "cartographer.js", "editor_panel.js", "asset_library.js",
        "map-library.js", "tts_client.js", "ambient_engine.js", "sfx_engine.js",
        "dice/physics", "dice/geometries", "dice3d.js", "editor/serialization.js",
        "editor/terrain_manifest.js", "editor/asset_initializer.js", "editor/asset_renderer.js",
        "editor/terrain_renderer.js",
    ]
    player_scripts = "\n".join(_script_srcs(html))
    for needle in forbidden:
        assert needle not in player_scripts
    assert "/static/js/ui/player_shell.js" in html
    assert "PLAYER_BOOT_HTML_LOADED" in html
    assert "Player boot failed before scripts loaded." in html


def test_rendered_dm_manifest_keeps_dm_editor_tools():
    html = _rendered_play("dm")
    for needle in ["/static/js/editor/serialization.js", "/static/js/ui/editor_panel.js", "/static/js/ui/asset_library.js", "/static/js/ui/dm_assistant.js", "/static/js/cartographer.js"]:
        assert needle in html


def test_rendered_player_response_size_sane_and_no_full_char_profiles_embed():
    html = _rendered_play("player")
    assert len(html.encode("utf-8")) < 2_500_000
    assert "field=char_profiles" not in html
    assert "4555336" not in html


def test_returning_player_uses_player_manifest_not_dm_manifest():
    html = _rendered_play("player", "&returning=1")
    assert "/static/js/ui/player_shell.js" in html
    assert "/static/js/ui/dm_assistant.js" not in html
    assert "/static/js/editor/serialization.js" not in html


def test_player_manifest_first_external_js_is_core_boot_and_no_forbidden_preload_paths():
    html = _rendered_play("player")
    scripts = _script_srcs(html)
    assert scripts[0] == "/static/js/core/diagnostics.js"
    assert scripts[:7] == [
        "/static/js/core/diagnostics.js",
        "/static/js/core/csrf.js",
        "/static/js/state/store.js",
        "/static/js/core/runtime_bridge.js",
        "/static/js/core/boot_shell.js",
        "/static/js/core/ws.js?v=heartbeat-pong-v4",
        "/static/js/core/message_dispatch.js",
    ]
    forbidden = ["/api/assistant/status", "/api/tts/voices", "/api/tts/warmup-phrases", "/static/assets/audio/manifest.json", "battle_loop_20260328.wav", "clack"]
    for needle in forbidden:
        assert needle not in html
