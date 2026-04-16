from server.character.summon_runtime import (
    build_summon_runtime_payload,
    register_active_summon,
    remove_active_summon,
    reconcile_native_summons,
    reconcile_session_active_summons,
    synchronize_active_summon_state,
)
from server.character.summon_state import normalize_summon_state
from server.session import Session, User, Token


def _seed_player_with_beast_master_profile(session: Session, player: User):
    owner_key = player.name.strip().lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-ranger",
                "name": "Mira",
                "nativeCharacter": {
                    "classes": [
                        {
                            "classId": "ranger",
                            "level": 5,
                            "subclassId": "beast-master",
                        }
                    ],
                    "abilities": {"scores": {"wis": 16, "con": 14}},
                    "summons": {
                        "unlockedTemplates": [
                            "ranger-primal-beast-land",
                            "ranger-primal-beast-sea",
                            "ranger-primal-beast-sky",
                        ],
                        "selectedVariants": {"ranger-primal-beast": "ranger-primal-beast-land"},
                        "activeSummons": [],
                    },
                },
                "nativeRuntime": {},
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-ranger"}


def _seed_player_with_warlock_profile(session: Session, player: User):
    owner_key = player.name.strip().lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-warlock",
                "name": "Vesper",
                "nativeCharacter": {
                    "classes": [{"classId": "warlock", "level": 5, "subclassId": "fiend"}],
                    "abilities": {"scores": {"cha": 18}},
                    "summons": {
                        "unlockedTemplates": [
                            "warlock-chain-imp",
                            "warlock-chain-pseudodragon",
                            "warlock-chain-quasit",
                            "warlock-chain-sprite",
                        ],
                        "selectedVariants": {"warlock-pact-chain-familiar": "warlock-chain-imp"},
                        "activeSummons": [],
                    },
                },
                "nativeRuntime": {},
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-warlock"}


def _seed_player_with_tinker_mechanist_profile(session: Session, player: User):
    owner_key = player.name.strip().lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-tinker",
                "name": "Brix",
                "nativeCharacter": {
                    "classes": [{"classId": "tinker", "level": 6, "subclassId": "mechanist"}],
                    "abilities": {"scores": {"int": 18}},
                    "summons": {
                        "unlockedTemplates": ["tinker-mechanist-companion-frame"],
                        "selectedVariants": {"tinker-mechanist-frame": "tinker-mechanist-companion-frame"},
                        "activeSummons": [],
                    },
                },
                "nativeRuntime": {},
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-tinker"}


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


def test_beast_master_runtime_resolves_land_sea_sky_variants_with_real_actor_payload():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_beast_master_profile(session, player)

    by_variant = {}
    for variant in ("ranger-primal-beast-land", "ranger-primal-beast-sea", "ranger-primal-beast-sky"):
        result = build_summon_runtime_payload(
            session=session,
            user=player,
            payload={
                "profile_id": "profile-ranger",
                "summon_template_id": variant,
                "selected_variant": variant,
            },
        )
        assert result.get("ok") is True
        actor = result.get("actor") or {}
        assert actor.get("name")
        assert actor.get("ac") >= 13
        assert (actor.get("hp") or {}).get("max", 0) > 0
        assert isinstance(actor.get("attacks"), list) and actor.get("attacks")
        by_variant[variant] = actor

    assert by_variant["ranger-primal-beast-land"]["movement"].get("climb") == 40
    assert by_variant["ranger-primal-beast-sea"]["movement"].get("swim") == 60
    assert by_variant["ranger-primal-beast-sky"]["movement"].get("fly") == 60


