import asyncio
from types import SimpleNamespace

from server.connections import ConnectionManager


class FakeWebSocket:
    def __init__(self, *, fail=False, on_send=None):
        self.accepted = False
        self.closed = False
        self.sent = []
        self.fail = fail
        self.on_send = on_send

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=""):
        self.closed = True

    async def send_text(self, payload):
        self.sent.append(payload)
        if self.on_send:
            await self.on_send()
        if self.fail:
            raise RuntimeError("send failed")


async def _connect(manager, session_id, user_id, websocket):
    await manager.connect(session_id, user_id, websocket)


def test_broadcast_failed_old_socket_does_not_disconnect_newer_current_socket():
    async def run_case():
        manager = ConnectionManager()
        session_id = "sess-broadcast"
        user_id = "user-1"
        new_socket = FakeWebSocket()

        async def reconnect_before_failure():
            await manager.connect(session_id, user_id, new_socket)

        old_socket = FakeWebSocket(fail=True, on_send=reconnect_before_failure)
        await _connect(manager, session_id, user_id, old_socket)

        await manager.broadcast(session_id, {"type": "state_update"})

        assert manager.get_socket(session_id, user_id) is new_socket
        assert manager.is_connected(session_id, user_id)

    asyncio.run(run_case())


def test_send_to_failed_old_socket_does_not_disconnect_newer_current_socket():
    async def run_case():
        manager = ConnectionManager()
        session_id = "sess-send-to"
        user_id = "user-1"
        new_socket = FakeWebSocket()

        async def reconnect_before_failure():
            await manager.connect(session_id, user_id, new_socket)

        old_socket = FakeWebSocket(fail=True, on_send=reconnect_before_failure)
        await _connect(manager, session_id, user_id, old_socket)

        sent = await manager.send_to(session_id, user_id, {"type": "direct_message"})

        assert sent is False
        assert manager.get_socket(session_id, user_id) is new_socket
        assert manager.is_connected(session_id, user_id)

    asyncio.run(run_case())


def test_broadcast_to_role_failed_old_socket_does_not_disconnect_newer_current_socket():
    async def run_case():
        manager = ConnectionManager()
        session_id = "sess-role"
        user_id = "user-1"
        new_socket = FakeWebSocket()

        async def reconnect_before_failure():
            await manager.connect(session_id, user_id, new_socket)

        old_socket = FakeWebSocket(fail=True, on_send=reconnect_before_failure)
        await _connect(manager, session_id, user_id, old_socket)
        session_obj = SimpleNamespace(users={user_id: SimpleNamespace(role="player")})

        await manager.broadcast_to_role(session_id, {"type": "player_notice"}, {"player"}, session_obj)

        assert manager.get_socket(session_id, user_id) is new_socket
        assert manager.is_connected(session_id, user_id)

    asyncio.run(run_case())


def test_broadcast_filtered_failed_old_socket_does_not_disconnect_newer_current_socket():
    async def run_case():
        manager = ConnectionManager()
        session_id = "sess-filtered"
        user_id = "user-1"
        new_socket = FakeWebSocket()

        async def reconnect_before_failure():
            await manager.connect(session_id, user_id, new_socket)

        old_socket = FakeWebSocket(fail=True, on_send=reconnect_before_failure)
        await _connect(manager, session_id, user_id, old_socket)

        await manager.broadcast_filtered(session_id, {"type": "token_moved", "payload": {}})

        assert manager.get_socket(session_id, user_id) is new_socket
        assert manager.is_connected(session_id, user_id)

    asyncio.run(run_case())


def test_failed_current_socket_is_still_removed():
    async def run_case():
        manager = ConnectionManager()
        session_id = "sess-current"
        user_id = "user-1"
        socket = FakeWebSocket(fail=True)
        await _connect(manager, session_id, user_id, socket)

        await manager.broadcast(session_id, {"type": "state_update"})

        assert manager.get_socket(session_id, user_id) is None
        assert not manager.is_connected(session_id, user_id)

    asyncio.run(run_case())
