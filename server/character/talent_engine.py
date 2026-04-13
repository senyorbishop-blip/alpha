"""Casual D&D native talent resolution helpers.

Talents are intentionally modeled as a separate progression layer from
class/subclass progression so they can evolve independently (including future
Awakening ties) without mutating official 5e class trees.
"""
from __future__ import annotations

import copy
from typing import Any

from server.character.rules_catalog import load_rules_catalog

_ALLOWED_GRANT_TYPES = {
    "derived_tag",
    "resource_bonus",
    "speed_bonus",
    "proficiency_grant",
    "action_unlock",
    "spell_unlock",
}



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



def _safe_str(value: Any) -> str:
    return str(value or "").strip()



def _sanitize_grant(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    grant_type = _safe_str(row.get("type")).lower()
    if grant_type not in _ALLOWED_GRANT_TYPES:
        return None
    return {
        "type": grant_type,
        "id": _safe_str(row.get("id") or grant_type),
        "value": _clone(row.get("value")),
        "scope": _safe_str(row.get("scope")),
    }



def apply_talent_grants(runtime: dict[str, Any], talent_grants: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply a conservative subset of talent grants to runtime.

    This keeps talent scaffolding future-friendly while preventing accidental
    overrides of existing class/subclass progression behavior.
    """
    derived_tags = runtime.get("derivedTags") if isinstance(runtime.get("derivedTags"), list) else []
    unresolved: list[dict[str, Any]] = []

    for grant in talent_grants:
        if not isinstance(grant, dict):
            continue

        grant_type = _safe_str(grant.get("type")).lower()
        if grant_type == "derived_tag":
            tag_value = _safe_str(grant.get("value"))
            if tag_value and tag_value not in derived_tags:
                derived_tags.append(tag_value)
            continue

        # Keep all non-tag grants as deferred metadata for future level-up and
        # Awakening-integrated resolvers, rather than mutating combat/runtime now.
        unresolved.append(_clone(grant))

    runtime["derivedTags"] = derived_tags
    runtime["pendingTalentGrants"] = unresolved
    return runtime



def resolve_talents_for_runtime(document: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    """Resolve selected native talents into conservative runtime metadata.

    This hook intentionally does not directly mutate core combat math yet.
    It only returns normalized talent rows and sanitized grant metadata so
    later slices can opt-in to each grant type safely.
    """
    catalog = load_rules_catalog()
    talents_by_id = catalog.get("talentsById") if isinstance(catalog.get("talentsById"), dict) else {}

    classes = document.get("classes") if isinstance(document.get("classes"), list) else []
    class_ids = {
        _safe_str(row.get("classId") or row.get("name")).lower()
        for row in classes
        if isinstance(row, dict)
    }

    selected_rows = document.get("talents") if isinstance(document.get("talents"), list) else []
    selected_ids: list[str] = []
    for row in selected_rows:
        if isinstance(row, str):
            talent_id = _safe_str(row).lower()
        elif isinstance(row, dict):
            talent_id = _safe_str(row.get("talentId") or row.get("id")).lower()
        else:
            talent_id = ""
        if talent_id and talent_id not in selected_ids:
            selected_ids.append(talent_id)

    level_total = _safe_int(runtime.get("levelTotal"), 1, minimum=1)

    resolved_talents: list[dict[str, Any]] = []
    resolved_grants: list[dict[str, Any]] = []

    for talent_id in selected_ids:
        catalog_row = talents_by_id.get(talent_id)
        if not isinstance(catalog_row, dict):
            continue

        source = _safe_str(catalog_row.get("source") or "casualdnd_talent").lower()
        if source != "casualdnd_talent":
            # Reserve strict handling for future external talent pack types.
            continue

        minimum_level = _safe_int(catalog_row.get("minimumLevel"), 1, minimum=1)
        if level_total < minimum_level:
            continue

        class_restrictions = [
            _safe_str(item).lower()
            for item in (catalog_row.get("classRestrictions") or [])
            if _safe_str(item)
        ]
        if class_restrictions and not (class_ids & set(class_restrictions)):
            continue

        grants: list[dict[str, Any]] = []
        for grant in catalog_row.get("grants") or []:
            sanitized = _sanitize_grant(grant)
            if sanitized:
                grants.append(sanitized)
                resolved_grants.append(
                    {
                        "talentId": talent_id,
                        "source": "casualdnd_talent",
                        **sanitized,
                    }
                )

        resolved_talents.append(
            {
                "id": _safe_str(catalog_row.get("id") or talent_id),
                "displayName": _safe_str(catalog_row.get("displayName")),
                "minimumLevel": minimum_level,
                "classRestrictions": class_restrictions,
                "tags": list(catalog_row.get("tags") or []),
                "source": "casualdnd_talent",
                "grants": grants,
            }
        )

    return {
        "talents": resolved_talents,
        "grants": resolved_grants,
    }
