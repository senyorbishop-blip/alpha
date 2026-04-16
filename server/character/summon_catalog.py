"""Summon template registry for character progression metadata (Pass A)."""
from __future__ import annotations

import copy
from typing import Any


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
    "spell-conjure-fey-manifestation": {
        "id": "spell-conjure-fey-manifestation",
        "displayName": "Conjure Fey Manifestation",
        "summonCategory": "spell_effect",
        "sourceClassId": "spell",
        "sourceSubclassId": "",
        "sourceFeatureId": "spell:conjure-fey",
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
        "summonOrigin": "spell",
        "spellId": "conjure-fey",
        "temporary": True,
        "concentrationRequired": True,
        "durationSeconds": 3600,
        "cleanupPolicy": ["dismiss", "duration_expiry", "long_rest", "short_rest", "stale_token"],
        "controlModel": "caster_owned_independent_effect",
        "tags": ["spell", "summon", "temporary", "concentration", "conjuration"],
    },
    "spell-conjure-celestial-manifestation": {
        "id": "spell-conjure-celestial-manifestation",
        "displayName": "Conjure Celestial Manifestation",
        "summonCategory": "spell_effect",
        "sourceClassId": "spell",
        "sourceSubclassId": "",
        "sourceFeatureId": "spell:conjure-celestial",
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
        "summonOrigin": "spell",
        "spellId": "conjure-celestial",
        "temporary": True,
        "concentrationRequired": True,
        "durationSeconds": 3600,
        "cleanupPolicy": ["dismiss", "duration_expiry", "long_rest", "short_rest", "stale_token"],
        "controlModel": "caster_owned_independent_effect",
        "tags": ["spell", "summon", "temporary", "concentration", "conjuration"],
    },
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
