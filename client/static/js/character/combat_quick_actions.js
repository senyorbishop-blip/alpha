/*
 * Combat Quick Actions modal flows for spells and equipped weapons.
 * Keeps the quick bar lightweight while reusing play.html's live spell/attack
 * math and dice/chat functions.
 * Exposes: window.CombatQuickActions
 */
(function initCombatQuickActions(global) {
  'use strict';

  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function _firstText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value === null || value === undefined) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }

  function _safeArray(value) { return Array.isArray(value) ? value : []; }

  function _allSpells() {
    if (typeof global.getCombatQuickBarSpells === 'function') return _safeArray(global.getCombatQuickBarSpells());
    if (typeof global._getCombatQuickSpells === 'function') return _safeArray(global._getCombatQuickSpells());
    return [];
  }

  function _findSpell(spellOrId) {
    if (spellOrId && typeof spellOrId === 'object') return spellOrId;
    const raw = String(spellOrId || '').trim();
    const lower = raw.toLowerCase();
    return _allSpells().find(function (spell) {
      return String(spell && spell.id || '') === raw || String(spell && spell.name || '').toLowerCase() === lower;
    }) || null;
  }

  function _allWeapons() {
    return typeof global._getUnifiedQuickAttackCards === 'function' ? _safeArray(global._getUnifiedQuickAttackCards()) : [];
  }

  function _findWeapon(actionOrId) {
    if (actionOrId && typeof actionOrId === 'object' && (actionOrId.damage_formula || actionOrId.attack_bonus || actionOrId.source === 'equip_only')) return actionOrId;
    const raw = typeof actionOrId === 'object' ? _firstText(actionOrId.id, actionOrId.name) : String(actionOrId || '').trim();
    const lower = raw.toLowerCase();
    return _allWeapons().find(function (card) {
      return String(card && card.id || '') === raw || String(card && card.name || '').toLowerCase() === lower;
    }) || null;
  }

  function _baseSpellLevel(spell) {
    const raw = spell && (spell.level ?? spell.spell_level ?? (spell.card && (spell.card.level ?? spell.card.spell_level)));
    if (raw === null || raw === undefined || raw === '') return null;
    const n = Number(raw);
    return Number.isFinite(n) ? Math.max(0, Math.min(9, Math.floor(n))) : null;
  }

  function _levelLabel(level) {
    const ordinals = ['Cantrip', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th'];
    if (level === null || level === undefined || level === '') return 'Unknown spell level';
    const n = Number(level);
    if (!Number.isFinite(n)) return 'Unknown spell level';
    return n <= 0 ? 'Cantrip' : (ordinals[n] || (n + 'th')) + '-level';
  }

  function _spellCastOptions(spell) {
    if (typeof global._getCombatSpellCastOptions === 'function') return _safeArray(global._getCombatSpellCastOptions(spell));
    const level = _baseSpellLevel(spell);
    return level === 0 ? [{ value: 0, label: 'Cantrip', disabled: false }] : [];
  }

  function _selectedCastLevel(spell) {
    const select = document.getElementById('combat-quick-spell-level');
    if (select && select.value !== '') return Number(select.value);
    const base = _baseSpellLevel(spell);
    return base === null ? '' : base;
  }

  function _spellDamagePreview(spell, castLevel) {
    if (typeof global.getCombatSpellDamagePreview === 'function') return global.getCombatSpellDamagePreview(spell.id || spell.name, castLevel);
    const card = spell.card || spell || {};
    const current = card.current || {};
    return _firstText((card.cast_options || {})[String(castLevel)] && (card.cast_options || {})[String(castLevel)].formula, current.formula, card.damage_dice, card.damage, card.damage_formula, card.base_damage_formula, '');
  }

  function _spellSaveText(card) {
    const saveAbility = _firstText(card.save_ability, card.saveAbility, card.save).toUpperCase().replace(/[^A-Z]/g, '');
    const saveDc = _firstText(card.save_dc, card.saveDC);
    if (saveDc && saveAbility) return 'DC ' + saveDc + ' ' + saveAbility;
    if (saveDc) return 'DC ' + saveDc;
    if (saveAbility) return saveAbility + ' save';
    return '';
  }

  function _spellHasAttack(card) {
    const text = [card.attack_type, card.attackType, card.base_effect_text, card.description, card.current && card.current.effect].filter(Boolean).join(' ').toLowerCase();
    return /spell attack|attack roll|ranged spell attack|melee spell attack/.test(text) || /attack/.test(String(card.attack_type || '').toLowerCase());
  }

  function _spellDetailsHtml(spell, castLevel) {
    const card = spell.card || spell || {};
    const damage = _spellDamagePreview(spell, castLevel);
    const save = _spellSaveText(card);
    const attackBonus = _firstText(card.attack_bonus, card.attackBonus);
    const flags = [card.concentration || card.is_concentration ? 'Concentration' : '', card.ritual || card.is_ritual ? 'Ritual' : '', card.prepared === false ? 'Known' : (card.prepared === true ? 'Prepared' : '')].filter(Boolean);
    const rows = [
      ['Level', _levelLabel(_baseSpellLevel(spell))],
      ['School / Type', _firstText(card.school, card.level_school, card.levelSchool, spell.level_school, '—')],
      ['Casting Time', _firstText(card.casting_time, card.castingTime, spell.casting_time, '1 action')],
      ['Range', _firstText(card.range, spell.range, '—')],
      ['Attack Bonus', attackBonus || '—'],
      ['Save', save || '—'],
      ['Damage', damage || '—'],
      ['Damage Type', _firstText(card.damage_type, card.damageType, card.healing_type, '—')],
      ['Flags', flags.join(' • ') || '—'],
    ];
    return rows.map(function (row) {
      return '<div class="cqa-meta-card"><strong>' + _esc(row[0]) + '</strong><span>' + _esc(row[1]) + '</span></div>';
    }).join('');
  }

  function refreshSpellModalDamage() {
    const overlay = document.getElementById('combat-quick-action-modal');
    if (!overlay) return;
    const spell = _findSpell(overlay.getAttribute('data-cqa-spell-id'));
    if (!spell) return;
    const castLevel = _selectedCastLevel(spell);
    const detailHost = overlay.querySelector('[data-cqa-spell-details]');
    if (detailHost) detailHost.innerHTML = _spellDetailsHtml(spell, castLevel);
    const dmg = overlay.querySelector('[data-cqa-damage-preview]');
    if (dmg) dmg.textContent = _spellDamagePreview(spell, castLevel) || 'No damage roll';
  }

  function closeModal() {
    const existing = document.getElementById('combat-quick-action-modal');
    if (existing) existing.remove();
  }

  function _installStyles() {
    if (document.getElementById('combat-quick-actions-styles')) return;
    const style = document.createElement('style');
    style.id = 'combat-quick-actions-styles';
    style.textContent = '.cqa-overlay{position:fixed;inset:0;background:rgba(0,0,0,.68);z-index:9999;display:flex;align-items:center;justify-content:center;padding:1rem}.cqa-panel{width:min(460px,calc(100vw - 28px));min-width:240px;max-width:min(820px,96vw);min-height:180px;max-height:90vh;overflow-y:auto;overflow-x:auto;resize:both;border:1px solid rgba(0,229,204,.32);border-radius:16px;background:linear-gradient(145deg,rgba(13,18,24,.98),rgba(28,20,13,.96));box-shadow:0 18px 48px rgba(0,0,0,.62);color:#f5ead6;padding:1rem;box-sizing:border-box}.cqa-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;margin-bottom:.7rem}.cqa-kicker{font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;color:#9ff6ea}.cqa-title{font-family:Cinzel,serif;font-size:1rem;color:var(--gold,#d4af37);font-weight:800}.cqa-sub{font-size:.68rem;color:rgba(245,234,214,.68);margin-top:.15rem}.cqa-close{border:1px solid rgba(255,255,255,.15);border-radius:999px;background:rgba(255,255,255,.05);color:#f5ead6;width:1.9rem;height:1.9rem;cursor:pointer;flex-shrink:0}.cqa-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:.42rem;margin:.6rem 0}.cqa-meta-card{border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.04);padding:.42rem .5rem;display:grid;gap:.12rem}.cqa-meta-card strong{font-size:.55rem;color:rgba(245,234,214,.62);text-transform:uppercase;letter-spacing:.07em}.cqa-meta-card span{font-size:.72rem;color:#f7ecd8}.cqa-desc{font-size:.7rem;line-height:1.4;color:rgba(245,234,214,.75);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:.55rem;background:rgba(0,0,0,.18);margin:.5rem 0}.cqa-controls{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.75rem}.cqa-btn{border:1px solid rgba(0,229,204,.35);border-radius:9px;background:rgba(0,229,204,.12);color:#9ff6ea;padding:.48rem .7rem;cursor:pointer;font-size:.72rem;font-weight:800}.cqa-btn.damage{border-color:rgba(255,120,80,.38);background:rgba(255,120,80,.12);color:#ffb39a}.cqa-btn.save{border-color:rgba(255,210,90,.38);background:rgba(255,210,90,.12);color:#ffe8a3}.cqa-btn.cast{border-color:rgba(155,89,182,.5);background:rgba(155,89,182,.18);color:#d8b7ff}.cqa-btn:disabled{opacity:.45;cursor:not-allowed}.cqa-select{width:100%;border:1px solid rgba(255,255,255,.14);border-radius:9px;background:rgba(0,0,0,.24);color:#f7ecd8;padding:.44rem .55rem;margin:.45rem 0 .2rem}.cqa-levels{margin:.35rem 0 .5rem}.cqa-levels-title{font-size:.52rem;text-transform:uppercase;letter-spacing:.08em;color:rgba(245,234,214,.45);margin-bottom:.28rem}.cqa-levels-grid{display:flex;flex-wrap:wrap;gap:.22rem}.cqa-level-cell{font-size:.62rem;border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:.14rem .34rem;color:rgba(245,234,214,.65);background:rgba(255,255,255,.03)}.cqa-level-cell.active{border-color:rgba(0,229,204,.45);color:#9ff6ea;background:rgba(0,229,204,.08);font-weight:700}.cqa-level-cell.disabled{opacity:.45}';
    document.head.appendChild(style);
  }

  var _CQA_LS_KEY = 'cqa_modal_size_v1';

  function _applySavedPanelSize(panel) {
    try {
      var saved = JSON.parse(localStorage.getItem(_CQA_LS_KEY) || 'null');
      if (saved && saved.w && saved.h) {
        panel.style.width = Math.max(240, Math.min(820, saved.w)) + 'px';
        panel.style.height = Math.max(180, Math.min(window.innerHeight * 0.9, saved.h)) + 'px';
      }
    } catch (e) {}
  }

  function _watchPanelResize(panel) {
    if (typeof ResizeObserver === 'undefined') return;
    var ro = new ResizeObserver(function () {
      try {
        localStorage.setItem(_CQA_LS_KEY, JSON.stringify({ w: panel.offsetWidth, h: panel.offsetHeight }));
      } catch (e) {}
    });
    ro.observe(panel);
  }

  function openSpellAction(spellOrId, preferredLevel) {
    const spell = _findSpell(spellOrId);
    if (!spell) return false;
    _installStyles();
    closeModal();
    const card = spell.card || spell || {};
    const baseLevel = _baseSpellLevel(spell);
    if (baseLevel === null && global.console && global.console.warn) {
      global.console.warn('[CombatQuickActions] Spell metadata missing; showing safe fallback.', { spell: spell.name || spell.id, missing: ['level'] });
    }
    const options = _spellCastOptions(spell);
    const selected = preferredLevel !== undefined ? preferredLevel : (options.find(function (opt) { return !opt.disabled; }) || options[0] || {}).value;
    const cardDirectDamage = _firstText(card.damage_dice, card.damage, card.damage_formula, card.base_damage_formula, card.current && card.current.formula && card.current.formula !== '—' ? card.current.formula : '', '');
    const hasDamage = !!_spellDamagePreview(spell, selected) || (!!cardDirectDamage && cardDirectDamage !== '—');
    const hasAttack = _spellHasAttack(card) || !!_firstText(card.attack_bonus, card.attackBonus);
    const hasSave = !!_spellSaveText(card);
    const fullText = _firstText(card.fullPlayerDetailText, card.description, card.base_effect_text, card.current && card.current.effect, 'No spell details are loaded yet.');
    const overlay = document.createElement('div');
    overlay.id = 'combat-quick-action-modal';
    overlay.className = 'cqa-overlay';
    overlay.setAttribute('data-cqa-spell-id', String(spell.id || spell.name || ''));
    const schoolPart = _firstText(card.school, '');
    const subtitleParts = [baseLevel !== null ? _levelLabel(baseLevel) : '', schoolPart].filter(Boolean);
    const damageType = _firstText(card.damage_type, card.damageType, card.healing_type, '');
    // Build per-level damage scaling row (DnD-Beyond style)
    var levelScalingHtml = '';
    if (baseLevel !== null && baseLevel > 0 && options.length) {
      var cells = options.map(function (opt) {
        var dmg = _spellDamagePreview(spell, opt.value) || (String(opt.value) === String(baseLevel) ? _firstText(card.damage_dice, card.damage, card.damage_formula, card.base_damage_formula, '') : '');
        var label = typeof opt.value === 'number' && opt.value > 0 ? (['', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th'][opt.value] || (opt.value + 'th')) : (opt.label || String(opt.value));
        return dmg ? '<span class="cqa-level-cell' + (String(opt.value) === String(selected) ? ' active' : '') + (opt.disabled ? ' disabled' : '') + '">' + _esc(label) + ': ' + _esc(dmg + (damageType ? ' ' + damageType : '')) + '</span>' : '';
      }).filter(Boolean);
      if (cells.length) levelScalingHtml = '<div class="cqa-levels"><div class="cqa-levels-title">At each slot level</div><div class="cqa-levels-grid">' + cells.join('') + '</div></div>';
    }
    overlay.innerHTML = '<div class="cqa-panel" role="dialog" aria-modal="true" aria-label="Quick spell action">'
      + '<div class="cqa-head"><div><div class="cqa-kicker">Quick Spell</div><div class="cqa-title">' + _esc(spell.name || 'Spell') + '</div><div class="cqa-sub">' + _esc(subtitleParts.join(' • ')) + '</div></div><button class="cqa-close" type="button" data-cqa-close>×</button></div>'
      + (baseLevel === 0 ? '' : '<label class="cqa-kicker" for="combat-quick-spell-level">Cast Level / Slot</label><select id="combat-quick-spell-level" class="cqa-select" onchange="window.CombatQuickActions.refreshSpellModalDamage()">' + options.map(function (opt) { return '<option value="' + _esc(opt.value) + '" ' + (String(opt.value) === String(selected) ? 'selected' : '') + ' ' + (opt.disabled ? 'disabled' : '') + '>' + _esc(opt.label || 'Cast') + '</option>'; }).join('') + '</select>')
      + '<div class="cqa-meta" data-cqa-spell-details>' + _spellDetailsHtml(spell, selected) + '</div>'
      + (levelScalingHtml ? levelScalingHtml : '')
      + '<div class="cqa-desc">' + _esc(fullText) + '</div>'
      + '<div class="cqa-controls"><button class="cqa-btn cast" type="button" data-cqa-cast ' + ((options[0] && options[0].disabled) ? 'disabled' : '') + '>Cast</button>'
      + (hasAttack ? '<button class="cqa-btn" type="button" data-cqa-spell-attack>Roll Attack</button>' : '')
      + (hasDamage ? '<button class="cqa-btn damage" type="button" data-cqa-spell-damage>Roll Damage</button>' : '')
      + (hasSave ? '<button class="cqa-btn save" type="button" data-cqa-spell-save>Show Save DC</button>' : '')
      + '<button class="cqa-btn" type="button" data-cqa-inspect>Open Full Spell</button></div></div>';
    overlay.addEventListener('click', function (ev) {
      if (ev.target === overlay || ev.target.closest('[data-cqa-close]')) { closeModal(); return; }
      const castLevel = _selectedCastLevel(spell);
      if (ev.target.closest('[data-cqa-cast]')) { global.combatQuickCastSpell(spell.id || spell.name, castLevel); closeModal(); return; }
      if (ev.target.closest('[data-cqa-spell-attack]')) { global.combatQuickRollSpellAttack(spell.id || spell.name, castLevel); return; }
      if (ev.target.closest('[data-cqa-spell-damage]')) { global.combatQuickRollSpellDamage(spell.id || spell.name, castLevel); return; }
      if (ev.target.closest('[data-cqa-spell-save]')) { global.combatQuickShowSpellSave(spell.id || spell.name, castLevel); return; }
      if (ev.target.closest('[data-cqa-inspect]') && typeof global.playerInspectSpell === 'function') global.playerInspectSpell(spell.id || spell.name);
    });
    document.body.appendChild(overlay);
    var panel = overlay.querySelector('.cqa-panel');
    if (panel) { _applySavedPanelSize(panel); _watchPanelResize(panel); }
    return true;
  }

  function openWeaponAction(actionOrId) {
    const card = _findWeapon(actionOrId);
    if (!card) return false;
    _installStyles();
    closeModal();
    const hasVersatile = !!card.versatile_damage_formula;
    const properties = _safeArray(card.properties).join(', ');
    const rows = [
      ['Attack Bonus', _firstText(card.attack_bonus, card.attackBonus, '—')],
      ['Damage', _firstText(card.damage_formula, card.damage, '—')],
      ['Damage Type', _firstText(card.damage_type, card.damageType, '—')],
      ['Ability / Proficiency', _firstText(card.ability_label, card.ability, '') + (_firstText(card.proficiency_label, card.proficient === false ? 'Not proficient' : 'Proficient') ? (' • ' + _firstText(card.proficiency_label, card.proficient === false ? 'Not proficient' : 'Proficient')) : '')],
      ['Range / Reach', _firstText(card.range, card.reach, '—')],
      ['Properties', properties || _safeArray(card.badges).join(', ') || '—'],
      ['Versatile', card.versatile_damage_formula || '—'],
    ];
    const overlay = document.createElement('div');
    overlay.id = 'combat-quick-action-modal';
    overlay.className = 'cqa-overlay';
    overlay.setAttribute('data-cqa-weapon-id', String(card.id || card.name || ''));
    overlay.innerHTML = '<div class="cqa-panel" role="dialog" aria-modal="true" aria-label="Quick weapon action">'
      + '<div class="cqa-head"><div><div class="cqa-kicker">Quick Weapon</div><div class="cqa-title">' + _esc(card.name || 'Weapon') + '</div><div class="cqa-sub">' + _esc([card.slot, card.handed, card.mastery_label ? ('Mastery ' + card.mastery_label) : ''].filter(Boolean).join(' • ')) + '</div></div><button class="cqa-close" type="button" data-cqa-close>×</button></div>'
      + (hasVersatile ? '<label class="cqa-kicker" for="combat-quick-weapon-mode">Damage Mode</label><select id="combat-quick-weapon-mode" class="cqa-select"><option value="base">One-handed / normal</option><option value="versatile">Two-handed versatile</option></select>' : '')
      + '<div class="cqa-meta">' + rows.map(function (row) { return '<div class="cqa-meta-card"><strong>' + _esc(row[0]) + '</strong><span>' + _esc(row[1]) + '</span></div>'; }).join('') + '</div>'
      + '<div class="cqa-desc">' + _esc(_firstText(card.notes, card.mastery_text, 'Equipped weapon quick action.')) + '</div>'
      + '<div class="cqa-controls"><button class="cqa-btn" type="button" data-cqa-weapon-attack>Roll Attack</button><button class="cqa-btn damage" type="button" data-cqa-weapon-damage>Roll Damage</button><button class="cqa-btn damage" type="button" data-cqa-weapon-crit>Roll Critical Damage</button></div></div>';
    overlay.addEventListener('click', function (ev) {
      if (ev.target === overlay || ev.target.closest('[data-cqa-close]')) { closeModal(); return; }
      const modeSelect = document.getElementById('combat-quick-weapon-mode');
      const mode = modeSelect ? modeSelect.value : 'base';
      if (ev.target.closest('[data-cqa-weapon-attack]')) { global.combatQuickWeaponAttack(card.id || card.name, mode); closeModal(); return; }
      if (ev.target.closest('[data-cqa-weapon-damage]')) { global.combatQuickRollWeaponDamage(card.id || card.name, mode, false); return; }
      if (ev.target.closest('[data-cqa-weapon-crit]')) { global.combatQuickRollWeaponDamage(card.id || card.name, mode, true); return; }
    });
    document.body.appendChild(overlay);
    var panel = overlay.querySelector('.cqa-panel');
    if (panel) { _applySavedPanelSize(panel); _watchPanelResize(panel); }
    return true;
  }

  global.CombatQuickActions = { openSpellAction, openWeaponAction, refreshSpellModalDamage, closeModal };
}(window));
