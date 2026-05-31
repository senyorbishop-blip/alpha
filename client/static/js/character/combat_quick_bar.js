/* Movable player combat quick action bar. Depends on CombatQuickSelectors and live play.html helpers. */
(function (global) {
  'use strict';

  const STORAGE_PREFIX = 'tavern_combat_quick_bar_';
  const DEFAULT_POS = { left: 24, top: 96 };
  let root = null;
  let toggle = null;
  let minimized = false;
  let manualVisible = false;
  let lastCombatActive = false;
  let drag = null;

  function _runtime() {
    const rt = global.CombatQuickRuntime || {};
    return {
      getRole: typeof rt.getRole === 'function' ? rt.getRole : function () { return global.ROLE; },
      getUserId: typeof rt.getUserId === 'function' ? rt.getUserId : function () { return global.USER_ID; },
      getSessionId: typeof rt.getSessionId === 'function' ? rt.getSessionId : function () { return global.SESSION_ID; },
      getName: typeof rt.getName === 'function' ? rt.getName : function () { return global.NAME; },
      getCombat: typeof rt.getCombat === 'function' ? rt.getCombat : function () { return global._combat; },
      getCharSheet: typeof rt.getCharSheet === 'function' ? rt.getCharSheet : function () { return global._charSheet; },
      getTokens: typeof rt.getTokens === 'function' ? rt.getTokens : function () { return global.tokens || {}; },
    };
  }

  function _esc(value) {
    if (typeof global.escapeHtml === 'function') return global.escapeHtml(String(value == null ? '' : value));
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function _storageKey(suffix) {
    const rt = _runtime();
    const sid = String(rt.getSessionId() || 'session');
    const uid = String(rt.getUserId() || rt.getName() || 'player');
    return `${STORAGE_PREFIX}${sid}_${uid}_${suffix}`;
  }

  function _loadJson(key, fallback) {
    try {
      const raw = global.localStorage && global.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (_err) { return fallback; }
  }

  function _saveJson(key, value) {
    try { if (global.localStorage) global.localStorage.setItem(key, JSON.stringify(value)); } catch (_err) {}
  }

  function _readBool(key, fallback) {
    try {
      const raw = global.localStorage && global.localStorage.getItem(key);
      if (raw === '1') return true;
      if (raw === '0') return false;
    } catch (_err) {}
    return fallback;
  }

  function _writeBool(key, value) {
    try { if (global.localStorage) global.localStorage.setItem(key, value ? '1' : '0'); } catch (_err) {}
  }

  function _env() {
    return {
      charData: _runtime().getCharSheet(),
      getPlayerActionsSections: global._getPlayerActionsSections,
      getCombatQuickSpells: global._getCombatQuickSpells,
      getActionEconomyState: global._buildActionEconomyState,
      evaluateActionAvailability: global._evaluateActionEconomyAvailability,
      getSpellSlotRemaining: global.getSpellSlotRemaining,
      getActiveConcentration: global._getActiveConcentrationSpellName,
    };
  }

  function _combatActive() {
    const combat = _runtime().getCombat();
    return !!(combat && combat.active && Array.isArray(combat.combatants) && combat.combatants.length);
  }

  function _isPlayer() {
    return String(_runtime().getRole() || '').toLowerCase() === 'player';
  }

  function _hasSheetData() {
    const sheet = _runtime().getCharSheet() || {};
    return !!(sheet && typeof sheet === 'object' && (sheet.name || sheet.book || sheet.rulesSpellbook || sheet.spellbookEntries || sheet.nativeCharacter));
  }

  function _ensureDom() {
    if (!root) {
      root = document.createElement('aside');
      root.id = 'combat-quick-bar';
      root.className = 'combat-quick-bar';
      root.setAttribute('aria-live', 'polite');
      root.style.display = 'none';
      document.body.appendChild(root);
      _applyPosition(_loadJson(_storageKey('pos'), DEFAULT_POS));
    }
    if (!toggle) {
      toggle = document.createElement('button');
      toggle.id = 'combat-quick-bar-toggle';
      toggle.className = 'combat-quick-bar-toggle';
      toggle.type = 'button';
      toggle.textContent = '⚔ Actions';
      toggle.title = 'Show combat quick bar';
      toggle.addEventListener('click', function () {
        manualVisible = !manualVisible;
        _writeBool(_storageKey('manual'), manualVisible);
        if (manualVisible) minimized = false;
        _writeBool(_storageKey('min'), minimized);
        renderCombatQuickBar();
      });
      document.body.appendChild(toggle);
    }
  }

  function _applyPosition(pos) {
    if (!root) return;
    const maxLeft = Math.max(8, global.innerWidth - 360);
    const maxTop = Math.max(48, global.innerHeight - 260);
    const left = Math.min(Math.max(8, Number(pos && pos.left) || DEFAULT_POS.left), maxLeft);
    const top = Math.min(Math.max(48, Number(pos && pos.top) || DEFAULT_POS.top), maxTop);
    root.style.left = `${left}px`;
    root.style.top = `${top}px`;
  }

  function _startDrag(ev) {
    if (!root || ev.target.closest('button,select,a,input')) return;
    const rect = root.getBoundingClientRect();
    const point = ev.touches ? ev.touches[0] : ev;
    drag = { dx: point.clientX - rect.left, dy: point.clientY - rect.top };
    root.classList.add('dragging');
    ev.preventDefault();
  }

  function _moveDrag(ev) {
    if (!drag || !root) return;
    const point = ev.touches ? ev.touches[0] : ev;
    _applyPosition({ left: point.clientX - drag.dx, top: point.clientY - drag.dy });
  }

  function _endDrag() {
    if (!drag || !root) return;
    drag = null;
    root.classList.remove('dragging');
    const rect = root.getBoundingClientRect();
    _saveJson(_storageKey('pos'), { left: Math.round(rect.left), top: Math.round(rect.top) });
  }

  function _bindDrag() {
    if (!root || root.dataset.dragBound === '1') return;
    root.dataset.dragBound = '1';
    root.addEventListener('mousedown', function (ev) {
      if (ev.target.closest('.combat-quick-bar-header')) _startDrag(ev);
    });
    root.addEventListener('touchstart', function (ev) {
      if (ev.target.closest('.combat-quick-bar-header')) _startDrag(ev);
    }, { passive: false });
    document.addEventListener('mousemove', _moveDrag);
    document.addEventListener('touchmove', _moveDrag, { passive: false });
    document.addEventListener('mouseup', _endDrag);
    document.addEventListener('touchend', _endDrag);
    global.addEventListener('resize', function () { _applyPosition(_loadJson(_storageKey('pos'), DEFAULT_POS)); });
  }

  function _actionClasses(action) {
    const classes = ['combat-quick-action'];
    if (action.disabled) classes.push('disabled');
    (action.states || []).forEach(function (state) { classes.push(`state-${state.replace(/_/g, '-')}`); });
    return classes.join(' ');
  }

  function _meta(action) {
    const bits = [];
    if (action.attackBonus) bits.push(`Hit ${action.attackBonus}`);
    if (action.damage) bits.push(action.damage + (action.damageType ? ` ${action.damageType}` : ''));
    if (action.range) bits.push(action.range);
    if (action.uses || action.resource) bits.push(action.uses || action.resource);
    if (action.slotLabel) bits.push(action.slotLabel);
    return bits.slice(0, 3).join(' • ');
  }

  function _renderAction(action) {
    const stateLabel = action.disabledReason || (action.states || []).map(function (s) { return s.replace(/_/g, ' '); }).join(', ');
    const type = action.type || 'action';
    return `<button class="${_actionClasses(action)}" type="button" data-source="${_esc(action.source || '')}" data-action-id="${_esc(action.id || '')}" data-type="${_esc(type)}" ${action.disabled ? 'disabled' : ''} title="${_esc(stateLabel || action.description || action.name)}">
      <span class="combat-quick-action-type">${_esc(type)}</span>
      <span class="combat-quick-action-name">${_esc(action.name || 'Action')}</span>
      <span class="combat-quick-action-meta">${_esc(_meta(action) || stateLabel || 'Ready')}</span>
    </button>`;
  }

  function _section(title, rows, empty) {
    if (!rows || !rows.length) return empty ? `<section class="combat-quick-section empty"><h5>${_esc(title)}</h5><div class="combat-quick-empty">${_esc(empty)}</div></section>` : '';
    return `<section class="combat-quick-section"><h5>${_esc(title)}</h5><div class="combat-quick-grid">${rows.map(_renderAction).join('')}</div></section>`;
  }

  function _spellSlots(slots) {
    if (!slots || !slots.length) return '';
    return `<div class="combat-quick-slots" aria-label="Spell slots">${slots.map(function (slot) {
      const empty = Number(slot.remaining || 0) <= 0;
      return `<span class="combat-quick-slot ${empty ? 'empty' : ''}">L${Number(slot.level)} ${Number(slot.remaining)}/${Number(slot.total)}</span>`;
    }).join('')}</div>`;
  }

  function _summary(model) {
    const econ = model && model.economy;
    const parts = [];
    if (econ) {
      parts.push(`Act ${Math.max(0, Number(econ.actions_total || 0) - Number(econ.actions_used || 0))}/${Number(econ.actions_total || 0)}`);
      parts.push(`Bonus ${Math.max(0, Number(econ.bonus_actions_total || 0) - Number(econ.bonus_actions_used || 0))}/${Number(econ.bonus_actions_total || 0)}`);
      parts.push(`React ${Math.max(0, Number(econ.reactions_total || 0) - Number(econ.reactions_used || 0))}/${Number(econ.reactions_total || 0)}`);
    }
    return parts.join(' • ');
  }

  function _openFullSheet() {
    if (typeof global.openCharacterBook === 'function') {
      global.openCharacterBook('premiumsheet');
      return;
    }
    if (typeof global.showToast === 'function') global.showToast('Character sheet is not ready yet.');
  }

  function _useAction(actionId, source, type) {
    if (!actionId) return;
    if (source === 'spell') {
      if (typeof global.combatQuickCastSpell === 'function') global.combatQuickCastSpell(actionId);
      return;
    }
    if (typeof global.playerUseAction === 'function') {
      global.playerUseAction(source || type || 'book', actionId);
      return;
    }
    if (typeof global.showToast === 'function') global.showToast('Action runtime is not ready yet.');
  }

  function _bindActions() {
    if (!root) return;
    root.querySelectorAll('.combat-quick-action').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _useAction(btn.getAttribute('data-action-id'), btn.getAttribute('data-source'), btn.getAttribute('data-type'));
        setTimeout(renderCombatQuickBar, 50);
      });
    });
    const minBtn = root.querySelector('[data-cqb-min]');
    if (minBtn) minBtn.addEventListener('click', function () {
      minimized = !minimized;
      _writeBool(_storageKey('min'), minimized);
      renderCombatQuickBar();
    });
    const closeBtn = root.querySelector('[data-cqb-close]');
    if (closeBtn) closeBtn.addEventListener('click', function () {
      manualVisible = false;
      if (!_combatActive()) minimized = true;
      _writeBool(_storageKey('manual'), manualVisible);
      _writeBool(_storageKey('min'), minimized);
      renderCombatQuickBar();
    });
    const sheetBtn = root.querySelector('[data-cqb-sheet]');
    if (sheetBtn) sheetBtn.addEventListener('click', _openFullSheet);
  }

  function renderCombatQuickBar() {
    _ensureDom();
    _bindDrag();
    if (!manualVisible && toggle) manualVisible = _readBool(_storageKey('manual'), false);
    minimized = _readBool(_storageKey('min'), minimized);

    const active = _combatActive();
    if (active && !lastCombatActive) {
      manualVisible = true;
      minimized = false;
      _writeBool(_storageKey('manual'), true);
      _writeBool(_storageKey('min'), false);
    }
    if (!active && lastCombatActive && !manualVisible) minimized = true;
    lastCombatActive = active;

    const visible = _isPlayer() && _hasSheetData() && (active || manualVisible);
    if (toggle) toggle.style.display = _isPlayer() && _hasSheetData() && !visible ? 'inline-flex' : 'none';
    if (!visible) {
      root.style.display = 'none';
      return;
    }

    const selector = global.CombatQuickSelectors && global.CombatQuickSelectors.selectCombatQuickActions;
    const model = typeof selector === 'function' ? selector(_env()) : { primaryActions: [], bonusActions: [], reactions: [], topSpells: [], resources: [], concentration: null, spellSlots: [] };
    const combat = _runtime().getCombat() || {};
    const tokens = _runtime().getTokens() || {};
    const targetName = combat.selected_target_id && tokens[combat.selected_target_id]
      ? (tokens[combat.selected_target_id].name || 'Target selected')
      : 'No target selected';
    root.classList.toggle('minimized', !!minimized);
    root.style.display = 'block';
    root.innerHTML = `<div class="combat-quick-bar-header">
        <div><strong>⚔ Quick Actions</strong><span>${active ? 'Combat ready' : 'Manual tray'}${_summary(model) ? ' • ' + _esc(_summary(model)) : ''}</span></div>
        <div class="combat-quick-header-controls">
          <button type="button" data-cqb-sheet title="Open full character sheet">Sheet</button>
          <button type="button" data-cqb-min>${minimized ? 'Expand' : 'Min'}</button>
          <button type="button" data-cqb-close title="Hide quick bar">×</button>
        </div>
      </div>
      <div class="combat-quick-body">
        <div class="combat-quick-status-row">
          <span class="combat-quick-status ${model.concentration ? 'active' : ''}">${model.concentration ? '🌀 Concentrating: ' + _esc(model.concentration.name) : 'No concentration'}</span>
          <span class="combat-quick-status target">🎯 ${_esc(targetName)}</span>
        </div>
        ${_spellSlots(model.spellSlots)}
        ${_section('Main weapon / actions', model.primaryActions, 'No attack actions loaded.')}
        ${_section('Top spells', model.topSpells, '')}
        ${_section('Bonus action', model.bonusActions, 'No bonus action exposed.')}
        ${_section('Reaction', model.reactions, '')}
        ${_section('Resources', model.resources, '')}
      </div>`;
    _bindActions();
  }

  function toggleCombatQuickBar(force) {
    manualVisible = typeof force === 'boolean' ? force : !manualVisible;
    if (manualVisible) minimized = false;
    _writeBool(_storageKey('manual'), manualVisible);
    _writeBool(_storageKey('min'), minimized);
    renderCombatQuickBar();
  }

  function _patchRenderCombat() {
    if (typeof global.renderCombat !== 'function' || global.renderCombat.__combatQuickBarPatched) return;
    const original = global.renderCombat;
    function patchedRenderCombat() {
      const result = original.apply(this, arguments);
      try { renderCombatQuickBar(); } catch (err) { console.warn('[combat quick bar] render failed', err); }
      return result;
    }
    patchedRenderCombat.__combatQuickBarPatched = true;
    global.renderCombat = patchedRenderCombat;
  }

  function initCombatQuickBar() {
    manualVisible = _readBool(_storageKey('manual'), false);
    minimized = _readBool(_storageKey('min'), false);
    _ensureDom();
    _bindDrag();
    _patchRenderCombat();
    renderCombatQuickBar();
  }

  global.CombatQuickBar = { init: initCombatQuickBar, render: renderCombatQuickBar, toggle: toggleCombatQuickBar };
  global.toggleCombatQuickBar = toggleCombatQuickBar;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCombatQuickBar);
  } else {
    initCombatQuickBar();
  }
}(window));
