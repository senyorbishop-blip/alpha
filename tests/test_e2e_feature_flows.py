"""
tests/test_e2e_feature_flows.py — End-to-end scenario tests for the
D&D tabletop application.

These tests exercise complete user flows as they would happen in a real
session, covering:

1. Happy path — DM starts session, player joins, combat runs end-to-end
2. Error recovery — unknown WS message type handled gracefully
3. Tab switching with unsaved state — changing map context preserves prior data
4. Whisper chat — private messages only reach sender and target
5. Viewer restrictions — viewers cannot send chat or trigger DM actions
6. Role-based state snapshots — each role receives correct subset of state
7. Request state — reconnecting player receives full sync
8. Journal upsert flow — DM creates journal entry, stored in session
9. Discovery flow — DM triggers discovery, only correct player receives it
10. Poll lifecycle — create → vote → close
11. WS dispatch routing — handle_message routes all known types
12. Accessibility / keyboard nav — play.html tab elements identifiable

Why these tests matter:
End-to-end scenarios catch cross-handler regressions that unit/integration
tests may miss.  They verify the entire message lifecycle from WS receipt
through handler dispatch to broadcast delivery.
"""
import asyncio
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_session():
    """Create a session with DM, player, and viewer users."""
    from server.session import Session, User
    session = Session(id="e2e-session-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    viewer = User(id="viewer1", name="Spectator", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.log = []
    session.fog_maps = {"world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16}}
    return session, dm, player, viewer


def _patch_manager(monkeypatch):
    """
    Patch the singleton manager object's broadcast/send_to methods.
    Because all handlers import the same manager object from server.connections,
    this single patch affects every handler module.
    """
    import server.handlers.common as common_mod

    broadcasts = []
    sent = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "broadcast", _broadcast)
    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)
    return broadcasts, sent


# ---------------------------------------------------------------------------
# 1. Happy path: DM starts combat, player rolls initiative
# ---------------------------------------------------------------------------

def test_e2e_combat_happy_path(monkeypatch):
    """
    Full combat flow:
    1. DM starts combat with two combatants
    2. DM advances to next turn
    3. State is broadcast at each step
    """
    from server.handlers import combat as ch
    from server.session import Session, User, Token
    session = Session(id="e2e-combat-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    token1 = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                   color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    token2 = Token(id="tok2", name="Wolf", x=100, y=100, width=40, height=40,
                   color="#888", shape="circle", owner_id=None, hp=12, max_hp=12)
    session.tokens[token1.id] = token1
    session.tokens[token2.id] = token2

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    async def _noop_hazards(_session, **kwargs):
        return None

    import server.handlers.hazards as haz
    monkeypatch.setattr(haz, "_process_current_start_turn_hazards", _noop_hazards)
    monkeypatch.setattr(haz, "_process_current_end_turn_hazards", _noop_hazards)
    monkeypatch.setattr(haz, "_process_end_round_hazards", _noop_hazards)

    # DM starts combat
    asyncio.run(ch.handle_combat_update({
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": [
            {"id": "c1", "token_id": "tok1", "name": "Alice", "initiative": 20, "is_player": True, "owner_id": "player1", "hp": 20, "max_hp": 20},
            {"id": "c2", "token_id": "tok2", "name": "Wolf", "initiative": 10, "is_player": False, "hp": 12, "max_hp": 12},
        ],
    }, session, dm))

    combat_types = [msg["type"] for _, msg, _ in broadcasts]
    assert "combat_state" in combat_types

    # DM advances turn
    asyncio.run(ch.handle_combat_next({}, session, dm))
    assert session.combat["turn"] == 1


# ---------------------------------------------------------------------------
# 2. Error recovery: unknown WS message type returns error
# ---------------------------------------------------------------------------

def test_e2e_unknown_ws_message_type_returns_error(monkeypatch):
    """
    Sending an unknown WS message type should return an error message
    to the sender, not raise an exception.
    """
    from server.handlers import handle_message
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(handle_message(
        {"type": "totally_unknown_message_type_xyz", "payload": {}},
        session,
        player,
    ))

    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert error_msgs, "Unknown message type should produce an error response to the sender"


# ---------------------------------------------------------------------------
# 3. Tab switching: map context change preserves world layers
# ---------------------------------------------------------------------------

