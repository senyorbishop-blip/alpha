from pathlib import Path


def test_actions_tab_renders_compact_summon_manager_controls():
    src = Path('client/static/js/character/tabs/actions_tab.js').read_text()
    assert 'Summon Manager' in src
    assert 'data-summon-variant-for' in src
    assert 'data-summon-focus-token' in src
    assert 'data-summon-inspect-token' in src


def test_dm_companion_has_summon_admin_panel_and_ws_handlers():
    src = Path('client/templates/play.html').read_text()
    assert 'Summon Admin' in src
    assert 'dmCompanionSummonRefresh' in src
    assert "type: 'summon_runtime_admin'" in src
    assert "case 'summon_runtime_admin_result'" in src


def test_dispatch_registers_summon_admin_message_type():
    src = Path('server/handlers/__init__.py').read_text()
    assert 'summon_runtime_admin' in src


def test_summon_admin_handler_supports_dismiss_and_cleanup_stale():
    src = Path('server/handlers/summons.py').read_text()
    assert 'handle_summon_runtime_admin' in src
    assert 'cleanup_stale' in src
    assert 'role_not_allowed' in src
    assert 'token_deleted' in src
