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


def _compute_base_hp(document: dict, level_total: int, runtime_classes: list[dict[str, Any]]) -> dict:
    abilities = document.get("abilities") if isinstance(document.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    con_mod = _ability_modifier(scores.get("con", 10))

    hit_dice: list[dict[str, Any]] = []
    max_hp = 0
    classes = runtime_classes if isinstance(runtime_classes, list) else []
    if classes:
        for row in classes:
            if not isinstance(row, dict):
                continue
            lvl = _safe_int(row.get("level"), 1, minimum=1)
            class_id = str(row.get("classId") or "").strip().lower()
            class_catalog = get_class_catalog_row(class_id) if class_id else None
            hit_die = _safe_int((class_catalog or {}).get("hitDie"), 8, minimum=1)
            hit_die_average = max(1, (hit_die // 2) + 1)
            class_hp = max(1, (hit_die_average * lvl) + (con_mod * lvl))
            max_hp += class_hp
            hit_dice.append({"die": hit_die, "count": lvl, "classId": class_id})
    else:
        max_hp = max(1, level_total * (6 + con_mod))

    max_hp = max(1, max_hp)
    return {
        "max": max_hp,
        "current": max_hp,
        "temp": 0,
        "hitDice": hit_dice,
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

        # Maintain compatibility: keep class row carrying both subclassId + subclass display.
        if idx < len(classes) and isinstance(classes[idx], dict):
            classes[idx]["classId"] = class_id
            classes[idx]["name"] = class_name
            classes[idx]["level"] = level
            if subclass_id:
                classes[idx]["subclassId"] = subclass_id
            if subclass_display_name:
                classes[idx]["subclass"] = subclass_display_name

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
    for template_id in unlocked_templates:
        row = get_summon_template(template_id)
        if isinstance(row, dict):
            template_rows.append(row)
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
    proficiency_bonus = _compute_proficiency_bonus(level_total)

    runtime["levelTotal"] = level_total
    runtime["proficiencyBonus"] = proficiency_bonus

    species = normalized.get("species") if isinstance(normalized.get("species"), dict) else {}
    speed = _safe_int(species.get("speed"), 30, minimum=0)
    runtime["speed"] = {"walk": speed}
    runtime_classes = _resolve_runtime_classes(normalized)
    runtime["hp"] = _compute_base_hp(normalized, level_total, runtime_classes)
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
    runtime["ac"] = max(10, 10 + dex_mod)

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
    runtime["senses"]["passivePerception"] = 10 + wis_mod

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
    seen_resource_ids = set()
    for payload in runtime_feature_sets:
        for row in payload.get("resources") or []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id") or "").strip()
            if not rid or rid in seen_resource_ids:
                continue
            seen_resource_ids.add(rid)
            merged_resources.append(_clone(row))

    runtime["resources"] = merged_resources
    runtime["actions"] = [item for payload in runtime_feature_sets for item in (payload.get("actions") or [])]
    runtime["bonusActions"] = [item for payload in runtime_feature_sets for item in (payload.get("bonusActions") or [])]
    runtime["reactions"] = [item for payload in runtime_feature_sets for item in (payload.get("reactions") or [])]
    runtime["passives"] = [item for payload in runtime_feature_sets for item in (payload.get("passives") or [])]
    runtime["classFeatures"] = [item for payload in runtime_feature_sets for item in (payload.get("classFeatures") or [])]
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

    walk_speed = _safe_int(species.get("speed"), _safe_int(runtime["speed"].get("walk"), 30, minimum=0), minimum=0)
    if isinstance(species.get("movement"), dict):
        walk_speed = _safe_int(species.get("movement", {}).get("walk"), walk_speed, minimum=0)
    armor_class = max(10, 10 + dex_mod)
    if primary_class_id == "barbarian":
        armor_class = max(armor_class, 10 + dex_mod + con_mod)
    elif primary_class_id == "monk":
        armor_class = max(armor_class, 10 + dex_mod + wis_mod)
    runtime["ac"] = armor_class

    current_hp = _safe_int(
        normalized.get("currentHP"),
        _safe_int(
            (normalized.get("hp") if isinstance(normalized.get("hp"), dict) else {}).get("current"),
            _safe_int(runtime["hp"].get("current"), runtime["hp"]["max"]),
            minimum=0,
        ),
        minimum=0,
    )
    runtime["hp"]["current"] = min(runtime["hp"]["max"], current_hp or runtime["hp"]["max"])

    runtime["combat"] = {
        "ac": runtime["ac"],
        "maxHP": runtime["hp"]["max"],
        "currentHP": runtime["hp"]["current"],
        "initiative": dex_mod,
        "speed": walk_speed,
        "proficiencyBonus": proficiency_bonus,
        "attackBonus": {
            "str": str_mod + proficiency_bonus,
            "dex": dex_mod + proficiency_bonus,
            "spell": (spellcasting_mod + proficiency_bonus) if is_caster else None,
        },
        "savingThrows": saving_throws,
        "spellSaveDC": (8 + proficiency_bonus + spellcasting_mod) if is_caster else None,
        "darkvision": darkvision,
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

    audit = normalized.get("audit") if isinstance(normalized.get("audit"), dict) else {}
    audit["resolverVersion"] = _RESOLVER_VERSION
    audit["lastResolvedAt"] = time.time()
    normalized["audit"] = audit

    return {
        "document": normalized,
        "runtime": runtime,
    }
