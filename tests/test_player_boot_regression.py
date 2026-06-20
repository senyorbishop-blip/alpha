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
