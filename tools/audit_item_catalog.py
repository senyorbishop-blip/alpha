#!/usr/bin/env python3
"""Audit the item catalog for schema coverage, spell grant integrity, and SRD completeness.

Usage:
    python tools/audit_item_catalog.py [--json] [--category CATEGORY] [--strict]

Exits with non-zero if critical violations are found and --strict is set.
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

PLUS_PATTERN_RE = __import__("re").compile(r"\+[123]\b")


def _normalize(name: str) -> str:
    return name.strip().lower().replace("_", " ").replace("-", " ")


def _load_compendium_items() -> list[dict]:
    try:
        from server.item_compendium import all_items
        return all_items()
    except Exception:
        return []


def _load_session_items(session_data: dict | None = None) -> list[dict]:
    items: list[dict] = []
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


def _load_known_spell_ids() -> set[str]:
    try:
        from server.item_compendium import all_spell_ids
        return all_spell_ids()
    except Exception:
        return set()


def audit_item(item: dict) -> dict:
    name = str(item.get("name") or "?")
    category = str(item.get("category") or "").lower()
    missing_required = [f for f in REQUIRED_FIELDS if not item.get(f)]
    is_equippable = bool(item.get("equippable"))
    has_slot = bool(item.get("equip_slot"))
    charges_max = int(item.get("charges_max") or 0)
    granted_spells = list(item.get("granted_spells") or [])
    granted_actions = list(item.get("granted_actions") or [])
    recharge_type = str(item.get("recharge_type") or "").lower()

    issues: list[str] = []

    if missing_required:
        issues.append(f"Missing required fields: {', '.join(missing_required)}")
    if is_equippable and not has_slot:
        issues.append("Equippable but no equip_slot set")
    if charges_max > 0 and not granted_spells and not granted_actions and not item.get("effect"):
        issues.append("Has charges but no granted_spells, granted_actions, or effect text")
    if category in {"wand", "staff", "rod"} and charges_max == 0 and recharge_type in {"", "none"} and not granted_spells:
        issues.append(f"{category.title()} has no charges or recharge data and no granted_spells")
    if bool(item.get("requires_attunement") or item.get("attunement_required")) and not item.get("effect") and not granted_spells and not granted_actions:
        issues.append("Attunement item has no effect, granted_spells, or granted_actions")
    if PLUS_PATTERN_RE.search(name) and category == "weapon":
        bonus_str = PLUS_PATTERN_RE.search(name).group(0)
        expected = int(bonus_str[1:])
        atk = int(item.get("attack_bonus") or 0)
        dmg = int(item.get("damage_bonus") or 0)
        if atk != expected or dmg != expected:
            issues.append(f"Named '{name}' but attack_bonus={atk}, damage_bonus={dmg} (expected {expected} each)")
    if PLUS_PATTERN_RE.search(name) and category in {"armor", "shield"}:
        bonus_str = PLUS_PATTERN_RE.search(name).group(0)
        expected = int(bonus_str[1:])
        ac_b = int(item.get("ac_bonus") or 0)
        if ac_b == 0:
            issues.append(f"Named '{name}' but ac_bonus=0 (expected {expected})")

    return {
        "name": name,
        "id": str(item.get("id") or ""),
        "category": category,
        "issues": issues,
        "schema_ok": not missing_required,
        "equip_ok": (not is_equippable) or has_slot,
        "is_equippable": is_equippable,
        "charges_max": charges_max,
        "granted_spells": granted_spells,
        "granted_actions": granted_actions,
    }


def audit_granted_spells(items: list[dict], known_spell_ids: set[str]) -> list[dict]:
    violations: list[dict] = []
    for item in items:
        name = str(item.get("name") or "?")
        granted_spells = list(item.get("granted_spells") or [])
        for gs in granted_spells:
            if isinstance(gs, str):
                spell_id = gs.lower().replace(" ", "-")
                charge_cost = None
            elif isinstance(gs, dict):
                spell_id = str(gs.get("id") or "").strip()
                charge_cost = gs.get("charge_cost")
            else:
                continue
            if not spell_id:
                violations.append({"item": name, "issue": "granted_spell entry has no id"})
                continue
            if known_spell_ids and spell_id not in known_spell_ids:
                violations.append({"item": name, "issue": f"granted_spell id '{spell_id}' not found in spell compendium"})
            if charge_cost is None:
                violations.append({"item": name, "issue": f"granted_spell '{spell_id}' has no charge_cost"})
    return violations


def check_duplicate_ids(items: list[dict]) -> list[str]:
    seen: dict[str, int] = {}
    dups: list[str] = []
    for item in items:
        item_id = str(item.get("id") or "").strip()
        if item_id:
            seen[item_id] = seen.get(item_id, 0) + 1
    for item_id, count in seen.items():
        if count > 1:
            dups.append(f"{item_id} (×{count})")
    return dups


def main():
    parser = argparse.ArgumentParser(description="Audit item catalog for coverage and spell integrity")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--category", default=None, help="Filter by category")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any issue")
    args = parser.parse_args()

    compendium_items = _load_compendium_items()
    session_items = _load_session_items()
    all_items = compendium_items or session_items
    known_spell_ids = _load_known_spell_ids()

    if args.category:
        all_items = [i for i in all_items if str(i.get("category") or "").lower() == args.category.lower()]

    results = [audit_item(i) for i in all_items]
    item_names = {_normalize(r["name"]) for r in results}

    missing_srd_weapons = [w for w in SRD_WEAPONS if _normalize(w) not in item_names]
    missing_srd_armor = [a for a in SRD_ARMOR if _normalize(a) not in item_names]
    missing_srd_potions = [p for p in SRD_POTIONS if _normalize(p) not in item_names]

    schema_issues = [r for r in results if r["issues"]]
    equipped_without_slot = [r for r in results if r["is_equippable"] and not r["equip_ok"]]

    spell_violations = audit_granted_spells(all_items, known_spell_ids)
    duplicate_ids = check_duplicate_ids(all_items)

    has_charged_no_action = [
        r for r in results
        if r["charges_max"] > 0 and not r["granted_spells"] and not r["granted_actions"]
    ]

    no_charge_cost = [
        v for v in spell_violations if "charge_cost" in v.get("issue", "")
    ]
    spell_id_missing = [
        v for v in spell_violations if "not found in spell compendium" in v.get("issue", "")
    ]

    summary = {
        "total_items": len(results),
        "compendium_items": len(compendium_items),
        "session_items": len(session_items),
        "schema_issues": len(schema_issues),
        "equip_slot_missing": len(equipped_without_slot),
        "charged_no_action_or_spell": len(has_charged_no_action),
        "spell_grant_violations": len(spell_violations),
        "spell_id_not_in_compendium": len(spell_id_missing),
        "missing_charge_cost": len(no_charge_cost),
        "duplicate_ids": duplicate_ids,
        "missing_srd_weapons": missing_srd_weapons,
        "missing_srd_armor": missing_srd_armor,
        "missing_srd_potions": missing_srd_potions,
        "srd_weapons_covered": len(SRD_WEAPONS) - len(missing_srd_weapons),
        "srd_armor_covered": len(SRD_ARMOR) - len(missing_srd_armor),
        "item_issues": [{"name": r["name"], "id": r["id"], "issues": r["issues"]} for r in schema_issues],
        "spell_violations": spell_violations,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Item Catalog Audit: {len(results)} items ({len(compendium_items)} compendium, {len(session_items)} session)")
        print(f"  Schema issues:            {len(schema_issues)}")
        print(f"  Charged w/o action/spell: {len(has_charged_no_action)}")
        print(f"  Missing equip slot:       {len(equipped_without_slot)}")
        print(f"  Duplicate IDs:            {len(duplicate_ids)}")
        print(f"  SRD weapons:              {summary['srd_weapons_covered']}/{len(SRD_WEAPONS)}")
        print(f"  SRD armor:                {summary['srd_armor_covered']}/{len(SRD_ARMOR)}")
        print(f"  Spell grant violations:   {len(spell_violations)}")
        print(f"    - Spell ID not found:   {len(spell_id_missing)}")
        print(f"    - Missing charge_cost:  {len(no_charge_cost)}")
        if duplicate_ids:
            print(f"\nDuplicate IDs: {', '.join(duplicate_ids)}")
        if missing_srd_weapons:
            print(f"  Missing SRD weapons: {', '.join(missing_srd_weapons[:10])}")
        if missing_srd_armor:
            print(f"  Missing SRD armor:   {', '.join(missing_srd_armor[:6])}")
        if missing_srd_potions:
            print(f"  Missing SRD potions: {', '.join(missing_srd_potions)}")
        if schema_issues:
            print(f"\nSchema issues ({len(schema_issues)}):")
            for r in schema_issues[:10]:
                print(f"  [{r['id'] or r['name']}] {'; '.join(r['issues'])}")
        if spell_violations:
            print(f"\nSpell grant violations ({len(spell_violations)}):")
            for v in spell_violations[:10]:
                print(f"  [{v['item']}] {v['issue']}")

    any_critical = schema_issues or spell_violations or duplicate_ids
    if any_critical:
        print(f"\nWARN: {len(schema_issues)} schema issues, {len(spell_violations)} spell grant violations, {len(duplicate_ids)} duplicate IDs.")
    print("\nPASS: Item catalog audit complete.")

    if args.strict and any_critical:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
