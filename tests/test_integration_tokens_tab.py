"""
tests/test_integration_tokens_tab.py — Integration tests for the token
management full user flow.

Covers:
- handle_token_create: DM creates NPC token; player creates own token; player
  blocked from creating for another player; viewer blocked
- handle_token_delete: DM deletes own NPC token; player cannot delete DM token;
  missing token is noop
- handle_token_hp_update: DM adjusts HP; broadcasts token_hp_update to all
- handle_toggle_hidden: DM hides a token; DM reveals a token; player cannot hide
- handle_token_emote: player emotes own token; player blocked on NPC token;
  viewer blocked; broadcasts token_emote

Why these tests matter:
Token operations are the most frequent real-time actions in a tabletop session.
Every create/delete/HP change/visibility toggle must broadcast immediately to all
clients.  Role guards prevent players from interfering with NPC tokens and viewers
from injecting any token actions.
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

def _make_session():
    from server.session import Session, User, Token
    session = Session(id="tok-integ-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    player2 = User(id="player2", name="Bob", role="player")
    viewer = User(id="viewer1", name="Watcher", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[player2.id] = player2
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    session.dm_map_context = "world"

    # DM NPC token
    npc = Token(id="tok_npc", name="Wolf", x=100, y=100, width=40, height=40,
                color="#888", shape="circle", owner_id=None, hp=12, max_hp=12)
    # Player-owned token
    hero = Token(id="tok_hero", name="Alice", x=0, y=0, width=40, height=40,
                 color="#f00", shape="circle", owner_id="player1", hp=20, max_hp=20)
    session.tokens[npc.id] = npc
    session.tokens[hero.id] = hero
    return session, dm, player, player2, viewer


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
# handle_token_create
# ---------------------------------------------------------------------------

def test_token_create_dm_creates_npc(monkeypatch):
    """
    DM can create an NPC token with no owner.  The token must appear in
    session.tokens and a token_created broadcast should fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_create(
        {"name": "Dragon", "x": 200, "y": 200, "width": 80, "height": 80,
         "color": "#800", "shape": "circle", "owner_id": None, "hp": 50, "max_hp": 50},
        session, dm,
    ))

    names = [t.name for t in session.tokens.values()]
    assert "Dragon" in names, "DM-created NPC token must be in session.tokens"

    all_types = (
        [msg.get("type") for _, msg, _ in broadcasts]
        + [msg.get("type") for _, uid, msg in sent]
    )
    assert any("token" in t for t in all_types), (
        "Token creation must produce at least one token-related broadcast"
    )


def test_token_create_player_creates_own_token(monkeypatch):
    """
    A player with no active token can create a token they own.
    """
    from server.handlers import tokens as tok_mod
    from server.session import Session, User
    # Use a fresh session so player2 has no existing token
    session = Session(id="tok-create-p2")
    dm = User(id="dm1", name="DM", role="dm")
    p2 = User(id="player2", name="Bob", role="player")
    session.users[dm.id] = dm
    session.users[p2.id] = p2
    session.dm_id = dm.id

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_create(
        {"name": "Bob", "x": 0, "y": 0, "width": 40, "height": 40,
         "color": "#0f0", "shape": "circle", "owner_id": "player2", "hp": 15, "max_hp": 15},
        session, p2,
    ))

    owners = [getattr(t, "owner_id", None) for t in session.tokens.values()]
    assert "player2" in owners, "Player must be able to create a token they own"


def test_token_create_player_blocked_for_other_player(monkeypatch):
    """
    A player must not be able to create a token owned by a different player.
    An error must be returned and no token stored.
    """
    from server.handlers import tokens as tok_mod
    from server.session import Session, User
    session = Session(id="tok-create-block")
    dm = User(id="dm1", name="DM", role="dm")
    p1 = User(id="player1", name="Alice", role="player")
    p2 = User(id="player2", name="Bob", role="player")
    session.users[dm.id] = dm
    session.users[p1.id] = p1
    session.users[p2.id] = p2
    session.dm_id = dm.id

    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_create(
        {"name": "Impersonated Bob", "x": 0, "y": 0, "width": 40, "height": 40,
         "color": "#00f", "shape": "circle", "owner_id": "player2", "hp": 10, "max_hp": 10},
        session, p1,
    ))

    owners = [getattr(t, "owner_id", None) for t in session.tokens.values()]
    assert "player2" not in owners, (
        "Player must not be able to create tokens owned by another player"
    )

    error_msgs = [msg for _, uid, msg in sent if uid == p1.id and msg.get("type") == "error"]
    assert error_msgs, "Blocked token creation must return an error to the requesting player"


