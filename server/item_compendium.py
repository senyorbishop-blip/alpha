"""
server/item_compendium.py — Item compendium loader and spell-lookup utilities.

Loads structured item JSON from server/data/rules/5e2024/items/ and
provides lookup functions used by the inventory system and audit tools.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "rules", "5e2024")
_ITEMS_DIR = os.path.join(_DATA_DIR, "items")
_SPELLS_DIR = os.path.join(_DATA_DIR, "spells")

_ITEM_FILES = [
    "weapons.json", "armor.json", "shields.json", "adventuring_gear.json",
    "tools.json", "potions.json", "scrolls.json", "wands.json",
    "staffs.json", "rods.json", "rings.json", "wondrous.json", "homebrew.json",
]

_SPELL_FILES = [
    "spells-cantrip.json", "spells-1st.json", "spells-2nd.json",
    "spells-3rd.json", "spells-4th.json", "spells-5th.json",
    "spells-6th.json", "spells-7th.json", "spells-8th.json", "spells-9th.json",
]


def _load_item_compendium_impl() -> dict[str, dict]:
    """Load all item compendium files; return dict keyed by item id."""
    catalog: dict[str, dict] = {}
    for fname in _ITEM_FILES:
        path = os.path.join(_ITEMS_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("items", [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "").strip()
                if item_id and item_id not in catalog:
                    catalog[item_id] = item
        except Exception:
            pass
    return catalog


def _load_spell_index_impl() -> dict[str, dict]:
    """Load all spell level JSON files; return dict keyed by spell id."""
    index: dict[str, dict] = {}
    for fname in _SPELL_FILES:
        path = os.path.join(_SPELLS_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            spells = data.get("spells", []) if isinstance(data, dict) else []
            for spell in spells:
                if not isinstance(spell, dict):
                    continue
                sid = str(spell.get("id") or "").strip()
                if sid and sid not in index:
                    index[sid] = spell
        except Exception:
            pass
    return index


_ITEM_CATALOG: dict[str, dict] | None = None
_SPELL_INDEX: dict[str, dict] | None = None


def _item_catalog() -> dict[str, dict]:
    global _ITEM_CATALOG
    if _ITEM_CATALOG is None:
        _ITEM_CATALOG = _load_item_compendium_impl()
    return _ITEM_CATALOG


def _spell_index() -> dict[str, dict]:
    global _SPELL_INDEX
    if _SPELL_INDEX is None:
        _SPELL_INDEX = _load_spell_index_impl()
    return _SPELL_INDEX


def clear_cache() -> None:
    """Invalidate in-process caches — useful in tests."""
    global _ITEM_CATALOG, _SPELL_INDEX
    _ITEM_CATALOG = None
    _SPELL_INDEX = None


def _slugify_name(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")[:120]


def get_item_by_id(item_id: str) -> dict | None:
    """Return the compendium entry for the given item id, or None."""
    return _item_catalog().get(str(item_id or "").strip())


def get_item_by_slug(slug: str) -> dict | None:
    """Return the compendium entry for the given slug, or None.

    Matches against item 'slug' field or a slug derived from item 'id'.
    """
    target = str(slug or "").strip().lower()
    if not target:
        return None
    for item in _item_catalog().values():
        item_slug = str(item.get("slug") or item.get("id") or "").strip().lower()
        if item_slug == target:
            return item
    return None


def get_spell_metadata(spell_id: str) -> dict | None:
    """Return spell JSON for the given spell id (from spell level files), or None."""
    return _spell_index().get(str(spell_id or "").strip())


def all_items() -> list[dict]:
    """Return all compendium items as a flat list."""
    return list(_item_catalog().values())


def all_items_by_category(category: str) -> list[dict]:
    """Return all compendium items matching the given category string."""
    cat = str(category or "").lower().strip()
    return [item for item in all_items() if str(item.get("category") or "").lower() == cat]


def all_items_by_subtype(subtype: str) -> list[dict]:
    """Return all compendium items matching the given subtype string."""
    st = str(subtype or "").lower().strip()
    return [item for item in all_items() if str(item.get("subtype") or "").lower() == st]


def find_item_by_name(name: str) -> dict | None:
    """Case-insensitive exact lookup of an item by name."""
    target = str(name or "").strip().lower()
    for item in all_items():
        if str(item.get("name") or "").strip().lower() == target:
            return item
    return None


def search_items_by_name(partial_name: str, *, limit: int = 20) -> list[dict]:
    """Case-insensitive partial-name search across all compendium items."""
    needle = str(partial_name or "").strip().lower()
    if not needle:
        return []
    results = [
        item for item in all_items()
        if needle in str(item.get("name") or "").lower()
    ]
    return results[:limit]


def merge_compendium_metadata(inventory_entry: dict) -> dict:
    """Merge compendium metadata into an inventory entry, preserving live state.

    Looks up the compendium record by id then name. If found, fills in any
    missing compendium fields (category, rarity, weapon_type, etc.) without
    overwriting live inventory state (equipped, attuned, charges_current, qty).
    """
    entry = dict(inventory_entry or {})
    item_id = str(entry.get("id") or entry.get("magic_item_id") or "").strip()
    name = str(entry.get("name") or "").strip()

    comp = get_item_by_id(item_id) or find_item_by_name(name)
    if not comp:
        return entry

    _LIVE_STATE_KEYS = {
        "equipped", "attuned", "qty", "quantity", "charges_current",
        "uses_current", "notes", "source", "price",
    }
    for key, value in comp.items():
        if key in _LIVE_STATE_KEYS:
            continue
        if not entry.get(key):
            entry[key] = value
    return entry


def all_spell_ids() -> set[str]:
    """Return the set of all known spell ids in the compendium."""
    return set(_spell_index().keys())


def catalog_for_dm_picker() -> list[dict]:
    """Return a sorted, DM-friendly item list for shop/chest/picker UIs.

    Returns lightweight dicts with id, name, category, subtype, rarity, source.
    """
    out = []
    for item in all_items():
        out.append({
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or ""),
            "category": str(item.get("category") or "misc"),
            "subtype": str(item.get("subtype") or ""),
            "rarity": str(item.get("rarity") or "common"),
            "requires_attunement": bool(item.get("requires_attunement")),
            "charges_max": int(item.get("charges_max") or 0),
            "has_spells": bool(item.get("granted_spells")),
            "source": str(item.get("source") or "compendium"),
        })
    out.sort(key=lambda x: (x["category"], x["name"].lower()))
    return out
