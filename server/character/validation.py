"""Validation and migration-safe normalization for canonical character docs."""
from __future__ import annotations

import copy
from typing import Any

from server.character.schema import (
    CHARACTER_SCHEMA_NAME,
    CHARACTER_SCHEMA_VERSION,
    default_character_document,
    normalize_character_document,
)

_REQUIRED_TOP_LEVEL_FIELDS = {
    "schemaVersion",
    "rulesMode",
    "ruleset",
    "contentPackVersion",
    "sourceMode",
    "identity",
    "species",
    "background",
    "abilities",
    "classes",
    "feats",
    "talents",
    "awakening",
    "equipment",
    "spellState",
    "importMeta",
    "audit",
}


class CharacterValidationError(ValueError):
    """Raised when a character document cannot be normalized safely."""


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


def validate_required_shape(document: Any) -> list[str]:
    """Return shape errors for a canonical character document candidate."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["character document must be a dictionary"]

    missing = sorted(_REQUIRED_TOP_LEVEL_FIELDS.difference(document.keys()))
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")

    if str(document.get("schema") or CHARACTER_SCHEMA_NAME) != CHARACTER_SCHEMA_NAME:
        errors.append("invalid schema name")

    version = _safe_int(document.get("schemaVersion"), 0)
    if version <= 0:
        errors.append("schemaVersion must be a positive integer")

    for nested_key in (
        "identity",
        "species",
        "background",
        "abilities",
        "awakening",
        "equipment",
        "spellState",
        "importMeta",
        "audit",
    ):
        if not isinstance(document.get(nested_key), dict):
            errors.append(f"{nested_key} must be a dictionary")

    for list_key in ("classes", "feats", "talents"):
        if not isinstance(document.get(list_key), list):
            errors.append(f"{list_key} must be a list")

    return errors


def ensure_character_defaults(document: Any) -> dict:
    """Normalize and fill defaults without removing unknown/extensible fields."""
    normalized = normalize_character_document(document)
    base = default_character_document()

    for key, value in base.items():
        if key not in normalized:
            normalized[key] = _clone(value)

    normalized.setdefault("schema", CHARACTER_SCHEMA_NAME)
    normalized["schemaVersion"] = _safe_int(
        normalized.get("schemaVersion"),
        CHARACTER_SCHEMA_VERSION,
        minimum=1,
    )

    audit = normalized.get("audit") if isinstance(normalized.get("audit"), dict) else {}
    if not isinstance(audit, dict):
        audit = {}
    audit.setdefault("resolverVersion", 1)
    audit.setdefault("migrationHistory", [])
    audit.setdefault("dirty", False)
    normalized["audit"] = audit

    return normalized


def validate_or_raise(document: Any) -> dict:
    """Validate and return a normalized document, raising if still invalid."""
    normalized = ensure_character_defaults(document)
    errors = validate_required_shape(normalized)
    if errors:
        raise CharacterValidationError("; ".join(errors))
    return normalized