def test_token_create_viewer_blocked(monkeypatch):
    """
    Viewers must not be able to create tokens.
    An error must be returned.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    initial_count = len(session.tokens)
    asyncio.run(tok_mod.handle_token_create(
        {"name": "Viewer Hack", "x": 0, "y": 0, "width": 40, "height": 40,
         "color": "#fff", "shape": "circle", "owner_id": None, "hp": 5, "max_hp": 5},
        session, viewer,
    ))

    assert len(session.tokens) == initial_count, "Viewers must not be able to create tokens"
    error_msgs = [msg for _, uid, msg in sent if uid == viewer.id and msg.get("type") == "error"]
    assert error_msgs, "Viewer must receive an error when attempting to create a token"


# ---------------------------------------------------------------------------
# handle_token_delete
# ---------------------------------------------------------------------------

def test_token_delete_dm_removes_npc_token(monkeypatch):
    """
    DM can delete any token including NPC tokens.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_delete({"token_id": "tok_npc"}, session, dm))

    assert "tok_npc" not in session.tokens, "DM must be able to delete NPC tokens"


def test_token_delete_player_cannot_delete_npc(monkeypatch):
    """
    A player must not be able to delete an NPC token (DM-owned).
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_token_delete({"token_id": "tok_npc"}, session, player))

    assert "tok_npc" in session.tokens, "Player must not be able to delete NPC tokens"


def test_token_delete_missing_token_is_noop(monkeypatch):
    """
    Deleting a non-existent token_id must not crash the handler.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    # Should not raise
    asyncio.run(tok_mod.handle_token_delete({"token_id": "GHOST"}, session, dm))


# ---------------------------------------------------------------------------
# handle_token_hp_update
# ---------------------------------------------------------------------------

def test_token_hp_update_broadcasts_to_all(monkeypatch):
    """
    HP update must broadcast char_hp_update to all connected users so
    health bars update in real time for every client.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(tok_mod.handle_char_hp_update(
        {"token_id": "tok_hero", "hp": 15, "max_hp": 20},
        session, dm,
    ))

    types_broadcast = [msg.get("type") for _, msg, _ in broadcasts]
    assert "char_hp_update" in types_broadcast, (
        "HP update must produce a char_hp_update broadcast to all clients"
    )


# ---------------------------------------------------------------------------
# handle_toggle_hidden
# ---------------------------------------------------------------------------

def test_toggle_hidden_dm_hides_token(monkeypatch):
    """
    DM can hide an NPC token.  The token's hidden flag must be set to True
    and a token visibility broadcast must fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_toggle_hidden({"token_id": "tok_npc"}, session, dm))

    assert session.tokens["tok_npc"].hidden is True, "DM must be able to hide a token"


def test_toggle_hidden_dm_reveals_token(monkeypatch):
    """
    DM can reveal a hidden token (toggle off).
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    session.tokens["tok_npc"].hidden = True
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_toggle_hidden({"token_id": "tok_npc"}, session, dm))

    assert session.tokens["tok_npc"].hidden is False, "DM must be able to reveal a hidden token"


def test_toggle_hidden_player_cannot_hide_token(monkeypatch):
    """
    Players must not be able to hide tokens (DM-only action).
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    async def _save(_):
        return True

    monkeypatch.setattr(tok_mod, "save_campaign_async", _save)

    asyncio.run(tok_mod.handle_toggle_hidden({"token_id": "tok_npc"}, session, player))

    assert not getattr(session.tokens["tok_npc"], "hidden", False), (
        "Player must not be able to hide tokens"
    )


# ---------------------------------------------------------------------------
# handle_token_emote
# ---------------------------------------------------------------------------

def test_token_emote_player_own_token(monkeypatch):
    """
    Player can emote with their own token.  A token_emote broadcast should fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(tok_mod.handle_token_emote(
        {"token_id": "tok_hero", "emote_id": "ready"},
        session, player,
    ))

    all_types = (
        [msg.get("type") for _, msg, _ in broadcasts]
        + [msg.get("type") for _, uid, msg in sent]
    )
    assert any("emote" in t for t in all_types), (
        "Player emote on own token must produce a token_emote broadcast"
    )


def test_token_emote_viewer_blocked(monkeypatch):
    """
    Viewers must not be able to emote.  No emote broadcast should fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(tok_mod.handle_token_emote(
        {"token_id": "tok_npc", "emote_id": "danger"},
        session, viewer,
    ))

    all_types = (
        [msg.get("type") for _, msg, _ in broadcasts]
        + [msg.get("type") for _, uid, msg in sent]
    )
    assert not any("emote" in t for t in all_types), (
        "Viewers must not be able to emit token emotes"
    )


def test_token_emote_player_blocked_on_npc(monkeypatch):
    """
    Player must not be able to emote with an NPC token they don't own.
    No emote broadcast should fire.
    """
    from server.handlers import tokens as tok_mod
    session, dm, player, player2, viewer = _make_session()
    broadcasts, sent = _patch_manager(monkeypatch)

    asyncio.run(tok_mod.handle_token_emote(
        {"token_id": "tok_npc", "emote_id": "laugh"},
        session, player,
    ))

    emote_broadcasts = [
        msg for _, msg, _ in broadcasts if msg.get("type") == "token_emote"
    ]
    assert len(emote_broadcasts) == 0, (
        "Player must not be able to emote with NPC tokens they don't own"
    )
