"""
Tests for client/static/js/ui/role_access.js

These tests verify the extracted pure helper functions by parsing the module
source directly — no browser runtime required.  The module is loaded as text
and each function's behaviour is validated through pattern matching and
structural assertions.

Behavioural contracts tested:
  - buildScopeSet: normalises and deduplicates raw scope arrays
  - hasScope: only passes for role 'assistant_dm'; scope must be present
  - canAccessDmControl: dm always passes; assistant_dm scope-gated; others blocked
  - canUseFlyout: absent-from-map → unrestricted; mapped → canAccessDmControl
  - FLYOUT_SCOPE_MAP: structural completeness and correct scope assignments
"""

from __future__ import annotations

import re
from pathlib import Path

ROLE_ACCESS_PATH = Path('client/static/js/ui/role_access.js')
PLAY_PATH = Path('client/templates/play.html')


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# Module structure
# ---------------------------------------------------------------------------

def test_module_exports_required_symbols():
    src = _read(ROLE_ACCESS_PATH)
    assert 'global.RoleAccessHelpers = {' in src
    for symbol in ('FLYOUT_SCOPE_MAP', 'buildScopeSet', 'hasScope', 'canAccessDmControl', 'canUseFlyout'):
        assert symbol in src, f'RoleAccessHelpers must export {symbol}'


def test_module_is_iife_with_window_binding():
    src = _read(ROLE_ACCESS_PATH)
    assert src.startswith('(function (global) {')
    assert src.strip().endswith(')(window);')
    assert "'use strict';" in src


def test_module_has_no_dom_references():
    """Pure module must not reference document, querySelector, getElementById etc."""
    src = _read(ROLE_ACCESS_PATH)
    assert 'document' not in src
    assert 'querySelector' not in src
    assert 'getElementById' not in src


def test_module_has_no_global_variable_reads():
    """Module must not read ROLE, assistantDmPermissions, or any other play.html global."""
    src = _read(ROLE_ACCESS_PATH)
    # Must not reference the play.html globals directly (they belong to the wrapper)
    assert re.search(r'\bROLE\b', src) is None, 'Must not read ROLE global'
    assert 'assistantDmPermissions' not in src


# ---------------------------------------------------------------------------
# FLYOUT_SCOPE_MAP contract
# ---------------------------------------------------------------------------

def test_flyout_scope_map_contains_all_required_entries():
    src = _read(ROLE_ACCESS_PATH)
    required_entries = [
        "'flyout-token':",
        "'flyout-map':",
        "'flyout-perm':",
        "'flyout-editor':",
        "'flyout-cart':",
        "'flyout-assistant':",
        "'flyout-fog':",
        "'flyout-sound':",
    ]
    for entry in required_entries:
        assert entry in src, f'FLYOUT_SCOPE_MAP must contain {entry}'


def test_flyout_scope_map_restricted_entries_have_correct_scopes():
    src = _read(ROLE_ACCESS_PATH)
    # Scoped (assistant_dm-delegatable) flyouts
    assert "'flyout-fog':       'maps.fog'" in src or "'flyout-fog': 'maps.fog'" in src
    assert "'flyout-sound':     'narration.broadcast'" in src or "'flyout-sound': 'narration.broadcast'" in src


def test_flyout_scope_map_dm_only_entries_have_empty_scope():
    src = _read(ROLE_ACCESS_PATH)
    # Empty scope = dm-only, no delegation
    assert re.search(r"'flyout-token'\s*:\s*''", src)
    assert re.search(r"'flyout-map'\s*:\s*''", src)
    assert re.search(r"'flyout-perm'\s*:\s*''", src)
    assert re.search(r"'flyout-editor'\s*:\s*''", src)


# ---------------------------------------------------------------------------
# buildScopeSet semantics (structural)
# ---------------------------------------------------------------------------

def test_build_scope_set_function_is_defined():
    src = _read(ROLE_ACCESS_PATH)
    assert 'function buildScopeSet(scopes) {' in src


def test_build_scope_set_normalises_with_trim_and_filter():
    src = _read(ROLE_ACCESS_PATH)
    # Must trim whitespace
    assert ".trim()" in src
    # Must drop empty strings
    assert ".filter(Boolean)" in src
    # Must handle non-array input safely
    assert 'Array.isArray(scopes)' in src


def test_build_scope_set_returns_a_set():
    src = _read(ROLE_ACCESS_PATH)
    assert 'return new Set(' in src


# ---------------------------------------------------------------------------
# hasScope semantics (structural)
# ---------------------------------------------------------------------------

def test_has_scope_function_is_defined():
    src = _read(ROLE_ACCESS_PATH)
    assert 'function hasScope(role, scopes, scope) {' in src


def test_has_scope_rejects_non_assistant_dm_roles():
    src = _read(ROLE_ACCESS_PATH)
    # Must early-return false for any role that isn't assistant_dm
    assert "'assistant_dm'" in src
    assert "return false;" in src


def test_has_scope_delegates_to_build_scope_set():
    src = _read(ROLE_ACCESS_PATH)
    assert 'buildScopeSet(scopes)' in src


# ---------------------------------------------------------------------------
# canAccessDmControl semantics (structural)
# ---------------------------------------------------------------------------

