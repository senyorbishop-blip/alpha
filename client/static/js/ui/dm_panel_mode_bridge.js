(function () {
  'use strict';

  const FALLBACK_MODE = 'run';
  const MODE_ACTIVE_CLASS = 'dm-panel-mode-active';
  const MODE_INACTIVE_CLASS = 'dm-panel-mode-inactive';
  const SECTION_SELECTOR = '[data-dm-mode], [data-dm-tool], [data-dm-section]';

  // Emergency regression kill switch. Default to disabled for the risky legacy
  // panel guard so DM boot/WebSocket startup cannot be blocked by panel cleanup.
  if (typeof window.__DISABLE_DM_MAP_FIRST_GUARD === 'undefined') {
    window.__DISABLE_DM_MAP_FIRST_GUARD = true;
  }

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
      description: 'Debug diagnostics are closed by default and visible to the DM only when Debug mode is active.',
      debugPanel: true,
      diagnostics: Object.freeze([
        Object.freeze({ id: 'stream-readiness', text: 'Stream readiness loading…', mountId: 'stream-readiness-panel' }),
        Object.freeze({ id: 'payload-warnings', text: 'Payload warnings remain tracked in the stream readiness summary.' }),
        Object.freeze({ id: 'reconnect-warnings', text: 'Reconnect warnings remain tracked in the stream readiness summary.' }),
        Object.freeze({ id: 'websocket-diagnostics', text: 'WebSocket diagnostics remain available through the standard status dot/label and debug helpers.' }),
        Object.freeze({ id: 'sync-diagnostics', text: 'Sync diagnostics remain available through live-state debug summaries.' }),
        Object.freeze({ id: 'visibility-checks', text: 'Visibility checks remain grouped here with hidden-token and fog safety diagnostics.' }),
        Object.freeze({ id: 'dm-focus-testing-guidance', text: 'DM focus/testing guidance and development-only hints live in Debug, not Live Table.' }),
      ]),
      tools: Object.freeze([]),
    }),
  ]);


  function runAction(action) {
    if (!action) return;
    try {
      // Existing play.html handlers own these actions; this adapter only calls them.
      Function(action)();
    } catch (err) {
      console.warn('[dm-panel-mode] action failed', action, err);
    } finally {
      forceLegacyRightPanelsClosed(document);
    }
  }

  function appendCompactButton(doc, parent, options) {
    const button = doc.createElement('button');
    button.type = 'button';
    button.className = options.className || 'dm-compact-action';
    if (options.tool) button.dataset.dmTool = options.tool;
    if (options.tab) button.dataset.dmCompactTab = options.tab;
    button.textContent = options.label;
    if (options.title) button.title = options.title;
    if (options.action) button.addEventListener('click', () => runAction(options.action));
    parent.appendChild(button);
    return button;
  }

  function appendCompactShortcutPanel(doc, section, definition) {
    const grid = doc.createElement('div');
    grid.className = 'dm-compact-shortcuts';
    grid.setAttribute('aria-label', `${definition.label} shortcuts`);
    Array.from(definition.tools || []).slice(0, 4).forEach((tool) => {
      appendCompactButton(doc, grid, {
        className: 'dm-compact-action',
        tool: tool.id,
        label: tool.label,
        title: tool.label,
        action: tool.action,
      });
    });
    section.appendChild(grid);
  }

  function appendNpcMonsterPanel(doc, section) {
    const panel = doc.createElement('div');
    panel.className = 'dm-npc-compact-panel';
    panel.dataset.dmCompactNpcPanel = 'true';

    const tabs = doc.createElement('div');
    tabs.className = 'dm-npc-compact-tabs';
    tabs.setAttribute('aria-label', 'NPC / Monster tools');
    [
      ['bestiary', 'Bestiary', "switchRTab('bestiary')"],
      ['spawn', 'Spawn', "switchRTab('bestiary')"],
      ['token', 'Token', "toggleFlyout('flyout-token')"],
      ['combat', 'Combat', "switchRTab('combat')"],
    ].forEach(([tab, label, action], index) => {
      const btn = appendCompactButton(doc, tabs, { className: 'dm-npc-compact-tab', tab, label, action });
      btn.setAttribute('aria-pressed', index === 0 ? 'true' : 'false');
    });
    panel.appendChild(tabs);

    const searchRow = doc.createElement('div');
    searchRow.className = 'dm-npc-search-row';
    const search = doc.createElement('input');
    search.id = 'dm-compact-bestiary-search';
    search.type = 'search';
    search.placeholder = 'Search bestiary…';
    search.setAttribute('aria-label', 'Search bestiary');
    search.dataset.dmTool = 'bestiary-search';
    search.addEventListener('input', () => {
      const existing = doc.getElementById('bestiary-search');
      if (!existing) return;
      existing.value = search.value;
      existing.dispatchEvent(new Event('input', { bubbles: true }));
    });
    searchRow.appendChild(search);
    appendCompactButton(doc, searchRow, {
      className: 'dm-filter-chip',
      label: 'Filters',
      title: 'Open full bestiary filters',
      action: "switchRTab('bestiary')",
    });
    panel.appendChild(searchRow);

    const list = doc.createElement('div');
    list.className = 'dm-npc-card-list';
    list.setAttribute('aria-label', 'Compact creature results');
    ['Use the Bestiary tab results', 'Select a creature for preview', 'Spawn onto the map'].forEach((text) => {
      const card = doc.createElement('button');
      card.type = 'button';
      card.className = 'dm-npc-card';
      card.textContent = text;
      card.addEventListener('click', () => runAction("switchRTab('bestiary')"));
      list.appendChild(card);
    });
    panel.appendChild(list);

    const actions = doc.createElement('div');
    actions.className = 'dm-npc-primary-actions';
    appendCompactButton(doc, actions, { className: 'dm-primary-action', tool: 'spawn-token', label: 'Spawn', action: "if (typeof beginBestiarySpawn === 'function') beginBestiarySpawn(); else switchRTab('bestiary')" });
    appendCompactButton(doc, actions, { tool: 'creature-quick-actions', label: 'Add to Encounter', action: "switchRTab('combat')" });
    appendCompactButton(doc, actions, { tool: 'creature-hp-ac-speed', label: 'Edit', action: "toggleFlyout('flyout-token')" });
    appendCompactButton(doc, actions, { tool: 'visibility-state', label: 'Hide / Reveal', action: "toggleFlyout('flyout-token')" });
    section.appendChild(panel);
    section.appendChild(actions);
  }

  function appendDebugDiagnostics(doc, section, diagnostics) {
    section.dataset.dmDebugPanel = '';
    const grid = doc.createElement('div');
    grid.className = 'dm-context-marker-grid';
    grid.setAttribute('aria-label', 'Debug diagnostic tools');
    Array.from(diagnostics || []).forEach((diagnostic) => {
      const mounted = diagnostic.mountId ? doc.getElementById(diagnostic.mountId) : null;
      const card = mounted || doc.createElement('div');
      card.classList.add('dm-debug-diagnostic-card');
      card.dataset.dmTool = diagnostic.id;
      if (!card.textContent || card.textContent.trim() === '') card.textContent = diagnostic.text;
      if (diagnostic.mountId && !mounted) card.id = diagnostic.mountId;
      if (diagnostic.mountId === 'stream-readiness-panel') card.setAttribute('aria-live', 'polite');
      grid.appendChild(card);
    });
    section.appendChild(grid);
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
      if (definition.description) {
        section.setAttribute('title', definition.description);
        section.dataset.dmModeHelp = definition.description;
      }
      if (definition.debugPanel) {
        appendDebugDiagnostics(doc, section, definition.diagnostics);
      }
      if (definition.mode === 'npc-monster') {
        appendNpcMonsterPanel(doc, section);
      } else if (definition.tools.length && !definition.debugPanel) {
        appendCompactShortcutPanel(doc, section, definition);
      }
      if (definition.markers && definition.markers.length) {
        const marker = doc.createElement('div');
        marker.className = definition.mode === 'run' ? 'dm-context-keepout' : 'dm-context-markers';
        marker.dataset[definition.markerName] = definition.markers.join(' ');
        marker.hidden = true;
        marker.setAttribute('aria-hidden', 'true');
        marker.textContent = definition.markerText || '';
        section.appendChild(marker);
      }
      body.appendChild(section);
    });
  }

  function registry() {
    return window.AppUIDMModeToolRegistry || {};
  }


  function isMapFirstActive(docRoot) {
    const body = docRoot && docRoot.body ? docRoot.body : document.body;
    return !!(body && body.classList && body.classList.contains('dm-map-first-active'));
  }

  function isLegacyGuardDisabled() {
    if (window.__DISABLE_DM_MAP_FIRST_GUARD === true) return true;
    try {
      return String(window.localStorage && window.localStorage.getItem('disableDmMapFirstGuard') || '') === '1';
    } catch (_err) {
      return false;
    }
  }

  function forceLegacyRightPanelsClosed(root, options) {
    if (isLegacyGuardDisabled()) return false;
    const safeRoot = root || document;
    const docRoot = safeRoot.querySelector ? safeRoot : document;
    const body = docRoot.body || document.body;
    if (!body || !isMapFirstActive(docRoot)) return false;
    const allowDrawer = !!(options && options.allowDrawer) || body.classList.contains('dm-legacy-drawer-open');
    if (!allowDrawer) body.classList.remove('dm-legacy-drawer-open');
    const selectors = [
      '#right-tab-bar',
      '#right-panel-context',
      '#sidebar-right .rtab-shell',
      '#sidebar-right .rtab-panes',
      '#sidebar-right .rtab-pane',
      '#rtab-pane-combat',
      '#combat-list',
      '#combat-controls',
      '#combat-pre',
      '#combat-add-row',
      '#combat-spell-tray',
      '#combat-weapon-tray',
      '#right-panel-context',
    ];
    docRoot.querySelectorAll(selectors.join(',')).forEach((el) => {
      if (!allowDrawer || !el.closest('.rtab-shell')) {
        if (el.getAttribute('aria-hidden') !== 'true') el.setAttribute('aria-hidden', 'true');
        el.dataset.dmMapFirstLegacyHidden = 'true';
      }
    });
    return true;
  }

  function ensureLegacyPanelObserver(root) {
    // Temporarily disabled: observing #sidebar-right while writing attributes
    // inside that subtree can thrash during boot and prevent the live app from
    // reaching connectWS/request_state. Keep this as a safe no-op until the
    // guard is reintroduced with a proven post-connect debounce.
    void root;
    return null;
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

  function renderRichContext(safeRoot, activeMode) {
    // Mount rich, live content (current turn, initiative, party, tools) into the
    // context body. Replaces the old text-link markers. No-ops if the renderer
    // module isn't present, so the panel degrades to the marker fallback.
    const renderer = window.AppUIDMContextRender;
    if (!renderer || typeof renderer.render !== 'function') return;
    const docRoot = safeRoot && safeRoot.querySelector ? safeRoot : document;
    const body = docRoot.querySelector('#dm-context-shell .dm-map-first-context-body');
    if (!body) return;

    // Tab strip (mounted once, refreshed per mode).
    let tabsEl = body.querySelector('.dcx-tabs');
    if (!tabsEl) {
      tabsEl = document.createElement('div');
      tabsEl.className = 'dcx-tabs';
      body.insertBefore(tabsEl, body.firstChild);
    }
    const tabs = typeof renderer.tabs === 'function' ? (renderer.tabs(activeMode) || []) : [];
    tabsEl.innerHTML = tabs.map(function (t, i) {
      const badge = t[2] ? '<span class="dcx-badge">' + t[2] + '</span>' : '';
      return '<button class="dcx-tab" type="button" aria-pressed="' + (i === 0) +
        '" data-dm-compact-tab="' + String(t[0]).replace(/"/g, '') + '" onclick="if(window.AppUIDMActions&&AppUIDMActions.openCompactCombatDrawer)AppUIDMActions.openCompactCombatDrawer();">' + String(t[1]) + badge + '</button>';
    }).join('');
    tabsEl.style.display = tabs.length ? 'flex' : 'none';

    // Rich content container (mounted once, refilled per mode).
    let rich = body.querySelector('#dm-rich-context');
    if (!rich) {
      rich = document.createElement('div');
      rich.id = 'dm-rich-context';
      if (tabsEl.nextSibling) body.insertBefore(rich, tabsEl.nextSibling);
      else body.appendChild(rich);
    }
    try { rich.innerHTML = renderer.render(activeMode); } catch (_e) { return; }
    if (typeof renderer.afterRender === 'function') {
      try { renderer.afterRender(rich); } catch (_e2) {}
    }

    // Header glyph + note, mirroring the chosen mode.
    if (typeof renderer.meta === 'function') {
      const m = renderer.meta(activeMode) || {};
      const noteEl = docRoot.querySelector('.dm-context-map-note');
      if (noteEl && m.note) noteEl.textContent = m.note;
    }
  }

  function activateMode(root, modeId) {
    const safeRoot = root || document;
    try {
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
      const titleEl = safeRoot.getElementById ? safeRoot.getElementById('dm-context-title') : null;
      if (titleEl) titleEl.textContent = activeConfig.label || 'Live Table';
      if (safeRoot.dataset) {
        safeRoot.dataset.dmActiveMode = activeMode;
        safeRoot.dataset.debugOpen = activeMode === 'debug' ? 'true' : 'false';
      }
      if (safeRoot.body && safeRoot.body.dataset) {
        safeRoot.body.dataset.dmActiveMode = activeMode;
        safeRoot.body.dataset.debugOpen = activeMode === 'debug' ? 'true' : 'false';
      }
      renderRichContext(safeRoot, activeMode);
      if (window.__DM_MAP_FIRST_CAN_ENHANCE === true) {
        ensureLegacyPanelObserver(safeRoot);
        forceLegacyRightPanelsClosed(safeRoot);
      }
      if (typeof window.renderStreamReadinessPanel === 'function') {
        window.renderStreamReadinessPanel();
      }
      return activeConfig;
    } catch (err) {
      console.warn('[dm-panel-mode] activate skipped to preserve app boot', err);
      return getModeConfig(FALLBACK_MODE);
    }
  }

  function init(root) {
    const safeRoot = root || document;
    const buttons = Array.from(safeRoot.querySelectorAll('[data-dm-mode-button]'));
    buttons.forEach((button) => {
      button.addEventListener('click', () => activateMode(safeRoot, button.dataset.dmModeButton));
    });
    return activateMode(safeRoot, FALLBACK_MODE);
  }

  // Re-renders the rich context panel for whatever mode is currently active,
  // without touching mode/button state. Live state pushes (combat_state,
  // state_sync, etc.) arrive independently of mode-switch clicks, so callers
  // that mutate _combat/charProfiles/etc. need a way to refresh the panel.
  function refresh(root) {
    const safeRoot = root || document;
    if (window.__DM_MAP_FIRST_CAN_ENHANCE !== true) return null;
    const activeMode = (safeRoot.dataset && safeRoot.dataset.dmActiveMode)
      || (safeRoot.body && safeRoot.body.dataset && safeRoot.body.dataset.dmActiveMode)
      || FALLBACK_MODE;
    try {
      renderRichContext(safeRoot, normalizeMode(activeMode));
      ensureLegacyPanelObserver(safeRoot);
      forceLegacyRightPanelsClosed(safeRoot);
    } catch (err) {
      console.warn('[dm-panel-mode] refresh skipped to preserve app runtime', err);
    }
    return null;
  }

  window.AppUIDMPanelModeBridge = Object.freeze({
    listModes,
    getModeConfig,
    classifyElement,
    registerPanelSection,
    activateMode,
    refresh,
    forceLegacyRightPanelsClosed,
    init,
  });
})();
