"""Canonical native character schema for Casual D&D progression."""
from __future__ import annotations

import copy
import time
from typing import Any

from server.character.summon_state import default_summon_state

CHARACTER_SCHEMA_NAME = "casual-dnd.character"
CHARACTER_SCHEMA_VERSION = 1

DEFAULT_RULES_MODE = "casual"
DEFAULT_RULESET = "casual-dnd-5e-compatible"
DEFAULT_SOURCE_MODE = "native"


_RULES_MODES = {"casual", "classic", "custom"}
_SOURCE_MODES = {"native", "dndbeyond", "existing"}


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _safe_str(value: Any, fallback: str = "", *, limit: int = 120) -> str:
    text = str(value or fallback).strip()[:limit]
    return text or fallback


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        num = int(value)
    except Exception:
        num = fallback
    if minimum is not None:
        num = max(minimum, num)
    return num


def _deep_merge_dicts(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge canonical defaults with incoming dict while preserving nested defaults."""
    merged = _clone(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = _clone(value)
    return merged


def default_character_document() -> dict:
    """Create a migration-safe canonical character document."""
    now = time.time()
    return {
        "schema": CHARACTER_SCHEMA_NAME,
        "schemaVersion": CHARACTER_SCHEMA_VERSION,
        "rulesMode": DEFAULT_RULES_MODE,
        "ruleset": DEFAULT_RULESET,
        "contentPackVersion": "",
        "sourceMode": DEFAULT_SOURCE_MODE,
        "identity": {
            "characterId": "",
            "playerId": "",
            "name": "",
            "displayName": "",
            "pronouns": "",
            "portraitUrl": "",
            "tokenImageUrl": "",
            "alignment": "",
            "deity": "",
            "age": "",
            "height": "",
            "weight": "",
            "eyes": "",
            "hair": "",
            "skin": "",
            "homeland": "",
            "backstory": "",
            "personalityTraits": "",
            "ideals": "",
            "bonds": "",
            "flaws": "",
            "notes": "",
        },
        "presentation": {
            "portraitFrame": "classic",
            "tokenDisplay": {
                "scale": 1,
                "cropMode": "cover",
                "ringStyle": "classic",
                "accentColor": "#00e5cc",
                "labelFormat": "class_name",
            },
        },
        "species": {
            "id": "",
            "name": "",
            "size": "medium",
            "speed": 30,
            "traits": [],
            "senses": [],
            "resistances": [],
            "gameplayBenefits": [],
            "summary": "",
            "choices": {},
        },
        "background": {
            "id": "",
            "name": "",
            "traits": [],
            "proficiencies": [],
            "tools": [],
            "languages": [],
            "equipmentPicks": [],
            "featureSummary": "",
        },
        "abilities": {
            "generationMode": "manual",
            "scores": {
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
                "cha": 10,
            },
            "bonuses": {},
            "finalScores": {},
            "sources": {},
            "saves": {},
            "skills": {},
        },
        "classes": [],
        "feats": [],
        "talents": [],
        "awakening": {
            "stage": 0,
            "pathId": "",
            "nodes": [],
            "flags": {},
        },
        "equipment": {
            "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
            "inventory": [],
            "equipped": {},
            "containers": [],
        },
        "spellState": {
            "known": [],
            "prepared": [],
            "slots": {},
            "focus": {},
            "rituals": [],
            "spellbookEntries": [],
            "classSources": [],
        },
        "summons": default_summon_state(),
        "importMeta": {
            "origin": "",
            "externalId": "",
            "importedAt": None,
            "rawVersion": "",
            "rawSnapshot": {},
            "mappingNotes": [],
        },
        "audit": {
            "createdAt": now,
            "updatedAt": now,
            "lastResolvedAt": None,
            "resolverVersion": 1,
            "migrationHistory": [],
            "dirty": False,
        },
    }


def default_runtime() -> dict:
    """Create a baseline runtime object for gameplay compatibility mapping."""
    return {
        "levelTotal": 1,
        "proficiencyBonus": 2,
        "hp": {
            "max": 1,
            "current": 1,
            "temp": 0,
            "hitDice": [],
        },
        "ac": 10,
        "speed": {
            "walk": 30,
        },
        "senses": {
            "passivePerception": 10,
            "darkvision": 0,
            "blindsight": 0,
            "tremorsense": 0,
            "truesight": 0,
        },
        "resources": [],
        "classes": [],
        "classDisplay": {
            "classId": "",
            "className": "",
            "subclassId": "",
            "subclassName": "",
            "subclassUnlockLevel": 0,
            "subclassUnlocked": False,
            "subclassFeatureUnlocksByLevel": {},
        },
        "actions": [],
        "bonusActions": [],
        "reactions": [],
        "passives": [],
        "talents": [],
        "talentGrants": [],
        "pendingTalentGrants": [],
        "awakening": {
            "unlocked": False,
            "pathId": "",
            "pathName": "",
            "stage": 0,
            "minimumLevel": 15,
            "classRestriction": [],
            "grants": [],
        },
        "awakeningGrants": [],
        "spellAccess": {
            "ability": "",
            "attackBonus": 0,
            "saveDc": 8,
            "slots": {},
            "known": [],
            "prepared": [],
            "availableBySubclass": [],
        },
        "derivedTags": [],
    }


def normalize_character_document(raw: Any) -> dict:
    """Normalize an unknown payload into the canonical document shape."""
    base = default_character_document()
    src = raw if isinstance(raw, dict) else {}

    base["schema"] = CHARACTER_SCHEMA_NAME
    base["schemaVersion"] = _safe_int(src.get("schemaVersion"), CHARACTER_SCHEMA_VERSION, minimum=1)

    rules_mode = _safe_str(src.get("rulesMode"), DEFAULT_RULES_MODE, limit=40).lower()
    base["rulesMode"] = rules_mode if rules_mode in _RULES_MODES else DEFAULT_RULES_MODE
    base["ruleset"] = _safe_str(src.get("ruleset"), DEFAULT_RULESET, limit=80)
    base["contentPackVersion"] = _safe_str(src.get("contentPackVersion"), "", limit=80)

    source_mode = _safe_str(src.get("sourceMode"), DEFAULT_SOURCE_MODE, limit=40).lower()
    base["sourceMode"] = source_mode if source_mode in _SOURCE_MODES else DEFAULT_SOURCE_MODE

    for key in (
        "identity",
        "presentation",
        "species",
        "background",
        "abilities",
        "awakening",
        "equipment",
        "spellState",
        "summons",
        "importMeta",
        "audit",
    ):
        value = src.get(key)
        if isinstance(value, dict):
            base[key] = _deep_merge_dicts(base[key], value)

    for key in ("classes", "feats", "talents"):
        value = src.get(key)
        if isinstance(value, list):
            base[key] = list(value)

    return base
