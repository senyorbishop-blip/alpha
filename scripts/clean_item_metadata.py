#!/usr/bin/env python3
"""
scripts/clean_item_metadata.py — PR 1 metadata cleanup (idempotent).

Fixes:
  1. Attunement sync: require_attunement <- attunement.required (nested obj canonical)
  2. Vorpal Sword: move from mundane_weapons.json → legendary_magic_items.json
  3. Contradictory recharge: clear recharge_formula/type when charges_max == 0
  4. Filler granted_actions: strip "Activate this item." on uncharged items
  5. Scaffolding passive_effects: strip "Starter magic item metadata."
  6. Homebrew TODO: add draft:true to items with TODO placeholder summaries

Run:
  python scripts/clean_item_metadata.py          # apply fixes
  python scripts/clean_item_metadata.py --check  # audit-only, no writes
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

ITEMS_DIR = pathlib.Path(__file__).parent.parent / "server" / "data" / "rules" / "5e2024" / "items"
SKIP_FILES = {"item_coverage_manifest.json", "index.json"}

MUNDANE_WEAPONS_FILE = ITEMS_DIR / "mundane_weapons.json"
LEGENDARY_FILE = ITEMS_DIR / "legendary_magic_items.json"
HOMEBREW_FILE = ITEMS_DIR / "homebrew_items.json"

FILLER_ACTION_SUMMARY = "Activate this item."
SCAFFOLD_NOTE_SUMMARY = "Starter magic item metadata."
TODO_MARKERS = ("TODO homebrew effect.", "TODO homebrew action.")


def load_file(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_file(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def iter_all_items(files: dict[str, dict]) -> list[tuple[str, dict]]:
    out = []
    for fname, data in files.items():
        for item in data.get("items", []):
            out.append((fname, item))
    return out


def count_issues(files: dict[str, dict]) -> dict[str, int]:
    all_items = iter_all_items(files)
    counts: dict[str, int] = {}

    # 1. Attunement disagree
    counts["attunement_disagree"] = sum(
        1 for _, it in all_items
        if isinstance(it.get("attunement"), dict)
        and it.get("requires_attunement") != it["attunement"].get("required")
    )

    # 2. Contradictory recharge
    counts["contradictory_recharge"] = sum(
        1 for _, it in all_items
        if it.get("charges_max", 0) == 0
        and it.get("recharge_formula", "") not in ("", "none")
    )

    # 3a. Filler actions on uncharged items
    counts["filler_actions_uncharged"] = sum(
        1 for _, it in all_items
        if it.get("charges_max", 0) == 0
        and any(
            isinstance(a, dict) and a.get("summary") == FILLER_ACTION_SUMMARY
            for a in it.get("granted_actions", [])
        )
    )
    # 3b. Filler actions on charged items (flagged, not removed)
    counts["filler_actions_charged_review"] = sum(
        1 for _, it in all_items
        if it.get("charges_max", 0) > 0
        and any(
            isinstance(a, dict) and a.get("summary") == FILLER_ACTION_SUMMARY
            for a in it.get("granted_actions", [])
        )
    )

    # 4. Scaffolding notes
    counts["scaffold_notes"] = sum(
        1 for _, it in all_items
        if any(
            isinstance(e, dict) and e.get("summary") == SCAFFOLD_NOTE_SUMMARY
            for e in it.get("passive_effects", [])
        )
    )

    # 5. Homebrew TODO
    homebrew_items = [it for fn, it in all_items if fn == "homebrew_items.json"]
    counts["homebrew_todo_items"] = sum(
        1 for it in homebrew_items
        if any(
            isinstance(x, dict) and any(m in str(x.get("summary", "")) for m in TODO_MARKERS)
            for x in it.get("granted_actions", []) + it.get("passive_effects", [])
        )
    )
    counts["homebrew_todo_summaries"] = sum(
        sum(
            1 for x in it.get("granted_actions", []) + it.get("passive_effects", [])
            if isinstance(x, dict) and any(m in str(x.get("summary", "")) for m in TODO_MARKERS)
        )
        for it in homebrew_items
    )

    # 6. Vorpal sword in wrong file
    counts["vorpal_in_mundane"] = sum(
        1 for fn, it in all_items
        if fn == "mundane_weapons.json" and it.get("id") == "vorpal-sword"
    )

    return counts


def fix_attunement(item: dict) -> bool:
    """Sync requires_attunement <- attunement.required. Returns True if changed."""
    attn = item.get("attunement")
    if not isinstance(attn, dict):
        return False
    canonical = attn.get("required", False)
    if item.get("requires_attunement") != canonical:
        item["requires_attunement"] = canonical
        return True
    return False


def fix_recharge(item: dict) -> bool:
    """Clear recharge_formula/type when charges_max==0. Returns True if changed."""
    if item.get("charges_max", 0) != 0:
        return False
    changed = False
    if item.get("recharge_formula", "") not in ("", "none"):
        item["recharge_formula"] = ""
        changed = True
    if item.get("recharge_type", "none") not in ("", "none"):
        item["recharge_type"] = "none"
        changed = True
    return changed


def strip_filler_actions(item: dict) -> bool:
    """Remove 'Activate this item.' granted_actions only on uncharged items."""
    if item.get("charges_max", 0) != 0:
        return False
    original = item.get("granted_actions", [])
    filtered = [
        a for a in original
        if not (isinstance(a, dict) and a.get("summary") == FILLER_ACTION_SUMMARY)
    ]
    if len(filtered) != len(original):
        item["granted_actions"] = filtered
        return True
    return False


def strip_scaffold_notes(item: dict) -> bool:
    """Remove 'Starter magic item metadata.' passive_effects entries."""
    original = item.get("passive_effects", [])
    filtered = [
        e for e in original
        if not (isinstance(e, dict) and e.get("summary") == SCAFFOLD_NOTE_SUMMARY)
    ]
    if len(filtered) != len(original):
        item["passive_effects"] = filtered
        return True
    return False


def flag_homebrew_draft(item: dict) -> bool:
    """Add draft:true if item has any TODO placeholder summaries."""
    has_todo = any(
        isinstance(x, dict) and any(m in str(x.get("summary", "")) for m in TODO_MARKERS)
        for x in item.get("granted_actions", []) + item.get("passive_effects", [])
    )
    if has_todo and not item.get("draft"):
        item["draft"] = True
        return True
    return False


def move_vorpal_sword(
    mundane_data: dict, legendary_data: dict
) -> tuple[bool, dict | None]:
    """
    Remove vorpal-sword from mundane_data and add (fixed) to legendary_data.
    Returns (changed: bool, vorpal_item | None).
    """
    mundane_items = mundane_data.get("items", [])
    vorpal = next((it for it in mundane_items if it.get("id") == "vorpal-sword"), None)
    if vorpal is None:
        return False, None

    # Already in legendary?
    legendary_items = legendary_data.get("items", [])
    already = any(it.get("id") == "vorpal-sword" for it in legendary_items)

    # Remove from mundane (idempotent)
    new_mundane = [it for it in mundane_items if it.get("id") != "vorpal-sword"]
    if len(new_mundane) != len(mundane_items):
        mundane_data["items"] = new_mundane

    if already:
        return True, None  # already moved in a previous run

    # Fix and add to legendary
    fixed = dict(vorpal)
    fixed["rarity"] = "legendary"
    fixed["requires_attunement"] = True
    fixed["attunement"] = {"required": True, "supported": True}
    # category stays "weapon" per spec
    legendary_data.setdefault("items", []).append(fixed)
    return True, fixed


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean 5e2024 item metadata")
    parser.add_argument("--check", action="store_true", help="Audit only, no file writes")
    args = parser.parse_args()

    # Load all item files
    files: dict[str, dict] = {}
    for path in sorted(ITEMS_DIR.glob("*.json")):
        if path.name in SKIP_FILES:
            continue
        files[path.name] = load_file(path)

    before = count_issues(files)

    print("=== BEFORE ===")
    print(f"  Total items:                   {sum(len(d.get('items',[])) for d in files.values())}")
    print(f"  Attunement disagreements:      {before['attunement_disagree']}")
    print(f"  Contradictory recharge:        {before['contradictory_recharge']}")
    print(f"  Filler actions (uncharged):    {before['filler_actions_uncharged']}")
    print(f"  Filler actions (charged, ⚠):  {before['filler_actions_charged_review']}")
    print(f"  Scaffold passive notes:        {before['scaffold_notes']}")
    print(f"  Homebrew TODO items:           {before['homebrew_todo_items']}")
    print(f"  Homebrew TODO summaries:       {before['homebrew_todo_summaries']}")
    print(f"  Vorpal sword in mundane file:  {before['vorpal_in_mundane']}")

    if args.check:
        print("\n(--check mode: no files written)")
        sys.exit(0 if all(v == 0 for k, v in before.items() if k != "filler_actions_charged_review") else 1)

    # ── Fix 1: Move + fix vorpal sword ───────────────────────────────────────
    mundane_data = files["mundane_weapons.json"]
    legendary_data = files["legendary_magic_items.json"]
    vorpal_moved, vorpal_item = move_vorpal_sword(mundane_data, legendary_data)
    if vorpal_moved:
        print("\n[FIX] Vorpal Sword moved to legendary_magic_items.json (rarity=legendary, attunement=true)")

    # ── Fix 2–5: Per-item fixes ───────────────────────────────────────────────
    n_attn = n_recharge = n_filler = n_scaffold = n_draft = 0
    for fname, data in files.items():
        for item in data.get("items", []):
            if fix_attunement(item):
                n_attn += 1
            if fix_recharge(item):
                n_recharge += 1
            if strip_filler_actions(item):
                n_filler += 1
            if strip_scaffold_notes(item):
                n_scaffold += 1
            if fname == "homebrew_items.json" and flag_homebrew_draft(item):
                n_draft += 1

    print(f"\n[FIX] Attunement synced:         {n_attn} items")
    print(f"[FIX] Recharge cleared:          {n_recharge} items")
    print(f"[FIX] Filler actions stripped:   {n_filler} items")
    print(f"[FIX] Scaffold notes stripped:   {n_scaffold} items")
    print(f"[FIX] Homebrew items flagged:    {n_draft} items")

    # ── Write files ───────────────────────────────────────────────────────────
    for fname, data in files.items():
        save_file(ITEMS_DIR / fname, data)
    print("\nFiles written.")

    # ── After counts ─────────────────────────────────────────────────────────
    # Reload to verify idempotency
    files2: dict[str, dict] = {}
    for path in sorted(ITEMS_DIR.glob("*.json")):
        if path.name in SKIP_FILES:
            continue
        files2[path.name] = load_file(path)

    after = count_issues(files2)

    print("\n=== AFTER ===")
    print(f"  Total items:                   {sum(len(d.get('items',[])) for d in files2.values())}")
    print(f"  Attunement disagreements:      {after['attunement_disagree']}")
    print(f"  Contradictory recharge:        {after['contradictory_recharge']}")
    print(f"  Filler actions (uncharged):    {after['filler_actions_uncharged']}")
    print(f"  Filler actions (charged, ⚠):  {after['filler_actions_charged_review']}")
    print(f"  Scaffold passive notes:        {after['scaffold_notes']}")
    print(f"  Homebrew TODO items:           {after['homebrew_todo_items']}")
    print(f"  Homebrew TODO summaries:       {after['homebrew_todo_summaries']}")
    print(f"  Vorpal sword in mundane file:  {after['vorpal_in_mundane']}")

    # Acceptance checks
    errors = []
    if after["attunement_disagree"] != 0:
        errors.append(f"FAIL: {after['attunement_disagree']} attunement disagreements remain")
    if after["contradictory_recharge"] != 0:
        errors.append(f"FAIL: {after['contradictory_recharge']} contradictory recharge remain")
    if after["filler_actions_uncharged"] != 0:
        errors.append(f"FAIL: {after['filler_actions_uncharged']} filler actions on uncharged remain")
    if after["scaffold_notes"] != 0:
        errors.append(f"FAIL: {after['scaffold_notes']} scaffold notes remain")
    if after["vorpal_in_mundane"] != 0:
        errors.append("FAIL: vorpal-sword still in mundane_weapons.json")

    # Verify vorpal in legendary
    leg_items = files2.get("legendary_magic_items.json", {}).get("items", [])
    vorpal_in_leg = next((it for it in leg_items if it.get("id") == "vorpal-sword"), None)
    if not vorpal_in_leg:
        errors.append("FAIL: vorpal-sword not found in legendary_magic_items.json")
    elif vorpal_in_leg.get("rarity") != "legendary":
        errors.append(f"FAIL: vorpal-sword rarity={vorpal_in_leg.get('rarity')!r}, expected 'legendary'")
    elif not vorpal_in_leg.get("requires_attunement"):
        errors.append("FAIL: vorpal-sword requires_attunement is not true")
    elif not (isinstance(vorpal_in_leg.get("attunement"), dict) and vorpal_in_leg["attunement"].get("required")):
        errors.append("FAIL: vorpal-sword attunement.required is not true")

    if errors:
        print()
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\nAll acceptance checks PASSED.")

    # List charged items with filler actions for human review
    all_items2 = iter_all_items(files2)
    charged_filler = [
        (fn, it.get("id"), it.get("name"))
        for fn, it in all_items2
        if it.get("charges_max", 0) > 0
        and any(
            isinstance(a, dict) and a.get("summary") == FILLER_ACTION_SUMMARY
            for a in it.get("granted_actions", [])
        )
    ]
    if charged_filler:
        print(f"\n⚠ {len(charged_filler)} charged items with generic 'Activate this item.' action (LEFT for human review):")
        for fn, iid, name in charged_filler:
            print(f"  {fn}: {iid} ({name})")

    homebrew_drafts = [
        it.get("id")
        for fn, it in all_items2
        if fn == "homebrew_items.json" and it.get("draft")
    ]
    if homebrew_drafts:
        print(f"\n⚠ {len(homebrew_drafts)} homebrew items flagged as draft (TODO summaries, need human authoring):")
        for iid in homebrew_drafts:
            print(f"  {iid}")


if __name__ == "__main__":
    main()
