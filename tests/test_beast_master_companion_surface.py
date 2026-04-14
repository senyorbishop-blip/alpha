def _load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_actions_tab_surfaces_beast_master_companion_token_controls():
    src = _load_text("client/static/js/character/tabs/actions_tab.js")
    assert "Beast Master Companion" in src
    assert "Place companion token" in src
    assert "placeBeastMasterCompanionToken" in src


def test_play_html_has_companion_token_spawn_runtime_hook():
    src = _load_text("client/templates/play.html")
    assert "function placeBeastMasterCompanionToken(companionData = {})" in src
    assert "tokenType: 'companion'" in src
    assert "sendWS({ type: 'token_create', payload });" in src
