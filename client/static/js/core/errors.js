(function (global) {
  'use strict';

  let currentMessageGetter = () => '';
  let currentMessageSetter = () => {};
  let bannerId = 'client-runtime-banner';
  let handlersInstalled = false;

  function configure(options = {}) {
    if (typeof options.getCurrentMessage === 'function') currentMessageGetter = options.getCurrentMessage;
    if (typeof options.setCurrentMessage === 'function') currentMessageSetter = options.setCurrentMessage;
    if (options.bannerId) bannerId = String(options.bannerId);
  }

  function ensureRuntimeBanner() {
    let el = document.getElementById(bannerId);
    if (el) return el;
    el = document.createElement('div');
    el.id = bannerId;
    el.style.position = 'fixed';
    el.style.left = '72px';
    el.style.right = '18px';
    el.style.bottom = '18px';
    el.style.zIndex = '99999';
    el.style.display = 'none';
    el.style.padding = '10px 12px';
    el.style.border = '1px solid rgba(255,120,120,0.55)';
    el.style.background = 'rgba(48,10,10,0.92)';
    el.style.color = '#ffd6d6';
    el.style.fontSize = '13px';
    el.style.borderRadius = '10px';
    el.style.boxShadow = '0 8px 24px rgba(0,0,0,0.28)';
    document.body.appendChild(el);
    return el;
  }

  function normalizeErrorMessage(label, err) {
    return `${label}: ${err && err.message ? err.message : err}`;
  }

  function reportRuntimeError(label, err) {
    const msg = normalizeErrorMessage(label, err);
    if (currentMessageGetter() === msg) return;
    currentMessageSetter(msg);
    console.error(`[CLIENT RUNTIME] ${msg}`, err);
    const el = ensureRuntimeBanner();
    el.textContent = msg;
    el.style.display = 'block';
  }

  function clearRuntimeError() {
    currentMessageSetter('');
    const el = document.getElementById(bannerId);
    if (el) el.style.display = 'none';
  }

  function safeCall(label, fn, fallback = null) {
    try {
      return fn();
    } catch (err) {
      reportRuntimeError(label, err);
      return fallback;
    }
  }

  function installGlobalHandlers() {
    if (handlersInstalled) return;
    handlersInstalled = true;
    global.addEventListener('error', (ev) => {
      reportRuntimeError('Browser error', ev.error || ev.message || 'Unknown error');
    });
    global.addEventListener('unhandledrejection', (ev) => {
      reportRuntimeError('Promise rejection', ev.reason || 'Unhandled promise rejection');
    });
  }

  global.AppErrors = {
    configure,
    ensureRuntimeBanner,
    reportRuntimeError,
    clearRuntimeError,
    safeCall,
    installGlobalHandlers,
  };
})(window);