def test_runtime_payload_spawns_player_owned_companion_token_data_and_tracks_active_state():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_beast_master_profile(session, player)

    # Anchor token on active map to validate nearby placement fallback.
    session.tokens["tok-player"] = Token(
        id="tok-player",
        name="Ayla",
        x=300,
        y=300,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=player.id,
        token_type="player",
        map_context="world",
    )

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-ranger",
            "summon_template_id": "ranger-primal-beast-land",
            "selected_variant": "ranger-primal-beast-land",
        },
    )
    assert result.get("ok") is True

    token_payload = result.get("token_payload") or {}
    assert token_payload.get("owner_id") == player.id
    assert token_payload.get("token_type") == "companion"
    assert token_payload.get("map_context") == "world"
    assert token_payload.get("x") >= 300

    native = result.get("native_document") or {}
    active_entry = {
        "id": "summon-active",
        "variantId": "ranger-primal-beast-land",
        "source": {"variantGroup": "ranger-primal-beast"},
        "tokenId": "tok-companion",
    }
    updated = register_active_summon(native, active_entry)
    summons = (updated.get("summons") or {}) if isinstance(updated, dict) else {}
    active = summons.get("activeSummons") or []
    assert len(active) == 1
    assert active[0].get("tokenId") == "tok-companion"


def test_runtime_replaces_existing_active_summon_record_for_single_active_group():
    native = {
        "summons": {
            "activeSummons": [
                {
                    "id": "old",
                    "source": {"variantGroup": "ranger-primal-beast"},
                    "tokenId": "tok-old",
                }
            ],
            "selectedVariants": {"ranger-primal-beast": "ranger-primal-beast-land"},
        }
    }
    updated = register_active_summon(
        native,
        {
            "id": "new",
            "variantId": "ranger-primal-beast-sky",
            "source": {"variantGroup": "ranger-primal-beast"},
            "tokenId": "tok-new",
        },
    )
    active = ((updated.get("summons") or {}).get("activeSummons") or [])
    assert len(active) == 1
    assert active[0].get("id") == "new"
    assert ((updated.get("summons") or {}).get("selectedVariants") or {}).get("ranger-primal-beast") == "ranger-primal-beast-sky"


def test_runtime_fails_cleanly_for_invalid_variant_and_missing_map_context():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_beast_master_profile(session, player)

    invalid_variant = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-ranger",
            "summon_template_id": "ranger-primal-beast-sun",
            "selected_variant": "ranger-primal-beast-sun",
        },
    )
    assert invalid_variant.get("ok") is False
    assert invalid_variant.get("error") == "invalid_variant"

    missing_map = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-ranger",
            "summon_template_id": "ranger-primal-beast-land",
            "selected_variant": "ranger-primal-beast-land",
            "map_context": "",
        },
    )
    assert missing_map.get("ok") is False
    assert missing_map.get("error") == "missing_map_context"


def test_warlock_chain_runtime_resolves_all_familiar_variants_with_real_actor_payload():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_warlock_profile(session, player)

    for variant in ("warlock-chain-imp", "warlock-chain-pseudodragon", "warlock-chain-quasit", "warlock-chain-sprite"):
        result = build_summon_runtime_payload(
            session=session,
            user=player,
            payload={
                "profile_id": "profile-warlock",
                "summon_group_id": "warlock-pact-chain-familiar",
                "summon_template_id": variant,
                "selected_variant": variant,
            },
        )
        assert result.get("ok") is True
        assert (result.get("actor") or {}).get("summonCategory") == "familiar"
        assert (result.get("token_payload") or {}).get("token_type") == "companion"
        assert (result.get("token_payload") or {}).get("monster_type") == "familiar"


def test_tinker_mechanist_runtime_resolves_construct_payload():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_tinker_mechanist_profile(session, player)

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-tinker",
            "summon_group_id": "tinker-mechanist-frame",
            "summon_template_id": "tinker-mechanist-companion-frame",
            "selected_variant": "tinker-mechanist-companion-frame",
        },
    )
    assert result.get("ok") is True
    actor = result.get("actor") or {}
    assert actor.get("summonCategory") == "construct"


