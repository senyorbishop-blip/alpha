"""
Tests for the universal JS spell runtime resolver (resolveSpellRuntime).

Covers every scaling type, all spells mentioned in the spec, imported/PDF
cast_options rows, dropdown behaviour invariants, and attack/save correctness.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Bridge helpers
# ---------------------------------------------------------------------------

def node_eval(script: str) -> object:
    code = "const rt=require('./client/static/js/character/spell_runtime.js');\n" + script
    out = subprocess.check_output(["node", "-e", code], cwd=ROOT, text=True, timeout=30)
    return json.loads(out)


def resolve(card: dict, opts: dict | None = None) -> dict:
    return node_eval(
        f"console.log(JSON.stringify(rt.resolveSpellRuntime("
        f"{json.dumps(card)}, {json.dumps(opts or {})})))"
    )


def resolve_all_levels(spell_id: str, name: str, base: int, up_to: int = 9,
                        char_level: int = 17, mod: int = 5, save_dc: int = 17) -> list[dict]:
    """Resolve a spell at every cast level from base to up_to."""
    script = f"""
const card = {{id:{json.dumps(spell_id)}, name:{json.dumps(name)}}};
const results = [];
for (let cl = {base}; cl <= {up_to}; cl++) {{
  results.push(rt.resolveSpellRuntime(card, {{
    castLevel: cl,
    characterLevel: {char_level},
    spellcastingModifier: {mod},
    saveDc: {save_dc},
  }}));
}}
console.log(JSON.stringify(results));
"""
    return node_eval(script)


# ---------------------------------------------------------------------------
# ── 1. Fireball – all levels 3–9 ──────────────────────────────────────────
# ---------------------------------------------------------------------------

def test_fireball_all_levels():
    expected = {3: "8d6", 4: "9d6", 5: "10d6", 6: "11d6", 7: "12d6", 8: "13d6", 9: "14d6"}
    rows = resolve_all_levels("fireball", "Fireball", 3)
    for r in rows:
        cl = r["castLevel"]
        assert r["finalDamageFormula"] == expected[cl], (
            f"Fireball level {cl}: expected {expected[cl]!r}, got {r['finalDamageFormula']!r}"
        )
    # save-only — no attack roll
    assert not rows[0]["requiresAttackRoll"]
    assert rows[0]["saveAbility"] == "DEX"
    assert rows[0]["saveDc"] == "17"


def test_fireball_at_3rd_and_9th():
    third = resolve({"id": "fireball", "name": "Fireball"}, {"castLevel": 3, "saveDc": "15"})
    ninth = resolve({"id": "fireball", "name": "Fireball"}, {"castLevel": 9, "saveDc": "15"})
    assert third["finalDamageFormula"] == "8d6"
    assert ninth["finalDamageFormula"] == "14d6"
    assert not ninth["requiresAttackRoll"]
    assert ninth["saveAbility"] == "DEX"


# ---------------------------------------------------------------------------
# ── 2. Call Lightning – all levels 3–9 ────────────────────────────────────
# ---------------------------------------------------------------------------

def test_call_lightning_all_levels():
    expected = {3: "3d10", 4: "4d10", 5: "5d10", 6: "6d10", 7: "7d10", 8: "8d10", 9: "9d10"}
    rows = resolve_all_levels("call-lightning", "Call Lightning", 3)
    for r in rows:
        cl = r["castLevel"]
        assert r["finalDamageFormula"] == expected[cl], (
            f"Call Lightning level {cl}: expected {expected[cl]!r}, got {r['finalDamageFormula']!r}"
        )
    assert not rows[0]["requiresAttackRoll"]
    assert rows[0]["saveAbility"] == "DEX"


# ---------------------------------------------------------------------------
# ── 3. Lightning Bolt – all levels 3–9 ───────────────────────────────────
# ---------------------------------------------------------------------------

def test_lightning_bolt_all_levels():
    expected = {3: "8d6", 4: "9d6", 5: "10d6", 6: "11d6", 7: "12d6", 8: "13d6", 9: "14d6"}
    rows = resolve_all_levels("lightning-bolt", "Lightning Bolt", 3)
    for r in rows:
        cl = r["castLevel"]
        assert r["finalDamageFormula"] == expected[cl], (
            f"Lightning Bolt level {cl}: expected {expected[cl]!r}, got {r['finalDamageFormula']!r}"
        )
    assert not rows[0]["requiresAttackRoll"]
    assert rows[0]["saveAbility"] == "DEX"


# ---------------------------------------------------------------------------
# ── 4. Absorb Elements – all levels 1–9 ──────────────────────────────────
# ---------------------------------------------------------------------------

def test_absorb_elements_all_levels():
    """1st → 1d6, 2nd → 2d6, 3rd → 3d6 … 9th → 9d6"""
    rows = resolve_all_levels("absorb-elements", "Absorb Elements", 1)
    for r in rows:
        cl = r["castLevel"]
        expected = f"{cl}d6"
        assert r["finalDamageFormula"] == expected, (
            f"Absorb Elements level {cl}: expected {expected!r}, got {r['finalDamageFormula']!r}"
        )


def test_absorb_elements_3rd_and_4th():
    third = resolve({"id": "absorb-elements", "name": "Absorb Elements"}, {"castLevel": 3})
    fourth = resolve({"id": "absorb-elements", "name": "Absorb Elements"}, {"castLevel": 4})
    assert third["finalDamageFormula"] == "3d6"
    assert fourth["finalDamageFormula"] == "4d6"


# ---------------------------------------------------------------------------
# ── 5. Cure Wounds – healing scales correctly ─────────────────────────────
# ---------------------------------------------------------------------------

def test_cure_wounds_healing_scales():
    first = resolve({"id": "cure-wounds", "name": "Cure Wounds"}, {"castLevel": 1})
    fifth = resolve({"id": "cure-wounds", "name": "Cure Wounds"}, {"castLevel": 5})
    assert first["finalHealingFormula"] == "1d8 + spellcasting modifier"
    assert fifth["finalHealingFormula"] == "5d8 + spellcasting modifier"
    assert fifth["finalDamageFormula"] == ""
    assert fifth["healingType"] == "healing"

    # With a known modifier
    fifth_mod = resolve(
        {"id": "cure-wounds", "name": "Cure Wounds"},
        {"castLevel": 5, "spellcastingModifier": 4}
    )
    assert "5d8" in fifth_mod["finalHealingFormula"]
    assert "+4" in fifth_mod["finalHealingFormula"]


# ---------------------------------------------------------------------------
# ── 6. Magic Missile – dart counting ─────────────────────────────────────
# ---------------------------------------------------------------------------

def test_magic_missile_dart_counts():
    expected_darts = {1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 11}
    rows = resolve_all_levels("magic-missile", "Magic Missile", 1)
    for r in rows:
        cl = r["castLevel"]
        formula = r["displayFormula"]
        assert str(expected_darts[cl]) in formula, (
            f"Magic Missile level {cl}: expected {expected_darts[cl]} darts in '{formula}'"
        )
    assert not rows[0]["requiresAttackRoll"]  # auto-hit, no attack roll


# ---------------------------------------------------------------------------
# ── 7. Scorching Ray – ray counting ──────────────────────────────────────
# ---------------------------------------------------------------------------

def test_scorching_ray_ray_counts():
    expected_rays = {2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10}
    rows = resolve_all_levels("scorching-ray", "Scorching Ray", 2)
    for r in rows:
        cl = r["castLevel"]
        formula = r["displayFormula"]
        assert str(expected_rays[cl]) in formula, (
            f"Scorching Ray level {cl}: expected {expected_rays[cl]} rays in '{formula}'"
        )
    assert rows[0]["requiresAttackRoll"]  # ranged spell attack


# ---------------------------------------------------------------------------
# ── 8. Fire Bolt – cantrip level scaling ─────────────────────────────────
# ---------------------------------------------------------------------------

def test_fire_bolt_cantrip_scaling():
    for char_level, expected_formula in [(1, "1d10"), (4, "1d10"), (5, "2d10"), (10, "2d10"), (11, "3d10"), (16, "3d10"), (17, "4d10")]:
        r = resolve(
            {"id": "fire-bolt", "name": "Fire Bolt"},
            {"characterLevel": char_level}
        )
        assert r["finalDamageFormula"] == expected_formula, (
            f"Fire Bolt at char level {char_level}: expected {expected_formula!r}, got {r['finalDamageFormula']!r}"
        )
    # Cantrips never consume a spell slot
    r = resolve({"id": "fire-bolt", "name": "Fire Bolt"}, {"characterLevel": 17})
    assert r["castLevel"] == 0
    assert not r["consumesSpellSlot"]
    assert r["requiresAttackRoll"]


# ---------------------------------------------------------------------------
# ── 9. Cantrips – all standard tiers correct ──────────────────────────────
# ---------------------------------------------------------------------------

def test_cantrip_tiers():
    cantrips = [
        ("ray-of-frost",    "Ray of Frost",    8),
        ("sacred-flame",    "Sacred Flame",    8),
        ("shocking-grasp",  "Shocking Grasp",  8),
        ("chill-touch",     "Chill Touch",     8),
        ("poison-spray",    "Poison Spray",    12),
        ("thorn-whip",      "Thorn Whip",      6),
        ("vicious-mockery", "Vicious Mockery", 6),
        ("produce-flame",   "Produce Flame",   8),
        ("toll-the-dead",   "Toll the Dead",   8),
        ("eldritch-blast",  "Eldritch Blast",  10),
    ]
    for spell_id, name, die in cantrips:
        for char_level, expected_count in [(1, 1), (5, 2), (11, 3), (17, 4)]:
            r = resolve({"id": spell_id, "name": name}, {"characterLevel": char_level})
            expected = f"{expected_count}d{die}"
            assert r["finalDamageFormula"] == expected, (
                f"{name} char level {char_level}: expected {expected!r}, got {r['finalDamageFormula']!r}"
            )


# ---------------------------------------------------------------------------
# ── 10. Imported / PDF cast_options rows ──────────────────────────────────
# ---------------------------------------------------------------------------

def test_imported_cast_options_rows_create_correct_formula():
    """When a spell card arrives with cast_options, the resolver uses them."""
    card = {
        "id": "fireball",
        "name": "Fireball",
        "level": 3,
        "cast_options": {
            "3": {"cast_level": 3, "formula": "8d6", "effect": "Fireball"},
            "4": {"cast_level": 4, "formula": "9d6", "effect": "Fireball upcast"},
            "5": {"cast_level": 5, "formula": "10d6", "effect": "Fireball upcast"},
        },
    }
    r3 = resolve(card, {"castLevel": 3})
    r4 = resolve(card, {"castLevel": 4})
    r5 = resolve(card, {"castLevel": 5})
    assert r3["displayFormula"] == "8d6",  f"cast_options at 3: {r3['displayFormula']}"
    assert r4["displayFormula"] == "9d6",  f"cast_options at 4: {r4['displayFormula']}"
    assert r5["displayFormula"] == "10d6", f"cast_options at 5: {r5['displayFormula']}"


def test_imported_call_lightning_cast_options():
    card = {
        "id": "call-lightning",
        "name": "Call Lightning",
        "level": 3,
        "cast_options": {
            "3": {"cast_level": 3, "formula": "3d10"},
            "4": {"cast_level": 4, "formula": "4d10"},
        },
    }
    r3 = resolve(card, {"castLevel": 3})
    r4 = resolve(card, {"castLevel": 4})
    assert r3["displayFormula"] == "3d10"
    assert r4["displayFormula"] == "4d10"


def test_imported_absorb_elements_cast_options():
    card = {
        "id": "absorb-elements",
        "name": "Absorb Elements",
        "level": 1,
        "cast_options": {
            "3": {"cast_level": 3, "formula": "3d6"},
            "4": {"cast_level": 4, "formula": "4d6"},
        },
    }
    r3 = resolve(card, {"castLevel": 3})
    r4 = resolve(card, {"castLevel": 4})
    assert r3["displayFormula"] == "3d6"
    assert r4["displayFormula"] == "4d6"


# ---------------------------------------------------------------------------
# ── 11. importedSlotRow option ────────────────────────────────────────────
# ---------------------------------------------------------------------------

def test_imported_slot_row_option_wins():
    """importedSlotRow.formula takes highest priority over everything."""
    r = resolve(
        {"id": "fireball", "name": "Fireball", "level": 3},
        {"castLevel": 9, "importedSlotRow": {"formula": "20d6"}}
    )
    assert r["displayFormula"] == "20d6"


# ---------------------------------------------------------------------------
# ── 12. Null card values don't override BUILTIN data ──────────────────────
# ---------------------------------------------------------------------------

def test_null_card_values_dont_override_builtin():
    """Spell JSON files send null for many fields; BUILTIN must still win."""
    # Simulate a raw JSON card (nulls for all combat fields)
    raw_json_card = {
        "id": "fireball",
        "displayName": "Fireball",
        "level": 3,
        "school": "Evocation",
        "damageFormula": None,
        "damageType": None,
        "savingThrow": None,
        "attackType": None,
        "scalingNote": None,
    }
    r3 = resolve(raw_json_card, {"castLevel": 3})
    r9 = resolve(raw_json_card, {"castLevel": 9})
    assert r3["finalDamageFormula"] == "8d6",  f"got {r3['finalDamageFormula']}"
    assert r9["finalDamageFormula"] == "14d6", f"got {r9['finalDamageFormula']}"
    assert r3["saveAbility"] == "DEX"
    assert not r3["requiresAttackRoll"]


def test_null_call_lightning_still_resolves():
    raw = {"id": "call-lightning", "name": "Call Lightning", "level": 3,
           "damageFormula": None, "savingThrow": None, "scalingNote": None}
    r3 = resolve(raw, {"castLevel": 3})
    r4 = resolve(raw, {"castLevel": 4})
    assert r3["finalDamageFormula"] == "3d10"
    assert r4["finalDamageFormula"] == "4d10"


# ---------------------------------------------------------------------------
# ── 13. Utility spells – no fake damage or attack ─────────────────────────
# ---------------------------------------------------------------------------

def test_utility_spells_no_fake_damage():
    for spell_id, name in [
        ("counterspell",  "Counterspell"),
        ("shield",        "Shield"),
        ("detect-magic",  "Detect Magic"),
        ("misty-step",    "Misty Step"),
        ("dispel-magic",  "Dispel Magic"),
        ("polymorph",     "Polymorph"),
        ("haste",         "Haste"),
        ("banishment",    "Banishment"),
    ]:
        r = resolve({"id": spell_id, "name": name})
        assert r["finalDamageFormula"] == "", f"{name} should have no damage, got {r['finalDamageFormula']!r}"
        assert not r["requiresAttackRoll"],    f"{name} must not require attack roll"


# ---------------------------------------------------------------------------
# ── 14. Save-only spells show DC, no attack ──────────────────────────────
# ---------------------------------------------------------------------------

def test_save_only_spells_have_save_not_attack():
    save_spells = [
        ("fireball",       "Fireball",      "DEX"),
        ("lightning-bolt", "Lightning Bolt","DEX"),
        ("call-lightning", "Call Lightning","DEX"),
        ("thunderwave",    "Thunderwave",   "CON"),
        ("burning-hands",  "Burning Hands", "DEX"),
        ("sacred-flame",   "Sacred Flame",  "DEX"),
        ("shatter",        "Shatter",       "CON"),
        ("moonbeam",       "Moonbeam",      "CON"),
    ]
    for spell_id, name, expected_save in save_spells:
        r = resolve({"id": spell_id, "name": name}, {"saveDc": "15"})
        assert r["saveAbility"] == expected_save, f"{name}: expected save {expected_save!r}, got {r['saveAbility']!r}"
        assert not r["requiresAttackRoll"], f"{name}: must NOT require attack roll (save spell)"


# ---------------------------------------------------------------------------
# ── 15. Attack spells have attack roll, no save ───────────────────────────
# ---------------------------------------------------------------------------

def test_attack_spells_have_attack_roll():
    attack_spells = [
        ("fire-bolt",     "Fire Bolt"),
        ("guiding-bolt",  "Guiding Bolt"),
        ("scorching-ray", "Scorching Ray"),
        ("inflict-wounds","Inflict Wounds"),
        ("shocking-grasp","Shocking Grasp"),
        ("chill-touch",   "Chill Touch"),
        ("ray-of-frost",  "Ray of Frost"),
    ]
    for spell_id, name in attack_spells:
        r = resolve({"id": spell_id, "name": name}, {"characterLevel": 5})
        assert r["requiresAttackRoll"], f"{name}: expected requiresAttackRoll=True"
        assert not r["saveAbility"], f"{name}: should NOT have saveAbility (attack spell)"


# ---------------------------------------------------------------------------
# ── 16. Healing-only spells – no damage ───────────────────────────────────
# ---------------------------------------------------------------------------

def test_healing_spells_no_damage():
    for spell_id, name in [
        ("cure-wounds",        "Cure Wounds"),
        ("healing-word",       "Healing Word"),
        ("mass-cure-wounds",   "Mass Cure Wounds"),
        ("prayer-of-healing",  "Prayer of Healing"),
    ]:
        r = resolve({"id": spell_id, "name": name}, {"castLevel": 3, "spellcastingModifier": 4})
        assert r["finalDamageFormula"] == "", f"{name} should have no damage formula"
        assert r["finalHealingFormula"], f"{name} should have a healing formula"


# ---------------------------------------------------------------------------
# ── 17. Combine function correctness ─────────────────────────────────────
# ---------------------------------------------------------------------------

def test_combine_formula():
    cases = [
        # (base, per, delta, expected)
        ("8d6",                         "1d6", 1,  "9d6"),
        ("8d6",                         "1d6", 5,  "13d6"),
        ("8d6",                         "1d6", 6,  "14d6"),
        ("3d10",                        "1d10",1,  "4d10"),
        ("1d8 + spellcasting modifier", "1d8", 4,  "5d8 + spellcasting modifier"),
        ("2d8",                         "1d8", 0,  "2d8"),   # delta=0 returns base
    ]
    script = f"""
