"""Dedicated coverage for guardQuickActionBridge (PR 335->339 quick-action
recursion-guard regression): a blocked recursive call must not wedge the
guard permanently, and the guarded bridges must never invoke render or
persistence paths as a side effect of merely dispatching an action.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _guard_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("const __quickBridgeActive = new Set();")
    end = src.index("window._getCombatSpellCastOptions = _getCombatSpellCastOptions;", start)
    return src[start:end]


def _run(driver_js: str) -> dict:
    code = f"""
const calls = {{ renderCombat: 0, markCharProfileDirty: 0, scheduleCharProfileAutosave: 0, save: 0, showToast: 0 }};
global.window = global;
global.console = {{ error(){{}}, trace(){{}}, log: (...args) => process.stdout.write(args.join(' ') + '\\n') }};
global.showToast = () => {{ calls.showToast++; }};
global.renderCombat = () => {{ calls.renderCombat++; }};
global.markCharProfileDirty = () => {{ calls.markCharProfileDirty++; }};
global.scheduleCharProfileAutosave = () => {{ calls.scheduleCharProfileAutosave++; }};
global.performCombatQuickWeaponAttack = (actionOrId, mode) => {{ return 'attacked:' + actionOrId; }};
global.performCombatQuickRollWeaponDamage = () => 'rolled';
global.findCombatSpell = (id) => ({{ id }});
global.performCombatQuickCastSpell = () => 'cast';
global.performCombatQuickRollSpellDamage = () => 'spell-rolled';
global.performExecuteCombatQuickBarSpell = () => 'executed';
global.performOpenCombatQuickBarWeaponAction = () => 'opened';
global.combatQuickRollSpellAttack = () => {{}};
global.combatQuickShowSpellSave = () => {{}};
global.getCombatSpellDamagePreview = () => {{}};
global._getCombatSpellCastOptions = () => {{}};
global._getUnifiedQuickAttackCards = () => {{}};
global._getCombatQuickSpells = () => {{}};
global.getCombatQuickBarRuntime = () => {{}};
global.getCombatQuickBarSpells = () => {{}};
{_guard_snippet()}
{driver_js}
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def test_recursive_bridge_call_is_blocked_without_throwing():
    result = _run(
        "let innerResult;"
        "global.performCombatQuickWeaponAttack = () => { innerResult = window.combatQuickWeaponAttack('id-2'); return 'outer'; };"
        "const outer = window.combatQuickWeaponAttack('id-1');"
        "console.log(JSON.stringify({ outer, innerResult, calls }));"
    )
    assert result["outer"] == "outer"
    assert result["innerResult"] is False, "the nested recursive call must be blocked and return false, not throw"
    assert result["calls"]["showToast"] == 1


def test_guard_self_heals_after_a_blocked_recursion():
    # After a call is blocked (or even completes normally), the guard must
    # release the name so a later, unrelated call still goes through.
    result = _run(
        "global.performCombatQuickWeaponAttack = () => { window.combatQuickWeaponAttack('blocked'); return 'first'; };"
        "const first = window.combatQuickWeaponAttack('a');"
        "const second = window.combatQuickWeaponAttack('b');"
        "console.log(JSON.stringify({ first, second, calls }));"
    )
    assert result["first"] == "first"
    assert result["second"] == "first", "second top-level call after the guard cleared must execute normally"


def test_guard_self_heals_even_if_wrapped_fn_throws():
    result = _run(
        "global.performCombatQuickWeaponAttack = () => { throw new Error('boom'); };"
        "let threw = false;"
        "try { window.combatQuickWeaponAttack('a'); } catch (e) { threw = true; }"
        "global.performCombatQuickWeaponAttack = () => 'recovered';"
        "const after = window.combatQuickWeaponAttack('b');"
        "console.log(JSON.stringify({ threw, after, calls }));"
    )
    assert result["threw"] is True
    assert result["after"] == "recovered", "guard must release the name in its finally block even when fn throws"


def test_quick_action_bridges_do_not_render_or_persist_as_a_side_effect():
    # Dispatching a quick action must not itself trigger a combat repaint or
    # character-sheet autosave — those are the caller's responsibility, not
    # something the bridge plumbing should do implicitly.
    result = _run(
        "window.combatQuickWeaponAttack('a');"
        "window.combatQuickRollWeaponDamage('a', 'normal', false);"
        "window.combatQuickCastSpell('s1', 1);"
        "window.combatQuickRollSpellDamage('s1', 1);"
        "window.executeCombatQuickBarSpell({ id: 's1' });"
        "window.openCombatQuickBarWeaponAction({ id: 'a' });"
        "console.log(JSON.stringify({ calls }));"
    )
    assert result["calls"]["renderCombat"] == 0
    assert result["calls"]["markCharProfileDirty"] == 0
    assert result["calls"]["scheduleCharProfileAutosave"] == 0


def test_cast_spell_bridge_short_circuits_on_missing_spell_without_invoking_perform():
    result = _run(
        "global.findCombatSpell = () => null;"
        "let performCalled = false;"
        "global.performCombatQuickCastSpell = () => { performCalled = true; };"
        "const result = window.combatQuickCastSpell('missing', 1);"
        "console.log(JSON.stringify({ result, performCalled, calls }));"
    )
    assert result["result"] is None
    assert result["performCalled"] is False
    assert result["calls"]["showToast"] == 1
