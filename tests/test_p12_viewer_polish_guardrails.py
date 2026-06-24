"""P12 viewer polish guardrails.

Viewer polish should keep spectator interaction fun without exposing DM/player
controls. These tests lock the viewer-safe message contract and the viewer power
client module boundary.
"""

from __future__ import annotations

from pathlib import Path

from server.handlers.ws_permissions import (
    DM_ADMIN_MESSAGE_TYPES,
    VIEWER_ALLOWED_MESSAGE_TYPES,
    is_ws_message_allowed_for_role,
)

ROOT = Path(__file__).resolve().parents[1]
VIEWER_JS = ROOT / "client" / "static" / "js" / "gameplay" / "viewer_powers.js"


def test_viewer_allowed_messages_are_small_and_intentional():
    assert VIEWER_ALLOWED_MESSAGE_TYPES == frozenset({
        "ping",
        "pong",
        "viewer_power_use",
        "viewer_cursor_update",
        "viewer_emote",
        "poll_vote",
    })


def test_viewer_can_use_polish_actions_but_not_gameplay_or_admin_actions():
    allowed = ["viewer_power_use", "viewer_cursor_update", "viewer_emote", "poll_vote"]
    denied = [
        "chat_message",
        "token_move",
        "token_create",
        "combat_attack_request",
        "viewer_power_grant",
        "viewer_power_revoke",
        "viewer_presence_toggle",
        "fog_paint",
    ]

    for msg_type in allowed:
        assert is_ws_message_allowed_for_role(msg_type, "viewer").allowed, msg_type
    for msg_type in denied:
        assert not is_ws_message_allowed_for_role(msg_type, "viewer").allowed, msg_type


def test_viewer_power_admin_messages_remain_dm_admin_only():
    for msg_type in [
        "viewer_power_create",
        "viewer_power_grant",
        "viewer_power_grant_preset",
        "viewer_power_revoke",
        "viewer_power_pending_decision",
        "viewer_presence_toggle",
    ]:
        assert msg_type in DM_ADMIN_MESSAGE_TYPES
        assert not is_ws_message_allowed_for_role(msg_type, "viewer").allowed
        assert not is_ws_message_allowed_for_role(msg_type, "player").allowed
        assert is_ws_message_allowed_for_role(msg_type, "dm").allowed


def test_viewer_power_client_module_owns_public_contract():
    src = VIEWER_JS.read_text(encoding="utf-8")

    assert "window.AppGameplayViewer" in src
    for marker in [
        "viewerProfileEntries",
        "viewerPowerDefs",
        "viewerPowerName",
        "viewerPowerDescription",
        "viewerPowerActionLabel",
        "viewerPowerCooldownLabel",
        "viewerFxScreenPoint",
        "showViewerFx",
    ]:
        assert marker in src


def test_viewer_power_catalog_keeps_clear_target_modes_and_cooldown_labels():
    src = VIEWER_JS.read_text(encoding="utf-8")

    assert "target_mode:'token'" in src
    assert "target_mode:'point'" in src
    assert "cooldown_sec" in src
    assert "No cooldown" in src
    assert "s cooldown" in src
    assert "Target on Map" in src
    assert "Use on Token" in src


def test_viewer_fx_nodes_are_non_interactive_and_self_cleanup():
    src = VIEWER_JS.read_text(encoding="utf-8")

    assert "pointerEvents = 'none'" in src or "pointerEvents:'none'" in src
    assert "zIndex" in src
    assert "setTimeout" in src
    assert ".remove()" in src


def test_viewer_fx_supports_recap_friendly_power_effects():
    src = VIEWER_JS.read_text(encoding="utf-8")

    for marker in [
        "healing_spark",
        "lightning_strike",
        "status_ring",
        "item_gift",
        "fireball",
    ]:
        assert marker in src
