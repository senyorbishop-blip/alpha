from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.config import AppConfig
from server.auth import models as auth_models
from server.auth import dependencies as auth_dependencies
from server.auth import routes as auth_routes


def _auth_deps_status() -> tuple[bool, bool]:
    """Return (bcrypt_available, jwt_available) for healthy-install gating."""
    return auth_dependencies.load_bcrypt() is not None, auth_dependencies.load_jwt() is not None


def _require_healthy_auth_deps() -> None:
    """Skip healthy-install runtime tests when required auth deps are unavailable."""
    bcrypt_ok, jwt_ok = _auth_deps_status()
    missing: list[str] = []
    if not bcrypt_ok:
        missing.append("bcrypt")
    if not jwt_ok:
        missing.append("PyJWT")
    if missing:
        pytest.skip(f"Healthy auth runtime tests require installed dependencies: {', '.join(missing)}")


def _config(*, app_env: str, rate_limit_enabled: bool = False) -> AppConfig:
    return AppConfig(
        public_domain="",
        port=8000,
        ngrok_domain="",
        app_env=app_env,
        public_base_url="",
        trust_proxy_headers=False,
        auth_cookie_secure=False,
        auth_cookie_samesite="lax",
        auth_cookie_domain="",
        auth_cookie_name="dnd_session",
        auth_rate_limit_enabled=rate_limit_enabled,
        auth_rate_limit_window_seconds=300,
        auth_rate_limit_max_attempts=20,
        log_level="INFO",
        commercial_deployment_model="self_host",
        commercial_default_plan="community",
        support_contact_email="",
        support_portal_url="",
        legal_terms_url="",
        legal_privacy_url="",
        legal_dpa_url="",
        release_runbook_version="v1",
    )


def _build_client(tmp_path, monkeypatch, *, app_env: str = "development") -> TestClient:
    _require_healthy_auth_deps()
    db_path = tmp_path / "auth-reset.db"
    monkeypatch.setattr(auth_models, "DB_PATH", db_path)
    monkeypatch.setattr(auth_routes, "_APP_CONFIG", _config(app_env=app_env, rate_limit_enabled=False))
    auth_routes._RATE_LIMIT_BUCKETS.clear()

    app = FastAPI()
    auth_dependencies.install_auth_runtime(app)
    auth_models.init_auth_db()
    app.include_router(auth_routes.router)
    return TestClient(app, raise_server_exceptions=False)


def _register_user(client: TestClient, username: str, email: str, password: str = "oldpass123") -> None:
    res = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password, "role": "player"},
    )
    assert res.status_code == 201


def test_request_password_reset_valid_and_invalid_are_generic(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="production")
    _register_user(client, "alice", "alice@example.com")

    valid = client.post(
        "/api/auth/request-password-reset",
        json={"username": "alice", "email": "alice@example.com"},
    )
    invalid = client.post(
        "/api/auth/request-password-reset",
        json={"username": "alice", "email": "wrong@example.com"},
    )

    assert valid.status_code == 200
    assert invalid.status_code == 200
    assert valid.json()["message"] == invalid.json()["message"]
    assert "dev_reset_code" not in valid.json()
    assert "dev_reset_code" not in invalid.json()


def test_complete_password_reset_with_valid_token_changes_login_password(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="development")
    _register_user(client, "resetme", "resetme@example.com", password="old-password")

    req = client.post(
        "/api/auth/request-password-reset",
        json={"username": "resetme", "email": "resetme@example.com"},
    )
    token = req.json().get("dev_reset_code")
    assert token

    complete = client.post(
        "/api/auth/complete-password-reset",
        json={"username": "resetme", "token": token, "new_password": "new-password-123"},
    )
    assert complete.status_code == 200
    assert complete.status_code != 503

    old_login = client.post("/api/auth/login", json={"username_or_email": "resetme", "password": "old-password"})
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={"username_or_email": "resetme", "password": "new-password-123"})
    assert new_login.status_code == 200


