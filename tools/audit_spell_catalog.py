#!/usr/bin/env python3
"""Audit the spell catalog for completeness and data quality.

Usage:
    python tools/audit_spell_catalog.py [--json] [--level N] [--class CLASS]

Exits with non-zero if critical fields are missing for more than 20% of spells.
"""
from __future__ import annotations
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_FIELDS = ["id", "name", "level", "school", "castingTime", "range", "components", "duration"]
COMBAT_FIELDS = ["attackType", "savingThrow", "damageFormula", "damageType", "healingFormula"]
CRITICAL_THRESHOLD = 0.20

def audit_spell(spell):
    missing_required = [f for f in REQUIRED_FIELDS if not spell.get(f) and spell.get(f) != 0]
    level = spell.get("level")
    level_ok = isinstance(level, int) and 0 <= level <= 9
    has_combat_context = bool(spell.get("attackType") or spell.get("savingThrow"))
    return {
        "id": spell.get("id", "?"),
        "name": spell.get("name", "?"),
        "level": level,
        "level_valid": level_ok,
        "missing_required": missing_required,
        "has_description": bool(spell.get("description")),
        "has_combat_context": has_combat_context,
        "is_cantrip": level == 0,
        "legacy_fields": [f for f in ["spell_level", "spellLevel", "level_school"] if f in spell],
    }

def main():
    parser = argparse.ArgumentParser(description="Audit spell catalog completeness")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--level", type=int, default=None)
    parser.add_argument("--class", dest="cls", default=None)
    args = parser.parse_args()

    from server.character.spell_compendium import get_spell_list
    spells = get_spell_list()
    if args.level is not None:
        spells = [s for s in spells if s.get("level") == args.level]
    if args.cls:
        cls_lower = args.cls.lower()
        spells = [s for s in spells if cls_lower in [c.lower() for c in (s.get("classes") or [])]]

    results = [audit_spell(s) for s in spells]
    total = len(results)
    if total == 0:
        print("No spells found.")
        sys.exit(0)

    missing_required_count = sum(1 for r in results if r["missing_required"])
    missing_level_valid = sum(1 for r in results if not r["level_valid"])
    missing_description = sum(1 for r in results if not r["has_description"])
    missing_combat = sum(1 for r in results if not r["has_combat_context"] and not r["is_cantrip"])
    fully_complete = sum(1 for r in results if not r["missing_required"] and r["has_description"])
    has_legacy_fields = sum(1 for r in results if r["legacy_fields"])

    summary = {
        "total_spells": total,
        "fully_complete": fully_complete,
        "pct_complete": round(fully_complete / total * 100, 1) if total else 0,
        "missing_required_fields": missing_required_count,
        "invalid_level": missing_level_valid,
        "missing_description": missing_description,
        "missing_combat_context": missing_combat,
        "has_legacy_fields": has_legacy_fields,
        "issues": [r for r in results if r["missing_required"] or not r["level_valid"] or not r["has_description"]],
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Spell Catalog Audit: {total} spells")
        print(f"  Fully complete:          {fully_complete}/{total} ({summary['pct_complete']}%)")
        print(f"  Missing required fields: {missing_required_count}")
        print(f"  Invalid/missing level:   {missing_level_valid}")
        print(f"  Missing description:     {missing_description}")
        print(f"  Missing combat context:  {missing_combat} (non-cantrips)")
        print(f"  Legacy field names:      {has_legacy_fields}")
        if summary["issues"]:
            print(f"\nIssues ({len(summary['issues'])} spells):")
            for issue in summary["issues"][:30]:
                print(f"  [L{issue['level']}] {issue['name']}: missing={issue['missing_required']}")

    critical_rate = missing_required_count / total if total else 0
    if critical_rate > CRITICAL_THRESHOLD:
        print(f"\nFAIL: {critical_rate:.1%} missing required fields (threshold {CRITICAL_THRESHOLD:.1%})")
        sys.exit(1)
    print("\nPASS: Spell catalog audit passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
