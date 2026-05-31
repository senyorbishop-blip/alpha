import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _play_html():
    with open(os.path.join(PROJECT_ROOT, "client", "templates", "play.html"), "r", encoding="utf-8") as f:
        return f.read()


def test_viewer_power_fx_payload_contains_recap_targets_and_approval_status():
    from server.handlers.viewer_powers import _viewer_power_fx_payload, VIEWER_BASE_POWER_DEFS
    from server.session import Token

    token = Token(id="tok-1", name="Goblin", x=100, y=150, width=50, height=50, color="#f00", shape="circle", owner_id="")
    payload = _viewer_power_fx_payload(
        VIEWER_BASE_POWER_DEFS["fireball"],
        "fireball",
        "Fireball",
        "SenyorFan",
        {"mode": "point", "x": 125, "y": 175},
        [token],
        "SenyorFan cast Fireball for 18 damage, hitting Goblin.",
        "dm_approved",
    )

    assert payload["recap_text"].startswith("SenyorFan cast Fireball")
    assert payload["approval_status"] == "dm_approved"
    assert payload["target_count"] == 1
    assert payload["targets"] == [{"token_id": "tok-1", "name": "Goblin"}]
    assert payload["target_point"] == {"x": 125.0, "y": 175.0}
    assert payload["radius_ft"] == 15.0


def test_viewer_power_fx_client_has_banner_recap_settings_and_visual_handlers():
    html = _play_html()

    required_markers = [
        "function _handleViewerPowerFx(p)",
        "function _appendViewerPowerRecap(p)",
        "Viewer Power Recap",
        "viewer_fx_intensity",
        "viewer_fx_disable_disruptive",
        "viewer-fx-reduce-motion",
        "function _drawViewerPowerTelegraph",
        "function _drawViewerPowerKnockbackArrow",
        "effect:'fireball'",
        "effect:'healing_spark'",
        "effect:'status_ring'",
        "effect:'item_gift'",
        "case 'viewer_power_fx'",
    ]
    missing = [marker for marker in required_markers if marker not in html]
    assert not missing


def test_viewer_power_settings_are_allowed_for_dm_broadcast():
    from server.handlers.content import ALLOWED_DM_SETTINGS

    assert "viewer_fx_intensity" in ALLOWED_DM_SETTINGS
    assert "viewer_fx_disable_disruptive" in ALLOWED_DM_SETTINGS