def test_can_access_dm_control_function_is_defined():
    src = _read(ROLE_ACCESS_PATH)
    assert 'function canAccessDmControl(role, scopes, requiredScope) {' in src


def test_can_access_dm_control_dm_always_passes():
    src = _read(ROLE_ACCESS_PATH)
    assert "if (r === 'dm') return true;" in src


def test_can_access_dm_control_other_roles_blocked():
    src = _read(ROLE_ACCESS_PATH)
    assert "if (r !== 'assistant_dm') return false;" in src


def test_can_access_dm_control_empty_scope_blocks_assistant_dm():
    """An empty requiredScope means dm-only — assistant_dm must be blocked."""
    src = _read(ROLE_ACCESS_PATH)
    # The guard: non-empty scope required to delegate
    assert 'return normalized ? hasScope(role, scopes, normalized) : false;' in src


def test_can_access_dm_control_normalizes_role_to_lowercase():
    src = _read(ROLE_ACCESS_PATH)
    assert '.toLowerCase()' in src


# ---------------------------------------------------------------------------
# canUseFlyout semantics (structural)
# ---------------------------------------------------------------------------

def test_can_use_flyout_function_is_defined():
    src = _read(ROLE_ACCESS_PATH)
    assert 'function canUseFlyout(id, role, scopes, scopeMap) {' in src


def test_can_use_flyout_absent_id_returns_true():
    src = _read(ROLE_ACCESS_PATH)
    # When scope === undefined the flyout is unrestricted
    assert 'if (scope === undefined) return true;' in src


def test_can_use_flyout_delegates_to_can_access_dm_control():
    src = _read(ROLE_ACCESS_PATH)
    assert 'return canAccessDmControl(role, scopes, scope);' in src


def test_can_use_flyout_accepts_scope_map_override_for_testing():
    """scopeMap parameter must be honoured (not silently ignored)."""
    src = _read(ROLE_ACCESS_PATH)
    assert 'const map = scopeMap || FLYOUT_SCOPE_MAP;' in src
    assert 'const scope = map[flyoutId];' in src


# ---------------------------------------------------------------------------
# play.html integration — wrapper functions remain and delegate
# ---------------------------------------------------------------------------

def test_play_wrappers_still_present_for_backward_compat():
    """The wrapper functions must still exist in play.html so call sites and
    existing tests that grep for the function names are not broken."""
    play_src = _read(PLAY_PATH)
    assert 'function __assistantScopeSet()' in play_src
    assert 'function __hasAssistantScope(scope)' in play_src
    assert 'function __canAccessDmControl(scope' in play_src
    assert 'const __ROLE_FLYOUT_SCOPE' in play_src
    assert 'function __canUseFlyout(id)' in play_src


def test_play_wrappers_delegate_to_role_access_helpers():
    play_src = _read(PLAY_PATH)
    assert 'window.RoleAccessHelpers' in play_src
    assert 'window.RoleAccessHelpers.buildScopeSet' in play_src
    assert 'window.RoleAccessHelpers.canAccessDmControl' in play_src
    assert 'window.RoleAccessHelpers.canUseFlyout' in play_src


def test_play_flyout_scope_fallback_entries_match_canonical_map():
    """The inline fallback in play.html must contain the same entries as
    role_access.js so load-order failures degrade gracefully."""
    play_src = _read(PLAY_PATH)
    role_src = _read(ROLE_ACCESS_PATH)

    # Check key and value are adjacent (allowing optional alignment whitespace).
    scoped_entries = [
        (r"'flyout-fog'\s*:\s*'maps\.fog'", 'flyout-fog → maps.fog'),
        (r"'flyout-sound'\s*:\s*'narration\.broadcast'", 'flyout-sound → narration.broadcast'),
    ]
    for pattern, label in scoped_entries:
        assert re.search(pattern, play_src), f'play.html fallback must contain {label}'
        assert re.search(pattern, role_src), f'role_access.js must contain {label}'


def test_play_inline_fallback_documented_as_load_order_only():
    play_src = _read(PLAY_PATH)
    assert 'load-order fallback' in play_src
    assert 'do not add' in play_src.lower() or 'do not add new entries' in play_src


# ---------------------------------------------------------------------------
# tabs.js normalizeTab export
# ---------------------------------------------------------------------------

def test_tabs_exports_normalize_tab():
    tabs_src = Path('client/static/js/ui/tabs.js').read_text(encoding='utf-8')
    assert 'normalizeTab,' in tabs_src
    # The export must sit inside the AppUITabs object literal
    assert re.search(r'global\.AppUITabs\s*=\s*\{[^}]*normalizeTab', tabs_src, re.S)


def test_tabs_normalize_tab_defaults_to_party():
    tabs_src = Path('client/static/js/ui/tabs.js').read_text(encoding='utf-8')
    assert "return String(tab || 'party');" in tabs_src


def test_tabs_documents_relationship_to_role_access():
    tabs_src = Path('client/static/js/ui/tabs.js').read_text(encoding='utf-8')
    # The comment block must acknowledge the parallel with role_access.js
    assert 'role_access.js' in tabs_src
    assert 'RoleAccessHelpers' in tabs_src
