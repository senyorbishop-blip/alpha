import asyncio


def _patch_broadcast(monkeypatch):
    import server.handlers.common as common_mod
    sent = []

    async def _broadcast(session_id, message, exclude_user=None):
        sent.append((session_id, message, exclude_user))

    monkeypatch.setattr(common_mod.manager, "broadcast", _broadcast)
    return sent


def test_handle_ping_map_blocks_player_when_map_setting_disallows(monkeypatch):
    from server.handlers.map_editor import handle_ping_map
    from server.session import Session, User

    session = Session(id="ping-perm-1")
    player = User(id="p1", name="Player", role="player")
    session.users[player.id] = player
    session.map_settings = {"world": {"world": {"allow_player_ping": False}}}

    sent = _patch_broadcast(monkeypatch)
    asyncio.run(handle_ping_map({"x": 100, "y": 120, "map_context": "world"}, session, player))
    assert sent == []


def test_handle_ping_map_allows_dm_and_relays_mode(monkeypatch):
    from server.handlers.map_editor import handle_ping_map
    from server.session import Session, User

    session = Session(id="ping-perm-2")
    dm = User(id="dm1", name="DM", role="dm")
    session.users[dm.id] = dm

    sent = _patch_broadcast(monkeypatch)
    asyncio.run(handle_ping_map({"x": 10, "y": 20, "mode": "point", "map_context": "world"}, session, dm))

    assert len(sent) == 1
    _, message, excluded = sent[0]
    assert excluded == dm.id
    assert message["type"] == "map_ping"
    assert message["payload"]["mode"] == "point"
