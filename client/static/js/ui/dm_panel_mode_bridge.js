(function () {
  'use strict';

  const FALLBACK_MODE = 'run';
  const MODE_ACTIVE_CLASS = 'dm-panel-mode-active';
  const MODE_INACTIVE_CLASS = 'dm-panel-mode-inactive';
  const SECTION_SELECTOR = '[data-dm-mode], [data-dm-tool], [data-dm-section]';

  const MODE_PANEL_DEFINITIONS = Object.freeze([
    Object.freeze({
      mode: 'run',
      label: 'Live Table clean context',
      description: 'Live Table keeps the session view focused on party status, chat, combat pacing, dice, handouts, and the selected-token quick panel.',
      markerName: 'liveTableCleanMarkers',
      markers: Object.freeze(['wall-editor', 'fog-brush', 'shop-editor', 'debug-diagnostics']),
      markerText: 'Wall, fog, shop setup, and debug tools stay in their dedicated DM modes so Live Table remains clean.',
      tools: Object.freeze([
        Object.freeze({ id: 'party-overview', label: 'Party', action: "switchRTab('party')" }),
        Object.freeze({ id: 'current-scene-notes', label: 'Moments', action: "switchRTab('memory')" }),
        Object.freeze({ id: 'handout-shortcuts', label: 'Handouts', action: "switchRTab('handouts')" }),
        Object.freeze({ id: 'narration-shortcuts', label: 'Sound / Narration', action: "toggleFlyout('flyout-sound')" }),
      ]),
    }),
    Object.freeze({
      mode: 'map-build',
      label: 'Map Build tools',
      description: 'Map Build groups setup-heavy editing controls without changing fog, reveal/hide, token visibility, wall collision, door collision, or placement authority.',
      markerName: 'mapBuildMarkers',
      markers: Object.freeze(['fog-tools', 'wall-tools', 'door-tools', 'reveal-hide-tools', 'terrain-tools', 'token-layer', 'prop-layer', 'lighting-weather-tools', 'asset-library', 'map-save-apply']),
      tools: Object.freeze([
        Object.freeze({ id: 'terrain-tools', label: 'Terrain Tools', action: "toggleFlyout('flyout-editor')" }),
        Object.freeze({ id: 'fog-tools', label: 'Fog Tools', action: "toggleFlyout('flyout-fog')" }),
        Object.freeze({ id: 'wall-tools', label: 'Wall Tools', action: "toggleFlyout('flyout-editor')" }),
        Object.freeze({ id: 'door-tools', label: 'Door Tools', action: "toggleFlyout('flyout-editor')" }),
        Object.freeze({ id: 'reveal-hide-tools', label: 'Reveal / Hide', action: "toggleFlyout('flyout-fog')" }),
        Object.freeze({ id: 'token-layer', label: 'Token Layer', action: "toggleFlyout('flyout-editor')" }),
        Object.freeze({ id: 'prop-layer', label: 'Prop Layer', action: "toggleFlyout('flyout-editor')" }),
        Object.freeze({ id: 'lighting-weather-tools', label: 'Lighting / Weather', action: "toggleFlyout('flyout-map')" }),
        Object.freeze({ id: 'asset-library', label: 'Asset Library', action: "toggleFlyout('flyout-editor')" }),
        Object.freeze({ id: 'map-save-apply', label: 'Map Save / Apply', action: "toggleFlyout('flyout-editor')" }),
      ]),
    }),
    Object.freeze({
      mode: 'npc-monster',
      label: 'NPC and Monster tools',
      description: 'NPC / Monster groups creature search, spawning, stats, visibility, conditions, notes, and quick actions while preserving the existing bestiary and token editor controls.',
      markerName: 'npcMonsterMarkers',
      markers: Object.freeze(['bestiary-search', 'spawn-token', 'visibility-state', 'creature-hp-ac-speed', 'initiative-modifier', 'conditions', 'creature-notes', 'creature-quick-actions']),
      tools: Object.freeze([
        Object.freeze({ id: 'bestiary-search', label: 'Bestiary Search', action: "switchRTab('bestiary')" }),
        Object.freeze({ id: 'spawn-token', label: 'Spawn Token', action: "switchRTab('bestiary')" }),
        Object.freeze({ id: 'creature-hp-ac-speed', label: 'HP / AC / Speed', action: "toggleFlyout('flyout-token')" }),
        Object.freeze({ id: 'visibility-state', label: 'Visibility State', action: "toggleFlyout('flyout-token')" }),
        Object.freeze({ id: 'initiative-modifier', label: 'Initiative Modifier', action: "toggleFlyout('flyout-token')" }),
        Object.freeze({ id: 'conditions', label: 'Conditions', action: "toggleFlyout('flyout-token')" }),
        Object.freeze({ id: 'creature-notes', label: 'Creature Notes', action: "toggleFlyout('flyout-token')" }),
        Object.freeze({ id: 'creature-quick-actions', label: 'Quick Actions', action: "toggleFlyout('flyout-token')" }),
      ]),
    }),
    Object.freeze({
      mode: 'debug',
      label: 'Debug diagnostics',
      description: 'Debug diagnostics are closed by default.',
      tools: Object.freeze([]),
    }),
  ]);

  function appendTextElement(doc, parent, tagName, className, text) {
    const el = doc.createElement(tagName);
    if (className) el.className = className;
    el.textContent = text;
    parent.appendChild(el);
    return el;
  }

  function ensureModePanels(root) {
    const safeRoot = root || document;
    const doc = safeRoot.createElement ? safeRoot : document;
    const body = safeRoot.querySelector ? safeRoot.querySelector('#dm-context-shell .dm-map-first-context-body') : null;
    if (!body || body.dataset.dmContextPanelsMounted === 'true') return;
    body.dataset.dmContextPanelsMounted = 'true';
    MODE_PANEL_DEFINITIONS.forEach((definition) => {
      const section = doc.createElement('section');
      section.className = 'dm-context-mode-panel';
      section.dataset.dmMode = definition.mode;
      section.setAttribute('aria-label', definition.label);
      appendTextElement(doc, section, 'p', '', definition.description);
      if (definition.tools.length) {
        const grid = doc.createElement('div');
        grid.className = 'dm-context-tool-grid';
        grid.setAttribute('aria-label', `${definition.label} shortcuts`);
        definition.tools.forEach((tool) => {
          const button = doc.createElement('button');
          button.type = 'button';
          button.className = 'mini-btn';
          button.dataset.dmTool = tool.id;
          button.setAttribute('onclick', tool.action);
          button.textContent = tool.label;
          grid.appendChild(button);
        });
        section.appendChild(grid);
      }
      if (definition.markers && definition.markers.length) {
        const marker = doc.createElement('div');
        marker.className = definition.mode === 'run' ? 'dm-context-keepout' : 'dm-context-markers';
        marker.dataset[definition.markerName] = definition.markers.join(' ');
        marker.textContent = definition.markerText || '';
        section.appendChild(marker);
      }
      body.appendChild(section);
    });
  }

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
    ensureModePanels(safeRoot);
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
