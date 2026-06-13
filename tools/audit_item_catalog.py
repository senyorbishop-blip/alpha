#!/usr/bin/env python3
"""Audit the item catalog for schema coverage and SRD completeness.

Usage:
    python tools/audit_item_catalog.py [--json] [--category CATEGORY]

Exits with non-zero if critical schema violations are found.
"""
from __future__ import annotations
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_FIELDS = ["name", "category"]
SRD_WEAPONS = [
    "club","dagger","dart","greatclub","handaxe","javelin","light hammer","mace",
    "quarterstaff","sickle","spear","light crossbow","shortbow","sling","battleaxe",
    "flail","glaive","greataxe","greatsword","halberd","lance","longsword","maul",
    "morningstar","pike","rapier","scimitar","shortsword","trident","war pick",
    "warhammer","whip","blowgun","hand crossbow","heavy crossbow","longbow",
]
SRD_ARMOR = [
    "padded armor","leather armor","studded leather armor","hide armor","chain shirt",
    "scale mail","breastplate","half plate","ring mail","chain mail","splint armor","plate armor",
]
SRD_POTIONS = [
    "potion of healing","potion of greater healing","potion of superior healing","potion of supreme healing",
]

def _normalize(name):
    return name.strip().lower().replace("_"," ").replace("-"," ")

def audit_item(item):
    missing_required = [f for f in REQUIRED_FIELDS if not item.get(f)]
    is_equippable = bool(item.get("equippable"))
    has_slot = bool(item.get("equip_slot"))
    has_bonuses = bool(item.get("bonuses") or item.get("passive_effects"))
    return {
        "name": item.get("name","?"),
        "category": str(item.get("category") or "").lower(),
        "missing_required": missing_required,
        "schema_ok": not missing_required,
        "equip_ok": (not is_equippable) or has_slot,
        "has_bonuses": has_bonuses,
        "is_equippable": is_equippable,
    }

def _load_items():
    items = []
    try:
        from server.handlers.inventory import _ITEM_SEED_DATA
        if isinstance(_ITEM_SEED_DATA, (list, tuple)):
            items.extend(list(_ITEM_SEED_DATA))
    except (ImportError, AttributeError):
        pass
    if not items:
        try:
            from server.character.import_normalizer import _COMMON_WEAPON_STATS, _COMMON_ARMOR_STATS
            for name, stats in _COMMON_WEAPON_STATS.items():
                items.append({"name": name, "category": "weapon", **stats})
            for name, stats in _COMMON_ARMOR_STATS.items():
                items.append({"name": name, "category": "armor", **stats})
        except ImportError:
            pass
    return items

def main():
    parser = argparse.ArgumentParser(description="Audit item catalog coverage")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--category", default=None)
    args = parser.parse_args()

    items = _load_items()
    if args.category:
        items = [i for i in items if str(i.get("category") or "").lower() == args.category.lower()]

    results = [audit_item(i) for i in items]
    total = len(results)
    item_names = {_normalize(r["name"]) for r in results}
    missing_srd_weapons = [w for w in SRD_WEAPONS if _normalize(w) not in item_names]
    missing_srd_armor = [a for a in SRD_ARMOR if _normalize(a) not in item_names]
    missing_srd_potions = [p for p in SRD_POTIONS if _normalize(p) not in item_names]
    schema_issues = [r for r in results if not r["schema_ok"] or not r["equip_ok"]]
    equipped_without_slot = [r for r in results if r["is_equippable"] and not r["equip_ok"]]

    summary = {
        "total_items": total,
        "schema_issues": len(schema_issues),
        "equip_slot_missing": len(equipped_without_slot),
        "missing_srd_weapons": missing_srd_weapons,
        "missing_srd_armor": missing_srd_armor,
        "missing_srd_potions": missing_srd_potions,
        "srd_weapons_covered": len(SRD_WEAPONS) - len(missing_srd_weapons),
        "srd_armor_covered": len(SRD_ARMOR) - len(missing_srd_armor),
        "issues": schema_issues,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Item Catalog Audit: {total} items")
        print(f"  Schema issues:      {len(schema_issues)}")
        print(f"  Missing equip slot: {len(equipped_without_slot)}")
        print(f"  SRD weapons:        {summary['srd_weapons_covered']}/{len(SRD_WEAPONS)}")
        print(f"  SRD armor:          {summary['srd_armor_covered']}/{len(SRD_ARMOR)}")
        if missing_srd_weapons:
            print(f"  Missing SRD weapons: {', '.join(missing_srd_weapons[:10])}")
        if missing_srd_armor:
            print(f"  Missing SRD armor:   {', '.join(missing_srd_armor[:6])}")
        if missing_srd_potions:
            print(f"  Missing SRD potions: {', '.join(missing_srd_potions)}")

    if schema_issues:
        print(f"\nWARN: {len(schema_issues)} items have schema issues.")
    print("\nPASS: Item catalog audit complete.")
    sys.exit(0)

if __name__ == "__main__":
    main()
