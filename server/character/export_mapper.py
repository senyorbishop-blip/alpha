"""Compatibility export mapping from canonical native characters to legacy shapes.

These helpers intentionally keep mapping conservative so existing runtime consumers keep
working while native character progression becomes the long-term authority.
"""
from __future__ import annotations

import copy
from typing import Any


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _safe_int(value: Any, fallback: int, *, minimum: int | None = None) -> int:
    try:
        number = int(value)
    except Exception:
        number = fallback
    if minimum is not None:
        number = max(minimum, number)
    return number


def _safe_str(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _ability_scores_map(document: dict[str, Any]) -> dict[str, int]:
    abilities = document.get("abilities") if isinstance(document.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    return {
        "str": _safe_int(scores.get("str"), 10),
        "dex": _safe_int(scores.get("dex"), 10),
        "con": _safe_int(scores.get("con"), 10),
        "int": _safe_int(scores.get("int"), 10),
        "wis": _safe_int(scores.get("wis"), 10),
        "cha": _safe_int(scores.get("cha"), 10),
    }


def _primary_class(document: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_classes = document.get("classes") if isinstance(document.get("classes"), list) else []
    classes = [row for row in raw_classes if isinstance(row, dict)]
    first = classes[0] if classes else {}
    return classes, first


def _resolve_identity_name(identity: dict[str, Any]) -> str:
    return _safe_str(identity.get("name")) or _safe_str(identity.get("displayName"))


def map_character_to_charsheet(document: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    """Map canonical document+runtime into the current charSheet compatibility shape.

    The mapping intentionally only exports stable baseline fields currently used by legacy
    consumers and gameplay paths.
    """
    identity = document.get("identity") if isinstance(document.get("identity"), dict) else {}
    species = document.get("species") if isinstance(document.get("species"), dict) else {}
    background = document.get("background") if isinstance(document.get("background"), dict) else {}
    presentation = document.get("presentation") if isinstance(document.get("presentation"), dict) else {}
    classes, _ = _primary_class(document)
    hp = runtime.get("hp") if isinstance(runtime.get("hp"), dict) else {}

    level_total = _safe_int(runtime.get("levelTotal"), 1, minimum=1)
    proficiency_bonus = _safe_int(runtime.get("proficiencyBonus"), 2)
    ac_value = _safe_int(runtime.get("ac"), 10)
    speed_map = runtime.get("speed") if isinstance(runtime.get("speed"), dict) else {"walk": 30}

    return {
        "name": _resolve_identity_name(identity),
        "species": _safe_str(species.get("name")),
        "background": _safe_str(background.get("name")),
        "classes": classes,
        "avatarUrl": _safe_str(identity.get("portraitUrl")),
        "tokenImageUrl": _safe_str(identity.get("tokenImageUrl")) or _safe_str(identity.get("portraitUrl")),
        "portraitFrame": _safe_str(presentation.get("portraitFrame"), "classic"),
        "tokenDisplay": _clone(presentation.get("tokenDisplay") or {}),
        "level": level_total,
        "totalLevel": level_total,
        "proficiencyBonus": proficiency_bonus,
        "ac": ac_value,
        "hp": {
            "max": _safe_int(hp.get("max"), 1, minimum=1),
            "current": _safe_int(hp.get("current"), 1, minimum=0),
            "temp": _safe_int(hp.get("temp"), 0),
        },
        "speed": _clone(speed_map),
        "senses": _clone(runtime.get("senses") or {}),
        "spellAccess": _clone(runtime.get("spellAccess") or {}),
        # TODO(character-native): add derived modifiers/saves/skills once canonical runtime computes them.
        # TODO(character-native): map conditions, resources, and action economy when runtime owns these fields.
    }


def map_character_to_charbook(document: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    """Map canonical document+runtime into the current charBook compatibility shape.

    This keeps charBook-style cards/list views functional while native character docs remain
    the authoritative progression source.
    """
    identity = document.get("identity") if isinstance(document.get("identity"), dict) else {}
    species = document.get("species") if isinstance(document.get("species"), dict) else {}
    background = document.get("background") if isinstance(document.get("background"), dict) else {}
    presentation = document.get("presentation") if isinstance(document.get("presentation"), dict) else {}
    equipment = document.get("equipment") if isinstance(document.get("equipment"), dict) else {}
    ability_scores = _ability_scores_map(document)
    _, primary_class = _primary_class(document)
    hp = runtime.get("hp") if isinstance(runtime.get("hp"), dict) else {}
    speed_map = runtime.get("speed") if isinstance(runtime.get("speed"), dict) else {}
    spell_access = runtime.get("spellAccess") if isinstance(runtime.get("spellAccess"), dict) else {}
    spell_state = document.get("spellState") if isinstance(document.get("spellState"), dict) else {}

    class_name = _safe_str(primary_class.get("name"))
    subclass_name = _safe_str(primary_class.get("subclass"))

    currency_raw = equipment.get("currency") if isinstance(equipment.get("currency"), dict) else {}
    currency = {
        "cp": _safe_int(currency_raw.get("cp"), 0),
        "sp": _safe_int(currency_raw.get("sp"), 0),
        "ep": _safe_int(currency_raw.get("ep"), 0),
        "gp": _safe_int(currency_raw.get("gp"), 0),
        "pp": _safe_int(currency_raw.get("pp"), 0),
    }

    # Prefer runtime-resolved known/prepared lists; fall back to document spellState when absent.
    spell_known = list(spell_access.get("known") or spell_state.get("known") or [])
    spell_prepared = list(spell_access.get("prepared") or spell_state.get("prepared") or [])

    return {
        "name": _resolve_identity_name(identity),
        "species": _safe_str(species.get("name")),
        "background": _safe_str(background.get("name")),
        "className": class_name,
        "subclass": subclass_name,
        "level": _safe_int(runtime.get("levelTotal"), 1, minimum=1),
        "proficiencyBonus": _safe_int(runtime.get("proficiencyBonus"), 2),
        "avatarUrl": _safe_str(identity.get("portraitUrl")),
        "tokenImageUrl": _safe_str(identity.get("tokenImageUrl")) or _safe_str(identity.get("portraitUrl")),
        "portraitFrame": _safe_str(presentation.get("portraitFrame"), "classic"),
        "tokenDisplay": _clone(presentation.get("tokenDisplay") or {}),
        "abilities": {
            key: {"score": value}
            for key, value in ability_scores.items()
        },
        "ac": _safe_int(runtime.get("ac"), 10),
        "speed": _safe_int(speed_map.get("walk"), 30, minimum=0),
        "maxHp": _safe_int(hp.get("max"), 1, minimum=1),
        "currentHp": _safe_int(hp.get("current"), 1, minimum=0),
        "tempHp": _safe_int(hp.get("temp"), 0),
        "feats": list(document.get("feats") or []),
        "currency": currency,
        # Conservative placeholder fields so existing UI paths can render without deep spell/resource rewiring.
        "resources": list(runtime.get("resources") or []),
        "spells": {
            "slots": _clone(spell_access.get("slots") or {}),
            "known": spell_known,
            "prepared": spell_prepared,
        },
        # TODO(character-native): support richer class display labels for multiclass and archetype formatting.
        # TODO(character-native): export awakening and level-up progression summaries for charBook panels.
    }