def test_expired_token_fails(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="development")
    _register_user(client, "expireme", "expireme@example.com")

    req = client.post(
        "/api/auth/request-password-reset",
        json={"username": "expireme", "email": "expireme@example.com"},
    )
    token = req.json().get("dev_reset_code")
    assert token

    original_time = auth_models.time.time
    try:
        monkeypatch.setattr(auth_models.time, "time", lambda: original_time() + (60 * 60))
        expired = client.post(
            "/api/auth/complete-password-reset",
            json={"username": "expireme", "token": token, "new_password": "another-password"},
        )
    finally:
        monkeypatch.setattr(auth_models.time, "time", original_time)

    assert expired.status_code == 400
    assert "Invalid or expired reset token" in expired.json().get("detail", "")


def test_used_token_and_reuse_fail(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="development")
    _register_user(client, "once", "once@example.com")

    req = client.post(
        "/api/auth/request-password-reset",
        json={"username": "once", "email": "once@example.com"},
    )
    token = req.json().get("dev_reset_code")
    assert token

    first = client.post(
        "/api/auth/complete-password-reset",
        json={"username": "once", "token": token, "new_password": "newpass111"},
    )
    second = client.post(
        "/api/auth/complete-password-reset",
        json={"username": "once", "token": token, "new_password": "newpass222"},
    )

    assert first.status_code == 200
    assert second.status_code == 400


def test_wrong_username_token_pair_fails(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="development")
    _register_user(client, "alice", "alice@example.com")
    _register_user(client, "bob", "bob@example.com")

    req = client.post(
        "/api/auth/request-password-reset",
        json={"username": "alice", "email": "alice@example.com"},
    )
    token = req.json().get("dev_reset_code")
    assert token

    wrong_user_attempt = client.post(
        "/api/auth/complete-password-reset",
        json={"username": "bob", "token": token, "new_password": "bob-new-123"},
    )

    assert wrong_user_attempt.status_code == 400
    assert "Invalid or expired reset token" in wrong_user_attempt.json().get("detail", "")


def test_auth_routes_fail_closed_when_startup_contract_is_bypassed(tmp_path, monkeypatch):
    """Defensive fallback: routes must fail closed if auth runtime was not initialized."""
    db_path = tmp_path / "auth-reset.db"
    monkeypatch.setattr(auth_models, "DB_PATH", db_path)
    auth_models.init_auth_db()
    monkeypatch.setattr(auth_routes, "_APP_CONFIG", _config(app_env="development", rate_limit_enabled=False))
    auth_routes._RATE_LIMIT_BUCKETS.clear()

    app = FastAPI()
    app.include_router(auth_routes.router)
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "oldpass123", "role": "player"},
        )

    assert res.status_code == 503
    assert "auth runtime is not initialized" in res.json().get("detail", "").lower()


def test_validate_auth_dependencies_fails_when_bcrypt_missing(monkeypatch):
    original_import_module = importlib.import_module

    def _fake_import_module(name: str):
        if name == "bcrypt":
            raise ModuleNotFoundError("No module named 'bcrypt'")
        return original_import_module(name)

    monkeypatch.setattr(auth_dependencies.importlib, "import_module", _fake_import_module)

    with pytest.raises(RuntimeError) as exc_info:
        auth_dependencies.validate_auth_dependencies(require_bcrypt=True)

    message = str(exc_info.value)
    assert "missing required" in message
    assert "bcrypt" in message
    assert "pip install -r requirements.txt" in message


def test_validate_auth_dependencies_fails_when_jwt_missing(monkeypatch):
    """Startup validation must also reject a broken/missing PyJWT install."""
    original_import_module = importlib.import_module

    def _fake_import_module(name: str):
        if name == "jwt":
            raise ModuleNotFoundError("No module named 'jwt'")
        return original_import_module(name)

    monkeypatch.setattr(auth_dependencies.importlib, "import_module", _fake_import_module)

    with pytest.raises(RuntimeError) as exc_info:
        auth_dependencies.validate_auth_dependencies(require_bcrypt=True)

    message = str(exc_info.value)
    assert "missing required" in message
    assert "PyJWT" in message
    assert "pip install -r requirements.txt" in message


