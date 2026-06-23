"""Hard repair pass 3: combat_state is the single source of truth.

These tests pin the authoritative-apply contract described in the repair task:

  combat_state is the ONLY authoritative source for combatants, initiative
  values, order, active turn, NOW/NEXT marker and the current combatant.

  combat_initiative_rolled / dice_result are notification/animation only and
  must never permanently mutate the roster/order/current turn.

The client logic lives inline in ``client/templates/play.html``; we extract the
relevant function bodies and exercise them in a Node harness so the runtime
source of truth (play.html) is the thing under test.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"

_DIAGNOSTICS_PREAMBLE = """
window.__depths = window.__depths || {};
window.__debugTrace = window.__debugTrace || [];
window.__combatApplyStateActive = false;
window.__stateSyncApplying = false;
global.traceEnter = function () {};
global.__logReentry = function () {};
global.__enterDepth = function (name, details, maxDepth) {
  const cap = maxDepth || 5;
  window.__depths[name] = (Number(window.__depths[name]) || 0) + 1;
  if (window.__depths[name] > cap) {
    window.__depths[name] = Math.max(0, window.__depths[name] - 1);
    throw new Error(name + ' recursion depth exceeded');
  }
};
global.__exitDepth = function (name) {
  window.__depths[name] = Math.max(0, (Number(window.__depths[name]) || 0) - 1);
};
"""


def _combat_apply_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function _combatInitiativeSignature(state) {")
    end = src.index("// ── Combat tab attention: glow, YOUR TURN, coach, hints ───", start)
    return src[start:end]


def _initiative_roll_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("let _combatInitiativeResyncTimer = null;")
    end = src.index("function _formatInitiativeCellValue(combatant) {", start)
    return src[start:end]


def _run(seq_js: str, *, role: str = "dm",
         initial_combat_js: str = "{ active: false, turn: 0, combatants: [] }") -> dict:
    code = f"""
