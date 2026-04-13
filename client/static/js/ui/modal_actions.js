(function(){
  function submitInventoryGoldChange(env, stateCtl) {
    const mode = stateCtl.getMode() === 'remove' ? 'remove' : 'add';
    const amount = String(env.document.getElementById('inventory-gold-amount')?.value || '').trim();
    if (!amount) {
      env.showToast(mode === 'remove' ? 'Add a gold amount to remove first' : 'Add a gold amount first');
      return;
    }
    const source = String(env.document.getElementById('inventory-gold-source')?.value || '').trim().slice(0, 60) || (mode === 'remove' ? (env.getRole() === 'dm' ? 'DM Adjustment' : 'Manual Spend') : (env.getRole() === 'dm' ? 'DM Award' : 'Manual Add'));
    const targetUserId = env.getRole() === 'dm' ? String(env.document.getElementById('inventory-gold-target')?.value || '').trim() : '';
    const type = mode === 'remove' ? 'inventory_remove_gold' : 'inventory_add_gold';
    env.sendWS({ type, payload: { amount, source_name: source, target_user_id: targetUserId } });
    env.closeInventoryGoldModal();
  }

  function submitInventoryManualAdd(env) {
    const name = String(env.document.getElementById('inventory-manual-name')?.value || '').trim().slice(0, 80);
    if (!name) {
      env.showToast('Add an item name first');
      return;
    }
    const qty = Math.max(1, Math.min(9999, parseInt(env.document.getElementById('inventory-manual-qty')?.value || '', 10) || 1));
    const price = String(env.document.getElementById('inventory-manual-price')?.value || '').trim().slice(0, 32);
    const source = String(env.document.getElementById('inventory-manual-source')?.value || 'Manual Add').trim().slice(0, 60) || 'Manual Add';
    const notes = String(env.document.getElementById('inventory-manual-notes')?.value || '').trim().slice(0, 160);
    env.sendWS({ type: 'inventory_add_item', payload: { entry: { name, qty, price, notes }, source_name: source } });
    env.closeInventoryManualAddModal();
  }

  async function saveCustomSpellRule(env) {
    if (env.getRole() !== 'dm') return;
    let spell;
    try { spell = env.collectCustomSpellRuleForm(); }
    catch (err) { env.showToast(err.message); return; }
    if (!spell.name) { env.showToast('Custom spell needs a name'); return; }
    try {
      const r = await env.fetch('/api/rules/custom-spells', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: env.getSessionId(), user_id: env.getUserId(), spell })
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || 'Could not save custom spell');
      env.showToast(`Saved custom spell: ${d.spell?.name || spell.name}`);
      await env.openSpellRulesReviewModal();
      await env.refreshRulesSpellbook(false);
      if (d.spell?.id) env.loadCustomSpellIntoForm(d.spell.id);
    } catch (err) {
      console.error(err);
      env.showToast(err.message || 'Could not save custom spell');
    }
  }

  async function deleteCustomSpellRule(env) {
    if (env.getRole() !== 'dm') return;
    const spellId = String(env.document.getElementById('rules-custom-id')?.value || '').trim();
    if (!spellId) { env.showToast('Load a custom spell first'); return; }
    if (!env.confirm('Delete this custom spell?')) return;
    try {
      const r = await env.fetch(`/api/rules/custom-spells/${encodeURIComponent(spellId)}?session_id=${encodeURIComponent(env.getSessionId())}&user_id=${encodeURIComponent(env.getUserId())}`, { method: 'DELETE' });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || 'Could not delete custom spell');
      env.resetCustomSpellRuleForm();
      env.showToast('Custom spell deleted');
      await env.openSpellRulesReviewModal();
      await env.refreshRulesSpellbook(false);
    } catch (err) {
      console.error(err);
      env.showToast(err.message || 'Could not delete custom spell');
    }
  }

  window.AppUIModalActions = {
    submitInventoryGoldChange,
    submitInventoryManualAdd,
    saveCustomSpellRule,
    deleteCustomSpellRule,
  };
})();
