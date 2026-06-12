"""Full integrity sweep for native 5e2024 class and subclass rules data.

These tests intentionally read the JSON source files directly instead of only
using ``load_rules_catalog()``, because the catalog loader can synthesize or
sanitize runtime feature rows. The goal here is to catch weak authored data
before runtime fallbacks make it look acceptable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.character.feature_catalog import FEATURE_METADATA, RESOURCE_FIELD_BLUEPRINTS
from server.character.rules_catalog import load_rules_catalog
from server.character.service import resolve_runtime

RULES_ROOT = Path("server/data/rules/5e2024")
CLASS_DIR = RULES_ROOT / "classes"
SUBCLASS_DIR = RULES_ROOT / "subclasses"
AUDIT_LEVELS = (1, 3, 5, 10, 15, 20)
FULL_CASTER_MAX_SLOT_LEVEL = 9
HALF_CASTER_MAX_SLOT_LEVEL = 5
PACT_CASTER_MAX_SLOT_LEVEL = 5

# TODO(native-rules): replace this with a first-class shared feature registry
# when class unlocks are intentionally allowed to reference shared feature IDs.
KNOWN_SHARED_FEATURE_IDS = {
    str(row.get("id") or "").strip()
    for row in RESOURCE_FIELD_BLUEPRINTS.values()
    if isinstance(row, dict) and str(row.get("id") or "").strip()
} | {
    key.strip().lower().replace(" ", "-").replace("'", "")
    for key in FEATURE_METADATA
    if str(key or "").strip()
}

RESOURCE_KEYS = {
    "resourceName",
    "resource",
    "resourceId",
}
USE_LIMIT_KEYS = {
    "max",
    "uses",
    "maxUses",
    "scaling",
    "usage",
    "recovery",
    "recharge",
    "recoveryType",
}
RECOVERY_KEYS = {
    "recovery",
    "recharge",
    "recoveryType",
    "usage",
}
RESOURCE_MECHANIC_KEYS = set(RESOURCE_FIELD_BLUEPRINTS)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict), f"{path} must contain a JSON object"
    return payload


def _class_files() -> list[Path]:
    files = sorted(CLASS_DIR.glob("*.json"))
    assert files, f"No class JSON files found under {CLASS_DIR}"
    return files


def _subclass_files() -> list[Path]:
    return sorted(SUBCLASS_DIR.glob("*.json")) if SUBCLASS_DIR.exists() else []


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _feature_name(feature: dict[str, Any], fallback: str = "") -> str:
    return str(feature.get("name") or feature.get("displayName") or fallback or "").strip()


def _progression_feature_names_by_unlock_id(class_data: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for row in class_data.get("progressionTable") or []:
        if not isinstance(row, dict):
            continue
        unlock_ids = row.get("unlockIds") if isinstance(row.get("unlockIds"), list) else []
        feature_labels = row.get("features") if isinstance(row.get("features"), list) else []
        for index, unlock_id in enumerate(unlock_ids):
            if not _non_empty_text(unlock_id):
                continue
            label = str(feature_labels[index] if index < len(feature_labels) else "").strip()
            if label:
                names[str(unlock_id).strip()] = label
    return names


def _highest_slot_level(slot_table: dict[str, Any]) -> int:
    highest = 0
    ordinal_to_level = {
        "1st": 1,
        "2nd": 2,
        "3rd": 3,
        "4th": 4,
        "5th": 5,
        "6th": 6,
        "7th": 7,
        "8th": 8,
        "9th": 9,
    }
    for row in slot_table.values():
        if not isinstance(row, dict):
            continue
        for raw_level, raw_count in row.items():
            if not raw_count:
                continue
            level = ordinal_to_level.get(str(raw_level).strip().lower())
            if level is None:
                digits = "".join(ch for ch in str(raw_level) if ch.isdigit())
                level = int(digits) if digits else 0
            highest = max(highest, level)
    return highest


def _has_full_level_coverage(slot_table: dict[str, Any], *, start_level: int) -> bool:
    levels = {int(level) for level in slot_table if str(level).isdigit()}
    return all(level in levels for level in range(start_level, 21))


def _has_resource_mechanics_at_level(class_data: dict[str, Any], level: int) -> bool:
    for row in class_data.get("progressionTable") or []:
        if not isinstance(row, dict) or row.get("level") != level:
            continue
        mechanics = row.get("classMechanics") if isinstance(row.get("classMechanics"), dict) else {}
        if any(key in mechanics and mechanics.get(key) not in (None, "", 0, "0", []) for key in RESOURCE_MECHANIC_KEYS):
            return True
    return False


@pytest.mark.parametrize("class_path", _class_files(), ids=lambda path: path.stem)
def test_class_json_has_required_top_level_fields(class_path: Path):
    class_data = _load_json(class_path)

    assert _non_empty_text(class_data.get("id")), f"{class_path} missing non-empty id"
    assert _non_empty_text(class_data.get("name")) or _non_empty_text(class_data.get("displayName")), (
        f"{class_path} missing name/displayName"
    )
    assert isinstance(class_data.get("hitDie"), int) and class_data["hitDie"] > 0, (
        f"{class_path} missing positive hitDie"
    )
    assert isinstance(class_data.get("progressionTable"), list) and class_data["progressionTable"], (
        f"{class_path} missing progressionTable"
    )
    assert isinstance(class_data.get("featureDefinitions"), dict) and class_data["featureDefinitions"], (
        f"{class_path} missing featureDefinitions object"
    )


@pytest.mark.parametrize("class_path", _class_files(), ids=lambda path: path.stem)
def test_class_progression_table_is_complete_and_unlocks_are_defined(class_path: Path):
    class_data = _load_json(class_path)
    feature_definitions = class_data.get("featureDefinitions") or {}
    table = class_data.get("progressionTable") or []
    failures: list[str] = []

    levels = [row.get("level") for row in table if isinstance(row, dict)]
    missing_levels = [level for level in range(1, 21) if level not in levels]
    duplicate_levels = sorted({level for level in levels if levels.count(level) > 1})
    if missing_levels:
        failures.append(f"missing levels {missing_levels}")
    if duplicate_levels:
        failures.append(f"duplicate levels {duplicate_levels}")

    for expected_level in range(1, 21):
        row = next((candidate for candidate in table if isinstance(candidate, dict) and candidate.get("level") == expected_level), None)
        if row is None:
            continue
        if row.get("level") != expected_level:
            failures.append(f"level {expected_level}: missing exact level number")
        if not isinstance(row.get("unlockIds"), list):
            failures.append(f"level {expected_level}: unlockIds must be a list")
            continue
        for unlock_id in row.get("unlockIds") or []:
            if not _non_empty_text(unlock_id):
                failures.append(f"level {expected_level}: blank unlockId")
                continue
            if unlock_id not in feature_definitions and str(unlock_id).strip().lower() not in KNOWN_SHARED_FEATURE_IDS:
                failures.append(f"level {expected_level}: unlockId {unlock_id!r} has no feature definition")

    assert not failures, f"{class_path} progression integrity failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("class_path", _class_files(), ids=lambda path: path.stem)
def test_class_feature_definitions_are_well_formed_and_resource_metadata_is_complete(class_path: Path):
    class_data = _load_json(class_path)
    failures: list[str] = []

    progression_names = _progression_feature_names_by_unlock_id(class_data)

    for feature_id, feature in (class_data.get("featureDefinitions") or {}).items():
        if not isinstance(feature, dict):
            failures.append(f"{feature_id}: feature definition must be an object, got {type(feature).__name__}")
            continue
        if str(feature.get("id") or feature_id).strip() != str(feature_id).strip():
            failures.append(f"{feature_id}: id must match featureDefinitions key")
        if not _feature_name(feature, progression_names.get(str(feature_id).strip(), "")):
            failures.append(f"{feature_id}: missing name/displayName and no matching progression feature label")
        # TODO(native-rules): every authored feature should carry player-facing
        # effect text so runtime cards do not have to invent placeholder copy.
        if not any(_non_empty_text(feature.get(key)) for key in ("summary", "description", "effect")):
            failures.append(f"{feature_id}: missing summary/description/effect text")

        tracks_uses = bool(feature.get("trackUses")) or any(_non_empty_text(feature.get(key)) for key in RESOURCE_KEYS)
        if tracks_uses:
            has_resource_name = any(_non_empty_text(feature.get(key)) for key in RESOURCE_KEYS)
            has_use_limit = any(feature.get(key) not in (None, "", []) for key in USE_LIMIT_KEYS)
            has_recovery = any(feature.get(key) not in (None, "", []) for key in RECOVERY_KEYS)
            if not has_resource_name:
                failures.append(f"{feature_id}: usage-tracked feature missing resourceName/resourceId")
            if not has_use_limit:
                failures.append(f"{feature_id}: usage-tracked feature missing max/uses/scaling/usage metadata")
            if not has_recovery:
                failures.append(f"{feature_id}: usage-tracked feature missing recovery/recharge metadata")

    assert not failures, f"{class_path} feature definition integrity failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("class_path", _class_files(), ids=lambda path: path.stem)
def test_subclass_gates_are_declared_for_classes_with_subclasses(class_path: Path):
    catalog = load_rules_catalog()
    class_data = _load_json(class_path)
    class_id = str(class_data.get("id") or "").strip().lower()
    subclasses = catalog.get("subclassesByClass", {}).get(class_id) or []
    if not subclasses:
        pytest.skip(f"{class_id} has no subclass rows")

    subclass_level = class_data.get("subclassLevel")
    assert isinstance(subclass_level, int) and 1 <= subclass_level <= 20, (
        f"{class_path} must declare a 1-20 subclassLevel when subclasses exist"
    )
    gate_row = next(
        (row for row in class_data.get("progressionTable") or [] if isinstance(row, dict) and row.get("level") == subclass_level),
        None,
    )
    assert gate_row is not None, f"{class_path} has subclassLevel {subclass_level} but no progression row"
    gate_unlocks = [str(item).lower() for item in (gate_row.get("unlockIds") or [])]
    gate_names = [str(item).lower() for item in (gate_row.get("features") or [])]
    assert any("subclass" in item or "archetype" in item or "oath" in item or "patron" in item or "college" in item for item in gate_unlocks + gate_names), (
        f"{class_path} subclass gate level {subclass_level} must include an explicit subclass unlock"
    )


@pytest.mark.parametrize("subclass_path", _subclass_files(), ids=lambda path: path.stem)
def test_subclass_feature_unlocks_reference_existing_subclass_features(subclass_path: Path):
    subclass_data = _load_json(subclass_path)
    feature_definitions = subclass_data.get("featureDefinitions") or {}
    features = subclass_data.get("features") if isinstance(subclass_data.get("features"), list) else []
    feature_ids = {
        str(row.get("id") or "").strip()
        for row in features
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    failures: list[str] = []

    assert _non_empty_text(subclass_data.get("id")), f"{subclass_path} missing id"
    assert _non_empty_text(subclass_data.get("classId")), f"{subclass_path} missing classId"
    assert isinstance(subclass_data.get("featureUnlocksByLevel"), dict) and subclass_data["featureUnlocksByLevel"], (
        f"{subclass_path} missing featureUnlocksByLevel"
    )

    for raw_level, unlock_ids in (subclass_data.get("featureUnlocksByLevel") or {}).items():
        if not str(raw_level).isdigit() or not 1 <= int(raw_level) <= 20:
            failures.append(f"level key {raw_level!r} must be an integer string from 1-20")
        if not isinstance(unlock_ids, list):
            failures.append(f"level {raw_level}: unlock list must be a list")
            continue
        for unlock_id in unlock_ids:
            if not _non_empty_text(unlock_id):
                failures.append(f"level {raw_level}: blank unlockId")
                continue
            if unlock_id not in feature_definitions and unlock_id not in feature_ids:
                failures.append(f"level {raw_level}: unlockId {unlock_id!r} has no subclass feature definition")

    assert not failures, f"{subclass_path} subclass unlock integrity failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("class_path", _class_files(), ids=lambda path: path.stem)
def test_spellcasting_progression_matches_declared_casting_type(class_path: Path):
    class_data = _load_json(class_path)
    class_id = class_data.get("id")
    casting_type = str(class_data.get("spellcastingType") or "").strip().lower()
    slot_table = class_data.get("spellSlots") if isinstance(class_data.get("spellSlots"), dict) else {}
    pact_magic = class_data.get("pactMagic") if isinstance(class_data.get("pactMagic"), dict) else {}

    assert casting_type in {"none", "full", "half", "pact"}, f"{class_path} has invalid spellcastingType {casting_type!r}"

    if casting_type == "none":
        assert not slot_table, f"{class_id} is non-caster but declares spellSlots"
        assert not pact_magic, f"{class_id} is non-caster but declares pactMagic"
        return

    assert _non_empty_text(class_data.get("spellcastingAbility")), f"{class_id} caster missing spellcastingAbility"

    if casting_type == "pact":
        assert class_id == "warlock", f"Only warlock should use pact casting, got {class_id}"
        assert pact_magic, f"{class_id} pact caster missing pactMagic"
        assert not slot_table, f"{class_id} pact caster must not use the full/half spellSlots table"
        slots_per_level = pact_magic.get("slotsPerLevel") if isinstance(pact_magic.get("slotsPerLevel"), dict) else {}
        slot_level = pact_magic.get("slotLevel") if isinstance(pact_magic.get("slotLevel"), dict) else {}
        assert _has_full_level_coverage(slots_per_level, start_level=1), f"{class_id} pactMagic.slotsPerLevel must cover levels 1-20"
        assert _has_full_level_coverage(slot_level, start_level=1), f"{class_id} pactMagic.slotLevel must cover levels 1-20"
        assert max(int(value) for value in slot_level.values()) <= PACT_CASTER_MAX_SLOT_LEVEL, (
            f"{class_id} pact slot level must cap at {PACT_CASTER_MAX_SLOT_LEVEL}"
        )
        assert _non_empty_text(pact_magic.get("recoveryType")), f"{class_id} pactMagic missing recoveryType"
        return

    assert slot_table, f"{class_id} {casting_type} caster missing spellSlots"
    if casting_type == "full":
        assert _has_full_level_coverage(slot_table, start_level=1), f"{class_id} full caster spellSlots must cover levels 1-20"
        assert _highest_slot_level(slot_table) == FULL_CASTER_MAX_SLOT_LEVEL, (
            f"{class_id} full caster should progress to {FULL_CASTER_MAX_SLOT_LEVEL}th-level slots"
        )
    elif casting_type == "half":
        assert _highest_slot_level(slot_table) <= HALF_CASTER_MAX_SLOT_LEVEL, (
            f"{class_id} half caster must not receive full-caster slots above {HALF_CASTER_MAX_SLOT_LEVEL}th level"
        )


@pytest.mark.parametrize("class_path", _class_files(), ids=lambda path: path.stem)
def test_runtime_resolves_core_surface_for_each_class_at_audit_levels(class_path: Path):
    catalog = load_rules_catalog()
    class_data = _load_json(class_path)
    class_id = str(class_data.get("id") or "").strip().lower()
    subclass_rows = catalog.get("subclassesByClass", {}).get(class_id) or []
    subclass_id = str((subclass_rows[0] or {}).get("id") or "").strip() if subclass_rows else ""
    for level in AUDIT_LEVELS:
        expects_resources = _has_resource_mechanics_at_level(class_data, level)
        document = {
            "identity": {"name": f"{class_id.title()} Integrity {level}"},
            "classes": [{"classId": class_id, "level": level, "subclassId": subclass_id}],
            "abilities": {
                "scores": {"str": 16, "dex": 16, "con": 14, "int": 16, "wis": 16, "cha": 16}
            },
            "spellState": {"known": ["fire-bolt", "mage-hand", "magic-missile"], "prepared": ["magic-missile"]},
        }
        runtime = resolve_runtime(document)["runtime"]

        assert isinstance(runtime.get("classDisplay"), dict), f"{class_id} level {level} missing classDisplay"
        assert runtime.get("levelTotal") == level, f"{class_id} level {level} incorrect levelTotal"
        assert isinstance(runtime.get("proficiencyBonus"), int) and runtime["proficiencyBonus"] >= 2, (
            f"{class_id} level {level} missing proficiency bonus"
        )
        assert isinstance(runtime.get("hp"), dict) and runtime["hp"].get("max", 0) > 0, (
            f"{class_id} level {level} missing positive hp"
        )
        assert isinstance(runtime.get("ac"), int) and runtime["ac"] > 0, f"{class_id} level {level} missing ac"
        assert isinstance(runtime.get("classFeatures"), list) and runtime["classFeatures"], (
            f"{class_id} level {level} missing resolved class features"
        )
        for key in ("actions", "bonusActions", "reactions", "resources"):
            assert isinstance(runtime.get(key), list), f"{class_id} level {level} runtime.{key} must be a list"
        if expects_resources:
            assert runtime.get("resources"), f"{class_id} level {level} should expose resource rows"
