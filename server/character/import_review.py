"""Import review summaries for character imports.

The review object is deliberately data-only so both API responses and the
browser import modal can render the same safety decision before play.
"""
from __future__ import annotations

import time
from typing import Any

REVIEW_STATUSES = {"exact", "playable_with_warnings", "needs_review", "blocked"}
SOURCE_TYPES = {"native", "dndbeyond", "pdf", "manual", "unknown"}


def _safe_str(value: Any, fallback: str = "", *, limit: int = 160) -> str:
    text = str(value or fallback).strip()[:limit]
    return text or fallback


def _safe_int(value: Any, default: int = 0, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, parsed)


def normalize_import_source(value: Any, *, import_meta: dict[str, Any] | None = None) -> str:
    """Return the canonical import-review source type."""
    meta = import_meta if isinstance(import_meta, dict) else {}
    raw = _safe_str(value or meta.get("sourceType") or meta.get("source") or meta.get("origin"), "unknown", limit=80).lower()
    if raw in SOURCE_TYPES:
        return raw
    if raw in {"ddb", "ddb_json", "dndbeyond_json", "dndbeyond_id"} or "dndbeyond" in raw or "d&d beyond" in raw:
        return "dndbeyond"
    if "pdf" in raw:
        return "pdf"
    if raw in {"builder", "created", "hand_entry"}:
        return "manual"
    if raw in {"existing", "legacy", ""}:
        return "unknown"
    return "unknown"


def _class_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in (document.get("classes") if isinstance(document.get("classes"), list) else []) if isinstance(row, dict)]


def _primary_class(document: dict[str, Any]) -> dict[str, Any]:
    rows = _class_rows(document)
    return rows[0] if rows else {}


def _class_summary(document: dict[str, Any]) -> str:
    labels: list[str] = []
    for row in _class_rows(document):
        name = _safe_str(row.get("name") or row.get("className") or row.get("classId"), limit=80)
        level = _safe_int(row.get("level"), 0, minimum=0)
        if name:
            labels.append(f"{name} {level}".strip() if level else name)
    return " / ".join(labels)


def _total_level(document: dict[str, Any]) -> int:
    total = sum(_safe_int(row.get("level"), 0, minimum=0) for row in _class_rows(document))
    return total or _safe_int(document.get("level"), 0, minimum=0)


def _name_list(rows: Any, *, name_key: str = "name") -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict):
            name = _safe_str(row.get(name_key) or row.get("displayName") or row.get("id"), limit=120)
        else:
            name = _safe_str(row, limit=120)
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            out.append(name)
    return out


