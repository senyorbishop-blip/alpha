import asyncio
import logging

from server.connections import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=""):
        return None

    async def send_text(self, payload):
        self.sent.append(payload)


def _message_with_private_content(size):
    return {
        "type": "private_profile_sync",
        "payload": {
            "private_notes": "SECRET_PRIVATE_NOTES_DO_NOT_LOG",
            "profile": "A" * size,
        },
    }


def test_small_payload_emits_no_warning(caplog):
    async def run_case():
        manager = ConnectionManager()
        ws = FakeWebSocket()
        await manager.connect("sess-small", "user-small", ws, role="player")

        with caplog.at_level(logging.DEBUG, logger="server.connections"):
            sent = await manager.send_to("sess-small", "user-small", {"type": "ping"})

        assert sent is True

    asyncio.run(run_case())

    send_records = [record for record in caplog.records if "outbound_send" in record.getMessage()]
    assert send_records, "expected outbound diagnostic log for small payload"
    assert all(record.levelno < logging.WARNING for record in send_records)
    assert "message_type=ping" in caplog.text
    assert "byte_size=" in caplog.text


def test_payload_over_128kb_emits_warning(caplog):
    async def run_case():
        manager = ConnectionManager()
        ws = FakeWebSocket()
        await manager.connect("sess-warn", "user-warn", ws, role="viewer")

        with caplog.at_level(logging.DEBUG, logger="server.connections"):
            await manager.send_to("sess-warn", "user-warn", _message_with_private_content(129 * 1024))

    asyncio.run(run_case())

    records = [record for record in caplog.records if "outbound_send" in record.getMessage()]
    assert any(record.levelno == logging.WARNING for record in records)
    assert not any(record.levelno >= logging.ERROR for record in records)
    assert "message_type=private_profile_sync" in caplog.text
    assert "recipient_role=viewer" in caplog.text
    assert "byte_size=" in caplog.text


def test_payload_over_512kb_emits_error(caplog):
    async def run_case():
        manager = ConnectionManager()
        ws = FakeWebSocket()
        await manager.connect("sess-error", "user-error", ws, role="dm")

        with caplog.at_level(logging.DEBUG, logger="server.connections"):
            await manager.broadcast("sess-error", _message_with_private_content(513 * 1024))

    asyncio.run(run_case())

    records = [record for record in caplog.records if "outbound_send" in record.getMessage()]
    assert any(record.levelno == logging.ERROR for record in records)
    assert "message_type=private_profile_sync" in caplog.text
    assert "recipient_role=dm" in caplog.text
    assert "byte_size=" in caplog.text


def test_diagnostic_log_excludes_raw_private_payload_content(caplog):
    async def run_case():
        manager = ConnectionManager()
        ws = FakeWebSocket()
        await manager.connect("sess-private", "user-private", ws, role="player")

        with caplog.at_level(logging.DEBUG, logger="server.connections"):
            await manager.send_to("sess-private", "user-private", _message_with_private_content(129 * 1024))

    asyncio.run(run_case())

    assert "message_type=private_profile_sync" in caplog.text
    assert "byte_size=" in caplog.text
    assert "SECRET_PRIVATE_NOTES_DO_NOT_LOG" not in caplog.text
    assert "private_notes" not in caplog.text
    assert "\"profile\"" not in caplog.text
