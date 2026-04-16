from pathlib import Path


def test_actions_tab_renders_compact_summon_manager_controls():
    src = Path('client/static/js/character/tabs/actions_tab.js').read_text()
    assert 'Summon Manager' in src
    assert 'data-summon-variant-for' in src
    assert 'data-summon-focus-token' in src
    assert 'data-summon-inspect-token' in src


def test_dispatch_registers_summon_admin_message_type():
    src = Path('server/handlers/__init__.py').read_text()
    assert 'summon_runtime_admin' in src


def test_summon_admin_handler_supports_dismiss_and_cleanup_stale():
    src = Path('server/handlers/summons.py').read_text()
    assert 'handle_summon_runtime_admin' in src
    assert 'cleanup_stale' in src
    assert 'role_not_allowed' in src
    assert 'token_deleted' in src


def test_spell_summon_templates_are_registered_for_pass_i():
    src = Path('server/character/summon_catalog.py').read_text()
    assert 'spell-conjure-fey-manifestation' in src
    assert 'spell-conjure-celestial-manifestation' in src
    assert '"summonOrigin": "spell"' in src
    assert '"temporary": True' in src


def test_play_page_routes_supported_spell_summons_into_runtime_request():
    src = Path('client/templates/play.html').read_text()
    assert '_spellSummonRuntimeTemplateForSpell' in src
    assert "sendWS({" in src and "type: 'summon_runtime_request'" in src
    assert "spell_id: spellId" in src
