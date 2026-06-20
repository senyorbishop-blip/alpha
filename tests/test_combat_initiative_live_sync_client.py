import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"

# Minimal stand-ins for the diagnostics globals that play.html sets up at boot
# (window.__depths + the __enterDepth/__exitDepth/__logReentry recursion guards).
# The extracted snippets reference these, so the node harness must provide them.
# __enterDepth mirrors the self-healing production guard: it decrements before
# throwing so a single trip never leaves the depth counter permanently elevated.
_DIAGNOSTICS_PREAMBLE = """
window.__depths = window.__depths || {};
window.__debugTrace = window.__debugTrace || [];
window.__combatApplyStateActive = false;
window.__stateSyncApplying = false;
global.isApplyingRemoteState = false;
global.traceEnter = function () {};
global.__debugSnapshot = function (extra) { return extra || {}; };
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
global.__isRemoteStateOrCombatApplying = function () {
  return !!(global.isApplyingRemoteState || window.__stateSyncApplying || window.__combatApplyStateActive);
};
"""


def _combat_apply_state_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function _combatInitiativeSignature(state) {")
    end = src.index("// ── Combat tab attention: glow, YOUR TURN, coach, hints ───", start)
    return src[start:end]


def _run(state_seq_js: str, *, initial_combat_js: str = "{ active: false, turn: 0, combatants: [] }") -> dict:
    code = f"""
const calls = {{ renderCombat: 0, refreshRightPanelContextUI: 0, renderPartyStatusPanel: 0, refreshBigScreenDisplayOverlay: 0, drawFrame: 0, drawTokens: 0, renderTokens: 0, refreshTokenBadges: 0, refreshCombatBadges: 0, updateActiveContext: 0 }};
global.document = {{ getElementById: () => null }};
global.tokens = {{}};
global.ROLE = 'dm';
global.equipSummary = null;
global._tokenOwnedByMe = () => false;
global._playerActionTurnKey = () => '';
global._playerActionEconomyRuntime = {{ action_surge_armed: false, bonus_action_converted_actions: 0 }};
global._resetInspectResults = () => {{}};
global.renderCombat = () => {{ calls.renderCombat++; }};
global.refreshRightPanelContextUI = () => {{ calls.refreshRightPanelContextUI++; }};
global.renderPartyStatusPanel = () => {{ calls.renderPartyStatusPanel++; }};
global.refreshBigScreenDisplayOverlay = () => {{ calls.refreshBigScreenDisplayOverlay++; }};
global.drawFrame = () => {{ calls.drawFrame++; }};
global.drawTokens = () => {{ calls.drawTokens++; }};
global.renderTokens = () => {{ calls.renderTokens++; }};
global.refreshTokenBadges = () => {{ calls.refreshTokenBadges++; }};
global.refreshCombatBadges = () => {{ calls.refreshCombatBadges++; }};
global.updateActiveContext = () => {{ calls.updateActiveContext++; }};
global._updateCombatTabAttention = () => {{}};
global.window = global;
{_DIAGNOSTICS_PREAMBLE}
let _combat = {initial_combat_js};
let _combatRound = 1;
{_combat_apply_state_snippet()}
{state_seq_js}
console.log(JSON.stringify({{ calls, combat: _combat, sent: (typeof sent !== 'undefined' ? sent : undefined) }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def _initiative_roll_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("let _combatInitiativeResyncTimer = null;")
    end = src.index("function _formatInitiativeCellValue(combatant) {", start)
    return src[start:end]


def _run_initiative_event(event_js: str, *, initial_combat_js: str) -> dict:
    code = f"""
const calls = {{ renderCombat: 0, refreshRightPanelContextUI: 0, updateActiveContext: 0, refreshCombatBadges: 0, refreshTokenBadges: 0 }};
global.window = global;
global.renderCombat = () => {{ calls.renderCombat++; }};
global.refreshRightPanelContextUI = () => {{ calls.refreshRightPanelContextUI++; }};
global.updateActiveContext = () => {{ calls.updateActiveContext++; }};
global.refreshCombatBadges = () => {{ calls.refreshCombatBadges++; }};
global.refreshTokenBadges = () => {{ calls.refreshTokenBadges++; }};
global.clearTimeout = () => {{}};
global.setTimeout = (fn) => {{ fn(); return 1; }};
{_DIAGNOSTICS_PREAMBLE}
let _combat = {initial_combat_js};
function _sortCombatants() {{
  _combat.combatants.sort((a, b) => (b.initiative ?? -99) - (a.initiative ?? -99));
}}
{_initiative_roll_snippet()}
{event_js}
console.log(JSON.stringify({{ calls, combat: _combat, sent: (typeof sent !== 'undefined' ? sent : undefined) }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def test_higher_revision_applies_and_renders():
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 5, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 17 }] });"
    )
    assert result["calls"]["renderCombat"] == 1
    assert result["calls"]["refreshRightPanelContextUI"] == 1
    assert result["combat"]["revision"] == 5
    assert result["combat"]["combatants"][0]["initiative"] == 17


