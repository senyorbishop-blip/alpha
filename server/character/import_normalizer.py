from __future__ import annotations

import copy
import re
import time
from typing import Any

from server.character.spell_compendium import get_spell_by_id
from server.character.validation import validate_or_raise


_DDB_ABILITY_MAP = {
    1: "str",
    2: "dex",
    3: "con",
    4: "int",
    5: "wis",
    6: "cha",
}

_KNOWN_SUBCLASS_BY_CLASS: dict[str, set[str]] = {
    "barbarian": {"path of the berserker", "path of the totem warrior", "path of the world tree"},
    "bard": {"college of glamour", "college of lore", "college of valor"},
    "cleric": {"life domain", "light domain", "trickery domain", "war domain"},
    "druid": {"circle of the land", "circle of the moon"},
    "fighter": {"champion", "battle master", "eldritch knight", "psi warrior"},
    "monk": {"way of the open hand", "way of shadow", "way of the four elements"},
    "paladin": {"oath of devotion", "oath of the ancients", "oath of vengeance"},
    "ranger": {"hunter", "beast master", "gloom stalker"},
    "rogue": {"thief", "assassin", "arcane trickster"},
    "sorcerer": {"draconic bloodline", "wild magic"},
    "warlock": {"the archfey", "the fiend", "the great old one"},
    "wizard": {"school of abjuration", "school of divination", "school of evocation", "school of illusion", "school of necromancy"},
}

_SPECIES_ALIAS_MAP: dict[str, list[str]] = {
    "elf": ["high elf", "wood elf", "drow"],
    "dwarf": ["hill dwarf", "mountain dwarf"],
    "gnome": ["forest gnome", "rock gnome"],
    "halfling": ["lightfoot halfling", "stout halfling"],
}


_DDB_ACTION_TYPE_MAP = {
    1: "action",
    2: "none",
    3: "bonus action",
    4: "reaction",
    5: "minute",
    6: "hour",
    7: "special",
    8: "legendary action",
}

_DDB_ABILITY_NAME_MAP = {
    "strength": "str",
    "dexterity": "dex",
    "constitution": "con",
    "intelligence": "int",
    "wisdom": "wis",
    "charisma": "cha",
}

_COMMON_ARMOR_STATS: dict[str, dict[str, Any]] = {
    "padded": {"base_ac": 11, "armor_type": "light", "stealth_disadvantage": True},
    "leather": {"base_ac": 11, "armor_type": "light"},
    "studded leather": {"base_ac": 12, "armor_type": "light"},
    "hide": {"base_ac": 12, "armor_type": "medium", "dex_cap": 2},
    "chain shirt": {"base_ac": 13, "armor_type": "medium", "dex_cap": 2},
    "scale mail": {"base_ac": 14, "armor_type": "medium", "dex_cap": 2, "stealth_disadvantage": True},
    "breastplate": {"base_ac": 14, "armor_type": "medium", "dex_cap": 2},
    "half plate": {"base_ac": 15, "armor_type": "medium", "dex_cap": 2, "stealth_disadvantage": True},
    "ring mail": {"base_ac": 14, "armor_type": "heavy", "stealth_disadvantage": True},
    "chain mail": {"base_ac": 16, "armor_type": "heavy", "strength_requirement": 13, "stealth_disadvantage": True},
    "splint": {"base_ac": 17, "armor_type": "heavy", "strength_requirement": 15, "stealth_disadvantage": True},
    "plate": {"base_ac": 18, "armor_type": "heavy", "strength_requirement": 15, "stealth_disadvantage": True},
}

_COMMON_WEAPON_STATS: dict[str, dict[str, Any]] = {
    "club": {"damage_dice": "1d4", "damage_type": "bludgeoning", "properties": ["Light"], "range": "Melee 5 ft"},
    "dagger": {"damage_dice": "1d4", "damage_type": "piercing", "properties": ["Finesse", "Light", "Thrown"], "range": "20/60 ft"},
    "dart": {"damage_dice": "1d4", "damage_type": "piercing", "properties": ["Finesse", "Thrown"], "range": "20/60 ft"},
    "greatclub": {"damage_dice": "1d8", "damage_type": "bludgeoning", "properties": ["Two-Handed"], "range": "Melee 5 ft"},
    "handaxe": {"damage_dice": "1d6", "damage_type": "slashing", "properties": ["Light", "Thrown"], "range": "20/60 ft"},
    "javelin": {"damage_dice": "1d6", "damage_type": "piercing", "properties": ["Thrown"], "range": "30/120 ft"},
    "light hammer": {"damage_dice": "1d4", "damage_type": "bludgeoning", "properties": ["Light", "Thrown"], "range": "20/60 ft"},
    "mace": {"damage_dice": "1d6", "damage_type": "bludgeoning", "properties": [], "range": "Melee 5 ft"},
    "quarterstaff": {"damage_dice": "1d6", "damage_type": "bludgeoning", "versatile_damage": "1d8", "properties": ["Versatile"], "range": "Melee 5 ft"},
    "sickle": {"damage_dice": "1d4", "damage_type": "slashing", "properties": ["Light"], "range": "Melee 5 ft"},
    "spear": {"damage_dice": "1d6", "damage_type": "piercing", "versatile_damage": "1d8", "properties": ["Thrown", "Versatile"], "range": "20/60 ft"},
    "light crossbow": {"damage_dice": "1d8", "damage_type": "piercing", "properties": ["Ammunition", "Loading", "Two-Handed"], "range": "80/320 ft"},
    "shortbow": {"damage_dice": "1d6", "damage_type": "piercing", "properties": ["Ammunition", "Two-Handed"], "range": "80/320 ft"},
    "sling": {"damage_dice": "1d4", "damage_type": "bludgeoning", "properties": ["Ammunition"], "range": "30/120 ft"},
    "battleaxe": {"damage_dice": "1d8", "damage_type": "slashing", "versatile_damage": "1d10", "properties": ["Versatile"], "range": "Melee 5 ft"},
    "flail": {"damage_dice": "1d8", "damage_type": "bludgeoning", "properties": [], "range": "Melee 5 ft"},
    "glaive": {"damage_dice": "1d10", "damage_type": "slashing", "properties": ["Heavy", "Reach", "Two-Handed"], "range": "Melee 10 ft"},
    "greataxe": {"damage_dice": "1d12", "damage_type": "slashing", "properties": ["Heavy", "Two-Handed"], "range": "Melee 5 ft"},
    "greatsword": {"damage_dice": "2d6", "damage_type": "slashing", "properties": ["Heavy", "Two-Handed"], "range": "Melee 5 ft"},
    "halberd": {"damage_dice": "1d10", "damage_type": "slashing", "properties": ["Heavy", "Reach", "Two-Handed"], "range": "Melee 10 ft"},
    "lance": {"damage_dice": "1d12", "damage_type": "piercing", "properties": ["Reach", "Special"], "range": "Melee 10 ft"},
    "longsword": {"damage_dice": "1d8", "damage_type": "slashing", "versatile_damage": "1d10", "properties": ["Versatile"], "range": "Melee 5 ft"},
    "maul": {"damage_dice": "2d6", "damage_type": "bludgeoning", "properties": ["Heavy", "Two-Handed"], "range": "Melee 5 ft"},
    "morningstar": {"damage_dice": "1d8", "damage_type": "piercing", "properties": [], "range": "Melee 5 ft"},
    "pike": {"damage_dice": "1d10", "damage_type": "piercing", "properties": ["Heavy", "Reach", "Two-Handed"], "range": "Melee 10 ft"},
    "rapier": {"damage_dice": "1d8", "damage_type": "piercing", "properties": ["Finesse"], "range": "Melee 5 ft"},
    "scimitar": {"damage_dice": "1d6", "damage_type": "slashing", "properties": ["Finesse", "Light"], "range": "Melee 5 ft"},
    "shortsword": {"damage_dice": "1d6", "damage_type": "piercing", "properties": ["Finesse", "Light"], "range": "Melee 5 ft"},
    "trident": {"damage_dice": "1d6", "damage_type": "piercing", "versatile_damage": "1d8", "properties": ["Thrown", "Versatile"], "range": "20/60 ft"},
    "war pick": {"damage_dice": "1d8", "damage_type": "piercing", "properties": [], "range": "Melee 5 ft"},
    "warhammer": {"damage_dice": "1d8", "damage_type": "bludgeoning", "versatile_damage": "1d10", "properties": ["Versatile"], "range": "Melee 5 ft"},
    "whip": {"damage_dice": "1d4", "damage_type": "slashing", "properties": ["Finesse", "Reach"], "range": "Melee 10 ft"},
    "blowgun": {"damage_dice": "1", "damage_type": "piercing", "properties": ["Ammunition", "Loading"], "range": "25/100 ft"},
    "hand crossbow": {"damage_dice": "1d6", "damage_type": "piercing", "properties": ["Ammunition", "Light", "Loading"], "range": "30/120 ft"},
    "heavy crossbow": {"damage_dice": "1d10", "damage_type": "piercing", "properties": ["Ammunition", "Heavy", "Loading", "Two-Handed"], "range": "100/400 ft"},
    "longbow": {"damage_dice": "1d8", "damage_type": "piercing", "properties": ["Ammunition", "Heavy", "Two-Handed"], "range": "150/600 ft"},
}

