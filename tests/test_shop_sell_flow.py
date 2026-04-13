"""
tests/test_shop_sell_flow.py
Stage 6: Sell + Sell Haggle tests.

Anti-exploit model tested:
- Server computes all offer values; client-supplied amounts are never used.
- buy_rate_pct spread guarantees sell offer < buy price (no profitable resale).
- Resale lockout blocks selling back to the same shop within RESALE_LOCKOUT_SECONDS.
- Vendor cash cap rejects sales that exceed available merchant funds.
- Category acceptance rejects items of wrong type.
- Sell haggle result comes from server d20 roll; client cannot forge bonus.
- Transaction log is written for every successful sale.
"""
import asyncio
import time

import pytest

from server.handlers import inventory
from server.session import Session, User, get_player_gold_for_user, set_player_gold_for_user


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_BASE_SHOP = {
    "id": "shop-1",
    "name": "Trader Post",
    "shopkeeper_name": "Marta",
    "is_open": 1,
    "buy_rate_pct": 50,
    "vendor_cash_units": None,  # unlimited by default
    "shop_sales_enabled": True,
    "player_sell_enabled": True,
    "selling_enabled": True,
    "buyback_enabled": False,
    "accepted_item_types_json": ["weapon", "armour", "consumable", "tool", "material", "trinket", "magic", "misc"],
    "inventory": [
        {
            "id": "item-1",
            "item_name": "Rope",
            "item_type": "misc",
            "description": "50 ft hemp rope",
            "price_gp": 10,
            "price_sp": 0,
            "price_cp": 0,
            "quantity": 5,
        }
    ],
}


class _DBStub:
    def __init__(self, shop_override=None):
        self.shop = dict(_BASE_SHOP) if shop_override is None else dict(shop_override)
        self.sell_transaction_calls = []
        self.vendor_cash_updates = []

    def get_shop_by_id(self, _shop_id):
        return dict(self.shop)

    def record_shop_sell_transaction(self, shop_id, seller_user_id, item_name, qty, price_paid_gp):
        self.sell_transaction_calls.append({
            "shop_id": shop_id,
            "seller": seller_user_id,
            "item_name": item_name,
            "qty": qty,
            "price_gp": price_paid_gp,
        })
        return True

    def update_vendor_cash(self, shop_id, new_cash):
        self.vendor_cash_updates.append(new_cash)
        return True

    # Buy-flow stubs (used by handle_purchase_item dependency chain)
    def decrement_shop_item(self, item_id, qty):
        return True

    def record_shop_transaction(self, shop_id, user_id, item_id, qty, price_paid_gp):
        return True


def _setup_runtime(monkeypatch):
    sent = []
    broadcast = []

    async def _send_to(_sid, uid, msg):
        sent.append((uid, msg))

    async def _broadcast(_sid, msg):
        broadcast.append(msg)

    monkeypatch.setattr(inventory.manager, "send_to", _send_to)
    monkeypatch.setattr(inventory.manager, "broadcast", _broadcast)
    monkeypatch.setattr(inventory, "save_campaign_async", lambda _s: asyncio.sleep(0))
    monkeypatch.setattr(inventory, "_broadcast_inventory_state", lambda _s: asyncio.sleep(0))
    return sent, broadcast


def _setup_db(monkeypatch, shop_override=None):
    stub = _DBStub(shop_override)
    monkeypatch.setattr("server.db.get_shop_by_id", stub.get_shop_by_id)
    monkeypatch.setattr("server.db.record_shop_sell_transaction", stub.record_shop_sell_transaction)
    monkeypatch.setattr("server.db.update_vendor_cash", stub.update_vendor_cash)
    monkeypatch.setattr("server.db.record_shop_transaction", stub.record_shop_transaction)
    monkeypatch.setattr("server.db.decrement_shop_item", stub.decrement_shop_item)
    return stub


