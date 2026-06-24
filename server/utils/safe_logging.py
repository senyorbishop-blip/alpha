"""Safe logging helpers.

Use these helpers when adding structured logging for WebSocket messages,
request payloads, auth flows, or integration calls. The helpers keep useful
operational context while redacting secret-looking keys and truncating large or
untrusted values.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"
MAX_STRING_LENGTH = 240
MAX_LIST_ITEMS = 12
MAX_DICT_ITEMS = 40

_SECRET_KEY_PARTS = (
    "secret",
    "token",
    "api_key",
    "apikey",
    "key",
    "password",
    "passwd",
    "authorization",
    "cookie",
    "session",
    "jwt",
    "bearer",
)

_SAFE_KEY_EXCEPTIONS = {
    "token_id",
    "token_ids",
    "token_name",
    "token_type",
    "token_state_revision",
    "visibility_token_revision",
    "session_id",
    "user_id",
    "target_user_id",
    "owner_id",
}


def _is_secret_key(key: Any) -> bool:
    text = str(key or "").strip().lower()
    if not text:
        return False
    if text in _SAFE_KEY_EXCEPTIONS:
        return False
    return any(part in text for part in _SECRET_KEY_PARTS)


def _truncate(text: str, *, limit: int = MAX_STRING_LENGTH) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def sanitize_for_log(value: Any, *, depth: int = 0) -> Any:
    """Return a JSON-ish value safe for structured logs."""
    if depth > 5:
        return "[MAX_DEPTH]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate(value)
    if isinstance(value, bytes):
        return f"[bytes:{len(value)}]"
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_DICT_ITEMS:
                out["..."] = f"{len(value) - MAX_DICT_ITEMS} more keys"
                break
            key_text = _truncate(str(key), limit=80)
            if _is_secret_key(key):
                out[key_text] = REDACTED
            else:
                out[key_text] = sanitize_for_log(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = list(value)
        trimmed = [sanitize_for_log(item, depth=depth + 1) for item in items[:MAX_LIST_ITEMS]]
        if len(items) > MAX_LIST_ITEMS:
            trimmed.append(f"... {len(items) - MAX_LIST_ITEMS} more items")
        return trimmed
    return _truncate(repr(value))


def safe_log_extra(**kwargs: Any) -> dict[str, Any]:
    """Build a sanitized `extra` dict for logger calls."""
    return {str(key): sanitize_for_log(value) for key, value in kwargs.items()}
