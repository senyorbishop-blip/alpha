import asyncio
import logging

from server.handlers import handle_message
from server.handlers.common import manager
from server.session import Session, User


def test_unknown_message_type_logs_warning_and_sends_generic_error(monkeypatch, caplog):
    session = Session(id="session-unknown-msg")
    user = User(id="player-unknown-msg", name="Unknown Msg Player", role="player")
    sent = []

    async def fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(manager, "send_to", fake_send_to)

    caplog.set_level(logging.WARNING, logger="server.handlers")

    asyncio.run(
        handle_message(
            {"type": "unknown_message_type_for_logging", "payload": {"debug": "do-not-leak"}},
            session,
            user,
        )
    )

    warnings = [
        record
        for record in caplog.records
        if record.name == "server.handlers"
        and record.levelno == logging.WARNING
        and getattr(record, "msg_type", None) == "unknown_message_type_for_logging"
    ]
    assert warnings, "Unknown message types should emit a structured warning log."

    record = warnings[0]
    assert record.session_id == "session-unknown-msg"
    assert record.user_id == "player-unknown-msg"
    assert record.user_role == "player"

    assert sent == [
        (
            "session-unknown-msg",
            "player-unknown-msg",
            {
                "type": "error",
                "payload": {"message": "Something went wrong. Please refresh and try again."},
            },
        )
    ]
    assert "unknown_message_type_for_logging" not in sent[0][2]["payload"]["message"]
    assert "do-not-leak" not in sent[0][2]["payload"]["message"]
