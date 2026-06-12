"""Runtime resolver scaffold for canonical native character documents."""
from __future__ import annotations

import copy
import time
from typing import Any

from server.character.awakening import apply_awakening_grants, resolve_awakening_for_runtime
from server.character.feature_catalog import (
    build_class_feature_definitions,
    build_runtime_feature_payload,
    build_subclass_feature_definitions,
)
from server.character.feature_authored_data import build_background_feature_profile, build_feat_profile, build_species_trait_profile
from server.character.rules_catalog import get_class_catalog_row, get_subclass_catalog_row, load_rules_catalog
from server.character.spell_compendium import build_character_spell_manifest
from server.character.summon_catalog import get_summon_template
from server.character.talent_engine import apply_talent_grants, resolve_talents_for_runtime
from server.character.summon_state import sync_summon_unlocks_from_features
from server.character.schema import default_runtime
from server.character.validation import ensure_character_defaults
from server.rules_content import OPEN_5E_SPELLS as _OPEN_5E_SPELLS

_RESOLVER_VERSION = 1


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        num = int(value)
    except Exception:
        num = fallback
    if minimum is not None:
        num = max(minimum, num)
    return num


def _ability_modifier(score: Any) -> int:
    try:
        value = int(score)
    except Exception:
        value = 10
    return (value - 10) // 2


def _compute_total_level(document: dict) -> int:
    classes = document.get("classes") if isinstance(document.get("classes"), list) else []
    total = 0
    for class_row in classes:
        if not isinstance(class_row, dict):
            continue
        total += _safe_int(class_row.get("level"), 0, minimum=0)
    return max(1, total)