def _player_session_with_item(item_name="Longsword", item_type="weapon", gold=5000):
    session = Session(id="sess-1")
    user = User(id="player-1", name="Aria", role="player")
    session.users = {user.id: user}
    set_player_gold_for_user(session, user.id, gold)
    # Key must match _user_bucket_key(user) = normalize_profile_owner_key(user.name) = "aria"
    from server.session import normalize_profile_owner_key
    bucket_key = normalize_profile_owner_key(user.name)
    session.player_inventories = {
        bucket_key: [
            {"name": item_name, "qty": 3, "notes": "", "item_type": item_type}
        ]
    }
    # Grant shop access token so proximity check passes
    inventory._mark_shop_access(session, user, {"id": "shop-1", "prop_id": "prop-1"})
    return session, user


def _find_last(sent, msg_type):
    msgs = [m for _, m in sent if isinstance(m, dict) and m.get("type") == msg_type]
    return msgs[-1] if msgs else None


# ---------------------------------------------------------------------------
# Test 1: item sells correctly
# ---------------------------------------------------------------------------

def test_item_sells_correctly(monkeypatch):
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch)
    session, user = _player_session_with_item("Longsword", "weapon", gold=500)

    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Longsword", "quantity": 1},
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result is not None
    payload = result["payload"]
    assert payload["success"] is True
    assert payload["item_name"] == "Longsword"
    assert payload["quantity"] == 1
    # offer = 50% of weapon default (1500 cp) = 750 cp
    assert payload["offer_units"] == 750
    # Gold should increase by 750
    assert get_player_gold_for_user(session, user.id) == 500 + 750
    # Transaction was logged
    assert len(stub.sell_transaction_calls) == 1
    txn = stub.sell_transaction_calls[0]
    assert txn["item_name"] == "Longsword"
    assert txn["qty"] == 1


# ---------------------------------------------------------------------------
# Test 2: invalid category rejected
# ---------------------------------------------------------------------------

def test_invalid_category_rejected(monkeypatch):
    shop = dict(_BASE_SHOP)
    shop["accepted_item_types_json"] = ["weapon", "armour"]  # only weapons and armour
    sent, _ = _setup_runtime(monkeypatch)
    _setup_db(monkeypatch, shop)
    session, user = _player_session_with_item("Healing Potion", "consumable", gold=1000)

    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Healing Potion", "quantity": 1},
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "does not accept" in result["payload"]["message"].lower() or "consumable" in result["payload"]["message"].lower()
    # Gold must be unchanged
    assert get_player_gold_for_user(session, user.id) == 1000


def test_player_sell_disabled_blocks_sell_flow(monkeypatch):
    shop = dict(_BASE_SHOP)
    shop["shop_sales_enabled"] = True
    shop["player_sell_enabled"] = False
    shop["selling_enabled"] = False  # back-compat mirror
    sent, _ = _setup_runtime(monkeypatch)
    _setup_db(monkeypatch, shop)
    session, user = _player_session_with_item("Longsword", "weapon", gold=1000)

    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Longsword", "quantity": 1},
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "does not buy" in result["payload"]["message"].lower()
    assert get_player_gold_for_user(session, user.id) == 1000


# ---------------------------------------------------------------------------
# Test 3: vendor cash cap enforced
# ---------------------------------------------------------------------------

def test_vendor_cash_cap_enforced(monkeypatch):
    shop = dict(_BASE_SHOP)
    shop["vendor_cash_units"] = 100  # only 1 gp on hand
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch, shop)
    # Longsword offer = 50% × 1500 = 750 cp, but vendor only has 100 cp
    session, user = _player_session_with_item("Longsword", "weapon", gold=500)

    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Longsword", "quantity": 1},
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "enough coin" in result["payload"]["message"].lower() or "doesn't have" in result["payload"]["message"].lower()
    assert get_player_gold_for_user(session, user.id) == 500
    assert len(stub.sell_transaction_calls) == 0


# ---------------------------------------------------------------------------
# Test 4: forged client sell value is ignored (server is authoritative)
# ---------------------------------------------------------------------------

