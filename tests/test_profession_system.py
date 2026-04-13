import asyncio

from server.handlers import inventory
from server.session import Session, User, Token


def _setup_runtime(monkeypatch):
    sent = []

    async def _send_to(_sid, uid, msg):
        sent.append((uid, msg))

    monkeypatch.setattr(inventory.manager, "send_to", _send_to)
    monkeypatch.setattr(inventory.manager, "broadcast", lambda *_args, **_kwargs: asyncio.sleep(0))
    return sent


def _find_last(sent, msg_type):
    msgs = [msg for _, msg in sent if isinstance(msg, dict) and msg.get("type") == msg_type]
    return msgs[-1] if msgs else None


class _ProfessionDBStub:
    def __init__(self):
        self.shops = {
            "shop-good": {
                "id": "shop-good",
                "prop_id": "prop-1",
                "shop_type": "blacksmith",
                "is_open": 1,
                "taught_professions_json": ["blacksmithing"],
            },
            "shop-wrong": {
                "id": "shop-wrong",
                "prop_id": "prop-1",
                "shop_type": "blacksmith",
                "is_open": 1,
                "taught_professions_json": ["blacksmithing"],
            },
        }
        self.professions = {
            "blacksmithing": {"id": "blacksmithing", "name": "Blacksmithing"},
            "alchemy": {"id": "alchemy", "name": "Potion Crafting / Alchemy"},
            "woodworking": {"id": "woodworking", "name": "Woodworking"},
        }
        self.player = {}

    def get_shop_by_id(self, shop_id):
        row = self.shops.get(shop_id)
        return dict(row) if row else None

    def get_shop_by_prop_id(self, _campaign_id, prop_id):
        for row in self.shops.values():
            if row.get("prop_id") == prop_id:
                return dict(row)
        return None

    def get_profession_by_id(self, pid):
        row = self.professions.get(pid)
        return dict(row) if row else None

    def get_player_professions(self, cid, uid):
        return list(self.player.get((cid, uid), []))

    def set_player_professions(self, cid, uid, ids):
        cleaned = []
        for pid in ids:
            if pid not in cleaned:
                cleaned.append(pid)
        self.player[(cid, uid)] = cleaned[:2]
        return list(self.player[(cid, uid)])

    def resolve_shop_taught_profession_ids(self, shop):
        return list(shop.get("taught_professions_json") or [])

    def list_professions(self):
        return [dict(v) for v in self.professions.values()]


def _wire_db_stub(monkeypatch, stub):
    monkeypatch.setattr("server.db.get_shop_by_id", stub.get_shop_by_id)
    monkeypatch.setattr("server.db.get_shop_by_prop_id", stub.get_shop_by_prop_id)
    monkeypatch.setattr("server.db.get_profession_by_id", stub.get_profession_by_id)
    monkeypatch.setattr("server.db.get_player_professions", stub.get_player_professions)
    monkeypatch.setattr("server.db.set_player_professions", stub.set_player_professions)
    monkeypatch.setattr("server.db.resolve_shop_taught_profession_ids", stub.resolve_shop_taught_profession_ids)
    monkeypatch.setattr("server.db.list_professions", stub.list_professions)


def _session_with_player_near_shop():
    session = Session(id="camp-1")
    user = User(id="u1", name="Aria", role="player")
    session.users[user.id] = user
    session.tokens["tok-1"] = Token(
        id="tok-1", name="Aria", x=100, y=100, width=1, height=1, color="#fff", shape="circle", owner_id=user.id
    )
    session.editor_props = {
        "world": [
            {"id": "prop-1", "x": 100, "y": 100, "w": 1, "h": 1},
        ]
    }
    return session, user


def test_profession_can_be_learned_at_valid_merchant(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _ProfessionDBStub()
    _wire_db_stub(monkeypatch, stub)
    session, user = _session_with_player_near_shop()

    asyncio.run(inventory.handle_open_shop({"prop_id": "prop-1"}, session, user))
    asyncio.run(inventory.handle_learn_profession({"shop_id": "shop-good", "profession_id": "blacksmithing"}, session, user))

    result = _find_last(sent, "profession_learn_result")
    assert result is not None
    assert result["payload"]["success"] is True
    assert stub.player[(session.id, user.id)] == ["blacksmithing"]


def test_invalid_merchant_cannot_teach_unconfigured_profession(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _ProfessionDBStub()
    _wire_db_stub(monkeypatch, stub)
    session, user = _session_with_player_near_shop()

    asyncio.run(inventory.handle_open_shop({"prop_id": "prop-1"}, session, user))
    asyncio.run(inventory.handle_learn_profession({"shop_id": "shop-good", "profession_id": "alchemy"}, session, user))

    result = _find_last(sent, "profession_learn_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "cannot teach" in result["payload"]["message"].lower()


def test_max_two_professions_and_replace_flow(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _ProfessionDBStub()
    _wire_db_stub(monkeypatch, stub)
    session, user = _session_with_player_near_shop()
    stub.player[(session.id, user.id)] = ["blacksmithing", "alchemy"]
    stub.shops["shop-good"]["taught_professions_json"] = ["woodworking"]

    asyncio.run(inventory.handle_open_shop({"prop_id": "prop-1"}, session, user))
    asyncio.run(inventory.handle_learn_profession({"shop_id": "shop-good", "profession_id": "woodworking"}, session, user))
    blocked = _find_last(sent, "profession_learn_result")
    assert blocked is not None
    assert blocked["payload"]["success"] is False

    asyncio.run(inventory.handle_learn_profession({
        "shop_id": "shop-good",
        "profession_id": "woodworking",
        "replace_profession_id": "alchemy",
    }, session, user))
    ok = _find_last(sent, "profession_learn_result")
    assert ok is not None
    assert ok["payload"]["success"] is True
    assert stub.player[(session.id, user.id)] == ["blacksmithing", "woodworking"]


def test_reconnect_persists_player_professions_db_roundtrip():
    from server import db

    db.init_db()
    before = db.set_player_professions("camp-reconnect", "user-reconnect", ["alchemy", "woodworking"])
    after = db.get_player_professions("camp-reconnect", "user-reconnect")

    assert before == ["alchemy", "woodworking"]
    assert after == ["alchemy", "woodworking"]
