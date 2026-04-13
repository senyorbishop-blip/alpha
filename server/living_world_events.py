"""Lightweight living-world event helpers for additive quest/content reactions."""
from __future__ import annotations

import secrets
import time
from typing import Any

from server.faction_reputation import apply_reputation_changes_to_session

RECENT_EVENT_LIMIT = 50


_ALLOWED_EVENT_TYPES = {
    "quest_accepted",
    "quest_completed",
    "interactable_used",
    "discovery_unlocked",
    "faction_reputation_changed",
    "guild_rank_changed",
    "handout_unlocked",
    "world_state_flag_set",
}


def _safe_text(value: Any, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


def _as_list(raw: Any) -> list[Any]:
    return list(raw) if isinstance(raw, list) else []


def normalize_world_event_envelope(event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = dict(payload or {})
    normalized_type = _safe_text(event_type, limit=64).lower() or "world_state_flag_set"
    if normalized_type not in _ALLOWED_EVENT_TYPES:
        normalized_type = "world_state_flag_set"
    return {
        "id": _safe_text(body.get("id") or f"wle-{secrets.token_hex(6)}", limit=64),
        "event_type": normalized_type,
        "ts": float(body.get("ts") or time.time()),
        "source": _safe_text(body.get("source"), limit=120),
        "actor_user_id": _safe_text(body.get("actor_user_id"), limit=64),
        "summary": _safe_text(body.get("summary"), limit=280),
        "quest_id": _safe_text(body.get("quest_id"), limit=64),
        "handout_id": _safe_text(body.get("handout_id"), limit=80),
        "discovery_id": _safe_text(body.get("discovery_id"), limit=80),
        "faction_id": _safe_text(body.get("faction_id"), limit=64),
        "guild_rank_id": _safe_text(body.get("guild_rank_id"), limit=64),
        "meta": dict(body.get("meta") or {}),
    }


def append_recent_world_event(session, event: dict[str, Any]) -> list[dict[str, Any]]:
    world_state = dict(getattr(session, "world_state", {}) or {})
    recent = _as_list(world_state.get("recent_events"))
    recent.append(dict(event or {}))
    world_state["recent_events"] = recent[-RECENT_EVENT_LIMIT:]
    session.world_state = world_state
    return world_state["recent_events"]


def emit_world_event(session, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    event = normalize_world_event_envelope(event_type, payload)
    append_recent_world_event(session, event)
    return event


def _append_unique_ids(world_state: dict[str, Any], key: str, values: list[Any], *, limit: int = 200) -> list[str]:
    out = [str(v).strip()[:80] for v in _as_list(world_state.get(key)) if str(v).strip()]
    for raw in values:
        text = str(raw or "").strip()[:80]
        if text and text not in out:
            out.append(text)
    world_state[key] = out[-limit:]
    return world_state[key]


def consume_world_event(session, event: dict[str, Any], reaction_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    event_row = normalize_world_event_envelope(str((event or {}).get("event_type") or ""), event)
    world_state = dict(getattr(session, "world_state", {}) or {})
    rules = dict(reaction_bundle or {})
    if not rules:
        registry = dict(world_state.get("event_reactions") or {})
        rules = dict(registry.get(event_row["event_type"]) or {})

    summary: dict[str, Any] = {
        "event_id": event_row["id"],
        "event_type": event_row["event_type"],
        "applied": {},
    }

    flags = dict(rules.get("set_world_state_flags") or rules.get("flags") or {})
    if flags:
        current_flags = dict(world_state.get("world_state_flags") or {})
        current_flags.update({str(k)[:80]: v for k, v in flags.items()})
        world_state["world_state_flags"] = current_flags
        summary["applied"]["world_state_flags"] = sorted(current_flags.keys())

    handouts = [str(v).strip()[:80] for v in _as_list(rules.get("unlock_handout_ids")) if str(v).strip()]
    if handouts:
        unlocked = _append_unique_ids(world_state, "unlocked_handout_ids", handouts)
        summary["applied"]["unlocked_handout_ids"] = unlocked

    discoveries = [str(v).strip()[:80] for v in _as_list(rules.get("append_discovery_ids")) if str(v).strip()]
    if discoveries:
        known = _append_unique_ids(world_state, "discovery_ids", discoveries)
        summary["applied"]["discovery_ids"] = known

    messages = [str(v).strip()[:240] for v in _as_list(rules.get("summary_messages")) if str(v).strip()]
    if messages:
        event_messages = [str(v).strip()[:240] for v in _as_list(world_state.get("event_messages")) if str(v).strip()]
        event_messages.extend(messages)
        world_state["event_messages"] = event_messages[-RECENT_EVENT_LIMIT:]
        summary["applied"]["summary_messages"] = messages

    refresh_ids = [str(v).strip()[:64] for v in _as_list(rules.get("refresh_quest_ids")) if str(v).strip()]
    if refresh_ids:
        marked = _append_unique_ids(world_state, "quest_refresh_ids", refresh_ids, limit=200)
        summary["applied"]["quest_refresh_ids"] = marked

    reputation_changes = rules.get("faction_reputation_changes") or rules.get("reputation")
    if isinstance(reputation_changes, (list, dict)):
        rep_applied = apply_reputation_changes_to_session(
            session,
            {"reputation": reputation_changes},
            source=f"event:{event_row['event_type']}",
        )
        if rep_applied:
            summary["applied"]["faction_reputation"] = rep_applied

    session.world_state = world_state
    return summary
