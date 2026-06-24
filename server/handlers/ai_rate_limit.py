"""Rate limiting and role gates for AI DM handlers."""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from server.session import Session, User

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_DEFAULT_PER_MINUTE = 6
_DEFAULT_PER_DAY = 100
_WINDOW_SECONDS = 60.0

_RECENT_CALLS: dict[str, Deque[float]] = defaultdict(deque)
_DAILY_CALLS: dict[str, tuple[int, int]] = {}


@dataclass(frozen=True)
class AiGateResult:
    allowed: bool
    kind: str
    message: str
    retry_after_seconds: int = 0


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, str(default)).strip()))
    except Exception:
        return default


def _allowed_roles_from_env() -> set[str]:
    raw = os.environ.get("AI_DM_NPC_SPEAK_ALLOWED_ROLES", "dm,assistant_dm").strip()
    roles = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return roles or {"dm", "assistant_dm"}


def _role(user: User) -> str:
    return str(getattr(user, "role", "") or "").strip().lower()


def _bucket_key(session: Session, user: User) -> str:
    return f"{getattr(session, 'id', '')}:{getattr(user, 'id', '')}"


def _daily_index(now: float) -> int:
    return int(now // 86400)


def reset_ai_rate_limits_for_tests() -> None:
    _RECENT_CALLS.clear()
    _DAILY_CALLS.clear()


def check_ai_gate(session: Session, user: User, action: str, *, consume: bool = True) -> AiGateResult:
    """Return whether an AI action is allowed and optionally consume quota.

    Environment variables:
    - AI_DM_ENABLED: false disables all AI handlers.
    - AI_DM_RATE_LIMIT_PER_MINUTE: per-session-user rolling minute limit.
    - AI_DM_RATE_LIMIT_PER_DAY: per-session-user daily limit.
    - AI_DM_NPC_SPEAK_ALLOWED_ROLES: comma-separated roles for ai_npc_speak.
    """
    if not _env_bool("AI_DM_ENABLED", True):
        return AiGateResult(False, "disabled", "AI DM is disabled for this server.")

    action = str(action or "ai").strip().lower() or "ai"
    user_role = _role(user)
    if action == "ai_npc_speak" and user_role not in _allowed_roles_from_env():
        return AiGateResult(False, "forbidden", "Only the DM can trigger AI NPC speech.")
    if action == "ai_describe_scene" and user_role != "dm":
        return AiGateResult(False, "forbidden", "Only the DM can trigger AI scene descriptions.")
    if user_role == "viewer":
        return AiGateResult(False, "forbidden", "Viewers cannot trigger AI requests.")

    per_minute = _env_int("AI_DM_RATE_LIMIT_PER_MINUTE", _DEFAULT_PER_MINUTE)
    per_day = _env_int("AI_DM_RATE_LIMIT_PER_DAY", _DEFAULT_PER_DAY)
    if per_minute == 0 and per_day == 0:
        return AiGateResult(True, "allowed", "AI request allowed.")

    now = time.time()
    key = _bucket_key(session, user)

    if per_minute > 0:
        recent = _RECENT_CALLS[key]
        while recent and now - recent[0] >= _WINDOW_SECONDS:
            recent.popleft()
        if len(recent) >= per_minute:
            retry_after = max(1, int(_WINDOW_SECONDS - (now - recent[0])))
            return AiGateResult(
                False,
                "throttled",
                "AI is cooling down. Please try again shortly.",
                retry_after,
            )

    if per_day > 0:
        today = _daily_index(now)
        stored_day, count = _DAILY_CALLS.get(key, (today, 0))
        if stored_day != today:
            count = 0
        if count >= per_day:
            return AiGateResult(
                False,
                "daily_limit",
                "This user has reached today's AI request limit.",
            )

    if consume:
        if per_minute > 0:
            _RECENT_CALLS[key].append(now)
        if per_day > 0:
            today = _daily_index(now)
            stored_day, count = _DAILY_CALLS.get(key, (today, 0))
            if stored_day != today:
                count = 0
            _DAILY_CALLS[key] = (today, count + 1)

    return AiGateResult(True, "allowed", "AI request allowed.")
