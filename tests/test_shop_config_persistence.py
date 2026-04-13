def test_shop_config_round_trip_persists_independent_sell_flags(tmp_path, monkeypatch):
    import server.db as db

    db_path = tmp_path / "shop-config.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    db.init_db()
    db.upsert_shop(
        campaign_id="camp-1",
        prop_id="prop-1",
        name="Copper Kettle",
        shopkeeper_name="Mina",
        shop_type="general",
        description="",
        inventory=[],
        shop_sales_enabled=False,
        player_sell_enabled=True,
        buyback_enabled=True,
        accepted_item_types=["consumable", "misc"],
        vendor_cash_units=1234,
        buy_rate_pct=65,
    )

    shop = db.get_shop_by_prop_id("camp-1", "prop-1")
    assert shop is not None
    assert shop["shop_sales_enabled"] is False
    assert shop["player_sell_enabled"] is True
    assert shop["buyback_enabled"] is True
    assert sorted(shop["accepted_item_types_json"]) == ["consumable", "misc"]
    assert shop["vendor_cash_units"] == 1234
    assert shop["buy_rate_pct"] == 65


def test_shop_config_round_trip_player_sell_can_be_disabled_independently(tmp_path, monkeypatch):
    import server.db as db

    db_path = tmp_path / "shop-config-2.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    db.init_db()
    db.upsert_shop(
        campaign_id="camp-2",
        prop_id="prop-2",
        name="Iron Ledger",
        shopkeeper_name="Brann",
        shop_type="blacksmith",
        description="",
        inventory=[],
        shop_sales_enabled=True,
        player_sell_enabled=False,
        buyback_enabled=False,
        accepted_item_types=["weapon", "armour"],
        vendor_cash_units=5000,
        buy_rate_pct=40,
    )

    shop = db.get_shop_by_prop_id("camp-2", "prop-2")
    assert shop is not None
    assert shop["shop_sales_enabled"] is True
    assert shop["player_sell_enabled"] is False
    # Back-compat alias should mirror player_sell_enabled for old client paths.
    assert shop["selling_enabled"] is False
    assert shop["buyback_enabled"] is False
    assert sorted(shop["accepted_item_types_json"]) == ["armour", "weapon"]
