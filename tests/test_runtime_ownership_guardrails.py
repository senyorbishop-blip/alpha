from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAY_HTML = PROJECT_ROOT / 'client' / 'templates' / 'play.html'
REPO_MAP = PROJECT_ROOT / 'docs' / 'repo-map.md'
MESSAGE_DISPATCH = PROJECT_ROOT / 'client' / 'static' / 'js' / 'core' / 'message_dispatch.js'


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_play_html_has_stage1_runtime_guardrail_comment():
    src = _read(PLAY_HTML)
    assert 'Runtime ownership guardrail (Stage 1, 2026-03-27)' in src
    assert 'play.html` remains the live gameplay/runtime authority' in src


def test_play_html_keeps_live_websocket_dispatch_chain_loaded():
    src = _read(PLAY_HTML)
    runtime_bridge_idx = src.index('/static/js/core/runtime_bridge.js')
    boot_shell_idx = src.index('/static/js/core/boot_shell.js')
    ws_idx = src.index('/static/js/core/ws.js')
    dispatch_idx = src.index('/static/js/core/message_dispatch.js')
    assert runtime_bridge_idx < boot_shell_idx < ws_idx < dispatch_idx


def test_play_html_does_not_load_dormant_message_handlers_router():
    src = _read(PLAY_HTML)
    assert '/static/js/core/message_handlers.js' not in src


def test_message_dispatch_still_routes_to_legacy_play_html_handler():
    src = _read(MESSAGE_DISPATCH)
    assert 'handleLegacyMessage' in src
    assert 'first-hop dispatcher' in src


def test_message_dispatch_exports_phase3_legacy_domain_shell_handler():
    src = _read(MESSAGE_DISPATCH)
    assert 'handleLegacyDomainMessage' in src
    assert 'quest_template_library_sync' in src
    assert 'session_quests_sync' in src


def test_play_html_uses_phase3_legacy_domain_shell_delegation():
    src = _read(PLAY_HTML)
    assert '__createLegacyMessageShellEnv' in src
    assert 'handleLegacyDomainMessage(msg, __createLegacyMessageShellEnv())' in src


def test_repo_map_contains_stage1_runtime_ownership_lockdown_table():
    src = _read(REPO_MAP)
    assert '## Stage 1 Runtime Ownership Lockdown (2026-03-27)' in src
    for subsystem in (
        'Session boot',
        'WebSocket connect/send/receive',
        'Client message dispatch',
        'Token state + ownership',
        'Map load/save/switching',
        'Fog/vision',
        'Combat',
        'Dice',
        'Narration/audio',
        'Inventory/shop',
        'Handouts/journal/discoveries',
        'DM assistant + map tools',
    ):
        assert subsystem in src
