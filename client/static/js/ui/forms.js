(function(){
  function sortedConnectedPlayers(users, filterFn) {
    return Object.values(users || {})
      .filter(u => u && u.connected && (!filterFn || filterFn(u)))
      .sort((a, b) => `${a.role || ''} ${a.name || ''}`.localeCompare(`${b.role || ''} ${b.name || ''}`));
  }

  function openItemLibraryManager(env) {
    if (env.getRole() !== 'dm') return;
    env.openItemLibraryModal('manage');
  }

  function openItemLibraryPicker(env, mode) {
    if (env.getRole() === 'viewer') return;
    if (mode === 'prop' && env.getRole() !== 'dm') return;
    env.openItemLibraryModal(mode === 'prop' ? 'prop' : 'inventory');
  }

  function refreshInventoryGoldTargets(env, stateCtl) {
    const document = env.document;
    const select = document.getElementById('inventory-gold-target');
    const wrap = document.getElementById('inventory-gold-target-wrap');
    const subtitle = document.getElementById('inventory-gold-subtitle');
    if (!select || !wrap) return;
    const modeWord = stateCtl.getMode() === 'remove' ? 'remove' : 'add';
    if (env.getRole() !== 'dm') {
      wrap.style.display = 'none';
      select.innerHTML = '';
      if (subtitle) subtitle.textContent = modeWord === 'remove' ? 'Remove gold from your purse.' : 'Add gold to your purse.';
      return;
    }
    const opts = sortedConnectedPlayers(env.getUsers(), (u) => u.role !== 'viewer');
    const prev = select.value || '';
    wrap.style.display = opts.length ? 'block' : 'none';
    select.innerHTML = opts.map(u => `<option value="${env.escapeHtml(u.id)}">${env.escapeHtml(u.name)}${u.role === 'dm' ? ' (DM)' : ''}</option>`).join('');
    if (opts.some(u => u.id === prev)) {
      select.value = prev;
    } else {
      select.value = opts.some(u => u.id === env.getUserId()) ? env.getUserId() : (opts[0]?.id || '');
    }
    if (subtitle) subtitle.textContent = modeWord === 'remove'
      ? 'Remove gold from any connected player purse, including your own.'
      : 'Add gold to any connected player purse, including your own.';
  }

  function refreshInventoryTransferTargets(env) {
    const document = env.document;
    const select = document.getElementById('inventory-transfer-target');
    const row = document.getElementById('inventory-transfer-row');
    if (!select || !row) return;
    if (env.getRole() === 'viewer') {
      row.style.display = 'none';
      return;
    }
    const opts = sortedConnectedPlayers(env.getUsers(), (u) => u.id !== env.getUserId() && u.role !== 'viewer');
    row.style.display = opts.length ? 'grid' : 'none';
    const prev = env.getInventoryTransferTargetIdState() || select.value || '';
    select.innerHTML = '<option value="">Choose player…</option>' + opts.map(u => `<option value="${env.escapeHtml(u.id)}">${env.escapeHtml(u.name)}${u.role === 'dm' ? ' (DM)' : ''}</option>`).join('');
    const next = opts.some(u => u.id === prev) ? prev : '';
    select.value = next;
    env.setInventoryTransferTargetIdState(next);
  }

  function getInventoryTransferTargetId(env) {
    const row = env.document.getElementById('inventory-transfer-row');
    const select = env.document.getElementById('inventory-transfer-target');
    const value = row && row.style.display !== 'none' ? String(select?.value || '').trim() : '';
    env.setInventoryTransferTargetIdState(value);
    return value;
  }

  window.AppUIForms = {
    openItemLibraryManager,
    openItemLibraryPicker,
    refreshInventoryGoldTargets,
    refreshInventoryTransferTargets,
    getInventoryTransferTargetId,
  };
})();
