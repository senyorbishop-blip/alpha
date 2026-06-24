"""Tests for AI DM role gates and request budgets."""

from __future__ import annotations

from types import SimpleNamespace

from server.handlers import ai_rate_limit


def _session() -> SimpleNamespace:
    return SimpleNamespace(id="session-1")


def _user(role: str = "player", user_id: str = "user-1") -> SimpleNamespace:
    return SimpleNamespace(id=user_id, role=role)


def _reset(monkeypatch):
    ai_rate_limit.reset_ai_rate_limits_for_tests()
    for key in (
        "AI_DM_ENABLED",
        "AI_DM_RATE_LIMIT_PER_MINUTE",
        "AI_DM_RATE_LIMIT_PER_DAY",
        "AI_DM_NPC_SPEAK_ALLOWED_ROLES",
    ):
        monkeypatch.delenv(key, raising=False)


def test_ai_disabled_blocks_without_consuming(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("AI_DM_ENABLED", "false")

    result = ai_rate_limit.check_ai_gate(_session(), _user("dm"), "ai_rules_oracle")

    assert not result.allowed
    assert result.kind == "disabled"


def test_npc_speech_is_dm_only_by_default(monkeypatch):
    _reset(monkeypatch)

    player_result = ai_rate_limit.check_ai_gate(_session(), _user("player"), "ai_npc_speak")
    dm_result = ai_rate_limit.check_ai_gate(_session(), _user("dm"), "ai_npc_speak")

    assert not player_result.allowed
    assert player_result.kind == "forbidden"
    assert dm_result.allowed


def test_viewer_cannot_trigger_ai(monkeypatch):
    _reset(monkeypatch)

    result = ai_rate_limit.check_ai_gate(_session(), _user("viewer"), "ai_rules_oracle")

    assert not result.allowed
    assert result.kind == "forbidden"


def test_per_minute_budget_throttles_before_api_call(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("AI_DM_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("AI_DM_RATE_LIMIT_PER_DAY", "100")

    session = _session()
    user = _user("player")

    assert ai_rate_limit.check_ai_gate(session, user, "ai_rules_oracle").allowed
    assert ai_rate_limit.check_ai_gate(session, user, "ai_rules_oracle").allowed
    blocked = ai_rate_limit.check_ai_gate(session, user, "ai_rules_oracle")

    assert not blocked.allowed
    assert blocked.kind == "throttled"
    assert blocked.retry_after_seconds >= 1


def test_daily_budget_blocks_after_limit(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("AI_DM_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("AI_DM_RATE_LIMIT_PER_DAY", "1")

    session = _session()
    user = _user("dm")

    assert ai_rate_limit.check_ai_gate(session, user, "ai_describe_scene").allowed
    blocked = ai_rate_limit.check_ai_gate(session, user, "ai_describe_scene")

    assert not blocked.allowed
    assert blocked.kind == "daily_limit"


def test_zero_budgets_mean_unlimited_for_allowed_roles(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("AI_DM_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("AI_DM_RATE_LIMIT_PER_DAY", "0")

    session = _session()
    user = _user("player")

    for _ in range(20):
        assert ai_rate_limit.check_ai_gate(session, user, "ai_rules_oracle").allowed
