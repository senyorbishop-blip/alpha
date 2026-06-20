"""Runtime summon orchestration (Pass H: expanded summon families via shared runtime)."""
from __future__ import annotations

import copy
import time
import threading
from typing import Any

from server.character.summon_catalog import get_summon_template
from server.character.summon_diagnostics import build_failure
from server.character.summon_state import normalize_summon_state
from server.session import Session, User


_METRICS_LOCK = threading.Lock()
_SUMMON_RUNTIME_METRICS: dict[str, Any] = {
    "build_payload_calls": 0,
    "build_payload_ms_total": 0.0,
    "build_payload_ms_last": 0.0,
    "reconcile_calls": 0,
    "reconcile_rows_scanned": 0,
    "reconcile_rows_pruned": 0,
    "prune_calls": 0,
    "prune_rows_scanned": 0,
    "prune_rows_removed": 0,
}


def _record_runtime_metric(metric_key: str, value: float | int = 1) -> None:
    with _METRICS_LOCK:
        _SUMMON_RUNTIME_METRICS[metric_key] = _SUMMON_RUNTIME_METRICS.get(metric_key, 0) + value


def get_summon_runtime_metrics() -> dict[str, Any]:
    with _METRICS_LOCK:
        return copy.deepcopy(_SUMMON_RUNTIME_METRICS)


_ERROR_CODE_TO_CATEGORY: dict[str, str] = {
    "profile_not_found": "missing_profile",
    "missing_native_character": "missing_native_character",
    "invalid_variant": "illegal_variant_selection",
    "variant_error": "illegal_variant_selection",
    "summon_not_unlocked": "missing_summon_unlock",
    "spell_not_available": "spell_not_available",
    "runtime_not_live_for_class": "runtime_not_live",
    "missing_map_context": "missing_map_context",
    "missing_template": "missing_template",
    "register_active_failed": "register_active_failed",
}


