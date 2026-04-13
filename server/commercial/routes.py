"""Commercial/account endpoints for plan + entitlement visibility.

These routes keep commercial concerns out of gameplay handlers and WS flows.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from server.auth.jwt_utils import ADMIN_HOST_KEY
from server.auth.models import get_user_by_id, upsert_user_entitlement
from server.commercial.service import build_commercial_context
from server.config import load_config
from server.http.auth import get_request_user

router = APIRouter()
_CONFIG = load_config()


@router.get("/api/account/commercial-context")
async def account_commercial_context(request: Request):
    if _CONFIG.commercial_deployment_model == "self_host":
        raise HTTPException(status_code=404, detail="Commercial features are not active in this deployment.")
    user = get_request_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse({"ok": True, "context": build_commercial_context(user, _CONFIG)})


@router.patch("/admin/commercial/entitlements/{user_id}")
async def admin_upsert_entitlement(user_id: str, request: Request):
    provided_key = request.headers.get("X-Admin-Key", "").strip()
    if not provided_key or provided_key != ADMIN_HOST_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    target_user = get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    plan_code = str(body.get("plan_code") or "").strip().lower()
    if plan_code not in {"community", "pro", "studio"}:
        raise HTTPException(status_code=400, detail="plan_code must be one of: community, pro, studio")

    upsert_user_entitlement(
        user_id=user_id,
        plan_code=plan_code,
        subscription_status=str(body.get("subscription_status") or "active").strip().lower(),
        subscription_provider=str(body.get("subscription_provider") or "manual").strip().lower(),
        subscription_ref=str(body.get("subscription_ref") or "").strip(),
        support_tier=str(body.get("support_tier") or "").strip().lower(),
        feature_overrides=body.get("feature_overrides") if isinstance(body.get("feature_overrides"), dict) else {},
        effective_at=body.get("effective_at"),
        expires_at=body.get("expires_at"),
        updated_by="admin_api",
    )

    refreshed = get_user_by_id(user_id)
    return JSONResponse({"ok": True, "user_id": user_id, "context": build_commercial_context(refreshed or {}, _CONFIG)})
