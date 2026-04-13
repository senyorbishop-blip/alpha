"""Quest objective normalization and event-driven progression helpers."""
from __future__ import annotations

import time
from copy import deepcopy

_ALLOWED_QUEST_STATUS = {
    "draft",
    "available",
    "accepted",
    "active",
    "ready_to_turn_in",
    "rewards_pending",
    "rewards_granted",
    "published",
    "hidden",
    "completed",
    "failed",
    "expired",
}
_ALLOWED_OBJECTIVE_STATUS = {"pending", "active", "completed", "failed"}
_ALLOWED_OBJECTIVE_TYPES = {
    "visit_poi",
    "discover_location",
    "talk_npc",
    "defeat_target",
    "clear_encounter",
    "collect_item",
    "read_handout_clue",
    "return_to_board",
    "return_to_giver",
    "manual",
}


def normalize_quest_status(raw: str, *, fallback: str = "draft") -> str:
    status = str(raw or fallback).strip().lower()[:32]
    return status if status in _ALLOWED_QUEST_STATUS else fallback


def normalize_objective(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or raw.get("name") or "").strip()[:160]
    if not title:
        return None
    objective_id = str(raw.get("id") or f"obj-{idx + 1}").strip()[:80]
    if not objective_id:
        return None
    objective_type = str(raw.get("type") or "manual").strip().lower()[:40]
    if objective_type not in _ALLOWED_OBJECTIVE_TYPES:
        objective_type = "manual"
    status = str(raw.get("status") or "pending").strip().lower()[:24]
    if status not in _ALLOWED_OBJECTIVE_STATUS:
        status = "pending"
    required_count = int(raw.get("required_count") or 1)
    required_count = min(999, max(1, required_count))
    current_count = int(raw.get("current_count") or 0)
    current_count = min(required_count, max(0, current_count))
    target_id = str(raw.get("target_id") or raw.get("target_ref") or "").strip()[:96]
    target_map = str(raw.get("target_map_context") or "").strip()[:80]
    notes = str(raw.get("notes") or "").strip()[:240]
    out = {
        "id": objective_id,
        "title": title,
        "type": objective_type,
        "status": status,
        "required_count": required_count,
        "current_count": current_count,
        "target_id": target_id,
        "target_map_context": target_map,
        "notes": notes,
    }
    if current_count >= required_count:
        out["status"] = "completed"
    return out


