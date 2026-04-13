"""
server/economy_scaffold.py — Stage scaffolding for future crafting/economy work.

This module is intentionally non-authoritative and non-runtime-impacting for current
inventory/shop/chest gameplay. It exists to document and normalize optional state
shapes that later stages can adopt incrementally.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


# Default-off feature gates for staged rollout work.
ECONOMY_FEATURE_FLAGS: dict[str, bool] = {
    "materials": False,
    "corpse_state": False,
    "professions": False,
    "recipes": False,
    "craft_jobs": False,
    "selling": False,
    "server_haggle": False,
}


# Optional per-campaign state shape reserved for future phases.
ECONOMY_STATE_TEMPLATE: dict[str, Any] = {
    "version": 1,
    "materials": {},          # item_id -> metadata
    "corpse_registry": {},    # token_id -> corpse metadata
    "professions": {},        # player_key -> profession summary
    "recipes": {},            # recipe_id -> recipe snapshot
    "craft_jobs": {},         # job_id -> queued/in-progress craft
    "sell_rules": {},         # DM-configurable selling policy knobs
    "haggle_rules": {},       # DM-configurable server-authoritative haggle knobs
}


def build_default_economy_state() -> dict[str, Any]:
    """Return a fresh mutable template for future economy features."""
    return deepcopy(ECONOMY_STATE_TEMPLATE)


def normalize_economy_state(raw: Any) -> dict[str, Any]:
    """Best-effort shape guard for optional economy state payloads.

    This function intentionally performs only shallow normalization because the
    feature set is not active yet.
    """
    src = raw if isinstance(raw, dict) else {}
    out = build_default_economy_state()

    version = src.get("version")
    try:
        out["version"] = max(1, int(version))
    except Exception:
        out["version"] = 1

    for key in (
        "materials",
        "corpse_registry",
        "professions",
        "recipes",
        "craft_jobs",
        "sell_rules",
        "haggle_rules",
    ):
        value = src.get(key)
        out[key] = dict(value) if isinstance(value, dict) else {}

    return out
