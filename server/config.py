"""Runtime configuration helpers.

This module keeps deployment-facing behavior explicit while preserving
config.txt compatibility for local/self-host workflows.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in _TRUE_VALUES


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _load_config_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        with path.open() as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, raw = line.split("=", 1)
                values[key.strip()] = raw.strip()
    except FileNotFoundError:
        pass
    return values


@dataclass(frozen=True)
class AppConfig:
    public_domain: str
    port: int
    ngrok_domain: str
    app_env: str
    public_base_url: str
    trust_proxy_headers: bool
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    auth_cookie_domain: str
    auth_cookie_name: str
    auth_rate_limit_enabled: bool
    auth_rate_limit_window_seconds: int
    auth_rate_limit_max_attempts: int
    log_level: str
    commercial_deployment_model: str
    commercial_default_plan: str
    support_contact_email: str
    support_portal_url: str
    legal_terms_url: str
    legal_privacy_url: str
    legal_dpa_url: str
    release_runbook_version: str

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def local_only_mode(self) -> bool:
        return (not self.public_domain) and (not self.public_base_url)

    @property
    def public_host(self) -> str:
        if self.public_base_url:
            host = self.public_base_url.split("//", 1)[-1]
            return host.split("/", 1)[0]
        return self.public_domain

    def preferred_external_url(self) -> str | None:
        if self.public_base_url:
            return self.public_base_url.rstrip("/")
        if self.public_domain:
            if self.port == 443:
                return f"https://{self.public_domain}"
            if self.port == 80:
                return f"http://{self.public_domain}"
            return f"http://{self.public_domain}:{self.port}"
        return None


def load_config(config_file: str | Path = "config.txt") -> AppConfig:
    cfg_path = Path(config_file)
    file_values = _load_config_file(cfg_path)

    def pick(key: str, default: str) -> str:
        return os.getenv(key, file_values.get(key, default))

    public_domain = pick("PUBLIC_DOMAIN", "").strip()
    ngrok_domain = pick("NGROK_DOMAIN", "").strip()
    port = _as_int(pick("PORT", "8000"), 8000)
    app_env = pick("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "production"}:
        app_env = "development"

    public_base_url = pick("PUBLIC_BASE_URL", "").strip().rstrip("/")
    trust_proxy_headers = _as_bool(os.getenv("TRUST_PROXY_HEADERS"), default=(app_env == "production"))

    auth_cookie_secure = _as_bool(os.getenv("AUTH_COOKIE_SECURE"), default=(app_env == "production"))
    _default_samesite = "strict" if app_env == "production" else "lax"
    auth_cookie_samesite = pick("AUTH_COOKIE_SAMESITE", _default_samesite).strip().lower()
    if auth_cookie_samesite not in {"lax", "strict", "none"}:
        auth_cookie_samesite = _default_samesite
    auth_cookie_domain = pick("AUTH_COOKIE_DOMAIN", "").strip()
    auth_cookie_name = pick("AUTH_COOKIE_NAME", "dnd_session").strip() or "dnd_session"

    auth_rate_limit_enabled = _as_bool(os.getenv("AUTH_RATE_LIMIT_ENABLED"), default=True)
    auth_rate_limit_window_seconds = _as_int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS"), 300)
    auth_rate_limit_max_attempts = _as_int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS"), 10)

    log_level = pick("LOG_LEVEL", "INFO").strip().upper() or "INFO"

    commercial_deployment_model = pick("COMMERCIAL_DEPLOYMENT_MODEL", "self_host").strip().lower()
    if commercial_deployment_model not in {"self_host", "hosted_saas", "hybrid"}:
        commercial_deployment_model = "self_host"

    commercial_default_plan = pick("COMMERCIAL_DEFAULT_PLAN", "community").strip().lower()
    support_contact_email = pick("SUPPORT_CONTACT_EMAIL", "").strip()
    support_portal_url = pick("SUPPORT_PORTAL_URL", "").strip()
    legal_terms_url = pick("LEGAL_TERMS_URL", "").strip()
    legal_privacy_url = pick("LEGAL_PRIVACY_URL", "").strip()
    legal_dpa_url = pick("LEGAL_DPA_URL", "").strip()
    release_runbook_version = pick("RELEASE_RUNBOOK_VERSION", "v1").strip() or "v1"

    return AppConfig(
        public_domain=public_domain,
        port=port,
        ngrok_domain=ngrok_domain,
        app_env=app_env,
        public_base_url=public_base_url,
        trust_proxy_headers=trust_proxy_headers,
        auth_cookie_secure=auth_cookie_secure,
        auth_cookie_samesite=auth_cookie_samesite,
        auth_cookie_domain=auth_cookie_domain,
        auth_cookie_name=auth_cookie_name,
        auth_rate_limit_enabled=auth_rate_limit_enabled,
        auth_rate_limit_window_seconds=max(30, auth_rate_limit_window_seconds),
        auth_rate_limit_max_attempts=max(2, auth_rate_limit_max_attempts),
        log_level=log_level,
        commercial_deployment_model=commercial_deployment_model,
        commercial_default_plan=commercial_default_plan,
        support_contact_email=support_contact_email,
        support_portal_url=support_portal_url,
        legal_terms_url=legal_terms_url,
        legal_privacy_url=legal_privacy_url,
        legal_dpa_url=legal_dpa_url,
        release_runbook_version=release_runbook_version,
    )
