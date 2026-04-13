/*
 * client/static/js/character/spells_modal.js
 * Spell Detail Modal — Shows complete spell information on click.
 *
 * Exposes: window.SpellModal
 *   .openSpellModal(spellData)
 *   .closeSpellModal()
 */

(function initSpellModal(global) {
  'use strict';

  /* ── Helpers ──────────────────────────────────────────────────────────── */
  function _esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])
    );
  }

  /* Build a plain-text description into safe HTML paragraphs. */
  function _descToHtml(text) {
    if (!text) return '';
    return String(text)
      .split(/\n{2,}/)
      .map(p => `<p>${_esc(p.trim()).replace(/\n/g, '<br>')}</p>`)
      .join('');
  }

  /* Map school slug → display name. */
  const SCHOOL_NAMES = {
    abjuration:    'Abjuration',
    conjuration:   'Conjuration',
    divination:    'Divination',
    enchantment:   'Enchantment',
    evocation:     'Evocation',
    illusion:      'Illusion',
    necromancy:    'Necromancy',
    transmutation: 'Transmutation',
  };

  /* Map level number → ordinal label. */
  function _levelLabel(level) {
    const n = parseInt(level, 10);
    if (!n || n === 0) return 'Cantrip';
    const suffix = n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th';
    return `${n}${suffix}-Level`;
  }

  /* ── DOM helpers ──────────────────────────────────────────────────────── */
  let _overlay = null;
  let _closeTimeout = null;

  function _ensureOverlay() {
    if (_overlay && document.body.contains(_overlay)) return _overlay;
    _overlay = document.createElement('div');
    _overlay.className = 'cs-spell-modal';
    _overlay.setAttribute('role', 'dialog');
    _overlay.setAttribute('aria-modal', 'true');
    document.body.appendChild(_overlay);
    return _overlay;
  }

  /* ── Build modal HTML ─────────────────────────────────────────────────── */
  function _buildModalHtml(spell) {
    const school = SCHOOL_NAMES[String(spell.school || '').toLowerCase()] || _esc(spell.school || 'Unknown');
    const levelLabel = _levelLabel(spell.level);
    const isConc  = Boolean(spell.concentration);
    const isRitual = Boolean(spell.ritual);

    /* Components — stored as a plain string "V, S, M (material)" or as object */
    let compText = '—';
    if (spell.components) {
      if (typeof spell.components === 'string') {
        compText = _esc(spell.components);
      } else if (typeof spell.components === 'object') {
        /* Legacy object form */
        const compParts = [];
        if (spell.components.verbal)   compParts.push('V');
        if (spell.components.somatic)  compParts.push('S');
        if (spell.components.material) {
          const mat = spell.components.material_text || spell.components.material;
          compParts.push(typeof mat === 'string' && mat !== 'true' ? `M (${_esc(mat)})` : 'M');
        }
        compText = compParts.length ? compParts.join(', ') : '—';
      }
    }

    const badges = [
      isConc   ? `<span class="cs-modal-badge concentration">Concentration</span>` : '',
      isRitual ? `<span class="cs-modal-badge ritual">Ritual</span>` : '',
    ].filter(Boolean).join('');

    const tags = Array.isArray(spell.tags) && spell.tags.length
      ? `<div class="cs-modal-section-title">Tags</div>
         <div class="cs-modal-tags">${spell.tags.map(t => `<span class="cs-modal-tag">${_esc(t)}</span>`).join('')}</div>`
      : '';

    const classes = Array.isArray(spell.classes) && spell.classes.length
      ? `<div class="cs-modal-section-title">Classes</div>
         <div class="cs-modal-classes">${spell.classes.map(_esc).join(', ')}</div>`
      : '';

    const higherLevel = spell.scalingNote || spell.higher_levels || spell.atHigherLevels || spell.higherLevel
      ? `<div class="cs-modal-section-title">Scaling & Slot Use</div>
         <div class="cs-modal-higher">${_esc(spell.scalingNote || spell.higher_levels || spell.atHigherLevels || spell.higherLevel)}</div>`
      : '';

    const quickEffect = (spell.effect || spell.playerFacingEffectSummary)
      ? `<div class="cs-modal-section-title">Quick Summary</div><div class="cs-modal-higher">${_esc(spell.effect || spell.playerFacingEffectSummary)}</div>`
      : '';

    const combat = `<div class="cs-modal-section-title">Combat Summary</div>
      <div class="cs-modal-meta-grid">
        <div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Attack / Save</span><span class="cs-modal-meta-value">${_esc(spell.attackType || spell.savingThrow || spell.saveDC || '—')}</span></div>
        <div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Damage / Healing</span><span class="cs-modal-meta-value">${_esc(spell.damageFormula || spell.healingFormula || '—')}</span></div>
        <div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Damage Type</span><span class="cs-modal-meta-value">${_esc(spell.damageType || '—')}</span></div>
        <div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Effect</span><span class="cs-modal-meta-value">${_esc(spell.effect || spell.playerFacingEffectSummary || '—')}</span></div>
      </div>`;

    return `
      <div class="cs-spell-modal-inner">
        <button class="cs-modal-close" aria-label="Close spell details" data-csp-close>&#x2715;</button>

        <div class="cs-modal-title">${_esc(spell.displayName || spell.name || 'Unknown Spell')}</div>
        <div>
          <span class="cs-modal-school">${_esc(levelLabel)} · ${_esc(school)}</span>
        </div>

        ${badges ? `<div class="cs-modal-badges">${badges}</div>` : ''}

        <div class="cs-modal-meta-grid">
          <div class="cs-modal-meta-item">
            <span class="cs-modal-meta-label">Casting Time</span>
            <span class="cs-modal-meta-value">${_esc(spell.castingTime || spell.casting_time || '—')}</span>
          </div>
          <div class="cs-modal-meta-item">
            <span class="cs-modal-meta-label">Range</span>
            <span class="cs-modal-meta-value">${_esc(spell.range || '—')}</span>
          </div>
          <div class="cs-modal-meta-item">
            <span class="cs-modal-meta-label">Components</span>
            <span class="cs-modal-meta-value">${compText}</span>
          </div>
          <div class="cs-modal-meta-item">
            <span class="cs-modal-meta-label">Duration</span>
            <span class="cs-modal-meta-value">${_esc(spell.duration || '—')}</span>
          </div>
          <div class="cs-modal-meta-item">
            <span class="cs-modal-meta-label">Area / Target</span>
            <span class="cs-modal-meta-value">${_esc(spell.areaText || spell.target || '—')}</span>
          </div>
        </div>

        ${quickEffect}
        <div class="cs-modal-desc">${_descToHtml(spell.fullPlayerDetailText || spell.description || spell.desc || '')}</div>

        ${combat}
        ${higherLevel}
        ${tags}
        ${classes}
      </div>
    `;
  }

  /* ── Close animation ──────────────────────────────────────────────────── */
  function _animateClose(cb) {
    if (!_overlay) { if (cb) cb(); return; }
    _overlay.classList.add('closing');
    clearTimeout(_closeTimeout);
    _closeTimeout = setTimeout(() => {
      if (_overlay && _overlay.parentNode) {
        _overlay.parentNode.removeChild(_overlay);
      }
      _overlay = null;
      document.removeEventListener('keydown', _onKeyDown);
      if (cb) cb();
    }, 220);
  }

  /* ── Key handler ──────────────────────────────────────────────────────── */
  function _onKeyDown(e) {
    if (e.key === 'Escape') closeSpellModal();
  }

  /* ── Public API ───────────────────────────────────────────────────────── */
  function openSpellModal(spellData) {
    if (!spellData || typeof spellData !== 'object') return;

    clearTimeout(_closeTimeout);

    const overlay = _ensureOverlay();
    overlay.classList.remove('closing');
    overlay.innerHTML = _buildModalHtml(spellData);

    /* Close on overlay background click */
    overlay.addEventListener('click', function _overlayClick(e) {
      if (e.target === overlay) {
        closeSpellModal();
        overlay.removeEventListener('click', _overlayClick);
      }
    });

    /* Close button */
    const closeBtn = overlay.querySelector('[data-csp-close]');
    if (closeBtn) closeBtn.addEventListener('click', closeSpellModal);

    document.addEventListener('keydown', _onKeyDown);
  }

  function closeSpellModal() {
    _animateClose();
    document.removeEventListener('keydown', _onKeyDown);
  }

  /* ── Namespace export ─────────────────────────────────────────────────── */
  global.SpellModal = { openSpellModal, closeSpellModal };

}(window));
