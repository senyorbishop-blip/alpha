from pathlib import Path


PLAY_HTML = Path('client/templates/play.html')


def _play_html() -> str:
    return PLAY_HTML.read_text(encoding='utf-8')


def test_dm_staging_rail_filters_to_connected_player_tokens():
    src = _play_html()
    assert 'function _stagingTokenBelongsToConnectedPlayer(token)' in src
    assert "String(user.role || '') === 'player'" in src
    assert '&& user.connected' in src
    assert '&& _tokenOwnedByUser(token, user)' in src
    assert 'return list.filter(t => _stagingTokenBelongsToConnectedPlayer(t));' in src


def test_staging_rail_refreshes_when_player_presence_changes():
    src = _play_html()
    assert 'users[u.id] = { ...u, connected: true };\n      renderPlayerList();\n      buildStagingArea();' in src
    assert 'if (users[p.user_id]) users[p.user_id].connected = false;\n      renderPlayerList();\n      buildStagingArea();' in src
