"""Service helpers for canonical native character docs and runtime resolution.

This module intentionally keeps persistence integration shallow for now:
- canonical native documents are validated/resolved here
- legacy charBook/charSheet compatibility payloads can be generated on demand
"""
from __future__ import annotations

import time
from typing import Any

from server.character.export_mapper import (
    map_character_to_charbook,
    map_character_to_charsheet,
)
from server.character.progression import apply_levelup, build_levelup_preview
from server.character.resolver import resolve_character_runtime
from server.character.rules_catalog import load_rules_catalog
from server.character.schema import default_character_document
from server.character.spell_reconciler import reconcile_character_spell_state
from server.character.validation import ensure_character_defaults, validate_or_raise


_NATIVE_SERVICE_VERSION = 1


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _safe_str(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _build_class_summary(char_sheet: dict) -> str:
    if not isinstance(char_sheet, dict):
        return ""
    classes = char_sheet.get("classes") if isinstance(char_sheet.get("classes"), list) else []
    labels: list[str] = []
    for item in classes:
        if not isinstance(item, dict):
            continue
        name = _safe_str(item.get("name"))
        subclass = _safe_str(item.get("subclass"))
        if not name:
            continue
        if subclass:
            labels.append(f"{name} ({subclass})")
        else:
            labels.append(name)
    return " / ".join(labels)[:120]


def _normalize_builder_draft_document(raw: dict) -> dict:
    """Coerce builder-draft payloads into a canonical document candidate."""
    identity = raw.get("identity") if isinstance(raw.get("identity"), dict) else {}
    presentation = raw.get("presentation") if isinstance(raw.get("presentation"), dict) else {}
    token_display = presentation.get("tokenDisplay") if isinstance(presentation.get("tokenDisplay"), dict) else {}
    species = raw.get("species") if isinstance(raw.get("species"), dict) else {}
    background = raw.get("background") if isinstance(raw.get("background"), dict) else {}
    cls = raw.get("class") if isinstance(raw.get("class"), dict) else {}
    progression = raw.get("progression") if isinstance(raw.get("progression"), dict) else {}
    awakening = progression.get("awakening") if isinstance(progression.get("awakening"), dict) else {}
    origins = raw.get("origins") if isinstance(raw.get("origins"), dict) else {}
    spellbook = raw.get("spellbook") if isinstance(raw.get("spellbook"), dict) else {}
    equipment = raw.get("equipment") if isinstance(raw.get("equipment"), dict) else {}
    import_meta = raw.get("importMeta") if isinstance(raw.get("importMeta"), dict) else {}

    level = _safe_int(progression.get("level"), 1, minimum=1)
    class_id = _safe_str(cls.get("id"))
    class_subclass_id = _safe_str(cls.get("subclassId") or cls.get("subclass"))
    class_subclass = _safe_str(cls.get("subclass"))

    abilities = raw.get("abilities") if isinstance(raw.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else abilities

    classes = raw.get("classes") if isinstance(raw.get("classes"), list) else []
    if not classes and class_id:
        class_row = {"name": class_id, "classId": class_id, "level": level}
        if class_subclass_id:
            class_row["subclassId"] = class_subclass_id
        if class_subclass:
            class_row["subclass"] = class_subclass
        classes = [class_row]

    if not background and _safe_str(identity.get("background")):
        background = {"name": _safe_str(identity.get("background"))}
    if not background and (_safe_str(origins.get("backgroundId")) or _safe_str(origins.get("backgroundName"))):
        background = {
            "id": _safe_str(origins.get("backgroundId")),
            "name": _safe_str(origins.get("backgroundName") or origins.get("backgroundId")),
        }

    spell_known = spellbook.get("known") if isinstance(spellbook.get("known"), list) else []
    spell_prepared = spellbook.get("prepared") if isinstance(spellbook.get("prepared"), list) else []
    spell_mode = _safe_str(spellbook.get("castingMode"), "none").lower()[:24]

    equipment_currency = equipment.get("currency") if isinstance(equipment.get("currency"), dict) else {}
    equipment_choices = equipment.get("choices") if isinstance(equipment.get("choices"), list) else []
    origins_languages = origins.get("languages") if isinstance(origins.get("languages"), list) else []
    origins_proficiencies = origins.get("proficiencies") if isinstance(origins.get("proficiencies"), list) else []
    progression_feats = progression.get("feats") if isinstance(progression.get("feats"), list) else []
    progression_talents = progression.get("talents") if isinstance(progression.get("talents"), list) else []

    return {
        "schemaVersion": _safe_int(raw.get("schemaVersion"), 1, minimum=1),
        "rulesMode": _safe_str(raw.get("rulesMode"), "casual"),
        "ruleset": _safe_str(raw.get("ruleset"), "casual-dnd-5e-compatible"),
        "contentPackVersion": _safe_str(raw.get("contentPackVersion"), ""),
        "sourceMode": _safe_str(raw.get("sourceMode"), "native").lower(),
        "identity": {
            "characterId": _safe_str(identity.get("characterId")),
            "name": _safe_str(identity.get("name")),
            "displayName": _safe_str(identity.get("displayName") or identity.get("name")),
            "pronouns": _safe_str(identity.get("pronouns")),
            "portraitUrl": _safe_str(identity.get("portraitUrl") or identity.get("avatarUrl")),
            "tokenImageUrl": _safe_str(identity.get("tokenImageUrl")),
            "alignment": _safe_str(identity.get("alignment")),
            "deity": _safe_str(identity.get("deity")),
            "age": _safe_str(identity.get("age")),
            "height": _safe_str(identity.get("height")),
            "weight": _safe_str(identity.get("weight")),
            "eyes": _safe_str(identity.get("eyes")),
            "hair": _safe_str(identity.get("hair")),
            "skin": _safe_str(identity.get("skin")),
            "homeland": _safe_str(identity.get("homeland")),
            "backstory": _safe_str(identity.get("backstory")),
            "personalityTraits": _safe_str(identity.get("personalityTraits")),
            "ideals": _safe_str(identity.get("ideals")),
            "bonds": _safe_str(identity.get("bonds")),
            "flaws": _safe_str(identity.get("flaws")),
            "notes": _safe_str(identity.get("notes")),
        },
        "presentation": {
            "portraitFrame": _safe_str(presentation.get("portraitFrame"), "classic"),
            "tokenDisplay": {
                "scale": max(0, _safe_int(token_display.get("scale"), 1)),
                "cropMode": _safe_str(token_display.get("cropMode"), "cover"),
                "ringStyle": _safe_str(token_display.get("ringStyle"), "classic"),
                "accentColor": _safe_str(token_display.get("accentColor"), "#00e5cc"),
                "labelFormat": _safe_str(token_display.get("labelFormat"), "class_name"),
            },
        },
        "species": {
            "id": _safe_str(species.get("id")),
            "name": _safe_str(species.get("name") or species.get("id")),
            "size": _safe_str(species.get("size"), "medium"),
            "speed": _safe_int(species.get("speed"), 30, minimum=0),
            "traits": list(species.get("traits") or []),
            "senses": list(species.get("senses") or []),
            "resistances": list(species.get("resistances") or []),
            "gameplayBenefits": list(species.get("gameplayBenefits") or []),
            "choices": species.get("choices") if isinstance(species.get("choices"), dict) else {},
            "summary": _safe_str(species.get("summary")),
        },
        "background": {
            "id": _safe_str(background.get("id") or origins.get("backgroundId")),
            "name": _safe_str(background.get("name") or origins.get("backgroundName")),
            "traits": list(background.get("traits") or []),
            "proficiencies": [str(item or "").strip() for item in origins_proficiencies if str(item or "").strip()],
            "tools": list(background.get("tools") or []),
            "languages": [str(item or "").strip() for item in origins_languages if str(item or "").strip()],
            "equipmentPicks": list(background.get("equipmentPicks") or []),
            "featureSummary": _safe_str(background.get("featureSummary")),
        },
        "abilities": {
            "generationMode": _safe_str(raw.get("abilityGenerationMode"), "manual"),
            "scores": {
                "str": _safe_int(scores.get("str"), 10),
                "dex": _safe_int(scores.get("dex"), 10),
                "con": _safe_int(scores.get("con"), 10),
                "int": _safe_int(scores.get("int"), 10),
                "wis": _safe_int(scores.get("wis"), 10),
                "cha": _safe_int(scores.get("cha"), 10),
            },
            "bonuses": abilities.get("bonuses") if isinstance(abilities.get("bonuses"), dict) else {},
            "finalScores": abilities.get("finalScores") if isinstance(abilities.get("finalScores"), dict) else {},
            "sources": abilities.get("sources") if isinstance(abilities.get("sources"), dict) else {},
        },
        "classes": classes,
        "feats": [str(item or "").strip() for item in progression_feats if str(item or "").strip()],
        "talents": [{"talentId": str(item or "").strip()} for item in progression_talents if str(item or "").strip()],
        "awakening": {
            "stage": _safe_int(awakening.get("tier"), 0, minimum=0),
            "pathId": _safe_str(awakening.get("track")),
        },
        "equipment": {
            "currency": {
                "cp": _safe_int(equipment_currency.get("cp"), 0, minimum=0),
                "sp": _safe_int(equipment_currency.get("sp"), 0, minimum=0),
                "ep": _safe_int(equipment_currency.get("ep"), 0, minimum=0),
                "gp": _safe_int(equipment_currency.get("gp"), 0, minimum=0),
                "pp": _safe_int(equipment_currency.get("pp"), 0, minimum=0),
            },
            "inventory": [
                {"name": str(item or "").strip(), "source": "builder_starting_choice"}
                for item in equipment_choices
                if str(item or "").strip()
            ],
            "equipped": {},
            "containers": [],
        },
        "spellState": {
            "known": [str(item or "").strip() for item in spell_known if str(item or "").strip()],
            "prepared": [str(item or "").strip() for item in spell_prepared if str(item or "").strip()],
            "slots": {},
            "focus": {
                "castingMode": spell_mode,
                "spellcastingAbility": _safe_str(spellbook.get("spellcastingAbility"), "").lower()[:20],
                "languages": [str(item or "").strip() for item in origins_languages if str(item or "").strip()],
            },
            "rituals": list(spellbook.get("rituals") or []),
            "spellbookEntries": list(spellbook.get("entries") or []),
            "classSources": list(spellbook.get("classSources") or []),
        },
        "importMeta": import_meta,
    }


def normalize_incoming_document(payload: Any) -> dict:
    """Accept canonical docs or builder draft payloads and normalize to canonical."""
    src = payload if isinstance(payload, dict) else {}
    if isinstance(src.get("character_document"), dict):
        src = src.get("character_document")
    elif isinstance(src.get("document"), dict):
        src = src.get("document")
    elif isinstance(src.get("nativeCharacter"), dict):
        src = src.get("nativeCharacter")

    is_canonical_hint = isinstance(src, dict) and (
        "schema" in src or "spellState" in src or "ruleset" in src
    )
    if is_canonical_hint:
        return validate_or_raise(src)
    return validate_or_raise(_normalize_builder_draft_document(src if isinstance(src, dict) else {}))


def create_character_document(seed: dict | None = None) -> dict:
    """Create a new canonical character document, optionally merged with seed data."""
    doc = default_character_document()
    if seed and isinstance(seed, dict):
        doc.update(seed)
    return ensure_character_defaults(doc)


def normalize_character_document(document: Any) -> dict:
    """Normalize and fill defaults for potentially legacy character payloads."""
    return ensure_character_defaults(document)


def validate_character_document(document: Any) -> dict:
    """Validate canonical character document shape and return normalized payload."""
    return validate_or_raise(document)




def get_builder_rules_catalog() -> dict:
    """Return data-driven starter rules catalog for native character builder UIs."""
    return load_rules_catalog()

def resolve_runtime(document: Any) -> dict:
    """Resolve canonical character runtime, returning both normalized doc and runtime."""
    valid_doc = validate_or_raise(document)
    return resolve_character_runtime(valid_doc)


def to_legacy_character_payload(document: Any) -> dict:
    """Map canonical native character data into current charBook/charSheet consumers.

    This keeps existing systems working while native documents become the long-term
    progression authority.
    """
    resolved = resolve_runtime(document)
    canonical = resolved["document"]
    runtime = resolved["runtime"]

    char_book = map_character_to_charbook(canonical, runtime)
    char_sheet = map_character_to_charsheet(canonical, runtime)

    return {
        "charBook": char_book,
        "charSheet": char_sheet,
        "nativeCharacter": canonical,
        "nativeRuntime": runtime,
        "nativeMeta": {
            "serviceVersion": _NATIVE_SERVICE_VERSION,
            "resolvedAt": time.time(),
        },
    }


def preview_levelup(document: Any) -> dict:
    """Build a server-side preview of the next-level progression state."""
    valid_doc = validate_or_raise(document)
    return build_levelup_preview(valid_doc)


def apply_character_levelup(document: Any, *, choices: Any = None) -> dict:
    """Apply one level increment and return resolved canonical/runtime payloads."""
    valid_doc = validate_or_raise(document)
    return apply_levelup(valid_doc, choices=choices)


def build_profile_library_entry(document: Any, *, profile_id: str = "") -> dict:
    """Build a profile-library-safe entry that preserves legacy compatibility fields."""
    mapped = to_legacy_character_payload(document)
    canonical = mapped["nativeCharacter"]
    identity = canonical.get("identity") if isinstance(canonical.get("identity"), dict) else {}

    return {
        "id": profile_id or identity.get("characterId") or "",
        "name": identity.get("displayName") or identity.get("name") or "",
        "charBook": mapped["charBook"],
        "charSheet": mapped["charSheet"],
        "nativeCharacter": mapped["nativeCharacter"],
        "nativeRuntime": mapped["nativeRuntime"],
        "nativeMeta": mapped["nativeMeta"],
    }


def build_profile_upsert_payload(document: Any, *, profile_id: str = "") -> dict:
    """Build a session-profile payload preserving legacy + native compatibility fields."""
    if isinstance(document, dict):
        document = reconcile_character_spell_state(document)
    entry = build_profile_library_entry(document, profile_id=profile_id)
    level = None
    try:
        level = _safe_int((entry.get("charSheet") or {}).get("totalLevel"), 1, minimum=1)
    except Exception:
        level = None
    source_mode = _safe_str((entry.get("nativeCharacter") or {}).get("sourceMode"), "native").lower()

    return {
        "id": entry.get("id") or "",
        "name": entry.get("name") or "Character",
        "charBook": entry.get("charBook") or {},
        "charSheet": entry.get("charSheet") or {},
        "nativeCharacter": entry.get("nativeCharacter") or {},
        "nativeRuntime": entry.get("nativeRuntime") or {},
        "nativeMeta": entry.get("nativeMeta") or {},
        "sourceMode": source_mode,
        "classSummary": _build_class_summary(entry.get("charSheet") or {}),
        "importMeta": (entry.get("nativeCharacter") or {}).get("importMeta") or {},
        "level": level,
    }