def test_tinker_artillerist_runtime_resolves_deployable_payload():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_tinker_artillerist_profile(session, player)

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-artillerist",
            "summon_group_id": "tinker-artillerist-cannon",
            "summon_template_id": "tinker-artillerist-arc-cannon",
            "selected_variant": "tinker-artillerist-arc-cannon",
        },
    )
    assert result.get("ok") is True
    actor = result.get("actor") or {}
    token_payload = result.get("token_payload") or {}
    assert actor.get("summonCategory") == "deployable"
    assert actor.get("commandModel") == "action_command"
    assert isinstance(actor.get("actions"), list) and actor.get("actions")
    assert token_payload.get("monster_type") == "deployable"
    assert isinstance(actor.get("attacks"), list) and actor.get("attacks")
    assert all(isinstance(row.get("id"), str) and row.get("id") for row in actor.get("actions"))
    assert all("classification" in row for row in actor.get("actions"))
    assert all("summary" in row for row in actor.get("actions"))
    assert isinstance(actor.get("traits"), list) and actor.get("traits")
    assert (result.get("token_payload") or {}).get("monster_type") == "deployable"


def test_non_live_paths_remain_non_live_in_runtime_service():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    owner_key = player.name.strip().lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-artillerist",
                "nativeCharacter": {
                    "classes": [{"classId": "fighter", "level": 6, "subclassId": "champion"}],
                    "summons": {"unlockedTemplates": ["tinker-artillerist-arc-cannon"], "selectedVariants": {}, "activeSummons": []},
                },
                "nativeRuntime": {},
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-artillerist"}

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-artillerist",
            "summon_group_id": "tinker-artillerist-cannon",
            "summon_template_id": "tinker-artillerist-arc-cannon",
            "selected_variant": "tinker-artillerist-arc-cannon",
        },
    )
    assert result.get("ok") is False
    assert result.get("error") == "tinker_artillerist_only"


def test_active_summon_state_normalizes_legacy_single_slot_record():
    summons = normalize_summon_state(
        {
            "activeSummon": {
                "id": "legacy-one",
                "summonTemplateId": "warlock-chain-imp",
                "tokenId": "tok-legacy",
                "source": {"variantGroup": "warlock-pact-chain-familiar", "featureId": "warlock-pact-boon"},
            }
        }
    )
    active = summons.get("activeSummons") or []
    assert len(active) == 1
    assert active[0].get("templateId") == "warlock-chain-imp"
    assert active[0].get("summonGroupId") == "warlock-pact-chain-familiar"
    assert active[0].get("sourceFeatureId") == "warlock-pact-boon"


def test_register_active_summon_respects_single_active_policy_per_group():
    native = {
        "summons": {
            "activeSummons": [
                {
                    "id": "old-a",
                    "templateId": "warlock-chain-imp",
                    "summonGroupId": "warlock-pact-chain-familiar",
                    "ownerProfileId": "profile-warlock",
                    "tokenId": "tok-old",
                }
            ]
        }
    }
    updated = register_active_summon(
        native,
        {
            "id": "new-a",
            "templateId": "warlock-chain-sprite",
            "summonGroupId": "warlock-pact-chain-familiar",
            "ownerProfileId": "profile-warlock",
            "tokenId": "tok-new",
        },
    )
    active = ((updated.get("summons") or {}).get("activeSummons") or [])
    assert len(active) == 1
    assert active[0].get("id") == "new-a"
    assert active[0].get("tokenId") == "tok-new"


def test_dismiss_removes_only_targeted_summon_entry():
    native = {
        "summons": {
            "activeSummons": [
                {"id": "keep", "tokenId": "tok-keep", "summonGroupId": "tinker-mechanist-frame", "ownerProfileId": "profile-tinker"},
                {"id": "drop", "tokenId": "tok-drop", "summonGroupId": "warlock-pact-chain-familiar", "ownerProfileId": "profile-tinker"},
            ]
        }
    }
    removed = remove_active_summon(native, active_id="drop", owner_profile_id="profile-tinker")
    remaining = ((native.get("summons") or {}).get("activeSummons") or [])
    assert len(removed) == 1
    assert removed[0].get("id") == "drop"
    assert len(remaining) == 1
    assert remaining[0].get("id") == "keep"


