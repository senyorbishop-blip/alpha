"""Derived premium quest progression: faction reputation + guild rank.

This module intentionally derives state from session_quests so quest state remains
single-source-of-truth.
"""
from __future__ import annotations

from typing import Any
from server.faction_reputation import (
    normalize_faction_reputation_state,
    normalize_reputation_change_list,
    reputation_tier_for,
)

_COMPLETED = {"completed", "rewards_granted"}
_RANK_TIERS = [
    {"key": "novice", "label": "Novice", "min_points": 0, "board_tier": "town"},
    {"key": "trusted", "label": "Trusted", "min_points": 3, "board_tier": "regional"},
    {"key": "proven", "label": "Proven", "min_points": 6, "board_tier": "regional"},
    {"key": "renowned", "label": "Renowned", "min_points": 10, "board_tier": "high_risk"},
    {"key": "paragon", "label": "Paragon", "min_points": 15, "board_tier": "legendary"},
]


def _safe_int(raw: Any, default: int = 0, *, minimum: int = -10_000, maximum: int = 10_000) -> int:
    try:
        value = int(raw)
    except Exception:
        return default
    return max(minimum, min(maximum, value))


def _normalize_faction_key(raw: Any) -> str:
    return str(raw or "").strip()[:64]


def _parse_legacy_reputation_flag(raw: Any) -> list[dict[str, Any]]:
    text = str(raw or "").strip()
    if not text:
        return []
    out: list[dict[str, Any]] = []
    for chunk in text.split(",")[:20]:
        token = str(chunk or "").strip()
        if not token:
            continue
        if ":" in token:
            faction_raw, delta_raw = token.split(":", 1)
        elif "=" in token:
            faction_raw, delta_raw = token.split("=", 1)
        else:
            parts = token.rsplit(" ", 1)
            faction_raw = parts[0]
            delta_raw = parts[1] if len(parts) > 1 else ""
        faction = _normalize_faction_key(faction_raw)
        delta = _safe_int(delta_raw, 0)
        if faction and delta:
            out.append({"faction": faction, "delta": delta})
    return out


