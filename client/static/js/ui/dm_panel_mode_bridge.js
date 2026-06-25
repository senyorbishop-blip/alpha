(function () {
  'use strict';

  const FALLBACK_MODE = 'run';
  const MODE_ACTIVE_CLASS = 'dm-panel-mode-active';
  const MODE_INACTIVE_CLASS = 'dm-panel-mode-inactive';
  const SECTION_SELECTOR = '[data-dm-mode], [data-dm-tool], [data-dm-section]';

  function registry() {
    return window.AppUIDMModeToolRegistry || {};
  }

  function registryModes() {
    const source = registry().modes || {};
    return Object.keys(source).length ? source : {
      run: { label: 'Live Table', primaryTools: [] },
      combat: { label: 'Combat', primaryTools: [] },
      'map-build': { label: 'Map Build', primaryTools: [] },
      'npc-monster': { label: 'NPC / Monster', primaryTools: [] },
      'loot-shop': { label: 'Loot / Shop', primaryTools: [] },
      'session-tools': { label: 'Session Tools', primaryTools: [] },
      'viewer-powers': { label: 'Viewer Powers', primaryTools: [] },
      debug: { label: 'Debug', primaryTools: [], closedByDefault: true },
    };
  }

  function cloneModeConfig(id, config) {
    const safeConfig = config || {};
    return {
      id,
      label: safeConfig.label || id,
      purpose: safeConfig.purpose || '',
      primaryTools: Array.from(safeConfig.primaryTools || []),
      keepOut: Array.from(safeConfig.keepOut || []),
      closedByDefault: Boolean(safeConfig.closedByDefault),
    };
  }

  function listModes() {
    const modeEntries = Object.entries(registryModes());
    return modeEntries.map(([id, config]) => cloneModeConfig(id, config));
  }

  function normalizeMode(modeId) {
    const modes = registryModes();
    return Object.prototype.hasOwnProperty.call(modes, modeId) ? modeId : FALLBACK_MODE;
  }

  function getModeConfig(modeId) {
    const safeMode = normalizeMode(modeId);
    return cloneModeConfig(safeMode, registryModes()[safeMode]);
  }

  function findModeForTool(toolId) {
    if (!toolId) return FALLBACK_MODE;
    const match = listModes().find((mode) => mode.primaryTools.includes(toolId));
    return match ? match.id : FALLBACK_MODE;
  }

  function classifyElement(element) {
    if (!element || !element.dataset) {
      return getModeConfig(FALLBACK_MODE);
    }
    if (element.dataset.dmMode) {
      return getModeConfig(element.dataset.dmMode);
    }
    if (element.dataset.dmTool) {
      return getModeConfig(findModeForTool(element.dataset.dmTool));
    }
    if (element.dataset.dmSection) {
      return getModeConfig(element.dataset.dmSection);
    }
    return getModeConfig(FALLBACK_MODE);
  }

  function applySectionState(element, activeMode) {
    const sectionMode = classifyElement(element).id;
    const isActive = sectionMode === activeMode;
    element.dataset.dmResolvedMode = sectionMode;
    element.dataset.dmModeActive = String(isActive);
    element.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    element.classList.toggle(MODE_ACTIVE_CLASS, isActive);
    element.classList.toggle(MODE_INACTIVE_CLASS, !isActive);
    element.hidden = !isActive;
  }

  function registerPanelSection(element, modeId) {
    if (!element || !element.dataset) return null;
    element.dataset.dmMode = normalizeMode(modeId || classifyElement(element).id);
    return element;
  }

  function activateMode(root, modeId) {
    const safeRoot = root || document;
    const activeMode = normalizeMode(modeId);
    const sections = Array.from(safeRoot.querySelectorAll(SECTION_SELECTOR));
    sections.forEach((section) => applySectionState(section, activeMode));
    safeRoot.querySelectorAll('[data-dm-mode-button]').forEach((button) => {
      const isActive = normalizeMode(button.dataset.dmModeButton) === activeMode;
      button.dataset.dmModeActive = String(isActive);
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
    const activeConfig = getModeConfig(activeMode);
    const title = safeRoot.getElementById ? safeRoot.getElementById('dm-context-title') : null;
    if (title) title.textContent = activeConfig.label || 'Live Table';
    if (safeRoot.dataset) {
      safeRoot.dataset.dmActiveMode = activeMode;
    }
    return activeConfig;
  }

  function init(root) {
    const safeRoot = root || document;
    const buttons = Array.from(safeRoot.querySelectorAll('[data-dm-mode-button]'));
    buttons.forEach((button) => {
      button.addEventListener('click', () => activateMode(safeRoot, button.dataset.dmModeButton));
    });
    return activateMode(safeRoot, FALLBACK_MODE);
  }

  window.AppUIDMPanelModeBridge = Object.freeze({
    listModes,
    getModeConfig,
    classifyElement,
    registerPanelSection,
    activateMode,
    init,
  });
})();
