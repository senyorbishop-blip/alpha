from types import SimpleNamespace

from fastapi import HTTPException

from server import config as app_config
from server.auth import routes as auth_routes


class _DummyURL:
    def __init__(self, scheme: str = "http"):
        self.scheme = scheme


class _DummyRequest:
    def __init__(self, *, headers=None, scheme: str = "http", client_ip: str = "127.0.0.1"):
        self.headers = headers or {}
        self.url = _DummyURL(scheme)
        self.client = SimpleNamespace(host=client_ip)


def test_load_config_production_defaults_enable_safer_auth(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("AUTH_COOKIE_SAMESITE", raising=False)
    monkeypatch.delenv("AUTH_RATE_LIMIT_ENABLED", raising=False)

    cfg = app_config.load_config("does-not-exist.txt")

    assert cfg.is_production is True
    assert cfg.auth_cookie_secure is True
    assert cfg.auth_cookie_samesite == "strict"
    assert cfg.auth_rate_limit_enabled is True


def test_secure_cookie_uses_forwarded_proto_when_trusted(monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "_APP_CONFIG",
        app_config.AppConfig(
            public_domain="",
            port=8000,
            ngrok_domain="",
            app_env="development",
            public_base_url="",
            trust_proxy_headers=True,
            auth_cookie_secure=False,
            auth_cookie_samesite="lax",
            auth_cookie_domain="",
            auth_cookie_name="dnd_session",
            auth_rate_limit_enabled=False,
            auth_rate_limit_window_seconds=300,
            auth_rate_limit_max_attempts=10,
            log_level="INFO",
            commercial_deployment_model="self_host",
            commercial_default_plan="community",
            support_contact_email="",
            support_portal_url="",
            legal_terms_url="",
            legal_privacy_url="",
            legal_dpa_url="",
            release_runbook_version="v1",
        ),
    )

    req = _DummyRequest(headers={"x-forwarded-proto": "https"}, scheme="http")
    assert auth_routes._should_use_secure_cookie(req) is True


def test_auth_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "_APP_CONFIG",
        app_config.AppConfig(
            public_domain="",
            port=8000,
            ngrok_domain="",
            app_env="production",
            public_base_url="",
            trust_proxy_headers=False,
            auth_cookie_secure=True,
            auth_cookie_samesite="lax",
            auth_cookie_domain="",
            auth_cookie_name="dnd_session",
            auth_rate_limit_enabled=True,
            auth_rate_limit_window_seconds=300,
            auth_rate_limit_max_attempts=2,
            log_level="INFO",
            commercial_deployment_model="self_host",
            commercial_default_plan="community",
            support_contact_email="",
            support_portal_url="",
            legal_terms_url="",
            legal_privacy_url="",
            legal_dpa_url="",
            release_runbook_version="v1",
        ),
    )
    auth_routes._RATE_LIMIT_BUCKETS.clear()

    req = _DummyRequest(client_ip="10.0.0.5")
    auth_routes._enforce_rate_limit(req, "login")
    auth_routes._enforce_rate_limit(req, "login")

    try:
        auth_routes._enforce_rate_limit(req, "login")
        assert False, "Expected HTTPException for exceeding rate limit"
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "Retry-After" in (exc.headers or {})
