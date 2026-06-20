(function(){try{if(window.__PLAY_BOOT_ROLE==='player'){window.__playerBootState=window.__playerBootState||{};window.__playerBootState.scriptsStarted=true;if(window.__playerBootCheckpoint)window.__playerBootCheckpoint('PLAYER_BOOT_FIRST_SCRIPT');}}catch(_e){}})();
(function (global) {
  'use strict';

  // ───────────────────────────────────────────────────────────────────────────
  // Client diagnostics: freeze watchdog, boot phase tracking, and safe mode.
  //
  // This module is intentionally tiny and dependency-free so it can load FIRST,
  // before any heavy gameplay/render code. Its whole job is to make a frozen
  // player browser observable (so the websocket heartbeat starvation is no longer
  // a mystery) and to provide a "safe mode" that disables the heavy subsystems.
  // ───────────────────────────────────────────────────────────────────────────

  const VERSION = 'diagnostics-v1';

  // ── Safe mode ──────────────────────────────────────────────────────────────
  // ?safe=1 disables the heavy systems one switch at a time so a frozen player
  // page can be brought back to life and the offending system re-enabled.
  let SAFE = false;
  try {
    const params = new global.URLSearchParams(global.location.search || '');
    SAFE = params.get('safe') === '1' || params.get('safe') === 'true';
  } catch (_err) {
    SAFE = false;
  }

  // Features disabled by safe mode. Individual systems consult this so safe mode
  // is a single source of truth.
  const SAFE_DISABLED = new Set([
    'audio',
    'audio-preload',
    'dice3d',
    'fog-animation',
    'map-effects',
    'vision-overlay',
    'quick-actions-autobuild',
    'map-library-import',
    'tts-polling',
    'character-builder-preload',
    'prop-library',
  ]);

  const AppSafeMode = {
    enabled: SAFE,
    isOn() { return SAFE; },
    // Returns true when the named feature must stay disabled this session.
    disabled(feature) { return SAFE && SAFE_DISABLED.has(String(feature || '')); },
  };
  global.AppSafeMode = AppSafeMode;
  global.SAFE_MODE = SAFE;

  // ── Boot phase tracking ────────────────────────────────────────────────────
  // currentPhase is updated synchronously right before heavy work begins, so when
  // the freeze watchdog fires (after the main thread unblocks) it can name the
  // phase that was running when the event loop stalled.
  // Tracks which `console.time('[BOOT] x')` timers are open so `console.timeEnd`
  // is never called for a label that was never started (which logs a warning).
  const _openTimers = new Set();
  function _timeStart(label) {
    try {
      if (_openTimers.has(label)) return;
      _openTimers.add(label);
      console.time(label);
    } catch (_err) {}
  }
  function _timeEnd(label) {
    try {
      if (!_openTimers.has(label)) return;
      _openTimers.delete(label);
      console.timeEnd(label);
    } catch (_err) {}
  }

  const AppBoot = {
    currentPhase: 'idle',
    startedAt: (global.performance && global.performance.now) ? global.performance.now() : Date.now(),
    _seen: Object.create(null),

    // Logs `[BOOT] <name> <state>`, tracks the active phase, and emits matching
    // `console.time`/`console.timeEnd` pairs (e.g. `[BOOT] state_sync`,
    // `[BOOT] map render`, `[BOOT] token render`) so each boot phase is timed.
    phase(name, state) {
      const label = String(name || 'phase');
      const timerLabel = `[BOOT] ${label}`;
      const st = state ? String(state) : '';
      if (st === 'start') {
        this.currentPhase = label;
        _timeStart(timerLabel);
      } else if (st === 'end') {
        if (this.currentPhase === label) this.currentPhase = 'idle';
        _timeEnd(timerLabel);
      }
      console.info('[BOOT]', st ? `${label} ${st}` : label);
    },

    // Cheap synchronous marker (no logging) for hot paths that still want to
    // record what they are doing so the watchdog can report it.
    mark(name) {
      this.currentPhase = String(name || 'idle');
    },

    // Runs fn wrapped in start/end phase logs and a try/catch so a throwing
    // startup/render module cannot take down the websocket heartbeat.
    scope(name, fn) {
      this.phase(name, 'start');
      try {
        return fn();
      } catch (err) {
        console.error(`[BOOT] ${name} threw — continuing so heartbeat survives`, err);
        return undefined;
      } finally {
        this.phase(name, 'end');
      }
    },

    done() {
      this.currentPhase = 'idle';
      // Close any still-open phase timers, then the overall total.
      Array.from(_openTimers).forEach((label) => { if (label !== '[BOOT] total') _timeEnd(label); });
      _timeEnd('[BOOT] total');
      console.info('[BOOT] done');
    },
  };
  global.AppBoot = AppBoot;

  _timeStart('[BOOT] total');
  console.info('[BOOT] start', VERSION, SAFE ? '(SAFE MODE)' : '');

  // ── Freeze watchdog ────────────────────────────────────────────────────────
  // A 1s interval measures event-loop lag. The interval callback cannot run while
  // the main thread is blocked, so a large gap between expected and actual fire
  // time is direct evidence of a freeze. We log every tick at debug level and
  // escalate to an error (naming the active phase) when lag crosses the freeze
  // threshold.
  const TICK_MS = 1000;
  // Per spec: a measured event-loop delay over 1000ms is a freeze.
  const FREEZE_THRESHOLD_MS = 1000;
  let expected = (global.performance && global.performance.now) ? global.performance.now() : Date.now();

  function now() {
    return (global.performance && global.performance.now) ? global.performance.now() : Date.now();
  }

  function tick() {
    const actual = now();
    const lag = Math.max(0, Math.round(actual - expected));
    expected = now() + TICK_MS;
    if (lag > FREEZE_THRESHOLD_MS) {
      console.error(
        `[FREEZE WATCHDOG] lag_ms=${lag} current_phase=${AppBoot.currentPhase}`,
        { renderPhase: global.__appRenderPhase || 'unknown' }
      );
    } else {
      console.debug(`[FREEZE WATCHDOG] lag_ms=${lag} current_phase=${AppBoot.currentPhase}`);
    }
  }

  function startWatchdog() {
    expected = now() + TICK_MS;
    global.setInterval(tick, TICK_MS);
  }

  if (global.document && global.document.readyState === 'loading') {
    global.document.addEventListener('DOMContentLoaded', startWatchdog, { once: true });
  } else {
    startWatchdog();
  }

  global.AppDiagnostics = { version: VERSION, AppBoot, AppSafeMode };
})(window);
