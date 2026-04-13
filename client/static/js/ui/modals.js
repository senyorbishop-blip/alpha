(function () {
  function setDisplay(el, value) { if (el && el.style) el.style.display = value; return el; }
  function closeSpellRulesReviewModal(env) {
    env.document.getElementById('spell-rules-modal')?.classList.remove('open');
  }

  async function openSpellRulesReviewModal(env, prefillName = '') {
    if (env.getRole() !== 'dm') return;
    env.document.getElementById('spell-rules-modal')?.classList.add('open');
    try {
      const r = await env.fetch(`/api/rules/review-queue?session_id=${encodeURIComponent(env.getSessionId())}&user_id=${encodeURIComponent(env.getUserId())}`);
      const d = await r.json();
      if (r.ok && d.ok) {
        env.setRulesReviewQueue(Array.isArray(d.entries) ? d.entries.map(row => row.imported_payload || row) : env.getRulesReviewQueue());
        env.setRulesCustomSpells(Array.isArray(d.custom_spells) ? d.custom_spells : env.getRulesCustomSpells());
      }
    } catch (err) {
      console.warn('review queue fetch failed', err);
    }
    env.renderSpellRulesReviewModal();
    if (prefillName) env.prefillCustomSpellRule(prefillName);
  }

  function openItemLibraryModal(env, mode) {
    env.setItemLibraryModalMode(mode || 'manage');
    const document = env.document;
    const modal = document.getElementById('item-library-modal');
    if (!modal) return;
    const manage = document.getElementById('itemlib-manage-section');
    const pick = document.getElementById('itemlib-pick-section');
    const title = document.getElementById('itemlib-modal-title');
    const subtitle = document.getElementById('itemlib-modal-subtitle');
    const manageMode = env.getItemLibraryModalMode() === 'manage';
    if (manage) setDisplay(manage, manageMode ? 'flex' : 'none');
    if (pick) setDisplay(pick, manageMode ? 'none' : 'flex');
    if (title) title.textContent = manageMode ? 'Item Library' : (env.getItemLibraryModalMode() === 'prop' ? 'Add Library Item To Container' : 'Add Library Item To Inventory');
    if (subtitle) subtitle.textContent = manageMode
      ? 'Save reusable loot and shop entries, then pull them into chests, stores, or inventories.'
      : (env.getItemLibraryModalMode() === 'prop'
        ? 'Pick a saved item and add it into the currently open chest, merchant, or store.'
        : 'Pick a saved item and add it into your own inventory.');
    if (manageMode) {
      const pasteEl = document.getElementById('itemlib-paste');
      if (pasteEl) pasteEl.value = '';
    } else {
      const qtyEl = document.getElementById('itemlib-pick-qty');
      const priceEl = document.getElementById('itemlib-pick-price');
      const notesEl = document.getElementById('itemlib-pick-notes');
      if (qtyEl) qtyEl.value = '';
      if (priceEl) priceEl.value = '';
      if (notesEl) notesEl.value = '';
    }
    setDisplay(modal, 'flex');
    env.renderItemLibraryList();
    env.renderItemLibraryEditor();
    env.refreshItemLibraryPickerSummary();
  }

  function closeItemLibraryModal(env) {
    const modal = env.document.getElementById('item-library-modal');
    if (modal) setDisplay(modal, 'none');
    env.setItemLibraryModalMode(null);
  }

  function openInventoryManualAddModal(env) {
    if (env.getRole() === 'viewer') return;
    const document = env.document;
    const modal = document.getElementById('inventory-item-modal');
    if (!modal) return;
    const pasteEl = document.getElementById('inventory-manual-paste');
    if (pasteEl) pasteEl.value = '';
    const defaults = {
      'inventory-manual-name': '',
      'inventory-manual-qty': '1',
      'inventory-manual-price': '',
      'inventory-manual-source': 'Manual Add',
      'inventory-manual-notes': '',
    };
    Object.entries(defaults).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el) el.value = value;
    });
    setDisplay(modal, 'flex');
  }

  function closeInventoryManualAddModal(env) {
    const modal = env.document.getElementById('inventory-item-modal');
    if (modal) setDisplay(modal, 'none');
  }

  function openInventoryGoldModal(env, mode = 'add', stateCtl) {
    if (env.getRole() === 'viewer') return;
    stateCtl.setMode(mode === 'remove' ? 'remove' : 'add');
    env.refreshInventoryGoldTargets();
    const document = env.document;
    const modal = document.getElementById('inventory-gold-modal');
    if (!modal) return;
    const title = document.getElementById('inventory-gold-title');
    const submit = document.getElementById('inventory-gold-submit');
    const amt = document.getElementById('inventory-gold-amount');
    const src = document.getElementById('inventory-gold-source');
    const currentMode = stateCtl.getMode();
    if (title) title.textContent = currentMode === 'remove' ? 'Remove Gold' : 'Add Gold';
    if (submit) submit.textContent = currentMode === 'remove' ? 'Remove Gold' : 'Add Gold';
    if (amt) amt.value = '';
    if (src) src.value = currentMode === 'remove'
      ? (env.getRole() === 'dm' ? 'DM Adjustment' : 'Manual Spend')
      : (env.getRole() === 'dm' ? 'DM Award' : 'Manual Add');
    setDisplay(modal, 'flex');
  }

  function closeInventoryGoldModal(env) {
    const modal = env.document.getElementById('inventory-gold-modal');
    if (modal) setDisplay(modal, 'none');
  }

  window.AppUIModals = {
    closeSpellRulesReviewModal,
    openSpellRulesReviewModal,
    openItemLibraryModal,
    closeItemLibraryModal,
    openInventoryManualAddModal,
    closeInventoryManualAddModal,
    openInventoryGoldModal,
    closeInventoryGoldModal,
  };
})();