def test_e2e_map_context_switch_preserves_world_layers(monkeypatch):
    """
    DM navigating from world map to a local map should not overwrite world
    editor layers with local map data.
    """
    from server.handlers import map_editor as me
    session, dm, player, viewer = _make_full_session()
    # Pre-populate world layers — key format is "x:y", value is tile ID (int)
    session.editor_layers = {"world": {"1:1": 1}}
    session.fog_maps["local1"] = {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16}

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    # Save a layer in the local map context
    asyncio.run(me.handle_editor_layer_save(
        {"map_context": "local1", "cells": {"5:5": 2}},
        session,
        dm,
    ))

    # World data must be preserved
    world_layers = (session.editor_layers or {}).get("world", {})
    assert world_layers.get("1:1") == 1

    # Local data must also be present
    local_layers = (session.editor_layers or {}).get("local1", {})
    assert "5:5" in local_layers


# ---------------------------------------------------------------------------
# 4. Whisper chat — private messages only reach sender and target
# ---------------------------------------------------------------------------

def test_e2e_whisper_chat_only_reaches_sender_and_target(monkeypatch):
    """
    A whisper message must be sent only to the sender and their target,
    not broadcast to the whole session.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    # _patch_manager patches the actual manager object; content.manager is the same object
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_chat_message(
        {
            "message": "Secret whisper",
            "channel": "whisper",
            "target_user_id": "dm1",
        },
        session,
        player,
    ))

    # Must be sent only to sender (player1) and target (dm1)
    whisper_recipients = [uid for _, uid, msg in sent if msg.get("type") == "chat_message"]
    assert sorted(whisper_recipients) == ["dm1", "player1"]

    # Must NOT be broadcast
    broadcast_chat = [
        msg for _, msg, _ in broadcasts
        if isinstance(msg, dict) and msg.get("type") == "chat_message"
    ]
    assert len(broadcast_chat) == 0


# ---------------------------------------------------------------------------
# 5. Viewer restrictions — viewers cannot send chat
# ---------------------------------------------------------------------------

def test_e2e_viewer_cannot_send_chat(monkeypatch):
    """
    Viewers are receive-only for chat. A viewer sending a chat message
    must not produce any broadcast.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_chat_message(
        {"message": "Viewer says hi"},
        session,
        viewer,
    ))

    chat_broadcasts = [
        msg for _, msg, _ in broadcasts
        if isinstance(msg, dict) and msg.get("type") == "chat_message"
    ]
    assert len(chat_broadcasts) == 0


# ---------------------------------------------------------------------------
# 6. Role-based state snapshots
# ---------------------------------------------------------------------------

def test_e2e_player_state_snapshot_excludes_hidden_tokens():
    """
    to_state_dict_for_role called for a player should not include tokens
    that are marked as hidden.
    """
    from server.session import Session, User, Token
    session = Session(id="e2e-state-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    visible = Token(id="vis1", name="Wolf", x=0, y=0, width=40, height=40,
                    color="#888", shape="circle", owner_id=None)
    hidden = Token(id="hid1", name="Shadow Wolf", x=0, y=0, width=40, height=40,
                   color="#333", shape="circle", owner_id=None)
    visible.hidden = False
    hidden.hidden = True
    session.tokens[visible.id] = visible
    session.tokens[hidden.id] = hidden

    state = session.to_state_dict_for_role("player", player.id)
    token_ids = list((state.get("tokens") or {}).keys())
    assert "vis1" in token_ids
    assert "hid1" not in token_ids