const cases = {json.dumps(cases)};
const results = cases.map(([base, per, delta, _]) =>
  rt.combineSpellFormula(base, per, delta)
);
console.log(JSON.stringify(results));
"""
    results = node_eval(script)
    for (base, per, delta, expected), got in zip(cases, results):
        assert got == expected, f"combine({base!r},{per!r},{delta}): expected {expected!r}, got {got!r}"


# ---------------------------------------------------------------------------
# ── 18. Unknown spell / missing data safe ─────────────────────────────────
# ---------------------------------------------------------------------------

def test_unknown_level_warns():
    r = resolve({"id": "homebrew", "name": "Homebrew Spell"})
    assert "Unknown spell level" in r["warnings"]
    assert r["baseLevel"] is None


def test_missing_formula_warns():
    r = resolve({"id": "mystery-bolt", "name": "Mystery Bolt", "level": 1, "damageType": "fire"})
    assert r["finalDamageFormula"] == ""


# ---------------------------------------------------------------------------
# ── 19. Every compendium spell resolves without crashing ──────────────────
# ---------------------------------------------------------------------------

def test_every_compendium_spell_resolves():
    script = r"""
const fs=require('fs'), path=require('path');
const dir='server/data/rules/5e2024/spells';
let spells=[];
for (const file of fs.readdirSync(dir)) {
  if (!file.endsWith('.json')) continue;
  const data=JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
  spells=spells.concat(data.spells||[]);
}
const out=spells.map(s=>{
  try {
    const r=rt.resolveSpellRuntime(s, {characterLevel:17, castLevel: s.level??s.spell_level??0, spellcastingModifier:5, saveDc:17});
    return {
      id: s.id||'',
      ok: true,
      bad: (r.damageType||r.healingType)&&!r.displayFormula&&!r.warnings.length,
      saveAttack: !!(r.saveAbility&&r.requiresAttackRoll),
    };
  } catch(e) { return {id: s.id||'', ok:false, error:e.message}; }
});
const summary={
  count: out.length,
  crashes: out.filter(r=>!r.ok).length,
  bad: out.filter(r=>r.bad).length,
  saveAttack: out.filter(r=>r.saveAttack).length,
  crashList: out.filter(r=>!r.ok).map(r=>r.id+': '+r.error).slice(0,10),
};
console.log(JSON.stringify(summary));
"""
    result = node_eval(script)
    assert result["count"] > 100, f"Too few spells: {result['count']}"
    assert result["crashes"] == 0, f"Resolver crashes: {result['crashList']}"
    assert result["bad"] == 0, f"Spells with typed damage but no formula: {result['bad']}"
    assert result["saveAttack"] == 0, f"Save spells with attack buttons: {result['saveAttack']}"


# ---------------------------------------------------------------------------
# ── 20. buildSpellCastOptions helper ──────────────────────────────────────
# ---------------------------------------------------------------------------

def test_build_cast_options_fireball():
    script = """
