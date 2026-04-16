"""Runtime summon orchestration (Pass D: Beast Master + Warlock familiar + Tinker mechanist)."""
from __future__ import annotations

import copy
import time
from typing import Any

from server.character.summon_catalog import get_summon_template
from server.character.summon_state import normalize_summon_state
from server.session import Session, User


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
        "actions": [
            {
                "id": "maul",
                "name": "Maul",
                "toHit": "PB + WIS",
                "damage": "1d8 + 2 + PB",
                "type": "force",
                "rider": "If target is Large or smaller, it is knocked Prone.",
            }
        ],
    },
    "ranger-primal-beast-sea": {
        "movement": {"walk": 5, "swim": 60},
        "size": "medium",
        "senses": {"darkvision": 60},
        "actions": [
            {
                "id": "binding_strike",
                "name": "Binding Strike",
                "toHit": "PB + WIS",
                "damage": "1d6 + 2 + PB",
                "type": "piercing",
                "rider": "Target grappled (escape DC = spell save DC equivalent).",
            }
        ],
    },
    "ranger-primal-beast-sky": {
        "movement": {"walk": 10, "fly": 60},
        "size": "small",
        "senses": {"darkvision": 60},
        "actions": [
            {
                "id": "shred",
                "name": "Shred",
                "toHit": "PB + WIS",
                "damage": "1d4 + 3 + PB",
                "type": "slashing",
                "rider": "Flyby-style movement profile for hit-and-run positioning.",
            }
        ],
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
            {
                "id": "sting",
                "name": "Sting",
                "toHit": "+5",
                "damage": "1d4+3 piercing",
                "rider": "Poison save (DC 11).",
            }
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
            {
                "id": "sting",
                "name": "Sting",
                "toHit": "+4",
                "damage": "1d4+2 piercing",
                "rider": "Poison save (DC 11) vs poisoned/unconscious.",
            }
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
            {
                "id": "claws",
                "name": "Claws",
                "toHit": "+4",
                "damage": "1d4+3 slashing",
                "rider": "Poison save (DC 10).",
            }
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
            {
                "id": "shortbow",
                "name": "Shortbow",
                "toHit": "+6",
                "damage": "1 piercing",
                "rider": "Poison save (DC 10) vs poisoned.",
            }
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
        {
            "id": "force_slam",
            "name": "Force Slam",
            "toHit": "PB + INT",
            "damage": "1d8 + PB force",
            "rider": "On hit, can shove 5 ft if target fails STR save.",
        }
    ],
}


def _ability_mod(value: Any) -> int:
    return (_safe_int(value, 10) - 10) // 2