def test_player_initiative_roll_updates_dm_panel_without_refresh():
    # Simulates the DM client receiving the combat_state broadcast triggered by
    # a player's initiative roll: DM panel must update immediately, no refresh.
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 1, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }] });"
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 2, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 14 }] });"
    )
    assert result["calls"]["renderCombat"] == 2
    assert result["combat"]["combatants"][0]["initiative"] == 14


def test_dm_npc_initiative_roll_updates_player_panel_without_refresh():
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 1, "
        "combatants: [{ id: 'mage', token_id: 't-mage', name: 'Mage', initiative: null }] });"
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 2, "
        "combatants: [{ id: 'mage', token_id: 't-mage', name: 'Mage', initiative: 9 }] });",
        initial_combat_js="{ active: false, turn: 0, combatants: [] }",
    )
    assert result["combat"]["combatants"][0]["initiative"] == 9
    assert result["calls"]["renderCombat"] == 2


def test_stale_lower_revision_is_ignored():
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 5, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 17 }] });"
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 3, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 17 }] });"
    )
    # Second lower-revision identical broadcast must be ignored; renderCombat only called once.
    assert result["calls"]["renderCombat"] == 1
    assert result["combat"]["revision"] == 5
    assert result["combat"]["combatants"][0]["initiative"] == 17


def test_equal_revision_with_different_payload_still_applies():
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 4, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 17 }] });"
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 4, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 21 }] });"
    )
    assert result["calls"]["renderCombat"] == 2
    assert result["combat"]["combatants"][0]["initiative"] == 21


def test_initiative_roll_refreshes_token_and_party_surfaces_without_reload():
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 1, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }] });"
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 2, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 14 }] });"
    )
    assert result["calls"]["renderPartyStatusPanel"] == 2
    assert result["calls"]["refreshBigScreenDisplayOverlay"] == 2
    assert result["calls"]["drawFrame"] == 2
    assert result["calls"]["drawTokens"] == 2
    assert result["calls"]["renderTokens"] == 2
    assert result["calls"]["refreshTokenBadges"] == 2
    assert result["calls"]["refreshCombatBadges"] == 2
    assert result["calls"]["updateActiveContext"] == 2
    assert result["combat"]["combatants"][0]["initiative"] == 14



def test_live_combat_state_route_delegates_to_authoritative_handler():
    src = PLAY.read_text(encoding="utf-8")
    assert "case 'combat_state': {" in src
    assert "handleCombatStateLive(p);" in src
    assert "return true;" in src[src.index("case 'combat_state': {"):src.index("case 'combat_initiative_rolled': {")]
    assert "function handleCombatStateLive(payload)" in src
    assert "applyAuthoritativeCombatState(payload, 'combat_state');" in src
    assert "function applyAuthoritativeCombatState(payload, source)" in src


def test_actual_incoming_dispatch_combat_state_from_self_roll_applies():
    result = _run(
        "function handleLegacyMessage(msg){ const p = msg.payload || {}; switch(msg.type){ case 'combat_state': combatApplyState(p); break; } }"
        "handleLegacyMessage({ type: 'combat_state', source_user_id: 'u1', payload: { active: true, turn: 0, round: 1, revision: 2, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 13, roll: 11, modifier: 2 }] } });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 1, combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }] }",
    )
    assert result["calls"]["renderCombat"] == 1
    assert result["combat"]["combatants"][0]["initiative"] == 13


