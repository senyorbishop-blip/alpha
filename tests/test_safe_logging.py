"""P9 safe logging regression tests."""

from __future__ import annotations

from pathlib import Path

from server.utils.safe_logging import REDACTED, safe_log_extra, sanitize_for_log

ROOT = Path(__file__).resolve().parents[1]


def test_sanitize_for_log_redacts_secret_like_keys():
    payload = {
        "DND_JWT_SECRET": "super-secret-value",
        "api_key": "sk-live-123",
        "password": "hunter2",
        "Authorization": "Bearer abc",
        "nested": {"session_cookie": "cookie-value"},
    }

    clean = sanitize_for_log(payload)

    assert clean["DND_JWT_SECRET"] == REDACTED
    assert clean["api_key"] == REDACTED
    assert clean["password"] == REDACTED
    assert clean["Authorization"] == REDACTED
    assert clean["nested"]["session_cookie"] == REDACTED


def test_sanitize_for_log_keeps_safe_gameplay_identifiers():
    payload = {
        "session_id": "ABC123",
        "user_id": "player-1",
        "token_id": "tok-1",
        "token_state_revision": 7,
    }

    clean = sanitize_for_log(payload)

    assert clean == payload


def test_sanitize_for_log_truncates_large_strings_and_lists():
    clean = sanitize_for_log({
        "message": "x" * 500,
        "items": list(range(40)),
    })

    assert clean["message"].endswith("…")
    assert len(clean["message"]) <= 240
    assert clean["items"][-1] == "... 28 more items"


def test_safe_log_extra_sanitizes_all_values():
    clean = safe_log_extra(payload={"token": "secret", "token_id": "visible"}, raw="y" * 500)

    assert clean["payload"]["token"] == REDACTED
    assert clean["payload"]["token_id"] == "visible"
    assert clean["raw"].endswith("…")


def test_key_server_files_do_not_log_raw_payload_or_request_bodies():
    scanned = [
        ROOT / "main.py",
        ROOT / "server" / "handlers" / "__init__.py",
        ROOT / "server" / "handlers" / "ai_dm.py",
        ROOT / "server" / "handlers" / "inventory.py",
        ROOT / "server" / "handlers" / "tokens.py",
    ]
    forbidden_snippets = [
        "extra={\"payload\": payload}",
        "extra={'payload': payload}",
        "extra={\"raw\": raw}",
        "extra={'raw': raw}",
        "logger.info(payload",
        "logger.warning(payload",
        "logger.error(payload",
        "print(payload",
        "print(raw",
    ]

    offenders: list[str] = []
    for path in scanned:
        text = path.read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            if snippet in text:
                offenders.append(f"{path.relative_to(ROOT)} contains {snippet}")

    assert not offenders


def test_safe_logging_helper_exists_for_future_structured_logs():
    helper = ROOT / "server" / "utils" / "safe_logging.py"
    text = helper.read_text(encoding="utf-8")

    assert "def sanitize_for_log" in text
    assert "def safe_log_extra" in text
    assert "[REDACTED]" in text
