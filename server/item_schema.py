from __future__ import annotations

import re
from typing import Any

_CANONICAL_CATEGORIES = {
    "weapon", "armor", "shield", "potion", "scroll", "wand", "staff", "ring",
    "wondrous", "tool", "consumable", "material", "recipe", "trinket", "misc", "quest",
}

_RARITY_ALIASES = {
    "": "common",
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "very rare": "very_rare",
    "very_rare": "very_rare",
    "legendary": "legendary",
    "artifact": "artifact",
    "varies": "varies",
}

_SLOT_ALIASES = {
    "armor": "armor",
    "armour": "armor",
    "shield": "shield",
    "main_hand": "main_hand",
    "off_hand": "off_hand",
    "ring": "ring",
    "cloak": "cloak",
    "neck": "neck",
    "head": "head",
    "hands": "hands",
    "feet": "feet",
    "waist": "waist",
    "trinket": "trinket",
}

_SCROLL_KINDS = {"spell": "spell_scroll", "protection": "protection_scroll", "utility": "utility_scroll"}


def _clean_text(raw: Any, *, limit: int = 2000) -> str:
    return str(raw or "").strip()[:limit]


def _safe_int(raw: Any, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _safe_float(raw: Any, default: float = 0.0, *, minimum: float | None = None) -> float:
    try:
        value = float(raw)
    except Exception:
        value = float(default)
    if minimum is not None:
        value = max(minimum, value)
    return value


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug[:120] or "item"


def _ensure_list(raw: Any, *, cap: int = 32) -> list:
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [x.strip() for x in str(raw).split(",") if x.strip()]
    out: list = []
    for val in values:
        if isinstance(val, (dict, list)):
            out.append(val)
        else:
            txt = str(val or "").strip()
            if txt:
                out.append(txt[:120])
        if len(out) >= cap:
            break
    return out


def _normalize_category(raw: Any, raw_item_type: str, name: str, tags: list[str]) -> tuple[str, str]:
    category_raw = _clean_text(raw, limit=48).lower().replace(" ", "_")
    item_type = _clean_text(raw_item_type, limit=48).lower().replace(" ", "_")
    name_l = name.lower()
    tags_l = [str(t).lower() for t in tags]

    if item_type in {"armour"}:
        item_type = "armor"

    if category_raw in {"wondrous_item", "wondrous item", "wondrous"}:
        return "wondrous", item_type or "wondrous"
    if category_raw in _CANONICAL_CATEGORIES:
        return category_raw, item_type or category_raw
    if item_type in _CANONICAL_CATEGORIES:
        return item_type, item_type

    hints = [
        ("scroll", "scroll"), ("potion", "potion"), ("wand", "wand"), ("staff", "staff"),
        ("ring", "ring"), ("shield", "shield"), ("armor", "armor"), ("armour", "armor"),
        ("recipe", "recipe"), ("material", "material"), ("ingot", "material"), ("ore", "material"),
        ("hide", "material"), ("gem", "material"), ("reagent", "material"), ("tool", "tool"),
        ("pistol", "weapon"), ("musket", "weapon"), ("sword", "weapon"), ("bow", "weapon"),
        ("axe", "weapon"), ("dagger", "weapon"), ("cloak", "wondrous"), ("amulet", "wondrous"),
    ]
    for token, mapped in hints:
        if token in name_l or token in tags_l:
            return mapped, item_type or _slugify(name)
    return "misc", item_type or _slugify(name)


def _derive_scroll_data(name: str, effect_text: str, granted_spells: list) -> dict:
    name_l = name.lower()
    level_match = re.search(r"(\d+)(?:st|nd|rd|th)?\s*level", name_l)
    spell_level = _safe_int(level_match.group(1), 0, minimum=0, maximum=9) if level_match else 0
    kind = "spell"
    if "protection" in name_l:
        kind = "protection"
    elif "utility" in name_l:
        kind = "utility"
    spell_ref = ""
    if granted_spells and isinstance(granted_spells[0], dict):
        spell_ref = _clean_text(granted_spells[0].get("id") or granted_spells[0].get("name"), limit=120)
    return {
        "spell_level": spell_level,
        "spell_reference": spell_ref,
        "scroll_kind": _SCROLL_KINDS.get(kind, "spell_scroll"),
        "use_text": _clean_text(effect_text, limit=300) or "Use this scroll as an action.",
    }


def normalize_item_record(raw_item: dict | None, *, source_type: str = "inventory", source_id: str = "") -> dict:
    src = dict(raw_item or {})
    name = _clean_text(src.get("name") or src.get("item_name"), limit=120) or "Unknown Item"
    tags = _ensure_list(src.get("tags") or src.get("recipe_tags") or [])
    tags_flat = [str(t).lower() for t in tags if not isinstance(t, (dict, list))]

    category, subtype = _normalize_category(src.get("category"), src.get("item_type"), name, tags_flat)
    rarity_raw = _clean_text(src.get("rarity"), limit=32).lower()
    rarity = _RARITY_ALIASES.get(rarity_raw, "common")

    qty = _safe_int(src.get("quantity", src.get("qty", 1)), 1, minimum=1, maximum=9999)
    stack_limit = _safe_int(src.get("stack_limit", 1), 1, minimum=1, maximum=9999)
    charges_max = _safe_int(src.get("charges_max", 0), 0, minimum=0, maximum=999)
    charges_current_default = charges_max if charges_max > 0 else 0

    equip_slot = _clean_text(src.get("equip_slot"), limit=32).lower().replace(" ", "_")
    equip_slot = _SLOT_ALIASES.get(equip_slot, "")

    canonical = {
        "schema_version": 2,
        "identity": {
            "item_id": _clean_text(src.get("id") or src.get("item_id") or source_id, limit=80),
            "source_id": _clean_text(source_id or src.get("source_id") or src.get("magic_item_id") or src.get("id"), limit=80),
            "source_type": _clean_text(source_type or src.get("source_type") or "inventory", limit=40).lower(),
            "name": name,
            "slug": _clean_text(src.get("slug"), limit=120) or _slugify(name),
            "category": category,
            "subtype": _clean_text(src.get("subtype"), limit=80) or subtype,
            "rarity": rarity,
            "tags": tags,
            "item_schema_version": _safe_int(src.get("item_schema_version"), 2, minimum=1, maximum=99),
        },
        "display": {
            "icon": _clean_text(src.get("icon"), limit=300),
            "image_key": _clean_text(src.get("image_key"), limit=160),
            "image_url": _clean_text(src.get("image_url") or src.get("image_path"), limit=500),
            "image_path": _clean_text(src.get("image_path"), limit=500),
            "category_icon_key": _clean_text(src.get("category_icon_key"), limit=120),
            "subtype_icon_key": _clean_text(src.get("subtype_icon_key"), limit=120),
            "flavor_text": _clean_text(src.get("flavor_text"), limit=240),
            "short_description": _clean_text(src.get("notes") or src.get("description"), limit=240),
            "full_description": _clean_text(src.get("effect") or src.get("description"), limit=2000),
        },
        "economy": {
            "quantity": qty,
            "stack_limit": max(1, stack_limit),
            "weight_lbs": _safe_float(src.get("weight_lbs", src.get("weight", 0)), 0.0, minimum=0.0),
            "price_gp": _safe_int(src.get("price_gp", 0), 0, minimum=0),
            "price_sp": _safe_int(src.get("price_sp", 0), 0, minimum=0),
            "price_cp": _safe_int(src.get("price_cp", 0), 0, minimum=0),
            "sell_value_units": _safe_int(src.get("sell_value", 0), 0, minimum=0),
            "tradable": bool(src.get("tradable", True)),
            "droppable": bool(src.get("droppable", True)),
        },
        "equipment": {
            "equippable": bool(src.get("equippable", category in {"weapon", "armor", "shield", "ring", "wondrous", "staff", "wand"})),
            "equip_slot": equip_slot,
            "handedness": _clean_text(src.get("handedness"), limit=32),
            "armor_type": _clean_text(src.get("armor_type"), limit=32),
            "weapon_type": _clean_text(src.get("weapon_type"), limit=32),
            "ammo_type": _clean_text(src.get("ammo_type"), limit=32),
            "requires_attunement": bool(src.get("attunement_required") or src.get("requires_attunement")),
            "attuned": bool(src.get("attuned")),
            "proficiency_group": _clean_text(src.get("proficiency_group"), limit=40),
            "item_spell_attack_bonus": _safe_int(src.get("item_spell_attack_bonus"), 0, minimum=-20, maximum=30),
            "item_spell_save_dc": _safe_int(src.get("item_spell_save_dc"), 0, minimum=0, maximum=40),
        },
        "effects": {
            "passive_effects": _ensure_list(src.get("passive_effects"), cap=16),
            "granted_actions": _ensure_list(src.get("granted_actions"), cap=12),
            "granted_spells": _ensure_list(src.get("granted_spells"), cap=12),
            "bonuses": _ensure_list(src.get("bonuses"), cap=16),
            "resistances": _ensure_list(src.get("resistances"), cap=12),
            "immunities": _ensure_list(src.get("immunities"), cap=12),
            "senses_modifiers": _ensure_list(src.get("senses_modifiers"), cap=10),
            "movement_modifiers": _ensure_list(src.get("movement_modifiers"), cap=10),
            "stat_overrides": dict(src.get("stat_overrides") or {}) if isinstance(src.get("stat_overrides"), dict) else {},
            "stat_minimums": dict(src.get("stat_minimums") or {}) if isinstance(src.get("stat_minimums"), dict) else {},
        },
        "usage": {
            "consumable": bool(src.get("consumable", category in {"potion", "consumable", "scroll"})),
            "consumed_on_use": bool(src.get("consumed_on_use", category in {"potion", "scroll", "consumable"})),
            "remove_when_empty": bool(src.get("remove_when_empty", True)),
            "charges_current": _safe_int(src.get("charges_current", charges_current_default), charges_current_default, minimum=0, maximum=charges_max if charges_max > 0 else 999),
            "charges_max": charges_max,
            "uses_current": _safe_int(src.get("uses_current", 0), 0, minimum=0, maximum=999),
            "uses_max": _safe_int(src.get("uses_max", 0), 0, minimum=0, maximum=999),
            "recharge_type": _clean_text(src.get("recharge_type"), limit=32).lower(),
            "recharge_formula": _clean_text(src.get("recharge_formula"), limit=64),
            "recharge_on_rest": _clean_text(src.get("recharge_on_rest"), limit=24).lower(),
            "cooldown_type": _clean_text(src.get("cooldown_type"), limit=32).lower(),
        },
        "crafting": {
            "material_type": _clean_text(src.get("material_type"), limit=40),
            "recipe_tags": _ensure_list(src.get("recipe_tags"), cap=16),
            "profession_tags": _ensure_list(src.get("profession_tags"), cap=16),
            "item_family": _clean_text(src.get("item_family"), limit=60),
            "named_item_flag": bool(src.get("named_item_flag")),
            "legendary_flag": bool(src.get("legendary_flag") or rarity == "legendary"),
        },
        "scroll": {},
    }

    if category == "scroll":
        canonical["scroll"] = _derive_scroll_data(name, canonical["display"].get("full_description", ""), canonical["effects"].get("granted_spells") or [])
        canonical["usage"]["consumable"] = True
        canonical["usage"]["consumed_on_use"] = True

    return canonical


def normalize_magic_item_row(row: dict | None) -> dict:
    return normalize_item_record(row or {}, source_type="magic_item", source_id=str((row or {}).get("id") or ""))


def normalize_srd_item_row(row: dict | None) -> dict:
    return normalize_item_record(row or {}, source_type="srd_item", source_id=str((row or {}).get("id") or ""))


def normalize_shop_item_row(row: dict | None) -> dict:
    raw = dict(row or {})
    data = raw.get("item_data") if isinstance(raw.get("item_data"), dict) else {}
    merged = {
        **data,
        "id": raw.get("id") or data.get("id") or "",
        "name": raw.get("item_name") or data.get("name") or "Item",
        "item_type": raw.get("item_type") or data.get("item_type") or "misc",
        "description": raw.get("description") or data.get("description") or "",
        "price_gp": raw.get("price_gp", data.get("price_gp", 0)),
        "price_sp": raw.get("price_sp", data.get("price_sp", 0)),
        "price_cp": raw.get("price_cp", data.get("price_cp", 0)),
        "quantity": raw.get("quantity", data.get("quantity", 1)),
    }
    return normalize_item_record(merged, source_type="shop_item", source_id=str(raw.get("id") or ""))


def normalize_crafted_result_row(row: dict | None, *, recipe_id: str = "") -> dict:
    src = dict(row or {})
    return normalize_item_record(src, source_type="craft_result", source_id=recipe_id or str(src.get("id") or ""))


def to_inventory_entry(canonical: dict, *, notes: str = "", source_label: str = "", price_label: str = "") -> dict:
    identity = dict(canonical.get("identity") or {})
    display = dict(canonical.get("display") or {})
    economy = dict(canonical.get("economy") or {})
    equipment = dict(canonical.get("equipment") or {})
    usage = dict(canonical.get("usage") or {})
    effects = dict(canonical.get("effects") or {})
    crafting = dict(canonical.get("crafting") or {})

    entry = {
        "id": identity.get("item_id") or identity.get("source_id") or identity.get("slug"),
        "name": identity.get("name") or "Item",
        "qty": _safe_int(economy.get("quantity"), 1, minimum=1, maximum=9999),
        "notes": _clean_text(notes or display.get("short_description"), limit=240),
        "source": _clean_text(source_label, limit=80),
        "price": _clean_text(price_label, limit=32),
        "category": identity.get("category") or "misc",
        "item_type": identity.get("subtype") or identity.get("category") or "misc",
        "rarity": identity.get("rarity") or "common",
        "slug": identity.get("slug") or _slugify(identity.get("name") or "item"),
        "source_type": identity.get("source_type") or "inventory",
        "source_id": identity.get("source_id") or "",
        "tags": ", ".join(str(x) for x in list(identity.get("tags") or [])[:20] if not isinstance(x, (dict, list))),
        "icon": display.get("icon") or "",
        "image_key": display.get("image_key") or "",
        "image_url": display.get("image_url") or "",
        "image_path": display.get("image_path") or "",
        "category_icon_key": display.get("category_icon_key") or "",
        "subtype_icon_key": display.get("subtype_icon_key") or "",
        "weight_lbs": _safe_float(economy.get("weight_lbs"), 0.0, minimum=0.0),
        "stack_limit": _safe_int(economy.get("stack_limit"), 1, minimum=1, maximum=9999),
        "attunement_required": bool(equipment.get("requires_attunement")),
        "attuned": bool(equipment.get("attuned")),
        "equippable": bool(equipment.get("equippable")),
        "equip_slot": equipment.get("equip_slot") or "",
        "handedness": equipment.get("handedness") or "",
        "armor_type": equipment.get("armor_type") or "",
        "weapon_type": equipment.get("weapon_type") or "",
        "ammo_type": equipment.get("ammo_type") or "",
        "proficiency_group": equipment.get("proficiency_group") or "",
        "item_spell_attack_bonus": _safe_int(equipment.get("item_spell_attack_bonus"), 0, minimum=-20, maximum=30),
        "item_spell_save_dc": _safe_int(equipment.get("item_spell_save_dc"), 0, minimum=0, maximum=40),
        "item_schema_version": _safe_int((canonical.get("identity") or {}).get("item_schema_version"), 2, minimum=1, maximum=99),
        "consumable": bool(usage.get("consumable")),
        "consumed_on_use": bool(usage.get("consumed_on_use")),
        "remove_when_empty": bool(usage.get("remove_when_empty")),
        "charges_current": _safe_int(usage.get("charges_current"), 0, minimum=0, maximum=999),
        "charges_max": _safe_int(usage.get("charges_max"), 0, minimum=0, maximum=999),
        "uses_current": _safe_int(usage.get("uses_current"), 0, minimum=0, maximum=999),
        "uses_max": _safe_int(usage.get("uses_max"), 0, minimum=0, maximum=999),
        "recharge_type": _clean_text(usage.get("recharge_type"), limit=32),
        "recharge_formula": _clean_text(usage.get("recharge_formula"), limit=64),
        "passive_effects": list(effects.get("passive_effects") or []),
        "granted_spells": list(effects.get("granted_spells") or []),
        "bonuses": list(effects.get("bonuses") or []),
        "resistances": list(effects.get("resistances") or []),
        "immunities": list(effects.get("immunities") or []),
        "senses_modifiers": list(effects.get("senses_modifiers") or []),
        "movement_modifiers": list(effects.get("movement_modifiers") or []),
        "stat_overrides": dict(effects.get("stat_overrides") or {}),
        "stat_minimums": dict(effects.get("stat_minimums") or {}),
        "material_type": _clean_text(crafting.get("material_type"), limit=40),
        "recipe_tags": list(crafting.get("recipe_tags") or []),
        "profession_tags": list(crafting.get("profession_tags") or []),
        "item_family": _clean_text(crafting.get("item_family"), limit=60),
        "named_item_flag": bool(crafting.get("named_item_flag")),
        "legendary_flag": bool(crafting.get("legendary_flag")),
        "item_schema": canonical,
    }
    if canonical.get("scroll"):
        entry["scroll_data"] = dict(canonical.get("scroll") or {})
    return entry
