from pathlib import Path


def test_play_html_has_dm_weight_button_and_handler():
    source = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert "function dmSetInventoryItemWeight(" in source
    assert "inventory_update_item_weight" in source
    assert "⚖ Set Weight" in source


def test_play_html_camp_rest_button_uses_server_dm_authority():
    source = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert "function onCampRestTopbarClick()" in source
    assert "isServerAuthoritativeDm()" in source
    assert "function _updateCampRestTopbarBtn(cr)" in source


def test_play_html_uses_token_owned_by_me_helper_for_player_movement():
    source = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert "function _tokenOwnedByMe(token)" in source
    assert "if (ROLE === 'player' && _tokenOwnedByMe(t)) return true;" in source
    assert "const hitIsSelectable = hit && (ROLE === 'dm' || _tokenOwnedByMe(hit));" in source
