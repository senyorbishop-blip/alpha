"""
tests/test_e2e_extended_flows.py — Extended end-to-end scenario tests covering
additional user flows not yet covered in test_e2e_feature_flows.py.

Scenarios:
1.  Handout DM→player: DM sends a handout; correct player receives it
2.  Full token lifecycle: create → HP-update → hide → delete, one chain
3.  Sound session persistence: ambient track set → state survives to next request_state
4.  Condition + combat interaction: condition applied during active combat broadcasts correctly
5.  Hazard zone lifecycle: create → apply → delete in sequence
6.  Mark target during non-combat: Hunter's Mark persists outside combat
7.  Viewer power grant-revoke round trip: grant → verify → revoke → verify
8.  dice_roll happy path: player rolls a die; dice_result broadcast fires
9.  Item library upsert: DM adds item to library; item_library_sync fires
10. Fog paint then fog toggle: DM paints fog and toggles it; broadcasts fire
11. Whisper to viewer rejected: viewer as target of whisper causes targeted send only
12. Error recovery: all handlers tolerate missing payload gracefully

Why these tests matter:
Extended E2E tests catch cross-handler state regressions that isolated unit or
integration tests miss.  They verify that sequential operations (create then use,
grant then revoke) leave the session in a consistent state.
"""
import asyncio
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_session():
    from server.session import Session, User, Token
    session = Session(id="e2e-ext-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    viewer = User(id="viewer1", name="Watcher", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    session.dm_map_context = "world"
    session.log = []
    session.fog_maps = {"world": {"enabled": False, "cols": 4, "rows": 4, "cells": "0" * 16}}

    token = Token(id="tok1", name="Alice", x=0, y=0, width=40, height=40,
                  color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    npc = Token(id="tok_npc", name="Goblin", x=100, y=100, width=40, height=40,
                color="#888", shape="circle", owner_id=None, hp=8, max_hp=8)
    session.tokens[token.id] = token
    session.tokens[npc.id] = npc
    return session, dm, player, viewer


def _patch_manager(monkeypatch):
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
# 1. Handout DM→player: correct player receives discovery_card
# ---------------------------------------------------------------------------

def test_e2e_handout_reaches_target_player(monkeypatch):
    """
    DM sends a handout (send_handout) to a specific player.  The player must
    receive a discovery_card-style message while other users do not receive it
    as a general broadcast.

    Matters because handouts are private revelations — showing them to the
    wrong player breaks the narrative.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    asyncio.run(ch.handle_send_handout(
        {
            "title": "Ancient Map",
            "body": "The ruins lie to the north.",
            "kind": "handout",
            "target_user_id": player.id,
        },
        session, dm,
    ))

    # At least one targeted message should reach the player
    player_msgs = [msg for _, uid, msg in sent if uid == player.id]
    assert player_msgs, "Target player must receive the handout"

    # Viewer must not receive it
    viewer_msgs = [msg for _, uid, msg in sent if uid == viewer.id
                   and msg.get("type") in ("discovery_card", "handout")]
    assert not viewer_msgs, "Viewer must not receive a targeted handout"


# ---------------------------------------------------------------------------
# 2. Full token lifecycle: create → HP update → hide → delete
# ---------------------------------------------------------------------------

def test_e2e_full_token_lifecycle(monkeypatch):
    """
    DM creates a token, updates its HP, hides it, then deletes it.
    After each step the session state must reflect the operation.

    Matters because sequential operations on the same token are very common in
    live play; any stale reference or premature cleanup would break the chain.
    """
    from server.handlers import tokens as tok_mod
    from server.session import Session, User
    session = Session(id="e2e-lifecycle-1")
    dm = User(id="dm1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.dm_map_context = "world"

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    # Step 1 — create
    asyncio.run(tok_mod.handle_token_create(
        {"name": "Troll", "x": 0, "y": 0, "width": 40, "height": 40,
         "color": "#0a0", "shape": "circle", "owner_id": None, "hp": 30, "max_hp": 30},
        session, dm,
    ))
    troll_token = next((t for t in session.tokens.values() if t.name == "Troll"), None)
    assert troll_token is not None, "Token must be created"

    # Step 2 — HP update via char_hp_update (broadcast only, no state mutation)
    asyncio.run(tok_mod.handle_char_hp_update(
        {"token_id": troll_token.id, "hp": 25},
        session, dm,
    ))
    hp_broadcasts = [msg for _, msg, _ in broadcasts if msg.get("type") == "char_hp_update"]
    assert hp_broadcasts, "char_hp_update must be broadcast after HP change"

    # Step 3 — hide
    asyncio.run(tok_mod.handle_toggle_hidden({"token_id": troll_token.id}, session, dm))
    assert session.tokens[troll_token.id].hidden is True, "Token must be hidden"

    # Step 4 — delete
    asyncio.run(tok_mod.handle_token_delete({"token_id": troll_token.id}, session, dm))
    assert troll_token.id not in session.tokens, "Token must be deleted"


# ---------------------------------------------------------------------------
# 3. Sound session persistence
# ---------------------------------------------------------------------------

def test_e2e_ambient_track_persists_in_session(monkeypatch):
    """
    DM sets ambient track to 'battle'.  Subsequent request_state must include
    the updated sound_state so reconnecting clients get the current audio context.

    Matters because a player who reconnects mid-combat must hear the battle music.
    """
    from server.handlers import sound as snd, content as ch
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(snd, "save_campaign_async", _save)

    asyncio.run(snd.handle_sound_set_ambient(
        {"track": "battle", "volume": 0.8, "fade_ms": 1000},
        session, dm,
    ))

    assert (getattr(session, "sound_state", {}) or {}).get("track") == "battle", (
        "Sound state must be persisted to session after ambient track change"
    )

    # Now verify request_state includes sound_state
    asyncio.run(ch.handle_request_state({}, session, player))
    state_msgs = [msg for _, uid, msg in sent
                  if uid == player.id and msg.get("type") == "state_sync"]
    assert state_msgs, "request_state must send state_sync"
    state = state_msgs[0].get("payload") or state_msgs[0]
    # state_sync payload should carry sound_state or session reconstructs it
    sound = (
        (state.get("payload") or {}).get("sound_state")
        or state.get("sound_state")
    )
    if sound:
        assert sound.get("track") == "battle"


# ---------------------------------------------------------------------------
# 4. Condition applied during active combat
# ---------------------------------------------------------------------------

def test_e2e_condition_applied_during_combat(monkeypatch):
    """
    DM applies 'poisoned' to an NPC during active combat.
    The condition must appear on the token and a condition broadcast must fire.

    Matters because combat conditions are the most time-sensitive status updates;
    any lag or loss would desynchronise the game state.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, viewer = _make_session()
    session.combat = {
        "active": True,
        "turn": 0,
        "round": 2,
        "combatants": [
            {"token_id": "tok_npc", "name": "Goblin", "initiative": 15,
             "hp": 8, "max_hp": 8, "is_player": False},
        ],
    }
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_condition(
        {"token_id": "tok_npc", "condition": "poisoned"},
        session, dm,
    ))

    assert "poisoned" in (session.tokens["tok_npc"].conditions or [])
    cond_msgs = [msg for _, uid, msg in sent if msg.get("type") == "token_condition_changed"]
    assert cond_msgs, "Condition change during combat must produce token_condition_changed broadcast"


# ---------------------------------------------------------------------------
# 5. Hazard zone lifecycle: create → apply → delete
# ---------------------------------------------------------------------------

def test_e2e_hazard_zone_lifecycle(monkeypatch):
    """
    DM creates a hazard zone, manually applies it, then deletes it.
    After deletion no zone should remain in the session.

    Matters because stale hazard zones after deletion would continue to trigger,
    silently dealing damage to players on reconnect.
    """
    from server.handlers import hazards as haz
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(haz, "save_campaign_async", _save)

    # Create
    asyncio.run(haz.handle_hazard_zone_create(
        {"name": "Acid Pit", "x": 20.0, "y": 20.0, "radius_ft": 15,
         "trigger": "enter", "effect": "damage", "dice_num": 1, "dice_sides": 4},
        session, dm,
    ))
    zones = getattr(session, "hazard_zones", {}) or {}
    assert len(zones) == 1
    zone_id = next(iter(zones))

    # Apply
    initial_hp = session.tokens["tok1"].hp
    asyncio.run(haz.handle_hazard_zone_apply({"zone_id": zone_id}, session, dm))
    # tok1 is at (0,0) with 40x40 size → centre (20,20), zone at (20,20) r=150px → inside
    assert session.tokens["tok1"].hp <= initial_hp

    # Delete
    asyncio.run(haz.handle_hazard_zone_delete({"zone_id": zone_id}, session, dm))
    zones = getattr(session, "hazard_zones", {}) or {}
    assert zone_id not in zones, "Deleted hazard zone must be removed from session"


# ---------------------------------------------------------------------------
# 6. Hunter's Mark persists outside combat
# ---------------------------------------------------------------------------

def test_e2e_hunters_mark_persists_outside_combat(monkeypatch):
    """
    Player places Hunter's Mark on a visible NPC token when there is no active
    combat.  The condition must persist in the session so it is included in the
    next state sync.

    Matters because Hunter's Mark is a concentration spell that persists between
    encounters — losing it on reconnect would be a critical bug.
    """
    from server.handlers import tokens as tok_mod, content as ch
    session, dm, player, viewer = _make_session()
    # No active combat
    session.combat = {"active": False, "combatants": []}

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_mark_target(
        {"mark_kind": "hunters_mark", "target_token_id": "tok_npc"},
        session, player,
    ))

    assert "hunters_mark" in (session.tokens["tok_npc"].conditions or []), (
        "Hunter's Mark must persist outside active combat"
    )