def test_validate_auth_dependencies_fails_when_both_missing(monkeypatch):
    """Both missing deps should be reported in a single error, not silently half-failing."""
    original_import_module = importlib.import_module

    def _fake_import_module(name: str):
        if name in ("bcrypt", "jwt"):
            raise ModuleNotFoundError(f"No module named '{name}'")
        return original_import_module(name)

    monkeypatch.setattr(auth_dependencies.importlib, "import_module", _fake_import_module)

    with pytest.raises(RuntimeError) as exc_info:
        auth_dependencies.validate_auth_dependencies(require_bcrypt=True)

    message = str(exc_info.value)
    assert "'bcrypt'" in message
    assert "'PyJWT'" in message
    assert "pip install -r requirements.txt" in message


def test_register_succeeds_with_healthy_auth_dependencies(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="development")

    res = client.post(
        "/api/auth/register",
        json={"username": "healthy", "email": "healthy@example.com", "password": "oldpass123", "role": "player"},
    )

    assert res.status_code == 201
    assert res.status_code != 503
    payload = res.json()
    assert payload.get("ok") is True


def test_lifespan_initializes_canonical_auth_runtime(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch, app_env="development")
    runtime = getattr(client.app.state, auth_dependencies.AUTH_RUNTIME_STATE_KEY, None)
    assert runtime is not None
    assert getattr(runtime, "bcrypt", None) is not None
    assert getattr(runtime, "jwt", None) is not None


def test_startup_fails_clearly_when_bcrypt_dependency_missing(monkeypatch):
    import main as app_main

    def _raise_missing_bcrypt(_app):
        raise RuntimeError(
            "Auth startup validation failed: missing required dependency 'bcrypt'. "
            "Install dependencies with 'pip install -r requirements.txt' and restart the server."
        )

    monkeypatch.setattr(app_main, "install_auth_runtime", _raise_missing_bcrypt)
    monkeypatch.setattr(app_main, "ensure_data_dirs", lambda: None)
    monkeypatch.setattr(app_main, "migrate_legacy_data", lambda: {"db_copied": False, "maps_copied": False})
    monkeypatch.setattr(app_main, "create_startup_backup", lambda: None)
    monkeypatch.setattr(app_main, "init_db", lambda: None)
    monkeypatch.setattr(app_main, "init_map_library_db", lambda: None)
    monkeypatch.setattr(app_main, "init_auth_db", lambda: None)
    monkeypatch.setattr(app_main, "ensure_ambient_audio_assets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_main, "maybe_start_ngrok", lambda: None)
    monkeypatch.setattr(app_main.threading, "Thread", lambda *args, **kwargs: type("NoopThread", (), {"start": lambda self: None})())

    with pytest.raises(RuntimeError) as exc_info:
        with TestClient(app_main.app):
            pass

    message = str(exc_info.value)
    assert "Startup aborted: required auth dependency check failed" in message
    assert "pip install -r requirements.txt" in message


def test_password_reset_request_and_completion_return_no_503_in_healthy_install(tmp_path, monkeypatch):
    """Full reset flow must not surface 503 when auth dependencies are present.

    This is the explicit healthy-environment contract: request-password-reset
    (which does NOT require bcrypt) and complete-password-reset (which DOES)
    both return success codes, never 503, on a standard install.
    """
    client = _build_client(tmp_path, monkeypatch, app_env="development")
    _register_user(client, "resetok", "resetok@example.com", password="initial-pass-1")

    # Step 1 — request reset token (no bcrypt needed; generic 200 expected)
    req = client.post(
        "/api/auth/request-password-reset",
        json={"username": "resetok", "email": "resetok@example.com"},
    )
    assert req.status_code == 200, f"Expected 200, got {req.status_code}"
    assert req.status_code != 503
    token = req.json().get("dev_reset_code")
    assert token, "dev_reset_code must be present in development mode"

    # Step 2 — complete reset (bcrypt needed; 200 expected)
    complete = client.post(
        "/api/auth/complete-password-reset",
        json={"username": "resetok", "token": token, "new_password": "new-pass-secure-1"},
    )
    assert complete.status_code == 200, f"Expected 200, got {complete.status_code}"
    assert complete.status_code != 503
    assert complete.json().get("ok") is True
