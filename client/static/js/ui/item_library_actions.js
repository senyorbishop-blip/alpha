(function(){
  function getItemLibraryDraft(env) {
    const doc = env.document;
    return {
      id: env.getSelectedId() || `itemlib_${Date.now()}`,
      name: (doc.getElementById('itemlib-name')?.value || '').trim() || 'Unnamed Item',
      category: (doc.getElementById('itemlib-category')?.value || '').trim() || 'Gear',
      rarity: (doc.getElementById('itemlib-rarity')?.value || '').trim() || 'Common',
      default_qty: Math.max(1, Math.min(999, parseInt(doc.getElementById('itemlib-default-qty')?.value || '', 10) || 1)),
      price: (doc.getElementById('itemlib-price')?.value || '').trim().slice(0, 32),
      notes: (doc.getElementById('itemlib-notes')?.value || '').trim().slice(0, 240),
      updated_at: Date.now(),
    };
  }
  function saveItemLibraryEntry(env) {
    if (env.getRole() !== 'dm') return;
    const entry = getItemLibraryDraft(env);
    env.sendWS({ type: 'item_library_upsert', payload: entry });
    env.setSelectedId(entry.id);
    env.showToast(`Saved ${entry.name} to item library`);
  }
  function deleteItemLibraryEntry(env) {
    const selectedId = env.getSelectedId();
    const entries = env.getEntries() || {};
    if (env.getRole() !== 'dm' || !selectedId || !entries[selectedId]) return;
    env.sendWS({ type: 'item_library_delete', payload: { id: selectedId } });
    env.setSelectedId(null);
    env.showToast('Item library entry deleted');
  }
  window.AppUIItemLibraryActions = { getItemLibraryDraft, saveItemLibraryEntry, deleteItemLibraryEntry };
})();
