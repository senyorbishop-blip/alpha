import json
import subprocess
import sys

from server.character.summon_state import SUMMON_DEPLOY_SCHEMA_VERSION, normalize_summon_state


def test_pass_o_normalizes_single_legacy_deployment_slot_into_collection():
    state = normalize_summon_state(
        {
            "activeDeployment": {
                "id": "legacy-deploy-1",
                "deployableTemplateId": "tinker-artillerist-arc-cannon",
                "variantGroup": "tinker-artillerist-cannon",
                "token_id": "tok-cannon-1",
                "ownerId": "user-1",
                "profileId": "profile-artillerist",
                "commandModel": "action_command",
                "actorType": "deployable",
            }
        }
    )
    rows = state.get("activeSummons") or []
    assert len(rows) == 1
    row = rows[0]
    assert row["templateId"] == "tinker-artillerist-arc-cannon"
    assert row["summonGroupId"] == "tinker-artillerist-cannon"
    assert row["entityKind"] == "deployable"
    assert row["tokenId"] == "tok-cannon-1"
    assert "activeDeployment_single_upgraded" in ((state.get("migration") or {}).get("legacyUpgradesApplied") or [])


def test_pass_o_idempotent_for_current_state_payload():
    src = {
        "deploySchemaVersion": SUMMON_DEPLOY_SCHEMA_VERSION,
        "activeSummons": [
            {
                "id": "active-1",
                "templateId": "ranger-primal-beast-land",
                "summonGroupId": "ranger-primal-beast",
                "tokenId": "tok-1",
                "ownerUserId": "u1",
                "ownerProfileId": "profile-ranger",
                "entityKind": "creature",
                "status": "active",
            }
        ],
        "migration": {
            "normalizerVersion": SUMMON_DEPLOY_SCHEMA_VERSION,
            "legacyUpgradesApplied": [],
            "quarantinedCount": 0,
        },
    }
    first = normalize_summon_state(src)
    second = normalize_summon_state(first)
    assert first == second


def test_pass_o_quarantines_unsalvageable_legacy_rows():
    state = normalize_summon_state(
        {
            "activeEntities": [
                {"legacy": "missing identity"},
                {"id": "legacy-2", "state": "active"},
            ]
        }
    )
    assert state.get("activeSummons") == []
    quarantined = state.get("quarantinedSummons") or []
    assert len(quarantined) == 2
    reasons = {str(row.get("reason") or "") for row in quarantined if isinstance(row, dict)}
    assert "missing_identity" in reasons
    assert "missing_template_and_token" in reasons


def test_pass_o_legacy_variant_and_source_fields_are_mapped():
    state = normalize_summon_state(
        {
            "activeSummons": [
                {
                    "id": "legacy-variant",
                    "template": "warlock-chain-quasit",
                    "groupId": "warlock-pact-chain-familiar",
                    "variant": "warlock-chain-quasit",
                    "sourceSpellId": "",
                    "featureId": "pact-of-the-chain",
                    "classId": "warlock",
                    "subclassId": "fiend",
                    "token": "tok-familiar",
                    "owner": {"userId": "u-warlock", "profileId": "profile-warlock"},
                }
            ]
        }
    )
    row = (state.get("activeSummons") or [])[0]
    assert row["sourceClassId"] == "warlock"
    assert row["sourceSubclassId"] == "fiend"
    assert row["sourceFeatureId"] == "pact-of-the-chain"
    assert row["variantId"] == "warlock-chain-quasit"


def test_pass_o_dry_run_tool_reports_upgrade_and_quarantine(tmp_path):
    payload = {
        "summons": {
            "activeDeployment": {
                "id": "legacy-ok",
                "deployableTemplateId": "tinker-artillerist-arc-cannon",
                "token": "tok-1",
            },
            "activeEntities": [{"legacyOnly": True}],
        }
    }
    src = tmp_path / "legacy.json"
    src.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "tools/summon_deploy_compat_report.py", "--input", str(src)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "legacyUpgradesApplied" in result.stdout
    assert "Quarantined entries" in result.stdout
