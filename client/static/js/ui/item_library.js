(function(){
  function renderItemLibraryList(env) {
    const wrap = env.document.getElementById('itemlib-list');
    if (!wrap) return;
    const q = String(env.document.getElementById('itemlib-search')?.value || '').trim().toLowerCase();
    const selectedId = env.getSelectedId();
    const entries = Object.values(env.getEntries() || {})
      .filter((entry) => !q || `${entry.name || ''} ${entry.category || ''} ${entry.rarity || ''} ${entry.notes || ''}`.toLowerCase().includes(q))
      .sort((a, b) => `${a.category || ''} ${a.name || ''}`.localeCompare(`${b.category || ''} ${b.name || ''}`));
    if (!entries.length) {
      wrap.innerHTML = '<div style="padding:0.65rem;border:1px dashed rgba(212,175,55,0.18);border-radius:8px;font-size:0.68rem;color:var(--parchment-dim);line-height:1.45;">No item library entries yet. Save a reusable item here, then pull it into chests, merchants, stores, or inventory.</div>';
      return;
    }
    wrap.innerHTML = entries.map((entry) => {
      const active = entry.id === selectedId;
      return `<button type="button" onclick="selectItemLibraryEntry('${entry.id}')" style="text-align:left;padding:0.5rem 0.55rem;border:1px solid ${active ? 'rgba(212,175,55,0.45)' : 'var(--border)'};background:${active ? 'rgba(212,175,55,0.12)' : 'rgba(0,0,0,0.18)'};border-radius:8px;color:var(--parchment);cursor:pointer;display:flex;flex-direction:column;gap:0.2rem;">
      <div style="display:flex;justify-content:space-between;gap:0.45rem;align-items:center;">
        <div style="font-size:0.72rem;font-weight:700;line-height:1.3;">${env.escapeHtml(entry.name || 'Unnamed Item')}</div>
        <span style="font-size:0.55rem;color:var(--gold-dim);text-transform:uppercase;">${env.escapeHtml(entry.rarity || 'Common')}</span>
      </div>
      <div style="display:flex;gap:0.4rem;flex-wrap:wrap;font-size:0.58rem;color:var(--parchment-dim);">
        <span>${env.escapeHtml(entry.category || 'Gear')}</span>
        <span>Qty ${entry.default_qty || 1}</span>
        ${entry.price ? `<span>${env.escapeHtml(entry.price)}</span>` : ''}
      </div>
      ${entry.notes ? `<div style="font-size:0.6rem;color:var(--parchment-dim);line-height:1.4;">${env.escapeHtml(entry.notes)}</div>` : ''}
    </button>`;
    }).join('');
    env.refreshItemLibraryPickerSummary();
  }
  function renderItemLibraryEditor(env) {
    const entry = env.getSelectedId() ? (env.getEntries() || {})[env.getSelectedId()] : null;
    const vals = entry || { name:'', category:'Gear', rarity:'Common', default_qty:1, price:'', notes:'' };
    const set = (id, val='') => { const el = env.document.getElementById(id); if (el) el.value = val ?? ''; };
    set('itemlib-name', vals.name);
    set('itemlib-category', vals.category);
    set('itemlib-rarity', vals.rarity);
    set('itemlib-default-qty', vals.default_qty || 1);
    set('itemlib-price', vals.price || '');
    set('itemlib-notes', vals.notes || '');
    env.refreshItemLibraryPickerSummary();
  }
  function selectItemLibraryEntry(env, id) {
    env.setSelectedId(id);
    renderItemLibraryList(env);
    renderItemLibraryEditor(env);
  }
  function newItemLibraryEntry(env) {
    env.setSelectedId(null);
    renderItemLibraryList(env);
    renderItemLibraryEditor(env);
  }
  window.AppUIItemLibrary = { renderItemLibraryList, renderItemLibraryEditor, selectItemLibraryEntry, newItemLibraryEntry };
})();
