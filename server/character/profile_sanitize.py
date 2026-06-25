"""Character profile runtime/transient field stripping.

A character profile is the PERSISTENT save document for a player character. The
live tabletop client rebuilds all combat/UI runtime state from canonical data on
load, so any runtime cache that leaks into a saved profile is pure bloat. Letting
that bloat accumulate is what historically pushed the persisted ``char_profiles``
campaign field past 4.5 MB (see the DB ``large_field`` warning) and slowed every
save and reconnect sync.

This module is the server-side guard mirroring the client's
``_stripCharProfileRuntimeFields`` so profiles are cleaned both before they are
persisted (defence in depth) and via an explicit migration for already-oversized
profiles. The migration only removes known runtime caches — it never deletes real
character data (name, ability scores, inventory, spell selections, etc.). Large
inline ``data:image`` strings are relocated into ``/static/user_uploads`` beside
this runtime stripping so PDF-imported portraits do not bloat every state sync.
"""
from __future__ import annotations

import re
from typing import Any

from server.character.profile_assets import sanitize_profile_persistence

# Exact key names that only ever hold rebuildable runtime state. Keep this list
# in sync with CHAR_PROFILE_RUNTIME_KEYS in client/templates/play.html.
RUNTIME_KEYS: frozenset[str] = frozenset({
    # quick-action computed cards / recomputed action models
    "_quickActionCards", "quickActionCards", "_computedActions", "_computedCards",
    "_allActions", "_unifiedAttackCards", "_combatQuickCache", "_combatQuickRuntime",
    # rendered HTML blobs
    "renderedHtml", "_renderedHtml", "innerHTML", "_html",
    # dice results / roll caches
    "diceResults", "_diceResults", "lastRoll", "_lastRoll", "lastRollResult",
    "rollResults", "_rollCache",
    # spell runtime caches
    "spellRuntime", "_spellRuntime", "_spellRuntimeCache", "publicBaseCache",
    # item / image runtime caches
    "itemRuntime", "_itemRuntime", "_itemRuntimeCache", "_tokenImageCache",
    "imageCache", "_customAssetImageCache", "_monsterQuickCreatureCache",
    # combat runtime
    "combatRuntime", "_combatRuntime",
    # UI / transient modal state
    "uiState", "_uiState", "_panelState", "_scrollState",
    "modalState", "_modalState", "_pendingModal", "_openModal",
    # imported rawText duplicates kept only as transient caches
    "_rawTextCache", "rawTextDuplicate", "_rawTextDuplicate",
})

# Rendered-HTML style keys (renderedXxx / fooHtml / foo_html) are runtime-only.
_HTML_KEY_RE = re.compile(r"(?:^_)?rendered[A-Z_]|Html$|_html$")


def _is_runtime_key(key: str) -> bool:
    return key in RUNTIME_KEYS or bool(_HTML_KEY_RE.search(key))


def _strip_runtime_fields_only(value: Any, _seen: set[int] | None = None) -> Any:
    seen = _seen if _seen is not None else set()
    if isinstance(value, dict):
        ident = id(value)
        if ident in seen:
            return value
        seen.add(ident)
        for key in list(value.keys()):
            if _is_runtime_key(key):
                del value[key]
                continue
            _strip_runtime_fields_only(value[key], seen)
    elif isinstance(value, list):
        ident = id(value)
        if ident in seen:
            return value
        seen.add(ident)
        for item in value:
            _strip_runtime_fields_only(item, seen)
    return value


def strip_runtime_fields(value: Any, _seen: set[int] | None = None) -> Any:
    """Recursively remove runtime/transient keys from ``value`` in place.

    Returns the same object for convenience. Cycles and non-dict/list values are
    handled gracefully. When called at the profile save boundary, this also
    relocates oversized inline data-image fields and applies persistence-size
    caps so already-canonical but huge image strings do not survive saves.
    """
    _strip_runtime_fields_only(value, _seen)
    if isinstance(value, dict):
        sanitize_profile_persistence(value, profile_label=str(value.get("id") or value.get("name") or "?"))
    return value


def clean_oversized_profile(profile: Any) -> Any:
    """Migration entry point: strip runtime caches from a single stored profile.

    Safe to call on already-clean profiles and never removes canonical character
    data — only rebuildable runtime keys are stripped. Oversized data-image
    strings are relocated and any remaining clearly-oversized string is capped.
    """
    return strip_runtime_fields(profile)


def clean_char_profiles_map(profiles: dict) -> int:
    """Strip runtime caches from every profile in a ``char_profiles`` map
    (owner_key -> list[profile]). Returns the number of profiles cleaned."""
    cleaned = 0
    if not isinstance(profiles, dict):
        return 0
    for entries in profiles.values():
        if not isinstance(entries, list):
            continue
        for profile in entries:
            if isinstance(profile, dict):
                clean_oversized_profile(profile)
                cleaned += 1
    return cleaned
