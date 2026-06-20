"""Regression tests for three player-side combat bugs.

Bug 1 (render<->save infinite loop): the render-time selector
``CombatQuickSelectors.selectQuickActions`` must be side-effect free — calling
it repeatedly must never write localStorage (which schedules a char-profile
autosave that re-renders, producing the ``renderPlayerActionsHub recursion
depth exceeded`` loop). Canonicalising stored picks is a one-time migration
(``migrateQuickPicks``) that runs on character load, outside the render path.

Bug 1 (defensive): the ``__enterDepth`` recursion guard must be self-healing —
because it throws BEFORE the caller's try/finally runs, it has to undo its own
increment, otherwise one trip leaves the counter permanently elevated and
wedges the panel for the rest of the session.

Bug 3: players must still RECEIVE and RENDER fog the DM reveals. The fog state
application path (``AppFog.fogApplyUpdate``/``fogApplyState``) is role-agnostic;
this guards against a future role-gate sneaking back in.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _run_node(script: str):
    return json.loads(
        subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, timeout=30)
    )


# ── Bug 1: selector is side-effect free ──────────────────────────────────────

def test_select_quick_actions_does_not_write_localStorage_on_repeat_calls():
    rows = _run_node(
        r"""
global.window = global;
let writes = 0;
global.localStorage = (function () {
  const store = {};
  return {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { writes++; store[k] = String(v); },
    removeItem: k => { writes++; delete store[k]; },
  };
})();
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = () => [{ id: 'fireball', name: 'Fireball', level: 3, baseLevel: 3, source: 'class' }];
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {3: 1}, spellSlotState: {3: 1} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
// Store a NON-canonical pick so a buggy selector would "migrate" (write) on
// every render. The one-time migration runs first (outside render).
sel.writeQuickPicks(['spell:fireball::cast-5']);
sel.migrateQuickPicks();
const writesBeforeRenders = writes;
for (let i = 0; i < 25; i++) sel.selectQuickActions({});
console.log(JSON.stringify({ writesDuringRenders: writes - writesBeforeRenders }));
"""
    )
    assert rows["writesDuringRenders"] == 0


def test_migrate_quick_picks_runs_at_most_once_per_store():
    rows = _run_node(
        r"""
global.window = global;
let writes = 0;
global.localStorage = (function () {
  const store = {};
  return {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { writes++; store[k] = String(v); },
    removeItem: k => { writes++; delete store[k]; },
  };
})();
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = () => [];
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {}, spellSlotState: {} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
sel.writeQuickPicks(['spell:fireball::cast-5']);
const w0 = writes;
sel.migrateQuickPicks();              // canonicalises -> exactly one write
const w1 = writes;
sel.migrateQuickPicks();              // guarded: no-op
sel.migrateQuickPicks();
const w2 = writes;
console.log(JSON.stringify({ firstMigrate: w1 - w0, laterMigrates: w2 - w1, picks: sel.readQuickPicks() }));
"""
    )
    assert rows["firstMigrate"] == 1
    assert rows["laterMigrates"] == 0
    assert rows["picks"] == ["spell:fireball"]


# ── Bug 1 (defensive): self-healing depth guard ──────────────────────────────

def _depth_guard_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function __enterDepth(name")
    end = src.index("function __enablePlayerUiSafeMode")
    return src[start:end]


def test_render_hub_guard_does_not_accumulate_or_wedge():
    rows = _run_node(
        r"""
global.window = global;
window.__depths = {};
window.__debugTrace = [];
global.traceEnter = () => {};
global.__debugSnapshot = (e) => e || {};
global.console = { error: () => {}, warn: () => {}, info: () => {}, debug: () => {}, log: console.log };
"""
        + _depth_guard_snippet()
        + r"""
// Mirror the real renderPlayerActionsHub guard usage: enter before try,
// exit in finally.
function fakeRenderHub() {
  __enterDepth('renderPlayerActionsHub', {}, 5);
  try { /* render body */ } finally { __exitDepth('renderPlayerActionsHub'); }
}
// N balanced top-level calls must never trip the guard and must leave the
// counter at 0.
let trippedDuringNormalUse = false;
for (let i = 0; i < 50; i++) {
  try { fakeRenderHub(); } catch (_e) { trippedDuringNormalUse = true; }
}
const depthAfterNormal = window.__depths.renderPlayerActionsHub;

// Force a genuine over-recursion (depth > 5). The innermost guard must throw,
// but because it self-heals (decrements before throwing) and every outer frame
// runs its finally, the counter must unwind back to 0 — NOT stay stuck.
function recurse(n) {
  __enterDepth('renderPlayerActionsHub', {}, 5);
  try { if (n > 0) recurse(n - 1); } finally { __exitDepth('renderPlayerActionsHub'); }
}
let threw = false;
try { recurse(10); } catch (_e) { threw = true; }
const depthAfterTrip = window.__depths.renderPlayerActionsHub;

// The panel must be usable again after a trip (counter healed back to 0).
let usableAfterTrip = true;
try { fakeRenderHub(); } catch (_e) { usableAfterTrip = false; }

console.log(JSON.stringify({
  trippedDuringNormalUse,
  depthAfterNormal,
  threw,
  depthAfterTrip,
  usableAfterTrip,
  depthFinal: window.__depths.renderPlayerActionsHub,
}));
"""
    )
    assert rows["trippedDuringNormalUse"] is False
    assert rows["depthAfterNormal"] == 0
    assert rows["threw"] is True          # over-recursion is still detected
    assert rows["depthAfterTrip"] == 0    # ...but self-heals instead of wedging
    assert rows["usableAfterTrip"] is True
    assert rows["depthFinal"] == 0


# ── Bug 3: players receive and render DM-revealed fog ─────────────────────────

def test_player_receives_and_renders_dm_fog_reveal():
    rows = _run_node(
        r"""
global.window = global;
require('./client/static/js/render/fog.js');
let drawn = 0;
const state = {
  fogMaps: { world: { enabled: true, cols: 4, rows: 4, cells: new Uint8Array(16) } },
  fogMapCtx: 'world', fogEnabled: true, fogCols: 4, fogRows: 4,
  fogCells: new Uint8Array(16), fogCanvas: { width: 4, height: 4 },
};
const env = {
  ROLE: 'player',                 // a non-DM player
  getCurrentMapContext: () => 'world',
  canEditFog: () => false,        // players cannot AUTHOR fog...
  invalidateFogCache: () => {},
  drawFrame: () => { drawn++; },
  document: { getElementById: () => null },
  getDmMapContext: () => 'world',
  currentPoi: null,
  handlers: {},
};
// DM reveals cells 0,5,10 -> player receives the fog_update broadcast.
window.AppFog.fogApplyUpdate(state, env, { map_ctx: 'world', reveal: true, cells: [0, 5, 10] });
console.log(JSON.stringify({
  enabled: state.fogEnabled,
  revealed: Array.from(state.fogCells).map((v, i) => (v ? i : -1)).filter(i => i >= 0),
  drawFrameCalls: drawn,
}));
"""
    )
    # ...but players must still SEE the fog the DM reveals.
    assert rows["enabled"] is True
    assert rows["revealed"] == [0, 5, 10]
    assert rows["drawFrameCalls"] == 1