const opts = rt.buildSpellCastOptions(
  {id:'fireball', name:'Fireball'},
  {spellcastingModifier:5, saveDc:17, characterLevel:17}
);
console.log(JSON.stringify(opts));
"""
    opts = node_eval(script)
    assert len(opts) == 7, f"Expected 7 slot options (3–9), got {len(opts)}"
    formulas = [o["formula"] for o in opts]
    expected = ["8d6", "9d6", "10d6", "11d6", "12d6", "13d6", "14d6"]
    assert formulas == expected, f"Fireball cast options: {formulas}"


def test_build_cast_options_absorb_elements():
    script = """
const opts = rt.buildSpellCastOptions(
  {id:'absorb-elements', name:'Absorb Elements'},
  {spellcastingModifier:4, characterLevel:17}
);
console.log(JSON.stringify(opts));
"""
    opts = node_eval(script)
    assert len(opts) == 9, f"Expected 9 options (1–9), got {len(opts)}"
    formulas = [o["formula"] for o in opts]
    expected = [f"{i}d6" for i in range(1, 10)]
    assert formulas == expected, f"Absorb Elements cast options: {formulas}"


def test_build_cast_options_cantrip_is_empty():
    """Cantrips return no cast-level options (they don't use slots)."""
    script = """
const opts = rt.buildSpellCastOptions(
  {id:'fire-bolt', name:'Fire Bolt'},
  {characterLevel:17}
);
console.log(JSON.stringify(opts));
"""
    opts = node_eval(script)
    assert opts == [], f"Cantrip should return [], got {opts}"


# ---------------------------------------------------------------------------
# ── 21. scalingNote text inference (server-enriched cards) ────────────────
# ---------------------------------------------------------------------------

def test_scaling_note_text_parsing():
    """Cards that come from the server may have scalingNote but no scaling_type.
    The resolver must infer slot_damage from the text."""
    # Call Lightning from server: has damageFormula + scalingNote, no scaling_type
    card = {
        "id": "call-lightning-server",
        "name": "Call Lightning",
        "level": 3,
        "damageFormula": "3d10",
        "damageType": "lightning",
        "savingThrow": "DEX",
        "scalingNote": "Each slot level above 3rd adds 1d10 lightning damage to each strike.",
    }
    r3 = resolve(card, {"castLevel": 3})
    r4 = resolve(card, {"castLevel": 4})
    r5 = resolve(card, {"castLevel": 5})
    assert r3["finalDamageFormula"] == "3d10", f"got {r3['finalDamageFormula']}"
    assert r4["finalDamageFormula"] == "4d10", f"got {r4['finalDamageFormula']}"
    assert r5["finalDamageFormula"] == "5d10", f"got {r5['finalDamageFormula']}"


def test_scaling_note_adds_pattern():
    card = {
        "id": "thunderwave-server",
        "name": "Thunderwave",
        "level": 1,
        "damageFormula": "2d8",
        "damageType": "thunder",
        "savingThrow": "CON",
        "scalingNote": "When cast with a slot above 1st, add 1d8 thunder damage for each slot level above 1st.",
    }
    r1 = resolve(card, {"castLevel": 1})
    r3 = resolve(card, {"castLevel": 3})
    assert r1["finalDamageFormula"] == "2d8"
    assert r3["finalDamageFormula"] == "4d8", f"Thunderwave at 3rd: got {r3['finalDamageFormula']}"


# ---------------------------------------------------------------------------
# ── 22. Cantrip vs. leveled spell distinction ──────────────────────────────
# ---------------------------------------------------------------------------

def test_cantrips_do_not_consume_slots():
    for spell_id, name in [("fire-bolt","Fire Bolt"), ("sacred-flame","Sacred Flame"), ("eldritch-blast","Eldritch Blast")]:
        r = resolve({"id": spell_id, "name": name})
        assert not r["consumesSpellSlot"], f"{name} is a cantrip and must not consume a spell slot"
        assert r["castLevel"] == 0


def test_leveled_spells_consume_slots():
    for spell_id, name in [("fireball","Fireball"), ("cure-wounds","Cure Wounds"), ("magic-missile","Magic Missile")]:
        r = resolve({"id": spell_id, "name": name})
        assert r["consumesSpellSlot"], f"{name} must consume a spell slot"
