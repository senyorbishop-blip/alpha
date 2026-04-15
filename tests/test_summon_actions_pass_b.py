from pathlib import Path

from server.character.resolver import resolve_character_runtime


def _summon_actions(document: dict) -> list[dict]:
    resolved = resolve_character_runtime(document)
    runtime = resolved.get("runtime") if isinstance(resolved.get("runtime"), dict) else {}
    return runtime.get("summonActions") if isinstance(runtime.get("summonActions"), list) else []


def test_warlock_chain_pact_exposes_summon_action_row():
    actions = _summon_actions(
        {
            "classes": [
                {
                    "classId": "warlock",
                    "level": 3,
                    "selectedFeatures": [{"id": "warlock-pact-boon", "selectedChoice": "pact-of-the-chain"}],
                }
            ],
            "abilities": {"scores": {"cha": 16}},
        }
    )
    assert actions, "Expected at least one summon action row for Pact of the Chain."
    row = actions[0]
    assert row.get("sourceFeatureId") == "warlock-pact-boon"
    assert row.get("actionType") == "Summon"
    assert row.get("summonGroupId") == "warlock-pact-chain-familiar"
    assert len(row.get("variants") or []) >= 4


def test_beast_master_exposes_variant_readable_summon_action_row():
    actions = _summon_actions(
        {
            "classes": [
                {
                    "classId": "ranger",
                    "level": 3,
                    "subclassId": "beast-master",
                    "selectedFeatures": [
                        {"id": "beast-master-rangers-companion", "selectedChoice": "ranger-primal-beast-sky"},
                    ],
                }
            ],
            "abilities": {"scores": {"dex": 16, "wis": 14}},
        }
    )
    assert len(actions) == 1
    row = actions[0]
    variant_names = {str(v.get("displayName") or "").lower() for v in (row.get("variants") or [])}
    assert "primal beast of the land" in variant_names
    assert "primal beast of the sea" in variant_names
    assert "primal beast of the sky" in variant_names
    assert row.get("selectedVariantId") == "ranger-primal-beast-sky"


def test_tinker_subclasses_expose_deploy_rows():
    mechanist_actions = _summon_actions(
        {
            "classes": [{"classId": "tinker", "level": 3, "subclassId": "mechanist"}],
            "abilities": {"scores": {"int": 16}},
        }
    )
    assert any(row.get("summonTemplateId") == "tinker-mechanist-companion-frame" for row in mechanist_actions)

    artillerist_actions = _summon_actions(
        {
            "classes": [{"classId": "tinker", "level": 3, "subclassId": "artillerist"}],
            "abilities": {"scores": {"int": 16}},
        }
    )
    assert any(row.get("summonTemplateId") == "tinker-artillerist-arc-cannon" for row in artillerist_actions)


def test_non_summon_class_has_no_summon_actions():
    actions = _summon_actions(
        {
            "classes": [{"classId": "fighter", "level": 5, "subclassId": "champion"}],
            "abilities": {"scores": {"str": 16, "con": 14}},
        }
    )
    assert actions == []


def test_actions_tab_beast_master_summon_button_calls_runtime_request():
    src = Path("client/static/js/character/tabs/actions_tab.js").read_text(encoding="utf-8")
    assert "summon_runtime_request" in src
    assert "runtime path is not live for this class yet" in src
    assert "summon runtime not implemented yet" not in src.lower()
