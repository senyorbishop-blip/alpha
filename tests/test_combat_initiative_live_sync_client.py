import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


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
const calls = {{ renderCombat: 0 }};
global.renderCombat = () => {{ calls.renderCombat++; }};
global.clearTimeout = () => {{}};
global.setTimeout = (fn) => {{ fn(); return 1; }};
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
    assert "combatApplyState(payload);" in src


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


def test_initiative_event_is_notification_only_and_requests_resync():
    result = _run_initiative_event(
        "let sent = []; sendWS = (msg) => sent.push(msg); applyCombatInitiativeRolled({ combatant_id: 'guard', token_id: 't-guard', initiative: 18, roll: 18, modifier: 0, revision: 3 });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 2, encounter_id: 'enc-1', combatants: ["
        "{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 11, roll: 11, modifier: 0 },"
        "{ id: 'guard', token_id: 't-guard', name: 'Guard', initiative: null, roll: null, modifier: 0 }"
        "] }",
    )
    assert result["calls"]["renderCombat"] == 0
    assert [c["id"] for c in result["combat"]["combatants"]] == ["bishop", "guard"]
    assert result["combat"]["combatants"][1]["initiative"] is None
    assert result["sent"] == [{"type": "combat_state_request", "payload": {}}]


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
