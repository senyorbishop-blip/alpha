import asyncio

from server.handlers import content as content_handlers
from server.handlers import inventory as inventory_handlers
from server.session import Session, User, get_player_gold_for_user, get_player_inventory_for_user, set_player_gold_for_user


def _build_player_session():
    session = Session(id="sess-profile-inv")
    player = User(id="u-player", name="Alice", role="player", connected=True)
    session.users[player.id] = player
    session.char_profiles = {
        "alice": [
            {"id": "profile_a", "name": "Alpha"},
            {"id": "profile_b", "name": "Beta"},
        ]
    }
    return session, player


def test_inventory_and_gold_are_scoped_to_active_character_profile():
    session, player = _build_player_session()

    inventory_handlers._add_item_to_player_inventory(session, player, {"name": "Rope"}, 1)
    assert [entry["name"] for entry in get_player_inventory_for_user(session, player.id)] == ["Rope"]
    assert get_player_gold_for_user(session, player.id) == 0

    set_player_gold_for_user(session, player.id, 25)
    session.active_char_profiles[player.id] = "profile_a"

    # Legacy account bucket should migrate into the first selected profile bucket.
    assert [entry["name"] for entry in get_player_inventory_for_user(session, player.id)] == ["Rope"]
    assert get_player_gold_for_user(session, player.id) == 25

    inventory_handlers._add_item_to_player_inventory(session, player, {"name": "Longsword"}, 1)
    set_player_gold_for_user(session, player.id, 90)
    assert [entry["name"] for entry in get_player_inventory_for_user(session, player.id)] == ["Rope", "Longsword"]
    assert get_player_gold_for_user(session, player.id) == 90

    session.active_char_profiles[player.id] = "profile_b"
    assert get_player_inventory_for_user(session, player.id) == []
    assert get_player_gold_for_user(session, player.id) == 0

    inventory_handlers._add_item_to_player_inventory(session, player, {"name": "Spellbook"}, 1)
    set_player_gold_for_user(session, player.id, 12)
    assert [entry["name"] for entry in get_player_inventory_for_user(session, player.id)] == ["Spellbook"]
    assert get_player_gold_for_user(session, player.id) == 12

    session.active_char_profiles[player.id] = "profile_a"
    assert [entry["name"] for entry in get_player_inventory_for_user(session, player.id)] == ["Rope", "Longsword"]
    assert get_player_gold_for_user(session, player.id) == 90


def test_char_profile_select_updates_active_profile_and_rejects_unknown(monkeypatch):
    session, player = _build_player_session()

    monkeypatch.setattr(inventory_handlers, "_update_encumbrance_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(inventory_handlers, "_recompute_equipment_effects", lambda *_args, **_kwargs: None)

    async def _noop_async(*_args, **_kwargs):
        pass

    monkeypatch.setattr(inventory_handlers, "_broadcast_inventory_state", _noop_async)
    monkeypatch.setattr(content_handlers, "save_campaign_async", _noop_async)

    asyncio.run(content_handlers.handle_char_profile_select({"id": "profile_b"}, session, player))
    assert session.active_char_profiles.get(player.id) == "profile_b"

    asyncio.run(content_handlers.handle_char_profile_select({"id": "unknown"}, session, player))
    assert session.active_char_profiles.get(player.id) == "profile_b"

    asyncio.run(content_handlers.handle_char_profile_select({"id": ""}, session, player))
    assert player.id not in session.active_char_profiles
