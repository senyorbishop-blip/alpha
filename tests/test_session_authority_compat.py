from types import SimpleNamespace

from server.http import session_access
from server.session import Session, User


def test_resolve_session_authority_does_not_promote_dm_from_name_match(monkeypatch):
    session = Session(id="s-auth")
    dm = User(id="legacy-dm-id", name="DungeonMaster", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "auth-user-123", "username": "DungeonMaster"},
    )

    authority = session_access.resolve_session_authority(request, session, fallback_user_id="")

    assert authority["is_session_dm"] is False
    assert authority["participant_role"] is None
    assert authority["resolved_session_user_id"] is None
    assert authority["matched_via"] == "none"
    assert authority["resolved_user_id"] == "auth-user-123"


def test_resolve_session_authority_keeps_session_user_match_priority(monkeypatch):
    session = Session(id="s-auth-priority")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="auth-user-123", name="Different", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "auth-user-123", "username": "DM"},
    )

    authority = session_access.resolve_session_authority(request, session, fallback_user_id="")

    assert authority["resolved_session_user_id"] == player.id
    assert authority["participant_role"] == "player"
    assert authority["is_session_dm"] is False
    assert authority["matched_via"] == "session_user"


def test_resolve_session_authority_prefers_fallback_session_user_id_over_auth_id(monkeypatch):
    session = Session(id="s-auth-fallback")
    dm = User(id="dm-1", name="DungeonMaster", role="dm")
    player = User(id="session-player-id", name="Player One", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "auth-user-123", "username": "DungeonMaster"},
    )

    authority = session_access.resolve_session_authority(
        request,
        session,
        fallback_user_id=player.id,
    )

    assert authority["resolved_session_user_id"] == player.id
    assert authority["resolved_user_id"] == player.id
    assert authority["participant_role"] == "player"
    assert authority["is_session_dm"] is False
    assert authority["matched_via"] == "session_user"
