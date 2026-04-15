"""Runtime summon orchestration (Pass C Beast Master vertical slice)."""
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


def _resolve_variant(template_id: str, selected_variant: str, native_document: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str]:
    requested = str(selected_variant or template_id or "").strip().lower()
    template = get_summon_template(requested)
    if template:
        return requested, template, ""

    summons = native_document.get("summons") if isinstance(native_document.get("summons"), dict) else {}
    selected_variants = summons.get("selectedVariants") if isinstance(summons.get("selectedVariants"), dict) else {}
    fallback = str(selected_variants.get("ranger-primal-beast") or "").strip().lower()
    if fallback:
        template = get_summon_template(fallback)
        if template:
            return fallback, template, ""

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
    return (
        f"Beast Master Companion\n"
        f"Variant: {actor.get('variantName', actor.get('name', 'Primal Beast'))}\n"
        f"AC: {actor.get('ac', '—')}\n"
        f"HP: {hp.get('current', '—')}/{hp.get('max', '—')}\n"
        f"Movement: {movement_text}\n"
        f"Actions: {attack_text}\n"
        f"Owner: {((actor.get('owner') or {}).get('userName') or '')}"
    )


def register_active_summon(native_document: dict[str, Any], active_entry: dict[str, Any]) -> dict[str, Any]:
    summons = normalize_summon_state(native_document.get("summons"))
    group_id = str(((active_entry.get("source") or {}).get("variantGroup") or "")).strip().lower()

    filtered: list[dict[str, Any]] = []
    for row in (summons.get("activeSummons") or []):
        if not isinstance(row, dict):
            continue
        row_group = str(((row.get("source") or {}).get("variantGroup") or row.get("summonGroupId") or "")).strip().lower()
        if row_group and group_id and row_group == group_id:
            continue
        filtered.append(row)

    filtered.append(copy.deepcopy(active_entry))
    summons["activeSummons"] = filtered
    if group_id and str(active_entry.get("variantId") or "").strip():
        selected = summons.get("selectedVariants") if isinstance(summons.get("selectedVariants"), dict) else {}
        selected[group_id] = str(active_entry.get("variantId") or "").strip().lower()
        summons["selectedVariants"] = selected
    native_document["summons"] = summons
    return native_document


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
    requested_variant = str(payload.get("selected_variant") or payload.get("selectedVariant") or payload.get("selectedVariantId") or requested_template).strip().lower()
    selected_variant, template, variant_error = _resolve_variant(requested_template, requested_variant, native)
    if variant_error or not template:
        return {"ok": False, "error": variant_error or "invalid_variant"}
    if selected_variant not in unlocked:
        return {"ok": False, "error": "summon_not_unlocked"}

    try:
        actor = resolve_beast_master_actor(
            native_document=native,
            template=template,
            selected_variant=selected_variant,
            owner_user=user,
            profile_id=str(profile.get("id") or requested_profile_id or ""),
        )
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

    token_payload = {
        "name": f"🐾 {actor.get('name', 'Primal Beast')}",
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
    }

    return {
        "ok": True,
        "owner_key": owner_key,
        "profile_index": profile_index,
        "profile_id": str(profile.get("id") or ""),
        "native_document": native,
        "template": template,
        "selected_variant": selected_variant,
        "actor": actor,
        "token_payload": token_payload,
        "map_context": map_context,
    }
