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
    "weapons.json", "armor.json", "shields.json", "potions.json",
    "scrolls.json", "wands.json", "staffs.json", "rods.json",
    "rings.json", "wondrous.json", "homebrew.json",
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


def get_item_by_id(item_id: str) -> dict | None:
    """Return the compendium entry for the given item id, or None."""
    return _item_catalog().get(str(item_id or "").strip())


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


def find_item_by_name(name: str) -> dict | None:
    """Case-insensitive lookup of an item by name."""
    target = str(name or "").strip().lower()
    for item in all_items():
        if str(item.get("name") or "").strip().lower() == target:
            return item
    return None


def all_spell_ids() -> set[str]:
    """Return the set of all known spell ids in the compendium."""
    return set(_spell_index().keys())
