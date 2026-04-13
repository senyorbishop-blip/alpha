(function (global) {
  'use strict';

  function getTokensForMapContext(env) {
    const mapCtx = env.getMapContext();
    return Object.values(env.tokens || {}).filter(function (t) {
      return (t && (t.map_context || 'world') === mapCtx);
    });
  }

  function hitTestTokens(env, wx, wy) {
    const list = getTokensForMapContext(env);
    const hits = [];
    for (let i = list.length - 1; i >= 0; i -= 1) {
      const t = list[i];
      if (!t) continue;
      if (wx >= t.x && wx <= t.x + t.width && wy >= t.y && wy <= t.y + t.height) {
        hits.push(t);
      }
    }
    if (!hits.length) return null;

    if (env.role === 'player') {
      const nowSec = Date.now() / 1000;
      const own = hits.find(function (t) {
        return t.owner_id === env.userId || (t.temp_permissions && t.temp_permissions[env.userId] > nowSec);
      });
      if (own) return own;
    }

    return hits[0];
  }

  function canMoveToken(env, token) {
    if (!token) return false;
    if (env.role === 'dm') return true;
    if (env.role === 'player' && token.owner_id === env.userId) return true;
    if (token.temp_permissions && token.temp_permissions[env.userId]) {
      if (token.temp_permissions[env.userId] > Date.now() / 1000) return true;
    }
    return false;
  }

  function getCombatMoveRestrictionForToken(env, token) {
    if (!token || env.role === 'dm' || !env.combat || !env.combat.active) {
      return { allowed: true, message: '' };
    }
    const combatants = Array.isArray(env.combat.combatants) ? env.combat.combatants : [];
    const tokenId = String(token.id || '');
    if (!tokenId || !combatants.some(function (c) { return String(c && c.token_id || '') === tokenId; })) {
      return { allowed: true, message: '' };
    }
    const turnIndex = Math.max(0, Number(env.combat.turn) || 0);
    const current = combatants[turnIndex] || null;
    if (!current || String(current.token_id || '') !== tokenId) {
      return { allowed: false, message: 'It is not your turn to move that token.' };
    }
    const move = env.combat && env.combat.movement || null;
    if (move && String(move.token_id || '') === tokenId) {
      const remaining = Number(move.remaining_ft ?? move.speed_ft ?? 0);
      const speed = Number(move.speed_ft ?? 0);
      if (speed > 0 && remaining <= 0.01) {
        return { allowed: false, message: 'You have no movement left this turn.' };
      }
    }
    return { allowed: true, message: '' };
  }

  function shouldUsePreviewMode(env, token) {
    return !!(token && env.role === 'player' && env.combat && env.combat.active && token.owner_id === env.userId);
  }

  function movementSquaresFromDeltaCells(dxCells, dyCells) {
    const absDx = Math.abs(Math.round(Number(dxCells) || 0));
    const absDy = Math.abs(Math.round(Number(dyCells) || 0));
    const diag = Math.min(absDx, absDy);
    const straight = Math.max(absDx, absDy) - diag;
    return straight + (diag > 0 ? diag * 2 - 1 : 0);
  }

  function movementFtBetweenPoints(env, x1, y1, x2, y2) {
    const grid = Math.max(1, Number(env.pxPerGrid) || 50);
    const dxCells = Math.round((Number(x2 || 0) - Number(x1 || 0)) / grid);
    const dyCells = Math.round((Number(y2 || 0) - Number(y1 || 0)) / grid);
    return movementSquaresFromDeltaCells(dxCells, dyCells) * 5;
  }

  function getRemainingCombatMoveFt(env, token) {
    if (!token || !env.combat || !env.combat.active) return null;
    const move = env.combat && env.combat.movement || null;
    if (!move || String(move.token_id || '') !== String(token.id || '')) return null;
    const total = Number(move.remaining_ft);
    if (Number.isFinite(total)) return Math.max(0, total);
    const speedFt = Number(move.speed_ft ?? 0);
    const bonusFt = Number(move.bonus_ft ?? 0);
    const spentFt = Number(move.spent_ft ?? 0);
    return Math.max(0, (speedFt + bonusFt) - spentFt);
  }

  function clampCombatMoveForToken(env, token, x, y) {
    const remainingFt = getRemainingCombatMoveFt(env, token);
    if (remainingFt == null) return { x: x, y: y, clamped: false };
    if (remainingFt <= 0.01) {
      return { x: Number(env.drag.origX || token.x || 0), y: Number(env.drag.origY || token.y || 0), clamped: true };
    }
    const move = env.combat && env.combat.movement || null;
    const multiplier = move && move.difficult_terrain ? 2 : 1;
    const targetCost = movementFtBetweenPoints(env, env.drag.origX, env.drag.origY, x, y) * multiplier;
    if (targetCost <= remainingFt + 0.01) return { x: x, y: y, clamped: false };

    const originX = Number(env.drag.origX || token.x || 0);
    const originY = Number(env.drag.origY || token.y || 0);
    return { x: originX, y: originY, clamped: true };
  }

  function isSelectableHit(env, token) {
    return !!(token && (env.role === 'dm' || token.owner_id === env.userId));
  }

  function beginTokenDrag(env, token, wx, wy) {
    if (!token) return false;
    env.drag.active = true;
    env.drag.tokenId = token.id;
    env.drag.startX = wx;
    env.drag.startY = wy;
    env.drag.origX = token.x;
    env.drag.origY = token.y;
    env.drag.previewMode = shouldUsePreviewMode(env, token);
    if (env.setClickToken) env.setClickToken(token);
    return true;
  }

  function getDragDistanceWorld(env, wx, wy) {
    const dx = wx - Number(env.drag.startX || 0);
    const dy = wy - Number(env.drag.startY || 0);
    const moved = Math.sqrt(dx * dx + dy * dy);
    return { dx: dx, dy: dy, moved: moved, threshold: 4 / (env.cam.zoom || 1) };
  }

  function updateTokenDrag(env, wx, wy) {
    if (!env.drag.active || !env.drag.tokenId) return { updated: false };
    const token = env.tokens && env.tokens[env.drag.tokenId];
    if (!token) return { updated: false, missing: true };
    const delta = getDragDistanceWorld(env, wx, wy);
    const snapped = env.snapTokenToGrid(env.drag.origX + delta.dx, env.drag.origY + delta.dy, token);
    const limited = clampCombatMoveForToken(env, token, snapped.x, snapped.y);
    token.x = limited.x;
    token.y = limited.y;

    const broadcast = !env.drag.previewMode && env.shouldBroadcastMove && env.shouldBroadcastMove(env.drag.tokenId);
    return { updated: true, token: token, delta: delta, shouldBroadcast: !!broadcast, clamped: !!limited.clamped };
  }

  function clearDrag(env) {
    env.drag.active = false;
    env.drag.tokenId = null;
    env.drag.previewMode = false;
  }

  function finishTokenDrag(env) {
    if (!env.drag.active || !env.drag.tokenId) return { moved: false, token: null, previewMode: false };
    const token = env.tokens && env.tokens[env.drag.tokenId];
    const result = {
      moved: !!token,
      token: token || null,
      tokenId: env.drag.tokenId,
      origX: env.drag.origX,
      origY: env.drag.origY,
      previewMode: !!env.drag.previewMode,
    };
    clearDrag(env);
    return result;
  }

  function resolveClickToken(env, wx, wy) {
    const token = env.getClickToken ? env.getClickToken() : null;
    if (!token) return { isClick: false, token: null };
    const delta = getDragDistanceWorld(env, wx, wy);
    const isClick = delta.moved < delta.threshold;
    if (env.setClickToken) env.setClickToken(null);
    clearDrag(env);
    return { isClick: isClick, token: token, delta: delta };
  }

  global.AppTokenInteractions = {
    hitTestTokens: hitTestTokens,
    canMoveToken: canMoveToken,
    getCombatMoveRestrictionForToken: getCombatMoveRestrictionForToken,
    isSelectableHit: isSelectableHit,
    shouldUsePreviewMode: shouldUsePreviewMode,
    beginTokenDrag: beginTokenDrag,
    updateTokenDrag: updateTokenDrag,
    finishTokenDrag: finishTokenDrag,
    resolveClickToken: resolveClickToken,
  };
})(window);
