#!/usr/bin/env python3
"""
Comprehensive spell scaling audit.

Scans all rules spells (JSON), imported fixtures, and test characters.
Runs each through the universal JS resolver (resolveSpellRuntime) and
reports every category of problem described in the spell scaling spec.

Exit 0 = no blocking issues.  Exit 1 = blocking issues found.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPELL_DIR = ROOT / "server/data/rules/5e2024/spells"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_compendium_spells() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(SPELL_DIR.glob("spells-*.json")):
        data = json.loads(path.read_text())
        file_level = data.get("level")
        for spell in data.get("spells", []):
            spell = dict(spell)
            spell["_source_file"] = path.name
            spell["_file_level"] = file_level
            rows.append(spell)
    return rows


def load_fixture_spells() -> list[dict]:
    """Collect spells from any JSON fixture files under tests/fixtures/."""
    rows: list[dict] = []
    fixtures_dir = ROOT / "tests" / "fixtures"
    if not fixtures_dir.exists():
        return rows
    for json_file in fixtures_dir.rglob("*.json"):
        try:
            data = json.loads(json_file.read_text())
        except Exception:
            continue
        # Support: {"spells": [...]} or list of spell objects
        candidates = data.get("spells", data) if isinstance(data, dict) else data
        if not isinstance(candidates, list):
            continue
        for item in candidates:
            if isinstance(item, dict) and ("id" in item or "name" in item):
                item = dict(item)
                item["_source_file"] = json_file.name
                rows.append(item)
    return rows


# ---------------------------------------------------------------------------
# JS resolver bridge
# ---------------------------------------------------------------------------

_RESOLVE_SCRIPT = r"""
const rt = require('./client/static/js/character/spell_runtime.js');
let raw = '';
process.stdin.on('data', d => raw += d);
process.stdin.on('end', () => {
const spells = JSON.parse(raw);
const results = spells.map(s => {
  try {
    const levels = [];
    const base = s.level ?? s.spell_level ?? 0;
    if (base === 0) {
      levels.push({castLevel: 0, charLevel: 1});
      levels.push({castLevel: 0, charLevel: 5});
      levels.push({castLevel: 0, charLevel: 11});
      levels.push({castLevel: 0, charLevel: 17});
    } else {
      for (let cl = base; cl <= 9; cl++) levels.push({castLevel: cl, charLevel: 17});
    }
    const rows = levels.map(opts =>
      rt.resolveSpellRuntime(s, {
        castLevel: opts.castLevel,
        characterLevel: opts.charLevel,
        spellcastingModifier: 5,
        saveDc: 17,
      })
    );
    return {id: s.id || s.name || '', name: s.displayName || s.name || s.id || '', ok: true, rows: rows};
  } catch(e) {
    return {id: s.id || s.name || '', name: s.displayName || s.name || s.id || '', ok: false, error: e.message, rows: []};
  }
});
process.stdout.write(JSON.stringify(results));
});
"""


def resolve_batch(spells: list[dict]) -> list[dict]:
    """Run resolveSpellRuntime on a batch of spells via Node.js."""
    payload = json.dumps(spells)
    result = subprocess.run(
        ["node", "-e", _RESOLVE_SCRIPT],
        input=payload,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"[WARN] Node error: {result.stderr[:400]}", file=sys.stderr)
        return []
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Per-level formula reference for key spells
# ---------------------------------------------------------------------------

EXPECTED_FORMULAS: dict[str, dict[int, str]] = {
    "fireball":      {3: "8d6",  4: "9d6",  5: "10d6", 6: "11d6", 7: "12d6", 8: "13d6", 9: "14d6"},
    "call-lightning":{3: "3d10", 4: "4d10", 5: "5d10", 6: "6d10", 7: "7d10", 8: "8d10", 9: "9d10"},
    "lightning-bolt":{3: "8d6",  4: "9d6",  5: "10d6", 6: "11d6", 7: "12d6", 8: "13d6", 9: "14d6"},
    "absorb-elements":{1: "1d6", 2: "2d6",  3: "3d6",  4: "4d6",  5: "5d6",  6: "6d6",  7: "7d6",  8: "8d6", 9: "9d6"},
    "vampiric-touch":{3: "3d6",  4: "4d6",  5: "5d6"},
    "shatter":       {2: "3d8",  3: "4d8",  4: "5d8"},
    "thunderwave":   {1: "2d8",  2: "3d8",  3: "4d8"},
    "burning-hands": {1: "3d6",  2: "4d6",  3: "5d6"},
}


def _normalise_formula(f: str) -> str:
    """Strip whitespace and lowercase for comparison."""
    return f.strip().lower().replace(" ", "").replace("+spellcastingmodifier", "")


# ---------------------------------------------------------------------------
# Issue categorisation
# ---------------------------------------------------------------------------

def audit(spells: list[dict], label: str, results: list[dict], issues: defaultdict) -> None:
    """Compare raw spells against their resolved runtime rows and record issues."""
    ids_seen: dict[str, int] = {}
    for spell, res in zip(spells, results):
        name = spell.get("displayName") or spell.get("name") or spell.get("id") or "<unknown>"
        sid  = str(spell.get("id") or "").strip()
        src  = spell.get("_source_file", label)

        # Crash / resolver failure
        if not res.get("ok"):
            issues["resolver_crash"].append(f"{name} ({src}): {res.get('error','')}")
            continue

        rows = res.get("rows", [])
        if not rows:
            continue

        base_row = rows[0]
        base_level = base_row.get("baseLevel")
        scaling_type = base_row.get("scalingType", "none")

        # Missing spell ID
        if not sid:
            issues["missing_spell_id"].append(f"{name} ({src})")

        # Duplicate IDs within this batch
        if sid:
            ids_seen[sid] = ids_seen.get(sid, 0) + 1
            if ids_seen[sid] == 2:
                issues["duplicate_spell_id"].append(f"{sid} ({src})")

        # Missing base level
        if base_level is None:
            issues["missing_base_level"].append(f"{name} ({src})")

        # Cantrip shown as slot-spell or vice versa
        raw_level = spell.get("level") or spell.get("spell_level")
        if raw_level is not None:
            if str(raw_level).lower() == "cantrip" and base_level != 0:
                issues["cantrip_shown_as_slot_spell"].append(f"{name} ({src})")
            elif raw_level == 0 and base_level != 0:
                issues["cantrip_shown_as_slot_spell"].append(f"{name} ({src})")
            elif isinstance(raw_level, int) and raw_level > 0 and base_level == 0:
                issues["leveled_shown_as_cantrip"].append(f"{name} ({src})")

        # Damage / healing type present but no formula
        has_dmg_type  = bool(spell.get("damageType") or spell.get("damage_type"))
        has_heal_type = bool(spell.get("healingType") or spell.get("healing_type"))
        display = str(base_row.get("displayFormula") or "").strip()
        if (has_dmg_type or has_heal_type) and not display:
            issues["missing_formula_for_typed_spell"].append(f"{name} ({src}): type={spell.get('damageType') or spell.get('healingType')}")

        # Upcast text but no scaling
        upcast_text = bool(
            spell.get("scalingNote") or spell.get("higher_level_text") or
            spell.get("scalingNote") or spell.get("atHigherLevels")
        )
        if upcast_text and scaling_type == "none" and base_level not in (None, 0):
            issues["upcast_text_no_scaling"].append(f"{name} ({src}): '{str(spell.get('scalingNote',''))[:60]}'")

        # Save-only spell has attack button
        save = str(base_row.get("saveAbility") or "").strip()
        requires_attack = bool(base_row.get("requiresAttackRoll"))
        if save and requires_attack:
            issues["save_spell_has_attack_button"].append(f"{name} ({src}): save={save}")

        # Attack spell missing attack type
        if requires_attack and not str(base_row.get("attackType") or "").strip():
            issues["attack_spell_missing_type"].append(f"{name} ({src})")

        # Spell level mismatch between JSON file level and declared level
        file_level = spell.get("_file_level")
        declared   = spell.get("level") or spell.get("spell_level")
        if file_level is not None and declared is not None and file_level != declared:
            issues["spell_level_mismatch"].append(f"{name} ({src}): file says {file_level}, spell says {declared}")

        # Expected formula check
        slug = sid.lower().strip() if sid else _normalise_formula(name)
        if slug in EXPECTED_FORMULAS:
            for row in rows:
                cl = row.get("castLevel")
                if cl is None:
                    continue
                expected = EXPECTED_FORMULAS[slug].get(cl)
                if expected is None:
                    continue
                got = str(row.get("displayFormula") or "").strip()
                if _normalise_formula(got) != _normalise_formula(expected):
                    issues["wrong_formula_at_level"].append(
                        f"{name} at level {cl}: expected '{expected}', got '{got}'"
                    )

        # Preview formula differs from roll formula at base level
        raw_preview = str(spell.get("damageFormula") or spell.get("healingFormula") or "").strip()
        if raw_preview and display and base_row.get("castLevel") == base_level:
            if scaling_type not in ("extra_dart_per_slot", "extra_ray_per_slot", "cast_options") and \
               _normalise_formula(raw_preview) != _normalise_formula(display):
                issues["preview_differs_from_roll"].append(
                    f"{name} ({src}): preview='{raw_preview}' roll='{display}'"
                )

        # Higher-level imported rows (cast_options) check
        cast_opts = spell.get("cast_options") or spell.get("castOptions") or {}
        if isinstance(cast_opts, dict) and len(cast_opts) > 1:
            for lvl_key, opt in cast_opts.items():
                opt_formula = str((opt or {}).get("formula") or "").strip()
                if not opt_formula:
                    issues["cast_option_missing_formula"].append(f"{name} ({src}) at level {lvl_key}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    issues: defaultdict[str, list[str]] = defaultdict(list)

    print("Loading compendium spells …")
    compendium = load_compendium_spells()
    print(f"  {len(compendium)} spells from {SPELL_DIR.name}/")

    print("Resolving compendium spells …")
    comp_results = resolve_batch(compendium)

    print("Auditing compendium spells …")
    audit(compendium, "compendium", comp_results, issues)

    print("Loading fixture / imported spells …")
    fixtures = load_fixture_spells()
    if fixtures:
        print(f"  {len(fixtures)} fixture spells")
        fix_results = resolve_batch(fixtures)
        audit(fixtures, "fixtures", fix_results, issues)
    else:
        print("  (no fixture spells found)")

    # ── Report ────────────────────────────────────────────────────────────
    BLOCKING = {
        "resolver_crash",
        "missing_spell_id",
        "duplicate_spell_id",
        "save_spell_has_attack_button",
        "wrong_formula_at_level",
    }
    CATEGORIES = [
        ("resolver_crash",               "Resolver crashes"),
        ("missing_spell_id",             "Missing spell ID"),
        ("duplicate_spell_id",           "Duplicate spell IDs"),
        ("missing_base_level",           "Missing base level"),
        ("missing_formula_for_typed_spell","Typed spell missing formula"),
        ("upcast_text_no_scaling",       "Upcast text but no scaling data"),
        ("save_spell_has_attack_button", "Save-only spell has attack button"),
        ("attack_spell_missing_type",    "Attack spell missing attack type"),
        ("spell_level_mismatch",         "Spell level mismatch"),
        ("wrong_formula_at_level",       "Wrong formula at specific level"),
        ("preview_differs_from_roll",    "Preview formula differs from roll formula"),
        ("cast_option_missing_formula",  "Cast option (imported) missing formula"),
        ("cantrip_shown_as_slot_spell",  "Cantrip shown as slot spell"),
        ("leveled_shown_as_cantrip",     "Leveled spell shown as cantrip"),
    ]

    total_scanned = len(compendium) + len(fixtures)
    print(f"\n{'='*60}")
    print(f"Spell scaling audit — {total_scanned} spells scanned")
    print(f"{'='*60}")

    has_blocking = False
    for key, label in CATEGORIES:
        vals = issues.get(key, [])
        prefix = "❌ BLOCKING" if key in BLOCKING else "⚠️  WARNING "
        marker = "❌" if (key in BLOCKING and vals) else ("✅" if not vals else "⚠️ ")
        print(f"\n{marker} {label}: {len(vals)}")
        for v in vals[:15]:
            print(f"   - {v}")
        if len(vals) > 15:
            print(f"   … and {len(vals) - 15} more")
        if key in BLOCKING and vals:
            has_blocking = True

    print(f"\n{'='*60}")
    if has_blocking:
        print("RESULT: BLOCKING issues found — fix before release.")
        return 1
    print("RESULT: No blocking issues. Warnings above are advisory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