def _normalize_reputation_changes(reward_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    changes = [
        {"faction": str(row.get("name") or row.get("id") or "").strip(), "delta": int(row.get("delta") or 0)}
        for row in normalize_reputation_change_list(reward_bundle)
    ]
    flags = reward_bundle.get("flags") if isinstance(reward_bundle.get("flags"), dict) else {}
    changes.extend(_parse_legacy_reputation_flag(flags.get("faction_reputation")))
    deduped: dict[str, int] = {}
    for row in changes:
        faction = _normalize_faction_key(row.get("faction"))
        if faction:
            deduped[faction] = deduped.get(faction, 0) + int(row.get("delta") or 0)
    return [{"faction": faction, "delta": delta} for faction, delta in sorted(deduped.items()) if delta]


def _quest_rank_points(quest: dict[str, Any]) -> int:
    meta = quest.get("meta") if isinstance(quest.get("meta"), dict) else {}
    reward = quest.get("reward_bundle") if isinstance(quest.get("reward_bundle"), dict) else {}
    reward_meta = reward.get("meta") if isinstance(reward.get("meta"), dict) else {}
    explicit = reward_meta.get("guild_rank_points")
    if explicit is None:
        explicit = meta.get("guild_rank_points")
    if explicit is None:
        return 1
    return _safe_int(explicit, 1, minimum=0, maximum=100)


def guild_rank_tiers() -> list[dict[str, Any]]:
    return [dict(tier) for tier in _RANK_TIERS]


def _resolve_rank_idx(points: int) -> int:
    rank_idx = 0
    for idx, tier in enumerate(_RANK_TIERS):
        if points >= int(tier["min_points"]):
            rank_idx = idx
    return rank_idx


def rank_for_points(points: int) -> dict[str, Any]:
    return dict(_RANK_TIERS[_resolve_rank_idx(_safe_int(points, 0, minimum=0, maximum=10_000))])


def guild_rank_points_from_completed_quests(session) -> int:
    quests = list(getattr(session, "session_quests", []) or [])
    completed = [
        dict(row or {})
        for row in quests
        if str((row or {}).get("status") or "").strip().lower() in _COMPLETED
    ]
    return sum(_quest_rank_points(quest) for quest in completed)


def _guild_rank_up_events(completed_quests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline = sorted(
        completed_quests,
        key=lambda row: (
            float((row or {}).get("completed_at") or 0),
            float((row or {}).get("updated_at") or 0),
            float((row or {}).get("created_at") or 0),
            str((row or {}).get("id") or ""),
        ),
    )
    events: list[dict[str, Any]] = []
    points = 0
    current_idx = 0
    for quest in timeline:
        points += _quest_rank_points(quest)
        next_idx = _resolve_rank_idx(points)
        if next_idx <= current_idx:
            continue
        for idx in range(current_idx + 1, next_idx + 1):
            tier = dict(_RANK_TIERS[idx])
            events.append({
                "rank_id": str(tier.get("key") or ""),
                "rank_label": str(tier.get("label") or ""),
                "threshold_points": int(tier.get("min_points") or 0),
                "board_tier": str(tier.get("board_tier") or ""),
                "quest_id": str(quest.get("id") or ""),
                "quest_title": str(quest.get("title") or ""),
                "achieved_at": float(quest.get("completed_at") or quest.get("updated_at") or quest.get("created_at") or 0),
            })
        current_idx = next_idx
    return events[-8:]


def build_premium_progression_snapshot(session, *, role: str | None = None, user_id: str | None = None) -> dict[str, Any]:
    quests = list(getattr(session, "session_quests", []) or [])
    completed = [
        dict(row or {})
        for row in quests
        if str((row or {}).get("status") or "").strip().lower() in _COMPLETED
    ]

    faction_totals: dict[str, int] = {}
    guild_points = 0
    for quest in completed:
        reward = dict(quest.get("reward_bundle") or {})
        guild_points += _quest_rank_points(quest)
        for change in _normalize_reputation_changes(reward):
            key = change["faction"]
            faction_totals[key] = faction_totals.get(key, 0) + int(change["delta"])

    normalized_state = normalize_faction_reputation_state(
        (getattr(session, "world_state", {}) or {}).get("faction_reputation")
    )
    if normalized_state:
        faction_rows = sorted(
            normalized_state.values(),
            key=lambda row: (-int(row.get("reputation") or 0), str(row.get("name") or row.get("id") or "").lower()),
        )
    else:
        faction_rows = []
        for faction, score in sorted(faction_totals.items(), key=lambda entry: (-entry[1], entry[0].lower())):
            tier = reputation_tier_for(score)
            faction_rows.append({
                "id": _normalize_faction_key(faction).lower().replace(" ", "-"),
                "name": faction,
                "tag": _normalize_faction_key(faction).lower().replace(" ", "-"),
                "reputation": score,
                "tier": tier["key"],
                "tier_label": tier["label"],
                "visibility": "party",
            })

    role_norm = str(role or "").strip().lower()
    if role_norm and role_norm != "dm":
        faction_rows = [row for row in faction_rows if str((row or {}).get("visibility") or "party") != "dm_only"]
    faction_rows = [{
        "id": str(row.get("id") or ""),
        "faction": str(row.get("name") or row.get("faction") or "Faction"),
        "name": str(row.get("name") or row.get("faction") or "Faction"),
        "tag": str(row.get("tag") or ""),
        "score": int(row.get("reputation", row.get("score", 0)) or 0),
        "reputation": int(row.get("reputation", row.get("score", 0)) or 0),
        "tier": str(row.get("tier") or ""),
        "tier_label": str(row.get("tier_label") or ""),
        "visibility": str(row.get("visibility") or "party"),
    } for row in faction_rows]

    rank_idx = _resolve_rank_idx(guild_points)
    current_rank = dict(_RANK_TIERS[rank_idx])
    next_rank = dict(_RANK_TIERS[rank_idx + 1]) if (rank_idx + 1) < len(_RANK_TIERS) else None

    rank_progress = {
        "points": guild_points,
        "rank_id": str(current_rank.get("key") or "novice"),
        "rank_label": str(current_rank.get("label") or "Novice"),
        "rank_threshold_points": int(current_rank.get("min_points") or 0),
        "current_rank": current_rank,
        "next_rank": next_rank,
        "points_to_next": max(0, int(next_rank["min_points"]) - guild_points) if next_rank else 0,
        "completed_quests": len(completed),
        "thresholds": guild_rank_tiers(),
        "rank_up_events": _guild_rank_up_events(completed),
        "unlock_hooks": {
            "board_tier": str(current_rank.get("board_tier") or "town"),
            "suggested_unlocks": [f"board_tier:{str(current_rank.get('board_tier') or 'town')}"],
        },
    }

    return {
        "faction_reputation": faction_rows[:16],
        "guild_rank": rank_progress,
    }
