(function (global) {
  'use strict';

const KNOWN_RENDER_CHAR_SHEET_CALLERS = new Set([
  'openMyTokenStats',
  'placeCharacter',
  'syncCharacterBookInputs',
  'openCharacterBook',
  'autoFillCharacterBookFromPaste',
  'loadCharacterFromJson',
  'importCharacterBookFromUpload',
  'adjustHp',
  'toggleSpellSlot',
  'updateMyChar',
  'applyCharProfileRecord',
  'legacy-renderCharSheet-shim',
]);

function requestCharacterBookOverviewRender(source = 'unknown') {
  renderCharacterBookOverviewContent();
}


function _prettySheetLabel(raw) {
  return String(raw || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); });
}

function _formatGoldUnits(units) {
  const totalCp = Math.max(0, Math.round(Number(units || 0)));
  const gp = Math.floor(totalCp / 100);
  const sp = Math.floor((totalCp % 100) / 10);
  const cp = totalCp % 10;
  if (gp > 0) return `${gp} gp${sp > 0 ? ` ${sp} sp` : ''}${cp > 0 ? ` ${cp} cp` : ''}`;
  if (sp > 0) return `${sp} sp${cp > 0 ? ` ${cp} cp` : ''}`;
  return `${cp} cp`;
}

function renderCharSheet() {
  requestCharacterBookOverviewRender('legacy-renderCharSheet-shim');
}

