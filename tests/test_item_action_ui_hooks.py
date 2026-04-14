from pathlib import Path


def test_actions_tab_renders_item_actions_section():
    src = Path('client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
    assert "'Item Actions'" in src
    assert "_buildItemActionCards" in src


def test_play_html_has_item_action_use_route():
    src = Path('client/templates/play.html').read_text(encoding='utf-8')
    assert "inventory_use_item_action" in src
    assert "source: 'item_action'" in src
