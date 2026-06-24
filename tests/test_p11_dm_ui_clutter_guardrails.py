"""P11 DM UI clutter guardrails.

The right-sidebar tab controller should keep the DM surface powerful without
turning every role into the full DM control wall. These tests lock the role-aware
visibility, library grouping, context focus, and dropdown behaviour that keep the
panel readable.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABS = ROOT / "client" / "static" / "js" / "ui" / "tabs.js"
FRONTEND_DOC = ROOT / "docs" / "frontend-modularization.md"


def _src() -> str:
    return TABS.read_text(encoding="utf-8")


def test_right_sidebar_tabs_have_single_modular_owner():
    src = _src()

    assert "global.AppUITabs" in src
    assert "TAB_REGISTRY" in src
    assert "function syncTabUI(env)" in src
    assert "function switchRTab(env, tab)" in src


def test_dm_library_tabs_are_grouped_under_library_dropdown():
    src = _src()

    assert "const DROPDOWN_DEFS" in src
    assert "library:" in src
    assert "#rtab-dropdown-library" in src
    assert "#rtab-menu-library" in src
    assert re.search(r"id: 'shop'.*group: 'library'", src, re.S)
    assert re.search(r"id: 'bestiary'.*group: 'library'", src, re.S)
    assert re.search(r"id: 'spelllib'.*group: 'library'", src, re.S)
    assert re.search(r"id: 'handouts'.*group: 'library'", src, re.S)


def test_viewer_cannot_see_player_or_dm_library_tabs():
    src = _src()

    assert "function canUsePlayerTabs(env)" in src
    assert "return !isRole(env, 'viewer');" in src
    assert "function canUseDmLibraryTabs(env)" in src
    assert "return isRole(env, 'dm');" in src
    assert re.search(r"id: 'inventory'.*isVisible: \(env\) => canUsePlayerTabs\(env\)", src, re.S)
    assert re.search(r"id: 'memory'.*isVisible: \(env\) => canUsePlayerTabs\(env\)", src, re.S)
    assert re.search(r"id: 'shop'.*isVisible: \(env\) => canUseDmLibraryTabs\(env\)", src, re.S)
    assert re.search(r"id: 'bestiary'.*isVisible: \(env\) => canUseDmLibraryTabs\(env\)", src, re.S)


def test_assistant_dm_library_access_requires_explicit_scopes():
    src = _src()

    assert "function hasAssistantScope(env, scope)" in src
    assert "hasAssistantScope(env, 'handouts.manage')" in src
    assert "hasAssistantScope(env, 'quests.manage')" in src
    assert "getAssistantScopes" in src


def test_hidden_dropdowns_close_when_no_visible_items():
    src = _src()

    assert "function syncDropdownVisibility(env)" in src
    assert "hasVisibleItems" in src
    assert "setVisible(wrap, hasVisibleItems)" in src
    assert "menu.classList.remove('open')" in src
    assert "aria-expanded", "false" or "aria-expanded'" in src


def test_context_focus_mutes_non_relevant_tabs_instead_of_autoshowing_everything():
    src = _src()

    assert "CONTEXT_DEFAULT" in src
    assert "context-priority" in src
    assert "context-muted" in src
    assert "shouldAutoFocusContext" in src
    assert "context.recommendedTab" in src


def test_sync_tab_ui_normalizes_invalid_active_tab_to_visible_default():
    src = _src()

    assert "normalizeAllowedTab" in src
    assert "getVisibleTabIds(env)" in src
    assert "getDefaultTab(env)" in src
    assert "if (!visibleIds.has(activeTab))" in src
    assert "env.setActiveTab?.(activeTab)" in src


def test_docs_record_p11_dm_ui_clutter_guardrails():
    doc = FRONTEND_DOC.read_text(encoding="utf-8")

    assert "## Stage 11 — DM UI clutter guardrails" in doc
    assert "right-sidebar" in doc
    assert "library dropdown" in doc
    assert "role-visible tabs" in doc
    assert "tests/test_p11_dm_ui_clutter_guardrails.py" in doc
