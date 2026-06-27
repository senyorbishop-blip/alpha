"""Summon template registry, authoring helpers, and validation guards."""
from __future__ import annotations

import copy
from typing import Any


_NON_CREATURE_CATEGORIES = {"deployable", "device", "trap", "ward", "effect", "object", "spell_effect"}
_NON_CREATURE_ENTITY_KINDS = {"deployable", "device", "trap", "ward", "effect", "object", "spell_effect"}
_ALLOWED_ENTITY_KINDS = _NON_CREATURE_ENTITY_KINDS | {"creature", "construct", "familiar", "companion"}
_ALLOWED_COMMAND_MODELS = {"bonus_action_command", "action_command", "spell_effect", "owner_controlled"}


def _source_link(*, class_id: str, feature_id: str, subclass_id: str = "", origin: str = "feature", spell_id: str = "") -> dict[str, Any]:
    # Spell templates are authored with {"summonOrigin": "spell", "temporary": True}.
    block = {
        "sourceClassId": str(class_id or "").strip().lower(),
        "sourceSubclassId": str(subclass_id or "").strip().lower(),
        "sourceFeatureId": str(feature_id or "").strip().lower(),
        "summonOrigin": str(origin or "feature").strip().lower(),
    }
    spell_key = str(spell_id or "").strip().lower()
    if spell_key:
        block["spellId"] = spell_key
    return block


def _lifecycle(*, temporary: bool, duration_seconds: int = 0, concentration_required: bool = False, cleanup_policy: list[str] | None = None) -> dict[str, Any]:
    block = {
        "temporary": bool(temporary),
        "concentrationRequired": bool(concentration_required),
        "durationSeconds": int(duration_seconds or 0),
    }
    if cleanup_policy is not None:
        block["cleanupPolicy"] = [str(row or "").strip().lower() for row in cleanup_policy if str(row or "").strip()]
    return block


def _control(*, model: str = "owner_controlled") -> dict[str, Any]:
    return {"controlModel": str(model or "owner_controlled").strip().lower()}


def _build_template(base: dict[str, Any], *, source: dict[str, Any] | None = None, lifecycle: dict[str, Any] | None = None, control: dict[str, Any] | None = None) -> dict[str, Any]:
    row = copy.deepcopy(base)
    if isinstance(source, dict):
        row.update(source)
    if isinstance(lifecycle, dict):
        row.update(lifecycle)
    if isinstance(control, dict):
        row.update(control)
    return row