def test_websocket_combat_state_dispatch_forces_right_sidebar_and_active_context():
    result = _run(
        "function handleCombatStateLive(payload) { combatApplyState(payload); return true; }"
        "function handleLegacyMessage(msg){ const p = msg.payload || {}; switch(msg.type){ case 'combat_state': handleCombatStateLive(p); return true; } }"
        "handleLegacyMessage({ type: 'combat_state', payload: { active: true, turn: 0, round: 1, revision: 5, "
        "combatants: [{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 20, roll: 20, modifier: 0 },"
        "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 8, roll: 8, modifier: 0 }],"
        "suspended_combatants: [{ id: 'mage', token_id: 't-mage', name: 'Mage', initiative: 12, suspended_reasons: ['fog'] }] } });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 4, combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }] }",
    )
    assert result["calls"]["renderCombat"] == 1
    assert result["calls"]["refreshRightPanelContextUI"] == 1
    assert result["calls"]["updateActiveContext"] == 1
    assert [c["initiative"] for c in result["combat"]["combatants"]] == [20, 8]
    assert result["combat"]["suspended_combatants"][0]["token_id"] == "t-mage"


def test_actual_incoming_dispatch_dm_npc_roll_updates_dm_client():
    result = _run(
        "function handleLegacyMessage(msg){ const p = msg.payload || {}; switch(msg.type){ case 'combat_state': combatApplyState(p); break; } }"
        "handleLegacyMessage({ type: 'combat_state', payload: { active: true, turn: 0, round: 1, revision: 2, "
        "combatants: [{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 14 }] } });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 1, combatants: [{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: null }] }",
    )
    assert result["combat"]["combatants"][0]["initiative"] == 14


def test_initiative_event_does_not_mutate_roster_and_may_request_resync():
    # Notification-only event. combat_state is the sole authority for the roster,
    # so applyCombatInitiativeRolled must NOT patch initiative/roll locally. When
    # the event hints at a newer revision than we hold, it may ask the server for
    # the authoritative state, but it never mutates or re-renders the roster.
    result = _run_initiative_event(
        "let sent = []; sendWS = (msg) => sent.push(msg); applyCombatInitiativeRolled({ combatant_id: 'guard', token_id: 't-guard', initiative: 18, roll: 18, modifier: 0, revision: 3 });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 2, encounter_id: 'enc-1', combatants: ["
        "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 11, roll: 11, modifier: 0 },"
        "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: null, roll: null, modifier: 0 }"
        "] }",
    )
    assert result["calls"]["renderCombat"] == 0
    guard = next(c for c in result["combat"]["combatants"] if c["id"] == "guard")
    assert guard["initiative"] is None
    assert guard["roll"] is None
    assert any(m.get("type") == "combat_state_request" for m in result["sent"])



def test_dice_result_initiative_does_not_mutate_roster():
    # dice_result is animation/log only; applyInitiativeResultToCombatState must
    # never patch the authoritative combatant rows.
    result = _run_initiative_event(
        "let sent = []; sendWS = (msg) => sent.push(msg); applyInitiativeResultToCombatState({ roll_label: 'Bishop initiative', combatant_id: 'bishop', token_id: 't-bishop', rolls: [8], total: 8, modifier: 0, revision: 2 });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 1, combatants: ["
        "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: null, roll: null, modifier: 0 },"
        "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null, roll: null, modifier: 0 }"
        "] }",
    )
    bishop = next(c for c in result["combat"]["combatants"] if c["id"] == "bishop")
    assert bishop["initiative"] is None
    assert bishop["roll"] is None
    assert result["calls"]["renderCombat"] == 0


def test_combat_initiative_rolled_does_not_mutate_roster():
    result = _run_initiative_event(
        "let sent = []; sendWS = (msg) => sent.push(msg); applyCombatInitiativeRolled({ combatant_id: 'guard', token_id: 't-guard', initiative: 1, roll: 1, modifier: 0, revision: 3 });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 2, combatants: ["
        "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: null, roll: null, modifier: 0 },"
        "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null, roll: null, modifier: 0 }"
        "] }",
    )
    guard = next(c for c in result["combat"]["combatants"] if c["id"] == "guard")
    assert guard["initiative"] is None
    assert guard["roll"] is None
    assert result["calls"]["renderCombat"] == 0


