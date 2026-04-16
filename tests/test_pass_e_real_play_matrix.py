from __future__ import annotations

import pytest

from server.character.service import apply_character_levelup, preview_levelup, resolve_runtime


LIVE_CLASS_MATRIX = [
    ("barbarian", "berserker", False),
    ("bard", "college-of-lore", True),
    ("cleric", "life-domain", True),
    ("druid", "circle-of-the-land", True),
    ("fighter", "battlemaster", False),
    ("monk", "way-of-the-open-hand", False),
    ("paladin", "oath-of-devotion", True),
    ("ranger", "hunter", True),
    ("rogue", "thief", False),
    ("sorcerer", "draconic-bloodline", True),
    ("warlock", "fiend-patron", True),
    ("wizard", "evoker", True),
    ("tinker", "mechanist", True),
    ("pirate", "corsair", False),
]


SUMMON_DEPLOY_CASES = [
    (
        "ranger",
        "beast-master",
        [],
        "ranger-primal-beast",
    ),
    (
        "warlock",
        "fiend-patron",
        [{"id": "warlock-pact-boon", "selectedChoice": "pact-of-the-chain"}],
        "warlock-pact-chain-familiar",
    ),
    (
        "tinker",
        "mechanist",
        [],
        "tinker-mechanist-frame",
    ),
]


def _doc_for(class_id: str, subclass_id: str, *, level: int = 5, selected_features: list[dict] | None = None) -> dict:
    return {
        "identity": {"name": f"{class_id.title()} Audit"},
        "classes": [
            {
                "classId": class_id,
                "level": level,
                "subclassId": subclass_id,
                "selectedFeatures": list(selected_features or []),
            }
        ],
        "abilities": {
            "scores": {
                "str": 16,
                "dex": 16,
                "con": 14,
                "int": 14,
                "wis": 14,
                "cha": 16,
            }
        },
        "spellState": {
            "known": ["fire-bolt", "mage-hand", "magic-missile", "shield"],
            "prepared": ["magic-missile", "shield"],
        },
    }


def _auto_apply_choices(preview: dict, *, subclass_id: str = "") -> dict:
    feature_choices: dict[str, str] = {}
    feature_rows_by_id = {
        str((row or {}).get("id") or "").strip(): row
        for row in (preview.get("newFeatures") or [])
        if isinstance(row, dict) and str((row or {}).get("id") or "").strip()
    }
    for row in preview.get("requiredChoices") or []:
        if not isinstance(row, dict) or row.get("type") != "feature_choice":
            continue
        options = row.get("choices") if isinstance(row.get("choices"), list) else []
        if not options:
            feature_row = feature_rows_by_id.get(str(row.get("id") or "").strip()) or {}
            options = feature_row.get("choices") if isinstance(feature_row.get("choices"), list) else []
        if not options:
            continue
        first = options[0] if isinstance(options[0], dict) else {}
        choice_id = str(first.get("id") or "").strip()
        if choice_id:
            feature_choices[str(row.get("id") or "").strip()] = choice_id

    spell_choices = preview.get("spellChoices") if isinstance(preview.get("spellChoices"), dict) else {}
    cantrip_needed = int(spell_choices.get("cantripPicksRequired") or 0)
    levelled_needed = int(spell_choices.get("levelledPicksRequired") or 0)
    cantrip_options = [
        str((row or {}).get("id") or "").strip()
        for row in (spell_choices.get("cantripOptions") or [])
        if isinstance(row, dict)
    ]
    levelled_options = [
        str((row or {}).get("id") or "").strip()
        for row in (spell_choices.get("levelledOptions") or [])
        if isinstance(row, dict)
    ]

    choice_payload = {
        "featureChoices": feature_choices,
        "spellChoices": {
            "cantripAdds": [spell_id for spell_id in cantrip_options[:cantrip_needed] if spell_id],
            "levelledAdds": [spell_id for spell_id in levelled_options[:levelled_needed] if spell_id],
            "swap": {},
        },
    }
    for row in preview.get("requiredChoices") or []:
        if not isinstance(row, dict) or str(row.get("type") or "").strip().lower() != "subclass":
            continue
        if subclass_id:
            choice_payload["subclassChoice"] = subclass_id
    return choice_payload


