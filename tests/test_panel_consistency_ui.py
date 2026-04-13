from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_play_has_shared_panel_consistency_classes():
    src = _play_html()
    for token in (
        '.panel-helper-text {',
        '.panel-empty-state {',
        '.panel-section-stack {',
    ):
        assert token in src


def test_right_panel_empty_states_use_shared_panel_empty_class():
    src = _play_html()
    for token in (
        'id="viewer-empty" class="viewer-empty panel-empty-state"',
        'id="inventory-empty" class="panel-empty-state"',
        'id="party-stash-empty" class="panel-empty-state"',
        'id="party-loot-empty" class="panel-empty-state"',
        'id="shop-ledger-empty" class="panel-empty-state"',
        'id="bestiary-empty" class="panel-empty-state"',
        'id="sl-empty" class="panel-empty-state"',
    ):
        assert token in src


def test_panel_helper_and_section_stack_adopted_in_inventory_and_shop():
    src = _play_html()
    assert 'id="inventory-tools-note" class="panel-helper-text"' in src
    assert '<div class="panel-helper-text">Click a shop prop on the map → Manage Stock to restock. Use Award Gold to refund a player.</div>' in src
    assert 'id="inventory-loot-log-section" class="panel-section-stack"' in src
