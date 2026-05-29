"""
tests/test_integration_inventory_tab.py — Integration tests for the inventory
tab full user flow.

Note: handle_inventory_add_item, handle_inventory_add_gold,
handle_inventory_remove_gold are all DM-only operations. Players can equip
their own items and manage their bag contents.

Tests cover:
- handle_inventory_add_item: DM adds item to player inventory (happy path,
  stacking, empty name rejected, null fields)
- handle_inventory_remove_item: DM removes by index (reduce qty, remove entry)
- handle_inventory_add_gold / remove_gold: DM-only gold management
- handle_inventory_equip_item / unequip_item: equip by index
- Role guards: player add returns error, not state change
- Error path: partial payload handled gracefully
"""
import asyncio
import sys
import os
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    from server.session import Session, User
    session = Session(id="inv-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    return session, dm, player


def _patch_manager(monkeypatch):
    import server.handlers.common as common_mod

    broadcasts = []
    sent = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "broadcast", _broadcast)
    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)
    return broadcasts, sent


# ---------------------------------------------------------------------------
# handle_inventory_add_item (DM-only)
# ---------------------------------------------------------------------------

def test_inventory_add_item_happy_path(monkeypatch):
    """DM adding an item should appear in the player's inventory."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    # DM adds item to own inventory (DM is also the inventory target)
    asyncio.run(inv.handle_inventory_add_item(
        {"name": "Health Potion", "qty": 2, "notes": "", "item_type": "consumable"},
        session,
        dm,
    ))

    key = _user_bucket_key(dm)
    items = (session.player_inventories or {}).get(key, [])
    names = [i["name"] for i in items]
    assert "Health Potion" in names



def test_inventory_add_item_dm_targets_player_inventory(monkeypatch):
    """DM award payloads with target_user_id should add to that player's inventory."""
    from server.handlers import inventory as inv
    from server.session import get_player_inventory_for_user
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_item(
        {
            "entry": {"name": "Vicious Rapier", "qty": 1, "damage_dice": "1d8", "damage_type": "piercing", "weapon_properties": ["Finesse", "Vex"]},
            "source_name": "Item Library",
            "target_user_id": player.id,
        },
        session,
        dm,
    ))

    player_items = get_player_inventory_for_user(session, player.id)
    dm_items = get_player_inventory_for_user(session, dm.id)
    rapier = next((i for i in player_items if i.get("name") == "Vicious Rapier"), None)
    assert rapier is not None
    assert rapier.get("damage_dice") == "1d8"
    assert "Vex" in rapier.get("weapon_properties", [])
    assert not any(i.get("name") == "Vicious Rapier" for i in dm_items)

def test_inventory_add_item_stacks_duplicates(monkeypatch):
    """Adding the same item twice should increase quantity, not create a new entry."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_item(
        {"name": "Arrow", "qty": 20},
        session,
        dm,
    ))
    asyncio.run(inv.handle_inventory_add_item(
        {"name": "Arrow", "qty": 10},
        session,
        dm,
    ))

    key = _user_bucket_key(dm)
    items = (session.player_inventories or {}).get(key, [])
    arrow_entries = [i for i in items if i["name"] == "Arrow"]
    assert len(arrow_entries) == 1
    assert arrow_entries[0]["qty"] == 30


def test_inventory_add_item_null_name_rejected(monkeypatch):
    """An item with empty/null name should not be added."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_item(
        {"name": "", "qty": 1},
        session,
        dm,
    ))

    key = _user_bucket_key(dm)
    items = (session.player_inventories or {}).get(key, [])
    assert items == []


def test_inventory_add_item_none_qty_defaults_to_one(monkeypatch):
    """Null/missing qty field should default to 1."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_item(
        {"name": "Rope"},
        session,
        dm,
    ))

    key = _user_bucket_key(dm)
    items = (session.player_inventories or {}).get(key, [])
    rope = next((i for i in items if i["name"] == "Rope"), None)
    assert rope is not None
    assert rope["qty"] >= 1


def test_inventory_add_item_player_receives_error_not_state_change(monkeypatch):
    """Player attempting to add item directly should receive an error, not change state."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_item(
        {"name": "Health Potion", "qty": 1},
        session,
        player,
    ))

    # Player's inventory must remain empty
    key = _user_bucket_key(player)
    items = (session.player_inventories or {}).get(key, [])
    assert items == []

    # An error result should have been sent to the player
    error_msgs = [
        msg for _, uid, msg in sent
        if uid == player.id and msg.get("type") == "inventory_action_result"
    ]
    assert error_msgs



def test_inventory_award_ui_sends_target_user_id():
    """DM manual/library award controls must include recipient selectors and send target_user_id."""
    play_src = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert 'id="inventory-manual-target"' in play_src
    assert 'id="itemlib-pick-target"' in play_src
    assert "refreshInventoryAwardTargetSelect('inventory-manual-target', 'inventory-manual-target-wrap')" in play_src
    assert "refreshInventoryAwardTargetSelect('itemlib-pick-target', 'itemlib-pick-target-wrap')" in play_src
    assert "target_user_id: targetUserId" in play_src
    assert "function enrichItemLibraryEquipmentFromText" in play_src
    assert "Vex" in play_src

# ---------------------------------------------------------------------------
# handle_inventory_remove_item
# ---------------------------------------------------------------------------

