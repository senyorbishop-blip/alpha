from __future__ import annotations

import copy
import re
import time
from typing import Any

from server.character.validation import validate_or_raise


_DDB_ABILITY_MAP = {
    1: "str",
    2: "dex",
    3: "con",
    4: "int",
    5: "wis",
    6: "cha",
}

_KNOWN_SUBCLASS_BY_CLASS: dict[str, set[str]] = {
    "barbarian": {"path of the berserker", "path of the totem warrior", "path of the world tree"},
    "bard": {"college of glamour", "college of lore", "college of valor"},
    "cleric": {"life domain", "light domain", "trickery domain", "war domain"},
    "druid": {"circle of the land", "circle of the moon"},
    "fighter": {"champion", "battle master", "eldritch knight", "psi warrior"},
    "monk": {"way of the open hand", "way of shadow", "way of the four elements"},
    "paladin": {"oath of devotion", "oath of the ancients", "oath of vengeance"},
    "ranger": {"hunter", "beast master", "gloom stalker"},
    "rogue": {"thief", "assassin", "arcane trickster"},
    "sorcerer": {"draconic bloodline", "wild magic"},
    "warlock": {"the archfey", "the fiend", "the great old one"},
    "wizard": {"school of abjuration", "school of divination", "school of evocation", "school of illusion", "school of necromancy"},
}

_SPECIES_ALIAS_MAP: dict[str, list[str]] = {
    "elf": ["high elf", "wood elf", "drow"],
    "dwarf": ["hill dwarf", "mountain dwarf"],
    "gnome": ["forest gnome", "rock gnome"],
    "halfling": ["lightfoot halfling", "stout halfling"],
}

_KNOWN_FEATS: set[str] = {
    "alert",
    "athlete",
    "dual wielder",
    "great weapon master",
    "healer",
    "lucky",
    "magic initiate",
    "mobile",
    "observant",
    "resilient",
    "sharpshooter",
    "tough",
    "war caster",
}


