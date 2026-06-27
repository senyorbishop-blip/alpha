"""
server/twitch_ext/config.py — Environment-driven configuration for the EBS.

All values are read lazily (per-call) so tests and operators can set the env
after import. ``ext_configured()`` gates every endpoint: if the core Extension
credentials are missing the routes respond with a clear "not configured" error
instead of crashing.
"""
import os
import base64
import binascii


def _env(key: str) -> str:
    return str(os.environ.get(key, "") or "").strip()


def client_id() -> str:
    return _env("TWITCH_EXT_CLIENT_ID")


def owner_id() -> str:
    return _env("TWITCH_EXT_OWNER_ID")


def raw_secret_b64() -> str:
    return _env("TWITCH_EXT_SECRET")


def secret_bytes() -> bytes:
    """Return the decoded HS256 signing key (the console secret is base64)."""
    raw = raw_secret_b64()
    if not raw:
        raise ValueError("TWITCH_EXT_SECRET is not set")
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("TWITCH_EXT_SECRET is not valid base64") from exc


def client_secret() -> str:
    """OAuth client secret used to mint a Helix App Access Token (sub path)."""
    return _env("TWITCH_EXT_CLIENT_SECRET")


def sub_power_ids() -> list[str]:
    raw = _env("TWITCH_EXT_SUB_POWERS") or "healing_spark,battle_blessing"
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


def sub_cooldown_sec() -> int:
    try:
        return max(0, int(_env("TWITCH_EXT_SUB_COOLDOWN_SEC") or "900"))
    except ValueError:
        return 900


def ext_configured() -> bool:
    """True when the core Extension credentials are present."""
    return bool(client_id() and raw_secret_b64() and owner_id())


def sub_path_configured() -> bool:
    """The sub-claim path additionally needs an OAuth client secret for Helix."""
    return bool(ext_configured() and client_id() and client_secret())


def missing_core_keys() -> list[str]:
    missing = []
    if not client_id():
        missing.append("TWITCH_EXT_CLIENT_ID")
    if not raw_secret_b64():
        missing.append("TWITCH_EXT_SECRET")
    if not owner_id():
        missing.append("TWITCH_EXT_OWNER_ID")
    return missing
