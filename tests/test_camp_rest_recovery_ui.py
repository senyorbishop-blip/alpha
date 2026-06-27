from pathlib import Path


def test_camp_rest_module_has_player_recovery_summary_and_death_save_track():
    src = Path("client/static/js/ui/camp_rest.js").read_text(encoding="utf-8")
    assert "function _buildPlayerRecoveryHtml()" in src
    assert "function _buildDeathSaveTrackHtml(ds)" in src
    assert "Downed at 0 HP" in src
    assert "Hit dice spent this rest" in src


def test_play_html_has_mobile_friendly_camp_rest_recovery_styles():
    # CSS was extracted out of play.html into the dedicated stylesheet.
    src = Path("client/static/css/play.css").read_text(encoding="utf-8")
    assert ".cr-player-recovery {" in src
    assert ".cr-hit-die-btn {" in src
    assert ".cr-rest-btn { min-height: 44px;" in src
    assert ".cr-act-check input { width: 18px; height: 18px; }" in src


def test_play_html_shows_recovery_feedback_when_player_returns_above_zero_hp():
    src = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert "You're back up at" in src