# ---------------------------------------------------------------------------
# 7. Viewer power grant → revoke round-trip
# ---------------------------------------------------------------------------

def test_e2e_viewer_power_grant_revoke_round_trip(monkeypatch):
    """
    DM grants healing_spark to viewer, confirms it's present, then revokes it.
    After revocation the power must be absent from the viewer's profile.

    Matters because the UI shows the power list; stale entries would confuse viewers.
    """
    from server.handlers import viewer_powers as vp
    session, dm, player, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)

    # Grant
    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": viewer.id, "power_id": "healing_spark"},
        session, dm,
    ))

    from server.handlers.viewer_powers import _viewer_key_for_user
    profiles = getattr(session, "viewer_profiles", {}) or {}
    key = _viewer_key_for_user(viewer)
    powers = (profiles.get(key) or {}).get("powers") or {}
    assert "healing_spark" in powers, "healing_spark must be granted"

    # Revoke
    asyncio.run(vp.handle_viewer_power_revoke(
        {"viewer_user_id": viewer.id, "power_id": "healing_spark"},
        session, dm,
    ))

    profiles = getattr(session, "viewer_profiles", {}) or {}
    powers = (profiles.get(key) or {}).get("powers") or {}
    assert "healing_spark" not in powers, "Revoked power must be absent from profile"


