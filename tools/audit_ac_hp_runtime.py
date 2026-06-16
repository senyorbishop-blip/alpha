#!/usr/bin/env python3
"""Audit saved/fixture characters for AC/HP runtime reconciliation issues."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from server.character.resolver import resolve_character_runtime


def iter_docs(path: Path):
    if path.is_file():
        files=[path]
    else:
        files=list(path.rglob('*.json'))
    for fp in files:
        try:
            data=json.loads(fp.read_text())
        except Exception:
            continue
        stack=[data]
        while stack:
            obj=stack.pop()
            if isinstance(obj, dict):
                if obj.get('classes') or obj.get('abilities') or obj.get('nativeCharacter'):
                    yield fp, obj.get('nativeCharacter') if isinstance(obj.get('nativeCharacter'), dict) else obj
                stack.extend(v for v in obj.values() if isinstance(v,(dict,list)))
            elif isinstance(obj, list):
                stack.extend(obj)


def audit_doc(doc: dict[str, Any]) -> list[str]:
    out=[]
    rt=resolve_character_runtime(doc).get('runtime', {})
    sheet=rt.get('characterSheetRuntime', {})
    ac=sheet.get('ac', {}) if isinstance(sheet.get('ac'), dict) else {'value': sheet.get('ac')}
    hp=sheet.get('hp', {}) if isinstance(sheet.get('hp'), dict) else {}
    if ac.get('needsReview'): out.append('character needs AC review')
    if hp.get('needsReview'): out.append('character needs HP review')
    if ac.get('importedValue') and ac.get('calculatedValue') and ac.get('importedValue') != ac.get('calculatedValue'): out.append('PDF import AC mismatch')
    if hp.get('importedMax') and hp.get('calculatedAverage') and hp.get('importedMax') != hp.get('calculatedAverage'): out.append('PDF import HP mismatch')
    if (doc.get('importedCustomModifiers') or ((doc.get('importMeta') or {}).get('importedCustomModifiers'))): out.append('imported custom modifiers present')
    if doc.get('acManualOverride') not in (None,'') or doc.get('hpManualOverride') not in (None,''): out.append('manual overrides present')
    if int(hp.get('current') or 0) > int(hp.get('max') or 0): out.append('current HP above max HP')
    if not hp.get('hitDice'): out.append('missing hit dice tracking')
    equip=(doc.get('equipment') or {}).get('inventory') if isinstance(doc.get('equipment'), dict) else []
    for item in equip if isinstance(equip, list) else []:
        kind=str(item.get('equipment_kind') or item.get('kind') or item.get('type') or '').lower()
        if kind=='armor' and item.get('equipped') and not item.get('base_ac'): out.append('missing equipped armor data')
        if kind=='shield' and item.get('equipped') and item.get('ac_bonus') in (None,''): out.append('missing shield AC')
    return sorted(set(out))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*', default=['tests'])
    args=ap.parse_args()
    total=0; issues=0
    for raw in args.paths:
        for fp, doc in iter_docs(Path(raw)):
            total+=1
            found=audit_doc(doc)
            if found:
                issues+=1
                print(f'{fp}: {doc.get("name") or (doc.get("identity") or {}).get("name") or "character"}: ' + '; '.join(found))
    print(f'Audited {total} character document(s); {issues} with AC/HP issues.')
    return 1 if issues else 0
if __name__ == '__main__':
    raise SystemExit(main())
