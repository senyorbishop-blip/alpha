import json

import pytest
from starlette.websockets import WebSocketDisconnect


class FakeWebSocket:
    def __init__(self):
        self.headers = {}
        self.accepted = False
        self.closed = None
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=None):
        self.closed = {"code": code, "reason": reason}

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def receive_text(self):
        raise WebSocketDisconnect()


@pytest.fixture(autouse=True)
def _clean_ws_state(monkeypatch):
    from server.connections import manager
    from server.session import _sessions

    monkeypatch.delenv("DND_JWT_SECRET", raising=False)
    _sessions.clear()
    manager._connections.clear()
    manager._connection_ids.clear()
    yield
    _sessions.clear()
    manager._connections.clear()
    manager._connection_ids.clear()


def _session_with_roles(session_id="ws-auth-test"):
    from server.session import Session, User, _sessions

    session = Session(id=session_id, dm_id="real-dm-id")
    session.users = {
        "real-dm-id": User(id="real-dm-id", name="DM", role="dm"),
        "real-player-id": User(id="real-player-id", name="Player", role="player"),
        "real-viewer-id": User(id="real-viewer-id", name="Viewer", role="viewer"),
    }
    _sessions[session.id] = session
    return session


@pytest.mark.anyio
@pytest.mark.parametrize("user_id", ["real-dm-id", "real-player-id"])
async def test_enforced_auth_rejects_dm_and_player_without_token(monkeypatch, user_id):
    from main import websocket_endpoint

    session = _session_with_roles()
    monkeypatch.setenv("DND_JWT_SECRET", "test-secret")
    ws = FakeWebSocket()

    await websocket_endpoint(ws, session.id, user_id)

    assert ws.closed == {"code": 4001, "reason": "Missing or invalid token"}
    assert not ws.accepted


@pytest.mark.anyio
async def test_enforced_auth_allows_viewer_without_token(monkeypatch):
    from main import websocket_endpoint

    session = _session_with_roles()
    monkeypatch.setenv("DND_JWT_SECRET", "test-secret")
    ws = FakeWebSocket()

    await websocket_endpoint(ws, session.id, "real-viewer-id")

    assert ws.accepted
    assert ws.closed is None
    assert any(message.get("type") == "state_sync" for message in ws.sent)


@pytest.mark.anyio
@pytest.mark.parametrize("user_id", ["real-dm-id", "real-player-id", "real-viewer-id"])
async def test_no_auth_secret_allows_all_roles_without_token(user_id):
    from main import websocket_endpoint

    session = _session_with_roles()
    ws = FakeWebSocket()

    await websocket_endpoint(ws, session.id, user_id)

    assert ws.accepted
    assert ws.closed is None
    assert any(message.get("type") == "state_sync" for message in ws.sent)


@pytest.mark.anyio
async def test_user_joined_payload_to_viewer_omits_real_user_ids():
    from main import websocket_endpoint
    from server.connections import manager

    session = _session_with_roles()
    viewer_ws = FakeWebSocket()
    await manager.connect(session.id, "real-viewer-id", viewer_ws, role="viewer")

    player_ws = FakeWebSocket()
    await websocket_endpoint(player_ws, session.id, "real-player-id")

    joined = [message for message in viewer_ws.sent if message.get("type") == "user_joined"]
    assert joined, "viewer should receive user_joined when another user connects"
    payload_values = json.dumps(joined[-1].get("payload", {}))
    for real_user_id in session.users:
        assert real_user_id not in payload_values
    user_payload = joined[-1]["payload"]["user"]
    assert "id" not in user_payload
    assert user_payload["handle"].startswith("user_")
    assert user_payload["name"] == "Player"
    assert user_payload["role"] == "player"
    assert user_payload["subgroup_id"] == "main"
