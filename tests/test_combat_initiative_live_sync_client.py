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
    return json.loads(out)


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
    return json.loads(out)


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



def test_actual_incoming_dispatch_combat_state_from_self_roll_applies():
    result = _run(
        "function handleLegacyMessage(msg){ const p = msg.payload || {}; switch(msg.type){ case 'combat_state': combatApplyState(p); break; } }"
        "handleLegacyMessage({ type: 'combat_state', source_user_id: 'u1', payload: { active: true, turn: 0, round: 1, revision: 2, "
        "combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: 13, roll: 11, modifier: 2 }] } });",
        initial_combat_js="{ active: true, turn: 0, round: 1, revision: 1, combatants: [{ id: 'bishop', token_id: 't-bishop', name: 'Bishop', initiative: null }] }",
    )
    assert result["calls"]["renderCombat"] == 1
    assert result["combat"]["combatants"][0]["initiative"] == 13


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
    assert "const combatants = (_combat && Array.isArray(_combat.combatants)) ? _combat.combatants : [];" in src
    assert "const combatant = getCombatantForToken(token && token.id);" in src
    assert "const initiativeValue = combatant ? combatant.initiative : null;" in src
    assert "`INIT ${initiativeValue}`" in src
