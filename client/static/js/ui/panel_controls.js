(function (global) {
  'use strict';

  function getDoc(env) {
    return env?.document || global.document;
  }

  function closeMobilePanel(env) {
    if (!env?.isMobilePanelViewport?.()) return;
    const doc = getDoc(env);
    doc.getElementById('sidebar-right')?.classList.remove('mobile-panel-open');
    const mobileToggle = doc.getElementById('mobile-panel-btn');
    if (mobileToggle) mobileToggle.textContent = '☰ Panel';
  }

  function onSidebarRightClick(event, env) {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const tabTrigger = target.closest('[data-rtab-target]');
    if (tabTrigger) {
      event.preventDefault();
      const tab = tabTrigger.dataset.rtabTarget;
      closeMobilePanel(env);
      env?.switchRightTab?.(tab);
      return;
    }

    const dropdownTrigger = target.closest('[data-rtab-dropdown]');
    if (dropdownTrigger) {
      event.preventDefault();
      env?.toggleTabDropdown?.(dropdownTrigger.dataset.rtabDropdown || '');
      return;
    }

    const rosterTrigger = target.closest('[data-party-roster-view]');
    if (rosterTrigger) {
      event.preventDefault();
      env?.setPartyRosterView?.(rosterTrigger.dataset.partyRosterView || 'party');
      return;
    }

    const layoutTrigger = target.closest('[data-inventory-layout]');
    if (layoutTrigger) {
      event.preventDefault();
      env?.setInventoryLayoutMode?.(layoutTrigger.dataset.inventoryLayout || 'essentials');
      return;
    }

    const collapseTrigger = target.closest('[data-collapse-target]');
    if (collapseTrigger) {
      event.preventDefault();
      const bodyId = collapseTrigger.dataset.collapseTarget;
      if (!bodyId) return;
      const doc = getDoc(env);
      const body = doc.getElementById(bodyId);
      if (!body) return;
      const arrowId = collapseTrigger.dataset.collapseArrow || '';
      const arrow = arrowId ? doc.getElementById(arrowId) : collapseTrigger.querySelector('[data-collapse-arrow]');
      const open = body.style.display !== 'none';
      const displayMode = collapseTrigger.dataset.collapseDisplay || 'block';
      body.style.display = open ? 'none' : displayMode;
      if (arrow) arrow.textContent = open ? '▶' : '▼';
    }
  }

  function installBindings(env) {
    const doc = getDoc(env);
    const sidebar = doc.getElementById('sidebar-right');
    if (!sidebar || sidebar.dataset.panelControlsBound === '1') return false;
    sidebar.dataset.panelControlsBound = '1';
    sidebar.addEventListener('click', function (event) {
      onSidebarRightClick(event, env);
    });
    sidebar.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter' && event.key !== ' ' && event.key !== 'Spacebar') return;
      const collapseTrigger = event.target.closest('.panel-collapse-toggle[data-collapse-target]');
      if (collapseTrigger) {
        event.preventDefault();
        collapseTrigger.click();
      }
    });
    return true;
  }

  function init(env) {
    installBindings(env);
  }

  global.AppUIPanelControls = {
    init,
    installBindings,
  };
})(window);
