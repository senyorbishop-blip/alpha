(function(){
  function refreshItemLibraryPickerSummary(env) {
    const summary = env.document.getElementById('itemlib-selected-summary');
    if (!summary) return;
    const entries = env.getEntries() || {};
    const selectedId = env.getSelectedId();
    const entry = selectedId ? entries[selectedId] : null;
    if (!entry) {
      summary.textContent = 'Select an item on the left.';
      return;
    }
    const qtyInput = env.document.getElementById('itemlib-pick-qty');
    const priceInput = env.document.getElementById('itemlib-pick-price');
    if (qtyInput && (!qtyInput.value || Number(qtyInput.value) < 1)) qtyInput.value = String(entry.default_qty || 1);
    if (priceInput && !priceInput.value) priceInput.value = String(entry.price || '');
    summary.innerHTML = `<div style="display:flex;justify-content:space-between;gap:0.45rem;align-items:center;"><strong style="color:var(--gold);">${env.escapeHtml(entry.name)}</strong><span style="font-size:0.62rem;color:var(--gold-dim);text-transform:uppercase;">${env.escapeHtml(entry.rarity || 'Common')}</span></div><div style="font-size:0.64rem;color:var(--parchment-dim);margin-top:0.15rem;">${env.escapeHtml(entry.category || 'Gear')}${entry.price ? ` • ${env.escapeHtml(entry.price)}` : ''}</div>${entry.notes ? `<div style="font-size:0.64rem;color:var(--parchment-dim);margin-top:0.2rem;line-height:1.45;">${env.escapeHtml(entry.notes)}</div>` : ''}`;
  }

  function addLibraryItemToOpenProp(env, entry, opts={}) {
    if (env.getRole() !== 'dm') return;
    const item = env.getOpenPropInventoryItem();
    if (!item || !env.editorPropSupportsContents(item)) return;
    const total = Math.max(1, Number(item.slot_count) || env.defaultEditorPropSlots(item.kind) || 1);
    if (!Array.isArray(item.inventory)) item.inventory = [];
    if (item.inventory.length >= total) {
      env.showToast('No free slots left in this container.');
      return;
    }
    const normalized = env.normalizeEditorPropInventoryEntry(env.buildInventoryEntryFromLibrary(entry, opts), item.kind);
    if (!normalized) return;
    item.inventory.push(normalized);
    env.queueOpenPropInventorySave(120);
    if (env.getOpenPropPopupId() === item.id) env.refreshEditorPropPopup(item);
    env.refreshPropInventoryModal();
    env.showToast(`Added ${entry.name} from item library`);
  }

  function confirmItemLibraryPick(env) {
    const entries = env.getEntries() || {};
    const selectedId = env.getSelectedId();
    const entry = selectedId ? entries[selectedId] : null;
    if (!entry) {
      env.showToast('Choose an item library entry first');
      return;
    }
    const qty = Math.max(1, Math.min(999, parseInt(env.document.getElementById('itemlib-pick-qty')?.value || '', 10) || entry.default_qty || 1));
    const price = String(env.document.getElementById('itemlib-pick-price')?.value || entry.price || '').trim().slice(0, 32);
    const notes = String(env.document.getElementById('itemlib-pick-notes')?.value || entry.notes || '').trim().slice(0, 160);
    if (env.getModalMode() === 'prop') {
      addLibraryItemToOpenProp(env, entry, { qty, price, notes });
      env.closeItemLibraryModal();
      return;
    }
    env.sendWS({ type: 'inventory_add_item', payload: { entry: { name: entry.name, qty, price, notes }, source_name: 'Item Library' } });
    env.closeItemLibraryModal();
  }

  window.AppUIItemLibraryPicker = { refreshItemLibraryPickerSummary, addLibraryItemToOpenProp, confirmItemLibraryPick };
})();
