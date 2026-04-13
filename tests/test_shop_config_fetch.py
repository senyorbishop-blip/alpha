import asyncio

from server.handlers import inventory
from server.session import Session, User


def test_dm_get_shop_config_returns_persisted_shop(monkeypatch):
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory.manager, "send_to", _send_to)
    monkeypatch.setattr(
        "server.db.get_shop_by_prop_id",
        lambda _campaign_id, _prop_id: {"id": "shop-1", "prop_id": "prop-1", "name": "Arcane Goods"},
    )

    session = Session(id="camp-1")
    dm = User(id="dm-1", name="DM", role="dm")

    asyncio.run(inventory.handle_dm_get_shop_config({"prop_id": "prop-1"}, session, dm))

    assert sent
    assert sent[-1]["type"] == "dm_shop_config"
    assert sent[-1]["payload"]["prop_id"] == "prop-1"
    assert sent[-1]["payload"]["shop"]["id"] == "shop-1"
