from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_combat_header_has_turn_summary_mount():
    src = _play_html()
    assert 'id="combat-turn-summary"' in src
    assert 'class="combat-turn-summary"' in src


def test_combat_entries_include_order_badges_and_meta_layout():
    src = _play_html()
    assert 'const orderBadge = isCurrent' in src
    assert "<span class=\"ce-order now\">Now</span>" in src
    assert "<span class=\"ce-order next\">Next</span>" in src
    assert '<div class="ce-meta">${targetStr}${hpStr}${defeatedStr}${hiddenStr}${ownerStr}${missingStr}${mapStr}${moveStr}</div>' in src


def test_tab_and_combat_panes_keep_scroll_containment():
    src = _play_html()
    assert 'overscroll-behavior: contain;' in src
    assert '#rtab-pane-combat {' in src
    assert 'overflow-y: auto;' in src
    assert '.combat-list {' in src
    assert 'touch-action: pan-y;' in src
