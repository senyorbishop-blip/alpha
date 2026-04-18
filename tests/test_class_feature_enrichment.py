import json
from pathlib import Path


CLASS_FILES = {
    "fighter": Path("server/data/rules/5e2024/classes/fighter.json"),
    "wizard": Path("server/data/rules/5e2024/classes/wizard.json"),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_enriched_classes_define_every_progression_unlock_id():
    for class_id, path in CLASS_FILES.items():
        data = _load(path)
        definitions = set((data.get("featureDefinitions") or {}).keys())

        missing = []
        for row in (data.get("progressionTable") or []):
            for unlock_id in (row.get("unlockIds") or []):
                if unlock_id not in definitions:
                    missing.append(unlock_id)

        assert not missing, f"{class_id} missing definitions: {sorted(set(missing))}"


def test_enriched_new_feature_definitions_include_player_facing_text():
    checks = {
        "fighter": [
            "fighter-extra-attack-4",
            "fighter-action-surge-2-uses",
            "fighter-subclass-capstone",
            "fighter-epic-boon",
        ],
        "wizard": [
            "wizard-spell-level-9",
            "wizard-subclass-feature-14",
            "wizard-cantrips-known-5",
            "wizard-epic-boon",
        ],
    }

    for class_id, ids in checks.items():
        data = _load(CLASS_FILES[class_id])
        definitions = data.get("featureDefinitions") or {}
        for feature_id in ids:
            row = definitions.get(feature_id) or {}
            assert row.get("summary"), f"{feature_id} should include a summary"
            assert row.get("description"), f"{feature_id} should include a description"
            assert row.get("tags"), f"{feature_id} should include tags"
