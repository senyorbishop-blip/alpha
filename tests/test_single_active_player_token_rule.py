import pytest
from pathlib import Path

from server.handlers import combat as combat_handlers
from server.handlers import tokens as token_handlers
from server.restore import restore_session_from_db
from server.session import Session, Token, User


def _restore_payload_with_player_tokens(tokens: list[dict], combatants: list[dict] | None = None) -> dict:
    return {
        "id": "RESTORE-TOKEN-RULE",
        "name": "Token Rule Campaign",
        "dm_name": "Dungeon Master",
        "player_invite": "PLAYTOKEN",
        "viewer_invite": "VIEWTOKEN",
        "created_at": 1.0,
        "updated_at": 1.0,
        "map_image_url": "/static/maps/world.png",
        "dm_id": "dm-1",
        "tokens": tokens,
        "logs": [],
        "players": [{"id": "p1", "name": "Player One", "role": "player"}],
        "pois": [],
        "combat": {
            "active": True,
            "turn": 0,
            "round": 1,
            "combatants": list(combatants or []),
        },
    }


@pytest.mark.anyio
async def test_player_claims_first_token_successfully(monkeypatch):
    session = Session(id="s-token-create-ok")
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

    await token_handlers.handle_token_create(
        {
            "name": "Hero",
            "owner_id": player.id,
            "x": 100,
            "y": 100,
            "tokenType": "player",
            "map_context": "world",
        },
        session,
        player,
    )

    created = [t for t in session.tokens.values() if t.owner_id == player.id and not t.staged]
    assert len(created) == 1
    assert sent == []


