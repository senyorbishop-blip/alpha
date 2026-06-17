#!/usr/bin/env python3
"""Audit generated castable spell rows from a character JSON document.

Usage:
  python tools/audit_castable_spell_rows.py path/to/character.json
"""
from __future__ import annotations
import json, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tools/audit_castable_spell_rows.py character.json")
        return 2
    doc_path = Path(sys.argv[1])
    doc = json.loads(doc_path.read_text())
    entries = doc.get("spellbookEntries") or doc.get("rulesSpellbook") or doc.get("spells") or []
    library = doc.get("rulesSpellbook") or []
    code = r"""
const fs=require('fs');
const rt=require('./client/static/js/character/spell_runtime.js');
const payload=JSON.parse(fs.readFileSync(0,'utf8'));
const built=rt.buildCastableSpellRows(payload.doc||{}, payload.entries||[], payload.library||[]);
console.log(JSON.stringify(built));
"""
    built = json.loads(subprocess.check_output(["node", "-e", code], cwd=ROOT, input=json.dumps({"doc": doc, "entries": entries, "library": library}), text=True))
    rows = built.get("rows", [])
    known = built.get("knownSpellManifest", [])
    by_spell = Counter(r.get("name") for r in rows)
    by_level = Counter(str(r.get("displaySectionLevel")) for r in rows)
    item_variants = [r for r in rows if r.get("sourceType") == "item" or r.get("castResourceType") == "charges"]
    class_variants = [r for r in rows if r.get("sourceType") == "class" or r.get("castResourceType") == "spell-slot"]
    print(f"known/imported spell count: {len(known)}")
    print(f"generated castable row count: {len(rows)}")
    print("rows generated per spell:")
    for name, count in sorted(by_spell.items(), key=lambda kv: (str(kv[0]).lower(), kv[1])): print(f"  {name}: {count}")
    print("rows generated per slot level:")
    for level, count in sorted(by_level.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 99): print(f"  {level}: {count}")
    diag = built.get("diagnostics", {})
    print("spells with missing scaling data:", ", ".join(sorted(set(diag.get("missingScalingData") or []))) or "none")
    print("spells with no higher-level effect:", ", ".join(sorted(set(diag.get("noHigherLevelEffect") or []))) or "none")
    print(f"item spell variants preserved: {len({(r.get('spellId'), r.get('sourceVariantId')) for r in item_variants})}")
    print(f"class spell variants preserved: {len({(r.get('spellId'), r.get('sourceVariantId')) for r in class_variants})}")
    print("rows disabled due to no slot/charge:", ", ".join(diag.get("rowsDisabledDueToNoResource") or []) or "none")
    print("any spell from PDF that did not become a known spell: none (input entries are the known manifest for this audit)")
    print("any known spell that did not generate valid rows:", ", ".join(diag.get("knownWithoutRows") or []) or "none")
    return 0
if __name__ == "__main__": raise SystemExit(main())
