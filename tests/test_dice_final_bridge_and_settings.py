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


def test_settle_pulse_restores_emissive_and_caps_glint():
    content = _read('client/static/js/dice/DiceFactory.js')
    assert 'emissiveIntensity' in content
    assert 'emissiveHex' in content
    assert 'material.emissive.setHex(emissiveHex)' in content
    assert 'material.emissiveIntensity = emissiveIntensity' in content
    assert 'Math.min(Number(opts.glintCap ?? 0.04) || 0, 0.05)' in content
    assert 'glint: die.settleGlint !== false' in _read('client/static/js/dice/dice3d.js')


def test_multi_dice_damage_visuals_disable_expensive_effects():
    content = _read('client/static/js/dice/dice3d.js')
    assert 'die.settleGlint = clampedDice.length < 5' in content
    assert 'die.settleGlintCap = clampedDice.length >= 5 ? 0 : 0.04' in content
    assert 'die.mesh.castShadow = clampedDice.length < 5' in content
    assert 'die.mesh.receiveShadow = clampedDice.length < 5' in content
    world = _read('client/static/js/dice/DiceWorld.js')
    assert 'this.renderer.shadowMap.enabled = clamped < 6' in world


def test_dice_prewarm_is_hidden_renderer_and_common_combat_dice_only():
    content = _read('client/static/js/dice/dice3d.js')
    assert 'requestIdleCallback' in content
    assert "['d20', 'd6', 'd8', 'd10']" in content
    assert 'prewarm: () => _prewarmDiceWorld()' in content
    assert 'isPrewarmed: () => _prewarmDone' in content
    assert 'diceWorld.init(container)' in content
    assert 'diceWorld.render?.()' in content
    assert 'showResultOverlay' not in content[content.index('function _prewarmDiceWorld'):content.index('function scheduleDicePrewarm')]
    assert 'playRollStart' not in content[content.index('function _prewarmDiceWorld'):content.index('function scheduleDicePrewarm')]
