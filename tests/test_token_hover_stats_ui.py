from pathlib import Path

PLAY_HTML = Path('client/templates/play.html')


def _src() -> str:
    return PLAY_HTML.read_text(encoding='utf-8')


def test_compact_token_hover_card_is_dm_toggleable_and_not_label_clutter():
    src = _src()
    assert 'id="token-hover-card"' in src
    assert 'Show compact token stats on hover' in src
    assert 'toggleCompactTokenHoverStats' in src
    assert "TOKEN_HOVER_STATS_SETTING_KEY = 'dm.showCompactTokenStatsOnHover'" in src
    # Passive perception should be in the hover card, not added as a new permanent token badge row.
    assert "${stat('PP', pp)}" in src
    assert "_tokenBadgeMeasurePill(`PP" not in src
    assert "_tokenBadgeMeasurePill(`Passive" not in src


def test_token_hover_card_respects_dm_stats_visibility_boundaries():
    src = _src()
    assert "if (ROLE === 'dm') return _showCompactTokenStatsOnHover;" in src
    # The hover card is DM-only: players used to get it on their own token, but
    # it popped up over their token on every hover/move with no way to dismiss
    # it, so the player branch was removed.
    assert "return ROLE === 'player' && _tokenOwnedByMe(token);" not in src
    assert "const canSeeDmStats = ROLE === 'dm' || _tokenOwnedByMe(token);" in src
    assert "updateTokenHoverCardFromPointer(e, _mw);" in src


def test_token_hover_card_includes_required_compact_stats():
    src = _src()
    for needle in [
        "token.name || 'Token'",
        "stat('HP', hpText)",
        "stat('AC', ac)",
        "_tokenHoverPassive(token, 'perception'",
        "_tokenHoverPassive(token, 'investigation'",
        "_tokenHoverPassive(token, 'insight'",
        "stat('Speed', speed ? `${speed} ft` : '—')",
        "_tokenHoverSenses(token)",
        "_tokenHoverConditionNames(token)",
        "Hidden from players",
    ]:
        assert needle in src


def test_character_book_passive_perception_auto_derives_from_perception_modifier():
    src = _src()
    assert 'function deriveCharacterBookPassivePerception()' in src
    assert "document.getElementById('cb-skill-perception')" in src
    assert 'return 10 + (Number.isFinite(skillMod) ? skillMod : wisMod);' in src
    assert 'syncCharacterBookPassivePerceptionDerived();' in src
    assert "set('char-passive', data.passivePerception != null ? data.passivePerception : '');" in src


def test_selected_token_editor_summary_shows_passive_perception():
    src = _src()
    assert 'id="te-summary-passive"' in src
    assert "const passive = document.getElementById('te-passive')?.value || t.passivePerception || '—';" in src
    assert "set('te-summary-passive', `${passive}`);" in src
