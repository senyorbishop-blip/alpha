#!/usr/bin/env python3
"""Audit the 5e2024 feature compendium for structural/runtime issues."""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.character.feature_compendium import load_feature_compendium  # noqa: E402

EXPECTED = {
 'barbarian':['Rage','Unarmored Defense','Reckless Attack','Danger Sense','Primal Knowledge','Extra Attack','Fast Movement','Feral Instinct','Brutal Critical','Relentless Rage','Persistent Rage','Indomitable Might','Primal Champion'],
 'bard':['Bardic Inspiration','Spellcasting','Jack of All Trades','Expertise','Font of Inspiration','Magical Secrets'],
 'cleric':['Spellcasting','Channel Divinity','Turn Undead','Divine Intervention'],
 'druid':['Spellcasting','Wild Shape','Druidic'],
 'fighter':['Fighting Style','Second Wind','Action Surge','Extra Attack','Indomitable'],
 'monk':['Martial Arts','Unarmored Defense','Flurry of Blows','Patient Defense','Step of the Wind','Slow Fall','Stunning Strike','Extra Attack','Evasion'],
 'paladin':['Lay on Hands','Spellcasting','Fighting Style','Channel Divinity','Aura of Protection','Extra Attack'],
 'ranger':['Spellcasting','Fighting Style','Extra Attack'],
 'rogue':['Expertise','Sneak Attack','Thieves’ Cant','Cunning Action','Uncanny Dodge','Evasion','Reliable Talent','Slippery Mind','Stroke of Luck'],
 'sorcerer':['Spellcasting','Font of Magic','Metamagic','Quickened Spell','Subtle Spell','Seeking Spell','Heightened Spell','Wild Magic Surge','Tides of Chaos'],
 'warlock':['Pact Magic','Eldritch Invocations','Pact Boon','Mystic Arcanum'],
 'wizard':['Spellcasting','Spellbook','Arcane Recovery'],
 'tinker':[], 'pirate':[],
}

def norm(s): return str(s or '').lower().replace('’',"'")

def main() -> int:
    c = load_feature_compendium()
    errors=[]; warnings=[]
    keys=Counter()
    for f in c.features:
        label=f"{f.get('id')} ({f.get('name')})"
        for k in ('id','name','kind'):
            if not f.get(k): errors.append(f"missing {k}: {label}")
        keys[(norm(f.get('kind')), norm(f.get('source')), norm(f.get('name')))] += 1
        if not f.get('action_type'): errors.append(f"missing action_type: {label}")
        limited=bool(f.get('uses_formula') or f.get('uses_max') or f.get('resource_cost'))
        if limited and not f.get('recovery'): errors.append(f"limited-use missing recovery: {label}")
        if (f.get('resource_cost') or f.get('uses_formula')) and not f.get('resource_name') and 'sorcery' not in norm(f.get('name')):
            warnings.append(f"resource feature missing resource_name: {label}")
        if f.get('grants_actions') and not isinstance(f.get('grants_actions'), list): errors.append(f"grants action malformed: {label}")
        if f.get('grants_spells') and not isinstance(f.get('grants_spells'), list): errors.append(f"grants spell malformed: {label}")
        if (f.get('damage_type') or 'damage' in norm(f.get('rules_summary'))) and f.get('action_type') != 'passive' and not (f.get('damage_formula') or f.get('needs_review')):
            warnings.append(f"damage mentioned without formula: {label}")
        if f.get('save_ability') and not f.get('save_dc_formula'): warnings.append(f"save missing DC: {label}")
        if not f.get('safe_summary'): errors.append(f"missing safe summary: {label}")
        if 'd&d beyond' in norm(f.get('source')) and not (f.get('needs_review') or f.get('source_bucket') in {'private_import','stub'}):
            errors.append(f"proprietary source not private/stub: {label}")
    for key,count in keys.items():
        if count>1: warnings.append(f"duplicate feature key {key}: {count}")
    by_class=defaultdict(list)
    for f in c.features:
        if f.get('class_id'): by_class[str(f.get('class_id'))].append(norm(f.get('name')))
    for cls,names in EXPECTED.items():
        got='|'.join(by_class.get(cls, []))
        for name in names:
            if norm(name) not in got:
                warnings.append(f"class missing expected core feature: {cls} / {name}")
    for line in errors: print('ERROR:', line)
    for line in warnings: print('WARN:', line)
    print(f"Audited {len(c.features)} features; errors={len(errors)} warnings={len(warnings)} duplicates_merged={len(c.duplicates)}")
    return 1 if errors else 0
if __name__ == '__main__': raise SystemExit(main())
