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
    assert '<div class="ce-meta">${targetStr}${hpStr}${defeatedStr}${hiddenStr}${ownerStr}${model.ownedByMe ?' in src


def test_tab_and_combat_panes_keep_scroll_containment():
    src = _play_html()
    assert 'overscroll-behavior: contain;' in src
    assert '#rtab-pane-combat {' in src
    assert 'overflow-y: auto;' in src
    assert '.combat-list {' in src
    assert 'touch-action: pan-y;' in src


def test_combat_cards_use_responsive_two_row_layout():
    src = _play_html()
    assert 'grid-template-columns: 2.35rem 1.75rem minmax(0, 1fr) auto;' in src
    assert '.ce-name-wrap { min-width:0; flex:1 1 auto; display:block; }' in src
    assert 'overflow: hidden; text-overflow: ellipsis; white-space: nowrap;' in src
    assert 'flex: 0 0 auto;' in src
    assert '@container (max-width: 340px)' in src
    assert '.ce-hp.move .ce-move-full { display:none; }' in src
    assert '.ce-hp.move .ce-move-short { display:inline; }' in src


def test_combat_cards_keep_full_names_and_owner_tooltips_accessible():
    src = _play_html()
    assert 'title="${escapeHtml(model.name)}"' in src
    assert 'class="ce-hp owner" title="${escapeHtml(ownerLabel)}"' in src
    assert '<span class="ce-name-wrap"><span class="ce-name"' in src
    assert 'Move ${Math.round(spentFt)}/${Math.round(totalFt)} ft${moveExtras}' in src
    assert '<span class="ce-move-short">${Math.round(spentFt)}/${Math.round(totalFt)} ft</span>' in src


def test_token_badges_drop_low_priority_labels_when_crowded():
    src = _play_html()
    assert 'const crowdedTokenLabels = zoom < 0.72' in src
    assert 'const veryCrowdedTokenLabels = zoom < 0.52' in src
    assert 'if (!veryCrowdedTokenLabels && canSeeVitals && token.ac' in src
    assert 'if (!crowdedTokenLabels) {' in src
    assert "rowsBelow.push(_tokenBadgeMeasurePill(isPlayerOwned ? 'PC' : 'NPC'" in src
