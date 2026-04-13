"""Faction reputation helpers for quest/campaign progression state."""
from __future__ import annotations

import time
from typing import Any


_TIERS = [
    {"key": "hostile", "label": "Hostile", "min": -10},
    {"key": "cold", "label": "Cold", "min": -4},
    {"key": "neutral", "label": "Neutral", "min": 0},
    {"key": "trusted", "label": "Trusted", "min": 5},
    {"key": "allied", "label": "Allied", "min": 12},
    {"key": "venerated", "label": "Venerated", "min": 20},
]


def _safe_int(raw: Any, default: int = 0, *, minimum: int = -10_000, maximum: int = 10_000) -> int:
    try:
        value = int(raw)
    except Exception:
        return default
    return max(minimum, min(maximum, value))


def _slugify(text: Any, *, limit: int = 64) -> str:
    raw = str(text or "").strip().lower()
    out = []
    prev_dash = False
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
            continue
        if ch in {" ", "_", "-", "."} and not prev_dash:
            out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")[:limit]
    return slug


def reputation_tier_for(value: Any) -> dict[str, Any]:
    score = _safe_int(value, 0, minimum=-10_000, maximum=10_000)
    picked = _TIERS[0]
    for tier in _TIERS:
        if score >= int(tier["min"]):
            picked = tier
    return {"key": picked["key"], "label": picked["label"]}


def normalize_reputation_change_list(reward_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(reward_bundle, dict):
        return []
    raw = reward_bundle.get("reputation")
    changes: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for faction_name, delta in list(raw.items())[:30]:
            name = str(faction_name or "").strip()[:80]
            amount = _safe_int(delta, 0)
            if name and amount:
                changes.append({
                    "id": _slugify(faction_name) or _slugify(name),
                    "name": name,
                    "tag": _slugify(faction_name) or _slugify(name),
                    "delta": amount,
                    "visibility": "party",
                })
    elif isinstance(raw, list):
        for row in raw[:30]:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or row.get("faction") or row.get("id") or "").strip()[:80]
            faction_id = str(row.get("id") or "").strip()[:64] or _slugify(name)
            tag = str(row.get("tag") or "").strip()[:48] or _slugify(name, limit=48)
            amount = _safe_int(row.get("delta"), 0)
            visibility = str(row.get("visibility") or "party").strip().lower()[:16]
            if visibility not in {"party", "dm_only"}:
                visibility = "party"
            if name and faction_id and amount:
                changes.append({
                    "id": faction_id,
                    "name": name,
                    "tag": tag or faction_id,
                    "delta": amount,
                    "visibility": visibility,
                })

    deduped: dict[str, dict[str, Any]] = {}
    for row in changes:
        key = str(row.get("id") or "").strip()[:64]
        if not key:
            continue
        if key not in deduped:
            deduped[key] = dict(row)
            continue
        deduped[key]["delta"] = int(deduped[key].get("delta") or 0) + int(row.get("delta") or 0)
        if str(row.get("visibility") or "") == "dm_only":
            deduped[key]["visibility"] = "dm_only"
    return [row for row in deduped.values() if int(row.get("delta") or 0)]


def normalize_faction_reputation_state(raw: Any) -> dict[str, dict[str, Any]]:
    src = dict(raw) if isinstance(raw, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in list(src.items())[:200]:
        row = dict(value) if isinstance(value, dict) else {}
        faction_id = str(row.get("id") or key or "").strip()[:64] or _slugify(key)
        if not faction_id:
            continue
        name = str(row.get("name") or row.get("faction") or faction_id).strip()[:80] or faction_id
        tag = str(row.get("tag") or "").strip()[:48] or _slugify(name, limit=48) or faction_id
        reputation = _safe_int(row.get("reputation"), 0, minimum=-50_000, maximum=50_000)
        visibility = str(row.get("visibility") or "party").strip().lower()[:16]
        if visibility not in {"party", "dm_only"}:
            visibility = "party"
        tier = reputation_tier_for(reputation)
        out[faction_id] = {
            "id": faction_id,
            "name": name,
            "tag": tag,
            "reputation": reputation,
            "tier": tier["key"],
            "tier_label": tier["label"],
            "visibility": visibility,
            "updated_at": float(row.get("updated_at") or 0.0),
        }
    return out


def apply_reputation_changes_to_session(
    session,
    reward_bundle: dict[str, Any],
    *,
    source: str = "",
) -> list[dict[str, Any]]:
    world_state = dict(getattr(session, "world_state", {}) or {})
    rep_state = normalize_faction_reputation_state(world_state.get("faction_reputation"))
    changes = normalize_reputation_change_list(reward_bundle)
    if not changes:
        world_state["faction_reputation"] = rep_state
        session.world_state = world_state
        return []

    now = time.time()
    applied: list[dict[str, Any]] = []
    for change in changes:
        faction_id = str(change.get("id") or "").strip()[:64]
        if not faction_id:
            continue
        current = dict(rep_state.get(faction_id) or {
            "id": faction_id,
            "name": str(change.get("name") or faction_id)[:80],
            "tag": str(change.get("tag") or faction_id)[:48],
            "reputation": 0,
            "visibility": str(change.get("visibility") or "party"),
            "updated_at": 0.0,
        })
        delta = int(change.get("delta") or 0)
        current_rep = _safe_int(current.get("reputation"), 0, minimum=-50_000, maximum=50_000)
        next_rep = _safe_int(current_rep + delta, 0, minimum=-50_000, maximum=50_000)
        tier = reputation_tier_for(next_rep)
        current.update({
            "name": str(change.get("name") or current.get("name") or faction_id)[:80],
            "tag": str(change.get("tag") or current.get("tag") or faction_id)[:48],
            "reputation": next_rep,
            "tier": tier["key"],
            "tier_label": tier["label"],
            "visibility": "dm_only" if str(change.get("visibility") or "") == "dm_only" else str(current.get("visibility") or "party"),
            "updated_at": now,
            "last_source": str(source or "")[:120],
        })
        rep_state[faction_id] = current
        applied.append({
            "id": faction_id,
            "name": current["name"],
            "tag": current["tag"],
            "delta": delta,
            "reputation": next_rep,
            "tier": current["tier"],
            "tier_label": current["tier_label"],
            "visibility": current["visibility"],
        })

    world_state["faction_reputation"] = rep_state
    session.world_state = world_state
    return applied
