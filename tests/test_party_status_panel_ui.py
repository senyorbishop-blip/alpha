from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_party_status_panel_mount_and_renderer_present():
    src = _play_html()
    assert 'id="party-status-panel"' in src
    assert 'function renderPartyStatusPanel()' in src
    assert 'function _partyStatusCombatantByTokenId(tokenId = \'\')' in src
    assert 'function _tokenOwnedByUser(token, user)' in src


def test_party_status_panel_includes_player_safe_combat_state_markers():
    src = _play_html()
    assert 'party-status-chip conc' in src
    assert 'party-status-chip downed' in src
    assert 'party-status-chip death' in src
    assert "card.initiativeLabel ?" in src
    assert "card.hiddenHp" in src


def test_party_status_panel_mobile_first_styles_present():
    src = _play_html()
    assert '.party-status-list {' in src
    assert 'touch-action: pan-y;' in src
    assert '@media (max-width: 900px) {' in src
    assert '.party-status-hpbar { height: 10px; }' in src


def test_party_status_panel_resolves_owner_identity_for_legacy_owner_keys():
    src = _play_html()
    assert 'const ownedTokens = tokenPool.filter(t => _tokenOwnedByUser(t, u));' in src
    assert 'const tok = ownedTokens.find(t => !Boolean(t?.staged)) || ownedTokens[0] || null;' in src
