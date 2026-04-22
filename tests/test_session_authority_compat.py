import asyncio
import json
from types import SimpleNamespace

from server.http import session_access
from server.session import Session, User
from server.sessions import service as sessions_service


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
    player.player_key = "auth_auth-user-123"
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


def test_resolve_session_authority_rejects_untrusted_fallback_dm_when_auth_present(monkeypatch):
    session = Session(id="s-auth-restrict")
    dm = User(id="dm-1", name="DungeonMaster", role="dm")
    player = User(id="player-1", name="Player", role="player")
    player.player_key = "auth_auth-user-123"
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "auth-user-123", "username": "Player"},
    )

    authority = session_access.resolve_session_authority(
        request,
        session,
        fallback_user_id=dm.id,
    )

    # Fallback to the DM slot is correctly rejected because the auth user's
    # player_key matches a different (player) session participant, not the DM.
    assert authority["fallback_allowed"] is False
    assert authority["fallback_allowed_via"] == "none"
    assert authority["is_session_dm"] is False
    # Auth user IS correctly identified as a player via player_key lookup
    assert authority["participant_role"] == "player"
    assert authority["matched_via"] == "player_key"
    assert authority["resolved_session_user_id"] == player.id


def test_resolve_session_authority_allows_fallback_when_linked_by_auth_player_key(monkeypatch):
    session = Session(id="s-auth-player-key")
    player = User(id="session-player-id", name="Player", role="player")
    player.player_key = "auth_auth-user-123"
    session.users[player.id] = player

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "auth-user-123", "username": "Player"},
    )

    authority = session_access.resolve_session_authority(
        request,
        session,
        fallback_user_id=player.id,
    )

    assert authority["fallback_allowed"] is True
    assert authority["fallback_allowed_via"] == "auth_player_key_match"
    assert authority["resolved_session_user_id"] == player.id
    assert authority["participant_role"] == "player"
    assert authority["is_session_dm"] is False


def test_resolve_session_authority_matches_dm_via_player_key(monkeypatch):
    """Auth DM is found via player_key lookup even when no fallback_user_id is given."""
    session = Session(id="s-dm-pk")
    dm = User(id="internal-dm-id", name="DM", role="dm")
    dm.player_key = "auth_auth-dm-456"
    session.users[dm.id] = dm
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "auth-dm-456", "username": "DM"},
    )

    authority = session_access.resolve_session_authority(request, session, fallback_user_id="")

    assert authority["is_session_dm"] is True
    assert authority["participant_role"] == "dm"
    assert authority["matched_via"] == "player_key"
    assert authority["resolved_session_user_id"] == dm.id


def test_backfill_dm_player_key_grants_access_for_legacy_session(monkeypatch):
    """DM with no player_key (legacy session) gets backfilled on first auth check."""
    from server.sessions.service import _backfill_dm_player_key_if_needed

    session = Session(id="s-legacy")
    dm = User(id="legacy-dm-id", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        "server.sessions.service.get_request_user",
        lambda _req: {"id": "returning-dm-auth", "username": "DM"},
    )

    backfilled = _backfill_dm_player_key_if_needed(request, session, fallback_user_id="legacy-dm-id")

    assert backfilled is True
    assert dm.player_key == "auth_returning-dm-auth"

    # After backfill, resolve_session_authority should now grant DM access
    monkeypatch.setattr(
        session_access,
        "get_request_user",
        lambda _req: {"id": "returning-dm-auth", "username": "DM"},
    )
    authority = session_access.resolve_session_authority(
        request, session, fallback_user_id="legacy-dm-id"
    )
    assert authority["is_session_dm"] is True
    assert authority["participant_role"] == "dm"


def test_backfill_dm_player_key_blocked_when_key_already_used_by_player(monkeypatch):
    """Backfill is rejected when the auth user's key belongs to another session participant."""
    from server.sessions.service import _backfill_dm_player_key_if_needed

    session = Session(id="s-blocked-backfill")
    dm = User(id="dm-id", name="DM", role="dm")
    player = User(id="player-id", name="Player", role="player")
    player.player_key = "auth_attacker-auth"
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.dm_id = dm.id

    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(
        "server.sessions.service.get_request_user",
        lambda _req: {"id": "attacker-auth", "username": "Attacker"},
    )

    backfilled = _backfill_dm_player_key_if_needed(request, session, fallback_user_id="dm-id")

    assert backfilled is False
    assert not getattr(dm, "player_key", None)


def test_session_authority_response_forces_dm_resolved_role_when_authoritative(monkeypatch):
    session = Session(id="s-role-force")
    dm = User(id="dm-1", name="DM", role="dm")
    session.users[dm.id] = dm
    session.dm_id = dm.id
    request = SimpleNamespace(cookies={}, headers={})

    monkeypatch.setattr(sessions_service, "get_or_restore_session", lambda _sid: session)
    monkeypatch.setattr(sessions_service, "_backfill_dm_player_key_if_needed", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        sessions_service,
        "resolve_session_authority",
        lambda *_args, **_kwargs: {
            "resolved_user_id": "dm-1",
            "resolved_session_user_id": "dm-1",
            "session_dm_id": "dm-1",
            "participant_role": "player",
            "is_session_dm": True,
            "matched_via": "session_user",
        },
    )

    response = asyncio.run(
        sessions_service.session_authority_response(request, "s-role-force", fallback_user_id="dm-1")
    )
    body = json.loads(response.body.decode("utf-8"))
    assert body["is_session_dm"] is True
    assert body["participant_role"] == "player"
    assert body["resolved_role"] == "dm"
