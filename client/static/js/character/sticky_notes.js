(function () {
  'use strict';

  const DEFAULT_NOTES = Object.freeze({
    session: '',
    private: '',
    updated_at: '',
    pinned: false,
    minimized: false,
    widget_position: { x: 100, y: 100 },
    widget_size: { width: 320, height: 260 },
  });
  const SAVE_DEBOUNCE_MS = 700;
  const META_DEBOUNCE_MS = 300;
  let _saveTimer = null;
  let _lastStatus = 'idle';
  let _drag = null;
  let _resize = null;
  let _activeNotes = clone(DEFAULT_NOTES);

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function role() {
    try { return String(ROLE || 'viewer').toLowerCase(); } catch (_) { return 'viewer'; }
  }

  function profileId() {
    try {
      if (typeof resolveActiveCharProfileId === 'function') return String(resolveActiveCharProfileId() || '').trim();
    } catch (_) {}
    return '';
  }

  function charProfilesList() {
    try { return Array.isArray(charProfiles) ? charProfiles : []; } catch (_) { return []; }
  }

  function activeProfile() {
    const id = profileId();
    return charProfilesList().find((entry) => String(entry && entry.id || '') === id) || null;
  }

  function text(value, limit) {
    return String(value == null ? '' : value).slice(0, limit || 12000);
  }

  function num(value, fallback, min, max) {
    const parsed = parseInt(value, 10);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.max(min, Math.min(max, parsed));
  }

  function normalizeNotes(source, fallbackProfile) {
    const profile = fallbackProfile || activeProfile() || {};
    const raw = (source && typeof source === 'object') ? source : (profile.characterNotes && typeof profile.characterNotes === 'object' ? profile.characterNotes : {});
    const book = (profile.charBook && typeof profile.charBook === 'object') ? profile.charBook : {};
    const sheet = (profile.charSheet && typeof profile.charSheet === 'object') ? profile.charSheet : {};
    const legacyQuick = safeValue('char-notes');
    const legacyBook = safeValue('cb-campaign-notes');
    const privateNote = text(raw.private || legacyQuick || legacyBook || profile.notes || book.campaignNotes || sheet.notes || '');
    const sessionNote = text(raw.session || book.sessionNotes || sheet.sessionNotes || '');
    const pos = (raw.widget_position && typeof raw.widget_position === 'object') ? raw.widget_position : {};
    const size = (raw.widget_size && typeof raw.widget_size === 'object') ? raw.widget_size : {};
    return {
      session: sessionNote,
      private: privateNote,
      updated_at: text(raw.updated_at || '', 40),
      pinned: !!raw.pinned,
      minimized: !!raw.minimized,
      widget_position: {
        x: num(pos.x, DEFAULT_NOTES.widget_position.x, 0, Math.max(0, window.innerWidth - 160)),
        y: num(pos.y, DEFAULT_NOTES.widget_position.y, 0, Math.max(0, window.innerHeight - 80)),
      },
      widget_size: {
        width: num(size.width, DEFAULT_NOTES.widget_size.width, 240, Math.max(260, window.innerWidth - 16)),
        height: num(size.height, DEFAULT_NOTES.widget_size.height, 160, Math.max(180, window.innerHeight - 16)),
      },
    };
  }

  function safeValue(id) {
    return document.getElementById(id)?.value || '';
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el && el.value !== value) el.value = value;
  }

  function syncLegacyFields(notes) {
    setValue('char-notes', notes.private || '');
    setValue('cb-campaign-notes', notes.private || '');
    try {
      if (typeof _charSheet === 'object' && _charSheet) {
        _charSheet.notes = notes.private || '';
        _charSheet.campaignNotes = notes.private || '';
        _charSheet.sessionNotes = notes.session || '';
      }
    } catch (_) {}
    try {
      if (typeof syncCharSheetFromBookData === 'function' && typeof getCharacterBookDataFromUI === 'function') {
        syncCharSheetFromBookData(getCharacterBookDataFromUI());
      }
    } catch (_) {}
    try {
      if (typeof requestCharacterBookOverviewRender === 'function') requestCharacterBookOverviewRender('stickyNotes');
    } catch (_) {}
  }

  function ensureStyle() {
    if (document.getElementById('sticky-notes-style')) return;
    const style = document.createElement('style');
    style.id = 'sticky-notes-style';
    style.textContent = `
      .sticky-notes-widget{position:fixed;z-index:9500;display:flex;flex-direction:column;min-width:240px;min-height:160px;border:1px solid rgba(212,166,55,.5);border-radius:12px;background:linear-gradient(180deg,rgba(38,30,14,.98),rgba(18,15,12,.96));box-shadow:0 18px 42px rgba(0,0,0,.45);color:var(--parchment,#f2e6c9);overflow:hidden;resize:none;}
      .sticky-notes-widget.minimized{min-height:0;height:auto!important;}
      .sticky-notes-header{display:flex;align-items:center;justify-content:space-between;gap:.45rem;padding:.45rem .55rem;border-bottom:1px solid rgba(212,166,55,.22);cursor:move;user-select:none;background:rgba(0,0,0,.18);}
      .sticky-notes-title{font-family:'Cinzel',serif;font-size:.78rem;color:var(--gold,#d4a637);letter-spacing:.04em;}
      .sticky-notes-actions{display:flex;align-items:center;gap:.25rem;}
      .sticky-notes-btn{border:1px solid rgba(255,255,255,.12);border-radius:6px;background:rgba(255,255,255,.06);color:var(--parchment,#f2e6c9);font-size:.68rem;padding:.18rem .35rem;cursor:pointer;}
      .sticky-notes-btn.active{border-color:rgba(0,229,204,.55);color:#9ff6ea;background:rgba(0,229,204,.12);}
      .sticky-notes-body{display:flex;flex-direction:column;gap:.45rem;flex:1;min-height:0;padding:.55rem;}
      .sticky-notes-widget.minimized .sticky-notes-body,.sticky-notes-widget.minimized .sticky-notes-resize{display:none;}
      .sticky-notes-label{display:flex;align-items:center;justify-content:space-between;font-size:.62rem;color:var(--parchment-dim,#a89c83);text-transform:uppercase;letter-spacing:.06em;}
      .sticky-notes-textarea{width:100%;box-sizing:border-box;flex:1;min-height:74px;resize:none;border:1px solid rgba(255,255,255,.14);border-radius:8px;background:rgba(0,0,0,.28);color:var(--parchment,#f2e6c9);font-size:.76rem;line-height:1.45;padding:.48rem .55rem;outline:none;}
      .sticky-notes-textarea:focus{border-color:rgba(0,229,204,.55);box-shadow:0 0 0 2px rgba(0,229,204,.12);}
      .sticky-notes-status{font-size:.62rem;color:var(--parchment-dim,#a89c83);}
      .sticky-notes-status.saving{color:#ffd36a}.sticky-notes-status.saved{color:#8df5ad}.sticky-notes-status.failed{color:#ff8b8b}
      .sticky-notes-resize{position:absolute;right:0;bottom:0;width:18px;height:18px;cursor:nwse-resize;background:linear-gradient(135deg,transparent 45%,rgba(212,166,55,.55) 46%,rgba(212,166,55,.55) 60%,transparent 61%);}
    `;
    document.head.appendChild(style);
  }

  function ensureWidget() {
    ensureStyle();
    let widget = document.getElementById('sticky-notes-widget');
    if (widget) return widget;
    widget = document.createElement('section');
    widget.id = 'sticky-notes-widget';
    widget.className = 'sticky-notes-widget';
    widget.setAttribute('aria-label', 'Live sticky character notes');
    widget.innerHTML = `
      <div class="sticky-notes-header" data-sticky-drag-handle="1">
        <div><div class="sticky-notes-title">Sticky Notes</div><div class="sticky-notes-status" id="sticky-notes-status">Saved</div></div>
        <div class="sticky-notes-actions">
          <button class="sticky-notes-btn" type="button" id="sticky-notes-pin" title="Pin open">Pin</button>
          <button class="sticky-notes-btn" type="button" id="sticky-notes-min" title="Minimise">—</button>
          <button class="sticky-notes-btn" type="button" id="sticky-notes-close" title="Close">×</button>
        </div>
      </div>
      <div class="sticky-notes-body">
        <label class="sticky-notes-label" for="sticky-notes-private">Character notes <span>autosaves</span></label>
        <textarea id="sticky-notes-private" class="sticky-notes-textarea" maxlength="12000" placeholder="Backstory, goals, secrets, reminders, personality, bonds, and flaws…"></textarea>
        <label class="sticky-notes-label" for="sticky-notes-session">Session notes <span>current clues</span></label>
        <textarea id="sticky-notes-session" class="sticky-notes-textarea" maxlength="12000" placeholder="Clues, NPC names, quests, and short-term reminders…"></textarea>
      </div>
      <div class="sticky-notes-resize" data-sticky-resize-handle="1" aria-hidden="true"></div>`;
    document.body.appendChild(widget);
    wireWidget(widget);
    return widget;
  }

  function stopInputHotkeys(event) {
    event.stopPropagation();
  }

  function wireWidget(widget) {
    widget.querySelectorAll('textarea, input, button').forEach((el) => {
      el.addEventListener('keydown', stopInputHotkeys, true);
      el.addEventListener('keypress', stopInputHotkeys, true);
      el.addEventListener('keyup', stopInputHotkeys, true);
    });
    widget.querySelector('#sticky-notes-private')?.addEventListener('input', () => updateFromWidget(true));
    widget.querySelector('#sticky-notes-session')?.addEventListener('input', () => updateFromWidget(true));
    widget.querySelector('#sticky-notes-pin')?.addEventListener('click', () => {
      _activeNotes.pinned = !_activeNotes.pinned;
      renderWidget();
      scheduleSave(META_DEBOUNCE_MS);
    });
    widget.querySelector('#sticky-notes-min')?.addEventListener('click', () => {
      _activeNotes.minimized = !_activeNotes.minimized;
      renderWidget();
      scheduleSave(META_DEBOUNCE_MS);
    });
    widget.querySelector('#sticky-notes-close')?.addEventListener('click', () => {
      flushSave();
      widget.remove();
    });
    widget.querySelector('[data-sticky-drag-handle]')?.addEventListener('pointerdown', startDrag);
    widget.querySelector('[data-sticky-resize-handle]')?.addEventListener('pointerdown', startResize);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction);
  }

  function renderWidget() {
    const widget = ensureWidget();
    const pos = _activeNotes.widget_position || DEFAULT_NOTES.widget_position;
    const size = _activeNotes.widget_size || DEFAULT_NOTES.widget_size;
    widget.style.left = `${pos.x}px`;
    widget.style.top = `${pos.y}px`;
    widget.style.width = `${size.width}px`;
    widget.style.height = `${size.height}px`;
    widget.classList.toggle('minimized', !!_activeNotes.minimized);
    const pin = widget.querySelector('#sticky-notes-pin');
    if (pin) pin.classList.toggle('active', !!_activeNotes.pinned);
    const min = widget.querySelector('#sticky-notes-min');
    if (min) min.textContent = _activeNotes.minimized ? '+' : '—';
    setTextArea('sticky-notes-private', _activeNotes.private || '');
    setTextArea('sticky-notes-session', _activeNotes.session || '');
    setStatus(_lastStatus === 'idle' ? 'saved' : _lastStatus);
  }

  function setTextArea(id, value) {
    const el = document.getElementById(id);
    if (el && el.value !== value) el.value = value;
  }

  function setStatus(status) {
    _lastStatus = status;
    const el = document.getElementById('sticky-notes-status');
    if (!el) return;
    el.className = `sticky-notes-status ${status}`;
    el.textContent = status === 'saving' ? 'Saving…' : status === 'failed' ? 'Save failed' : 'Saved';
  }

  function updateFromWidget(autosave) {
    _activeNotes.private = text(document.getElementById('sticky-notes-private')?.value || '');
    _activeNotes.session = text(document.getElementById('sticky-notes-session')?.value || '');
    _activeNotes.updated_at = new Date().toISOString();
    syncLegacyFields(_activeNotes);
    if (autosave) scheduleSave(SAVE_DEBOUNCE_MS);
  }

  function scheduleSave(delay) {
    if (role() !== 'player') return;
    clearTimeout(_saveTimer);
    setStatus('saving');
    _saveTimer = setTimeout(flushSave, delay || SAVE_DEBOUNCE_MS);
  }

  function flushSave() {
    clearTimeout(_saveTimer);
    _saveTimer = null;
    if (role() !== 'player') return;
    try {
      syncLegacyFields(_activeNotes);
      if (typeof saveCurrentCharProfile !== 'function') throw new Error('saveCurrentCharProfile unavailable');
      saveCurrentCharProfile({ silent: true, stickyNotes: true });
      setTimeout(() => setStatus('saved'), 180);
    } catch (err) {
      setStatus('failed');
      try { console.warn('Sticky notes save failed', err); } catch (_) {}
    }
  }

  function startDrag(event) {
    if (event.target && event.target.closest && event.target.closest('button')) return;
    const widget = ensureWidget();
    const rect = widget.getBoundingClientRect();
    _drag = { pointerId: event.pointerId, dx: event.clientX - rect.left, dy: event.clientY - rect.top };
    widget.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  function startResize(event) {
    const widget = ensureWidget();
    const rect = widget.getBoundingClientRect();
    _resize = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, w: rect.width, h: rect.height };
    widget.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  function onPointerMove(event) {
    const widget = document.getElementById('sticky-notes-widget');
    if (!widget) return;
    if (_drag) {
      _activeNotes.widget_position = {
        x: num(event.clientX - _drag.dx, DEFAULT_NOTES.widget_position.x, 0, Math.max(0, window.innerWidth - 120)),
        y: num(event.clientY - _drag.dy, DEFAULT_NOTES.widget_position.y, 0, Math.max(0, window.innerHeight - 48)),
      };
      renderWidget();
      return;
    }
    if (_resize) {
      _activeNotes.widget_size = {
        width: num(_resize.w + (event.clientX - _resize.x), DEFAULT_NOTES.widget_size.width, 240, Math.max(260, window.innerWidth - 16)),
        height: num(_resize.h + (event.clientY - _resize.y), DEFAULT_NOTES.widget_size.height, 160, Math.max(180, window.innerHeight - 16)),
      };
      renderWidget();
    }
  }

  function endPointerAction() {
    if (_drag || _resize) scheduleSave(META_DEBOUNCE_MS);
    _drag = null;
    _resize = null;
  }

  function openStickyNotes(options) {
    if (role() !== 'player') {
      try { if (typeof showToast === 'function') showToast('Sticky notes are available to players.'); } catch (_) {}
      return;
    }
    const profile = activeProfile();
    _activeNotes = normalizeNotes(profile?.characterNotes, profile);
    if (options && options.focus === false) {
      renderWidget();
      return;
    }
    renderWidget();
    requestAnimationFrame(() => document.getElementById('sticky-notes-private')?.focus());
  }

  function getCanonicalNotesForSave() {
    const widget = document.getElementById('sticky-notes-widget');
    if (widget) updateFromWidget(false);
    else _activeNotes = normalizeNotes(_activeNotes, activeProfile());
    return clone(_activeNotes);
  }

  function refreshFromProfile(profile) {
    _activeNotes = normalizeNotes(profile?.characterNotes, profile);
    const widget = document.getElementById('sticky-notes-widget');
    if (widget) renderWidget();
    if (_activeNotes.pinned && role() === 'player') renderWidget();
  }

  window.CharacterStickyNotes = {
    open: openStickyNotes,
    refreshFromProfile,
    getCanonicalNotesForSave,
    normalizeNotes,
    flushSave,
  };
  window.openCharacterStickyNotes = openStickyNotes;
})();