@pytest.mark.anyio
async def test_player_blocked_from_creating_second_active_owned_token(monkeypatch):
    session = Session(id="s-token-create-blocked")
    player = User(id="p1", name="Player One", role="player")
    session.users[player.id] = player
    session.tokens["tok-existing"] = Token(
        id="tok-existing",
        name="Existing Hero",
        x=0,
        y=0,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=player.id,
        staged=False,
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

    await token_handlers.handle_token_create(
        {"name": "Second Hero", "owner_id": player.id, "x": 120, "y": 120, "tokenType": "player"},
        session,
        player,
    )

    assert len([t for t in session.tokens.values() if t.owner_id == player.id and not t.staged]) == 1
    assert sent, "Player should receive a rejection message."
    assert "one active token" in str(sent[-1][0][2]["payload"]["message"]).lower()


@pytest.mark.anyio
async def test_player_blocked_from_placing_second_active_owned_token(monkeypatch):
    session = Session(id="s-token-place-blocked")
    player = User(id="p1", name="Player One", role="player")
    session.users[player.id] = player
    session.tokens["tok-active"] = Token(
        id="tok-active",
        name="Active Hero",
        x=100,
        y=100,
        width=40,
        height=40,
        color="#fff",
        shape="circle",
        owner_id=player.id,
        staged=False,
    )
    session.tokens["tok-staged"] = Token(
        id="tok-staged",
        name="Backup Hero",
        x=200,
        y=200,
        width=40,
        height=40,
        color="#0ff",
        shape="circle",
        owner_id=player.id,
        staged=True,
    )

    sent = []
    broadcast = []

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    async def _broadcast(*args, **kwargs):
        broadcast.append((args, kwargs))

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(token_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(token_handlers, "_broadcast_token_state_sync", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)

    await token_handlers.handle_token_placed(
        {"token_id": "tok-staged", "x": 260, "y": 260, "map_context": "world"},
        session,
        player,
    )

    assert session.tokens["tok-staged"].staged is True
    assert sent, "Player should receive a rejection message."
    assert "one active token" in str(sent[-1][0][2]["payload"]["message"]).lower()
    assert broadcast == []


@pytest.mark.anyio
async def test_dm_can_still_control_multiple_dm_tokens(monkeypatch):
    session = Session(id="s-token-dm-ok")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_broadcast_token_state_sync", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)

    await token_handlers.handle_token_create({"name": "Goblin", "x": 50, "y": 50, "tokenType": "monster"}, session, dm)
    await token_handlers.handle_token_create({"name": "Orc", "x": 90, "y": 90, "tokenType": "monster"}, session, dm)

    dm_tokens = [t for t in session.tokens.values() if not t.owner_id]
    assert len(dm_tokens) == 2


def test_legacy_duplicate_active_player_tokens_resolve_safely_on_restore():
    payload = _restore_payload_with_player_tokens(
        [
            {"id": "tok-a", "name": "Hero A", "x": 0, "y": 0, "width": 40, "height": 40, "color": "#fff", "shape": "circle", "owner_id": "p1", "staged": False},
            {"id": "tok-b", "name": "Hero B", "x": 50, "y": 50, "width": 40, "height": 40, "color": "#0ff", "shape": "circle", "owner_id": "p1", "staged": False},
        ],
        combatants=[
            {"id": "c-a", "token_id": "tok-a", "owner_id": "p1", "initiative": 15},
            {"id": "c-b", "token_id": "tok-b", "owner_id": "p1", "initiative": 12},
        ],
    )

    session, _ = restore_session_from_db(payload)

    active_owned = [t.id for t in session.tokens.values() if t.owner_id == "p1" and not t.staged]
    assert len(active_owned) == 1
    combat_token_ids = [str((c or {}).get("token_id") or "") for c in (session.combat.get("combatants") or [])]
    assert active_owned[0] in combat_token_ids
    assert len([tid for tid in combat_token_ids if tid in {"tok-a", "tok-b"}]) == 1


def test_reconnect_state_sync_does_not_surface_two_active_owned_tokens():
    payload = _restore_payload_with_player_tokens(
        [
            {"id": "tok-a", "name": "Hero A", "x": 0, "y": 0, "width": 40, "height": 40, "color": "#fff", "shape": "circle", "owner_id": "p1", "staged": False},
            {"id": "tok-b", "name": "Hero B", "x": 50, "y": 50, "width": 40, "height": 40, "color": "#0ff", "shape": "circle", "owner_id": "p1", "staged": False},
        ],
    )
    session, _ = restore_session_from_db(payload)

    state = session.to_state_dict_for_role("player", "p1")
    player_tokens = list((state.get("tokens") or {}).values())
    active_owned = [t for t in player_tokens if str(t.get("owner_id") or "") == "p1" and not bool(t.get("staged"))]
    assert len(active_owned) == 1


@pytest.mark.anyio
async def test_combat_turn_flow_still_works_after_duplicate_cleanup(monkeypatch):
    from server.handlers import hazards as hazard_handlers

    payload = _restore_payload_with_player_tokens(
        [
            {"id": "tok-a", "name": "Hero A", "x": 0, "y": 0, "width": 40, "height": 40, "color": "#fff", "shape": "circle", "owner_id": "p1", "staged": False, "speed": 30},
            {"id": "tok-b", "name": "Hero B", "x": 50, "y": 50, "width": 40, "height": 40, "color": "#0ff", "shape": "circle", "owner_id": "p1", "staged": False, "speed": 30},
        ],
        combatants=[
            {"id": "c-a", "token_id": "tok-a", "owner_id": "p1", "initiative": 15, "speed": 30},
            {"id": "c-b", "token_id": "tok-b", "owner_id": "p1", "initiative": 12, "speed": 30},
        ],
    )
    session, _ = restore_session_from_db(payload)
    dm = session.users["dm-1"]

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(combat_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _noop)
    monkeypatch.setattr(hazard_handlers, "_process_current_end_turn_hazards", _noop)
    monkeypatch.setattr(hazard_handlers, "_process_current_start_turn_hazards", _noop)
    monkeypatch.setattr(hazard_handlers, "_process_end_round_hazards", _noop)

    await combat_handlers.handle_combat_next({}, session, dm)

    assert session.combat.get("active") is True
    assert len(session.combat.get("combatants") or []) == 1
    assert int(session.combat.get("turn", -1)) == 0


def test_play_page_can_reposition_off_map_owned_token_instead_of_duplicate_create():
    src = Path("client/templates/play.html").read_text(encoding="utf-8")

    assert "function findOwnedOffMapActiveTokenForPlacement()" in src
    assert "placeExistingOwnedTokenOnCurrentMap(offMapOwnedToken, center, name)" in src
    assert "sendWS({ type: 'token_placed', payload });" in src


def test_play_page_normalizes_token_size_when_grid_changes():
    src = Path("client/templates/play.html").read_text(encoding="utf-8")

    assert "function normalizeTokenSizeForCurrentGrid(token)" in src
    assert "normalizeAllTokenSizesForCurrentGrid();" in src
    assert "normalizeTokenSizeForCurrentGrid(tok);" in src