_KNOWN_FEATS: set[str] = {
    "alert",
    "athlete",
    "dual wielder",
    "great weapon master",
    "healer",
    "lucky",
    "magic initiate",
    "mobile",
    "observant",
    "resilient",
    "sharpshooter",
    "tough",
    "war caster",
}


def _safe_str(value: Any, fallback: str = "", *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return text[:limit]


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _parse_coin_text(value: str) -> dict[str, int]:
    coins = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
    text = str(value or "").strip().lower()
    if not text:
        return coins

    for match in re.finditer(r"(\d+)\s*(cp|sp|ep|gp|pp)", text):
        amount = _safe_int(match.group(1), 0, minimum=0)
        kind = match.group(2)
        coins[kind] = amount
    return coins


def _extract_ddb_character(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    if isinstance(data, dict):
        return data
    return raw


def _make_warning(
    *,
    code: str,
    message: str,
    blocking: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "blocking": bool(blocking),
        "severity": "required" if blocking else "warning",
        "details": copy.deepcopy(details or {}),
    }



def _slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _strip_html(value: Any, *, limit: int = 1200) -> str:
    text = str(value or "").replace("\r", " ").strip()
    if not text:
        return ""
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.I)
    text = re.sub(r"</\s*p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:limit]


def _clean_item_name(value: Any) -> str:
    name = _safe_str(value, "", limit=120)
    name = re.sub(r"\s*[×x]\s*\d+$", "", name).strip()
    name = re.sub(r"\s*\(\d+\)$", "", name).strip()
    return name


def _lookup_common_weapon(name: Any) -> dict[str, Any]:
    clean = _clean_item_name(name).lower()
    clean = re.sub(r"^\+\d+\s+", "", clean).strip()
    clean = re.sub(r"\s*,\s*\+\d+$", "", clean).strip()
    clean = re.sub(r"\b(masterwork|silvered|adamantine)\b", "", clean).strip()
    clean = re.sub(r"\s+", " ", clean)
    if clean in _COMMON_WEAPON_STATS:
        return copy.deepcopy(_COMMON_WEAPON_STATS[clean])
    for key, stats in _COMMON_WEAPON_STATS.items():
        if clean.endswith(key) or key in clean:
            return copy.deepcopy(stats)
    return {}


def _lookup_common_armor(name: Any) -> dict[str, Any]:
    clean = _clean_item_name(name).lower()
    clean = re.sub(r"^\+\d+\s+", "", clean).strip()
    clean = clean.replace(" armor", "").strip()
    if clean in _COMMON_ARMOR_STATS:
        return copy.deepcopy(_COMMON_ARMOR_STATS[clean])
    for key, stats in _COMMON_ARMOR_STATS.items():
        if clean.endswith(key) or key in clean:
            return copy.deepcopy(stats)
    return {}


def _definition_from_ddb_row(row: dict[str, Any]) -> dict[str, Any]:
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
    if not definition and isinstance(row.get("item"), dict):
        definition = row.get("item") or {}
    return definition


def _damage_dice_from_definition(definition: dict[str, Any]) -> str:
    damage = definition.get("damage") if isinstance(definition.get("damage"), dict) else {}
    dice = damage.get("dice") if isinstance(damage.get("dice"), dict) else {}
    candidates = (
        definition.get("damageDice"),
        definition.get("damageDiceString"),
        damage.get("diceString"),
        dice.get("diceString"),
    )
    for value in candidates:
        text = _safe_str(value, "", limit=24)
        if text:
            return text
    dice_count = _safe_int(dice.get("diceCount") or damage.get("diceCount"), 0, minimum=0)
    dice_value = _safe_int(dice.get("diceValue") or damage.get("diceValue"), 0, minimum=0)
    if dice_count and dice_value:
        return f"{dice_count}d{dice_value}"
    fixed = _safe_int(damage.get("fixedValue"), 0, minimum=0)
    return str(fixed) if fixed else ""


def _damage_type_from_definition(definition: dict[str, Any]) -> str:
    damage_type = definition.get("damageType")
    if isinstance(damage_type, dict):
        return _safe_str(damage_type.get("name"), "", limit=40).lower()
    damage = definition.get("damage") if isinstance(definition.get("damage"), dict) else {}
    damage_type = damage.get("damageType")
    if isinstance(damage_type, dict):
        return _safe_str(damage_type.get("name"), "", limit=40).lower()
    return _safe_str(definition.get("damageTypeName") or damage.get("damageType"), "", limit=40).lower()


def _properties_from_definition(definition: dict[str, Any]) -> list[str]:
    raw_props = definition.get("properties") if isinstance(definition.get("properties"), list) else []
    out: list[str] = []
    for prop in raw_props:
        if isinstance(prop, dict):
            name = _safe_str(prop.get("name") or prop.get("description"), "", limit=40)
        else:
            name = _safe_str(prop, "", limit=40)
        if name and name not in out:
            out.append(name)
    return out[:12]


def _range_from_definition(definition: dict[str, Any], properties: list[str]) -> str:
    long_range = _safe_int(definition.get("longRange"), 0, minimum=0)
    normal_range = _safe_int(definition.get("range"), 0, minimum=0)
    if normal_range and long_range:
        return f"{normal_range}/{long_range} ft"
    if normal_range:
        if any(str(prop).lower() == "reach" for prop in properties):
            return f"Melee {normal_range} ft"
        return f"{normal_range} ft"
    if any(str(prop).lower() == "reach" for prop in properties):
        return "Melee 10 ft"
    return ""


def _normalize_ddb_inventory_row(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    definition = _definition_from_ddb_row(row)
    name = _safe_str(definition.get("name") or row.get("name"), "", limit=120)
    if not name:
        return None
    qty = _safe_int(row.get("quantity") or row.get("qty"), 1, minimum=1)
    filter_type = _safe_str(definition.get("filterType") or definition.get("type") or row.get("filterType"), "", limit=60).lower()
    type_name = _safe_str(definition.get("type") or row.get("type"), "", limit=60).lower()
    category = _safe_str(definition.get("category") or definition.get("subType") or row.get("category"), "", limit=80)
    properties = _properties_from_definition(definition)
    damage_dice = _damage_dice_from_definition(definition)
    damage_type = _damage_type_from_definition(definition)

    kind = "gear"
    if "weapon" in filter_type or "weapon" in type_name or damage_dice:
        kind = "weapon"
    elif "shield" in name.lower():
        kind = "shield"
    elif "armor" in filter_type or "armour" in filter_type or "armor" in type_name or definition.get("armorClass"):
        kind = "armor"
    elif "potion" in filter_type or "potion" in type_name or "potion" in name.lower():
        kind = "potion"
    elif "scroll" in filter_type or "scroll" in type_name or "spell scroll" in name.lower():
        kind = "scroll"

    out: dict[str, Any] = {
        "id": _safe_str(row.get("id") or definition.get("id"), _slugify(name), limit=80),
        "name": name,
        "qty": qty,
        "kind": kind,
        "type": kind,
        "item_type": kind,
        "equipment_kind": kind,
        "category": category or filter_type.title(),
        "source": "D&D Beyond import",
        "equipped": bool(row.get("equipped")),
        "notes": _strip_html(definition.get("description") or definition.get("snippet"), limit=700),
    }
    if row.get("isAttuned") is not None:
        out["attuned"] = bool(row.get("isAttuned"))
    if definition.get("canAttune") is not None or definition.get("requiresAttunement") is not None:
        out["attunement_required"] = bool(definition.get("canAttune") or definition.get("requiresAttunement"))
    weight = definition.get("weight")
    if weight is not None and str(weight).strip() != "":
        try:
            out["weight_lbs"] = float(weight)
        except Exception:
            pass
    price = definition.get("cost") or definition.get("price")
    if isinstance(price, dict):
        out["price"] = _safe_str(price.get("quantity") or price.get("value"), "", limit=40)
    elif price is not None:
        out["price"] = _safe_str(price, "", limit=80)

    if kind == "weapon":
        common = _lookup_common_weapon(name)
        out.update({k: v for k, v in common.items() if v not in (None, "", [])})
        if damage_dice:
            out["damage_dice"] = damage_dice
            out["damage"] = damage_dice
        if damage_type:
            out["damage_type"] = damage_type
        if properties:
            out["properties"] = properties
            out["weapon_properties"] = properties
        if _range_from_definition(definition, properties):
            out["range"] = _range_from_definition(definition, properties)
        if bool(row.get("equipped")):
            out["equip_slot"] = "main_hand"
    elif kind == "shield":
        out["ac_bonus"] = _safe_int(definition.get("armorClass"), 2, minimum=0) or 2
        out["equip_slot"] = "off_hand" if bool(row.get("equipped")) else ""
    elif kind == "armor":
        common = _lookup_common_armor(name)
        out.update({k: v for k, v in common.items() if v not in (None, "", [])})
        base_ac = _safe_int(definition.get("armorClass"), 0, minimum=0)
        if base_ac:
            out["base_ac"] = base_ac
        armor_type = _safe_str(definition.get("armorType") or definition.get("armorTypeName"), "", limit=40).lower()
        if armor_type:
            out["armor_type"] = armor_type
        if bool(row.get("equipped")):
            out["equip_slot"] = "armor"
    return out


def _normalize_ddb_inventory(ddb: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    inventory_rows = ddb.get("inventory") if isinstance(ddb.get("inventory"), list) else []
    inventory = [item for item in (_normalize_ddb_inventory_row(row) for row in inventory_rows) if item]
    if inventory and not any(row.get("equipped") and row.get("equipment_kind") == "weapon" for row in inventory):
        for item in inventory:
            if item.get("equipment_kind") == "weapon":
                item["equipped"] = True
                item.setdefault("equip_slot", "main_hand")
                break
    equipped: dict[str, dict[str, Any]] = {}
    for item in inventory:
        if not item.get("equipped"):
            continue
        slot = _safe_str(item.get("equip_slot"), "", limit=40)
        if not slot:
            kind = _safe_str(item.get("equipment_kind"), "", limit=40)
            slot = "main_hand" if kind == "weapon" else "off_hand" if kind == "shield" else "armor" if kind == "armor" else ""
        if slot:
            equipped[slot] = copy.deepcopy(item)
            equipped[slot]["equip_slot"] = slot
            equipped[slot]["equipped"] = True
    return inventory, equipped


def _normalize_ddb_activation(row: dict[str, Any]) -> str:
    activation = row.get("activation") if isinstance(row.get("activation"), dict) else {}
    raw = row.get("actionType") or row.get("activationType") or activation.get("activationType") or activation.get("type")
    if isinstance(raw, dict):
        text = _safe_str(raw.get("name") or raw.get("type"), "", limit=40).lower()
    elif isinstance(raw, int):
        text = _DDB_ACTION_TYPE_MAP.get(raw, "action")
    else:
        text = _safe_str(raw, "", limit=40).lower()
    if not text:
        raw_id = _safe_int(row.get("actionTypeId") or activation.get("activationTypeId"), 0, minimum=0)
        text = _DDB_ACTION_TYPE_MAP.get(raw_id, "action") if raw_id else "action"
    if "bonus" in text:
        return "bonus action"
    if "reaction" in text:
        return "reaction"
    if text in {"none", "no action", "special", "minute", "hour"}:
        return text
    return "action"


def _normalize_ddb_action_row(row: Any, *, source: str) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else row
    name = _safe_str(definition.get("name") or row.get("name") or definition.get("displayAs"), "", limit=120)
    if not name:
        return None
    action_type = _normalize_ddb_activation({**definition, **row})
    summary = _strip_html(definition.get("snippet") or row.get("snippet") or definition.get("summary"), limit=360)
    description = _strip_html(definition.get("description") or row.get("description") or summary, limit=1400)
    limited = row.get("limitedUse") if isinstance(row.get("limitedUse"), dict) else definition.get("limitedUse") if isinstance(definition.get("limitedUse"), dict) else {}
    uses = _safe_int(limited.get("maxUses") or limited.get("numberUsed") or row.get("uses"), 0, minimum=0)
    damage = _damage_dice_from_definition(definition)
    damage_type = _damage_type_from_definition(definition)
    recovery = _safe_str(limited.get("resetTypeDescription") or limited.get("resetType"), "", limit=80)
    activation_text = _safe_str(row.get("activationTime") or definition.get("activationTime") or action_type, "", limit=80)
    out: dict[str, Any] = {
        "id": f"ddb-{source}-{_slugify(name)}",
        "name": name,
        "displayName": name,
        "actionType": action_type,
        "type": action_type,
        "classification": "imported",
        "sourceType": source if source in {"class", "item", "feat", "background", "species", "subclass"} else "imported",
        "source": f"D&D Beyond {source}",
        "summary": summary or description[:240],
        "description": description or summary,
        "tags": ["dndbeyond", source],
        "trackUses": bool(limited),
        "limitedUse": copy.deepcopy(limited),
        "numberUsed": _safe_int(limited.get("numberUsed"), 0, minimum=0) if limited else 0,
        "recovery": recovery,
        "activationText": activation_text,
        "needsReview": True,
        "matchedNative": False,
    }
    if uses:
        out["uses"] = uses
        out["maxUses"] = uses
    if damage:
        out["damage"] = {"formula": damage, "type": damage_type}
        out["damageFormula"] = damage
        out["damageType"] = damage_type
    save_ability = definition.get("saveAbility") if isinstance(definition.get("saveAbility"), dict) else {}
    save_name = _safe_str(save_ability.get("name") or definition.get("saveAbility"), "", limit=40).lower()
    if save_name:
        out["save"] = _DDB_ABILITY_NAME_MAP.get(save_name, save_name)
    range_text = _range_from_definition(definition, _properties_from_definition(definition))
    if range_text:
        out["range"] = range_text
    return out


def _iter_ddb_action_candidates(ddb: dict[str, Any]) -> list[tuple[Any, str]]:
    rows: list[tuple[Any, str]] = []
    actions = ddb.get("actions") if isinstance(ddb.get("actions"), dict) else {}
    for key, bucket in actions.items():
        if isinstance(bucket, list):
            rows.extend((row, str(key or "action")) for row in bucket)
    for key in ("customActions", "characterActions", "actions"):
        bucket = ddb.get(key)
        if isinstance(bucket, list):
            rows.extend((row, str(key)) for row in bucket)
    return rows


def _normalize_ddb_actions(ddb: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row, source in _iter_ddb_action_candidates(ddb):
        action = _normalize_ddb_action_row(row, source=source)
        if not action:
            continue
        key = f"{action.get('name', '').lower()}::{action.get('actionType', '')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(action)
    return out[:80]


def _normalize_ddb_feature_row(row: Any, *, source: str, level: int = 0) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else row
    name = _safe_str(definition.get("name") or row.get("name"), "", limit=120)
    if not name:
        return None
    description = _strip_html(definition.get("description") or row.get("description") or definition.get("snippet"), limit=1600)
    feature_type = _normalize_ddb_activation({**definition, **row}) if (definition.get("activation") or row.get("activation") or definition.get("actionType") or row.get("actionType")) else "passive"
    limited = row.get("limitedUse") if isinstance(row.get("limitedUse"), dict) else definition.get("limitedUse") if isinstance(definition.get("limitedUse"), dict) else {}
    recovery = _safe_str(limited.get("resetTypeDescription") or limited.get("resetType"), "", limit=80)
    uses = _safe_int(limited.get("maxUses") or row.get("uses"), 0, minimum=0)
    return {
        "id": f"ddb-{source}-{_slugify(name)}",
        "name": name,
        "displayName": name,
        "section": source.title(),
        "type": feature_type,
        "actionType": feature_type,
        "sourceType": source,
        "source": f"D&D Beyond {source}",
        "minLevel": _safe_int(row.get("requiredLevel") or definition.get("requiredLevel") or level, 0, minimum=0),
        "summary": _strip_html(definition.get("snippet") or row.get("snippet") or description, limit=360),
        "description": description,
        "tags": ["dndbeyond", source],
        "kind": source,
        "usage": f"{uses} use{'s' if uses != 1 else ''}" if uses else "",
        "limitedUse": copy.deepcopy(limited),
        "numberUsed": _safe_int(limited.get("numberUsed"), 0, minimum=0) if limited else 0,
        "maxUses": uses or None,
        "recovery": recovery,
        "activationText": feature_type if feature_type != "passive" else "",
        "needsReview": True,
        "matchedNative": False,
    }


def _normalize_ddb_features(ddb: dict[str, Any], classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: Any, source: str, level: int = 0) -> None:
        feature = _normalize_ddb_feature_row(row, source=source, level=level)
        if not feature:
            return
        key = str(feature.get("name") or "").strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        out.append(feature)

    for row in ddb.get("classFeatures") if isinstance(ddb.get("classFeatures"), list) else []:
        add(row, "class")
    for class_row in ddb.get("classes") if isinstance(ddb.get("classes"), list) else []:
        if not isinstance(class_row, dict):
            continue
        level = _safe_int(class_row.get("level"), 0, minimum=0)
        for row in class_row.get("classFeatures") if isinstance(class_row.get("classFeatures"), list) else []:
            add(row, "class", level)
        for row in class_row.get("features") if isinstance(class_row.get("features"), list) else []:
            add(row, "class", level)
        subclass = class_row.get("subclassDefinition") if isinstance(class_row.get("subclassDefinition"), dict) else {}
        for row in subclass.get("classFeatures") if isinstance(subclass.get("classFeatures"), list) else []:
            add(row, "subclass", level)
        for row in subclass.get("features") if isinstance(subclass.get("features"), list) else []:
            add(row, "subclass", level)
    for row in ddb.get("racialTraits") if isinstance(ddb.get("racialTraits"), list) else []:
        add(row, "species")
    race = ddb.get("race") if isinstance(ddb.get("race"), dict) else {}
    for row in race.get("racialTraits") if isinstance(race.get("racialTraits"), list) else []:
        add(row, "species")
    for row in ddb.get("feats") if isinstance(ddb.get("feats"), list) else []:
        add(row, "feat")
    background = ddb.get("background") if isinstance(ddb.get("background"), dict) else {}
    background_def = background.get("definition") if isinstance(background.get("definition"), dict) else background
    feature_name = _safe_str(background_def.get("featureName") or background_def.get("featureTitle"), "", limit=120)
    feature_desc = _strip_html(background_def.get("featureDescription") or background_def.get("featureSummary"), limit=1600)
    if feature_name or feature_desc:
        add({"definition": {"name": feature_name or "Background Feature", "description": feature_desc}}, "background")
    return out[:120]




def _copy_imported_spell_fields(target: dict[str, Any], row: dict[str, Any], definition: dict[str, Any]) -> dict[str, Any]:
    source = {}
    source.update(definition if isinstance(definition, dict) else {})
    source.update(row if isinstance(row, dict) else {})
    direct_keys = {
        "spellId": ("spellId", "spell_id"),
        "level": ("level", "spellLevel"),
        "school": ("school",),
        "castingTime": ("castingTime", "casting_time", "castTime", "time"),
        "range": ("range",),
        "components": ("components",),
        "duration": ("duration",),
        "attackType": ("attackType", "attack_type"),
        "saveAbility": ("saveAbility", "save_ability", "savingThrow", "save"),
        "damageFormula": ("damageFormula", "damage_formula", "damageDice", "damage_dice", "damage"),
        "healingFormula": ("healingFormula", "healing_formula", "healing", "heal"),
        "damageType": ("damageType", "damage_type"),
        "notes": ("notes", "description", "summary", "snippet"),
    }
    for out_key, candidates in direct_keys.items():
        for key in candidates:
            if source.get(key) not in (None, ""):
                value = source.get(key)
                if out_key == "notes":
                    value = _strip_html(value, limit=1200)
                elif isinstance(value, str):
                    value = _safe_str(value, "", limit=700 if out_key in {"notes"} else 160)
                target[out_key] = value
                break
    for out_key, candidates in {
        "concentration": ("concentration", "isConcentration"),
        "ritual": ("ritual", "isRitual"),
        "known": ("known", "isKnown"),
    }.items():
        for key in candidates:
            if key in source:
                target[out_key] = bool(source.get(key))
                break
    return target

def _normalize_ddb_spell_entry(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else row
    name = _safe_str(definition.get("name") or row.get("name"), "", limit=120)
    if not name:
        return None
    spell = get_spell_by_id(name)
    spell_id = _safe_str((spell or {}).get("id"), _slugify(name), limit=120)
    prepared = bool(row.get("prepared") or row.get("alwaysPrepared") or row.get("isPrepared"))
    entry = {
        "id": spell_id,
        "spellId": _safe_str(definition.get("id") or row.get("spellId") or spell_id, spell_id, limit=120),
        "name": _safe_str((spell or {}).get("name"), name, limit=120),
        "prepared": prepared,
        "source": "D&D Beyond import",
        "matchedNative": bool(spell),
    }
    return _copy_imported_spell_fields(entry, row, definition)


def _normalize_ddb_spell_state(ddb: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    spell_rows = ddb.get("spells") if isinstance(ddb.get("spells"), dict) else {}
    entries: list[dict[str, Any]] = []
    missing = 0
    for bucket in spell_rows.values():
        if not isinstance(bucket, list):
            continue
        for row in bucket:
            entry = _normalize_ddb_spell_entry(row)
            if entry:
                entries.append(entry)
                if not entry.get("matchedNative"):
                    missing += 1
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for entry in entries:
        spell_id = str(entry.get("id") or "").strip()
        if not spell_id or spell_id in seen:
            continue
        seen.add(spell_id)
        deduped.append(entry)
    known = [entry["id"] for entry in deduped]
    prepared = [entry["id"] for entry in deduped if entry.get("prepared")]
    return {
        "known": known,
        "prepared": prepared,
        "slots": {},
        "focus": {},
        "rituals": [],
        "spellbookEntries": deduped,
        "classSources": [],
    }, deduped, missing

def _normalize_resolution_payload(src: dict[str, Any]) -> dict[str, str]:
    resolution = src.get("import_resolution")
    if not isinstance(resolution, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in resolution.items():
        if value is None:
            continue
        normalized[str(key).strip().lower()] = _safe_str(value, "", limit=80)
    return normalized


def normalize_ddb_json_payload(raw_payload: Any, *, external_id: str = "") -> dict[str, Any]:
    src = raw_payload if isinstance(raw_payload, dict) else {}
    ddb = _extract_ddb_character(src)
    warnings: list[dict[str, Any]] = []
    resolution = _normalize_resolution_payload(src)

    stats_rows = ddb.get("stats") if isinstance(ddb.get("stats"), list) else []
    bonus_rows = ddb.get("bonusStats") if isinstance(ddb.get("bonusStats"), list) else []
    override_rows = ddb.get("overrideStats") if isinstance(ddb.get("overrideStats"), list) else []

    base_scores: dict[int, int] = {}
    bonus_scores: dict[int, int] = {}
    override_scores: dict[int, int] = {}

    for row in stats_rows:
        if not isinstance(row, dict):
            continue
        ability_id = _safe_int(row.get("id"), 0)
        if ability_id:
            base_scores[ability_id] = _safe_int(row.get("value"), 10)

    for row in bonus_rows:
        if not isinstance(row, dict):
            continue
        ability_id = _safe_int(row.get("id"), 0)
        if ability_id:
            bonus_scores[ability_id] = _safe_int(row.get("value"), 0)

    for row in override_rows:
        if not isinstance(row, dict):
            continue
        ability_id = _safe_int(row.get("id"), 0)
        value = row.get("value")
        if ability_id and value is not None:
            override_scores[ability_id] = _safe_int(value, 10)

    ability_scores = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}
    for ability_id, key in _DDB_ABILITY_MAP.items():
        if ability_id in override_scores:
            ability_scores[key] = override_scores[ability_id]
        else:
            ability_scores[key] = base_scores.get(ability_id, 10) + bonus_scores.get(ability_id, 0)

    class_rows = ddb.get("classes") if isinstance(ddb.get("classes"), list) else []
    classes: list[dict[str, Any]] = []
    for row in class_rows:
        if not isinstance(row, dict):
            continue
        definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
        subclass_def = row.get("subclassDefinition") if isinstance(row.get("subclassDefinition"), dict) else {}
        class_name = _safe_str(definition.get("name"), "")
        level = _safe_int(row.get("level"), 1, minimum=1)
        if not class_name:
            continue
        class_entry = {
            "name": class_name,
            "classId": class_name.lower().replace(" ", "-"),
            "level": level,
        }
        subclass_name = _safe_str(subclass_def.get("name"), "")
        if subclass_name:
            class_entry["subclass"] = subclass_name
            known_subclasses = _KNOWN_SUBCLASS_BY_CLASS.get(class_entry["classId"], set())
            if known_subclasses and subclass_name.strip().lower() not in known_subclasses:
                warnings.append(
                    _make_warning(
                        code="unsupported_subclass",
                        message=f'Subclass "{subclass_name}" for class "{class_name}" is not fully mapped yet.',
                        blocking=False,
                        details={
                            "classId": class_entry["classId"],
                            "className": class_name,
                            "subclass": subclass_name,
                        },
                    )
                )
        classes.append(class_entry)

    if not classes:
        warnings.append(
            _make_warning(
                code="unsupported_subclass",
                message="No class levels were found in the import; defaulted to Adventurer level 1.",
                blocking=False,
            )
        )
        classes = [{"name": "Adventurer", "classId": "adventurer", "level": 1}]

    race = ddb.get("race") if isinstance(ddb.get("race"), dict) else {}
    background = ddb.get("background") if isinstance(ddb.get("background"), dict) else {}

    total_level = sum(_safe_int(cls.get("level"), 1, minimum=1) for cls in classes)
    if total_level <= 0:
        total_level = 1

    name = _safe_str(ddb.get("name"), "Unnamed Character", limit=120)
    if not _safe_str(ddb.get("name")):
        warnings.append(
            _make_warning(
                code="ambiguous_species",
                message="Character name was missing in import payload; using a fallback name.",
                blocking=False,
            )
        )

    character_id = _safe_str(ddb.get("id"), external_id, limit=120)
    if not character_id:
        character_id = f"ddb-{int(time.time())}"

    source_meta = {
        "origin": "dndbeyond",
        "source": "dndbeyond",
        "sourceType": "dndbeyond",
        "externalId": character_id,
        "importedAt": time.time(),
        "rawVersion": _safe_str(ddb.get("version") or ddb.get("dateModified") or "", limit=80),
        "rawSnapshot": copy.deepcopy(src),
        "mappingNotes": [],
    }

    speed = 30
    try:
        speed = _safe_int(((race.get("weightSpeeds") or {}).get("normal") or {}).get("walk"), 30, minimum=0)
    except Exception:
        speed = 30

    imported_inventory, imported_equipped = _normalize_ddb_inventory(ddb)
    imported_actions = _normalize_ddb_actions(ddb)
    imported_features = _normalize_ddb_features(ddb, classes)
    imported_spell_state, imported_spell_entries, unmatched_spell_count = _normalize_ddb_spell_state(ddb)
    species_traits = [
        copy.deepcopy(row)
        for row in imported_features
        if isinstance(row, dict) and row.get("kind") == "species"
    ]

    document = {
        "schemaVersion": 1,
        "rulesMode": "casual",
        "ruleset": "casual-dnd-5e-compatible",
        "sourceMode": "dndbeyond",
        "identity": {
            "characterId": character_id,
            "name": name,
            "displayName": name,
            "portraitUrl": _safe_str((ddb.get("decorations") or {}).get("avatarUrl"), "", limit=400),
            "alignment": _safe_str(ddb.get("alignmentName"), "", limit=60),
        },
        "species": {
            "id": _safe_str(race.get("baseName") or race.get("fullName"), "", limit=80).lower().replace(" ", "-"),
            "name": _safe_str(race.get("fullName") or race.get("baseName"), "", limit=80),
            "size": "medium",
            "speed": speed,
            "traits": species_traits,
        },
        "background": {
            "id": _safe_str((background.get("definition") or {}).get("name") or background.get("name"), "", limit=80).lower().replace(" ", "-"),
            "name": _safe_str((background.get("definition") or {}).get("name") or background.get("name"), "", limit=80),
        },
        "abilities": {
            "generationMode": "imported",
            "scores": ability_scores,
        },
        "classes": classes,
        "awakening": {
            "stage": 0,
            "pathId": "",
            "nodes": [],
            "flags": {},
        },
        "equipment": {
            "currency": {
                "cp": _safe_int(ddb.get("currencies", {}).get("cp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "sp": _safe_int(ddb.get("currencies", {}).get("sp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "ep": _safe_int(ddb.get("currencies", {}).get("ep"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "gp": _safe_int(ddb.get("currencies", {}).get("gp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "pp": _safe_int(ddb.get("currencies", {}).get("pp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
            },
            "inventory": imported_inventory,
            "equipped": imported_equipped,
            "containers": [],
        },
        "spellState": imported_spell_state,
        "importMeta": source_meta,
    }

    species_base = _safe_str(race.get("baseName"), "", limit=80)
    species_name = document["species"]["name"]
    if not species_name:
        resolved_species = _safe_str(resolution.get("species"), "", limit=80)
        if resolved_species:
            document["species"]["name"] = resolved_species
            document["species"]["id"] = resolved_species.lower().replace(" ", "-")
        else:
            warnings.append(
                _make_warning(
                    code="ambiguous_species",
                    message="Species/Race was not found in this import and must be selected before final save.",
                    blocking=True,
                    details={"resolutionKey": "species"},
                )
            )
    elif species_base and species_base.lower() in _SPECIES_ALIAS_MAP and not resolution.get("species"):
        warnings.append(
            _make_warning(
                code="ambiguous_species",
                message=f'Species "{species_base}" has multiple native mappings. Choose a species mapping to continue.',
                blocking=True,
                details={
                    "resolutionKey": "species",
                    "options": list(_SPECIES_ALIAS_MAP.get(species_base.lower()) or []),
                },
            )
        )
    elif resolution.get("species"):
        resolved_species = _safe_str(resolution.get("species"), species_name, limit=80)
        document["species"]["name"] = resolved_species
        document["species"]["id"] = resolved_species.lower().replace(" ", "-")

    if not document["background"]["name"]:
        warnings.append(
            _make_warning(
                code="unknown_feat",
                message="Background was not found in this import.",
                blocking=False,
            )
        )
    if total_level <= 0:
        warnings.append(
            _make_warning(
                code="unsupported_subclass",
                message="Character level could not be inferred; defaulted to level 1.",
                blocking=False,
            )
        )

    spell_rows = ddb.get("spells") if isinstance(ddb.get("spells"), dict) else {}
    missing_spell_names = 0
    for bucket in spell_rows.values():
        if not isinstance(bucket, list):
            continue
        for row in bucket:
            if not isinstance(row, dict):
                continue
            definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
            if not _safe_str(definition.get("name") or row.get("name"), ""):
                missing_spell_names += 1
    if missing_spell_names or unmatched_spell_count:
        warnings.append(
            _make_warning(
                code="missing_spell_mapping",
                message=(
                    f"{missing_spell_names} imported spell rows had no name; "
                    f"{unmatched_spell_count} named spells were preserved but did not exactly match the native spell compendium."
                ),
                blocking=False,
                details={"missingNameCount": missing_spell_names, "unmatchedNameCount": unmatched_spell_count},
            )
        )

    feat_rows = ddb.get("feats") if isinstance(ddb.get("feats"), list) else []
    imported_feats: list[dict[str, Any]] = []
    for feat_row in feat_rows:
        if not isinstance(feat_row, dict):
            continue
        definition = feat_row.get("definition") if isinstance(feat_row.get("definition"), dict) else feat_row
        feat_name = _safe_str(definition.get("name"), "", limit=120)
        if not feat_name:
            continue
        imported_feats.append({
            "featId": _slugify(feat_name),
            "name": feat_name,
            "source": "D&D Beyond import",
            "description": _strip_html(definition.get("description") or definition.get("snippet"), limit=1200),
        })
        if feat_name.lower() not in _KNOWN_FEATS:
            warnings.append(
                _make_warning(
                    code="unknown_feat",
                    message=f'Feat "{feat_name}" is not in the native feat map yet and was preserved as import metadata only.',
                    blocking=False,
                    details={"feat": feat_name},
                )
            )
    if imported_feats:
        document["feats"] = imported_feats

    source_meta["nativeImportMode"] = "ddb_import"
    source_meta["resolution"] = resolution
    source_meta["importedActions"] = imported_actions
    source_meta["importedFeatures"] = imported_features
    source_meta["importedSpells"] = imported_spell_entries
    source_meta["importedInventoryCount"] = len(imported_inventory)
    source_meta["mappingNotes"] = [
        f"Imported {len(imported_inventory)} inventory item(s) from D&D Beyond.",
        f"Imported {len(imported_actions)} action card(s) from D&D Beyond.",
        f"Imported {len(imported_features)} feature/trait row(s) from D&D Beyond.",
        f"Imported {len(imported_spell_entries)} spell row(s) from D&D Beyond.",
    ]
    source_meta["warnings"] = copy.deepcopy(warnings)

    canonical = validate_or_raise(document)
    required = [item for item in warnings if item.get("blocking")]
    return {
        "document": canonical,
        "warnings": warnings,
        "requires_resolution": bool(required),
        "required_choices": required,
    }


_PDF_SKILL_ABILITY = {
    "acrobatics": "dex",
    "animal handling": "wis",
    "arcana": "int",
    "athletics": "str",
    "deception": "cha",
    "history": "int",
    "insight": "wis",
    "intimidation": "cha",
    "investigation": "int",
    "medicine": "wis",
    "nature": "int",
    "perception": "wis",
    "performance": "cha",
    "persuasion": "cha",
    "religion": "int",
    "sleight of hand": "dex",
    "stealth": "dex",
    "survival": "wis",
}

_ABILITY_LABEL_TO_KEY = {
    "strength": "str",
    "str": "str",
    "dexterity": "dex",
    "dex": "dex",
    "constitution": "con",
    "con": "con",
    "intelligence": "int",
    "int": "int",
    "wisdom": "wis",
    "wis": "wis",
    "charisma": "cha",
    "cha": "cha",
}


def _first_present(src: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in src and src.get(key) not in (None, ""):
            return src.get(key)
    return default


def _parse_signed_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"[-+]?\d+", str(value or ""))
    if not match:
        return fallback
    return _safe_int(match.group(0), fallback)


def _normalize_pdf_saving_throws(value: Any) -> dict[str, int]:
    rows = value if isinstance(value, dict) else {}
    out: dict[str, int] = {}
    for key, raw in rows.items():
        ability = _ABILITY_LABEL_TO_KEY.get(str(key or "").strip().lower())
        if ability:
            out[ability] = _parse_signed_int(raw, 0)
    return out


def _normalize_pdf_skills(src: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_skills = _first_present(src, "skills", "skillData", default={})
    raw_prof = src.get("profSkills") if isinstance(src.get("profSkills"), list) else []
    raw_half = src.get("halfSkills") if isinstance(src.get("halfSkills"), list) else []
    out: dict[str, dict[str, Any]] = {}
    if isinstance(raw_skills, dict):
        for name, value in raw_skills.items():
            label = _safe_str(name, "", limit=80)
            if not label:
                continue
            key = _slugify(label).replace("-", "_")
            out[key] = {
                "name": label,
                "ability": _PDF_SKILL_ABILITY.get(label.lower(), ""),
                "total": _parse_signed_int(value, 0),
                "raw": _safe_str(value, "", limit=40),
                "proficient": label in raw_prof,
                "halfProficient": label in raw_half,
                "source": "PDF import",
            }
    return out


def _split_pdf_text_lines(value: Any) -> list[str]:
    text = _strip_html(value, limit=5000)
    if not text:
        return []
    return [line.strip(" •\t-") for line in re.split(r"[\n;]+", text) if line.strip(" •\t-")]


def _parse_pdf_equipment_line(line: str) -> dict[str, Any] | None:
    original = _safe_str(line, "", limit=240)
    if not original or original.lower() in {"equipment", "attuned magic items"}:
        return None
    name_part = re.split(r"\s+[—-]\s+", original, maxsplit=1)[0].strip()
    qty = 1
    match = re.search(r"(?:[×x]\s*(\d+)|\((\d+)\)\s*$|^(\d+)\s+)", name_part)
    if match:
        qty = max(1, _safe_int(next((g for g in match.groups() if g), "1"), 1, minimum=1))
        if match.group(3):
            name_part = name_part[match.end(3):].strip()
        else:
            name_part = re.sub(r"\s*(?:[×x]\s*\d+|\(\d+\))\s*$", "", name_part).strip()
    name = _clean_item_name(name_part)
    if not name:
        return None
    row = {
        "id": f"pdf-item-{_slugify(name)}",
        "name": name,
        "qty": qty,
        "kind": "gear",
        "type": "gear",
        "item_type": "gear",
        "equipment_kind": "gear",
        "category": "PDF Equipment",
        "source": "PDF import",
        "equipped": False,
        "notes": original if original != name else "",
    }
    weapon = _lookup_common_weapon(name)
    armor = _lookup_common_armor(name)
    if weapon:
        row.update({k: v for k, v in weapon.items() if v not in (None, "", [])})
        row.update({"kind": "weapon", "type": "weapon", "item_type": "weapon", "equipment_kind": "weapon"})
    elif "shield" in name.lower():
        row.update({"kind": "shield", "type": "shield", "item_type": "shield", "equipment_kind": "shield", "ac_bonus": 2})
    elif armor:
        row.update({k: v for k, v in armor.items() if v not in (None, "", [])})
        row.update({"kind": "armor", "type": "armor", "item_type": "armor", "equipment_kind": "armor"})
    elif "potion" in name.lower():
        row.update({"kind": "potion", "type": "potion", "item_type": "potion", "equipment_kind": "potion"})
    return row


def _normalize_pdf_inventory(src: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_entries = _first_present(src, "inventoryEntries", "importedInventoryItems", "equipment", default=[])
    if isinstance(raw_entries, list):
        for idx, item in enumerate(raw_entries):
            if isinstance(item, dict):
                name = _safe_str(item.get("name"), "", limit=120)
                if not name:
                    continue
                row = _parse_pdf_equipment_line(f"{name} x{_safe_int(item.get('qty'), 1, minimum=1)}") or {}
                row.update({
                    "id": _safe_str(item.get("id"), row.get("id") or f"pdf-item-{idx+1}", limit=80),
                    "name": name,
                    "qty": _safe_int(item.get("qty"), row.get("qty") or 1, minimum=1),
                    "notes": _safe_str(item.get("notes"), row.get("notes") or "", limit=700),
                    "source": "PDF import",
                })
                rows.append(row)
            elif isinstance(item, str):
                parsed = _parse_pdf_equipment_line(item)
                if parsed:
                    rows.append(parsed)
    if not rows:
        for line in _split_pdf_text_lines(_first_present(src, "gearText", "equipmentText", default="") or (src.get("book") or {}).get("gear")):
            parsed = _parse_pdf_equipment_line(line)
            if parsed:
                rows.append(parsed)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = f"{str(row.get('name') or '').lower()}::{row.get('qty')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:200]


def _normalize_pdf_attack_row(row: Any, idx: int) -> dict[str, Any] | None:
    if isinstance(row, str):
        pieces = [part.strip() for part in re.split(r"\s+[—-]\s+", row) if part.strip()]
        row = {"name": pieces[0] if pieces else row, "notes": " — ".join(pieces[1:])}
    if not isinstance(row, dict):
        return None
    name = _safe_str(row.get("name") or row.get("weapon") or row.get("title"), "", limit=120)
    if not name:
        return None
    attack_raw = _safe_str(row.get("attack") or row.get("attackBonus") or row.get("toHit"), "", limit=40)
    damage_raw = _safe_str(row.get("damage") or row.get("damageDice") or row.get("damageFormula"), "", limit=120)
    notes = _strip_html(row.get("notes") or row.get("description"), limit=700)
    damage_formula = ""
    damage_type = ""
    match = re.search(r"(\d+d\d+(?:\s*[-+]\s*\d+)?)\s*([A-Za-z]+)?", damage_raw)
    if match:
        damage_formula = re.sub(r"\s+", "", match.group(1))
        damage_type = _safe_str(match.group(2), "", limit=40).lower()
    common = _lookup_common_weapon(name)
    if not damage_formula:
        damage_formula = _safe_str(common.get("damage_dice"), "", limit=40)
    if not damage_type:
        damage_type = _safe_str(common.get("damage_type"), "", limit=40)
    action = {
        "id": f"pdf-attack-{_slugify(name) or idx+1}",
        "name": name,
        "displayName": name,
        "actionType": "action",
        "classification": "attack",
        "attackBonus": _parse_signed_int(attack_raw, 0) if attack_raw else 0,
        "attackBonusRaw": attack_raw,
        "damage": {"formula": damage_formula or damage_raw, "type": damage_type},
        "summary": notes or damage_raw,
        "description": notes,
        "range": _safe_str(row.get("range") or common.get("range"), "", limit=80),
        "source": "PDF import",
        "tags": ["pdf", "imported", "attack"],
    }
    return action


def _normalize_pdf_attacks(src: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _first_present(src, "attacks", "attackEntries", default=[])
    if isinstance(rows, str):
        rows = _split_pdf_text_lines(rows)
    if not isinstance(rows, list):
        rows = []
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, row in enumerate(rows):
        action = _normalize_pdf_attack_row(row, idx)
        if not action:
            continue
        key = f"{action.get('name','').lower()}::{action.get('attackBonusRaw','')}::{(action.get('damage') or {}).get('formula','')}"
        if key in seen:
            continue
        seen.add(key)
        actions.append(action)
    return actions[:40]


def _normalize_pdf_spell_entries(src: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    raw_entries = _first_present(src, "spellbookEntries", "spells", "spellEntries", default=[])
    entries: list[dict[str, Any]] = []
    if isinstance(raw_entries, str):
        raw_entries = [{"name": line} for line in _split_pdf_text_lines(raw_entries)]
    if isinstance(raw_entries, list):
        for row in raw_entries:
            if isinstance(row, dict):
                name = _safe_str(row.get("name"), "", limit=120)
                section = _safe_str(row.get("section") or row.get("level"), "", limit=80)
                notes = _strip_html(row.get("notes") or row.get("description"), limit=700)
                prepared = bool(row.get("prepared") or row.get("isPrepared"))
            else:
                name = _safe_str(row, "", limit=120)
                section = ""
                notes = ""
                prepared = False
            if not name:
                continue
            spell = get_spell_by_id(name)
            spell_id = _safe_str((spell or {}).get("id"), _slugify(name), limit=120)
            entry = {
                "id": spell_id,
                "spellId": spell_id,
                "name": _safe_str((spell or {}).get("name"), name, limit=120),
                "prepared": prepared,
                "source": "PDF import",
                "matchedNative": bool(spell),
                "section": section,
                "notes": notes,
            }
            if isinstance(row, dict):
                entry = _copy_imported_spell_fields(entry, row, row)
            entries.append(entry)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    unmatched = 0
    for entry in entries:
        spell_id = str(entry.get("id") or "").strip()
        if not spell_id or spell_id in seen:
            continue
        seen.add(spell_id)
        deduped.append(entry)
        if not entry.get("matchedNative"):
            unmatched += 1
    spell_slots = src.get("spellSlots") if isinstance(src.get("spellSlots"), dict) else {}
    known = [entry["id"] for entry in deduped if entry.get("matchedNative")]
    prepared = [entry["id"] for entry in deduped if entry.get("prepared") and entry.get("matchedNative")]
    return {
        "known": known,
        "prepared": prepared,
        "slots": copy.deepcopy(spell_slots),
        "focus": {},
        "rituals": [],
        "spellbookEntries": deduped,
        "classSources": [],
    }, deduped, unmatched


def normalize_pdf_payload(raw_payload: Any, *, filename: str = "") -> dict[str, Any]:
    src = raw_payload if isinstance(raw_payload, dict) else {}
    warnings: list[dict[str, Any]] = []

    classes = src.get("classes") if isinstance(src.get("classes"), list) else []
    canonical_classes: list[dict[str, Any]] = []
    for row in classes:
        if not isinstance(row, dict):
            continue
        name = _safe_str(row.get("name"), "", limit=80)
        if not name:
            continue
        class_id = name.lower().replace(" ", "-")
        canonical_classes.append(
            {
                "name": name,
                "classId": class_id,
                "level": _safe_int(row.get("level"), 1, minimum=1),
                "subclass": _safe_str(row.get("subclass"), "", limit=80),
            }
        )
        if class_id not in _KNOWN_SUBCLASS_BY_CLASS and class_id != "adventurer":
            warnings.append(_make_warning(
                code="ambiguous_class",
                message=f'Class "{name}" came from PDF text and may need review against native class options.',
                details={"className": name},
            ))

    if not canonical_classes:
        canonical_classes = [{"name": "Adventurer", "classId": "adventurer", "level": 1}]
        warnings.append(_make_warning(
            code="ambiguous_class",
            message="Class data was incomplete in the PDF; defaulted to Adventurer level 1.",
            details={"resolutionKey": "class"},
        ))

    stats = src.get("stats") if isinstance(src.get("stats"), list) else []
    ability_scores = {
        "str": _safe_int(stats[0], 10) if len(stats) > 0 else 10,
        "dex": _safe_int(stats[1], 10) if len(stats) > 1 else 10,
        "con": _safe_int(stats[2], 10) if len(stats) > 2 else 10,
        "int": _safe_int(stats[3], 10) if len(stats) > 3 else 10,
        "wis": _safe_int(stats[4], 10) if len(stats) > 4 else 10,
        "cha": _safe_int(stats[5], 10) if len(stats) > 5 else 10,
    }

    book = src.get("book") if isinstance(src.get("book"), dict) else {}
    currency_src = src.get("currencyBreakdown") if isinstance(src.get("currencyBreakdown"), dict) else None
    currency = {
        "cp": _safe_int((currency_src or {}).get("cp"), 0, minimum=0),
        "sp": _safe_int((currency_src or {}).get("sp"), 0, minimum=0),
        "ep": _safe_int((currency_src or {}).get("ep"), 0, minimum=0),
        "gp": _safe_int((currency_src or {}).get("gp"), 0, minimum=0),
        "pp": _safe_int((currency_src or {}).get("pp"), 0, minimum=0),
    } if currency_src else _parse_coin_text(_safe_str(src.get("currency") or book.get("currency"), ""))

    imported_id = _safe_str(src.get("id") or src.get("name") or filename, "", limit=120)
    character_id = f"pdf-{re.sub(r'[^a-zA-Z0-9]+', '-', imported_id).strip('-').lower()}" if imported_id else f"pdf-{int(time.time())}"
    name = _safe_str(src.get("name"), "Unnamed Character", limit=120)
    race_name = _safe_str(src.get("race") or book.get("race"), "", limit=80)
    background_name = _safe_str(src.get("background") or book.get("background"), "", limit=80)

    imported_ac = _safe_int(_first_present(src, "ac", "armorClass", default=book.get("ac")), 10, minimum=1)
    imported_max_hp = _safe_int(_first_present(src, "maxHp", "maxHP", default=book.get("maxHp")), 1, minimum=1)
    imported_current_hp = _safe_int(_first_present(src, "currentHp", "currentHP", default=book.get("currentHp")), imported_max_hp, minimum=0)
    imported_temp_hp = _safe_int(_first_present(src, "tempHp", "tempHP", default=book.get("tempHp")), 0, minimum=0)
    imported_hit_dice = _first_present(src, "hitDice", "hit_dice", default=book.get("hitDice")) or []
    imported_custom_modifiers = _first_present(src, "customModifiers", "customValues", default=book.get("customModifiers")) or []
    import_needs_review = bool(imported_custom_modifiers)

    saving_throws = _normalize_pdf_saving_throws(_first_present(src, "savingThrows", default=book.get("savingThrows")))
    skills = _normalize_pdf_skills(src if src.get("skills") is not None else {**src, "skills": book.get("skills", {})})
    imported_inventory = _normalize_pdf_inventory(src)
    imported_actions = _normalize_pdf_attacks(src)
    spell_state, spell_entries, unmatched_spell_count = _normalize_pdf_spell_entries(src)

    passive_perception = _safe_int(_first_present(src, "passivePerception", default=book.get("passivePerception")), 0, minimum=0)
    passive_insight = _safe_int(_first_present(src, "passiveInsight", default=book.get("passiveInsight")), 0, minimum=0)
    passive_investigation = _safe_int(_first_present(src, "passiveInvestigation", default=book.get("passiveInvestigation")), 0, minimum=0)
    passives = {
        key: value for key, value in {
            "perception": passive_perception,
            "insight": passive_insight,
            "investigation": passive_investigation,
        }.items() if value
    }

    proficiencies_text = _safe_str(_first_present(src, "proficiencies", default=book.get("proficiencies")), "", limit=2000)
    senses_text = _safe_str(_first_present(src, "senses", default=book.get("senses")), "", limit=1200)
    resistances_text = _safe_str(_first_present(src, "resistances", "defenses", default=book.get("resistances")), "", limit=1200)
    personality_notes = _strip_html(
        _first_present(src, "personality", "personalityTraits", "featuresText", default="")
        or book.get("campaignNotes")
        or book.get("features")
        or "",
        limit=3000,
    )

    imported_ac = _safe_int(_first_present(src, "ac", "armorClass", default=book.get("ac")), 10, minimum=1)
    imported_max_hp = _safe_int(_first_present(src, "maxHp", "maxHP", default=book.get("maxHp")), 1, minimum=1)
    imported_current_hp = _safe_int(_first_present(src, "currentHp", "currentHP", default=book.get("currentHp")), imported_max_hp, minimum=0)
    imported_temp_hp = _safe_int(_first_present(src, "tempHp", "tempHP", default=book.get("tempHp")), 0, minimum=0)
    imported_hit_dice = _first_present(src, "hitDice", "hit_dice", default=book.get("hitDice")) or []
    imported_custom_modifiers = _first_present(src, "customModifiers", "customValues", default=book.get("customModifiers")) or []
    import_needs_review = bool(imported_custom_modifiers)

    document = {
        "schemaVersion": 1,
        "rulesMode": "casual",
        "ruleset": "casual-dnd-5e-compatible",
        "sourceMode": "pdf",
        "identity": {
            "characterId": character_id,
            "name": name,
            "displayName": name,
            "alignment": _safe_str(src.get("alignment") or book.get("alignment"), "", limit=60),
            "personalityTraits": personality_notes,
            "backstory": _strip_html(_first_present(src, "backstory", default=book.get("backstory")), limit=3000),
            "notes": _strip_html(book.get("campaignNotes") or src.get("notes"), limit=3000),
        },
        "species": {
            "id": race_name.lower().replace(" ", "-"),
            "name": race_name,
            "size": "medium",
            "speed": _safe_int(_first_present(src, "speed", default=book.get("speed")), 30, minimum=0),
            "senses": [{"name": "Imported senses", "type": "text", "description": senses_text}] if senses_text else [],
            "resistances": [{"name": "Imported defenses", "description": resistances_text}] if resistances_text else [],
        },
        "background": {
            "id": background_name.lower().replace(" ", "-"),
            "name": background_name,
            "proficiencies": _split_pdf_text_lines(proficiencies_text),
            "languages": _split_pdf_text_lines(proficiencies_text),
        },
        "abilities": {
            "generationMode": "imported",
            "scores": ability_scores,
            "saves": saving_throws,
            "skills": skills,
        },
        "classes": canonical_classes,
        "maxHP": imported_max_hp,
        "currentHP": imported_current_hp,
        "tempHP": imported_temp_hp,
        "ac": imported_ac,
        "importedAc": imported_ac,
        "importedMaxHp": imported_max_hp,
        "importedCurrentHp": imported_current_hp,
        "importedTempHp": imported_temp_hp,
        "importedHitDice": imported_hit_dice,
        "importedEquipment": copy.deepcopy(imported_inventory),
        "importedCustomModifiers": copy.deepcopy(imported_custom_modifiers),
        "importedSource": "pdf",
        "importedAt": time.time(),
        "importNeedsReview": import_needs_review,
        "importWarnings": warnings,
        "initiative": _parse_signed_int(_first_present(src, "initiative", default=book.get("initiative")), 0),
        "proficiencyBonus": _safe_int(_first_present(src, "profBonus", "proficiencyBonus", default=book.get("profBonus")), 2, minimum=0),
        "passives": passives,
        "defenses": {
            "senses": senses_text,
            "resistances": resistances_text,
            "proficiencies": proficiencies_text,
        },
        "equipment": {
            "currency": currency,
            "inventory": imported_inventory,
            "equipped": {},
            "containers": [],
        },
        "spellState": spell_state,
        "importMeta": {
            "origin": "pdf",
            "source": "pdf",
            "sourceType": "pdf",
            "externalId": character_id,
            "importedAt": time.time(),
            "rawVersion": "",
            "rawSnapshot": copy.deepcopy(src),
            "nativeImportMode": "pdf_import",
            "mappingNotes": [
                f"Imported {len(imported_inventory)} inventory item(s) from PDF text.",
                f"Imported {len(imported_actions)} attack/action card(s) from PDF text.",
                f"Imported {len(spell_entries)} spell row(s) from PDF text.",
            ],
            "importedActions": imported_actions,
            "importedSpells": spell_entries,
            "importedInventoryCount": len(imported_inventory),
            "importedAc": imported_ac,
            "importedMaxHp": imported_max_hp,
            "importedCurrentHp": imported_current_hp,
            "importedTempHp": imported_temp_hp,
            "importedHitDice": imported_hit_dice,
            "importedEquipment": copy.deepcopy(imported_inventory),
            "importedCustomModifiers": copy.deepcopy(imported_custom_modifiers),
            "importNeedsReview": import_needs_review,
            "importWarnings": warnings,
            "pdfFieldSummary": {
                "hasSkills": bool(skills),
                "hasSavingThrows": bool(saving_throws),
                "hasPassives": bool(passives),
                "hasDefenses": bool(senses_text or resistances_text),
            },
        },
    }

    if not race_name:
        warnings.append(_make_warning(
            code="ambiguous_species",
            message="Species/Race was not found in the PDF import and should be reviewed.",
            details={"resolutionKey": "species"},
        ))
    elif race_name.lower() in _SPECIES_ALIAS_MAP:
        warnings.append(_make_warning(
            code="ambiguous_species",
            message=f'Species "{race_name}" may map to multiple native species options.',
            details={"options": list(_SPECIES_ALIAS_MAP.get(race_name.lower()) or [])},
        ))
    if not background_name:
        warnings.append(_make_warning(
            code="partial_pdf_fields",
            message="Background was not found in the PDF import.",
            details={"field": "background"},
        ))
    if not imported_inventory:
        warnings.append(_make_warning(
            code="missing_inventory",
            message="No parseable equipment rows were found in the PDF, so inventory may need to be entered manually.",
        ))
    if not spell_entries:
        warnings.append(_make_warning(
            code="missing_spells",
            message="No parseable spell rows were found in the PDF. This is expected for non-spellcasters.",
        ))
    elif unmatched_spell_count:
        warnings.append(_make_warning(
            code="missing_spells",
            message=f"{unmatched_spell_count} PDF spell(s) did not match the native spell compendium and were preserved as unmatched spellbook entries.",
            details={"unmatchedNameCount": unmatched_spell_count},
        ))
    missing_core = [
        key for key, present in {
            "skills": bool(skills),
            "saving_throws": bool(saving_throws),
            "attacks": bool(imported_actions),
            "passive_scores": bool(passives),
        }.items() if not present
    ]
    if missing_core or src.get("_rawFields") is None:
        warnings.append(_make_warning(
            code="partial_pdf_fields",
            message="Some PDF fields could not be parsed and were left for manual review.",
            details={"missing": missing_core, "rawFieldsAvailable": src.get("_rawFields") is not None},
        ))

    document["importMeta"]["warnings"] = copy.deepcopy(warnings)
    canonical = validate_or_raise(document)
    return {
        "document": canonical,
        "warnings": warnings,
    }
