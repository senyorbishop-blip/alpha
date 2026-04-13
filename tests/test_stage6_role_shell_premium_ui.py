from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def test_play_page_has_premium_role_shell_polish_hook():
    src = _read('client/templates/play.html')
    assert 'function applyPremiumRoleShellPolish()' in src
    assert 'applyPremiumRoleShellPolish();' in src
    assert "id = 'shell-role-focus'" in src
    assert 'Viewer mode: this tool is DM/player only.' in src


def test_play_page_reduces_viewer_library_and_inventory_clutter():
    src = _read('client/templates/play.html')
    assert "ROLE === 'viewer'" in src
    assert "prepPriorityTabs = ['rtab-dropdown-library', 'rtab-memory'];" in src


def test_play_page_focus_copy_matches_role_tool_hierarchy():
    src = _read('client/templates/play.html')
    assert 'Prep in <strong>Library</strong>' in src
    assert 'storytelling through <strong>Journal/Sound</strong>' in src
    assert '<strong>My Character</strong> + <strong>Dice</strong>' in src
    assert 'charges, cooldowns, and approval state' in src


def test_onboarding_viewer_step_calls_out_permissions_and_cooldowns():
    src = _read('client/static/js/ui/onboarding.js')
    assert 'Powers, Permissions, and Cooldowns' in src
    assert 'charge counts, cooldown timing, and explicit approval state' in src
    assert 'permissions: 3' in src
    assert 'powers: 3' in src
