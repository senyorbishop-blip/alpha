import asyncio
import json
from types import SimpleNamespace

import server.sessions.service as sessions_service


def _decode_json_response(response):
    return json.loads((response.body or b"{}").decode("utf-8"))


def test_delete_session_token_allows_owned_token_when_multiple_users_share_player_key(monkeypatch):
    owner_user = SimpleNamespace(id="owner-user", role="player", player_key="auth_auth-1")
    viewer_user = SimpleNamespace(id="viewer-user", role="viewer", player_key="auth_auth-1")
    session = SimpleNamespace(
        users={"viewer-user": viewer_user, "owner-user": owner_user},
        tokens={"tok-1": SimpleNamespace(owner_id="owner-user")},
        corpse_states={},
    )
    saved = {"called": False}

    async def _fake_save(_session):
        saved["called"] = True

    monkeypatch.setattr(sessions_service, "get_request_user", lambda request: {"id": "auth-1"})
    monkeypatch.setattr(sessions_service, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(sessions_service, "resolve_session_authority", lambda request, session, fallback_user_id="": {"is_session_dm": False})
    monkeypatch.setattr(sessions_service, "save_campaign_async", _fake_save)

    response = asyncio.run(
        sessions_service.delete_session_token_response(SimpleNamespace(), "s1", "tok-1")
    )

    assert response.status_code == 200
    payload = _decode_json_response(response)
    assert payload["ok"] is True
    assert "tok-1" not in session.tokens
    assert saved["called"] is True


def test_delete_session_token_rejects_when_owner_player_key_does_not_match(monkeypatch):
    owner_user = SimpleNamespace(id="owner-user", role="player", player_key="auth_other")
    session = SimpleNamespace(
        users={"owner-user": owner_user},
        tokens={"tok-1": SimpleNamespace(owner_id="owner-user")},
        corpse_states={},
    )

    monkeypatch.setattr(sessions_service, "get_request_user", lambda request: {"id": "auth-1"})
    monkeypatch.setattr(sessions_service, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(sessions_service, "resolve_session_authority", lambda request, session, fallback_user_id="": {"is_session_dm": False})

    response = asyncio.run(
        sessions_service.delete_session_token_response(SimpleNamespace(), "s1", "tok-1")
    )

    assert response.status_code == 403
    payload = _decode_json_response(response)
    assert payload["error"] == "Forbidden"