def test_forged_client_sell_value_ignored(monkeypatch):
    """Client cannot send a sell_item with a fake high offer value; server ignores it."""
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch)
    session, user = _player_session_with_item("Longsword", "weapon", gold=500)

    # Even if client sends a fabricated huge "offer_units" field, server must compute its own.
    asyncio.run(inventory.handle_sell_item(
        {
            "shop_id": "shop-1",
            "item_name": "Longsword",
            "quantity": 1,
            "offer_units": 999999,  # forged — must be ignored
            "final_offer_units": 999999,  # forged
        },
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result is not None
    assert result["payload"]["success"] is True
    # Server must charge at the correct rate, not the forged value
    assert result["payload"]["offer_units"] == 750  # 50% of 1500 cp
    assert get_player_gold_for_user(session, user.id) == 500 + 750


# ---------------------------------------------------------------------------
# Test 5: sell haggle result comes only from server
# ---------------------------------------------------------------------------

def test_haggle_result_comes_from_server(monkeypatch):
    """Server roll determines bonus; client cannot supply a favourable roll."""
    sent, _ = _setup_runtime(monkeypatch)
    _setup_db(monkeypatch)
    session, user = _player_session_with_item("Longsword", "weapon", gold=500)

    # Force server roll to 20 → 20% bonus
    monkeypatch.setattr(inventory.random, "randint", lambda _a, _b: 20)

    asyncio.run(inventory.handle_haggle_sell_item(
        {"shop_id": "shop-1", "item_name": "Longsword", "charisma_modifier": 0},
        session, user
    ))

    result = _find_last(sent, "sell_haggle_result")
    assert result is not None
    payload = result["payload"]
    assert payload["success"] is True
    assert payload["bonus_pct"] == 20
    # 50% base rate × 1500 cp = 750 cp, plus 20% bonus → 750 × 1.20 = 900 cp
    assert payload["final_offer_units"] == 900

    # Now sell — the stored server haggle offer should apply
    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Longsword", "quantity": 1},
        session, user
    ))

    sell = _find_last(sent, "sell_result")
    assert sell["payload"]["success"] is True
    assert sell["payload"]["offer_units"] == 900
    assert sell["payload"]["haggle_consumed"] is True


# ---------------------------------------------------------------------------
# Test 6: no profit loop from buy-then-immediate-sell
# ---------------------------------------------------------------------------

def test_no_profit_loop_buy_then_sell(monkeypatch):
    """
    Resale lockout: player buys an item from a shop, then immediately tries to
    sell it back to the same shop. This must be rejected when buyback_enabled=False.

    Even if it weren't rejected, the 50% spread ensures no profit. But the lockout
    adds a hard block as a defense-in-depth measure.
    """
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch)
    session, user = _player_session_with_item("Rope", "misc", gold=5000)

    # Simulate a buy (record in buy log)
    inventory._record_buy_in_log(session, user, "shop-1", "Rope", 1000)  # 10 gp base price

    # Now try to sell it back immediately
    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Rope", "quantity": 1},
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "recently purchased" in result["payload"]["message"].lower() or "buyback" in result["payload"]["message"].lower()
    # No transaction recorded
    assert len(stub.sell_transaction_calls) == 0


# ---------------------------------------------------------------------------
# Test 7: transaction logs remain correct
# ---------------------------------------------------------------------------

def test_transaction_logs_correct(monkeypatch):
    """Sell transactions are recorded with correct shop, seller, item, qty, price."""
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch)
    session, user = _player_session_with_item("Longsword", "weapon", gold=0)

    asyncio.run(inventory.handle_sell_item(
        {"shop_id": "shop-1", "item_name": "Longsword", "quantity": 2},
        session, user
    ))

    result = _find_last(sent, "sell_result")
    assert result["payload"]["success"] is True
    assert result["payload"]["offer_units"] == 750 * 2  # 2 × 750 cp

    assert len(stub.sell_transaction_calls) == 1
    txn = stub.sell_transaction_calls[0]
    assert txn["shop_id"] == "shop-1"
    assert txn["seller"] == user.id
    assert txn["item_name"] == "Longsword"
    assert txn["qty"] == 2
    # price_gp = total_offer // 100 = 1500 // 100 = 15
    assert txn["price_gp"] == 15
