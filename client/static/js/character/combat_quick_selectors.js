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

  function _slugKey(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/::cast-?\d+::?$/i, '')
      .replace(/::(?:slot|level|lvl)-?\d+::?$/i, '')
      .replace(/(?:::|:|-)(?:cast|slot|level|lvl)-?\d+$/i, '')
      .replace(/(?:::|:)\d+$/i, '')
      .replace(/\s+\bL[1-9]\b$/i, '')
      .replace(/\s+\((?:cast|slot|level|lvl)\s*[1-9]\)$/i, '')
      .replace(/[^a-z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function _canonicalSpellKey(spell) {
    const card = spell && spell.card ? spell.card : {};
    return _slugKey(_firstText(
      spell && spell.spellId,
      card && card.id,
      spell && spell.baseSpellId,
      spell && spell.base_spell_id,
      spell && spell.name,
      spell && spell.displayName
    ));
  }

  function _candidateKey(kind, item) {
    if (String(kind || '').toLowerCase() === 'spell' || (item && item.quickBarType === 'spell')) {
      return 'spell:' + _canonicalSpellKey(item);
    }
    return String(kind || 'action') + ':' + _firstText(item && item.id, item && item.name);
  }

  // Names that are section headings / bookkeeping rows leaking out of the
  // character sheet's feature or spellbook parsers — never real quick actions.
  function _isHeadingOrBookkeepingName(name) {
    const clean = String(name || '').replace(/\[[^\]]+\]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
    if (!clean) return true;
    if (/^(?:cantrip|\d+(?:st|nd|rd|th))-level spells?$/.test(clean)) return true;
    if (/^\d+(?:st|nd|rd|th)-level spell slots?$/.test(clean)) return true;
    if (/^cantrips?(?: known)?$/.test(clean)) return true;
    if (/^spells? known\b/.test(clean)) return true;
    if (/^spell slots?\b/.test(clean)) return true;
    if (clean === 'spellcasting') return true;
    if (clean === 'metamagic') return true;
    if (clean === 'subclass feature' || clean === 'subclass features') return true;
    if (clean === 'class feature' || clean === 'class features') return true;
    if (clean === 'ability score improvement') return true;
    if (/spellcasting progression/.test(clean)) return true;
    return false;
  }

  // Canonical filter: only actions a player can actually click/cast/use belong
  // in the Quick Actions surface (default lanes or the Customize Top 5 picker).
  function isPlayableQuickAction(action) {
    if (!action || typeof action !== 'object') return false;
    const id = _firstText(action.id, action.name);
    const name = _firstText(action.name, action.displayName);
    if (!id || !name) return false;
    if (_isHeadingOrBookkeepingName(name)) return false;

    const isSpell = action.quickBarType === 'spell' || action.category === 'Spell';
    if (isSpell) return true;

    const kind = action.quickBarKind;
    if (kind === 'passive' || kind === 'subclass_gate') return false;

    const source = String(action.source || '').toLowerCase();
    if (source === 'feature-fallback') return false;

    // attack / save_effect / transformation / use are all backed by a real
    // activation (roll attack, roll save, transform, spend resource/use item).
    return kind === 'attack' || kind === 'save_effect' || kind === 'transformation' || kind === 'use';
  }

  function _categoryFor(item) {
    if (!item) return 'Utility';
    if (item.quickBarType === 'spell') return 'Spell';
    const lane = String(item.quickBarLane || '').toLowerCase();
    if (lane === 'bonus') return 'Bonus Action';
    if (lane === 'reaction') return 'Reaction';
    const source = String(item.source || '').toLowerCase();
    const kind = item.quickBarKind;
    if (source === 'weapon' || source === 'equip_only' || source === 'system_unarmed' || kind === 'attack') return 'Attack';
    if (/item/.test(source)) return 'Item';
    const resourceState = item.quickBarResourceState;
    if (resourceState && Number.isFinite(Number(resourceState.max)) && Number(resourceState.max) > 0) return 'Limited Use';
    if (source === 'native_action' || source === 'custom_druid_action') return 'Class Feature';
    return 'Utility';
  }

  function _normalizeActionCandidate(item) {
    const category = _categoryFor(item);
    const executableType = item.quickBarKind === 'attack' ? 'roll_attack'
      : item.quickBarKind === 'save_effect' ? 'roll_save'
      : item.quickBarKind === 'transformation' ? 'transform'
      : 'use_action';
    const economy = Array.isArray(item.quickBarEconomy) ? item.quickBarEconomy[0] : item.quickBarEconomy;
    return Object.assign({}, item, {
      category: category,
      type: category,
      sourceType: _firstText(item.sourceType, item.source, 'action'),
      actionType: _firstText(item.actionType, economy, item.quickBarLane, 'action'),
      cost: _firstText(item.cost, economy, 'action'),
      resourceCost: _firstText(item.resourceName, item.resourceSummary, '') || null,
      limitedUse: !!(item.quickBarResourceState && Number.isFinite(Number(item.quickBarResourceState.max)) && Number(item.quickBarResourceState.max) > 0),
      castLevel: null,
      spellId: null,
      itemId: /item/.test(String(item.source || '').toLowerCase()) ? _firstText(item.id, item.name) : null,
      featureId: _firstText(item.featureId, item.sourceFeatureId, ''),
      executableType: executableType,
      preview: _firstText(item.quickBarDamageText, item.quickBarSlotSummary, item.summary, item.description, ''),
      sortKey: category + '::' + String(_firstText(item.name, '')).toLowerCase(),
    });
  }

  function _normalizeSpellCandidate(spell, runtime) {
    return _canonicalSpellDisplayCandidate(spell, runtime);
  }

  // De-duplicate by what the action actually *does*, not just its label, so
  // e.g. "Scorching Ray" cast at the same slot level merges into one row while
  // a weapon-charge variant of the same spell name stays distinct.
  function _executableIdentity(candidate) {
    const name = String(_firstText(candidate.name, '')).toLowerCase();
    if (candidate.category === 'Spell') {
      const key = _canonicalSpellKey(candidate);
      if (candidate.sourceType === 'item') return 'spell::' + key + '::item::' + String(candidate.itemId || candidate.sourceItemId || candidate.source || '').toLowerCase();
      if (candidate.featureId) return 'spell::' + key + '::feature::' + String(candidate.featureId).toLowerCase();
      return 'spell::' + key + '::slot-spell';
    }
    return String(candidate.category) + '::' + name + '::' + String(candidate.sourceType || candidate.source || '').toLowerCase() + '::' + String(candidate.actionType || '').toLowerCase();
  }

  // Builds the clean, deduplicated candidate list shown in the Customize Top 5
  // picker. Anything that fails isPlayableQuickAction never reaches the UI.
  function buildQuickActionCandidates(runtimeOverride) {
    const runtime = runtimeOverride || _runtime();
    const sheet = runtime.charSheet || {};
    const actionModel = global.ActionsTab && typeof global.ActionsTab.buildQuickActionModel === 'function'
      ? global.ActionsTab.buildQuickActionModel(sheet)
      : { _allActions: [] };
    const rawActions = _safeArray(actionModel._allActions);
    const rawSpells = _spellCandidates(runtime).map(function (spell) { return _decorateSpell(spell, runtime); });

    const normalized = [];
    rawActions.forEach(function (item) {
      if (!isPlayableQuickAction(item)) return;
      normalized.push(_normalizeActionCandidate(item));
    });
    rawSpells.forEach(function (spell) {
      if (!isPlayableQuickAction(spell)) return;
      normalized.push(_normalizeSpellCandidate(spell, runtime));
    });

    const byIdentity = new Map();
    normalized.forEach(function (candidate) {
      const identity = _executableIdentity(candidate);
      if (!byIdentity.has(identity)) byIdentity.set(identity, candidate);
    });
    return Array.from(byIdentity.values()).sort(function (a, b) {
      return a.sortKey < b.sortKey ? -1 : a.sortKey > b.sortKey ? 1 : 0;
    });
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

  function _canonicalQuickPickKey(pickKey) {
    const raw = String(pickKey || '').trim();
    if (!raw) return '';
    if (raw.indexOf('spell:') === 0) {
      return 'spell:' + _slugKey(raw.slice(6).replace(/^spell-/, ''));
    }
    return raw;
  }

  function toggleQuickPickKey(pickKey) {
    const runtime = _runtime();
    const key = _canonicalQuickPickKey(pickKey);
    if (!key || /:$/.test(key)) return readQuickPicks(runtime);
    const picks = readQuickPicks(runtime).map(_canonicalQuickPickKey);
    const existing = picks.indexOf(key);
    if (existing >= 0) { picks.splice(existing, 1); return writeQuickPicks(picks, runtime); }
    if (picks.length >= QUICK_PICK_LIMIT) return picks;
    picks.push(key);
    return writeQuickPicks(picks, runtime);
  }

  function toggleQuickPick(kind, item) {
    const runtime = _runtime();
    const key = _candidateKey(kind, item);
    if (!key || /:$/.test(key)) return readQuickPicks(runtime);
    const picks = readQuickPicks(runtime);
    const existing = picks.indexOf(key);
    if (existing >= 0) { picks.splice(existing, 1); return writeQuickPicks(picks, runtime); }
    // At the limit: refuse the add instead of silently bumping an existing
    // pick. The UI disables unpicked rows once 5/5 are selected.
    if (picks.length >= QUICK_PICK_LIMIT) return picks;
    picks.push(key);
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

  function _baseSpellLevelForQuickAction(spell) {
    const card = spell && spell.card ? spell.card : {};
    return _parseSpellLevelText(spell && (spell.baseLevel ?? spell.base_level ?? spell.spell_level), card && (card.level ?? card.spell_level));
  }

  function _spellLevel(spell) {
    const card = spell && spell.card ? spell.card : {};
    const explicit = _baseSpellLevelForQuickAction(spell);
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

  function _slotRemaining(runtime, level) {
    const slots = runtime && runtime.spellSlots ? runtime.spellSlots : {};
    const used = runtime && runtime.spellSlotState ? runtime.spellSlotState : {};
    const max = Number(slots[level] ?? slots[String(level)] ?? 0) || 0;
    const spent = Number(used[level] ?? used[String(level)] ?? 0) || 0;
    return { max: max, spent: spent, remaining: Math.max(0, max - spent) };
  }

  function _availableCastLevels(spell, runtime) {
    const level = _spellLevel(spell);
    if (level === null) return [];
    if (level === 0) return [0];
    const out = [];
    for (let lvl = level; lvl <= 9; lvl += 1) {
      if (_slotRemaining(runtime, lvl).remaining > 0) out.push(lvl);
    }
    return out;
  }

  function _spellSlotSummary(spell, runtime) {
    const level = _spellLevel(spell);
    if (level === null) return 'Unknown spell level';
    if (level === 0) return 'Cantrip';
    const rows = [];
    for (let lvl = level; lvl <= 9; lvl += 1) {
      const slot = _slotRemaining(runtime, lvl);
      if (slot.max > 0) rows.push('L' + lvl + ' ' + slot.remaining + '/' + slot.max);
    }
    if (!rows.length || !rows.some(function (row) { return /\s[1-9]\d*\//.test(row); })) return 'No slots';
    return rows.slice(0, 4).join(' · ') + (rows.length > 4 ? ' · +' : '');
  }

  function _spellAvailable(spell, runtime) {
    const level = _spellLevel(spell);
    if (level === null) return true;
    if (level === 0) return true;
    for (let lvl = level; lvl <= 9; lvl += 1) {
      if (_slotRemaining(runtime, lvl).remaining > 0) return true;
    }
    return false;
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
      const sheetRuntime = sheet.characterSheetRuntime || sheet.sheetRuntime || {};
      spells = _safeArray(sheetRuntime.spells).length || _safeArray(sheetRuntime.itemSpells).length
        ? _safeArray(sheetRuntime.spells).concat(_safeArray(sheetRuntime.itemSpells))
        : _safeArray(sheet.rulesSpellCards || sheet.rulesSpellbook || sheet.spellbookEntries);
    }
    // Reject spell-level section headings / non-castable rows before they
    // ever reach scoring, sorting, or the Customize Top 5 picker.
    spells = spells.concat(_itemSpellRows());
    spells = spells.filter(function (spell) { return isPlayableQuickAction(Object.assign({ quickBarType: 'spell' }, spell)); });
    const bySpell = new Map();
    spells.forEach(function (spell) {
      const candidate = _canonicalSpellDisplayCandidate(spell, runtime);
      const identity = _executableIdentity(candidate);
      if (!bySpell.has(identity)) bySpell.set(identity, candidate);
    });
    return Array.from(bySpell.values()).sort(function (a, b) {
      const scoreDelta = _spellQuickScore(b) - _spellQuickScore(a);
      if (scoreDelta) return scoreDelta;
      return ((_spellLevel(a) ?? 99) - (_spellLevel(b) ?? 99));
    });
  }

  function _canonicalSpellDisplayCandidate(spell, runtime) {
    const card = spell && spell.card ? spell.card : spell;
    const key = _canonicalSpellKey(spell);
    const level = _spellLevel(spell);
    const sourceType = _firstText(spell && spell.sourceType, spell && spell.source, 'class');
    const itemSourceId = _firstText(spell && spell.sourceItemId, spell && spell.itemId, card && card.item_id, spell && spell.sourceVariantId, '');
    return Object.assign({}, spell, {
      id: key,
      spellId: key,
      name: _firstText(spell && spell.name, spell && spell.displayName, card && card.name, key),
      baseLevel: level,
      spell_level: level,
      castLevel: null,
      slotLevel: null,
      availableCastLevels: _availableCastLevels(spell, runtime),
      category: 'Spell',
      type: 'Spell',
      quickBarType: 'spell',
      quickBarPickKey: spell && spell.quickBarPickKey ? spell.quickBarPickKey : (sourceType === 'item' ? ('spell:item:' + _slugKey(itemSourceId) + ':' + key) : 'spell:' + key),
      actionType: 'spell',
      cost: _firstText(spell && spell.quickBarCastTimeText, '1 action'),
      resourceCost: _firstText(spell && spell.quickBarSlotSummary, '') || null,
      limitedUse: !!(level && level > 0),
      executableType: 'cast_spell',
      preview: _firstText(spell && spell.quickBarDamageText, spell && spell.quickBarSaveText, spell && spell.quickBarInfoSummary, ''),
      sortKey: 'Spell::' + String(_firstText(spell && spell.name, '')).toLowerCase(),
      sourceType: sourceType,
      itemId: sourceType === 'item' ? itemSourceId : null,
      featureId: _firstText(spell && spell.featureId, spell && spell.sourceFeatureId, ''),
    });
  }

  function _decorateSpell(spell, runtime) {
    spell = _canonicalSpellDisplayCandidate(spell, runtime);
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
    const sourceLabel = spell.sourceType === 'item'
      ? ('Source: ' + _firstText(spell.sourceItemName, spell.itemName, spell.sourceName, 'Magic Item'))
      : spell.featureId ? 'Class Feature' : 'Character Spell';
    return Object.assign({}, spell, {
      quickBarType: 'spell',
      quickBarSourceLabel: sourceLabel,
      quickBarLane: level === 0 ? 'cantrip' : 'spell',
      quickBarLevelUnknown: level === null,
      quickBarPickKey: _candidateKey('spell', spell),
      quickBarSlotSummary: _spellSlotSummary(spell, runtime),
      quickBarNeedsSlot: needsSlot,
      quickBarCanUse: available,
      quickBarDisabledReason: available ? '' : 'No spell slots available',
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

  // Generic mapping of any equipped/attuned magic item's granted actions and
  // spells (server-built `_playerItemActions` / `_playerItemSpellCards`) into
  // Quick-Bar-compatible rows. Works for any item — never keyed off a name.
  function _itemActionRows() {
    return _safeArray(global._playerItemActions).map(function (itemAction, idx) {
      const activation = String(itemAction && itemAction.activation_type || 'action').toLowerCase();
      const lane = activation === 'bonus_action' ? 'bonus' : activation === 'reaction' ? 'reaction' : 'action';
      const hasCurrentCharges = itemAction && itemAction.charges_current !== null && itemAction.charges_current !== undefined && Number.isFinite(Number(itemAction.charges_current));
      const hasMaxCharges = itemAction && itemAction.charges_max !== null && itemAction.charges_max !== undefined && Number.isFinite(Number(itemAction.charges_max));
      const hasQty = itemAction && itemAction.quantity !== null && itemAction.quantity !== undefined && Number.isFinite(Number(itemAction.quantity));
      const itemName = _firstText(itemAction && itemAction.item_name, 'Magic Item');
      const id = String((itemAction && itemAction.action_id) || (itemAction && itemAction.item_id) || ('item_action_' + idx));
      return {
        id: id,
        name: _firstText(itemAction && itemAction.action_name, itemAction && itemAction.item_name, 'Item Action'),
        source: 'item_action',
        sourceType: 'item_action',
        sourceName: itemName,
        itemName: itemName,
        quickBarSourceLabel: itemName,
        quickBarType: 'action',
        quickBarLane: lane,
        quickBarPickKey: 'action:' + id,
        quickBarAttackText: itemAction && itemAction.attack_bonus != null ? _formatSignedNumber(itemAction.attack_bonus) : '',
        quickBarDamageText: _firstText(itemAction && itemAction.damage_formula, ''),
        quickBarRangeText: _firstText(itemAction && itemAction.range, ''),
        quickBarResourceState: (hasCurrentCharges || hasMaxCharges) ? { remaining: hasCurrentCharges ? Number(itemAction.charges_current) : null, max: hasMaxCharges ? Number(itemAction.charges_max) : null } : null,
        quickBarUsesText: (!hasCurrentCharges && !hasMaxCharges && hasQty) ? ('Qty ' + Number(itemAction.quantity)) : '',
        quickBarCanUse: !(itemAction && itemAction.disabled),
        quickBarDisabledReason: _firstText(itemAction && itemAction.disabled_reason, ''),
        quickBarInfoSummary: _firstText(itemAction && itemAction.effect_text, 'Open for details'),
      };
    });
  }

  function _itemSpellRows() {
    return _safeArray(global._playerItemSpellCards).map(function (card, idx) {
      const itemName = _firstText(card && card.item_name, 'Magic Item');
      const id = 'item_spell_' + idx + '_' + String((card && card.item_id) || '') + '_' + String((card && card.spell_id) || '');
      const hasCurrentCharges = card && card.charges_current !== null && card.charges_current !== undefined && Number.isFinite(Number(card.charges_current));
      const hasMaxCharges = card && card.charges_max !== null && card.charges_max !== undefined && Number.isFinite(Number(card.charges_max));
      const chargeCost = Number((card && card.charge_cost) || 0);
      const variableMin = card && Number.isFinite(Number(card.charge_cost_min)) ? Number(card.charge_cost_min) : null;
      const variableMax = card && Number.isFinite(Number(card.charge_cost_max)) ? Number(card.charge_cost_max) : null;
      const isVariableCost = variableMin !== null && variableMax !== null && variableMax > variableMin;
      const chargeCostText = isVariableCost
        ? ('Costs ' + variableMin + '-' + variableMax + ' charges')
        : (chargeCost > 0 ? ('Costs ' + chargeCost + ' charge' + (chargeCost !== 1 ? 's' : '')) : '');
      const dcText = card && card.uses_item_dc && Number(card.item_spell_save_dc) > 0 ? ('DC ' + Number(card.item_spell_save_dc)) : '';
      const atkText = card && card.uses_item_attack_bonus && Number(card.item_spell_attack_bonus) !== 0 ? _formatSignedNumber(card.item_spell_attack_bonus) : '';
      const spellLevel = card && Number.isFinite(Number(card.level)) ? Number(card.level) : null;
      return {
        id: id,
        name: _firstText(card && card.spell_name, card && card.spell_id, 'Item Spell'),
        source: 'item',
        sourceType: 'item',
        sourceName: itemName,
        sourceItemName: itemName,
        itemName: itemName,
        sourceItemId: String((card && card.item_id) || ''),
        quickBarSourceLabel: 'Source: ' + itemName,
        quickBarType: 'spell',
        quickBarLane: 'spell',
        quickBarPickKey: 'spell:item:' + String((card && card.item_id) || '').toLowerCase().replace(/[^a-z0-9]+/g, '-') + ':' + String((card && card.spell_id) || '').toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        quickBarAttackKind: atkText ? 'spell' : '',
        quickBarAttackText: atkText,
        quickBarSaveText: dcText,
        quickBarDamageText: _firstText(card && card.damage_formula, ''),
        quickBarRangeText: _firstText(card && card.range, ''),
        quickBarResourceState: (hasCurrentCharges || hasMaxCharges) ? { remaining: hasCurrentCharges ? Number(card.charges_current) : null, max: hasMaxCharges ? Number(card.charges_max) : null } : null,
        quickBarUsesText: chargeCostText,
        quickBarCanUse: !(card && card.disabled),
        quickBarDisabledReason: _firstText(card && card.disabled_reason, ''),
        quickBarInfoSummary: _firstText(card && card.description, 'Open for spell details'),
        quickBarVariableChargeCost: isVariableCost,
        quickBarChargeCostMin: variableMin,
        quickBarChargeCostMax: variableMax,
        spellLevel: spellLevel,
        itemId: String((card && card.item_id) || ''),
        itemIndex: Number((card && card.item_index) || 0),
        spellId: String((card && card.spell_id) || ''),
        usesItemCharges: chargeCost > 0,
        usesCharges: chargeCost > 0,
        chargeCost: chargeCost,
        castLevel: Number((card && card.cast_level) || 0),
        baseLevel: spellLevel,
        level: spellLevel,
        card: Object.assign({}, card || {}, { id: String((card && card.spell_id) || ''), spellId: String((card && card.spell_id) || ''), name: _firstText(card && card.spell_name, card && card.spell_id, 'Item Spell'), level: spellLevel, spell_level: spellLevel, damage_formula: _firstText(card && card.damage_formula, ''), damage: _firstText(card && card.damage_formula, ''), damage_type: _firstText(card && card.damage_type, ''), attack_bonus: atkText, save_dc: card && card.item_spell_save_dc, range: _firstText(card && card.range, ''), casting_time: _firstText(card && card.casting_time, '1 Action') }),
      };
    });
  }

  function _normalizeInlineMagicItemAction(item, itemIndex, raw, actionIndex, kind) {
    if (!raw || typeof raw !== 'object') return null;
    const itemName = _firstText(item && item.name, raw.item_name, 'Magic Item');
    const actionName = _firstText(raw.name, raw.action_name, raw.label, raw.spell_name, raw.effect_name, itemName + ' Action');
    const actionId = _firstText(raw.id, raw.action_id, raw.spell_id, raw.slug, kind + '_' + itemIndex + '_' + actionIndex);
    const activation = _firstText(raw.activation, raw.activation_type, raw.actionType, raw.cost, raw.casting_time, 'action').toLowerCase();
    const lane = /bonus/.test(activation) ? 'bonus' : (/reaction/.test(activation) ? 'reaction' : (/spell/.test(kind) ? 'spell' : 'action'));
    const current = raw.charges_current ?? raw.chargesCurrent ?? item.charges_current ?? item.chargesCurrent ?? item.charges?.current ?? item.uses?.remaining ?? item.uses?.current;
    const max = raw.charges_max ?? raw.chargesMax ?? item.charges_max ?? item.chargesMax ?? item.charges?.max ?? item.uses?.max;
    const hasCurrent = current !== null && current !== undefined && Number.isFinite(Number(current));
    const hasMax = max !== null && max !== undefined && Number.isFinite(Number(max));
    const damage = _firstText(raw.damage_formula, raw.damageFormula, raw.damage_dice, raw.damage, raw.formula, '');
    const saveDc = _firstText(raw.save_dc, raw.saveDC, raw.dc, item.save_dc, item.saveDC, '');
    const saveAbility = _firstText(raw.save_ability, raw.saveAbility, raw.save, raw.savingThrow, '');
    const attackBonus = _firstText(raw.attack_bonus, raw.attackBonus, raw.to_hit, '');
    const isSpellLike = /spell/i.test(kind) || raw.spell_id || raw.spell_name || raw.spellLevel || raw.spell_level;
    const base = {
      id: String(actionId),
      name: actionName,
      source: isSpellLike ? 'item' : 'item_action',
      sourceType: isSpellLike ? 'item' : 'item_action',
      sourceName: itemName,
      sourceItemName: itemName,
      itemName: itemName,
      itemId: _firstText(item.id, item.item_id, String(itemIndex)),
      sourceItemId: _firstText(item.id, item.item_id, String(itemIndex)),
      itemIndex: itemIndex,
      quickBarSourceLabel: 'Source: ' + itemName,
      quickBarType: isSpellLike ? 'spell' : 'action',
      quickBarLane: lane,
      quickBarPickKey: (isSpellLike ? 'spell:item:' : 'action:item:') + String(_firstText(item.id, itemName, itemIndex)).toLowerCase().replace(/[^a-z0-9]+/g, '-') + ':' + String(actionId).toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      quickBarAttackText: attackBonus,
      quickBarSaveText: [saveDc ? ('DC ' + saveDc) : '', saveAbility].filter(Boolean).join(' '),
      quickBarDamageText: damage,
      quickBarRangeText: _firstText(raw.range, raw.reach, ''),
      quickBarResourceState: (hasCurrent || hasMax) ? { remaining: hasCurrent ? Number(current) : null, max: hasMax ? Number(max) : null } : null,
      quickBarUsesText: _firstText(raw.usesText, raw.uses_text, raw.charge_cost ? ('Costs ' + raw.charge_cost + ' charge' + (Number(raw.charge_cost) === 1 ? '' : 's')) : '', ''),
      quickBarCanUse: raw.disabled !== true,
      quickBarDisabledReason: _firstText(raw.disabled_reason, ''),
      quickBarInfoSummary: _firstText(raw.effect_text, raw.summary, raw.description, raw.effect, 'Open for details'),
      damage_formula: damage,
      damage_type: _firstText(raw.damage_type, raw.damageType, ''),
      save_dc: saveDc,
      attack_bonus: attackBonus,
    };
    if (isSpellLike) {
      const spellLevel = Number.isFinite(Number(raw.level ?? raw.spell_level ?? raw.spellLevel)) ? Number(raw.level ?? raw.spell_level ?? raw.spellLevel) : null;
      base.spellLevel = spellLevel;
      base.level = spellLevel;
      base.baseLevel = spellLevel;
      base.spellId = _firstText(raw.spell_id, raw.id, actionId);
      base.usesCharges = !!raw.charge_cost;
      base.chargeCost = Number(raw.charge_cost || 0);
      base.card = Object.assign({}, raw, { id: base.spellId, spellId: base.spellId, name: actionName, level: spellLevel, spell_level: spellLevel, damage_formula: damage, damage: damage, damage_type: base.damage_type, attack_bonus: attackBonus, save_dc: saveDc, range: base.quickBarRangeText, casting_time: _firstText(raw.casting_time, raw.activation, '1 Action') });
    }
    return base;
  }

  function _inlineMagicItemRows(charData) {
    const rows = [];
    _safeArray(charData && charData.inventory).forEach(function (item, itemIndex) {
      if (!item || typeof item !== 'object') return;
      [
        ['actions', item.actions], ['chargedActions', item.chargedActions], ['magicActions', item.magicActions], ['effects', item.effects], ['spells', item.spells]
      ].forEach(function (pair) {
        _safeArray(pair[1]).forEach(function (raw, actionIndex) {
          const row = _normalizeInlineMagicItemAction(item, itemIndex, raw, actionIndex, pair[0]);
          if (row) rows.push(row);
        });
      });
    });
    return rows;
  }

  function _magicItemActionRows(charData) {
    return _itemActionRows().concat(_itemSpellRows()).concat(_inlineMagicItemRows(charData || {}));
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
    const picks = readQuickPicks(runtime).map(_canonicalQuickPickKey);
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
    const playableRawActions = _safeArray(actionModel._allActions).filter(isPlayableQuickAction);
    const allActions = mark(_uniqueByName(playableRawActions, playableRawActions.length), 'action');
    const allSpells = mark(_spellCandidates(runtime).map(function (spell) { return _decorateSpell(spell, runtime); }), 'spell');
    const pickedActions = [];
    const pickedSpells = [];
    const invalidPicks = [];
    function disabledSavedPick(pick) {
      const label = pick.indexOf('spell:') === 0 ? pick.slice(6).replace(/-/g, ' ') : pick.replace(/^[^:]+:/, '').replace(/-/g, ' ');
      return { id: pick, name: label || 'Saved quick pick', quickBarPickKey: pick, quickBarPinned: true, quickBarCanUse: false, quickBarDisabledReason: 'Saved pick is not currently available', quickBarType: pick.indexOf('spell:') === 0 ? 'spell' : 'action', category: pick.indexOf('spell:') === 0 ? 'Spell' : 'Utility' };
    }
    if (picks.length) {
      picks.forEach(function (rawPick) {
        const pick = _canonicalQuickPickKey(rawPick);
        const pool = pick.indexOf('spell:') === 0 ? allSpells : allActions;
        let found = pool.find(function (item) { return item.quickBarPickKey === pick; });
        if (!found && pick.indexOf('spell:') === 0) {
          const canonical = _canonicalQuickPickKey(pick);
          found = pool.find(function (item) { return _canonicalQuickPickKey(item && item.quickBarPickKey) === canonical; });
        }
        if (!found) {
          invalidPicks.push(pick);
          found = disabledSavedPick(pick);
        }
        if (pick.indexOf('spell:') === 0) pickedSpells.push(found);
        else pickedActions.push(found);
      });
      if (invalidPicks.length && global.console && typeof global.console.warn === 'function') {
        global.console.warn('[CombatQuickSelectors] Saved quick action picks are unavailable but preserved:', invalidPicks);
      }
      if (picks.some(function (pick, idx) { return pick !== readQuickPicks(runtime)[idx]; })) writeQuickPicks(picks, runtime);
    }
    const primary = picks.length ? pickedActions.filter(function (item) { return String(item.quickBarLane || '').toLowerCase() !== 'bonus' && String(item.quickBarLane || '').toLowerCase() !== 'reaction'; }) : mark(_uniqueByName(_safeArray(actionModel.primaryActions).filter(isPlayableQuickAction), 2), 'action');
    const bonus = picks.length ? pickedActions.filter(function (item) { return String(item.quickBarLane || '').toLowerCase() === 'bonus'; }) : mark(_uniqueByName(_safeArray(actionModel.bonusActions).filter(isPlayableQuickAction), 2), 'action');
    const reactions = picks.length ? pickedActions.filter(function (item) { return String(item.quickBarLane || '').toLowerCase() === 'reaction'; }) : mark(_uniqueByName(_safeArray(actionModel.reactions).filter(isPlayableQuickAction), 2), 'action');
    return {
      primaryActions: mark(primary, 'action'),
      bonusActions: mark(bonus, 'action'),
      reactions: mark(reactions, 'action'),
      topSpells: picks.length ? mark(pickedSpells, 'spell') : mark(_topSpells(runtime, QUICK_PICK_LIMIT), 'spell'),
      magicItemActions: mark(_magicItemActionRows(sheet), 'action'),
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
    toggleQuickPickKey: toggleQuickPickKey,
    isPlayableQuickAction: isPlayableQuickAction,
    buildQuickActionCandidates: buildQuickActionCandidates,
    _canonicalSpellKey: _canonicalSpellKey,
    _canonicalQuickPickKey: _canonicalQuickPickKey,
    _baseSpellLevelForQuickAction: _baseSpellLevelForQuickAction,
    _canonicalSpellDisplayCandidate: _canonicalSpellDisplayCandidate,
    _spellAvailable: _spellAvailable,
    _spellSlotSummary: _spellSlotSummary,
    quickPickLimit: QUICK_PICK_LIMIT,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.CombatQuickSelectors;
}(typeof window !== 'undefined' ? window : globalThis));
