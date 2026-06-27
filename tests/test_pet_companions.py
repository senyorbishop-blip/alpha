"""Owned-animal pet companions: catalog, runtime resolution, and buy/release flow."""
import asyncio

import pytest

from server.character.summon_catalog import (
    get_summon_template,
    validate_summon_template_registry,
)
from server.character.pet_catalog import (
    list_pet_shop_entries,
    is_pet_template,
    get_pet_price_gp,
)
from server.character.summon_runtime import build_summon_runtime_payload
from server.character.resolver import resolve_character_runtime
from server.handlers.pets import handle_pet_acquire, handle_pet_release, _deduct_currency
from server.session import Session, User, Token


PETS = ("pet-dog", "pet-cat", "pet-bird", "pet-monkey")


def _seed_player(session: Session, player: User, *, unlocked=None, gp=200):
    session.char_profiles = {
        player.name.strip().lower(): [
            {
                "id": "profile-pet",
                "name": player.name,
                "nativeCharacter": {
                    "classes": [{"classId": "fighter", "level": 3}],
                    "abilities": {"scores": {"str": 14}},
                    "equipment": {"currency": {"gp": gp, "sp": 0, "cp": 0, "ep": 0, "pp": 0}},
                    "summons": {
                        "unlockedTemplates": list(unlocked or []),
                        "selectedVariants": {},
                        "activeSummons": [],
                    },
                },
                "nativeRuntime": {},
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-pet"}


def test_pet_templates_registered_and_registry_valid():
    assert validate_summon_template_registry() == []
    for pet in PETS:
        template = get_summon_template(pet)
        assert template is not None
        assert template.get("sourceClassId") == "pet"
        assert template.get("summonCategory") == "companion"
        assert template.get("variantGroup") == pet


def test_pet_shop_catalog_lists_all_pets_with_prices():
    entries = list_pet_shop_entries()
    assert {e["templateId"] for e in entries} == set(PETS)
    for entry in entries:
        assert is_pet_template(entry["templateId"])
        assert get_pet_price_gp(entry["templateId"]) >= 0
        assert entry["name"]


def test_owned_pet_resolves_into_controllable_companion_token():
    session = Session(id="TPET")
    player = User(id="u1", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player(session, player, unlocked=["pet-dog"])

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={"profile_id": "profile-pet", "summon_template_id": "pet-dog", "selected_variant": "pet-dog"},
    )
    assert result.get("ok") is True
    actor = result.get("actor") or {}
    token_payload = result.get("token_payload") or {}
    assert actor.get("summonCategory") == "companion"
    assert (actor.get("hp") or {}).get("max", 0) > 0
    assert isinstance(actor.get("actions"), list) and actor.get("actions")
    assert token_payload.get("token_type") == "companion"
    assert token_payload.get("owner_id") == player.id


def test_pet_summon_requires_ownership_unlock():
    session = Session(id="TPET")
    player = User(id="u1", name="Ayla", role="player")
    session.users[player.id] = player
    _seed_player(session, player, unlocked=[])  # owns nothing

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={"profile_id": "profile-pet", "summon_template_id": "pet-dog", "selected_variant": "pet-dog"},
    )
    assert result.get("ok") is False
    assert result.get("error") == "summon_not_unlocked"


def test_runtime_pet_shop_surface_marks_owned_and_affordable():
    native = {
        "classes": [{"classId": "fighter", "level": 3}],
        "equipment": {"currency": {"gp": 30}},
        "summons": {"unlockedTemplates": ["pet-dog"], "selectedVariants": {}, "activeSummons": []},
    }
    runtime = resolve_character_runtime(native).get("runtime") or {}
    shop = runtime.get("petShop") or {}
    entries = {e["templateId"]: e for e in shop.get("entries") or []}
    assert entries["pet-dog"]["owned"] is True
    assert entries["pet-monkey"]["owned"] is False
    # 30 gp wallet: dog already owned, cat (10gp) affordable, monkey (50gp) not.
    assert entries["pet-cat"]["affordable"] is True
    assert entries["pet-monkey"]["affordable"] is False
    assert shop.get("wallet", {}).get("gp") == 30


def test_pet_acquire_deducts_currency_and_records_ownership():
    session = Session(id="TPET")
    player = User(id="u1", name="Bob", role="player")
    session.users[player.id] = player
    _seed_player(session, player, unlocked=[], gp=30)

    asyncio.run(handle_pet_acquire({"template_id": "pet-dog", "profile_id": "profile-pet"}, session, player))
    native = session.char_profiles["bob"][0]["nativeCharacter"]
    assert "pet-dog" in native["summons"]["unlockedTemplates"]
    # 30 gp - 25 gp dog = 5 gp remaining.
    assert native["equipment"]["currency"]["gp"] == 5


def test_pet_acquire_rejects_when_funds_insufficient():
    session = Session(id="TPET")
    player = User(id="u1", name="Bob", role="player")
    session.users[player.id] = player
    _seed_player(session, player, unlocked=[], gp=5)  # cannot afford a 25 gp dog

    asyncio.run(handle_pet_acquire({"template_id": "pet-dog", "profile_id": "profile-pet"}, session, player))
    native = session.char_profiles["bob"][0]["nativeCharacter"]
    assert "pet-dog" not in native["summons"]["unlockedTemplates"]
    assert native["equipment"]["currency"]["gp"] == 5


def test_pet_release_drops_ownership_and_removes_active_token():
    session = Session(id="TPET")
    player = User(id="u1", name="Bob", role="player")
    session.users[player.id] = player
    _seed_player(session, player, unlocked=["pet-dog"], gp=0)
    # Simulate an active deployed pet token tracked in summon state.
    native = session.char_profiles["bob"][0]["nativeCharacter"]
    native["summons"]["activeSummons"] = [
        {"id": "a1", "templateId": "pet-dog", "summonGroupId": "pet-dog", "ownerProfileId": "profile-pet", "tokenId": "tok-pet"}
    ]
    session.tokens["tok-pet"] = Token(
        id="tok-pet", name="Dog", x=0, y=0, width=40, height=40, color="#fff", shape="circle",
        owner_id=player.id, token_type="companion", map_context="world",
    )

    asyncio.run(handle_pet_release({"template_id": "pet-dog", "profile_id": "profile-pet"}, session, player))
    native = session.char_profiles["bob"][0]["nativeCharacter"]
    assert "pet-dog" not in native["summons"]["unlockedTemplates"]
    assert "tok-pet" not in session.tokens


def test_dm_can_grant_pet_for_free():
    session = Session(id="TPET")
    dm = User(id="dm1", name="GM", role="dm")
    session.users[dm.id] = dm
    _seed_player(session, dm, unlocked=[], gp=0)  # no money

    asyncio.run(handle_pet_acquire({"template_id": "pet-monkey", "profile_id": "profile-pet"}, session, dm))
    native = session.char_profiles["gm"][0]["nativeCharacter"]
    assert "pet-monkey" in native["summons"]["unlockedTemplates"]


def test_deduct_currency_makes_change_across_denominations():
    wallet = {"equipment": {"currency": {"gp": 0, "sp": 50, "cp": 0, "ep": 0, "pp": 0}}}
    assert _deduct_currency(wallet, 3) is True  # 50 sp = 5 gp; spend 3 gp
    cur = wallet["equipment"]["currency"]
    # 5 gp - 3 gp = 2 gp worth left, re-minted as 20 sp.
    total_copper = cur["gp"] * 100 + cur["sp"] * 10 + cur["cp"]
    assert total_copper == 200
