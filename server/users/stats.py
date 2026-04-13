"""
server/users/stats.py — Character stat persistence endpoints.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from server.auth.jwt_utils import verify_token
from server.auth.models import get_user_by_id, get_user_stats, upsert_user_stats

router = APIRouter()

_COOKIE_NAME = "dnd_session"


def _get_auth_user(request: Request):
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


@router.get("/api/users/me/stats")
async def get_my_stats(request: Request):
    user = _get_auth_user(request)
    stats = get_user_stats(user["id"])
    return JSONResponse({"ok": True, "stats": stats or {}})


@router.patch("/api/users/me/stats")
async def update_my_stats(request: Request):
    user = _get_auth_user(request)
    if user["role"] == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot update stats")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    upsert_user_stats(user["id"], body)
    stats = get_user_stats(user["id"])
    return JSONResponse({"ok": True, "stats": stats or {}})
