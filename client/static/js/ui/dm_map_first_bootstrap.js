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
      // Hide the legacy panes WITHOUT inline `!important`. The steady-state CSS
      // (dm-map-first-fixes.css FIX 9, scoped to :not(.dm-legacy-drawer-open))
      // already pins them off-screen with `!important`, so these inline styles
      // only need to win the brief boot flash before that CSS settles. Crucially,
      // they must remain *overridable*: when the DM opens a compact legacy drawer
      // the FIX 8 rule promotes the active pane to `visibility:visible !important;
      // pointer-events:auto !important`, and an inline `!important` here would beat
      // that (author inline !important > author stylesheet !important), leaving the
      // drawer present-but-invisible and unclickable. Plain inline values yield to
      // the stylesheet `!important`, so the drawer shows and stays interactive.
      document.querySelectorAll(legacySelectors.join(',')).forEach(function(el) {
        el.style.setProperty('visibility', 'hidden');
        el.style.setProperty('pointer-events', 'none');
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

  // Self-healing: if init() is called before the bridge script has loaded,
  // retry up to 5 times with 200ms spacing rather than silently failing.
  function initWithRetry(attempt) {
    attempt = attempt || 1;
    const bridge = window.AppUIDMPanelModeBridge;
    const renderer = window.AppUIDMContextRender;
    if (!bridge || typeof bridge.init !== 'function' || !renderer || typeof renderer.render !== 'function') {
      if (attempt < 6) {
        console.info('[dm-map-first] bridge not ready, retrying in 200ms (attempt ' + attempt + ')');
        setTimeout(function() { initWithRetry(attempt + 1); }, 200);
      } else {
        console.warn('[dm-map-first] giving up after 5 retries — bridge or renderer never loaded');
      }
      return null;
    }
    return init();
  }

  // Diagnostic helper — run in browser console to see why panel isn't working
  function diagnose() {
    var d = {
      role: getBootRole(),
      isDm: isDmRole(),
      disabled: isDisabled(),
      canEnhance: window.__DM_MAP_FIRST_CAN_ENHANCE,
      bootstrapState: JSON.stringify(window.__dmMapFirstBootstrap || {}),
      bridgeLoaded: !!(window.AppUIDMPanelModeBridge && typeof window.AppUIDMPanelModeBridge.init === 'function'),
      rendererLoaded: !!(window.AppUIDMContextRender && typeof window.AppUIDMContextRender.render === 'function'),
      bodyHasActiveClass: document.body.classList.contains('dm-map-first-active'),
      railHidden: !!(document.getElementById('dm-live-mode-rail') || {hidden:true}).hidden,
      shellHidden: !!(document.getElementById('dm-context-shell') || {hidden:true}).hidden,
      modeButtonCount: document.querySelectorAll('[data-dm-mode-button]').length,
      richContextLen: (document.getElementById('dm-rich-context') || {innerHTML:''}).innerHTML.length,
      contextTitle: (document.getElementById('dm-context-title') || {textContent:'?'}).textContent,
      tabBarDisplay: getComputedStyle(document.getElementById('right-tab-bar') || document.body).display,
    };
    console.table(d);
    return d;
  }

  window.AppUIDMMapFirstBootstrap = Object.freeze({
    init,
    initWithRetry,
    diagnose,
    findDmRoot,
    getBootRole,
    isDmRole,
  });

  scheduleInit();
})();
