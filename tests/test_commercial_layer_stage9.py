from pathlib import Path

from server import config as app_config
from server.auth import models as auth_models
from server.commercial import service as commercial_service


def _base_cfg(**overrides):
    base = dict(
        public_domain="",
        port=8000,
        ngrok_domain="",
        app_env="development",
        public_base_url="",
        trust_proxy_headers=False,
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
        support_contact_email="support@example.com",
        support_portal_url="https://support.example.com",
        legal_terms_url="https://example.com/terms",
        legal_privacy_url="https://example.com/privacy",
        legal_dpa_url="https://example.com/dpa",
        release_runbook_version="v1",
    )
    base.update(overrides)
    return app_config.AppConfig(**base)


def test_load_config_commercial_defaults(monkeypatch):
    monkeypatch.delenv("COMMERCIAL_DEPLOYMENT_MODEL", raising=False)
    monkeypatch.delenv("COMMERCIAL_DEFAULT_PLAN", raising=False)
    cfg = app_config.load_config("does-not-exist.txt")

    assert cfg.commercial_deployment_model == "self_host"
    assert cfg.commercial_default_plan == "community"
    assert cfg.release_runbook_version == "v1"


def test_resolve_user_entitlements_uses_default_plan(monkeypatch):
    monkeypatch.setattr(commercial_service, "get_user_entitlement", lambda _uid: None)
    user = {"id": "u1", "role": "player"}
    context = commercial_service.build_commercial_context(user, _base_cfg(commercial_default_plan="pro"))

    assert context["deployment_model"] == "self_host"
    assert context["entitlements"]["plan_code"] == "pro"
    assert context["entitlements"]["source"] == "default_plan"


def test_user_entitlement_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "commercial.db"
    monkeypatch.setattr(auth_models, "DB_PATH", db_path)
    auth_models.init_auth_db()

    with auth_models.get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
            ("u2", "merchant", "merchant@example.com", "x", "dm", 1.0),
        )

    auth_models.upsert_user_entitlement(
        "u2",
        plan_code="studio",
        subscription_status="active",
        support_tier="priority",
        feature_overrides={"features": {"api_access": True}},
        updated_by="test",
    )

    saved = auth_models.get_user_entitlement("u2")
    assert saved is not None
    assert saved["plan_code"] == "studio"
    assert saved["support_tier"] == "priority"
    assert saved["feature_overrides"]["features"]["api_access"] is True

    user = {"id": "u2", "role": "dm"}
    resolved = commercial_service.resolve_user_entitlements(user, _base_cfg())
    assert resolved["source"] == "account_override"
    assert resolved["plan_code"] == "studio"
    assert resolved["features"]["api_access"] is True
