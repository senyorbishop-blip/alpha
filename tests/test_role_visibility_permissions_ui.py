import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel_path: str) -> str:
    with open(os.path.join(PROJECT_ROOT, rel_path), 'r', encoding='utf-8') as f:
        return f.read()


def test_tabs_visibility_uses_shared_role_helpers():
    tabs_src = _read('client/static/js/ui/tabs.js')
    assert 'function canUsePlayerTabs(env)' in tabs_src
    assert 'function canUseDmLibraryTabs(env)' in tabs_src
    assert "isVisible: (env) => canUsePlayerTabs(env)" in tabs_src
    assert "isVisible: (env) => canUseDmLibraryTabs(env)" in tabs_src


def test_assistant_dm_scopes_are_centralized_for_visibility_and_tabs():
    play_src = _read('client/templates/play.html')
    tabs_src = _read('client/static/js/ui/tabs.js')
    assert 'function __assistantScopeSet()' in play_src
    assert 'function __hasAssistantScope(scope)' in play_src
    assert 'if (__hasAssistantScope(\'quests.manage\') || __hasAssistantScope(\'handouts.manage\')) return true;' in play_src
    assert 'getAssistantScopes: () => Array.from(__assistantScopeSet())' in play_src
    assert "hasAssistantScope(env, 'handouts.manage') || hasAssistantScope(env, 'quests.manage')" in tabs_src


def test_restricted_flyouts_are_blocked_by_shared_role_guard():
    play_src = _read('client/templates/play.html')
    role_access_src = _read('client/static/js/ui/role_access.js')

    # Canonical flyout scope map now lives in role_access.js.
    assert 'FLYOUT_SCOPE_MAP' in role_access_src
    # Key/value check allows alignment whitespace (e.g. 'flyout-fog':       'maps.fog')
    assert re.search(r"'flyout-fog'\s*:\s*'maps\.fog'", role_access_src)
    assert re.search(r"'flyout-sound'\s*:\s*'narration\.broadcast'", role_access_src)

    # play.html still declares __ROLE_FLYOUT_SCOPE as a load-order fallback
    # (delegates to RoleAccessHelpers.FLYOUT_SCOPE_MAP when the module is loaded).
    assert 'const __ROLE_FLYOUT_SCOPE' in play_src
    # Inline fallback entries must match the canonical map.
    assert "'flyout-perm': ''" in play_src
    assert "'flyout-editor': ''" in play_src
    assert "'flyout-fog': 'maps.fog'" in play_src
    assert "'flyout-sound': 'narration.broadcast'" in play_src

    # Guard and function name unchanged — all call sites remain valid.
    assert 'function __canUseFlyout(id)' in play_src
    assert "if (!__canUseFlyout(id)) {" in play_src


def test_assistant_dm_scope_sync_reapplies_role_visibility_controls():
    play_src = _read('client/templates/play.html')
    assert "case 'assistant_dm_permissions_sync': {" in play_src
    assert "if (ROLE === 'assistant_dm') {" in play_src
    assert "document.getElementById('rail-fog-btn').style.display = __canAccessDmControl('maps.fog') ? 'flex' : 'none';" in play_src
    assert "document.getElementById('rail-sound-btn').style.display = __canAccessDmControl('narration.broadcast') ? 'flex' : 'none';" in play_src
