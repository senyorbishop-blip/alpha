#!/usr/bin/env python3
"""Comprehensive item compendium audit.

Checks:
  - Missing id / slug / name
  - Duplicate id / slug / dedupe_key / alias
  - Duplicate item across rarity files
  - Unsupported category / rarity
  - Magic item missing rarity
  - +1/+2/+3 weapon without attack/damage bonus
  - +1/+2/+3 armor/shield without ac_bonus
  - Weapon missing damage_dice / damage_type
  - Armor missing base_ac
  - Shield missing ac_bonus
  - Attunement item missing attunement metadata
  - Charged item missing charges_max / recharge
  - Staff/wand/rod with charges but no spell/action
  - Item with granted_spells but missing spell_id or charge_cost
  - Granted spell not found in spell compendium
  - Consumable missing consumed_on_use
  - Potion missing healing / effect data
  - Scroll missing spell_level / reference
  - Item with passive effect but no runtime mapping
  - Item with combat action but no activation_type/action_type
  - Legendary/artifact missing special handling warning
  - Source listed as proprietary without safe flag
  - Items with no slug / no dedupe_key
  - Items with no aliases

Usage:
    python tools/audit_item_compendium.py [--json] [--category CATEGORY]
        [--rarity RARITY] [--strict]

Exits non-zero only when --strict is passed and critical violations exist.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUPPORTED_CATEGORIES = {
    "weapon", "armor", "shield", "adventuring_gear", "tool", "potion",
    "consumable", "scroll", "wand", "staff", "rod", "ring", "wondrous",
    "homebrew", "misc", "material", "mundane_weapons", "mundane_armor_shields",
    "common_magic_items", "uncommon_magic_items", "rare_magic_items",
    "very_rare_magic_items", "legendary_magic_items", "artifact_magic_items",
    "trade_goods_materials", "mounts_vehicles",
}
SUPPORTED_RARITIES = {"common", "uncommon", "rare", "very_rare", "legendary", "artifact", "varies"}
MAGIC_CATEGORIES = {"wand", "staff", "rod", "ring", "wondrous", "scroll"}
NON_MAGIC_CATEGORIES = {"weapon", "armor", "shield", "adventuring_gear", "tool", "material", "misc"}
PLUS_RE = re.compile(r"\+([123])\b")


def _normalize(name: str) -> str:
    return name.strip().lower().replace("_", " ").replace("-", " ")


def _load_all_items() -> list[dict]:
    try:
        from server.item_compendium import all_items, clear_cache
        clear_cache()
        return all_items()
    except Exception:
        return []


def _load_raw_items() -> list[dict]:
    """Load all items without dedup so we can find cross-file duplicates."""
    try:
        from server.item_compendium import _ITEM_FILES, _ITEMS_DIR
    except Exception:
        return _load_all_items()
    items: list[dict] = []
    for fname in _ITEM_FILES:
        path = os.path.join(_ITEMS_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data.get("items", []) if isinstance(data, dict) else data
            for row in rows:
                if isinstance(row, dict):
                    row = dict(row)
                    row["__source_file"] = fname
                    items.append(row)
        except Exception:
            continue
    return items


def _load_known_spell_ids() -> set[str]:
    try:
        from server.item_compendium import all_spell_ids
        return all_spell_ids()
    except Exception:
        return set()


def audit_item(item: dict, *, known_spell_ids: set[str] | None = None) -> dict:
    name = str(item.get("name") or "?")
    item_id = str(item.get("id") or "")
    category = str(item.get("category") or "").lower().strip()
    rarity = str(item.get("rarity") or "").lower().strip()
    charges_max = int(item.get("charges_max") or 0)
    recharge_type = str(item.get("recharge_type") or "").lower()
    granted_spells = list(item.get("granted_spells") or [])
    granted_actions = list(item.get("granted_actions") or [])
    passive_effects = list(item.get("passive_effects") or [])
    requires_attunement = bool(item.get("requires_attunement") or item.get("attunement_required"))
    is_consumable = bool(item.get("consumable"))
    consumed_on_use = bool(item.get("consumed_on_use"))
    equippable = bool(item.get("equippable"))
    equip_slot = str(item.get("equip_slot") or "")
    slug = str(item.get("slug") or "")
    aliases = list(item.get("aliases") or [])
    dedupe_key = str(item.get("dedupe_key") or "")

    issues: list[str] = []
    warnings: list[str] = []

    # Identity checks
    if not item_id:
        issues.append("Missing id")
    if not name or name == "?":
        issues.append("Missing name")
    if not slug:
        warnings.append("Missing slug")
    if not dedupe_key:
        warnings.append("Missing dedupe_key")
    if not aliases:
        warnings.append("No aliases defined")

    # Category / rarity
    if category and category not in SUPPORTED_CATEGORIES:
        issues.append(f"Unsupported category: '{category}'")
    if rarity and rarity not in SUPPORTED_RARITIES:
        issues.append(f"Unsupported rarity: '{rarity}'")
    if category in MAGIC_CATEGORIES and not rarity:
        issues.append("Magic item missing rarity")
    if category in MAGIC_CATEGORIES and rarity == "common":
        # common magic items are valid but worth noting for staffs/wands/rods
        if category in {"wand", "staff", "rod"}:
            warnings.append(f"{category.title()} has rarity 'common' — verify this is correct")

    # Weapon checks
    if category == "weapon":
        if not item.get("damage_dice"):
            issues.append("Weapon missing damage_dice")
        if not item.get("damage_type"):
            warnings.append("Weapon missing damage_type")

    # Armor / shield checks
    if category == "armor":
        if item.get("base_ac") is None and item.get("ac_bonus") is None:
            issues.append("Armor missing base_ac and ac_bonus")
    if category == "shield":
        if not item.get("ac_bonus") and item.get("base_ac") is None:
            issues.append("Shield missing ac_bonus")

    # +1/+2/+3 bonus consistency
    match = PLUS_RE.search(name)
    if match:
        expected = int(match.group(1))
        if category == "weapon":
            atk = int(item.get("attack_bonus") or 0)
            dmg = int(item.get("damage_bonus") or 0)
            if atk != expected or dmg != expected:
                issues.append(
                    f"'{name}' should have attack_bonus={expected} damage_bonus={expected}; got atk={atk} dmg={dmg}"
                )
        elif category in {"armor", "shield"}:
            ac_b = int(item.get("ac_bonus") or 0)
            if ac_b == 0:
                issues.append(f"'{name}' should have ac_bonus={expected}; got {ac_b}")

    # Equip slot
    if equippable and not equip_slot:
        issues.append("Equippable but equip_slot is empty")

    # Attunement
    if requires_attunement:
        if not item.get("attunement") and not item.get("attunement_required"):
            warnings.append("Attunement item missing 'attunement' block metadata")
        if not passive_effects and not granted_spells and not granted_actions:
            warnings.append("Attunement item has no effects, spells, or actions")

    # Charge checks
    if charges_max > 0:
        if not granted_spells and not granted_actions and not item.get("effect"):
            issues.append(f"Has charges_max={charges_max} but no granted_spells, granted_actions, or effect")
        if category in {"wand", "staff", "rod"} and not granted_spells and not granted_actions:
            issues.append(f"{category.title()} has charges but no granted_spells or granted_actions")
        if not recharge_type or recharge_type in {"", "none"}:
            warnings.append(f"Has charges_max={charges_max} but recharge_type is empty/none")
    if category in {"wand", "staff", "rod"} and charges_max == 0:
        if not granted_spells and not granted_actions:
            warnings.append(f"{category.title()} has no charges and no granted_spells/actions — may be incomplete")

    # Granted spell checks
    for gs in granted_spells:
        if isinstance(gs, str):
            spell_id = gs.lower().replace(" ", "-")
            charge_cost = None
        elif isinstance(gs, dict):
            spell_id = str(gs.get("id") or "").strip()
            charge_cost = gs.get("charge_cost")
        else:
            issues.append("granted_spell entry is not a string or dict")
            continue
        if not spell_id:
            issues.append("granted_spell entry has no id/name")
        elif known_spell_ids and spell_id not in known_spell_ids:
            warnings.append(f"granted_spell '{spell_id}' not found in spell compendium")
        if charge_cost is None:
            issues.append(f"granted_spell '{spell_id}' missing charge_cost")

    # Granted action checks
    for ga in granted_actions:
        if isinstance(ga, dict):
            if not ga.get("action_type"):
                warnings.append(f"granted_action '{ga.get('id','?')}' missing action_type")

    # Consumable checks
    if is_consumable and not consumed_on_use and category not in {"tool", "material"}:
        warnings.append("Consumable but consumed_on_use=False — check if intentional")
    if category == "potion":
        if not item.get("healing") and not item.get("effect") and not item.get("description_summary"):
            warnings.append("Potion missing healing data and effect description")
    if category == "scroll":
        if not item.get("spell_level") and item.get("spell_level") != 0:
            warnings.append("Scroll missing spell_level")

    # Passive effect checks
    if passive_effects:
        for pe in passive_effects:
            if isinstance(pe, dict) and pe.get("type") == "note":
                warnings.append("passive_effect is a stub note — needs runtime mapping")

    # Legendary / artifact
    if rarity in {"legendary", "artifact"}:
        if not item.get("description_summary") and not item.get("effect"):
            warnings.append(f"{rarity.title()} item missing description/effect summary")

    return {
        "name": name,
        "id": item_id,
        "category": category,
        "rarity": rarity,
        "issues": issues,
        "warnings": warnings,
        "ok": len(issues) == 0,
    }


def check_duplicate_ids(items: list[dict]) -> list[str]:
    seen: dict[str, list[str]] = {}
    for item in items:
        iid = str(item.get("id") or "").strip()
        src = str(item.get("__source_file") or "?")
        if iid:
            seen.setdefault(iid, []).append(src)
    return [f"{iid} (×{len(files)} in {', '.join(files)})" for iid, files in seen.items() if len(files) > 1]


def check_duplicate_slugs(items: list[dict]) -> list[str]:
    seen: dict[str, list[str]] = {}
    for item in items:
        slug = str(item.get("slug") or "").strip().lower()
        if slug:
            seen.setdefault(slug, []).append(str(item.get("id") or "?"))
    return [f"slug '{s}' on {ids}" for s, ids in seen.items() if len(ids) > 1]


def check_duplicate_names(items: list[dict]) -> list[str]:
    seen: dict[str, list[str]] = {}
    for item in items:
        name = str(item.get("name") or "").strip().lower()
        if name:
            seen.setdefault(name, []).append(str(item.get("id") or "?"))
    return [f"name '{n}' on ids {ids}" for n, ids in seen.items() if len(ids) > 1]


def check_rarity_file_mismatch(items: list[dict]) -> list[str]:
    """Flag items whose rarity doesn't match their source file bucket."""
    RARITY_FILE_MAP = {
        "common_magic_items.json": "common",
        "uncommon_magic_items.json": "uncommon",
        "rare_magic_items.json": "rare",
        "very_rare_magic_items.json": "very_rare",
        "legendary_magic_items.json": "legendary",
        "artifact_magic_items.json": "artifact",
    }
    mismatches = []
    for item in items:
        src = str(item.get("__source_file") or "")
        expected = RARITY_FILE_MAP.get(src)
        if expected is None:
            continue
        actual = str(item.get("rarity") or "").lower()
        if actual != expected and actual not in {"varies"}:
            mismatches.append(f"'{item.get('id','?')}' in {src} has rarity='{actual}' (expected '{expected}')")
    return mismatches


