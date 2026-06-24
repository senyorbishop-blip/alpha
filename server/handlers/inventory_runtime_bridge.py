"""Runtime inventory rehydration bridge.

Quick Actions and some inventory sync paths historically called
``server.session.get_player_inventory_for_user``. That lightweight helper keeps
old rows readable, but it does not use the stronger compendium rehydration in
``server.handlers.inventory``. Magic items can therefore appear repaired in the
inventory mutation path but stale in Quick Actions.

This bridge installs a richer runtime getter after the inventory handler module
has loaded. It keeps the authoritative implementation in inventory.py while
making session-level callers see the same repaired item rows.
"""
from __future__ import annotations

from typing import Any


def get_rehydrated_player_inventory_for_user(session: Any, user_id: str) -> list[dict]:
    """Return a player's inventory after compendium/runtime rehydration.

    The implementation imports lazily to avoid circular imports during server
    startup. It also writes the repaired inventory back to the session because
    ``_get_player_inventory_store`` normalises stale rows and migrates legacy
    owner buckets.
    """
    user = (getattr(session, "users", {}) or {}).get(user_id)
    if not user:
        return []
    from server.handlers.inventory import _get_player_inventory_store

    _inventories, _owner_key, items = _get_player_inventory_store(session, user)
    return list(items or [])


def install_inventory_runtime_bridge() -> None:
    """Install the rehydrated getter for session and inventory runtime callers."""
    import server.session as session_mod

    session_mod.get_player_inventory_for_user = get_rehydrated_player_inventory_for_user

    # inventory.py imports get_player_inventory_for_user at module import time, so
    # update its local reference too when the module is already loaded.
    try:
        import server.handlers.inventory as inventory_mod
        inventory_mod.get_player_inventory_for_user = get_rehydrated_player_inventory_for_user
    except Exception:
        pass
