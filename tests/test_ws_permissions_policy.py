import asyncio
from pathlib import Path

from server.handlers import handle_message
from server.handlers.common import manager
from server.handlers.ws_permissions import is_ws_message_allowed_for_role
from server.session import Session, User


ROOT = Path(__file__).resolve().parents[1]


def test_is_ws_message_allowed_for_role_covers_core_role_contracts():
    """ws_permissions.py is the canonical role/message decision table."""
    for msg_type in ["token_move", "fog_paint", "viewer_power_grant", "unknown_dm_tool"]:
        assert is_ws_message_allowed_for_role(msg_type, "dm").allowed, msg_type

    for msg_type in [
        "ping",
        "pong",
        "viewer_power_use",
        "viewer_cursor_update",
        "viewer_emote",
        "poll_vote",
    ]:
        assert is_ws_message_allowed_for_role(msg_type, "viewer").allowed, msg_type

    for msg_type in ["chat_message", "token_move", "dice_roll"]:
        assert is_ws_message_allowed_for_role(msg_type, "player").allowed, msg_type

    for msg_type in ["fog_paint", "editor_layer_save", "viewer_power_grant", "unknown_player_tool"]:
        decision = is_ws_message_allowed_for_role(msg_type, "player")
        assert not decision.allowed, msg_type
        assert decision.error_message == "You don't have permission to do that."

    for msg_type in ["chat_message", "ai_rules_oracle"]:
        assert is_ws_message_allowed_for_role(msg_type, "assistant_dm").allowed, msg_type

    for msg_type in ["token_delete", "token_create", "editor_layer_save", "grant_permission"]:
        decision = is_ws_message_allowed_for_role(msg_type, "assistant_dm")
        assert not decision.allowed, msg_type
        assert decision.error_message == "Assistant DM scope does not allow that action."


def test_handle_message_blocks_denied_messages_before_dispatch(monkeypatch):
    session = Session(id="session-policy-dispatch")
    user = User(id="player-policy-dispatch", name="Policy Player", role="player")
    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(manager, "send_to", fake_send_to)

    asyncio.run(handle_message({"type": "editor_layer_save", "payload": {"layers": []}}, session, user))

    assert sent == [
        (
            "session-policy-dispatch",
            "player-policy-dispatch",
            {"type": "error", "payload": {"message": "You don't have permission to do that."}},
        )
    ]


def test_main_websocket_endpoint_does_not_keep_duplicate_role_allow_lists():
    source = (ROOT / "main.py").read_text(encoding="utf-8")

    forbidden_markers = [
        "_VIEWER_ALLOWED",
        "_PLAYER_DENIED",
        "_ASSISTANT_DM_DENIED",
        "VIEWER_ALLOWED_MESSAGE_TYPES",
        "PLAYER_KNOWN_GAMEPLAY_MESSAGE_TYPES",
        "ASSISTANT_DM_DENIED_MESSAGE_TYPES",
        "DM_ADMIN_MESSAGE_TYPES",
    ]
    for marker in forbidden_markers:
        assert marker not in source, f"main.py must not maintain duplicate role policy marker {marker}"

    assert "await handle_message(raw, session, user)" in source
    assert "msg_type == \"pong\"" in source
