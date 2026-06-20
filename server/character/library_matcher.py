"""Character-import library matching and gap reporting.

This module is intentionally read-only: it compares imported character names to
Alpha's current rules/item libraries and records gaps without mutating imported
items, spells, or features.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from server.character.rules_catalog import load_rules_catalog
from server.character.spell_compendium import list_spells

_REPORT_GROUPS = ("items", "spells", "features")
_REPORT_BUCKETS = ("exact", "alias", "normalized", "partial", "missing")
_RULESET_ROOT = Path(__file__).resolve().parents[1] / "data" / "rules" / "5e2024"
_ALIAS_ROOT = _RULESET_ROOT / "aliases"
_ALIAS_FILE_BY_GROUP = {
    "items": "item_aliases.json",
    "item": "item_aliases.json",
    "spells": "spell_aliases.json",
    "spell": "spell_aliases.json",
    "features": "feature_aliases.json",
    "feature": "feature_aliases.json",
    "subclasses": "subclass_aliases.json",
    "subclass": "subclass_aliases.json",
    "species": "species_aliases.json",
}


@dataclass(frozen=True)
class LibraryEntry:
    name: str
    content_type: str
    group: str
    source: str
    row_id: str = ""


def _coerce_alias_rows(payload: Any) -> dict[str, list[str]]:
    """Return {canonical_name_or_id: [aliases...]} from a small alias JSON payload."""
    if not isinstance(payload, dict):
        return {}
    rows: dict[str, list[str]] = {}
    for canonical, aliases in payload.items():
        canonical_text = str(canonical or "").strip()
        if not canonical_text:
            continue
        alias_values: list[str] = []
        if isinstance(aliases, list):
            alias_values = [str(value).strip() for value in aliases if str(value or "").strip()]
        elif isinstance(aliases, dict):
            for key in ("aliases", "names", "ddb", "dndBeyond", "ids", "slugs"):
                values = aliases.get(key)
                if isinstance(values, list):
                    alias_values.extend(str(value).strip() for value in values if str(value or "").strip())
                elif isinstance(values, str) and values.strip():
                    alias_values.append(values.strip())
        elif isinstance(aliases, str) and aliases.strip():
            alias_values = [aliases.strip()]
        rows[canonical_text] = sorted(set(alias_values), key=str.lower)
    return rows


@lru_cache(maxsize=None)
def load_alias_table(group: str) -> dict[str, list[str]]:
    """Load data-driven aliases for a 5e2024 rules group.

    The returned map is keyed by the canonical native display name or internal id;
    values are D&D Beyond/import aliases that should resolve to that canonical row.
    """
    normalized_group = str(group or "").strip().lower()
    filename = _ALIAS_FILE_BY_GROUP.get(normalized_group)
    if not filename:
        return {}
    path = _ALIAS_ROOT / filename
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return _coerce_alias_rows(payload)


def normalize_match_key(value: Any) -> str:
    """Normalize text for punctuation/case-insensitive library matching."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("&", " and ")
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"\barmour\b", "armor", text)
    text = re.sub(r"\bweapons? \+\s*(\d+)\b", r"weapon +\1", text)
    text = re.sub(r"\bshields? \+\s*(\d+)\b", r"shield +\1", text)
    plus_suffix = re.match(r"^\+(\d+)\s+(.+)$", text)
    if plus_suffix:
        text = f"{plus_suffix.group(2)} +{plus_suffix.group(1)}"
    text = re.sub(r"[^a-z0-9+]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 3 and text.endswith("s") and not text.endswith("ss"):
        text = text[:-1]
    return text


def _display_name(row: dict[str, Any]) -> str:
    return str(row.get("displayName") or row.get("name") or row.get("title") or row.get("id") or "").strip()


def _make_entry(row: dict[str, Any], *, content_type: str, group: str, source: str) -> LibraryEntry | None:
    name = _display_name(row)
    if not name:
        return None
    return LibraryEntry(
        name=name,
        content_type=content_type,
        group=group,
        source=source,
        row_id=str(row.get("id") or row.get("spell_id") or "").strip(),
    )


def _iter_feature_entries(catalog: dict[str, Any]) -> Iterable[LibraryEntry]:
    for key, ctype in (
        ("featsOrigin", "feat"),
        ("featsGeneral", "feat"),
        ("species", "species"),
        ("backgrounds", "background"),
        ("classes", "class"),
        ("subclasses", "subclass"),
    ):
        rows = catalog.get(key) if isinstance(catalog.get(key), list) else []
        for row in rows:
            if isinstance(row, dict):
                entry = _make_entry(row, content_type=ctype, group="features", source=f"rules_catalog.{key}")
                if entry:
                    yield entry
    for class_row in catalog.get("classes") if isinstance(catalog.get("classes"), list) else []:
        if not isinstance(class_row, dict):
            continue
        for feature in (class_row.get("featureDefinitions") or {}).values():
            if isinstance(feature, dict):
                entry = _make_entry(feature, content_type="class_feature", group="features", source="rules_catalog.class_features")
                if entry:
                    yield entry
    for subclass_row in catalog.get("subclasses") if isinstance(catalog.get("subclasses"), list) else []:
        if not isinstance(subclass_row, dict):
            continue
        for feature in (subclass_row.get("featureDefinitions") or {}).values():
            if isinstance(feature, dict):
                entry = _make_entry(feature, content_type="class_feature", group="features", source="rules_catalog.subclass_features")
                if entry:
                    yield entry


@lru_cache(maxsize=1)
def load_library_index() -> dict[str, Any]:
    """Build a small name index over Alpha's current item/spell/feature libraries."""
    entries: dict[str, list[LibraryEntry]] = {group: [] for group in _REPORT_GROUPS}

    try:
        from server.rules_db import get_all_srd_items, init_srd_items_table

        init_srd_items_table()
        for row in get_all_srd_items():
            if isinstance(row, dict):
                category = str(row.get("category") or "item").strip().lower() or "item"
                entry = _make_entry(row, content_type=category, group="items", source="srd_items")
                if entry:
                    entries["items"].append(entry)
    except Exception:
        pass

    catalog = load_rules_catalog()
    for row in catalog.get("spells") if isinstance(catalog.get("spells"), list) else []:
        if isinstance(row, dict):
            entry = _make_entry(row, content_type="spell", group="spells", source="rules_catalog.spells")
            if entry:
                entries["spells"].append(entry)
    for row in list_spells():
        if isinstance(row, dict):
            entry = _make_entry(row, content_type="spell", group="spells", source="spell_compendium")
            if entry:
                entries["spells"].append(entry)
    entries["features"].extend(_iter_feature_entries(catalog))

    by_key: dict[str, dict[str, LibraryEntry]] = {group: {} for group in _REPORT_GROUPS}
    exact_by_lower: dict[str, dict[str, LibraryEntry]] = {group: {} for group in _REPORT_GROUPS}
    for group, group_entries in entries.items():
        for entry in group_entries:
            exact_by_lower[group].setdefault(entry.name.lower(), entry)
            for value in (entry.name, entry.row_id):
                key = normalize_match_key(value)
                if key:
                    by_key[group].setdefault(key, entry)

    aliases: dict[str, dict[str, LibraryEntry]] = {group: {} for group in _REPORT_GROUPS}

    def _entry_for_alias_canonical(group: str, canonical: str, *, fallback_type: str) -> LibraryEntry:
        canonical_key = normalize_match_key(canonical)
        entry = by_key.get(group, {}).get(canonical_key)
        if entry:
            return entry
        return LibraryEntry(
            name=canonical,
            content_type=fallback_type,
            group=group,
            source="alias_table",
        )

    alias_sources = (
        ("items", "items", "alias"),
        ("spells", "spells", "spell"),
        ("features", "features", "feature"),
        ("features", "subclasses", "subclass"),
        ("features", "species", "species"),
    )
    for index_group, alias_group, fallback_type in alias_sources:
        for canonical, alias_names in load_alias_table(alias_group).items():
            canonical_entry = _entry_for_alias_canonical(index_group, canonical, fallback_type=fallback_type)
            for alias in [canonical, *alias_names]:
                alias_key = normalize_match_key(alias)
                if alias_key:
                    aliases[index_group].setdefault(alias_key, canonical_entry)

    return {"entries": entries, "by_key": by_key, "exact_by_lower": exact_by_lower, "aliases": aliases}


def _empty_report() -> dict[str, dict[str, list[dict[str, Any]]]]:
    return {group: {bucket: [] for bucket in _REPORT_BUCKETS} for group in _REPORT_GROUPS}


def _item_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("displayName") or value.get("label") or value.get("featId") or value.get("id") or "").strip()
    return str(value or "").strip()