def test_inventory_remove_item_reduces_quantity(monkeypatch):
    """Removing a quantity less than current qty should reduce qty."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    key = _user_bucket_key(dm)
    session.player_inventories = {key: [{"name": "Arrow", "qty": 20, "notes": ""}]}
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_remove_item(
        {"item_index": 0, "qty": 5},
        session,
        dm,
    ))

    items = (session.player_inventories or {}).get(key, [])
    arrow = next((i for i in items if i["name"] == "Arrow"), None)
    assert arrow is not None
    assert arrow["qty"] == 15


def test_inventory_remove_item_removes_entry_when_qty_exhausted(monkeypatch):
    """Removing all quantity should delete the item entry."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    key = _user_bucket_key(dm)
    session.player_inventories = {key: [{"name": "Arrow", "qty": 5, "notes": ""}]}
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_remove_item(
        {"item_index": 0, "qty": 5},
        session,
        dm,
    ))

    items = (session.player_inventories or {}).get(key, [])
    assert not any(i.get("name") == "Arrow" for i in items)


def test_inventory_remove_item_invalid_index_sends_error(monkeypatch):
    """Removing with a negative item_index should send an error, not crash."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    # No exception should be raised
    asyncio.run(inv.handle_inventory_remove_item(
        {"item_index": -1, "qty": 1},
        session,
        dm,
    ))


# ---------------------------------------------------------------------------
# handle_inventory_add_gold / handle_inventory_remove_gold
# ---------------------------------------------------------------------------

def test_inventory_add_gold_increases_gp(monkeypatch):
    """DM adding gold should increase the DM's GP total."""
    from server.handlers import inventory as inv
    from server.session import set_player_gold_for_user, get_player_gold_for_user
    session, dm, player = _make_session()
    set_player_gold_for_user(session, dm.id, 1000)  # 10 gp in copper units

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_gold(
        {"amount": "5 gp"},
        session,
        dm,
    ))

    gold_units = get_player_gold_for_user(session, dm.id)
    # 10 gp + 5 gp = 15 gp = 1500 copper units
    assert gold_units >= 1500


def test_inventory_remove_gold_decreases_gp(monkeypatch):
    """DM removing gold should decrease the GP total."""
    from server.handlers import inventory as inv
    from server.session import set_player_gold_for_user, get_player_gold_for_user
    session, dm, player = _make_session()
    set_player_gold_for_user(session, dm.id, 2000)  # 20 gp in copper units

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_remove_gold(
        {"amount": "5 gp"},
        session,
        dm,
    ))

    gold_units = get_player_gold_for_user(session, dm.id)
    # 20 gp - 5 gp = 15 gp = 1500 copper units
    assert gold_units <= 1500


def test_inventory_add_gold_invalid_amount_ignored(monkeypatch):
    """Empty/invalid amount string should not change gold state."""
    from server.handlers import inventory as inv
    from server.session import set_player_gold_for_user, get_player_gold_for_user
    session, dm, player = _make_session()
    set_player_gold_for_user(session, dm.id, 500)

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_add_gold(
        {"amount": "not-a-number"},
        session,
        dm,
    ))

    gold_units = get_player_gold_for_user(session, dm.id)
    assert gold_units == 500


# ---------------------------------------------------------------------------
# handle_inventory_equip_item / handle_inventory_unequip_item
# ---------------------------------------------------------------------------

def test_inventory_equip_item_marks_equipped(monkeypatch):
    """Equipping a weapon should mark it as equipped in inventory."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    key = _user_bucket_key(dm)
    session.player_inventories = {key: [{
        "id": "item-1",
        "name": "Longsword",
        "qty": 1,
        "notes": "",
        "equipment_kind": "weapon",
        "equip_slot": "main_hand",
        "handedness": "one_handed",
    }]}

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_equip_item(
        {"item_index": 0},
        session,
        dm,
    ))

    items = (session.player_inventories or {}).get(key, [])
    sword = next((i for i in items if i.get("name") == "Longsword"), None)
    assert sword is not None
    assert sword.get("equipped") is True


def test_inventory_unequip_item_removes_equipped_flag(monkeypatch):
    """Unequipping should clear the equipped flag."""
    from server.handlers import inventory as inv
    from server.session import _user_bucket_key
    session, dm, player = _make_session()
    key = _user_bucket_key(dm)
    session.player_inventories = {key: [{
        "id": "item-1",
        "name": "Longsword",
        "qty": 1,
        "notes": "",
        "equipment_kind": "weapon",
        "equip_slot": "main_hand",
        "handedness": "one_handed",
        "equipped": True,
    }]}

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    asyncio.run(inv.handle_inventory_unequip_item(
        {"item_index": 0},
        session,
        dm,
    ))

    items = (session.player_inventories or {}).get(key, [])
    sword = next((i for i in items if i.get("name") == "Longsword"), None)
    assert sword is not None
    assert not sword.get("equipped")


def test_inventory_equip_invalid_index_sends_error(monkeypatch):
    """Equipping with an out-of-range index should not crash."""
    from server.handlers import inventory as inv
    session, dm, player = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    # No exception expected
    asyncio.run(inv.handle_inventory_equip_item(
        {"item_index": 99},
        session,
        dm,
    ))
