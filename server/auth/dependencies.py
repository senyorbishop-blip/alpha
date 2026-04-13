"""Auth dependency probes and startup/runtime provider helpers."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from types import ModuleType

from fastapi import HTTPException, Request
from fastapi import status as http_status
from fastapi import FastAPI

logger = logging.getLogger(__name__)
AUTH_RUNTIME_STATE_KEY = "auth_runtime"


def load_bcrypt() -> ModuleType | None:
    """Attempt to import bcrypt; return None when unavailable."""
    try:
        return importlib.import_module("bcrypt")
    except ModuleNotFoundError:
        return None


def load_jwt() -> ModuleType | None:
    """Attempt to import jwt (PyJWT); return None when unavailable or broken.

    Uses a broad BaseException catch because a broken cffi/cryptography stack
    can cause the jwt module to raise a pyo3_runtime.PanicException (a Rust
    panic surfaced as a Python BaseException subclass) rather than a plain
    ImportError.
    """
    try:
        return importlib.import_module("jwt")
    except BaseException:  # noqa: BLE001 — intentional broad catch for pyo3 panics
        return None


@dataclass(frozen=True)
class AuthRuntime:
    """Resolved auth dependency bundle shared by all auth routes."""

    bcrypt: ModuleType
    jwt: ModuleType


def validate_auth_dependencies(*, require_bcrypt: bool = True) -> dict[str, bool]:
    """Validate auth-critical dependencies and raise with remediation guidance."""
    bcrypt_module = load_bcrypt()
    jwt_module = load_jwt()

    status = {"bcrypt": bcrypt_module is not None, "jwt": jwt_module is not None}

    missing: list[str] = []
    if require_bcrypt and not status["bcrypt"]:
        missing.append("bcrypt")
    # jwt (PyJWT) is always required — auth tokens cannot be issued without it.
    if not status["jwt"]:
        missing.append("PyJWT")

    if missing:
        dep_word = "dependency" if len(missing) == 1 else "dependencies"
        missing_quoted = ", ".join(f"'{m}'" for m in missing)
        raise RuntimeError(
            f"Auth startup validation failed: missing required {dep_word} {missing_quoted}. "
            "Install dependencies with 'pip install -r requirements.txt' and restart the server."
        )

    return status


def log_auth_dependency_summary() -> dict[str, bool]:
    """Validate + log a concise auth dependency readiness summary."""
    status = validate_auth_dependencies(require_bcrypt=True)
    logger.info(
        "[AUTH] dependency_check bcrypt=%s jwt=%s",
        "loaded" if status["bcrypt"] else "missing",
        "loaded" if status["jwt"] else "missing",
    )
    return status


def build_auth_runtime() -> AuthRuntime:
    """Resolve and return the canonical auth runtime provider."""
    validate_auth_dependencies(require_bcrypt=True)
    bcrypt_module = load_bcrypt()
    jwt_module = load_jwt()
    if bcrypt_module is None or jwt_module is None:
        # Defensive invariant check: validate_auth_dependencies should have raised.
        raise RuntimeError("Auth runtime could not be initialized due to missing dependencies.")
    return AuthRuntime(bcrypt=bcrypt_module, jwt=jwt_module)


def install_auth_runtime(app: FastAPI) -> AuthRuntime:
    """Initialize and store auth runtime provider on app state."""
    runtime = build_auth_runtime()
    setattr(app.state, AUTH_RUNTIME_STATE_KEY, runtime)
    logger.info("[AUTH] runtime initialized and attached to app.state.%s", AUTH_RUNTIME_STATE_KEY)
    return runtime


def get_auth_runtime(request: Request) -> AuthRuntime:
    """Return initialized auth runtime provider for request handlers."""
    runtime = getattr(request.app.state, AUTH_RUNTIME_STATE_KEY, None)
    if runtime is None:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Auth runtime is not initialized. "
                "Ensure the app is created with startup/lifespan auth initialization."
            ),
        )
    return runtime
