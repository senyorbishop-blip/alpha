from pathlib import Path


def test_play_page_loads_item_image_resolver_and_uses_shared_helpers():
    src = Path('client/templates/play.html').read_text(encoding='utf-8')
    assert '/static/js/ui/item_image_resolver.js' in src
    assert 'function resolveItemVisual(item)' in src
    assert 'function renderItemVisualToken(item, options = {})' in src
    assert 'renderItemVisualToken(item, { size: 20, radius: 6' in src


def test_shop_and_chest_views_use_central_item_image_helper():
    shop_src = Path('client/static/js/editor/shop_view.js').read_text(encoding='utf-8')
    chest_src = Path('client/static/js/editor/chest_view.js').read_text(encoding='utf-8')

    # Shop view still calls the central AppItemImages helper directly through its
    # renderItemToken wrapper.
    assert 'window.AppItemImages.renderToken' in shop_src
    assert 'function renderItemToken(item, size = 22)' in shop_src
    assert 'renderItemToken(' in shop_src
    # Both shop and chest now also route item rows through the shared ItemRow
    # component, which itself renders icons via the central AppItemImages helper.
    assert 'window.ItemRow.renderItemRow' in shop_src
    assert 'window.ItemRow.renderItemRow' in chest_src


def test_item_image_resolver_manifest_supports_category_subtype_and_override_maps():
    src = Path('client/static/js/ui/item_image_resolver.js').read_text(encoding='utf-8')
    assert 'const KEY_TO_ASSET' in src
    assert 'const CATEGORY_TO_KEY' in src
    assert 'const SUBTYPE_TO_KEY' in src
    assert 'const ITEM_OVERRIDES' in src
    assert 'function resolveItemImage(item)' in src
