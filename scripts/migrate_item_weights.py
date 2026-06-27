#!/usr/bin/env python3
"""
scripts/migrate_item_weights.py — PR 2: Unify item weight as single source of truth.

For every item lacking weight_lbs, populate it from encumbrance.py curated tables:
  1. Exact name match  (ITEM_WEIGHT_BY_NAME)
  2. Keyword substring match  (_KEYWORD_WEIGHTS)
  3. Category-aware default  (ITEM_WEIGHT_BY_CATEGORY / ITEM_WEIGHT_BY_TYPE)
  NOT a blanket 0.5 fallback.

Item JSON becomes authoritative. Reports any item assigned the final DEFAULT_ITEM_WEIGHT
fallback for human review.

Run:
  python scripts/migrate_item_weights.py          # apply weights
  python scripts/migrate_item_weights.py --check  # audit-only, no writes
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ITEMS_DIR = pathlib.Path(__file__).parent.parent / "server" / "data" / "rules" / "5e2024" / "items"
SKIP_FILES = {"item_coverage_manifest.json", "index.json"}

# Import weight tables from canonical source
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from server.encumbrance import (
    ITEM_WEIGHT_BY_NAME,
    _KEYWORD_WEIGHTS,
    ITEM_WEIGHT_BY_CATEGORY,
    ITEM_WEIGHT_BY_TYPE,
    DEFAULT_ITEM_WEIGHT,
)


def load_file(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_file(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_weight(item: dict) -> tuple[float, str]:
    """
    Resolve weight for an item using encumbrance.py curated tables.
    Returns (weight, source_label).
    source_label is one of: 'exact_name', 'keyword', 'category', 'item_type', 'default'.
    """
    name_lower = str(item.get("name") or "").strip().lower()

    # 1. Exact name match
    if name_lower in ITEM_WEIGHT_BY_NAME:
        return ITEM_WEIGHT_BY_NAME[name_lower], "exact_name"

    # 2. Keyword substring match
    for kw, w in _KEYWORD_WEIGHTS:
        if kw in name_lower:
            return w, "keyword"

    # 3. Category lookup
    cat = str(item.get("category") or "").strip().lower()
    if cat in ITEM_WEIGHT_BY_CATEGORY:
        return ITEM_WEIGHT_BY_CATEGORY[cat], "category"

    # 4. item_type lookup
    subtype = str(item.get("subtype") or "").strip().lower()
    if subtype in ITEM_WEIGHT_BY_TYPE:
        return ITEM_WEIGHT_BY_TYPE[subtype], "item_type"

    # category → ITEM_WEIGHT_BY_TYPE as well
    if cat in ITEM_WEIGHT_BY_TYPE:
        return ITEM_WEIGHT_BY_TYPE[cat], "item_type"

    return DEFAULT_ITEM_WEIGHT, "default"


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate item weights to JSON")
    parser.add_argument("--check", action="store_true", help="Audit only, no file writes")
    args = parser.parse_args()

    files: dict[str, dict] = {}
    for path in sorted(ITEMS_DIR.glob("*.json")):
        if path.name in SKIP_FILES:
            continue
        files[path.name] = load_file(path)

    # Before counts
    all_items_before = [
        (fn, it)
        for fn, data in files.items()
        for it in data.get("items", [])
    ]
    before_with = sum(1 for _, it in all_items_before if it.get("weight_lbs") is not None)
    before_without = sum(1 for _, it in all_items_before if it.get("weight_lbs") is None)

    print("=== BEFORE ===")
    print(f"  Total items:          {len(all_items_before)}")
    print(f"  With weight_lbs:      {before_with}")
    print(f"  Without weight_lbs:   {before_without}")

    if args.check:
        print("\n(--check mode: no files written)")
        sys.exit(0 if before_without == 0 else 1)

    # Migrate
    n_migrated = 0
    by_source: dict[str, int] = {"exact_name": 0, "keyword": 0, "category": 0, "item_type": 0, "default": 0}
    default_items: list[tuple[str, str, str, str]] = []  # (fname, id, name, category)

    for fname, data in files.items():
        for item in data.get("items", []):
            if item.get("weight_lbs") is not None:
                continue
            weight, source = resolve_weight(item)
            item["weight_lbs"] = weight
            n_migrated += 1
            by_source[source] = by_source.get(source, 0) + 1
            if source == "default":
                default_items.append((fname, item.get("id", ""), item.get("name", ""), item.get("category", "")))

    print(f"\n[MIGRATE] Assigned weight_lbs to {n_migrated} items")
    for src, count in by_source.items():
        if count:
            print(f"  via {src}: {count}")

    # Write files
    for fname, data in files.items():
        save_file(ITEMS_DIR / fname, data)
    print("\nFiles written.")

    # After counts
    files2: dict[str, dict] = {}
    for path in sorted(ITEMS_DIR.glob("*.json")):
        if path.name in SKIP_FILES:
            continue
        files2[path.name] = load_file(path)

    all_items_after = [
        (fn, it)
        for fn, data in files2.items()
        for it in data.get("items", [])
    ]
    after_with = sum(1 for _, it in all_items_after if it.get("weight_lbs") is not None)
    after_without = sum(1 for _, it in all_items_after if it.get("weight_lbs") is None)

    print("\n=== AFTER ===")
    print(f"  Total items:          {len(all_items_after)}")
    print(f"  With weight_lbs:      {after_with}")
    print(f"  Without weight_lbs:   {after_without}")

    # Acceptance check
    if after_without != 0:
        print(f"\nFAIL: {after_without} items still lack weight_lbs")
        sys.exit(1)
    else:
        print("\nAll items now have weight_lbs. Acceptance check PASSED.")

    if default_items:
        print(f"\n⚠ {len(default_items)} items assigned DEFAULT weight ({DEFAULT_ITEM_WEIGHT} lb) — need human review:")
        print(f"  {'File':<40} {'ID':<45} {'Name':<40} {'Category'}")
        for fname, iid, name, cat in default_items:
            print(f"  {fname:<40} {iid:<45} {name:<40} {cat}")


if __name__ == "__main__":
    main()
