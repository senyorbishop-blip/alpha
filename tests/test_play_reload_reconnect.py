"""Regression tests for plain /play reload reconnect.

Symptom being guarded against: a returning, already-authenticated session member
reloads /play but the page bounces them through /join -> character picker ->
POST /api/session/join instead of connecting the WebSocket directly. The two
root causes covered here:

  1. The player's selected character profile (``active_char_profiles``) was never
     persisted to the DB, so a server restart dropped it.
  2. /play did not self-bootstrap a returning member when the URL identity was
     stale/missing, so the WebSocket handshake could not match a session user.

These tests round-trip a real join through ``save_campaign``/``load_campaign``/
``restore_session_from_db`` and exercise ``_reconnect_redirect_for_member``.
"""
import os
import tempfile
from urllib.parse import parse_qsl, urlparse, parse_qs

import pytest


@pytest.fixture()
def fresh_db(monkeypatch):
    """Point the DB/data dir at a throwaway location and init the schema."""
    monkeypatch.setenv("DND_DB_PATH", tempfile.mktemp(suffix=".db"))
    monkeypatch.setenv("DND_DATA_DIR", tempfile.mkdtemp())
    # paths.py reads the env vars at import time, so reload it (and db) under the patch.
    import importlib
    import server.paths as paths
    importlib.reload(paths)
    import server.db as db
    importlib.reload(db)
    db.init_db()
    return db


class _FakeRequest:
    def __init__(self, query_string: str, token: str | None = None):
        self.query_params = dict(parse_qsl(query_string))
        self.cookies = {"dnd_session": token} if token else {}
        self.headers = {}


def _join_player(db, auth_user_id="u-123", name="Bishop", profile_id="pdf-bishop"):
    from server.session import create_session, join_session
    from server.http.auth import auth_player_key

    session, _dm = create_session("DM Bob")
    pkey = auth_player_key(auth_user_id)
    _s, player, err = join_session(session.id, session.player_invite, name, pkey)
    assert not err, err
    # Player selects a character — mirrors _sync_player_state_from_profile.
    session.active_char_profiles = {player.id: profile_id}
    db.save_campaign(session)
    return session.id, player.id, pkey


def test_active_char_profiles_survive_restart(fresh_db):
    db = fresh_db
    sid, player_uid, pkey = _join_player(db)

    # Simulate a server restart: forget in-memory state and reload from DB.
    from server.session import _sessions
    from server.restore import restore_session_from_db

    _sessions.clear()
    data = db.load_campaign(sid)
    assert data is not None
    assert data.get("active_char_profiles", {}).get(player_uid) == "pdf-bishop"

    restored, _dm_id = restore_session_from_db(data)
    assert player_uid in restored.users
    assert restored.users[player_uid].player_key == pkey
    assert restored.active_char_profiles.get(player_uid) == "pdf-bishop"


def _authed_token(monkeypatch, auth_user_id="u-123"):
    import server.http.auth as http_auth
    from server.auth.jwt_utils import create_token

    monkeypatch.setattr(
        http_auth,
        "get_user_by_id",
        lambda uid: ({"id": uid, "username": "bishop", "role": "player"} if uid == auth_user_id else None),
    )
    return create_token(auth_user_id, "bishop", "player")


def _ctx_for(req):
    from server.pages.routes import _play_boot_context

    ctx = {"request": req}
    ctx.update(_play_boot_context(req))
    return ctx


def test_play_redirect_resolves_stale_identity(fresh_db, monkeypatch):
    db = fresh_db
    sid, player_uid, _pkey = _join_player(db)
    from server.session import _sessions

    _sessions.clear()  # restart — session must restore from DB
    token = _authed_token(monkeypatch)

    from server.pages.routes import _reconnect_redirect_for_member

    # Stale link with no user_id: should redirect to the resolved member identity.
    req = _FakeRequest(f"session_id={sid}&role=player", token=token)
    resp = _reconnect_redirect_for_member(req, _ctx_for(req))
    assert resp is not None
    loc = urlparse(resp.headers["location"])
    q = parse_qs(loc.query)
    assert loc.path == "/play"
    assert q["user_id"] == [player_uid]
    assert q["role"] == ["player"]
    assert q["returning"] == ["1"]
    assert q["name"] == ["Bishop"]


def test_play_no_redirect_when_identity_correct(fresh_db, monkeypatch):
    db = fresh_db
    sid, player_uid, _pkey = _join_player(db)
    from server.session import _sessions

    _sessions.clear()
    token = _authed_token(monkeypatch)

    from server.pages.routes import _reconnect_redirect_for_member

    req = _FakeRequest(
        f"session_id={sid}&user_id={player_uid}&role=player&name=Bishop", token=token
    )
    # Correct identity already in the URL — render directly so the client connects WS.
    assert _reconnect_redirect_for_member(req, _ctx_for(req)) is None


def test_play_no_redirect_for_unauthenticated_or_missing_session(fresh_db):
    db = fresh_db
    sid, _player_uid, _pkey = _join_player(db)
    from server.session import _sessions

    _sessions.clear()

    from server.pages.routes import _reconnect_redirect_for_member

    # No auth cookie -> stranger -> normal (unchanged) join flow.
    req = _FakeRequest(f"session_id={sid}&role=player", token=None)
    assert _reconnect_redirect_for_member(req, _ctx_for(req)) is None

    # No session_id -> nothing to resolve.
    req = _FakeRequest("role=player", token=None)
    assert _reconnect_redirect_for_member(req, _ctx_for(req)) is None
