"""Tests for server/auth/jwt_utils.py secret loading (env -> config.txt -> dev fallback)."""

import server.auth.jwt_utils as jwt_utils


def _clear_secret_env(monkeypatch):
    monkeypatch.delenv("DND_JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)


def test_env_var_secret_takes_priority_over_config_and_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_JWT_SECRET", "env-secret-value")
    monkeypatch.setattr(jwt_utils, "_CONFIG_PATH", tmp_path / "config.txt")

    assert jwt_utils._load_jwt_secret() == "env-secret-value"


def test_config_txt_secret_used_when_env_var_absent(monkeypatch, tmp_path):
    _clear_secret_env(monkeypatch)
    cfg = tmp_path / "config.txt"
    cfg.write_text("DND_JWT_SECRET=from-config-file\n")
    monkeypatch.setattr(jwt_utils, "_CONFIG_PATH", cfg)

    assert jwt_utils._load_jwt_secret() == "from-config-file"


def test_dev_fallback_secret_is_stable_across_simulated_restarts(monkeypatch, tmp_path):
    """A random per-process secret would invalidate every issued token on restart;
    the development fallback must persist and reuse the same generated secret."""
    _clear_secret_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(jwt_utils, "_CONFIG_PATH", tmp_path / "config.txt")
    monkeypatch.setattr(jwt_utils, "_DEV_SECRET_FILE", tmp_path / ".dnd_jwt_secret.local")

    secret_before_restart = jwt_utils._load_jwt_secret()
    # Simulate a process restart: nothing in memory carries over, only the file on disk.
    secret_after_restart = jwt_utils._load_jwt_secret()

    assert secret_before_restart == secret_after_restart
    assert (tmp_path / ".dnd_jwt_secret.local").read_text().strip() == secret_before_restart


def test_non_development_env_fails_fast_instead_of_minting_random_secret(monkeypatch, tmp_path):
    _clear_secret_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(jwt_utils, "_CONFIG_PATH", tmp_path / "config.txt")
    monkeypatch.setattr(jwt_utils, "_DEV_SECRET_FILE", tmp_path / ".dnd_jwt_secret.local")

    try:
        jwt_utils._load_jwt_secret()
        assert False, "expected RuntimeError when DND_JWT_SECRET is unset in production"
    except RuntimeError as exc:
        assert "DND_JWT_SECRET" in str(exc)

    # No throwaway secret file should be persisted for a failed production start.
    assert not (tmp_path / ".dnd_jwt_secret.local").exists()


def test_repo_root_config_path_resolves_to_real_config_txt():
    """The config.txt lookup must be anchored to this module's location, not cwd."""
    assert jwt_utils._CONFIG_PATH.name == "config.txt"
    assert jwt_utils._CONFIG_PATH.parent == jwt_utils._REPO_ROOT
    assert (jwt_utils._REPO_ROOT / "main.py").exists()