function _csrArray(value) { return Array.isArray(value) ? value.filter(Boolean) : []; }
function _csrObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function _csrInt(value, fallback) { const n = parseInt(value, 10); return Number.isFinite(n) ? n : fallback; }
function _csrSlug(value) { return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); }
function _csrName(value) { return String(value || '').replace(/^spell[_-]+/i, '').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); }); }
function _csrFirst() {
  for (let i = 0; i < arguments.length; i += 1) {
    const value = arguments[i];
    if (value === undefined || value === null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return '';
}
function _csrSpellActionType(castingTime) {
  const text = String(castingTime || '').toLowerCase();
  if (text.includes('bonus')) return 'bonus action';
  if (text.includes('reaction')) return 'reaction';
  return 'action';
}
function _csrFeatureKind(feature) {
  const text = `${feature && (feature.name || feature.displayName || '')} ${feature && (feature.type || feature.section || '')}`.toLowerCase();
  if (/feat/.test(text)) return 'feat';
  if (/species|race|trait/.test(text)) return 'trait';
  if (/background/.test(text)) return 'background';
  return 'feature';
}
function _csrResource(id, name, current, max, recovery, source) {
  const safeMax = Math.max(0, _csrInt(max, _csrInt(current, 0)));
  const safeCurrent = Math.max(0, Math.min(safeMax || _csrInt(current, 0), _csrInt(current, safeMax)));
  return {
    id: id || _csrSlug(name),
    name,
    current: safeCurrent,
    max: safeMax,
    recovery: recovery || 'long rest',
    source: source || 'class',
    spendable: true,
    restReset: /short/i.test(recovery || '') ? 'short' : 'long',
    linkedFeatures: [],
    linkedActions: [],
  };
}
function _csrPushUnique(list, row, keyFn) {
  if (!row) return null;
  const key = keyFn ? keyFn(row) : String(row.id || row.name || '').toLowerCase();
  if (!key) return null;
  const existing = list.find(function (entry) { return (keyFn ? keyFn(entry) : String(entry.id || entry.name || '').toLowerCase()) === key; });
  if (existing) return existing;
  list.push(row);
  return row;
}
function _csrBuildSpell(spell, character, source) {
  const name = _csrName(spell && (spell.name || spell.displayName || spell.id)) || 'Spell';
  const id = _csrSlug(spell && (spell.id || name)).replace(/^spell-/, '');
  const rawLevel = spell && (spell.level ?? spell.spell_level ?? spell.spellLevel);
  let level = rawLevel === undefined || rawLevel === null || rawLevel === '' ? null : _csrInt(rawLevel, 0);
  const options = {
    characterLevel: _csrInt(character.totalLevel || character.level, 1),
    castLevel: Math.max(level == null ? 0 : level, _csrInt(spell && (spell.castLevel || spell.slotLevel), level == null ? 0 : level)),
    saveDc: _csrFirst(character.spellSaveDc, _csrObject(character.book).spellSaveDc),
    spellAttackBonus: _csrFirst(character.spellAttack, _csrObject(character.book).spellAttack),
    abilityScores: character.abilities || character.abilityScores || {},
  };
  const resolverCard = Object.assign({}, spell, { id, name });
  if (level != null) resolverCard.level = level;
  const resolved = (global.resolveSpellRuntime ? global.resolveSpellRuntime(resolverCard, options) : {});
  if (level == null) level = _csrInt(resolved.baseLevel, 0);
  const castingTime = _csrFirst(spell && (spell.castingTime || spell.casting_time), resolved.castingTime, '1 action');
  const attack = _csrFirst(spell && (spell.attackType || spell.attack_type), resolved.attackType, '');
  const save = _csrFirst(spell && (spell.savingThrow || spell.saveAbility || spell.save_ability), resolved.savingThrow, resolved.saveAbility, '');
  const formula = _csrFirst(resolved.finalDamageFormula, resolved.finalHealingFormula, spell && (spell.damageFormula || spell.damage || spell.base_damage_formula || spell.healingFormula), '');
  const upcastLevels = [];
  const scalingType = _csrFirst(spell && (spell.scaling_type || spell.scalingType), resolved.scaling_type, resolved.scalingType, '');
  if (level > 0 && scalingType && scalingType !== 'none') {
    for (let slot = level; slot <= 9; slot += 1) upcastLevels.push(slot);
  }
  return {
    id,
    name,
    level,
    spellLevel: level,
    castingTime,
    actionType: _csrSpellActionType(castingTime),
    range: _csrFirst(spell && (spell.range || spell.range_text), resolved.range, ''),
    attackType: attack,
    saveAbility: save,
    saveDc: save ? options.saveDc : '',
    spellAttackBonus: attack ? options.spellAttackBonus : '',
    damageFormula: formula,
    healingFormula: _csrFirst(resolved.finalHealingFormula, spell && spell.healingFormula, ''),
    effectFormula: formula,
    scaling: { type: scalingType || 'none', upcastLevels, resolver: 'resolveSpellRuntime' },
    concentration: !!(spell && (spell.concentration || spell.is_concentration) || resolved.concentration),
    ritual: !!(spell && spell.ritual || resolved.ritual),
    components: _csrFirst(spell && spell.components, resolved.components, ''),
    source: source || _csrFirst(spell && spell.source, 'class'),
    preparation: _csrFirst(spell && (spell.preparation || spell.status), level === 0 ? 'known' : 'known'),
    resolverPreview: resolved,
  };
}
function _csrAction(id, name, actionType, opts) {
  const o = _csrObject(opts);
  return {
    id: id || _csrSlug(name),
    name,
    actionType: actionType || 'action',
    cost: o.cost || actionType || 'action',
    resourceCost: o.resourceCost || null,
    current: o.current ?? null,
    max: o.max ?? null,
    recovery: o.recovery || '',
    roll: o.roll || '',
    effectSummary: o.effectSummary || o.summary || '',
    sourceFeature: o.sourceFeature || '',
    source: o.source || 'feature',
    disabledReason: o.disabledReason || '',
    linkedResources: o.linkedResources || [],
    featureModifiers: o.featureModifiers || [],
  };
}
function buildCharacterSheetRuntime(characterDocument) {
  const doc = _csrObject(characterDocument);
  const native = _csrObject(doc.nativeRuntime || doc.runtime);
  const book = _csrObject(doc.book || doc.charBook);
  const classes = _csrArray(doc.classes);
  const classLine = _csrFirst(doc.className, doc.class, book.className, classes.map(function (c) { return c && c.name; }).filter(Boolean).join(' / '));
  const classKey = classLine.toLowerCase();
  const level = _csrInt(doc.totalLevel || doc.level || book.level || native.levelTotal, 1);
  const sorcererLevel = classes.reduce(function (acc, c) { return /sorcerer/i.test(c && c.name || '') ? Math.max(acc, _csrInt(c.level, level)) : acc; }, /sorcerer/i.test(classKey) ? level : 0);
  const resources = _csrArray(native.resources || doc.nativeResources).map(function (r) {
    return Object.assign(_csrResource(r.id, r.name, r.current ?? r.uses ?? r.remaining, r.max ?? r.limit, r.recovery || r.recharge || r.reset, r.source), r);
  });
  function ensureResource(id, name, current, max, recovery, source) {
    return _csrPushUnique(resources, _csrResource(id, name, current, max, recovery, source), function (r) { return String(r.id || r.name || '').toLowerCase(); });
  }
  if (sorcererLevel) ensureResource('sorcery_points', 'Sorcery Points', doc.sorceryPoints ?? sorcererLevel, sorcererLevel, 'long rest', 'sorcerer');
  const features = [];
  _csrArray(native.classFeatures || doc.nativeClassFeatures || doc.nativeFeatures || doc.features).forEach(function (f) {
    if (typeof f === 'string') f = { name: f };
    const name = _csrFirst(f.name, f.displayName);
    if (!name) return;
    const row = Object.assign({ id: _csrSlug(name), name, source: f.source || 'class', kind: _csrFeatureKind(f), modifiers: [], linkedResources: [], linkedActions: [], needsReview: !!f.needsReview }, f);
    _csrPushUnique(features, row, function (x) { return `${String(x.name || '').toLowerCase()}|${String(x.source || x.kind || '').toLowerCase()}`; });
  });
  function ensureFeature(name, source, extra) {
    const key = String(name || '').toLowerCase();
    const existing = features.find(function (x) { return String(x.name || '').toLowerCase() === key; });
    if (existing) {
      const patch = extra || {};
      Object.keys(patch).forEach(function (prop) {
        if (Array.isArray(patch[prop])) existing[prop] = Array.from(new Set(_csrArray(existing[prop]).concat(patch[prop])));
        else if (existing[prop] === undefined || existing[prop] === null || existing[prop] === '') existing[prop] = patch[prop];
      });
      existing.needsReview = false;
      return existing;
    }
    return _csrPushUnique(features, Object.assign({ id: _csrSlug(name), name, source: source || 'class', kind: 'feature', modifiers: [], linkedResources: [], linkedActions: [], needsReview: false }, extra || {}), function (x) { return String(x.name || '').toLowerCase(); });
  }
  if (sorcererLevel) {
    ensureFeature('Font of Magic', 'Sorcerer', { linkedResources: ['sorcery_points'], summary: 'Convert Sorcery Points and spell slots.' });
    ensureFeature('Metamagic', 'Sorcerer', { linkedResources: ['sorcery_points'], summary: 'Spend Sorcery Points to modify spell casting.' });
    if (/wild/i.test(_csrFirst(doc.subclass, book.subclass, classes.map(c => c && c.subclass).join(' ')))) {
      ensureFeature('Wild Magic Surge', 'Wild Magic', { modifiers: [{ type: 'spell_cast_reminder', spellLevel: 'leveled' }] });
      ensureFeature('Tides of Chaos', 'Wild Magic', { linkedResources: ['tides_of_chaos'] });
      ensureResource('tides_of_chaos', 'Tides of Chaos', doc.tidesOfChaosUsed ? 0 : 1, 1, 'long rest or DM surge reset', 'subclass');
    }
  }
  const actions = _csrArray(native.actions || _csrObject(doc.nativeActionCards).actions).map(a => _csrAction(a.id, a.name, a.actionType || 'action', a));
  const bonusActions = _csrArray(native.bonusActions || _csrObject(doc.nativeActionCards).bonusActions).map(a => _csrAction(a.id, a.name, a.actionType || 'bonus action', a));
  const reactions = _csrArray(native.reactions || _csrObject(doc.nativeActionCards).reactions).map(a => _csrAction(a.id, a.name, a.actionType || 'reaction', a));
  function addAction(name, type, opts) {
    const lane = type === 'bonus action' ? bonusActions : (type === 'reaction' ? reactions : actions);
    return _csrPushUnique(lane, _csrAction(_csrSlug(name), name, type, opts), function (a) { return String(a.name || '').toLowerCase(); });
  }
  if (sorcererLevel) {
    addAction('Flexible Casting: Create Spell Slot', 'bonus action', { sourceFeature: 'Font of Magic', resourceCost: { resourceId: 'sorcery_points', amount: 2 }, linkedResources: ['sorcery_points'], effectSummary: 'Spend Sorcery Points to create a spell slot.' });
    addAction('Quickened Spell / Metamagic', 'bonus action', { sourceFeature: 'Metamagic', resourceCost: { resourceId: 'sorcery_points', amount: 2 }, linkedResources: ['sorcery_points'], featureModifiers: [{ type: 'spell_action_economy', from: 'action', to: 'bonus action', eligibility: '1-action spell' }], effectSummary: 'Cast an eligible 1-action spell using your bonus action.' });
    addAction('Subtle Spell / Metamagic', 'bonus action', { sourceFeature: 'Metamagic', resourceCost: { resourceId: 'sorcery_points', amount: 1 }, linkedResources: ['sorcery_points'], featureModifiers: [{ type: 'component_modification', removes: ['V', 'S'] }] });
    addAction('Heightened Spell / Metamagic', 'bonus action', { sourceFeature: 'Metamagic', resourceCost: { resourceId: 'sorcery_points', amount: 2 }, linkedResources: ['sorcery_points'], featureModifiers: [{ type: 'saving_throw_flow', effect: 'one target has disadvantage on first save' }] });
  }
  const attacks = [];
  _csrArray(doc.attacks || doc.quickAttacks).forEach(a => _csrPushUnique(attacks, Object.assign({ id: _csrSlug(a.name), source: 'attack' }, a), x => String(x.name || x.id || '').toLowerCase()));
  _csrArray(doc.inventory || doc.items || book.inventory).forEach(function (item) {
    const name = _csrFirst(item.name, item.displayName);
    if (/quarterstaff|weapon|sword|bow|dagger|axe|mace/i.test(`${name} ${item.type || ''}`)) {
      _csrPushUnique(attacks, { id: _csrSlug(name), name, source: item.source || 'item', actionType: 'action', attackBonus: item.attackBonus || '', damage: item.damage || item.damageFormula || '', item }, x => String(x.name || '').toLowerCase());
    }
  });
  _csrPushUnique(attacks, { id: 'unarmed-strike', name: 'Unarmed Strike', source: 'system', actionType: 'action', damage: '1 + STR mod' }, x => String(x.name || '').toLowerCase());
  const spellInputs = [].concat(_csrArray(native.spells), _csrArray(doc.rulesSpellbook), _csrArray(doc.spells), _csrArray(book.spells));
  const spells = [];
  spellInputs.forEach(function (spell) { _csrPushUnique(spells, _csrBuildSpell(spell, doc, spell.source || 'class'), function (s) { return String(s.name || s.id || '').toLowerCase(); }); });
  ['Fire Bolt', 'Scorching Ray', 'Fireball'].forEach(function (name) {
    if (sorcererLevel) _csrPushUnique(spells, _csrBuildSpell({ name, id: _csrSlug(name) }, doc, 'class'), function (s) { return String(s.name || s.id || '').toLowerCase(); });
  });
  const limitedUseActions = actions.concat(bonusActions, reactions).filter(function (a) { return a.resourceCost || a.max != null || a.current != null; });
  resources.forEach(function (r) {
    r.linkedFeatures = features.filter(f => _csrArray(f.linkedResources).includes(r.id) || String(f.resourceName || '').toLowerCase() === String(r.name || '').toLowerCase()).map(f => f.id);
    r.linkedActions = actions.concat(bonusActions, reactions).filter(a => _csrArray(a.linkedResources).includes(r.id) || _csrObject(a.resourceCost).resourceId === r.id).map(a => a.id);
  });
  return {
    identity: { name: _csrFirst(doc.name, book.name, 'Adventurer'), className: classLine, level, species: _csrFirst(doc.species, doc.race, book.species, book.race), background: _csrFirst(doc.background, book.background) },
    abilities: doc.abilities || doc.abilityScores || {}, saves: doc.saves || doc.savingThrows || {}, skills: doc.skills || {}, senses: doc.senses || {}, defenses: { resistances: doc.resistances || [], immunities: doc.immunities || [] }, conditions: doc.conditions || [],
    hp: Object.assign({ current: _csrInt(doc.currentHP || doc.currentHp, _csrInt(doc.maxHP || doc.maxHp, 0)), max: _csrInt(doc.maxHP || doc.maxHp, 0), temp: _csrInt(doc.tempHP || doc.tempHp, 0) }, _csrObject(native.hp)),
    ac: _csrInt(native.ac ?? doc.ac, 10), speed: native.speed || { walk: _csrInt(doc.speed, 30) }, initiative: _csrInt(doc.initiative ?? _csrObject(native.combat).initiative, 0), proficiencyBonus: _csrInt(native.proficiencyBonus ?? doc.profBonus ?? doc.proficiencyBonus, Math.ceil(level / 4) + 1),
    resources, actions, bonusActions, reactions, limitedUseActions, attacks, spells, features, traits: features.filter(f => f.kind === 'trait'), feats: features.filter(f => f.kind === 'feat'), background: doc.backgroundFeatures || book.background || {}, inventory: doc.inventory || doc.items || book.inventory || [], warnings: [], needsReview: features.some(f => f.needsReview),
  };
}
function spendCharacterSheetResource(runtime, resourceId, amount) {
  const rt = _csrObject(runtime);
  const id = String(resourceId || '').toLowerCase();
  const cost = Math.max(0, _csrInt(amount, 1));
  const row = _csrArray(rt.resources).find(function (r) { return String(r.id || r.name || '').toLowerCase() === id || String(r.name || '').toLowerCase() === id; });
  if (!row || !row.spendable) return { ok: false, reason: 'resource unavailable', runtime: rt };
  const current = _csrInt(row.current, 0);
  if (current < cost) return { ok: false, reason: 'insufficient resource', runtime: rt };
  row.current = current - cost;
  return { ok: true, resource: row, runtime: rt };
}
function resetCharacterSheetResources(runtime, restType) {
  const rt = _csrObject(runtime);
  const type = String(restType || 'long').toLowerCase();
  _csrArray(rt.resources).forEach(function (row) {
    const reset = String(row.restReset || row.recovery || '').toLowerCase();
    if (type === 'long' || reset.includes(type)) row.current = _csrInt(row.max, _csrInt(row.current, 0));
  });
  return rt;
}

function renderCharacterBookOverviewContent() {
  const c = ensureCharSheetRuntimeDefaults(_charSheet);
  if (!c) return;

  document.getElementById('sheet-char-name').textContent = c.name || 'Adventurer';
  const speciesLine = _prettySheetLabel(c.species || c.race || '');
  const backgroundLine = _prettySheetLabel(c.background || c.book?.background || '');
  document.getElementById('sheet-char-sub').textContent = [speciesLine, backgroundLine].filter(Boolean).join(' · ') || 'Character details';

  const body = document.getElementById('sheet-body');
  if (!body) return;
  body.innerHTML = '';
  const book = (c && typeof c.book === 'object' && c.book) ? c.book : {};
  const levelValue = parseInt(c.totalLevel || c.level || book.level, 10) || 1;
  const heroClass = ((Array.isArray(c.classes) ? c.classes : []).map(cl => cl?.name).filter(Boolean).join(' / ') || book.className || 'Adventurer');
  const heroSubclass = ((Array.isArray(c.classes) ? c.classes : []).map(cl => cl?.subclass).filter(Boolean).join(' / ') || book.subclass || '');
  const heroRace = c.species || c.race || book.species || book.race || '';
  const heroBackground = c.background || book.background || '';
  const heroSize = c.size || c.speciesGameplay?.size || 'Medium';
  const heroSenses = String(c.senses || book.senses || (Array.isArray(c.speciesGameplay?.senses) ? c.speciesGameplay.senses.join(', ') : '') || '').trim();
  const heroResistances = String(c.resistances || book.resistances || (Array.isArray(c.speciesGameplay?.resistances) ? c.speciesGameplay.resistances.join(', ') : '') || '').trim();
  const heroDarkvision = parseInt(c.darkvisionRadius ?? c.speciesGameplay?.darkvision_radius ?? 0, 10) || 0;
  const heroPortrait = c.avatarUrl || book.avatarUrl || '';
  const passivePerception = parseInt(c.passivePerception ?? book.passivePerception, 10);
  const profBonus = parseInt(c.profBonus ?? book.profBonus, 10);
  const speedValue = parseInt(c.speed, 10) || 0;
  const spellSaveDc = String(c.spellSaveDc ?? book.spellSaveDc ?? '').trim();
  const spellAttack = String(c.spellAttack ?? book.spellAttack ?? '').trim();
  const inspiration = String(c.inspiration ?? book.inspiration ?? '').trim();
  const accentColor = _coerceHexColor(c.accentColor || document.getElementById('char-accent-color')?.value || '#00e5cc', '#00e5cc');
  const tagline = String(c.tagline || document.getElementById('char-tagline')?.value || '').trim();
  const portraitFrame = String(c.portraitFrame || document.getElementById('char-portrait-frame')?.value || 'classic').trim() || 'classic';
  const frameStyle = PLAYER_PORTRAIT_FRAMES[portraitFrame] || PLAYER_PORTRAIT_FRAMES.classic;
  applyCharacterSheetTheme(c);

  // ── HP Section ──
  const combatSnapshot = _getSheetCombatSnapshot(c);
  const safeMaxHp = combatSnapshot.maxHp;
  const safeCurrentHp = combatSnapshot.currentHp;
  const safeTempHp = combatSnapshot.tempHp;
  const hpPct = safeMaxHp > 0 ? Math.max(0, Math.min(100, (safeCurrentHp / safeMaxHp) * 100)) : 0;
  const hpColor = hpPct > 50 ? '#2ecc71' : hpPct > 25 ? '#e67e22' : '#e74c3c';
  const trackedFeatures = _getStructuredClassFeatures().filter(f => f.trackUses);
  const classFeature = _getSheetPrimaryClassResource(trackedFeatures);
  const classState = classFeature ? _getClassFeatureResourceState(classFeature) : null;
  const classFeatureRows = trackedFeatures.map((feature) => {
    const state = _getClassFeatureResourceState(feature);
    return state ? { feature, state } : null;
  }).filter(Boolean);
  const secondaryResourceRows = classFeatureRows
    .filter(row => row && row.feature?.key !== classFeature?.key)
    .slice(0, 3);
  const inventoryRows = _sheetInventorySummaryRows(c);
  const actionSections = _getPlayerActionsSections();
  const spotlightAttacks = (actionSections.Attacks || []).slice(0, 4);
  const spotlightBonus = (actionSections['Bonus Actions'] || []).slice(0, 3);
  const spotlightReactions = (actionSections.Reactions || []).slice(0, 3);
  const rawSpellSpotlightCards = (typeof _getStructuredRulesSpellbookCards === 'function' ? _getStructuredRulesSpellbookCards() : []);
  const spellUsage = (_charSheet && typeof _charSheet.spellUsageCounts === 'object' && _charSheet.spellUsageCounts) ? _charSheet.spellUsageCounts : {};
  const prettySpellName = function (raw) { return String(raw || '').replace(/^spell[_-]+/i, '').replace(/[_-]+/g, ' ').replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); }).trim(); };
  const selectedSpellNames = (typeof _currentSpellSelectionNames === 'function') ? _currentSpellSelectionNames(c) : [];
  const readySpellCards = (typeof _getCombatQuickSpells === 'function' ? _getCombatQuickSpells() : []).map(function (entry, idx) {
    const card = entry && entry.card ? entry.card : {};
    const prettyName = prettySpellName(entry && (entry.name || entry.id) || card.name || 'Spell');
    const level = Number(entry && entry.level != null ? entry.level : (card.spell_level != null ? card.spell_level : (card.level != null ? card.level : 0))) || 0;
    return Object.assign({
      id: String(entry && (entry.id || prettyName || ('quick-spell-' + idx)) || ('quick-spell-' + idx)),
      name: prettyName,
      displayName: prettyName,
      spell_level: level,
      level: level,
      concentration: !!(card.concentration || card.is_concentration),
      is_concentration: !!(card.concentration || card.is_concentration),
      base_effect_text: card.base_effect_text || card.effect || card.current?.effect || '',
      current: card.current || { effect: card.base_effect_text || card.effect || '', formula: card.damage_dice || card.damage || card.damage_formula || card.base_damage_formula || '' },
      level_school: card.level_school || card.school || (level === 0 ? 'Cantrip' : ''),
      range: entry && entry.range || card.range || '',
      source: entry && entry.source || 'spell',
      card: card
    }, card || {});
  });
  const spellSpotlightSource = readySpellCards.length ? readySpellCards : rawSpellSpotlightCards;
  const spellSpotlightCards = spellSpotlightSource.slice().sort(function (a, b) {
    const aCount = parseInt(spellUsage[String(a && (a.id || a.name) || '').toLowerCase()] || 0, 10) || 0;
    const bCount = parseInt(spellUsage[String(b && (b.id || b.name) || '').toLowerCase()] || 0, 10) || 0;
    if (bCount !== aCount) return bCount - aCount;
    return (parseInt(a && (a.spell_level || a.level || 0), 10) || 0) - (parseInt(b && (b.spell_level || b.level || 0), 10) || 0);
  }).slice(0, 4);
  const liveCurrency = (typeof _getLivePlayerGoldValue === 'function' && _getLivePlayerGoldValue() > 0) ? _getLivePlayerGoldValue() : null;
  const inventoryHost = document.getElementById('sheet-inventory-summary');
  if (inventoryHost) {
    inventoryHost.innerHTML = inventoryRows.length
      ? inventoryRows.map(row => `<div class="sheet-inventory-row"><span>${escapeHtml(row.name)} ×${row.qty}</span><span style="color:var(--parchment-dim);">${escapeHtml(row.note || '—')}</span></div>`).join('')
      : '<div class="sheet-note">No synced inventory entries yet.</div>';
  }

  const quickAttackCards = (typeof _getUnifiedQuickAttackCards === 'function') ? _getUnifiedQuickAttackCards() : [];
  const rulesSpellCards = readySpellCards.length ? readySpellCards : ((typeof _getStructuredRulesSpellbookCards === 'function') ? _getStructuredRulesSpellbookCards() : []);
  const syncedSpellCount = Math.max(rulesSpellCards.length, selectedSpellNames.length);
  const nativeActionGroups = (typeof _getNativeCharacterBookActionCards === 'function') ? _getNativeCharacterBookActionCards() : { actions: [], bonusActions: [], reactions: [] };
  const nativeActionCards = []
    .concat(Array.isArray(nativeActionGroups?.actions) ? nativeActionGroups.actions : [])
    .concat(Array.isArray(nativeActionGroups?.bonusActions) ? nativeActionGroups.bonusActions : [])
    .concat(Array.isArray(nativeActionGroups?.reactions) ? nativeActionGroups.reactions : []);
  const nativeResourceCards = (typeof _getNativeCharacterBookResources === 'function') ? _getNativeCharacterBookResources() : [];
  const nativeFeatureCards = (typeof _getNativeCharacterBookFeatures === 'function') ? _getNativeCharacterBookFeatures() : [];
  const selectedTarget = (typeof _nativeActionSelectedTarget === 'function') ? _nativeActionSelectedTarget() : null;
  const activeConcentration = (typeof _getActiveConcentrationSpellName === 'function') ? _getActiveConcentrationSpellName() : '';
  body.innerHTML += `
    <div class="sheet-combat-strip">
      <div class="sheet-hp-hero">
        <div class="sheet-inline-title">Play State</div>
        <div class="hp-bar-wrap"><div class="hp-bar-fill" style="width:${Math.round(hpPct)}%;background:${hpColor};"></div></div>
        <div class="hp-numbers"><span class="hp-current">${safeCurrentHp}</span><span class="hp-sep">/</span><span class="hp-max">${safeMaxHp}</span><span class="sheet-combat-chip"><strong>Temp ${safeTempHp}</strong></span></div>
        <div class="sheet-combat-chip-row">
          <span class="sheet-combat-chip"><strong>AC ${combatSnapshot.ac}</strong></span>
          <span class="sheet-combat-chip"><strong>SPD ${combatSnapshot.speed || '—'} ft</strong></span>
          <span class="sheet-combat-chip"><strong>Init ${Number.isFinite(combatSnapshot.initiative) ? formatSignedSummaryValue(combatSnapshot.initiative) : '—'}</strong></span>
          ${spellSaveDc ? `<span class="sheet-combat-chip"><strong>DC ${escapeHtml(spellSaveDc)}</strong></span>` : ''}
          ${spellAttack ? `<span class="sheet-combat-chip"><strong>Atk ${escapeHtml(spellAttack)}</strong></span>` : ''}
          <span class="sheet-combat-chip"><strong>PB ${Number.isFinite(combatSnapshot.profBonus) ? formatSignedSummaryValue(combatSnapshot.profBonus) : '—'}</strong></span>
          <span class="sheet-combat-chip"><strong>Passive ${Number.isFinite(combatSnapshot.passivePerception) ? combatSnapshot.passivePerception : '—'}</strong></span>
          ${combatSnapshot.isCombatActive ? `<span class="sheet-combat-chip"><strong>${combatSnapshot.isMyTurn ? 'Your Turn' : 'Combat Active'}</strong></span>` : ''}
          ${combatSnapshot.concentration ? `<span class="sheet-combat-chip"><strong>⟳ Concentrating</strong></span>` : ''}
          ${combatSnapshot.conditionList.filter(id => String(id).toLowerCase() !== 'concentrating').slice(0, 4).map(id => `<span class="sheet-combat-chip">${escapeHtml(CONDITIONS_MAP[id]?.name || id)}</span>`).join('')}
        </div>
      </div>
      <div class="sheet-class-resource-hero">
        <div class="sheet-class-resource-title">Class Resource</div>
        <div class="sheet-class-resource-main">${escapeHtml(classFeature?.name || 'Class Feature')}</div>
        <div class="sheet-note" style="margin-top:0.2rem;">${classState ? `Uses ${escapeHtml(classState.summary)}` : 'No tracked uses found in current book text.'}</div>
        ${secondaryResourceRows.length ? `<div class="sheet-combat-chip-row">${secondaryResourceRows.map(row => `<span class="sheet-combat-chip"><strong>${escapeHtml(row.feature.name || 'Feature')}</strong> ${escapeHtml(row.state.summary)}</span>`).join('')}</div>` : ''}
        <div class="sheet-combat-chip-row">
          ${classFeature?.key ? `<button class="sheet-quick-btn" type="button" onclick="adjustClassFeatureUse('${escapeHtml(classFeature.key)}', 1)">Use</button><button class="sheet-quick-btn" type="button" onclick="adjustClassFeatureUse('${escapeHtml(classFeature.key)}', -1)">Restore</button>` : '<span class="sheet-note">Add usage text like “Wild Shape 1/2”.</span>'}
        </div>
      </div>
    </div>
    <div class="sheet-quick-actions">
      <div class="sheet-inline-title">Quick Actions</div>
      <input id="sheet-hp-delta" class="sheet-book-input mono" type="number" min="1" max="999" value="5" style="max-width:92px;margin-bottom:0.35rem;" />
      <div class="sheet-quick-actions-grid">
        <button class="sheet-quick-btn primary" type="button" onclick="runSheetQuickAction('initiative')">Roll Initiative</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('class')">Class Action</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('cast')">Cast Spell</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('damage')">Damage</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('heal')">Heal</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('rest')">Rest</button>
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Attack Spotlight</div>
      <div class="sheet-inline-list">
        ${spotlightAttacks.map(action => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(action.name || 'Attack')}</strong><div class="sheet-inline-tags">${(action.badges || []).slice(0,2).map(tag => `<span class="sheet-inline-tag">${escapeHtml(String(tag))}</span>`).join('')}</div></div><div class="sheet-note">${escapeHtml(action.desc || action.resource || 'Attack roll')}</div><div class="sheet-combat-chip-row" style="margin-top:0.35rem;"><button class="sheet-quick-btn" type="button" onclick="playerUseAction('${escapeHtml(action.source || 'weapon')}', '${escapeHtml(action.id || '')}')">Roll</button><button class="sheet-quick-btn" type="button" onclick="playerInspectAction('${escapeHtml(action.source || 'weapon')}', '${escapeHtml(action.id || '')}')">Info</button></div></div>`).join('') || '<div class="sheet-note">Equip a weapon or add an attack entry to populate this section.</div>'}
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Bonus Actions & Reactions</div>
      <div class="sheet-inline-list">
        ${spotlightBonus.concat(spotlightReactions).map(action => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(action.name || 'Action')}</strong><div class="sheet-inline-tags">${(action.badges || []).slice(0,2).map(tag => `<span class="sheet-inline-tag">${escapeHtml(String(tag))}</span>`).join('')}</div></div><div class="sheet-note">${escapeHtml(action.resource || action.desc || 'Quick-turn option')}</div><div class="sheet-combat-chip-row" style="margin-top:0.35rem;"><button class="sheet-quick-btn" type="button" onclick="playerUseAction('${escapeHtml(action.source || 'native_action')}', '${escapeHtml(action.id || '')}')">Use</button><button class="sheet-quick-btn" type="button" onclick="playerInspectAction('${escapeHtml(action.source || 'native_action')}', '${escapeHtml(action.id || '')}')">Info</button></div></div>`).join('') || '<div class="sheet-note">Native bonus actions and reactions will appear here once the class runtime is mapped.</div>'}
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Spell Spotlight</div>
      <div class="sheet-inline-list">
        ${spellSpotlightCards.map(card => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(prettySpellName(card.name || card.displayName || 'Spell'))}</strong><div class="sheet-inline-tags"><span class="sheet-inline-tag">${escapeHtml((card.spell_level || card.level || 0) === 0 ? 'Cantrip' : `Lv ${(card.spell_level || card.level || 0)}`)}</span>${card.concentration || card.is_concentration ? '<span class="sheet-inline-tag">Concentration</span>' : ''}</div></div><div class="sheet-note">${escapeHtml(card.base_effect_text || card.current?.effect || card.level_school || 'Quick cast-ready spell card.')}</div><div class="sheet-combat-chip-row" style="margin-top:0.35rem;"><button class="sheet-quick-btn" type="button" onclick="castRulesSpell('${escapeHtml(card.id || card.name || '')}')">Cast</button><button class="sheet-quick-btn" type="button" onclick="playerInspectSpell('${escapeHtml(card.id || card.name || '')}')">Info</button></div></div>`).join('') || '<div class="sheet-note">Link spell cards or learn spells in the Magic tab to surface quick-cast spell cards here.</div>'}
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Loadout Snapshot</div>
      <div class="sheet-note" style="margin-bottom:0.4rem;">${liveCurrency != null ? `Gold on hand: ${escapeHtml(_formatGoldUnits(liveCurrency))}` : 'Open Inventory for the full bag. This strip shows the live synced loadout first.'}</div>
      <div class="sheet-inline-list">
        ${inventoryRows.slice(0, 6).map(row => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(row.name || 'Item')}</strong><div class="sheet-inline-tags"><span class="sheet-inline-tag">×${escapeHtml(String(row.qty || 1))}</span></div></div><div class="sheet-note">${escapeHtml(row.note || 'Loadout item')}</div></div>`).join('') || '<div class="sheet-note">No synced inventory items yet.</div>'}
      </div>
    </div>
    <div class="sheet-overview-hero">
      <div class="sheet-overview-portrait" style="border:${escapeHtml(frameStyle.border)};border-radius:${escapeHtml(frameStyle.radius)};box-shadow:${escapeHtml(frameStyle.shadow)};">${heroPortrait ? `<img src="${escapeHtml(heroPortrait)}" alt="Portrait of ${escapeHtml(c.name || 'Adventurer')}" loading="lazy">` : `<span>${escapeHtml(String(c.name || 'A').slice(0, 1).toUpperCase())}</span>`}</div>
      <div class="sheet-overview-meta">
        <div class="sheet-overview-name">${escapeHtml(c.name || 'Adventurer')}</div>
        <div class="sheet-overview-subline">${escapeHtml(_prettySheetLabel(heroClass))}${heroSubclass ? ` · ${escapeHtml(_prettySheetLabel(heroSubclass))}` : ''}</div>
        ${tagline ? `<div class="sheet-overview-subline" style="font-style:italic;color:var(--sheet-accent, var(--gold));">“${escapeHtml(tagline)}”</div>` : ''}
        <div class="sheet-overview-tags">
          <span class="sheet-overview-tag">Level ${levelValue}</span>
          ${heroRace ? `<span class="sheet-overview-tag">${escapeHtml(heroRace)}</span>` : ''}
          ${heroSize ? `<span class="sheet-overview-tag">${escapeHtml(heroSize)}</span>` : ''}
          ${heroBackground ? `<span class="sheet-overview-tag">${escapeHtml(heroBackground)}</span>` : ''}
        </div>
      </div>
    </div>`;
  body.innerHTML += `
    <div class="sheet-glance-grid">
      <div class="sheet-glance-tile primary"><div class="sheet-glance-label">Armor Class</div><div class="sheet-glance-value">${parseInt(c.ac, 10) || 0}</div><div class="sheet-glance-sub">Defense</div></div>
      <div class="sheet-glance-tile primary"><div class="sheet-glance-label">Current HP</div><div class="sheet-glance-value">${safeCurrentHp}</div><div class="sheet-glance-sub">of ${safeMaxHp}</div></div>
      <div class="sheet-glance-tile"><div class="sheet-glance-label">Temp HP</div><div class="sheet-glance-value">${safeTempHp}</div><div class="sheet-glance-sub">buffer</div></div>
      <div class="sheet-glance-tile"><div class="sheet-glance-label">Speed</div><div class="sheet-glance-value">${speedValue || '—'}</div><div class="sheet-glance-sub">${speedValue ? 'ft' : 'not set'}</div></div>
    </div>`;
  body.innerHTML += `
    <div class="sheet-resource-grid">
      <div class="sheet-resource-item"><label>Proficiency</label><strong>${Number.isFinite(profBonus) ? formatSignedSummaryValue(profBonus) : '—'}</strong></div>
      <div class="sheet-resource-item"><label>Passive Perception</label><strong>${Number.isFinite(passivePerception) && passivePerception > 0 ? passivePerception : '—'}</strong></div>
      ${heroDarkvision > 0 ? `<div class="sheet-resource-item"><label>Darkvision</label><strong>${heroDarkvision} ft</strong></div>` : ''}
      ${spellSaveDc ? `<div class="sheet-resource-item"><label>Spell Save DC</label><strong>${escapeHtml(spellSaveDc)}</strong></div>` : ''}
      ${spellAttack ? `<div class="sheet-resource-item"><label>Spell Attack</label><strong>${escapeHtml(spellAttack)}</strong></div>` : ''}
      ${inspiration ? `<div class="sheet-resource-item"><label>Inspiration</label><strong>${escapeHtml(inspiration)}</strong></div>` : ''}
    </div>`;
  body.innerHTML += `
    <div class="sheet-resource-grid">
      <div class="sheet-resource-item"><label>Senses</label><strong>${escapeHtml(heroSenses || '—')}</strong></div>
      <div class="sheet-resource-item"><label>Resistances</label><strong>${escapeHtml(heroResistances || '—')}</strong></div>
    </div>`;

  // ── Class Features List ──
  const allClassFeatures = typeof _getStructuredClassFeatures === 'function' ? _getStructuredClassFeatures() : [];
  if (allClassFeatures.length) {
    const featuresBySection = {};
    allClassFeatures.forEach(f => {
      const sec = f.section || 'Class Features';
      if (!featuresBySection[sec]) featuresBySection[sec] = [];
      featuresBySection[sec].push(f);
    });
    const sectionOrder = ['Class Features', 'Actions', 'Bonus Actions', 'Reactions'];
    const otherSections = Object.keys(featuresBySection).filter(s => !sectionOrder.includes(s));
    const allSections = [...sectionOrder, ...otherSections].filter(s => featuresBySection[s]);
    const featureHtml = allSections.map(sec => {
      const items = featuresBySection[sec];
      return `<div style="margin-bottom:0.6rem;">
        <div class="sheet-inline-title" style="margin-bottom:0.3rem;">${escapeHtml(sec)}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0.3rem;">
          ${items.map(f => {
            const tagParts = [];
            if (f.className) tagParts.push(f.className);
            if (f.subclass) tagParts.push(`(${f.subclass})`);
            if (f.minLevel > 1) tagParts.push(`Lv.${f.minLevel}`);
            const tags = tagParts.join(' ');
            return `<span class="sheet-combat-chip" style="cursor:default;" title="${escapeHtml(tags)}">${escapeHtml(f.name)}</span>`;
          }).join('')}
        </div>
      </div>`;
    }).join('');
    body.innerHTML += `
      <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
        <div class="sheet-inline-title">Class Abilities at Level ${levelValue}</div>
        <div style="font-size:0.68rem;color:var(--parchment-dim);margin-bottom:0.55rem;">Features unlocked for your class and subclass up to your current level.</div>
        ${featureHtml}
      </div>`;
  }
}


  global.AppCharacterSheetRuntime = {
    buildCharacterSheetRuntime,
    spendCharacterSheetResource,
    resetCharacterSheetResources,
    requestCharacterBookOverviewRender,
    renderCharSheet,
    renderCharacterBookOverviewContent,
  };
  global.buildCharacterSheetRuntime = buildCharacterSheetRuntime;
  global.spendCharacterSheetResource = spendCharacterSheetResource;
  global.resetCharacterSheetResources = resetCharacterSheetResources;
})(window);
