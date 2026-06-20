"""Hard repair pass 4 — weapon damage rolls must not freeze the browser and
char_profiles must stop accumulating runtime bloat.

The acceptance criteria are:
  - Player rolls weapon damage without freeze (damage rolls are pure runtime).
  - A damage roll never marks the char profile dirty, schedules an autosave,
    rebuilds the character sheet, or recomputes/rerenders the quick actions.
  - The damage result still appears and the broadcast payload stays lightweight.
  - Saving a profile strips runtime caches.
  - The oversized char_profiles warning names exactly which key is huge.
  - An already-oversized profile can be cleaned without losing real data.
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


def _damage_pipeline_body() -> str:
    """All weapon damage roll functions: the wrapper, the canonical roller, the
    modal-context roller, and the public rollQuickWeapon* helpers."""
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function performQuickWeaponDamageRoll(actionOrId, options = {})")
    end = src.index("function performCombatQuickCastSpell", start)
    return src[start:end]


# ── Tests 1-3: damage rolls never touch profile save / render / select ───────

def test_damage_roll_does_not_schedule_char_profile_autosave():
    body = _damage_pipeline_body()
    assert "scheduleCharProfileAutosave" not in body
    assert "saveCurrentCharProfile" not in body


def test_damage_roll_does_not_mark_char_profile_dirty_or_collect_profile():
    body = _damage_pipeline_body()
    assert "markCharProfileDirty" not in body
    assert "collectCurrentCharProfile" not in body
    assert "syncCharSheetFromBookData" not in body


def test_damage_roll_does_not_render_hub_or_rebuild_quick_actions():
    body = _damage_pipeline_body()
    for forbidden in [
        "renderPlayerActionsHub(",
        "selectQuickActions",
        "CombatQuickBar",
        "refreshCombatQuickActions",
        "renderCombat(",
    ]:
        assert forbidden not in body, forbidden


# ── Test 4: the damage result still appears ──────────────────────────────────

def test_damage_roll_still_shows_result_card_and_local_dice():
    body = _damage_pipeline_body()
    assert "_showCombatResultCard(" in body
    assert "appDiceShowLocalResult" in body


# ── Test 5: the broadcast payload is lightweight ─────────────────────────────

def test_damage_roll_chat_payload_is_lightweight():
    body = _damage_pipeline_body()
    assert "sendWS({ type: 'chat_message'" in body
    # A lightweight payload carries only roll metadata — never the full profile.
    # (_charSheet?.name is fine: that reads a single string, not the whole sheet.)
    for heavy in ["charBook", "nativeRuntime", "nativeCharacter", "char_profile_upsert", "collectCurrentCharProfile", "serializeCharSheetForProfile"]:
        assert heavy not in body, heavy
    # The combat log payload describes the weapon roll, nothing else.
    assert "roll_payload" in body
    assert "weaponName" in body


# ── Single canonical public API for weapon quick actions ─────────────────────

def test_single_public_weapon_quick_api_is_exported():
    src = PLAY.read_text(encoding="utf-8")
    assert "window.openCombatQuickBarWeaponAction = function" in src
    assert "window.rollQuickWeaponAttack = rollQuickWeaponAttack;" in src
    assert "window.rollQuickWeaponDamage = rollQuickWeaponDamage;" in src
    assert "window.rollQuickWeaponCriticalDamage = rollQuickWeaponCriticalDamage;" in src


# ── Autosave forbidden-caller dev trace ──────────────────────────────────────

def test_autosave_emits_dev_trace_when_called_from_forbidden_render_stack():
    src = PLAY.read_text(encoding="utf-8")
    assert "function __traceForbiddenCharProfileAutosave" in src
    guard_start = src.index("function __isCharProfileRenderStackActive()")
    guard_end = src.index("function scheduleCharBookQuickPanelSync")
    guard = src[guard_start:guard_end]
    assert "__traceForbiddenCharProfileAutosave(reason)" in guard
    assert "console.trace(" in guard


# ── Test 6: saving a profile strips runtime caches ───────────────────────────

def _strip_snippet() -> str:
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("const CHAR_PROFILE_RUNTIME_KEYS = Object.freeze([")
    end = src.index("function collectCurrentCharProfile(opts = {})")
    return src[start:end]


def test_strip_char_profile_runtime_fields_removes_caches_keeps_real_data():
    rows = _run_node(
        r"""
global.window = global;
"""
        + _strip_snippet()
        + r"""
