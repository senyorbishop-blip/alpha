from server.character.summon_runtime import build_summon_runtime_payload, register_active_summon
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
    assert isinstance(actor.get("attacks"), list) and actor.get("attacks")
    assert isinstance(actor.get("traits"), list) and actor.get("traits")
    assert (result.get("token_payload") or {}).get("monster_type") == "construct"


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
                    "classes": [{"classId": "tinker", "level": 6, "subclassId": "artillerist"}],
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
    assert result.get("error") == "runtime_not_live_for_class"