def normalize_objective_list(raw_list) -> list[dict]:
    if not isinstance(raw_list, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for idx, raw in enumerate(raw_list[:40]):
        objective = normalize_objective(raw, idx)
        if not objective:
            continue
        oid = objective["id"]
        if oid in seen:
            continue
        seen.add(oid)
        out.append(objective)
    return out


def rebuild_progress(quest: dict) -> dict:
    progress = dict(quest.get("progress") or {})
    objective_status = {}
    objective_counts = {}
    completed = 0
    for objective in quest.get("objective_list") or []:
        oid = str(objective.get("id") or "")
        if not oid:
            continue
        status = str(objective.get("status") or "pending")
        objective_status[oid] = status
        objective_counts[oid] = {
            "current": int(objective.get("current_count") or 0),
            "required": int(objective.get("required_count") or 1),
        }
        if status == "completed":
            completed += 1
    total = len(quest.get("objective_list") or [])
    progress["objective_status"] = objective_status
    progress["objective_counts"] = objective_counts
    progress["completed_objectives"] = completed
    progress["total_objectives"] = total
    if total:
        progress["summary"] = f"{completed}/{total} objectives completed"
    return progress


def recompute_quest_lifecycle(quest: dict) -> None:
    status = normalize_quest_status(str(quest.get("status") or "draft"), fallback="draft")
    if status in {"completed", "failed", "expired", "hidden", "draft", "rewards_pending", "rewards_granted"}:
        quest["status"] = status
        return
    objectives = list(quest.get("objective_list") or [])
    if not objectives:
        if status == "available":
            quest["status"] = "available"
        elif status == "accepted":
            quest["status"] = "active"
        else:
            quest["status"] = status if status in _ALLOWED_QUEST_STATUS else "active"
        return

    complete = [o for o in objectives if str(o.get("status") or "pending") == "completed"]
    incomplete = [o for o in objectives if str(o.get("status") or "pending") != "completed"]
    if not incomplete:
        quest["status"] = "ready_to_turn_in"
        return

    return_gate = [
        o for o in incomplete
        if str(o.get("type") or "") in {"return_to_board", "return_to_giver"}
    ]
    non_return_incomplete = [o for o in incomplete if o not in return_gate]
    if return_gate and not non_return_incomplete:
        quest["status"] = "ready_to_turn_in"
        return

    if status == "available" and complete:
        quest["status"] = "active"
    elif status == "accepted":
        quest["status"] = "active"
    else:
        quest["status"] = status if status in _ALLOWED_QUEST_STATUS else "active"


def normalize_quest_payload_shape(quest: dict) -> dict:
    out = deepcopy(dict(quest or {}))
    out["status"] = normalize_quest_status(str(out.get("status") or "draft"), fallback="draft")
    out["objective_list"] = normalize_objective_list(out.get("objective_list"))
    out["progress"] = rebuild_progress(out)
    recompute_quest_lifecycle(out)
    return out


def apply_objective_event(quest: dict, event: dict) -> bool:
    event_type = str(event.get("event_type") or "").strip().lower()[:40]
    if not event_type:
        return False
    target_id = str(event.get("target_id") or "").strip()
    target_map_context = str(event.get("target_map_context") or event.get("map_context") or "").strip()

    changed = False
    objectives = list(quest.get("objective_list") or [])
    for objective in objectives:
        objective_type = str(objective.get("type") or "manual")
        status = str(objective.get("status") or "pending")
        if status in {"completed", "failed"}:
            continue
        if objective_type != event_type:
            continue
        objective_target = str(objective.get("target_id") or "").strip()
        objective_map = str(objective.get("target_map_context") or "").strip()
        if objective_target and target_id and objective_target != target_id:
            continue
        if objective_map and target_map_context and objective_map != target_map_context:
            continue

        required_count = max(1, int(objective.get("required_count") or 1))
        current_count = max(0, int(objective.get("current_count") or 0)) + max(1, int(event.get("delta") or 1))
        objective["current_count"] = min(required_count, current_count)
        if objective["current_count"] >= required_count:
            objective["status"] = "completed"
        elif status == "pending":
            objective["status"] = "active"
        changed = True

    if not changed:
        return False
    quest["objective_list"] = objectives
    quest["progress"] = rebuild_progress(quest)
    if normalize_quest_status(str(quest.get("status") or "draft"), fallback="draft") == "available":
        quest["status"] = "accepted"
    recompute_quest_lifecycle(quest)
    quest["updated_at"] = time.time()
    return True


def apply_dm_override(quest: dict, payload: dict) -> bool:
    action = str(payload.get("action") or "advance_objective").strip().lower()
    now = time.time()
    objectives = list(quest.get("objective_list") or [])
    objective_id = str(payload.get("objective_id") or "").strip()
    changed = False

    if action in {"complete_quest", "force_complete"}:
        for objective in objectives:
            required = max(1, int(objective.get("required_count") or 1))
            objective["current_count"] = required
            objective["status"] = "completed"
        quest["objective_list"] = objectives
        quest["status"] = "completed"
        changed = True
    elif action in {"fail_quest", "force_fail"}:
        quest["status"] = "failed"
        changed = True
    elif action in {"set_status", "set_quest_status"}:
        next_status = normalize_quest_status(str(payload.get("status") or "active"), fallback="active")
        quest["status"] = next_status
        changed = True
    elif action in {"advance_objective", "set_objective_status", "correct_objective"}:
        target = next((row for row in objectives if str(row.get("id") or "") == objective_id), None)
        if not target:
            return False
        if action == "set_objective_status":
            status = str(payload.get("status") or "active").strip().lower()
            if status in _ALLOWED_OBJECTIVE_STATUS:
                target["status"] = status
                required = max(1, int(target.get("required_count") or 1))
                if status == "completed":
                    target["current_count"] = required
                elif status == "pending":
                    target["current_count"] = 0
                changed = True
        else:
            required = max(1, int(target.get("required_count") or 1))
            delta = max(1, int(payload.get("delta") or 1))
            if action == "correct_objective" and payload.get("current_count") is not None:
                current = max(0, int(payload.get("current_count") or 0))
            else:
                current = max(0, int(target.get("current_count") or 0)) + delta
            target["current_count"] = min(required, current)
            target["status"] = "completed" if target["current_count"] >= required else "active"
            changed = True
        quest["objective_list"] = objectives

    if not changed:
        return False
    quest["progress"] = rebuild_progress(quest)
    recompute_quest_lifecycle(quest)
    quest["updated_at"] = now
    return True
