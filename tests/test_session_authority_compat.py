from types import SimpleNamespace

from server.http import session_access
from server.session import Session, User


def test_resolve_session_authority_matches_dm_by_name_fallback(monkeypatch):
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

    assert authority["is_session_dm"] is True
    assert authority["participant_role"] == "dm"
    assert authority["resolved_session_user_id"] == dm.id
    assert authority["matched_via"] == "dm_name"


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