def _proficiency_bonus(level_total: int) -> int:
    return 2 + max(0, (max(1, level_total) - 1) // 4)


def _resolve_primary_class(native_document: dict[str, Any]) -> dict[str, Any]:
    classes = native_document.get("classes") if isinstance(native_document.get("classes"), list) else []
    return classes[0] if classes and isinstance(classes[0], dict) else {}


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
        "attacks": copy.deepcopy(variant_defaults.get("actions") or []),
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
        "attacks": copy.deepcopy(familiar.get("actions") or []),
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
        "attacks": copy.deepcopy(_TINKER_MECHANIST_FRAME.get("actions") or []),
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


def _summoner_anchor_token(session: Session, user: User, map_context: str):
    owned = []
    for tok in (getattr(session, "tokens", {}) or {}).values():
        if str(getattr(tok, "owner_id", "") or "") != str(user.id):
            continue
        if bool(getattr(tok, "staged", False)):
            continue
        if str(getattr(tok, "map_context", "world") or "world") != map_context:
            continue
        if str(getattr(tok, "token_type", "player") or "player").strip().lower() == "companion":
            continue
        owned.append(tok)
    if owned:
        owned.sort(key=lambda t: str(getattr(t, "id", "")))
        return owned[0]
    return None


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
    attacks = actor.get("attacks") if isinstance(actor.get("attacks"), list) else []
    attack_lines = []
    for row in attacks:
        if not isinstance(row, dict):
            continue
        attack_lines.append(f"{row.get('name', 'Attack')} ({row.get('damage', '')})")
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


def _entry_group_id(row: dict[str, Any]) -> str:
    return str(row.get("summonGroupId") or ((row.get("source") or {}).get("variantGroup")) or "").strip().lower()


def _entry_template_id(row: dict[str, Any]) -> str:
    return str(row.get("templateId") or row.get("summonTemplateId") or "").strip().lower()


def _entry_source_feature_id(row: dict[str, Any]) -> str:
    return str(row.get("sourceFeatureId") or ((row.get("source") or {}).get("featureId")) or "").strip().lower()


def _entry_owner_profile_id(row: dict[str, Any]) -> str:
    return str(row.get("ownerProfileId") or ((row.get("owner") or {}).get("profileId")) or "").strip()


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

    existing: list[dict[str, Any]] = [row for row in (summons.get("activeSummons") or []) if isinstance(row, dict)]
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
    for row in (summons.get("activeSummons") or []):
        if not isinstance(row, dict):
            continue
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
    template = get_summon_template(template_id) or {}
    mutation_plan = plan_active_summon_mutations(native_document, active_entry=active_entry, template=template)
    for row in mutation_plan.get("remove_entries") or []:
        if not isinstance(row, dict):
            continue
        remove_active_summon(
            native_document,
            active_id=str(row.get("id") or ""),
            token_id=str(row.get("tokenId") or ""),
            owner_profile_id=_entry_owner_profile_id(active_entry),
        )

    summons = normalize_summon_state(native_document.get("summons"))
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
    summons["activeSummons"] = list(summons.get("activeSummons") or []) + [row]
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
    active_rows = list(summons.get("activeSummons") or [])
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
    summons["activeSummons"] = kept
    native_document["summons"] = summons
    return native_document


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


def build_summon_runtime_payload(*, session: Session, user: User, payload: dict[str, Any]) -> dict[str, Any]:
    requested_profile_id = str(payload.get("profile_id") or payload.get("profileId") or "").strip()
    owner_key, profile_index, profile = _find_active_profile(session, user, requested_profile_id)
    if profile_index < 0 or not isinstance(profile, dict):
        return {"ok": False, "error": "profile_not_found"}

    native = profile.get("nativeCharacter") if isinstance(profile.get("nativeCharacter"), dict) else {}
    if not native:
        return {"ok": False, "error": "missing_native_character"}

    summons = normalize_summon_state(native.get("summons"))
    unlocked = {str(v).strip().lower() for v in (summons.get("unlockedTemplates") or []) if str(v).strip()}

    requested_template = str(payload.get("summon_template_id") or payload.get("summonTemplateId") or "").strip().lower()
    requested_group = str(payload.get("summon_group_id") or payload.get("summonGroupId") or "").strip().lower()
    requested_variant = str(payload.get("selected_variant") or payload.get("selectedVariant") or payload.get("selectedVariantId") or requested_template).strip().lower()
    selected_variant, template, variant_error = _resolve_variant(
        template_id=requested_template,
        selected_variant=requested_variant,
        summon_group_id=requested_group,
        native_document=native,
        unlocked=unlocked,
    )
    if variant_error or not template:
        return {"ok": False, "error": variant_error or "invalid_variant"}
    if selected_variant not in unlocked:
        return {"ok": False, "error": "summon_not_unlocked"}

    try:
        source_class = str(template.get("sourceClassId") or "").strip().lower()
        source_subclass = str(template.get("sourceSubclassId") or "").strip().lower()
        if source_class == "ranger" and source_subclass == "beast-master":
            actor = resolve_beast_master_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=str(profile.get("id") or requested_profile_id or ""),
            )
        elif source_class == "warlock" and str(template.get("summonCategory") or "").strip().lower() == "familiar":
            actor = resolve_warlock_familiar_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=str(profile.get("id") or requested_profile_id or ""),
            )
        elif source_class == "tinker" and source_subclass == "mechanist":
            actor = resolve_tinker_mechanist_actor(
                native_document=native,
                template=template,
                selected_variant=selected_variant,
                owner_user=user,
                profile_id=str(profile.get("id") or requested_profile_id or ""),
            )
        else:
            return {"ok": False, "error": "runtime_not_live_for_class"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    map_context = _resolve_map_context(session, user, payload)
    if not map_context:
        return {"ok": False, "error": "missing_map_context"}

    sx, sy, sw, sh = _compute_spawn_position(session, user, map_context)
    token_size = str(actor.get("size") or "medium").lower()
    if token_size == "small":
        sw = sh = 32.0
    elif token_size == "medium":
        sw = sh = 40.0

    summon_category = str(actor.get("summonCategory") or "").strip().lower()
    icon = "🐾"
    if summon_category == "familiar":
        icon = "🦇"
    elif summon_category in {"construct", "deployable", "device", "turret"}:
        icon = "⚙️"
    token_payload = {
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

    return {
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
    }
