"""
server/auth/routes.py — FastAPI router for all /api/auth/* and /admin/* endpoints.
"""
import time
import logging
from collections import defaultdict, deque
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse

from server.auth.jwt_utils import create_token, verify_token, ADMIN_HOST_KEY
from server.auth.dependencies import AuthRuntime, get_auth_runtime
from server.config import load_config
from server.auth.models import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    get_user_by_username_or_email,
    update_last_login,
    update_password,
    safe_user,
    add_reset_request,
    list_reset_requests,
    resolve_reset_request,
    create_password_reset_token,
    consume_password_reset_token,
    prune_password_reset_tokens,
    migrate_campaigns_to_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_APP_CONFIG = load_config()
_COOKIE_NAME = _APP_CONFIG.auth_cookie_name
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
# Prune stale rate-limit keys periodically to prevent unbounded memory growth.
_RATE_LIMIT_LAST_PRUNE: float = 0.0
_RATE_LIMIT_PRUNE_INTERVAL = 600  # seconds between prune sweeps (10 min)
_PASSWORD_RESET_TOKEN_TTL_SECONDS = 20 * 60
_PASSWORD_RESET_GENERIC_MESSAGE = "If the details match an account, a reset code has been issued."


def _hash_password(password: str, auth_runtime: AuthRuntime) -> str:
    return auth_runtime.bcrypt.hashpw(password.encode("utf-8"), auth_runtime.bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str, auth_runtime: AuthRuntime) -> bool:
    return auth_runtime.bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _should_use_secure_cookie(request: Request) -> bool:
    if _APP_CONFIG.auth_cookie_secure:
        return True
    if _APP_CONFIG.trust_proxy_headers:
        forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        if forwarded_proto == "https":
            return True
    return str(request.url.scheme).lower() == "https"


def _prune_rate_limit_buckets(now: float, window_seconds: float) -> None:
    """Remove expired rate-limit buckets to prevent unbounded memory growth."""
    global _RATE_LIMIT_LAST_PRUNE
    if now - _RATE_LIMIT_LAST_PRUNE < _RATE_LIMIT_PRUNE_INTERVAL:
        return
    _RATE_LIMIT_LAST_PRUNE = now
    stale_keys = [k for k, bucket in _RATE_LIMIT_BUCKETS.items() if not bucket or (now - bucket[0]) > window_seconds]
    for k in stale_keys:
        del _RATE_LIMIT_BUCKETS[k]


def _enforce_rate_limit(request: Request, scope: str) -> None:
    if not _APP_CONFIG.auth_rate_limit_enabled:
        return

    forwarded_for = ""
    if _APP_CONFIG.trust_proxy_headers:
        forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
    key = f"{scope}:{client_ip.lower()[:128]}"

    now = time.time()
    window_seconds = _APP_CONFIG.auth_rate_limit_window_seconds
    max_attempts = _APP_CONFIG.auth_rate_limit_max_attempts
    _prune_rate_limit_buckets(now, window_seconds)
    bucket = _RATE_LIMIT_BUCKETS[key]
    while bucket and (now - bucket[0]) > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_attempts:
        retry_after = max(1, int(window_seconds - (now - bucket[0])))
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Please retry in about {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)


def _request_ip(request: Request) -> str:
    if _APP_CONFIG.trust_proxy_headers:
        forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if forwarded_for:
            return forwarded_for
    return request.client.host if request.client else "unknown"


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=_COOKIE_MAX_AGE,
        samesite=_APP_CONFIG.auth_cookie_samesite,
        secure=_should_use_secure_cookie(request),
        domain=_APP_CONFIG.auth_cookie_domain or None,
    )


def _get_current_user(request: Request) -> Optional[dict]:
    """Extract and verify the JWT from cookie or Authorization header."""
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    return get_user_by_id(payload["sub"])


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/api/auth/register")
async def register(request: Request, auth_runtime: AuthRuntime = Depends(get_auth_runtime)):
    _enforce_rate_limit(request, "register")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    role = (body.get("role") or "player").strip().lower()

    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="username, email, and password are required")
    if role not in ("dm", "player", "viewer"):
        raise HTTPException(status_code=400, detail="role must be dm, player, or viewer")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be 72 bytes or fewer")

    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username already taken")
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = _hash_password(password, auth_runtime)
    user = create_user(username, email, password_hash, role)

    # Legacy migration — link any unclaimed campaigns that match this username
    migrated_count = 0
    if role == "dm":
        migrated_count = migrate_campaigns_to_user(username, user["id"])

    token = create_token(user["id"], user["username"], user["role"])
    resp = JSONResponse({
        "ok": True,
        "user": safe_user(user),
        "migrated": migrated_count > 0,
        "migrated_campaigns": migrated_count,
        "token": token,
    }, status_code=201)
    _set_session_cookie(request, resp, token)
    return resp


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/api/auth/login")
async def login(request: Request, auth_runtime: AuthRuntime = Depends(get_auth_runtime)):
    _enforce_rate_limit(request, "login")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    identifier = (body.get("username_or_email") or "").strip()
    password = body.get("password") or ""

    if not identifier or not password:
        raise HTTPException(status_code=400, detail="username_or_email and password are required")

    user = get_user_by_username_or_email(identifier)
    if not user or not _verify_password(password, user["password_hash"], auth_runtime):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    update_last_login(user["id"])
    token = create_token(user["id"], user["username"], user["role"])
    resp = JSONResponse({"ok": True, "user": safe_user(user), "token": token})
    _set_session_cookie(request, resp, token)
    return resp


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/api/auth/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(_COOKIE_NAME, domain=_APP_CONFIG.auth_cookie_domain or None)
    return resp


