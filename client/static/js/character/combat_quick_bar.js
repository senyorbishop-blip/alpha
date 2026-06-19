/*
 * Movable Combat Quick Actions Bar.
 * Renders compact player combat choices from CombatQuickSelectors.
 * Exposes: window.CombatQuickBar
 */
(function initCombatQuickBar(global) {
  'use strict';

  const STORAGE_KEY = 'combat_quick_bar.v1';
  const SIZE_KEY = 'combat_quick_bar_size.v1';
  const DEFAULT_STATE = { x: null, y: null, minimized: false, manual: false, combatWasActive: false, customizing: false, dismissedForCombatTurn: '', dismissedUntilManualOpen: false };
  let state = Object.assign({}, DEFAULT_STATE);
  let root = null;
  let dragging = null;
  let toggleDragging = null;
  let suppressToggleClick = false;

  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function _safeArray(v) { return Array.isArray(v) ? v : []; }
  function _firstText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const v = arguments[i];
      if (v === null || v === undefined) continue;
      const t = String(v).trim();
      if (t) return t;
    }
    return '';
  }

  function _runtime() {
    return typeof global.getCombatQuickBarRuntime === 'function' ? (global.getCombatQuickBarRuntime() || {}) : {};
  }

  function _loadState() {
    try {
      const raw = global.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      const merged = Object.assign({}, DEFAULT_STATE, parsed || {});
      // Sanitize field types to prevent corrupted localStorage from breaking the bar
      state = {
        x: Number.isFinite(Number(merged.x)) ? Number(merged.x) : null,
        y: Number.isFinite(Number(merged.y)) ? Number(merged.y) : null,
        buttonX: Number.isFinite(Number(merged.buttonX)) ? Number(merged.buttonX) : null,
        buttonY: Number.isFinite(Number(merged.buttonY)) ? Number(merged.buttonY) : null,
        w: Number.isFinite(Number(merged.w)) ? Number(merged.w) : undefined,
        h: Number.isFinite(Number(merged.h)) ? Number(merged.h) : undefined,
        minimized: !!merged.minimized,
        manual: !!merged.manual,
        combatWasActive: !!merged.combatWasActive,
        customizing: !!merged.customizing,
        dismissedForCombatTurn: typeof merged.dismissedForCombatTurn === 'string' ? merged.dismissedForCombatTurn : '',
        dismissedUntilManualOpen: !!merged.dismissedUntilManualOpen,
      };
    } catch (_err) {
      state = Object.assign({}, DEFAULT_STATE);
    }
  }

  function _saveState() {
    try { global.localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_err) {}
  }

  function _installStyles() {
    if (document.getElementById('combat-quick-bar-styles')) return;
    const style = document.createElement('style');
    style.id = 'combat-quick-bar-styles';
    style.textContent = `
      .combat-quick-bar-toggle{position:fixed;right:18px;bottom:84px;z-index:1085;border:1px solid rgba(0,229,204,.45);border-radius:999px;background:rgba(13,18,24,.88);color:#dffbf7;padding:.42rem .62rem;font-size:.72rem;box-shadow:0 8px 22px rgba(0,0,0,.35);cursor:grab;pointer-events:auto;touch-action:none;user-select:none;}
      .combat-quick-bar-toggle:focus-visible{outline:2px solid #9ff6ea;outline-offset:3px;}
      .combat-quick-bar-toggle.is-dragging{cursor:grabbing;}
      .combat-quick-bar{position:fixed;left:50%;bottom:88px;transform:translateX(-50%);z-index:1086;width:min(720px,calc(100vw - 28px));min-width:280px;min-height:140px;max-height:min(72vh,600px);display:flex;flex-direction:column;gap:.48rem;border:1px solid rgba(0,229,204,.32);border-radius:16px;background:linear-gradient(145deg,rgba(13,18,24,.96),rgba(28,20,13,.94));box-shadow:0 18px 44px rgba(0,0,0,.48),inset 0 0 0 1px rgba(255,255,255,.04);color:#f5ead6;font-family:inherit;overflow:hidden;resize:both;box-sizing:border-box;}
      .combat-quick-bar.is-minimized{width:min(360px,calc(100vw - 28px));min-height:unset;resize:none;}
      .combat-quick-bar[hidden],.combat-quick-bar-toggle[hidden]{display:none!important;}
      .combat-quick-bar-head{display:flex;align-items:center;justify-content:space-between;gap:.7rem;padding:.55rem .7rem .42rem;cursor:grab;background:rgba(255,255,255,.035);border-bottom:1px solid rgba(255,255,255,.08);user-select:none;}
      .combat-quick-bar-title{display:flex;align-items:center;gap:.45rem;font-weight:800;font-size:.78rem;letter-spacing:.03em;text-transform:uppercase;color:#9ff6ea;}
      .combat-quick-bar-sub{font-size:.62rem;color:rgba(245,234,214,.68);font-weight:500;text-transform:none;letter-spacing:0;}
      .combat-quick-bar-head-actions{display:flex;gap:.35rem;align-items:center;}
      .combat-quick-bar-icon-btn{border:1px solid rgba(255,255,255,.14);border-radius:999px;background:rgba(0,0,0,.28);color:#f5ead6;min-width:1.8rem;height:1.8rem;cursor:pointer;}
      .combat-quick-bar-body{display:grid;gap:.55rem;padding:.58rem .7rem .72rem;overflow:auto;}
      .combat-quick-bar-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(138px,1fr));gap:.42rem;}
      .combat-quick-bar-section{display:grid;gap:.35rem;}
      .combat-quick-bar-section-title{font-size:.61rem;color:rgba(245,234,214,.62);text-transform:uppercase;letter-spacing:.08em;}
      .combat-quick-tile{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:.22rem;min-height:4.1rem;border:1px solid rgba(255,255,255,.12);border-radius:12px;background:rgba(255,255,255,.045);color:#f7ecd8;padding:.5rem .55rem;text-align:left;cursor:pointer;}
      .combat-quick-tile:hover{border-color:rgba(0,229,204,.45);background:rgba(0,229,204,.08);}
      .combat-quick-tile:disabled,.combat-quick-tile.is-disabled{opacity:.5;cursor:not-allowed;filter:saturate(.65);}
      .combat-quick-tile.is-used{border-color:rgba(255,210,90,.42);}
      .combat-quick-tile.needs-target:after,.combat-quick-tile.needs-slot:after{content:attr(data-state);position:absolute;right:.42rem;top:.38rem;font-size:.52rem;border:1px solid rgba(255,210,90,.35);border-radius:999px;padding:.08rem .28rem;color:#ffe8a3;background:rgba(80,52,0,.45);}
      .combat-quick-pin{position:absolute;right:.35rem;bottom:.35rem;border:1px solid rgba(255,210,90,.32);border-radius:999px;background:rgba(0,0,0,.3);color:#ffe8a3;width:1.35rem;height:1.35rem;line-height:1;cursor:pointer;z-index:2;}
      .combat-quick-pin.is-pinned{background:rgba(255,210,90,.18);border-color:rgba(255,210,90,.65);}
      .combat-quick-name{font-weight:800;font-size:.72rem;line-height:1.15;max-width:calc(100% - 1.7rem);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
      .combat-quick-meta{font-size:.58rem;color:rgba(245,234,214,.68);line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
      .combat-quick-pill-row{display:flex;flex-wrap:wrap;gap:.22rem;margin-top:auto;}
      .combat-quick-pill{font-size:.52rem;border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:.08rem .28rem;color:rgba(245,234,214,.72);background:rgba(0,0,0,.18);}
      .combat-quick-pill.good{border-color:rgba(0,229,204,.32);color:#9ff6ea;}.combat-quick-pill.warn{border-color:rgba(255,210,90,.35);color:#ffe8a3;}.combat-quick-pill.danger{border-color:rgba(231,76,60,.42);color:#ffb4a8;}.combat-quick-pill.accent{border-color:rgba(112,167,255,.38);color:#b8d2ff;}.combat-quick-pill.damage{border-color:rgba(255,121,87,.36);color:#ffc0aa;}.combat-quick-pill.source{border-color:rgba(170,150,255,.35);color:#d6c9ff;}
      .combat-quick-status{display:flex;gap:.35rem;flex-wrap:wrap;align-items:center;font-size:.6rem;color:rgba(245,234,214,.66);}
      .combat-quick-resource-row{display:flex;gap:.3rem;flex-wrap:wrap;}.combat-quick-resource{font-size:.58rem;border:1px solid rgba(255,210,90,.24);border-radius:999px;padding:.14rem .38rem;color:#ffe8a3;background:rgba(96,64,8,.25);}
      .combat-quick-empty{font-size:.63rem;color:rgba(245,234,214,.58);padding:.35rem .1rem;}
      .combat-quick-sheet-btn{border:1px solid rgba(0,229,204,.4);border-radius:999px;background:rgba(0,229,204,.12);color:#dffbf7;padding:.35rem .55rem;font-weight:800;cursor:pointer;}
      .combat-quick-customize{display:grid;gap:.42rem;border:1px solid rgba(0,229,204,.18);border-radius:12px;background:rgba(0,0,0,.18);padding:.52rem;}
      .combat-quick-customize-head{display:flex;justify-content:space-between;gap:.5rem;align-items:center;font-size:.62rem;color:rgba(245,234,214,.72);}
      .combat-quick-pick-group{display:grid;gap:.3rem;}
      .combat-quick-pick:disabled{opacity:.4;cursor:not-allowed;}
      .combat-quick-pick-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.3rem;}
      .combat-quick-pick{border:1px solid rgba(255,255,255,.12);border-radius:10px;background:rgba(255,255,255,.04);color:#f5ead6;padding:.34rem .42rem;text-align:left;font-size:.62rem;cursor:pointer;}
      .combat-quick-pick.is-picked{border-color:rgba(255,210,90,.58);background:rgba(255,210,90,.12);color:#ffe8a3;}
      .combat-quick-pick small{display:block;color:rgba(245,234,214,.58);font-size:.54rem;margin-top:.08rem;}
      @media(max-width:760px){.combat-quick-bar{bottom:72px}.combat-quick-bar-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.combat-quick-bar-toggle{bottom:72px;right:12px;}}
    `;
    document.head.appendChild(style);
  }

  function _loadSavedSize() {
    try {
      const saved = JSON.parse(global.localStorage.getItem(SIZE_KEY) || 'null');
      if (saved && saved.w && saved.h && root) {
        root.style.width  = Math.max(280, Math.min(global.innerWidth  - 28, saved.w)) + 'px';
        root.style.height = Math.max(140, Math.min(global.innerHeight * 0.85, saved.h)) + 'px';
      }
    } catch (_e) {}
  }

  function _watchSize() {
    if (typeof ResizeObserver === 'undefined' || !root) return;
    const ro = new ResizeObserver(function () {
      if (state.minimized) return;
      try {
        global.localStorage.setItem(SIZE_KEY, JSON.stringify({ w: root.offsetWidth, h: root.offsetHeight }));
      } catch (_e) {}
    });
    ro.observe(root);
  }

  function _ensureRoot() {
    if (root) return root;
    _installStyles();
    root = document.createElement('aside');
    root.id = 'combat-quick-bar';
    root.className = 'combat-quick-bar';
    root.setAttribute('aria-label', 'Combat quick actions');
    document.body.appendChild(root);
    _loadSavedSize();
    _watchSize();
    const toggle = document.createElement('button');
    toggle.id = 'combat-quick-bar-toggle';
    toggle.type = 'button';
    toggle.className = 'combat-quick-bar-toggle';
    toggle.textContent = '⚔ Quick Bar';
    toggle.addEventListener('pointerdown', _startToggleDrag);
    toggle.addEventListener('pointermove', _dragToggle);
    toggle.addEventListener('pointerup', _stopToggleDrag);
    toggle.addEventListener('pointercancel', _stopToggleDrag);
    toggle.addEventListener('click', function (ev) {
      ev.stopPropagation();
      if (suppressToggleClick) { suppressToggleClick = false; return; }
      openManual();
    });
    document.body.appendChild(toggle);
    root.addEventListener('click', _handleClick);
    root.addEventListener('pointermove', _drag);
    root.addEventListener('pointerup', _stopDrag);
    root.addEventListener('pointercancel', _stopDrag);
    _watchBarResize();
    return root;
  }

  function _clampPoint(x, y, w, h) {
    const width = Math.max(48, Number(w) || 48);
    const height = Math.max(40, Number(h) || 40);
    return {
      x: Math.max(8, Math.min(global.innerWidth - width - 8, Number(x) || 8)),
      y: Math.max(8, Math.min(global.innerHeight - height - 8, Number(y) || 8)),
    };
  }

  function _applyTogglePosition() {
    const toggle = document.getElementById('combat-quick-bar-toggle');
    if (!toggle) return;
    if (Number.isFinite(Number(state.buttonX)) && Number.isFinite(Number(state.buttonY))) {
      const point = _clampPoint(state.buttonX, state.buttonY, toggle.offsetWidth || 120, toggle.offsetHeight || 36);
      state.buttonX = point.x;
      state.buttonY = point.y;
      toggle.style.left = point.x + 'px';
      toggle.style.top = point.y + 'px';
      toggle.style.right = 'auto';
      toggle.style.bottom = 'auto';
    } else {
      toggle.style.left = 'auto';
      toggle.style.top = 'auto';
      toggle.style.right = global.innerWidth < 760 ? '12px' : '18px';
      toggle.style.bottom = global.innerWidth < 760 ? '72px' : '84px';
    }
  }

  function _applyPosition() {
    if (!root) return;
    if (Number.isFinite(Number(state.x)) && Number.isFinite(Number(state.y))) {
      const point = _clampPoint(state.x, state.y, root.offsetWidth || 280, root.offsetHeight || 140);
      state.x = point.x;
      state.y = point.y;
      root.style.left = point.x + 'px';
      root.style.top = Math.max(8, Math.min(global.innerHeight - (root.offsetHeight || 140) - 8, point.y)) + 'px';
      root.style.bottom = 'auto';
      root.style.transform = 'none';
    } else {
      root.style.left = '50%';
      root.style.top = 'auto';
      root.style.bottom = '88px';
      root.style.transform = 'translateX(-50%)';
    }
    if (state.w && Number.isFinite(Number(state.w))) root.style.width = Math.max(280, Math.min(global.innerWidth - 16, Number(state.w))) + 'px';
    if (state.h && Number.isFinite(Number(state.h))) root.style.height = Math.max(140, Math.min(global.innerHeight * 0.85, Number(state.h))) + 'px';
  }

  var _resizeObserver = null;
  function _watchBarResize() {
    if (_resizeObserver || typeof ResizeObserver === 'undefined') return;
    _resizeObserver = new ResizeObserver(function () {
      if (!root) return;
      state.w = root.offsetWidth;
      state.h = root.offsetHeight;
      _saveState();
    });
    _resizeObserver.observe(root);
  }

  function _startDrag(ev) {
    if (ev.target.closest('button,[data-qb-minimize],[data-qb-hide]')) return;
    const rect = root.getBoundingClientRect();
    // Once the player interacts with the bar, convert the default bottom anchor
    // to an explicit top/left anchor so native resize:both can grow downward too.
    if (!Number.isFinite(Number(state.x)) || !Number.isFinite(Number(state.y))) {
      state.x = rect.left;
      state.y = rect.top;
      _applyPosition();
    }
    dragging = { dx: ev.clientX - rect.left, dy: ev.clientY - rect.top };
    root.setPointerCapture && root.setPointerCapture(ev.pointerId);
  }
  function _drag(ev) {
    if (!dragging) return;
    state.x = ev.clientX - dragging.dx;
    state.y = ev.clientY - dragging.dy;
    _applyPosition();
  }
  function _stopDrag() {
    if (!dragging) return;
    dragging = null;
    _saveState();
  }

  function _startToggleDrag(ev) {
    const toggle = document.getElementById('combat-quick-bar-toggle');
    if (!toggle) return;
    const rect = toggle.getBoundingClientRect();
    toggleDragging = { dx: ev.clientX - rect.left, dy: ev.clientY - rect.top, startX: ev.clientX, startY: ev.clientY, moved: false };
    toggle.classList.add('is-dragging');
    toggle.setPointerCapture && toggle.setPointerCapture(ev.pointerId);
  }
  function _dragToggle(ev) {
    if (!toggleDragging) return;
    if (Math.abs(ev.clientX - toggleDragging.startX) > 4 || Math.abs(ev.clientY - toggleDragging.startY) > 4) toggleDragging.moved = true;
    const toggle = document.getElementById('combat-quick-bar-toggle');
    const point = _clampPoint(ev.clientX - toggleDragging.dx, ev.clientY - toggleDragging.dy, toggle?.offsetWidth || 120, toggle?.offsetHeight || 36);
    state.buttonX = point.x;
    state.buttonY = point.y;
    _applyTogglePosition();
  }
  function _stopToggleDrag() {
    if (!toggleDragging) return;
    suppressToggleClick = !!toggleDragging.moved;
    toggleDragging = null;
    const toggle = document.getElementById('combat-quick-bar-toggle');
    if (toggle) toggle.classList.remove('is-dragging');
    _saveState();
  }

  function _typeLabel(action, fallback) {
    const lane = _firstText(action && action.quickBarLane, action && action.actionType, fallback, 'action').toLowerCase();
    if (/bonus/.test(lane)) return 'bonus action';
    if (/reaction/.test(lane)) return 'reaction';
    if (/cantrip/.test(lane)) return 'cantrip';
    if (/spell/.test(lane)) return 'spell';
    if (/^action$/.test(lane) || !lane) {
      const sourceType = _firstText(action && action.sourceType, action && action.source, '').toLowerCase();
      if (/weapon/.test(sourceType)) return 'weapon attack';
      if (/item_spell|item-spell/.test(sourceType)) return 'magic item spell';
      if (/item_action|item-action|^item$/.test(sourceType)) return 'item action';
      if (/feature/.test(sourceType)) return 'class feature';
    }
    return 'action';
  }

  function _formatAttackBonus(value) {
    const raw = _firstText(value, '');
    if (!raw) return '';
    const parsed = Number(String(raw).replace(/[^+\-\d.]/g, ''));
    if (Number.isFinite(parsed)) return parsed >= 0 ? '+' + parsed : String(parsed);
    return raw;
  }

  function _actionAttackText(action) {
    return _formatAttackBonus(_firstText(
      action && action.quickBarAttackText,
      action && action.attackBonus,
      action && action.attack_bonus,
      action && action.toHit,
      ''
    ));
  }

  function _actionDamageText(action) {
    const damage = _firstText(
      action && action.quickBarDamageText,
      action && action.damage,
      action && action.damageText,
      action && action.damage_formula,
      action && action.base_damage_formula,
      ''
    );
    const type = _firstText(action && action.damageType, action && action.damage_type, '');
    return damage ? (damage + (type && String(damage).toLowerCase().indexOf(String(type).toLowerCase()) === -1 ? ' ' + type : '')) : '';
  }

  function _actionSourceText(action) {
    return _firstText(
      action && action.quickBarSourceLabel,
      action && action.sourceName,
      action && action.itemName,
      ''
    );
  }

  function _actionDetailPills(action) {
    const attackText = _actionAttackText(action);
    const damageText = _actionDamageText(action);
    const saveText = _firstText(action && action.quickBarSaveText, action && action.saveText, '');
    const rangeText = _firstText(action && action.quickBarRangeText, action && action.range, '');
    const castTimeText = _firstText(action && action.quickBarCastTimeText, '');
    const sourceText = _actionSourceText(action);
    const attackLabel = action && action.quickBarAttackKind === 'spell' ? 'Spell atk ' : 'Atk ';
    const pills = [];
    if (attackText) pills.push('<span class="combat-quick-pill accent">' + attackLabel + _esc(attackText) + '</span>');
    if (saveText) pills.push('<span class="combat-quick-pill accent">' + _esc(saveText) + '</span>');
    if (damageText) pills.push('<span class="combat-quick-pill damage">Dmg ' + _esc(damageText) + '</span>');
    if (rangeText) pills.push('<span class="combat-quick-pill">' + _esc(rangeText) + '</span>');
    if (castTimeText && !/^action$/i.test(String(castTimeText))) pills.push('<span class="combat-quick-pill">' + _esc(castTimeText) + '</span>');
    if (sourceText) pills.push('<span class="combat-quick-pill source">Source: ' + _esc(sourceText) + '</span>');
    return pills.join('');
  }

  function _tile(action, category, idx) {
    const key = _firstText(action && action.id, action && action.name, category + '-' + idx);
    const disabled = action && action.quickBarCanUse === false;
    const used = !!(action && action.quickBarUsedThisTurn);
    const needsTarget = !!(action && action.quickBarNeedsTarget);
    const needsSlot = !!(action && action.quickBarNeedsSlot && disabled);
    const stateText = needsSlot ? 'Needs slot' : needsTarget ? 'Needs target' : '';
    const classes = ['combat-quick-tile'];
    if (disabled) classes.push('is-disabled');
    if (used) classes.push('is-used');
    if (needsTarget) classes.push('needs-target');
    if (needsSlot) classes.push('needs-slot');
    const name = _firstText(action && action.name, action && action.displayName, 'Action');
    const type = action && action.quickBarType === 'spell' ? _typeLabel(action, 'spell') : _typeLabel(action, category);
    const summary = _firstText(action && action.quickBarInfoSummary, action && action.desc, action && action.description, action && action.current && action.current.effect, action && action.quickBarSlotSummary, action && action.resourceSummary, 'Open for details');
    const uses = action && action.quickBarResourceState ? action.quickBarResourceState : null;
    const usesHasRemaining = uses && uses.remaining !== null && uses.remaining !== undefined && Number.isFinite(Number(uses.remaining));
    const usesHasMax = uses && uses.max !== null && uses.max !== undefined && Number.isFinite(Number(uses.max));
    const usesText = _firstText(action && action.quickBarUsesText, (usesHasRemaining && usesHasMax) ? (Number(uses.remaining) + '/' + Number(uses.max)) : '', action && action.quickBarSlotSummary, '');
    const pillTone = disabled ? 'danger' : used ? 'warn' : 'good';
    const titleText = disabled ? (action && action.quickBarDisabledReason || 'Unavailable') : summary;
    return `<button type="button" class="${classes.join(' ')}" data-qb-kind="${_esc(category)}" data-qb-key="${_esc(key)}" data-state="${_esc(stateText)}" title="${_esc(titleText)}">
      ${category !== 'resource' ? `<span role="button" tabindex="0" class="combat-quick-pin ${action && action.quickBarPinned ? 'is-pinned' : ''}" data-qb-pin="${_esc(action && action.quickBarPickKey ? action.quickBarPickKey : (category + ':' + key))}" data-qb-pin-kind="${_esc(category === 'spell' ? 'spell' : 'action')}" title="${action && action.quickBarPinned ? 'Remove from custom quick picks' : 'Pin to custom top 5'}">${action && action.quickBarPinned ? '★' : '☆'}</span>` : ''}
      <span class="combat-quick-name">${_esc(name)}</span>
      <span class="combat-quick-meta">${_esc(summary)}</span>
      <span class="combat-quick-pill-row">
        <span class="combat-quick-pill ${pillTone}">${_esc(disabled ? (action && action.quickBarDisabledReason || 'Unavailable') : used ? 'Used this turn' : 'Available')}</span>
        <span class="combat-quick-pill">${_esc(type)}</span>
        ${usesText ? `<span class="combat-quick-pill">${_esc(usesText)}</span>` : ''}
        ${_actionDetailPills(action)}
        ${action && action.quickBarConcentration ? '<span class="combat-quick-pill warn">Concentration</span>' : ''}
      </span>
    </button>`;
  }

  function _section(title, items, category, empty) {
    const rows = _safeArray(items);
    if (!rows.length) return `<section class="combat-quick-bar-section"><div class="combat-quick-bar-section-title">${_esc(title)}</div><div class="combat-quick-empty">${_esc(empty || 'None')}</div></section>`;
    return `<section class="combat-quick-bar-section"><div class="combat-quick-bar-section-title">${_esc(title)}</div><div class="combat-quick-bar-grid">${rows.map(function (item, idx) { return _tile(item, category, idx); }).join('')}</div></section>`;
  }

  const QUICK_CATEGORY_ORDER = ['Attack', 'Spell', 'Bonus Action', 'Reaction', 'Class Feature', 'Item', 'Limited Use', 'Utility'];

  function _customizePanel(model) {
    if (!state.customizing) return '';
    const picks = _safeArray(model && model.quickPicks);
    const limit = Number(model && model.quickPickLimit) || 5;
    const atLimit = picks.length >= limit;
    const candidates = global.CombatQuickSelectors && typeof global.CombatQuickSelectors.buildQuickActionCandidates === 'function'
      ? global.CombatQuickSelectors.buildQuickActionCandidates()
      : [];
    const groups = new Map();
    candidates.forEach(function (item) {
      const cat = _firstText(item.category, 'Utility');
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat).push(item);
    });
    const sections = QUICK_CATEGORY_ORDER.filter(function (cat) { return groups.has(cat); }).map(function (cat) {
      const rows = groups.get(cat);
      return `<div class="combat-quick-pick-group">
        <div class="combat-quick-bar-section-title">${_esc(cat)}</div>
        <div class="combat-quick-pick-list">${rows.map(function (item) {
          const pickKey = _firstText(item.quickBarPickKey, (item.category === 'Spell' ? 'spell' : 'action') + ':' + _firstText(item.id, item.name));
          const picked = picks.indexOf(pickKey) >= 0;
          const disableAdd = !picked && atLimit;
          const note = [_firstText(item.sourceType, ''), _firstText(item.resourceCost, item.cost, ''), _firstText(item.preview, '')].filter(Boolean).join(' · ') || 'Action';
          return `<button type="button" class="combat-quick-pick ${picked ? 'is-picked' : ''}" ${disableAdd ? 'disabled' : ''} data-qb-pick-kind="${_esc(item.category === 'Spell' ? 'spell' : 'action')}" data-qb-pick-key="${_esc(pickKey)}">${picked ? '★ ' : '☆ '}${_esc(_firstText(item.name, item.displayName, 'Choice'))}<small>${_esc(note)}</small></button>`;
        }).join('')}</div>
      </div>`;
    }).join('');
    return `<section class="combat-quick-customize">
      <div class="combat-quick-customize-head"><strong>Choose your top ${_esc(limit)}</strong><span>${_esc(picks.length)}/${_esc(limit)} selected · click to swap any time</span></div>
      ${sections || '<div class="combat-quick-empty">No playable actions found yet.</div>'}
    </section>`;
  }

  function render() {
    _ensureRoot();
    const runtime = _runtime();
    const combat = runtime.combat || { active: false };
    const role = _firstText(runtime.role, global.ROLE, '').toLowerCase();
    const turnKey = combat.active ? String((combat.round || 1) + ':' + (combat.turn || 0)) : '';
    const dismissed = !!(combat.active && state.dismissedUntilManualOpen && state.dismissedForCombatTurn === turnKey);
    const roleCanUseQuickBar = role === 'player';
    const shouldShow = roleCanUseQuickBar && !dismissed && (!!combat.active || !!state.manual);
    const toggle = document.getElementById('combat-quick-bar-toggle');
    // Toggle is visible for known players; when role is unknown don't change it
    if (toggle && role) toggle.hidden = !roleCanUseQuickBar;
    // During active combat the toggle must always be visible for players so they
    // can reopen the bar after closing it — never let dismissed state hide it.
    if (toggle && roleCanUseQuickBar && combat.active) toggle.hidden = false;
    if (!shouldShow) {
      root.hidden = true;
      if (toggle && roleCanUseQuickBar) toggle.hidden = false;
      _applyTogglePosition();
      state.combatWasActive = !!combat.active;
      _saveState();
      return;
    }
    if (combat.active && !state.combatWasActive && !state.dismissedUntilManualOpen) state.minimized = false;
    state.combatWasActive = !!combat.active;
    const model = global.CombatQuickSelectors && typeof global.CombatQuickSelectors.selectQuickActions === 'function'
      ? global.CombatQuickSelectors.selectQuickActions(runtime.charSheet || {})
      : { primaryActions: [], bonusActions: [], reactions: [], topSpells: [], resources: [], concentration: null };
    const current = _safeArray(combat.combatants)[Math.max(0, Number(combat.turn || 0))] || null;
    const targetName = runtime.selectedTargetId && runtime.tokens ? _firstText(runtime.tokens[runtime.selectedTargetId] && runtime.tokens[runtime.selectedTargetId].name, 'Selected') : 'No target';
    root.hidden = false;
    if (toggle) toggle.hidden = true;
    root.classList.toggle('is-minimized', !!state.minimized);
    root.innerHTML = `<header class="combat-quick-bar-head">
      <div class="combat-quick-bar-title">⚔ Quick Actions <span class="combat-quick-bar-sub">${combat.active ? `Round ${_esc(combat.round || 1)} · ${_esc(current && current.name || 'Turn')}` : 'Manual'}</span></div>
      <div class="combat-quick-bar-head-actions">
        <button type="button" class="combat-quick-sheet-btn" data-qb-customize>${state.customizing ? 'Done' : 'Customize Top 5'}</button>
        <button type="button" class="combat-quick-sheet-btn" data-qb-open-notes>Notes</button>
        <button type="button" class="combat-quick-sheet-btn" data-qb-open-sheet>Open Full Sheet</button>
        <button type="button" class="combat-quick-bar-icon-btn" data-qb-minimize title="Minimise">${state.minimized ? '▣' : '—'}</button>
        <button type="button" class="combat-quick-bar-icon-btn" data-qb-hide title="Hide">×</button>
      </div>
    </header>
    ${state.minimized ? '' : `<div class="combat-quick-bar-body">
      <div class="combat-quick-status"><span>Target: ${_esc(targetName)}</span>${model.concentration ? `<span class="combat-quick-resource">Concentration: ${_esc(model.concentration)}</span>` : '<span>Concentration: none</span>'}${model.quickPicks && model.quickPicks.length ? `<span>Custom picks: ${_esc(model.quickPicks.length)}/${_esc(model.quickPickLimit || 5)}</span>` : '<span>Auto picks · customize top 5 any time</span>'}</div>
      ${_customizePanel(model)}
      ${(!model.primaryActions?.length && !model.topSpells?.length && !model.bonusActions?.length && !model.reactions?.length && !model.magicItemActions?.length) ? '<div class="combat-quick-empty">No quick actions are available yet. Loading quick actions… If this remains, open the full sheet and add attacks, spells, or actions.</div>' : ''}
      ${_section('Primary', model.primaryActions, 'action', 'No attacks/actions found on the sheet.')}
      ${_section('Spells', model.topSpells, 'spell', 'No spell clutter for this character.')}
      ${_section('Bonus', model.bonusActions, 'bonus', 'No bonus actions found.')}
      ${_section('Reaction', model.reactions, 'reaction', 'No reactions found.')}
      ${model.magicItemActions && model.magicItemActions.length ? _section('Magic Item Actions', model.magicItemActions, 'magic', 'No equipped magic item actions found.') : ''}
      ${model.resources && model.resources.length ? `<div class="combat-quick-resource-row">${model.resources.map(function (r) { return `<button type="button" class="combat-quick-resource" data-qb-kind="resource" data-qb-key="${_esc(_firstText(r.name))}">${_esc(_firstText(r.name, 'Resource'))}: ${_esc(_firstText(r.quickBarUsesText, r.summary, 'Tracked'))}</button>`; }).join('')}</div>` : ''}
    </div>`}`;
    const head = root.querySelector('.combat-quick-bar-head');
    if (head) {
      head.addEventListener('pointerdown', _startDrag);
    }
    _applyPosition();
    _applyTogglePosition();
    _saveState();
  }

  function _actionMatchKeys(action) {
    return [
      action && action.id,
      action && action.itemId,
      action && action.item_id,
      action && action.actionId,
      action && action.action_id,
      action && action.combatCardId,
      action && action.name,
      action && action.displayName,
    ].filter(function (value) { return value !== null && value !== undefined && String(value).trim(); }).map(String);
  }

  function _slug(value) {
    return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  }

  function _findAction(key) {
    const model = global.CombatQuickSelectors && global.CombatQuickSelectors.selectQuickActions(_runtime().charSheet || {});
    const all = [].concat(model.primaryActions || [], model.bonusActions || [], model.reactions || [], model.resources || [], model.magicItemActions || []);
    const raw = String(key || '').trim();
    const rawLower = raw.toLowerCase();
    const rawSlug = _slug(raw);
    return all.find(function (item) {
      const keys = _actionMatchKeys(item);
      return keys.some(function (candidate) {
        const text = String(candidate || '').trim();
        return text === raw || text.toLowerCase() === rawLower || (!!rawSlug && _slug(text) === rawSlug);
      });
    }) || null;
  }

  function _findSpell(key) {
    const model = global.CombatQuickSelectors && global.CombatQuickSelectors.selectQuickActions(_runtime().charSheet || {});
    return _safeArray(model.topSpells).find(function (item) { return _firstText(item && item.id, item && item.name) === key; }) || null;
  }

  function _handleClick(ev) {
    const min = ev.target.closest('[data-qb-minimize]');
    if (min) { ev.preventDefault(); ev.stopPropagation(); state.minimized = !state.minimized; state.dismissedUntilManualOpen = false; _saveState(); render(); return; }
    const hide = ev.target.closest('[data-qb-hide]');
    if (hide) { ev.preventDefault(); ev.stopPropagation(); dismissForTurn(); return; }
    const customize = ev.target.closest('[data-qb-customize]');
    if (customize) { state.customizing = !state.customizing; _saveState(); render(); return; }
    const pin = ev.target.closest('[data-qb-pin]');
    if (pin) {
      ev.preventDefault();
      ev.stopPropagation();
      const raw = String(pin.getAttribute('data-qb-pin') || '');
      if (global.CombatQuickSelectors && typeof global.CombatQuickSelectors.toggleQuickPickKey === 'function') {
        global.CombatQuickSelectors.toggleQuickPickKey(raw);
      } else if (global.CombatQuickSelectors && typeof global.CombatQuickSelectors.toggleQuickPick === 'function') {
        global.CombatQuickSelectors.toggleQuickPick(raw.indexOf('spell:') === 0 ? 'spell' : 'action', { id: raw.replace(/^(action|spell):/, '') });
      }
      render();
      return;
    }
    const pick = ev.target.closest('[data-qb-pick-key]');
    if (pick) {
      const raw = String(pick.getAttribute('data-qb-pick-key') || '');
      if (global.CombatQuickSelectors && typeof global.CombatQuickSelectors.toggleQuickPickKey === 'function') global.CombatQuickSelectors.toggleQuickPickKey(raw);
      else if (global.CombatQuickSelectors && typeof global.CombatQuickSelectors.toggleQuickPick === 'function') global.CombatQuickSelectors.toggleQuickPick(raw.indexOf('spell:') === 0 ? 'spell' : 'action', { id: raw.replace(/^(action|spell):/, '') });
      render();
      return;
    }
    const notes = ev.target.closest('[data-qb-open-notes]');
    if (notes) { if (typeof global.openCharacterStickyNotes === 'function') global.openCharacterStickyNotes(); return; }
    const sheet = ev.target.closest('[data-qb-open-sheet]');
    if (sheet) { if (typeof global.openCharacterBook === 'function') global.openCharacterBook('premiumsheet'); else if (typeof global.toggleSheet === 'function') global.toggleSheet(); return; }
    const tile = ev.target.closest('[data-qb-kind][data-qb-key]');
    if (!tile || tile.disabled || tile.classList.contains('is-disabled')) return;
    const kind = tile.getAttribute('data-qb-kind');
    const key = tile.getAttribute('data-qb-key');
    if (kind === 'spell') {
      const spell = _findSpell(key);
      if (spell && typeof global.executeCombatQuickBarSpell === 'function') {
        global.executeCombatQuickBarSpell(spell);
      } else if (spell && typeof global.playerInspectSpell === 'function') {
        global.playerInspectSpell(spell.id || spell.name);
      }
      render();
      return;
    }
    if (kind === 'resource') {
      if (global.CSContainer && typeof global.CSContainer.openDetailDrawer === 'function') {
        const action = _findAction(key) || { name: key };
        global.CSContainer.openDetailDrawer({ kicker: 'Resource', title: action.name || key, subtitle: action.summary || 'Tracked character resource', sections: [{ title: 'Summary', body: action.note || action.summary || 'Open the full sheet to spend or recover this resource.' }] });
      }
      return;
    }
    try {
      const action = _findAction(key);
      const actionName = _firstText(action && action.name, key, 'Quick action');
      const actionSource = _firstText(action && action.source, kind);
      if (action && /^(weapon|equip_only|system_unarmed|attack)$/i.test(actionSource)) {
        if (typeof global.openCombatQuickBarWeaponAction === 'function') {
          global.openCombatQuickBarWeaponAction(action);
        } else {
          const _missingMsg = '[CombatQuickBar] openCombatQuickBarWeaponAction is missing. No action spent.';
          if (global.console) global.console.error(_missingMsg);
          if (typeof global.showToast === 'function') global.showToast('Weapon roll handler is not loaded. No action spent.');
        }
      } else if (action && typeof global.playerUseAction === 'function') {
        let chargeOverride = null;
        if (action.quickBarVariableChargeCost) {
          const min = Number(action.quickBarChargeCostMin) || 1;
          const max = Number(action.quickBarChargeCostMax) || min;
          const raw = global.prompt(`Spend how many charges on ${_firstText(action.name, 'this item')}? (${min}-${max})`, String(min));
          if (raw === null) { render(); return; }
          const parsed = Math.max(min, Math.min(max, Math.round(Number(raw)) || min));
          chargeOverride = parsed;
        }
        global.playerUseAction(actionSource, _firstText(action.id, action.name), chargeOverride !== null ? { chargeCost: chargeOverride } : undefined);
        global.CombatQuickSelectors && global.CombatQuickSelectors.markUsed(key);
      } else if (action && global.CSContainer && typeof global.CSContainer.openDetailDrawer === 'function') {
        global.CSContainer.openDetailDrawer({ kicker: 'Action', title: action.name || key, subtitle: action.desc || action.description || 'Quick action', sections: [{ title: 'Details', body: action.longText || action.description || action.desc || 'Open the full sheet for details.' }] });
      }
    } catch (err) {
      if (global.console && typeof global.console.warn === 'function') {
        global.console.warn('[CombatQuickBar] Quick action card failed; card was not executed.', { name: key, kind: kind, error: err });
      }
      if (typeof global.showToast === 'function') global.showToast('Quick action failed for ' + key + '. Check console for details.');
    }
    render();
  }

  function openManual() {
    state.manual = true;
    state.minimized = false;
    state.dismissedUntilManualOpen = false;
    state.dismissedForCombatTurn = '';
    _saveState();
    render();
  }

  function dismissForTurn() {
    const runtime = _runtime();
    const combat = runtime.combat || {};
    state.manual = false;
    state.minimized = false;
    state.dismissedUntilManualOpen = true;
    state.dismissedForCombatTurn = combat.active ? String((combat.round || 1) + ':' + (combat.turn || 0)) : 'manual';
    _saveState();
    render();
  }

  function resetQuickBarVisibility() {
    try { global.localStorage.removeItem(STORAGE_KEY); global.localStorage.removeItem(SIZE_KEY); } catch (_e) {}
    state = Object.assign({}, DEFAULT_STATE);
    _saveState();
    render();
  }

  function toggleManual() {
    if (state.dismissedUntilManualOpen || root?.hidden || !state.manual) openManual();
    else { state.manual = false; _saveState(); render(); }
  }

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      const modal = document.getElementById('combat-quick-action-modal');
      if (modal) { modal.remove(); ev.stopPropagation(); }
      else if (root && !root.hidden && document.activeElement && root.contains(document.activeElement)) dismissForTurn();
    }
  });

  _loadState();
  function refreshCombatQuickActions() {
    render();
    if (global.CombatQuickActions && typeof global.CombatQuickActions.refreshSpellModalSlots === 'function') {
      global.CombatQuickActions.refreshSpellModalSlots();
    }
  }

  global.CombatQuickBar = { render: render, toggleManual: toggleManual, openManual: openManual, dismissForTurn: dismissForTurn, resetQuickBarVisibility: resetQuickBarVisibility, refreshCombatQuickActions: refreshCombatQuickActions };
  // Also available as top-level shortcuts for quick recovery and slot/rest sync.
  global.resetQuickBarVisibility = resetQuickBarVisibility;
  global.refreshCombatQuickActions = refreshCombatQuickActions;
  ['character:spell-state-updated', 'character:runtime-updated', 'character:resources-updated', 'character:rest-completed', 'spellSlots:updated'].forEach(function (eventName) {
    global.addEventListener && global.addEventListener(eventName, refreshCombatQuickActions);
  });
  document.addEventListener('DOMContentLoaded', render);
}(window));
