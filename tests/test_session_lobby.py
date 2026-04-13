import json

from server.session import Session, User, Token
from server.sessions import service as session_service


class FakeRequest:
    def __init__(self, user=None):
        self.state = type("State", (), {"user": user})()
        self.cookies = {}
        self.headers = {}


def _response_json(resp):
    return json.loads(resp.body.decode("utf-8"))


def _build_session():
    session = Session(id="ABCD")
    dm = User(id="dm1", name="DM", role="dm")
    alice = User(id="u1", name="Alice", role="player")
    bob = User(id="u2", name="Bob", role="player")
    alice.player_key = "auth_a1"
    bob.player_key = "auth_b1"
    session.dm_id = dm.id
    session.users = {dm.id: dm, alice.id: alice, bob.id: bob}
    session.tokens = {
        "t1": Token(id="t1", name="Alice Token", x=0, y=0, width=40, height=40, color="#fff", shape="circle", owner_id=alice.id),
        "t2": Token(id="t2", name="Bob Token", x=0, y=0, width=40, height=40, color="#0ff", shape="circle", owner_id=bob.id),
    }
    return session


def test_lobby_player_only_gets_owned_tokens(monkeypatch):
    session = _build_session()
    monkeypatch.setattr(session_service, "get_or_restore_session", lambda _sid: session)
    monkeypatch.setattr(session_service, "get_request_user", lambda _req: {"id": "a1", "display_name": "Alice"})

    resp = session_service.lobby_response(FakeRequest({"id": "a1"}), session.id, role="player")
    data = _response_json(resp)

    assert [tok["id"] for tok in data["tokens"]] == ["t1"]


def test_lobby_player_with_no_match_gets_no_tokens(monkeypatch):
    session = _build_session()
    monkeypatch.setattr(session_service, "get_or_restore_session", lambda _sid: session)
    monkeypatch.setattr(session_service, "get_request_user", lambda _req: {"id": "nobody", "display_name": "Unknown"})

    resp = session_service.lobby_response(FakeRequest({"id": "nobody"}), session.id, role="player")
    data = _response_json(resp)

    assert data["tokens"] == []


def test_lobby_dm_role_requires_dm_authority(monkeypatch):
    session = _build_session()
    monkeypatch.setattr(session_service, "get_or_restore_session", lambda _sid: session)
    monkeypatch.setattr(session_service, "get_request_user", lambda _req: {"id": "a1", "display_name": "Alice"})

    resp = session_service.lobby_response(FakeRequest({"id": "a1"}), session.id, role="dm")
    data = _response_json(resp)

    assert data["tokens"] == []