def _compute_proficiency_bonus(level_total: int) -> int:
    return 2 + max(0, (max(1, level_total) - 1) // 4)

def _rules_background_by_id(background_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(background_id or '').strip().lower()
    if not key:
        return None
    for row in catalog.get('backgrounds', []) or []:
        if isinstance(row, dict) and str(row.get('id') or '').strip().lower() == key:
            return row
    return None


def _rules_feat_by_id(feat_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(feat_id or '').strip().lower()
    if not key:
        return None
    for bucket in ('featsOrigin', 'featsGeneral'):
        for row in catalog.get(bucket, []) or []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get('id') or '').strip().lower()
            name = str(row.get('displayName') or row.get('name') or '').strip().lower()
            if key and key in {rid, name}:
                return row
    return None


def _resolve_runtime_origin_traits(document: dict[str, Any]) -> list[dict[str, Any]]:
    species = document.get('species') if isinstance(document.get('species'), dict) else {}
    species_id = str(species.get('id') or species.get('name') or '').strip().lower()
    rows = species.get('traits') if isinstance(species.get('traits'), list) else []
    return [
        build_species_trait_profile(species_id, row)
        for row in rows
        if isinstance(row, dict)
    ]


def _resolve_runtime_background_features(document: dict[str, Any]) -> list[dict[str, Any]]:
    background = document.get('background') if isinstance(document.get('background'), dict) else {}
    background_id = str(background.get('id') or '').strip().lower()
    rules_row = _rules_background_by_id(background_id)
    rows: list[dict[str, Any]] = []
    if isinstance(rules_row, dict):
        feature = build_background_feature_profile(rules_row)
        if feature:
            rows.append(feature)
    elif background:
        feature = build_background_feature_profile({
            'id': background_id or background.get('name'),
            'displayName': background.get('name') or background_id,
            'featureTitle': background.get('featureTitle'),
            'featureDescription': background.get('featureSummary') or background.get('description'),
        })
        if feature:
            rows.append(feature)
    return rows


def _resolve_runtime_feat_features(document: dict[str, Any]) -> list[dict[str, Any]]:
    feats = document.get('feats') if isinstance(document.get('feats'), list) else []
    out: list[dict[str, Any]] = []
    for row in feats:
        if isinstance(row, dict):
            feat_id = str(row.get('featId') or row.get('id') or row.get('name') or '').strip()
            feat_row = _rules_feat_by_id(feat_id) or row
        else:
            feat_id = str(row or '').strip()
            feat_row = _rules_feat_by_id(feat_id) or {'id': feat_id, 'displayName': feat_id}
        feature = build_feat_profile(feat_row)
        if feature:
            out.append(feature)
    return out



def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or fallback


def _imported_source_type(row: dict[str, Any], fallback: str = "imported") -> str:
    raw = _safe_text(row.get("sourceType") or row.get("kind") or row.get("classification") or row.get("section") or fallback).lower()
    if "subclass" in raw:
        return "subclass"
    if "class" in raw:
        return "class"
    if raw in {"species", "race", "racial", "trait", "origin"} or "species" in raw or "racial" in raw:
        return "species"
    if "feat" in raw:
        return "feat"
    if "background" in raw:
        return "background"
    if "item" in raw or "weapon" in raw or "equipment" in raw:
        return "item"
    return "imported"


def _imported_recovery_text(row: dict[str, Any]) -> str:
    limited = row.get("limitedUse") if isinstance(row.get("limitedUse"), dict) else {}
    reset = _safe_text(row.get("recovery") or row.get("recharge") or limited.get("resetType") or limited.get("resetTypeDescription"))
    if reset:
        lowered = reset.lower().replace("_", " ").replace("-", " ")
        if "short" in lowered and "long" in lowered:
            return "Short or long rest"
        if "short" in lowered:
            return "Short rest"
        if "long" in lowered:
            return "Long rest"
        if "turn" in lowered:
            return "Start/end of turn"
        return reset
    return ""


def _imported_usage_text(row: dict[str, Any]) -> str:
    limited = row.get("limitedUse") if isinstance(row.get("limitedUse"), dict) else {}
    explicit = _safe_text(row.get("usage") or row.get("resourceSummary") or row.get("usesText") or row.get("activationText"))
    max_uses = row.get("maxUses") if row.get("maxUses") not in (None, "") else limited.get("maxUses")
    number_used = row.get("numberUsed") if row.get("numberUsed") not in (None, "") else limited.get("numberUsed")
    if max_uses not in (None, ""):
        max_value = _safe_int(max_uses, 0, minimum=0)
        if max_value:
            remaining = max(0, max_value - _safe_int(number_used, 0, minimum=0))
            return f"{remaining}/{max_value} uses" if number_used not in (None, "") else f"{max_value} use{'s' if max_value != 1 else ''}"
    stat_uses = limited.get("statModifierUsesId") or limited.get("operator")
    if stat_uses and explicit:
        return explicit
    return explicit


def _imported_damage_formula(row: dict[str, Any]) -> tuple[str, str]:
    damage = row.get("damage") if isinstance(row.get("damage"), dict) else {}
    formula = _safe_text(row.get("damageFormula") or row.get("damageText") or damage.get("formula") or damage.get("dice") or row.get("damage"))
    damage_type = _safe_text(row.get("damageType") or damage.get("type"))
    return formula, damage_type


def _imported_needs_review(row: dict[str, Any], context: dict[str, Any], *, name: str) -> bool:
    native_names = context.get("native_names") if isinstance(context.get("native_names"), set) else set()
    if name.strip().lower() in native_names:
        return False
    if row.get("needsReview") is not None:
        return bool(row.get("needsReview"))
    if row.get("matchedNative") is not None:
        return not bool(row.get("matchedNative"))
    return True


def build_imported_feature_card(imported_feature: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Build a readable runtime fallback card from preserved imported feature data."""
    if not isinstance(imported_feature, dict):
        return None
    ctx = context if isinstance(context, dict) else {}
    name = _safe_text(imported_feature.get("name") or imported_feature.get("displayName") or imported_feature.get("label"))
    if not name:
        return None
    source_type = _imported_source_type(imported_feature)
    action_type = _safe_text(imported_feature.get("actionType") or imported_feature.get("type"), "passive").lower()
    summary = _safe_text(imported_feature.get("summary") or imported_feature.get("snippet") or imported_feature.get("effect"))
    description = _safe_text(imported_feature.get("description") or imported_feature.get("text") or summary, "Needs DM review.")
    usage = _imported_usage_text(imported_feature)
    recovery = _imported_recovery_text(imported_feature)
    needs_review = _imported_needs_review(imported_feature, ctx, name=name)
    tags = [str(tag).strip() for tag in (imported_feature.get("tags") if isinstance(imported_feature.get("tags"), list) else []) if str(tag).strip()]
    if "imported" not in {tag.lower() for tag in tags}:
        tags.append("imported")
    if needs_review:
        tags.append("Needs review")
    card = {
        "id": _safe_text(imported_feature.get("id"), f"imported-feature-{name.lower().replace(' ', '-')}").lower(),
        "name": name,
        "displayName": name,
        "section": _safe_text(imported_feature.get("section"), "Imported Features" if source_type == "imported" else f"{source_type.title()} Features"),
        "type": action_type,
        "actionType": action_type,
        "sourceType": source_type,
        "source": _safe_text(imported_feature.get("source"), f"Imported {source_type}"),
        "kind": source_type if source_type != "species" else "trait",
        "minLevel": _safe_int(imported_feature.get("minLevel") or imported_feature.get("level"), 0, minimum=0),
        "summary": summary or description[:240],
        "description": description,
        "usage": usage,
        "recovery": recovery,
        "activationText": _safe_text(imported_feature.get("activationText") or imported_feature.get("activation")),
        "resourceName": _safe_text(imported_feature.get("resourceName") or imported_feature.get("resource")),
        "range": _safe_text(imported_feature.get("range")),
        "duration": _safe_text(imported_feature.get("duration")),
        "trigger": _safe_text(imported_feature.get("trigger")),
        "save": _safe_text(imported_feature.get("save") or imported_feature.get("saveDC")),
        "needsReview": needs_review,
        "matchedNative": not needs_review,
        "tags": tags,
        "importedFallback": True,
    }
    damage_formula, damage_type = _imported_damage_formula(imported_feature)
    if damage_formula:
        card["damageFormula"] = damage_formula
        card["damage"] = {"formula": damage_formula, "type": damage_type}
        card["damageType"] = damage_type
    return card


def build_imported_action_card(imported_action: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Build a usable runtime fallback action card from preserved imported action data."""
    if not isinstance(imported_action, dict):
        return None
    ctx = context if isinstance(context, dict) else {}
    name = _safe_text(imported_action.get("name") or imported_action.get("displayName") or imported_action.get("label"))
    if not name:
        return None
    source_type = _imported_source_type(imported_action, "imported")
    action_type = _safe_text(imported_action.get("actionType") or imported_action.get("type"), "action").lower()
    if action_type in {"none", "no action"}:
        action_type = "passive"
    summary = _safe_text(imported_action.get("summary") or imported_action.get("snippet") or imported_action.get("effect"))
    description = _safe_text(imported_action.get("description") or imported_action.get("text") or summary, "Needs DM review.")
    usage = _imported_usage_text(imported_action)
    recovery = _imported_recovery_text(imported_action)
    damage_formula, damage_type = _imported_damage_formula(imported_action)
    needs_review = _imported_needs_review(imported_action, ctx, name=name)
    tags = [str(tag).strip() for tag in (imported_action.get("tags") if isinstance(imported_action.get("tags"), list) else []) if str(tag).strip()]
    if "imported" not in {tag.lower() for tag in tags}:
        tags.append("imported")
    if needs_review:
        tags.append("Needs review")
    card = {
        "id": _safe_text(imported_action.get("id"), f"imported-action-{name.lower().replace(' ', '-')}").lower(),
        "name": name,
        "displayName": name,
        "type": action_type,
        "actionType": action_type,
        "sourceType": source_type,
        "source": _safe_text(imported_action.get("source"), f"Imported {source_type}"),
        "classification": _safe_text(imported_action.get("classification"), "imported"),
        "summary": summary or description[:240],
        "description": description,
        "desc": summary or description,
        "usage": usage,
        "recovery": recovery,
        "activationText": _safe_text(imported_action.get("activationText") or imported_action.get("activation")),
        "attackBonus": imported_action.get("attackBonus", ""),
        "range": _safe_text(imported_action.get("range")),
        "duration": _safe_text(imported_action.get("duration")),
        "trigger": _safe_text(imported_action.get("trigger")),
        "save": _safe_text(imported_action.get("save") or imported_action.get("saveDC")),
        "resourceName": _safe_text(imported_action.get("resourceName") or imported_action.get("resource")),
        "trackUses": bool(imported_action.get("trackUses") or usage),
        "needsReview": needs_review,
        "matchedNative": not needs_review,
        "tags": tags,
        "importedFallback": True,
    }
    if imported_action.get("maxUses") not in (None, ""):
        card["maxUses"] = _safe_int(imported_action.get("maxUses"), 0, minimum=0)
    if imported_action.get("uses") not in (None, ""):
        card["uses"] = _safe_int(imported_action.get("uses"), 0, minimum=0)
    if damage_formula:
        card["damage"] = damage_formula
        card["damageFormula"] = damage_formula
        card["damageType"] = damage_type
    return card


def _compute_base_hp(document: dict, level_total: int, runtime_classes: list[dict[str, Any]]) -> dict:
    abilities = document.get("abilities") if isinstance(document.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    con_mod = _ability_modifier(scores.get("con", 10))

    hit_dice: list[dict[str, Any]] = []
    max_hp = 0
    classes = runtime_classes if isinstance(runtime_classes, list) else []
    if classes:
        level_index = 0
        for row in classes:
            if not isinstance(row, dict):
                continue
            lvl = _safe_int(row.get("level"), 1, minimum=1)
            class_id = str(row.get("classId") or "").strip().lower()
            class_catalog = get_class_catalog_row(class_id) if class_id else None
            hit_die = _safe_int((class_catalog or {}).get("hitDie"), 8, minimum=1)
            hit_die_average = max(1, (hit_die // 2) + 1)
            class_hp = 0
            # Level-1 bonus is granted once for the character's first total level.
            for class_level in range(lvl):
                gain = (hit_die if level_index == 0 else hit_die_average) + con_mod
                class_hp += max(1, gain)
                level_index += 1
            max_hp += class_hp
            hit_dice.append({"die": hit_die, "count": lvl, "classId": class_id})
    else:
        default_avg = max(1, (6 // 2) + 1)
        max_hp = max(1, 6 + con_mod)
        for _ in range(max(0, level_total - 1)):
            max_hp += max(1, default_avg + con_mod)

    max_hp = max(1, max_hp)
    return {
        "max": max_hp,
        "current": max_hp,
        "temp": 0,
        "hitDice": hit_dice,
    }


def _runtime_hp_from_document(document: dict[str, Any], base_hp: dict[str, Any]) -> dict[str, Any]:
    root_hp = document.get("hp") if isinstance(document.get("hp"), dict) else {}
    max_hp = _safe_int(
        document.get("maxHP"),
        _safe_int(
            document.get("maxHp"),
            _safe_int(root_hp.get("max"), _safe_int(base_hp.get("max"), 1, minimum=1), minimum=1),
            minimum=1,
        ),
        minimum=1,
    )
    current_hp = _safe_int(
        document.get("currentHP"),
        _safe_int(
            document.get("currentHp"),
            _safe_int(root_hp.get("current"), max_hp, minimum=0),
            minimum=0,
        ),
        minimum=0,
    )
    temp_hp = _safe_int(
        document.get("tempHP"),
        _safe_int(
            document.get("tempHp"),
            _safe_int(root_hp.get("temp"), 0),
        ),
        minimum=0,
    )
    return {
        "max": max(1, max_hp),
        "current": max(0, min(max_hp, current_hp)),
        "temp": max(0, temp_hp),
        "hitDice": list(base_hp.get("hitDice") or []),
    }


def _compute_equipment_ac(document: dict[str, Any], *, dex_mod: int, fallback_ac: int) -> int:
    equipment = document.get("equipment") if isinstance(document.get("equipment"), dict) else {}
    inventory = equipment.get("inventory") if isinstance(equipment.get("inventory"), list) else []
    equipped_rows = [row for row in inventory if isinstance(row, dict) and bool(row.get("equipped"))]
    armor_rows = [
        row for row in equipped_rows
        if str(row.get("equipment_kind") or row.get("kind") or row.get("item_type") or "").strip().lower() == "armor"
    ]
    shield_rows = [
        row for row in equipped_rows
        if str(row.get("equipment_kind") or row.get("kind") or row.get("item_type") or "").strip().lower() == "shield"
    ]

    armor_ac = fallback_ac
    for armor in armor_rows:
        base_ac = _safe_int(armor.get("base_ac"), 0, minimum=0)
        if base_ac <= 0:
            continue
        armor_type = str(armor.get("armor_type") or "").strip().lower()
        dex_cap = armor.get("dex_cap")
        if armor_type == "heavy":
            dex_for_ac = 0
        elif armor_type == "medium":
            dex_for_ac = min(dex_mod, _safe_int(dex_cap, 2))
        else:
            dex_for_ac = min(dex_mod, _safe_int(dex_cap, dex_mod)) if dex_cap not in (None, "") else dex_mod
        armor_bonus = _safe_int(armor.get("ac_bonus"), 0)
        armor_ac = max(armor_ac, base_ac + dex_for_ac + armor_bonus)

    shield_bonus = 0
    for shield in shield_rows:
        shield_bonus += _safe_int(shield.get("ac_bonus"), 2)
    return max(fallback_ac, armor_ac + shield_bonus)


def _format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _display_item_name(row: dict[str, Any] | None, fallback: str = "None") -> str:
    if not isinstance(row, dict):
        return fallback
    return str(row.get("name") or row.get("displayName") or row.get("id") or fallback).strip() or fallback


def _warning(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "message": message}
    if details:
        out["details"] = details
    return out


def _equipped_inventory_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    equipment = document.get("equipment") if isinstance(document.get("equipment"), dict) else {}
    inventory = equipment.get("inventory") if isinstance(equipment.get("inventory"), list) else []
    return [row for row in inventory if isinstance(row, dict) and bool(row.get("equipped"))]


def _inventory_kind(row: dict[str, Any]) -> str:
    return str(row.get("equipment_kind") or row.get("kind") or row.get("item_type") or row.get("type") or "").strip().lower()


def _resolve_ac_audit(
    document: dict[str, Any],
    *,
    dex_mod: int,
    con_mod: int,
    wis_mod: int,
    primary_class_id: str,
    fallback_ac: int,
) -> dict[str, Any]:
    equipped_rows = _equipped_inventory_rows(document)
    armor_rows = [row for row in equipped_rows if _inventory_kind(row) == "armor"]
    shield_rows = [row for row in equipped_rows if _inventory_kind(row) == "shield"]

    warnings: list[dict[str, Any]] = []
    missing_data: list[str] = []
    active_bonuses: list[dict[str, Any]] = []
    breakdown: list[str] = []

    unarmored_formula = "Base unarmored: 10"
    base_unarmored = 10 + dex_mod
    if primary_class_id == "barbarian":
        class_unarmored = 10 + dex_mod + con_mod
        if class_unarmored >= base_unarmored:
            base_unarmored = class_unarmored
            unarmored_formula = f"Barbarian Unarmored Defense: 10 + Dex {_format_signed(dex_mod)} + Con {_format_signed(con_mod)} = {base_unarmored}"
    elif primary_class_id == "monk":
        class_unarmored = 10 + dex_mod + wis_mod
        if class_unarmored >= base_unarmored:
            base_unarmored = class_unarmored
            unarmored_formula = f"Monk Unarmored Defense: 10 + Dex {_format_signed(dex_mod)} + Wis {_format_signed(wis_mod)} = {base_unarmored}"
    if unarmored_formula == "Base unarmored: 10":
        unarmored_formula = f"Base unarmored: 10 + Dex {_format_signed(dex_mod)} = {base_unarmored}"
    breakdown.append(unarmored_formula)

    best_armor_value = base_unarmored
    best_armor: dict[str, Any] | None = None
    best_armor_breakdown = "No equipped armour; using unarmoured AC."
    for armor in armor_rows:
        name = _display_item_name(armor, "Unknown armour")
        base_ac = _safe_int(armor.get("base_ac"), 0, minimum=0)
        if base_ac <= 0:
            warnings.append(_warning("unknown_armor", f'Unknown armour "{name}"; AC may need manual verification.', details={"item": name}))
            missing_data.append(f"Armour base AC for {name}")
            continue
        armor_type = str(armor.get("armor_type") or "").strip().lower()
        dex_cap = armor.get("dex_cap")
        if armor_type == "heavy":
            dex_for_ac = 0
            dex_text = "Dex modifier ignored for heavy armour"
        elif armor_type == "medium":
            cap = _safe_int(dex_cap, 2)
            dex_for_ac = min(dex_mod, cap)
            dex_text = f"Dex modifier capped at +{cap}: {_format_signed(dex_for_ac)}"
        else:
            dex_for_ac = min(dex_mod, _safe_int(dex_cap, dex_mod)) if dex_cap not in (None, "") else dex_mod
            dex_text = f"Dex modifier: {_format_signed(dex_for_ac)}"
        armor_bonus = _safe_int(armor.get("ac_bonus"), 0)
        if armor_bonus:
            active_bonuses.append({"source": name, "type": "armor_ac_bonus", "value": armor_bonus})
        value = base_ac + dex_for_ac + armor_bonus
        parts = [f"Base armour: {name} = {base_ac}", dex_text]
        if armor_bonus:
            parts.append(f"Armour bonus: {_format_signed(armor_bonus)}")
        parts.append(f"Armour total: {value}")
        if best_armor is None or value > best_armor_value:
            best_armor = armor
            best_armor_value = value
            best_armor_breakdown = "; ".join(parts)

    breakdown.append(best_armor_breakdown)

    shield_bonus = 0
    equipped_shield: dict[str, Any] | None = None
    if shield_rows:
        for shield in shield_rows:
            name = _display_item_name(shield, "Unknown shield")
            if shield.get("ac_bonus") in (None, ""):
                warnings.append(_warning("unknown_shield", f'Shield "{name}" has no explicit AC bonus; assuming +2.', details={"item": name}))
                missing_data.append(f"Shield AC bonus for {name}")
            bonus = _safe_int(shield.get("ac_bonus"), 2)
            shield_bonus += bonus
            equipped_shield = equipped_shield or shield
            active_bonuses.append({"source": name, "type": "shield_ac_bonus", "value": bonus})
        breakdown.append(f"Shield: {_display_item_name(equipped_shield)} = {_format_signed(shield_bonus)}")
    else:
        breakdown.append("Shield: +0")

    for row in equipped_rows:
        name = _display_item_name(row, "Unknown item")
        if bool(row.get("attuned")) and ("magic" in str(row.get("category") or row.get("notes") or "").lower()) and not any(key in row for key in ("ac_bonus", "bonus", "attack_bonus")):
            warnings.append(_warning("unknown_magic_item_bonus", f'Magic item "{name}" may have bonuses Alpha cannot infer yet.', details={"item": name}))
        if row.get("custom") or row.get("isCustom") or str(row.get("source") or "").strip().lower() in {"custom", "d&d beyond custom"}:
            warnings.append(_warning("unknown_custom_dndbeyond_modifier", f'Custom imported item/modifier "{name}" needs manual verification.', details={"item": name}))

    calculated_value = max(fallback_ac, best_armor_value + shield_bonus)
    imported_ac = _safe_int(document.get("ac"), 0, minimum=0)
    final_value = max(imported_ac, calculated_value)
    if imported_ac and imported_ac != calculated_value:
        breakdown.append(f"Imported AC: {imported_ac}; Alpha calculation: {calculated_value}; final uses higher value {final_value}.")
    else:
        breakdown.append(f"Final AC: {final_value}")

    return {
        "value": final_value,
        "calculatedValue": calculated_value,
        "importedValue": imported_ac or None,
        "breakdown": breakdown,
        "warnings": warnings,
        "missingData": missing_data,
        "equippedArmour": _clone(best_armor) if best_armor else None,
        "equippedArmor": _clone(best_armor) if best_armor else None,
        "equippedShield": _clone(equipped_shield) if equipped_shield else None,
        "activeBonuses": active_bonuses,
    }


def _build_hp_audit(document: dict[str, Any], runtime_classes: list[dict[str, Any]], runtime_hp: dict[str, Any]) -> dict[str, Any]:
    abilities = document.get("abilities") if isinstance(document.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    con_mod = _ability_modifier(scores.get("con", 10))
    warnings: list[dict[str, Any]] = []
    missing_data: list[str] = []
    breakdown: list[str] = []
    level_index = 0
    calculated = 0
    for row in runtime_classes if isinstance(runtime_classes, list) else []:
        if not isinstance(row, dict):
            continue
        lvl = _safe_int(row.get("level"), 1, minimum=1)
        class_id = str(row.get("classId") or "").strip().lower()
        class_name = str(row.get("className") or row.get("name") or class_id or "Unknown class").strip()
        class_catalog = get_class_catalog_row(class_id) if class_id else None
        if not isinstance(class_catalog, dict) or not class_catalog.get("hitDie"):
            warnings.append(_warning("missing_class_hit_die", f'Class "{class_name}" is missing hit die data; assuming d8.', details={"classId": class_id}))
            missing_data.append(f"Class hit die for {class_name}")
        hit_die = _safe_int((class_catalog or {}).get("hitDie"), 8, minimum=1)
        average = max(1, (hit_die // 2) + 1)
        class_total = 0
        if level_index == 0 and lvl > 0:
            first_gain = max(1, hit_die + con_mod)
            class_total += first_gain
            calculated += first_gain
            breakdown.append(f"Level 1 {class_name} hit die: {hit_die} + Con {_format_signed(con_mod)} = {first_gain}")
            level_index += 1
            remaining = lvl - 1
        else:
            remaining = lvl
        if remaining > 0:
            per_level = max(1, average + con_mod)
            gain = remaining * per_level
            class_total += gain
            calculated += gain
            breakdown.append(f"Levels {level_index + 1}-{level_index + remaining} {class_name} average gain: {average} + Con {_format_signed(con_mod)} = {per_level} per level ({gain})")
            level_index += remaining
        if lvl > 0:
            breakdown.append(f"{class_name} subtotal: {class_total}")
    if not breakdown:
        default_first = max(1, 6 + con_mod)
        calculated = default_first
        breakdown.append(f"Fallback level 1 hit die: 6 + Con {_format_signed(con_mod)} = {default_first}")
        warnings.append(_warning("missing_class_hit_die", "No class rows were available; assuming d6 fallback HP."))
        missing_data.append("Class levels and hit dice")
    final_max = _safe_int(runtime_hp.get("max"), calculated, minimum=1)
    if final_max != calculated:
        breakdown.append(f"Imported/manual max HP overrides calculated HP: {final_max} (calculated {calculated}).")
    else:
        breakdown.append(f"Final max HP: {final_max}")
    return {
        "value": final_max,
        "calculatedValue": calculated,
        "breakdown": breakdown,
        "warnings": warnings,
        "missingData": missing_data,
    }


def _build_character_audit_result(
    document: dict[str, Any],
    *,
    runtime_classes: list[dict[str, Any]],
    runtime: dict[str, Any],
    dex_mod: int,
    con_mod: int,
    wis_mod: int,
    spellcasting_ability: str,
    spellcasting_mod: int,
    is_caster: bool,
    primary_class_id: str,
) -> dict[str, Any]:
    level_total = _safe_int(runtime.get("levelTotal"), _compute_total_level(document), minimum=1)
    proficiency_bonus = _safe_int(runtime.get("proficiencyBonus"), _compute_proficiency_bonus(level_total), minimum=0)
    fallback_ac = max(10, 10 + dex_mod)
    if primary_class_id == "barbarian":
        fallback_ac = max(fallback_ac, 10 + dex_mod + con_mod)
    elif primary_class_id == "monk":
        fallback_ac = max(fallback_ac, 10 + dex_mod + wis_mod)
    ac_audit = _resolve_ac_audit(
        document,
        dex_mod=dex_mod,
        con_mod=con_mod,
        wis_mod=wis_mod,
        primary_class_id=primary_class_id,
        fallback_ac=fallback_ac,
    )
    hp_audit = _build_hp_audit(document, runtime_classes, runtime.get("hp") if isinstance(runtime.get("hp"), dict) else {})

    warnings = list(ac_audit.get("warnings") or []) + list(hp_audit.get("warnings") or [])
    missing_data = list(ac_audit.get("missingData") or []) + list(hp_audit.get("missingData") or [])

    species = document.get("species") if isinstance(document.get("species"), dict) else {}
    if not str(species.get("id") or species.get("name") or "").strip():
        warnings.append(_warning("missing_species_race_feature", "Species/race is missing; species features cannot be fully resolved."))
        missing_data.append("Species/race features")
    for row in runtime_classes:
        if not isinstance(row, dict):
            continue
        level = _safe_int(row.get("level"), 1, minimum=1)
        subclass_level = _safe_int(row.get("subclassUnlockLevel"), 0, minimum=0)
        if subclass_level and level >= subclass_level and not str(row.get("subclassId") or row.get("subclassName") or "").strip():
            warnings.append(_warning("missing_subclass_feature", f'{row.get("className") or row.get("classId") or "Class"} has no subclass selected; subclass features may be missing.'))
            missing_data.append("Subclass features")
    feats = document.get("feats") if isinstance(document.get("feats"), list) else []
    for feat in feats:
        feat_id = str((feat or {}).get("featId") or (feat or {}).get("id") or (feat or {}).get("name") or "").strip() if isinstance(feat, dict) else str(feat or "").strip()
        if feat_id and _rules_feat_by_id(feat_id) is None:
            warnings.append(_warning("missing_feat", f'Feat "{feat_id}" is not mapped in the native rules catalog.', details={"feat": feat_id}))
            missing_data.append(f"Feat: {feat_id}")
    import_meta = document.get("importMeta") if isinstance(document.get("importMeta"), dict) else {}
    raw_snapshot = import_meta.get("rawSnapshot") if isinstance(import_meta.get("rawSnapshot"), dict) else {}
    if raw_snapshot.get("customModifiers") or raw_snapshot.get("customValues"):
        warnings.append(_warning("unknown_custom_dndbeyond_modifier", "D&D Beyond custom modifiers were present in the import and need manual verification."))
        missing_data.append("D&D Beyond custom modifiers")

    spell_state = document.get("spellState") if isinstance(document.get("spellState"), dict) else {}
    spell_entries = spell_state.get("spellbookEntries") if isinstance(spell_state.get("spellbookEntries"), list) else []
    for spell in spell_entries:
        if isinstance(spell, dict) and spell.get("matchedNative") is False:
            name = str(spell.get("name") or spell.get("id") or "Unknown spell").strip()
            warnings.append(_warning("missing_spell", f'Spell "{name}" is preserved but not matched to the native spell compendium.', details={"spell": name}))
            missing_data.append(f"Spell: {name}")

    spell_save_dc = 8 + proficiency_bonus + spellcasting_mod if is_caster else None
    spell_attack_bonus = proficiency_bonus + spellcasting_mod if is_caster else None
    initiative = _safe_int((runtime.get("combat") or {}).get("initiative") if isinstance(runtime.get("combat"), dict) else document.get("initiative"), dex_mod)
    return {
        "ac": {key: value for key, value in ac_audit.items() if key not in {"equippedArmour", "equippedArmor", "equippedShield", "activeBonuses", "missingData"}},
        "hp": {key: value for key, value in hp_audit.items() if key != "missingData"},
        "initiative": {"value": initiative, "breakdown": [f"Dex modifier: {_format_signed(dex_mod)}"]},
        "proficiencyBonus": {"value": proficiency_bonus, "breakdown": [f"Total level {level_total} => proficiency bonus {_format_signed(proficiency_bonus)}"]},
        "spellSaveDC": {"value": spell_save_dc, "breakdown": ([f"8 + proficiency {_format_signed(proficiency_bonus)} + {spellcasting_ability.upper()} {_format_signed(spellcasting_mod)} = {spell_save_dc}"] if is_caster else ["No spellcasting ability resolved."])},
        "spellAttackBonus": {"value": spell_attack_bonus, "breakdown": ([f"Proficiency {_format_signed(proficiency_bonus)} + {spellcasting_ability.upper()} {_format_signed(spellcasting_mod)} = {_format_signed(spell_attack_bonus or 0)}"] if is_caster else ["No spellcasting ability resolved."])},
        "equippedArmour": ac_audit.get("equippedArmour"),
        "equippedArmor": ac_audit.get("equippedArmor"),
        "equippedShield": ac_audit.get("equippedShield"),
        "activeBonuses": ac_audit.get("activeBonuses") or [],
        "warnings": warnings,
        "missingData": missing_data,
    }


def _resource_dedupe_key(resource_id: Any, name: Any) -> str:
    import re

    base = str(resource_id or name or "").strip().lower()
    if not base:
        return ""
    return re.sub(r"[^a-z0-9]+", "", base)


def _build_first_turn_strike_action(
    *,
    proficiency_bonus: int,
    str_mod: int,
) -> dict[str, Any]:
    return {
        "id": "basic-unarmed-strike",
        "displayName": "Basic Strike",
        "actionType": "action",
        "classification": "attack",
        "range": "Melee 5 ft",
        "attackBonus": proficiency_bonus + str_mod,
        "damage": {
            "formula": "1 + STR",
            "type": "bludgeoning",
        },
        "summary": "Reliable first-turn fallback so every class can immediately make an attack roll.",
        "resourceName": "",
        "trackUses": False,
    }


def _resolve_runtime_classes(normalized: dict) -> list[dict[str, Any]]:
    classes = normalized.get("classes") if isinstance(normalized.get("classes"), list) else []
    resolved_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(classes):
        if not isinstance(row, dict):
            continue
        class_id_raw = str(row.get("classId") or row.get("id") or "").strip()
        if not class_id_raw:
            class_id_raw = str(row.get("name") or "").strip()
        if not class_id_raw:
            continue
        class_lookup_id = class_id_raw.lower()

        level = _safe_int(row.get("level"), 1, minimum=1)
        class_catalog = get_class_catalog_row(class_lookup_id)
        class_id = class_id_raw or str((class_catalog or {}).get("id") or "").strip()
        class_name = str(
            row.get("name")
            or (class_catalog.get("displayName") if isinstance(class_catalog, dict) else "")
            or class_id
        ).strip()

        subclass_id = str(row.get("subclassId") or "").strip()
        subclass_name = str(row.get("subclass") or "").strip()
        if not subclass_id and subclass_name:
            subclass_id = subclass_name.strip().lower().replace(" ", "-")

        subclass_unlock_level = _safe_int(
            (class_catalog or {}).get("subclassLevel"),
            0,
            minimum=0,
        )
        subclass_catalog = get_subclass_catalog_row(subclass_id.lower()) if subclass_id else None
        subclass_display_name = str(
            subclass_name
            or (subclass_catalog.get("displayName") if isinstance(subclass_catalog, dict) else "")
        ).strip()
        selected_features = row.get("selectedFeatures") if isinstance(row.get("selectedFeatures"), list) else []

        # Maintain compatibility: keep class row carrying both subclassId + subclass display.
        if idx < len(classes) and isinstance(classes[idx], dict):
            classes[idx]["classId"] = class_id
            classes[idx]["name"] = class_name
            classes[idx]["level"] = level
            if subclass_id:
                classes[idx]["subclassId"] = subclass_id
            if subclass_display_name:
                classes[idx]["subclass"] = subclass_display_name
            if selected_features:
                classes[idx]["selectedFeatures"] = _clone(selected_features)

        unlocks = {}
        if isinstance(subclass_catalog, dict):
            unlocks = subclass_catalog.get("featureUnlocksByLevel")
            if not isinstance(unlocks, dict):
                unlocks = {}

        resolved_rows.append(
            {
                "classId": class_id,
                "name": class_name,
                "level": level,
                "subclassId": subclass_id,
                "subclassName": subclass_display_name,
                "subclassUnlockLevel": subclass_unlock_level,
                "subclassUnlocked": bool(subclass_id and subclass_unlock_level and level >= subclass_unlock_level),
                "subclassPending": bool((not subclass_id) and subclass_unlock_level and level >= subclass_unlock_level),
                "subclassFeatureUnlocksByLevel": unlocks,
                "selectedFeatures": _clone(selected_features),
            }
        )

    return resolved_rows


def _resolve_subclass_available_spells(runtime_classes: list[dict[str, Any]]) -> list[str]:
    """Return spell IDs accessible to the character's active subclasses.

    Checks each spell's subclass_lists against the character's active subclass IDs.
    This covers both the school-restricted access (level 3+) and the "any wizard
    spell" rule (level 8+) for Eldritch Knight and Arcane Trickster — as those
    subclass IDs are already populated on every qualifying spell in OPEN_5E_SPELLS.

    Subclass IDs are normalised to lowercase to match the lowercase IDs stored in
    spell subclass_lists (e.g. "eldritch-knight", "arcane-trickster").
    """
    active_subclass_ids: set[str] = set()
    for rc in runtime_classes:
        if not isinstance(rc, dict):
            continue
        # Normalise to lowercase: spell subclass_lists always store lowercase IDs.
        sid = str(rc.get("subclassId") or "").strip().lower()
        if sid:
            active_subclass_ids.add(sid)

    if not active_subclass_ids:
        return []

    available: list[str] = []
    for spell in _OPEN_5E_SPELLS:
        if not isinstance(spell, dict):
            continue
        spell_subclass_lists = spell.get("subclass_lists") or []
        if any(sc_id in active_subclass_ids for sc_id in spell_subclass_lists):
            spell_id = str(spell.get("id") or "").strip()
            if spell_id:
                available.append(spell_id)
    return available


def _resolve_summon_feature_name(
    *,
    feature_id: str,
    class_catalog: dict[str, Any] | None,
    subclass_catalog: dict[str, Any] | None,
) -> str:
    class_defs = (class_catalog or {}).get("featureDefinitions") if isinstance((class_catalog or {}).get("featureDefinitions"), dict) else {}
    subclass_defs = (subclass_catalog or {}).get("featureDefinitions") if isinstance((subclass_catalog or {}).get("featureDefinitions"), dict) else {}
    source = {}
    if isinstance(subclass_defs.get(feature_id), dict):
        source = subclass_defs.get(feature_id) or {}
    elif isinstance(class_defs.get(feature_id), dict):
        source = class_defs.get(feature_id) or {}
    return str(source.get("displayName") or source.get("name") or feature_id).strip()


def _command_model_summary(command_model: str) -> str:
    mapping = {
        "bonus_action_command": "Commands usually consume your Bonus Action.",
        "action_command": "Commands usually consume your Action.",
    }
    return mapping.get(command_model, "Command economy rules will be applied in runtime.")



def _imported_runtime_rows(document: dict[str, Any], key: str) -> list[dict[str, Any]]:
    import_meta = document.get("importMeta") if isinstance(document.get("importMeta"), dict) else {}
    rows = import_meta.get(key) if isinstance(import_meta.get(key), list) else []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("displayName") or "").strip()
        if not name:
            continue
        item = _clone(row)
        item.setdefault("id", f"ddb-import-{key}-{idx}")
        item.setdefault("displayName", name)
        item.setdefault("source", "D&D Beyond import")
        item.setdefault("tags", ["dndbeyond", "imported"])
        dedupe = f"{str(item.get('id') or '').lower()}::{name.lower()}::{str(item.get('actionType') or item.get('type') or '').lower()}"
        if dedupe in seen:
            continue
        seen.add(dedupe)
        out.append(item)
    return out


def _bucket_imported_actions(document: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    buckets = {"actions": [], "bonusActions": [], "reactions": [], "passives": []}
    for row in _imported_runtime_rows(document, "importedActions"):
        card = build_imported_action_card(row, context or {})
        if not card:
            continue
        action_type = str(card.get("actionType") or card.get("type") or "action").strip().lower()
        if "reaction" in action_type:
            buckets["reactions"].append(card)
        elif "bonus" in action_type:
            buckets["bonusActions"].append(card)
        elif action_type in {"passive", "none", "no action"}:
            buckets["passives"].append(card)
        else:
            buckets["actions"].append(card)
    return buckets

def _build_runtime_summon_actions(
    document: dict[str, Any],
    runtime_classes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summons = document.get("summons") if isinstance(document.get("summons"), dict) else {}
    unlocked_templates = [
        str(template_id or "").strip().lower()
        for template_id in (summons.get("unlockedTemplates") or [])
        if str(template_id or "").strip()
    ]
    if not unlocked_templates:
        return []

    classes = document.get("classes") if isinstance(document.get("classes"), list) else []
    primary_class = classes[0] if classes and isinstance(classes[0], dict) else {}
    class_id = str(primary_class.get("classId") or primary_class.get("id") or primary_class.get("name") or "").strip().lower()
    subclass_id = str(primary_class.get("subclassId") or "").strip().lower()
    class_catalog = get_class_catalog_row(class_id) if class_id else None
    subclass_catalog = get_subclass_catalog_row(subclass_id) if subclass_id else None

    selected_variants = summons.get("selectedVariants") if isinstance(summons.get("selectedVariants"), dict) else {}
    active_summons = summons.get("activeSummons") if isinstance(summons.get("activeSummons"), list) else []

    template_rows: list[dict[str, Any]] = []
    seen_template_ids: set[str] = set()
    for template_id in unlocked_templates:
        row = get_summon_template(template_id)
        if isinstance(row, dict):
            template_rows.append(row)
            seen_template_ids.add(str(row.get("id") or "").strip().lower())
    for active in active_summons:
        if not isinstance(active, dict):
            continue
        active_template_id = str(active.get("templateId") or active.get("summonTemplateId") or "").strip().lower()
        if not active_template_id or active_template_id in seen_template_ids:
            continue
        row = get_summon_template(active_template_id)
        if isinstance(row, dict):
            template_rows.append(row)
            seen_template_ids.add(active_template_id)
    if not template_rows:
        return []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in template_rows:
        group_key = str(row.get("variantGroup") or row.get("id") or "").strip().lower()
        if not group_key:
            continue
        grouped.setdefault(group_key, []).append(row)

    out: list[dict[str, Any]] = []
    for group_key, rows in grouped.items():
        primary = rows[0] if rows else {}
        source_feature_id = str(primary.get("sourceFeatureId") or "").strip().lower()
        source_feature_name = _resolve_summon_feature_name(
            feature_id=source_feature_id,
            class_catalog=class_catalog if isinstance(class_catalog, dict) else None,
            subclass_catalog=subclass_catalog if isinstance(subclass_catalog, dict) else None,
        ) if source_feature_id else "Summon Feature"
        selected_variant = str(selected_variants.get(group_key) or "").strip().lower()
        if not selected_variant and rows:
            selected_variant = str(rows[0].get("id") or "").strip().lower()
        unlocked_variant_ids = [str(row.get("id") or "").strip().lower() for row in rows if str(row.get("id") or "").strip()]
        variant_names = [str(row.get("displayName") or row.get("tokenName") or row.get("id") or "").strip() for row in rows]
        selected_variant_name = next(
            (
                str(row.get("displayName") or row.get("tokenName") or row.get("id") or "").strip()
                for row in rows
                if str(row.get("id") or "").strip().lower() == selected_variant
            ),
            (variant_names[0] if variant_names else str(primary.get("displayName") or primary.get("tokenName") or "Summon").strip()),
        )
        max_active = _safe_int(primary.get("maxActive"), 1, minimum=0)
        active_count = 0
        active_rows: list[dict[str, Any]] = []
        for active in active_summons:
            if not isinstance(active, dict):
                continue
            if str(active.get("status") or "active").strip().lower() not in {"", "active"}:
                continue
            active_template_id = str(active.get("templateId") or active.get("summonTemplateId") or active.get("id") or "").strip().lower()
            if active_template_id and active_template_id in unlocked_variant_ids:
                active_count += 1
                active_rows.append(
                    {
                        "id": str(active.get("id") or "").strip(),
                        "tokenId": str(active.get("tokenId") or "").strip(),
                        "variantId": str(active.get("variantId") or active_template_id).strip().lower(),
                        "variantName": next(
                            (
                                str(row.get("displayName") or row.get("tokenName") or row.get("id") or "").strip()
                                for row in rows
                                if str(row.get("id") or "").strip().lower() == str(active.get("variantId") or active_template_id).strip().lower()
                            ),
                            str(active.get("variantId") or active_template_id).strip(),
                        ),
                        "mapContext": str(active.get("mapContext") or active.get("sceneId") or "").strip(),
                        "status": str(active.get("status") or "active").strip().lower() or "active",
                        "actorName": str(((active.get("actor") or {}).get("name") or "")).strip(),
                        "commandModel": str(((active.get("actor") or {}).get("commandModel") or primary.get("commandModel") or "")).strip().lower(),
                        "actions": copy.deepcopy(((active.get("actor") or {}).get("actions") or [])),
                    }
                )
        summon_category = str(primary.get("summonCategory") or "").strip().lower()
        entity_kind = str(primary.get("entityKind") or ("creature" if bool(primary.get("isCreature", True)) else "effect")).strip().lower()
        is_creature = bool(primary.get("isCreature", True))
        action_label = "Deploy" if (not is_creature or summon_category in {"deployable", "construct", "turret", "cannon", "device"}) else "Summon"
        command_model = str(primary.get("commandModel") or "").strip().lower()
        replace_on_resummon = bool(primary.get("replaceOnResummon"))
        summary_bits = [
            f"{action_label} {selected_variant_name}."
        ]
        if len(variant_names) > 1:
            summary_bits.append("Variants: " + ", ".join(variant_names[:6]))
        summary_bits.append(f"Active {active_count}/{max_active}.")
        if replace_on_resummon:
            summary_bits.append("Re-summoning replaces an existing summon.")
        out.append(
            {
                "id": f"summon:{group_key}",
                "displayName": f"{action_label} {str(primary.get('tokenName') or primary.get('displayName') or 'Companion').strip()}",
                "sourceFeatureId": source_feature_id,
                "sourceFeatureName": source_feature_name,
                "sourceClassId": str(primary.get("sourceClassId") or class_id or "").strip().lower(),
                "sourceSubclassId": str(primary.get("sourceSubclassId") or subclass_id or "").strip().lower(),
                "summonGroupId": group_key,
                "summonTemplateId": selected_variant or str(primary.get("id") or "").strip().lower(),
                "variants": [
                    {
                        "id": str(row.get("id") or "").strip().lower(),
                        "displayName": str(row.get("displayName") or row.get("tokenName") or row.get("id") or "").strip(),
                        "tags": list(row.get("tags") or []),
                    }
                    for row in rows
                ],
                "selectedVariantId": selected_variant,
                "selectedVariantName": selected_variant_name,
                "actionType": action_label,
                "entityKind": entity_kind,
                "isCreature": is_creature,
                "actionSurfaceType": str(primary.get("actionSurfaceType") or ("summoned_creature" if is_creature else "deployed_field_effect")).strip().lower(),
                "placementRules": copy.deepcopy(primary.get("placementRules") or {}),
                "interactionModel": {
                    "controllable": bool(is_creature or entity_kind in {"device", "object"}),
                    "selectable": True,
                    "inspectable": True,
                    "destructible": bool(primary.get("destructible", True)),
                    "triggerable": bool(entity_kind in {"device", "trap", "ward", "effect"}),
                    "passive": bool(entity_kind in {"ward", "effect"} and not bool(primary.get("destructible", True))),
                    "ownerActivated": bool((primary.get("ownershipModel") or {}).get("ownerActivated", True)),
                    "stationary": bool((primary.get("placementRules") or {}).get("stationary", False)),
                },
                "commandModel": command_model,
                "commandModelSummary": _command_model_summary(command_model),
                "maxActive": max_active,
                "currentActiveCount": active_count,
                "replaceOnResummon": replace_on_resummon,
                "activeSummons": active_rows,
                "activeSummonActionCount": sum(
                    len(row.get("actions") or []) if isinstance(row.get("actions"), list) else 0
                    for row in active_rows
                ),
                "shortSummary": " ".join(bit for bit in summary_bits if bit).strip(),
                "tags": sorted({str(tag).strip() for row in rows for tag in (row.get("tags") or []) if str(tag).strip()}),
                "summonDisplayName": str(primary.get("displayName") or primary.get("tokenName") or "").strip(),
            }
        )
    return out


def resolve_character_runtime(document: Any) -> dict:
    """Resolve canonical character document into runtime payload.

    This is intentionally conservative and only computes stable core fields.
    TODO: replace stubs with ruleset/species/class aware calculators.
    """
    normalized = ensure_character_defaults(document)
    normalized = sync_summon_unlocks_from_features(normalized)
    runtime = default_runtime()

    level_total = _compute_total_level(normalized)
    proficiency_bonus = _safe_int(normalized.get("proficiencyBonus"), _compute_proficiency_bonus(level_total), minimum=0)

    runtime["levelTotal"] = level_total
    runtime["proficiencyBonus"] = proficiency_bonus

    species = normalized.get("species") if isinstance(normalized.get("species"), dict) else {}
    speed = _safe_int(species.get("speed"), 30, minimum=0)
    runtime["speed"] = {"walk": speed}
    runtime_classes = _resolve_runtime_classes(normalized)
    runtime["hp"] = _compute_base_hp(normalized, level_total, runtime_classes)
    runtime["hp"] = _runtime_hp_from_document(normalized, runtime["hp"])
    runtime["classes"] = runtime_classes
    if runtime_classes:
        primary = runtime_classes[0]
        runtime["classDisplay"] = {
            "classId": primary.get("classId") or "",
            "className": primary.get("name") or "",
            "subclassId": primary.get("subclassId") or "",
            "subclassName": primary.get("subclassName") or "",
            "subclassUnlockLevel": _safe_int(primary.get("subclassUnlockLevel"), 0, minimum=0),
            "subclassUnlocked": bool(primary.get("subclassUnlocked")),
            "subclassPending": bool(primary.get("subclassPending")),
            "subclassFeatureUnlocksByLevel": _clone(primary.get("subclassFeatureUnlocksByLevel") or {}),
        }
    else:
        runtime["classDisplay"] = {
            "classId": "",
            "className": "",
            "subclassId": "",
            "subclassName": "",
            "subclassUnlockLevel": 0,
            "subclassUnlocked": False,
            "subclassPending": False,
            "subclassFeatureUnlocksByLevel": {},
        }

    abilities = normalized.get("abilities") if isinstance(normalized.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    str_mod = _ability_modifier(scores.get("str", 10))
    dex_mod = _ability_modifier(scores.get("dex", 10))
    con_mod = _ability_modifier(scores.get("con", 10))
    int_mod = _ability_modifier(scores.get("int", 10))
    wis_mod = _ability_modifier(scores.get("wis", 10))
    cha_mod = _ability_modifier(scores.get("cha", 10))
    runtime["ac"] = _safe_int(
        normalized.get("ac"),
        max(10, 10 + dex_mod),
        minimum=1,
    )

    senses = species.get("senses") if isinstance(species.get("senses"), list) else []
    darkvision = _safe_int(runtime["senses"].get("darkvision"), 0, minimum=0)
    for sense in senses:
        if not isinstance(sense, dict):
            continue
        sense_name = str(sense.get("type") or sense.get("name") or "").strip().lower()
        sense_range = _safe_int(sense.get("range") or sense.get("radius"), 0, minimum=0)
        if sense_name == "darkvision":
            darkvision = max(darkvision, sense_range)
    runtime["senses"]["darkvision"] = darkvision
    imported_passives = normalized.get("passives") if isinstance(normalized.get("passives"), dict) else {}
    runtime["senses"]["passivePerception"] = _safe_int(imported_passives.get("perception"), 10 + wis_mod, minimum=0)
    if imported_passives.get("insight") is not None:
        runtime["senses"]["passiveInsight"] = _safe_int(imported_passives.get("insight"), 10 + wis_mod, minimum=0)
    if imported_passives.get("investigation") is not None:
        runtime["senses"]["passiveInvestigation"] = _safe_int(imported_passives.get("investigation"), 10 + int_mod, minimum=0)

    imported_skills = (abilities.get("skills") if isinstance(abilities.get("skills"), dict) else {})
    if imported_skills:
        runtime["skills"] = _clone(imported_skills)

    # TODO(character-native): class/species/background feature resolution.
    # TODO(character-native): spell list, slot, and resource progression resolution.
    # TODO(character-native): rules-content lookup for actions/reactions/passives.

    spell_state = normalized.get("spellState") if isinstance(normalized.get("spellState"), dict) else {}
    primary_class = runtime_classes[0] if runtime_classes else {}
    primary_class_id = str(primary_class.get("classId") or "").strip().lower()
    primary_class_level = _safe_int(primary_class.get("level"), 1, minimum=1)
    primary_catalog = get_class_catalog_row(primary_class_id) if primary_class_id else None
    spellcasting_ability = str((primary_catalog or {}).get("spellcastingAbility") or "").strip().lower()
    spellcasting_mod = _ability_modifier(scores.get(spellcasting_ability, 10)) if spellcasting_ability else 0
    is_caster = bool(spellcasting_ability)
    class_spell_slots = {}
    if isinstance((primary_catalog or {}).get("spellSlots"), dict):
        class_spell_slots = (primary_catalog or {}).get("spellSlots", {}).get(str(primary_class_level), {})
        if not isinstance(class_spell_slots, dict):
            class_spell_slots = {}
    pact_magic = (primary_catalog or {}).get("pactMagic") if isinstance((primary_catalog or {}).get("pactMagic"), dict) else {}
    pact_slots_by_level = pact_magic.get("slotsPerLevel") if isinstance(pact_magic.get("slotsPerLevel"), dict) else {}
    pact_slot_levels = pact_magic.get("slotLevel") if isinstance(pact_magic.get("slotLevel"), dict) else {}
    pact_slot_count = _safe_int(pact_slots_by_level.get(str(primary_class_level)), 0, minimum=0)
    pact_slot_level = _safe_int(pact_slot_levels.get(str(primary_class_level)), 0, minimum=0)

    spell_manifest = build_character_spell_manifest(normalized)
    runtime["spellAccess"] = {
        "ability": spellcasting_ability,
        "attackBonus": proficiency_bonus + spellcasting_mod if is_caster else 0,
        "saveDc": 8 + proficiency_bonus + spellcasting_mod if is_caster else 8,
        "slots": _clone(class_spell_slots or spell_state.get("slots") or {}),
        "known": list(spell_manifest.get("known") or spell_state.get("known") or []),
        "prepared": list(spell_manifest.get("prepared") or spell_state.get("prepared") or []),
        "availableBySubclass": _resolve_subclass_available_spells(runtime_classes),
        "limits": _clone(spell_manifest.get("limits") or {}),
        "validation": _clone(spell_manifest.get("validation") or {}),
        "cards": _clone(spell_manifest.get("cards") or []),
        "pactMagic": {
            "enabled": bool(pact_magic),
            "slotCount": pact_slot_count,
            "slotLevel": pact_slot_level,
            "recoveryType": str(pact_magic.get("recoveryType") or "").strip(),
            "note": str(pact_magic.get("note") or "").strip(),
        },
    }

    runtime_feature_sets = []
    class_mechanics_by_class: dict[str, dict[str, Any]] = {}
    for class_row in runtime_classes:
        if not isinstance(class_row, dict):
            continue
        class_id = str(class_row.get("classId") or "").strip().lower()
        subclass_id = str(class_row.get("subclassId") or "").strip().lower()
        class_level = _safe_int(class_row.get("level"), 1, minimum=1)
        catalog_row = get_class_catalog_row(class_id)
        if isinstance(catalog_row, dict):
            progression_rows = catalog_row.get("progressionTable") if isinstance(catalog_row.get("progressionTable"), list) else []
            level_row = next(
                (
                    row for row in progression_rows
                    if isinstance(row, dict) and _safe_int(row.get("level"), 0, minimum=0) == class_level
                ),
                {},
            )
            mechanics = level_row.get("classMechanics") if isinstance(level_row, dict) and isinstance(level_row.get("classMechanics"), dict) else {}
            if isinstance(mechanics, dict) and mechanics:
                class_mechanics_by_class[class_id] = _clone(mechanics)
        runtime_feature_sets.append(
            build_runtime_feature_payload(
                catalog_row,
                class_name=str(class_row.get("name") or class_row.get("classId") or "Class"),
                level=class_level,
                subclass_row=get_subclass_catalog_row(subclass_id) if subclass_id else None,
                ability_scores=scores,
            )
        )

    merged_resources = []
    seen_resource_keys = set()
    for payload in runtime_feature_sets:
        for row in payload.get("resources") or []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id") or "").strip()
            dedupe_key = _resource_dedupe_key(rid, row.get("name"))
            if not dedupe_key or dedupe_key in seen_resource_keys:
                continue
            seen_resource_keys.add(dedupe_key)
            merged_resources.append(_clone(row))

    native_feature_names = {
        str(item.get("name") or item.get("displayName") or "").strip().lower()
        for payload in runtime_feature_sets
        for item in (payload.get("classFeatures") or [])
        if isinstance(item, dict) and str(item.get("name") or item.get("displayName") or "").strip()
    }
    native_action_names = {
        str(item.get("name") or item.get("displayName") or "").strip().lower()
        for payload in runtime_feature_sets
        for bucket_name in ("actions", "bonusActions", "reactions", "passives")
        for item in (payload.get(bucket_name) or [])
        if isinstance(item, dict) and str(item.get("name") or item.get("displayName") or "").strip()
    }
    imported_action_buckets = _bucket_imported_actions(normalized, {"native_names": native_action_names})
    imported_features = [
        card for card in (
            build_imported_feature_card(row, {"native_names": native_feature_names})
            for row in _imported_runtime_rows(normalized, "importedFeatures")
        )
        if card
    ]

    runtime["resources"] = merged_resources
    runtime["actions"] = [item for payload in runtime_feature_sets for item in (payload.get("actions") or [])] + imported_action_buckets["actions"]
    runtime["bonusActions"] = [item for payload in runtime_feature_sets for item in (payload.get("bonusActions") or [])] + imported_action_buckets["bonusActions"]
    runtime["reactions"] = [item for payload in runtime_feature_sets for item in (payload.get("reactions") or [])] + imported_action_buckets["reactions"]
    runtime["passives"] = [item for payload in runtime_feature_sets for item in (payload.get("passives") or [])] + imported_action_buckets["passives"]
    runtime["classFeatures"] = [item for payload in runtime_feature_sets for item in (payload.get("classFeatures") or [])] + imported_features
    runtime["nativeActions"] = {
        "actions": _clone(runtime["actions"]),
        "bonusActions": _clone(runtime["bonusActions"]),
        "reactions": _clone(runtime["reactions"]),
        "passives": _clone(runtime["passives"]),
    }
    runtime["nativeFeatures"] = _clone(runtime["classFeatures"])
    has_first_turn_path = bool(runtime["actions"] or runtime["bonusActions"] or runtime.get("summonActions"))
    if not has_first_turn_path:
        runtime["actions"] = [_build_first_turn_strike_action(proficiency_bonus=proficiency_bonus, str_mod=str_mod)]
    selected_runtime_features = []
    for class_row in runtime_classes:
        if not isinstance(class_row, dict):
            continue
        class_name = str(class_row.get("name") or class_row.get("classId") or "Class").strip()
        class_level = _safe_int(class_row.get("level"), 1, minimum=1)
        class_id = str(class_row.get("classId") or "").strip().lower()
        subclass_id = str(class_row.get("subclassId") or "").strip().lower()
        class_defs = build_class_feature_definitions(get_class_catalog_row(class_id) or {})
        subclass_defs = build_subclass_feature_definitions(get_subclass_catalog_row(subclass_id) or {}) if subclass_id else {}
        for row in class_row.get("selectedFeatures") or []:
            if not isinstance(row, dict):
                continue
            feature_id = str(row.get("id") or "").strip()
            class_def = class_defs.get(feature_id) if isinstance(class_defs, dict) else {}
            subclass_def = subclass_defs.get(feature_id) if isinstance(subclass_defs, dict) else {}
            definition = subclass_def if isinstance(subclass_def, dict) and subclass_def else class_def if isinstance(class_def, dict) else {}
            feature_name = str(row.get("displayName") or definition.get("displayName") or feature_id or "Feature Choice").strip()
            selected_choice = row.get("selectedChoice")
            selected_choice_id = str(selected_choice or "").strip()
            selected_choice_name = selected_choice_id
            selected_choice_description = ""
            for choice in (definition.get("choices") if isinstance(definition.get("choices"), list) else []):
                if not isinstance(choice, dict):
                    continue
                if str(choice.get("id") or "").strip().lower() == selected_choice_id.lower():
                    selected_choice_name = str(choice.get("name") or selected_choice_id).strip()
                    selected_choice_description = str(choice.get("description") or "").strip()
                    break
            is_subclass_feature = isinstance(subclass_def, dict) and bool(subclass_def)
            feature_description = str(row.get("description") or definition.get("description") or "").strip()
            if selected_choice_description:
                feature_description = (feature_description + "\n\n" + selected_choice_description).strip()
            selected_runtime_features.append(
                {
                    "id": feature_id or f"selected-{len(selected_runtime_features)+1}",
                    "name": feature_name + (f" — {selected_choice_name}" if selected_choice_name else ""),
                    "section": str(definition.get("section") or "Class Features"),
                    "type": str(definition.get("type") or "passive"),
                    "className": class_name,
                    "subclassName": str(class_row.get("subclassName") or "").strip(),
                    "minLevel": class_level,
                    "resourceName": str(definition.get("resourceName") or ""),
                    "trackUses": bool(definition.get("trackUses")),
                    "tags": list(definition.get("tags") or ["selection", "build-choice"]),
                    "summary": str(definition.get("summary") or row.get("description") or "").strip(),
                    "description": feature_description,
                    "range": str(definition.get("range") or ""),
                    "duration": str(definition.get("duration") or ""),
                    "save": str(definition.get("save") or ""),
                    "trigger": str(definition.get("trigger") or ""),
                    "usage": str(definition.get("usage") or ""),
                    "recovery": str(definition.get("recovery") or ""),
                    "effect": f"Selected option: {selected_choice_name}" if selected_choice_name else "",
                    "isSubclass": is_subclass_feature,
                    "kind": "class",
                    "source": "native-selected-feature",
                }
            )
    if selected_runtime_features:
        runtime["classFeatures"] = runtime["classFeatures"] + selected_runtime_features
    runtime["classMechanicsByClass"] = class_mechanics_by_class
    runtime["classMechanics"] = _clone(class_mechanics_by_class.get(primary_class_id) or {})

    runtime["originTraits"] = _resolve_runtime_origin_traits(normalized)
    runtime["backgroundFeatures"] = _resolve_runtime_background_features(normalized)
    runtime["featFeatures"] = _resolve_runtime_feat_features(normalized)
    runtime["nativeFeatures"] = _clone(runtime["classFeatures"] + runtime["originTraits"] + runtime["backgroundFeatures"] + runtime["featFeatures"])
    runtime["summonActions"] = _build_runtime_summon_actions(normalized, runtime_classes)

    class_saving_throws = []
    if isinstance((primary_catalog or {}).get("savingThrows"), list):
        class_saving_throws = [
            str(value or "").strip().lower()
            for value in (primary_catalog or {}).get("savingThrows", [])
            if str(value or "").strip()
        ]
    saving_throw_lookup = {
        "str": str_mod,
        "dex": dex_mod,
        "con": con_mod,
        "int": int_mod,
        "wis": wis_mod,
        "cha": cha_mod,
    }
    saving_throws = {
        key: base + (proficiency_bonus if key in class_saving_throws else 0)
        for key, base in saving_throw_lookup.items()
    }
    imported_saves = abilities.get("saves") if isinstance(abilities.get("saves"), dict) else {}
    for key, value in imported_saves.items():
        ability_key = str(key or "").strip().lower()
        if ability_key in saving_throws:
            saving_throws[ability_key] = _safe_int(value, saving_throws[ability_key])

    walk_speed = _safe_int(species.get("speed"), _safe_int(runtime["speed"].get("walk"), 30, minimum=0), minimum=0)
    if isinstance(species.get("movement"), dict):
        walk_speed = _safe_int(species.get("movement", {}).get("walk"), walk_speed, minimum=0)
    armor_class = max(10, 10 + dex_mod)
    if primary_class_id == "barbarian":
        armor_class = max(armor_class, 10 + dex_mod + con_mod)
    elif primary_class_id == "monk":
        armor_class = max(armor_class, 10 + dex_mod + wis_mod)
    imported_ac = _safe_int(normalized.get("ac"), 0, minimum=0)
    runtime["ac"] = _compute_equipment_ac(normalized, dex_mod=dex_mod, fallback_ac=armor_class)
    runtime["ac"] = max(imported_ac, runtime["ac"])
    runtime["speed"]["walk"] = walk_speed
    imported_initiative = _safe_int(normalized.get("initiative"), dex_mod)

    runtime["combat"] = {
        "ac": runtime["ac"],
        "maxHP": runtime["hp"]["max"],
        "currentHP": runtime["hp"]["current"],
        "tempHP": runtime["hp"]["temp"],
        "initiative": imported_initiative,
        "speed": walk_speed,
        "proficiencyBonus": proficiency_bonus,
        "attackBonus": {
            "str": str_mod + proficiency_bonus,
            "dex": dex_mod + proficiency_bonus,
            "spell": (spellcasting_mod + proficiency_bonus) if is_caster else None,
        },
        "savingThrows": saving_throws,
        "spellSaveDC": (8 + proficiency_bonus + spellcasting_mod) if is_caster else None,
        "spellAttackBonus": (spellcasting_mod + proficiency_bonus) if is_caster else None,
        "darkvision": darkvision,
        "senses": _clone(runtime.get("senses") or {}),
    }

    runtime["derivedTags"] = [
        f"rulesMode:{normalized.get('rulesMode')}",
        f"sourceMode:{normalized.get('sourceMode')}",
    ]

    talent_resolution = resolve_talents_for_runtime(normalized, runtime)
    runtime["talents"] = talent_resolution.get("talents") or []
    runtime["talentGrants"] = talent_resolution.get("grants") or []
    apply_talent_grants(runtime, runtime["talentGrants"])

    awakening_resolution = resolve_awakening_for_runtime(normalized, runtime)
    runtime["awakening"] = awakening_resolution
    runtime["awakeningGrants"] = awakening_resolution.get("grants") or []
    apply_awakening_grants(runtime, runtime["awakeningGrants"])

    character_audit_result = _build_character_audit_result(
        normalized,
        runtime_classes=runtime_classes,
        runtime=runtime,
        dex_mod=dex_mod,
        con_mod=con_mod,
        wis_mod=wis_mod,
        spellcasting_ability=spellcasting_ability,
        spellcasting_mod=spellcasting_mod,
        is_caster=is_caster,
        primary_class_id=primary_class_id,
    )
    runtime["characterAudit"] = _clone(character_audit_result)

    audit = normalized.get("audit") if isinstance(normalized.get("audit"), dict) else {}
    audit["resolverVersion"] = _RESOLVER_VERSION
    audit["lastResolvedAt"] = time.time()
    audit["characterAudit"] = _clone(character_audit_result)
    normalized["audit"] = audit

    return {
        "document": normalized,
        "runtime": runtime,
    }
