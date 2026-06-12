/*
 * Combat Quick Action selectors.
 *
 * This module intentionally reuses the premium character sheet action model
 * exported by ActionsTab instead of re-parsing attacks/features or duplicating
 * combat math.  It adds only the compact grouping needed by the movable combat
 * quick bar.
 *
 * Exposes: window.CombatQuickSelectors
 */
(function initCombatQuickSelectors(global) {
  'use strict';

  function _safeArray(value) {
    return Array.isArray(value) ? value : [];
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

  function _runtime() {
    if (typeof global.getCombatQuickBarRuntime === 'function') {
      return global.getCombatQuickBarRuntime() || {};
    }
    return {
      combat: global._combat || { active: false, turn: 0, combatants: [] },
      charSheet: global._charSheet || {},
      selectedTargetId: global._combat && global._combat.selected_target_id,
    };
  }

  function _uniqueByName(items, limit) {
    const seen = new Set();
    const out = [];
    _safeArray(items).forEach(function (item) {
      const key = _firstText(item && item.id, item && item.name).toLowerCase();
      if (!key || seen.has(key)) return;
      seen.add(key);
      out.push(item);
    });
    return out.slice(0, limit || out.length);
  }

  function _combatTurnKey(combat) {
    if (!combat || !combat.active) return '';
    const current = _safeArray(combat.combatants)[Math.max(0, Number(combat.turn || 0))] || null;
    return [combat.round || 1, combat.turn || 0, current && (current.token_id || current.id || current.name || '')].join(':');
  }

  function _usedThisTurnStoreKey(runtime) {
    const sessionId = _firstText(runtime && runtime.sessionId, global.SESSION_ID, 'session');
    const userId = _firstText(runtime && runtime.userId, global.USER_ID, 'anon');
    return 'combat_quick_bar.used.' + sessionId + '.' + userId;
  }

  function _readUsedThisTurn(runtime) {
    try {
      const raw = global.localStorage && global.localStorage.getItem(_usedThisTurnStoreKey(runtime));
      const parsed = raw ? JSON.parse(raw) : null;
      if (!parsed || parsed.turnKey !== _combatTurnKey(runtime.combat)) return { turnKey: _combatTurnKey(runtime.combat), used: {} };
      return { turnKey: parsed.turnKey, used: parsed.used || {} };
    } catch (_err) {
      return { turnKey: _combatTurnKey(runtime.combat), used: {} };
    }
  }

  function markUsed(actionKey) {
    const runtime = _runtime();
    if (!actionKey) return;
    const state = _readUsedThisTurn(runtime);
    state.used[String(actionKey)] = true;
    try {
      global.localStorage && global.localStorage.setItem(_usedThisTurnStoreKey(runtime), JSON.stringify(state));
    } catch (_err) {}
  }

  const QUICK_PICK_LIMIT = 5;

  function _quickPickCharacterKey(runtime) {
    const sheet = runtime && runtime.charSheet ? runtime.charSheet : {};
    return _firstText(sheet.id, sheet.profileId, sheet.characterId, sheet.name, global.NAME, 'character')
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, '-');
  }

  function _quickPickStoreKey(runtime) {
    const sessionId = _firstText(runtime && runtime.sessionId, global.SESSION_ID, 'session');
    const userId = _firstText(runtime && runtime.userId, global.USER_ID, 'anon');
    return 'combat_quick_bar.picks.' + sessionId + '.' + userId + '.' + _quickPickCharacterKey(runtime);
  }

  function _candidateKey(kind, item) {
    return String(kind || 'action') + ':' + _firstText(item && item.id, item && item.name);
  }

  function readQuickPicks(runtime) {
    try {
      const raw = global.localStorage && global.localStorage.getItem(_quickPickStoreKey(runtime || _runtime()));
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.map(function (entry) { return String(entry || '').trim(); }).filter(Boolean).slice(0, QUICK_PICK_LIMIT) : [];
    } catch (_err) {
      return [];
    }
  }

  function writeQuickPicks(picks, runtime) {
    const next = _safeArray(picks).map(function (entry) { return String(entry || '').trim(); }).filter(Boolean).slice(0, QUICK_PICK_LIMIT);
    try {
      if (next.length) global.localStorage && global.localStorage.setItem(_quickPickStoreKey(runtime || _runtime()), JSON.stringify(next));
      else global.localStorage && global.localStorage.removeItem(_quickPickStoreKey(runtime || _runtime()));
    } catch (_err) {}
    return next;
  }

  function toggleQuickPick(kind, item) {
    const runtime = _runtime();
    const key = _candidateKey(kind, item);
    if (!key || /:$/.test(key)) return readQuickPicks(runtime);
    const picks = readQuickPicks(runtime);
    const existing = picks.indexOf(key);
    if (existing >= 0) picks.splice(existing, 1);
    else {
      if (picks.length >= QUICK_PICK_LIMIT) picks.shift();
      picks.push(key);
    }
    return writeQuickPicks(picks, runtime);
  }


  function _parseSpellLevelText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value === null || value === undefined || value === '') continue;
      if (typeof value === 'number' && Number.isFinite(value)) return Math.max(0, Math.min(9, Math.floor(value)));
      const text = String(value).trim().toLowerCase();
      if (!text) continue;
      if (text === 'cantrip' || /\bcantrip\b/.test(text)) return 0;
      const direct = Number(text);
      if (Number.isFinite(direct)) return Math.max(0, Math.min(9, Math.floor(direct)));
      const ordinal = text.match(/\b([1-9])(?:st|nd|rd|th)?\s*(?:level|lvl|spell|spells)\b/);
      if (ordinal) return Math.max(0, Math.min(9, parseInt(ordinal[1], 10)));
      const levelWord = text.match(/\blevel\s*([1-9])\b/);
      if (levelWord) return Math.max(0, Math.min(9, parseInt(levelWord[1], 10)));
    }
    return null;
  }

  function _baseLevelFromCastOptions(castOptions) {
    if (!castOptions || typeof castOptions !== 'object') return null;
    const levels = Object.keys(castOptions)
      .map(function (key) { return _parseSpellLevelText(key, castOptions[key] && castOptions[key].cast_level, castOptions[key] && castOptions[key].spell_level); })
      .filter(function (level) { return Number.isFinite(level); });
    const positive = levels.filter(function (level) { return level > 0; });
    if (positive.length) return Math.min.apply(null, positive);
    return levels.length ? Math.min.apply(null, levels) : null;
  }

  function _spellLevel(spell) {
    const card = spell && spell.card ? spell.card : {};
    const explicit = _parseSpellLevelText(spell && (spell.level ?? spell.spell_level), card && (card.level ?? card.spell_level));
    const levelText = _firstText(spell && (spell.level_school || spell.levelSchool || spell.section), card && (card.level_school || card.levelSchool || card.section));
    if (explicit !== null) return explicit;
    if (/cantrip/i.test(levelText)) return 0;
    const fromText = _parseSpellLevelText(levelText);
    if (fromText !== null) return fromText;
    const fromOptions = _baseLevelFromCastOptions((card && card.cast_options) || (spell && spell.cast_options));
    if (fromOptions !== null) return fromOptions;
    return _parseSpellLevelText(card && card.default_cast_level, card && card.current && (card.current.cast_level ?? card.current.spell_level), spell && spell.default_cast_level);
  }

  function _spellNeedsSlot(spell) {
    const level = _spellLevel(spell);
    return level !== null && level > 0;
  }

  function _spellSlotSummary(spell, runtime) {
    const level = _spellLevel(spell);
    if (level === null) return 'Unknown spell level';
    if (level === 0) return 'Cantrip';
    const slots = runtime && runtime.spellSlots ? runtime.spellSlots : {};
    const used = runtime && runtime.spellSlotState ? runtime.spellSlotState : {};
    const max = Number(slots[level] ?? slots[String(level)] ?? 0) || 0;
    const spent = Number(used[level] ?? used[String(level)] ?? 0) || 0;
    if (!max) return 'Needs slot';
    return 'L' + level + ' slots ' + Math.max(0, max - spent) + '/' + max;
  }

  function _spellAvailable(spell, runtime) {
    const level = _spellLevel(spell);
    if (level === null) return true;
    if (level === 0) return true;
    const slots = runtime && runtime.spellSlots ? runtime.spellSlots : {};
    const used = runtime && runtime.spellSlotState ? runtime.spellSlotState : {};
    const max = Number(slots[level] ?? slots[String(level)] ?? 0) || 0;
    const spent = Number(used[level] ?? used[String(level)] ?? 0) || 0;
    return max > 0 && spent < max;
  }

  function _formatSignedNumber(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return _firstText(value, '');
    return parsed >= 0 ? '+' + parsed : String(parsed);
  }

  function _spellTextBlob(spell) {
    const card = spell && spell.card ? spell.card : spell;
    const current = card && card.current ? card.current : {};
    return [
      card && card.attack_type,
      card && card.description,
      card && card.fullPlayerDetailText,
      card && card.playerFacingEffectSummary,
      card && card.effect,
      card && card.base_effect_text,
      current && current.effect,
      spell && spell.description,
      spell && spell.effect,
      spell && spell.base_effect_text,
    ].filter(Boolean).join(' ');
  }

  function _spellAttackKind(spell) {
    const card = spell && spell.card ? spell.card : spell;
    const attackType = _firstText(card && (card.attack_type || card.attackType), spell && (spell.attack_type || spell.attackType), '').toLowerCase();
    const text = _spellTextBlob(spell).toLowerCase();
    if (attackType) {
      if (/weapon/.test(attackType)) return 'weapon';
      if (/spell|ranged|melee/.test(attackType) || /attack/.test(attackType)) return 'spell';
    }
    if (/spell attack|ranged spell attack|melee spell attack/.test(text)) return 'spell';
    if (/weapon attack|melee weapon attack|ranged weapon attack/.test(text)) return 'weapon';
    return '';
  }

  function _spellAttackText(spell, runtime) {
    const card = spell && spell.card ? spell.card : spell;
    const sheet = runtime && runtime.charSheet ? runtime.charSheet : {};
    const raw = _firstText(
      card && card.attack_bonus,
      card && card.attackBonus,
      card && card.spell_attack_bonus,
      spell && spell.attack_bonus,
      spell && spell.attackBonus,
      _spellAttackKind(spell) === 'spell' && sheet && sheet.spellAttack,
      _spellAttackKind(spell) === 'spell' && sheet && sheet.spellAttackBonus,
      ''
    );
    return raw ? _formatSignedNumber(raw) : '';
  }

  function _spellSaveText(spell, runtime) {
    const card = spell && spell.card ? spell.card : spell;
    const sheet = runtime && runtime.charSheet ? runtime.charSheet : {};
    const saveAbility = _firstText(card && card.save_ability, card && card.saveAbility, card && card.save, spell && spell.save_ability, spell && spell.saveAbility, spell && spell.save, '');
    const explicitSaveDc = _firstText(card && card.save_dc, card && card.saveDC, spell && spell.save_dc, spell && spell.saveDC, '');
    const saveDc = _firstText(explicitSaveDc, saveAbility && sheet && sheet.spellSaveDc, saveAbility && sheet && sheet.spell_save_dc, '');
    if (saveDc && saveAbility) return 'DC ' + saveDc + ' ' + String(saveAbility).toUpperCase().replace(/[^A-Z]/g, '');
    if (explicitSaveDc) return 'DC ' + explicitSaveDc;
    if (saveAbility) return String(saveAbility).toUpperCase().replace(/[^A-Z]/g, '') + ' save';
    return '';
  }

  function _spellDamageText(spell) {
    const card = spell && spell.card ? spell.card : spell;
    const current = card && card.current ? card.current : {};
    const damage = _firstText(
      current && current.formula,
      card && card.damage_dice,
      card && card.damage,
      card && card.damage_formula,
      card && card.base_damage_formula,
      spell && spell.damage_dice,
      spell && spell.damage,
      spell && spell.damage_formula,
      spell && spell.base_damage_formula,
      ''
    );
    const type = _firstText(card && card.damage_type, card && card.damageType, spell && spell.damage_type, spell && spell.damageType, '');
    return damage && damage !== '—' ? (damage + (type && !String(damage).toLowerCase().includes(String(type).toLowerCase()) ? ' ' + type : '')) : '';
  }

  function _spellInfoSummary(spell) {
    const card = spell && spell.card ? spell.card : spell;
    const current = card && card.current ? card.current : {};
    const text = _firstText(current && current.effect, card && card.base_effect_text, card && card.effect, card && card.description, spell && spell.base_effect_text, spell && spell.effect, spell && spell.description, 'Open for spell details');
    return text.length > 150 ? text.slice(0, 147) + '…' : text;
  }

  function _spellCastTimeText(spell) {
    const card = spell && spell.card ? spell.card : spell;
    return _firstText(card && card.casting_time, card && card.castingTime, spell && spell.casting_time, spell && spell.castingTime, '1 action');
  }

  function _spellRangeText(spell) {
    const card = spell && spell.card ? spell.card : spell;
    return _firstText(card && card.range, spell && spell.range, '');
  }

  function _spellQuickScore(spell) {
    const attackKind = _spellAttackKind(spell);
    const damage = _spellDamageText(spell);
    const save = _spellSaveText(spell, _runtime());
    const cast = _spellCastTimeText(spell).toLowerCase();
    let score = 0;
    if (attackKind === 'spell') score += 60;
    if (damage) score += 30;
    if (save) score += 18;
    if (/bonus action|reaction/.test(cast)) score += 12;
    if (_spellLevel(spell) === 0) score += 8;
    return score;
  }

  function _spellCandidates(runtime) {
    let spells = [];
    if (typeof global.getCombatQuickBarSpells === 'function') {
      spells = global.getCombatQuickBarSpells() || [];
    } else if (typeof global._getCombatQuickSpells === 'function') {
      spells = global._getCombatQuickSpells() || [];
    } else {
      const sheet = runtime && runtime.charSheet ? runtime.charSheet : {};
      spells = _safeArray(sheet.rulesSpellCards || sheet.rulesSpellbook || sheet.spellbookEntries);
    }
    return _uniqueByName(spells, spells.length).sort(function (a, b) {
      const scoreDelta = _spellQuickScore(b) - _spellQuickScore(a);
      if (scoreDelta) return scoreDelta;
      return ((_spellLevel(a) ?? 99) - (_spellLevel(b) ?? 99));
    });
  }

  function _decorateSpell(spell, runtime) {
    const card = spell && spell.card ? spell.card : spell;
    const level = _spellLevel(spell);
    const needsSlot = _spellNeedsSlot(spell);
    const available = _spellAvailable(spell, runtime);
    const concentration = /concentration/i.test(_firstText(card && card.duration, card && card.base_effect_text, card && card.description, spell && spell.duration));
    const attackText = _spellAttackText(spell, runtime);
    const attackKind = _spellAttackKind(spell);
    const damageText = _spellDamageText(spell);
    const saveText = _spellSaveText(spell, runtime);
    const rangeText = _spellRangeText(spell);
    const castTimeText = _spellCastTimeText(spell);
    return Object.assign({}, spell, {
      quickBarType: 'spell',
      quickBarLane: level === 0 ? 'cantrip' : 'spell',
      quickBarLevelUnknown: level === null,
      quickBarPickKey: _candidateKey('spell', spell),
      quickBarSlotSummary: _spellSlotSummary(spell, runtime),
      quickBarNeedsSlot: needsSlot,
      quickBarCanUse: available,
      quickBarDisabledReason: available ? '' : 'Needs spell slot',
      quickBarConcentration: concentration,
      quickBarAttackKind: attackKind,
      quickBarAttackText: attackText,
      quickBarDamageText: damageText,
      quickBarSaveText: saveText,
      quickBarRangeText: rangeText,
      quickBarCastTimeText: castTimeText,
      quickBarInfoSummary: _spellInfoSummary(spell),
    });
  }

  function _topSpells(runtime, limit) {
    return _spellCandidates(runtime).slice(0, limit || QUICK_PICK_LIMIT).map(function (spell) { return _decorateSpell(spell, runtime); });
  }

  function _resourceRows(model) {
    return _uniqueByName(_safeArray(model.resources), 4).map(function (resource) {
      const current = Number(resource && resource.current);
      const max = Number(resource && resource.max);
      const limited = Number.isFinite(current) && Number.isFinite(max) && max > 0;
      return Object.assign({}, resource, {
        quickBarType: 'resource',
        quickBarCanUse: !limited || current > 0,
        quickBarDisabledReason: limited && current <= 0 ? 'Out of uses' : '',
        quickBarUsesText: limited ? (current + '/' + max) : _firstText(resource && resource.summary, 'Tracked'),
      });
    });
  }

  function selectQuickActions(charData) {
    const runtime = _runtime();
    const sheet = charData || runtime.charSheet || {};
    const actionModel = global.ActionsTab && typeof global.ActionsTab.buildQuickActionModel === 'function'
      ? global.ActionsTab.buildQuickActionModel(sheet)
      : { primaryActions: [], bonusActions: [], reactions: [], resources: [], concentration: null, _allActions: [] };
    const usedState = _readUsedThisTurn(runtime);
    const picks = readQuickPicks(runtime);
    const pickSet = new Set(picks);
    function mark(items, kind) {
      return _safeArray(items).map(function (item) {
        const key = _firstText(item && item.id, item && item.name);
        const pickKey = _candidateKey(kind || (item && item.quickBarType === 'spell' ? 'spell' : 'action'), item);
        return Object.assign({}, item, {
          quickBarPickKey: item && item.quickBarPickKey ? item.quickBarPickKey : pickKey,
          quickBarPinned: pickSet.has(pickKey),
          quickBarUsedThisTurn: !!(key && usedState.used[key]),
        });
      });
    }
    const allActions = mark(_uniqueByName(actionModel._allActions || [], (actionModel._allActions || []).length), 'action');
    const allSpells = mark(_spellCandidates(runtime).map(function (spell) { return _decorateSpell(spell, runtime); }), 'spell');
    const pickedActions = [];
    const pickedSpells = [];
    if (picks.length) {
      picks.forEach(function (pick) {
        const pool = pick.indexOf('spell:') === 0 ? allSpells : allActions;
        const found = pool.find(function (item) { return item.quickBarPickKey === pick; });
        if (!found) return;
        if (pick.indexOf('spell:') === 0) pickedSpells.push(found);
        else pickedActions.push(found);
      });
    }
    const primary = picks.length ? pickedActions.filter(function (item) { return String(item.quickBarLane || '').toLowerCase() !== 'bonus' && String(item.quickBarLane || '').toLowerCase() !== 'reaction'; }) : mark(_uniqueByName(actionModel.primaryActions, 2), 'action');
    const bonus = picks.length ? pickedActions.filter(function (item) { return String(item.quickBarLane || '').toLowerCase() === 'bonus'; }) : mark(_uniqueByName(actionModel.bonusActions, 2), 'action');
    const reactions = picks.length ? pickedActions.filter(function (item) { return String(item.quickBarLane || '').toLowerCase() === 'reaction'; }) : mark(_uniqueByName(actionModel.reactions, 2), 'action');
    return {
      primaryActions: mark(primary, 'action'),
      bonusActions: mark(bonus, 'action'),
      reactions: mark(reactions, 'action'),
      topSpells: picks.length ? mark(pickedSpells, 'spell') : mark(_topSpells(runtime, QUICK_PICK_LIMIT), 'spell'),
      resources: _resourceRows(actionModel),
      concentration: actionModel.concentration || (runtime.charSheet && runtime.charSheet.activeConcentration) || null,
      combat: runtime.combat || { active: false },
      selectedTargetId: runtime.selectedTargetId || '',
      allActions: allActions,
      allSpells: allSpells,
      quickPicks: picks,
      quickPickLimit: QUICK_PICK_LIMIT,
    };
  }

  global.CombatQuickSelectors = {
    selectQuickActions: selectQuickActions,
    markUsed: markUsed,
    readQuickPicks: readQuickPicks,
    writeQuickPicks: writeQuickPicks,
    toggleQuickPick: toggleQuickPick,
    quickPickLimit: QUICK_PICK_LIMIT,
  };
}(window));
