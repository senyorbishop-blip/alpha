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
    // Always return document as root — mode buttons, context shell, and legacy
    // panels are siblings at the top level, not nested under a single ancestor.
    // Returning a specific element like #dm-assistant-host or #sidebar-left
    // means bridge.init() can't find buttons/panels that live elsewhere.
    return document;
  }

  function hasDmOnlyAnchor(root) {
    if (!root || typeof root.querySelector !== 'function') return false;
    if (root.matches && (root.matches('[data-dm-map-first-root]') || root.matches('[data-dm-panel-root]'))) return true;
    return Boolean(
      root.querySelector('[data-dm-map-first-root], [data-dm-panel-root], #dm-mode-switch, #flyout-editor, #dm-assistant-host')
    );
  }

  function isDisabled() {
    if (window.__DISABLE_DM_MAP_FIRST === true) return true;
    try {
      if (new URLSearchParams(window.location.search).get('disable_dm_map_first') === '1') return true;
      return String(window.localStorage && window.localStorage.getItem('disableDmMapFirst') || '') === '1';
    } catch (_err) { return false; }
  }

  function init() {
    try {
      if (isDisabled()) {
        window.__DISABLE_DM_MAP_FIRST = true;
        window.__dmMapFirstBootstrap = Object.freeze({ initialized: false, disabled: true, role: getBootRole() });
        return null;
      }
      if (window.__DM_MAP_FIRST_CAN_ENHANCE !== true) {
        window.__dmMapFirstBootstrap = Object.freeze({ initialized: false, deferred: true, role: getBootRole() });
        return null;
      }
      if (!isDmRole()) return null;
      const root = findDmRoot();
      if (!hasDmOnlyAnchor(root)) return null;
      const bridge = window.AppUIDMPanelModeBridge;
      if (!bridge || typeof bridge.init !== 'function') return null;
      // Ensure the mode rail and context shell are visible before wiring buttons.
      const rail = document.getElementById('dm-live-mode-rail');
      const shell = document.getElementById('dm-context-shell');
      const strip = document.getElementById('dm-map-first-quick-strip');
      if (rail) rail.hidden = false;
      if (shell) shell.hidden = false;
      if (strip) strip.hidden = false;
      // Explicitly hide legacy right-panel tabs and panes — CSS alone can lose the
      // race if dm-map-first-active is applied after the tab bar is already shown.
      const tabBar = document.getElementById('right-tab-bar');
      if (tabBar) tabBar.style.setProperty('display', 'none', 'important');
      const legacySelectors = [
        '#sidebar-right .rtab-pane',
        '#sidebar-right .rtab-shell',
        '#sidebar-right #right-panel-context',
        '#sidebar-right #combat-list',
        '#sidebar-right #combat-controls',
      ];
      document.querySelectorAll(legacySelectors.join(',')).forEach(function(el) {
        el.style.setProperty('visibility', 'hidden', 'important');
        el.style.setProperty('pointer-events', 'none', 'important');
        el.style.position = 'fixed';
        el.style.left = '-9999px';
        el.style.top = '-9999px';
      });
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
    if (isDisabled()) {
      window.__DISABLE_DM_MAP_FIRST = true;
      window.__dmMapFirstBootstrap = Object.freeze({ initialized: false, disabled: true, role: getBootRole() });
      return;
    }
    // DM map-first enhancements are intentionally not run during initial
    // DOMContentLoaded boot. Core boot, WebSocket connect, request_state/state
    // sync, and first render must win; play.html enables
    // __DM_MAP_FIRST_CAN_ENHANCE after state_sync and then calls refresh().
    window.__dmMapFirstBootstrap = Object.freeze({ initialized: false, deferred: true, role: getBootRole() });
  }

  window.AppUIDMMapFirstBootstrap = Object.freeze({
    init,
    findDmRoot,
    getBootRole,
    isDmRole,
  });

  scheduleInit();
})();