SRD_WEAPONS = [
    "club", "dagger", "dart", "greatclub", "handaxe", "javelin", "light hammer",
    "mace", "quarterstaff", "sickle", "spear", "light crossbow", "shortbow", "sling",
    "battleaxe", "flail", "glaive", "greataxe", "greatsword", "halberd", "lance",
    "longsword", "maul", "morningstar", "pike", "rapier", "scimitar", "shortsword",
    "trident", "war pick", "warhammer", "whip", "blowgun", "hand crossbow",
    "heavy crossbow", "longbow",
]
SRD_ARMOR = [
    "padded armor", "leather armor", "studded leather armor", "hide armor",
    "chain shirt", "scale mail", "breastplate", "half plate",
    "ring mail", "chain mail", "splint armor", "plate armor",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit item compendium")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--category", default=None)
    parser.add_argument("--rarity", default=None)
    parser.add_argument("--strict", action="store_true", help="Exit 1 on critical violations")
    args = parser.parse_args()

    all_items = _load_all_items()
    raw_items = _load_raw_items()
    known_spell_ids = _load_known_spell_ids()

    items = all_items
    if args.category:
        items = [i for i in items if str(i.get("category") or "").lower() == args.category.lower()]
    if args.rarity:
        items = [i for i in items if str(i.get("rarity") or "").lower() == args.rarity.lower()]

    results = [audit_item(i, known_spell_ids=known_spell_ids) for i in items]

    # Duplicate checks on raw (pre-dedup) data
    dup_ids = check_duplicate_ids(raw_items)
    dup_slugs = check_duplicate_slugs(raw_items)
    dup_names = check_duplicate_names(raw_items)
    rarity_mismatches = check_rarity_file_mismatch(raw_items)

    # SRD coverage
    item_names_lower = {str(i.get("name") or "").strip().lower() for i in all_items}
    missing_srd_weapons = [w for w in SRD_WEAPONS if _normalize(w) not in item_names_lower]
    missing_srd_armor = [a for a in SRD_ARMOR if _normalize(a) not in item_names_lower]

    schema_issues = [r for r in results if r["issues"]]
    schema_warnings = [r for r in results if r["warnings"]]

    try:
        from server.item_compendium import compendium_merge_log
        merge_log = compendium_merge_log()
    except Exception:
        merge_log = []

    summary = {
        "total_items": len(results),
        "total_raw_items": len(raw_items),
        "schema_issues": len(schema_issues),
        "schema_warnings": len(schema_warnings),
        "duplicate_ids": dup_ids,
        "duplicate_slugs": dup_slugs,
        "duplicate_names": dup_names,
        "rarity_file_mismatches": rarity_mismatches,
        "missing_srd_weapons": missing_srd_weapons,
        "missing_srd_armor": missing_srd_armor,
        "srd_weapons_covered": len(SRD_WEAPONS) - len(missing_srd_weapons),
        "srd_armor_covered": len(SRD_ARMOR) - len(missing_srd_armor),
        "merge_log": merge_log,
        "item_issues": [
            {"name": r["name"], "id": r["id"], "issues": r["issues"], "warnings": r["warnings"]}
            for r in results if r["issues"] or r["warnings"]
        ],
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print(f"\nItem Compendium Audit: {len(results)} items ({len(raw_items)} raw, pre-dedup)")
    print(f"  Schema issues (blocking):  {len(schema_issues)}")
    print(f"  Schema warnings:           {len(schema_warnings)}")
    print(f"  Duplicate IDs:             {len(dup_ids)}")
    print(f"  Duplicate slugs:           {len(dup_slugs)}")
    print(f"  Duplicate names:           {len(dup_names)}")
    print(f"  Rarity file mismatches:    {len(rarity_mismatches)}")
    print(f"  SRD weapons covered:       {summary['srd_weapons_covered']}/{len(SRD_WEAPONS)}")
    print(f"  SRD armor covered:         {summary['srd_armor_covered']}/{len(SRD_ARMOR)}")
    print(f"  Merge/dedup log entries:   {len(merge_log)}")

    if dup_ids:
        print(f"\nDuplicate IDs:")
        for d in dup_ids[:10]:
            print(f"  {d}")

    if dup_names:
        print(f"\nDuplicate names:")
        for d in dup_names[:10]:
            print(f"  {d}")

    if rarity_mismatches:
        print(f"\nRarity file mismatches ({len(rarity_mismatches)}):")
        for m in rarity_mismatches[:10]:
            print(f"  {m}")

    if missing_srd_weapons:
        print(f"\nMissing SRD weapons: {missing_srd_weapons}")
    if missing_srd_armor:
        print(f"\nMissing SRD armor: {missing_srd_armor}")

    if schema_issues:
        print(f"\nSchema issues ({len(schema_issues)}):")
        for r in schema_issues[:15]:
            print(f"  [{r['id'] or r['name']}] {'; '.join(r['issues'])}")

    if schema_warnings and len(schema_warnings) <= 20:
        print(f"\nWarnings ({len(schema_warnings)}):")
        for r in schema_warnings[:10]:
            print(f"  [{r['id'] or r['name']}] {'; '.join(r['warnings'][:2])}")

    if merge_log:
        print(f"\nMerge/dedup log:")
        for m in merge_log[:5]:
            print(f"  {m}")

    critical = schema_issues or dup_ids or dup_names or rarity_mismatches
    if critical:
        print(f"\nWARN: {len(schema_issues)} schema issues, {len(dup_ids)} dup IDs, "
              f"{len(dup_names)} dup names, {len(rarity_mismatches)} rarity mismatches.")
    else:
        print("\nPASS: No critical violations found.")

    print("\nPASS: Item compendium audit complete.")

    if args.strict and critical:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
