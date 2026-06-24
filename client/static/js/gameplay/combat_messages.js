(function (global) {
  'use strict';

  // Combat message handler slice.
  //
  // This module is deliberately thin: it delegates to the existing play.html
  // runtime functions and does not own combat state. The authoritative combat
  // source remains window._combat/combatApplyState until the larger play.html
  // monolith is reduced further.

  const COMBAT_MESSAGE_TYPES = new Set([
    'combat_state',
    'combat_attack_result',
    'combat_move_state',
    'combat_move_preview_result',
    'combat_initiative_rolled',
    'token_move_denied',
  ]);

  function isCombatMessageType(type) {
    return COMBAT_MESSAGE_TYPES.has(String(type || ''));
  }

  function getFn(env, name) {
    if (env && typeof env[name] === 'function') return env[name];
    if (typeof global[name] === 'function') return global[name].bind(global);
    return null;
  }

  function callIfPresent(env, name, ...args) {
    const fn = getFn(env, name);
    if (!fn) return false;
    fn(...args);
    return true;
  }

  function getPayload(msg) {
    return (msg && msg.payload && typeof msg.payload === 'object') ? msg.payload : {};
  }

  function handleCombatState(payload, env) {
    return callIfPresent(env, 'combatApplyState', payload || {});
  }

  function handleCombatAttackResult(payload, env) {
    if (payload && payload.log) callIfPresent(env, 'addLogEntry', payload.log);
    return callIfPresent(env, 'showCombatAttackResult', payload || {});
  }

  function handleCombatMoveState(payload, env) {
    const setMovement = callIfPresent(env, 'setCombatMovement', payload && typeof payload === 'object' ? payload : null);
    const rendered = callIfPresent(env, 'renderCombat');
    return setMovement || rendered;
  }

  function handleCombatMovePreviewResult(payload, env) {
    // Prefer an extracted/specialized preview renderer if it exists. If it does
    // not, fall through to legacy play.html so current behaviour is preserved.
    return callIfPresent(env, 'handleCombatMovePreviewResult', payload || {})
      || callIfPresent(env, 'showCombatMovePreviewResult', payload || {});
  }

  function handleCombatInitiativeRolled(payload, env) {
    // Some builds only log/show the initiative result in legacy play.html. Only
    // claim the message when an explicit handler exists or a log was applied.
    if (callIfPresent(env, 'handleCombatInitiativeRolled', payload || {})) return true;
    if (payload && payload.log) {
      callIfPresent(env, 'addLogEntry', payload.log);
      return true;
    }
    return false;
  }

  function handleTokenMoveDenied(payload, env) {
    const tokenId = payload && payload.token_id;
    let handled = false;
    if (tokenId) handled = callIfPresent(env, 'clearPendingMoveConfirmForToken', tokenId) || handled;
    if (payload && payload.movement) {
      handled = callIfPresent(env, 'setCombatMovement', payload.movement) || handled;
      handled = callIfPresent(env, 'renderCombat') || handled;
    }
    if (payload && payload.message) handled = callIfPresent(env, 'showToast', payload.message) || handled;
    return handled;
  }

  function handleIncoming(msg, env) {
    if (!msg || typeof msg !== 'object') return false;
    const type = String(msg.type || '');
    if (!isCombatMessageType(type)) return false;
    const payload = getPayload(msg);

    switch (type) {
      case 'combat_state':
        return handleCombatState(payload, env);
      case 'combat_attack_result':
        return handleCombatAttackResult(payload, env);
      case 'combat_move_state':
        return handleCombatMoveState(payload, env);
      case 'combat_move_preview_result':
        return handleCombatMovePreviewResult(payload, env);
      case 'combat_initiative_rolled':
        return handleCombatInitiativeRolled(payload, env);
      case 'token_move_denied':
        return handleTokenMoveDenied(payload, env);
      default:
        return false;
    }
  }

  global.AppCombatMessages = {
    handleIncoming,
    isCombatMessageType,
    _types: Array.from(COMBAT_MESSAGE_TYPES),
  };
})(window);
