"""Summon unlock normalization and feature-driven persistence helpers (Pass A)."""
from __future__ import annotations

import copy
from typing import Any

from server.character.rules_catalog import get_class_catalog_row, get_subclass_catalog_row
from server.character.summon_catalog import get_summon_template

SUMMON_DEPLOY_SCHEMA_VERSION = 3


def default_summon_state() -> dict[str, Any]:
    return {
        "deploySchemaVersion": SUMMON_DEPLOY_SCHEMA_VERSION,
        "migration": {
            "normalizerVersion": SUMMON_DEPLOY_SCHEMA_VERSION,
            "legacyUpgradesApplied": [],
            "quarantinedCount": 0,
        },
        "unlockedTemplates": [],
        "unlockedGroups": [],
        "selectedVariants": {},
        "activeSummons": [],
        "quarantinedSummons": [],
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


def _dedupe_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in values:
        text = str(row or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _parse_cleanup_policy(value: Any) -> Any:
    if isinstance(value, dict):
        return copy.deepcopy(value)
    if isinstance(value, list):
        out: list[str] = []
        for row in value:
            key = _safe_lower_str(row)
            if key and key not in out:
                out.append(key)
        return out
    if isinstance(value, str):
        tokens = [tok.strip() for tok in value.replace(";", ",").split(",")]
        return [k for k in (_safe_lower_str(tok) for tok in tokens) if k]
    return []


def _parse_bool(value: Any, *, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
    return fallback


def _parse_int(value: Any, *, fallback: int = 0, minimum: int | None = None) -> int:
    try:
        out = int(value)
    except Exception:
        out = fallback
    if minimum is not None:
        out = max(minimum, out)
    return out


def _resolve_legacy_template_id(raw: dict[str, Any], source: dict[str, Any]) -> str:
    template_id = _safe_lower_str(
        raw.get("templateId")
        or raw.get("summonTemplateId")
        or raw.get("template")
        or raw.get("summonTemplate")
        or raw.get("variantTemplateId")
        or raw.get("deploymentTemplateId")
        or raw.get("deployableTemplateId")
        or raw.get("legacyTemplateId")
        or source.get("templateId")
        or source.get("summonTemplateId")
    )
    if template_id:
        return template_id
    fallback = _safe_lower_str(raw.get("id"))
    if fallback and isinstance(get_summon_template(fallback), dict):
        return fallback
    return ""


def _resolve_legacy_group_id(raw: dict[str, Any], source: dict[str, Any], template_id: str) -> str:
    return _safe_lower_str(
        raw.get("summonGroupId")
        or raw.get("groupId")
        or raw.get("variantGroup")
        or raw.get("summonFamilyId")
        or raw.get("deploymentGroupId")
        or raw.get("deploymentFamily")
        or source.get("variantGroup")
        or source.get("summonGroupId")
        or template_id
    )


def _resolve_entity_kind(*, raw: dict[str, Any], source_origin: str, source: dict[str, Any]) -> str:
    entity_kind = _safe_lower_str(raw.get("entityKind") or raw.get("kind") or raw.get("deploymentKind"))
    if entity_kind:
        return entity_kind
    actor = raw.get("actor") if isinstance(raw.get("actor"), dict) else {}
    actor_type = _safe_lower_str(actor.get("actorType") or raw.get("actorType") or raw.get("summonType"))
    if actor_type in {"deployable", "spell_effect", "object"}:
        return "deployable" if actor_type == "object" else actor_type
    template = get_summon_template(_resolve_legacy_template_id(raw, source)) or {}
    template_kind = _safe_lower_str(template.get("entityKind"))
    if template_kind:
        return template_kind
    if source_origin == "spell":
        return "spell_effect"
    return "creature"


def _legacy_source_payload(raw: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(source)
    if not isinstance(out, dict):
        out = {}
    if not out.get("classId"):
        out["classId"] = _safe_lower_str(raw.get("sourceClassId") or raw.get("classId") or raw.get("ownerClassId"))
    if not out.get("subclassId"):
        out["subclassId"] = _safe_lower_str(raw.get("sourceSubclassId") or raw.get("subclassId"))
    if not out.get("featureId"):
        out["featureId"] = _safe_lower_str(raw.get("sourceFeatureId") or raw.get("featureId"))
    if not out.get("spellId"):
        out["spellId"] = _safe_lower_str(raw.get("spellId") or raw.get("sourceSpellId"))
    if not out.get("variantGroup"):
        out["variantGroup"] = _safe_lower_str(raw.get("summonGroupId") or raw.get("variantGroup"))
    return out


def _normalize_active_summon_entry(raw: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(raw, dict):
        return None, None
    source = copy.deepcopy(raw.get("source")) if isinstance(raw.get("source"), dict) else {}
    source = _legacy_source_payload(raw, source)
    source_class = _safe_lower_str(raw.get("sourceClassId") or source.get("classId"))
    source_subclass = _safe_lower_str(raw.get("sourceSubclassId") or source.get("subclassId"))
    source_feature = _safe_lower_str(raw.get("sourceFeatureId") or source.get("featureId"))
    template_id = _resolve_legacy_template_id(raw, source)
    summon_group_id = _resolve_legacy_group_id(raw, source, template_id)
    variant_id = _safe_lower_str(raw.get("variantId") or raw.get("variant") or template_id)
    token_id = str(raw.get("tokenId") or raw.get("token_id") or raw.get("token") or "").strip()
    owner_user_id = str(raw.get("ownerUserId") or raw.get("ownerId") or (raw.get("owner") or {}).get("userId") or "").strip()
    owner_profile_id = str(raw.get("ownerProfileId") or raw.get("profileId") or (raw.get("owner") or {}).get("profileId") or "").strip()
    map_context = str(raw.get("mapContext") or raw.get("sceneId") or raw.get("tokenMapContext") or raw.get("map") or "").strip()[:80]
    source_origin = _safe_lower_str(raw.get("sourceOriginType") or raw.get("summonOrigin") or source.get("summonOrigin"))
    if not source_origin:
        source_origin = "spell" if _safe_lower_str(raw.get("spellId") or source.get("spellId")) else "feature"
    control_model = _safe_lower_str(raw.get("controlModel") or raw.get("commandModel") or raw.get("control") or raw.get("legacyControlModel"))
    if not control_model:
        control_model = "owner_controlled"
    entity_kind = _resolve_entity_kind(raw=raw, source_origin=source_origin, source=source)
    created_at = raw.get("createdAt", raw.get("spawnedAt"))
    updated_at = raw.get("updatedAt", created_at)
    status = _safe_lower_str(raw.get("status") or raw.get("state") or "active") or "active"
    try:
        max_active = max(0, int(raw.get("maxActive")))
    except Exception:
        max_active = None
    id_fallback = str(raw.get("id") or raw.get("activeId") or "").strip() or template_id or token_id
    if not id_fallback:
        return None, {
            "reason": "missing_identity",
            "raw": copy.deepcopy(raw),
            "status": "quarantined",
        }
    if not template_id and not token_id:
        return None, {
            "reason": "missing_template_and_token",
            "activeId": id_fallback,
            "raw": copy.deepcopy(raw),
            "status": "quarantined",
        }
    duration_seconds = _parse_int(raw.get("durationSeconds"), fallback=0, minimum=0)
    if not duration_seconds:
        duration_seconds = _parse_int((raw.get("lifecycle") or {}).get("durationSeconds") if isinstance(raw.get("lifecycle"), dict) else None, fallback=0, minimum=0)
    cleanup_policy = _parse_cleanup_policy(raw.get("cleanupPolicy"))
    if not cleanup_policy and isinstance(raw.get("lifecycle"), dict):
        cleanup_policy = _parse_cleanup_policy((raw.get("lifecycle") or {}).get("cleanupPolicy"))
    normalized = {
        "id": id_fallback,
        "templateId": template_id,
        "summonTemplateId": template_id,
        "summonGroupId": summon_group_id,
        "variantId": variant_id,
        "variant": variant_id,
        "entityId": str(raw.get("entityId") or raw.get("id") or raw.get("activeId") or "").strip() or template_id or token_id,
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
        "temporary": _parse_bool(raw.get("temporary"), fallback=_parse_bool((raw.get("lifecycle") or {}).get("temporary") if isinstance(raw.get("lifecycle"), dict) else False, fallback=False)),
        "concentrationRequired": _parse_bool(raw.get("concentrationRequired"), fallback=False),
        "durationSeconds": duration_seconds,
        "expiresAt": raw.get("expiresAt") if raw.get("expiresAt") is not None else ((raw.get("lifecycle") or {}).get("expiresAt") if isinstance(raw.get("lifecycle"), dict) else None),
        "cleanupPolicy": cleanup_policy,
        "replaceOnResummon": bool(raw.get("replaceOnResummon")),
        "maxActive": max_active,
        "controlModel": control_model,
        "commandModel": _safe_lower_str(raw.get("commandModel") or (raw.get("actor") or {}).get("commandModel") if isinstance(raw.get("actor"), dict) else ""),
        "lifecycle": {
            "temporary": _parse_bool(raw.get("temporary"), fallback=False),
            "status": status,
            "durationSeconds": duration_seconds,
            "expiresAt": raw.get("expiresAt") if raw.get("expiresAt") is not None else ((raw.get("lifecycle") or {}).get("expiresAt") if isinstance(raw.get("lifecycle"), dict) else None),
            "cleanupPolicy": cleanup_policy,
        },
        "source": source,
    }
    if raw.get("isCreature") is not None:
        normalized["isCreature"] = _parse_bool(raw.get("isCreature"), fallback=entity_kind == "creature")
    else:
        normalized["isCreature"] = entity_kind == "creature"
    if isinstance(raw.get("placementRules"), dict):
        normalized["placementRules"] = copy.deepcopy(raw.get("placementRules"))
    elif isinstance((raw.get("actor") or {}).get("placementRules") if isinstance(raw.get("actor"), dict) else None, dict):
        normalized["placementRules"] = copy.deepcopy((raw.get("actor") or {}).get("placementRules"))
    if isinstance(raw.get("interactionModel"), dict):
        normalized["interactionModel"] = copy.deepcopy(raw.get("interactionModel"))
    elif isinstance((raw.get("actor") or {}).get("interactionModel") if isinstance(raw.get("actor"), dict) else None, dict):
        normalized["interactionModel"] = copy.deepcopy((raw.get("actor") or {}).get("interactionModel"))
    action_surface_type = str(raw.get("actionSurfaceType") or "").strip()
    if action_surface_type:
        normalized["actionSurfaceType"] = action_surface_type
    if isinstance(raw.get("actor"), dict):
        normalized["actor"] = copy.deepcopy(raw.get("actor"))
    if raw.get("legacyMeta") is not None:
        normalized["legacyMeta"] = copy.deepcopy(raw.get("legacyMeta"))
    return normalized, None


def _normalize_active_summons(src: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    rows: list[Any] = []
    upgrades: list[str] = []
    if isinstance(src.get("activeSummons"), list):
        rows.extend(list(src.get("activeSummons") or []))
    for legacy_list_key in ("activeDeployments", "activeEntities", "deployments"):
        legacy_rows = src.get(legacy_list_key)
        if isinstance(legacy_rows, list):
            rows.extend(list(legacy_rows))
            upgrades.append(f"{legacy_list_key}_list_upgraded")
    # Backward compatibility: single active summon slot used in earlier passes.
    for legacy_key in ("activeSummon", "active", "currentSummon", "activeDeployment", "currentDeployment"):
        legacy = src.get(legacy_key)
        if isinstance(legacy, dict):
            rows.append(legacy)
            upgrades.append(f"{legacy_key}_single_upgraded")
    out: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in rows:
        normalized, rejected = _normalize_active_summon_entry(raw)
        if rejected:
            quarantined.append(rejected)
            continue
        if not normalized:
            continue
        row_id = str(normalized.get("id") or "").strip()
        dedupe_key = row_id or str(normalized.get("tokenId") or "").strip() or str(normalized.get("templateId") or "").strip()
        if not dedupe_key or dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        out.append(normalized)
    return out, quarantined, upgrades


def normalize_summon_state(raw: Any) -> dict[str, Any]:
    base = default_summon_state()
    src = raw if isinstance(raw, dict) else {}
    migration = src.get("migration") if isinstance(src.get("migration"), dict) else {}
    prior_upgrades = _dedupe_string_list(migration.get("legacyUpgradesApplied"))
    base["deploySchemaVersion"] = SUMMON_DEPLOY_SCHEMA_VERSION
    base["unlockedTemplates"] = _normalize_list(src.get("unlockedTemplates"))
    base["unlockedGroups"] = _normalize_list(src.get("unlockedGroups"))
    base["selectedVariants"] = _normalize_selected_variants(src.get("selectedVariants"))
    active, quarantined, upgrades = _normalize_active_summons(src)
    base["activeSummons"] = active
    base["quarantinedSummons"] = list(src.get("quarantinedSummons") or []) if isinstance(src.get("quarantinedSummons"), list) else []
    base["quarantinedSummons"].extend(quarantined)
    base["rules"] = copy.deepcopy(src.get("rules")) if isinstance(src.get("rules"), dict) else {}
    base["lastUpdatedFromFeatures"] = _normalize_list(src.get("lastUpdatedFromFeatures"))
    deduped_upgrades = _dedupe_string_list(prior_upgrades + upgrades)
    base["migration"] = {
        "normalizerVersion": SUMMON_DEPLOY_SCHEMA_VERSION,
        "legacyUpgradesApplied": deduped_upgrades,
        "quarantinedCount": len(base["quarantinedSummons"]),
    }
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
    elif variant_group and default_template_id and default_template_id in state["unlockedTemplates"] and not selected_variants.get(variant_group):
        selected_variants[variant_group] = default_template_id
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