def _content_type_from(row: Any, *keys: str, fallback: str = "item") -> str:
    if not isinstance(row, dict):
        return fallback
    for key in keys:
        text = str(row.get(key) or "").strip()
        if text:
            return text
    return fallback


def _add_unique_name(rows: list[dict[str, Any]], source: Any, *, content_type: str, source_hint: str = "") -> None:
    name = _item_name(source)
    if not name:
        return
    notes = ""
    if isinstance(source, dict):
        notes = str(source.get("notes") or source.get("description") or source.get("summary") or "").strip()
        row_source = str(source.get("source") or source_hint or "").strip()
    else:
        row_source = source_hint
    key = normalize_match_key(f"{content_type}:{name}:{row_source}")
    if any(item.get("_dedupeKey") == key for item in rows):
        return
    rows.append({"name": name, "content_type": content_type, "source": row_source, "notes": notes, "_dedupeKey": key})


def collect_imported_library_names(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract imported item/spell/feature names while preserving original names/notes."""
    doc = document if isinstance(document, dict) else {}
    out: dict[str, list[dict[str, Any]]] = {group: [] for group in _REPORT_GROUPS}

    equipment = doc.get("equipment") if isinstance(doc.get("equipment"), dict) else {}
    for row in equipment.get("inventory") if isinstance(equipment.get("inventory"), list) else []:
        _add_unique_name(out["items"], row, content_type=_content_type_from(row, "kind", "type", "equipment_kind", "item_type", fallback="item"), source_hint="equipment.inventory")
    for row in equipment.get("equipped", {}).values() if isinstance(equipment.get("equipped"), dict) else []:
        _add_unique_name(out["items"], row, content_type=_content_type_from(row, "kind", "type", "equipment_kind", "item_type", fallback="item"), source_hint="equipment.equipped")

    spell_state = doc.get("spellState") if isinstance(doc.get("spellState"), dict) else {}
    for row in spell_state.get("spellbookEntries") if isinstance(spell_state.get("spellbookEntries"), list) else []:
        _add_unique_name(out["spells"], row, content_type="spell", source_hint="spellState.spellbookEntries")
    for spell_id in list(spell_state.get("known") or []) + list(spell_state.get("prepared") or []):
        _add_unique_name(out["spells"], spell_id, content_type="spell", source_hint="spellState.ids")

    species = doc.get("species") if isinstance(doc.get("species"), dict) else {}
    _add_unique_name(out["features"], species.get("name"), content_type="species", source_hint="species")
    for trait in species.get("traits") if isinstance(species.get("traits"), list) else []:
        _add_unique_name(out["features"], trait, content_type="species_trait", source_hint="species.traits")

    background = doc.get("background") if isinstance(doc.get("background"), dict) else {}
    _add_unique_name(out["features"], background.get("name"), content_type="background", source_hint="background")
    for trait in background.get("traits") if isinstance(background.get("traits"), list) else []:
        _add_unique_name(out["features"], trait, content_type="background_trait", source_hint="background.traits")

    for row in doc.get("feats") if isinstance(doc.get("feats"), list) else []:
        _add_unique_name(out["features"], row.get("name") or row.get("featId"), content_type="feat", source_hint="feats")
    for row in doc.get("classes") if isinstance(doc.get("classes"), list) else []:
        if not isinstance(row, dict):
            continue
        _add_unique_name(out["features"], row.get("name"), content_type="class", source_hint="classes")
        _add_unique_name(out["features"], row.get("subclass"), content_type="subclass", source_hint="classes.subclass")
        for feature in row.get("features") if isinstance(row.get("features"), list) else []:
            _add_unique_name(out["features"], feature, content_type="class_feature", source_hint="classes.features")

    import_meta = doc.get("importMeta") if isinstance(doc.get("importMeta"), dict) else {}
    for feature in import_meta.get("importedFeatures") if isinstance(import_meta.get("importedFeatures"), list) else []:
        _add_unique_name(out["features"], feature, content_type=_content_type_from(feature, "kind", "type", fallback="feature"), source_hint="importMeta.importedFeatures")
    return out


def match_name(name: str, group: str, *, content_type: str = "") -> dict[str, Any]:
    """Match one imported name against a library group."""
    index = load_library_index()
    text = str(name or "").strip()
    lower = text.lower()
    key = normalize_match_key(text)
    exact = index["exact_by_lower"].get(group, {}).get(lower)
    alias = index["aliases"].get(group, {}).get(key)
    if exact and alias and (alias.row_id != exact.row_id or alias.name != exact.name):
        return {"status": "alias", "matched_name": alias.name, "matched_id": alias.row_id, "match_type": "alias"}
    if exact:
        return {"status": "exact", "matched_name": exact.name, "matched_id": exact.row_id, "match_type": "exact"}
    if alias:
        return {"status": "alias", "matched_name": alias.name, "matched_id": alias.row_id, "match_type": "alias"}
    normalized = index["by_key"].get(group, {}).get(key)
    if normalized:
        return {"status": "normalized", "matched_name": normalized.name, "matched_id": normalized.row_id, "match_type": "normalized"}
    if key:
        candidates = []
        for candidate_key, entry in index["by_key"].get(group, {}).items():
            if len(key) < 4 and len(candidate_key) < 4:
                continue
            if key in candidate_key or candidate_key in key:
                candidates.append((abs(len(candidate_key) - len(key)), entry))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1].name))
            entry = candidates[0][1]
            return {"status": "partial", "matched_name": entry.name, "matched_id": entry.row_id, "match_type": "partial"}
    return {"status": "missing", "matched_name": "", "matched_id": "", "match_type": "missing"}


def build_library_gap_report(document: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Return exact/alias/normalized/partial/missing buckets for imported character content."""
    report = _empty_report()
    imported = collect_imported_library_names(document)
    for group, rows in imported.items():
        seen: set[str] = set()
        for row in rows:
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            dedupe = normalize_match_key(f"{group}:{row.get('content_type')}:{name}")
            if dedupe in seen:
                continue
            seen.add(dedupe)
            match = match_name(name, group, content_type=str(row.get("content_type") or ""))
            bucket = match["status"] if match["status"] in _REPORT_BUCKETS else "missing"
            report[group][bucket].append({
                "imported_name": name,
                "content_type": row.get("content_type") or ("spell" if group == "spells" else "item"),
                "source": row.get("source") or "",
                "notes": row.get("notes") or "",
                "matched_name": match.get("matched_name") or "",
                "matched_id": match.get("matched_id") or "",
                "match_type": match.get("match_type") or bucket,
            })
    return report


def attach_library_gap_report(document: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Compute and attach importMeta.libraryGapReport without altering imported rows."""
    report = build_library_gap_report(document)
    if isinstance(document, dict):
        meta = document.get("importMeta") if isinstance(document.get("importMeta"), dict) else {}
        document["importMeta"] = meta
        meta["libraryGapReport"] = report
    return report


def summarize_library_gaps_from_profiles(profiles_by_owner: Any, *, limit: int = 20) -> dict[str, Any]:
    """Aggregate top missing content from stored character profiles."""
    counters = {group: Counter() for group in _REPORT_GROUPS}
    sources: dict[str, dict[str, list[dict[str, str]]]] = {group: defaultdict(list) for group in _REPORT_GROUPS}  # type: ignore[assignment]
    if isinstance(profiles_by_owner, dict):
        iterable = []
        for owner, rows in profiles_by_owner.items():
            if isinstance(rows, list):
                iterable.extend((owner, row) for row in rows if isinstance(row, dict))
    elif isinstance(profiles_by_owner, list):
        iterable = [("", row) for row in profiles_by_owner if isinstance(row, dict)]
    else:
        iterable = []

    for owner, profile in iterable:
        native = profile.get("nativeCharacter") if isinstance(profile.get("nativeCharacter"), dict) else {}
        meta = native.get("importMeta") if isinstance(native.get("importMeta"), dict) else profile.get("importMeta") if isinstance(profile.get("importMeta"), dict) else {}
        report = meta.get("libraryGapReport") if isinstance(meta.get("libraryGapReport"), dict) else {}
        character_name = str(profile.get("name") or ((native.get("identity") or {}) if isinstance(native.get("identity"), dict) else {}).get("name") or "Unknown Character").strip()
        source_mode = str(profile.get("sourceMode") or native.get("sourceMode") or meta.get("origin") or meta.get("source") or "import").strip()
        profile_id = str(profile.get("id") or "").strip()
        for group in _REPORT_GROUPS:
            missing = (report.get(group) or {}).get("missing") if isinstance(report.get(group), dict) else []
            for row in missing if isinstance(missing, list) else []:
                name = str((row or {}).get("imported_name") or (row or {}).get("name") or "").strip()
                if not name:
                    continue
                counters[group][name] += 1
                sources[group][name].append({
                    "character": character_name,
                    "profile_id": profile_id,
                    "owner": str(owner or ""),
                    "source": source_mode,
                    "content_type": str((row or {}).get("content_type") or ""),
                })
    top = {}
    for group in _REPORT_GROUPS:
        top[group] = [
            {"name": name, "count": count, "sources": sources[group][name][:10]}
            for name, count in counters[group].most_common(max(1, limit))
        ]
    return {"ok": True, "top_missing": top}
