from pathlib import Path

PLAY = Path('client/templates/play.html').read_text(encoding='utf-8')


def _body(name: str) -> str:
    marker = f"function {name}("
    start = PLAY.index(marker)
    next_start = PLAY.find("\nfunction ", start + len(marker))
    return PLAY[start: next_start if next_start != -1 else len(PLAY)]


def test_token_badge_layout_function_is_single_stack_owner():
    body = _body('layoutTokenBadges')
    assert 'rowsAbove.push(_tokenBadgeMeasurePill(renderContext.turnLabel' in body
    assert 'rowsAbove.push(_tokenBadgeMeasurePill(`AC ${token.ac}`' in body
    assert 'rowsAbove.push(_tokenBadgeMeasurePill(`HP ${shownCur}/${shownMax}`' in body
    assert body.index('renderContext.turnLabel') < body.index('`AC ${token.ac}`') < body.index('`HP ${shownCur}/${shownMax}`')
    assert 'rowsBelow.push(_tokenBadgeMeasurePill(safeName' in body
    assert "rowsBelow.push(_tokenBadgeMeasurePill(isPlayerOwned ? 'PC' : 'NPC'" in body


def test_token_badge_layout_uses_measured_rows_not_fixed_overlapping_turn_offsets():
    body = _body('layoutTokenBadges')
    assert 'ctx.measureText(label).width' in _body('_tokenBadgeMeasurePill')
    assert 'row.y = y - row.height' in body
    assert 'y = row.y - gap' in body
    assert 'y = row.y + row.height + gap' in body
    assert 'sy - (18 / cam.zoom) - boxH' not in _body('drawToken')


def test_draw_token_renders_shared_badge_layout_for_now_next_ac_hp_and_type():
    body = _body('drawToken')
    assert 'const tokenBadgeLayout = layoutTokenBadges(t' in body
    assert "turnLabel: _isActiveTurn ? 'NOW' : (_isNextTurn ? 'NEXT' : '')" in body
    assert 'canSeeVitals' in body
    assert 'showHpText: showHpBar' in body
    assert 'drawTokenBadgeRows(tokenBadgeLayout)' in body
    assert "const _orderText = _isActiveTurn ? 'NOW'" not in body


def test_hidden_and_player_visibility_rules_are_preserved():
    body = _body('drawToken')
    assert "if (isHidden && ROLE !== 'dm') return" in body
    assert "const canSeeVitals = ROLE === 'dm' || isOwnToken" in body
    assert "ROLE === 'dm' || (ROLE === 'player' && isPlayerOwnedToken)" in body