def test_e2e_dm_state_snapshot_includes_hidden_tokens():
    """
    DM state snapshot must include all tokens, including hidden ones.
    """
    from server.session import Session, User, Token
    session = Session(id="e2e-state-2")
    dm = User(id="dm1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id

    hidden = Token(id="hid2", name="Shadow Wolf", x=0, y=0, width=40, height=40,
                   color="#333", shape="circle", owner_id=None)
    hidden.hidden = True
    session.tokens[hidden.id] = hidden

    state = session.to_state_dict_for_role("dm", dm.id)
    token_ids = list((state.get("tokens") or {}).keys())
    assert "hid2" in token_ids


# ---------------------------------------------------------------------------
# 7. Request state — reconnecting player receives full sync
# ---------------------------------------------------------------------------

def test_e2e_request_state_sends_full_state_to_player(monkeypatch):
    """
    handle_request_state should send the full session state to the
    requesting user.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_request_state({}, session, player))

    state_msgs = [msg for _, uid, msg in sent
                  if uid == player.id and msg.get("type") == "state_sync"]
    assert state_msgs, "Reconnecting player must receive a state_sync message"


# ---------------------------------------------------------------------------
# 8. Journal upsert flow — DM creates entry, stored in session
# ---------------------------------------------------------------------------

def test_e2e_journal_upsert_stored_and_synced(monkeypatch):
    """
    DM upserting a journal entry should store it in session.journal_entries
    and broadcast to all session members.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    asyncio.run(ch.handle_journal_upsert(
        {"id": "j1", "title": "The Whispering Keep", "content": "Ancient ruins abound."},
        session,
        dm,
    ))

    # Journal entry must be stored in session
    entries = getattr(session, "journal_entries", []) or []
    assert len(entries) > 0
    assert any(e.get("title") == "The Whispering Keep" for e in entries)

    # journal_sync must have been sent to each user
    journal_types = [msg.get("type") for _, uid, msg in sent]
    assert "journal_sync" in journal_types


# ---------------------------------------------------------------------------
# 9. Discovery flow — target player only
# ---------------------------------------------------------------------------

def test_e2e_discovery_private_player_targeting(monkeypatch):
    """
    DM triggering a private discovery should send it only to the target
    player, not broadcast to everyone.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_discovery_trigger(
        {
            "title": "Hidden Compartment",
            "body": "Behind the painting you find a key.",
            "kind": "clue",
            "visibility": "private_player",
            "target_user_id": player.id,
        },
        session,
        dm,
    ))

    card_recipients = [uid for _, uid, msg in sent if msg.get("type") == "discovery_card"]
    assert card_recipients == [player.id], (
        "Private discovery must be sent only to the target player"
    )


# ---------------------------------------------------------------------------
# 10. Poll lifecycle — create → vote → close
# ---------------------------------------------------------------------------

def test_e2e_poll_create_and_vote(monkeypatch):
    """
    DM creates a poll, player votes by index, DM closes it.
    Each step should produce appropriate state changes.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    # Create
    asyncio.run(ch.handle_poll_create(
        {"question": "Split or stay?", "options": ["Split", "Stay"]},
        session,
        dm,
    ))

    assert session.active_poll is not None
    poll_id = session.active_poll["id"]

    all_types_after_create = [msg["type"] for _, msg, _ in broadcasts] + [msg["type"] for _, uid, msg in sent]
    assert any("poll" in t for t in all_types_after_create)

    # Vote using option_index (int) — the handler requires an int, not a string
    asyncio.run(ch.handle_poll_vote(
        {"poll_id": poll_id, "option_index": 1},
        session,
        player,
    ))

    assert player.id in (session.active_poll.get("votes") or {})

    # Close
    asyncio.run(ch.handle_poll_close(
        {"poll_id": poll_id},
        session,
        dm,
    ))

    assert session.active_poll is None or session.active_poll.get("closed") is True


def test_e2e_poll_vote_with_string_option_index_rejected(monkeypatch):
    """
    handle_poll_vote requires option_index to be an int.
    Sending a string should be silently rejected without crashing or recording a vote.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_full_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    asyncio.run(ch.handle_poll_create(
        {"question": "Go left or right?", "options": ["Left", "Right"]},
        session,
        dm,
    ))

    poll_id = session.active_poll["id"]

    # Intentionally pass a string — handler should reject it
    asyncio.run(ch.handle_poll_vote(
        {"poll_id": poll_id, "option_index": "Left"},
        session,
        player,
    ))

    # No vote should be recorded
    votes = (session.active_poll.get("votes") or {})
    assert player.id not in votes, "String option_index must not produce a recorded vote"


def test_e2e_ws_dispatch_routes_known_message_types():
    """
    handle_message must define dispatch entries for all critical message
    types used throughout the application.
    """
    import inspect
    from server.handlers import handle_message
    source = inspect.getsource(handle_message)

    critical_types = [
        "token_move", "token_create", "token_delete",
        "combat_update", "combat_next",
        "fog_paint", "fog_toggle",
        "chat_message", "dice_roll",
        "inventory_add_item",
        "journal_upsert",
        "discovery_trigger",
        "sound_set_ambient",
        "request_state",
    ]
    for t in critical_types:
        assert t in source, f"Critical message type '{t}' missing from handle_message dispatch"


# ---------------------------------------------------------------------------
# 12. Accessibility: play.html tab elements are keyboard-accessible buttons
# ---------------------------------------------------------------------------

def test_e2e_play_html_main_tabs_are_buttons():
    """
    The main right panel tabs (combat, inventory, party, log, etc.) must use
    <button> elements so they are keyboard-accessible without JavaScript
    event delegation hacks.
    """
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    # The right-panel tabs use class="rtab"
    assert 'class="rtab' in src, (
        "play.html must have rtab button elements for keyboard-accessible tab navigation"
    )
    # They must be <button> elements
    assert '<button class="rtab' in src, (
        "Right-panel tabs must use <button> elements for keyboard accessibility"
    )


def test_e2e_play_html_has_data_rtab_target_attributes():
    """
    Tab buttons must carry data-rtab-target attributes that identify the
    associated panel — this enables JS tab switching without coupling to
    element position.
    """
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'data-rtab-target=' in src, (
        "Tab buttons must carry data-rtab-target attributes for panel association"
    )


def test_e2e_play_html_tab_panels_exist_for_each_nav_tab():
    """
    For each key tab button, a corresponding rtab-pane element must exist.
    """
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    key_tabs = ["combat", "inventory", "party", "log"]
    for tab in key_tabs:
        assert f'id="rtab-pane-{tab}"' in src or f"id='rtab-pane-{tab}'" in src, (
            f"play.html must have an rtab-pane for the '{tab}' tab"
        )


def test_e2e_play_html_has_dialog_elements_with_aria():
    """
    Modal dialogs/overlays in play.html must carry role='dialog' and
    aria-modal or aria-label for screen reader accessibility.
    """
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'role="dialog"' in src or "role='dialog'" in src, (
        "play.html must have at least one dialog element with role='dialog'"
    )


# ---------------------------------------------------------------------------
# 13. Error recovery: partial payload does not crash handlers
# ---------------------------------------------------------------------------

def test_e2e_inventory_add_item_with_partial_payload_does_not_crash(monkeypatch):
    """
    Sending a minimal/partial payload to inventory_add_item should not
    raise an unhandled exception.
    """
    from server.handlers import inventory as inv
    from server.session import Session, User
    session = Session(id="e2e-partial-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(inv, "save_campaign_async", _save)

    # Only name provided — all other fields missing
    asyncio.run(inv.handle_inventory_add_item(
        {"name": "Mystery Item"},
        session,
        dm,
    ))
    # Should complete without raising


def test_e2e_combat_update_empty_combatants_does_not_crash(monkeypatch):
    """
    Sending combat_update with an empty combatants list should not crash.
    """
    from server.handlers import combat as ch
    from server.session import Session, User
    session = Session(id="e2e-empty-combat")
    dm = User(id="dm1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.combat = {"active": False, "turn": 0, "combatants": []}

    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    async def _noop_hazards(_session, **kwargs):
        return None

    import server.handlers.hazards as haz
    monkeypatch.setattr(haz, "_process_current_start_turn_hazards", _noop_hazards)

    asyncio.run(ch.handle_combat_update(
        {"active": False, "turn": 0, "combatants": []},
        session,
        dm,
    ))
    # Should complete without raising


# ---------------------------------------------------------------------------
# 14. Tab switching: requesting state after map context change
# ---------------------------------------------------------------------------

def test_e2e_player_receives_correct_state_after_map_context_change(monkeypatch):
    """
    When the DM switches to a local map, a reconnecting player's
    state_sync should reflect the current map context.
    """
    from server.handlers import content as ch
    from server.session import Session, User
    session = Session(id="e2e-ctx-switch")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id
    session.dm_map_context = "local-tavern"
    session.log = []

    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_request_state({}, session, player))

    state_msgs = [msg for _, uid, msg in sent
                  if uid == player.id and msg.get("type") == "state_sync"]
    assert state_msgs
    state_payload = state_msgs[0].get("payload") or {}
    assert state_payload.get("dm_map_context") == "local-tavern"
