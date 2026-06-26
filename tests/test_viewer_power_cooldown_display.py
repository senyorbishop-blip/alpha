"""Guardrail for the map-first viewer power display.

Regression: a DM-granted power that merely *has* a cooldown configured (e.g.
Fireball, Trip Hex, Knockback) was rendered as if it were already on cooldown —
greyed out and non-clickable — so the viewer could see it but never use it.

``viewerPowerCooldownLabel`` returns an informational label like ``"90s
cooldown"`` even when the power is ready, so the map-first render functions must
decide the disabled/greyed state from the live cooldown timer
(``_viewerPowerOnCooldown`` / ``cooldown_until``), never by string-matching that
label.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY_HTML = ROOT / "client" / "templates" / "play.html"


def _function_body(src: str, name: str) -> str:
    """Return the source of a top-level ``function name(...) { ... }`` block."""
    start = src.index(f"function {name}(")
    brace = src.index("{", start)
    depth = 0
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
    raise AssertionError(f"Unbalanced braces while scanning {name}")


def test_map_first_viewer_render_keys_cooldown_off_live_timer():
    src = PLAY_HTML.read_text(encoding="utf-8")

    for fn_name in ("_rpViewerPowersHtml", "_refreshViewerHud"):
        body = _function_body(src, fn_name)

        # The disabled/greyed state must be derived from the live cooldown timer.
        assert "_viewerPowerOnCooldown(entry)" in body or "cooldown_until" in body, (
            f"{fn_name} must decide cooldown state from the live timer"
        )

        # And it must NOT fall back to treating the informational label string as
        # the cooldown state — that is the exact bug this guards against.
        offending = re.search(
            r"onCd\s*=\s*coolLabel\s*&&\s*coolLabel\s*!==\s*'Ready'", body
        )
        assert offending is None, (
            f"{fn_name} must not infer cooldown state from the label string"
        )


def test_viewer_power_on_cooldown_helper_checks_timer():
    src = PLAY_HTML.read_text(encoding="utf-8")
    body = _function_body(src, "_viewerPowerOnCooldown")
    assert "cooldown_until" in body
    assert "Date.now()" in body
