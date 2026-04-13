#!/usr/bin/env python3
"""
scripts/import_srd_items.py — Bulk-import D&D 5e SRD items from dnd5eapi.co

Codebase notes (reconnaissance):
- Item library is stored per-campaign in session.item_library_entries (JSON field in SQLite campaigns table)
- A shared srd_items SQLite table (same DB as campaigns) stores globally available imported SRD items
- Item schema: id, name, category, rarity, weight, default_price, default_qty, description, tags
- Rarity values (title-case): Common, Uncommon, Rare, Very Rare, Legendary
- Loot generation (server/handlers/inventory.py) reads from srd_items by rarity for level-aware drops
- DB path is resolved via server.paths.DB_PATH (env: DND_DB_PATH, default: ~/.casual-dnd/campaigns.db)

Usage:
    python scripts/import_srd_items.py
    python scripts/import_srd_items.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Add project root to sys.path so we can import server modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.rules_db import insert_srd_items_batch, get_srd_item_count, init_srd_items_table
from server.db import get_conn

BASE_URL = "https://www.dnd5eapi.co"

# ── Category mapping: API equipment_category.name → our category field ─────────
_CATEGORY_MAP = {
    "adventuring gear":    "Gear",
    "ammunition":          "Gear",
    "arcane foci":         "Gear",
    "armor":               "Armor",
    "artisan's tools":     "Tool",
    "druidic foci":        "Gear",
    "equipment packs":     "Gear",
    "gaming sets":         "Tool",
    "heavy armor":         "Armor",
    "holy symbols":        "Gear",
    "kits":                "Gear",
    "land vehicles":       "Mount",
    "light armor":         "Armor",
    "medium armor":        "Armor",
    "melee weapons":       "Weapon",
    "mounts and vehicles": "Mount",
    "mounts and other animals": "Mount",
    "musical instruments": "Tool",
    "other tools":         "Tool",
    "ranged weapons":      "Weapon",
    "rod":                 "Wondrous Item",
    "ring":                "Ring",
    "scroll":              "Scroll",
    "shield":              "Armor",
    "shields":             "Armor",
    "simple melee weapons":"Weapon",
    "simple ranged weapons":"Weapon",
    "staff":               "Wondrous Item",
    "standard gear":       "Gear",
    "tack, harness, and drawn vehicles": "Mount",
    "tools":               "Tool",
    "treasure":            "Gear",
    "wand":                "Wondrous Item",
    "wondrous items":      "Wondrous Item",
    "wondrous item":       "Wondrous Item",
    "weapon":              "Weapon",
    "weapons":             "Weapon",
    "waterborne vehicles": "Mount",
}

# ── Rarity mapping ──────────────────────────────────────────────────────────────
_RARITY_MAP = {
    "common":    "Common",
    "uncommon":  "Uncommon",
    "rare":      "Rare",
    "very rare": "Very Rare",
    "legendary": "Legendary",
    "artifact":  "Legendary",
    "varies":    "Common",
    "unknown":   "Common",
}


def _map_category(equipment_category: str, item_type: str = "") -> str:
    """Map API equipment_category name to our internal category values."""
    key = (equipment_category or "").strip().lower()
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    # Try partial match
    for api_key, cat in _CATEGORY_MAP.items():
        if api_key in key or key in api_key:
            return cat
    # Magic item type fallback
    item_lower = (item_type or "").strip().lower()
    if item_lower in ("ring",):
        return "Ring"
    if item_lower in ("scroll",):
        return "Scroll"
    if item_lower in ("potion",):
        return "Potion"
    if item_lower in ("wand", "rod", "staff"):
        return "Wondrous Item"
    if item_lower in ("armor", "shield"):
        return "Armor"
    if item_lower in ("weapon",):
        return "Weapon"
    return "Gear"


def _map_rarity(rarity_name: str) -> str:
    """Normalize rarity string to title-case standard value."""
    key = (rarity_name or "Common").strip().lower()
    return _RARITY_MAP.get(key, "Common")


def _cost_to_gp_string(cost: dict | None) -> str:
    """Convert API cost object {quantity, unit} to a display string like '50 gp'."""
    if not cost:
        return ""
    qty = cost.get("quantity", 0) or 0
    unit = (cost.get("unit") or "gp").lower()
    if qty <= 0:
        return ""
    if unit == "gp":
        return f"{qty} gp"
    if unit == "sp":
        # Round to 2 decimals for display, but store as string
        gp_val = qty / 10
        if gp_val == int(gp_val):
            return f"{int(gp_val)} gp" if gp_val >= 1 else f"{qty} sp"
        return f"{qty} sp"
    if unit == "cp":
        gp_val = qty / 100
        if gp_val >= 1 and gp_val == int(gp_val):
            return f"{int(gp_val)} gp"
        return f"{qty} cp"
    if unit == "pp":
        return f"{qty} pp"
    return f"{qty} {unit}"


def _fetch_json(path: str, retries: int = 3) -> dict | list | None:
    """Fetch JSON from dnd5eapi.co with retry logic."""
    url = BASE_URL + path if path.startswith("/") else path
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
    return None


def _build_description(detail: dict) -> str:
    """Build a description string from API detail fields."""
    parts = []
    desc_list = detail.get("desc") or []
    if isinstance(desc_list, list):
        parts.extend(str(d) for d in desc_list if d)
    elif isinstance(desc_list, str) and desc_list:
        parts.append(desc_list)
    # Add weapon properties
    props = detail.get("properties") or []
    if props:
        prop_names = [p.get("name", "") for p in props if p.get("name")]
        if prop_names:
            parts.append("Properties: " + ", ".join(prop_names))
    # Add damage info for weapons
    damage = detail.get("damage") or {}
    if damage.get("damage_dice"):
        dmg_type = (damage.get("damage_type") or {}).get("name", "")
        parts.append(f"Damage: {damage['damage_dice']}" + (f" {dmg_type}" if dmg_type else ""))
    # Range for ranged weapons
    rng = detail.get("range") or {}
    if rng.get("normal"):
        far = rng.get("long")
        parts.append(f"Range: {rng['normal']}" + (f"/{far}" if far else "") + " ft")
    return "\n".join(parts)


def _build_tags(detail: dict, category: str) -> str:
    """Build comma-separated tags string."""
    tags = set()
    cat_name = (detail.get("equipment_category") or {}).get("name", "")
    if cat_name:
        tags.add(cat_name)
    weapon_cat = (detail.get("weapon_category") or "").strip()
    if weapon_cat:
        tags.add(weapon_cat)
    weapon_range = (detail.get("weapon_range") or "").strip()
    if weapon_range:
        tags.add(weapon_range)
    armor_cat = (detail.get("armor_category") or "").strip()
    if armor_cat:
        tags.add(armor_cat)
    gear_cat = (detail.get("gear_category") or {}).get("name", "")
    if gear_cat:
        tags.add(gear_cat)
    return ", ".join(sorted(tags))


def fetch_equipment_items() -> list[dict]:
    """Fetch all mundane equipment items from the API."""
    print("Fetching equipment list…")
    data = _fetch_json("/api/equipment")
    if not data or not isinstance(data.get("results"), list):
        print("  Warning: could not fetch /api/equipment")
        return []

    items = []
    results = data["results"]
    total = len(results)
    print(f"  Found {total} equipment entries. Fetching details…")

    for i, entry in enumerate(results, 1):
        index = entry.get("index", "")
        if not index:
            continue
        detail = _fetch_json(f"/api/equipment/{index}")
        if not detail:
            continue

        # Derive fields
        cat_name = (detail.get("equipment_category") or {}).get("name", "")
        category = _map_category(cat_name)
        rarity_obj = detail.get("rarity") or {}
        rarity_name = rarity_obj.get("name", "") if isinstance(rarity_obj, dict) else str(rarity_obj)
        rarity = _map_rarity(rarity_name) if rarity_name else "Common"
        weight = float(detail.get("weight") or 0)
        cost_str = _cost_to_gp_string(detail.get("cost"))
        description = _build_description(detail)
        tags = _build_tags(detail, category)

        items.append({
            "id": f"srd_eq_{index}",
            "name": str(detail.get("name") or entry.get("name") or "")[:80],
            "category": category,
            "rarity": rarity,
            "weight": weight,
            "default_price": cost_str,
            "default_qty": 1,
            "description": description,
            "tags": tags,
        })

        if i % 50 == 0 or i == total:
            print(f"  Processed {i}/{total} equipment items…")
        time.sleep(0.05)  # be gentle on the API

    return items


def fetch_magic_items() -> list[dict]:
    """Fetch all magic items from the API."""
    print("Fetching magic items list…")
    data = _fetch_json("/api/magic-items")
    if not data or not isinstance(data.get("results"), list):
        print("  Warning: could not fetch /api/magic-items")
        return []

    items = []
    results = data["results"]
    total = len(results)
    print(f"  Found {total} magic item entries. Fetching details…")

    for i, entry in enumerate(results, 1):
        index = entry.get("index", "")
        if not index:
            continue
        detail = _fetch_json(f"/api/magic-items/{index}")
        if not detail:
            continue

        rarity_obj = detail.get("rarity") or {}
        rarity_name = rarity_obj.get("name", "") if isinstance(rarity_obj, dict) else str(rarity_obj)
        rarity = _map_rarity(rarity_name)

        cat_obj = detail.get("equipment_category") or {}
        cat_name = cat_obj.get("name", "") if isinstance(cat_obj, dict) else str(cat_obj)
        item_type = (detail.get("item_category") or "").strip()
        category = _map_category(cat_name, item_type) if cat_name else _map_category("", item_type)
        if category == "Gear" and item_type:
            # Improve category for magic items using item_type hint
            category = _map_category(item_type)

        desc_list = detail.get("desc") or []
        if isinstance(desc_list, list):
            description = "\n".join(str(d) for d in desc_list if d)
        else:
            description = str(desc_list or "")

        items.append({
            "id": f"srd_mi_{index}",
            "name": str(detail.get("name") or entry.get("name") or "")[:80],
            "category": category,
            "rarity": rarity,
            "weight": 0.0,
            "default_price": "",
            "default_qty": 1,
            "description": description[:2000],
            "tags": cat_name or item_type or "",
        })

        if i % 50 == 0 or i == total:
            print(f"  Processed {i}/{total} magic items…")
        time.sleep(0.05)

    return items


def fetch_weapon_properties() -> dict[str, str]:
    """Fetch weapon properties descriptions for use in weapon descriptions."""
    data = _fetch_json("/api/weapon-properties")
    if not data or not isinstance(data.get("results"), list):
        return {}
    props = {}
    for entry in data["results"]:
        index = entry.get("index", "")
        if not index:
            continue
        detail = _fetch_json(f"/api/weapon-properties/{index}")
        if detail:
            desc = detail.get("desc") or []
            if isinstance(desc, list):
                props[entry.get("name", index)] = " ".join(str(d) for d in desc)
    return props


def main() -> None:
    """Main entry point: fetch and insert all SRD items."""
    parser = argparse.ArgumentParser(description="Import D&D 5e SRD items into the item library database.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write to database.")
    parser.add_argument("--equipment-only", action="store_true", help="Import only mundane equipment, skip magic items.")
    parser.add_argument("--magic-only", action="store_true", help="Import only magic items, skip mundane equipment.")
    parser.add_argument("--offline", action="store_true", help="Use built-in seed data instead of fetching from API.")
    args = parser.parse_args()

    if args.offline:
        print("Running in offline mode: seeding from built-in dataset…")
        from server.rules_db import init_loot_db, get_srd_item_count
        init_loot_db()
        count = get_srd_item_count()
        print(f"Total srd_items in database: {count}")
        print("Done. (Use without --offline to fetch from dnd5eapi.co when network is available.)")
        return

    # Ensure srd_items table exists
    init_srd_items_table()
    before_count = get_srd_item_count()
    print(f"Current srd_items count before import: {before_count}")
    print()

    all_items: list[dict] = []

    if not args.magic_only:
        equipment = fetch_equipment_items()
        all_items.extend(equipment)
        print(f"  Collected {len(equipment)} equipment items.\n")

    if not args.equipment_only:
        magic = fetch_magic_items()
        all_items.extend(magic)
        print(f"  Collected {len(magic)} magic items.\n")

    if not all_items:
        print("No items collected. Check network connectivity or API availability.")
        sys.exit(1)

    print(f"Total items collected: {len(all_items)}")

    if args.dry_run:
        print("\n[DRY RUN] Would insert items:")
        from collections import Counter
        rarity_counts = Counter(item["rarity"] for item in all_items)
        cat_counts = Counter(item["category"] for item in all_items)
        print(f"  By rarity: {dict(sorted(rarity_counts.items()))}")
        print(f"  By category: {dict(sorted(cat_counts.items()))}")
        print("\n[DRY RUN] No database changes made.")
        return

    print("\nInserting into database…")
    inserted, skipped = insert_srd_items_batch(all_items)

    after_count = get_srd_item_count()
    print(f"\nImport complete!")
    print(f"  Inserted: {inserted} new items")
    print(f"  Skipped:  {skipped} duplicates")
    print(f"  Total srd_items in database: {after_count}")


if __name__ == "__main__":
    main()
