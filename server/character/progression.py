"""Level-up preview + apply helpers for canonical native character documents."""
from __future__ import annotations

import copy
from typing import Any

from server.character.resolver import resolve_character_runtime
from server.character.rules_catalog import load_rules_catalog
from server.character.spell_compendium import (
    build_spell_limits_for_class,
    get_effective_document_spell_state,
    get_spell_by_id,
    get_spell_list,
    validate_spell_selection,
)
from server.character.validation import validate_or_raise


def _safe_int(value: Any, fallback: int = 0, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = fallback
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _ability_modifier(score: Any) -> int:
    return (_safe_int(score, 10) - 10) // 2


def _proficiency_bonus(level_total: int) -> int:
    return 2 + max(0, (max(1, level_total) - 1) // 4)


def _class_hit_die(class_row: dict[str, Any] | None) -> int:
    if not isinstance(class_row, dict):
        return 6
    return _safe_int(class_row.get("hitDie"), 6, minimum=1)


def _resolve_class_id(class_entry: dict[str, Any]) -> str:
    return str(
        class_entry.get("classId")
        or class_entry.get("id")
        or class_entry.get("name")
        or ""
    ).strip().lower()


def _normalize_slot_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, int] = {}
    for slot_level, amount in value.items():
        slot_key = str(slot_level or "").strip()
        if not slot_key:
            continue
        normalized[slot_key] = _safe_int(amount, 0, minimum=0)
    return normalized


class LevelupApplyError(ValueError):
    """Raised when level-up apply cannot be performed safely."""


def _resolve_con_score(canonical: dict[str, Any]) -> int:
    abilities = canonical.get("abilities") if isinstance(canonical.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    return _safe_int(scores.get("con", abilities.get("con", 10)), 10, minimum=1)


def _normalize_choice_list(value: Any) -> list[dict[str, Any]]:
    choices = value if isinstance(value, list) else []
    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(choices):
        if isinstance(row, dict):
            choice_id = str(row.get("id") or row.get("name") or f"choice-{idx + 1}").strip().lower()
            normalized.append(
                {
                    "id": choice_id,
                    "name": str(row.get("name") or row.get("displayName") or choice_id).strip() or choice_id,
                    "description": str(row.get("description") or "").strip(),
                }
            )
        elif isinstance(row, str):
            choice_id = row.strip().lower()
            if choice_id:
                normalized.append({"id": choice_id, "name": row.strip(), "description": ""})
    return normalized


def _unique_spell_ids(value: Any) -> list[str]:
    rows = value if isinstance(value, list) else []
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        spell_id = str(row or "").strip()
        if not spell_id or spell_id in seen:
            continue
        seen.add(spell_id)
        out.append(spell_id)
    return out


def _spell_option_row(spell: dict[str, Any], *, class_id: str) -> dict[str, Any]:
    unlock = (spell.get("classUnlockLevels") or {}).get(class_id)
    return {
        "id": str(spell.get("id") or "").strip(),
        "name": str(spell.get("displayName") or spell.get("name") or spell.get("id") or "Spell").strip(),
        "level": _safe_int(spell.get("level"), 0, minimum=0, maximum=9),
        "school": str(spell.get("school") or "").strip(),
        "castingTime": str(spell.get("castingTime") or "").strip(),
        "range": str(spell.get("range") or "").strip(),
        "summary": str(spell.get("shortPlayerSummary") or spell.get("description") or "").strip(),
        "unlockLevel": _safe_int(unlock, 1, minimum=1, maximum=20) if unlock is not None else None,
    }


def _highest_spell_level_from_limits(limits: dict[str, Any]) -> int:
    slot_map = limits.get("spellSlots") if isinstance(limits, dict) else {}
    highest = 0
    if isinstance(slot_map, dict):
        for slot_level, amount in slot_map.items():
            if _safe_int(amount, 0, minimum=0) <= 0:
                continue
            slot_text = str(slot_level or "").strip().lower()
            parsed_level = _safe_int(slot_text[:1], 0, minimum=0, maximum=9)
            highest = max(highest, parsed_level)
    return highest


def _sort_spell_options(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            _safe_int((row or {}).get("level"), 0, minimum=0, maximum=9),
            str((row or {}).get("name") or "").lower(),
            str((row or {}).get("id") or "").lower(),
        ),
    )


def _current_spell_state(document: dict[str, Any], *, class_id: str, class_level: int) -> dict[str, Any]:
    effective_spell_state = get_effective_document_spell_state(document, class_id=class_id, class_level=class_level)
    known = _unique_spell_ids(effective_spell_state.get("known"))
    prepared = _unique_spell_ids(effective_spell_state.get("prepared"))
    validation = validate_spell_selection(
        class_id=class_id,
        class_level=class_level,
        abilities=document.get("abilities") if isinstance(document.get("abilities"), dict) else {},
        known=known,
        prepared=prepared,
        document=document,
    )
    return {
        "known": list(validation.get("known") or []),
        "prepared": list(validation.get("prepared") or []),
        "validation": validation,
    }


def _build_spell_choices_preview(
    document: dict[str, Any],
    *,
    class_id: str,
    class_name: str,
    current_level: int,
    next_level: int,
    current_class_mechanics: dict[str, Any],
    next_class_mechanics: dict[str, Any],
) -> dict[str, Any] | None:
    if not class_id:
        return None

    current_spell_state = _current_spell_state(document, class_id=class_id, class_level=current_level)
    current_known = current_spell_state["known"]
    current_prepared = current_spell_state["prepared"]
    current_known_set = set(current_known)

    current_limits = build_spell_limits_for_class(class_id, current_level, document.get("abilities") if isinstance(document.get("abilities"), dict) else {})
    next_limits = build_spell_limits_for_class(class_id, next_level, document.get("abilities") if isinstance(document.get("abilities"), dict) else {})

    known_spells = []
    known_cantrips = []
    for spell_id in current_known:
        spell = get_spell_by_id(spell_id)
        if not spell:
            continue
        if _safe_int(spell.get("level"), 0) <= 0:
            known_cantrips.append(spell)
        else:
            known_spells.append(spell)

    has_spellbook_track = isinstance(current_class_mechanics, dict) and ("spellbookSpells" in current_class_mechanics or "spellbookSpells" in next_class_mechanics)
    current_spellbook_spells = _safe_int(current_class_mechanics.get("spellbookSpells"), len(known_spells), minimum=0) if has_spellbook_track else 0
    next_spellbook_spells = _safe_int(next_class_mechanics.get("spellbookSpells"), current_spellbook_spells, minimum=0) if has_spellbook_track else 0

    mode = "none"
    if has_spellbook_track:
        mode = "spellbook"
    elif next_limits.get("spellsKnown") is not None:
        mode = "known"
    elif next_limits.get("preparedLimit") is not None:
        mode = "prepared"

    cantrip_target = next_limits.get("cantripsKnown")
    cantrip_required = 0
    if cantrip_target is not None:
        cantrip_required = max(0, int(cantrip_target) - len(known_cantrips))

    levelled_required = 0
    if mode == "spellbook":
        levelled_required = max(0, next_spellbook_spells - len(known_spells))
    elif mode == "known" and next_limits.get("spellsKnown") is not None:
        levelled_required = max(0, int(next_limits.get("spellsKnown") or 0) - len(known_spells))

    next_highest_spell_level = _highest_spell_level_from_limits(next_limits)
    current_highest_spell_level = _highest_spell_level_from_limits(current_limits)

    accessible_spells = []
    for spell in get_spell_list():
        unlock = (spell.get("classUnlockLevels") or {}).get(class_id)
        if unlock is None or next_level < int(unlock):
            continue
        spell_level = _safe_int(spell.get("level"), 0, minimum=0, maximum=9)
        if spell_level > 0 and next_highest_spell_level > 0 and spell_level > next_highest_spell_level:
            continue
        accessible_spells.append(spell)

    cantrip_options = _sort_spell_options([
        _spell_option_row(spell, class_id=class_id)
        for spell in accessible_spells
        if _safe_int(spell.get("level"), 0) <= 0 and str(spell.get("id") or "") not in current_known_set
    ])
    levelled_options = _sort_spell_options([
        _spell_option_row(spell, class_id=class_id)
        for spell in accessible_spells
        if _safe_int(spell.get("level"), 0) > 0 and str(spell.get("id") or "") not in current_known_set
    ])
    if (cantrip_required > 0 and not cantrip_options) or (levelled_required > 0 and not levelled_options):
        class_name_key = str(class_name or "").strip().lower()
        fallback_spells = []
        for spell in get_spell_list():
            spell_level = _safe_int(spell.get("level"), 0, minimum=0, maximum=9)
            if spell_level > 0 and next_highest_spell_level > 0 and spell_level > next_highest_spell_level:
                continue
            classes = spell.get("classes")
            classish = []
            if isinstance(classes, list):
                for row in classes:
                    if isinstance(row, str):
                        classish.append(row.strip().lower())
                    elif isinstance(row, dict):
                        classish.extend([str(row.get("id") or "").strip().lower(), str(row.get("name") or "").strip().lower()])
            if class_name_key and class_name_key not in classish and str(class_id or "").strip().lower() not in classish:
                continue
            fallback_spells.append(spell)
        if cantrip_required > 0 and not cantrip_options:
            cantrip_options = _sort_spell_options([
                _spell_option_row(spell, class_id=class_id)
                for spell in fallback_spells
                if _safe_int(spell.get("level"), 0) <= 0 and str(spell.get("id") or "") not in current_known_set
            ])
        if levelled_required > 0 and not levelled_options:
            levelled_options = _sort_spell_options([
                _spell_option_row(spell, class_id=class_id)
                for spell in fallback_spells
                if _safe_int(spell.get("level"), 0) > 0 and str(spell.get("id") or "") not in current_known_set
            ])
    replaceable_known = _sort_spell_options([_spell_option_row(spell, class_id=class_id) for spell in known_spells])
    swap_allowed = mode in {"known", "spellbook"} and bool(replaceable_known) and bool(levelled_options)

    next_validation = validate_spell_selection(
        class_id=class_id,
        class_level=next_level,
        abilities=document.get("abilities") if isinstance(document.get("abilities"), dict) else {},
        known=current_known,
        prepared=current_prepared,
        document=document,
    )
    subclass_spell_grants = next_validation.get("subclassGrants") if isinstance(next_validation, dict) else {}
    has_subclass_spell_unlocks = bool([
        row for row in (subclass_spell_grants.get("unlockedSpells") or [])
        if _safe_int(row.get("unlockLevel"), 0) == next_level
    ])

    if not cantrip_required and not levelled_required and not swap_allowed and mode != "prepared" and not has_subclass_spell_unlocks:
        return None

    no_choices_message = ""
    if mode == "prepared" and not cantrip_required and not levelled_required:
        no_choices_message = "Your spell access expands automatically at this level. After leveling, open Manage Spells to prepare from the legal list for your new tier."
        unlocked = [row for row in (subclass_spell_grants.get("unlockedSpells") or []) if _safe_int(row.get("unlockLevel"), 0) == next_level]
        if unlocked:
            names = []
            for row in unlocked:
                for spell in row.get("spells") or []:
                    label = str(spell.get("name") or "").strip()
                    if label and label not in names:
                        names.append(label)
            if names:
                no_choices_message = "Your subclass also unlocks: " + ", ".join(names[:6]) + ("." if len(names) <= 6 else ", and more.")

    return {
        "mode": mode,
        "classId": class_id,
        "className": class_name,
        "currentLevel": current_level,
        "nextLevel": next_level,
        "cantripPicksRequired": cantrip_required,
        "levelledPicksRequired": levelled_required,
        "swapAllowed": swap_allowed,
        "currentKnownCantrips": len(known_cantrips),
        "currentKnownLevelled": len(known_spells),
        "currentPrepared": len(current_prepared),
        "currentLimits": current_limits,
        "nextLimits": next_limits,
        "currentHighestSpellLevel": current_highest_spell_level,
        "nextHighestSpellLevel": next_highest_spell_level,
        "spellbookCurrent": current_spellbook_spells if mode == "spellbook" else None,
        "spellbookTarget": next_spellbook_spells if mode == "spellbook" else None,
        "cantripOptions": cantrip_options,
        "levelledOptions": levelled_options,
        "replaceableKnown": replaceable_known,
        "noChoicesMessage": no_choices_message,
        "subclassSpellGrants": subclass_spell_grants,
    }


def build_levelup_preview(document: Any) -> dict[str, Any]:
    """Returns a complete levelup preview for one class level gained."""
    normalized = validate_or_raise(document)
    resolved = resolve_character_runtime(normalized)
    canonical = resolved["document"]
    runtime = resolved["runtime"]

    catalog = load_rules_catalog()
    classes_by_id = catalog.get("classesById", {})
    if not isinstance(classes_by_id, dict):
        classes_by_id = {}

    _classes_list = canonical.get("classes") if isinstance(canonical.get("classes"), list) else []
    primary_class = _classes_list[0] if _classes_list else {}
    if not isinstance(primary_class, dict):
        primary_class = {}
    class_id = _resolve_class_id(primary_class)
    class_catalog = classes_by_id.get(class_id, {}) if class_id else {}
    if not isinstance(class_catalog, dict):
        class_catalog = {}

    current_level = _safe_int(primary_class.get("level"), 1, minimum=1, maximum=20)
    next_level = min(20, current_level + 1)

    progression_table = class_catalog.get("progressionTable", [])
    if not isinstance(progression_table, list):
        progression_table = []
    current_level_row = next((row for row in progression_table if isinstance(row, dict) and _safe_int(row.get("level"), 0) == current_level), {})
    next_level_row = next((row for row in progression_table if isinstance(row, dict) and _safe_int(row.get("level"), 0) == next_level), {})

    next_level_unlock_ids = next_level_row.get("unlockIds", []) if isinstance(next_level_row, dict) else []
    if not isinstance(next_level_unlock_ids, list):
        next_level_unlock_ids = []
    new_feature_ids = [
        str(fid or "").strip()
        for fid in next_level_unlock_ids
        if str(fid or "").strip()
    ]
    if not new_feature_ids:
        # Compatibility fallback for catalogs that still only expose levelUnlockIds.
        fallback_unlocks = class_catalog.get("levelUnlockIds", {}).get(str(next_level), [])
        if isinstance(fallback_unlocks, list):
            new_feature_ids = [str(fid or "").strip() for fid in fallback_unlocks if str(fid or "").strip()]
    feature_defs = class_catalog.get("featureDefinitions", {})
    if not isinstance(feature_defs, dict):
        feature_defs = {}
    new_features: list[dict[str, Any]] = []
    for fid in new_feature_ids:
        feature_id = str(fid or "").strip()
        if not feature_id:
            continue
        definition = feature_defs.get(feature_id, {})
        if not isinstance(definition, dict):
            definition = {}
        new_features.append(
            {
                "id": feature_id,
                "displayName": str(definition.get("displayName") or feature_id.replace("-", " ").title()),
                "description": str(definition.get("description") or ""),
                "choices": _normalize_choice_list(definition.get("choices", [])),
            }
        )

    if not new_features:
        for idx, feature_name in enumerate(next_level_row.get("features", []) if isinstance(next_level_row.get("features"), list) else []):
            label = str(feature_name or "").strip()
            if not label:
                continue
            new_features.append(
                {
                    "id": f"{class_id or 'class'}-l{next_level}-{idx + 1}",
                    "displayName": label,
                    "description": "",
                    "choices": [],
                }
            )

    is_asi_level = bool(next_level_row.get("asiOrFeat", False))
    hit_die = _class_hit_die(class_catalog)
    con_mod = _ability_modifier(_resolve_con_score(canonical))
    hp_roll_average = (hit_die // 2) + 1
    hp_gained = max(1, hp_roll_average + con_mod)

    spell_slots_table = class_catalog.get("spellSlots", {})
    if not isinstance(spell_slots_table, dict):
        spell_slots_table = {}
    current_spell_slots = _normalize_slot_map(spell_slots_table.get(str(current_level), {}))
    new_spell_slots = _normalize_slot_map(spell_slots_table.get(str(next_level), {}))

    new_prof_bonus = 2 + max(0, (next_level - 1) // 4)
    class_mechanics = next_level_row.get("classMechanics", {})
    if not isinstance(class_mechanics, dict):
        class_mechanics = {}
    current_class_mechanics = current_level_row.get("classMechanics", {})
    if not isinstance(current_class_mechanics, dict):
        current_class_mechanics = {}

    class_display_name = str(class_catalog.get("displayName") or primary_class.get("name") or class_id or "Class")
    current_total = _safe_int(runtime.get("levelTotal"), current_level, minimum=1, maximum=20)
    required_choices: list[dict[str, Any]] = []
    for feature in new_features:
        if feature.get("choices"):
            required_choices.append(
                {
                    "id": str(feature.get("id") or ""),
                    "type": "feature_choice",
                    "reason": f"{feature.get('displayName') or 'Feature'} requires a selection.",
                }
            )
    if is_asi_level:
        required_choices.append(
            {
                "id": f"{class_id or 'class'}-asi-level-{next_level}",
                "type": "asi_or_feat",
                "reason": f"{class_display_name} can take an Ability Score Improvement or feat at level {next_level}.",
            }
        )
    subclass_level = _safe_int(class_catalog.get("subclassLevel"), 0, minimum=0, maximum=20)
    subclass_id = str(primary_class.get("subclassId") or "").strip().lower()
    if subclass_level and next_level >= subclass_level and not subclass_id:
        required_choices.append(
            {
                "id": f"{class_id or 'class'}-subclass-choice-level-{next_level}",
                "type": "subclass",
                "reason": f"{class_display_name} selects a subclass at level {subclass_level}.",
            }
        )

    spell_choices = _build_spell_choices_preview(
        canonical,
        class_id=class_id,
        class_name=class_display_name,
        current_level=current_level,
        next_level=next_level,
        current_class_mechanics=current_class_mechanics,
        next_class_mechanics=class_mechanics,
    )
    if spell_choices:
        if _safe_int(spell_choices.get("cantripPicksRequired"), 0, minimum=0) > 0:
            required_choices.append(
                {
                    "id": f"{class_id or 'class'}-spell-cantrips-level-{next_level}",
                    "type": "spell_cantrips",
                    "reason": f"Choose {_safe_int(spell_choices.get('cantripPicksRequired'), 0)} cantrip(s) for level {next_level}.",
                }
            )
        if _safe_int(spell_choices.get("levelledPicksRequired"), 0, minimum=0) > 0:
            required_choices.append(
                {
                    "id": f"{class_id or 'class'}-spell-levelled-level-{next_level}",
                    "type": "spell_levelled",
                    "reason": (
                        f"Add {_safe_int(spell_choices.get('levelledPicksRequired'), 0)} "
                        + ("spellbook spell(s)" if spell_choices.get("mode") == "spellbook" else "spell(s) known")
                        + f" for level {next_level}."
                    ),
                }
            )

    return {
        "currentLevel": current_level,
        "nextLevel": next_level,
        "classId": class_id,
        "className": class_display_name,
        "newFeatures": new_features,
        "isAsiLevel": is_asi_level,
        "hpGained": hp_gained,
        "hitDie": hit_die,
        "newSpellSlots": new_spell_slots,
        "currentSpellSlots": current_spell_slots,
        "hasNewSpellSlots": bool(new_spell_slots),
        "newProficiencyBonus": new_prof_bonus,
        "currentProficiencyBonus": _proficiency_bonus(current_level),
        "currentClassMechanics": current_class_mechanics,
        "classMechanics": class_mechanics,
        "requiresChoices": bool(required_choices),
        "spellChoices": spell_choices,
        "nextLevelSummary": {
            "classId": class_id,
            "className": class_display_name,
            "fromClassLevel": current_level,
            "toClassLevel": next_level,
            "fromTotalLevel": current_total,
            "toTotalLevel": min(20, current_total + 1),
            "rulesMode": str(canonical.get("rulesMode") or "casual"),
            "sourceMode": str(canonical.get("sourceMode") or "native"),
            "isAtLevelCap": current_level >= 20,
        },
        "unlockedFeatures": [
            {"id": row.get("id"), "name": row.get("displayName"), "description": row.get("description")}
            for row in new_features
        ],
        "requiredChoices": required_choices,
        "optionalChoices": [],
        "meta": {"previewOnly": True, "applySupported": True, "engine": "character.levelup.preview.v3"},
    }


def apply_levelup(document: Any, *, choices: Any = None) -> dict[str, Any]:
    normalized = validate_or_raise(document)
    canonical = copy.deepcopy(normalized)
    preview = build_levelup_preview(canonical)
    current_level = _safe_int(preview.get("currentLevel"), 1, minimum=1, maximum=20)
    next_level = _safe_int(preview.get("nextLevel"), current_level, minimum=1, maximum=20)
    if current_level >= 20:
        raise LevelupApplyError("Cannot apply level-up: character is already at level cap (20).")

    classes = canonical.get("classes") if isinstance(canonical.get("classes"), list) else []
    if not classes or not isinstance(classes[0], dict):
        raise LevelupApplyError("Cannot apply level-up: character has no primary class.")
    primary_class = classes[0]
    primary_class["level"] = next_level

    selected_choices = choices if isinstance(choices, dict) else {}
    feature_choices = selected_choices.get("featureChoices") if isinstance(selected_choices.get("featureChoices"), dict) else {}
    asi_choice = selected_choices.get("asiChoice") if isinstance(selected_choices.get("asiChoice"), dict) else {}
    feat_choice = str(selected_choices.get("featChoice") or "").strip().lower()
    spell_choice_payload = selected_choices.get("spellChoices") if isinstance(selected_choices.get("spellChoices"), dict) else {}

    unresolved_required = []
    for row in preview.get("requiredChoices") or []:
        if not isinstance(row, dict):
            continue
        row_type = str(row.get("type") or "").strip().lower()
        if row_type == "feature_choice":
            feature_id = str(row.get("id") or "").strip()
            if feature_id and not feature_choices.get(feature_id):
                unresolved_required.append(row)
        elif row_type == "asi_or_feat":
            has_asi = isinstance(asi_choice, dict) and bool(str(asi_choice.get("mode") or "").strip())
            if not feat_choice and not has_asi:
                unresolved_required.append(row)
        elif row_type == "spell_cantrips":
            spell_plan = preview.get("spellChoices") if isinstance(preview.get("spellChoices"), dict) else {}
            required = _safe_int(spell_plan.get("cantripPicksRequired"), 0, minimum=0)
            if len(_unique_spell_ids(spell_choice_payload.get("cantripAdds"))) < required:
                unresolved_required.append(row)
        elif row_type == "spell_levelled":
            spell_plan = preview.get("spellChoices") if isinstance(preview.get("spellChoices"), dict) else {}
            required = _safe_int(spell_plan.get("levelledPicksRequired"), 0, minimum=0)
            if len(_unique_spell_ids(spell_choice_payload.get("levelledAdds"))) < required:
                unresolved_required.append(row)
        elif row_type == "subclass":
            unresolved_required.append(row)
    if unresolved_required:
        raise LevelupApplyError("Cannot apply level-up: unresolved required choices remain.")

    class_features = primary_class.get("selectedFeatures") if isinstance(primary_class.get("selectedFeatures"), list) else []
    known_feature_ids = {str(row.get("id") or "").strip().lower() for row in class_features if isinstance(row, dict)}
    for feature in preview.get("newFeatures") or []:
        if not isinstance(feature, dict):
            continue
        feature_id = str(feature.get("id") or "").strip()
        if not feature_id or feature_id.lower() in known_feature_ids:
            continue
        class_features.append(
            {
                "id": feature_id,
                "displayName": str(feature.get("displayName") or feature_id),
                "description": str(feature.get("description") or ""),
                "selectedChoice": feature_choices.get(feature_id),
            }
        )
    primary_class["selectedFeatures"] = class_features

    abilities = canonical.get("abilities") if isinstance(canonical.get("abilities"), dict) else {}
    scores = abilities.get("scores") if isinstance(abilities.get("scores"), dict) else {}
    if not isinstance(scores, dict):
        scores = {}
    if bool(preview.get("isAsiLevel")):
        if feat_choice:
            feats = canonical.get("feats") if isinstance(canonical.get("feats"), list) else []
            existing = {str((row if isinstance(row, str) else row.get("featId") or row.get("id") or "")).strip().lower() for row in feats if isinstance(row, (str, dict))}
            if feat_choice not in existing:
                feats.append({"featId": feat_choice})
            canonical["feats"] = feats
        else:
            mode = str(asi_choice.get("mode") or "").strip().lower()
            if mode == "plus2":
                ability = str(asi_choice.get("ability") or "").strip().lower()
                if ability:
                    scores[ability] = _safe_int(scores.get(ability), 10, minimum=1, maximum=30) + 2
            elif mode == "plus1x2":
                abilities_selected = asi_choice.get("abilities") if isinstance(asi_choice.get("abilities"), list) else []
                unique = []
                for key in abilities_selected:
                    ability = str(key or "").strip().lower()
                    if ability and ability not in unique:
                        unique.append(ability)
                for ability in unique[:2]:
                    scores[ability] = _safe_int(scores.get(ability), 10, minimum=1, maximum=30) + 1
    abilities["scores"] = scores
    canonical["abilities"] = abilities

    spell_state = canonical.get("spellState") if isinstance(canonical.get("spellState"), dict) else {}
    spell_plan = preview.get("spellChoices") if isinstance(preview.get("spellChoices"), dict) else {}
    if spell_plan:
        class_id = str(preview.get("classId") or "").strip().lower()
        current_spell_state = _current_spell_state(canonical, class_id=class_id, class_level=next_level)
        known = list(current_spell_state.get("known") or [])
        prepared = list(current_spell_state.get("prepared") or [])
        known_set = set(known)

        cantrip_adds = _unique_spell_ids(spell_choice_payload.get("cantripAdds"))
        levelled_adds = _unique_spell_ids(spell_choice_payload.get("levelledAdds"))
        cantrip_required = _safe_int(spell_plan.get("cantripPicksRequired"), 0, minimum=0)
        levelled_required = _safe_int(spell_plan.get("levelledPicksRequired"), 0, minimum=0)
        if cantrip_required and len(cantrip_adds) != cantrip_required:
            raise LevelupApplyError(f"Choose exactly {cantrip_required} cantrip(s) before applying this level.")
        if levelled_required and len(levelled_adds) != levelled_required:
            raise LevelupApplyError(f"Choose exactly {levelled_required} new spell(s) before applying this level.")

        legal_cantrips = {str(row.get("id") or "") for row in spell_plan.get("cantripOptions") or [] if isinstance(row, dict)}
        legal_levelled = {str(row.get("id") or "") for row in spell_plan.get("levelledOptions") or [] if isinstance(row, dict)}
        replaceable_known = {str(row.get("id") or "") for row in spell_plan.get("replaceableKnown") or [] if isinstance(row, dict)}

        for spell_id in cantrip_adds:
            if spell_id not in legal_cantrips:
                raise LevelupApplyError("Illegal cantrip selection detected during level-up.")
            if spell_id not in known_set:
                known.append(spell_id)
                known_set.add(spell_id)
        for spell_id in levelled_adds:
            if spell_id not in legal_levelled:
                raise LevelupApplyError("Illegal spell selection detected during level-up.")
            if spell_id not in known_set:
                known.append(spell_id)
                known_set.add(spell_id)

        swap = spell_choice_payload.get("swap") if isinstance(spell_choice_payload.get("swap"), dict) else {}
        swap_drop = str(swap.get("drop") or "").strip()
        swap_add = str(swap.get("learn") or "").strip()
        if swap_drop or swap_add:
            if not spell_plan.get("swapAllowed"):
                raise LevelupApplyError("Spell replacement is not allowed for this level-up.")
            if not swap_drop or not swap_add:
                raise LevelupApplyError("A spell replacement needs both the old spell and the new spell.")
            if swap_drop == swap_add:
                raise LevelupApplyError("Choose a different spell to learn when replacing one.")
            if swap_drop not in replaceable_known:
                raise LevelupApplyError("That spell cannot be replaced right now.")
            if swap_add not in legal_levelled:
                raise LevelupApplyError("That replacement spell is not unlocked for this level.")
            if swap_add in set(cantrip_adds + levelled_adds):
                raise LevelupApplyError("Do not spend your optional swap on a spell you already picked as a new gain.")
            known = [spell_id for spell_id in known if spell_id != swap_drop]
            if swap_add not in known:
                known.append(swap_add)

        validation_next = validate_spell_selection(
            class_id=class_id,
            class_level=next_level,
            abilities=canonical.get("abilities") if isinstance(canonical.get("abilities"), dict) else {},
            known=known,
            prepared=prepared,
            document=canonical,
        )
        if not validation_next.get("ok"):
            raise LevelupApplyError(" ".join(validation_next.get("errors") or ["Spell choices are not valid for this level-up."]))
        spell_state["known"] = list(validation_next.get("known") or [])
        spell_state["prepared"] = list(validation_next.get("prepared") or [])

    if bool(preview.get("hasNewSpellSlots")):
        spell_state["slots"] = copy.deepcopy(preview.get("newSpellSlots") or {})
    canonical["spellState"] = spell_state

    progression = canonical.get("progression") if isinstance(canonical.get("progression"), dict) else {}
    progression["lastAppliedLevelup"] = {
        "fromLevel": current_level,
        "toLevel": next_level,
        "hpGained": _safe_int(preview.get("hpGained"), 1, minimum=1),
        "choices": copy.deepcopy(selected_choices),
    }
    progression["hpGainedFromLevelups"] = _safe_int(progression.get("hpGainedFromLevelups"), 0, minimum=0) + _safe_int(
        preview.get("hpGained"), 1, minimum=1
    )
    canonical["progression"] = progression

    resolved_after = resolve_character_runtime(canonical)
    result_document = resolved_after["document"]
    result_runtime = resolved_after["runtime"]
    result_document.setdefault("audit", {})
    if isinstance(result_document.get("audit"), dict):
        result_document["audit"]["dirty"] = True

    return {
        "document": result_document,
        "runtime": result_runtime,
        "applied": {
            "fromClassLevel": current_level,
            "toClassLevel": next_level,
            "classId": preview.get("classId") or "",
            "className": preview.get("className") or "",
            "hpGained": _safe_int(preview.get("hpGained"), 1, minimum=1),
            "newSpellSlots": copy.deepcopy(preview.get("newSpellSlots") or {}),
            "choices": copy.deepcopy(selected_choices),
        },
        "meta": {
            "engine": "character.levelup.apply.v3",
        },
    }