def _safe_str(value: Any, fallback: str = "", *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return text[:limit]


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _parse_coin_text(value: str) -> dict[str, int]:
    coins = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
    text = str(value or "").strip().lower()
    if not text:
        return coins

    for match in re.finditer(r"(\d+)\s*(cp|sp|ep|gp|pp)", text):
        amount = _safe_int(match.group(1), 0, minimum=0)
        kind = match.group(2)
        coins[kind] = amount
    return coins


def _extract_ddb_character(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else None
    if isinstance(data, dict):
        return data
    return raw


def _make_warning(
    *,
    code: str,
    message: str,
    blocking: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "blocking": bool(blocking),
        "severity": "required" if blocking else "warning",
        "details": copy.deepcopy(details or {}),
    }


def _normalize_resolution_payload(src: dict[str, Any]) -> dict[str, str]:
    resolution = src.get("import_resolution")
    if not isinstance(resolution, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in resolution.items():
        if value is None:
            continue
        normalized[str(key).strip().lower()] = _safe_str(value, "", limit=80)
    return normalized


def normalize_ddb_json_payload(raw_payload: Any, *, external_id: str = "") -> dict[str, Any]:
    src = raw_payload if isinstance(raw_payload, dict) else {}
    ddb = _extract_ddb_character(src)
    warnings: list[dict[str, Any]] = []
    resolution = _normalize_resolution_payload(src)

    stats_rows = ddb.get("stats") if isinstance(ddb.get("stats"), list) else []
    bonus_rows = ddb.get("bonusStats") if isinstance(ddb.get("bonusStats"), list) else []
    override_rows = ddb.get("overrideStats") if isinstance(ddb.get("overrideStats"), list) else []

    base_scores: dict[int, int] = {}
    bonus_scores: dict[int, int] = {}
    override_scores: dict[int, int] = {}

    for row in stats_rows:
        if not isinstance(row, dict):
            continue
        ability_id = _safe_int(row.get("id"), 0)
        if ability_id:
            base_scores[ability_id] = _safe_int(row.get("value"), 10)

    for row in bonus_rows:
        if not isinstance(row, dict):
            continue
        ability_id = _safe_int(row.get("id"), 0)
        if ability_id:
            bonus_scores[ability_id] = _safe_int(row.get("value"), 0)

    for row in override_rows:
        if not isinstance(row, dict):
            continue
        ability_id = _safe_int(row.get("id"), 0)
        value = row.get("value")
        if ability_id and value is not None:
            override_scores[ability_id] = _safe_int(value, 10)

    ability_scores = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}
    for ability_id, key in _DDB_ABILITY_MAP.items():
        if ability_id in override_scores:
            ability_scores[key] = override_scores[ability_id]
        else:
            ability_scores[key] = base_scores.get(ability_id, 10) + bonus_scores.get(ability_id, 0)

    class_rows = ddb.get("classes") if isinstance(ddb.get("classes"), list) else []
    classes: list[dict[str, Any]] = []
    for row in class_rows:
        if not isinstance(row, dict):
            continue
        definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
        subclass_def = row.get("subclassDefinition") if isinstance(row.get("subclassDefinition"), dict) else {}
        class_name = _safe_str(definition.get("name"), "")
        level = _safe_int(row.get("level"), 1, minimum=1)
        if not class_name:
            continue
        class_entry = {
            "name": class_name,
            "classId": class_name.lower().replace(" ", "-"),
            "level": level,
        }
        subclass_name = _safe_str(subclass_def.get("name"), "")
        if subclass_name:
            class_entry["subclass"] = subclass_name
            known_subclasses = _KNOWN_SUBCLASS_BY_CLASS.get(class_entry["classId"], set())
            if known_subclasses and subclass_name.strip().lower() not in known_subclasses:
                warnings.append(
                    _make_warning(
                        code="unsupported_subclass",
                        message=f'Subclass "{subclass_name}" for class "{class_name}" is not fully mapped yet.',
                        blocking=False,
                        details={
                            "classId": class_entry["classId"],
                            "className": class_name,
                            "subclass": subclass_name,
                        },
                    )
                )
        classes.append(class_entry)

    if not classes:
        warnings.append(
            _make_warning(
                code="unsupported_subclass",
                message="No class levels were found in the import; defaulted to Adventurer level 1.",
                blocking=False,
            )
        )
        classes = [{"name": "Adventurer", "classId": "adventurer", "level": 1}]

    race = ddb.get("race") if isinstance(ddb.get("race"), dict) else {}
    background = ddb.get("background") if isinstance(ddb.get("background"), dict) else {}

    total_level = sum(_safe_int(cls.get("level"), 1, minimum=1) for cls in classes)
    if total_level <= 0:
        total_level = 1

    name = _safe_str(ddb.get("name"), "Unnamed Character", limit=120)
    if not _safe_str(ddb.get("name")):
        warnings.append(
            _make_warning(
                code="ambiguous_species",
                message="Character name was missing in import payload; using a fallback name.",
                blocking=False,
            )
        )

    character_id = _safe_str(ddb.get("id"), external_id, limit=120)
    if not character_id:
        character_id = f"ddb-{int(time.time())}"

    source_meta = {
        "origin": "dndbeyond",
        "source": "dndbeyond",
        "externalId": character_id,
        "importedAt": time.time(),
        "rawVersion": _safe_str(ddb.get("version") or ddb.get("dateModified") or "", limit=80),
        "rawSnapshot": copy.deepcopy(src),
        "mappingNotes": [],
    }

    speed = 30
    try:
        speed = _safe_int(((race.get("weightSpeeds") or {}).get("normal") or {}).get("walk"), 30, minimum=0)
    except Exception:
        speed = 30

    document = {
        "schemaVersion": 1,
        "rulesMode": "casual",
        "ruleset": "casual-dnd-5e-compatible",
        "sourceMode": "dndbeyond",
        "identity": {
            "characterId": character_id,
            "name": name,
            "displayName": name,
            "portraitUrl": _safe_str((ddb.get("decorations") or {}).get("avatarUrl"), "", limit=400),
            "alignment": _safe_str(ddb.get("alignmentName"), "", limit=60),
        },
        "species": {
            "id": _safe_str(race.get("baseName") or race.get("fullName"), "", limit=80).lower().replace(" ", "-"),
            "name": _safe_str(race.get("fullName") or race.get("baseName"), "", limit=80),
            "size": "medium",
            "speed": speed,
        },
        "background": {
            "id": _safe_str((background.get("definition") or {}).get("name") or background.get("name"), "", limit=80).lower().replace(" ", "-"),
            "name": _safe_str((background.get("definition") or {}).get("name") or background.get("name"), "", limit=80),
        },
        "abilities": {
            "generationMode": "imported",
            "scores": ability_scores,
        },
        "classes": classes,
        "awakening": {
            "stage": 0,
            "pathId": "",
            "nodes": [],
            "flags": {},
        },
        "equipment": {
            "currency": {
                "cp": _safe_int(ddb.get("currencies", {}).get("cp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "sp": _safe_int(ddb.get("currencies", {}).get("sp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "ep": _safe_int(ddb.get("currencies", {}).get("ep"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "gp": _safe_int(ddb.get("currencies", {}).get("gp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
                "pp": _safe_int(ddb.get("currencies", {}).get("pp"), 0, minimum=0) if isinstance(ddb.get("currencies"), dict) else 0,
            },
            "inventory": [],
            "equipped": {},
            "containers": [],
        },
        "importMeta": source_meta,
    }

    species_base = _safe_str(race.get("baseName"), "", limit=80)
    species_name = document["species"]["name"]
    if not species_name:
        resolved_species = _safe_str(resolution.get("species"), "", limit=80)
        if resolved_species:
            document["species"]["name"] = resolved_species
            document["species"]["id"] = resolved_species.lower().replace(" ", "-")
        else:
            warnings.append(
                _make_warning(
                    code="ambiguous_species",
                    message="Species/Race was not found in this import and must be selected before final save.",
                    blocking=True,
                    details={"resolutionKey": "species"},
                )
            )
    elif species_base and species_base.lower() in _SPECIES_ALIAS_MAP and not resolution.get("species"):
        warnings.append(
            _make_warning(
                code="ambiguous_species",
                message=f'Species "{species_base}" has multiple native mappings. Choose a species mapping to continue.',
                blocking=True,
                details={
                    "resolutionKey": "species",
                    "options": list(_SPECIES_ALIAS_MAP.get(species_base.lower()) or []),
                },
            )
        )
    elif resolution.get("species"):
        resolved_species = _safe_str(resolution.get("species"), species_name, limit=80)
        document["species"]["name"] = resolved_species
        document["species"]["id"] = resolved_species.lower().replace(" ", "-")

    if not document["background"]["name"]:
        warnings.append(
            _make_warning(
                code="unknown_feat",
                message="Background was not found in this import.",
                blocking=False,
            )
        )
    if total_level <= 0:
        warnings.append(
            _make_warning(
                code="unsupported_subclass",
                message="Character level could not be inferred; defaulted to level 1.",
                blocking=False,
            )
        )

    spell_rows = ddb.get("spells") if isinstance(ddb.get("spells"), dict) else {}
    class_spells = spell_rows.get("class") if isinstance(spell_rows.get("class"), list) else []
    missing_spell_names = 0
    for row in class_spells:
        if not isinstance(row, dict):
            continue
        definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
        if not _safe_str(definition.get("name"), ""):
            missing_spell_names += 1
    if missing_spell_names:
        warnings.append(
            _make_warning(
                code="missing_spell_mapping",
                message=f"{missing_spell_names} imported spell rows could not be mapped and were skipped.",
                blocking=False,
                details={"count": missing_spell_names},
            )
        )

    feat_rows = ddb.get("feats") if isinstance(ddb.get("feats"), list) else []
    for feat_row in feat_rows:
        if not isinstance(feat_row, dict):
            continue
        feat_name = _safe_str((feat_row.get("definition") or {}).get("name"), "", limit=120)
        if not feat_name:
            continue
        if feat_name.lower() not in _KNOWN_FEATS:
            warnings.append(
                _make_warning(
                    code="unknown_feat",
                    message=f'Feat "{feat_name}" is not in the native feat map yet and was preserved as import metadata only.',
                    blocking=False,
                    details={"feat": feat_name},
                )
            )

    source_meta["nativeImportMode"] = "ddb_import"
    source_meta["resolution"] = resolution
    source_meta["warnings"] = copy.deepcopy(warnings)

    canonical = validate_or_raise(document)
    required = [item for item in warnings if item.get("blocking")]
    return {
        "document": canonical,
        "warnings": warnings,
        "requires_resolution": bool(required),
        "required_choices": required,
    }


def normalize_pdf_payload(raw_payload: Any, *, filename: str = "") -> dict[str, Any]:
    src = raw_payload if isinstance(raw_payload, dict) else {}
    warnings: list[str] = []

    classes = src.get("classes") if isinstance(src.get("classes"), list) else []
    canonical_classes: list[dict[str, Any]] = []
    for row in classes:
        if not isinstance(row, dict):
            continue
        name = _safe_str(row.get("name"), "")
        if not name:
            continue
        canonical_classes.append(
            {
                "name": name,
                "classId": name.lower().replace(" ", "-"),
                "level": _safe_int(row.get("level"), 1, minimum=1),
                "subclass": _safe_str(row.get("subclass"), "", limit=80),
            }
        )

    if not canonical_classes:
        canonical_classes = [{"name": "Adventurer", "classId": "adventurer", "level": 1}]
        warnings.append("Class data was incomplete in PDF import; defaulted to Adventurer level 1.")

    stats = src.get("stats") if isinstance(src.get("stats"), list) else []
    ability_scores = {
        "str": _safe_int(stats[0], 10) if len(stats) > 0 else 10,
        "dex": _safe_int(stats[1], 10) if len(stats) > 1 else 10,
        "con": _safe_int(stats[2], 10) if len(stats) > 2 else 10,
        "int": _safe_int(stats[3], 10) if len(stats) > 3 else 10,
        "wis": _safe_int(stats[4], 10) if len(stats) > 4 else 10,
        "cha": _safe_int(stats[5], 10) if len(stats) > 5 else 10,
    }

    book = src.get("book") if isinstance(src.get("book"), dict) else {}
    currency = _parse_coin_text(_safe_str(src.get("currency") or book.get("currency"), ""))
    imported_id = _safe_str(src.get("id") or src.get("name") or filename, "", limit=120)
    character_id = f"pdf-{re.sub(r'[^a-zA-Z0-9]+', '-', imported_id).strip('-').lower()}" if imported_id else f"pdf-{int(time.time())}"

    document = {
        "schemaVersion": 1,
        "rulesMode": "casual",
        "ruleset": "casual-dnd-5e-compatible",
        "sourceMode": "dndbeyond",
        "identity": {
            "characterId": character_id,
            "name": _safe_str(src.get("name"), "Unnamed Character", limit=120),
            "displayName": _safe_str(src.get("name"), "Unnamed Character", limit=120),
            "alignment": _safe_str(src.get("alignment"), "", limit=60),
        },
        "species": {
            "id": _safe_str(src.get("race"), "", limit=80).lower().replace(" ", "-"),
            "name": _safe_str(src.get("race"), "", limit=80),
            "size": "medium",
            "speed": _safe_int(src.get("speed"), 30, minimum=0),
        },
        "background": {
            "id": _safe_str(src.get("background"), "", limit=80).lower().replace(" ", "-"),
            "name": _safe_str(src.get("background"), "", limit=80),
        },
        "abilities": {
            "generationMode": "imported",
            "scores": ability_scores,
        },
        "classes": canonical_classes,
        "equipment": {
            "currency": currency,
            "inventory": [],
            "equipped": {},
            "containers": [],
        },
        "importMeta": {
            "origin": "dndbeyond_pdf",
            "source": "pdf",
            "externalId": character_id,
            "importedAt": time.time(),
            "rawVersion": "",
            "rawSnapshot": copy.deepcopy(src),
            "mappingNotes": [],
        },
    }

    if not document["species"]["name"]:
        warnings.append("Species/Race was not found in PDF import.")
    if not document["background"]["name"]:
        warnings.append("Background was not found in PDF import.")
    if src.get("_rawFields") is None:
        warnings.append("Raw PDF fields were unavailable; import may be partial.")

    canonical = validate_or_raise(document)
    return {
        "document": canonical,
        "warnings": warnings,
    }
