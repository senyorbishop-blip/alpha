from pathlib import Path


def test_shop_panel_declares_buyback_and_accept_types_before_template_use():
    src = Path("client/static/js/editor/shop_panel.js").read_text(encoding="utf-8")

    assert "const buybackEnabled = !!instance.buyback_enabled;" in src
    assert "const acceptedSet = new Set(acceptedTypesRaw.map(v => String(v || '').trim().toLowerCase()).filter(Boolean));" in src
    assert "id=\"sp-buyback-enabled\" ${buybackEnabled ? 'checked' : ''}" in src


def test_shop_panel_selling_control_ids_are_unique():
    src = Path("client/static/js/editor/shop_panel.js").read_text(encoding="utf-8")

    assert src.count('id="sp-shop-sales-enabled"') == 1
    assert src.count('id="sp-player-sell-enabled"') == 1
    assert 'id="sp-selling-enabled"' not in src


def test_shop_panel_normalizes_legacy_inventory_shape():
    src = Path("client/static/js/editor/shop_panel.js").read_text(encoding="utf-8")

    assert "const item_name = String(raw.item_name || raw.name || '').trim();" in src
    assert "const priceFromUnits = Number(raw.price_units);" in src
    assert "if (raw.infinite || raw.unlimited) quantity = null;" in src