def _warning_rows(import_meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = import_meta.get("warnings") if isinstance(import_meta.get("warnings"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def _warning_messages(rows: list[dict[str, Any]], *, blocking: bool | None = None) -> list[str]:
    out: list[str] = []
    for row in rows:
        if blocking is not None and bool(row.get("blocking")) != blocking:
            continue
        msg = _safe_str(row.get("message") or row.get("code"), limit=240)
        if msg:
            out.append(msg)
    return out


def _missing_from_warnings(rows: list[dict[str, Any]], codes: set[str]) -> list[str]:
    values: list[str] = []
    for row in rows:
        code = _safe_str(row.get("code"), limit=80).lower()
        if code not in codes:
            continue
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        for key in ("spell", "spells", "item", "items", "feature", "feat", "missing"):
            raw = details.get(key)
            if isinstance(raw, list):
                values.extend(_name_list(raw))
            elif raw:
                values.append(_safe_str(raw, limit=120))
        if not values:
            msg = _safe_str(row.get("message") or code.replace("_", " "), limit=180)
            if msg:
                values.append(msg)
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            deduped.append(value)
    return deduped


def _comparison(*, label: str, source_value: Any, resolved_value: Any) -> dict[str, Any]:
    has_source = source_value not in (None, "")
    has_resolved = resolved_value not in (None, "")
    status = "unavailable"
    if has_source and has_resolved:
        status = "match" if str(source_value) == str(resolved_value) else "needs_review"
    elif has_source or has_resolved:
        status = "available"
    return {"label": label, "source": source_value, "resolved": resolved_value, "status": status}


def build_import_review(document: Any, *, source_type: str = "", runtime: Any = None) -> dict[str, Any]:
    """Build a structured import review result from a canonical character document."""
    doc = document if isinstance(document, dict) else {}
    runtime_doc = runtime if isinstance(runtime, dict) else {}
    identity = doc.get("identity") if isinstance(doc.get("identity"), dict) else {}
    species = doc.get("species") if isinstance(doc.get("species"), dict) else {}
    background = doc.get("background") if isinstance(doc.get("background"), dict) else {}
    equipment = doc.get("equipment") if isinstance(doc.get("equipment"), dict) else {}
    spell_state = doc.get("spellState") if isinstance(doc.get("spellState"), dict) else {}
    import_meta = doc.get("importMeta") if isinstance(doc.get("importMeta"), dict) else {}
    warnings = _warning_rows(import_meta)

    source = normalize_import_source(source_type or doc.get("sourceMode"), import_meta=import_meta)
    imported_spells = import_meta.get("importedSpells") if isinstance(import_meta.get("importedSpells"), list) else []
    if not imported_spells:
        imported_spells = spell_state.get("spellbookEntries") if isinstance(spell_state.get("spellbookEntries"), list) else []
    imported_features = import_meta.get("importedFeatures") if isinstance(import_meta.get("importedFeatures"), list) else []
    inventory_rows = equipment.get("inventory") if isinstance(equipment.get("inventory"), list) else []

    spells_matched = _name_list([row for row in imported_spells if not isinstance(row, dict) or row.get("matchedNative", True)])
    spells_missing = _name_list([row for row in imported_spells if isinstance(row, dict) and row.get("matchedNative") is False])
    spells_missing.extend(_missing_from_warnings(warnings, {"missing_spell_mapping", "missing_spells"}))

    items_matched = _name_list(inventory_rows)
    items_missing = _missing_from_warnings(warnings, {"missing_inventory", "missing_item_mapping", "missing_items"})

    features_matched = _name_list(imported_features)
    features_missing = _missing_from_warnings(warnings, {"unknown_feat", "missing_features", "missing_feature_mapping"})

    runtime_hp = runtime_doc.get("hp") if isinstance(runtime_doc.get("hp"), dict) else {}
    runtime_combat = runtime_doc.get("combat") if isinstance(runtime_doc.get("combat"), dict) else {}
    source_ac = doc.get("ac") if doc.get("ac") not in (None, "") else import_meta.get("sourceAC")
    resolved_ac = runtime_doc.get("ac") if runtime_doc.get("ac") not in (None, "") else runtime_combat.get("ac")
    source_hp = doc.get("maxHP") if doc.get("maxHP") not in (None, "") else import_meta.get("sourceMaxHP")
    resolved_hp = runtime_hp.get("max") if runtime_hp.get("max") not in (None, "") else runtime_combat.get("maxHP")

    required_basics = {
        "name": bool(_safe_str(identity.get("displayName") or identity.get("name") or doc.get("name"))),
        "class": bool(_class_rows(doc)),
        "species": bool(_safe_str(species.get("name") or species.get("id"))),
        "background": bool(_safe_str(background.get("name") or background.get("id"))),
    }
    has_ac = (source_ac not in (None, "")) or (resolved_ac not in (None, ""))
    has_hp = (source_hp not in (None, "")) or (resolved_hp not in (None, ""))

    blocking_issues = _warning_messages(warnings, blocking=True)
    if not required_basics["name"]:
        blocking_issues.append("Character name is required before play.")
    if not required_basics["class"]:
        blocking_issues.append("At least one class/level is required before play.")
    if not has_hp:
        blocking_issues.append("HP is required before play.")
    if not has_ac:
        blocking_issues.append("AC is required before play.")

    review_warnings = _warning_messages(warnings, blocking=False)
    if not required_basics["species"]:
        review_warnings.append("Species/race is missing and should be reviewed.")
    if not required_basics["background"]:
        review_warnings.append("Background is missing and should be reviewed.")

    if blocking_issues:
        status = "blocked"
    elif spells_missing or items_missing or features_missing:
        status = "needs_review"
    elif review_warnings:
        status = "playable_with_warnings"
    else:
        status = "exact"

    can_continue = not blocking_issues and required_basics["name"] and required_basics["class"] and has_hp and has_ac
    can_review_later = can_continue and status in {"playable_with_warnings", "needs_review"}

    return {
        "sourceType": source,
        "importTimestamp": import_meta.get("importedAt") or time.time(),
        "characterName": _safe_str(identity.get("displayName") or identity.get("name") or doc.get("name"), "Unnamed Character"),
        "class": _class_summary(doc),
        "subclass": _safe_str(_primary_class(doc).get("subclass") or _primary_class(doc).get("subclassName") or _primary_class(doc).get("subclassId")),
        "level": _total_level(doc),
        "speciesRace": _safe_str(species.get("name") or species.get("id")),
        "background": _safe_str(background.get("name") or background.get("id")),
        "acComparison": _comparison(label="Armor Class", source_value=source_ac, resolved_value=resolved_ac),
        "hpComparison": _comparison(label="Hit Points", source_value=source_hp, resolved_value=resolved_hp),
        "spellsMatched": spells_matched,
        "spellsMissing": spells_missing,
        "itemsMatched": items_matched,
        "itemsMissing": items_missing,
        "featuresMatched": features_matched,
        "featuresMissing": features_missing,
        "warnings": review_warnings,
        "blockingIssues": blocking_issues,
        "requiredBasics": required_basics,
        "hasHP": has_hp,
        "hasAC": has_ac,
        "canContinueToPlay": can_continue,
        "canReviewLater": can_review_later,
        "reviewStatus": status if status in REVIEW_STATUSES else "needs_review",
    }
