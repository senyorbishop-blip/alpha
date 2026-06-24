"""WebSocket role policy regression tests."""

from __future__ import annotations

import inspect

from server.handlers import handle_message
from server.handlers.ws_permissions import (
    DM_ADMIN_MESSAGE_TYPES,
    PLAYER_KNOWN_GAMEPLAY_MESSAGE_TYPES,
    is_ws_message_allowed_for_role,
)


def test_dispatch_calls_central_ws_role_policy_before_handler_lookup():
    source = inspect.getsource(handle_message)

    policy_index = source.index("is_ws_message_allowed_for_role")
    handler_index = source.index("handler = dispatch.get")
    assert policy_index < handler_index


def test_viewer_can_only_send_viewer_safe_messages():
    assert is_ws_message_allowed_for_role("viewer_power_use", "viewer").allowed
    assert is_ws_message_allowed_for_role("viewer_cursor_update", "viewer").allowed
    assert not is_ws_message_allowed_for_role("token_move", "viewer").allowed
    assert not is_ws_message_allowed_for_role("chat_message", "viewer").allowed


def test_player_cannot_send_real_editor_or_dm_admin_messages():
    denied = [
        "token_delete",
        "fog_paint",
        "fog_toggle",
        "editor_walls_save",
        "editor_walls_clear",
        "editor_props_save",
        "map_set_url",
        "door_toggle",
        "assistant_dm_permissions_set",
        "grant_permission",
        "combat_update",
        "combat_clear",
        "combat_add_token",
        "combat_remove_combatant",
        "hazard_zone_create",
        "camp_rest_take_rest",
        "ai_describe_scene",
    ]
    for msg_type in denied:
        decision = is_ws_message_allowed_for_role(msg_type, "player")
        assert not decision.allowed, msg_type
        assert decision.reason == "player_forbidden"


def test_player_owned_token_and_gameplay_messages_remain_allowed():
    allowed = [
        "token_create",
        "token_placed",
        "token_send_to_staging",
        "token_move",
        "token_edit",
        "token_hp_update",
        "inventory_transfer_item",
        "inventory_equip_item",
        "interactable_action",
        "prop_take_item",
        "combat_attack_request",
        "combat_roll_initiative",
        "combat_state_request",
        "combat_move_commit",
        "character_rest",
    ]
    for msg_type in allowed:
        assert is_ws_message_allowed_for_role(msg_type, "player").allowed, msg_type


def test_player_initiative_roll_is_not_classified_as_dm_admin():
    assert "combat_roll_initiative" in PLAYER_KNOWN_GAMEPLAY_MESSAGE_TYPES
    assert "combat_roll_initiative" not in DM_ADMIN_MESSAGE_TYPES
    assert is_ws_message_allowed_for_role("combat_roll_initiative", "player").allowed
    assert is_ws_message_allowed_for_role("combat_roll_initiative", "dm").allowed


def test_player_unknown_messages_default_deny():
    decision = is_ws_message_allowed_for_role("made_up_admin_action", "player")

    assert not decision.allowed
    assert decision.reason == "player_unknown_type"


def test_assistant_dm_blocks_high_risk_editor_and_identity_controls():
    denied = [
        "assistant_dm_permissions_set",
        "token_create",
        "token_delete",
        "token_placed",
        "fog_paint",
        "editor_walls_save",
        "map_set_url",
        "bring_all_to_map",
    ]
    for msg_type in denied:
        decision = is_ws_message_allowed_for_role(msg_type, "assistant_dm")
        assert not decision.allowed, msg_type
        assert decision.reason == "assistant_dm_forbidden"


def test_dm_can_send_any_dispatch_message():
    assert is_ws_message_allowed_for_role("editor_walls_save", "dm").allowed
    assert is_ws_message_allowed_for_role("made_up_future_dm_message", "dm").allowed
