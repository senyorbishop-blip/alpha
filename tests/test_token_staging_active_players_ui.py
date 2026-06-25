from pathlib import Path


PLAY_HTML = Path('client/templates/play.html')


def _play_html() -> str:
    return PLAY_HTML.read_text(encoding='utf-8')


def test_dm_staging_rail_shows_connected_player_tokens_and_unowned_npcs():
    src = _play_html()
    assert 'function _stagingTokenBelongsToConnectedPlayer(token)' in src
    assert "String(user.role || '') === 'player'" in src
    assert '&& user.connected' in src
    assert '&& _tokenOwnedByUser(token, user)' in src
    assert 'function _stagingTokenVisibleToDm(token)' in src
    assert "if (!ownerId) return true;" in src
    assert 'return _stagingTokenBelongsToConnectedPlayer(token);' in src
    assert 'return list.filter(t => _stagingTokenVisibleToDm(t));' in src


def test_staging_rail_refreshes_when_player_presence_changes():
    src = _play_html()
    assert 'users[userHandle] = { ...u, id: userHandle, connected: true };\n      renderPlayerList();\n      buildStagingArea();' in src
    assert 'if (users[p.user_id]) users[p.user_id].connected = false;\n      renderPlayerList();\n      buildStagingArea();' in src
