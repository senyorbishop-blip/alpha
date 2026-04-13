import os

from server.connections import ConnectionManager


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


class _FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.close_calls = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=""):
        self.closed = True
        self.close_calls.append((code, reason))

    async def send_text(self, _payload):
        return None


async def _connect(manager, session_id, user_id, socket):
    await manager.connect(session_id, user_id, socket)


def test_connection_manager_replaces_prior_socket_for_same_user():
    import asyncio

    manager = ConnectionManager()
    old_socket = _FakeWebSocket()
    new_socket = _FakeWebSocket()

    asyncio.run(_connect(manager, "sess-1", "user-1", old_socket))
    asyncio.run(_connect(manager, "sess-1", "user-1", new_socket))

    assert old_socket.closed, "Old socket must be closed when a newer socket replaces it"
    assert manager.get_session_connections("sess-1").get("user-1") is new_socket


def test_connection_manager_ignores_stale_disconnect_for_replaced_socket():
    import asyncio

    manager = ConnectionManager()
    old_socket = _FakeWebSocket()
    new_socket = _FakeWebSocket()

    asyncio.run(_connect(manager, "sess-2", "user-2", old_socket))
    asyncio.run(_connect(manager, "sess-2", "user-2", new_socket))

    removed = manager.disconnect("sess-2", "user-2", old_socket)
    assert not removed, "Disconnect from stale socket must not evict the active socket"
    assert manager.get_session_connections("sess-2").get("user-2") is new_socket


def test_ws_core_installs_lifecycle_and_stale_socket_guards():
    ws_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "core", "ws.js")
    with open(ws_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "global.addEventListener('beforeunload', stopSocketLifecycle);" in src
    assert "global.addEventListener('pagehide', stopSocketLifecycle);" in src
    assert "if (config.getSocket() !== socket) return;" in src
    assert "if (config.getReconnectTimer()) return;" in src
