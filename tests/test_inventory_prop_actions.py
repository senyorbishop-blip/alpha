import asyncio
from pathlib import Path

from server.handlers import inventory
from server.session import Session, User, Token, get_player_gold_for_user


async def _run_take_with_context_fallback(sent_messages):
    session = Session(id="s1")
    user = User(id="p1", name="Player One", role="player")
    session.users = {user.id: user}
    session.editor_props = {
        "poi-1": [
            {
                "id": "chest-1",
                "kind": "chest",
                "name": "Treasure Chest",
                "slot_count": 12,
                "hidden": False,
                "inventory": [{"name": "Potion of Healing", "qty": 1, "notes": "Fresh"}],
            }
        ]
    }

    async def _send_to(_sid, uid, msg):
        sent_messages.append((uid, msg))

    async def _broadcast(_sid, msg):
        sent_messages.append(("broadcast", msg))

    inventory.manager.send_to = _send_to
    inventory.manager.broadcast = _broadcast
    inventory.save_campaign_async = lambda _session: asyncio.sleep(0)

    await inventory.handle_prop_take_item(
        {
            "map_context": "world",  # intentionally wrong context to exercise fallback
            "prop_id": "chest-1",
            "item_index": 0,
            "qty": 1,
        },
        session,
        user,
    )

    return session


def test_prop_take_item_falls_back_to_prop_context_when_map_context_is_stale():
    sent_messages = []
    session = asyncio.run(_run_take_with_context_fallback(sent_messages))

    all_inventories = list((session.player_inventories or {}).values())
    assert all_inventories and all_inventories[0], "Expected chest loot to be added to player inventory"
    assert all_inventories[0][0]["name"] == "Potion of Healing"

    chest_items = (((session.editor_props or {}).get("poi-1") or [])[0].get("inventory") or [])
    assert chest_items == []

    message_types = [msg.get("type") for _, msg in sent_messages if isinstance(msg, dict)]
    assert "prop_action_result" in message_types


def test_play_left_click_on_shop_uses_open_shop_flow():
    play_src = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert "if (editorPropIsShopKind(String(hitProp.kind || '').toLowerCase())) {" in play_src
    assert "openShopFromProp(hitProp);" in play_src


def test_prop_take_item_converts_chest_coin_entry_into_player_gold():
    sent_messages = []
    session = Session(id="s-gold")
    user = User(id="p1", name="Player One", role="player")
    session.users = {user.id: user}
    session.editor_props = {
        "world": [
            {
                "id": "chest-gold-1",
                "kind": "chest",
                "name": "Coin Chest",
                "hidden": False,
                "inventory": [{"name": "37 gp", "qty": 1}],
            }
        ]
    }

    async def _send_to(_sid, uid, msg):
        sent_messages.append((uid, msg))

    async def _broadcast(_sid, msg):
        sent_messages.append(("broadcast", msg))

    inventory.manager.send_to = _send_to
    inventory.manager.broadcast = _broadcast
    inventory.save_campaign_async = lambda _session: asyncio.sleep(0)

    asyncio.run(
        inventory.handle_prop_take_item(
            {"map_context": "world", "prop_id": "chest-gold-1", "item_index": 0, "qty": 1},
            session,
            user,
        )
    )

    player_items = list((session.player_inventories or {}).values())
    assert not player_items or player_items[0] == []
    assert get_player_gold_for_user(session, user.id) == 3700
    chest_items = (((session.editor_props or {}).get("world") or [])[0].get("inventory") or [])
    assert chest_items == []
    loot_msgs = [msg for _, msg in sent_messages if isinstance(msg, dict) and msg.get("type") == "loot_received"]
    assert loot_msgs, "Expected loot_received feedback"
    payload = loot_msgs[-1].get("payload") or {}
    assert payload.get("coins", {}).get("gp") == 37
    assert payload.get("items") == []


def test_prop_take_item_prompts_need_greed_roll_for_multiple_nearby_players():
    sent_messages = []
    session = Session(id="s-roll-prompt")
    p1 = User(id="p1", name="Alpha", role="player", connected=True)
    p2 = User(id="p2", name="Bravo", role="player", connected=True)
    session.users = {p1.id: p1, p2.id: p2}
    session.tokens = {
        "t1": Token(id="t1", name="Alpha", x=100, y=100, width=50, height=50, color="#fff", shape="circle", owner_id="p1", map_context="world"),
        "t2": Token(id="t2", name="Bravo", x=180, y=120, width=50, height=50, color="#fff", shape="circle", owner_id="p2", map_context="world"),
    }
    session.editor_props = {
        "world": [{"id": "chest-roll-1", "kind": "chest", "name": "Party Chest", "x": 120, "y": 110, "w": 1, "h": 1, "hidden": False, "inventory": [{"name": "Ruby", "qty": 1}]}]
    }

    async def _send_to(_sid, uid, msg):
        sent_messages.append((uid, msg))

    async def _broadcast(_sid, msg):
        sent_messages.append(("broadcast", msg))

    inventory.manager.send_to = _send_to
    inventory.manager.broadcast = _broadcast
    inventory.save_campaign_async = lambda _session: asyncio.sleep(0)

    asyncio.run(inventory.handle_prop_take_item({"map_context": "world", "prop_id": "chest-roll-1", "item_index": 0, "qty": 1}, session, p1))

    assert (((session.editor_props or {}).get("world") or [])[0].get("inventory") or [])[0]["name"] == "Ruby"
    prompts = [msg for _, msg in sent_messages if isinstance(msg, dict) and msg.get("type") == "chest_loot_roll_prompt"]
    assert len(prompts) == 2
    assert "loot_roll_state" in session.__dict__


