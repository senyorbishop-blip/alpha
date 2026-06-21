"""Dedicated coverage for forceCombatStateUISync's collision/retry machinery
(PR 335ish regression: a combat_state landing mid-render must never
re-enter renderCombat synchronously, and a burst of colliding combat_state
frames must collapse into a single deferred retry instead of queuing a
microtask storm). test_combat_initiative_live_sync_client.py covers a single
collision through the full combatApplyState path; this file isolates
forceCombatStateUISync itself and drives it through repeated/bursty
collisions.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _force_sync_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("let _combatStateUISyncDeferred = false;")
    end = src.index("function _isAccidentalEmptyCombatState(state) {", start)
    return src[start:end]


def _run(driver_js: str) -> str:
    return f"""
const calls = {{ renderCombat: 0, refreshRightPanelContextUI: 0, updateActiveContext: 0, renderPartyStatusPanel: 0, refreshBigScreenDisplayOverlay: 0, refreshTokenBadges: 0, refreshCombatBadges: 0, renderTokens: 0, drawTokens: 0, drawFrame: 0 }};
const microtasks = [];
global.queueMicrotask = (fn) => {{ microtasks.push(fn); }};
global.window = global;
global.renderCombat = () => {{ calls.renderCombat++; }};
global.refreshRightPanelContextUI = () => {{ calls.refreshRightPanelContextUI++; }};
global.updateActiveContext = () => {{ calls.updateActiveContext++; }};
global.renderPartyStatusPanel = () => {{ calls.renderPartyStatusPanel++; }};
global.refreshBigScreenDisplayOverlay = () => {{ calls.refreshBigScreenDisplayOverlay++; }};
global.refreshTokenBadges = () => {{ calls.refreshTokenBadges++; }};
global.refreshCombatBadges = () => {{ calls.refreshCombatBadges++; }};
global.renderTokens = () => {{ calls.renderTokens++; }};
global.drawTokens = () => {{ calls.drawTokens++; }};
global.drawFrame = () => {{ calls.drawFrame++; }};
{_force_sync_snippet()}
{driver_js}
function drain() {{ while (microtasks.length) {{ microtasks.shift()(); }} }}
"""


def _exec(code: str) -> dict:
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def test_collision_defers_to_a_single_microtask_and_retries_once():
    code = _run(
        "window.__combatRenderActive = true;"
        "forceCombatStateUISync();"
        "const duringCollision = { renderCombat: calls.renderCombat, microtasks: microtasks.length };"
        "window.__combatRenderActive = false;"
        "drain();"
        "console.log(JSON.stringify({ duringCollision, calls }));"
    )
    result = _exec(code)
    assert result["duringCollision"]["renderCombat"] == 0
    assert result["duringCollision"]["microtasks"] == 1
    assert result["calls"]["renderCombat"] == 1


def test_burst_of_colliding_calls_collapses_into_one_deferred_retry():
    # Five combat_state frames land back-to-back while the render is still
    # active. The single-flight flag must collapse all five into exactly one
    # queued microtask, not five (a microtask storm).
    code = _run(
        "window.__combatRenderActive = true;"
        "for (let i = 0; i < 5; i++) { forceCombatStateUISync(); }"
        "const duringBurst = { renderCombat: calls.renderCombat, microtasks: microtasks.length };"
        "window.__combatRenderActive = false;"
        "drain();"
        "console.log(JSON.stringify({ duringBurst, calls }));"
    )
    result = _exec(code)
    assert result["duringBurst"]["microtasks"] == 1, "a burst of collisions must collapse into a single queued retry"
    assert result["duringBurst"]["renderCombat"] == 0
    assert result["calls"]["renderCombat"] == 1


def test_collision_during_deferred_retry_itself_queues_exactly_one_more():
    # While the deferred retry is draining, a fresh collision occurs again
    # (render re-entered). This must queue exactly one more retry, never an
    # unbounded chain.
    code = _run(
        "window.__combatRenderActive = true;"
        "forceCombatStateUISync();"
        "window.__combatRenderActive = false;"
        "global.renderCombat = () => { calls.renderCombat++; window.__combatRenderActive = true; forceCombatStateUISync(); window.__combatRenderActive = false; };"
        "microtasks.shift()();"  # run exactly the one queued retry, which re-collides once
        "const afterFirstDrain = { renderCombat: calls.renderCombat, microtasks: microtasks.length };"
        "console.log(JSON.stringify({ afterFirstDrain, calls }));"
    )
    result = _exec(code)
    assert result["afterFirstDrain"]["microtasks"] == 1, "re-collision inside the retry must queue exactly one more microtask"
    assert result["calls"]["renderCombat"] == 1


def test_no_collision_runs_synchronously_with_all_surfaces():
    code = _run(
        "forceCombatStateUISync();"
        "console.log(JSON.stringify({ microtasks: microtasks.length, calls }));"
    )
    result = _exec(code)
    assert result["microtasks"] == 0
    assert result["calls"]["renderCombat"] == 1
    assert result["calls"]["refreshRightPanelContextUI"] == 1
    assert result["calls"]["updateActiveContext"] == 1
    assert result["calls"]["renderPartyStatusPanel"] == 1
    assert result["calls"]["refreshBigScreenDisplayOverlay"] == 1
    assert result["calls"]["refreshTokenBadges"] == 1
    assert result["calls"]["refreshCombatBadges"] == 1
    assert result["calls"]["renderTokens"] == 1
    assert result["calls"]["drawTokens"] == 1
