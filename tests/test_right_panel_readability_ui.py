from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def _play_css() -> str:
    return Path('client/static/css/play.css').read_text(encoding='utf-8')


def test_right_panel_has_shared_readability_scaffold_classes():
    # CSS was extracted from play.html into play.css; these rules now live there.
    src = _play_css()
    for token in (
        '.rtab-pane-head {',
        '.rtab-pane-head-actions {',
        '.rtab-pane-scroll {',
        '.rtab-pane-note {',
    ):
        assert token in src


def test_major_right_tabs_opt_out_of_nested_shell_scroll_when_active():
    # CSS was extracted from play.html into play.css; these rules now live there.
    src = _play_css()
    for pane in (
        '#rtab-pane-party.active',
        '#rtab-pane-inventory.active',
        '#rtab-pane-shop.active',
        '#rtab-pane-bestiary.active',
        '#rtab-pane-spelllib.active',
        '#rtab-pane-log.active',
        '#rtab-pane-memory.active',
        '#rtab-pane-combat.active',
    ):
        assert pane in src


def test_shop_bestiary_and_spell_tabs_use_shared_header_structure():
    src = _play_html()
    assert '<div class="rtab-pane-head" style="border-bottom-color:rgba(201,162,39,0.12);background:rgba(201,162,39,0.04);">' in src
    assert '<div class="rtab-pane-head" style="border-bottom-color:rgba(93,122,255,0.15);background:rgba(93,122,255,0.04);">' in src
    assert '<div class="sl-header rtab-pane-head" style="border-bottom-color:rgba(155,89,182,0.2);background:rgba(155,89,182,0.05);">' in src
