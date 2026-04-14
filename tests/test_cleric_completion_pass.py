import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_cleric_subclass_files_are_valid_json_and_unlock_ids_match_features():
    for rel in [
        "server/data/rules/5e2024/subclasses/life-domain.json",
        "server/data/rules/5e2024/subclasses/light-domain.json",
        "server/data/rules/5e2024/subclasses/trickery-domain.json",
        "server/data/rules/5e2024/subclasses/war-domain.json",
    ]:
        row = _load(rel)
        feature_ids = {str(f.get("id")) for f in (row.get("features") or []) if isinstance(f, dict) and f.get("id")}
        unlock_ids = {
            str(fid)
            for unlocks in (row.get("featureUnlocksByLevel") or {}).values()
            if isinstance(unlocks, list)
            for fid in unlocks
            if str(fid).strip()
        }
        assert unlock_ids <= feature_ids, f"{rel} has unlock IDs that do not map to feature rows"


def test_cleric_domain_feature_definitions_match_subclass_feature_ids():
    for rel in [
        "server/data/rules/5e2024/subclasses/life-domain.json",
        "server/data/rules/5e2024/subclasses/light-domain.json",
        "server/data/rules/5e2024/subclasses/trickery-domain.json",
        "server/data/rules/5e2024/subclasses/war-domain.json",
    ]:
        row = _load(rel)
        feature_ids = {str(f.get("id")) for f in (row.get("features") or []) if isinstance(f, dict) and f.get("id")}
        definition_ids = set((row.get("featureDefinitions") or {}).keys())
        assert feature_ids <= definition_ids, f"{rel} has feature rows without detailed feature definitions"


def test_cleric_progression_unlock_ids_have_authored_definitions_and_channel_scaling():
    cleric = _load("server/data/rules/5e2024/classes/cleric.json")
    defs = cleric.get("featureDefinitions") or {}
    table = cleric.get("progressionTable") or []

    for row in table:
        unlocks = row.get("unlockIds") or []
        for feature_id in unlocks:
            assert feature_id in defs, f"Missing cleric featureDefinitions entry for unlock ID: {feature_id}"

    channel_by_level = {
        int(row.get("level")): int((row.get("classMechanics") or {}).get("channelDivinityUses", 0))
        for row in table
        if isinstance(row, dict)
    }
    assert channel_by_level[2] == 1
    assert channel_by_level[6] == 2
    assert channel_by_level[18] == 3
