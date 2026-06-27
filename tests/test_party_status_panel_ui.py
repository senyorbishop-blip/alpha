from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def _play_css() -> str:
    return Path('client/static/css/play.css').read_text(encoding='utf-8')


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
    # CSS was extracted from play.html into play.css; these rules now live there.
    src = _play_css()
    assert '.party-status-list {' in src
    assert 'touch-action: pan-y;' in src
    assert '@media (max-width: 900px) {' in src
    assert '.party-status-hpbar { height: 10px; }' in src


def test_party_status_panel_resolves_owner_identity_for_legacy_owner_keys():
    src = _play_html()
    assert 'const ownedTokens = tokenPool.filter(t => _tokenOwnedByUser(t, u));' in src
    assert 'const tok = ownedTokens.find(t => !Boolean(t?.staged)) || ownedTokens[0] || null;' in src


def test_full_token_sync_refreshes_party_status_panel():
    # A joining player's token + HP arrive via the full-token-snapshot path
    # (applyAuthoritativeTokenSync). That path must re-render the party status
    # panel so health bars live-sync without a manual tab refresh.
    src = _play_html()
    sync_start = src.index('function applyAuthoritativeTokenSync(')
    sync_body = src[sync_start:sync_start + 2000]
    assert 'renderPartyStatusPanel' in sync_body
