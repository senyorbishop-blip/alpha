/**
 * chest_view.js
 * Parchment-styled chest-opening modal for players and DM.
 * Mirrors the ShopView aesthetic — wood border, parchment interior, item cards.
 *
 * Usage:
 *   ChestView.open(propData, role)     — open with chest prop data ('dm' | 'player')
 *   ChestView.close()                  — close and clean up
 *   ChestView.refresh(propData)        — update item list after a take action
 *   ChestView.isOpen()                 — boolean
 *   ChestView.getOpenPropId()          — id of current prop, or null
 *   ChestView.showTakeResult(msg, ok)  — show footer feedback
 *   ChestView._take(idx, qty)          — internal: called by take buttons
 *   ChestView._openManage()            — internal: DM fallback to editing modal
 *
 * propData: the editor prop object { id, name, kind, inventory[], slot_count, hidden }
 * inventory entry: { name, qty, notes, rarity, is_magic, is_identified,
 *                    unidentified_description, attunement_required }
 */
(function () {
  'use strict';

  let _modalEl  = null;
  let _propData = null;
  let _role     = 'player';

  // DM-only loot generator preview state. Reset whenever the chest is (re)opened
  // or the previewed loot is committed to the chest. Locking is preview-only —
  // nothing here persists until _addLootToChest() runs.
  let _lootGen = null; // { items: [{...item, _locked}], budget, gold } | null

  const MODAL_ID = 'dnd-chest-view';

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }


  /* ── Item card renderer ───────────────────────────────────────────────── */
  function _renderItemCard(entry, idx, isDm) {
    const qty           = Math.max(1, Number(entry.qty) || 1);
    const isMagic       = !!entry.is_magic;
    const isIdentified  = entry.is_identified !== false;
    const attunement    = !!entry.attunement_required;

    const displayName  = isMagic && !isIdentified
      ? '??? — Unidentified Magic Item'
      : (entry.name || 'Item');
    const displayNotes = isMagic && !isIdentified && entry.unidentified_description
      ? esc(entry.unidentified_description)
      : esc(entry.notes || '');

    const magicBadge    = isMagic    ? '<span class="cv-badge cv-badge-magic">✨ Magic</span>'         : '';
    const attuneBadge   = attunement ? '<span class="cv-badge cv-badge-attune">⚡ Attunement</span>'   : '';
    const unidentBadge  = isMagic && !isIdentified
      ? '<span class="cv-badge cv-badge-unident">? Unidentified</span>' : '';
    const extraBadgesHtml = (magicBadge || attuneBadge || unidentBadge)
      ? `<div class="cv-badge-row">${magicBadge}${attuneBadge}${unidentBadge}</div>`
      : '';

    const row = window.ItemRow.renderItemRow(entry, {
      mode: 'chest',
      rowClassName: 'cv-item',
      rowId: `cv-item-${idx}`,
      nameOverride: displayName,
      qty,
      noteHtml: displayNotes ? `<div class="cv-item-notes">${displayNotes}</div>` : '',
      extraBadgesHtml,
      takeOne: { onClick: `ChestView._take(${idx}, 1)`, label: '🎒 Take 1' },
      takeAll: { onClick: `ChestView._take(${idx}, ${qty})`, label: `Take All (${qty})` },
    });
    return row.outerHTML;
  }

  function _renderItems() {
    if (!_modalEl || !_propData) return;
    const list = _modalEl.querySelector('.cv-list');
    if (!list) return;
    const isDm      = _role === 'dm';
    const inventory = Array.isArray(_propData.inventory) ? _propData.inventory : [];
    if (!inventory.length) {
      const empty = document.createElement('div');
      empty.className = 'cv-empty';
      empty.textContent = 'This chest is empty.';
      list.replaceChildren(empty);
    } else {
      list.innerHTML = inventory.map((e, i) => _renderItemCard(e, i, isDm)).join('');
    }
  }

  function _updateSlotCount() {
    if (!_modalEl || !_propData) return;
    const el = _modalEl.querySelector('#cv-slot-count');
    if (!el) return;
    const used  = Array.isArray(_propData.inventory) ? _propData.inventory.length : 0;
    const total = Math.max(1, Number(_propData.slot_count) || 12);
    el.textContent = `${used} / ${total} slots`;
  }

  /* ── DM loot generator ───────────────────────────────────────────────────── */

  function _renderLootRow(item, idx) {
    const valueLabel = item.gp != null ? `${item.gp} gp` : '';
    const row = window.ItemRow.renderItemRow(item, {
      mode: 'loot',
      rowClassName: 'cv-loot-row',
      rowId: `cv-loot-row-${idx}`,
      valueLabel,
      locked: !!item._locked,
      lockToggle: {
        onClick: `ChestView._toggleLootLock(${idx})`,
        lockedLabel: '🔒 Locked',
        unlockedLabel: '🔓 Unlocked',
      },
    });
    return row.outerHTML;
  }

  function _renderLootList() {
    if (!_modalEl) return;
    const list  = _modalEl.querySelector('#cv-loot-list');
    const empty = _modalEl.querySelector('#cv-loot-empty');
    if (!list || !empty) return;
    const items = (_lootGen && _lootGen.items) || [];
    empty.style.display = items.length ? 'none' : 'block';
    list.innerHTML = items.map((it, idx) => _renderLootRow(it, idx)).join('');
  }

  const _BUDGET_BAND_COLORS = { light: '#d99a2b', balanced: '#1fab95', generous: '#dd6a52' };

  function _renderLootBudget() {
    if (!_modalEl) return;
    const el = _modalEl.querySelector('#cv-loot-budget');
    if (!el) return;
    const budget = _lootGen && _lootGen.budget;
    if (!budget) { el.style.display = 'none'; return; }
    const totalGp  = Number(budget.total_gp) || 0;
    const targetGp = Number(budget.target_gp) || 0;
    const pct   = targetGp > 0 ? Math.max(0, Math.min(100, Math.round((totalGp / targetGp) * 100))) : 0;
    const color = _BUDGET_BAND_COLORS[budget.band] || _BUDGET_BAND_COLORS.balanced;
    el.style.display = 'block';
    el.innerHTML = `
      <div class="cv-loot-budget-row">
        <span class="cv-loot-budget-amounts">${Math.round(totalGp)} gp / ${Math.round(targetGp)} gp target</span>
        <span class="cv-loot-budget-badge" style="color:${color};border-color:${color}99;background:${color}22;">${esc(budget.band)}</span>
      </div>
      <div class="cv-loot-budget-bar"><div class="cv-loot-budget-fill" style="width:${pct}%;background:${color};"></div></div>
    `;
  }

  function _setLootButtonsEnabled(hasItems) {
    if (!_modalEl) return;
    const rerollBtn = _modalEl.querySelector('#cv-loot-reroll-btn');
    const addBtn    = _modalEl.querySelector('#cv-loot-add-btn');
    if (rerollBtn) rerollBtn.disabled = !hasItems;
    if (addBtn)    addBtn.disabled    = !hasItems;
  }

  /** DM button: generate or reroll loot. When keepLocked, locked rows are resent as `keep`. */
  function _generateLoot(keepLocked) {
    if (!_modalEl || !_propData || _role !== 'dm') return;
    const levelInput = _modalEl.querySelector('#cv-loot-level');
    const themeInput = _modalEl.querySelector('#cv-loot-theme');
    const level = Math.max(1, Math.min(20, parseInt(levelInput && levelInput.value, 10) || 5));
    const theme = themeInput ? String(themeInput.value || '') : '';
    const keep = (keepLocked && _lootGen)
      ? _lootGen.items.filter(it => it._locked).map(it => {
          const copy = Object.assign({}, it);
          delete copy._locked;
          return copy;
        })
      : [];
    if (typeof sendWS === 'function') {
      sendWS({
        type: 'generate_loot',
        payload: { prop_id: _propData.id, dungeon_level: level, theme, keep },
      });
    }
  }

  /** Called by play.html when the WS loot_generated (preview) response arrives. */
  function _onLootGenerated(payload) {
    if (!_modalEl || !_propData || !payload) return;
    if (payload.prop_id && payload.prop_id !== _propData.id) return;
    const lockedNames = new Set(
      (_lootGen ? _lootGen.items.filter(it => it._locked) : []).map(it => String(it.name || '').toLowerCase())
    );
    const items = (Array.isArray(payload.items) ? payload.items : []).map(it => Object.assign({}, it, {
      _locked: lockedNames.has(String(it.name || '').toLowerCase()),
    }));
    _lootGen = { items, budget: payload.budget || null, gold: payload.gold || 0 };
    _renderLootList();
    _renderLootBudget();
    _setLootButtonsEnabled(items.length > 0);
  }

  /** Toggle a generated row's lock state (preview-only; does not persist). */
  function _toggleLootLock(idx) {
    if (!_lootGen || !_lootGen.items[idx]) return;
    _lootGen.items[idx]._locked = !_lootGen.items[idx]._locked;
    _renderLootList();
  }

  /** DM button: commit the full current preview (locked + unlocked) into the chest, unchanged. */
  function _addLootToChest() {
    if (!_lootGen || !_propData || !_lootGen.items.length) return;
    const items = _lootGen.items.map(it => ({ name: it.name, qty: it.qty || 1, rarity: it.rarity, gp: it.gp }));
    const updated = (typeof window._chestAddLootItems === 'function')
      ? window._chestAddLootItems(_propData.id, items)
      : null;
    if (updated) _propData.inventory = updated.inventory;
    const count = items.length;
    _lootGen = null;
    _renderItems();
    _updateSlotCount();
    _renderLootList();
    _renderLootBudget();
    _setLootButtonsEnabled(false);
    showTakeResult(`Added ${count} item${count === 1 ? '' : 's'} to the chest.`, true);
  }

  /* ── Public API ───────────────────────────────────────────────────────── */

  /* ── Mimic ───────────────────────────────────────────────────────────────── */

  /**
   * Show the mimic reveal overlay. Called when a player opens a mimic-enabled
   * chest and the roll triggers the mimic. The DM sees the same overlay.
   * @param {string} propName
   */
  function _showMimicReveal(propName) {
    const el = document.createElement('div');
    el.id = 'dnd-mimic-reveal';
    el.innerHTML = `
      <div class="mr-backdrop"></div>
      <div class="mr-dialog" role="alertdialog" aria-modal="true">
        <div class="mr-glow"></div>
        <div class="mr-icon">🦷</div>
        <h2 class="mr-title">IT'S A MIMIC!</h2>
        <p class="mr-body">
          <strong class="mr-prop-name"></strong> snaps open,
          revealing rows of vicious teeth and a writhing tongue.
          It was never a chest at all!
        </p>
        <p class="mr-note">
          The Mimic lunges — roll for initiative!
        </p>
        <div class="mr-actions">
          <button class="mr-bestiary-btn" onclick="ChestView._openMimicBestiary()">
            📖 View Mimic Stats
          </button>
          <button class="mr-close-btn" onclick="ChestView._closeMimicReveal()">
            ⚔️ Begin Combat
          </button>
        </div>
      </div>`;
    el.querySelector('.mr-prop-name').textContent = propName || 'The chest';
    _injectMimicStyles();
    document.body.appendChild(el);
  }

  function _closeMimicReveal() {
    const el = document.getElementById('dnd-mimic-reveal');
    if (el) el.remove();
  }

  function _openMimicBestiary() {
    if (typeof window._openBestiaryToMimic === 'function') {
      window._openBestiaryToMimic();
    }
  }

  /**
   * Open the chest modal.
   * @param {Object} propData  - editor prop object (kind === 'chest')
   * @param {string} role      - 'dm' | 'player'
   */
  function open(propData, role) {
    close();
    _propData = propData || {};
    _role     = String(role || 'player');
    _lootGen  = null;

    // ── Mimic check (players only) ──────────────────────────────────────────
    // When the DM arms mimic mode, players opening the chest should always
    // get the reveal. The DM can still inspect the chest normally to stage it.
    if (_role !== 'dm' && _propData.mimic_enabled) {
      _propData = null;
      _showMimicReveal(propData.name || 'The chest');
      return;
    }

    const chestName = esc(_propData.name || 'Chest');
    const isDm      = _role === 'dm';
    const used      = Array.isArray(_propData.inventory) ? _propData.inventory.length : 0;
    const total     = Math.max(1, Number(_propData.slot_count) || 12);
    const isHidden  = !!_propData.hidden;

    const modal = document.createElement('div');
    modal.id    = MODAL_ID;
    modal.innerHTML = `
      <div class="cv-backdrop"></div>
      <div class="cv-dialog" role="dialog" aria-modal="true" aria-label="Chest: ${chestName}">

        <!-- Wood header strip -->
        <div class="cv-wood-border">
          <div class="cv-header">
            <div class="cv-header-left">
              <div class="cv-chest-icon">🧰</div>
              <div class="cv-chest-meta">
                <div class="cv-chest-name">${chestName}</div>
                <div class="cv-chest-sub">Treasure Chest${isHidden && isDm ? ' · <em>Hidden from players</em>' : ''}</div>
              </div>
            </div>
            <div class="cv-header-right">
              <div id="cv-slot-count" class="cv-slot-badge">${used} / ${total} slots</div>
              <button class="cv-close" title="Close" aria-label="Close">✕</button>
            </div>
          </div>
          <div class="cv-title-bar">
            <span class="cv-deco">⚔️</span>
            <h2 class="cv-title">CHEST CONTENTS</h2>
            <span class="cv-deco">⚔️</span>
          </div>
        </div>

        <!-- Item list -->
        <div class="cv-list"></div>

        ${isDm ? `
        <!-- DM loot generator -->
        <div class="cv-lootgen">
          <div class="cv-lootgen-head">
            <span class="cv-lootgen-title">🎲 Generate Loot</span>
            <div class="cv-lootgen-controls">
              <label class="cv-loot-level-label">Lvl <span id="cv-loot-level-val">5</span></label>
              <input id="cv-loot-level" type="range" min="1" max="20" value="5"
                     oninput="document.getElementById('cv-loot-level-val').textContent=this.value" />
              <select id="cv-loot-theme" class="cv-loot-theme-select">
                <option value="">Any theme</option>
                <option value="weapon">Weapons</option>
                <option value="armor">Armor</option>
                <option value="potion">Potions</option>
                <option value="scroll">Scrolls</option>
                <option value="wondrous">Wondrous</option>
              </select>
            </div>
          </div>
          <div id="cv-loot-budget" class="cv-loot-budget" style="display:none;"></div>
          <div id="cv-loot-list" class="cv-loot-list"></div>
          <div id="cv-loot-empty" class="cv-loot-empty">No loot generated yet.</div>
          <div class="cv-lootgen-actions">
            <button class="cv-loot-btn" onclick="ChestView._generateLoot(false)">🎲 Generate Loot</button>
            <button class="cv-loot-btn" id="cv-loot-reroll-btn" onclick="ChestView._generateLoot(true)" disabled>🔄 Reroll Unlocked</button>
            <button class="cv-loot-btn cv-loot-add-btn" id="cv-loot-add-btn" onclick="ChestView._addLootToChest()" disabled>➕ Add to Chest</button>
          </div>
        </div>` : ''}

        <!-- Footer -->
        <div class="cv-footer">
          <span class="cv-footer-note" id="cv-footer-note"></span>
          <div class="cv-footer-btns">
            ${isDm ? `<button class="cv-mimic-btn ${_propData.mimic_enabled ? 'cv-mimic-on' : ''}"
                              id="cv-mimic-toggle"
                              onclick="ChestView._toggleMimic()"
                              title="${_propData.mimic_enabled ? 'Mimic Mode ON — players opening this chest trigger the mimic reveal. Click to disable.' : 'Mimic Mode OFF — chest opens normally. Click to enable mimic reveal.'}"
                      >🪤 Mimic: ${_propData.mimic_enabled ? 'ON' : 'OFF'}</button>` : ''}
            ${isDm ? '<button class="cv-manage-btn" onclick="ChestView._openManage()">⚙ Edit Contents</button>' : ''}
            <button class="cv-done">Close Chest</button>
          </div>
        </div>
      </div>`;

    _injectStyles();
    document.body.appendChild(modal);
    _modalEl = modal;

    _renderItems();

    modal.querySelector('.cv-backdrop').addEventListener('click', close);
    modal.querySelector('.cv-close').addEventListener('click', close);
    modal.querySelector('.cv-done').addEventListener('click', close);
  }

  /** Refresh item list + slot count when prop data changes (e.g. after a take). */
  function refresh(propData) {
    if (!_modalEl) return;
    if (propData) _propData = propData;
    _renderItems();
    _updateSlotCount();
    // Clear stale "Taking…" note if items changed
    const noteEl = _modalEl.querySelector('#cv-footer-note');
    if (noteEl && noteEl.textContent === 'Taking item…') noteEl.textContent = '';
  }

  /** Show a result message (success / error) in the footer. */
  function showTakeResult(message, isSuccess) {
    if (!_modalEl) return;
    const el = _modalEl.querySelector('#cv-footer-note');
    if (!el) return;
    el.textContent = message || '';
    el.className   = 'cv-footer-note ' + (isSuccess ? 'cv-note-ok' : 'cv-note-err');
  }

  function isOpen()        { return !!_modalEl; }
  function getOpenPropId() { return _propData ? (_propData.id || null) : null; }

  /** Close and remove the modal. Also clears the play.html tracking ID. */
  function close() {
    if (_modalEl) {
      _modalEl.remove();
      _modalEl = null;
    }
    _propData = null;
    // Tell play.html to clear _openPropInventoryId
    if (typeof window._onChestViewClose === 'function') {
      window._onChestViewClose();
    }
  }

  /* ── Button handlers (called by inline onclick) ───────────────────────── */

  function _take(idx, qty) {
    if (!_propData) return;
    const noteEl = _modalEl && _modalEl.querySelector('#cv-footer-note');
    if (noteEl) { noteEl.textContent = 'Taking item…'; noteEl.className = 'cv-footer-note'; }
    // Use play.html's sendPropInventoryAction if available (handles encumbrance warning)
    if (typeof takePropInventoryItem === 'function') {
      takePropInventoryItem(idx, qty || 1);
    } else if (typeof sendWS === 'function') {
      sendWS({
        type: 'prop_take_item',
        payload: {
          map_context: typeof editorMapContextKey === 'function' ? editorMapContextKey() : 'world',
          prop_id:     _propData.id,
          item_index:  idx,
          qty:         Math.max(1, Number(qty) || 1),
        },
      });
    }
  }

  function _openManage() {
    if (!_propData) return;
    // Remove ChestView overlay but keep _openPropInventoryId alive in play.html
    // so the editing modal can re-use it. We do NOT call close() here — that would
    // clear _openPropInventoryId through the _onChestViewClose hook.
    if (_modalEl) { _modalEl.remove(); _modalEl = null; }
    _propData = null;
    // Ask play.html to open the editing modal (does NOT go through ChestView again)
    if (typeof openPropInventoryEditing === 'function') {
      openPropInventoryEditing();
    }
  }

  /**
   * DM-only: toggle mimic mode on/off for this chest.
   * Persists via the _chestMimicToggle hook defined in play.html.
   */
  function _toggleMimic() {
    if (!_propData || _role !== 'dm') return;
    const newState = !_propData.mimic_enabled;
    _propData.mimic_enabled = newState;
    // Update the button label/state in the open modal
    const btn = _modalEl && _modalEl.querySelector('#cv-mimic-toggle');
    if (btn) {
      btn.textContent = `🪤 Mimic: ${newState ? 'ON' : 'OFF'}`;
      btn.title = newState
        ? 'Mimic Mode ON — players opening this chest trigger the mimic reveal. Click to disable.'
        : 'Mimic Mode OFF — chest opens normally. Click to enable mimic reveal.';
      btn.classList.toggle('cv-mimic-on', newState);
    }
    // Persist the change via play.html hook
    if (typeof window._chestMimicToggle === 'function') {
      window._chestMimicToggle(_propData.id, newState);
    }
  }

  /* ── CSS ──────────────────────────────────────────────────────────────── */
  let _stylesInjected = false;
  function _injectStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    const s = document.createElement('style');
    s.textContent = `
      /* ── Chest View Modal ── */
      #${MODAL_ID} {
        position:fixed;inset:0;z-index:9800;
        display:flex;align-items:center;justify-content:center;
      }
      #${MODAL_ID} .cv-backdrop {
        position:absolute;inset:0;
        background:rgba(0,0,0,0.72);backdrop-filter:blur(3px);
      }
      #${MODAL_ID} .cv-dialog {
        position:relative;z-index:1;
        background:linear-gradient(175deg,#f5e8c8 0%,#e8d5a3 60%,#d4b87a 100%);
        border-radius:14px;
        box-shadow:0 20px 60px rgba(0,0,0,0.85),
                   inset 0 0 0 2px rgba(100,60,10,0.35);
        width:500px;max-width:92vw;max-height:82vh;
        display:flex;flex-direction:column;
        color:#2c1a08;font-family:inherit;
        overflow:hidden;
      }

      /* Wood border strip (same tone as ShopView, slightly darker) */
      #${MODAL_ID} .cv-wood-border {
        background:linear-gradient(180deg,#4a2910 0%,#6b3a1c 50%,#4a2910 100%);
        border-radius:14px 14px 0 0;
        padding:0.6rem 1rem;
        border-bottom:3px solid #2d1507;
        box-shadow:inset 0 -4px 8px rgba(0,0,0,0.35);
        flex-shrink:0;
      }
      #${MODAL_ID} .cv-header {
        display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;
        margin-bottom:0.4rem;
      }
      #${MODAL_ID} .cv-header-left  { display:flex;align-items:center;gap:0.55rem;flex:1;min-width:0; }
      #${MODAL_ID} .cv-header-right { display:flex;align-items:center;gap:0.5rem;flex-shrink:0; }
      #${MODAL_ID} .cv-chest-icon   { font-size:22px;line-height:1; }
      #${MODAL_ID} .cv-chest-meta   { min-width:0; }
      #${MODAL_ID} .cv-chest-name {
        font-size:17px;font-weight:800;color:#f5e8c8;
        letter-spacing:0.02em;text-shadow:1px 1px 3px rgba(0,0,0,0.6);
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
      }
      #${MODAL_ID} .cv-chest-sub {
        font-size:11px;color:#c8a878;letter-spacing:0.05em;margin-top:1px;
      }
      #${MODAL_ID} .cv-chest-sub em { color:#f0c060;font-style:normal; }
      #${MODAL_ID} .cv-slot-badge {
        font-size:11px;color:#f5e8c8;background:rgba(0,0,0,0.3);
        border:1px solid rgba(245,200,90,0.35);border-radius:6px;
        padding:0.22rem 0.55rem;white-space:nowrap;
      }
      #${MODAL_ID} .cv-close {
        background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.15);
        color:#f5e8c8;cursor:pointer;font-size:16px;padding:0 6px;
        border-radius:4px;line-height:1.5;
      }
      #${MODAL_ID} .cv-close:hover { color:#ff8080;background:rgba(180,30,30,0.3); }

      #${MODAL_ID} .cv-title-bar {
        display:flex;align-items:center;justify-content:center;gap:0.55rem;
      }
      #${MODAL_ID} .cv-deco  { font-size:13px;opacity:0.65; }
      #${MODAL_ID} .cv-title {
        margin:0;font-size:14px;font-weight:700;color:#f5e8c8;
        font-family:'Cinzel',serif;letter-spacing:0.14em;text-transform:uppercase;
        text-shadow:1px 1px 4px rgba(0,0,0,0.55);
      }

      /* Item list */
      #${MODAL_ID} .cv-list {
        flex:1;overflow-y:auto;
        padding:0.7rem 0.9rem;
        display:flex;flex-direction:column;gap:0.5rem;
      }
      #${MODAL_ID} .cv-empty {
        text-align:center;color:#8b6b3d;padding:2rem 0;
        font-size:14px;font-style:italic;
      }
      #${MODAL_ID} .cv-item {
        background:rgba(255,255,255,0.45);
        border:1px solid rgba(139,90,20,0.22);
        border-radius:10px;padding:0.6rem 0.8rem;
        box-shadow:0 2px 6px rgba(0,0,0,0.07);
        transition:background 0.15s;
      }
      #${MODAL_ID} .cv-item:hover { background:rgba(255,255,255,0.6); }

      #${MODAL_ID} .cv-item-top {
        display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;
      }
      #${MODAL_ID} .cv-item-name {
        font-weight:700;font-size:14px;flex:1;color:#2c1a08;
      }
      #${MODAL_ID} .cv-qty-badge {
        font-size:12px;font-weight:600;color:#6b3d0a;
        background:rgba(139,90,20,0.12);border:1px solid rgba(139,90,20,0.25);
        border-radius:10px;padding:1px 8px;white-space:nowrap;
      }

      /* Rarity / badge row */
      #${MODAL_ID} .cv-badge-row {
        display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.3rem;
      }
      #${MODAL_ID} .cv-badge {
        font-size:10px;font-weight:600;border:1px solid;
        border-radius:4px;padding:1px 6px;white-space:nowrap;
      }
      #${MODAL_ID} .cv-badge-magic   { color:#d4af37;border-color:#d4af3766;background:rgba(212,175,55,0.1); }
      #${MODAL_ID} .cv-badge-attune  { color:#9b59b6;border-color:#9b59b666;background:rgba(155,89,182,0.1); }
      #${MODAL_ID} .cv-badge-unident { color:#e67e22;border-color:#e67e2266;background:rgba(230,126,34,0.08); }

      #${MODAL_ID} .cv-item-notes {
        font-size:12px;color:#6b4c2a;margin-top:0.3rem;line-height:1.45;font-style:italic;
      }
      #${MODAL_ID} .cv-item-actions {
        display:flex;gap:0.4rem;margin-top:0.45rem;flex-wrap:wrap;
      }
      #${MODAL_ID} .cv-take-btn {
        padding:0.3rem 0.85rem;border-radius:7px;
        font-size:12px;font-weight:600;cursor:pointer;border:none;
        background:#8b4513;color:#fff;
        transition:background 0.12s;
      }
      #${MODAL_ID} .cv-take-btn:hover { background:#a0522d; }
      #${MODAL_ID} .cv-take-all {
        background:rgba(100,60,20,0.14);color:#6b3d0a;
        border:1px solid rgba(100,60,20,0.28)!important;border-style:solid!important;
      }
      #${MODAL_ID} .cv-take-all:hover { background:rgba(100,60,20,0.24); }

      /* Footer */
      #${MODAL_ID} .cv-footer {
        display:flex;align-items:center;justify-content:space-between;
        padding:0.55rem 0.9rem;
        background:linear-gradient(180deg,#6b3a1c 0%,#4a2910 100%);
        border-top:3px solid #2d1507;
        border-radius:0 0 14px 14px;
        flex-shrink:0;gap:0.5rem;
      }
      #${MODAL_ID} .cv-footer-note { font-size:12px;flex:1; }
      #${MODAL_ID} .cv-note-ok  { color:#a5d6a7; }
      #${MODAL_ID} .cv-note-err { color:#ef9a9a; }
      #${MODAL_ID} .cv-footer-btns { display:flex;gap:0.45rem;flex-shrink:0; }

      #${MODAL_ID} .cv-manage-btn {
        padding:0.4rem 0.9rem;
        background:rgba(245,232,200,0.1);border:1px solid rgba(245,232,200,0.28);
        border-radius:7px;color:#f5d27f;cursor:pointer;font-size:12px;font-weight:600;
      }
      #${MODAL_ID} .cv-manage-btn:hover { background:rgba(245,232,200,0.2); }
      #${MODAL_ID} .cv-done {
        padding:0.4rem 1.1rem;
        background:rgba(245,232,200,0.12);border:1px solid rgba(245,232,200,0.3);
        border-radius:7px;color:#f5e8c8;cursor:pointer;font-size:13px;font-weight:600;
      }
      #${MODAL_ID} .cv-done:hover { background:rgba(245,232,200,0.22); }

      /* Mimic toggle button */
      #${MODAL_ID} .cv-mimic-btn {
        padding:0.4rem 0.9rem;
        background:rgba(245,232,200,0.08);border:1px solid rgba(180,100,20,0.35);
        border-radius:7px;color:#c8956a;cursor:pointer;font-size:12px;font-weight:600;
        transition:all 0.15s;
      }
      #${MODAL_ID} .cv-mimic-btn:hover { background:rgba(180,100,20,0.18); }
      #${MODAL_ID} .cv-mimic-btn.cv-mimic-on {
        background:rgba(180,40,40,0.22);border-color:rgba(220,60,60,0.5);
        color:#f08080;box-shadow:0 0 6px rgba(220,60,60,0.25);
      }

      /* DM loot generator panel */
      #${MODAL_ID} .cv-lootgen {
        flex-shrink:0;border-top:2px dashed rgba(139,90,20,0.3);
        padding:0.6rem 0.9rem;display:flex;flex-direction:column;gap:0.45rem;
        background:rgba(139,90,20,0.06);max-height:38vh;overflow-y:auto;
      }
      #${MODAL_ID} .cv-lootgen-head {
        display:flex;align-items:center;justify-content:space-between;gap:0.5rem;flex-wrap:wrap;
      }
      #${MODAL_ID} .cv-lootgen-title { font-weight:700;font-size:13px;color:#5a3a10; }
      #${MODAL_ID} .cv-lootgen-controls { display:flex;align-items:center;gap:0.45rem;flex-wrap:wrap; }
      #${MODAL_ID} .cv-loot-level-label { font-size:11px;color:#6b4c2a;white-space:nowrap; }
      #${MODAL_ID} #cv-loot-level { width:110px;accent-color:#8b4513; }
      #${MODAL_ID} .cv-loot-theme-select {
        font-size:11px;padding:0.25rem 0.4rem;border-radius:6px;
        border:1px solid rgba(139,90,20,0.3);background:rgba(255,255,255,0.5);color:#3a2710;
      }
      #${MODAL_ID} .cv-loot-budget { display:flex;flex-direction:column;gap:0.25rem; }
      #${MODAL_ID} .cv-loot-budget-row {
        display:flex;align-items:center;justify-content:space-between;gap:0.5rem;font-size:11px;color:#5a3a10;
      }
      #${MODAL_ID} .cv-loot-budget-badge {
        font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.03em;
        border:1px solid;border-radius:999px;padding:1px 8px;
      }
      #${MODAL_ID} .cv-loot-budget-bar {
        height:6px;border-radius:4px;background:rgba(139,90,20,0.15);overflow:hidden;
      }
      #${MODAL_ID} .cv-loot-budget-fill { height:100%;transition:width 0.2s; }
      #${MODAL_ID} .cv-loot-list { display:flex;flex-direction:column;gap:0.35rem; }
      #${MODAL_ID} .cv-loot-row {
        background:rgba(255,255,255,0.4);border:1px solid rgba(139,90,20,0.18);border-radius:8px;
      }
      #${MODAL_ID} .item-row-lock-toggle {
        padding:0.25rem 0.6rem;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;
        border:1px solid rgba(139,90,20,0.3);background:rgba(255,255,255,0.5);color:#5a3a10;
      }
      #${MODAL_ID} .cv-loot-empty {
        text-align:center;color:#8b6b3d;font-size:12px;font-style:italic;padding:0.4rem 0;
      }
      #${MODAL_ID} .cv-lootgen-actions { display:flex;gap:0.4rem;flex-wrap:wrap; }
      #${MODAL_ID} .cv-loot-btn {
        flex:1;min-width:110px;padding:0.4rem 0.6rem;border-radius:7px;
        font-size:11px;font-weight:600;cursor:pointer;border:1px solid rgba(139,90,20,0.3);
        background:rgba(139,90,20,0.1);color:#5a3a10;
      }
      #${MODAL_ID} .cv-loot-btn:hover:not(:disabled) { background:rgba(139,90,20,0.2); }
      #${MODAL_ID} .cv-loot-btn:disabled { opacity:0.5;cursor:not-allowed; }
      #${MODAL_ID} .cv-loot-add-btn {
        background:rgba(0,150,130,0.12);border-color:rgba(0,150,130,0.35);color:#0a6b5c;
      }
      #${MODAL_ID} .cv-loot-add-btn:hover:not(:disabled) { background:rgba(0,150,130,0.22); }
    `;
    document.head.appendChild(s);
  }

  /* Mimic reveal overlay styles */
  let _mimicStylesInjected = false;
  function _injectMimicStyles() {
    if (_mimicStylesInjected) return;
    _mimicStylesInjected = true;
    const s = document.createElement('style');
    s.textContent = `
      #dnd-mimic-reveal {
        position:fixed;inset:0;z-index:9900;
        display:flex;align-items:center;justify-content:center;
      }
      #dnd-mimic-reveal .mr-backdrop {
        position:absolute;inset:0;
        background:rgba(0,0,0,0.88);backdrop-filter:blur(4px);
      }
      #dnd-mimic-reveal .mr-dialog {
        position:relative;z-index:1;
        background:linear-gradient(160deg,#1a0a04 0%,#2d0e08 60%,#1a0a04 100%);
        border:2px solid rgba(200,50,20,0.6);
        border-radius:16px;
        box-shadow:0 0 60px rgba(200,50,20,0.5),
                   0 20px 60px rgba(0,0,0,0.9),
                   inset 0 0 40px rgba(200,50,20,0.08);
        width:440px;max-width:92vw;
        padding:2rem 2rem 1.5rem;
        text-align:center;color:#f5e8c8;font-family:inherit;
        animation:mr-slam 0.35s cubic-bezier(0.17,0.67,0.5,1.3) both;
      }
      @keyframes mr-slam {
        0%   { transform:scale(0.6) rotate(-4deg); opacity:0; }
        100% { transform:scale(1)   rotate(0deg);  opacity:1; }
      }
      #dnd-mimic-reveal .mr-glow {
        position:absolute;inset:-2px;border-radius:16px;
        background:transparent;
        box-shadow:0 0 30px 6px rgba(220,60,20,0.4);
        pointer-events:none;
        animation:mr-pulse 1.2s ease-in-out infinite alternate;
      }
      @keyframes mr-pulse {
        from { box-shadow:0 0 20px 4px rgba(220,60,20,0.3); }
        to   { box-shadow:0 0 50px 10px rgba(220,60,20,0.6); }
      }
      #dnd-mimic-reveal .mr-icon {
        font-size:52px;line-height:1;margin-bottom:0.5rem;
        animation:mr-shake 0.5s ease-in-out 0.3s both;
      }
      @keyframes mr-shake {
        0%,100% { transform:rotate(0); }
        20%     { transform:rotate(-10deg); }
        40%     { transform:rotate(10deg); }
        60%     { transform:rotate(-8deg); }
        80%     { transform:rotate(8deg); }
      }
      #dnd-mimic-reveal .mr-title {
        margin:0 0 0.75rem;
        font-size:28px;font-weight:900;
        font-family:'Cinzel',serif;letter-spacing:0.08em;
        color:#ff4422;text-shadow:0 0 20px rgba(255,60,20,0.8);
        text-transform:uppercase;
      }
      #dnd-mimic-reveal .mr-body {
        font-size:15px;line-height:1.6;color:#e8cfa8;margin:0 0 0.6rem;
      }
      #dnd-mimic-reveal .mr-note {
        font-size:13px;color:#c08060;font-style:italic;margin:0 0 1.2rem;
      }
      #dnd-mimic-reveal .mr-actions {
        display:flex;gap:0.7rem;justify-content:center;flex-wrap:wrap;
      }
      #dnd-mimic-reveal .mr-bestiary-btn {
        padding:0.55rem 1.2rem;border-radius:8px;
        background:rgba(50,80,200,0.2);border:1px solid rgba(100,140,255,0.4);
        color:#a0b4ff;cursor:pointer;font-size:13px;font-weight:600;
      }
      #dnd-mimic-reveal .mr-bestiary-btn:hover { background:rgba(50,80,200,0.35); }
      #dnd-mimic-reveal .mr-close-btn {
        padding:0.55rem 1.4rem;border-radius:8px;
        background:rgba(200,40,20,0.25);border:1px solid rgba(220,60,20,0.5);
        color:#ff8060;cursor:pointer;font-size:13px;font-weight:700;
      }
      #dnd-mimic-reveal .mr-close-btn:hover { background:rgba(200,40,20,0.4); }
    `;
    document.head.appendChild(s);
  }

  window.ChestView = Object.freeze({
    open, close, refresh, isOpen, getOpenPropId, showTakeResult,
    _take, _openManage, _toggleMimic, _closeMimicReveal, _openMimicBestiary,
    _generateLoot, _onLootGenerated, _toggleLootLock, _addLootToChest,
  });
})();
