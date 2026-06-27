"""
server/item_compendium.py — Item compendium loader, dedup engine, and lookup utilities.

Loads structured item JSON from server/data/rules/5e2024/items/ using the
rarity-split file organization and provides:
  - Lookup by id, slug, name, alias, legacy_id, dedupe_key
  - Duplicate detection and safe-merge with warnings
  - Category / rarity / attunement / charges / spells / passive / combat filters
  - DM item picker catalog builder
  - Compendium metadata merge into inventory entries
  - Spell index for granted_spell validation
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "rules", "5e2024")
_ITEMS_DIR = os.path.join(_DATA_DIR, "items")
_SPELLS_DIR = os.path.join(_DATA_DIR, "spells")

_logger = logging.getLogger(__name__)

# Primary item files — rarity-split organization.
_ITEM_FILES = [
    "mundane_weapons.json",
    "mundane_armor_shields.json",
    "adventuring_gear.json",
    "tools.json",
    "trade_goods_materials.json",
    "mounts_vehicles.json",
    "common_magic_items.json",
    "uncommon_magic_items.json",
    "rare_magic_items.json",
    "very_rare_magic_items.json",
    "legendary_magic_items.json",
    "artifact_magic_items.json",
    "homebrew_items.json",
    "expanded_magic_items.json",
    "expanded_crafting_materials.json",
]

_SPELL_FILES = [
    "spells-cantrip.json", "spells-1st.json", "spells-2nd.json",
    "spells-3rd.json", "spells-4th.json", "spells-5th.json",
    "spells-6th.json", "spells-7th.json", "spells-8th.json", "spells-9th.json",
]

# ---------------------------------------------------------------------------
# Internal index structure
# ---------------------------------------------------------------------------

class _CompendiumIndex:
    """Multi-key lookup index for all compendium items."""

    def __init__(self) -> None:
        self._by_id: dict[str, dict] = {}
        self._by_slug: dict[str, str] = {}       # slug → id
        self._by_name: dict[str, str] = {}       # lower_name → id
        self._by_dedupe: dict[str, str] = {}     # dedupe_key → id
        self._by_alias: dict[str, str] = {}      # alias → id
        self._by_legacy: dict[str, str] = {}     # legacy_id → id
        self._merge_log: list[str] = []
        self._all_items_ordered: list[dict] = []

    def add(self, item: dict, *, source_file: str = "") -> None:
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            return

        name = str(item.get("name") or "").strip()
        slug = str(item.get("slug") or _slugify_name(name)).strip().lower()
        dk = str(item.get("dedupe_key") or _dedupe_key(name)).strip().lower()
        aliases = [str(a).strip().lower() for a in (item.get("aliases") or []) if a]
        legacy_ids = [str(l).strip() for l in (item.get("legacy_ids") or []) if l]
        name_l = name.lower()

        # --- Duplicate detection ---
        conflict_id: str | None = None
        conflict_reason: str | None = None

        if item_id in self._by_id:
            conflict_id = item_id
            conflict_reason = f"duplicate id '{item_id}'"
        elif slug and slug in self._by_slug and self._by_slug[slug] != item_id:
            conflict_id = self._by_slug[slug]
            conflict_reason = f"slug collision '{slug}' with '{conflict_id}'"
        elif dk and dk in self._by_dedupe and self._by_dedupe[dk] != item_id:
            conflict_id = self._by_dedupe[dk]
            conflict_reason = f"name collision (dedupe_key '{dk}') with '{conflict_id}'"

        if conflict_id is not None:
            # Safe merge: warn and skip the duplicate
            msg = (
                f"DEDUPE [{source_file}] Skipping '{item_id}' — {conflict_reason}. "
                f"Canonical record kept."
            )
            _logger.warning(msg)
            self._merge_log.append(msg)
            return

        # --- Register item ---
        self._by_id[item_id] = item
        self._all_items_ordered.append(item)

        if slug:
            self._by_slug[slug] = item_id
        if name_l:
            self._by_name[name_l] = item_id
        if dk:
            self._by_dedupe[dk] = item_id
        for alias in aliases:
            if alias not in self._by_alias:
                self._by_alias[alias] = item_id
        for leg in legacy_ids:
            if leg not in self._by_legacy:
                self._by_legacy[leg] = item_id

    def get_by_id(self, item_id: str) -> dict | None:
        return self._by_id.get(str(item_id or "").strip())

    def get_by_slug(self, slug: str) -> dict | None:
        target = str(slug or "").strip().lower()
        found_id = self._by_slug.get(target)
        if found_id:
            return self._by_id.get(found_id)
        # fallback: check if target matches an id directly
        return self._by_id.get(target)

    def get_by_name(self, name: str) -> dict | None:
        target = str(name or "").strip().lower()
        found_id = self._by_name.get(target)
        return self._by_id.get(found_id) if found_id else None

    def get_by_alias(self, alias: str) -> dict | None:
        target = str(alias or "").strip().lower()
        found_id = self._by_alias.get(target)
        return self._by_id.get(found_id) if found_id else None

    def get_by_legacy_id(self, legacy_id: str) -> dict | None:
        target = str(legacy_id or "").strip()
        found_id = self._by_legacy.get(target)
        return self._by_id.get(found_id) if found_id else None

    def get_by_dedupe_key(self, dk: str) -> dict | None:
        target = str(dk or "").strip().lower()
        found_id = self._by_dedupe.get(target)
        return self._by_id.get(found_id) if found_id else None

    def all(self) -> list[dict]:
        return list(self._all_items_ordered)

    def merge_log(self) -> list[str]:
        return list(self._merge_log)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")[:120]

def _dedupe_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())[:120]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_compendium_impl() -> _CompendiumIndex:
    index = _CompendiumIndex()
    for fname in _ITEM_FILES:
        path = os.path.join(_ITEMS_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("items", [])
            for item in items:
                if isinstance(item, dict):
                    index.add(item, source_file=fname)
        except Exception as exc:
            _logger.error("Failed to load %s: %s", fname, exc)
    return index


def _load_spell_index_impl() -> dict[str, dict]:
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
                if isinstance(spell, dict):
                    sid = str(spell.get("id") or "").strip()
                    if sid and sid not in index:
                        index[sid] = spell
        except Exception:
            pass
    return index


# ---------------------------------------------------------------------------
# Module-level caches
# ---------------------------------------------------------------------------

_INDEX: _CompendiumIndex | None = None
_SPELL_INDEX: dict[str, dict] | None = None


def _compendium() -> _CompendiumIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = _load_compendium_impl()
    return _INDEX


def _spell_index() -> dict[str, dict]:
    global _SPELL_INDEX
    if _SPELL_INDEX is None:
        _SPELL_INDEX = _load_spell_index_impl()
    return _SPELL_INDEX


def clear_cache() -> None:
    """Invalidate in-process caches — useful in tests."""
    global _INDEX, _SPELL_INDEX
    _INDEX = None
    _SPELL_INDEX = None


# ---------------------------------------------------------------------------
# Public lookup API
# ---------------------------------------------------------------------------

def get_item_by_id(item_id: str) -> dict | None:
    """Return compendium entry by exact id."""
    return _compendium().get_by_id(item_id)


def get_item_by_slug(slug: str) -> dict | None:
    """Return compendium entry by slug."""
    return _compendium().get_by_slug(slug)


def find_item_by_name(name: str) -> dict | None:
    """Case-insensitive exact name lookup."""
    return _compendium().get_by_name(name)


def find_item_by_alias(alias: str) -> dict | None:
    """Lookup by any registered alias or alternate slug."""
    idx = _compendium()
    # Check alias index first
    item = idx.get_by_alias(alias)
    if item:
        return item
    # Also try it as a slug or name
    target = str(alias or "").strip().lower()
    return idx.get_by_slug(target) or idx.get_by_name(target)


def find_item_by_legacy_id(legacy_id: str) -> dict | None:
    """Return the canonical item that claims a given legacy/old ID."""
    return _compendium().get_by_legacy_id(legacy_id)


def find_item_by_dedupe_key(dk: str) -> dict | None:
    """Return item by normalized dedupe key (lowercase, alphanumeric only)."""
    return _compendium().get_by_dedupe_key(dk)


def resolve_item(ref: str) -> dict | None:
    """Try all lookup strategies in priority order: id → slug → alias → legacy_id → name → dedupe_key."""
    idx = _compendium()
    return (
        idx.get_by_id(ref)
        or idx.get_by_slug(ref)
        or idx.get_by_alias(ref)
        or idx.get_by_legacy_id(ref)
        or idx.get_by_name(ref)
        or idx.get_by_dedupe_key(_dedupe_key(ref))
    )


def get_spell_metadata(spell_id: str) -> dict | None:
    """Return spell JSON for the given spell id, or None."""
    return _spell_index().get(str(spell_id or "").strip())


# ---------------------------------------------------------------------------
# Collection queries
# ---------------------------------------------------------------------------

def all_items() -> list[dict]:
    """Return all compendium items as a flat list."""
    return _compendium().all()


def all_items_by_category(category: str) -> list[dict]:
    cat = str(category or "").lower().strip()
    return [i for i in all_items() if str(i.get("category") or "").lower() == cat]


def all_items_by_subtype(subtype: str) -> list[dict]:
    st = str(subtype or "").lower().strip()
    return [i for i in all_items() if str(i.get("subtype") or "").lower() == st]


def all_items_by_rarity(rarity: str) -> list[dict]:
    """Return items matching the given rarity string."""
    target = str(rarity or "").lower().strip()
    return [i for i in all_items() if str(i.get("rarity") or "").lower() == target]


def search_items_by_name(partial_name: str, *, limit: int = 20) -> list[dict]:
    """Case-insensitive partial-name search."""
    needle = str(partial_name or "").strip().lower()
    if not needle:
        return []
    results = [i for i in all_items() if needle in str(i.get("name") or "").lower()]
    return results[:limit]


# ---------------------------------------------------------------------------
# Filter helpers (for DM picker / search)
# ---------------------------------------------------------------------------

def filter_items(
    *,
    category: str | None = None,
    rarity: str | None = None,
    source: str | None = None,
    requires_attunement: bool | None = None,
    has_charges: bool | None = None,
    grants_spells: bool | None = None,
    has_passive_effect: bool | None = None,
    combat_usable: bool | None = None,
) -> list[dict]:
    """Return items matching all non-None filter criteria."""
    results = all_items()
    if category is not None:
        cat = category.lower().strip()
        results = [i for i in results if str(i.get("category") or "").lower() == cat]
    if rarity is not None:
        rar = rarity.lower().strip()
        results = [i for i in results if str(i.get("rarity") or "").lower() == rar]
    if source is not None:
        src = source.lower().strip()
        results = [i for i in results if src in str(i.get("source") or "").lower()]
    if requires_attunement is not None:
        results = [
            i for i in results
            if bool(i.get("requires_attunement") or i.get("attunement_required")) == requires_attunement
        ]
    if has_charges is not None:
        results = [i for i in results if bool(int(i.get("charges_max") or 0) > 0) == has_charges]
    if grants_spells is not None:
        results = [i for i in results if bool(i.get("granted_spells")) == grants_spells]
    if has_passive_effect is not None:
        results = [i for i in results if bool(i.get("passive_effects")) == has_passive_effect]
    if combat_usable is not None:
        def _is_combat_usable(item: dict) -> bool:
            if item.get("granted_actions"):
                return True
            if item.get("granted_spells"):
                return True
            cat = str(item.get("category") or "").lower()
            if cat in {"weapon", "consumable", "potion"}:
                return True
            if item.get("damage_dice"):
                return True
            return False
        results = [i for i in results if _is_combat_usable(i) == combat_usable]
    return results


# ---------------------------------------------------------------------------
# Compendium metadata merge
# ---------------------------------------------------------------------------

_PLAYER_STATE_KEYS = frozenset({
    # Player-owned state must survive compendium/library rehydration.
    "qty", "quantity", "equipped", "attuned", "charges_current", "uses_current",
    "notes", "price", "bag_contents", "contents", "container_contents",
})

_CANONICAL_REHYDRATE_KEYS = frozenset({
    "id", "name", "display_name", "icon", "image_key", "image_url", "image_path",
    "category_icon_key", "subtype_icon_key", "category", "item_type", "subtype",
    "rarity", "slug", "aliases", "legacy_ids", "dedupe_key", "is_magic",
    "requires_attunement", "attunement_required", "attunement", "equippable", "equip_slot",
    "handedness", "armor_type", "weapon_type", "ammo_type", "weapon_properties",
    "base_ac", "dex_cap", "ac_bonus", "strength_requirement", "stealth_disadvantage",
    "attack_bonus", "damage_bonus", "damage_dice", "damage_type", "damage_formula",
    "versatile_damage", "versatile_damage_formula", "magic_bonus", "range", "reach",
    "charges_max", "recharge_type", "recharge_formula", "recharge_on_rest",
    "uses_max", "granted_spells", "granted_actions", "magicActions", "passive_effects",
    "bonuses", "resistances", "immunities", "senses_modifiers", "movement_modifiers",
    "stat_overrides", "stat_minimums", "item_spell_save_dc", "item_spell_attack_bonus",
    "action_card", "effect", "effect_text", "description_summary", "rules_summary",
    "unidentified_description", "consumable", "consumed_on_use", "remove_when_empty",
    "grants_action", "action_type", "activation_type", "usage_cost", "target_type",
    "save_dc", "healing_formula", "item_schema_version", "weight_lbs", "stack_limit",
})


def _source_revision_for_item(item: dict) -> int:
    for key in ("source_revision", "revision", "item_schema_version", "updated_at"):
        raw = item.get(key)
        try:
            if raw not in (None, ""):
                return max(1, int(float(raw)))
        except Exception:
            continue
    return 1


def _resolve_compendium_for_inventory(entry: dict) -> dict | None:
    source_id = str(entry.get("source_id") or "").strip()
    if source_id:
        return resolve_item(source_id)

    magic_item_id = str(entry.get("magic_item_id") or "").strip()
    if magic_item_id:
        # An explicit but unknown magic_item_id is usually a custom/homebrew row;
        # do not fall through to a same-name library item and overwrite it.
        return resolve_item(magic_item_id)

    # Rows that already carry their own granted spells/actions without source
    # markers are treated as self-contained custom/test items, not stale library
    # copies, unless a source_id/magic_item_id above explicitly linked them.
    if entry.get("granted_spells") or entry.get("granted_actions"):
        return None

    candidates = [entry.get("id"), entry.get("slug"), entry.get("name")]
    seen: set[str] = set()
    for raw in candidates:
        ref = str(raw or "").strip()
        if not ref or ref.lower() in seen:
            continue
        seen.add(ref.lower())
        found = resolve_item(ref)
        if found:
            return found
    return None


def merge_compendium_metadata(inventory_entry: dict) -> dict:
    """Safely rehydrate an inventory entry from the canonical item library.

    Player-owned state (quantity, equipment/attunement state, current charges,
    notes, and container contents) is preserved. Canonical library metadata such
    as rarity, display fields, granted spells/actions, max charges/recharge, and
    attack/damage metadata is refreshed whenever a source item can be resolved.
    """
    entry = dict(inventory_entry or {})
    comp = _resolve_compendium_for_inventory(entry)
    if not comp:
        entry.setdefault("source_type", str(entry.get("source_type") or "inventory"))
        entry.setdefault("source_id", str(entry.get("source_id") or entry.get("magic_item_id") or entry.get("id") or ""))
        entry.setdefault("source_revision", _source_revision_for_item(entry))
        return entry

    prior_current = entry.get("charges_current")
    prior_max = entry.get("charges_max")
    source_revision = _source_revision_for_item(comp)
    has_entry_revision = entry.get("source_revision") not in (None, "")
    entry_revision = _source_revision_for_item(entry) if has_entry_revision else source_revision
    comp_rarity = str(comp.get("rarity") or "").strip().lower()
    entry_rarity = str(entry.get("rarity") or "").strip().lower()
    needs_repair = (
        (has_entry_revision and entry_revision < source_revision)
        or (entry_rarity in {"", "common", "starter", "unknown"} and comp_rarity not in {"", "common", "starter", "unknown"})
        or (not entry.get("granted_spells") and bool(comp.get("granted_spells")))
        or (int(entry.get("charges_max") or 0) <= 0 and int(comp.get("charges_max") or 0) > 0)
    )

    for key in _CANONICAL_REHYDRATE_KEYS:
        if key in _PLAYER_STATE_KEYS or key not in comp:
            continue
        value = comp.get(key)
        if value in (None, ""):
            continue
        if needs_repair or entry.get(key) in (None, "", [], {}):
            entry[key] = value

    comp_id = str(comp.get("id") or "").strip()
    entry["source_type"] = "compendium"
    entry["source_id"] = comp_id or str(entry.get("source_id") or entry.get("magic_item_id") or entry.get("id") or "")
    entry["source_revision"] = source_revision
    if comp_id:
        entry["id"] = comp_id
        entry.setdefault("magic_item_id", comp_id)

    # Preserve current charges unless the canonical max changed enough to require
    # clamping, or the legacy entry never had a current value at all.
    try:
        comp_max = max(0, int(comp.get("charges_max") or 0))
    except Exception:
        comp_max = 0
    if comp_max > 0 and (needs_repair or entry.get("charges_max") in (None, "", 0, "0")):
        entry["charges_max"] = comp_max
        if prior_current in (None, ""):
            entry["charges_current"] = comp.get("charges_current", comp_max) or comp_max
        else:
            try:
                current = max(0, int(prior_current))
            except Exception:
                current = comp_max
            entry["charges_current"] = min(current, comp_max)
    elif prior_max not in (None, "") and prior_current not in (None, ""):
        entry["charges_current"] = prior_current

    return entry


# ---------------------------------------------------------------------------
# Spell utilities
# ---------------------------------------------------------------------------

def all_spell_ids() -> set[str]:
    """Return the set of all known spell ids in the compendium."""
    return set(_spell_index().keys())


# ---------------------------------------------------------------------------
# DM Item Picker
# ---------------------------------------------------------------------------

def catalog_for_dm_picker(
    *,
    category: str | None = None,
    rarity: str | None = None,
    source: str | None = None,
    requires_attunement: bool | None = None,
    has_charges: bool | None = None,
    grants_spells: bool | None = None,
    has_passive_effect: bool | None = None,
    combat_usable: bool | None = None,
    search: str | None = None,
) -> list[dict]:
    """Return a sorted, filterable DM item list for shop/chest/picker UIs.

    Supports all filter_items() criteria plus a partial-name search.
    Returns lightweight dicts with id, name, category, subtype, rarity,
    slug, aliases, source, has_spells, has_charges, requires_attunement,
    combat_usable.
    """
    items = filter_items(
        category=category,
        rarity=rarity,
        source=source,
        requires_attunement=requires_attunement,
        has_charges=has_charges,
        grants_spells=grants_spells,
        has_passive_effect=has_passive_effect,
        combat_usable=combat_usable,
    )
    if search:
        needle = search.strip().lower()
        items = [
            i for i in items
            if needle in str(i.get("name") or "").lower()
            or any(needle in str(a).lower() for a in (i.get("aliases") or []))
        ]

    out = []
    for item in items:
        def _is_combat(i: dict) -> bool:
            if i.get("granted_actions") or i.get("granted_spells"):
                return True
            if str(i.get("category") or "").lower() in {"weapon", "potion", "consumable"}:
                return True
            if i.get("damage_dice"):
                return True
            return False

        out.append({
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or ""),
            "slug": str(item.get("slug") or ""),
            "aliases": list(item.get("aliases") or []),
            "legacy_ids": list(item.get("legacy_ids") or []),
            "dedupe_key": str(item.get("dedupe_key") or ""),
            "category": str(item.get("category") or "misc"),
            "subtype": str(item.get("subtype") or ""),
            "rarity": str(item.get("rarity") or "common"),
            "requires_attunement": bool(item.get("requires_attunement") or item.get("attunement_required")),
            "charges_max": int(item.get("charges_max") or 0),
            "has_spells": bool(item.get("granted_spells")),
            "has_passive_effect": bool(item.get("passive_effects")),
            "combat_usable": _is_combat(item),
            "source": str(item.get("source") or "compendium"),
            "description_summary": str(item.get("description_summary") or ""),
        })
    out.sort(key=lambda x: (x["rarity"], x["category"], x["name"].lower()))
    return out


# ---------------------------------------------------------------------------
# Audit / diagnostics helpers
# ---------------------------------------------------------------------------

def compendium_merge_log() -> list[str]:
    """Return the list of dedup/merge warnings emitted during load."""
    return _compendium().merge_log()


# Expose internal lists for audit tools (read-only)
def _item_catalog() -> dict[str, dict]:
    return _compendium()._by_id
