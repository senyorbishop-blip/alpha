from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def test_play_page_has_premium_role_shell_polish_hook():
    src = _read('client/templates/play.html')
    assert 'function applyPremiumRoleShellPolish()' in src
    assert 'applyPremiumRoleShellPolish();' in src
    assert 'Viewer mode: this tool is DM/player only.' in src


def test_play_page_drops_stale_role_focus_blurb():
    """The old "Player focus: …" role-focus help blurb was removed; the polish
    hook should now clean up any stray element instead of injecting one."""
    src = _read('client/templates/play.html')
    assert "focus.id = 'shell-role-focus'" not in src
    assert 'Player focus:' not in src
    css = _read('client/static/css/play.css')
    assert '#shell-role-focus' not in css


def test_play_page_reduces_viewer_library_and_inventory_clutter():
    src = _read('client/templates/play.html')
    assert "ROLE === 'viewer'" in src
    assert "prepPriorityTabs = ['rtab-dropdown-library', 'rtab-memory'];" in src


def test_onboarding_viewer_step_calls_out_permissions_and_cooldowns():
    src = _read('client/static/js/ui/onboarding.js')
    assert 'Powers, Permissions, and Cooldowns' in src
    assert 'charge counts, cooldown timing, and explicit approval state' in src
    assert 'permissions: 3' in src
    assert 'powers: 3' in src
