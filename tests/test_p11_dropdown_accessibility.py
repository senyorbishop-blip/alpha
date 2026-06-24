"""P11 dropdown accessibility guard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABS = ROOT / "client" / "static" / "js" / "ui" / "tabs.js"


def test_library_dropdown_resets_expanded_state_when_hidden():
    src = TABS.read_text(encoding="utf-8")

    assert "function syncDropdownVisibility(env)" in src
    assert "if (!hasVisibleItems)" in src
    assert "menu.classList.remove('open')" in src
    assert "trigger.setAttribute('aria-expanded', 'false')" in src
