from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from functools import lru_cache
from typing import Any

from server.character.rules_catalog import get_class_catalog_row, load_rules_catalog
from server.character.spell_text_generator import enrich_spell_row




_SUBCLASS_SPELL_GRANTS: dict[str, dict[str, Any]] = {
    'trickery-domain': {
        'mode': 'prepared',
        'spellsByLevel': {
            1: ['charm-person', 'disguise-self'],
            3: ['pass-without-trace'],
            5: ['blink', 'dispel-magic'],
            7: ['dimension-door', 'polymorph'],
            9: ['dominate-person', 'mislead'],
        },
    },
    'life-domain': {
        'mode': 'prepared',
        'spellsByLevel': {
            1: ['bless', 'cure-wounds'],
            3: ['lesser-restoration'],
            5: ['revivify'],
            7: ['guardian-of-faith'],
            9: ['greater-restoration'],
        },
    },
    'light-domain': {
        'mode': 'prepared',
        'spellsByLevel': {
            1: ['burning-hands', 'faerie-fire'],
            3: ['scorching-ray'],
            5: ['fireball'],
            7: ['guardian-of-faith'],
            9: ['flame-strike'],
        },
    },
    'war-domain': {
        'mode': 'prepared',
        'spellsByLevel': {
            1: ['shield-of-faith'],
            3: ['magic-weapon'],
            5: ['spirit-guardians'],
            7: ['freedom-of-movement'],
            9: ['flame-strike'],
        },
    },
    'oath-of-devotion': {
        'mode': 'prepared',
        'spellsByLevel': {
            3: ['protection-from-evil-and-good', 'sanctuary'],
            5: ['lesser-restoration'],
            9: ['dispel-magic', 'beacon-of-hope'],
            13: ['freedom-of-movement', 'guardian-of-faith'],
            17: ['flame-strike'],
        },
    },
    'archfey-patron': {
        'mode': 'known',
        'spellsByLevel': {
            1: ['faerie-fire', 'sleep'],
            3: ['blink'],
            5: ['plant-growth'],
            7: ['greater-invisibility'],
            9: ['seeming'],
        },
    },
    'fiend-patron': {
        'mode': 'known',
        'spellsByLevel': {
            1: ['burning-hands', 'command'],
            3: ['scorching-ray'],
            5: ['fireball'],
            7: ['fire-shield'],
            9: ['flame-strike'],
        },
    },
    'great-old-one-patron': {
        'mode': 'known',
        'spellsByLevel': {
            1: ['dissonant-whispers', 'hideous-laughter'],
            3: ['detect-thoughts'],
            5: ['clairvoyance'],
            7: ['confusion'],
            9: ['telekinesis'],
        },
    },
    'artillerist': {
        'mode': 'known',
        'spellsByLevel': {
            3: ['burning-hands', 'shield'],
            5: ['scorching-ray', 'shatter'],
            9: ['fireball'],
            13: ['fire-shield'],
            17: ['wall-of-force'],
        },
    },
    'alchemist': {
        'mode': 'known',
        'spellsByLevel': {
            3: ['cure-wounds', 'ray-of-sickness'],
            5: ['enhance-ability', 'lesser-restoration'],
            9: ['gaseous-form', 'revivify'],
            13: ['blight', 'death-ward'],
            17: ['greater-restoration', 'cloudkill'],
        },
    },
    'mechanist': {
        'mode': 'known',
        'spellsByLevel': {
            3: ['find-familiar', 'grease'],
            5: ['arcane-lock', 'magic-weapon'],
            9: ['haste', 'lightning-bolt'],
            13: ['fabricate', 'otilukes-resilient-sphere'],
            17: ['animate-objects', 'telekinesis'],
        },
    },
    'saboteur': {
        'mode': 'known',
        'spellsByLevel': {
            3: ['disguise-self', 'snare'],
            5: ['darkness', 'pass-without-trace'],
            9: ['glyph-of-warding', 'nondetection'],
            13: ['greater-invisibility', 'evards-black-tentacles'],
            17: ['mislead', 'seeming'],
        },
    },
}

_SUBCLASS_CASTER_OVERRIDES: dict[str, dict[str, Any]] = {
    "arcane-trickster": {
        "classId": "rogue",
        "minLevel": 3,
        "spellcastingAbility": "int",
        "castingType": "third",
        "mode": "known",
        "cantripsKnownByLevel": {
            3: 3,
            4: 3,
            5: 3,
            6: 3,
            7: 3,
            8: 3,
            9: 3,
            10: 4,
            11: 4,
            12: 4,
            13: 4,
            14: 4,
            15: 4,
            16: 4,
            17: 4,
            18: 4,
            19: 4,
            20: 4,
        },
        "spellsKnownByLevel": {
            3: 3,
            4: 4,
            5: 4,
            6: 4,
            7: 5,
            8: 6,
            9: 6,
            10: 7,
            11: 8,
            12: 8,
            13: 9,
            14: 10,
            15: 10,
            16: 11,
            17: 11,
            18: 11,
            19: 12,
            20: 13,
        },
        "spellSlotsByLevel": {
            3: {"1st": 2},
            4: {"1st": 3},
            5: {"1st": 3},
            6: {"1st": 3},
            7: {"1st": 4, "2nd": 2},
            8: {"1st": 4, "2nd": 2},
            9: {"1st": 4, "2nd": 2},
            10: {"1st": 4, "2nd": 3},
            11: {"1st": 4, "2nd": 3},
            12: {"1st": 4, "2nd": 3},
            13: {"1st": 4, "2nd": 3, "3rd": 2},
            14: {"1st": 4, "2nd": 3, "3rd": 2},
            15: {"1st": 4, "2nd": 3, "3rd": 2},
            16: {"1st": 4, "2nd": 3, "3rd": 3},
            17: {"1st": 4, "2nd": 3, "3rd": 3},
            18: {"1st": 4, "2nd": 3, "3rd": 3},
            19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
            20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
        },
    }
}

_ORDINAL_TO_NUM = {
    '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5, '6th': 6, '7th': 7, '8th': 8, '9th': 9,
}


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _norm(value: Any) -> str:
    return str(value or '').strip().lower()


def _slug(value: Any) -> str:
    text = re.sub(r'[^a-z0-9]+', '-', _norm(value)).strip('-')
    return text




@lru_cache(maxsize=1)
def _class_spell_list_index() -> dict[str, set[str]]:
    root = Path(__file__).resolve().parents[1] / "data" / "rules" / "5e2024" / "class_spell_lists.json"
    try:
        payload = json.loads(root.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, set[str]] = {}
    if not isinstance(payload, dict):
        return out
    for class_id, buckets in payload.items():
        if not isinstance(buckets, dict):
            continue
        spell_ids: set[str] = set()
        for values in buckets.values():
            if not isinstance(values, list):
                continue
            for spell_id in values:
                sid = _slug(spell_id)
                if sid:
                    spell_ids.add(sid)
        if spell_ids:
            out[_slug(class_id)] = spell_ids
    return out


def _augment_classes_from_class_spell_lists(spell_id: str, classes: list[str]) -> list[str]:
    rows = _class_spell_list_index()
    if not rows:
        return classes
    existing = list(classes)
    seen = {_norm(v) for v in existing}
    catalog = load_rules_catalog()
    class_rows = catalog.get('classes') if isinstance(catalog.get('classes'), list) else []
    for row in class_rows:
        if not isinstance(row, dict):
            continue
        class_id = _slug(row.get('id'))
        if spell_id not in rows.get(class_id, set()):
            continue
        display = str(row.get('displayName') or row.get('name') or class_id).strip()
        if _norm(display) in seen:
            continue
        seen.add(_norm(display))
        existing.append(display)
    return existing


def _resolve_active_subclass_ids(document: dict[str, Any], *, class_id: str) -> list[str]:
    classes = document.get('classes') if isinstance(document.get('classes'), list) else []
    out: list[str] = []
    seen: set[str] = set()
    for row in classes:
        if not isinstance(row, dict):
            continue
        row_class_id = _norm(row.get('classId') or row.get('id') or row.get('name'))
        if class_id and row_class_id != class_id:
            continue
        subclass_id = _norm(row.get('subclassId'))
        if subclass_id and subclass_id not in seen:
            seen.add(subclass_id)
            out.append(subclass_id)
    return out


