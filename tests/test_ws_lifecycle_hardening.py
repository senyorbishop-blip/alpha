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


def test_connection_manager_tracks_current_connection_id_for_reconnects():
    import asyncio

    manager = ConnectionManager()
    old_socket = _FakeWebSocket()
    new_socket = _FakeWebSocket()

    old_id = asyncio.run(manager.connect("sess-3", "user-3", old_socket, connection_id="socket-a"))
    new_id = asyncio.run(manager.connect("sess-3", "user-3", new_socket, connection_id="socket-b"))

    assert old_id == "socket-a"
    assert new_id == "socket-b"
    assert not manager.is_current_connection("sess-3", "user-3", old_id)
    assert manager.is_current_connection("sess-3", "user-3", new_id)
    assert manager.get_socket("sess-3", "user-3") is new_socket


def test_stale_heartbeat_exits_without_closing_new_socket():
    import asyncio
    from main import _websocket_heartbeat_loop

    async def run_case():
        manager = ConnectionManager()
        old_socket = _FakeWebSocket()
        new_socket = _FakeWebSocket()
        old_id = await manager.connect("sess-4", "user-4", old_socket, connection_id="socket-a")
        await manager.connect("sess-4", "user-4", new_socket, connection_id="socket-b")

        await _websocket_heartbeat_loop(
            websocket=old_socket,
            session_id="sess-4",
            user_id="user-4",
            connection_id=old_id,
            last_pong={"t": asyncio.get_running_loop().time() - 999},
            ping_interval=0,
            pong_timeout=0.001,
            connection_manager=manager,
        )

        assert not new_socket.closed, "Stale heartbeat must not close the replacement socket"
        assert manager.get_socket("sess-4", "user-4") is new_socket

    asyncio.run(run_case())


def test_current_heartbeat_pings_after_valid_pong_and_only_current_timeout_closes():
    import asyncio
    from main import _websocket_heartbeat_loop

    async def run_case():
        manager = ConnectionManager()
        socket = _FakeWebSocket()
        conn_id = await manager.connect("sess-5", "user-5", socket, connection_id="socket-current")

        ping_task = asyncio.create_task(_websocket_heartbeat_loop(
            websocket=socket,
            session_id="sess-5",
            user_id="user-5",
            connection_id=conn_id,
            last_pong={"t": asyncio.get_running_loop().time()},
            ping_interval=0,
            pong_timeout=60,
            connection_manager=manager,
        ))
        await asyncio.sleep(0)
        ping_task.cancel()
        await asyncio.gather(ping_task, return_exceptions=True)
        assert not socket.closed

        await _websocket_heartbeat_loop(
            websocket=socket,
            session_id="sess-5",
            user_id="user-5",
            connection_id=conn_id,
            last_pong={"t": asyncio.get_running_loop().time() - 999},
            ping_interval=0,
            pong_timeout=0.001,
            connection_manager=manager,
        )
        assert socket.closed
        assert socket.close_calls[-1] == (1001, "Heartbeat timeout")

    asyncio.run(run_case())


def test_websocket_endpoint_cancels_lifecycle_tasks_and_logs_connection_id():
    main_path = os.path.join(PROJECT_ROOT, "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "connection_id = await manager.connect" in src
    assert "heartbeat_handle.cancel()" in src
    assert "autosave_handle.cancel()" in src
    assert "[WS] heartbeat start user_id=%s connection_id=%s" in src
    assert "[WS] heartbeat stale exit user_id=%s connection_id=%s" in src
    assert "[WS] pong received user_id=%s connection_id=%s" in src
    assert "[WS] timeout closing current socket user_id=%s connection_id=%s" in src
