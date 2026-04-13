import asyncio


def test_auto_tag_supports_5e_mount_and_cart_containers():
    from server.encumbrance import auto_tag_extradimensional

    riding_horse = auto_tag_extradimensional({"name": "Riding Horse", "qty": 1})
    draft_horse = auto_tag_extradimensional({"name": "Draft Horse", "qty": 1})
    cart = auto_tag_extradimensional({"name": "Cart", "qty": 1})

    assert riding_horse.get("is_container") is True
    assert riding_horse.get("capacity_lbs") == 480.0
    assert riding_horse.get("extradimensional") is not True

    assert draft_horse.get("is_container") is True
    assert draft_horse.get("capacity_lbs") == 540.0
    assert draft_horse.get("extradimensional") is not True

    assert cart.get("is_container") is True
    assert cart.get("capacity_lbs") == 300.0
    assert cart.get("extradimensional") is not True


def test_non_extradimensional_container_contents_count_for_weight():
    from server.encumbrance import get_total_carried_weight

    inventory = [
        {
            "name": "Cart",
            "qty": 1,
            "is_container": True,
            "capacity_lbs": 300,
            "own_weight_lbs": 0,
            "bag_contents": [{"name": "Rope", "qty": 2}],
        }
    ]
    assert get_total_carried_weight(inventory, 0) == 20.0


def test_bag_add_item_accepts_mundane_container(monkeypatch):
    from server.handlers import inventory as inventory_mod
    from server.session import Session, User, get_player_inventory_for_user

    class FakeManager:
        async def send_to(self, session_id, user_id, message):
            return None

    async def fake_save_campaign_async(session):
        return None

    monkeypatch.setattr(inventory_mod, "manager", FakeManager())
    monkeypatch.setattr(inventory_mod, "save_campaign_async", fake_save_campaign_async)

    session = Session(id="container-move")
    player = User(id="p1", name="Alice", role="player")
    session.users[player.id] = player
    session.player_inventories = {
        "alice": [
            {"name": "Cart", "qty": 1, "is_container": True, "capacity_lbs": 300, "bag_contents": []},
            {"name": "Rope", "qty": 1},
        ]
    }

    asyncio.run(inventory_mod.handle_bag_add_item({"bag_index": 0, "item_index": 1, "qty": 1}, session, player))

    items = get_player_inventory_for_user(session, player.id)
    assert len(items) == 1
    assert items[0]["name"] == "Cart"
    assert items[0]["bag_contents"][0]["name"] == "Rope"


def test_srd_mundane_seed_contains_mount_vehicle_entries():
    from server.rules_db import _SRD_MUNDANE

    ids = {item.get("id") for item in _SRD_MUNDANE}
    assert "seq_riding_horse" in ids
    assert "seq_draft_horse" in ids
    assert "seq_cart" in ids