def test_reconcile_prunes_stale_or_duplicate_summon_links_without_token_spam():
    native = {
        "summons": {
            "activeSummons": [
                {"id": "a", "tokenId": "tok-a", "mapContext": "world"},
                {"id": "b", "tokenId": "tok-missing", "mapContext": "world"},
                {"id": "a", "tokenId": "tok-a", "mapContext": "world"},
                {"id": "c", "tokenId": "tok-c", "mapContext": "invalid-map"},
            ]
        }
    }
    reconcile_native_summons(native, existing_token_ids={"tok-a", "tok-c"}, valid_map_contexts={"world"})
    active = ((native.get("summons") or {}).get("activeSummons") or [])
    assert len(active) == 1
    assert active[0].get("id") == "a"
    assert active[0].get("tokenId") == "tok-a"


def test_session_reconcile_removes_stale_active_rows_after_restore():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_beast_master_profile(session, player)
    owner_key = player.name.strip().lower()
    profile = (session.char_profiles.get(owner_key) or [])[0]
    native = profile.get("nativeCharacter") or {}
    native["summons"]["activeSummons"] = [
        {"id": "exists", "tokenId": "tok-ok", "mapContext": "world"},
        {"id": "stale", "tokenId": "tok-missing", "mapContext": "world"},
    ]
    session.tokens["tok-ok"] = Token(
        id="tok-ok",
        name="Companion",
        x=0,
        y=0,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=player.id,
        token_type="companion",
        map_context="world",
    )
    changed = reconcile_session_active_summons(session)
    updated_active = (((session.char_profiles.get(owner_key) or [])[0].get("nativeCharacter") or {}).get("summons") or {}).get("activeSummons") or []
    assert changed == 1
    assert len(updated_active) == 1
    assert updated_active[0].get("id") == "exists"


def test_runtime_actions_include_combat_payload_fields_for_live_summons():
    session = Session(id="TESTSUMMON")
    player = User(id="u-player", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player_with_beast_master_profile(session, player)

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-ranger",
            "summon_template_id": "ranger-primal-beast-land",
            "selected_variant": "ranger-primal-beast-land",
        },
    )
    assert result.get("ok") is True
    actions = ((result.get("actor") or {}).get("actions") or [])
    assert actions
    first = actions[0]
    assert first.get("id")
    assert first.get("displayName")
    assert first.get("actionType")
    assert first.get("classification") in {"attack", "save", "utility", "support"}
    assert first.get("range")
    assert "summary" in first
    assert "commandRequired" in first


def test_synchronize_active_summon_state_updates_hp_and_handles_removal():
    native = {
        "summons": {
            "activeSummons": [
                {
                    "id": "active-1",
                    "tokenId": "tok-1",
                    "status": "active",
                    "actor": {"hp": {"current": 20, "max": 20}},
                }
            ]
        }
    }
    changed = synchronize_active_summon_state(native, token_id="tok-1", hp_current=7, hp_max=20)
    assert changed is True
    row = ((native.get("summons") or {}).get("activeSummons") or [])[0]
    assert ((row.get("actor") or {}).get("hp") or {}).get("current") == 7
    assert row.get("status") == "active"

    changed_down = synchronize_active_summon_state(native, token_id="tok-1", hp_current=0, hp_max=20)
    assert changed_down is True
    row = ((native.get("summons") or {}).get("activeSummons") or [])[0]
    assert row.get("status") == "defeated"

    removed = synchronize_active_summon_state(native, token_id="tok-1", remove=True)
    assert removed is True
    assert ((native.get("summons") or {}).get("activeSummons") or []) == []