SUMMON_TEMPLATE_REGISTRY: dict[str, dict[str, Any]] = {
    "warlock-chain-imp": {
        "id": "warlock-chain-imp",
        "displayName": "Imp Familiar",
        "summonCategory": "familiar",
        "sourceClassId": "warlock",
        "sourceSubclassId": "",
        "sourceFeatureId": "warlock-pact-boon",
        "variantGroup": "warlock-pact-chain-familiar",
        "actorType": "companion",
        "tokenName": "Imp",
        "size": "tiny",
        "movement": {"walk": 20, "fly": 40},
        "senses": {"darkvision": 120},
        "baseStats": {"scaling": "warlock_familiar_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["warlock", "familiar", "chain"],
    },
    "warlock-chain-pseudodragon": {
        "id": "warlock-chain-pseudodragon",
        "displayName": "Pseudodragon Familiar",
        "summonCategory": "familiar",
        "sourceClassId": "warlock",
        "sourceSubclassId": "",
        "sourceFeatureId": "warlock-pact-boon",
        "variantGroup": "warlock-pact-chain-familiar",
        "actorType": "companion",
        "tokenName": "Pseudodragon",
        "size": "tiny",
        "movement": {"walk": 15, "fly": 60},
        "senses": {"blindsight": 10, "darkvision": 60},
        "baseStats": {"scaling": "warlock_familiar_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["warlock", "familiar", "chain"],
    },
    "warlock-chain-quasit": {
        "id": "warlock-chain-quasit",
        "displayName": "Quasit Familiar",
        "summonCategory": "familiar",
        "sourceClassId": "warlock",
        "sourceSubclassId": "",
        "sourceFeatureId": "warlock-pact-boon",
        "variantGroup": "warlock-pact-chain-familiar",
        "actorType": "companion",
        "tokenName": "Quasit",
        "size": "tiny",
        "movement": {"walk": 40},
        "senses": {"darkvision": 120},
        "baseStats": {"scaling": "warlock_familiar_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["warlock", "familiar", "chain"],
    },
    "warlock-chain-sprite": {
        "id": "warlock-chain-sprite",
        "displayName": "Sprite Familiar",
        "summonCategory": "familiar",
        "sourceClassId": "warlock",
        "sourceSubclassId": "",
        "sourceFeatureId": "warlock-pact-boon",
        "variantGroup": "warlock-pact-chain-familiar",
        "actorType": "companion",
        "tokenName": "Sprite",
        "size": "tiny",
        "movement": {"walk": 10, "fly": 40},
        "senses": {"darkvision": 60},
        "baseStats": {"scaling": "warlock_familiar_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["warlock", "familiar", "chain"],
    },
    "ranger-primal-beast-land": {
        "id": "ranger-primal-beast-land",
        "displayName": "Primal Beast of the Land",
        "summonCategory": "companion",
        "sourceClassId": "ranger",
        "sourceSubclassId": "beast-master",
        "sourceFeatureId": "beast-master-rangers-companion",
        "variantGroup": "ranger-primal-beast",
        "actorType": "companion",
        "tokenName": "Primal Beast (Land)",
        "size": "medium",
        "movement": {"walk": 40, "climb": 40},
        "senses": {"darkvision": 60},
        "baseStats": {"scaling": "ranger_primal_beast_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["ranger", "beast-master", "primal-beast", "land"],
    },
    "ranger-primal-beast-sea": {
        "id": "ranger-primal-beast-sea",
        "displayName": "Primal Beast of the Sea",
        "summonCategory": "companion",
        "sourceClassId": "ranger",
        "sourceSubclassId": "beast-master",
        "sourceFeatureId": "beast-master-rangers-companion",
        "variantGroup": "ranger-primal-beast",
        "actorType": "companion",
        "tokenName": "Primal Beast (Sea)",
        "size": "medium",
        "movement": {"walk": 5, "swim": 60},
        "senses": {"darkvision": 60},
        "baseStats": {"scaling": "ranger_primal_beast_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["ranger", "beast-master", "primal-beast", "sea"],
    },
    "ranger-primal-beast-sky": {
        "id": "ranger-primal-beast-sky",
        "displayName": "Primal Beast of the Sky",
        "summonCategory": "companion",
        "sourceClassId": "ranger",
        "sourceSubclassId": "beast-master",
        "sourceFeatureId": "beast-master-rangers-companion",
        "variantGroup": "ranger-primal-beast",
        "actorType": "companion",
        "tokenName": "Primal Beast (Sky)",
        "size": "small",
        "movement": {"walk": 10, "fly": 60},
        "senses": {"darkvision": 60},
        "baseStats": {"scaling": "ranger_primal_beast_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["ranger", "beast-master", "primal-beast", "sky"],
    },
    "tinker-mechanist-companion-frame": {
        "id": "tinker-mechanist-companion-frame",
        "displayName": "Mechanist Companion Frame",
        "summonCategory": "construct",
        "sourceClassId": "tinker",
        "sourceSubclassId": "mechanist",
        "sourceFeatureId": "mechanist-companion-frame",
        "variantGroup": "tinker-mechanist-frame",
        "actorType": "construct",
        "tokenName": "Companion Frame",
        "size": "medium",
        "movement": {"walk": 30},
        "senses": {"darkvision": 60},
        "baseStats": {"scaling": "tinker_mechanist_frame_placeholder"},
        "commandModel": "bonus_action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["tinker", "mechanist", "construct", "companion"],
    },
    "tinker-artillerist-arc-cannon": {
        "id": "tinker-artillerist-arc-cannon",
        "displayName": "Arc Cannon",
        "summonCategory": "deployable",
        "sourceClassId": "tinker",
        "sourceSubclassId": "artillerist",
        "sourceFeatureId": "artillerist-arc-cannon",
        "variantGroup": "tinker-artillerist-cannon",
        "actorType": "deployable",
        "tokenName": "Arc Cannon",
        "size": "small",
        "movement": {"walk": 15},
        "senses": {},
        "baseStats": {"scaling": "tinker_arc_cannon_placeholder"},
        "commandModel": "action_command",
        "maxActive": 1,
        "replaceOnResummon": True,
        "entityKind": "device",
        "isCreature": False,
        "actionSurfaceType": "deployed_field_device",
        "placementRules": {
            "stationary": True,
            "spawnNearOwner": True,
            "ownerPlacementOnly": True,
        },
        "collisionSemantics": {
            "blocksMovement": False,
            "occupiesTile": True,
        },
        "durationModel": {
            "type": "until_dismissed",
            "supportsExpiry": False,
        },
        "ownershipModel": {
            "controller": "owner",
            "ownerActivated": True,
        },
        "interactable": True,
        "destructible": True,
        "triggerRules": {
            "mode": "manual_activation",
            "placeholder": True,
        },
        "cleanupPolicy": {
            "onDismiss": "remove_token",
            "onOwnerRecast": "replace_existing",
            "onReconcileMissingToken": "prune_state",
        },
        "tags": ["tinker", "artillerist", "deployable", "cannon"],
    },
    # --- Owned animal pets (purchased, not class-gated) ----------------------
    # Pets are ordinary owned animals (dog/cat/bird/monkey). They are unlocked by
    # purchase/ownership rather than by a class feature, but they ride the same
    # summon runtime so the owner can summon, move, re-summon, dismiss, and
    # command the resulting token in combat. Each pet is its own variant group so
    # an owner can have several different pets deployed at once.
    "pet-dog": {
        "id": "pet-dog",
        "displayName": "Dog",
        "summonCategory": "companion",
        "sourceClassId": "pet",
        "sourceSubclassId": "",
        "sourceFeatureId": "pet-ownership",
        "variantGroup": "pet-dog",
        "actorType": "companion",
        "tokenName": "Dog",
        "size": "medium",
        "movement": {"walk": 40},
        "senses": {},
        "baseStats": {"scaling": "pet_companion_static"},
        "commandModel": "owner_controlled",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["pet", "animal", "dog"],
    },
    "pet-cat": {
        "id": "pet-cat",
        "displayName": "Cat",
        "summonCategory": "companion",
        "sourceClassId": "pet",
        "sourceSubclassId": "",
        "sourceFeatureId": "pet-ownership",
        "variantGroup": "pet-cat",
        "actorType": "companion",
        "tokenName": "Cat",
        "size": "tiny",
        "movement": {"walk": 40, "climb": 30},
        "senses": {},
        "baseStats": {"scaling": "pet_companion_static"},
        "commandModel": "owner_controlled",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["pet", "animal", "cat"],
    },
    "pet-bird": {
        "id": "pet-bird",
        "displayName": "Bird",
        "summonCategory": "companion",
        "sourceClassId": "pet",
        "sourceSubclassId": "",
        "sourceFeatureId": "pet-ownership",
        "variantGroup": "pet-bird",
        "actorType": "companion",
        "tokenName": "Bird",
        "size": "tiny",
        "movement": {"walk": 10, "fly": 60},
        "senses": {},
        "baseStats": {"scaling": "pet_companion_static"},
        "commandModel": "owner_controlled",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["pet", "animal", "bird"],
    },
    "pet-monkey": {
        "id": "pet-monkey",
        "displayName": "Monkey",
        "summonCategory": "companion",
        "sourceClassId": "pet",
        "sourceSubclassId": "",
        "sourceFeatureId": "pet-ownership",
        "variantGroup": "pet-monkey",
        "actorType": "companion",
        "tokenName": "Monkey",
        "size": "tiny",
        "movement": {"walk": 30, "climb": 30},
        "senses": {},
        "baseStats": {"scaling": "pet_companion_static"},
        "commandModel": "owner_controlled",
        "maxActive": 1,
        "replaceOnResummon": True,
        "tags": ["pet", "animal", "monkey"],
    },
    "spell-conjure-fey-manifestation": _build_template(
        {
            "id": "spell-conjure-fey-manifestation",
            "displayName": "Conjure Fey Manifestation",
            "summonCategory": "spell_effect",
            "variantGroup": "spell-conjure-fey",
            "actorType": "spell_effect",
            "tokenName": "Conjured Fey",
            "size": "large",
            "movement": {"walk": 30},
            "senses": {},
            "baseStats": {"scaling": "spell_effect_placeholder"},
            "commandModel": "spell_effect",
            "maxActive": 1,
            "replaceOnResummon": True,
            "tags": ["spell", "summon", "temporary", "concentration", "conjuration"],
        },
        source=_source_link(class_id="spell", feature_id="spell:conjure-fey", origin="spell", spell_id="conjure-fey"),
        lifecycle=_lifecycle(
            temporary=True,
            concentration_required=True,
            duration_seconds=3600,
            cleanup_policy=["dismiss", "duration_expiry", "long_rest", "short_rest", "stale_token"],
        ),
        control=_control(model="caster_owned_independent_effect"),
    ),
    "spell-conjure-celestial-manifestation": _build_template(
        {
            "id": "spell-conjure-celestial-manifestation",
            "displayName": "Conjure Celestial Manifestation",
            "summonCategory": "spell_effect",
            "variantGroup": "spell-conjure-celestial",
            "actorType": "spell_effect",
            "tokenName": "Conjured Celestial",
            "size": "large",
            "movement": {"walk": 30, "fly": 60},
            "senses": {"darkvision": 60},
            "baseStats": {"scaling": "spell_effect_placeholder"},
            "commandModel": "spell_effect",
            "maxActive": 1,
            "replaceOnResummon": True,
            "tags": ["spell", "summon", "temporary", "concentration", "conjuration"],
        },
        source=_source_link(class_id="spell", feature_id="spell:conjure-celestial", origin="spell", spell_id="conjure-celestial"),
        lifecycle=_lifecycle(
            temporary=True,
            concentration_required=True,
            duration_seconds=3600,
            cleanup_policy=["dismiss", "duration_expiry", "long_rest", "short_rest", "stale_token"],
        ),
        control=_control(model="caster_owned_independent_effect"),
    ),
}


def _with_entity_defaults(row: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(row)
    summon_category = str(normalized.get("summonCategory") or "").strip().lower()
    default_is_creature = summon_category not in {"deployable", "device", "trap", "ward", "effect", "object"}
    normalized["isCreature"] = bool(normalized.get("isCreature", default_is_creature))
    normalized["entityKind"] = str(
        normalized.get("entityKind")
        or ("creature" if normalized["isCreature"] else "effect")
    ).strip().lower()
    normalized["actionSurfaceType"] = str(
        normalized.get("actionSurfaceType")
        or ("summoned_creature" if normalized["isCreature"] else "deployed_field_effect")
    ).strip().lower()
    if not isinstance(normalized.get("placementRules"), dict):
        normalized["placementRules"] = {
            "stationary": False,
            "spawnNearOwner": True,
            "ownerPlacementOnly": True,
        }
    if not isinstance(normalized.get("durationModel"), dict):
        normalized["durationModel"] = {"type": "until_dismissed", "supportsExpiry": False}
    if not isinstance(normalized.get("ownershipModel"), dict):
        normalized["ownershipModel"] = {"controller": "owner", "ownerActivated": True}
    if not isinstance(normalized.get("cleanupPolicy"), dict):
        normalized["cleanupPolicy"] = {
            "onDismiss": "remove_token",
            "onOwnerRecast": "replace_existing",
            "onReconcileMissingToken": "prune_state",
        }
    normalized["interactable"] = bool(normalized.get("interactable", True))
    normalized["destructible"] = bool(normalized.get("destructible", True))
    if not isinstance(normalized.get("triggerRules"), dict):
        normalized["triggerRules"] = {"mode": "none", "placeholder": False}
    if not isinstance(normalized.get("collisionSemantics"), dict):
        normalized["collisionSemantics"] = {"blocksMovement": False, "occupiesTile": True}
    return normalized


def get_summon_template(template_id: Any) -> dict[str, Any] | None:
    key = str(template_id or "").strip().lower()
    if not key:
        return None
    row = SUMMON_TEMPLATE_REGISTRY.get(key)
    return _with_entity_defaults(row) if isinstance(row, dict) else None


def list_summon_templates() -> list[dict[str, Any]]:
    return [_with_entity_defaults(row) for row in SUMMON_TEMPLATE_REGISTRY.values() if isinstance(row, dict)]


def list_summon_templates_for_group(group_id: Any) -> list[dict[str, Any]]:
    key = str(group_id or "").strip().lower()
    if not key:
        return []
    return [
        row
        for row in list_summon_templates()
        if str(row.get("variantGroup") or "").strip().lower() == key
    ]


def list_summon_templates_for_source(*, class_id: Any = "", feature_id: Any = "", subclass_id: Any = "") -> list[dict[str, Any]]:
    class_key = str(class_id or "").strip().lower()
    feature_key = str(feature_id or "").strip().lower()
    subclass_key = str(subclass_id or "").strip().lower()
    out: list[dict[str, Any]] = []
    for row in list_summon_templates():
        if class_key and str(row.get("sourceClassId") or "").strip().lower() != class_key:
            continue
        if feature_key and str(row.get("sourceFeatureId") or "").strip().lower() != feature_key:
            continue
        if subclass_key and str(row.get("sourceSubclassId") or "").strip().lower() != subclass_key:
            continue
        out.append(row)
    return out


def validate_summon_template_registry(registry: dict[str, dict[str, Any]] | None = None) -> list[str]:
    src = registry if isinstance(registry, dict) else SUMMON_TEMPLATE_REGISTRY
    errors: list[str] = []
    groups: dict[str, list[str]] = {}
    required = (
        "id",
        "displayName",
        "summonCategory",
        "sourceClassId",
        "sourceFeatureId",
        "variantGroup",
        "actorType",
        "tokenName",
        "commandModel",
        "maxActive",
        "replaceOnResummon",
    )

    for key, raw in src.items():
        if not isinstance(raw, dict):
            errors.append(f"[{key}] template row must be a dictionary")
            continue
        template = _with_entity_defaults(raw)
        template_id = str(template.get("id") or "").strip().lower()
        if template_id != str(key or "").strip().lower():
            errors.append(f"[{key}] id must match registry key (got {template_id or '<empty>'})")
        for field in required:
            value = template.get(field)
            if isinstance(value, str) and not value.strip():
                errors.append(f"[{template_id or key}] missing required field '{field}'")
            elif value is None:
                errors.append(f"[{template_id or key}] missing required field '{field}'")

        group = str(template.get("variantGroup") or "").strip().lower()
        if group:
            groups.setdefault(group, []).append(template_id or str(key))

        entity_kind = str(template.get("entityKind") or "").strip().lower()
        is_creature = bool(template.get("isCreature", True))
        if entity_kind not in _ALLOWED_ENTITY_KINDS:
            errors.append(f"[{template_id or key}] invalid entityKind '{entity_kind}'")
        if is_creature and entity_kind in _NON_CREATURE_ENTITY_KINDS:
            errors.append(f"[{template_id or key}] isCreature=true conflicts with entityKind '{entity_kind}'")
        if (not is_creature) and entity_kind == "creature":
            errors.append(f"[{template_id or key}] isCreature=false conflicts with entityKind 'creature'")

        max_active = template.get("maxActive")
        try:
            max_active_int = int(max_active)
        except Exception:
            errors.append(f"[{template_id or key}] maxActive must be an integer")
            max_active_int = 0
        replace = bool(template.get("replaceOnResummon"))
        if max_active_int < 0:
            errors.append(f"[{template_id or key}] maxActive must be >= 0")
        if max_active_int == 0 and replace:
            errors.append(f"[{template_id or key}] replaceOnResummon cannot be true when maxActive is 0")

        command_model = str(template.get("commandModel") or "").strip().lower()
        if command_model and command_model not in _ALLOWED_COMMAND_MODELS:
            errors.append(f"[{template_id or key}] unsupported commandModel '{command_model}'")

        action_surface = str(template.get("actionSurfaceType") or "").strip().lower()
        if not action_surface:
            errors.append(f"[{template_id or key}] actionSurfaceType must resolve to a non-empty value")

        origin = str(template.get("summonOrigin") or "feature").strip().lower()
        spell_id = str(template.get("spellId") or "").strip().lower()
        if origin == "spell":
            if str(template.get("sourceClassId") or "").strip().lower() != "spell":
                errors.append(f"[{template_id or key}] spell origin requires sourceClassId='spell'")
            if not spell_id:
                errors.append(f"[{template_id or key}] spell origin requires spellId")
            if not str(template.get("sourceFeatureId") or "").strip().lower().startswith("spell:"):
                errors.append(f"[{template_id or key}] spell origin requires sourceFeatureId like 'spell:<id>'")

        temporary = bool(template.get("temporary"))
        cleanup = template.get("cleanupPolicy")
        if temporary:
            try:
                duration = int(template.get("durationSeconds") or 0)
            except Exception:
                duration = 0
            if duration <= 0:
                errors.append(f"[{template_id or key}] temporary summons require positive durationSeconds")
            if not isinstance(cleanup, (list, dict)) or len(cleanup) == 0:
                errors.append(f"[{template_id or key}] temporary summons require non-empty cleanupPolicy")

        ownership = template.get("ownershipModel")
        if isinstance(ownership, dict):
            controller = str(ownership.get("controller") or "").strip().lower()
            if not controller:
                errors.append(f"[{template_id or key}] ownershipModel.controller is required when ownershipModel is defined")

        if not isinstance(template.get("baseStats"), dict):
            errors.append(f"[{template_id or key}] baseStats must be a dictionary")

    for group, template_ids in groups.items():
        if len(template_ids) == 0:
            errors.append(f"[{group}] variantGroup has no template ids")
    return errors


def validate_summon_template_registry_or_raise(registry: dict[str, dict[str, Any]] | None = None) -> None:
    errors = validate_summon_template_registry(registry)
    if errors:
        raise ValueError("Summon template registry validation failed:\n- " + "\n- ".join(errors))


validate_summon_template_registry_or_raise()
