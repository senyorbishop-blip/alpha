"""Commercial service layer.

This module intentionally keeps billing/provider logic out of gameplay handlers.
It provides a stable seam for account-level plan and entitlement resolution.
"""

from __future__ import annotations

import time
from copy import deepcopy

from server.auth.models import get_user_entitlement
from server.config import AppConfig


_PLAN_CATALOG: dict[str, dict] = {
    "community": {
        "display_name": "Community",
        "caps": {
            "max_campaigns_owned": 3,
            "max_concurrent_players_per_session": 8,
            "max_uploaded_assets": 100,
        },
        "features": {
            "premium_tts": False,
            "priority_map_generation": False,
            "api_access": False,
            "session_analytics": False,
        },
        "support_tier": "community",
    },
    "pro": {
        "display_name": "Pro",
        "caps": {
            "max_campaigns_owned": 20,
            "max_concurrent_players_per_session": 25,
            "max_uploaded_assets": 500,
        },
        "features": {
            "premium_tts": True,
            "priority_map_generation": True,
            "api_access": False,
            "session_analytics": True,
        },
        "support_tier": "email",
    },
    "studio": {
        "display_name": "Studio",
        "caps": {
            "max_campaigns_owned": 100,
            "max_concurrent_players_per_session": 50,
            "max_uploaded_assets": 2500,
        },
        "features": {
            "premium_tts": True,
            "priority_map_generation": True,
            "api_access": True,
            "session_analytics": True,
        },
        "support_tier": "priority",
    },
}


def _as_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _default_plan_for_role(role: str | None, config: AppConfig) -> str:
    configured = (config.commercial_default_plan or "community").strip().lower()
    if configured in _PLAN_CATALOG:
        return configured
    if (role or "").strip().lower() == "dm":
        return "pro"
    return "community"


def _normalize_plan_code(plan_code: str | None, role: str | None, config: AppConfig) -> str:
    code = (plan_code or "").strip().lower()
    if code in _PLAN_CATALOG:
        return code
    return _default_plan_for_role(role, config)


def _apply_overrides(plan: dict, overrides: dict) -> dict:
    merged = deepcopy(plan)
    caps = overrides.get("caps") if isinstance(overrides, dict) else None
    features = overrides.get("features") if isinstance(overrides, dict) else None
    if isinstance(caps, dict):
        merged["caps"].update(caps)
    if isinstance(features, dict):
        merged["features"].update({k: _as_bool(v) for k, v in features.items()})
    return merged


def resolve_user_entitlements(user: dict, config: AppConfig) -> dict:
    """Resolve an account's commercial entitlements.

    Order of precedence:
      1) explicit per-user entitlement override row
      2) configured default plan
      3) conservative role-based fallback
    """
    role = str(user.get("role") or "player").lower()
    record = get_user_entitlement(str(user.get("id") or "")) if user.get("id") else None

    plan_code = _normalize_plan_code((record or {}).get("plan_code"), role, config)
    base_plan = deepcopy(_PLAN_CATALOG[plan_code])
    merged_plan = _apply_overrides(base_plan, (record or {}).get("feature_overrides") or {})

    support_tier = (record or {}).get("support_tier") or merged_plan["support_tier"]
    subscription_status = (record or {}).get("subscription_status") or "inactive"
    if not record and plan_code == "community":
        subscription_status = "self_host"

    return {
        "plan_code": plan_code,
        "plan_name": merged_plan["display_name"],
        "subscription_status": subscription_status,
        "subscription_provider": (record or {}).get("subscription_provider") or "manual",
        "support_tier": support_tier,
        "caps": merged_plan["caps"],
        "features": merged_plan["features"],
        "expires_at": (record or {}).get("expires_at"),
        "effective_at": (record or {}).get("effective_at"),
        "resolved_at": time.time(),
        "source": "account_override" if record else "default_plan",
    }


def build_commercial_context(user: dict, config: AppConfig) -> dict:
    entitlements = resolve_user_entitlements(user, config)
    return {
        "deployment_model": config.commercial_deployment_model,
        "entitlements": entitlements,
        "support": {
            "email": config.support_contact_email,
            "url": config.support_portal_url,
            "runbook_version": config.release_runbook_version,
        },
        "legal": {
            "terms_url": config.legal_terms_url,
            "privacy_url": config.legal_privacy_url,
            "dpa_url": config.legal_dpa_url,
            "license_file": "LICENSE.txt",
        },
    }
