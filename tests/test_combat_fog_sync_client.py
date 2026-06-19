import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _combat_fog_sync_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("let _combat = { active: false")
    end = src.index("let _combatTargeting = false;", start)
    return src[start:end]


def _run_request(map_context_js: str) -> dict:
    code = f"""
const sent = [];
global.window = {{}};
global.tokens = {{}};
global.sendWS = (msg) => sent.push(msg);
global.sendMessageOrWs = (msg) => sent.push(msg);
global.console = console;
{map_context_js}
{_combat_fog_sync_snippet()}
_combat.active = true;
window.requestCombatFogSync('fog_changed');
console.log(JSON.stringify(sent));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)[0]


def test_request_combat_fog_sync_without_current_map_context_uses_world():
    msg = _run_request("delete window.currentMapContext;")
    assert msg["type"] == "combat_fog_sync_request"
    assert msg["payload"]["map_context"] == "world"
    assert msg["payload"]["reason"] == "fog_changed"


def test_request_combat_fog_sync_prefers_get_current_map_context():
    msg = _run_request("window.getCurrentMapContext = () => 'castle-1';")
    assert msg["payload"]["map_context"] == "castle-1"


def test_play_html_combat_fog_sync_never_uses_bare_current_map_context():
    snippet = _combat_fog_sync_snippet()
    assert "currentMapContext" not in snippet
    assert "resolveCurrentMapContextSafe" in snippet
    assert "requestCombatFogSyncDebounced" in snippet