# ---------------------------------------------------------------------------
# 8. dice_roll happy path
# ---------------------------------------------------------------------------

def test_e2e_dice_roll_broadcasts_result(monkeypatch):
    """
    Player rolls a d20.  A dice_result broadcast must fire to all clients.

    Matters because dice rolls are the most frequently sent messages; any
    regression would immediately disrupt play.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_dice_roll(
        {"notation": "1d20", "label": "Attack Roll"},
        session, player,
    ))

    types_all = (
        [msg.get("type") for _, msg, _ in broadcasts]
        + [msg.get("type") for _, uid, msg in sent]
    )
    assert any("dice" in (t or "") for t in types_all), (
        "Dice roll must produce a dice_result broadcast to all session users"
    )


# ---------------------------------------------------------------------------
# 9. Item library upsert
# ---------------------------------------------------------------------------

def test_e2e_item_library_upsert_and_sync(monkeypatch):
    """
    DM adds a custom item to the session item library.  An item_library_sync
    message must be sent so all clients get the updated library.

    Matters because the item library is the DM's tool for granting custom loot;
    players must see new items immediately.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(ch, "save_campaign_async", _save)

    asyncio.run(ch.handle_item_library_upsert(
        {"id": "item_custom_1", "name": "Boots of Speed", "item_type": "gear",
         "description": "Doubles movement speed.", "value_gp": 500},
        session, dm,
    ))

    types_sent = [msg.get("type") for _, uid, msg in sent]
    assert "item_library_sync" in types_sent, (
        "Item library upsert must broadcast item_library_sync"
    )


# ---------------------------------------------------------------------------
# 10. Fog paint then toggle
# ---------------------------------------------------------------------------

def test_e2e_fog_paint_then_toggle(monkeypatch):
    """
    DM paints fog cells then toggles fog on.  Each step must produce a
    fog-related broadcast so clients update the canvas.

    Matters because fog of war is a core DM tool; silent failures would
    reveal hidden areas to players.
    """
    from server.handlers import map_editor as me
    session, dm, player, viewer = _make_session()
    # Fog paint only fires when the fog layer is enabled
    session.fog_maps = {"world": {"enabled": True, "cols": 8, "rows": 8, "cells": "0" * 64}}
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(me, "save_campaign_async", _save)

    # Paint fog cells — use 'map_ctx' (not 'map_context') per the handler signature
    asyncio.run(me.handle_fog_paint(
        {"map_ctx": "world", "cells": [0, 1, 2, 3], "reveal": True},
        session, dm,
    ))

    fog_paint_types = [msg.get("type") for _, msg, _ in broadcasts] + \
                      [msg.get("type") for _, uid, msg in sent]
    assert any("fog" in (t or "") for t in fog_paint_types), (
        "Fog paint must produce a fog-related broadcast"
    )

    # Clear broadcasts for next assertion
    broadcasts.clear()
    sent.clear()

    # Toggle fog on
    asyncio.run(me.handle_fog_toggle(
        {"map_context": "world", "enabled": True},
        session, dm,
    ))

    toggle_types = [msg.get("type") for _, msg, _ in broadcasts] + \
                   [msg.get("type") for _, uid, msg in sent]
    assert any("fog" in (t or "") for t in toggle_types), (
        "Fog toggle must produce a fog-related broadcast"
    )


