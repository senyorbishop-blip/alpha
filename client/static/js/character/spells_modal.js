/*
 * client/static/js/character/spells_modal.js
 * Spell Detail Modal — Shows complete spell information on click.
 * Uses resolveSpellRuntime (spell_runtime.js) so preview + formulas are
 * always consistent with every other spell surface.
 *
 * Exposes: window.SpellModal
 *   .openSpellModal(spellData, castOpts?)
 *   .closeSpellModal()
 *
 * castOpts: { castLevel?, characterLevel?, spellcastingModifier?, saveDc?,
 *             spellAttackBonus? }
 */

(function initSpellModal(global) {
  'use strict';

  /* ── Module state ─────────────────────────────────────────────────────── */
  var _overlay = null;
  var _closeTimeout = null;
  var _currentSpell = null;
  var _currentOpts  = {};

  /* ── Helpers ──────────────────────────────────────────────────────────── */
  function _esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      function (ch) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]; }
    );
  }

  function _descToHtml(text) {
    if (!text) return '';
    return String(text)
      .split(/\n{2,}/)
      .map(function (p) { return '<p>' + _esc(p.trim()).replace(/\n/g, '<br>') + '</p>'; })
      .join('');
  }

  function _rt() {
    /* Resolve the runtime for the current spell + options. */
    if (!_currentSpell || typeof global.resolveSpellRuntime !== 'function') return null;
    var castLevel = num(document.getElementById('cs-modal-level-select') && document.getElementById('cs-modal-level-select').value, null);
    var opts = Object.assign({}, _currentOpts);
    if (castLevel !== null) opts.castLevel = castLevel;
    try { return global.resolveSpellRuntime(_currentSpell, opts); } catch (e) { return null; }
  }

  function num(v, fb) {
    if (fb === undefined) fb = null;
    if (v === null || v === undefined || v === '') return fb;
    var n = Number(v);
    return Number.isFinite(n) ? Math.floor(n) : fb;
  }

  var SCHOOL_NAMES = {
    abjuration: 'Abjuration', conjuration: 'Conjuration', divination: 'Divination',
    enchantment: 'Enchantment', evocation: 'Evocation', illusion: 'Illusion',
    necromancy: 'Necromancy', transmutation: 'Transmutation',
  };

  function _levelLabel(level) {
    var n = parseInt(level, 10);
    if (!n || n === 0) return 'Cantrip';
    var suffix = n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th';
    return n + suffix + '-Level';
  }

  /* ── Build slot-level options list ───────────────────────────────────── */
  function _slotOptions(baseLevel, selectedLevel) {
    if (!baseLevel || baseLevel <= 0) return '';
    var ordinals = ['', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th'];
    var html = '';
    for (var lvl = baseLevel; lvl <= 9; lvl++) {
      var sel = (lvl === selectedLevel) ? ' selected' : '';
      html += '<option value="' + lvl + '"' + sel + '>' + (ordinals[lvl] || (lvl + 'th')) + ' level</option>';
    }
    return html;
  }

  /* ── Build modal HTML ─────────────────────────────────────────────────── */
  function _buildModalHtml(spell, rt, selectedLevel) {
    var school = SCHOOL_NAMES[String(spell.school || '').toLowerCase()] || _esc(spell.school || 'Unknown');
    var baseLevel = rt ? rt.baseLevel : (parseInt(spell.level, 10) || 0);
    var levelLabel = _levelLabel(rt ? rt.castLevel : baseLevel);
    var isConc  = Boolean(rt ? rt.concentration : spell.concentration);
    var isRitual = Boolean(rt ? rt.ritual : spell.ritual);

    var compText = '—';
    if (spell.components) {
      if (typeof spell.components === 'string') {
        compText = _esc(spell.components);
      } else if (typeof spell.components === 'object') {
        var compParts = [];
        if (spell.components.verbal)   compParts.push('V');
        if (spell.components.somatic)  compParts.push('S');
        if (spell.components.material) {
          var mat = spell.components.material_text || spell.components.material;
          compParts.push(typeof mat === 'string' && mat !== 'true' ? 'M (' + _esc(mat) + ')' : 'M');
        }
        compText = compParts.length ? compParts.join(', ') : '—';
      }
    }

    var badges = [
      isConc   ? '<span class="cs-modal-badge concentration">Concentration</span>' : '',
      isRitual ? '<span class="cs-modal-badge ritual">Ritual</span>'              : '',
    ].filter(Boolean).join('');

    var tags = Array.isArray(spell.tags) && spell.tags.length
      ? '<div class="cs-modal-section-title">Tags</div><div class="cs-modal-tags">' + spell.tags.map(function (t) { return '<span class="cs-modal-tag">' + _esc(t) + '</span>'; }).join('') + '</div>'
      : '';

    var classes = Array.isArray(spell.classes) && spell.classes.length
      ? '<div class="cs-modal-section-title">Classes</div><div class="cs-modal-classes">' + spell.classes.map(_esc).join(', ') + '</div>'
      : '';

    var higherLevel = (spell.scalingNote || spell.higher_levels || spell.atHigherLevels || spell.higherLevel)
      ? '<div class="cs-modal-section-title">Scaling &amp; Slot Use</div><div class="cs-modal-higher">' + _esc(spell.scalingNote || spell.higher_levels || spell.atHigherLevels || spell.higherLevel) + '</div>'
      : '';

    var quickEffect = (spell.effect || spell.playerFacingEffectSummary)
      ? '<div class="cs-modal-section-title">Quick Summary</div><div class="cs-modal-higher">' + _esc(spell.effect || spell.playerFacingEffectSummary) + '</div>'
      : '';

    /* Resolved combat values */
    var formula    = (rt && rt.displayFormula) ? rt.displayFormula : (spell.damageFormula || spell.healingFormula || '—');
    var attackSave = '';
    if (rt && rt.saveAbility)       attackSave = 'DC ' + (rt.saveDc || '?') + ' ' + rt.saveAbility + ' save';
    else if (rt && rt.attackType)   attackSave = rt.attackType + (rt.attackBonus ? ' (' + rt.attackBonus + ')' : '');
    else attackSave = _esc(spell.attackType || spell.savingThrow || spell.saveDC || '—');

    var dmgType = (rt && (rt.damageType || rt.healingType)) ? (rt.damageType || rt.healingType) : (spell.damageType || '—');

    /* Slot picker – only for upcastable (non-cantrip) spells */
    var slotPickerHtml = '';
    if (baseLevel !== null && baseLevel > 0) {
      slotPickerHtml = '<div class="cs-modal-slot-picker">'
        + '<label class="cs-modal-slot-label" for="cs-modal-level-select">Cast at level:</label>'
        + '<select id="cs-modal-level-select" class="cs-modal-slot-select">' + _slotOptions(baseLevel, selectedLevel || rt && rt.castLevel || baseLevel) + '</select>'
        + '</div>';
    }

    /* Formula display */
    var formulaHtml = formula && formula !== '—'
      ? '<div class="cs-modal-section-title">Formula at <span id="cs-modal-level-label">' + _esc(_levelLabel(rt ? rt.castLevel : baseLevel)) + '</span></div>'
        + '<div class="cs-modal-formula" id="cs-modal-formula">' + _esc(formula) + '</div>'
      : '';

    var combat = '<div class="cs-modal-section-title">Combat Summary</div>'
      + '<div class="cs-modal-meta-grid">'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Attack / Save</span><span class="cs-modal-meta-value">' + attackSave + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Damage / Healing</span><span class="cs-modal-meta-value" id="cs-modal-damage-preview">' + _esc(formula) + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Damage Type</span><span class="cs-modal-meta-value">' + _esc(dmgType) + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Effect</span><span class="cs-modal-meta-value">' + _esc(spell.effect || spell.playerFacingEffectSummary || '—') + '</span></div>'
      + '</div>';

    return '<div class="cs-spell-modal-inner">'
      + '<button class="cs-modal-close" aria-label="Close spell details" data-csp-close>&#x2715;</button>'
      + '<div class="cs-modal-title">' + _esc(spell.displayName || spell.name || 'Unknown Spell') + '</div>'
      + '<div><span class="cs-modal-school">' + _esc(levelLabel) + ' &middot; ' + _esc(school) + '</span></div>'
      + (badges ? '<div class="cs-modal-badges">' + badges + '</div>' : '')
      + slotPickerHtml
      + formulaHtml
      + '<div class="cs-modal-meta-grid">'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Casting Time</span><span class="cs-modal-meta-value">' + _esc(spell.castingTime || spell.casting_time || (rt && rt.castingTime) || '—') + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Range</span><span class="cs-modal-meta-value">' + _esc(spell.range || (rt && rt.range) || '—') + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Components</span><span class="cs-modal-meta-value">' + compText + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Duration</span><span class="cs-modal-meta-value">' + _esc(spell.duration || (rt && rt.duration) || '—') + '</span></div>'
      + '<div class="cs-modal-meta-item"><span class="cs-modal-meta-label">Area / Target</span><span class="cs-modal-meta-value">' + _esc(spell.areaText || spell.target || '—') + '</span></div>'
      + '</div>'
      + quickEffect
      + '<div class="cs-modal-desc">' + _descToHtml(spell.fullPlayerDetailText || spell.description || spell.desc || '') + '</div>'
      + combat
      + higherLevel
      + tags
      + classes
      + '</div>';
  }

  /* ── Update formula display when cast level changes ───────────────────── */
  function _refreshFormula() {
    if (!_currentSpell) return;
    var rt = _rt();
    if (!rt) return;

    var formulaEl = _overlay && _overlay.querySelector('#cs-modal-formula');
    var previewEl = _overlay && _overlay.querySelector('#cs-modal-damage-preview');
    var labelEl   = _overlay && _overlay.querySelector('#cs-modal-level-label');

    var display = rt.displayFormula || '—';
    if (formulaEl) formulaEl.textContent = display;
    if (previewEl) previewEl.textContent = display;
    if (labelEl)   labelEl.textContent   = _levelLabel(rt.castLevel);
  }

  /* ── DOM helpers ──────────────────────────────────────────────────────── */
  function _ensureOverlay() {
    if (_overlay && document.body.contains(_overlay)) return _overlay;
    _overlay = document.createElement('div');
    _overlay.className = 'cs-spell-modal';
    _overlay.setAttribute('role', 'dialog');
    _overlay.setAttribute('aria-modal', 'true');
    document.body.appendChild(_overlay);
    return _overlay;
  }

  /* ── Close animation ──────────────────────────────────────────────────── */
  function _animateClose(cb) {
    if (!_overlay) { if (cb) cb(); return; }
    _overlay.classList.add('closing');
    clearTimeout(_closeTimeout);
    _closeTimeout = setTimeout(function () {
      if (_overlay && _overlay.parentNode) _overlay.parentNode.removeChild(_overlay);
      _overlay = null;
      document.removeEventListener('keydown', _onKeyDown);
      if (cb) cb();
    }, 220);
  }

  function _onKeyDown(e) { if (e.key === 'Escape') closeSpellModal(); }

  /* ── Public API ───────────────────────────────────────────────────────── */
  /**
   * @param {object} spellData  – raw or enriched spell card
   * @param {object} [castOpts] – { castLevel?, characterLevel?, spellcastingModifier?, saveDc?, spellAttackBonus? }
   */
  function openSpellModal(spellData, castOpts) {
    if (!spellData || typeof spellData !== 'object') return;

    _currentSpell = spellData;
    _currentOpts  = Object.assign({}, castOpts || {});

    clearTimeout(_closeTimeout);

    /* Resolve runtime for the initial display */
    var rt = null;
    if (typeof global.resolveSpellRuntime === 'function') {
      try { rt = global.resolveSpellRuntime(spellData, _currentOpts); } catch (e) {}
    }
    var selectedLevel = _currentOpts.castLevel || (rt && rt.castLevel) || parseInt(spellData.level, 10) || 0;

    var overlay = _ensureOverlay();
    overlay.classList.remove('closing');
    overlay.innerHTML = _buildModalHtml(spellData, rt, selectedLevel);

    /* Wire slot picker – must use addEventListener to survive innerHTML replace
     * and to call stopPropagation so the overlay click handler can't fire.      */
    var levelSelect = overlay.querySelector('#cs-modal-level-select');
    if (levelSelect) {
      levelSelect.addEventListener('change', function (ev) {
        ev.stopPropagation();
        _refreshFormula();
      });
      levelSelect.addEventListener('click', function (ev) {
        ev.stopPropagation(); /* prevent click from bubbling to overlay close */
      });
      /* Also intercept mousedown so option-list open/close doesn't reach overlay */
      levelSelect.addEventListener('mousedown', function (ev) {
        ev.stopPropagation();
      });
    }

    /* Close on overlay background click only */
    overlay.addEventListener('click', function _overlayClick(ev) {
      var tag = ev.target && ev.target.tagName ? ev.target.tagName.toUpperCase() : '';
      if (tag === 'SELECT' || tag === 'OPTION') { ev.stopPropagation(); return; }
      if (ev.target === overlay) {
        closeSpellModal();
        overlay.removeEventListener('click', _overlayClick);
      }
    });

    /* Close button */
    var closeBtn = overlay.querySelector('[data-csp-close]');
    if (closeBtn) closeBtn.addEventListener('click', closeSpellModal);

    document.addEventListener('keydown', _onKeyDown);
  }

  function closeSpellModal() {
    _currentSpell = null;
    _currentOpts  = {};
    _animateClose();
    document.removeEventListener('keydown', _onKeyDown);
  }

  /* ── Namespace export ─────────────────────────────────────────────────── */
  global.SpellModal = { openSpellModal: openSpellModal, closeSpellModal: closeSpellModal };

}(window));
