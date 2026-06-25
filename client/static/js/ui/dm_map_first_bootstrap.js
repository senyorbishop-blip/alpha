(function () {
  'use strict';

  const DM_ROOT_SELECTORS = [
    '[data-dm-map-first-root]',
    '[data-dm-panel-root]',
    '#dm-map-first-root',
    '#dm-assistant-host',
    '#sidebar-left',
  ];

  function normalizeRole(value) {
    return String(value || '').trim().toLowerCase();
  }

  function roleFromUrl() {
    try {
      return normalizeRole(new URLSearchParams(window.location.search).get('role'));
    } catch (_err) {
      return '';
    }
  }

  function getBootRole() {
    return normalizeRole(window.__PLAY_BOOT_ROLE || window.PLAY_ROLE || window.ROLE || roleFromUrl());
  }

  function isDmRole() {
    return getBootRole() === 'dm';
  }

  function findDmRoot() {
    if (!document || typeof document.querySelector !== 'function') return null;
    for (const selector of DM_ROOT_SELECTORS) {
      const root = document.querySelector(selector);
      if (root) return root;
    }
    return null;
  }

  function hasDmOnlyAnchor(root) {
    if (!root || typeof root.querySelector !== 'function') return false;
    if (root.matches && (root.matches('[data-dm-map-first-root]') || root.matches('[data-dm-panel-root]'))) return true;
    return Boolean(
      root.querySelector('[data-dm-map-first-root], [data-dm-panel-root], #dm-mode-switch, #flyout-editor, #dm-assistant-host')
    );
  }

  function init() {
    try {
      if (!isDmRole()) return null;
      const root = findDmRoot();
      if (!hasDmOnlyAnchor(root)) return null;
      const bridge = window.AppUIDMPanelModeBridge;
      if (!bridge || typeof bridge.init !== 'function') return null;
      const result = bridge.init(root);
      window.__dmMapFirstBootstrap = Object.freeze({ initialized: true, role: getBootRole() });
      return result;
    } catch (err) {
      window.__dmMapFirstBootstrap = Object.freeze({ initialized: false, error: String((err && err.message) || err || 'unknown') });
      if (window.console && typeof window.console.warn === 'function') {
        window.console.warn('[dm-map-first-bootstrap] skipped', err);
      }
      return null;
    }
  }

  function scheduleInit() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init, { once: true });
      return;
    }
    init();
  }

  window.AppUIDMMapFirstBootstrap = Object.freeze({
    init,
    findDmRoot,
    getBootRole,
    isDmRole,
  });

  scheduleInit();
})();
