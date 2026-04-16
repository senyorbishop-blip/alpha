from server.character.resolver import resolve_character_runtime
from server.character.summon_catalog import get_summon_template
from server.character.summon_runtime import build_summon_runtime_payload
from server.character.summon_state import normalize_summon_state
from server.session import Session, User


def _seed_player_with_tinker_artillerist_profile(session: Session, player: User):
    owner_key = player.name.strip().lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-artillerist",
                "name": "Rook",
                "nativeCharacter": {
                    "classes": [{"classId": "tinker", "level": 6, "subclassId": "artillerist"}],
                    "abilities": {"scores": {"int": 18}},
                    "summons": {
                        "unlockedTemplates": ["tinker-artillerist-arc-cannon"],
                        "selectedVariants": {"tinker-artillerist-cannon": "tinker-artillerist-arc-cannon"},
                        "activeSummons": [],
                    },
                },
                "nativeRuntime": {},
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-artillerist"}


def test_arc_cannon_template_is_non_creature_deployed_device():
    template = get_summon_template("tinker-artillerist-arc-cannon")
    assert isinstance(template, dict)
    assert template.get("isCreature") is False
    assert template.get("entityKind") == "device"
    assert template.get("actionSurfaceType") == "deployed_field_device"
    assert bool((template.get("placementRules") or {}).get("stationary")) is True


def test_artillerist_runtime_deploys_stationary_non_creature_field_entity():
    session = Session(id="TESTPASSJ")
    player = User(id="u-player", name="Rook", role="player")
    session.users[player.id] = player
    _seed_player_with_tinker_artillerist_profile(session, player)

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-artillerist",
            "summon_template_id": "tinker-artillerist-arc-cannon",
            "selected_variant": "tinker-artillerist-arc-cannon",
        },
    )
    assert result.get("ok") is True
    actor = result.get("actor") or {}
    assert actor.get("isCreature") is False
    assert actor.get("entityKind") == "device"
    assert (actor.get("movement") or {}).get("walk") == 0
    assert bool((actor.get("interactionModel") or {}).get("stationary")) is True

    token_payload = result.get("token_payload") or {}
    assert token_payload.get("monster_type") == "device"
    assert int(token_payload.get("speed") or 0) == 0


def test_runtime_summon_actions_mark_non_creature_entries_and_keep_creature_entries():
    artillerist_doc = {
        "classes": [{"classId": "tinker", "level": 6, "subclassId": "artillerist"}],
        "abilities": {"scores": {"int": 18}},
        "summons": {
            "unlockedTemplates": ["tinker-artillerist-arc-cannon"],
            "selectedVariants": {"tinker-artillerist-cannon": "tinker-artillerist-arc-cannon"},
            "activeSummons": [],
        },
    }
    artillerist_runtime = resolve_character_runtime(artillerist_doc).get("runtime") or {}
    artillerist_rows = artillerist_runtime.get("summonActions") or []
    assert len(artillerist_rows) == 1
    assert artillerist_rows[0].get("actionType") == "Deploy"
    assert artillerist_rows[0].get("isCreature") is False
    assert artillerist_rows[0].get("entityKind") == "device"

    ranger_doc = {
        "classes": [{"classId": "ranger", "level": 6, "subclassId": "beast-master"}],
        "abilities": {"scores": {"wis": 16, "con": 14}},
        "summons": {
            "unlockedTemplates": ["ranger-primal-beast-land"],
            "selectedVariants": {"ranger-primal-beast": "ranger-primal-beast-land"},
            "activeSummons": [],
        },
    }
    ranger_runtime = resolve_character_runtime(ranger_doc).get("runtime") or {}
    ranger_rows = ranger_runtime.get("summonActions") or []
    assert len(ranger_rows) == 1
    assert ranger_rows[0].get("actionType") == "Summon"
    assert ranger_rows[0].get("isCreature") is True
    assert ranger_rows[0].get("entityKind") == "creature"


def test_summon_state_normalizer_preserves_non_creature_fields():
    normalized = normalize_summon_state(
        {
            "activeSummons": [
                {
                    "id": "arc-1",
                    "templateId": "tinker-artillerist-arc-cannon",
                    "tokenId": "tok-arc",
                    "entityKind": "device",
                    "isCreature": False,
                    "actionSurfaceType": "deployed_field_device",
                    "placementRules": {"stationary": True},
                    "interactionModel": {"triggerable": True},
                    "cleanupPolicy": {"onDismiss": "remove_token"},
                }
            ]
        }
    )
    row = (normalized.get("activeSummons") or [])[0]
    assert row.get("entityKind") == "device"
    assert row.get("isCreature") is False
    assert bool((row.get("placementRules") or {}).get("stationary")) is True
