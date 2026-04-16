"""Shared summon/deployment diagnostics and health helpers (Pass L hardening)."""
from __future__ import annotations

import copy
import time
from typing import Any

from server.session import Session

_FAILURE_CATEGORY_BY_CODE: dict[str, str] = {
    "template_not_found": "template_resolution_failure",
    "invalid_variant": "illegal_variant_selection",
    "summon_not_unlocked": "missing_summon_unlock",
    "spell_not_available": "missing_summon_unlock",
    "missing_map_context": "missing_scene_map_context",
    "token_spawn_failed": "token_spawn_failure",
    "ownership_assignment_failed": "ownership_control_assignment_failure",
    "stale_active_conflict": "stale_active_state_conflict",
    "profile_not_found": "restore_rebind_failure",
    "missing_native_character": "restore_rebind_failure",
    "runtime_not_live_for_class": "unsupported_non_live_deployment_path",
    "register_active_failed": "lifecycle_cleanup_failure",
    "unknown_action": "unsupported_non_live_deployment_path",
}


def classify_failure(code: str) -> str:
    key = str(code or "unknown_failure").strip().lower()
    return _FAILURE_CATEGORY_BY_CODE.get(key, "unknown_failure")


def build_failure(*, code: str, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "category": classify_failure(code),
        "code": str(code or "unknown_failure").strip().lower() or "unknown_failure",
        "message": str(message or "Deployment request failed."),
        "context": copy.deepcopy(context or {}),
        "timestamp": time.time(),
    }
    return payload


def _summon_runtime_store(session: Session) -> dict[str, Any]:
    world_state = dict(getattr(session, "world_state", {}) or {})
    store = world_state.get("summon_runtime") if isinstance(world_state.get("summon_runtime"), dict) else {}
    metrics = store.get("metrics") if isinstance(store.get("metrics"), dict) else {}
    metrics.setdefault("deploy_success", 0)
    metrics.setdefault("deploy_failure", 0)
    metrics.setdefault("restore_success", 0)
    metrics.setdefault("restore_failure", 0)
    metrics.setdefault("cleanup_count", 0)
    metrics.setdefault("quarantined_count", 0)
    metrics.setdefault("failure_by_category", {})
    metrics.setdefault("failure_by_family", {})
    store["metrics"] = metrics
    world_state["summon_runtime"] = store
    session.world_state = world_state
    return store


def increment_metric(session: Session, key: str, *, amount: int = 1) -> None:
    store = _summon_runtime_store(session)
    metrics = store.get("metrics") if isinstance(store.get("metrics"), dict) else {}
    metrics[key] = int(metrics.get(key) or 0) + max(1, int(amount or 1))
    store["metrics"] = metrics


def record_failure_metric(session: Session, *, failure: dict[str, Any], family: str = "") -> None:
    store = _summon_runtime_store(session)
    metrics = store.get("metrics") if isinstance(store.get("metrics"), dict) else {}
    failure_by_category = metrics.get("failure_by_category") if isinstance(metrics.get("failure_by_category"), dict) else {}
    failure_by_family = metrics.get("failure_by_family") if isinstance(metrics.get("failure_by_family"), dict) else {}

    category = str((failure or {}).get("category") or "unknown_failure")
    failure_by_category[category] = int(failure_by_category.get(category) or 0) + 1
    metrics["failure_by_category"] = failure_by_category

    family_key = str(family or "unknown").strip().lower() or "unknown"
    family_bucket = failure_by_family.get(family_key) if isinstance(failure_by_family.get(family_key), dict) else {}
    family_bucket[category] = int(family_bucket.get(category) or 0) + 1
    failure_by_family[family_key] = family_bucket
    metrics["failure_by_family"] = failure_by_family
    store["metrics"] = metrics


def metrics_snapshot(session: Session) -> dict[str, Any]:
    store = _summon_runtime_store(session)
    metrics = store.get("metrics") if isinstance(store.get("metrics"), dict) else {}
    return copy.deepcopy(metrics)


def build_entry_breadcrumb(*, action: str, ok: bool, detail: str = "", failure: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {
        "action": str(action or "unknown").strip().lower() or "unknown",
        "ok": bool(ok),
        "detail": str(detail or "").strip(),
        "timestamp": time.time(),
    }
    if isinstance(failure, dict) and failure:
        out["failure"] = {
            "category": str(failure.get("category") or ""),
            "code": str(failure.get("code") or ""),
            "message": str(failure.get("message") or ""),
        }
    return out
