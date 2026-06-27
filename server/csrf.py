"""CSRF protection middleware using the double-submit cookie pattern.

On every GET/HEAD/OPTIONS response the middleware ensures a `csrf_token`
cookie is present (generating a fresh one if absent).  For all other
(state-changing) requests it requires the token to be echoed back in an
`X-CSRF-Token` request header, and compares it against the cookie value
using a constant-time comparison to prevent timing attacks.

WebSocket upgrade requests are exempt because:
  1. The browser enforces the same-origin policy for WebSocket handshakes.
  2. Custom headers cannot be sent during a WebSocket upgrade, so the
     normal token-in-header check would break legitimate connections.
"""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF middleware for FastAPI / Starlette."""

    def __init__(self, app, *, cookie_secure: bool = False, cookie_samesite: str = "lax", exempt_prefixes: tuple[str, ...] = ()) -> None:
        super().__init__(app)
        self._cookie_secure = cookie_secure
        self._cookie_samesite = cookie_samesite
        # Path prefixes exempt from the double-submit token check. Intended for
        # endpoints authenticated by another signed credential that are called
        # cross-origin and therefore cannot carry our CSRF cookie/header (e.g.
        # the Twitch Extension EBS, secured by Twitch-signed Extension JWTs).
        self._exempt_prefixes = tuple(exempt_prefixes)

    async def dispatch(self, request: Request, call_next):
        # WebSocket upgrade requests are exempt – browsers enforce same-origin
        # for WS handshakes and custom headers cannot be sent during the upgrade.
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Exempt configured path prefixes (authenticated by another signed token).
        if self._exempt_prefixes and request.url.path.startswith(self._exempt_prefixes):
            return await call_next(request)

        if request.method in _SAFE_METHODS:
            response = await call_next(request)
            # Ensure the token cookie exists so the next mutation can read it.
            if CSRF_COOKIE_NAME not in request.cookies:
                response.set_cookie(
                    CSRF_COOKIE_NAME,
                    secrets.token_hex(32),
                    httponly=False,  # JS must be able to read this cookie
                    samesite=self._cookie_samesite,
                    secure=self._cookie_secure,
                    path="/",
                )
            return response

        # --- State-changing request: validate the double-submit token ---
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
        header_token = request.headers.get(CSRF_HEADER_NAME, "")

        if not cookie_token or not header_token:
            return JSONResponse(
                {"ok": False, "error": "CSRF token missing"},
                status_code=403,
            )

        if not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(
                {"ok": False, "error": "CSRF token invalid"},
                status_code=403,
            )

        return await call_next(request)
