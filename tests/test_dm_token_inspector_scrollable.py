"""Tests that DM token editor panel is viewport-scrollable."""


def _read_play():
    with open("client/templates/play.html") as f:
        return f.read()


def test_token_editor_has_max_height():
    src = _read_play()
    idx = src.find('id="token-editor"')
    assert idx >= 0, "token-editor div must exist"
    snippet = src[idx:idx+400]
    assert "max-height" in snippet, \
        f"token-editor must have max-height CSS; snippet: {snippet[:200]}"


def test_token_editor_has_overflow_y():
    src = _read_play()
    idx = src.find('id="token-editor"')
    assert idx >= 0
    snippet = src[idx:idx+400]
    assert "overflow-y" in snippet, \
        f"token-editor must have overflow-y CSS; snippet: {snippet[:200]}"


def test_token_editor_max_height_is_viewport_relative():
    src = _read_play()
    idx = src.find('id="token-editor"')
    snippet = src[idx:idx+400]
    assert "90vh" in snippet or "80vh" in snippet, \
        "token-editor max-height should be viewport-relative (vh units)"