const calls = {{
  renderCombat: 0, refreshRightPanelContextUI: 0, updateActiveContext: 0,
  refreshCombatBadges: 0, refreshTokenBadges: 0, renderPartyStatusPanel: 0,
  refreshBigScreenDisplayOverlay: 0, renderTokens: 0, drawTokens: 0, drawFrame: 0,
  requestRenderFrame: 0,
  selectQuickActions: 0, renderPlayerActionsHub: 0, markCharProfileDirty: 0,
  scheduleCharProfileAutosave: 0, collectCurrentCharProfile: 0,
  warns: 0,
}};
global.window = global;
global.document = {{ getElementById: () => null }};
global.tokens = {{}};
global.ROLE = '{role}';
global.equipSummary = null;
global._tokenOwnedByMe = () => false;
global._playerActionTurnKey = () => '';
global._playerActionEconomyRuntime = {{ action_surge_armed: false, bonus_action_converted_actions: 0 }};
global._resetInspectResults = () => {{}};
global.clearTimeout = () => {{}};
global.setTimeout = (fn) => {{ fn(); return 1; }};
let sent = [];
global.sendWS = (msg) => sent.push(msg);
global.renderCombat = () => {{ calls.renderCombat++; }};
global.refreshRightPanelContextUI = () => {{ calls.refreshRightPanelContextUI++; }};
global.updateActiveContext = () => {{ calls.updateActiveContext++; }};
global.refreshCombatBadges = () => {{ calls.refreshCombatBadges++; }};
global.refreshTokenBadges = () => {{ calls.refreshTokenBadges++; }};
global.renderPartyStatusPanel = () => {{ calls.renderPartyStatusPanel++; }};
global.refreshBigScreenDisplayOverlay = () => {{ calls.refreshBigScreenDisplayOverlay++; }};
global.renderTokens = () => {{ calls.renderTokens++; }};
global.drawTokens = () => {{ calls.drawTokens++; }};
global.drawFrame = () => {{ calls.drawFrame++; }};
global.requestRenderFrame = () => {{ calls.requestRenderFrame++; }};
global._updateCombatTabAttention = () => {{}};
// Forbidden paths: must never be touched by the apply/render path.
global.selectQuickActions = () => {{ calls.selectQuickActions++; }};
global.renderPlayerActionsHub = () => {{ calls.renderPlayerActionsHub++; }};
global.markCharProfileDirty = () => {{ calls.markCharProfileDirty++; }};
global.scheduleCharProfileAutosave = () => {{ calls.scheduleCharProfileAutosave++; }};
global.collectCurrentCharProfile = () => {{ calls.collectCurrentCharProfile++; }};
const _origWarn = console.warn;
console.warn = (...args) => {{ calls.warns++; }};
{_DIAGNOSTICS_PREAMBLE}
let _combat = {initial_combat_js};
let _combatRound = 1;
function _sortCombatants() {{
  _combat.combatants.sort((a, b) => (b.initiative ?? -99) - (a.initiative ?? -99));
}}
{_combat_apply_snippet()}
{_initiative_roll_snippet()}
{seq_js}
console.log(JSON.stringify({{ calls, combat: _combat, sent, debug: window.__debugCombat() }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


_GUARD_BISHOP_NONE = (
    "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 1, "
    "combatants: ["
    "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: null },"
    "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }"
    "] }, 'combat_state');"
)
_GUARD_INIT = (
    "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 2, "
    "combatants: ["
    "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 1 },"
    "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }"
    "] }, 'combat_state');"
)
_BISHOP_INIT = (
    "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 3, "
    "combatants: ["
    "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 7 },"
    "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 1 }"
    "] }, 'combat_state');"
)


# 1. Feed combat_state revision 1 with Guard/Bishop none, roster updates.
def test_revision_1_seeds_roster_with_no_initiative():
    result = _run(_GUARD_BISHOP_NONE)
    inits = {c["id"]: c["initiative"] for c in result["combat"]["combatants"]}
    assert inits == {"guard": None, "bishop": None}
    assert result["combat"]["revision"] == 1
    assert result["calls"]["renderCombat"] == 1
    assert result["debug"]["lastAppliedSource"] == "combat_state"


# 2. Feed revision 2 with Guard initiative, roster updates.
def test_revision_2_applies_guard_initiative():
    result = _run(_GUARD_BISHOP_NONE + _GUARD_INIT)
    inits = {c["id"]: c["initiative"] for c in result["combat"]["combatants"]}
    assert inits == {"guard": 1, "bishop": None}
    assert result["combat"]["revision"] == 2
    assert result["calls"]["renderCombat"] == 2


# 3. Feed revision 3 with Bishop initiative, roster updates (and re-orders).
def test_revision_3_applies_bishop_initiative_and_order():
    result = _run(_GUARD_BISHOP_NONE + _GUARD_INIT + _BISHOP_INIT)
    order = [f"{c['name']}:{c['initiative']}" for c in result["combat"]["combatants"]]
    assert order == ["Bishop:7", "Guard:1"]
    assert result["combat"]["revision"] == 3
    assert result["calls"]["renderCombat"] == 3


# 4. The same authoritative state updates both DM and player render paths.
def test_same_state_updates_dm_and_player_render_paths():
    for role in ("dm", "player"):
        result = _run(_GUARD_BISHOP_NONE + _GUARD_INIT + _BISHOP_INIT, role=role)
        order = [f"{c['name']}:{c['initiative']}" for c in result["combat"]["combatants"]]
        assert order == ["Bishop:7", "Guard:1"], role
        assert result["calls"]["renderCombat"] == 3, role
        assert result["calls"]["refreshRightPanelContextUI"] == 3, role
        assert result["calls"]["updateActiveContext"] == 3, role
        assert result["debug"]["role"] == role


# 5. combat_initiative_rolled alone only animates/logs, never mutates the roster.
def test_combat_initiative_rolled_alone_does_not_mutate_roster():
    result = _run(
        _GUARD_BISHOP_NONE
        + "applyCombatInitiativeRolled({ combatant_id: 'guard', token_id: 't-guard', "
          "initiative: 1, roll: 1, modifier: 0, revision: 1 });"
    )
    inits = {c["id"]: c["initiative"] for c in result["combat"]["combatants"]}
    # Roster is untouched by the notification-only event.
    assert inits == {"guard": None, "bishop": None}
    # Only the single authoritative revision-1 apply rendered.
    assert result["calls"]["renderCombat"] == 1
    assert result["combat"]["revision"] == 1


# 6. Older revision is ignored.
def test_older_revision_is_ignored():
    result = _run(
        _GUARD_INIT  # revision 2 first
        + "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 1, "
          "combatants: [{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 1 },"
          "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }] }, 'stale-combat_state');"
    )
    assert result["combat"]["revision"] == 2
    assert result["calls"]["renderCombat"] == 1  # stale apply did not render
    assert result["debug"]["lastIgnoredSource"] == "stale-combat_state"
    assert "stale-revision" in (result["debug"]["lastIgnoredReason"] or "")


# 7. Same revision with changed order logs a warning and still applies.
def test_same_revision_changed_order_logs_warning_and_applies():
    result = _run(
        "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 4, "
        "combatants: [{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 10 },"
        "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 5 }] }, 'combat_state');"
        "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 4, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 18 },"
        "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 10 }] }, 'combat_state');"
    )
    order = [f"{c['name']}:{c['initiative']}" for c in result["combat"]["combatants"]]
    assert order == ["Bishop:18", "Guard:10"]
    assert result["calls"]["renderCombat"] == 2
    assert result["calls"]["warns"] >= 1


# 8. The render/apply path never touches autosave or quick-action selectors.
def test_apply_path_does_not_touch_autosave_or_quick_actions():
    result = _run(_GUARD_BISHOP_NONE + _GUARD_INIT + _BISHOP_INIT, role="player")
    assert result["calls"]["selectQuickActions"] == 0
    assert result["calls"]["renderPlayerActionsHub"] == 0
    assert result["calls"]["markCharProfileDirty"] == 0
    assert result["calls"]["scheduleCharProfileAutosave"] == 0
    assert result["calls"]["collectCurrentCharProfile"] == 0


# Authoritative aliases + envelope normalization + NOW marker follow current combatant.
def test_aliases_and_envelope_and_current_combatant():
    result = _run(
        # envelope form: payload.combat carries the state
        "applyAuthoritativeCombatState({ combat: { active: true, turn: 1, round: 1, revision: 9, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 7 },"
        "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 1 }] } }, 'combat_state');"
        "global.__aliasMatch = (window._combat === window.combatState) && (window.combatState === window.currentCombat);"
    )
    assert result["combat"]["revision"] == 9
    # turn index 1 → current combatant is the Guard row.
    assert result["debug"]["turn"] == 1
    assert result["debug"]["currentCombatant"] == "Guard"
    assert result["debug"]["order"] == ["Bishop:7", "Guard:1"]


def test_debug_combat_reports_last_ignored_for_invalid_payload():
    result = _run("applyAuthoritativeCombatState(null, 'combat_state');")
    assert result["debug"]["lastIgnoredReason"] == "invalid-payload"


def test_stale_inactive_default_cannot_overwrite_active_combat():
    result = _run(
        "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 5, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 12 }] }, 'authoritative_snapshot');"
        "applyAuthoritativeCombatState({ active: false, turn: 0, round: 1, revision: 4, combatants: [] }, 'state_sync');"
    )
    assert result["combat"]["active"] is True
    assert result["combat"]["revision"] == 5
    assert [c["name"] for c in result["combat"]["combatants"]] == ["Bishop"]
    assert result["calls"]["renderCombat"] == 1
    assert "stale-revision" in (result["debug"]["lastIgnoredReason"] or "")


def test_newer_inactive_revision_can_clear_combat():
    result = _run(
        "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, revision: 5, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 12 }] }, 'combat_state');"
        "applyAuthoritativeCombatState({ active: false, turn: 0, round: 1, revision: 6, combatants: [], reason: 'clear_combat' }, 'clear_combat');"
    )
    assert result["combat"]["active"] is False
    assert result["combat"]["revision"] == 6
    assert result["combat"]["combatants"] == []
    assert result["calls"]["renderCombat"] == 2


def test_missing_revision_logs_warning_but_remains_backward_compatible():
    result = _run(
        "applyAuthoritativeCombatState({ active: true, turn: 0, round: 1, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 12 }] }, 'legacy_state_sync');"
    )
    assert result["combat"]["active"] is True
    assert result["combat"]["revision"] == 0
    assert result["calls"]["warns"] >= 1
    assert result["debug"]["lastAppliedSource"] == "legacy_state_sync"
