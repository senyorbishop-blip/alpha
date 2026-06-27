"""Regression coverage for the player-facing token staging bar.

The "Waiting to place" staging rail should appear for a player when (and only
when) they have a token waiting in staging, and should hide again once the token
is placed on the map. A player's first placement therefore routes through
staging: the token is created `staged=True`, shows in the player's own staging
rail, and is dragged onto the board from there.

These tests lock in:
  * server: a player may create their FIRST token as staged without tripping the
    single-active-token limit (the limit only counts *active*, non-staged tokens),
  * client: play.html routes a player's first placement through staging and keeps
    the DM dropping straight onto the board, and the staging rail visibility
    filter only shows a player their own tokens.
"""

from pathlib import Path

import pytest

from server.handlers import tokens as token_handlers
from server.session import Session, Token, User


PLAY_HTML = Path("client/templates/play.html")


def _play_html() -> str:
    return PLAY_HTML.read_text(encoding="utf-8")


@pytest.mark.anyio
async def test_player_first_token_can_be_created_staged(monkeypatch):
    session = Session(id="s-stage-first")
    player = User(id="p1", name="Player One", role="player")
    session.users[player.id] = player

    sent = []

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_token_state_sync", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(token_handlers, "run_combat_fog_sync", _noop)

    await token_handlers.handle_token_create(
        {
            "name": "Hero",
            "owner_id": player.id,
            "x": 100,
            "y": 100,
            "tokenType": "player",
            "map_context": "world",
            "staged": True,
        },
        session,
        player,
    )

    owned = [t for t in session.tokens.values() if t.owner_id == player.id]
    assert len(owned) == 1, "Player's first staged token should be created."
    assert owned[0].staged is True, "First placement should land in the staging tray."
    # Creating a staged token must NOT be rejected as a duplicate active token.
    assert sent == [], "Staged first placement should not be denied."


@pytest.mark.anyio
async def test_staged_token_does_not_count_against_active_limit(monkeypatch):
    """A waiting (staged) token still lets the player place an active one."""
    session = Session(id="s-stage-then-active")
    player = User(id="p1", name="Player One", role="player")
    session.users[player.id] = player
    session.tokens["tok-staged"] = Token(
        id="tok-staged",
        name="Waiting Hero",
        x=0,
        y=0,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=player.id,
        staged=True,
    )

    sent = []

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_token_state_sync", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(token_handlers, "run_combat_fog_sync", _noop)

    await token_handlers.handle_token_create(
        {
            "name": "Another Hero",
            "owner_id": player.id,
            "x": 120,
            "y": 120,
            "tokenType": "player",
            "map_context": "world",
            "staged": True,
        },
        session,
        player,
    )

    owned = [t for t in session.tokens.values() if t.owner_id == player.id]
    assert len(owned) == 2, "A second staged token is allowed alongside a waiting one."
    assert sent == [], "Staged creation should not be denied."


def test_player_first_placement_routes_through_staging():
    src = _play_html()
    # First placement is staged for players, direct for DMs.
    assert "const stageOnCreate = ROLE === 'player';" in src
    assert "if (stageOnCreate) payload.staged = true;" in src
    # Messaging tells the player the token is waiting in the tray.
    assert "waiting in the staging tray" in src


def test_player_staging_rail_only_shows_own_tokens():
    src = _play_html()
    # Players only ever see their own staged tokens in the rail.
    assert "return list.filter(t => _tokenOwnedByMe(t));" in src
    # The rail hides entirely when the player has nothing waiting to place.
    assert "if (visibleStaging.length === 0) {" in src
    assert "area.classList.remove('visible');" in src
