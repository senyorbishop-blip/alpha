#!/usr/bin/env python3
"""Audit spell compendium metadata against the universal JS spell runtime resolver."""
from __future__ import annotations
import json, subprocess, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPELL_DIR = ROOT / 'server/data/rules/5e2024/spells'

def load_spells():
    rows=[]
    for p in sorted(SPELL_DIR.glob('spells-*.json')):
        data=json.loads(p.read_text())
        for s in data.get('spells',[]):
            s=dict(s); s['_file']=p.name; s['_file_level']=data.get('level'); rows.append(s)
    return rows

def resolve_all(spells):
    code = """
const rt=require('./client/static/js/character/spell_runtime.js');
const fs=require('fs'); const spells=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(spells.map(s=>rt.resolveSpellRuntime(s,{characterLevel:17,castLevel:s.level??s.spell_level??0,saveDc:15}))));
"""
    return json.loads(subprocess.check_output(['node','-e',code], input=json.dumps(spells), cwd=ROOT, text=True))

def main():
    spells=load_spells(); runtimes=resolve_all(spells); ids=[str(s.get('id') or '').strip() for s in spells]
    counts=Counter(ids); issues=[]
    for sid,c in counts.items():
        if not sid: issues.append(('missing spell ID', c, ''))
        elif c>1: issues.append(('duplicate spell IDs', c, sid))
    for s,r in zip(spells,runtimes):
        name=s.get('displayName') or s.get('name') or s.get('id') or '<unknown>'
        if r['baseLevel'] is None: issues.append(('missing base level',1,name))
        if r['baseLevel'] is None and any(x in r['warnings'] for x in ['Unknown spell level']): issues.append(('spells that would show as cantrip because level is missing',1,name))
        if (s.get('damageType') or s.get('healingType')) and not r['displayFormula']: issues.append(('missing damage/healing formula for damage/healing spells',1,name))
        if r['scalingType'] not in ('none','slot_damage','slot_healing','extra_dart_per_slot','extra_ray_per_slot','extra_target_per_slot','text_only','cantrip_level'):
            issues.append(('invalid scaling data',1,name+': '+r['scalingType']))
        if r['saveAbility'] and r['requiresAttackRoll']: issues.append(('save-only spell incorrectly marked as attack spell',1,name))
        if r['requiresAttackRoll'] and not r['attackType']: issues.append(('attack spell missing attack type',1,name))
        if (s.get('scalingNote') or s.get('higher_level_text')) and r['scalingType']=='none': issues.append(('spell with upcast text but no scaling data',1,name))
        if r['scalingType']!='none' and r['warnings'] and r['displayFormula']: issues.append(('spell with scaling data that cannot resolve',1,name+': '+'; '.join(r['warnings'])))
        if s.get('level') != s.get('_file_level') and s.get('level') is not None: issues.append(('spell level mismatch between level, spell_level, level_school, and cast options',1,f"{name}: level {s.get('level')} in {s.get('_file')}"))
        preview=s.get('damageFormula') or s.get('healingFormula') or ''
        if preview and r['displayFormula'] and preview != r['displayFormula'] and r['castLevel']==r['baseLevel'] and r['scalingType'] not in ('extra_dart_per_slot','extra_ray_per_slot'):
            issues.append(('spells that have damage preview different from roll formula',1,f"{name}: {preview} vs {r['displayFormula']}"))
    grouped={}
    for kind,_,detail in issues: grouped.setdefault(kind,[]).append(detail)
    print(f"Spell runtime audit scanned {len(spells)} spells.")
    for key in ['missing spell ID','duplicate spell IDs','missing base level','missing damage/healing formula for damage/healing spells','invalid scaling data','save-only spell incorrectly marked as attack spell','attack spell missing attack type','spell with upcast text but no scaling data','spell with scaling data that cannot resolve','spell level mismatch between level, spell_level, level_school, and cast options','spells that would show as cantrip because level is missing','spells that have damage preview different from roll formula']:
        vals=grouped.get(key,[])
        print(f"{key}: {len(vals)}")
        for v in vals[:20]:
            if v: print(f"  - {v}")
    return 1 if grouped.get('missing spell ID') or grouped.get('duplicate spell IDs') else 0
if __name__ == '__main__': sys.exit(main())
