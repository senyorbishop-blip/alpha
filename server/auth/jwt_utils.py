"""
server/auth/jwt_utils.py — JWT creation and verification helpers.
"""
import logging
import os
import secrets
import time
from pathlib import Path

try:
    import jwt  # PyJWT
except BaseException as _jwt_import_err:  # noqa: BLE001 — pyo3 panics surface as BaseException
    raise ImportError(
        "Failed to import PyJWT — required for auth token handling. "
        "Install dependencies with 'pip install -r requirements.txt'. "
        f"Original error: {_jwt_import_err}"
    ) from _jwt_import_err

_logger = logging.getLogger(__name__)

# Resolve the repo root from this file's location (server/auth/jwt_utils.py)
# rather than the process cwd, so config.txt is found regardless of how/where
# the server was launched from. config.txt is limited to non-secret settings.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _REPO_ROOT / "config.txt"
# Dev-only: persists an auto-generated secret so it survives restarts instead
# of silently invalidating every issued cookie/token each time.
_DEV_SECRET_FILE = _REPO_ROOT / ".dnd_jwt_secret.local"
_SECRET_CONFIG_KEYS = {"DND_JWT_SECRET", "DND_ADMIN_KEY"}


def _read_config_value(path: Path, key: str) -> str:
    if key in _SECRET_CONFIG_KEYS:
        return ""
    try:
        with path.open() as handle:
            for line in handle:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


def _resolve_app_env() -> str:
    env = os.environ.get("APP_ENV", "").strip().lower()
    if not env:
        env = _read_config_value(_CONFIG_PATH, "APP_ENV").strip().lower()
    return env if env in {"development", "production"} else "development"


def _persist_dev_secret(secret: str) -> None:
    try:
        _DEV_SECRET_FILE.write_text(secret + "\n", encoding="utf-8")
    except OSError:
        pass


def _load_jwt_secret() -> str:
    """Load the JWT signing secret, preferring stable sources over randomness.

    Order: DND_JWT_SECRET env var -> (non-development: fail fast) ->
    (development: reuse a previously persisted auto-generated secret, or
    generate+persist a new one). config.txt is intentionally not a secret
    source.
    """
    secret = os.environ.get("DND_JWT_SECRET", "").strip()
    if secret:
        return secret

    app_env = _resolve_app_env()
    if app_env != "development":
        raise RuntimeError(
            "DND_JWT_SECRET is not set. Refusing to start in a non-development "
            "environment (APP_ENV="
            f"{app_env}) with an auto-generated secret, since that would "
            "silently invalidate every issued session on the next restart. "
            "Set DND_JWT_SECRET in the environment or .env."
        )

    try:
        existing = _DEV_SECRET_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        _logger.warning(
            "DND_JWT_SECRET is not set — reusing the development secret persisted "
            "at %s. Set DND_JWT_SECRET in the environment or .env before deploying.",
            _DEV_SECRET_FILE,
        )
        return existing

    generated = secrets.token_hex(32)
    _persist_dev_secret(generated)
    _logger.warning(
        "DND_JWT_SECRET is not set — generated a new development-only secret and "
        "persisted it to %s so it survives restarts. Set DND_JWT_SECRET in "
        "the environment or .env before deploying.",
        _DEV_SECRET_FILE,
    )
    return generated


# Secret key — loaded from env or development fallback; config.txt is not a
# secret source.
_JWT_SECRET: str = _load_jwt_secret()

_ALGORITHM = "HS256"
_TOKEN_TTL = 60 * 60 * 24 * 7  # 7 days

# Admin host key for the /admin/reset-password endpoint.
ADMIN_HOST_KEY: str = os.environ.get("DND_ADMIN_KEY", "").strip()

if not ADMIN_HOST_KEY:
    ADMIN_HOST_KEY = secrets.token_hex(16)
    print(
        "\n[WARNING] DND_ADMIN_KEY is not set — a temporary key has been generated for this session.\n"
        "          To make it permanent, set DND_ADMIN_KEY in your environment or .env file.\n"
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