def _runtime_failure(code: str, *, message: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a structured failure payload for build_summon_runtime_payload."""
    category = _ERROR_CODE_TO_CATEGORY.get(str(code or ""), str(code or "unknown_failure"))
    return {
        "ok": False,
        "error": str(code or "unknown_failure"),
        "message": str(message or ""),
        "failure": {
            "category": category,
            "code": str(code or "unknown_failure"),
            "message": str(message or ""),
            "context": context if isinstance(context, dict) else {},
        },
    }


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed




_BEAST_VARIANTS = {
    "ranger-primal-beast-land": {
        "movement": {"walk": 40, "climb": 40},
        "size": "medium",
        "senses": {"darkvision": 60},
        "actions": [{"id": "maul", "name": "Maul", "classification": "attack", "range": "Melee 5 ft", "damage": {"formula": "1d8+2+PB", "type": "force"}, "summary": "On hit, Large or smaller targets are knocked prone."}],
    },
    "ranger-primal-beast-sea": {
        "movement": {"walk": 5, "swim": 60},
        "size": "medium",
        "senses": {"darkvision": 60},
        "actions": [{"id": "binding_strike", "name": "Binding Strike", "classification": "attack", "range": "Melee 5 ft", "damage": {"formula": "1d6+2+PB", "type": "piercing"}, "summary": "On hit, target is grappled until it escapes."}],
    },
    "ranger-primal-beast-sky": {
        "movement": {"walk": 10, "fly": 60},
        "size": "small",
        "senses": {"darkvision": 60},
        "actions": [{"id": "shred", "name": "Shred", "classification": "attack", "range": "Melee 5 ft", "damage": {"formula": "1d4+3+PB", "type": "slashing"}, "summary": "Fast flyby strike for hit-and-run positioning."}],
    },
}

_WARLOCK_FAMILIAR_VARIANTS = {
    "warlock-chain-imp": {
        "ac": 13,
        "hp": 10,
        "movement": {"walk": 20, "fly": 40},
        "senses": {"darkvision": 120},
        "size": "tiny",
        "traits": ["Devil's Sight", "Shapechanger (Raven/Rat/Spider)"],
        "actions": [
            {"id": "sting", "name": "Sting", "classification": "attack", "range": "Melee 5 ft", "attackBonus": 5, "damage": {"formula": "1d4+3", "type": "piercing"}, "saveDC": 11, "saveAbility": "CON", "summary": "Target makes CON save or suffers poison effect."}
        ],
    },
    "warlock-chain-pseudodragon": {
        "ac": 13,
        "hp": 7,
        "movement": {"walk": 15, "fly": 60},
        "senses": {"blindsight": 10, "darkvision": 60},
        "size": "tiny",
        "traits": ["Keen Senses", "Limited Telepathy"],
        "actions": [
            {"id": "sting", "name": "Sting", "classification": "attack", "range": "Melee 5 ft", "attackBonus": 4, "damage": {"formula": "1d4+2", "type": "piercing"}, "saveDC": 11, "saveAbility": "CON", "summary": "Failed save can poison or knock out the target."}
        ],
    },
    "warlock-chain-quasit": {
        "ac": 13,
        "hp": 7,
        "movement": {"walk": 40},
        "senses": {"darkvision": 120},
        "size": "tiny",
        "traits": ["Magic Resistance", "Shapechanger (Bat/Centipede/Toad)"],
        "actions": [
            {"id": "claws", "name": "Claws", "classification": "attack", "range": "Melee 5 ft", "attackBonus": 4, "damage": {"formula": "1d4+3", "type": "slashing"}, "saveDC": 10, "saveAbility": "CON", "summary": "Target makes CON save against poison."}
        ],
    },
    "warlock-chain-sprite": {
        "ac": 15,
        "hp": 2,
        "movement": {"walk": 10, "fly": 40},
        "senses": {"darkvision": 60},
        "size": "tiny",
        "traits": ["Heart Sight", "Fey Step profile"],
        "actions": [
            {"id": "shortbow", "name": "Shortbow", "classification": "attack", "range": "40/160 ft", "attackBonus": 6, "damage": {"formula": "1", "type": "piercing"}, "saveDC": 10, "saveAbility": "CON", "summary": "Arrow carries poison on hit."}
        ],
    },
}

_TINKER_MECHANIST_FRAME = {
    "ac_base": 13,
    "hp_base": 10,
    "hp_per_level": 5,
    "movement": {"walk": 30},
    "senses": {"darkvision": 60},
    "size": "medium",
    "traits": ["Construct Resilience", "Command Relay Link"],
    "actions": [
        {"id": "force_slam", "name": "Force Slam", "classification": "attack", "range": "Melee 5 ft", "damage": {"formula": "1d8+PB", "type": "force"}, "saveDC": None, "saveAbility": "STR", "summary": "On hit, target can be shoved 5 ft on failed STR save."}
    ],
}

_TINKER_ARTILLERIST_ARC_CANNON = {
    "ac_base": 14,
    "hp_base": 8,
    "hp_per_level": 4,
    "movement": {"walk": 15},
    "senses": {},
    "size": "small",
    "traits": ["Arc Core", "Stabilized Emplacement"],
    "actions": [
        {
            "id": "arc_blast",
            "name": "Arc Blast",
            "classification": "attack",
            "range": "Ranged 120 ft",
            "damage": {"formula": "2d8+PB", "type": "force"},
            "saveDC": None,
            "saveAbility": "DEX",
            "summary": "Discharge a focused bolt of force from the cannon core.",
        }
    ],
}


def _ability_mod(value: Any) -> int:
    return (_safe_int(value, 10) - 10) // 2


def _proficiency_bonus(level_total: int) -> int:
    return 2 + max(0, (max(1, level_total) - 1) // 4)


def _format_signed(value: int) -> str:
    return f"{value:+d}" if value >= 0 else str(value)


def _normalize_action_payload(*, actor: dict[str, Any], action: dict[str, Any], index: int, attack_bonus: int | None = None, save_dc: int | None = None, command_model: str = "") -> dict[str, Any]:
    action_id = str(action.get("id") or f"action-{index+1}").strip().lower()
    display = str(action.get("displayName") or action.get("name") or action_id.replace("_", " ").title()).strip()
    classification = str(action.get("classification") or action.get("kind") or "attack").strip().lower()
    action_type = str(action.get("actionType") or action.get("type") or "action").strip().lower()
    payload = {
        "id": action_id or f"action-{index+1}",
        "displayName": display or "Action",
        "actionType": action_type or "action",
        "classification": classification or "attack",
        "range": str(action.get("range") or "").strip(),
        "reach": str(action.get("reach") or "").strip(),
        "attackBonus": attack_bonus if attack_bonus is not None else action.get("attackBonus"),
        "saveDC": save_dc if save_dc is not None else action.get("saveDC"),
        "saveAbility": str(action.get("saveAbility") or "").strip().upper(),
        "damage": copy.deepcopy(action.get("damage") or {}),
        "healing": copy.deepcopy(action.get("healing") or {}),
        "usage": copy.deepcopy(action.get("usage") or {}),
        "summary": str(action.get("summary") or action.get("rider") or "").strip(),
        "commandModel": command_model,
        "commandRequired": bool(command_model in {"bonus_action_command", "action_command"}),
    }
    if not payload["range"] and classification == "attack":
        payload["range"] = "Melee"
    return payload


def _legacy_attacks_from_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        dmg = action.get("damage") if isinstance(action.get("damage"), dict) else {}
        formula = str(dmg.get("formula") or "").strip()
        dtype = str(dmg.get("type") or "").strip()
        out.append({
            "id": str(action.get("id") or ""),
            "name": str(action.get("displayName") or action.get("name") or "Action"),
            "toHit": _format_signed(int(action.get("attackBonus") or 0)) if action.get("attackBonus") is not None else "",
            "damage": formula,
            "type": dtype,
            "rider": str(action.get("summary") or "").strip(),
        })
    return out


def _resolve_primary_class(native_document: dict[str, Any]) -> dict[str, Any]:
    classes = native_document.get("classes") if isinstance(native_document.get("classes"), list) else []
    return classes[0] if classes and isinstance(classes[0], dict) else {}


def _extract_profile_spell_ids(native_document: dict[str, Any]) -> set[str]:
    spell_state = native_document.get("spellState") if isinstance(native_document.get("spellState"), dict) else {}
    out: set[str] = set()
    for key in ("known", "prepared"):
        rows = spell_state.get(key) if isinstance(spell_state.get(key), list) else []
        for row in rows:
            spell_id = str(row or "").strip().lower()
            if spell_id:
                out.add(spell_id)
    entries = native_document.get("spellbookEntries") if isinstance(native_document.get("spellbookEntries"), list) else []
    for row in entries:
        if not isinstance(row, dict):
            continue
        spell_id = str(row.get("id") or row.get("spellId") or "").strip().lower()
        if spell_id:
            out.add(spell_id)
    return out


def _resolve_map_context(session: Session, user: User, payload: dict[str, Any]) -> str:
    if "map_context" in payload or "mapContext" in payload:
        explicit = str(payload.get("map_context") or payload.get("mapContext") or "").strip()
        return explicit[:80]
    subgroup_ctx = session.get_subgroup_map_context(getattr(user, "subgroup_id", "")) if hasattr(session, "get_subgroup_map_context") else ""
    if subgroup_ctx:
        return subgroup_ctx
    dm_ctx = str(getattr(session, "dm_map_context", "world") or "world").strip()
    return dm_ctx[:80] or "world"


def _resolve_owner_key(session: Session, user: User) -> str:
    # Keep behavior aligned with existing character profile ownership key model.
    from server.handlers.content import _char_profile_bucket_key  # local import avoids circular import at module load

    return _char_profile_bucket_key(session, user)


def _find_active_profile(session: Session, user: User, requested_profile_id: str = "") -> tuple[str, int, dict[str, Any]]:
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    owner_key = _resolve_owner_key(session, user)
    bucket = profiles.get(owner_key)
    rows = list(bucket) if isinstance(bucket, list) else []

    active_id = str(requested_profile_id or "").strip()
    if not active_id:
        active_id = str((getattr(session, "active_char_profiles", {}) or {}).get(user.id) or "").strip()

    if active_id:
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            if str(row.get("id") or "").strip() == active_id:
                return owner_key, idx, row

    for idx, row in enumerate(rows):
        if isinstance(row, dict):
            return owner_key, idx, row
    return owner_key, -1, {}


def _resolve_variant(
    *,
    template_id: str,
    selected_variant: str,
    summon_group_id: str,
    native_document: dict[str, Any],
    unlocked: set[str],
) -> tuple[str, dict[str, Any] | None, str]:
    requested = str(selected_variant or template_id or "").strip().lower()
    template = get_summon_template(requested) if requested else None
    if template and requested in unlocked:
        return requested, template, ""
    if template and requested:
        return requested, template, ""

    group_id = str(summon_group_id or (template or {}).get("variantGroup") or "").strip().lower()
    summons = native_document.get("summons") if isinstance(native_document.get("summons"), dict) else {}
    selected_variants = summons.get("selectedVariants") if isinstance(summons.get("selectedVariants"), dict) else {}
    fallback = str(selected_variants.get(group_id) or "").strip().lower()
    if fallback and fallback in unlocked:
        template = get_summon_template(fallback)
        if template:
            return fallback, template, ""

    if group_id:
        group_options = sorted(
            tid
            for tid in unlocked
            if str((get_summon_template(tid) or {}).get("variantGroup") or "").strip().lower() == group_id
        )
        if group_options:
            first = group_options[0]
            template = get_summon_template(first)
            if template:
                return first, template, ""

    return "", None, "invalid_variant"


def resolve_beast_master_actor(*, native_document: dict[str, Any], template: dict[str, Any], selected_variant: str, owner_user: User, profile_id: str) -> dict[str, Any]:
    primary = _resolve_primary_class(native_document)
    class_id = str(primary.get("classId") or primary.get("id") or "").strip().lower()
    subclass_id = str(primary.get("subclassId") or "").strip().lower()
    class_level = _safe_int(primary.get("level"), 1, minimum=1, maximum=20)
    level_total = class_level

    if class_id != "ranger" or subclass_id != "beast-master":
        raise ValueError("beast_master_only")

    ability_scores = ((native_document.get("abilities") or {}).get("scores") or {}) if isinstance(native_document.get("abilities"), dict) else {}
    wis_mod = _ability_mod(ability_scores.get("wis", 10))
    con_mod = _ability_mod(ability_scores.get("con", 10))
    proficiency = _proficiency_bonus(level_total)

    variant_defaults = _BEAST_VARIANTS.get(selected_variant)
    if not isinstance(variant_defaults, dict):
        raise ValueError("invalid_variant")

    max_hp = max(5, 5 + (class_level * 5) + con_mod)
    ac = 13 + proficiency
    token_name = str(template.get("tokenName") or template.get("displayName") or "Primal Beast").strip()
    command_model = str(template.get("commandModel") or "bonus_action_command").strip().lower()
    action_rows = [
        _normalize_action_payload(
            actor={},
            action=row,
            index=index,
            attack_bonus=proficiency + wis_mod,
            save_dc=8 + proficiency + wis_mod,
            command_model=command_model,
        )
        for index, row in enumerate(list(variant_defaults.get("actions") or []))
        if isinstance(row, dict)
    ]

    return {
        "id": f"summon-{owner_user.id}-{int(time.time() * 1000)}",
        "templateId": str(template.get("id") or selected_variant),
        "variantId": selected_variant,
        "variantName": str(template.get("displayName") or token_name),
        "name": token_name,
        "actorType": "companion",
        "summonCategory": "companion",
        "size": str(variant_defaults.get("size") or template.get("size") or "medium"),
        "movement": copy.deepcopy(variant_defaults.get("movement") or template.get("movement") or {"walk": 30}),
        "senses": copy.deepcopy(variant_defaults.get("senses") or template.get("senses") or {}),
        "ac": ac,
        "hp": {"current": max_hp, "max": max_hp},
        "actions": action_rows,
        "attacks": _legacy_attacks_from_actions(action_rows),
        "proficiencyBonus": proficiency,
        "levelSource": {
            "classId": "ranger",
            "subclassId": "beast-master",
            "classLevel": class_level,
            "featureId": str(template.get("sourceFeatureId") or "beast-master-rangers-companion"),
            "featureName": "Ranger's Companion",
        },
        "owner": {
            "userId": str(owner_user.id),
            "userName": str(owner_user.name),
            "profileId": str(profile_id or ""),
        },
        "commandModel": command_model,
        "source": {
            "classId": str(template.get("sourceClassId") or "ranger"),
            "subclassId": str(template.get("sourceSubclassId") or "beast-master"),
            "featureId": str(template.get("sourceFeatureId") or "beast-master-rangers-companion"),
            "variantGroup": str(template.get("variantGroup") or "ranger-primal-beast"),
        },
        "tokenVisual": {
            "color": "#7ad67a",
            "shape": "circle",
            "image_url": str(template.get("imageUrl") or "").strip() or None,
            "fallbackEmoji": "🐾",
        },
    }


def resolve_warlock_familiar_actor(*, native_document: dict[str, Any], template: dict[str, Any], selected_variant: str, owner_user: User, profile_id: str) -> dict[str, Any]:
    primary = _resolve_primary_class(native_document)
    class_id = str(primary.get("classId") or primary.get("id") or "").strip().lower()
    class_level = _safe_int(primary.get("level"), 1, minimum=1, maximum=20)
    if class_id != "warlock":
        raise ValueError("warlock_only")

    familiar = _WARLOCK_FAMILIAR_VARIANTS.get(selected_variant)
    if not isinstance(familiar, dict):
        raise ValueError("invalid_variant")

    token_name = str(template.get("tokenName") or template.get("displayName") or "Familiar").strip()
    hp = max(1, _safe_int(familiar.get("hp"), 1, minimum=1))
    ac = max(1, _safe_int(familiar.get("ac"), 10, minimum=1))
    movement = copy.deepcopy(familiar.get("movement") or template.get("movement") or {"walk": 30})
    senses = copy.deepcopy(familiar.get("senses") or template.get("senses") or {})
    command_model = str(template.get("commandModel") or "bonus_action_command").strip().lower()
    action_rows = [
        _normalize_action_payload(
            actor={},
            action=row,
            index=index,
            attack_bonus=(_safe_int(row.get("attackBonus"), 0) if row.get("attackBonus") is not None else None),
            save_dc=(_safe_int(row.get("saveDC"), 0) if row.get("saveDC") is not None else None),
            command_model=command_model,
        )
        for index, row in enumerate(list(familiar.get("actions") or []))
        if isinstance(row, dict)
    ]
    return {
        "id": f"summon-{owner_user.id}-{int(time.time() * 1000)}",
        "templateId": str(template.get("id") or selected_variant),
        "variantId": selected_variant,
        "variantName": str(template.get("displayName") or token_name),
        "name": token_name,
        "actorType": "familiar",
        "summonCategory": "familiar",
        "size": str(familiar.get("size") or template.get("size") or "tiny"),
        "movement": movement,
        "senses": senses,
        "ac": ac,
        "hp": {"current": hp, "max": hp},
        "actions": action_rows,
        "attacks": _legacy_attacks_from_actions(action_rows),
        "traits": copy.deepcopy(familiar.get("traits") or []),
        "proficiencyBonus": _proficiency_bonus(class_level),
        "levelSource": {
            "classId": "warlock",
            "subclassId": str(primary.get("subclassId") or "").strip().lower(),
            "classLevel": class_level,
            "featureId": str(template.get("sourceFeatureId") or "warlock-pact-boon"),
            "featureName": "Pact Boon (Pact of the Chain)",
        },
        "owner": {"userId": str(owner_user.id), "userName": str(owner_user.name), "profileId": str(profile_id or "")},
        "commandModel": command_model,
        "source": {
            "classId": str(template.get("sourceClassId") or "warlock"),
            "subclassId": str(template.get("sourceSubclassId") or ""),
            "featureId": str(template.get("sourceFeatureId") or "warlock-pact-boon"),
            "variantGroup": str(template.get("variantGroup") or "warlock-pact-chain-familiar"),
        },
        "tokenVisual": {
            "color": "#9f87ff",
            "shape": "circle",
            "image_url": str(template.get("imageUrl") or "").strip() or None,
            "fallbackEmoji": "🦇",
        },
    }


def resolve_tinker_mechanist_actor(*, native_document: dict[str, Any], template: dict[str, Any], selected_variant: str, owner_user: User, profile_id: str) -> dict[str, Any]:
    primary = _resolve_primary_class(native_document)
    class_id = str(primary.get("classId") or primary.get("id") or "").strip().lower()
    subclass_id = str(primary.get("subclassId") or "").strip().lower()
    class_level = _safe_int(primary.get("level"), 1, minimum=1, maximum=20)
    if class_id != "tinker" or subclass_id != "mechanist":
        raise ValueError("tinker_mechanist_only")
    if selected_variant != "tinker-mechanist-companion-frame":
        raise ValueError("invalid_variant")

    ability_scores = ((native_document.get("abilities") or {}).get("scores") or {}) if isinstance(native_document.get("abilities"), dict) else {}
    int_mod = _ability_mod(ability_scores.get("int", 10))
    proficiency = _proficiency_bonus(class_level)
    hp = max(5, _safe_int(_TINKER_MECHANIST_FRAME["hp_base"], 10) + (_safe_int(_TINKER_MECHANIST_FRAME["hp_per_level"], 5) * class_level) + int_mod)
    ac = max(10, _safe_int(_TINKER_MECHANIST_FRAME["ac_base"], 13) + max(0, proficiency - 2))
    token_name = str(template.get("tokenName") or template.get("displayName") or "Companion Frame").strip()
    command_model = str(template.get("commandModel") or "bonus_action_command").strip().lower()
    action_rows = [
        _normalize_action_payload(
            actor={},
            action=row,
            index=index,
            attack_bonus=proficiency + int_mod,
            save_dc=8 + proficiency + int_mod,
            command_model=command_model,
        )
        for index, row in enumerate(list(_TINKER_MECHANIST_FRAME.get("actions") or []))
        if isinstance(row, dict)
    ]
    return {
        "id": f"summon-{owner_user.id}-{int(time.time() * 1000)}",
        "templateId": str(template.get("id") or selected_variant),
        "variantId": selected_variant,
        "variantName": str(template.get("displayName") or token_name),
        "name": token_name,
        "actorType": "construct",
        "summonCategory": "construct",
        "size": str(_TINKER_MECHANIST_FRAME.get("size") or template.get("size") or "medium"),
        "movement": copy.deepcopy(_TINKER_MECHANIST_FRAME.get("movement") or template.get("movement") or {"walk": 30}),
        "senses": copy.deepcopy(_TINKER_MECHANIST_FRAME.get("senses") or template.get("senses") or {}),
        "ac": ac,
        "hp": {"current": hp, "max": hp},
        "actions": action_rows,
        "attacks": _legacy_attacks_from_actions(action_rows),
        "traits": copy.deepcopy(_TINKER_MECHANIST_FRAME.get("traits") or []),
        "proficiencyBonus": proficiency,
        "levelSource": {
            "classId": "tinker",
            "subclassId": "mechanist",
            "classLevel": class_level,
            "featureId": str(template.get("sourceFeatureId") or "mechanist-companion-frame"),
            "featureName": "Companion Frame",
        },
        "owner": {"userId": str(owner_user.id), "userName": str(owner_user.name), "profileId": str(profile_id or "")},
        "commandModel": command_model,
        "source": {
            "classId": str(template.get("sourceClassId") or "tinker"),
            "subclassId": str(template.get("sourceSubclassId") or "mechanist"),
            "featureId": str(template.get("sourceFeatureId") or "mechanist-companion-frame"),
            "variantGroup": str(template.get("variantGroup") or "tinker-mechanist-frame"),
        },
        "tokenVisual": {
            "color": "#6fd7ff",
            "shape": "square",
            "image_url": str(template.get("imageUrl") or "").strip() or None,
            "fallbackEmoji": "⚙️",
        },
    }


def resolve_tinker_artillerist_actor(*, native_document: dict[str, Any], template: dict[str, Any], selected_variant: str, owner_user: User, profile_id: str) -> dict[str, Any]:
    primary = _resolve_primary_class(native_document)
    class_id = str(primary.get("classId") or primary.get("id") or "").strip().lower()
    subclass_id = str(primary.get("subclassId") or "").strip().lower()
    class_level = _safe_int(primary.get("level"), 1, minimum=1, maximum=20)
    if class_id != "tinker" or subclass_id != "artillerist":
        raise ValueError("tinker_artillerist_only")
    if selected_variant != "tinker-artillerist-arc-cannon":
        raise ValueError("invalid_variant")

    ability_scores = ((native_document.get("abilities") or {}).get("scores") or {}) if isinstance(native_document.get("abilities"), dict) else {}
    int_mod = _ability_mod(ability_scores.get("int", 10))
    proficiency = _proficiency_bonus(class_level)
    hp = max(
        5,
        _safe_int(_TINKER_ARTILLERIST_ARC_CANNON["hp_base"], 8) + (_safe_int(_TINKER_ARTILLERIST_ARC_CANNON["hp_per_level"], 4) * class_level) + int_mod,
    )
    ac = max(10, _safe_int(_TINKER_ARTILLERIST_ARC_CANNON["ac_base"], 14) + max(0, proficiency - 2))
    token_name = str(template.get("tokenName") or template.get("displayName") or "Arc Cannon").strip()
    command_model = str(template.get("commandModel") or "action_command").strip().lower()
    placement_rules = template.get("placementRules") if isinstance(template.get("placementRules"), dict) else {}
    stationary = bool(placement_rules.get("stationary", True))
    movement = copy.deepcopy(_TINKER_ARTILLERIST_ARC_CANNON.get("movement") or template.get("movement") or {"walk": 15})
    if stationary:
        movement["walk"] = 0
    action_rows = [
        _normalize_action_payload(
            actor={},
            action=row,
            index=index,
            attack_bonus=proficiency + int_mod,
            save_dc=8 + proficiency + int_mod,
            command_model=command_model,
        )
        for index, row in enumerate(list(_TINKER_ARTILLERIST_ARC_CANNON.get("actions") or []))
        if isinstance(row, dict)
    ]
    return {
        "id": f"summon-{owner_user.id}-{int(time.time() * 1000)}",
        "templateId": str(template.get("id") or selected_variant),
        "variantId": selected_variant,
        "variantName": str(template.get("displayName") or token_name),
        "name": token_name,
        "actorType": "deployable",
        "summonCategory": "deployable",
        "isCreature": bool(template.get("isCreature", False)),
        "entityKind": str(template.get("entityKind") or "device").strip().lower(),
        "actionSurfaceType": str(template.get("actionSurfaceType") or "deployed_field_effect").strip().lower(),
        "size": str(_TINKER_ARTILLERIST_ARC_CANNON.get("size") or template.get("size") or "small"),
        "movement": movement,
        "senses": copy.deepcopy(_TINKER_ARTILLERIST_ARC_CANNON.get("senses") or template.get("senses") or {}),
        "ac": ac,
        "hp": {"current": hp, "max": hp},
        "actions": action_rows,
        "attacks": _legacy_attacks_from_actions(action_rows),
        "traits": copy.deepcopy(_TINKER_ARTILLERIST_ARC_CANNON.get("traits") or []),
        "proficiencyBonus": proficiency,
        "levelSource": {
            "classId": "tinker",
            "subclassId": "artillerist",
            "classLevel": class_level,
            "featureId": str(template.get("sourceFeatureId") or "artillerist-arc-cannon"),
            "featureName": "Arc Cannon",
        },
        "owner": {"userId": str(owner_user.id), "userName": str(owner_user.name), "profileId": str(profile_id or "")},
        "commandModel": command_model,
        "interactionModel": {
            "controllable": True,
            "selectable": True,
            "inspectable": True,
            "destructible": True,
            "triggerable": True,
            "passive": False,
            "ownerActivated": True,
            "stationary": stationary,
        },
        "placementRules": copy.deepcopy(placement_rules),
        "cleanupPolicy": copy.deepcopy(template.get("cleanupPolicy") or {}),
        "source": {
            "classId": str(template.get("sourceClassId") or "tinker"),
            "subclassId": str(template.get("sourceSubclassId") or "artillerist"),
            "featureId": str(template.get("sourceFeatureId") or "artillerist-arc-cannon"),
            "variantGroup": str(template.get("variantGroup") or "tinker-artillerist-cannon"),
        },
        "tokenVisual": {
            "color": "#ffb466",
            "shape": "square",
            "image_url": str(template.get("imageUrl") or "").strip() or None,
            "fallbackEmoji": "💥",
        },
    }


def resolve_spell_manifestation_actor(*, template: dict[str, Any], selected_variant: str, owner_user: User, profile_id: str) -> dict[str, Any]:
    token_name = str(template.get("tokenName") or template.get("displayName") or "Spell Manifestation").strip()
    command_model = str(template.get("commandModel") or "spell_effect").strip().lower()
    spell_id = str(template.get("spellId") or "").strip().lower()
    summon_id = f"summon-{owner_user.id}-{int(time.time() * 1000)}"
    return {
        "id": summon_id,
        "templateId": str(template.get("id") or selected_variant),
        "variantId": selected_variant,
        "variantName": str(template.get("displayName") or token_name),
        "name": token_name,
        "actorType": "spell_effect",
        "summonCategory": "spell_effect",
        "size": str(template.get("size") or "medium"),
        "movement": copy.deepcopy(template.get("movement") or {"walk": 30}),
        "senses": copy.deepcopy(template.get("senses") or {}),
        "ac": 10,
        "hp": {"current": 1, "max": 1},
        "actions": [],
        "attacks": [],
        "traits": ["Spell-created temporary manifestation"],
        "proficiencyBonus": 0,
        "levelSource": {
            "classId": "spell",
            "subclassId": "",
            "classLevel": 1,
            "featureId": str(template.get("sourceFeatureId") or f"spell:{spell_id}"),
            "featureName": str(template.get("displayName") or "Spell Manifestation"),
        },
        "owner": {"userId": str(owner_user.id), "userName": str(owner_user.name), "profileId": str(profile_id or "")},
        "commandModel": command_model,
        "source": {
            "classId": "spell",
            "subclassId": "",
            "featureId": str(template.get("sourceFeatureId") or f"spell:{spell_id}"),
            "variantGroup": str(template.get("variantGroup") or template.get("id") or "").strip().lower(),
            "summonOrigin": "spell",
            "spellId": spell_id,
        },
        "tokenVisual": {
            "color": "#d4af37",
            "shape": "circle",
            "image_url": str(template.get("imageUrl") or "").strip() or None,
            "fallbackEmoji": "✨",
        },
        "temporary": bool(template.get("temporary")),
        "spellId": spell_id,
        "concentrationRequired": bool(template.get("concentrationRequired")),
    }


def _summoner_anchor_token(session: Session, user: User, map_context: str):
    best = None
    best_id = ""
    for tok in (getattr(session, "tokens", {}) or {}).values():
        if str(getattr(tok, "owner_id", "") or "") != str(user.id):
            continue
        if bool(getattr(tok, "staged", False)):
            continue
        if str(getattr(tok, "map_context", "world") or "world") != map_context:
            continue
        if str(getattr(tok, "token_type", "player") or "player").strip().lower() == "companion":
            continue
        tok_id = str(getattr(tok, "id", "") or "")
        if best is None or tok_id < best_id:
            best = tok
            best_id = tok_id
    return best


def _compute_spawn_position(session: Session, user: User, map_context: str) -> tuple[float, float, float, float]:
    anchor = _summoner_anchor_token(session, user, map_context)
    if anchor:
        width = max(32.0, float(getattr(anchor, "width", 40.0) or 40.0))
        height = max(32.0, float(getattr(anchor, "height", 40.0) or 40.0))
        return (
            float(getattr(anchor, "x", 100.0) or 100.0) + width,
            float(getattr(anchor, "y", 100.0) or 100.0),
            width,
            height,
        )
    return 120.0, 120.0, 40.0, 40.0


def _notes_for_actor(actor: dict[str, Any]) -> str:
    movement = actor.get("movement") if isinstance(actor.get("movement"), dict) else {}
    movement_text = ", ".join(f"{k}:{v}" for k, v in movement.items()) or "walk:30"
    attacks = actor.get("actions") if isinstance(actor.get("actions"), list) else (actor.get("attacks") if isinstance(actor.get("attacks"), list) else [])
    attack_lines = []
    for row in attacks:
        if not isinstance(row, dict):
            continue
        damage = row.get('damage') if isinstance(row.get('damage'), dict) else {}
        dmg_text = damage.get('formula') if isinstance(damage, dict) else row.get('damage', '')
        attack_lines.append(f"{row.get('displayName', row.get('name', 'Attack'))} ({dmg_text or '—'})")
    attack_text = "; ".join(attack_lines) if attack_lines else "Bestial Strike"
    hp = (actor.get("hp") or {}) if isinstance(actor.get("hp"), dict) else {}
    title = str(actor.get("summonCategory") or actor.get("actorType") or "summon").replace("-", " ").title()
    traits = actor.get("traits") if isinstance(actor.get("traits"), list) else []
    traits_text = ", ".join(str(t) for t in traits if str(t).strip())
    return (
        f"{title}\n"
        f"Variant: {actor.get('variantName', actor.get('name', 'Summon'))}\n"
        f"AC: {actor.get('ac', '—')}\n"
        f"HP: {hp.get('current', '—')}/{hp.get('max', '—')}\n"
        f"Movement: {movement_text}\n"
        f"Actions: {attack_text}\n"
        f"Traits: {traits_text or '—'}\n"
        f"Owner: {((actor.get('owner') or {}).get('userName') or '')}"
    )


def _resolve_entity_kind(template: dict[str, Any], actor: dict[str, Any]) -> str:
    actor_type = str(actor.get("actorType") or "").strip().lower()
    summon_category = str(actor.get("summonCategory") or template.get("summonCategory") or "").strip().lower()
    if actor_type == "spell_effect":
        return actor_type
    if summon_category in {"deployable", "construct", "device", "turret"}:
        return summon_category
    if actor_type == "deployable":
        return actor_type
    if summon_category in {"spell_effect", "spell"}:
        return "spell_effect"
    return "creature"


def _resolve_origin_type(template: dict[str, Any], actor: dict[str, Any]) -> str:
    origin = str(template.get("summonOrigin") or ((actor.get("source") or {}).get("summonOrigin")) or "").strip().lower()
    if origin:
        return origin
    source_class = str(template.get("sourceClassId") or ((actor.get("source") or {}).get("classId")) or "").strip().lower()
    if source_class == "spell":
        return "spell"
    return "feature"


def _resolve_control_model(template: dict[str, Any], actor: dict[str, Any]) -> str:
    explicit = str(template.get("controlModel") or actor.get("controlModel") or "").strip().lower()
    if explicit:
        return explicit
    command_model = str(actor.get("commandModel") or template.get("commandModel") or "").strip().lower()
    if command_model in {"bonus_action_command", "action_command"}:
        return "owner_commanded"
    if command_model == "spell_effect":
        return "caster_owned_independent_effect"
    return "owner_controlled"


def _token_icon_for_category(summon_category: str) -> str:
    summon_category = str(summon_category or "").strip().lower()
    if summon_category == "familiar":
        return "🦇"
    if summon_category in {"construct", "deployable", "device", "turret"}:
        return "⚙️"
    if summon_category in {"spell_effect", "spell"}:
        return "✨"
    return "🐾"


def build_active_deployment_entry(
    *,
    actor: dict[str, Any],
    template: dict[str, Any],
    token_id: str,
    owner_user: User,
    profile_id: str,
    selected_variant: str,
    map_context: str,
    created_at: float | None = None,
) -> dict[str, Any]:
    # Shared deployment entity model for all live families (companion/familiar,
    # spell manifestations, and non-creature deployables). Add future families by
    # feeding this builder, not by introducing family-specific state schemas.
    now = float(created_at if created_at is not None else time.time())
    source = copy.deepcopy(actor.get("source") or {}) if isinstance(actor.get("source"), dict) else {}
    template_id = str(actor.get("templateId") or template.get("id") or selected_variant or "").strip().lower()
    summon_group_id = str(source.get("variantGroup") or template.get("variantGroup") or "").strip().lower()
    origin_type = _resolve_origin_type(template, actor)
    duration_seconds = int(template.get("durationSeconds") or 0)
    is_temporary = bool(template.get("temporary"))
    expires_at = (now + duration_seconds) if is_temporary and duration_seconds > 0 else None
    return {
        "id": str(actor.get("id") or ""),
        "entityId": str(actor.get("id") or ""),
        "entityKind": _resolve_entity_kind(template, actor),
        "templateId": template_id,
        "summonTemplateId": template_id,
        "variantId": selected_variant,
        "variant": selected_variant,
        "summonGroupId": summon_group_id,
        "sourceOriginType": origin_type,
        "sourceClassId": str(source.get("classId") or template.get("sourceClassId") or "").strip().lower(),
        "sourceSubclassId": str(source.get("subclassId") or template.get("sourceSubclassId") or "").strip().lower(),
        "sourceFeatureId": str(source.get("featureId") or template.get("sourceFeatureId") or "").strip().lower(),
        "summonOrigin": origin_type,
        "spellId": str(template.get("spellId") or source.get("spellId") or "").strip().lower(),
        "tokenId": str(token_id or ""),
        "ownerUserId": str(owner_user.id),
        "ownerProfileId": str(profile_id or ""),
        "mapContext": str(map_context or "world"),
        "sceneId": str(map_context or "world"),
        "status": "active",
        "durationSeconds": duration_seconds,
        "expiresAt": expires_at,
        "temporary": is_temporary,
        "concentrationRequired": bool(template.get("concentrationRequired")),
        "cleanupPolicy": copy.deepcopy(template.get("cleanupPolicy") if isinstance(template.get("cleanupPolicy"), (dict, list)) else (list(template.get("cleanupPolicy") or []) if template.get("cleanupPolicy") else [])),
        "maxActive": int(template.get("maxActive") or 1),
        "replaceOnResummon": bool(template.get("replaceOnResummon")),
        "controlModel": _resolve_control_model(template, actor),
        "commandModel": str(actor.get("commandModel") or template.get("commandModel") or "").strip().lower(),
        "createdAt": now,
        "updatedAt": now,
        "spawnedAt": now,
        "source": source,
        "actor": actor,
    }


def normalize_deployment_ui_entry(*, active_entry: dict[str, Any], token: Any = None, owner_name: str = "", owner_bucket_key: str = "", profile_index: int = -1, profile_id: str = "") -> dict[str, Any]:
    row = copy.deepcopy(active_entry if isinstance(active_entry, dict) else {})
    map_context = str(
        getattr(token, "map_context", "") or row.get("mapContext") or row.get("sceneId") or "world"
    ).strip() or "world"
    actor = row.get("actor") if isinstance(row.get("actor"), dict) else {}
    resolved_owner_name = str(owner_name or ((actor.get("owner") or {}).get("userName") or "")).strip()
    row["ownerBucketKey"] = str(owner_bucket_key or "")
    row["profileIndex"] = int(profile_index)
    row["profileId"] = str(profile_id or row.get("ownerProfileId") or "")
    row["ownerName"] = resolved_owner_name
    row["tokenPresent"] = bool(token)
    row["tokenName"] = str(getattr(token, "name", "") or actor.get("name") or "")
    row["tokenMapContext"] = map_context
    row["ui"] = {
        "entityLabel": str(actor.get("name") or row.get("variantId") or "Summon"),
        "kindLabel": str(row.get("entityKind") or "creature").replace("_", " "),
        "originLabel": str(row.get("sourceOriginType") or row.get("summonOrigin") or "feature"),
        "temporary": bool(row.get("temporary")),
        "controllable": str(row.get("controlModel") or "").strip().lower() not in {"passive", "none"},
    }
    return row


def _build_token_payload(*, actor: dict[str, Any], user: User, map_context: str, sx: float, sy: float, sw: float, sh: float) -> dict[str, Any]:
    summon_category = str(actor.get("summonCategory") or "").strip().lower()
    icon = _token_icon_for_category(summon_category)
    return {
        "name": f"{icon} {actor.get('name', 'Summon')}",
        "x": sx,
        "y": sy,
        "width": sw,
        "height": sh,
        "map_context": map_context,
        "owner_id": user.id,
        "hp": int(((actor.get("hp") or {}).get("current") or 1)),
        "max_hp": int(((actor.get("hp") or {}).get("max") or 1)),
        "ac": int(actor.get("ac") or 10),
        "speed": int((actor.get("movement") or {}).get("walk") or 0),
        "token_type": "companion",
        "faction": "allies",
        "notes": _notes_for_actor(actor),
        "image_url": ((actor.get("tokenVisual") or {}).get("image_url") or None),
        "monster_type": summon_category or "summon",
    }


def _entry_group_id(row: dict[str, Any]) -> str:
    return str(row.get("summonGroupId") or ((row.get("source") or {}).get("variantGroup")) or "").strip().lower()


def _entry_template_id(row: dict[str, Any]) -> str:
    return str(row.get("templateId") or row.get("summonTemplateId") or "").strip().lower()


def _entry_source_feature_id(row: dict[str, Any]) -> str:
    return str(row.get("sourceFeatureId") or ((row.get("source") or {}).get("featureId")) or "").strip().lower()


def _entry_owner_profile_id(row: dict[str, Any]) -> str:
    return str(row.get("ownerProfileId") or ((row.get("owner") or {}).get("profileId")) or "").strip()


def _entry_temporary(row: dict[str, Any]) -> bool:
    if row.get("temporary") is not None:
        return bool(row.get("temporary"))
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    return bool(source.get("temporary")) or str(source.get("summonOrigin") or "").strip().lower() == "spell"


def _template_for_row(row: dict[str, Any]) -> dict[str, Any]:
    return get_summon_template(_entry_template_id(row)) or {}


def _active_rows(summons: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in (summons.get("activeSummons") or []) if isinstance(row, dict)]


def _summon_limit_policy(summons: dict[str, Any], template: dict[str, Any], group_id: str) -> tuple[int, bool]:
    rules = summons.get("rules") if isinstance(summons.get("rules"), dict) else {}
    per_group = rules.get("maxActiveByGroup") if isinstance(rules.get("maxActiveByGroup"), dict) else {}
    per_template = rules.get("maxActiveByTemplate") if isinstance(rules.get("maxActiveByTemplate"), dict) else {}
    replace_rules = rules.get("replaceOnResummonByGroup") if isinstance(rules.get("replaceOnResummonByGroup"), dict) else {}
    template_id = str(template.get("id") or "").strip().lower()
    max_active = _safe_int(template.get("maxActive"), 1, minimum=0)
    if group_id and per_group.get(group_id) is not None:
        max_active = _safe_int(per_group.get(group_id), max_active, minimum=0)
    if template_id and per_template.get(template_id) is not None:
        max_active = _safe_int(per_template.get(template_id), max_active, minimum=0)
    replace = bool(template.get("replaceOnResummon"))
    if group_id in replace_rules:
        replace = bool(replace_rules.get(group_id))
    return max_active, replace


def plan_active_summon_mutations(native_document: dict[str, Any], *, active_entry: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    summons = normalize_summon_state(native_document.get("summons"))
    group_id = _entry_group_id(active_entry)
    template_id = _entry_template_id(active_entry)
    owner_profile_id = _entry_owner_profile_id(active_entry)
    source_feature_id = _entry_source_feature_id(active_entry)
    max_active, replace_on_resummon = _summon_limit_policy(summons, template, group_id)

    existing = _active_rows(summons)
    scoped = [
        row for row in existing
        if _entry_owner_profile_id(row) == owner_profile_id
        and (_entry_group_id(row) == group_id or _entry_template_id(row) == template_id)
    ]
    to_remove: list[dict[str, Any]] = []
    if replace_on_resummon and scoped:
        to_remove.extend(scoped)
    elif max_active >= 0 and len(scoped) >= max_active > 0:
        overflow = (len(scoped) - max_active) + 1
        to_remove.extend(scoped[:overflow])
    if max_active == 0:
        to_remove.extend(scoped)
    # deterministic unique removes
    seen: set[str] = set()
    unique = []
    for row in to_remove:
        key = str(row.get("id") or row.get("tokenId") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(copy.deepcopy(row))
    return {"max_active": max_active, "replace_on_resummon": replace_on_resummon, "remove_entries": unique}


def list_active_summons(
    native_document: dict[str, Any], *,
    template_id: str = "", summon_group_id: str = "", source_feature_id: str = "", owner_profile_id: str = ""
) -> list[dict[str, Any]]:
    summons = normalize_summon_state(native_document.get("summons"))
    match_template = str(template_id or "").strip().lower()
    match_group = str(summon_group_id or "").strip().lower()
    match_feature = str(source_feature_id or "").strip().lower()
    match_owner_profile = str(owner_profile_id or "").strip()
    out = []
    for row in _active_rows(summons):
        if match_template and _entry_template_id(row) != match_template:
            continue
        if match_group and _entry_group_id(row) != match_group:
            continue
        if match_feature and _entry_source_feature_id(row) != match_feature:
            continue
        if match_owner_profile and _entry_owner_profile_id(row) != match_owner_profile:
            continue
        out.append(copy.deepcopy(row))
    return out


def remove_active_summon(
    native_document: dict[str, Any], *,
    active_id: str = "", token_id: str = "", summon_group_id: str = "", source_feature_id: str = "", owner_profile_id: str = ""
) -> list[dict[str, Any]]:
    summons = normalize_summon_state(native_document.get("summons"))
    match_id = str(active_id or "").strip()
    match_token_id = str(token_id or "").strip()
    match_group = str(summon_group_id or "").strip().lower()
    match_feature = str(source_feature_id or "").strip().lower()
    match_owner_profile = str(owner_profile_id or "").strip()
    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for row in (summons.get("activeSummons") or []):
        if not isinstance(row, dict):
            continue
        remove = False
        if match_id and str(row.get("id") or "").strip() == match_id:
            remove = True
        if match_token_id and str(row.get("tokenId") or "").strip() == match_token_id:
            remove = True
        if match_group and _entry_group_id(row) == match_group:
            remove = True
        if match_feature and _entry_source_feature_id(row) == match_feature:
            remove = True
        if match_owner_profile and _entry_owner_profile_id(row) != match_owner_profile:
            remove = False
        if remove:
            removed.append(copy.deepcopy(row))
        else:
            kept.append(row)
    summons["activeSummons"] = kept
    native_document["summons"] = summons
    return removed


def register_active_summon(native_document: dict[str, Any], active_entry: dict[str, Any]) -> dict[str, Any]:
    template_id = _entry_template_id(active_entry)
    template = _template_for_row(active_entry)
    mutation_plan = plan_active_summon_mutations(native_document, active_entry=active_entry, template=template)
    summons = normalize_summon_state(native_document.get("summons"))
    existing_rows = _active_rows(summons)
    owner_profile_id = _entry_owner_profile_id(active_entry)
    remove_ids = {
        str(row.get("id") or "").strip()
        for row in (mutation_plan.get("remove_entries") or [])
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    remove_tokens = {
        str(row.get("tokenId") or "").strip()
        for row in (mutation_plan.get("remove_entries") or [])
        if isinstance(row, dict) and str(row.get("tokenId") or "").strip()
    }
    if remove_ids or remove_tokens:
        existing_rows = [
            row for row in existing_rows
            if not (
                _entry_owner_profile_id(row) == owner_profile_id
                and (
                    str(row.get("id") or "").strip() in remove_ids
                    or str(row.get("tokenId") or "").strip() in remove_tokens
                )
            )
        ]
    group_id = _entry_group_id(active_entry)

    row = copy.deepcopy(active_entry)
    row["templateId"] = template_id
    row["summonTemplateId"] = template_id
    row["summonGroupId"] = group_id
    row["sourceFeatureId"] = _entry_source_feature_id(active_entry)
    row["sourceClassId"] = str(row.get("sourceClassId") or ((row.get("source") or {}).get("classId")) or "").strip().lower()
    row["sourceSubclassId"] = str(row.get("sourceSubclassId") or ((row.get("source") or {}).get("subclassId")) or "").strip().lower()
    row["ownerProfileId"] = _entry_owner_profile_id(active_entry)
    row["variant"] = str(row.get("variant") or row.get("variantId") or template_id).strip().lower()
    row["status"] = str(row.get("status") or "active").strip().lower() or "active"
    row["updatedAt"] = time.time()
    row["createdAt"] = row.get("createdAt") if row.get("createdAt") is not None else row.get("spawnedAt", row["updatedAt"])
    if row.get("maxActive") is None:
        row["maxActive"] = mutation_plan.get("max_active")
    if row.get("replaceOnResummon") is None:
        row["replaceOnResummon"] = bool(mutation_plan.get("replace_on_resummon"))
    summons["activeSummons"] = existing_rows + [row]
    if group_id and str(active_entry.get("variantId") or "").strip():
        selected = summons.get("selectedVariants") if isinstance(summons.get("selectedVariants"), dict) else {}
        selected[group_id] = str(active_entry.get("variantId") or "").strip().lower()
        summons["selectedVariants"] = selected
    native_document["summons"] = summons
    return native_document


def reconcile_native_summons(
    native_document: dict[str, Any], *,
    existing_token_ids: set[str] | None = None,
    valid_map_contexts: set[str] | None = None,
) -> dict[str, Any]:
    summons = normalize_summon_state(native_document.get("summons"))
    active_rows = _active_rows(summons)
    _record_runtime_metric("reconcile_calls")
    _record_runtime_metric("reconcile_rows_scanned", len(active_rows))
    kept: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_tokens: set[str] = set()
    for row in active_rows:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("id") or "").strip()
        token_id = str(row.get("tokenId") or "").strip()
        map_context = str(row.get("mapContext") or row.get("sceneId") or "").strip()
        if row_id and row_id in seen_ids:
            continue
        if token_id and token_id in seen_tokens:
            continue
        if existing_token_ids is not None and token_id and token_id not in existing_token_ids:
            continue
        if valid_map_contexts is not None and map_context and map_context not in valid_map_contexts:
            continue
        if row_id:
            seen_ids.add(row_id)
        if token_id:
            seen_tokens.add(token_id)
        kept.append(copy.deepcopy(row))
    if len(kept) != len(active_rows):
        _record_runtime_metric("reconcile_rows_pruned", len(active_rows) - len(kept))
    summons["activeSummons"] = kept
    native_document["summons"] = summons
    return native_document


def prune_expired_temporary_summons(
    native_document: dict[str, Any],
    *,
    now_ts: float | None = None,
    rest_type: str = "",
) -> list[dict[str, Any]]:
    summons = normalize_summon_state(native_document.get("summons"))
    rows = _active_rows(summons)
    _record_runtime_metric("prune_calls")
    _record_runtime_metric("prune_rows_scanned", len(rows))
    now_value = float(now_ts if now_ts is not None else time.time())
    rest_mode = str(rest_type or "").strip().lower()
    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        should_remove = False
        if _entry_temporary(row):
            expires_at = row.get("expiresAt")
            try:
                if expires_at is not None and float(expires_at) <= now_value:
                    should_remove = True
            except Exception:
                pass
            if rest_mode in {"short", "long"}:
                cleanup = row.get("cleanupPolicy")
                cleanup_rules = set(str(v or "").strip().lower() for v in cleanup) if isinstance(cleanup, list) else set()
                if f"{rest_mode}_rest" in cleanup_rules:
                    should_remove = True
        if should_remove:
            removed.append(copy.deepcopy(row))
        else:
            kept.append(row)
    if removed:
        _record_runtime_metric("prune_rows_removed", len(removed))
        summons["activeSummons"] = kept
        native_document["summons"] = summons
    return removed


def reconcile_session_active_summons(session: Session) -> int:
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    valid_token_ids = {str(tid) for tid in (getattr(session, "tokens", {}) or {}).keys()}
    valid_map_contexts = {"world"}
    valid_map_contexts.update(str(k or "").strip() for k in (getattr(session, "pois", {}) or {}).keys())
    valid_map_contexts.update(str(k or "").strip() for k in (getattr(session, "map_documents", {}) or {}).keys())
    changed = 0
    for owner_key, rows in list(profiles.items()):
        if not isinstance(rows, list):
            continue
        bucket = list(rows)
        for idx, row in enumerate(bucket):
            if not isinstance(row, dict):
                continue
            native = row.get("nativeCharacter") if isinstance(row.get("nativeCharacter"), dict) else {}
            before = normalize_summon_state(native.get("summons"))
            reconcile_native_summons(native, existing_token_ids=valid_token_ids, valid_map_contexts=valid_map_contexts)
            after = normalize_summon_state(native.get("summons"))
            if before != after:
                row["nativeCharacter"] = native
                bucket[idx] = row
                changed += 1
        profiles[owner_key] = bucket
    if changed:
        session.char_profiles = profiles
    return changed


def synchronize_active_summon_state(native_document: dict[str, Any], *, token_id: str, hp_current: int | None = None, hp_max: int | None = None, remove: bool = False) -> bool:
    summons = normalize_summon_state(native_document.get("summons"))
    rows = list(summons.get("activeSummons") or [])
    changed = False
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_token_id = str(row.get("tokenId") or "").strip()
        if row_token_id != str(token_id or "").strip():
            out.append(row)
            continue
        if remove:
            changed = True
            continue
        next_row = copy.deepcopy(row)
        actor = next_row.get("actor") if isinstance(next_row.get("actor"), dict) else {}
        hp = actor.get("hp") if isinstance(actor.get("hp"), dict) else {}
        if hp_current is not None and hp.get("current") != hp_current:
            hp["current"] = max(0, int(hp_current))
            changed = True
        if hp_max is not None and hp.get("max") != hp_max:
            hp["max"] = max(1, int(hp_max))
            changed = True
        if hp:
            actor["hp"] = hp
            next_row["actor"] = actor
        if hp_current is not None and int(hp_current) <= 0 and next_row.get("status") != "defeated":
            next_row["status"] = "defeated"
            changed = True
        elif hp_current is not None and int(hp_current) > 0 and str(next_row.get("status") or "active") != "active":
            next_row["status"] = "active"
            changed = True
        if changed:
            next_row["updatedAt"] = time.time()
        out.append(next_row)
    if changed or remove:
        summons["activeSummons"] = out
        native_document["summons"] = summons
    return changed or remove


def build_summon_runtime_payload(*, session: Session, user: User, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    requested_profile_id = str(payload.get("profile_id") or payload.get("profileId") or "").strip()
    context: dict[str, Any] = {
        "owner_user_id": str(getattr(user, "id", "") or ""),
        "owner_role": str(getattr(user, "role", "") or ""),
        "profile_id": requested_profile_id,
        "summon_template_id": str(payload.get("summon_template_id") or payload.get("summonTemplateId") or "").strip().lower(),
        "summon_group_id": str(payload.get("summon_group_id") or payload.get("summonGroupId") or "").strip().lower(),
    }
    owner_key, profile_index, profile = _find_active_profile(session, user, requested_profile_id)
    if profile_index < 0 or not isinstance(profile, dict):
        return _runtime_failure("profile_not_found", message="No active character profile was found for this summon request.", context=context)

    native = profile.get("nativeCharacter") if isinstance(profile.get("nativeCharacter"), dict) else {}
    if not native:
        return _runtime_failure("missing_native_character", message="The selected profile is missing native character data.", context=context)

    summons = normalize_summon_state(native.get("summons"))
    unlocked = {str(v).strip().lower() for v in (summons.get("unlockedTemplates") or []) if str(v).strip()}

    requested_template = str(payload.get("summon_template_id") or payload.get("summonTemplateId") or "").strip().lower()
    requested_group = str(payload.get("summon_group_id") or payload.get("summonGroupId") or "").strip().lower()
    requested_variant = str(payload.get("selected_variant") or payload.get("selectedVariant") or payload.get("selectedVariantId") or requested_template).strip().lower()
    requested_spell_id = str(payload.get("spell_id") or payload.get("spellId") or "").strip().lower()
    selected_variant, template, variant_error = _resolve_variant(
        template_id=requested_template,
        selected_variant=requested_variant,
        summon_group_id=requested_group,
        native_document=native,
        unlocked=unlocked,
    )
    if variant_error or not template:
        return _runtime_failure(
            variant_error or "invalid_variant",
            message="The selected summon variant could not be resolved from unlocked templates.",
            context={**context, "resolved_template_id": str((template or {}).get("id") or "")},
        )
    template_origin = str(template.get("summonOrigin") or "").strip().lower()
    template_spell_id = str(template.get("spellId") or "").strip().lower()
    is_spell_template = template_origin == "spell" and bool(template_spell_id)
    if selected_variant not in unlocked and not is_spell_template:
        return _runtime_failure("summon_not_unlocked", message="This summon template is not unlocked for the selected profile.", context=context)
    if is_spell_template:
        if requested_spell_id != template_spell_id:
            return _runtime_failure("invalid_variant", message="Spell summon request spell_id does not match the selected template.", context={**context, "template_spell_id": template_spell_id})
        available_spells = _extract_profile_spell_ids(native)
        if template_spell_id not in available_spells:
            return _runtime_failure("spell_not_available", message="The selected spell summon is not currently available on the profile spell list.", context={**context, "template_spell_id": template_spell_id})

    try:
        source_class = str(template.get("sourceClassId") or "").strip().lower()
        source_subclass = str(template.get("sourceSubclassId") or "").strip().lower()
        summon_category = str(template.get("summonCategory") or "").strip().lower()
        resolver_key = (source_class, source_subclass, summon_category)
        owner_profile_id = str(profile.get("id") or requested_profile_id or "")
        runtime_resolvers = {
            ("ranger", "beast-master", ""): lambda: resolve_beast_master_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("ranger", "beast-master", "companion"): lambda: resolve_beast_master_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("warlock", "", "familiar"): lambda: resolve_warlock_familiar_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("tinker", "mechanist", ""): lambda: resolve_tinker_mechanist_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("tinker", "mechanist", "construct"): lambda: resolve_tinker_mechanist_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("tinker", "artillerist", ""): lambda: resolve_tinker_artillerist_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("tinker", "artillerist", "deployable"): lambda: resolve_tinker_artillerist_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=owner_profile_id,
            ),
            ("spell", "", "spell_effect"): lambda: resolve_spell_manifestation_actor(
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=str(profile.get("id") or requested_profile_id or ""),
            ),
        }
        resolver = runtime_resolvers.get(resolver_key)
        if resolver is None:
            return _runtime_failure("runtime_not_live_for_class", message="This summon family is not currently live in runtime deployment.", context={**context, "source_class": source_class, "source_subclass": source_subclass})
        actor = resolver()
        entity_kind = _resolve_entity_kind(template, actor)
        is_creature = entity_kind == "creature"
    except ValueError as exc:
        code = str(exc) or "runtime_resolution_failed"
        return _runtime_failure(code, message="Summon actor resolution failed for the selected deployment variant.", context=context)

    map_context = _resolve_map_context(session, user, payload)
    if not map_context:
        return _runtime_failure("missing_map_context", message="No valid map context was available for summon placement.", context=context)

    sx, sy, sw, sh = _compute_spawn_position(session, user, map_context)
    token_size = str(actor.get("size") or "medium").lower()
    if token_size == "small":
        sw = sh = 32.0
    elif token_size == "medium":
        sw = sh = 40.0

    token_payload = _build_token_payload(actor=actor, user=user, map_context=map_context, sx=sx, sy=sy, sw=sw, sh=sh)

    result = {
        "ok": True,
        "owner_key": owner_key,
        "profile_index": profile_index,
        "profile_id": str(profile.get("id") or ""),
        "native_document": native,
        "template": template,
        "selected_variant": selected_variant,
        "summon_group_id": str((template.get("variantGroup") or requested_group or "")).strip().lower(),
        "actor": actor,
        "token_payload": token_payload,
        "map_context": map_context,
        "entity_kind": entity_kind or "creature",
        "is_creature": is_creature,
    }
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    _record_runtime_metric("build_payload_calls")
    _record_runtime_metric("build_payload_ms_total", elapsed_ms)
    with _METRICS_LOCK:
        _SUMMON_RUNTIME_METRICS["build_payload_ms_last"] = elapsed_ms
    return result