def test_prop_take_item_prompts_connected_players_without_nearby_tokens():
    sent_messages = []
    session = Session(id="s-roll-fallback")
    p1 = User(id="p1", name="Alpha", role="player", connected=True)
    p2 = User(id="p2", name="Bravo", role="player", connected=True)
    session.users = {p1.id: p1, p2.id: p2}
    session.tokens = {
        # Only one player has a token on-map; fallback should still include both
        # connected players in the loot roll prompt.
        "t1": Token(id="t1", name="Alpha", x=100, y=100, width=50, height=50, color="#fff", shape="circle", owner_id="p1", map_context="world"),
    }
    session.editor_props = {
        "world": [{"id": "chest-roll-3", "kind": "chest", "name": "Party Chest", "x": 120, "y": 110, "w": 1, "h": 1, "hidden": False, "inventory": [{"name": "Sapphire", "qty": 1}]}]
    }

    async def _send_to(_sid, uid, msg):
        sent_messages.append((uid, msg))

    async def _broadcast(_sid, msg):
        sent_messages.append(("broadcast", msg))

    inventory.manager.send_to = _send_to
    inventory.manager.broadcast = _broadcast
    inventory.save_campaign_async = lambda _session: asyncio.sleep(0)

    asyncio.run(inventory.handle_prop_take_item({"map_context": "world", "prop_id": "chest-roll-3", "item_index": 0, "qty": 1}, session, p1))

    prompts = [msg for _, msg in sent_messages if isinstance(msg, dict) and msg.get("type") == "chest_loot_roll_prompt"]
    assert len(prompts) == 2
    targets = {uid for uid, msg in sent_messages if isinstance(msg, dict) and msg.get("type") == "chest_loot_roll_prompt"}
    assert targets == {"p1", "p2"}


def test_chest_loot_roll_resolution_prefers_need_and_awards_highest_roll(monkeypatch):
    sent_messages = []
    session = Session(id="s-roll-resolve")
    p1 = User(id="p1", name="Alpha", role="player", connected=True)
    p2 = User(id="p2", name="Bravo", role="player", connected=True)
    session.users = {p1.id: p1, p2.id: p2}
    session.tokens = {
        "t1": Token(id="t1", name="Alpha", x=100, y=100, width=50, height=50, color="#fff", shape="circle", owner_id="p1", map_context="world"),
        "t2": Token(id="t2", name="Bravo", x=180, y=120, width=50, height=50, color="#fff", shape="circle", owner_id="p2", map_context="world"),
    }
    session.editor_props = {
        "world": [{"id": "chest-roll-2", "kind": "chest", "name": "Party Chest", "x": 120, "y": 110, "w": 1, "h": 1, "hidden": False, "inventory": [{"name": "Emerald", "qty": 1}]}]
    }

    async def _send_to(_sid, uid, msg):
        sent_messages.append((uid, msg))

    async def _broadcast(_sid, msg):
        sent_messages.append(("broadcast", msg))

    inventory.manager.send_to = _send_to
    inventory.manager.broadcast = _broadcast
    inventory.save_campaign_async = lambda _session: asyncio.sleep(0)
    rolls = iter([5, 19])
    monkeypatch.setattr(inventory.random, "randint", lambda _a, _b: next(rolls))

    asyncio.run(inventory.handle_prop_take_item({"map_context": "world", "prop_id": "chest-roll-2", "item_index": 0, "qty": 1}, session, p1))
    roll_id = next(iter((session.loot_roll_state or {}).keys()))
    asyncio.run(inventory.handle_chest_loot_roll_choice({"roll_id": roll_id, "choice": "need"}, session, p1))
    asyncio.run(inventory.handle_chest_loot_roll_choice({"roll_id": roll_id, "choice": "greed"}, session, p2))

    p1_inventory = (session.player_inventories or {}).get("alpha", [])
    p2_inventory = (session.player_inventories or {}).get("bravo", [])
    assert p1_inventory and p1_inventory[0]["name"] == "Emerald"
    assert p2_inventory == []
    chest_items = (((session.editor_props or {}).get("world") or [])[0].get("inventory") or [])
    assert chest_items == []
    resolved_msgs = [msg for _, msg in sent_messages if isinstance(msg, dict) and msg.get("type") == "chest_loot_roll_resolved"]
    assert resolved_msgs
