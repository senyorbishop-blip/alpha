import asyncio

from server.handlers import inventory
from server.session import Session, User, get_player_gold_for_user, set_player_gold_for_user


class _DBStub:
    def __init__(self):
        self.shop = {
            "id": "shop-1",
            "name": "Copper Cup",
            "shopkeeper_name": "Marta",
            "is_open": 1,
            "inventory": [
                {
                    "id": "item-1",
                    "item_name": "Rope",
                    "description": "50 ft hemp rope",
                    "price_gp": 10,
                    "price_sp": 0,
                    "price_cp": 0,
                    "quantity": 5,
                }
            ],
        }
        self.decrement_calls = []
        self.transaction_calls = []

    def get_shop_by_id(self, _shop_id):
        return {
            **self.shop,
            "inventory": [dict(x) for x in self.shop["inventory"]],
        }

    def decrement_shop_item(self, item_id, qty):
        self.decrement_calls.append((item_id, qty))
        item = self.shop["inventory"][0]
        item["quantity"] = max(0, int(item.get("quantity") or 0) - int(qty or 0))
        return True

    def record_shop_transaction(self, shop_id, user_id, item_id, qty, price_paid_gp):
        self.transaction_calls.append((shop_id, user_id, item_id, qty, price_paid_gp))
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
    monkeypatch.setattr(inventory, "save_campaign_async", lambda _session: asyncio.sleep(0))
    monkeypatch.setattr(inventory, "_broadcast_inventory_state", lambda _session: asyncio.sleep(0))
    return sent, broadcast


def _setup_db(monkeypatch):
    stub = _DBStub()
    monkeypatch.setattr("server.db.get_shop_by_id", stub.get_shop_by_id)
    monkeypatch.setattr("server.db.decrement_shop_item", stub.decrement_shop_item)
    monkeypatch.setattr("server.db.record_shop_transaction", stub.record_shop_transaction)
    return stub


def _player_session():
    session = Session(id="sess-1")
    user = User(id="player-1", name="Aria", role="player")
    session.users = {user.id: user}
    set_player_gold_for_user(session, user.id, 2000)
    return session, user


def _find_last(sent, msg_type):
    msgs = [msg for _, msg in sent if isinstance(msg, dict) and msg.get("type") == msg_type]
    return msgs[-1] if msgs else None


def test_forged_client_discount_is_ignored_without_server_haggle(monkeypatch):
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch)
    session, user = _player_session()

    asyncio.run(inventory.handle_purchase_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "quantity": 1,
        "discount_pct": 99,  # forged client payload
    }, session, user))

    assert get_player_gold_for_user(session, user.id) == 1000
    assert stub.transaction_calls[-1][-1] == 10
    purchase = _find_last(sent, "purchase_result")
    assert purchase is not None
    quote = purchase["payload"]["price_quote"]
    assert quote["base_per_item_units"] == 1000
    assert quote["final_per_item_units"] == 1000
    assert quote["haggle"]["active"] is False


def test_valid_haggle_applies_only_when_server_offer_exists(monkeypatch):
    sent, _ = _setup_runtime(monkeypatch)
    _setup_db(monkeypatch)
    session, user = _player_session()

    monkeypatch.setattr(inventory.random, "randint", lambda _a, _b: 20)
    asyncio.run(inventory.handle_haggle_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "charisma_modifier": 0,
    }, session, user))

    haggle_msg = _find_last(sent, "haggle_result")
    assert haggle_msg is not None
    haggle_payload = haggle_msg["payload"]
    assert haggle_payload["success"] is True
    assert haggle_payload["price_quote"]["haggle"]["active"] is True
    assert haggle_payload["price_quote"]["final_per_item_units"] == 800


def test_discounted_purchase_consumes_haggle_offer(monkeypatch):
    sent, _ = _setup_runtime(monkeypatch)
    stub = _setup_db(monkeypatch)
    session, user = _player_session()

    monkeypatch.setattr(inventory.random, "randint", lambda _a, _b: 20)
    asyncio.run(inventory.handle_haggle_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "charisma_modifier": 0,
    }, session, user))

    asyncio.run(inventory.handle_purchase_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "quantity": 1,
    }, session, user))

    assert get_player_gold_for_user(session, user.id) == 1200
    purchase = _find_last(sent, "purchase_result")
    assert purchase is not None
    payload = purchase["payload"]
    assert payload["haggle_consumed"] is True
    assert payload["price_quote"]["final_per_item_units"] == 800

    # Next purchase should charge full price because haggle was consumed.
    asyncio.run(inventory.handle_purchase_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "quantity": 1,
    }, session, user))
    assert get_player_gold_for_user(session, user.id) == 200
    assert stub.transaction_calls[-1][-1] == 10


def test_base_price_purchase_still_works(monkeypatch):
    sent, _ = _setup_runtime(monkeypatch)
    _setup_db(monkeypatch)
    session, user = _player_session()

    asyncio.run(inventory.handle_purchase_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "quantity": 1,
    }, session, user))

    purchase = _find_last(sent, "purchase_result")
    assert purchase is not None
    assert purchase["payload"]["success"] is True
    assert purchase["payload"]["player_gold_units"] == 1000


def test_purchase_result_price_state_matches_charged_price(monkeypatch):
    sent, _ = _setup_runtime(monkeypatch)
    _setup_db(monkeypatch)
    session, user = _player_session()

    monkeypatch.setattr(inventory.random, "randint", lambda _a, _b: 20)
    asyncio.run(inventory.handle_haggle_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "charisma_modifier": 0,
    }, session, user))
    asyncio.run(inventory.handle_purchase_item({
        "shop_id": "shop-1",
        "item_id": "item-1",
        "quantity": 1,
    }, session, user))

    purchase = _find_last(sent, "purchase_result")
    assert purchase is not None
    payload = purchase["payload"]
    charged = payload["price_quote"]["final_total_units"]
    remaining = payload["player_gold_units"]
    assert charged == 800
    assert remaining == 1200
    post_state = payload["price_state"]["item-1"]
    assert post_state["final_price_units"] == 1000
    assert post_state["haggle"]["active"] is False
