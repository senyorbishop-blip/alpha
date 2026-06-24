"""Inventory runtime bridge regression tests."""

from __future__ import annotations

import server.session as session_mod
from server.handlers import inventory as inventory_handlers  # imports handlers and installs bridge
from server.handlers.inventory_runtime_bridge import install_inventory_runtime_bridge
from server.session import Session, User, build_quick_actions_sync_payload, normalize_profile_owner_key


def _session_with_stale_thunder_staff():
    session = Session(id="s-p6-runtime-bridge")
    user = User(id="player-1", name="Storm Hero", role="player")
    session.users[user.id] = user
    owner_key = normalize_profile_owner_key(user.name) or user.id
    session.player_inventories = {
        owner_key: [{
            "magic_item_id": "thunder-mage-quarterstaff-plus-3",
            "name": "Thunder Mage Quarterstaff +3",
            "rarity": "common",
            "equipped": True,
            "attuned": True,
            "attunement_required": True,
            "charges_current": 3,
            "charges_max": 0,
            "granted_spells": [],
            "qty": 1,
        }]
    }
    return session, user, owner_key


def test_bridge_installs_same_rehydrated_getter_for_session_and_inventory_modules():
    install_inventory_runtime_bridge()

    assert session_mod.get_player_inventory_for_user is inventory_handlers.get_player_inventory_for_user


def test_runtime_inventory_getter_repairs_stale_magic_item_rows():
    install_inventory_runtime_bridge()
    session, user, owner_key = _session_with_stale_thunder_staff()

    items = session_mod.get_player_inventory_for_user(session, user.id)

    assert items[0]["name"] == "Thunder Mage Quarterstaff, +3"
    assert items[0]["rarity"] == "very_rare"
    assert items[0]["charges_max"] == 10
    assert items[0]["charges_current"] == 3
    assert {s["id"] for s in items[0]["granted_spells"] if isinstance(s, dict)} >= {"lightning-bolt", "thunderwave"}
    assert session.player_inventories[owner_key][0]["charges_max"] == 10


def test_quick_actions_uses_rehydrated_inventory_for_item_spell_cards():
    install_inventory_runtime_bridge()
    session, user, _owner_key = _session_with_stale_thunder_staff()

    payload = build_quick_actions_sync_payload(session, user.id)

    spell_ids = {card["spell_id"] for card in payload.get("item_spell_cards", [])}
    assert "lightning-bolt" in spell_ids
    assert "thunderwave" in spell_ids
    assert all(card["charges_current"] == 3 for card in payload.get("item_spell_cards", []))
    assert all(card["charges_max"] == 10 for card in payload.get("item_spell_cards", []))


def test_inventory_state_builder_uses_rehydrated_inventory_reference():
    install_inventory_runtime_bridge()
    session, user, _owner_key = _session_with_stale_thunder_staff()

    items = inventory_handlers.get_player_inventory_for_user(session, user.id)
    cards = inventory_handlers._build_item_spell_cards(items)

    assert {card["spell_id"] for card in cards} >= {"lightning-bolt", "thunderwave"}
