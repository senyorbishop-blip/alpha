(function(){
  function renderSpellRulesReviewModal(env, state) {
    const host = env.document.getElementById('spell-rules-review-list');
    if (!host) return;
    const reviewItems = Array.isArray(state.reviewQueue) ? state.reviewQueue : [];
    const customItems = Array.isArray(state.customSpells) ? state.customSpells : [];
    const reviewHtml = reviewItems.length ? reviewItems.map((item) => `
      <div class="rules-review-item">
        <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
          <div>
            <div class="rules-spell-title" style="font-size:0.76rem;">${env.escapeHtml(item.name || item.original_name || 'Unknown')}</div>
            <div class="rules-note-line">${env.escapeHtml(String(item.status || 'review required').replace(/_/g, ' '))} • score ${env.escapeHtml(String(item.match_score || 0))}${item.suggested_name ? ` • suggested ${env.escapeHtml(item.suggested_name)}` : ''}</div>
          </div>
          <button class="mini-btn" type="button" onclick="prefillCustomSpellRule(decodeURIComponent('${encodeURIComponent(String(item.name || item.original_name || ''))}'))">Create Custom</button>
        </div>
      </div>`).join('') : '<div class="sheet-note">No unmatched spells are waiting for review right now.</div>';
    const customHtml = customItems.length ? customItems.map((item) => `
      <div class="rules-review-item">
        <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;">
          <div>
            <div class="rules-spell-title" style="font-size:0.76rem;">${env.escapeHtml(item.name || 'Custom Spell')}</div>
            <div class="rules-note-line">Level ${env.escapeHtml(String(item.spell_level ?? 0))} • ${env.escapeHtml(item.school || 'Spell')} • ${env.escapeHtml(item.scaling_type || 'none')}</div>
          </div>
          <button class="mini-btn" type="button" onclick="loadCustomSpellIntoForm('${item.id}')">Edit</button>
        </div>
      </div>`).join('') : '<div class="sheet-note">No DM custom spells saved yet.</div>';
    host.innerHTML = `
      <div class="sheet-note" style="margin-bottom:0.2rem;">Review Queue</div>
      ${reviewHtml}
      <div class="sheet-note" style="margin-top:0.6rem;">Custom Spell Catalog</div>
      ${customHtml}`;
  }
  window.AppUISpellRules = { renderSpellRulesReviewModal };
})();
