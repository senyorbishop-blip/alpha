"""Shared SRD item library payload helpers.

The SRD item list is static-ish and large, so live WebSocket connect messages send
only a stable version hash.  Clients request the full list only when their local
cache is missing or stale.
"""
import hashlib
import json
from functools import lru_cache
from typing import Any


def _load_srd_items() -> list[dict[str, Any]]:
    from server.rules_db import get_all_srd_items

    items = get_all_srd_items()
    return items if isinstance(items, list) else []


@lru_cache(maxsize=1)
def get_srd_items_snapshot() -> dict[str, Any]:
    """Return cached SRD items plus their stable SHA1 version hash."""
    items = _load_srd_items()
    compact = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "items": items,
        "version": hashlib.sha1(compact.encode("utf-8")).hexdigest(),
    }


def get_srd_items_version() -> str:
    """Return the current stable SRD item version hash."""
    return str(get_srd_items_snapshot().get("version") or "")


def get_srd_items_payload() -> dict[str, Any]:
    """Return the full SRD item response payload."""
    snapshot = get_srd_items_snapshot()
    return {
        "srd_items": list(snapshot.get("items") or []),
        "srd_items_version": str(snapshot.get("version") or ""),
    }


def clear_srd_items_snapshot_cache() -> None:
    """Clear cached SRD data; useful for tests/admin imports that mutate SRD rows."""
    get_srd_items_snapshot.cache_clear()
