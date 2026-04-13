"""Deterministic quest-chain and unlock resolution helpers."""
from __future__ import annotations

from copy import deepcopy
from server.quest_premium_progression import guild_rank_points_from_completed_quests, guild_rank_tiers


_COMPLETED_QUEST_STATUSES = {"completed", "rewards_granted"}


def _normalize_tag_list(raw, *, limit: int = 24) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for entry in raw:
        tag = str(entry or "").strip().lower()[:64]
        if not tag or tag in out:
            continue
        out.append(tag)
        if len(out) >= limit:
            break
    return out


def _normalize_id_list(raw, *, limit: int = 24) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for entry in raw:
        quest_id = str(entry or "").strip()[:64]
        if not quest_id or quest_id in out:
            continue
        out.append(quest_id)
        if len(out) >= limit:
            break
    return out


def _party_faction_tags(session) -> set[str]:
    tags: set[str] = set()
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    for profile_list in profiles.values():
        if not isinstance(profile_list, list):
            continue
        for profile in profile_list:
            if not isinstance(profile, dict):
                continue
            faction = str(profile.get("faction") or "").strip().lower()[:64]
            if faction:
                tags.add(faction)
    return tags


def normalize_quest_progression_fields(quest: dict) -> dict:
    out = deepcopy(dict(quest or {}))
    required_faction_tags = _normalize_tag_list(
        out.get("required_faction_tags")
        or (out.get("meta") or {}).get("required_faction_tags")
    )
    faction_tags = _normalize_tag_list(out.get("faction_tags"))
    guild_tags = _normalize_tag_list(out.get("guild_tags"))
    prerequisite_quest_ids = _normalize_id_list(out.get("prerequisite_quest_ids"))
    unlocks_quest_ids = _normalize_id_list(out.get("unlocks_quest_ids"))
    hidden_until_unlocked = bool(out.get("hidden_until_unlocked"))
    lock_visibility = str(out.get("lock_visibility") or "").strip().lower()
    if lock_visibility not in {"listed", "hidden"}:
        lock_visibility = "hidden" if hidden_until_unlocked else "listed"
    if out.get("required_faction_rank") is not None:
        out["required_faction_rank"] = str(out.get("required_faction_rank") or "").strip()[:80]
    required_rank_id = str(
        out.get("required_guild_rank_id")
        or (out.get("meta") or {}).get("required_guild_rank_id")
        or ""
    ).strip().lower()[:40]
    valid_rank_ids = {str(tier.get("key") or "") for tier in guild_rank_tiers()}
    if required_rank_id and required_rank_id not in valid_rank_ids:
        required_rank_id = ""
    required_rank_points = out.get("required_guild_rank_points")
    if required_rank_points is None:
        required_rank_points = (out.get("meta") or {}).get("required_guild_rank_points")
    try:
        required_rank_points = max(0, min(10_000, int(required_rank_points or 0)))
    except Exception:
        required_rank_points = 0
    out["required_guild_rank_id"] = required_rank_id
    out["required_guild_rank_points"] = required_rank_points
    out["required_faction_tags"] = required_faction_tags
    out["faction_tags"] = faction_tags
    out["guild_tags"] = guild_tags
    out["prerequisite_quest_ids"] = prerequisite_quest_ids
    out["unlocks_quest_ids"] = unlocks_quest_ids
    out["hidden_until_unlocked"] = hidden_until_unlocked
    out["lock_visibility"] = lock_visibility
    return out


def resolve_session_quest_progression(session) -> list[dict]:
    quests = list(getattr(session, "session_quests", []) or [])
    if not quests:
        return []
    by_id = {
        str((quest or {}).get("id") or ""): dict(quest or {})
        for quest in quests
        if str((quest or {}).get("id") or "")
    }
    for quest in by_id.values():
        quest.update(normalize_quest_progression_fields(quest))

    for quest in by_id.values():
        for target_id in list(quest.get("unlocks_quest_ids") or []):
            target = by_id.get(str(target_id))
            if not target:
                continue
            prereqs = _normalize_id_list(target.get("prerequisite_quest_ids"))
            quest_id = str(quest.get("id") or "")
            if quest_id and quest_id not in prereqs:
                prereqs.append(quest_id)
            target["prerequisite_quest_ids"] = prereqs

    party_tags = _party_faction_tags(session)
    guild_rank_points = guild_rank_points_from_completed_quests(session)
    rank_index = {
        str(tier.get("key") or ""): idx
        for idx, tier in enumerate(guild_rank_tiers())
        if str(tier.get("key") or "")
    }
    current_rank_id = ""
    current_rank_idx = 0
    for tier in guild_rank_tiers():
        min_points = int(tier.get("min_points") or 0)
        if guild_rank_points >= min_points:
            current_rank_id = str(tier.get("key") or "")
            current_rank_idx = rank_index.get(current_rank_id, current_rank_idx)
    changed: list[dict] = []
    for quest_id in sorted(by_id.keys()):
        quest = by_id[quest_id]
        prereqs = list(quest.get("prerequisite_quest_ids") or [])
        required_tags = list(quest.get("required_faction_tags") or [])
        required_guild_rank_id = str(quest.get("required_guild_rank_id") or "")
        required_guild_rank_points = max(0, int(quest.get("required_guild_rank_points") or 0))
        prereq_blockers = [
            req for req in prereqs
            if str((by_id.get(req) or {}).get("status") or "").strip().lower() not in _COMPLETED_QUEST_STATUSES
        ]
        missing_tags = [tag for tag in required_tags if tag not in party_tags]
        required_rank_idx = rank_index.get(required_guild_rank_id, 0) if required_guild_rank_id else 0
        missing_rank = bool(required_guild_rank_id and current_rank_idx < required_rank_idx)
        missing_rank_points = bool(required_guild_rank_points and guild_rank_points < required_guild_rank_points)
        unlocked = not prereq_blockers and not missing_tags and not missing_rank and not missing_rank_points
        meta = dict(quest.get("meta") or {})
        meta["unlock_state"] = "unlocked" if unlocked else "locked"
        meta["unlock_blockers"] = {
            "prerequisite_quest_ids": prereq_blockers,
            "missing_faction_tags": missing_tags,
            "required_guild_rank_id": required_guild_rank_id if missing_rank else "",
            "required_guild_rank_points": required_guild_rank_points if missing_rank_points else 0,
            "current_guild_rank_id": current_rank_id,
            "current_guild_rank_points": guild_rank_points,
        }
        quest["meta"] = meta
        quest["availability_state"] = "unlocked" if unlocked else ("hidden_locked" if quest.get("lock_visibility") == "hidden" else "locked")
        visibility = dict(quest.get("visibility") or {})
        mode = str(visibility.get("mode") or "dm_only").strip().lower() or "dm_only"
        if mode not in {"dm_only", "hidden"}:
            if unlocked:
                if mode in {"locked", "hidden_locked"}:
                    visibility["mode"] = "party_public"
            else:
                visibility["mode"] = "hidden_locked" if quest.get("lock_visibility") == "hidden" else "locked"
        quest["visibility"] = visibility
        changed.append(quest)

    changed.sort(key=lambda row: float(row.get("updated_at") or row.get("created_at") or 0))
    return changed