def _caster_override_for_subclass(class_id: str, class_level: int, subclass_id: str | None) -> dict[str, Any] | None:
    key = _norm(subclass_id)
    row = _SUBCLASS_CASTER_OVERRIDES.get(key) if key else None
    if not isinstance(row, dict):
        return None
    if _norm(row.get("classId")) != _norm(class_id):
        return None
    if class_level < _safe_int(row.get("minLevel"), 1):
        return None
    return row



_STANDARD_MULTICLASS_SPELL_SLOTS: dict[int, dict[str, int]] = {
    1: {"1st": 2},
    2: {"1st": 3},
    3: {"1st": 4, "2nd": 2},
    4: {"1st": 4, "2nd": 3},
    5: {"1st": 4, "2nd": 3, "3rd": 2},
    6: {"1st": 4, "2nd": 3, "3rd": 3},
    7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
    8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
    9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
    10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
    11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
    12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
    13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
    14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
    15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
    16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
    17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 2, "7th": 1, "8th": 1, "9th": 1},
    20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 2, "7th": 2, "8th": 1, "9th": 1},
}


def _dedupe_preserve(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _class_rows_for_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    rows = document.get("classes") if isinstance(document.get("classes"), list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        class_id = _class_name_index().get(_norm(row.get("classId") or row.get("id") or row.get("name")), _slug(row.get("classId") or row.get("id") or row.get("name")))
        if not class_id:
            continue
        subclass_id = _norm(row.get("subclassId") or row.get("subclass"))
        level = max(1, min(20, _safe_int(row.get("level"), 1)))
        catalog = get_class_catalog_row(class_id) or {}
        out.append({
            "classId": class_id,
            "className": str(catalog.get("displayName") or row.get("name") or class_id).strip(),
            "level": level,
            "subclassId": subclass_id,
            "subclassName": str(row.get("subclassName") or row.get("subclass") or "").strip(),
        })
    return out


def _add_spell_source(class_sources: dict[str, list[dict[str, Any]]], spell_id: str, source: dict[str, Any]) -> None:
    if not spell_id:
        return
    bucket = class_sources.setdefault(spell_id, [])
    key = (
        str(source.get("sourceType") or ""),
        str(source.get("classId") or ""),
        str(source.get("subclassId") or ""),
        str(source.get("origin") or ""),
    )
    for existing in bucket:
        if (
            str(existing.get("sourceType") or ""),
            str(existing.get("classId") or ""),
            str(existing.get("subclassId") or ""),
            str(existing.get("origin") or ""),
        ) == key:
            return
    bucket.append(source)


def _spell_id_from_any(value: Any) -> str:
    if isinstance(value, dict):
        raw = value.get("id") or value.get("spellId") or value.get("name") or value.get("displayName")
    else:
        raw = value
    spell = get_spell_by_id(str(raw or ""))
    return str((spell or {}).get("id") or "").strip()


def _extract_extra_spell_sources(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    containers = [
        ("feat", document.get("feats") if isinstance(document.get("feats"), list) else []),
        ("species", [document.get("species")] if isinstance(document.get("species"), dict) else []),
        ("item", ((document.get("equipment") or {}).get("inventory") if isinstance(document.get("equipment"), dict) else []) or []),
    ]
    keys = ("spellIds", "spells", "knownSpells", "preparedSpells", "grantedSpells")
    for source_type, rows in containers:
        for row in rows:
            if not isinstance(row, dict):
                continue
            origin = str(row.get("id") or row.get("name") or source_type).strip()
            for key in keys:
                values = row.get(key) if isinstance(row.get(key), list) else []
                for value in values:
                    spell_id = _spell_id_from_any(value)
                    if spell_id:
                        _add_spell_source(out, spell_id, {"sourceType": source_type, "origin": origin})
    return out


def _spellbook_entry_sources(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    spell_state = document.get("spellState") if isinstance(document.get("spellState"), dict) else {}
    entries = spell_state.get("spellbookEntries") if isinstance(spell_state.get("spellbookEntries"), list) else []
    if not entries:
        entries = document.get("spellbookEntries") if isinstance(document.get("spellbookEntries"), list) else []
    out: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        spell_id = _spell_id_from_any(entry)
        if not spell_id:
            continue
        source_class = _norm((entry or {}).get("classId") or (entry or {}).get("sourceClass") or (entry or {}).get("sourceClassId")) if isinstance(entry, dict) else ""
        source_subclass = _norm((entry or {}).get("subclassId") or (entry or {}).get("sourceSubclass") or (entry or {}).get("sourceSubclassId")) if isinstance(entry, dict) else ""
        _add_spell_source(out, spell_id, {
            "sourceType": "imported_spellbook",
            "classId": source_class,
            "subclassId": source_subclass,
            "origin": str((entry or {}).get("source") or (entry or {}).get("name") or "spellbookEntries").strip() if isinstance(entry, dict) else "spellbookEntries",
        })
    return out


def _highest_spell_level_for_class(class_id: str, class_level: int, subclass_id: str, document: dict[str, Any]) -> int:
    highest = 0
    for spell in get_spell_list():
        unlock = (spell.get("classUnlockLevels") or {}).get(class_id)
        subclass_unlock = _subclass_caster_unlock_for_spell(spell, class_id, class_level, subclass_id)
        if (unlock is not None and class_level >= int(unlock)) or subclass_unlock is not None:
            highest = max(highest, _safe_int(spell.get("level"), 0))
    grants = get_subclass_spell_grants(document, class_id=class_id, class_level=class_level)
    for spell_id in (grants.get("alwaysKnown") or []) + (grants.get("alwaysPrepared") or []):
        spell = get_spell_by_id(spell_id)
        if spell:
            highest = max(highest, _safe_int(spell.get("level"), 0))
    return highest


def _caster_level_contribution(casting_type: str, level: int) -> int:
    ctype = _norm(casting_type)
    if ctype == "full":
        return level
    if ctype == "half":
        return level // 2
    if ctype == "third":
        return level // 3
    return 0




def _subclass_caster_list_class(class_id: str, class_level: int, subclass_id: str | None) -> str:
    override = _caster_override_for_subclass(class_id, class_level, subclass_id)
    if not override:
        return ""
    # Arcane Trickster / Eldritch Knight style subclasses draw from the wizard spell list.
    if _norm(class_id) in {"rogue", "fighter"}:
        return "wizard"
    return ""


def _subclass_caster_unlock_for_spell(spell: dict[str, Any], class_id: str, class_level: int, subclass_id: str | None) -> int | None:
    list_class = _subclass_caster_list_class(class_id, class_level, subclass_id)
    if not list_class:
        return None
    unlock = (spell.get("classUnlockLevels") or {}).get(list_class)
    if unlock is None:
        return None
    if class_level < int(unlock):
        return None
    return int(unlock)

def build_multiclass_spell_context(document: dict[str, Any]) -> dict[str, Any]:
    """Build spell access, slot, and source context across every class row."""
    if not isinstance(document, dict):
        document = {}
    abilities = document.get("abilities") if isinstance(document.get("abilities"), dict) else {}
    class_rows = _class_rows_for_document(document)
    total_level = sum(_safe_int(row.get("level"), 0) for row in class_rows)
    context_classes: list[dict[str, Any]] = []
    class_sources: dict[str, list[dict[str, Any]]] = {}
    caster_level = 0
    pact_magic: dict[str, Any] = {"classes": [], "slots": {}, "highestSlotLevel": 0}

    for row in class_rows:
        class_id = str(row.get("classId") or "")
        class_level = _safe_int(row.get("level"), 1)
        subclass_id = str(row.get("subclassId") or "")
        limits = build_spell_limits_for_class(class_id, class_level, abilities, document=document, subclass_id=subclass_id)
        casting_type = str(limits.get("castingType") or "none")
        if _norm(casting_type) == "pact":
            mechanics = _class_mechanics_for_level(get_class_catalog_row(class_id), class_level)
            pact_slots = _safe_int(mechanics.get("pactSlots"), 0)
            pact_slot_level = _safe_int(mechanics.get("pactSlotLevel"), 0)
            if pact_slots > 0 and pact_slot_level > 0:
                pact_magic["classes"].append({"classId": class_id, "level": class_level, "slots": pact_slots, "slotLevel": pact_slot_level})
                pact_magic["slots"] = {f"{pact_slot_level}{'st' if pact_slot_level == 1 else 'nd' if pact_slot_level == 2 else 'rd' if pact_slot_level == 3 else 'th'}": pact_slots}
                pact_magic["highestSlotLevel"] = max(_safe_int(pact_magic.get("highestSlotLevel"), 0), pact_slot_level)
        else:
            caster_level += _caster_level_contribution(casting_type, class_level)

        highest_unlocked = _highest_spell_level_for_class(class_id, class_level, subclass_id, document)
        class_context = {**row, "limits": limits, "castingType": casting_type, "spellcastingAbility": limits.get("spellcastingAbility") or "", "highestUnlockedSpellLevel": highest_unlocked}
        context_classes.append(class_context)

        for spell in get_spell_list():
            spell_id = str(spell.get("id") or "")
            unlock = (spell.get("classUnlockLevels") or {}).get(class_id)
            if unlock is not None and class_level >= int(unlock):
                _add_spell_source(class_sources, spell_id, {
                    "sourceType": "class",
                    "classId": class_id,
                    "className": row.get("className") or class_id,
                    "subclassId": "",
                    "unlockLevel": int(unlock),
                })
            subclass_unlock = _subclass_caster_unlock_for_spell(spell, class_id, class_level, subclass_id)
            if subclass_unlock is not None:
                _add_spell_source(class_sources, spell_id, {
                    "sourceType": "subclass",
                    "classId": class_id,
                    "className": row.get("className") or class_id,
                    "subclassId": subclass_id,
                    "unlockLevel": subclass_unlock,
                })
        grants = get_subclass_spell_grants(document, class_id=class_id, class_level=class_level)
        for spell_id in (grants.get("alwaysKnown") or []) + (grants.get("alwaysPrepared") or []):
            _add_spell_source(class_sources, spell_id, {
                "sourceType": "subclass",
                "classId": class_id,
                "className": row.get("className") or class_id,
                "subclassId": subclass_id,
                "unlockLevel": None,
            })
        bonus = get_class_bonus_spell_access(document, class_id=class_id, class_level=class_level)
        for spell_id in bonus.get("alwaysKnown") or []:
            _add_spell_source(class_sources, spell_id, {"sourceType": "class_feature", "classId": class_id, "subclassId": "", "unlockLevel": class_level})

    for sources in (_extract_extra_spell_sources(document), _spellbook_entry_sources(document)):
        for spell_id, rows in sources.items():
            for source in rows:
                _add_spell_source(class_sources, spell_id, source)

    caster_level = max(0, min(20, caster_level))
    combined_slots = _clone(_STANDARD_MULTICLASS_SPELL_SLOTS.get(caster_level, {})) if caster_level else {}
    return {
        "classes": context_classes,
        "totalLevel": total_level,
        "casterLevel": caster_level,
        "pactMagic": pact_magic,
        "spellcastingAbilities": {str(row.get("classId") or ""): row.get("spellcastingAbility") or "" for row in context_classes},
        "classSourcesBySpell": class_sources,
        "highestUnlockedSpellLevelByClass": {str(row.get("classId") or ""): row.get("highestUnlockedSpellLevel") or 0 for row in context_classes},
        "spellSlots": combined_slots,
        "highestAvailableSlot": _highest_slot_level_from_limits({"spellSlots": combined_slots}),
    }


def _extract_target(description: str, range_text: str) -> str:
    desc = str(description or '').strip()
    if not desc:
        return ''
    first_sentence = desc.split('.')[0].strip()
    if first_sentence:
        return first_sentence[:180]
    return str(range_text or '').strip()


@lru_cache(maxsize=1)
def get_spell_index() -> dict[str, dict[str, Any]]:
    catalog = load_rules_catalog()
    rows = catalog.get('spells') if isinstance(catalog.get('spells'), list) else []
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        normalized = normalize_spell_entry(row)
        indexed[normalized['id']] = normalized
    return indexed


@lru_cache(maxsize=1)
def get_spell_list() -> list[dict[str, Any]]:
    return list(get_spell_index().values())


@lru_cache(maxsize=1)
def _class_name_index() -> dict[str, str]:
    catalog = load_rules_catalog()
    out: dict[str, str] = {}
    for row in catalog.get('classes') or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get('id') or '').strip().lower()
        cname = str(row.get('displayName') or row.get('name') or cid).strip()
        if cid:
            out[cid] = cid
            out[_norm(cname)] = cid
    return out


def _parse_level_from_slot_key(slot_key: str) -> int:
    cleaned = str(slot_key or '').strip().lower()
    if cleaned in _ORDINAL_TO_NUM:
        return _ORDINAL_TO_NUM[cleaned]
    match = re.search(r'(\d+)', cleaned)
    return int(match.group(1)) if match else 0


def get_class_spell_unlock_level(class_id: str, spell_level: int) -> int | None:
    row = get_class_catalog_row(class_id)
    if not isinstance(row, dict):
        return None
    if spell_level <= 0:
        if _norm(row.get('spellcastingType')) != 'none' or row.get('spellcastingAbility'):
            return 1
        return None
    slots = row.get('spellSlots') if isinstance(row.get('spellSlots'), dict) else {}
    for lvl in range(1, 21):
        level_slots = slots.get(str(lvl)) if isinstance(slots.get(str(lvl)), dict) else {}
        for slot_key in level_slots.keys():
            if _parse_level_from_slot_key(slot_key) >= spell_level:
                return lvl
    return None


def _build_roll_config(raw: dict[str, Any], normalized_id: str) -> dict[str, Any]:
    attack_type = str(raw.get('attackType') or '').strip()
    save_type = str(raw.get('savingThrow') or '').strip()
    damage_formula = str(raw.get('damageFormula') or '').strip()
    healing_formula = str(raw.get('healingFormula') or '').strip()
    return {
        'id': f'cast:{normalized_id}',
        'label': 'Cast',
        'action': 'cast_spell',
        'spellId': normalized_id,
        'hasAttackRoll': bool(attack_type),
        'hasSave': bool(save_type),
        'saveType': save_type,
        'attackType': attack_type,
        'damageFormula': damage_formula,
        'healingFormula': healing_formula,
    }


def normalize_spell_entry(raw: dict[str, Any]) -> dict[str, Any]:
    raw = enrich_spell_row(raw)
    spell_id = str(raw.get('id') or '').strip() or _slug(raw.get('displayName') or raw.get('name') or 'spell')
    level = _safe_int(raw.get('level'), 0)
    description = str(raw.get('description') or raw.get('desc') or '').strip()
    damage_formula = str(raw.get('damageFormula') or '').strip()
    healing_formula = str(raw.get('healingFormula') or '').strip()
    scaling_note = str(raw.get('scalingNote') or raw.get('higher_levels') or raw.get('atHigherLevels') or '').strip()
    classes = [str(item).strip() for item in (raw.get('classes') or []) if str(item).strip()]
    classes = _augment_classes_from_class_spell_lists(spell_id, classes)
    class_unlocks = {}
    name_index = _class_name_index()
    for class_name in classes:
        class_key = name_index.get(_norm(class_name), _slug(class_name))
        unlock = get_class_spell_unlock_level(class_key, level)
        if unlock is not None:
            class_unlocks[class_key] = unlock
    tags = [str(tag).strip().lower() for tag in (raw.get('tags') or []) if str(tag).strip()]
    if raw.get('ritual') and 'ritual' not in tags:
        tags.append('ritual')
    if raw.get('concentration') and 'concentration' not in tags:
        tags.append('concentration')
    if level == 0 and 'cantrip' not in tags:
        tags.append('cantrip')
    if raw.get('school'):
        school_tag = _slug(raw.get('school'))
        if school_tag not in tags:
            tags.append(school_tag)
    if raw.get('damageType'):
        damage_tag = _slug(raw.get('damageType'))
        if damage_tag not in tags:
            tags.append(damage_tag)
    if raw.get('savingThrow') and 'save' not in tags:
        tags.append('save')
    if raw.get('attackType') and 'attack-roll' not in tags:
        tags.append('attack-roll')
    summary_bits = [
        f"{('Cantrip' if level == 0 else f'Level {level}')} {str(raw.get('school') or 'Spell').strip()}".strip(),
        str(raw.get('castingTime') or '').strip(),
        str(raw.get('range') or '').strip(),
    ]
    summary = ' • '.join([bit for bit in summary_bits if bit])
    out = {
        'id': spell_id,
        'name': str(raw.get('displayName') or raw.get('name') or spell_id).strip(),
        'displayName': str(raw.get('displayName') or raw.get('name') or spell_id).strip(),
        'classList': classes,
        'classes': classes,
        'school': str(raw.get('school') or '').strip(),
        'spellLevel': level,
        'level': level,
        'castTime': str(raw.get('castingTime') or '').strip(),
        'castingTime': str(raw.get('castingTime') or '').strip(),
        'range': str(raw.get('range') or '').strip(),
        'components': str(raw.get('components') or '').strip(),
        'duration': str(raw.get('duration') or '').strip(),
        'concentration': bool(raw.get('concentration')),
        'ritual': bool(raw.get('ritual')),
        'target': _extract_target(description, raw.get('range')),
        'attackOrSaveType': str(raw.get('attackType') or raw.get('savingThrow') or '').strip(),
        'attackType': str(raw.get('attackType') or '').strip(),
        'savingThrow': str(raw.get('savingThrow') or '').strip(),
        'damageFormula': damage_formula,
        'damageType': str(raw.get('damageType') or '').strip(),
        'healingFormula': healing_formula,
        'scalingRules': {'summary': scaling_note} if scaling_note else {},
        'upcastingRules': {'summary': scaling_note} if scaling_note else {},
        'conditionsApplied': list(raw.get('conditionsApplied') or []),
        'actionType': 'action',
        'resourceUsage': {'kind': 'spell_slot', 'slotLevel': level} if level > 0 else {'kind': 'cantrip'},
        'tags': tags,
        'effect': str(raw.get('effect') or raw.get('playerFacingEffectSummary') or '').strip(),
        'playerFacingEffectSummary': str(raw.get('playerFacingEffectSummary') or raw.get('effect') or '').strip(),
        'areaText': str(raw.get('areaText') or '').strip(),
        'shortPlayerSummary': summary,
        'fullPlayerDetailText': description,
        'description': description,
        'rollButtonConfig': _build_roll_config(raw, spell_id),
        'cardUiMeta': {
            'accent': 'teal' if raw.get('concentration') else 'violet' if raw.get('ritual') else 'gold',
            'badges': [t for t in ['Concentration' if raw.get('concentration') else '', 'Ritual' if raw.get('ritual') else ''] if t],
            'showDamageChip': bool(damage_formula or raw.get('damageType')),
        },
        'classUnlockLevels': class_unlocks,
    }
    return out


def get_spell_by_id(spell_id: str) -> dict[str, Any] | None:
    raw_id = str(spell_id or '').strip()
    if not raw_id:
        return None
    index = get_spell_index()
    found = index.get(raw_id)
    if found is None:
        found = index.get(_slug(raw_id))
    if found is None and raw_id.lower().startswith('spell-'):
        found = index.get(_slug(raw_id[6:]))
    if found is None and raw_id.lower().startswith('spell_'):
        found = index.get(_slug(raw_id[6:]))
    return _clone(found) if found is not None else None


def list_spells(*, level: int | None = None, school: str | None = None, cls: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    rows = get_spell_list()
    if level is not None:
        rows = [row for row in rows if _safe_int(row.get('level'), -1) == int(level)]
    if school:
        s = _norm(school)
        rows = [row for row in rows if _norm(row.get('school')) == s]
    if cls:
        class_key = _class_name_index().get(_norm(cls), _slug(cls))
        rows = [row for row in rows if class_key in row.get('classUnlockLevels', {}) or any(_norm(v) == _norm(cls) for v in (row.get('classes') or []))]
    if search:
        q = _norm(search)
        rows = [row for row in rows if q in ' '.join([
            _norm(row.get('name')),
            _norm(row.get('school')),
            _norm(row.get('description')),
            _norm(row.get('damageType')),
            _norm(row.get('damageFormula')),
        ])]
    return [_clone(row) for row in rows]


def _ability_modifier(score: Any) -> int:
    try:
        value = int(score)
    except Exception:
        value = 10
    return (value - 10) // 2


def _class_mechanics_for_level(class_row: dict[str, Any] | None, level: int) -> dict[str, Any]:
    if not isinstance(class_row, dict):
        return {}
    table = class_row.get('progressionTable') if isinstance(class_row.get('progressionTable'), list) else []
    for row in table:
        if not isinstance(row, dict):
            continue
        if _safe_int(row.get('level'), 0) == level:
            mechanics = row.get('classMechanics') if isinstance(row.get('classMechanics'), dict) else {}
            return mechanics
    return {}


def build_spell_limits_for_class(
    class_id: str,
    class_level: int,
    abilities: dict[str, Any] | None = None,
    *,
    document: dict[str, Any] | None = None,
    subclass_id: str | None = None,
) -> dict[str, Any]:
    class_row = get_class_catalog_row(class_id)
    mechanics = _class_mechanics_for_level(class_row, class_level)
    abilities = abilities if isinstance(abilities, dict) else {}
    scores = abilities.get('scores') if isinstance(abilities.get('scores'), dict) else abilities
    active_subclass_id = _norm(subclass_id)
    if not active_subclass_id and isinstance(document, dict):
        active_subclasses = _resolve_active_subclass_ids(document, class_id=class_id)
        active_subclass_id = active_subclasses[0] if active_subclasses else ""
    caster_override = _caster_override_for_subclass(class_id, class_level, active_subclass_id)

    spell_ability = _norm((caster_override or {}).get("spellcastingAbility") or (class_row or {}).get('spellcastingAbility'))
    ability_mod = _ability_modifier(scores.get(spell_ability, 10)) if spell_ability else 0
    cantrips_known = (caster_override or {}).get("cantripsKnownByLevel", {}).get(class_level, mechanics.get('cantripsKnown'))
    spells_known = (caster_override or {}).get("spellsKnownByLevel", {}).get(class_level, mechanics.get('spellsKnown'))
    formula = str(mechanics.get('spellsPreparedFormula') or '').strip().lower()
    prepared_limit = None
    if formula:
        prepared_limit = max(1, ability_mod + max(1, class_level))
    spell_slots = _clone(((class_row or {}).get('spellSlots') or {}).get(str(class_level), {}))
    if caster_override:
        spell_slots = _clone((caster_override.get("spellSlotsByLevel") or {}).get(class_level, {}))
    return {
        'classId': class_id,
        'className': str((class_row or {}).get('displayName') or class_id).strip(),
        'level': class_level,
        'castingType': str((caster_override or {}).get("castingType") or (class_row or {}).get('spellcastingType') or 'none').strip(),
        'spellcastingAbility': spell_ability,
        'cantripsKnown': _safe_int(cantrips_known, 0) if cantrips_known is not None else None,
        'spellsKnown': _safe_int(spells_known, 0) if spells_known is not None else None,
        'preparedLimit': prepared_limit,
        'spellSlots': spell_slots,
        'sourceSubclassId': active_subclass_id if caster_override else '',
    }




def _infer_spell_ids_from_spellbook_entries(document: dict[str, Any], *, class_id: str, class_level: int) -> tuple[list[str], list[str]]:
    spell_state = document.get("spellState") if isinstance(document.get("spellState"), dict) else {}
    entries = spell_state.get("spellbookEntries") if isinstance(spell_state.get("spellbookEntries"), list) else []
    if not entries:
        entries = document.get("spellbookEntries") if isinstance(document.get("spellbookEntries"), list) else []
    if not entries:
        return [], []

    limits = build_spell_limits_for_class(class_id, class_level, document.get("abilities") if isinstance(document.get("abilities"), dict) else {})
    mode = "prepared" if limits.get("preparedLimit") is not None else ("known" if limits.get("spellsKnown") is not None else "library")

    resolved: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        name = ''
        if isinstance(entry, dict):
            name = str(entry.get("id") or entry.get("name") or entry.get("displayName") or '').strip()
        else:
            name = str(entry or '').strip()
        if not name:
            continue
        spell = get_spell_by_id(name) or get_spell_by_id(_slug(name))
        if not spell:
            continue
        spell_id = str(spell.get("id") or '').strip()
        if not spell_id or spell_id in seen:
            continue
        unlock = (spell.get("classUnlockLevels") or {}).get(class_id)
        if unlock is None or class_level < int(unlock):
            continue
        seen.add(spell_id)
        resolved.append(spell_id)

    if not resolved:
        return [], []

    known: list[str] = []
    prepared: list[str] = []
    for spell_id in resolved:
        spell = get_spell_by_id(spell_id)
        if not spell:
            continue
        level = _safe_int(spell.get("level"), 0)
        if level <= 0:
            known.append(spell_id)
        elif mode == "prepared":
            prepared.append(spell_id)
        else:
            known.append(spell_id)
    return known, prepared


def get_effective_document_spell_state(document: dict[str, Any], *, class_id: str, class_level: int) -> dict[str, list[str]]:
    spell_state = document.get('spellState') if isinstance(document.get('spellState'), dict) else {}
    known = [str(v or '').strip() for v in (spell_state.get('known') or []) if str(v or '').strip()]
    prepared = [str(v or '').strip() for v in (spell_state.get('prepared') or []) if str(v or '').strip()]
    grants = get_subclass_spell_grants(document, class_id=class_id, class_level=class_level)
    fallback_known, fallback_prepared = _infer_spell_ids_from_spellbook_entries(document, class_id=class_id, class_level=class_level)
    merged_known = _dedupe_preserve(list(known) + list(fallback_known))
    merged_prepared = _dedupe_preserve(list(prepared) + list(fallback_prepared))
    for spell_id in grants.get('alwaysKnown') or []:
        if spell_id not in merged_known:
            merged_known.append(spell_id)
    for spell_id in grants.get('alwaysPrepared') or []:
        if spell_id not in merged_prepared:
            merged_prepared.append(spell_id)
    return {'known': _clone(merged_known), 'prepared': _clone(merged_prepared)}



def get_subclass_spell_grants(document: dict[str, Any], *, class_id: str, class_level: int) -> dict[str, Any]:
    subclass_ids = _resolve_active_subclass_ids(document, class_id=class_id)
    prepared: list[str] = []
    known: list[str] = []
    unlocked_now: list[dict[str, Any]] = []
    seen_prepared: set[str] = set()
    seen_known: set[str] = set()
    for subclass_id in subclass_ids:
        config = _SUBCLASS_SPELL_GRANTS.get(subclass_id) if subclass_id else None
        if not isinstance(config, dict):
            continue
        mode = str(config.get('mode') or 'prepared').strip().lower()
        levels = config.get('spellsByLevel') if isinstance(config.get('spellsByLevel'), dict) else {}
        for raw_unlock, spell_ids in levels.items():
            unlock_level = _safe_int(raw_unlock, 0)
            if unlock_level <= 0 or class_level < unlock_level:
                continue
            unlocked_spell_rows: list[dict[str, Any]] = []
            for raw_spell_id in spell_ids if isinstance(spell_ids, list) else []:
                spell = get_spell_by_id(raw_spell_id)
                if not spell:
                    continue
                spell_id = str(spell.get('id') or '').strip()
                if not spell_id:
                    continue
                target_seen = seen_known if mode == 'known' else seen_prepared
                target_list = known if mode == 'known' else prepared
                if spell_id not in target_seen:
                    target_seen.add(spell_id)
                    target_list.append(spell_id)
                unlocked_spell_rows.append({
                    'id': spell_id,
                    'name': str(spell.get('name') or spell_id).strip(),
                    'level': _safe_int(spell.get('level'), 0),
                })
            if unlocked_spell_rows:
                unlocked_now.append({
                    'subclassId': subclass_id,
                    'mode': mode,
                    'unlockLevel': unlock_level,
                    'spells': unlocked_spell_rows,
                })
    return {
        'subclassIds': subclass_ids,
        'alwaysPrepared': prepared,
        'alwaysKnown': known,
        'unlockedSpells': unlocked_now,
    }


def get_class_bonus_spell_access(document: dict[str, Any], *, class_id: str, class_level: int) -> dict[str, Any]:
    class_key = _norm(class_id)
    if class_key != 'bard':
        return {'alwaysKnown': [], 'unlockedSpells': []}
    spell_state = document.get('spellState') if isinstance(document.get('spellState'), dict) else {}
    magical_known = spell_state.get('magicalSecretsKnown') if isinstance(spell_state.get('magicalSecretsKnown'), list) else []
    known: list[str] = []
    unlocked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spell_id in magical_known:
        spell_id = str(spell_id or '').strip()
        if not spell_id:
            continue
        spell = get_spell_by_id(spell_id)
        if not spell:
            continue
        canonical_id = str(spell.get('id') or '').strip()
        if not canonical_id or canonical_id in seen:
            continue
        seen.add(canonical_id)
        known.append(canonical_id)
        unlocked.append(
            {
                'featureId': 'bard-magical-secrets',
                'unlockLevel': class_level,
                'spells': [{'id': canonical_id, 'name': str(spell.get('name') or canonical_id).strip(), 'level': _safe_int(spell.get('level'), 0)}],
            }
        )
    return {'alwaysKnown': known, 'unlockedSpells': unlocked}

def _highest_slot_level_from_limits(limits: dict[str, Any] | None) -> int:
    if not isinstance(limits, dict):
        return 0
    slot_map = limits.get('spellSlots') if isinstance(limits.get('spellSlots'), dict) else {}
    highest = 0
    for key, amount in slot_map.items():
        if _safe_int(amount, 0) <= 0:
            continue
        parsed = _parse_level_from_slot_key(str(key or ''))
        if parsed > highest:
            highest = parsed
    return highest



def _is_multiclass_document(document: dict[str, Any] | None) -> bool:
    return isinstance(document, dict) and len(_class_rows_for_document(document)) > 1


def _validate_spell_selection_multiclass(*, abilities: dict[str, Any] | None, known: list[str], prepared: list[str], document: dict[str, Any]) -> dict[str, Any]:
    context = build_multiclass_spell_context(document)
    known_ids = _dedupe_preserve([str(v or '').strip() for v in known if str(v or '').strip()])
    prepared_ids = _dedupe_preserve([str(v or '').strip() for v in prepared if str(v or '').strip()])
    source_map = context.get("classSourcesBySpell") if isinstance(context.get("classSourcesBySpell"), dict) else {}
    errors: list[str] = []
    warnings: list[str] = []
    allowed_known: list[str] = []
    allowed_prepared: list[str] = []
    always_known: set[str] = set()
    always_prepared: set[str] = set()
    subclass_grants = {"subclassIds": [], "alwaysPrepared": [], "alwaysKnown": [], "unlockedSpells": []}
    class_bonus = {"alwaysKnown": [], "unlockedSpells": []}

    for cls in context.get("classes") or []:
        class_id = str(cls.get("classId") or "")
        class_level = _safe_int(cls.get("level"), 1)
        grants = get_subclass_spell_grants(document, class_id=class_id, class_level=class_level)
        subclass_grants["subclassIds"].extend(grants.get("subclassIds") or [])
        subclass_grants["alwaysPrepared"].extend(grants.get("alwaysPrepared") or [])
        subclass_grants["alwaysKnown"].extend(grants.get("alwaysKnown") or [])
        subclass_grants["unlockedSpells"].extend(grants.get("unlockedSpells") or [])
        always_prepared.update(grants.get("alwaysPrepared") or [])
        always_known.update(grants.get("alwaysKnown") or [])
        bonus = get_class_bonus_spell_access(document, class_id=class_id, class_level=class_level)
        class_bonus["alwaysKnown"].extend(bonus.get("alwaysKnown") or [])
        class_bonus["unlockedSpells"].extend(bonus.get("unlockedSpells") or [])
        always_known.update(bonus.get("alwaysKnown") or [])

    for spell_id in known_ids:
        spell = get_spell_by_id(spell_id)
        if not spell:
            warnings.append(f'Unknown spell id kept out of known list: {spell_id}')
            continue
        if spell_id not in source_map and spell_id not in always_known and spell_id not in always_prepared:
            errors.append(f"{spell.get('name')} is not unlocked by any current class, subclass, feat, species, item, or imported spellbook source.")
            continue
        allowed_known.append(spell_id)
    known_set = set(allowed_known)
    for spell_id in prepared_ids:
        spell = get_spell_by_id(spell_id)
        if not spell:
            warnings.append(f'Unknown spell id kept out of prepared list: {spell_id}')
            continue
        if _safe_int(spell.get('level'), 0) == 0:
            errors.append(f"{spell.get('name')} is a cantrip and should stay in known spells, not prepared spells.")
            continue
        if spell_id not in source_map and spell_id not in always_prepared and spell_id not in known_set:
            errors.append(f"{spell.get('name')} is not unlocked by any current class, subclass, feat, species, item, or imported spellbook source.")
            continue
        allowed_prepared.append(spell_id)
    for spell_id in sorted(always_known):
        if spell_id not in allowed_known:
            allowed_known.append(spell_id)
    for spell_id in sorted(always_prepared):
        if spell_id not in allowed_prepared:
            allowed_prepared.append(spell_id)
    subclass_grants["subclassIds"] = _dedupe_preserve(subclass_grants["subclassIds"])
    subclass_grants["alwaysPrepared"] = _dedupe_preserve(subclass_grants["alwaysPrepared"])
    subclass_grants["alwaysKnown"] = _dedupe_preserve(subclass_grants["alwaysKnown"])
    class_bonus["alwaysKnown"] = _dedupe_preserve(class_bonus["alwaysKnown"])
    return {
        'ok': not errors,
        'errors': errors,
        'warnings': warnings,
        'limits': {'classId': 'multiclass', 'level': context.get('totalLevel') or 0, 'castingType': 'multiclass', 'spellSlots': context.get('spellSlots') or {}, 'pactMagic': context.get('pactMagic') or {}, 'classes': context.get('classes') or {}},
        'known': allowed_known,
        'prepared': allowed_prepared,
        'subclassGrants': subclass_grants,
        'classBonusGrants': class_bonus,
        'multiclassContext': context,
    }

def validate_spell_selection(*, class_id: str, class_level: int, abilities: dict[str, Any] | None, known: list[str], prepared: list[str], document: dict[str, Any] | None = None, subclass_id: str | None = None) -> dict[str, Any]:
    if _is_multiclass_document(document):
        return _validate_spell_selection_multiclass(abilities=abilities, known=known, prepared=prepared, document=document or {})
    limits = build_spell_limits_for_class(class_id, class_level, abilities, document=document, subclass_id=subclass_id)
    known_ids = [str(v or '').strip() for v in known if str(v or '').strip()]
    prepared_ids = [str(v or '').strip() for v in prepared if str(v or '').strip()]
    known_cantrips = 0
    known_levelled = 0
    errors: list[str] = []
    warnings: list[str] = []
    allowed_known: list[str] = []
    allowed_prepared: list[str] = []
    subclass_grants = get_subclass_spell_grants(document or {'classes': ([{'classId': class_id, 'subclassId': subclass_id}] if subclass_id else [])}, class_id=class_id, class_level=class_level)
    class_bonus = get_class_bonus_spell_access(document or {'classes': []}, class_id=class_id, class_level=class_level)
    always_prepared = set(subclass_grants.get('alwaysPrepared') or [])
    always_known = set(subclass_grants.get('alwaysKnown') or []) | set(class_bonus.get('alwaysKnown') or [])
    bonus_access = always_prepared | always_known
    for spell_id in known_ids:
        spell = get_spell_by_id(spell_id)
        if not spell:
            warnings.append(f'Unknown spell id kept in known list: {spell_id}')
            continue
        unlock = (spell.get('classUnlockLevels') or {}).get(class_id)
        subclass_unlock = _subclass_caster_unlock_for_spell(spell, class_id, class_level, subclass_id)
        has_bonus_access = spell_id in bonus_access or subclass_unlock is not None
        if unlock is None and not has_bonus_access:
            errors.append(f"{spell.get('name')} is not on the {limits.get('className') or class_id} list.")
            continue
        if unlock is not None and class_level < int(unlock) and subclass_unlock is None:
            errors.append(f"{spell.get('name')} unlocks at level {unlock} for {limits.get('className') or class_id}.")
            continue
        allowed_known.append(spell_id)
        if spell_id in always_known:
            continue
        if _safe_int(spell.get('level'), 0) == 0:
            known_cantrips += 1
        else:
            known_levelled += 1
    cantrip_limit = limits.get('cantripsKnown')
    if cantrip_limit is not None and known_cantrips > int(cantrip_limit):
        errors.append(f'Cantrip limit exceeded ({known_cantrips}/{cantrip_limit}).')
    known_limit = limits.get('spellsKnown')
    if known_limit is not None and known_levelled > int(known_limit):
        errors.append(f'Spells known limit exceeded ({known_levelled}/{known_limit}).')
    known_set = set(allowed_known)
    for spell_id in prepared_ids:
        spell = get_spell_by_id(spell_id)
        if not spell:
            warnings.append(f'Unknown spell id kept out of prepared list: {spell_id}')
            continue
        if spell_id not in known_set and limits.get('preparedLimit') is None:
            errors.append(f"{spell.get('name')} cannot be prepared because it is not known.")
            continue
        unlock = (spell.get('classUnlockLevels') or {}).get(class_id)
        subclass_unlock = _subclass_caster_unlock_for_spell(spell, class_id, class_level, subclass_id)
        has_bonus_access = spell_id in bonus_access or subclass_unlock is not None
        if unlock is None and not has_bonus_access:
            errors.append(f"{spell.get('name')} is not on the {limits.get('className') or class_id} list.")
            continue
        if unlock is not None and class_level < int(unlock) and subclass_unlock is None:
            errors.append(f"{spell.get('name')} unlocks at level {unlock} for {limits.get('className') or class_id}.")
            continue
        if _safe_int(spell.get('level'), 0) == 0:
            errors.append(f"{spell.get('name')} is a cantrip and should stay in known spells, not prepared spells.")
            continue
        allowed_prepared.append(spell_id)
    for spell_id in sorted(always_known):
        if spell_id not in allowed_known:
            allowed_known.append(spell_id)
    for spell_id in sorted(always_prepared):
        if spell_id not in allowed_prepared:
            allowed_prepared.append(spell_id)
    prepared_limit = limits.get('preparedLimit')
    counted_prepared = [spell_id for spell_id in allowed_prepared if spell_id not in always_prepared]
    if prepared_limit is not None and len(counted_prepared) > int(prepared_limit):
        errors.append(f'Prepared spell limit exceeded ({len(counted_prepared)}/{prepared_limit}).')
    return {
        'ok': not errors,
        'errors': errors,
        'warnings': warnings,
        'limits': limits,
        'known': allowed_known,
        'prepared': allowed_prepared,
        'subclassGrants': subclass_grants,
        'classBonusGrants': class_bonus,
    }


def repair_spell_state_for_document(
    document: dict[str, Any],
    *,
    class_id: str,
    class_level: int,
    abilities: dict[str, Any] | None = None,
    subclass_id: str | None = None,
) -> dict[str, Any]:
    """Repair polluted spellState lists against strict class/level validation.

    Keeps validator strict and removes stale illegal spell entries from
    known/prepared lists so old UI corruption does not block progression flows.
    """
    if not isinstance(document, dict):
        return {
            "changed": False,
            "known": [],
            "prepared": [],
            "removedKnown": [],
            "removedPrepared": [],
            "validation": {
                "ok": True,
                "errors": [],
                "warnings": [],
                "known": [],
                "prepared": [],
            },
        }

    spell_state = document.get("spellState") if isinstance(document.get("spellState"), dict) else {}
    if not spell_state:
        spell_state = {}
        document["spellState"] = spell_state

    raw_known = []
    seen_known: set[str] = set()
    for row in spell_state.get("known") if isinstance(spell_state.get("known"), list) else []:
        spell_id = str(row or "").strip()
        if not spell_id or spell_id in seen_known:
            continue
        seen_known.add(spell_id)
        raw_known.append(spell_id)

    raw_prepared = []
    seen_prepared: set[str] = set()
    for row in spell_state.get("prepared") if isinstance(spell_state.get("prepared"), list) else []:
        spell_id = str(row or "").strip()
        if not spell_id or spell_id in seen_prepared:
            continue
        seen_prepared.add(spell_id)
        raw_prepared.append(spell_id)

    validation = validate_spell_selection(
        class_id=class_id,
        class_level=class_level,
        abilities=abilities if isinstance(abilities, dict) else {},
        known=raw_known,
        prepared=raw_prepared,
        document=document,
        subclass_id=subclass_id,
    )
    known = list(validation.get("known") or [])
    prepared = list(validation.get("prepared") or [])
    removed_known = [spell_id for spell_id in raw_known if spell_id not in set(known)]
    removed_prepared = [spell_id for spell_id in raw_prepared if spell_id not in set(prepared)]

    changed = (raw_known != known) or (raw_prepared != prepared)
    if changed:
        spell_state["known"] = known
        spell_state["prepared"] = prepared
        document["spellState"] = spell_state

    return {
        "changed": changed,
        "known": known,
        "prepared": prepared,
        "removedKnown": removed_known,
        "removedPrepared": removed_prepared,
        "validation": validation,
    }




_DICE_FORMULA_RE = re.compile(r"\b\d+d\d+(?:\s*[+\-]\s*\d+)?\b", re.IGNORECASE)


def _first_spell_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ''


def _first_spell_bool(row: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if isinstance(value, str):
            if value.strip().lower() in {'true', 'yes', 'y', '1', 'prepared', 'known'}:
                return True
            if value.strip().lower() in {'false', 'no', 'n', '0', 'none'}:
                return False
        return bool(value)
    return False


def _imported_spell_level(row: dict[str, Any]) -> int:
    raw = row.get('level') if row.get('level') is not None else row.get('spellLevel')
    if raw is None:
        raw = row.get('section')
    if isinstance(raw, str):
        lower = raw.strip().lower()
        if 'cantrip' in lower:
            return 0
        match = re.search(r"\b([1-9])(?:st|nd|rd|th)?\b", lower)
        if match:
            return _safe_int(match.group(1), 0)
    return _safe_int(raw, 0)


def _normalize_imported_attack_type(value: Any) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    lower = text.lower()
    if lower in {'1', 'melee', 'melee spell', 'melee spell attack'}:
        return 'Melee spell attack'
    if lower in {'2', 'ranged', 'ranged spell', 'ranged spell attack'}:
        return 'Ranged spell attack'
    if 'attack' not in lower and lower in {'spell', 'melee spell', 'ranged spell'}:
        return text + ' attack'
    return text


def _normalize_imported_save_ability(value: Any) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    lower = text.lower()
    aliases = {
        '1': 'str', 'strength': 'str', 'str': 'str',
        '2': 'dex', 'dexterity': 'dex', 'dex': 'dex',
        '3': 'con', 'constitution': 'con', 'con': 'con',
        '4': 'int', 'intelligence': 'int', 'int': 'int',
        '5': 'wis', 'wisdom': 'wis', 'wis': 'wis',
        '6': 'cha', 'charisma': 'cha', 'cha': 'cha',
    }
    return aliases.get(lower, text)


def _extract_imported_formula(row: dict[str, Any], *, healing: bool = False) -> str:
    keys = (
        ('healingFormula', 'healing_formula', 'healFormula', 'healing', 'heal')
        if healing else
        ('damageFormula', 'damage_formula', 'damageDice', 'damage_dice', 'damage', 'formula')
    )
    text = _first_spell_text(row, *keys)
    if not text:
        return ''
    match = _DICE_FORMULA_RE.search(text)
    return match.group(0).replace(' ', '') if match else text.strip()


def build_imported_spell_fallback_card(imported_spell: dict[str, Any], character_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a playable spell card from preserved imported spell metadata.

    This intentionally uses only the import row and character math context. It does not
    scrape or synthesize native compendium text for spells that failed native matching.
    """
    row = imported_spell if isinstance(imported_spell, dict) else {}
    ctx = character_context if isinstance(character_context, dict) else {}
    name = _first_spell_text(row, 'name', 'displayName', 'spellName') or 'Imported Spell'
    spell_id = _first_spell_text(row, 'id', 'spellId', 'spell_id') or _slug(name)
    level = _imported_spell_level(row)
    description = _first_spell_text(
        row,
        'description', 'notes', 'summary', 'snippet', 'shortDescription', 'fullPlayerDetailText', 'effect', 'playerFacingEffectSummary'
    )
    damage_formula = _extract_imported_formula(row)
    healing_formula = _extract_imported_formula(row, healing=True)
    damage_type = _first_spell_text(row, 'damageType', 'damage_type')
    attack_type = _normalize_imported_attack_type(_first_spell_text(row, 'attackType', 'attack_type'))
    save_ability = _normalize_imported_save_ability(_first_spell_text(row, 'saveAbility', 'save_ability', 'savingThrow', 'save'))
    prepared = bool(ctx.get('isPrepared') or _first_spell_bool(row, 'prepared', 'isPrepared', 'alwaysPrepared'))
    known = bool(ctx.get('isKnown') or prepared or row.get('known') is not False)
    highest_available_slot = _safe_int(ctx.get('highestAvailableSlot'), 0)
    max_level = highest_available_slot if highest_available_slot >= level else level
    available_cast_levels = list(range(level, max_level + 1)) if level > 0 else []
    formula = damage_formula or healing_formula
    badges = ['Imported-only', 'Needs DM review']
    if formula and _DICE_FORMULA_RE.search(formula):
        badges.append('Rollable')
    summary_bits = [
        'Cantrip' if level == 0 else f'Level {level}',
        _first_spell_text(row, 'school'),
        _first_spell_text(row, 'castingTime', 'casting_time', 'castTime', 'time'),
        _first_spell_text(row, 'range'),
    ]
    summary = ' • '.join(bit for bit in summary_bits if bit)
    if description:
        effect = description
    elif formula and damage_type:
        effect = f'{formula} {damage_type}'
    elif formula:
        effect = formula
    else:
        effect = 'Imported spell metadata preserved. Needs DM review before automation.'
    roll_config = {
        'id': f'cast:{spell_id}',
        'label': 'Cast',
        'action': 'cast_spell',
        'spellId': spell_id,
        'hasAttackRoll': bool(attack_type),
        'hasSave': bool(save_ability),
        'saveType': save_ability,
        'attackType': attack_type,
        'damageFormula': damage_formula,
        'healingFormula': healing_formula,
    }
    return {
        'id': spell_id,
        'spellId': spell_id,
        'name': name,
        'displayName': name,
        'level': level,
        'spellLevel': level,
        'school': _first_spell_text(row, 'school'),
        'castingTime': _first_spell_text(row, 'castingTime', 'casting_time', 'castTime', 'time'),
        'range': _first_spell_text(row, 'range'),
        'duration': _first_spell_text(row, 'duration'),
        'components': _first_spell_text(row, 'components'),
        'concentration': _first_spell_bool(row, 'concentration', 'isConcentration'),
        'ritual': _first_spell_bool(row, 'ritual', 'isRitual'),
        'attackType': attack_type,
        'savingThrow': save_ability,
        'saveAbility': save_ability,
        'saveDC': ctx.get('saveDc') or ctx.get('saveDC') or '',
        'attackBonus': ctx.get('attackBonus') if ctx.get('attackBonus') is not None else '',
        'requiresAttackRoll': bool(attack_type),
        'damageFormula': damage_formula,
        'healingFormula': healing_formula,
        'damageType': damage_type,
        'summary': summary or effect,
        'description': description,
        'effect': effect,
        'playerFacingEffectSummary': effect,
        'fullPlayerDetailText': description or effect,
        'rollConfig': roll_config,
        'rollButtonConfig': roll_config,
        'classes': list(row.get('classes') or []),
        'isKnown': known,
        'isPrepared': prepared,
        'isAccessible': True,
        'blockedReason': '',
        'highestAvailableSlot': highest_available_slot,
        'availableCastLevels': available_cast_levels,
        'selectionMode': str(ctx.get('selectionMode') or 'imported'),
        'stateLabel': 'Prepared' if prepared else 'Known' if known else 'Imported',
        'source': 'imported',
        '__source': 'imported',
        'matchedNative': False,
        'needsReview': True,
        'importedOnly': True,
        'cardUiMeta': {'accent': 'gold', 'badges': badges},
    }

def build_spell_card(spell: dict[str, Any], *, character_context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = character_context if isinstance(character_context, dict) else {}
    spell = _clone(spell)
    spell_level = _safe_int(spell.get('level'), 0)
    highest_available_slot = _safe_int(ctx.get('highestAvailableSlot'), 0)
    available_cast_levels = []
    if spell_level > 0:
        max_level = highest_available_slot if highest_available_slot >= spell_level else spell_level
        available_cast_levels = list(range(spell_level, max_level + 1))
    selection_mode = str(ctx.get('selectionMode') or '')
    state_label = 'Unavailable'
    if bool(ctx.get('isPrepared')):
        state_label = 'Prepared'
    elif bool(ctx.get('isKnown')):
        state_label = 'Known'
    elif bool(ctx.get('isAccessible', True)):
        state_label = 'Unlocked'
    card = {
        'id': spell.get('id'),
        'name': spell.get('name'),
        'displayName': spell.get('displayName') or spell.get('name'),
        'level': spell.get('level'),
        'school': spell.get('school'),
        'castingTime': spell.get('castingTime'),
        'range': spell.get('range'),
        'duration': spell.get('duration'),
        'components': spell.get('components'),
        'concentration': bool(spell.get('concentration')),
        'ritual': bool(spell.get('ritual')),
        'damageFormula': spell.get('damageFormula') or '',
        'healingFormula': spell.get('healingFormula') or '',
        'damageType': spell.get('damageType') or '',
        'savingThrow': spell.get('savingThrow') or '',
        'saveAbility': spell.get('savingThrow') or '',
        'attackType': spell.get('attackType') or '',
        'requiresAttackRoll': bool(spell.get('attackType') or ((spell.get('rollButtonConfig') or {}).get('hasAttackRoll'))),
        'classes': spell.get('classes') or [],
        'sourceClass': ctx.get('sourceClass') or '',
        'sourceSubclass': ctx.get('sourceSubclass') or '',
        'sourceType': ctx.get('sourceType') or '',
        'sourceClasses': ctx.get('sourceClasses') or [],
        'unlockLevel': ctx.get('unlockLevel'),
        'isKnown': bool(ctx.get('isKnown')),
        'isPrepared': bool(ctx.get('isPrepared')),
        'isAccessible': bool(ctx.get('isAccessible', True)),
        'blockedReason': str(ctx.get('blockedReason') or ''),
        'summary': spell.get('shortPlayerSummary') or '',
        'description': spell.get('description') or '',
        'scalingNote': ((spell.get('scalingRules') or {}).get('summary') or ''),
        'rollConfig': spell.get('rollButtonConfig') or {},
        'highestAvailableSlot': highest_available_slot,
        'availableCastLevels': available_cast_levels,
        'selectionMode': selection_mode,
        'stateLabel': state_label,
    }
    return card


def build_character_spell_manifest(document: dict[str, Any]) -> dict[str, Any]:
    classes = document.get('classes') if isinstance(document.get('classes'), list) else []
    abilities = document.get('abilities') if isinstance(document.get('abilities'), dict) else {}
    spell_state = document.get('spellState') if isinstance(document.get('spellState'), dict) else {}
    context = build_multiclass_spell_context(document)
    source_map = context.get('classSourcesBySpell') if isinstance(context.get('classSourcesBySpell'), dict) else {}
    class_contexts = context.get('classes') if isinstance(context.get('classes'), list) else []
    primary = class_contexts[0] if class_contexts else (_class_rows_for_document(document)[0] if _class_rows_for_document(document) else {})
    class_id = _norm(primary.get('classId') or primary.get('id') or primary.get('name'))
    class_level = _safe_int(primary.get('level'), 1)
    primary_limits = build_spell_limits_for_class(class_id, class_level, abilities, document=document, subclass_id=_norm(primary.get('subclassId'))) if class_id else {}
    limits = {**primary_limits, 'classes': class_contexts, 'multiclass': len(class_contexts) > 1, 'combinedSpellSlots': context.get('spellSlots') or {}, 'pactMagic': context.get('pactMagic') or {}, 'casterLevel': context.get('casterLevel') or 0}
    if len(class_contexts) > 1:
        limits['spellSlots'] = context.get('spellSlots') or {}
    highest_available_slot = max(_highest_slot_level_from_limits({'spellSlots': context.get('spellSlots') or {}}), _safe_int((context.get('pactMagic') or {}).get('highestSlotLevel'), 0), _highest_slot_level_from_limits(primary_limits))
    known: list[str] = []
    prepared: list[str] = []
    for cls in class_contexts or [primary]:
        cid = _norm((cls or {}).get('classId')) or class_id
        clevel = _safe_int((cls or {}).get('level'), class_level)
        effective = get_effective_document_spell_state(document, class_id=cid, class_level=clevel)
        known.extend(effective.get('known') or [])
        prepared.extend(effective.get('prepared') or [])
    known = _dedupe_preserve(known)
    prepared = _dedupe_preserve(prepared)
    validation = validate_spell_selection(class_id=class_id, class_level=class_level, abilities=abilities, known=known, prepared=prepared, document=document, subclass_id=_norm(primary.get('subclassId')))
    known_set = set(validation['known'])
    prepared_set = set(validation['prepared'])
    bonus_access = set((validation.get('subclassGrants') or {}).get('alwaysPrepared') or []) | set((validation.get('subclassGrants') or {}).get('alwaysKnown') or [])
    selection_mode = 'prepared' if limits.get('preparedLimit') is not None else ('known' if limits.get('spellsKnown') is not None else 'library')
    cards = []
    for spell in get_spell_list():
        spell_id = str(spell.get('id') or '')
        sources = list(source_map.get(spell_id) or [])
        accessible = bool(sources) or spell_id in bonus_access
        if not accessible and spell_id not in known_set and spell_id not in prepared_set:
            continue
        primary_source = sources[0] if sources else {}
        unlock = primary_source.get('unlockLevel') if isinstance(primary_source, dict) else None
        selection_mode = 'library'
        source_class = str(primary_source.get('classId') or '') if isinstance(primary_source, dict) else ''
        for cls in class_contexts:
            if str(cls.get('classId') or '') == source_class:
                cls_limits = cls.get('limits') if isinstance(cls.get('limits'), dict) else {}
                selection_mode = 'prepared' if cls_limits.get('preparedLimit') is not None else ('known' if cls_limits.get('spellsKnown') is not None else 'library')
                break
        card_context = {
            'unlockLevel': unlock,
            'isKnown': spell_id in known_set,
            'isPrepared': spell_id in prepared_set,
            'isAccessible': accessible,
            'blockedReason': '' if accessible else 'Not unlocked for any current class/level.',
            'highestAvailableSlot': highest_available_slot,
            'selectionMode': selection_mode,
            'sourceClass': str(primary_source.get('classId') or '') if isinstance(primary_source, dict) else '',
            'sourceSubclass': str(primary_source.get('subclassId') or '') if isinstance(primary_source, dict) else '',
            'sourceType': str(primary_source.get('sourceType') or '') if isinstance(primary_source, dict) else '',
            'sourceClasses': sources,
        }
        cards.append(build_spell_card(spell, character_context=card_context))
    entries = spell_state.get('spellbookEntries') if isinstance(spell_state.get('spellbookEntries'), list) else []
    existing_card_ids = {str(card.get('id') or '').strip().lower() for card in cards if isinstance(card, dict)}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get('matchedNative') is not False:
            continue
        fallback_id = str(entry.get('id') or entry.get('spellId') or _slug(entry.get('name') or 'imported-spell')).strip()
        if not fallback_id or fallback_id.lower() in existing_card_ids:
            continue
        prepared_flag = fallback_id in prepared_set or bool(entry.get('prepared') or entry.get('isPrepared'))
        known_flag = fallback_id in known_set or prepared_flag or entry.get('known') is not False
        cards.append(build_imported_spell_fallback_card(entry, {
            'isKnown': known_flag,
            'isPrepared': prepared_flag,
            'highestAvailableSlot': highest_available_slot,
            'selectionMode': selection_mode,
            'saveDc': validation.get('saveDc') or validation.get('spellSaveDc') or '',
            'attackBonus': validation.get('attackBonus') or validation.get('spellAttackBonus') or '',
        }))
        existing_card_ids.add(fallback_id.lower())

    return {
        'limits': limits,
        'validation': validation,
        'cards': cards,
        'known': validation['known'],
        'prepared': validation['prepared'],
        'multiclassContext': context,
    }
