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


def build_spell_limits_for_class(class_id: str, class_level: int, abilities: dict[str, Any] | None = None) -> dict[str, Any]:
    class_row = get_class_catalog_row(class_id)
    mechanics = _class_mechanics_for_level(class_row, class_level)
    abilities = abilities if isinstance(abilities, dict) else {}
    scores = abilities.get('scores') if isinstance(abilities.get('scores'), dict) else abilities
    spell_ability = _norm((class_row or {}).get('spellcastingAbility'))
    ability_mod = _ability_modifier(scores.get(spell_ability, 10)) if spell_ability else 0
    cantrips_known = mechanics.get('cantripsKnown')
    spells_known = mechanics.get('spellsKnown')
    formula = str(mechanics.get('spellsPreparedFormula') or '').strip().lower()
    prepared_limit = None
    if formula:
        prepared_limit = max(1, ability_mod + max(1, class_level))
    return {
        'classId': class_id,
        'className': str((class_row or {}).get('displayName') or class_id).strip(),
        'level': class_level,
        'castingType': str((class_row or {}).get('spellcastingType') or 'none').strip(),
        'spellcastingAbility': spell_ability,
        'cantripsKnown': _safe_int(cantrips_known, 0) if cantrips_known is not None else None,
        'spellsKnown': _safe_int(spells_known, 0) if spells_known is not None else None,
        'preparedLimit': prepared_limit,
        'spellSlots': _clone(((class_row or {}).get('spellSlots') or {}).get(str(class_level), {})),
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
    if known or prepared:
        merged_known = list(known)
        merged_prepared = list(prepared)
        for spell_id in grants.get('alwaysKnown') or []:
            if spell_id not in merged_known:
                merged_known.append(spell_id)
        for spell_id in grants.get('alwaysPrepared') or []:
            if spell_id not in merged_prepared:
                merged_prepared.append(spell_id)
        return {'known': _clone(merged_known), 'prepared': _clone(merged_prepared)}
    fallback_known, fallback_prepared = _infer_spell_ids_from_spellbook_entries(document, class_id=class_id, class_level=class_level)
    for spell_id in grants.get('alwaysKnown') or []:
        if spell_id not in fallback_known:
            fallback_known.append(spell_id)
    for spell_id in grants.get('alwaysPrepared') or []:
        if spell_id not in fallback_prepared:
            fallback_prepared.append(spell_id)
    return {'known': fallback_known, 'prepared': fallback_prepared}




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

def validate_spell_selection(*, class_id: str, class_level: int, abilities: dict[str, Any] | None, known: list[str], prepared: list[str], document: dict[str, Any] | None = None, subclass_id: str | None = None) -> dict[str, Any]:
    limits = build_spell_limits_for_class(class_id, class_level, abilities)
    known_ids = [str(v or '').strip() for v in known if str(v or '').strip()]
    prepared_ids = [str(v or '').strip() for v in prepared if str(v or '').strip()]
    known_cantrips = 0
    known_levelled = 0
    errors: list[str] = []
    warnings: list[str] = []
    allowed_known: list[str] = []
    allowed_prepared: list[str] = []
    subclass_grants = get_subclass_spell_grants(document or {'classes': ([{'classId': class_id, 'subclassId': subclass_id}] if subclass_id else [])}, class_id=class_id, class_level=class_level)
    always_prepared = set(subclass_grants.get('alwaysPrepared') or [])
    always_known = set(subclass_grants.get('alwaysKnown') or [])
    bonus_access = always_prepared | always_known
    for spell_id in known_ids:
        spell = get_spell_by_id(spell_id)
        if not spell:
            warnings.append(f'Unknown spell id kept in known list: {spell_id}')
            continue
        unlock = (spell.get('classUnlockLevels') or {}).get(class_id)
        has_bonus_access = spell_id in bonus_access
        if unlock is None and not has_bonus_access:
            errors.append(f"{spell.get('name')} is not on the {limits.get('className') or class_id} list.")
            continue
        if unlock is not None and class_level < int(unlock):
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
        has_bonus_access = spell_id in bonus_access
        if unlock is None and not has_bonus_access:
            errors.append(f"{spell.get('name')} is not on the {limits.get('className') or class_id} list.")
            continue
        if unlock is not None and class_level < int(unlock):
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
    primary = classes[0] if classes else {}
    class_id = _norm(primary.get('classId') or primary.get('id') or primary.get('name'))
    class_level = _safe_int(primary.get('level'), 1)
    limits = build_spell_limits_for_class(class_id, class_level, abilities)
    highest_available_slot = _highest_slot_level_from_limits(limits)
    effective_spell_state = get_effective_document_spell_state(document, class_id=class_id, class_level=class_level)
    known = list(effective_spell_state.get('known') or [])
    prepared = list(effective_spell_state.get('prepared') or [])
    validation = validate_spell_selection(class_id=class_id, class_level=class_level, abilities=abilities, known=known, prepared=prepared, document=document)
    known_set = set(validation['known'])
    prepared_set = set(validation['prepared'])
    bonus_access = set((validation.get('subclassGrants') or {}).get('alwaysPrepared') or []) | set((validation.get('subclassGrants') or {}).get('alwaysKnown') or [])
    cards = []
    for spell in get_spell_list():
        unlock = (spell.get('classUnlockLevels') or {}).get(class_id)
        accessible = (unlock is not None and class_level >= int(unlock)) or (spell.get('id') in bonus_access)
        if not accessible and spell.get('id') not in known_set and spell.get('id') not in prepared_set:
            continue
        cards.append(build_spell_card(spell, character_context={
            'unlockLevel': unlock,
            'isKnown': spell.get('id') in known_set,
            'isPrepared': spell.get('id') in prepared_set,
            'isAccessible': accessible,
            'blockedReason': '' if accessible else 'Not unlocked for current class/level.',
            'highestAvailableSlot': highest_available_slot,
            'selectionMode': 'prepared' if limits.get('preparedLimit') is not None else ('known' if limits.get('spellsKnown') is not None else 'library'),
        }))
    return {
        'limits': limits,
        'validation': validation,
        'cards': cards,
        'known': validation['known'],
        'prepared': validation['prepared'],
    }
