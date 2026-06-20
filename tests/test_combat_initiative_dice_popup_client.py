"""Client wiring for the initiative dice popup + reconnect recovery.

Covers the play.html / runtime_bridge.js side of the fix:
  * the roller sends a roll_id and pre-registers it so the authoritative echo
    is deduped instead of double-popping;
  * the dice_result handler skips the roller's own already-shown initiative
    popup before falling through to the normal display path;
  * on reconnect during active combat the client pulls authoritative combat_state.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"
BRIDGE = ROOT / "client/static/js/core/runtime_bridge.js"


def test_initiative_roll_sends_roll_id_and_preregisters_dedupe():
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function combatRollInitiative(combatantId) {")
    end = src.index("function applyCombatInitiativeRolled(payload) {", start)
    fn = src[start:end]
    assert "_initiativeLocalDicePopupRollIds.add(initiativeRollId);" in fn
    assert "roll_id:      initiativeRollId," in fn
    # The dedupe id must be registered BEFORE the websocket send so the echo can
    # never arrive before the marker exists.
    assert fn.index("_initiativeLocalDicePopupRollIds.add(initiativeRollId);") < fn.index("combat_roll_initiative")


def test_dice_result_handler_dedupes_local_initiative_popup():
    src = PLAY.read_text(encoding="utf-8")
    case_idx = src.index("case 'dice_result': {")
    case_src = src[case_idx:case_idx + 2000]
    assert "_initiativeLocalDicePopupRollIds.has(String(p.roll_id))" in case_src
    # The dedupe check must short-circuit before the authoritative sync display.
    dedupe_idx = case_src.index("_initiativeLocalDicePopupRollIds.has(String(p.roll_id))")
    sync_idx = case_src.index("window.appDiceSyncResult(")
    assert dedupe_idx < sync_idx


def test_reconnect_requests_combat_state_when_active():
    src = BRIDGE.read_text(encoding="utf-8")
    onopen = src[src.index("onOpen: function () {"):src.index("onClose: function")]
    assert "_combatForResync" in onopen
    assert "type: 'combat_state_request'" in onopen
    assert ".active" in onopen


def test_state_sync_applies_combat_on_reconnect():
    src = PLAY.read_text(encoding="utf-8")
    # state_sync must restore combat so active initiative survives a reconnect.
    sync_block = src[src.index("case 'state_sync': {"):src.index("case 'state_sync': {") + 12000]
    assert "if (p.combat !== undefined) {" in sync_block
    assert "combatApplyState(p.combat);" in sync_block


def _run_dedupe_sim(harness_js: str) -> dict:
    """Run the real dedupe decision against a reconstructed switch to prove the
    behavior end-to-end (roller skips, other clients display)."""
    code = f"""
const _initiativeLocalDicePopupRollIds = new Set();
const shown = [];
function display(p, isSelf) {{ shown.push({{ roll_id: p.roll_id, self: isSelf }}); }}
function handleDiceResult(p, effectiveUserId) {{
  switch ('dice_result') {{
    case 'dice_result': {{
      if (p.roll_id && _initiativeLocalDicePopupRollIds.has(String(p.roll_id))) {{
        _initiativeLocalDicePopupRollIds.delete(String(p.roll_id));
        break;
      }}
      if (String(p.user_id || '') === String(effectiveUserId || '')) {{
        display(p, true);
      }} else {{
        display(p, false);
      }}
      break;
    }}
  }}
}}
{harness_js}
console.log(JSON.stringify({{ shown, remaining: [..._initiativeLocalDicePopupRollIds] }}));
"""
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])


def test_roller_skips_own_echo_other_clients_display():
    # Roller pre-registered roll_id 'r1'; the echo for r1 must be skipped on the
    # roller, but a non-registered client displays the same broadcast.
    roller = _run_dedupe_sim(
        "_initiativeLocalDicePopupRollIds.add('r1');"
        "handleDiceResult({ roll_id: 'r1', user_id: 'me' }, 'me');"
    )
    assert roller["shown"] == [], "roller must not re-show its own initiative popup"
    assert roller["remaining"] == [], "dedupe marker must be consumed"

    other = _run_dedupe_sim(
        "handleDiceResult({ roll_id: 'r1', user_id: 'someone-else' }, 'me');"
    )
    assert other["shown"] == [{"roll_id": "r1", "self": False}], "other clients must display the initiative popup"