const profile = {
  id: 'p1', name: 'Bishop',
  charBook: { abilityScores: { str: 16 }, rawText: 'imported sheet text', _renderedHtml: '<b>x</b>' },
  charSheet: {
    spells: ['fireball'], inventory: [{ name: 'Longsword' }],
    _quickActionCards: [{ huge: 'x'.repeat(1000) }],
    spellRuntime: { cache: 'x'.repeat(1000) },
    itemRuntime: { cache: 'y'.repeat(1000) },
    diceResults: [1,2,3], uiState: { open: true }, modalState: { id: 'm' },
    attackSummaryHtml: '<div>...</div>',
  },
  nativeRuntime: { combatRuntime: { foo: 1 }, resources: { ki: 3 } },
};
_stripCharProfileRuntimeFields(profile);
console.log(JSON.stringify({
  // runtime caches gone
  quick: 'quickActionCards' in profile.charSheet || '_quickActionCards' in profile.charSheet,
  spellRuntime: 'spellRuntime' in profile.charSheet,
  itemRuntime: 'itemRuntime' in profile.charSheet,
  dice: 'diceResults' in profile.charSheet,
  ui: 'uiState' in profile.charSheet,
  modal: 'modalState' in profile.charSheet,
  html: 'attackSummaryHtml' in profile.charSheet,
  renderedHtml: '_renderedHtml' in profile.charBook,
  combatRuntime: 'combatRuntime' in profile.nativeRuntime,
  // real data preserved
  name: profile.name,
  abilityStr: profile.charBook.abilityScores.str,
  rawText: profile.charBook.rawText,
  spells: profile.charSheet.spells,
  inventory: profile.charSheet.inventory.length,
  ki: profile.nativeRuntime.resources.ki,
}));
"""
    )
    # caches removed
    assert rows["quick"] is False
    assert rows["spellRuntime"] is False
    assert rows["itemRuntime"] is False
    assert rows["dice"] is False
    assert rows["ui"] is False
    assert rows["modal"] is False
    assert rows["html"] is False
    assert rows["renderedHtml"] is False
    assert rows["combatRuntime"] is False
    # real data kept
    assert rows["name"] == "Bishop"
    assert rows["abilityStr"] == 16
    assert rows["rawText"] == "imported sheet text"
    assert rows["spells"] == ["fireball"]
    assert rows["inventory"] == 1
    assert rows["ki"] == 3


def test_collect_char_profile_strips_runtime_before_returning():
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function collectCurrentCharProfile(opts = {})")
    end = src.index("function saveCurrentCharProfile(opts = {})", start)
    body = src[start:end]
    assert "return _stripCharProfileRuntimeFields(profile);" in body


def test_oversized_profile_save_logs_top_key_sizes():
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function saveCurrentCharProfile(opts = {})")
    end = src.index("function saveCurrentCharProfileAsNew", start)
    body = src[start:end]
    assert "_charProfileKeySizes(profile)" in body
    assert "oversized profile save" in body
    assert "topKeys" in body


# ── Test 7: the server char_profiles large_field warning names the big key ───

def test_db_large_field_warning_for_char_profiles_includes_top_key_sizes():
    import io
    from contextlib import redirect_stdout
    from server import db

    big = "z" * 600_000
    profiles = {"owner-1": [{"id": "profA", "name": "Bishop", "charSheet": big, "ac": 15}]}
    value = json.dumps(profiles)

    db._large_field_warned.discard("camp-test:char_profiles")
    buf = io.StringIO()
    with redirect_stdout(buf):
        db._warn_large_persisted_field("camp-test", "char_profiles", value)
    out = buf.getvalue()
    assert "large_field" in out
    assert "top_keys[" in out
    # The huge charSheet key must be named explicitly.
    assert "charSheet=" in out
    assert "owner-1/profA" in out


# ── Test 8: an oversized stored profile can be cleaned without losing data ────

def test_server_clean_oversized_profile_strips_runtime_keeps_real_data():
    from server.character.profile_sanitize import clean_oversized_profile, clean_char_profiles_map

    profile = {
        "id": "p1",
        "name": "Bishop",
        "ac": 16,
        "charBook": {"abilityScores": {"str": 16}, "rawText": "real import"},
        "charSheet": {
            "spells": ["fireball"],
            "_quickActionCards": ["x" * 1000],
            "spellRuntime": {"cache": "x" * 1000},
            "combatRuntime": {"foo": 1},
            "renderedHtml": "<div/>",
            "attackSummaryHtml": "<span/>",
        },
    }
    clean_oversized_profile(profile)
    # runtime caches removed
    assert "_quickActionCards" not in profile["charSheet"]
    assert "spellRuntime" not in profile["charSheet"]
    assert "combatRuntime" not in profile["charSheet"]
    assert "renderedHtml" not in profile["charSheet"]
    assert "attackSummaryHtml" not in profile["charSheet"]
    # real character data preserved
    assert profile["name"] == "Bishop"
    assert profile["ac"] == 16
    assert profile["charBook"]["abilityScores"]["str"] == 16
    assert profile["charBook"]["rawText"] == "real import"
    assert profile["charSheet"]["spells"] == ["fireball"]

    # map-level migration cleans every bucket and reports the count.
    profiles_map = {
        "owner-1": [dict(profile, _quickActionCards=["a"]), {"id": "p2", "name": "Ari", "uiState": {"x": 1}}],
    }
    count = clean_char_profiles_map(profiles_map)
    assert count == 2
    assert "_quickActionCards" not in profiles_map["owner-1"][0]
    assert "uiState" not in profiles_map["owner-1"][1]
    assert profiles_map["owner-1"][1]["name"] == "Ari"


def test_server_upsert_strips_runtime_fields_before_storing():
    src = (ROOT / "server/handlers/content.py").read_text(encoding="utf-8")
    assert "from server.character.profile_sanitize import strip_runtime_fields" in src
    assert "strip_runtime_fields(profile)" in src


def test_restore_runs_char_profiles_migration():
    src = (ROOT / "server/restore.py").read_text(encoding="utf-8")
    assert "from server.character.profile_sanitize import clean_char_profiles_map" in src
    assert "clean_char_profiles_map(session.char_profiles)" in src
