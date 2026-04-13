(function (global) {
  'use strict';

  function clamp(value, min, max) {
    const num = Number(value);
    if (!Number.isFinite(num)) return Number.isFinite(min) ? min : 0;
    const lo = Number.isFinite(min) ? min : num;
    const hi = Number.isFinite(max) ? max : num;
    return Math.max(lo, Math.min(hi, num));
  }

  function safeNumber(value, fallback = 0) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
  }

  function distance(ax, ay, bx, by) {
    const dx = safeNumber(bx) - safeNumber(ax);
    const dy = safeNumber(by) - safeNumber(ay);
    return Math.hypot(dx, dy);
  }

  function distanceSq(ax, ay, bx, by) {
    const dx = safeNumber(bx) - safeNumber(ax);
    const dy = safeNumber(by) - safeNumber(ay);
    return dx * dx + dy * dy;
  }

  function makeId(prefix = 'id') {
    const rand = Math.random().toString(36).slice(2, 10);
    return `${prefix}-${Date.now().toString(36)}-${rand}`;
  }

  function debounce(fn, wait = 0) {
    let timer = null;
    return function debounced(...args) {
      const ctx = this;
      clearTimeout(timer);
      timer = global.setTimeout(() => fn.apply(ctx, args), wait);
    };
  }

  function throttle(fn, wait = 0) {
    let last = 0;
    let timer = null;
    let trailingArgs = null;
    let trailingCtx = null;
    return function throttled(...args) {
      const now = Date.now();
      const remaining = wait - (now - last);
      trailingArgs = args;
      trailingCtx = this;
      if (remaining <= 0) {
        last = now;
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
        fn.apply(trailingCtx, trailingArgs);
        trailingArgs = null;
        trailingCtx = null;
        return;
      }
      if (!timer) {
        timer = global.setTimeout(() => {
          last = Date.now();
          timer = null;
          if (trailingArgs) {
            fn.apply(trailingCtx, trailingArgs);
            trailingArgs = null;
            trailingCtx = null;
          }
        }, remaining);
      }
    };
  }

  function parseJsonSafe(text, fallback = null) {
    try {
      return JSON.parse(text);
    } catch (_err) {
      return fallback;
    }
  }

  function escHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function pointSegmentDistanceSquared(px, py, ax, ay, bx, by) {
    const abx = safeNumber(bx) - safeNumber(ax);
    const aby = safeNumber(by) - safeNumber(ay);
    if (abx === 0 && aby === 0) return distanceSq(px, py, ax, ay);
    const apx = safeNumber(px) - safeNumber(ax);
    const apy = safeNumber(py) - safeNumber(ay);
    const t = clamp((apx * abx + apy * aby) / (abx * abx + aby * aby), 0, 1);
    const cx = safeNumber(ax) + abx * t;
    const cy = safeNumber(ay) + aby * t;
    return distanceSq(px, py, cx, cy);
  }

  global.AppUtils = {
    clamp,
    safeNumber,
    distance,
    distanceSq,
    makeId,
    debounce,
    throttle,
    parseJsonSafe,
    escHtml,
    pointSegmentDistanceSquared,
  };
})(window);