@pytest.mark.parametrize("class_id,subclass_id,is_caster", LIVE_CLASS_MATRIX)
def test_pass_e_live_class_first_turn_and_loop_matrix(class_id: str, subclass_id: str, is_caster: bool):
    runtime = resolve_runtime(_doc_for(class_id, subclass_id))["runtime"]

    first_turn_options = []
    for key in ("actions", "bonusActions", "reactions", "summonActions"):
        rows = runtime.get(key) if isinstance(runtime.get(key), list) else []
        first_turn_options.extend(rows)

    assert first_turn_options, f"{class_id} lacks any first-turn actionable surface"
    assert runtime.get("classFeatures"), f"{class_id} should surface class loop context"

    for resource in runtime.get("resources") or []:
        if not isinstance(resource, dict):
            continue
        assert resource.get("name")
        if resource.get("max") is not None:
            assert int(resource.get("max")) >= 0
        if resource.get("current") is not None:
            assert int(resource.get("current")) >= 0

    spell_access = runtime.get("spellAccess") if isinstance(runtime.get("spellAccess"), dict) else {}
    if is_caster:
        assert spell_access.get("ability"), f"{class_id} should expose spellcasting ability"
        assert spell_access.get("saveDc") is not None
        assert spell_access.get("attackBonus") is not None


@pytest.mark.parametrize("class_id,subclass_id,selected_features,expected_group", SUMMON_DEPLOY_CASES)
def test_pass_e_summon_and_deploy_paths_surface_live_actions(class_id, subclass_id, selected_features, expected_group):
    runtime = resolve_runtime(
        _doc_for(class_id, subclass_id, selected_features=selected_features)
    )["runtime"]

    summon_actions = runtime.get("summonActions") if isinstance(runtime.get("summonActions"), list) else []
    assert summon_actions, f"{class_id}/{subclass_id} should surface summon/deploy action"
    assert any(str(row.get("summonGroupId") or "") == expected_group for row in summon_actions if isinstance(row, dict))


@pytest.mark.parametrize(
    "class_id,subclass_id",
    [
        ("barbarian", "berserker"),
        ("wizard", "evoker"),
        ("ranger", "hunter"),
    ],
)
def test_pass_e_levelup_continuation_preserves_runtime_playability(class_id: str, subclass_id: str):
    base_doc = _doc_for(class_id, subclass_id, level=4)
    before = resolve_runtime(base_doc)["runtime"]
    preview = preview_levelup(base_doc)

    applied = apply_character_levelup(base_doc, choices=_auto_apply_choices(preview, subclass_id=subclass_id))
    new_doc = applied["document"]
    after = resolve_runtime(new_doc)["runtime"]

    assert int((new_doc.get("classes") or [{}])[0].get("level") or 0) == 5
    assert (before.get("hp") or {}).get("max") is not None
    assert (after.get("hp") or {}).get("max") is not None

    first_turn_options_after = []
    for key in ("actions", "bonusActions", "reactions", "summonActions"):
        rows = after.get(key) if isinstance(after.get(key), list) else []
        first_turn_options_after.extend(rows)
    assert first_turn_options_after, f"{class_id} became unplayable after level-up"


def test_pass_e_resource_dedup_prevents_duplicate_first_turn_resource_cards():
    runtime = resolve_runtime(_doc_for("fighter", "battlemaster", level=5))["runtime"]
    names = [str(row.get("name") or "").strip().lower() for row in (runtime.get("resources") or []) if isinstance(row, dict)]

    assert names.count("second wind") == 1
    assert names.count("action surge") == 1
