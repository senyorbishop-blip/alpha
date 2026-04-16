(function (global) {
  'use strict';

  // Stage 6 right-sidebar tabs owner:
  // - owns tab registry, tab visibility, switching, dropdown open/close behavior,
  //   and badge sync through env-driven compatibility wrappers from play.html
  // - deliberately does NOT own pane-specific rendering logic, which remains inline
  //   in play.html during this migration stage
  //
  // Role/scope helpers (isRole, getAssistantScopes, hasAssistantScope,
  // canUsePlayerTabs, canUseDmLibraryTabs) are env-based analogues of the
  // raw-param helpers in role_access.js (RoleAccessHelpers).  They are kept
  // here rather than delegating to RoleAccessHelpers because they operate
  // on the env contract (env.getRole(), env.getAssistantScopes()), not on
  // bare role strings.  The two sets of helpers share identical semantics.

  const TAB_REGISTRY = [
    { id: 'party', label: 'Party', paneSelector: '#rtab-pane-party', buttonSelector: '#rtab-party', order: 10, group: 'core', supportsBadge: true, isVisible: () => true },
    { id: 'inventory', label: 'Inventory', paneSelector: '#rtab-pane-inventory', buttonSelector: '#rtab-inventory', order: 20, group: 'core', supportsBadge: true, isVisible: (env) => canUsePlayerTabs(env) },
    { id: 'log', label: 'Chat', paneSelector: '#rtab-pane-log', buttonSelector: '#rtab-log', order: 30, group: 'core', supportsBadge: true, isVisible: () => true },
    { id: 'memory', label: 'Moments', paneSelector: '#rtab-pane-memory', buttonSelector: '#rtab-memory', order: 40, group: 'core', supportsBadge: true, isVisible: (env) => canUsePlayerTabs(env) },
    { id: 'combat', label: 'Combat', paneSelector: '#rtab-pane-combat', buttonSelector: '#rtab-combat', order: 50, group: 'core', supportsBadge: true, isVisible: () => true },
    { id: 'shop', label: 'Shop', paneSelector: '#rtab-pane-shop', buttonSelector: '#rtab-shop', order: 60, group: 'library', supportsBadge: true, isVisible: (env) => canUseDmLibraryTabs(env) },
    { id: 'bestiary', label: 'Bestiary', paneSelector: '#rtab-pane-bestiary', buttonSelector: '#rtab-bestiary', order: 70, group: 'library', supportsBadge: true, isVisible: (env) => canUseDmLibraryTabs(env) },
    { id: 'spelllib', label: 'Spells', paneSelector: '#rtab-pane-spelllib', buttonSelector: '#rtab-spelllib', order: 80, group: 'library', supportsBadge: true, isVisible: (env) => canUsePlayerTabs(env) },
    {
      id: 'handouts',
      label: 'Handouts',
      paneSelector: '#rtab-pane-handouts',
      buttonSelector: '#rtab-handouts',
      order: 90,
      group: 'library',
      supportsBadge: true,
      isVisible: (env) => hasAssistantScope(env, 'handouts.manage') || hasAssistantScope(env, 'quests.manage') || !!env?.isHandoutsTabVisible?.(),
    },
  ];

  const DROPDOWN_DEFS = {
    library: {
      triggerSelector: '#rtab-dropdown-library',
      menuSelector: '#rtab-menu-library',
    },
  };

  const CONTEXT_DEFAULT = {
    key: 'neutral',
    label: 'Default',
    detail: 'No active selection',
    recommendedTab: 'party',
    strong: false,
    focusTabs: ['party', 'log'],
  };

  function getDoc(env) {
    return env?.document || global.document;
  }

  function isRole(env, role) {
    return String(env?.getRole?.() || 'viewer').toLowerCase() === String(role || '').toLowerCase();
  }

  function getAssistantScopes(env) {
    return new Set((env?.getAssistantScopes?.() || []).map((scope) => String(scope || '').trim()).filter(Boolean));
  }

  function hasAssistantScope(env, scope) {
    if (!isRole(env, 'assistant_dm')) return false;
    return getAssistantScopes(env).has(String(scope || '').trim());
  }

  function canUsePlayerTabs(env) {
    return !isRole(env, 'viewer');
  }

  function canUseDmLibraryTabs(env) {
    return isRole(env, 'dm');
  }

  function getEntry(tabId) {
    return TAB_REGISTRY.find((entry) => entry.id === String(tabId || '')) || null;
  }

  function hasValidMount(entry, env) {
    if (!entry) return false;
    const doc = getDoc(env);
    if (!doc) return false;
    const btn = doc.querySelector(entry.buttonSelector);
    const pane = doc.querySelector(entry.paneSelector);
    return !!(btn && pane);
  }

  function listVisibleTabs(env) {
    return TAB_REGISTRY
      .filter((entry) => {
        if (typeof entry.isVisible !== 'function') return true;
        if (!entry.isVisible(env)) return false;
        return hasValidMount(entry, env);
      })
      .sort((a, b) => Number(a.order || 0) - Number(b.order || 0));
  }

  function getVisibleTabIds(env) {
    return new Set(listVisibleTabs(env).map((entry) => entry.id));
  }

  function getDefaultTab(env) {
    const preferred = String(env?.getDefaultTab?.() || 'party');
    const visible = listVisibleTabs(env);
    if (!visible.length) return 'party';
    return visible.some((entry) => entry.id === preferred) ? preferred : visible[0].id;
  }

  function normalizeTab(tab) {
    return String(tab || 'party');
  }

  function normalizeAllowedTab(tab, env) {
    const requested = normalizeTab(tab);
    const visibleIds = getVisibleTabIds(env);
    if (visibleIds.has(requested)) return requested;
    return getDefaultTab(env);
  }

  function getActiveTab(env) {
    return normalizeAllowedTab(env?.getActiveTab?.() || getDefaultTab(env), env);
  }

  function getUnreadLog(env) {
    return Math.max(0, Number(env?.getUnreadLog?.() || 0));
  }

  function getPanelContext(env) {
    const raw = env?.getPanelContext?.();
    if (!raw || typeof raw !== 'object') return CONTEXT_DEFAULT;
    const recommendedTab = normalizeAllowedTab(raw.recommendedTab || CONTEXT_DEFAULT.recommendedTab, env);
    const focusTabsRaw = Array.isArray(raw.focusTabs) ? raw.focusTabs : CONTEXT_DEFAULT.focusTabs;
    const focusTabs = focusTabsRaw
      .map((tab) => normalizeAllowedTab(tab, env))
      .filter((tab, idx, arr) => arr.indexOf(tab) === idx);
    return {
      key: String(raw.key || CONTEXT_DEFAULT.key),
      label: String(raw.label || CONTEXT_DEFAULT.label),
      detail: String(raw.detail || CONTEXT_DEFAULT.detail),
      recommendedTab,
      strong: !!raw.strong,
      focusTabs: focusTabs.length ? focusTabs : [recommendedTab],
    };
  }

  function updateLogBadge(env) {
    const doc = getDoc(env);
    const unread = getUnreadLog(env);
    const badge = doc.getElementById('rtab-log-badge');
    if (!badge) return;
    badge.textContent = unread > 9 ? '9+' : (unread > 0 ? String(unread) : '');
    badge.classList.toggle('show', unread > 0);
  }

  function applyContextUI(env) {
    const doc = getDoc(env);
    const context = getPanelContext(env);
    const activeTab = getActiveTab(env);
    const bar = doc.getElementById('right-tab-bar');
    if (bar) bar.dataset.context = context.key;
    const chip = doc.getElementById('right-panel-context-chip');
    const label = doc.getElementById('right-panel-context-label');
    const detail = doc.getElementById('right-panel-context-detail');
    if (chip) {
      chip.textContent = context.label;
      chip.classList.toggle('strong', !!context.strong);
    }
    if (label) label.textContent = context.strong ? 'Active Context' : 'Panel Context';
    if (detail) detail.textContent = context.detail;

    const focusSet = new Set(context.focusTabs || []);
    TAB_REGISTRY.forEach((entry) => {
      const btn = doc.querySelector(entry.buttonSelector);
      if (!btn) return;
      btn.classList.remove('context-priority', 'context-muted');
      if (entry.id === activeTab && entry.id === context.recommendedTab) btn.classList.add('context-priority');
      if (context.strong && !focusSet.has(entry.id) && entry.id !== activeTab) btn.classList.add('context-muted');
    });

    const shouldAutoFocus = !!(
      context.strong &&
      env?.shouldAutoFocusContext?.() &&
      context.recommendedTab !== activeTab &&
      getVisibleTabIds(env).has(context.recommendedTab)
    );

    if (shouldAutoFocus) {
      env.setActiveTab?.(context.recommendedTab);
      env.syncShellState?.();
      env.markContextAutoFocus?.(context);
      syncTabUI(env);
      if (context.recommendedTab === 'combat') {
        const badge = doc.getElementById('rtab-combat-badge');
        if (badge) {
          badge.textContent = '!';
          badge.classList.add('show');
        }
      }
    }
  }

  function setVisible(node, visible) {
    if (!node) return;
    node.hidden = !visible;
    node.style.display = visible ? '' : 'none';
  }

  function isRendered(node) {
    if (!node || node.hidden) return false;
    return global.getComputedStyle(node).display !== 'none';
  }

  function syncDropdownVisibility(env) {
    const doc = getDoc(env);
    Object.values(DROPDOWN_DEFS).forEach((def) => {
      const trigger = doc.querySelector(def.triggerSelector);
      const menu = doc.querySelector(def.menuSelector);
      if (!trigger || !menu) return;
      const visibleItems = Array.from(menu.querySelectorAll('.rtab-dropdown-item')).filter((item) => isRendered(item));
      const hasVisibleItems = visibleItems.length > 0;
      const wrap = trigger.closest('.rtab-dropdown-wrap');
      setVisible(wrap, hasVisibleItems);
      setVisible(trigger, hasVisibleItems);
      if (!hasVisibleItems) {
        trigger.classList.remove('active-dropdown');
        menu.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
      } else {
        trigger.classList.toggle('active-dropdown', menu.classList.contains('open'));
        trigger.setAttribute('aria-expanded', menu.classList.contains('open') ? 'true' : 'false');
      }
    });
  }

  function alignPaneScroll(tab, env) {
    const doc = getDoc(env);
    const pane = doc.getElementById(`rtab-pane-${tab}`);
    if (!pane) return;
    if (tab === 'log') return;
    pane.scrollTop = 0;
  }

  function syncTabUI(env) {
    const doc = getDoc(env);
    const visibleIds = getVisibleTabIds(env);
    let activeTab = getActiveTab(env);
    if (!visibleIds.has(activeTab)) {
      activeTab = getDefaultTab(env);
      env.setActiveTab?.(activeTab);
      env.syncShellState?.();
    }

    TAB_REGISTRY.forEach((entry) => {
      const isVisible = visibleIds.has(entry.id);
      const isActive = entry.id === activeTab;
      const btn = doc.querySelector(entry.buttonSelector);
      if (btn) {
        setVisible(btn, isVisible);
        btn.classList.toggle('active', isVisible && isActive);
        btn.setAttribute('aria-selected', isVisible && isActive ? 'true' : 'false');
      }
      const pane = doc.querySelector(entry.paneSelector);
      if (pane) {
        setVisible(pane, isVisible);
        pane.classList.toggle('active', isVisible && isActive);
        pane.setAttribute('aria-hidden', isVisible && isActive ? 'false' : 'true');
      }
    });

    syncDropdownVisibility(env);

    const shell = doc.getElementById('sidebar-right');
    if (shell) shell.dataset.activeTab = activeTab;

    updateLogBadge(env);
    applyContextUI(env);
  }

  function closeAllDropdowns(env) {
    const doc = getDoc(env);
    doc.querySelectorAll('.rtab-dropdown-menu').forEach((menu) => menu.classList.remove('open'));
    doc.querySelectorAll('.rtab-dropdown-btn').forEach((btn) => {
      btn.setAttribute('aria-expanded', 'false');
      btn.classList.remove('active-dropdown');
    });
  }

  function toggleDropdown(env, menuId) {
    const doc = getDoc(env);
    const menu = doc.getElementById(menuId);
    if (!menu) return;
    const isOpen = menu.classList.contains('open');
    closeAllDropdowns(env);
    if (!isOpen) {
      menu.classList.add('open');
      const trigger = menu.parentElement?.querySelector('.rtab-dropdown-btn');
      if (trigger) {
        trigger.setAttribute('aria-expanded', 'true');
        trigger.classList.add('active-dropdown');
      }
    }
  }

  function switchRTab(env, tab) {
    tab = normalizeAllowedTab(tab, env);
    env.noteManualTabSwitch?.(tab);
    env.setActiveTab?.(tab);
    env.syncShellState?.();
    closeAllDropdowns(env);
    syncTabUI(env);
    alignPaneScroll(tab, env);
    const doc = getDoc(env);
    if (tab === 'shop') env.renderShopLedger?.();
    if (tab === 'bestiary') env.bestiaryLoad?.();
    if (tab === 'spelllib') {
      const customBtn = doc.getElementById('sl-custom-btn');
      if (customBtn) customBtn.style.display = env.getRole?.() === 'dm' ? 'block' : 'none';
      if (!env.getSpellLibraryLength?.()) env.spellLibRefresh?.();
      else env.renderSpellLibrary?.();
    }
    if (tab === 'log') {
      env.setUnreadLog?.(0);
      const badge = doc.getElementById('rtab-log-badge');
      if (badge) {
        badge.textContent = '';
        badge.classList.remove('show');
      }
      const feed = doc.getElementById('log-feed');
      if (feed) feed.scrollTop = feed.scrollHeight;
    }
    if (tab === 'memory') {
      env.clearUnreadMemory?.();
      const badge = doc.getElementById('rtab-memory-badge');
      if (badge) {
        badge.textContent = '';
        badge.classList.remove('show');
      }
      const addRow = doc.getElementById('memory-add-row');
      if (addRow) addRow.style.display = env.getRole?.() === 'dm' ? 'flex' : 'none';
    }
  }

  function bumpLogBadge(env) {
    if (getActiveTab(env) === 'log') return;
    const unread = getUnreadLog(env) + 1;
    env.setUnreadLog?.(unread);
    env.syncShellState?.();
    updateLogBadge(env);
  }

  function installBindings(env) {
    const doc = getDoc(env);
    if (doc.body?.dataset.uiTabsBound === '1') return false;
    if (doc.body) doc.body.dataset.uiTabsBound = '1';
    doc.addEventListener('click', function (event) {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.closest('#right-tab-bar')) closeAllDropdowns(env);
    });
    doc.addEventListener('click', function (event) {
      if (event.defaultPrevented) return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      const tabTrigger = target.closest('[data-rtab-target]');
      if (tabTrigger) {
        event.preventDefault();
        switchRTab(env, tabTrigger.dataset.rtabTarget || 'party');
        return;
      }
      const dropdownTrigger = target.closest('[data-rtab-dropdown]');
      if (dropdownTrigger) {
        event.preventDefault();
        toggleDropdown(env, dropdownTrigger.dataset.rtabDropdown || '');
      }
    });
    doc.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closeAllDropdowns(env);
        return;
      }
      const btn = event.target.closest('.rtab-dropdown-btn');
      if (btn && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        const menuId = btn.dataset.menuId;
        if (menuId) toggleDropdown(env, menuId);
      }
    });
    return true;
  }

  function init(env) {
    installBindings(env);
    syncTabUI(env);
  }

  global.AppUITabs = {
    TAB_REGISTRY,
    init,
    installBindings,
    closeAllDropdowns,
    toggleDropdown,
    switchRTab,
    bumpLogBadge,
    syncTabUI,
    alignPaneScroll,
    // Exported so callers that only need raw tab-id normalization (no visibility
    // filtering) can use the same canonical implementation without reimplementing
    // the String-coerce-and-default-to-'party' logic.
    normalizeTab,
  };
})(window);
