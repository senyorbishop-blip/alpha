"""Regression coverage for a player rolling THEIR OWN initiative (client side).

Two bugs this pins, both reported as "players weren't able to roll their own
initiative and it wasn't adding their initiative modifier":

1. Ownership for the roll gate (`_canRollInitiative`) and the panel "Roll mine"
   finder (`_rpRollMyInitiative`) was resolved ONLY through the combatant's
   token (`_isMyToken` -> tokens[token_id]). When the player's token wasn't in
   their local roster (different map context / not yet synced) the player could
   not roll at all. Ownership must fall back to the combatant's own owner_id.

2. The initiative modifier resolution only consulted the character sheet when
   the *token* was owned by the user; with a missing token the player's bonus
   was silently dropped. It must resolve the modifier for any combatant the
   player owns, and never fall back to 0 when a stored modifier exists.

These run the REAL functions extracted from play.html through node so the test
breaks if the production ownership/modifier logic regresses.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _extract(src: str, start: str, end: str) -> str:
    s = src.index(start)
    e = src.index(end, s)
    return src[s:e]


def _functions() -> str:
    src = PLAY.read_text(encoding="utf-8")
    ownership = _extract(src, "function _normalizeOwnerKey(value) {", "function _tokenOwnedByUser(token, user) {")
    can_roll = _extract(src, "function _canRollInitiative(com, idx) {", "// ── Start Combat")
    modifier = _extract(src, "function _parseInitiativeModifierValue(value, fallback = null) {", "function _combatCurrentMapContext()")
    return "\n".join([ownership, can_roll, modifier])


_PREAMBLE = """
global.window = global;
let _serverAuthority = { resolvedUserId: SCENARIO.resolvedUserId || SCENARIO.USER_ID };
const USER_ID = SCENARIO.USER_ID;
const NAME = SCENARIO.NAME;
const ROLE = SCENARIO.ROLE;
const tokens = SCENARIO.tokens || {};
let _combat = SCENARIO.combat;
let _charSheet = SCENARIO.charSheet || {};
let charProfiles = SCENARIO.charProfiles || [];
function getEffectiveUserId() { return String((_serverAuthority && _serverAuthority.resolvedUserId) || USER_ID || ''); }
function resolveActiveCharProfileId() { return SCENARIO.activeProfileId || ''; }
function _getCharacterModifiersForDice() { return SCENARIO.diceMods || {}; }
const document = { getElementById: () => null };
"""


def _run(scenario: dict, expr: str):
    code = (
        "const SCENARIO = " + json.dumps(scenario) + ";\n"
        + _PREAMBLE
        + _functions()
        + "\nconsole.log(JSON.stringify({ value: (" + expr + ") }));\n"
    )
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out.strip().splitlines()[-1])["value"]


def _base(**over):
    scenario = {
        "USER_ID": "u1", "NAME": "Player One", "ROLE": "player",
        "tokens": {"hero": {"id": "hero", "name": "Hero", "owner_id": "u1", "initiativeMod": 3}},
        "combat": {"active": True, "turn": 0, "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": "u1", "initiative": None, "modifier": 3},
        ]},
        "charSheet": {"initiative": 3},
    }
    scenario.update(over)
    return scenario


_COM = "_combat.combatants[0]"


def test_player_can_roll_when_their_token_is_loaded():
    assert _run(_base(), f"_canRollInitiative({_COM}, 0)") is True


def test_player_can_roll_when_token_missing_but_combatant_owned():
    # The player's token is NOT in their local roster (e.g. a different map
    # context). Ownership must still resolve from the combatant's owner_id.
    assert _run(_base(tokens={}), f"_canRollInitiative({_COM}, 0)") is True


def test_player_can_roll_when_owner_is_resolved_authority_key():
    # Logged-in player: the token/combatant owner_id is the server-resolved
    # player_key (auth_<id>), matched via getEffectiveUserId().
    scenario = _base(
        resolvedUserId="auth_u1",
        tokens={"hero": {"id": "hero", "name": "Hero", "owner_id": "auth_u1", "initiativeMod": 5}},
        combat={"active": True, "turn": 0, "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": "auth_u1", "initiative": None, "modifier": 5},
        ]},
    )
    assert _run(scenario, f"_canRollInitiative({_COM}, 0)") is True


def test_player_cannot_roll_another_players_combatant():
    scenario = _base(
        tokens={"foe": {"id": "foe", "name": "Other", "owner_id": "u2", "initiativeMod": 1}},
        combat={"active": True, "turn": 0, "combatants": [
            {"id": "cmb-foe", "token_id": "foe", "name": "Other", "owner_id": "u2", "initiative": None, "modifier": 1},
        ]},
    )
    assert _run(scenario, f"_canRollInitiative({_COM}, 0)") is False


def test_modifier_uses_token_initiative_mod_first():
    assert _run(_base(), f"_resolveCombatantInitiativeModifier({_COM}, null)") == 3


def test_modifier_falls_back_to_sheet_when_token_missing():
    # Token gone from roster, but the player owns the combatant -> use the sheet.
    scenario = _base(
        tokens={},
        charSheet={"initiative": 4},
        combat={"active": True, "turn": 0, "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": "u1", "initiative": None, "modifier": 0},
        ]},
    )
    assert _run(scenario, f"_resolveCombatantInitiativeModifier({_COM}, null)") == 4


def test_modifier_uses_stored_combatant_modifier_when_sheet_empty():
    # Sheet not loaded (resolves to 0) but the combatant carries a stored bonus:
    # the player's modifier must NOT be silently dropped to 0.
    scenario = _base(
        tokens={"hero": {"id": "hero", "name": "Hero", "owner_id": "u1"}},
        charSheet={},
        combat={"active": True, "turn": 0, "combatants": [
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": "u1", "initiative": None, "modifier": 6},
        ]},
    )
    assert _run(scenario, f"_resolveCombatantInitiativeModifier({_COM}, null)") == 6
