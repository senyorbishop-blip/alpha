"""Data-driven native rules catalog loader for character builder slices.

This module intentionally starts small and strict:
- loads JSON files from server/data/rules/5e2024/{species,classes,subclasses,talents,awakenings}
- returns stable IDs and index maps for runtime consumers
- avoids rewriting existing runtime resolution until builder integration expands
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from server.character.feature_catalog import build_class_feature_definitions, build_features_by_level

_RULESET_ID = "5e2024"
_RULES_ROOT = Path(__file__).resolve().parents[1] / "data" / "rules" / _RULESET_ID
_OPTIONAL_SPECIES_KEYS = (
    "size",
    "languages",
    "abilityBonuses",
    "proficiencies",
    "flavorText",
    "roleplayNotes",
    "recommendedClasses",
)
logger = logging.getLogger(__name__)


def _ordinal(level: int) -> str:
    lookup = {
        1: "1st",
        2: "2nd",
        3: "3rd",
        4: "4th",
        5: "5th",
        6: "6th",
        7: "7th",
        8: "8th",
        9: "9th",
    }
    return lookup.get(level, f"{level}th")


class RulesCatalogError(RuntimeError):
    """Raised when catalog data cannot be loaded safely."""


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RulesCatalogError(f"Missing rules catalog file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RulesCatalogError(f"Invalid JSON in rules catalog file: {path}") from exc
    if not isinstance(payload, dict):
        raise RulesCatalogError(f"Rules catalog file must contain a JSON object: {path}")
    return payload


def _load_collection(folder: str, required_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    root = _RULES_ROOT / folder
    if not root.exists() or not root.is_dir():
        raise RulesCatalogError(f"Missing rules catalog folder: {root}")

    rows: list[dict[str, Any]] = []
    for file_path in sorted(root.glob("*.json")):
        row = _load_json_file(file_path)
        missing = [key for key in required_keys if key not in row or row.get(key) is None]
        if missing:
            raise RulesCatalogError(
                f"Catalog file {file_path.name} missing required keys: {', '.join(missing)}"
            )
        rows.append(row)

    if not rows:
        raise RulesCatalogError(f"No catalog rows found in folder: {root}")
    return rows


def _index_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row.get("id") or "").strip().lower()
        if not item_id:
            continue
        if item_id in indexed:
            raise RulesCatalogError(f"Duplicate catalog id found: {item_id}")
        indexed[item_id] = row
    return indexed


@lru_cache(maxsize=1)
def load_rules_catalog() -> dict[str, Any]:
    """Load the native 5e2024 starter rules catalog from JSON files.

    The returned payload is safe for read-only runtime use and intentionally includes
    both list and map forms for future builder/search APIs.
    """
    species = _load_collection("species", ("id", "displayName", "movement", "senses", "traits"))
    for row in species:
        species_id = str(row.get("id") or "").strip() or "<unknown>"
        missing_optional = [key for key in _OPTIONAL_SPECIES_KEYS if row.get(key) is None]
        if missing_optional:
            logger.warning(
                "Species row '%s' is missing optional keys: %s",
                species_id,
                ", ".join(missing_optional),
            )
    classes = _load_collection(
        "classes",
        (
            "id",
            "displayName",
            "hitDie",
            "primaryAbilities",
            "savingThrows",
            "subclassLevel",
            "progressionTable",
            "progressionSummary",
            "levelUnlockIds",
        ),
    )
    for row in classes:
        generated_feature_defs = build_class_feature_definitions(row)
        row["featureDefinitions"] = generated_feature_defs
        row["featuresByLevel"] = build_features_by_level(row)
    subclasses = _load_collection("subclasses", ("id", "classId", "displayName", "featureUnlocksByLevel"))
    talents = _load_collection(
        "talents",
        ("id", "displayName", "classRestrictions", "minimumLevel", "grants", "tags", "source"),
    )
    awakenings = _load_collection(
        "awakenings",
        ("id", "displayName", "classRestrictions", "minimumLevel", "grants", "source"),
    )
    feats_origin = _load_json_file(_RULES_ROOT / "feats" / "origin-feats.json")
    feats_general = _load_json_file(_RULES_ROOT / "feats" / "general-feats.json")
    backgrounds = _load_json_file(_RULES_ROOT / "backgrounds" / "backgrounds.json")

    spells: list[dict[str, Any]] = []
    for level in range(10):
        fname = "spells-cantrip.json" if level == 0 else f"spells-{_ordinal(level)}.json"
        fpath = _RULES_ROOT / "spells" / fname
        if not fpath.exists():
            continue
        data = _load_json_file(fpath)
        loaded = data.get("spells", []) if isinstance(data.get("spells"), list) else [data]
        for row in loaded:
            if isinstance(row, dict):
                spells.append(row)

    classes_by_id = _index_by_id(classes)
    subclasses_by_id = _index_by_id(subclasses)
    talents_by_id = _index_by_id(talents)
    awakenings_by_id = _index_by_id(awakenings)

    subclasses_by_class: dict[str, list[dict[str, Any]]] = {}
    for subclass in subclasses:
        class_id = str(subclass.get("classId") or "").strip().lower()
        if class_id not in classes_by_id:
            raise RulesCatalogError(
                f"Subclass '{subclass.get('id')}' references unknown classId '{class_id}'"
            )
        subclasses_by_class.setdefault(class_id, []).append(subclass)

    talents_by_class: dict[str, list[dict[str, Any]]] = {}
    for talent in talents:
        restrictions = talent.get("classRestrictions")
        if not isinstance(restrictions, list):
            restrictions = []
        for class_id_raw in restrictions:
            class_id = str(class_id_raw or "").strip().lower()
            if not class_id or class_id not in classes_by_id:
                continue
            talents_by_class.setdefault(class_id, []).append(talent)

    awakenings_by_class: dict[str, list[dict[str, Any]]] = {}
    for awakening in awakenings:
        restrictions = awakening.get("classRestrictions")
        if not isinstance(restrictions, list):
            restrictions = []
        for class_id_raw in restrictions:
            class_id = str(class_id_raw or "").strip().lower()
            if not class_id or class_id not in classes_by_id:
                continue
            awakenings_by_class.setdefault(class_id, []).append(awakening)

    return {
        "rulesetId": _RULESET_ID,
        "loadedFrom": str(_RULES_ROOT),
        "species": species,
        "classes": classes,
        "subclasses": subclasses,
        "talents": talents,
        "awakenings": awakenings,
        "featsOrigin": feats_origin.get("feats", []),
        "featsGeneral": feats_general.get("feats", []),
        "backgrounds": backgrounds.get("backgrounds", []),
        "spells": spells,
        "speciesById": _index_by_id(species),
        "classesById": classes_by_id,
        "subclassesById": subclasses_by_id,
        "talentsById": talents_by_id,
        "awakeningsById": awakenings_by_id,
        "subclassesByClass": subclasses_by_class,
        "talentsByClass": talents_by_class,
        "awakeningsByClass": awakenings_by_class,
    }


def get_class_catalog_row(class_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(class_id or "").strip().lower()
    if not key:
        return None
    return catalog.get("classesById", {}).get(key)


def get_species_catalog_row(species_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(species_id or "").strip().lower()
    if not key:
        return None
    return catalog.get("speciesById", {}).get(key)


def get_subclass_catalog_row(subclass_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(subclass_id or "").strip().lower()
    if not key:
        return None
    return catalog.get("subclassesById", {}).get(key)


def get_talent_catalog_row(talent_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(talent_id or "").strip().lower()
    if not key:
        return None
    return catalog.get("talentsById", {}).get(key)


def get_awakening_catalog_row(path_id: Any) -> dict[str, Any] | None:
    catalog = load_rules_catalog()
    key = str(path_id or "").strip().lower()
    if not key:
        return None
    return catalog.get("awakeningsById", {}).get(key)
