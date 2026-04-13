import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(PROJECT_ROOT, relpath), 'r', encoding='utf-8') as f:
        return f.read()


def test_dice_vault_has_remote_visual_setting():
    content = _read('client/templates/play.html')
    assert 'id="dice-remote-visual-mode"' in content
    assert 'onDiceRemoteVisualModeChanged(this.value)' in content
    assert 'Shared roll visuals:' in content


def test_appdice_exposes_remote_visual_mode_helpers():
    content = _read('client/templates/play.html')
    assert 'getRemoteVisualMode: () => getDiceRemoteVisualMode()' in content
    assert 'setRemoteVisualMode: (mode) => setDiceRemoteVisualMode(mode)' in content


def test_authoritative_payload_sync_helper_exists():
    content = _read('client/templates/play.html')
    assert 'window.appDiceSyncAuthoritativePayload = function(payload = {})' in content
    assert "source: safe.source || 'authoritative-sync-payload'" in content


def test_message_handler_prefers_authoritative_bridge_helper():
    content = _read('client/static/js/core/message_handlers.js')
    assert 'env.appDiceSyncAuthoritativePayload' in content
    assert 'globalThis.appDiceSyncAuthoritativePayload' in content


def test_combat_module_no_longer_uses_direct_dice_animation_fallback():
    content = _read('client/static/js/gameplay/combat.js')
    assert 'env.showDiceAnimation(20, 1, null)' not in content
    assert "env.fillDiceResult([roll], total, 20, 1, modifier, 'Initiative')" not in content
    assert 'presentLocalInitiative' in content


def test_combat_env_exposes_authoritative_payload_helper():
    content = _read('client/static/js/core/env_builders_gameplay.js')
    assert 'appDiceSyncAuthoritativePayload' in content


def test_dice_factory_runtime_audit_present():
    content = _read('client/static/js/dice/DiceFactory.js')
    assert 'const EXPECTED_VALUE_SETS' in content
    assert 'function validateFaceAudit' in content
    assert 'validateFaceAudit(type, labels, faceValues, faceDefinitions, faceNormals);' in content


def test_audio_polish_present():
    content = _read('client/static/js/dice/utils/audio.js')
    assert 'recentImpactWindow' in content
    assert 'createStereoPanner' in content
    assert 'impact > 2.1' in content


def test_diceworld_performance_budget_tightened():
    content = _read('client/static/js/dice/DiceWorld.js')
    assert '31.0, 5.0' in content
    assert 'clamped >= 16 ? 0.55' in content


def test_docs_capture_final_qa_pass():
    content = _read('docs/dice-final-qa.md')
    assert 'Dice final QA + polish pass' in content
    assert 'Shared roll visuals now have a user-facing on/off setting' in content