def test_initiative_notification_never_mutates_regardless_of_source():
    base = "{ active: true, turn: 0, round: 1, revision: 1, combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null, roll: null, modifier: 0 }] }"
    for source_user_id in ("self", "other"):
        result = _run_initiative_event(
            f"let sent = []; sendWS = (msg) => sent.push(msg); global.USER_ID = 'self'; applyInitiativeResultToCombatState({{ source_user_id: '{source_user_id}', roll_label: 'Bishop initiative', combatant_id: 'bishop', token_id: 't-bishop', rolls: [8], total: 8, modifier: 0, revision: 2 }});",
            initial_combat_js=base,
        )
        assert result["combat"]["combatants"][0]["initiative"] is None
        assert result["calls"]["renderCombat"] == 0


def test_initiative_notification_returns_false_and_never_renders():
    # The legacy local patcher must report that it applied nothing and must not
    # render: combat_state is the only path that mutates and renders the roster.
    code = f"""
const calls = {{ renderCombat: 0, refreshRightPanelContextUI: 0, updateActiveContext: 0, refreshCombatBadges: 0, refreshTokenBadges: 0, queued: 0 }};
global.window = global;
global.renderCombat = () => {{ calls.renderCombat++; }};
global.refreshRightPanelContextUI = () => {{ calls.refreshRightPanelContextUI++; }};
global.updateActiveContext = () => {{ calls.updateActiveContext++; }};
global.refreshCombatBadges = () => {{ calls.refreshCombatBadges++; }};
global.refreshTokenBadges = () => {{ calls.refreshTokenBadges++; }};
global.queueMicrotask = (fn) => {{ calls.queued++; fn(); }};
global.clearTimeout = () => {{}};
global.setTimeout = (fn) => {{ fn(); return 1; }};
let sent = [];
global.sendWS = (msg) => sent.push(msg);
global.console = {{ warn(){{}}, error(){{}}, debug(){{}}, log: (...args) => process.stdout.write(args.join(' ') + '\\n') }};
{_DIAGNOSTICS_PREAMBLE}
let _combat = {{ active: true, turn: 0, round: 1, revision: 1, combatants: [{{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null, roll: null, modifier: 0 }}] }};
function _sortCombatants() {{}}
{_initiative_roll_snippet()}
const applied = applyInitiativeResultToCombatState({{ combatant_id: 'bishop', token_id: 't-bishop', initiative: 12, roll: 12, modifier: 0, revision: 2 }});
console.log(JSON.stringify({{ applied, calls, combat: _combat }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    result = json.loads(out.strip().splitlines()[-1])
    assert result["applied"] is False
    assert result["combat"]["combatants"][0]["initiative"] is None
    assert result["calls"]["renderCombat"] == 0


def test_lower_revision_with_changed_initiative_applies_with_warning():
    result = _run(
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 5, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 17 }] });"
        "combatApplyState({ active: true, turn: 0, round: 1, revision: 3, "
        "combatants: [{ id: 'c1', token_id: 't1', name: 'Bishop', initiative: 19 }] });"
    )
    assert result["calls"]["renderCombat"] == 2
    assert result["combat"]["combatants"][0]["initiative"] == 19


def test_token_badge_renderer_reads_initiative_from_combatant_state():
    src = PLAY.read_text(encoding="utf-8")
    assert "function getCombatantForToken(tokenId)" in src
    assert "const state = window._combat || window.combatState || _combat || {};" in src
    assert "const list = Array.isArray(state.combatants) ? state.combatants : [];" in src
    assert "const combatant = getCombatantForToken(token && token.id);" in src
    assert "const initiativeValue = combatant ? combatant.initiative : null;" in src
    assert "`INIT ${initiativeValue}`" in src


def _combat_dom_render_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function _combatRosterHpLabel(model) {")
    suspended_start = src.index("function _formatSuspendedCombatantReasons(row) {")
    suspended_end = src.index("function _isMyToken(tokenId) {", suspended_start)
    end = src.index("function _markLoadingWeaponUsedThisTurn(card) {", start)
    return src[start:end] + src[suspended_start:suspended_end]


def _run_dom_render(state_js: str) -> dict:
    code = f"""