# ── Current user ──────────────────────────────────────────────────────────────

@router.get("/api/auth/me")
async def me(request: Request):
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse({"ok": True, "user": safe_user(user)})


# ── Find account (username lookup by email) ───────────────────────────────────

@router.post("/api/auth/find-id")
async def find_id(request: Request):
    _enforce_rate_limit(request, "find_id")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    email = (body.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    user = get_user_by_email(email)
    if not user:
        # Queue a reset request so the host knows someone looked up this email
        add_reset_request("unknown", email)
        # Return a generic message to avoid account enumeration
        return JSONResponse({"ok": True, "message": "If that email is registered, the host will be notified."})

    add_reset_request(user["username"], email)
    return JSONResponse({
        "ok": True,
        "username": user["username"],
        "message": "Your username has been found. Contact the host to reset your password.",
    })


# ── Self-service password reset (token-based) ────────────────────────────────

@router.post("/api/auth/request-password-reset")
async def request_password_reset(request: Request):
    _enforce_rate_limit(request, "request_password_reset")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    if not username or not email:
        raise HTTPException(status_code=400, detail="username and email are required")

    user = get_user_by_username(username)
    created_token: Optional[str] = None

    if user and str(user.get("email") or "").lower() == email:
        created_token = create_password_reset_token(
            user["id"],
            user["username"],
            ttl_seconds=_PASSWORD_RESET_TOKEN_TTL_SECONDS,
            request_ip=_request_ip(request),
            request_user_agent=request.headers.get("user-agent", ""),
            delivery_method="dev_in_app" if _APP_CONFIG.app_env == "development" else "manual",
        )
        # Keep manual admin backlog behavior for host visibility/backward compat.
        add_reset_request(user["username"], email)
    else:
        add_reset_request("unknown", email)

    prune_password_reset_tokens()

    payload: dict = {"ok": True, "message": _PASSWORD_RESET_GENERIC_MESSAGE}
    if _APP_CONFIG.app_env == "development" and created_token:
        payload["dev_reset_code"] = created_token
        payload["expires_in_minutes"] = int(_PASSWORD_RESET_TOKEN_TTL_SECONDS / 60)
    return JSONResponse(payload)


@router.post("/api/auth/complete-password-reset")
async def complete_password_reset(request: Request, auth_runtime: AuthRuntime = Depends(get_auth_runtime)):
    _enforce_rate_limit(request, "complete_password_reset")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    username = (body.get("username") or "").strip()
    token = (body.get("token") or "").strip()
    new_password = body.get("new_password") or ""
    if not username or not token or not new_password:
        raise HTTPException(status_code=400, detail="username, token, and new_password are required")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be 72 bytes or fewer")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    consumed = consume_password_reset_token(user["id"], token)
    if not consumed:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    update_password(user["id"], _hash_password(new_password, auth_runtime))
    resolve_reset_request(username)
    return JSONResponse({"ok": True, "message": "Password reset successful. You can now log in."})


# ── Admin: reset password ─────────────────────────────────────────────────────

@router.patch("/admin/reset-password")
async def admin_reset_password(request: Request, auth_runtime: AuthRuntime = Depends(get_auth_runtime)):
    # Require host secret key
    provided_key = request.headers.get("X-Admin-Key", "").strip()
    if not provided_key or provided_key != ADMIN_HOST_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    username = (body.get("username") or "").strip()
    new_password = body.get("new_password") or ""

    if not username or not new_password:
        raise HTTPException(status_code=400, detail="username and new_password are required")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be 72 bytes or fewer")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_password(user["id"], _hash_password(new_password, auth_runtime))
    resolve_reset_request(username)
    return JSONResponse({"ok": True, "message": f"Password updated for {username}"})


# ── Admin: list reset requests ────────────────────────────────────────────────

@router.get("/admin/reset-requests")
async def admin_list_reset_requests(request: Request, resolved: bool = False):
    provided_key = request.headers.get("X-Admin-Key", "").strip()
    if not provided_key or provided_key != ADMIN_HOST_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return JSONResponse({"ok": True, "requests": list_reset_requests(resolved=resolved)})
