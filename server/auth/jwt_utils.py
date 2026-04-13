"""
server/auth/jwt_utils.py — JWT creation and verification helpers.
"""
import os
import secrets
import time

try:
    import jwt  # PyJWT
except BaseException as _jwt_import_err:  # noqa: BLE001 — pyo3 panics surface as BaseException
    raise ImportError(
        "Failed to import PyJWT — required for auth token handling. "
        "Install dependencies with 'pip install -r requirements.txt'. "
        f"Original error: {_jwt_import_err}"
    ) from _jwt_import_err

# Secret key — loaded from env or config, fallback generated on startup.
# Set DND_JWT_SECRET in the environment or config.txt for a stable key.
_JWT_SECRET: str = os.environ.get("DND_JWT_SECRET", "").strip()
if not _JWT_SECRET:
    # Try reading from the repo-level config.txt
    try:
        _cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.txt")
        with open(_cfg_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line.startswith("DND_JWT_SECRET="):
                    _JWT_SECRET = _line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

if not _JWT_SECRET:
    _JWT_SECRET = secrets.token_hex(32)
    print(
        "\n[WARNING] DND_JWT_SECRET is not set — a temporary key has been generated for this session.\n"
        "          All existing login sessions will be invalidated on the next restart.\n"
        "          To make it permanent, add this line to your config.txt or .env file:\n"
        f"          DND_JWT_SECRET={_JWT_SECRET}\n"
    )

_ALGORITHM = "HS256"
_TOKEN_TTL = 60 * 60 * 24 * 7  # 7 days

# Admin host key for the /admin/reset-password endpoint.
ADMIN_HOST_KEY: str = os.environ.get("DND_ADMIN_KEY", "").strip()
if not ADMIN_HOST_KEY:
    try:
        _cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.txt")
        with open(_cfg_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line.startswith("DND_ADMIN_KEY="):
                    ADMIN_HOST_KEY = _line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

if not ADMIN_HOST_KEY:
    ADMIN_HOST_KEY = secrets.token_hex(16)
    print(
        "\n[WARNING] DND_ADMIN_KEY is not set — a temporary key has been generated for this session.\n"
        "          To make it permanent, add this line to your config.txt or .env file:\n"
        f"          DND_ADMIN_KEY={ADMIN_HOST_KEY}\n"
    )


def create_token(user_id: str, username: str, role: str) -> str:
    """Create a signed JWT for the given user."""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + _TOKEN_TTL,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify and decode a JWT. Returns the payload dict or None on failure."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