class FakeElement {{
  constructor(tag='div') {{ this.tagName = tag; this.children = []; this.dataset = {{}}; this.style = {{}}; this.className = ''; this._html = ''; }}
  appendChild(child) {{ this.children.push(child); return child; }}
  set innerHTML(value) {{ this._html = String(value || ''); this.children = []; }}
  get innerHTML() {{ return this._html + this.children.map(c => c.innerHTML || c._html || '').join(''); }}
  scrollIntoView() {{}}
}}
const calls = {{ sendWS: [] }};
global.window = global;
{_DIAGNOSTICS_PREAMBLE}
global.location = {{ host: 'localhost' }};
global.document = {{ createElement: (tag) => new FakeElement(tag), getElementById: () => null }};
global.ROLE = 'dm';
global.USER_ID = 'dm1';
global.users = {{}};
global.tokens = {{}};
global._currentPoi = null;
global._currentMapContextKey = () => 'world';
global._tokenOwnedByMe = () => false;
global.escapeHtml = (v) => String(v ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
global._combatRosterHpLabel = () => '';
global._combatRosterTokenAvatarHtml = () => '';
global._canRollInitiative = () => false;
global._combat = {{ active: false, turn: 0, combatants: [] }};
global.sendWS = (msg) => calls.sendWS.push(msg);
global.renderPartyStatusPanel = () => {{}};
global.suggestVisibleHostilesForInitiative = () => {{}};
global.setTimeout = (fn) => 0;
function _canRollInitiative() {{ return false; }}
function _formatInitiativeCellValue(combatant) {{
  if (!combatant) return '—';
  const total = combatant.initiative;
  if (total === null || total === undefined) return '—';
  const rawRoll = parseInt(combatant.roll, 10);
  const mod = parseInt(combatant.modifier, 10) || 0;
  if (!Number.isFinite(rawRoll)) return `${{total}}`;
  const modText = mod === 0 ? '' : (mod > 0 ? `+${{mod}}` : `${{mod}}`);
  return modText ? `${{total}} (${{rawRoll}}${{modText}})` : `${{total}} (${{rawRoll}})`;
}}
{_combat_dom_render_snippet()}
{state_js}
console.log(JSON.stringify({{ html: list.innerHTML, order: list.children.map(c => c.dataset.combatantId), classes: list.children.map(c => c.className), calls }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def test_sidebar_dom_renders_authoritative_order_initiative_and_now_label():
    result = _run_dom_render("""
const list = new FakeElement('div');
_combat = { active: true, turn: 0, round: 1, combatants: [
  { id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 14, roll: 14, modifier: 0 },
  { id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 6, roll: 6, modifier: 0 },
  { id: 'mage', token_id: 't-mage', name: 'Mage', initiative: null, roll: null, modifier: 0 },
] };
const roster = _normalizeCombatRoster(_combat);
_renderCombatRoster(list, roster, true);
""")
    assert result["order"] == ["bishop", "guard", "mage"]
    assert "Bishop" in result["html"] and "14 (14)" in result["html"]
    assert "Guard" in result["html"] and "6 (6)" in result["html"]
    assert result["classes"][0].startswith("combat-entry current")
    assert "ce-order now\">Now" in result["html"]


def test_sidebar_dom_does_not_keep_guard_now_after_setup_sort():
    result = _run_dom_render("""
const list = new FakeElement('div');
_combat = { active: true, turn: 0, round: 1, combatants: [
  { id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 14, roll: 14, modifier: 0 },
  { id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 6, roll: 6, modifier: 0 },
] };
const roster = _normalizeCombatRoster(_combat);
_renderCombatRoster(list, roster, true);
""")
    assert result["order"] == ["bishop", "guard"]
    assert "combat-entry current" in result["classes"][0]
    assert "combat-entry current" not in result["classes"][1]


def test_right_sidebar_dom_stale_initiative_recovers_without_refresh():
    result = _run_dom_render("""
const list = new FakeElement('div');
_combat = { active: true, turn: 0, round: 1, combatants: [
  { id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null, roll: null, modifier: 0 },
] };
_renderCombatRoster(list, _normalizeCombatRoster(_combat), true);
_combat = { active: true, turn: 0, round: 1, combatants: [
  { id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 8, roll: 8, modifier: 0 },
] };
_renderCombatRoster(list, _normalizeCombatRoster(_combat), true);
""")
    assert "Bishop" in result["html"]
    assert "8 (8)" in result["html"]
    assert "🎲" not in result["html"]


def test_dm_right_sidebar_dom_shows_suspended_fog_combatants():
    result = _run_dom_render("""
const list = new FakeElement('div');
_combat = { active: true, turn: 0, round: 1, combatants: [
  { id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 20, roll: 20, modifier: 0 },
  { id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 8, roll: 8, modifier: 0 },
], suspended_combatants: [
  { id: 'mage', token_id: 't-mage', name: 'Mage', initiative: 12, suspended_reasons: ['fog'] },
] };
_renderCombatRoster(list, _normalizeCombatRoster(_combat), true);
_renderSuspendedCombatants(list);
""")
    assert "Guard" in result["html"] and "20 (20)" in result["html"]
    assert "Bishop" in result["html"] and "8 (8)" in result["html"]
    assert "Suspended Combatants" in result["html"]
    assert "Mage · Init 12" in result["html"]
    assert "Fog" in result["html"]


def test_player_right_sidebar_dom_hides_suspended_metadata_from_payload():
    result = _run_dom_render("""
ROLE = 'player';
const list = new FakeElement('div');
_combat = { active: true, turn: 0, round: 1, combatants: [
  { id: 'guard', token_id: 't-guard', name: 'Guard', initiative: 20, roll: 20, modifier: 0 },
  { id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 8, roll: 8, modifier: 0 },
] };
_renderCombatRoster(list, _normalizeCombatRoster(_combat), true);
_renderSuspendedCombatants(list);
""")
    assert "Guard" in result["html"] and "20 (20)" in result["html"]
    assert "Bishop" in result["html"] and "8 (8)" in result["html"]
    assert "Mage" not in result["html"]
    assert "Suspended Combatants" not in result["html"]


def test_incoming_combat_state_updates_actual_combat_tab_dom_immediately():
    src = PLAY.read_text(encoding="utf-8")
    roster_start = src.index("function _combatRosterTokenAvatarHtml(model)")
    roster_end = src.index("function _markLoadingWeaponUsedThisTurn", roster_start)
    render_start = src.index("function renderCombat()")
    render_end = src.index("function _formatSuspendedCombatantReasons", render_start)
    code = f"""
class Element {{
  constructor(id = '', tag = 'div') {{ this.id = id; this.tagName = tag; this.children = []; this.style = {{}}; this.dataset = {{}}; this.className = ''; this.classList = {{ add(){{}}, remove(){{}}, toggle(){{}}, contains(){{ return false; }} }}; this._innerHTML = ''; this.textContent = ''; }}
  set innerHTML(value) {{ this._innerHTML = String(value || ''); this.children = []; this.textContent = this._innerHTML.replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ').trim(); }}
  get innerHTML() {{ return this._innerHTML; }}
  appendChild(child) {{ this.children.push(child); this.textContent = this.children.map(c => c.textContent || c.innerHTML || '').join(' '); return child; }}
  querySelectorAll(selector) {{ return selector === '[data-combatant-id]' ? this.children.filter(c => c.dataset && c.dataset.combatantId) : []; }}
  scrollIntoView() {{}}
}}
const elements = {{}};
global.document = {{
  getElementById: (id) => elements[id] || null,
  createElement: (tag) => new Element('', tag),
}};
elements['combat-list'] = new Element('combat-list');
elements['combat-empty'] = new Element('combat-empty');
['combat-controls','combat-move-row','combat-offturn-row','combat-pre','combat-add-row','combat-round-label','combat-turn-summary','combat-prev-btn','combat-next-btn','combat-end-btn','combat-auto-suggest-row','combat-auto-suggest-hostiles','combat-mark-row','combat-spell-tray','combat-weapon-tray'].forEach(id => elements[id] = new Element(id));
global.window = global;
{_DIAGNOSTICS_PREAMBLE}
global.safeClientCall = (label, fn) => {{ try {{ return fn(); }} catch (_err) {{ return null; }} }};
global.location = {{ host: 'localhost' }};
global.console = {{ debug(){{}}, warn(){{}}, error(){{}}, log: (...args) => process.stdout.write(args.join(' ') + '\\n') }};
global.escapeHtml = (value) => String(value ?? '').replace(/[&<>\"]/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[ch]));
global.ROLE = 'dm';
global.USER_ID = 'dm';
global.tokens = {{}};
global.users = {{}};
global._currentPoi = null;
global._currentMapContextKey = () => 'world';
global._tokenOwnedByMe = () => false;
global._dicePhysicsActive = false;
global._renderCombatDebounceTmr = null;
global.renderPlayerActionsHub = () => {{}};
global._getCombatCurrentCombatant = () => null;
global._getCombatOffturnFocusToken = () => null;
global._combatantOwnedByMe = () => false;
global._getUnifiedQuickAttackCards = () => [];
global._rulesSpellbook = [];
global._playerGrantedSpells = [];
global._markTargeting = null;
global._combatAutoSuggestHostiles = false;
global._combatMovePlan = null;
global._combatTargeting = false;
global._combatMovementModeLabel = () => 'grid';
global._renderSuspendedCombatants = () => {{}};
global._updateCombatTabAttention = () => {{}};
global.equipSummary = null;
global.renderPartyStatusPanel = () => {{}};
global.suggestVisibleHostilesForInitiative = () => {{}};
global.setTimeout = (fn) => {{ fn(); return 1; }};
global.clearTimeout = () => {{}};
let _combat = {{ active: true, turn: 0, round: 1, revision: 0, combatants: [{{ id: 'guard', name: 'Guard', initiative: null }}, {{ id: 'bishop', name: 'Bishop', initiative: null }}] }};
let _combatRound = 1;
let _combatInitiativeResyncTimer = null;
let _playerActionEconomyRuntime = {{}};
let partySnapshot = {{}};
let activeContext = {{}};
function _playerActionTurnKey() {{ return ''; }}
function _resetInspectResults() {{}}
function forceCombatStateUISync() {{ renderCombat(); }}
{_combat_apply_state_snippet()}
{src[roster_start:roster_end]}
function _canRollInitiative() {{ return false; }}
function _formatInitiativeCellValue(combatant) {{ return combatant && combatant.initiative !== null && combatant.initiative !== undefined ? String(combatant.initiative) : '--'; }}
{src[render_start:render_end]}
renderCombat();
const before = elements['combat-list'].textContent;
combatApplyState({{ revision: 1, turn: 0, combatants: [
  {{ id: 'guard', name: 'Guard', initiative: 20, roll: 20, modifier: 0 }},
  {{ id: 'bishop', name: 'Bishop', initiative: 4, roll: 4, modifier: 0 }}
] }});
const rows = elements['combat-list'].children.map(row => row.textContent);
console.log(JSON.stringify({{ before, rows, combat: _combat }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    result = json.loads(out.strip().splitlines()[-1])
    assert "Guard" in result["before"] and "--" in result["before"]
    assert any("Guard" in row and "20" in row for row in result["rows"])
    assert any("Bishop" in row and "4" in row for row in result["rows"])
    assert result["combat"]["revision"] == 1
    assert result["combat"]["active"] is True


def test_initiative_notification_patchers_do_not_mutate_roster_source():
    # Source-of-truth guardrail: the legacy notification patchers must not locally
    # assign initiative/roll/order or re-sort the roster. Only the authoritative
    # combat_state apply path (combatApplyState) mutates the roster.
    src = PLAY.read_text(encoding="utf-8")
    body = src[src.index("function applyInitiativeResultToCombatState(result)"):src.index("function applyCombatInitiativeRolled")]
    assert ".initiative =" not in body
    assert ".roll =" not in body
    assert "_sortCombatants(" not in body
    assert "return false;" in body
    rolled = src[src.index("function applyCombatInitiativeRolled"):src.index("function _formatInitiativeCellValue")]
    assert ".initiative =" not in rolled
    assert ".roll =" not in rolled
    assert "_sortCombatants(" not in rolled


def test_authoritative_apply_exists_and_sets_aliases_and_debug():
    src = PLAY.read_text(encoding="utf-8")
    assert "function applyAuthoritativeCombatState(payload, source)" in src
    assert "window.applyAuthoritativeCombatState = applyAuthoritativeCombatState;" in src
    assert "window.__debugCombat = function ()" in src
    # The single apply implementation must set the three runtime aliases.
    apply_body = src[src.index("function combatApplyState(state, source)"):src.index("// ── Authoritative combat_state entry")]
    assert "window._combat = _combat;" in apply_body
    assert "window.combatState = _combat;" in apply_body
    assert "window.currentCombat = _combat;" in apply_body
    # applyAuthoritativeCombatState must not call the autosave / quick-action paths.
    auth_body = src[src.index("function applyAuthoritativeCombatState(payload, source)"):src.index("window.__debugCombat = function ()")]
    for forbidden in ("selectQuickActions", "renderPlayerActionsHub", "markCharProfileDirty", "scheduleCharProfileAutosave", "collectCurrentCharProfile"):
        assert forbidden not in auth_body

