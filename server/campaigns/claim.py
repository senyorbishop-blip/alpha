"""
server/campaigns/claim.py — Campaign claiming logic and ownership endpoints.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from server.auth.jwt_utils import verify_token
from server.auth.models import (
    list_my_campaigns,
    list_unclaimed_campaigns,
    claim_campaign,
    get_user_by_id,
)

router = APIRouter()

_COOKIE_NAME = "dnd_session"


def _get_auth_user(request: Request):
    """Return user dict from JWT or raise 401."""
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── My campaigns ──────────────────────────────────────────────────────────────

@router.get("/api/campaigns/mine")
async def api_my_campaigns(request: Request):
    user = _get_auth_user(request)
    return JSONResponse({"ok": True, "campaigns": list_my_campaigns(user["id"])})


# ── Unclaimed (shared pool) campaigns ────────────────────────────────────────

@router.get("/api/campaigns/unclaimed")
async def api_unclaimed_campaigns(request: Request):
    user = _get_auth_user(request)
    if user["role"] not in ("dm",):
        raise HTTPException(status_code=403, detail="DM role required")
    return JSONResponse({"ok": True, "campaigns": list_unclaimed_campaigns()})


# ── Claim a campaign ──────────────────────────────────────────────────────────

@router.patch("/api/campaigns/{campaign_id}/claim")
async def api_claim_campaign(campaign_id: str, request: Request):
    user = _get_auth_user(request)
    if user["role"] != "dm":
        raise HTTPException(status_code=403, detail="DM role required to claim campaigns")

    success = claim_campaign(campaign_id, user["id"], user["username"])
    if not success:
        raise HTTPException(
            status_code=409,
            detail="This campaign was just claimed by another DM.",
        )

    # Broadcast to all WebSocket clients so other DMs can update their UI
    # We broadcast to all sessions — the frontend filters by event type.
    try:
        import asyncio
        from server.connections import manager as ws_manager
        # Broadcast to every active session
        # Broadcast to every active session
        event = {
            "type": "campaign_claimed",
            "payload": {
                "campaign_id": campaign_id,
                "claimed_by": user["username"],
            },
        }
        for sid in ws_manager.get_active_session_ids():
            asyncio.create_task(ws_manager.broadcast(sid, event))
    except Exception:
        pass  # WS broadcast failure must not fail the HTTP response

    return JSONResponse({
        "ok": True,
        "campaign_id": campaign_id,
        "claimed_by": user["username"],
    })
