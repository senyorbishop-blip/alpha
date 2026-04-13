"""Spell ID reconciliation for canonical character documents.

Validates each spell ID in spellState.known / spellState.prepared against the
SQLite rules_spells table.  For any ID not found by exact match a fallback
lookup by normalised name is attempted.  Unresolvable IDs are logged as
warnings and kept as-is (never silently dropped).
"""
from __future__ import annotations

import logging
from typing import Any

from server.rules_db import get_spell_by_id, lookup_spell_id_by_normalized_name
from server.rules_engine import normalize_name

logger = logging.getLogger(__name__)


def reconcile_spell_ids(spell_ids: list[str], *, list_name: str = "known") -> list[str]:
    """Validate and reconcile a list of spell IDs against the rules_spells table.

    For each ID:
    - Exact match found in rules_spells    → kept unchanged.
    - No exact match, normalised-name match found → replaced with the canonical
      id from the DB and a WARNING is logged.
    - No match by either strategy          → WARNING logged, original ID kept
      as-is (not silently dropped).

    Returns the reconciled list (same length as valid non-empty input IDs).
    """
    if not spell_ids:
        return list(spell_ids)

    reconciled: list[str] = []
    for raw_id in spell_ids:
        spell_id = str(raw_id or "").strip()
        if not spell_id:
            continue

        # Fast path: exact ID match in rules_spells.
        if get_spell_by_id(spell_id) is not None:
            reconciled.append(spell_id)
            continue

        # Fallback: normalised-name lookup (handles cases where the stored
        # value is a human-readable name rather than a canonical slug).
        norm = normalize_name(spell_id)
        canonical_id = lookup_spell_id_by_normalized_name(norm) if norm else None
        if canonical_id:
            logger.warning(
                "spell_reconciler: %r not found by exact id; resolved to %r "
                "via normalised name (list=%s)",
                spell_id,
                canonical_id,
                list_name,
            )
            reconciled.append(canonical_id)
        else:
            logger.warning(
                "spell_reconciler: %r not found in rules_spells by id or "
                "normalised name – keeping as-is (list=%s)",
                spell_id,
                list_name,
            )
            reconciled.append(spell_id)

    return reconciled


def reconcile_character_spell_state(document: Any) -> Any:
    """Reconcile spellState.known and spellState.prepared in a canonical document.

    Mutates and returns the document with reconciled spell ID lists.
    Gracefully handles a missing or malformed spellState.
    """
    if not isinstance(document, dict):
        return document

    spell_state = document.get("spellState")
    if not isinstance(spell_state, dict):
        return document

    known = spell_state.get("known")
    if isinstance(known, list):
        spell_state["known"] = reconcile_spell_ids(known, list_name="known")

    prepared = spell_state.get("prepared")
    if isinstance(prepared, list):
        spell_state["prepared"] = reconcile_spell_ids(prepared, list_name="prepared")

    document["spellState"] = spell_state
    return document
