"""Summon unlock normalization and feature-driven persistence helpers (Pass A)."""
from __future__ import annotations

import copy
from typing import Any

from server.character.rules_catalog import get_class_catalog_row, get_subclass_catalog_row
from server.character.summon_catalog import get_summon_template


def default_summon_state() -> dict[str, Any]:
    return {
        "unlockedTemplates": [],
        "unlockedGroups": [],
        "selectedVariants": {},
        "activeSummons": [],
        "rules": {},
        "lastUpdatedFromFeatures": [],
    }


def _safe_lower_str(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_selected_variants(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key, selected in value.items():
        group = _safe_lower_str(key)
        template_id = _safe_lower_str(selected)
        if group and template_id:
            out[group] = template_id
    return out


def _normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in values:
        key = _safe_lower_str(row)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _normalize_active_summon_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    source = copy.deepcopy(raw.get("source")) if isinstance(raw.get("source"), dict) else {}
    source_class = _safe_lower_str(raw.get("sourceClassId") or source.get("classId"))
    source_subclass = _safe_lower_str(raw.get("sourceSubclassId") or source.get("subclassId"))
    source_feature = _safe_lower_str(raw.get("sourceFeatureId") or source.get("featureId"))
    summon_group_id = _safe_lower_str(raw.get("summonGroupId") or source.get("variantGroup"))
    template_id = _safe_lower_str(raw.get("templateId") or raw.get("summonTemplateId") or raw.get("id"))
    variant_id = _safe_lower_str(raw.get("variantId") or raw.get("variant") or template_id)
    token_id = str(raw.get("tokenId") or "").strip()
    owner_user_id = str(raw.get("ownerUserId") or (raw.get("owner") or {}).get("userId") or "").strip()
    owner_profile_id = str(raw.get("ownerProfileId") or (raw.get("owner") or {}).get("profileId") or "").strip()
    map_context = str(raw.get("mapContext") or raw.get("sceneId") or "").strip()[:80]
    source_origin = _safe_lower_str(raw.get("sourceOriginType") or raw.get("summonOrigin") or source.get("summonOrigin"))
    if not source_origin:
        source_origin = "spell" if _safe_lower_str(raw.get("spellId") or source.get("spellId")) else "feature"
    control_model = _safe_lower_str(raw.get("controlModel") or raw.get("commandModel"))
    if not control_model:
        control_model = "owner_controlled"
    entity_kind = _safe_lower_str(raw.get("entityKind"))
    if not entity_kind:
        actor_type = _safe_lower_str((raw.get("actor") or {}).get("actorType") if isinstance(raw.get("actor"), dict) else "")
        if actor_type in {"deployable", "spell_effect"}:
            entity_kind = actor_type
        elif source_origin == "spell":
            entity_kind = "spell_effect"
        else:
            entity_kind = "creature"
    created_at = raw.get("createdAt", raw.get("spawnedAt"))
    updated_at = raw.get("updatedAt", created_at)
    status = _safe_lower_str(raw.get("status") or "active") or "active"
    try:
        max_active = max(0, int(raw.get("maxActive")))
    except Exception:
        max_active = None
    normalized = {
        "id": str(raw.get("id") or "").strip() or template_id or token_id,
        "templateId": template_id,
        "summonTemplateId": template_id,
        "summonGroupId": summon_group_id,
        "variantId": variant_id,
        "variant": variant_id,
        "entityId": str(raw.get("entityId") or raw.get("id") or "").strip() or template_id or token_id,
        "entityKind": entity_kind,
        "sourceClassId": source_class,
        "sourceSubclassId": source_subclass,
        "sourceFeatureId": source_feature,
        "ownerUserId": owner_user_id,
        "ownerProfileId": owner_profile_id,
        "tokenId": token_id,
        "sceneId": map_context,
        "mapContext": map_context,
        "createdAt": created_at,
        "updatedAt": updated_at,
        "status": status,
        "sourceOriginType": source_origin,
        "summonOrigin": _safe_lower_str(raw.get("summonOrigin") or source.get("summonOrigin")),
        "spellId": _safe_lower_str(raw.get("spellId") or source.get("spellId")),
        "temporary": bool(raw.get("temporary")),
        "concentrationRequired": bool(raw.get("concentrationRequired")),
        "durationSeconds": int(raw.get("durationSeconds") or 0) if str(raw.get("durationSeconds") or "").strip() else 0,
        "expiresAt": raw.get("expiresAt"),
        "cleanupPolicy": list(raw.get("cleanupPolicy") or []) if isinstance(raw.get("cleanupPolicy"), list) else [],
        "replaceOnResummon": bool(raw.get("replaceOnResummon")),
        "maxActive": max_active,
        "controlModel": control_model,
        "commandModel": _safe_lower_str(raw.get("commandModel") or (raw.get("actor") or {}).get("commandModel") if isinstance(raw.get("actor"), dict) else ""),
        "lifecycle": {
            "temporary": bool(raw.get("temporary")),
            "status": status,
            "durationSeconds": int(raw.get("durationSeconds") or 0) if str(raw.get("durationSeconds") or "").strip() else 0,
            "expiresAt": raw.get("expiresAt"),
            "cleanupPolicy": list(raw.get("cleanupPolicy") or []) if isinstance(raw.get("cleanupPolicy"), list) else [],
        },
        "source": source,
    }
    if isinstance(raw.get("actor"), dict):
        normalized["actor"] = copy.deepcopy(raw.get("actor"))
    return normalized


def _normalize_active_summons(src: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[Any] = []
    if isinstance(src.get("activeSummons"), list):
        rows.extend(list(src.get("activeSummons") or []))
    # Backward compatibility: single active summon slot used in earlier passes.
    for legacy_key in ("activeSummon", "active", "currentSummon"):
        legacy = src.get(legacy_key)
        if isinstance(legacy, dict):
            rows.append(legacy)
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in rows:
        normalized = _normalize_active_summon_entry(raw)
        if not normalized:
            continue
        row_id = str(normalized.get("id") or "").strip()
        dedupe_key = row_id or str(normalized.get("tokenId") or "").strip() or str(normalized.get("templateId") or "").strip()
        if not dedupe_key or dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        out.append(normalized)
    return out


def normalize_summon_state(raw: Any) -> dict[str, Any]:
    base = default_summon_state()
    src = raw if isinstance(raw, dict) else {}
    base["unlockedTemplates"] = _normalize_list(src.get("unlockedTemplates"))
    base["unlockedGroups"] = _normalize_list(src.get("unlockedGroups"))
    base["selectedVariants"] = _normalize_selected_variants(src.get("selectedVariants"))
    base["activeSummons"] = _normalize_active_summons(src)
    base["rules"] = copy.deepcopy(src.get("rules")) if isinstance(src.get("rules"), dict) else {}
    base["lastUpdatedFromFeatures"] = _normalize_list(src.get("lastUpdatedFromFeatures"))
    return base


def _selected_feature_choices(primary_class: dict[str, Any]) -> dict[str, Any]:
    selected_features = primary_class.get("selectedFeatures") if isinstance(primary_class.get("selectedFeatures"), list) else []
    out: dict[str, Any] = {}
    for row in selected_features:
        if not isinstance(row, dict):
            continue
        feature_id = _safe_lower_str(row.get("id"))
        if not feature_id:
            continue
        out[feature_id] = row.get("selectedChoice")
    return out


def _extract_choice_id(choice_value: Any, *, default: str = "") -> str:
    if isinstance(choice_value, str):
        return _safe_lower_str(choice_value) or default
    if isinstance(choice_value, dict):
        for key in ("id", "choiceId", "selected", "value", "templateId"):
            value = _safe_lower_str(choice_value.get(key))
            if value:
                return value
    if isinstance(choice_value, list):
        for row in choice_value:
            value = _extract_choice_id(row)
            if value:
                return value
    return default


def _apply_summon_feature_unlock(
    state: dict[str, Any],
    *,
    feature_id: str,
    feature_def: dict[str, Any],
    selected_choice: Any,
    applied_features: set[str],
) -> None:
    if not isinstance(feature_def, dict) or not bool(feature_def.get("grantsSummons")):
        return
    applied_features.add(feature_id)

    template_ids = _normalize_list(feature_def.get("summonTemplateIds"))
    selected_variants = state.get("selectedVariants") if isinstance(state.get("selectedVariants"), dict) else {}

    unlock_mode = _safe_lower_str(feature_def.get("summonUnlockMode"))
    default_template_id = _safe_lower_str(feature_def.get("defaultSummonTemplateId"))

    if unlock_mode == "feature_choice_map":
        choice_map = feature_def.get("summonChoiceMap") if isinstance(feature_def.get("summonChoiceMap"), dict) else {}
        selected_choice_id = _extract_choice_id(selected_choice)
        selected_map = choice_map.get(selected_choice_id) if isinstance(choice_map.get(selected_choice_id), dict) else {}
        if not selected_map and default_template_id:
            selected_map = choice_map.get(default_template_id) if isinstance(choice_map.get(default_template_id), dict) else {}
        if selected_map:
            template_ids.extend(_normalize_list(selected_map.get("summonTemplateIds")))
            default_template_id = _safe_lower_str(selected_map.get("defaultSummonTemplateId")) or default_template_id

    variant_group = _safe_lower_str(feature_def.get("variantGroup"))
    if not variant_group and template_ids:
        first_template = get_summon_template(template_ids[0])
        variant_group = _safe_lower_str((first_template or {}).get("variantGroup"))

    for template_id in template_ids:
        if not get_summon_template(template_id):
            continue
        if template_id not in state["unlockedTemplates"]:
            state["unlockedTemplates"].append(template_id)

    if variant_group and variant_group not in state["unlockedGroups"]:
        state["unlockedGroups"].append(variant_group)

    if bool(feature_def.get("summonVariantChoice")) and variant_group:
        selected_variant = _extract_choice_id(selected_choice)
        if not selected_variant:
            selected_variant = _safe_lower_str(selected_variants.get(variant_group))
        if not selected_variant:
            selected_variant = default_template_id
        if selected_variant and selected_variant in state["unlockedTemplates"]:
            selected_variants[variant_group] = selected_variant
    state["selectedVariants"] = selected_variants


def sync_summon_unlocks_from_features(document: Any) -> dict[str, Any]:
    canonical = document if isinstance(document, dict) else {}
    classes = canonical.get("classes") if isinstance(canonical.get("classes"), list) else []
    primary_class = classes[0] if classes and isinstance(classes[0], dict) else {}

    current_state = normalize_summon_state(canonical.get("summons"))
    state = normalize_summon_state(canonical.get("summons"))

    class_id = _safe_lower_str(primary_class.get("classId") or primary_class.get("id") or primary_class.get("name"))
    subclass_id = _safe_lower_str(primary_class.get("subclassId"))
    class_level = 1
    try:
        class_level = max(1, int(primary_class.get("level") or 1))
    except Exception:
        class_level = 1

    class_row = get_class_catalog_row(class_id) if class_id else None
    subclass_row = get_subclass_catalog_row(subclass_id) if subclass_id else None
    class_defs = class_row.get("featureDefinitions") if isinstance((class_row or {}).get("featureDefinitions"), dict) else {}
    subclass_defs = subclass_row.get("featureDefinitions") if isinstance((subclass_row or {}).get("featureDefinitions"), dict) else {}

    selected_choices = _selected_feature_choices(primary_class)
    applied_features: set[str] = set()

    for feature_id, selected_choice in selected_choices.items():
        feature_def = class_defs.get(feature_id) if isinstance(class_defs.get(feature_id), dict) else {}
        if not feature_def and isinstance(subclass_defs.get(feature_id), dict):
            feature_def = subclass_defs.get(feature_id)
        _apply_summon_feature_unlock(
            state,
            feature_id=feature_id,
            feature_def=feature_def,
            selected_choice=selected_choice,
            applied_features=applied_features,
        )

    unlocks_by_level = subclass_row.get("featureUnlocksByLevel") if isinstance((subclass_row or {}).get("featureUnlocksByLevel"), dict) else {}
    for level_key, feature_ids in unlocks_by_level.items():
        try:
            unlock_level = int(level_key)
        except Exception:
            continue
        if unlock_level > class_level:
            continue
        if not isinstance(feature_ids, list):
            continue
        for feature_id_raw in feature_ids:
            feature_id = _safe_lower_str(feature_id_raw)
            feature_def = subclass_defs.get(feature_id) if isinstance(subclass_defs.get(feature_id), dict) else {}
            _apply_summon_feature_unlock(
                state,
                feature_id=feature_id,
                feature_def=feature_def,
                selected_choice=selected_choices.get(feature_id),
                applied_features=applied_features,
            )

    state["lastUpdatedFromFeatures"] = sorted(applied_features)
    canonical["summons"] = normalize_summon_state(state)

    if canonical["summons"] == current_state:
        return canonical

    audit = canonical.get("audit") if isinstance(canonical.get("audit"), dict) else {}
    audit["dirty"] = True
    canonical["audit"] = audit
    return canonical
