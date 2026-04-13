"""Casual D&D Awakening resolution helpers.

Awakening is a post-core progression layer (target unlock at level 15+) that
sits alongside class/subclass/talent systems instead of replacing them.
"""
from __future__ import annotations

import copy
from typing import Any

from server.character.rules_catalog import load_rules_catalog

_ALLOWED_GRANT_TYPES = {
    "passive_unlock",
    "action_unlock",
    "resource_bonus",
    "derived_tag",
}


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _sanitize_grant(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    grant_type = _safe_str(row.get("type")).lower()
    if grant_type not in _ALLOWED_GRANT_TYPES:
        return None
    grant_id = _safe_str(row.get("id") or row.get("name") or grant_type)
    return {
        "id": grant_id,
        "type": grant_type,
        "name": _safe_str(row.get("name") or grant_id),
        "value": _clone(row.get("value")),
        "scope": _safe_str(row.get("scope")),
        "tier": _safe_int(row.get("tier"), 1, minimum=1),
    }


def _selected_class_ids(document: dict[str, Any]) -> set[str]:
    classes = document.get("classes") if isinstance(document.get("classes"), list) else []
    selected: set[str] = set()
    for row in classes:
        if not isinstance(row, dict):
            continue
        class_id = _safe_str(row.get("classId") or row.get("id") or row.get("name")).lower()
        if class_id:
            selected.add(class_id)
    return selected


def _iter_active_tier_grants(path_row: dict[str, Any], stage: int) -> list[dict[str, Any]]:
    grants: list[dict[str, Any]] = []

    for row in path_row.get("grants") or []:
        sanitized = _sanitize_grant(row)
        if sanitized:
            grants.append(sanitized)

    tiers = path_row.get("tiers") if isinstance(path_row.get("tiers"), list) else []
    for tier in tiers:
        if not isinstance(tier, dict):
            continue
        tier_stage = _safe_int(tier.get("stage"), 0, minimum=0)
        if stage < tier_stage:
            continue
        for row in tier.get("grants") or []:
            sanitized = _sanitize_grant(row)
            if not sanitized:
                continue
            sanitized["tier"] = max(tier_stage, sanitized.get("tier") or 1)
            grants.append(sanitized)

    return grants


def apply_awakening_grants(runtime: dict[str, Any], grants: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply conservative awakening grants to runtime action/passive/resource lists."""
    passives = runtime.get("passives") if isinstance(runtime.get("passives"), list) else []
    actions = runtime.get("actions") if isinstance(runtime.get("actions"), list) else []
    resources = runtime.get("resources") if isinstance(runtime.get("resources"), list) else []
    derived_tags = runtime.get("derivedTags") if isinstance(runtime.get("derivedTags"), list) else []

    passive_ids = {str(row.get("id") or "") for row in passives if isinstance(row, dict)}
    action_ids = {str(row.get("id") or "") for row in actions if isinstance(row, dict)}
    resource_ids = {str(row.get("id") or "") for row in resources if isinstance(row, dict)}

    for grant in grants:
        if not isinstance(grant, dict):
            continue
        grant_type = _safe_str(grant.get("type")).lower()
        grant_id = _safe_str(grant.get("id"))

        if grant_type == "passive_unlock":
            if grant_id and grant_id not in passive_ids:
                passives.append(
                    {
                        "id": grant_id,
                        "name": _safe_str(grant.get("name")) or grant_id,
                        "source": "awakening",
                        "tier": _safe_int(grant.get("tier"), 1, minimum=1),
                        "details": _clone(grant.get("value")),
                    }
                )
                passive_ids.add(grant_id)
            continue

        if grant_type == "action_unlock":
            if grant_id and grant_id not in action_ids:
                actions.append(
                    {
                        "id": grant_id,
                        "name": _safe_str(grant.get("name")) or grant_id,
                        "source": "awakening",
                        "tier": _safe_int(grant.get("tier"), 1, minimum=1),
                        "details": _clone(grant.get("value")),
                    }
                )
                action_ids.add(grant_id)
            continue

        if grant_type == "resource_bonus":
            value = grant.get("value") if isinstance(grant.get("value"), dict) else {}
            resource_id = _safe_str(value.get("resourceId") or grant_id)
            if resource_id and resource_id not in resource_ids:
                resources.append(
                    {
                        "id": resource_id,
                        "label": _safe_str(value.get("label") or grant.get("name") or resource_id),
                        "current": _safe_int(value.get("max"), 0, minimum=0),
                        "max": _safe_int(value.get("max"), 0, minimum=0),
                        "scope": _safe_str(value.get("scope") or grant.get("scope") or "long_rest"),
                        "source": "awakening",
                        "tier": _safe_int(grant.get("tier"), 1, minimum=1),
                    }
                )
                resource_ids.add(resource_id)
            continue

        if grant_type == "derived_tag":
            tag_value = _safe_str(grant.get("value"))
            if tag_value and tag_value not in derived_tags:
                derived_tags.append(tag_value)

    runtime["passives"] = passives
    runtime["actions"] = actions
    runtime["resources"] = resources
    runtime["derivedTags"] = derived_tags
    return runtime


def resolve_awakening_for_runtime(document: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    """Resolve selected awakening path and active grants for current runtime level."""
    awakening = document.get("awakening") if isinstance(document.get("awakening"), dict) else {}
    path_id = _safe_str(awakening.get("pathId")).lower()
    stage = _safe_int(awakening.get("stage"), 0, minimum=0)

    level_total = _safe_int(runtime.get("levelTotal"), 1, minimum=1)
    class_ids = _selected_class_ids(document)

    result = {
        "unlocked": False,
        "pathId": path_id,
        "pathName": "",
        "stage": stage,
        "minimumLevel": 15,
        "classRestriction": [],
        "grants": [],
    }

    if not path_id:
        return result

    catalog = load_rules_catalog()
    path_row = (catalog.get("awakeningsById") or {}).get(path_id)
    if not isinstance(path_row, dict):
        return result

    min_level = _safe_int(path_row.get("minimumLevel"), 15, minimum=1)
    restrictions = [
        _safe_str(item).lower()
        for item in (path_row.get("classRestrictions") or [])
        if _safe_str(item)
    ]

    unlocked = level_total >= min_level and (not restrictions or bool(class_ids & set(restrictions)))

    grants = _iter_active_tier_grants(path_row, stage) if unlocked else []

    return {
        "unlocked": unlocked,
        "pathId": _safe_str(path_row.get("id") or path_id),
        "pathName": _safe_str(path_row.get("displayName")),
        "stage": stage,
        "minimumLevel": min_level,
        "classRestriction": restrictions,
        "grants": grants,
    }