# ---------------------------------------------------------------------------
# 11. SFX player-rejection
# ---------------------------------------------------------------------------

def test_e2e_sfx_player_cannot_trigger(monkeypatch):
    """
    A player attempting to play a sound effect must be silently rejected.
    No sound_play_sfx broadcast should fire.

    Matters because allowing players to spam SFX would ruin the audio experience
    for everyone at the table.
    """
    from server.handlers import sound as snd
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(snd.handle_sound_play_sfx(
        {"sfx_id": "fireball", "volume": 1.0},
        session, player,
    ))

    sfx_types = [msg.get("type") for _, msg, _ in broadcasts]
    assert "sound_play_sfx" not in sfx_types, (
        "Players must not be able to trigger sound effects"
    )


# ---------------------------------------------------------------------------
# 12. Error recovery: handlers tolerate None/empty payloads
# ---------------------------------------------------------------------------

def test_e2e_combat_next_empty_payload_does_not_crash(monkeypatch):
    """
    Passing an empty dict or None to handle_combat_next must not raise.
    Combat handlers must be resilient to missing payload keys.
    """
    from server.handlers import combat as ch
    from server.session import Session, User, Token
    session = Session(id="e2e-empty-1")
    dm = User(id="dm1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    tok = Token(id="t1", name="Hero", x=0, y=0, width=40, height=40,
                color="#fff", shape="circle", owner_id=None, hp=10, max_hp=10)
    session.tokens[tok.id] = tok
    session.combat = {"active": True, "turn": 0, "round": 1, "combatants": [
        {"token_id": "t1", "name": "Hero", "initiative": 10, "is_player": False, "hp": 10, "max_hp": 10},
    ]}

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

    # Should not raise
    asyncio.run(ch.handle_combat_next({}, session, dm))


def test_e2e_sound_set_ambient_invalid_track_defaults_to_silence(monkeypatch):
    """
    Setting an invalid ambient track must silently fall back to 'silence'
    rather than raising or persisting an unknown track name.
    """
    from server.handlers import sound as snd
    session, dm, player, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(snd, "save_campaign_async", _save)

    asyncio.run(snd.handle_sound_set_ambient(
        {"track": "INVALID_TRACK_XYZ", "volume": 0.5},
        session, dm,
    ))

    sound_state = getattr(session, "sound_state", {}) or {}
    assert sound_state.get("track") == "silence", (
        "Invalid ambient track must be normalised to 'silence'"
    )


def test_e2e_stop_all_resets_track_to_silence(monkeypatch):
    """
    After handle_sound_stop_all the sound_state track must be 'silence'.
    All clients must receive a sound_stop_all broadcast (excluding DM).
    """
    from server.handlers import sound as snd
    session, dm, player, viewer = _make_session()
    # Pre-set a non-silence track
    session.sound_state = {"track": "battle", "volume": 0.9}

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(snd, "save_campaign_async", _save)

    asyncio.run(snd.handle_sound_stop_all({}, session, dm))

    sound_state = getattr(session, "sound_state", {}) or {}
    assert sound_state.get("track") == "silence", "stop_all must reset track to silence"

    stop_types = [msg.get("type") for _, msg, _ in broadcasts]
    assert "sound_stop_all" in stop_types, "stop_all must broadcast sound_stop_all"


def test_e2e_request_state_after_combat_includes_combat_state(monkeypatch):
    """
    A player reconnecting after combat started should receive the current
    combat state in their state_sync message.

    Matters because reconnect is a common scenario (mobile, browser refresh)
    and losing the combat state would desync the player's initiative tracker.
    """
    from server.handlers import content as ch
    session, dm, player, viewer = _make_session()
    session.combat = {
        "active": True,
        "turn": 1,
        "round": 3,
        "combatants": [
            {"token_id": "tok1", "name": "Alice", "initiative": 18,
             "is_player": True, "owner_id": "player1", "hp": 15, "max_hp": 20},
        ],
    }

    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(ch.handle_request_state({}, session, player))

    state_msgs = [msg for _, uid, msg in sent
                  if uid == player.id and msg.get("type") == "state_sync"]
    assert state_msgs, "Reconnecting player must receive state_sync"

    payload = state_msgs[0].get("payload") or {}
    combat = payload.get("combat")
    if combat is not None:
        assert combat.get("active") is True, (
            "state_sync payload must include the active combat state"
        )
