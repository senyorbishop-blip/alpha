"""Canonical native character package."""

from server.character.export_mapper import map_character_to_charbook, map_character_to_charsheet
from server.character.resolver import resolve_character_runtime
from server.character.schema import (
    CHARACTER_SCHEMA_NAME,
    CHARACTER_SCHEMA_VERSION,
    default_character_document,
    default_runtime,
)
from server.character.service import (
    build_profile_library_entry,
    get_builder_rules_catalog,
    create_character_document,
    normalize_character_document,
    preview_levelup,
    resolve_runtime,
    to_legacy_character_payload,
    validate_character_document,
)
from server.character.validation import (
    CharacterValidationError,
    ensure_character_defaults,
    validate_or_raise,
    validate_required_shape,
)

__all__ = [
    "CHARACTER_SCHEMA_NAME",
    "CHARACTER_SCHEMA_VERSION",
    "CharacterValidationError",
    "build_profile_library_entry",
    "create_character_document",
    "default_character_document",
    "get_builder_rules_catalog",
    "map_character_to_charbook",
    "map_character_to_charsheet",
    "default_runtime",
    "ensure_character_defaults",
    "normalize_character_document",
    "preview_levelup",
    "resolve_character_runtime",
    "resolve_runtime",
    "to_legacy_character_payload",
    "validate_character_document",
    "validate_or_raise",
    "validate_required_shape",
]
