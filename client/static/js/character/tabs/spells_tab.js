/*
 * client/static/js/character/tabs/spells_tab.js
 * Spells Tab — Player-facing spell list plus managed spell selection.
 *
 * Exposes: window.SpellsTab
 *   .initSpellsTab(container, charData)
 */

(function initSpellsTabModule(global) {
  'use strict';
  // Stage 46 compatibility marker: data-map-panel-open="spelllib"

  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  const LEVEL_LABELS = ['ALL', 'CANTRIP', '1ST', '2ND', '3RD', '4TH', '5TH', '6TH', '7TH', '8TH', '9TH'];
  const LEVEL_LABEL_TO_KEY = {
    'CANTRIP': 'cantrip',
    '1ST': '1', '2ND': '2', '3RD': '3', '4TH': '4', '5TH': '5',
    '6TH': '6', '7TH': '7', '8TH': '8', '9TH': '9'
  };
  const CASTING_TIME_ABBR = {
    '1 action': '1A', 'bonus action': 'BA', reaction: 'R', '1 minute': '1M', '10 minutes': '10M', '1 hour': '1H', '8 hours': '8H', '12 hours': '12H', '24 hours': '24H'
  };
  const DEFAULT_SLOTS = {
    1: [0, 2, 0, 0, 0, 0, 0, 0, 0, 0], 2: [0, 3, 0, 0, 0, 0, 0, 0, 0, 0], 3: [0, 4, 2, 0, 0, 0, 0, 0, 0, 0],
    4: [0, 4, 3, 0, 0, 0, 0, 0, 0, 0], 5: [0, 4, 3, 2, 0, 0, 0, 0, 0, 0], 6: [0, 4, 3, 3, 0, 0, 0, 0, 0, 0],
    7: [0, 4, 3, 3, 1, 0, 0, 0, 0, 0], 8: [0, 4, 3, 3, 2, 0, 0, 0, 0, 0], 9: [0, 4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [0, 4, 3, 3, 3, 2, 0, 0, 0, 0], 11: [0, 4, 3, 3, 3, 2, 1, 0, 0, 0], 13: [0, 4, 3, 3, 3, 2, 1, 1, 0, 0],
    15: [0, 4, 3, 3, 3, 2, 1, 1, 1, 0], 17: [0, 4, 3, 3, 3, 2, 1, 1, 1, 1], 20: [0, 4, 3, 3, 3, 2, 1, 1, 1, 1]
  };

  function _safeArray(value) { return Array.isArray(value) ? value.filter(Boolean) : []; }
  function _humanizeSpellName(raw) {
    const text = String(raw == null ? '' : raw).trim();
    if (!text) return '';
    const cleaned = text.replace(/^spell[_-]+/i, '').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
    return cleaned.replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); });
  }
  function _spellName(spell) {
    return spell.displayName || _humanizeSpellName(spell.name || spell.id || '') || '—';
  }
  function _firstText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value === undefined || value === null) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }
  function _previewText(text, limit) {
    const raw = String(text || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    return raw.length > (limit || 220) ? raw.slice(0, (limit || 220) - 1) + '…' : raw;
  }
  function _meaningful(value) {
    const text = String(value == null ? '' : value).trim();
    return !!text && text !== '—' && text.toLowerCase() !== 'none';
  }
  function _compactRows(rows) {
    return _safeArray(rows).filter(function (row) { return row && _meaningful(row.value); });
  }
  function _parseSpellLevelValue(raw) {
    if (raw === null || raw === undefined || raw === '') return null;
    if (typeof raw === 'string' && raw.toLowerCase() === 'cantrip') return 0;
    const n = parseInt(raw, 10);
    return Number.isFinite(n) ? n : null;
  }

  function _spellBaseLevel(spell) {
    const card = spell && spell.card && typeof spell.card === 'object' ? spell.card : {};
    return _parseSpellLevelValue(spell && (spell.baseLevel ?? spell.base_level ?? spell.spell_level ?? spell.spellLevel ?? card.spell_level ?? card.level ?? spell.level));
  }

  function _spellDisplayCastLevel(spell) {
    const display = _parseSpellLevelValue(spell && (spell.castLevel ?? spell.slotLevel ?? spell.displaySectionLevel));
    return display !== null ? display : (_spellBaseLevel(spell) ?? 0);
  }

  function _spellLevelNumber(spell) {
    return _parseSpellLevelValue(spell && (spell.displaySectionLevel ?? spell.castLevel ?? spell.level ?? spell.spell_level ?? spell.spellLevel ?? spell.slotLevel));
  }
  function _abbrevTime(ct) {
    if (!ct) return '—';
    const lower = String(ct).toLowerCase().trim();
    if (CASTING_TIME_ABBR[lower]) return CASTING_TIME_ABBR[lower];
    return String(ct).slice(0, 3);
  }
  function _getSlotCounts(charData) {
    const level = parseInt(charData && (charData.totalLevel || charData.level), 10) || 1;
    if (charData && Array.isArray(charData.spellSlots)) return charData.spellSlots;
    const keys = Object.keys(DEFAULT_SLOTS).map(Number).sort(function (a, b) { return a - b; });
    let chosen = keys[0];
    for (let i = 0; i < keys.length; i += 1) if (level >= keys[i]) chosen = keys[i];
    return DEFAULT_SLOTS[chosen] || [];
  }
  function _getUsedSlots(charData) { return charData && Array.isArray(charData.usedSpellSlots) ? charData.usedSpellSlots : []; }
  function _pactMagicState(charData) {
    const spellAccess = charData && charData.spellAccess && typeof charData.spellAccess === 'object' ? charData.spellAccess : {};
    const pact = spellAccess && spellAccess.pactMagic && typeof spellAccess.pactMagic === 'object' ? spellAccess.pactMagic : {};
    const mechanics = charData && charData.classMechanics && typeof charData.classMechanics === 'object' ? charData.classMechanics : {};
    const slotCount = parseInt(pact.slotCount != null ? pact.slotCount : mechanics.pactSlots, 10);
    const slotLevel = parseInt(pact.slotLevel != null ? pact.slotLevel : mechanics.pactSlotLevel, 10);
    return {
      enabled: !!(pact.enabled || (Number.isFinite(slotCount) && slotCount > 0)),
      slotCount: Number.isFinite(slotCount) ? slotCount : 0,
      slotLevel: Number.isFinite(slotLevel) ? slotLevel : 0,
      recoveryType: _firstText(pact.recoveryType, ''),
      note: _firstText(pact.note, ''),
    };
  }
  function _classKey(charData) {
    return _firstText(charData && charData.className, charData && charData.class, '').toLowerCase().trim();
  }
  function _sorcererInsights(charData, state) {
    const mechanics = charData && charData.classMechanics && typeof charData.classMechanics === 'object' ? charData.classMechanics : {};
    const limits = state && state.manifest && state.manifest.limits && typeof state.manifest.limits === 'object' ? state.manifest.limits : {};
    const resources = _safeArray(charData && charData.nativeResources);
    const sorcery = resources.find(function (row) {
      const id = String(row && row.id || '').toLowerCase();
      return id === 'sorcery_points' || String(row && row.name || '').toLowerCase() === 'sorcery points';
    }) || null;
    const featureRows = _safeArray(charData && charData.nativeClassFeatures).concat(_safeArray(charData && charData.nativeFeatures));
    const metamagicChoices = featureRows
      .map(function (row) {
        const name = _firstText(row && row.name, row && row.displayName, '');
        if (!/metamagic/i.test(name || '')) return '';
        const effect = _firstText(row && row.effect, '');
        const fromEffect = effect.replace(/^selected option:\s*/i, '').trim();
        const fromName = name.split('—')[1] ? name.split('—')[1].trim() : '';
        return _firstText(fromEffect, fromName, '');
      })
      .filter(Boolean);
    const uniqueMeta = Array.from(new Set(metamagicChoices)).slice(0, 4);
    return {
      sorceryCurrent: sorcery && Number.isFinite(parseInt(sorcery.current, 10)) ? parseInt(sorcery.current, 10) : null,
      sorceryMax: sorcery && Number.isFinite(parseInt(sorcery.max, 10)) ? parseInt(sorcery.max, 10) : (Number.isFinite(parseInt(mechanics.sorceryPoints, 10)) ? parseInt(mechanics.sorceryPoints, 10) : null),
      knownLimit: Number.isFinite(parseInt(limits.spellsKnown, 10)) ? parseInt(limits.spellsKnown, 10) : null,
      cantripLimit: Number.isFinite(parseInt(limits.cantripsKnown, 10)) ? parseInt(limits.cantripsKnown, 10) : null,
      metamagicChoices: uniqueMeta,
    };
  }
  function _classSpellModelInsights(classKey, state, pact) {
    const snap = _limitSnapshot(state);
    const cards = [];
    let hint = '';
    if (classKey === 'cleric' || classKey === 'druid' || classKey === 'paladin' || classKey === 'wizard') {
      cards.push(_renderSummaryCard('Spell Model', 'Prepared', 'Prepare leveled spells from your unlocked list after rest.', 'teal'));
    } else if (classKey === 'bard' || classKey === 'ranger' || classKey === 'sorcerer' || classKey === 'warlock' || classKey === 'tinker') {
      cards.push(_renderSummaryCard('Spell Model', 'Known', 'Learned spells stay known; you cast from that persistent list.', 'gold'));
    } else {
      cards.push(_renderSummaryCard('Spell Model', 'Library', 'This class currently reads from linked spell cards and library data.', 'violet'));
    }
    if (snap.mode === 'prepared' && snap.preparedLimit != null) {
      cards.push(_renderSummaryCard('Prepared Limit', String(snap.preparedCount) + ' / ' + String(snap.preparedLimit), 'Leveled spells currently ready for this adventuring day.', snap.preparedCount <= snap.preparedLimit ? 'teal' : ''));
    }
    if (snap.mode === 'known' && snap.knownLimit != null) {
      cards.push(_renderSummaryCard('Known Limit', String(snap.knownCount) + ' / ' + String(snap.knownLimit), 'Leveled spells currently learned by this class.', snap.knownCount <= snap.knownLimit ? 'gold' : ''));
    }
    if (classKey === 'warlock' && pact && pact.enabled) {
      hint += 'Warlock flow: use at-will cantrips between pact-slot spikes; pact slots refresh on short rest. ';
    } else if (classKey === 'sorcerer') {
      hint += 'Sorcerer flow: cast from known spells, then spend Sorcery Points on Metamagic or Flexible Casting. ';
    } else if (classKey === 'druid') {
      hint += 'Druid flow: prepared spellcasting and Wild Shape are separate lanes; do not spend Wild Shape when casting normal spells. ';
    } else if (classKey === 'cleric') {
      hint += 'Cleric flow: prepared spells handle most turns, while Channel Divinity features sit on a separate class resource. ';
    } else if (classKey === 'wizard') {
      hint += 'Wizard flow: prepare your daily toolkit from your spellbook, then use Arcane Recovery to extend slot endurance. ';
    } else if (classKey === 'ranger' || classKey === 'paladin') {
      hint += 'Half-caster flow: slot tiers arrive slower than full casters, so combine weapon pressure with selective spell use. ';
    } else if (classKey === 'tinker') {
      hint += 'Tinker flow: treat specialty spells as part of your gadget loop, not separate from your class resource cadence. ';
    }
    return { cards: cards, hint: hint };
  }
  function _spellRankLabel(spell) {
    const level = _spellLevelNumber(spell);
    return level === null ? 'Unknown spell level' : (level === 0 ? 'Cantrip' : 'Level ' + level);
  }
  function _spellSubtitle(spell) {
    const bits = [];
    if (_meaningful(spell && spell.school)) bits.push(spell.school);
    bits.push(_spellRankLabel(spell));
    if (spell && (spell.concentration || spell.is_concentration)) bits.push('Concentration');
    return bits.join(' • ');
  }
  function _spellQuickRead(spell) {
    return _firstText(
      spell && spell.effect,
      spell && spell.playerFacingEffectSummary,
      spell && spell.summary,
      _previewText(spell && (spell.fullPlayerDetailText || spell.description || spell.shortDescription || ''), 240)
    ) || 'No quick summary loaded yet.';
  }
  function _spellTargetingLabel(spell) {
    return spell.areaText || spell.target || spell.range || '—';
  }
  function _spellTableRangeLabel(spell) {
    const raw = _firstText(spell && spell.areaText, spell && spell.area_text, spell && spell.target, spell && spell.range, '—');
    if (!_meaningful(raw)) return '—';
    const text = String(raw).replace(/\s+/g, ' ').trim();
    const normalized = text.match(/\b(self|touch|sight|unlimited)\b/i);
    if (normalized) return normalized[1].charAt(0).toUpperCase() + normalized[1].slice(1).toLowerCase();
    const feet = text.match(/(\d+)\s*(?:ft|feet|foot)\b/i);
    if (feet) return feet[1] + ' ft';
    const miles = text.match(/(\d+)\s*(?:mi|mile|miles)\b/i);
    if (miles) return miles[1] + ' mi';
    return _previewText(text, 24);
  }
  function _spellClassLabel(spell) {
    return Array.isArray(spell.classes) && spell.classes.length ? spell.classes.join(', ') : '—';
  }
  function _spellPlayerRules(spell) {
    return _compactRows([
      { label: 'Casting Time', value: spell.castingTime || '—' },
      { label: 'Range / Area', value: _spellTargetingLabel(spell) },
      { label: 'Duration', value: spell.duration || '—' },
      { label: 'Components', value: spell.components || '—' },
      { label: 'Classes', value: _spellClassLabel(spell) }
    ]);
  }
  function _spellCombatRows(spell) {
    const resolvedFormula = spell.damagePreview || spell.healingPreview || spell.damageFormula || spell.healingFormula || '—';
    return _compactRows([
      { label: 'Attack / Save', value: spell.attackType || spell.savingThrow || spell.saveDC || '—' },
      { label: 'Damage / Healing', value: resolvedFormula },
      { label: 'Damage Type', value: spell.damageType || '—' },
      { label: 'What It Does', value: spell.effectPreview || spell.effect || spell.playerFacingEffectSummary || '—' }
    ]);
  }
  function _spellScalingRows(spell) {
    const items = [];
    if (spell.scalingNote || spell.higherLevel || spell.higher_levels) items.push({ label: 'Higher Levels', value: spell.scalingNote || spell.higherLevel || spell.higher_levels });
    if (_spellLevelNumber(spell) > 0) {
      items.push({ label: 'Spell Slot', value: 'Consumes a spell slot when cast.' });
      const castLevels = _safeArray(spell.availableCastLevels);
      if (castLevels.length > 1) items.push({ label: 'Cast With', value: castLevels.map(function (level) { return 'Level ' + level; }).join(', ') + ' spell slots.' });
      else if (spell.highestAvailableSlot && spell.highestAvailableSlot >= _spellLevelNumber(spell)) items.push({ label: 'Current Slot Access', value: 'You currently have slots up to level ' + spell.highestAvailableSlot + ' for this spell.' });
    }
    return _compactRows(items);
  }


  function _spellTestingGuidance(spell) {
    const level = _spellLevelNumber(spell);
    const text = (_spellName(spell) + ' ' + String(spell && (spell.description || spell.summary || '') || '')).toLowerCase();
    const steps = [
      'Open this spell and make sure the card matches the row details.',
      level > 0 ? 'Cast it and confirm the correct slot tier is used.' : 'Cast it and confirm no slot is spent.'
    ];
    if (spell && (spell.concentration || spell.is_concentration)) steps.push('Confirm concentration starts or replaces the previous concentration spell.');
    if (/heal|restore|cure/.test(text)) steps.push('Verify the correct target is healed and cannot exceed maximum hit points.');
    else steps.push('Verify the attack, save, or direct effect matches the spell text.');
    return steps;
  }

  function _spellConnectedSystems(spell) {
    const systems = ['Spell card'];
    if (_spellLevelNumber(spell) > 0) systems.push('Spell slots');
    if (spell && (spell.concentration || spell.is_concentration)) systems.push('Concentration state');
    if (spell && (spell.attackType || spell.savingThrow || spell.saveDC)) systems.push('Attack / save flow');
    if (spell && (spell.damageFormula || spell.healingFormula || spell.damageType)) systems.push('Target application');
    return systems;
  }

  function _spellExpectedResults(spell) {
    return _compactRows([
      { label: 'Level', value: _spellLevelNumber(spell) === 0 ? 'Cantrip' : 'Level ' + _spellLevelNumber(spell) },
      { label: 'Effect', value: _spellEffectLabel(spell) },
      { label: 'Hit / Save', value: spell.attackType || spell.savingThrow || spell.saveDC || 'Direct effect' }
    ]);
  }

  function _spellRulesBreakdown(spell) {
    return _compactRows([
      { label: 'Cast lane', value: spell.__source === 'linked' ? 'Linked spell action' : 'Spell library entry' },
      { label: 'Resolution', value: spell.attackType ? 'Spell attack roll' : ((spell.savingThrow || spell.saveDC) ? 'Save / DC effect' : 'Direct spell effect') },
      { label: 'Resource model', value: _spellLevelNumber(spell) > 0 ? 'Consumes slot tier on cast' : 'Cantrip / no slot spend' },
      { label: 'Concentration model', value: (spell.concentration || spell.is_concentration) ? 'Starts / replaces concentration state' : 'No concentration state expected' }
    ]);
  }

  function _spellAutomationCoverage(spell) {
    return _compactRows([
      { label: 'Inspector depth', value: 'Ready' },
      { label: 'Slot handling', value: _spellLevelNumber(spell) > 0 ? 'Structured slot path' : 'Not applicable' },
      { label: 'Concentration handling', value: (spell.concentration || spell.is_concentration) ? 'Tracked' : 'Not applicable' },
      { label: 'Target / effect path', value: (spell.attackType || spell.savingThrow || spell.saveDC || spell.damageFormula || spell.healingFormula) ? 'Structured' : 'Mostly informational' }
    ]);
  }

  function _spellCommonBlockers(spell) {
    const blockers = [];
    if (_spellLevelNumber(spell) > 0) blockers.push({ label: 'Slot choice', value: 'Make sure the chosen cast level matches the slot you expect to spend.' });
    if (spell && (spell.concentration || spell.is_concentration)) blockers.push({ label: 'Concentration', value: 'Confirm a previous concentration spell drops when this one starts.' });
    if (spell && (spell.savingThrow || spell.saveDC)) blockers.push({ label: 'Save result', value: 'Check that the success and failure outcome read clearly at the table.' });
    if (!blockers.length) blockers.push({ label: 'Coverage', value: 'No common blockers detected from the current metadata.' });
    return blockers;
  }

function _spellAttackBonusValue(spell, charData) {
  const kind = _spellAttackKind(spell);
  const spellAccess = charData && charData.spellAccess && typeof charData.spellAccess === 'object' ? charData.spellAccess : {};
  const raw = _firstText(
    spell && (spell.attackBonus || spell.attack_bonus || spell.spellAttack || spell.spell_attack || ''),
    kind === 'spell' ? _firstText(charData && (charData.spellAttack || charData.spell_attack || ''), spellAccess.attackBonus != null ? String(spellAccess.attackBonus) : '') : '',
    ''
  );
  const parsed = parseInt(String(raw || '').replace(/^\s*\+/, '').trim(), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function _spellAttackKind(spell) {
  const attackType = _firstText(spell && (spell.attackType || spell.attack_type), '').toLowerCase();
  const text = [
    _firstText(spell && spell.description, ''),
    _firstText(spell && spell.fullPlayerDetailText, ''),
    _firstText(spell && spell.playerFacingEffectSummary, ''),
    _firstText(spell && spell.effect, ''),
    _firstText(spell && spell.base_effect_text, ''),
  ].join(' ').toLowerCase();
  if (attackType) {
    if (/weapon/.test(attackType)) return 'weapon';
    if (/spell|ranged|melee/.test(attackType) || /attack/.test(attackType)) return 'spell';
  }
  if (/spell attack/.test(text)) return 'spell';
  if (/weapon attack|make (a|one) melee attack|make (a|one) ranged attack|melee weapon attack|ranged weapon attack/.test(text)) return 'weapon';
  return '';
}

function _spellHasAttackRoll(spell, charData) {
  const attackKind = _spellAttackKind(spell);
  if (attackKind === 'weapon') return false;
  return attackKind === 'spell' && _spellAttackBonusValue(spell, charData) != null;
}

function _spellAttackSaveLabel(spell, charData) {
  const attackBonus = _spellAttackBonusValue(spell, charData);
  const spellAccess = charData && charData.spellAccess && typeof charData.spellAccess === 'object' ? charData.spellAccess : {};
  const saveDc = _firstText(
    spell && (spell.saveDC || spell.save_dc || ''),
    charData && (charData.spellSaveDc || charData.spell_save_dc || ''),
    spellAccess.saveDc != null ? String(spellAccess.saveDc) : '',
    ''
  );
  const saveAbility = _firstText(spell && (spell.savingThrow || spell.saveAbility || spell.save_ability || ''), '');
  const attackKind = _spellAttackKind(spell);
  if (attackKind && attackBonus != null) return 'Attack ' + (attackBonus >= 0 ? `+${attackBonus}` : String(attackBonus));
  if (saveDc && saveAbility) return 'DC ' + String(saveDc) + ' ' + String(saveAbility).toUpperCase();
  if (saveDc) return 'DC ' + String(saveDc);
  if (saveAbility) return String(saveAbility).toUpperCase() + ' save';
  return '—';
}

function _spellAttackSaveCell(spell, charData) {
  const spellId = String(spell && (spell.id || _spellName(spell) || '') || '').trim();
  const label = _spellAttackSaveLabel(spell, charData);
  const attackKind = _spellAttackKind(spell);
  const attackBonus = _spellAttackBonusValue(spell, charData);
  if ((global.AppSpellRuntime ? global.AppSpellRuntime.resolveSpellRuntime(spell || {}, { saveDc: charData && charData.spellSaveDc }).requiresAttackRoll : attackKind) && attackBonus != null && spellId) {
    return '<button type="button" class="cs-spell-roll-btn" data-spell-attack="' + _esc(spellId) + '" aria-label="Roll attack for ' + _esc(_spellName(spell)) + '">' + _esc(label) + ' 🎲</button>';
  }
  return _esc(label);
}


  function _spellEffectLabel(spell) {
    const formula = _firstText(
      spell && spell.damagePreview,
      spell && spell.damageFormula,
      spell && spell.damage_formula,
      spell && spell.healingPreview,
      spell && spell.healingFormula,
      spell && spell.healing_formula,
      spell && spell.damagePreview,
      spell && spell.rollConfig && spell.rollConfig.damageFormula,
      spell && spell.roll_config && spell.roll_config.damage_formula,
      ''
    );
    const type = _firstText(spell && spell.damageType, spell && spell.damage_type, '');
    const summary = _firstText(
      spell && spell.effectPreview,
      spell && spell.effect,
      spell && spell.effect_text,
      spell && spell.base_effect_text,
      spell && spell.playerFacingEffectSummary,
      spell && spell.player_facing_effect_summary,
      ''
    );
    if (formula && type) return formula + ' ' + type;
    if (formula) return formula;
    if (summary) return summary;
    if (type) return type;
    return '—';
  }

  function _characterLevel(charData) {
    const direct = parseInt(_firstText(charData && (charData.level || charData.characterLevel || charData.totalLevel), ''), 10);
    if (Number.isFinite(direct) && direct > 0) return direct;
    const classes = _safeArray(charData && charData.classes);
    const summed = classes.reduce(function (total, entry) {
      const lvl = parseInt(entry && entry.level, 10);
      return total + (Number.isFinite(lvl) && lvl > 0 ? lvl : 0);
    }, 0);
    return summed > 0 ? summed : 1;
  }

  function _spellRollBaseExpression(spell) {
    return _firstText(
      spell && spell.damagePreview,
      spell && spell.rollConfig && spell.rollConfig.damageFormula,
      spell && spell.rollConfig && spell.rollConfig.damage_formula,
      spell && spell.roll_config && spell.roll_config.damage_formula,
      spell && spell.damageFormula,
      spell && spell.damage_formula,
      spell && spell.healingPreview,
      spell && spell.rollConfig && spell.rollConfig.healingFormula,
      spell && spell.rollConfig && spell.rollConfig.healing_formula,
      spell && spell.roll_config && spell.roll_config.healing_formula,
      spell && spell.healingFormula,
      spell && spell.healing_formula,
      ''
    );
  }

  function _spellRollKind(spell) {
    return _firstText(
      spell && spell.healingFormula,
      spell && spell.healing_formula,
      spell && spell.healingPreview,
      spell && spell.rollConfig && spell.rollConfig.healingFormula,
      spell && spell.rollConfig && spell.rollConfig.healing_formula,
      spell && spell.roll_config && spell.roll_config.healing_formula,
      ''
    ) ? 'healing' : 'damage';
  }

  function _looksRollableFormula(expr) {
    const text = String(expr || '').trim();
    return !!text && /\d+d\d+/i.test(text);
  }

  function _spellUpcastScaling(spell) {
    const text = _firstText(spell && spell.scalingNote, spell && spell.higherLevel, spell && spell.atHigherLevels, '');
    if (!text) return null;
    let match = text.match(/add\s+(\d+)d(\d+)\s+to(?: the)?(?: main)?(?: damage| healing)? roll\s+for each slot level above/i);
    if (!match) match = text.match(/increase(?:s)?(?: the main)?(?: damage| healing)? roll to .*? and add\s+(\d+)d(\d+)\s+for each slot level above/i);
    if (!match) match = text.match(/for each slot level above[^.]*?(\d+)d(\d+)/i);
    if (!match) return null;
    return { count: parseInt(match[1], 10) || 0, sides: parseInt(match[2], 10) || 0 };
  }

  function _spellHasSlotScaling(spell) {
    const card = (spell && spell.card) || spell || {};
    const scalingText = _firstText(card.slot_damage, card.slot_healing, card.extra_ray_per_slot, card.damage_upcast_per_level, card.scalingNote, card.higherLevel, card.atHigherLevels, card.higher_levels, '');
    if (scalingText) return true;
    const name = String(card.name || spell && spell.name || '').trim().toLowerCase();
    return ['fireball', 'lightning bolt', 'call lightning', 'scorching ray'].includes(name);
  }

  function _spellRollExpressionForLevel(spell, slotLevel, charData) {
    const castLevel = parseInt(slotLevel, 10) || _spellDisplayCastLevel(spell);
    const runtimeBuiltinBase = (global.AppSpellRuntime && typeof global.AppSpellRuntime.getBuiltinSpellBaseLevel === 'function')
      ? global.AppSpellRuntime.getBuiltinSpellBaseLevel(spell || {})
      : null;
    const baseLevel = runtimeBuiltinBase !== null ? runtimeBuiltinBase : _spellBaseLevel(spell);
    const normalizedBase = Number.isFinite(baseLevel) ? baseLevel : _spellLevelNumber(spell);
    const preview = _firstText(spell && spell.damagePreview, spell && spell.healingPreview, '');
    let formula = '';
    if (global.AppSpellRuntime && typeof global.AppSpellRuntime.resolveSpellRuntime === 'function') {
      const card = (spell && spell.card) || spell || {};
      const resolverCard = Object.assign({}, card, spell || {}, {
        id: _firstText(spell && spell.id, card && card.id, ''),
        name: _firstText(spell && spell.name, card && card.name, ''),
        level: normalizedBase,
        spell_level: normalizedBase,
        baseLevel: normalizedBase,
        castLevel: castLevel,
        slotLevel: castLevel,
      });
      const runtime = global.AppSpellRuntime.resolveSpellRuntime(resolverCard, {
        castLevel: castLevel,
        slotLevel: castLevel,
        characterLevel: _characterLevel(charData),
        spellcastingModifier: (charData && charData.spellcastingModifier),
        saveDc: charData && (charData.spellSaveDc || charData.spell_save_dc)
      });
      formula = String(runtime.finalHealingFormula || runtime.finalDamageFormula || '').trim();
      if ((global.__DEV__ || global.DEBUG_SPELLS) && global.console && typeof global.console.debug === 'function') {
        global.console.debug('[SpellsTab] spell roll expression', { spell: _spellName(spell), baseLevel: runtime.baseLevel, castLevel: runtime.castLevel, formula: formula });
      }
    }
    if (formula) return formula;
    if (preview) {
      const baseFormula = String(_spellRollBaseExpression(Object.assign({}, spell || {}, { castLevel: normalizedBase, slotLevel: normalizedBase })) || '').trim();
      if (!(castLevel > normalizedBase && preview === baseFormula && _spellHasSlotScaling(spell))) return preview;
    }
    return String(_spellRollBaseExpression(spell) || '').trim();
  }

  function _pickSpellCastLevel(spell) {
    const baseLevel = (spell && spell.baseLevel != null) ? parseInt(spell.baseLevel, 10) : _spellLevelNumber(spell);
    if (spell && spell.isVirtualCastRow && spell.castLevel != null) return parseInt(spell.castLevel, 10);
    const levels = _safeArray(spell && spell.availableCastLevels).map(function (lvl) { return parseInt(lvl, 10); }).filter(function (lvl) { return Number.isFinite(lvl) && lvl >= baseLevel; });
    if (baseLevel <= 0 || levels.length <= 1 || typeof global.prompt !== 'function') return baseLevel;
    const defaultLevel = String(baseLevel);
    const response = global.prompt('Cast ' + _spellName(spell) + ' at which slot level? Available: ' + levels.join(', '), defaultLevel);
    if (response == null) return null;
    const chosen = parseInt(String(response || '').trim(), 10);
    if (!levels.includes(chosen)) return null;
    return chosen;
  }

  function _renderSpellCombatResult(spell, expr, finalResult, kind, slotLevel) {
    const result = finalResult;
    if (typeof global._showCombatResultCard === 'function') {
      const baseLevel = _spellLevelNumber(spell);
      const slotText = slotLevel > 0 ? ('Level ' + slotLevel) : 'Cantrip';
      global._showCombatResultCard({
        title: _spellName(spell),
        subtitle: baseLevel > 0 ? (slotText + ' ' + kind + ' roll') : (kind + ' roll'),
        outcome: 'hit',
        damage: result && Number.isFinite(result.total) ? result.total : null,
        damageRolls: result && Array.isArray(result.rolls) ? result.rolls : null,
        damageType: kind === 'healing' ? 'healing' : _firstText(spell && spell.damageType, '')
      });
    }

  }

  function _renderFallbackLocalDiceResult(spell, expr, result, kind) {
    if (global.AppDice && typeof global.AppDice.showLocalResult === 'function') {
      const previewMeta = typeof global._dicePreviewMetaFromExpr === 'function' ? global._dicePreviewMetaFromExpr(expr, result) : {};
      global.AppDice.showLocalResult({
        diceType: previewMeta && previewMeta.diceType,
        qty: previewMeta && previewMeta.qty,
        rolls: result && Array.isArray(result.rolls) ? result.rolls : [],
        total: result && Number.isFinite(result.total) ? result.total : 0,
        modifier: previewMeta && previewMeta.modifier,
        rollLabel: _spellName(spell) + ' • ' + (kind === 'healing' ? 'Healing Roll' : 'Damage Roll'),
        source: 'character-sheet-spell-roll',
        visualDisabled: true
      });
    } else if (typeof global._dicePreviewMetaFromExpr === 'function' && typeof global._showLegacySyncedLocalDiceResult === 'function') {
      const previewMeta = global._dicePreviewMetaFromExpr(expr, result);
      global._showLegacySyncedLocalDiceResult({
        diceType: previewMeta && previewMeta.diceType,
        qty: previewMeta && previewMeta.qty,
        rolls: result && Array.isArray(result.rolls) ? result.rolls : [],
        total: result && Number.isFinite(result.total) ? result.total : 0,
        modifier: previewMeta && previewMeta.modifier,
        rollLabel: _spellName(spell) + ' • ' + (kind === 'healing' ? 'Healing Roll' : 'Damage Roll'),
        source: 'character-sheet-spell-roll',
        visualDisabled: true
      });
    } else if (typeof global.appDiceShowLocalResult === 'function') {
      global.appDiceShowLocalResult({
        diceType: 20,
        qty: 1,
        rolls: result && Array.isArray(result.rolls) ? result.rolls : [],
        total: result && Number.isFinite(result.total) ? result.total : 0,
        modifier: 0,
        rollLabel: _spellName(spell) + ' • ' + (kind === 'healing' ? 'Healing Roll' : 'Damage Roll'),
        source: 'character-sheet-spell-roll',
        visualDisabled: true
      });
    }
  }

  function _showRolledSpellResult(spell, expr, result, kind, slotLevel, opts) {
    opts = opts || {};
    _renderSpellCombatResult(spell, expr, result, kind, slotLevel);
    if (opts.visualAlreadyResolved === true) return;
    _renderFallbackLocalDiceResult(spell, expr, result, kind);
  }



  function _rollSpellAttackFromUi(spell, state) {
    if (!spell) return { ok: false, reason: 'missing_spell' };
    const attackKind = _spellAttackKind(spell);
    const attackBonus = _spellAttackBonusValue(spell, state && state.charData);
    if (!attackKind || attackBonus == null) {
      return { ok: false, reason: 'not_attack_spell' };
    }
    if (attackKind === 'weapon') {
      return { ok: false, reason: 'weapon_attack_spell' };
    }
    const hasDisadvantage = typeof global._combatAttackHasEncumbranceDisadvantage === 'function'
      ? !!global._combatAttackHasEncumbranceDisadvantage()
      : false;
    const rollA = Math.floor(Math.random() * 20) + 1;
    const rollB = hasDisadvantage ? (Math.floor(Math.random() * 20) + 1) : null;
    const d20 = hasDisadvantage ? Math.min(rollA, rollB) : rollA;
    const total = d20 + (attackBonus || 0);
    const target = global._combat && global._combat.selected_target_id && global.tokens
      ? global.tokens[global._combat.selected_target_id]
      : null;
    const targetAc = Number(target && target.ac);
    const outcome = d20 === 20
      ? 'crit'
      : d20 === 1
        ? 'miss'
        : (Number.isFinite(targetAc) && targetAc > 0 ? (total >= targetAc ? 'hit' : 'miss') : 'hit');
    const attackBonusStr = attackBonus != null ? (attackBonus >= 0 ? `+${attackBonus}` : String(attackBonus)) : null;
    if (typeof global._showCombatResultCard === 'function') {
      global._showCombatResultCard({
        title: _spellName(spell),
        subtitle: target && target.name ? `spell attack vs ${target.name}` : 'spell attack roll',
        attackRoll: d20,
        attackBonusStr: attackBonusStr,
        attackTotal: total,
        altRoll: rollB,
        disadvantage: hasDisadvantage,
        outcome: outcome,
      });
    }
    if (global.AppDice && typeof global.AppDice.showLocalResult === 'function') {
      global.AppDice.showLocalResult({
        diceType: 20,
        qty: 1,
        rolls: [d20],
        total,
        modifier: attackBonus || 0,
        rollLabel: `${_spellName(spell)} • Spell Attack`,
        source: 'sheet-spell-attack'
      });
    } else if (typeof global.appDiceShowLocalResult === 'function') {
      global.appDiceShowLocalResult({
        diceType: 20,
        qty: 1,
        rolls: [d20],
        total,
        modifier: attackBonus || 0,
        rollLabel: `${_spellName(spell)} • Spell Attack`,
        source: 'sheet-spell-attack'
      });
    }
    if (typeof global.sendWS === 'function') {
      let msg = `✨ **${_spellName(spell)}** — To Hit: ${total} (d20:${d20}${attackBonusStr || ''})`;
      msg += outcome === 'crit' ? ' ⚡CRIT!' : outcome === 'miss' ? ' ✕Miss' : ' ✔Hit';
      if (target && target.name) msg += ` vs **${String(target.name)}**`;
      global.sendWS({ type: 'chat_message', payload: { message: msg, channel: 'everyone' } });
    }
    if (typeof global.showToast === 'function') {
      global.showToast(`${_spellName(spell)} attack rolled.`);
    }
    return { ok: true, total: total, outcome: outcome };
  }

  async function _rollSpellFromUi(spell, state, opts) {
    opts = opts || {};
    if (!spell) return { ok: false, reason: 'missing_spell' };
    const forcedCastLevel = parseInt(opts.forcedCastLevel, 10);
    const slotLevel = Number.isFinite(forcedCastLevel) && forcedCastLevel >= 0 ? forcedCastLevel : _pickSpellCastLevel(spell);
    if (slotLevel == null) return { ok: false, reason: 'cancelled' };
    const forcedExpr = String(opts.forcedExpr || '').trim();
    const expr = _looksRollableFormula(forcedExpr) ? forcedExpr : _spellRollExpressionForLevel(spell, slotLevel, state && state.charData);
    if (!_looksRollableFormula(expr)) return { ok: false, reason: 'no_formula' };
    let result = null;
    const kind = _spellRollKind(spell);
    if (global.AppDice && typeof global.AppDice.rollExpressionAndResolve === 'function') {
      result = await global.AppDice.rollExpressionAndResolve(expr, {
        rollLabel: _spellName(spell) + ' • ' + (kind === 'healing' ? 'Healing Roll' : 'Damage Roll'),
        source: 'character-sheet-spell-roll'
      });
      if (!result) return { ok: false, reason: 'bad_formula' };
      _renderSpellCombatResult(spell, expr, result, kind, slotLevel || _spellLevelNumber(spell));
      return { ok: true, total: result.total, expr: expr };
    }
    if (typeof global._rollDiceExpr !== 'function') return { ok: false, reason: 'no_formula' };
    result = global._rollDiceExpr(expr);
    if (!result) return { ok: false, reason: 'bad_formula' };
    _renderSpellCombatResult(spell, expr, result, kind, slotLevel || _spellLevelNumber(spell));
    _renderFallbackLocalDiceResult(spell, expr, result, kind);
    return { ok: true, total: result.total, expr: expr };
  }

  function _profileContext(charData) {
    return {
      profileId: _firstText(charData && (charData.profileId || charData.profile_id || charData.id), ''),
      sessionId: _firstText(charData && (charData.sessionId || charData.session_id), ''),
      userId: _firstText(global && global.USER_ID, '')
    };
  }

  function _fetchSpellDetail(spell, charData) {
    const spellId = String(spell && (spell.id || spell.spellId) || '').trim();
    if (!spellId) return Promise.resolve(spell);
    const ctx = _profileContext(charData || {});
    const params = new URLSearchParams();
    if (ctx.profileId) params.set('profile_id', ctx.profileId);
    if (ctx.sessionId) params.set('session_id', ctx.sessionId);
    if (ctx.userId) params.set('user_id', ctx.userId);
    return fetch('/api/spells/' + encodeURIComponent(spellId) + (params.toString() ? ('?' + params.toString()) : ''), { credentials: 'same-origin' })
      .then(function (res) { return res.ok ? res.json() : Promise.reject(res.status); })
      .then(function (json) { return (json && json.spell) ? json.spell : spell; })
      .catch(function () { return spell; });
  }

  function _openSpellDetails(spell, charData) {
    if (!spell) return;
    _fetchSpellDetail(spell, charData).then(function (resolved) {
      const mergedSpell = Object.assign({}, spell || {}, resolved || {});
      if (global.CSContainer && typeof global.CSContainer.openDetailDrawer === 'function') {
        global.CSContainer.openDetailDrawer({
          kicker: 'Spell',
          title: _spellName(mergedSpell),
          subtitle: _spellSubtitle(mergedSpell) || 'Spell',
          chips: [
            _spellLevelNumber(mergedSpell) === 0 ? 'At Will' : _spellRankLabel(mergedSpell),
            mergedSpell.concentration || mergedSpell.is_concentration ? 'Concentration' : '',
            mergedSpell.ritual ? 'Ritual' : '',
            _meaningful(mergedSpell.school) ? mergedSpell.school : ''
          ].filter(Boolean),
          sections: [
            { title: 'Full Text', body: mergedSpell.fullPlayerDetailText || mergedSpell.description || mergedSpell.higherLevel || mergedSpell.shortDescription || 'No detailed spell text is loaded for this entry yet.' },
            { title: 'At a Glance', body: _spellQuickRead(mergedSpell) },
            { title: 'Casting', items: _spellPlayerRules(mergedSpell) },
            { title: 'Roll / Effect', items: _spellCombatRows(mergedSpell) },
            { title: 'Higher Levels', items: _spellScalingRows(mergedSpell) }
          ]
        });
      } else if (global.SpellModal && global.SpellModal.openSpellModal) {
        global.SpellModal.openSpellModal(mergedSpell);
      }
    });
  }

  function _renderSummaryCard(label, value, note, accent) {
    return '<div class="cs-combat-summary-card' + (accent ? ' ' + _esc(accent) : '') + '"><div class="cs-combat-summary-label">' + _esc(label) + '</div><div class="cs-combat-summary-value">' + _esc(value) + '</div><div class="cs-combat-summary-note">' + _esc(note || '') + '</div></div>';
  }

  function _renderSlotsRow(charData) {
    const pact = _pactMagicState(charData);
    if (pact.enabled && pact.slotCount > 0) {
      const used = _getUsedSlots(charData);
      const usedCount = parseInt(used[pact.slotLevel] || 0, 10) || 0;
      const available = Math.max(0, pact.slotCount - usedCount);
      const pips = Array.from({ length: pact.slotCount }, function (_, i) {
        const avail = i < available;
        return '<button class="cs-slot-pip ' + (avail ? 'available' : 'used') + '" aria-label="Pact slot ' + (i + 1) + ' of level ' + pact.slotLevel + ' ' + (avail ? '(available)' : '(used)') + '" data-slot-level="' + _esc(String(pact.slotLevel)) + '" data-slot-index="' + _esc(String(i)) + '"></button>';
      }).join('');
      return '<div class="cs-slots-row" aria-label="Pact magic slots"><div class="cs-slot-group"><span class="cs-slot-label">PACT L' + _esc(String(pact.slotLevel || '?')) + '</span><div class="cs-slot-pips">' + pips + '</div></div></div>';
    }
    const slots = _getSlotCounts(charData);
    const used = _getUsedSlots(charData);
    const groups = [];
    for (let lvl = 1; lvl <= 9; lvl += 1) {
      const total = slots[lvl] || 0;
      if (!total) continue;
      const usedCount = used[lvl] || 0;
      const pips = Array.from({ length: total }, function (_, i) {
        const avail = i < (total - usedCount);
        return '<button class="cs-slot-pip ' + (avail ? 'available' : 'used') + '" aria-label="Slot ' + (i + 1) + ' of level ' + lvl + ' ' + (avail ? '(available)' : '(used)') + '" data-slot-level="' + _esc(String(lvl)) + '" data-slot-index="' + _esc(String(i)) + '"></button>';
      }).join('');
      groups.push('<div class="cs-slot-group"><span class="cs-slot-label">' + _esc(LEVEL_LABELS[lvl + 1] || ('L' + lvl)) + '</span><div class="cs-slot-pips">' + pips + '</div></div>');
    }
    return groups.length ? '<div class="cs-slots-row" aria-label="Spell slots">' + groups.join('') + '</div>' : '';
  }

  function _highestAvailableSpellLevel(state) {
    let highest = 0;
    const pools = []
      .concat(_safeArray(state && state.librarySpells))
      .concat(_safeArray(state && state.manifest && state.manifest.cards))
      .concat(_safeArray(state && state.linkedSpells));
    pools.forEach(function (spell) {
      if (!spell) return;
      if (spell.isAccessible === false && !spell.isKnown && !spell.isPrepared && !spell.__source) return;
      const level = _spellLevelNumber(spell);
      if (level > highest) highest = level;
    });
    const slotMap = state && state.manifest && state.manifest.limits && state.manifest.limits.spellSlots;
    if (slotMap && typeof slotMap === 'object') {
      Object.keys(slotMap).forEach(function (key) {
        const amount = parseInt(slotMap[key], 10) || 0;
        if (!amount) return;
        const match = String(key).match(/(\d+)/);
        const level = match ? parseInt(match[1], 10) : 0;
        if (level > highest) highest = level;
      });
    }
    return highest;
  }

  function _availableFilterLabels(state) {
    const highest = _highestAvailableSpellLevel(state);
    const labels = ['ALL'];
    if (_selectedSpells(Object.assign({}, state, { filter: 'ALL', query: '' })).some(function (spell) { return _spellLevelNumber(spell) === 0; })) labels.push('CANTRIP');
    for (let level = 1; level <= highest; level += 1) {
      if (LEVEL_LABELS[level + 1]) labels.push(LEVEL_LABELS[level + 1]);
    }
    return labels;
  }

  function _renderFilters(activeFilter, state) {
    const labels = Array.from(new Set(_availableFilterLabels(state)));
    return '<div class="cs-spell-filters" role="group" aria-label="Filter by spell level">' + labels.map(function (label) {
      return '<button class="cs-filter-chip' + (label === activeFilter ? ' active' : '') + '" data-filter="' + _esc(label) + '">' + _esc(label) + '</button>';
    }).join('') + '</div>';
  }

  function _renderSearch(placeholder) {
    return '<div class="cs-spell-search-wrap"><span class="cs-spell-search-icon" aria-hidden="true">&#128269;</span><input class="cs-spell-search" type="search" placeholder="' + _esc(placeholder || 'Search spells…') + '" autocomplete="off" aria-label="Search spells"></div>';
  }

  function _normalizeLinkedSpellCards(charData) {
    var seed = _safeArray(charData && charData.rulesSpellCards);
    if (!seed.length && typeof global._getStructuredRulesSpellbookCards === 'function') seed = _safeArray(global._getStructuredRulesSpellbookCards());
    if (!seed.length) {
      seed = _safeArray(charData && charData.spellbookEntries).map(function (entry, idx) {
        return {
          id: String(entry && (entry.id || entry.name) || ('linked-spell-' + idx)),
          name: _spellName(entry),
          description: entry && (entry.description || entry.effect || ''),
          range: entry && (entry.range || ''),
          castingTime: entry && (entry.time || entry.casting_time || '1 action'),
          level: _spellLevelNumber(entry),
          spell_level: _spellLevelNumber(entry),
          __source: 'linked'
        };
      });
    }
    return _safeArray(seed).map(function (spell) {
      return Object.assign({}, spell, {
        __source: spell && spell.__source ? spell.__source : 'linked',
        displayName: _spellName(spell),
        level: _spellLevelNumber(spell)
      });
    });
  }

  function _mergeSpellArrays(primary, secondary) {
    const byId = new Map();
    _safeArray(secondary).forEach(function (spell) {
      byId.set(String(spell && (spell.id || _spellName(spell)) || '').toLowerCase(), Object.assign({}, spell));
    });
    _safeArray(primary).forEach(function (spell) {
      const key = String(spell && (spell.id || _spellName(spell)) || '').toLowerCase();
      const existing = byId.get(key) || {};
      byId.set(key, Object.assign({}, existing, spell));
    });
    return Array.from(byId.values());
  }

  function _matchesSpellFilter(spell, filter, query) {
    const level = _spellLevelNumber(spell);
    if (filter && filter !== 'ALL') {
      if (filter === 'CANTRIP' && level !== 0) return false;
      if (filter !== 'CANTRIP' && String(level) !== String(LEVEL_LABEL_TO_KEY[filter] || '-1')) return false;
    }
    if (query) {
      const hay = [_spellName(spell), spell.school, spell.description, spell.damageType, spell.damage_type, spell.damageFormula, spell.damage_formula, spell.effect, spell.effect_text, spell.base_effect_text].filter(Boolean).join(' ').toLowerCase();
      if (hay.indexOf(String(query).toLowerCase()) === -1) return false;
    }
    return true;
  }

  function _selectionMode(limits) {
    if (limits && limits.preparedLimit != null) return 'prepared';
    if (limits && (limits.spellsKnown != null || limits.cantripsKnown != null)) return 'known';
    return 'library';
  }

  function _manifestHasTrackedSelections(state) {
    const manifest = state && state.manifest ? state.manifest : {};
    return _safeArray(manifest.known).length > 0 || _safeArray(manifest.prepared).length > 0;
  }


  function _currentKnownIdsFromState(state) {
    const ids = new Set(_safeArray(state && state.manifest && state.manifest.known).map(function (id) { return String(id || '').trim(); }).filter(Boolean));
    const cards = _mergeSpellArrays(_safeArray(state && state.manifest && state.manifest.cards), _safeArray(state && state.linkedSpells));
    cards.forEach(function (spell) {
      const spellId = String(spell && spell.id || '').trim();
      if (!spellId) return;
      if (spell.isKnown || (_spellLevelNumber(spell) === 0 && spell.isPrepared)) ids.add(spellId);
    });
    return Array.from(ids);
  }

  function _currentPreparedIdsFromState(state) {
    const ids = new Set(_safeArray(state && state.manifest && state.manifest.prepared).map(function (id) { return String(id || '').trim(); }).filter(Boolean));
    const cards = _mergeSpellArrays(_safeArray(state && state.manifest && state.manifest.cards), _safeArray(state && state.linkedSpells));
    cards.forEach(function (spell) {
      const spellId = String(spell && spell.id || '').trim();
      if (!spellId) return;
      if (spell.isPrepared && _spellLevelNumber(spell) > 0) ids.add(spellId);
    });
    return Array.from(ids);
  }

  function _spellIsSelectedInPlayView(spell, state) {
    const limits = (state && state.manifest && state.manifest.limits) || {};
    const mode = _selectionMode(limits);
    const level = _spellLevelNumber(spell);
    const hasTrackedSelections = _manifestHasTrackedSelections(state);
    if (mode === 'prepared') {
      if (level === 0) return !!(spell && (spell.isKnown || spell.isPrepared || (!hasTrackedSelections && spell.__source)));
      return !!(spell && (spell.isPrepared || (!hasTrackedSelections && spell.__source)));
    }
    if (mode === 'known') {
      return !!(spell && (spell.isKnown || (!hasTrackedSelections && spell.__source)));
    }
    return !!(spell && (spell.isKnown || spell.isPrepared || spell.__source));
  }

  function _selectedSpells(state) {
    const sourceCards = _safeArray(state.manifest && state.manifest.cards).length
      ? _mergeSpellArrays(_safeArray(state.manifest.cards), state.linkedSpells)
      : state.linkedSpells.slice();
    let selected = sourceCards.filter(function (spell) {
      return _spellIsSelectedInPlayView(spell, state);
    });
    if (!selected.length && !sourceCards.length && typeof global._currentSpellSelectionNames === 'function') {
      selected = _safeArray(global._currentSpellSelectionNames(state && state.charData)).map(function (name, idx) {
        return { id: 'selected-fallback-' + idx, name: name, displayName: name, level: 0, spell_level: 0, __source: 'selected-fallback' };
      });
    }
    return selected.filter(function (spell) { return _matchesSpellFilter(spell, state.filter, state.query); });
  }


  function _selectedSpellCount(state) {
    return _selectedSpells(Object.assign({}, state, { filter: 'ALL', query: '' })).length;
  }

  function _spellRowCastLevel(spell) {
    return _spellDisplayCastLevel(spell);
  }

  function _renderSpellRow(spell, actionsHtml, charData) {
    const isConc = Boolean(spell.concentration || spell.is_concentration);
    const isRitual = Boolean(spell.ritual);
    const effect = _spellEffectLabel(spell);
    const hitDcHtml = _spellAttackSaveCell(spell, charData);
    const range = _spellTableRangeLabel(spell);
    const rowCastLevel = _spellRowCastLevel(spell);
    const rollExpr = _spellRollExpressionForLevel(spell, rowCastLevel, charData);
    const canRoll = _looksRollableFormula(rollExpr);
    const effectHtml = canRoll
      ? ('<button type="button" class="cs-spell-roll-btn" data-spell-roll="' + _esc(String(spell.id || spell.rowId || _spellName(spell) || '')) + '" data-row-id="' + _esc(String(spell.rowId || '')) + '" data-cast-level="' + _esc(String(rowCastLevel)) + '" data-roll-expr="' + _esc(String(rollExpr)) + '" aria-label="Roll ' + _esc(_spellName(spell)) + '">' + _esc(String(rollExpr)) + ' 🎲</button>' + (String(effect) && String(effect) !== String(rollExpr) ? '<span class="cs-spell-effect-copy">' + _esc(String(effect)) + '</span>' : ''))
      : _esc(String(effect));

    // Upcast scaling badge — show when the spell can be cast at higher levels for extra effect
    const baseLevel = _spellLevelNumber(spell);
    const scalingText = _firstText(spell && spell.scalingNote, spell && spell.higherLevel, spell && spell.atHigherLevels, spell && spell.higher_levels, '');
    let upcastHtml = '';
    if (baseLevel > 0 && scalingText) {
      const upcast = _spellUpcastScaling(spell);
      const tooltip = scalingText.length > 120 ? scalingText.slice(0, 117) + '…' : scalingText;
      if (upcast && upcast.count > 0) {
        upcastHtml = '<span class="cs-spell-upcast-pill" title="' + _esc(tooltip) + '">+' + upcast.count + 'd' + upcast.sides + '/lvl ↑</span>';
      } else {
        upcastHtml = '<span class="cs-spell-upcast-pill" title="' + _esc(tooltip) + '">↑ scales</span>';
      }
    }

    return '<div class="cs-spell-row" data-spell-id="' + _esc(String(spell.id || _spellName(spell) || '')) + '" tabindex="0" role="button" aria-label="' + _esc(_spellName(spell)) + '">' +
      '<div class="cs-spell-cell"><span class="cs-spell-name">' + _esc(_spellName(spell)) + '</span>' + (isConc ? '<span class="cs-spell-indicator" title="Concentration">●</span>' : '') + (isRitual ? '<span class="cs-spell-indicator ritual" title="Ritual">ℝ</span>' : '') + '</div>' +
      '<div class="cs-spell-cell cs-spell-time">' + _esc(_abbrevTime(spell.castingTime || spell.casting_time)) + '</div>' +
      '<div class="cs-spell-cell cs-spell-range cs-col-range">' + _esc(range) + '</div>' +
      '<div class="cs-spell-cell cs-spell-hitdc">' + hitDcHtml + '</div>' +
      '<div class="cs-spell-cell cs-spell-effect">' + effectHtml + upcastHtml + '</div>' +
      (actionsHtml ? '<div class="cs-spell-cell cs-spell-actions-cell">' + actionsHtml + '</div>' : '') +
      '</div>';
  }

  function _renderSpellTable(spells, includeActions, actionBuilder, charData) {
    if (!spells || !spells.length) return '<div class="cs-empty-state"><span class="cs-empty-state-icon">📖</span><span>No spells found</span></div>';
    const byLevel = {};
    spells.forEach(function (spell) {
      const key = _spellLevelNumber(spell);
      if (!byLevel[key]) byLevel[key] = [];
      byLevel[key].push(spell);
    });
    const levelOrder = Object.keys(byLevel).map(Number).sort(function (a, b) { return a - b; });
    const groups = [];
    levelOrder.forEach(function (lvl) {
      const label = lvl === 0 ? 'Cantrips' : (LEVEL_LABELS[lvl + 1] || ('Level ' + lvl)) + ' Spells';
      const levelRows = byLevel[lvl].map(function (spell) {
        return _renderSpellRow(spell, includeActions && typeof actionBuilder === 'function' ? actionBuilder(spell) : '', charData || (actionBuilder && actionBuilder.__charData) || null);
      }).join('');
      groups.push('<section class="cs-spell-level-group"><div class="cs-spell-level-header">' + _esc(label) + '</div><div class="cs-spell-level-rows">' + levelRows + '</div></section>');
    });
    return '<div class="cs-spell-table' + (includeActions ? '' : ' no-actions') + '" role="table">' +
      '<div class="cs-spell-table-head" role="row">' +
        '<div class="cs-spell-head-cell">Name</div>' +
        '<div class="cs-spell-head-cell">Time</div>' +
        '<div class="cs-spell-head-cell cs-col-range">Range</div>' +
        '<div class="cs-spell-head-cell">Attack / Save</div>' +
        '<div class="cs-spell-head-cell">Effect</div>' +
        (includeActions ? '<div class="cs-spell-head-cell cs-spell-head-actions" aria-hidden="true"></div>' : '') +
      '</div>' +
      groups.join('') +
      '</div>';
  }

  function _fetchManifest(state, cb) {
    const ctx = _profileContext(state.charData || {});
    const seededSpellState = state && state.charData && state.charData.spellState && typeof state.charData.spellState === 'object'
      ? state.charData.spellState
      : {};
    const seededManifest = {
      known: _safeArray(seededSpellState.known),
      prepared: _safeArray(seededSpellState.prepared),
      limits: {},
      cards: state.linkedSpells.slice()
    };
    if (!ctx.profileId || !ctx.sessionId) {
      state.manifest = seededManifest;
      cb(null, state.manifest);
      return;
    }
    function load(url) {
      return fetch(url, { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); });
    }
    const userIdQuery = ctx.userId ? ('&user_id=' + encodeURIComponent(ctx.userId)) : '';
    const baseUrl = '/api/character/' + encodeURIComponent(ctx.profileId) + '/spells?session_id=' + encodeURIComponent(ctx.sessionId) + userIdQuery;
    load(baseUrl)
      .catch(function () {
        return load('/api/character/' + encodeURIComponent(ctx.profileId) + '/spells/known?session_id=' + encodeURIComponent(ctx.sessionId) + userIdQuery);
      })
      .then(function (data) {
        const hasKnown = !!(data && Object.prototype.hasOwnProperty.call(data, 'known'));
        const hasPrepared = !!(data && Object.prototype.hasOwnProperty.call(data, 'prepared'));
        const hasCards = !!(data && Object.prototype.hasOwnProperty.call(data, 'cards'));
        state.manifest = {
          known: hasKnown ? _safeArray(data && data.known) : seededManifest.known,
          prepared: hasPrepared ? _safeArray(data && data.prepared) : seededManifest.prepared,
          limits: data && data.limits ? data.limits : {},
          validation: data && data.validation ? data.validation : {},
          cards: hasCards ? _safeArray(data && data.cards) : seededManifest.cards
        };
        cb(null, state.manifest);
      })
      .catch(function (err) {
        state.manifest = seededManifest;
        cb(err, state.manifest);
      });
  }

  function _fetchSpells(state, cb) {
    const params = new URLSearchParams();
    if (state.query) params.set('search', state.query);
    if (state.filter && state.filter !== 'ALL') {
      const levelKey = LEVEL_LABEL_TO_KEY[state.filter];
      if (levelKey) params.set('level', levelKey);
    }
    const className = state.charData && (state.charData.className || (Array.isArray(state.charData.classes) && state.charData.classes[0] && state.charData.classes[0].name) || '');
    if (className) params.set('cls', className);
    const ctx = _profileContext(state.charData || {});
    if (ctx.profileId) params.set('profile_id', ctx.profileId);
    if (ctx.sessionId) params.set('session_id', ctx.sessionId);
    if (ctx.userId) params.set('user_id', ctx.userId);
    fetch('/api/spells?' + params.toString(), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (data) {
        state.librarySpells = _safeArray(Array.isArray(data) ? data : data && data.spells).filter(function (spell) {
          return !(spell && spell.isAccessible === false && !spell.isKnown && !spell.isPrepared);
        });
        if (data && data.manifest && !state.manifest) {
          state.manifest = data.manifest;
        }
        cb(null, state.librarySpells);
      })
      .catch(function (err) {
        state.librarySpells = [];
        cb(err, []);
      });
  }

  function _createState(charData) {
    const seeded = (charData && charData.spellState && typeof charData.spellState === 'object') ? charData.spellState : {};
    return {
      charData: charData || {},
      filter: 'ALL',
      query: '',
      linkedSpells: _normalizeLinkedSpellCards(charData || {}),
      librarySpells: [],
      manifest: { known: _safeArray(seeded.known), prepared: _safeArray(seeded.prepared), limits: {}, cards: [] },
      managerOpen: false,
      loading: false,
      saving: false,
      message: '',
      messageTone: ''
    };
  }

  function _limitSnapshot(state) {
    const limits = (state.manifest && state.manifest.limits) || {};
    const mode = _selectionMode(limits);
    const cards = _mergeSpellArrays(_safeArray(state.manifest && state.manifest.cards), state.linkedSpells);
    const cardsById = new Map(cards.map(function (spell) {
      return [String(spell && spell.id || '').trim(), spell];
    }).filter(function (entry) { return entry[0]; }));
    const manifestKnownIds = _safeArray(state && state.manifest && state.manifest.known)
      .map(function (id) { return String(id || '').trim(); })
      .filter(Boolean);
    const knownCantripCountFromManifest = manifestKnownIds.filter(function (spellId) {
      const knownSpell = cardsById.get(spellId);
      return knownSpell && _spellLevelNumber(knownSpell) === 0;
    }).length;
    const cantripCountFromCards = cards.filter(function (spell) { return _spellLevelNumber(spell) === 0 && _spellIsSelectedInPlayView(spell, state); }).length;
    const cantripCount = Math.max(cantripCountFromCards, knownCantripCountFromManifest);
    const preparedCount = cards.filter(function (spell) { return _spellLevelNumber(spell) > 0 && !!spell.isPrepared; }).length;
    const knownCount = cards.filter(function (spell) { return _spellLevelNumber(spell) > 0 && _spellIsSelectedInPlayView(spell, state); }).length;
    return {
      mode: mode,
      cantripCount: cantripCount,
      cantripLimit: limits.cantripsKnown,
      preparedCount: preparedCount,
      preparedLimit: limits.preparedLimit,
      knownCount: knownCount,
      knownLimit: limits.spellsKnown
    };
  }

  function _importedLimitWarnings(state) {
    const limits = state && state.manifest && state.manifest.limits && typeof state.manifest.limits === 'object' ? state.manifest.limits : {};
    const learning = limits.spellLearningLimits && typeof limits.spellLearningLimits === 'object' ? limits.spellLearningLimits : null;
    const warnings = learning && Array.isArray(learning.warnings) ? learning.warnings : [];
    return warnings.map(function (w) { return _firstText(w && w.message, ''); }).filter(Boolean);
  }

  function _renderManagerSummary(state) {
    const snap = _limitSnapshot(state);
    const cards = [];
    cards.push(_renderSummaryCard('Spell Mode', snap.mode === 'prepared' ? 'Prepare' : (snap.mode === 'known' ? 'Learn' : 'Library'), snap.mode === 'prepared' ? 'Pick cantrips you know, then prepare the leveled spells you want ready.' : (snap.mode === 'known' ? 'Learn cantrips and leveled spells until you hit your class limit.' : 'This class currently reads from a simple spell library.'), snap.mode === 'prepared' ? 'teal' : (snap.mode === 'known' ? 'gold' : 'violet')));
    if (snap.cantripLimit != null) cards.push(_renderSummaryCard('Cantrips', String(snap.cantripCount) + ' / ' + String(snap.cantripLimit), 'At-will spells you currently have.', 'violet'));
    if (snap.mode === 'prepared' && snap.preparedLimit != null) cards.push(_renderSummaryCard('Prepared', String(snap.preparedCount) + ' / ' + String(snap.preparedLimit), 'Leveled spells currently ready to cast.', 'teal'));
    if (snap.mode === 'known' && snap.knownLimit != null) cards.push(_renderSummaryCard('Known', String(snap.knownCount) + ' / ' + String(snap.knownLimit), 'Leveled spells you currently know.', 'gold'));
    const importWarnings = _importedLimitWarnings(state);
    importWarnings.forEach(function (message) {
      cards.push(_renderSummaryCard('Imported', message, 'Source data exceeds the internal class table; your imported count is preserved.', 'gold'));
    });
    return cards.join('');
  }

  function _managerActionForSpell(state, spell) {
    const level = _spellLevelNumber(spell);
    const snap = _limitSnapshot(state);
    const selectedCantrip = level === 0 && _spellIsSelectedInPlayView(spell, state);
    const selectedKnown = level > 0 && !!spell.isKnown;
    const selectedPrepared = level > 0 && !!spell.isPrepared;

    if (level === 0) {
      const overLimit = snap.cantripLimit != null && !selectedCantrip && snap.cantripCount >= snap.cantripLimit;
      return '<button type="button" class="cs-spell-manager-btn' + (selectedCantrip ? ' alt' : '') + '" data-spell-action="cantrip" data-spell-id="' + _esc(String(spell.id || '')) + '"' + (overLimit ? ' disabled title="Cantrip limit reached"' : '') + '>' + _esc(selectedCantrip ? 'Remove' : 'Learn Cantrip') + '</button>';
    }
    if (snap.mode === 'prepared') {
      const overLimit = snap.preparedLimit != null && !selectedPrepared && snap.preparedCount >= snap.preparedLimit;
      return '<button type="button" class="cs-spell-manager-btn' + (selectedPrepared ? ' alt' : '') + '" data-spell-action="prepared" data-spell-id="' + _esc(String(spell.id || '')) + '"' + (overLimit ? ' disabled title="Prepared limit reached"' : '') + '>' + _esc(selectedPrepared ? 'Unprepare' : 'Prepare') + '</button>';
    }
    if (snap.mode === 'known') {
      const overLimit = snap.knownLimit != null && !selectedKnown && snap.knownCount >= snap.knownLimit;
      return '<button type="button" class="cs-spell-manager-btn' + (selectedKnown ? ' alt' : '') + '" data-spell-action="known" data-spell-id="' + _esc(String(spell.id || '')) + '"' + (overLimit ? ' disabled title="Known spell limit reached"' : '') + '>' + _esc(selectedKnown ? 'Remove' : 'Learn Spell') + '</button>';
    }
    return '';
  }

  function _renderManager(state) {
    const snap = _limitSnapshot(state);
    const filtered = _safeArray(state.librarySpells).filter(function (spell) {
      const level = _spellLevelNumber(spell);
      const highest = _highestAvailableSpellLevel(state);
      if (spell.isAccessible === false && !spell.isKnown && !spell.isPrepared) return false;
      if (highest > 0 && level > highest && !spell.isKnown && !spell.isPrepared) return false;
      return _matchesSpellFilter(spell, state.filter, state.query);
    });
    const note = snap.mode === 'prepared'
      ? 'You only see spells unlocked for your class and level here. Cantrips are learned permanently; leveled spells below are the ones you prepare for the day.'
      : snap.mode === 'known'
        ? 'You only see spells unlocked for your class and level here. Learn cantrips and known spells until you hit your class limit.'
        : 'Use this list to manage the spells tied to this character.';
    return '<div class="cs-action-section cs-spell-manager">' +
      '<div class="cs-action-section-title">Spell Library</div><div class="cs-feature-section-copy">Manage Spells</div>' +
      '<div class="cs-feature-section-copy">' + _esc(note) + '</div>' +
      '<div class="cs-combat-hero-grid cs-spell-manager-grid">' + _renderManagerSummary(state) + '</div>' +
      '<div class="cs-inline-hint">Open the drawer on any spell to read the full text first, then use the button on the right to learn or prepare it.</div>' +
      '<div class="cs-spell-manager-table">' + _renderSpellTable(filtered, true, function (spell) { return _managerActionForSpell(state, spell); }, state.charData) + '</div>' +
      '</div>';
  }


  function _renderStructuredSpellSection(spells, concentrationName) {
    if (!spells || !spells.length) {
      return '<div class="cs-action-section"><div class="cs-action-section-title">Linked Spell Actions</div><div class="cs-empty-state compact"><span>No linked spell cards are loaded yet.</span></div></div>';
    }
    const concentrationText = concentrationName ? ('Active concentration: ' + concentrationName) : 'No concentration spell is currently active on your token.';
    return '<div class="cs-action-section" hidden><div class="cs-action-section-title">Linked Spell Actions</div><div class="cs-combat-callout-grid" style="margin-bottom:0.55rem;"><div class="cs-combat-callout"><div class="cs-combat-callout-title">Spell flow</div><div class="cs-combat-callout-copy">Check slots and concentration first, then use linked spell actions, then browse the wider spell library if you need additional options.</div></div><div class="cs-combat-callout muted"><div class="cs-combat-callout-title">Concentration status</div><div class="cs-combat-callout-copy">' + _esc(concentrationText) + '</div></div></div><div class="cs-inline-hint">Click any linked spell or library row to open a clean spell card with the important details first and the full rules text underneath.</div></div>';
  }

  function _spellCardMetaBits(spell, charData) {
    const bits = [];
    const subtitle = _spellSubtitle(spell);
    if (_meaningful(subtitle)) bits.push(subtitle);
    const time = _abbrevTime(spell && spell.castingTime);
    if (_meaningful(time)) bits.push(time);
    const range = _spellTargetingLabel(spell);
    if (_meaningful(range)) bits.push(range);
    const hitSave = String(_spellAttackSaveCell(spell, charData) || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    if (_meaningful(hitSave)) bits.push(hitSave);
    return bits;
  }

  function _spellCardBadgeHtml(spell) {
    const badges = [];
    badges.push('<span class="cs-resource-pill">' + _esc(_spellRankLabel(spell)) + '</span>');
    if (spell && (spell.concentration || spell.is_concentration)) badges.push('<span class="cs-resource-pill violet">Concentration</span>');
    if (spell && spell.ritual) badges.push('<span class="cs-resource-pill">Ritual</span>');
    if (spell && (spell.importedOnly || spell.source === 'imported' || spell.__source === 'imported')) badges.push('<span class="cs-resource-pill gold">Imported-only</span>');
    if (spell && spell.needsReview) badges.push('<span class="cs-resource-pill violet">Needs DM review</span>');
    if (spell && spell.__source === 'linked') badges.push('<span class="cs-resource-pill gold">Ready on map</span>');
    return badges.join('');
  }


  function _spellUseNowLabel(spell, charData) {
    if (_spellHasAttackRoll(spell, charData)) return 'Attack roll ready';
    if (_looksRollableFormula(_spellRollBaseExpression(spell))) return 'Effect roll ready';
    if (_spellCanCastFromCard(spell)) return 'Cast ready';
    return 'Reference only';
  }

  function _spellCardLanes(spell, charData) {
    const lanes = [
      { label: 'Attack / Save', value: _spellAttackSaveLabel(spell, charData) },
      { label: 'Effect', value: _spellEffectLabel(spell) },
      { label: 'Range', value: _spellTargetingLabel(spell) },
      { label: 'Use now', value: _spellUseNowLabel(spell, charData) }
    ];
    if (spell && spell.importedOnly && spell.needsReview) lanes.push({ label: 'Review', value: 'Needs DM review' });
    return lanes;
  }

  function _pulseRowFromTrigger(trigger) {
    const row = trigger && trigger.closest ? trigger.closest('.cs-spell-row, .cs-spell-card-row') : null;
    if (!row) return;
    row.classList.remove('cs-row-pulse');
    void row.offsetWidth;
    row.classList.add('cs-row-pulse');
    setTimeout(function () { row.classList.remove('cs-row-pulse'); }, 520);
  }


  function _spellCanCastFromCard(spell) {
    const key = String(spell && (spell.id || _spellName(spell) || '') || '').trim();
    return !!key && typeof global.castRulesSpell === 'function';
  }

  function _spellCanInspectFromCard(spell) {
    const key = String(spell && (spell.id || _spellName(spell) || '') || '').trim();
    return !!key && typeof global.playerInspectSpell === 'function';
  }

  function _spellCardActionHtml(spell, charData) {
    const spellKey = String(spell && (spell.id || _spellName(spell) || '') || '').trim();
    const castSpellKey = String(spell && (spell.spellId || (spell.card && spell.card.id) || spell.id || _spellName(spell) || '') || '').trim();
    const actions = [];
    if (_spellCanCastFromCard(spell)) actions.push('<button type="button" class="cs-feature-inspect" data-spell-cast="' + _esc(castSpellKey) + '" data-cast-level="' + _esc(String(spell && spell.castLevel != null ? spell.castLevel : (_spellLevelNumber(spell) || 0))) + '"' + (spell && spell.disabledReason ? ' disabled title="' + _esc(spell.disabledReason) + '"' : '') + '>Cast L' + _esc(String(spell && spell.castLevel != null ? spell.castLevel : (_spellLevelNumber(spell) || 0))) + '</button>');
    if (_spellHasAttackRoll(spell, charData)) actions.push('<button type="button" class="cs-feature-inspect" data-spell-attack="' + _esc(spellKey) + '">Attack</button>');
    const rowCastLevel = _spellRowCastLevel(spell);
    const rollExpr = _spellRollExpressionForLevel(spell, rowCastLevel, charData);
    if (_looksRollableFormula(rollExpr)) actions.push('<button type="button" class="cs-feature-inspect" data-spell-roll="' + _esc(spellKey) + '" data-row-id="' + _esc(String(spell && spell.rowId || '')) + '" data-cast-level="' + _esc(String(rowCastLevel)) + '" data-roll-expr="' + _esc(String(rollExpr)) + '">Roll Effect</button>');
    return actions.join('');
  }

  function _renderSelectedSpellCards(selected, charData) {
    if (!selected || !selected.length) return '<div class="cs-empty-state"><span class="cs-empty-state-icon">✨</span><span>No active spells ready on this character yet.</span></div>';
    const byLevel = {};
    selected.forEach(function (spell) {
      const lvl = _spellLevelNumber(spell);
      if (!byLevel[lvl]) byLevel[lvl] = [];
      byLevel[lvl].push(spell);
    });
    return Object.keys(byLevel).map(Number).sort(function (a, b) { return a - b; }).map(function (lvl) {
      const label = lvl === 0 ? 'Cantrips' : (LEVEL_LABELS[lvl + 1] || ('Level ' + lvl)) + ' Spells';
      const cards = byLevel[lvl].map(function (spell) {
        const spellKey = String(spell && (spell.id || _spellName(spell) || '') || '').trim();
        const summary = _spellQuickRead(spell);
        const meta = _spellCardMetaBits(spell, charData);
        const lanes = _spellCardLanes(spell, charData);
        return '<article class="cs-linked-spell-row cs-spell-card-row" data-spell-id="' + _esc(spellKey) + '" tabindex="0" role="button" aria-label="' + _esc(_spellName(spell)) + '">' +
          '<div class="cs-linked-spell-main">' +
            '<div class="cs-spell-card-topline">' +
              '<div>' +
                '<div class="cs-spell-kicker">' + _esc(_spellSubtitle(spell)) + '</div>' +
                '<div class="cs-linked-spell-name">' + _esc(_spellName(spell)) + '</div>' +
              '</div>' +
              '<div class="cs-spell-card-badges cs-spell-card-badges-inline">' + _spellCardBadgeHtml(spell) + '</div>' +
            '</div>' +
            '<div class="cs-spell-card-summary"><strong>' + _esc(summary) + '</strong></div>' +
            '<div class="cs-spell-lanes">' + lanes.map(function (lane) {
              return '<div class="cs-spell-lane"><span class="cs-spell-lane-label">' + _esc(lane.label) + '</span><span class="cs-spell-lane-value">' + _esc(lane.value || '—') + '</span></div>';
            }).join('') + '</div>' +
            (meta.length ? '<div class="cs-linked-spell-meta">' + _esc(meta.join(' • ')) + '</div>' : '') +
          '</div>' +
          '<div class="cs-linked-spell-side cs-spell-card-side">' +
            '<div class="cs-spell-card-actions">' + _spellCardActionHtml(spell, charData) + '</div>' +
          '</div>' +
        '</article>';
      }).join('');
      return '<div class="cs-spell-card-group"><div class="cs-spell-card-group-title">' + _esc(label) + '</div><div class="cs-linked-spell-stack cs-spell-card-stack">' + cards + '</div></div>';
    }).join('');
  }

  function _buildCastableRowsForState(state) {
    const selected = _selectedSpells(Object.assign({}, state, { filter: 'ALL', query: '' }));
    if (!(global.AppSpellRuntime && typeof global.AppSpellRuntime.buildCastableSpellRows === 'function')) return selected;
    const library = _mergeSpellArrays(_safeArray(state.librarySpells), _mergeSpellArrays(_safeArray(state.manifest && state.manifest.cards), state.linkedSpells));
    const built = global.AppSpellRuntime.buildCastableSpellRows(Object.assign({}, state.charData || {}, { manifest: state.manifest || {}, spellLibrary: library }), selected, library);
    state.castableSpellRows = _safeArray(built && built.rows);
    state.castableSpellDiagnostics = built && built.diagnostics ? built.diagnostics : {};
    return state.castableSpellRows;
  }

  function _renderSelectedSection(state) {
    const selected = _buildCastableRowsForState(state).filter(function (spell) { return _matchesSpellFilter(spell, state.filter, state.query); });
    const title = 'Castable Spells';
    const copy = 'D&D app-style rows are generated from your known/prepared spell manifest. Each row is already set to the slot level shown in its section, including higher-slot damage or effect previews.';
    return '<div class="cs-action-section"><div class="cs-action-section-title">' + _esc(title) + '</div><div class="cs-feature-section-copy">' + _esc(copy) + '</div><div class="cs-spell-manager-table">' + _renderSpellTable(selected, true, function (spell) { return _spellCardActionHtml(spell, state.charData); }, state.charData) + '</div></div>';
  }

  function _renderSpellsTab(container, state) {
    const concentration = _firstText(state.charData && state.charData.activeConcentration, '');
    const selected = _selectedSpells(state);
    const classKey = _classKey(state.charData || {});
    const pact = _pactMagicState(state.charData || {});
    const isSorcerer = _classKey(state.charData || {}) === 'sorcerer';
    const sorcerer = isSorcerer ? _sorcererInsights(state.charData || {}, state) : null;
    const model = _classSpellModelInsights(classKey, state, pact);
    const activeSlotTiers = _getSlotCounts(state.charData || {}).filter(function (count, idx) { return idx > 0 && count > 0; }).length;
    container.innerHTML = '' +
      '<div class="cs-combat-hero-grid">' +
        _renderSummaryCard('Spell Save DC', _firstText(state.charData && state.charData.spellSaveDc, '—'), _firstText(state.charData && state.charData.className, 'Spellcasting'), state.charData && state.charData.spellSaveDc ? 'teal' : '') +
        _renderSummaryCard('Spell Attack', _firstText(state.charData && state.charData.spellAttack, '—'), selected.length ? 'Attack-roll spells use this bonus.' : 'No spell attack bonus detected yet.', selected.length ? 'gold' : '') +
        _renderSummaryCard('Active Spells', String(_selectedSpellCount(state)), _selectedSpellCount(state) ? 'Known / prepared list is linked.' : 'Nothing selected yet.', _selectedSpellCount(state) ? 'violet' : '') +
        _renderSummaryCard('Concentration', concentration || 'None', concentration ? 'Active on this character now.' : 'No active concentration spell.', concentration ? 'violet' : '') +
        (isSorcerer ? _renderSummaryCard('Sorcery Points', (sorcerer && sorcerer.sorceryMax != null) ? ((sorcerer.sorceryCurrent != null ? sorcerer.sorceryCurrent : sorcerer.sorceryMax) + ' / ' + sorcerer.sorceryMax) : '—', 'Spend for Metamagic and Flexible Casting conversions.', (sorcerer && sorcerer.sorceryMax != null) ? 'gold' : '') : '') +
        (isSorcerer ? _renderSummaryCard('Spells Known', (sorcerer && sorcerer.knownLimit != null) ? (String(_limitSnapshot(state).knownCount) + ' / ' + sorcerer.knownLimit) : '—', 'Known-spell class: learned spells are persistent.', (sorcerer && sorcerer.knownLimit != null) ? 'violet' : '') : '') +
        (isSorcerer ? _renderSummaryCard('Cantrips', (sorcerer && sorcerer.cantripLimit != null) ? (String(_limitSnapshot(state).cantripCount) + ' / ' + sorcerer.cantripLimit) : '—', 'At-will sorcerer tools always ready.', (sorcerer && sorcerer.cantripLimit != null) ? 'teal' : '') : '') +
        (isSorcerer ? _renderSummaryCard('Metamagic', (sorcerer && sorcerer.metamagicChoices.length) ? sorcerer.metamagicChoices.length : 'Review', (sorcerer && sorcerer.metamagicChoices.length) ? sorcerer.metamagicChoices.join(', ') : 'Select and verify metamagic options in level-up/features.', (sorcerer && sorcerer.metamagicChoices.length) ? 'gold' : '') : '') +
        (pact.enabled ? _renderSummaryCard('Pact Slots', String(pact.slotCount || 0), (pact.slotLevel ? ('All cast at level ' + pact.slotLevel + '.') : 'Warlock pact slot economy.'), 'gold') : '') +
        (pact.enabled ? _renderSummaryCard('Pact Recovery', 'Short Rest', 'Pact slots refresh on Short Rest cadence.', 'teal') : '') +
        (pact.enabled ? _renderSummaryCard('Mystic Arcanum', 'Separate', 'Arcanum casts are not part of pact slot budgeting.', 'violet') : '') +
        model.cards.join('') +
      '</div>' +
      ((activeSlotTiers || concentration || pact.enabled || isSorcerer || model.hint) ? '<div class="cs-inline-hint">' + _esc(concentration ? ('Concentration: ' + concentration + ' • ') : '') + _esc(pact.enabled ? ('Pact Magic: ' + (pact.slotCount || 0) + ' slot(s) at level ' + (pact.slotLevel || '?') + ', refreshing on short rest. ') : '') + _esc(isSorcerer ? 'Sorcerer flow: cast from known spells, then spend Sorcery Points for Metamagic or Flexible Casting conversions. ' : '') + _esc(model.hint || '') + _esc(activeSlotTiers ? (activeSlotTiers + ' slot tiers are available for this character.') : 'Cantrips only are available right now.') + (pact.note ? (' ' + _esc(pact.note)) : '') + '</div>' : '') +
      _renderSlotsRow(state.charData) +
      '<div class="cs-spell-toolbar">' +
        _renderSearch(state.managerOpen ? 'Search spells you can add…' : 'Search your current spells…') +
        '<div class="cs-spell-toolbar-actions"><button type="button" class="cs-feature-inspect cs-manage-spells-btn">' + (state.managerOpen ? 'Close Manage Spells' : 'Manage Spells') + '</button></div>' +
      '</div>' +
      '<div class="cs-spell-filters-wrap">' + _renderFilters(state.filter, state) + '</div>' +
      (state.message ? '<div class="cs-inline-hint ' + _esc(state.messageTone || '') + '">' + _esc(state.message) + '</div>' : '') +
      _renderSelectedSection(state) +
      (state.managerOpen ? _renderManager(state) : '');
  }

  function _loadState(container, state) {
    state.loading = true;
    _fetchManifest(state, function () {
      _fetchSpells(state, function () {
        state.loading = false;
        _renderSpellsTab(container, state);
      });
    });
  }

  function _updateKnown(state, spellId, add) {
    const next = new Set(_currentKnownIdsFromState(state));
    if (add) next.add(spellId); else next.delete(spellId);
    return _saveSpellList(state, 'known', Array.from(next));
  }

  function _updatePrepared(state, spellId, add) {
    const next = new Set(_currentPreparedIdsFromState(state));
    if (add) next.add(spellId); else next.delete(spellId);
    return _saveSpellList(state, 'prepared', Array.from(next));
  }

  function _syncLocalSpellbookEntriesFromManifest(state) {
    const cards = _mergeSpellArrays(_safeArray(state && state.manifest && state.manifest.cards), _safeArray(state && state.linkedSpells));
    const nextEntries = cards.filter(function (spell) {
      return _spellIsSelectedInPlayView(spell, state);
    }).map(function (spell) {
      const spellId = String(spell && (spell.id || _spellName(spell) || '') || '').trim();
      const name = _spellName(spell);
      return { id: spellId || name, name: name };
    });
    if (state && state.charData && typeof state.charData === 'object') {
      state.charData.spellbookEntries = nextEntries.slice();
    }
    if (global._charSheet && typeof global._charSheet === 'object') {
      global._charSheet.spellbookEntries = nextEntries.slice();
    }
    state.linkedSpells = _normalizeLinkedSpellCards(state.charData || {});
  }

  function _saveSpellList(state, kind, list) {
    const ctx = _profileContext(state.charData || {});
    if (!ctx.profileId || !ctx.sessionId) return Promise.reject(new Error('No profile/session context available.'));
    state.saving = true;
    const path = kind === 'prepared' ? 'prepare' : 'known';
    const payload = { session_id: ctx.sessionId };
    payload[kind] = list;
    return fetch('/api/character/' + encodeURIComponent(ctx.profileId) + '/spells/' + path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          const detail = data && data.detail && data.detail.errors ? data.detail.errors.join(' ') : ((data && data.detail) ? String(data.detail) : 'Spell update failed.');
          throw new Error(detail);
        }
        return data;
      });
    }).then(function (data) {
      if (!state.manifest) state.manifest = {};
      state.manifest.limits = data && data.limits ? data.limits : (state.manifest.limits || {});
      state.manifest.validation = data && data.validation ? data.validation : (state.manifest.validation || {});
      if (kind === 'known') state.manifest.known = _safeArray(data && data.known);
      if (kind === 'prepared') state.manifest.prepared = _safeArray(data && data.prepared);
      const snap = _limitSnapshot(state);
      state.message = kind === 'known'
        ? ('Spell list updated. ' + (snap.knownLimit != null ? (String(snap.knownCount) + ' / ' + String(snap.knownLimit) + ' known spells.') : ''))
        : ('Prepared spells updated. ' + (snap.preparedLimit != null ? (String(snap.preparedCount) + ' / ' + String(snap.preparedLimit) + ' prepared.') : ''));
      state.messageTone = 'good';
      return new Promise(function (resolve) {
        if (!state.charData.spellState || typeof state.charData.spellState !== 'object') state.charData.spellState = {};
      state.charData.spellState[kind] = Array.isArray(data && data[kind]) ? data[kind].slice() : list.slice();
      if (global._charSheet && typeof global._charSheet === 'object') {
        if (!global._charSheet.spellState || typeof global._charSheet.spellState !== 'object') global._charSheet.spellState = {};
        global._charSheet.spellState[kind] = state.charData.spellState[kind].slice();
      }
      if (typeof global.requestCharacterBookOverviewRender === 'function') {
        try { global.requestCharacterBookOverviewRender('spells-tab-save'); } catch (_) {}
      }
      _fetchManifest(state, function () {
          _fetchSpells(state, function () {
            _syncLocalSpellbookEntriesFromManifest(state);
            state.saving = false;
            resolve();
          });
        });
      });
    }).catch(function (err) {
      state.saving = false;
      state.message = err && err.message ? err.message : 'Spell update failed.';
      state.messageTone = 'warn';
      throw err;
    });
  }

  function _bindSlotPips(container) {
    container.addEventListener('click', function (e) {
      const pip = e.target.closest('.cs-slot-pip');
      if (!pip) return;
      pip.classList.toggle('used');
      pip.classList.toggle('available');
      const isNowUsed = pip.classList.contains('used');
      pip.setAttribute('aria-label', pip.getAttribute('aria-label').replace(/(available|used)/, isNowUsed ? 'used' : 'available'));
    });
  }

  function _bindSpellRows(container, state) {
    container.addEventListener('click', function (e) {
      const actionBtn = e.target.closest('[data-spell-action]');
      if (actionBtn) {
        e.preventDefault();
        e.stopPropagation();
        if (state.saving || actionBtn.disabled) return;
        const spellId = String(actionBtn.getAttribute('data-spell-id') || '');
        const action = String(actionBtn.getAttribute('data-spell-action') || '');
        const spell = _safeArray(state.librarySpells).find(function (row) { return String(row.id || '') === spellId; });
        if (!spellId || !spell) return;
        const selected = action === 'prepared' ? !!spell.isPrepared : !!(spell.isKnown || spell.isPrepared);
        const snap = _limitSnapshot(state);
        if (action === 'prepared' && !selected && snap.preparedLimit != null && snap.preparedCount >= snap.preparedLimit) {
          state.message = 'Prepared spell limit reached. Unprepare another spell first.';
          state.messageTone = 'warn';
          _renderSpellsTab(container, state);
          return;
        }
        if (action === 'known' && _spellLevelNumber(spell) > 0 && !selected && snap.knownLimit != null && snap.knownCount >= snap.knownLimit) {
          state.message = 'Known spell limit reached. Remove another spell first.';
          state.messageTone = 'warn';
          _renderSpellsTab(container, state);
          return;
        }
        if (action === 'cantrip' && !selected && snap.cantripLimit != null && snap.cantripCount >= snap.cantripLimit) {
          state.message = 'Cantrip limit reached. Remove another cantrip first.';
          state.messageTone = 'warn';
          _renderSpellsTab(container, state);
          return;
        }
        const promise = action === 'prepared'
          ? _updatePrepared(state, spellId, !selected)
          : _updateKnown(state, spellId, !selected);
        promise.finally(function () { _renderSpellsTab(container, state); });
        return;
      }
      const manageBtn = e.target.closest('.cs-manage-spells-btn');
      if (manageBtn) {
        e.preventDefault();
        state.managerOpen = !state.managerOpen;
        state.message = '';
        _renderSpellsTab(container, state);
        return;
      }
      const castBtn = e.target.closest('[data-spell-cast]');
      if (castBtn) {
        _pulseRowFromTrigger(castBtn);
        e.preventDefault();
        e.stopPropagation();
        const spellKey = String(castBtn.getAttribute('data-spell-cast') || '');
        if (spellKey && typeof global.castRulesSpell === 'function') {
          global.castRulesSpell(spellKey, { castLevel: parseInt(castBtn.getAttribute('data-cast-level') || '0', 10) || 0, slotLevel: parseInt(castBtn.getAttribute('data-cast-level') || '0', 10) || 0 });
        }
        return;
      }

      const openBtn = e.target.closest('[data-spell-open]');
      if (openBtn) {
        _pulseRowFromTrigger(openBtn);
        e.preventDefault();
        e.stopPropagation();
        const spellId = String(openBtn.getAttribute('data-spell-open') || '');
        const pool = _mergeSpellArrays(_safeArray(state.librarySpells), _mergeSpellArrays(_safeArray(state.manifest && state.manifest.cards), state.linkedSpells));
        const spell = pool.find(function (s) { return String(s.id || _spellName(s) || '') === spellId; });
        if (spell) {
          if (typeof global.playerInspectSpell === 'function') global.playerInspectSpell(spellId);
          else _openSpellDetails(spell, state.charData);
        }
        return;
      }

      const rollBtn = e.target.closest('[data-spell-roll]');
      if (rollBtn) {
        _pulseRowFromTrigger(rollBtn);
        e.preventDefault();
        e.stopPropagation();
        const spellId = String(rollBtn.getAttribute('data-spell-roll') || '');
        const rowId = String(rollBtn.getAttribute('data-row-id') || '');
        const castLevel = parseInt(rollBtn.getAttribute('data-cast-level') || '0', 10) || 0;
        const forcedExpr = String(rollBtn.getAttribute('data-roll-expr') || '').trim();
        const castableRows = _safeArray(state.castableSpellRows);
        const exactRow = rowId ? castableRows.find(function (s) { return String(s.rowId || '') === rowId; }) : null;
        const castableById = !exactRow ? castableRows.find(function (s) { return String(s.id || _spellName(s) || '') === spellId; }) : null;
        const pool = _mergeSpellArrays(_safeArray(state.librarySpells), _mergeSpellArrays(_safeArray(state.manifest && state.manifest.cards), state.linkedSpells));
        const spell = exactRow || castableById || pool.find(function (s) { return String(s.id || _spellName(s) || '') === spellId; });
        if (spell && castLevel) spell.castLevel = castLevel;
        Promise.resolve(_rollSpellFromUi(spell, state, { forcedExpr: forcedExpr, forcedCastLevel: castLevel })).then(function (rolled) {
          if (!rolled.ok && rolled.reason !== 'cancelled') {
            state.message = rolled.reason === 'no_formula' ? 'That spell does not have a rollable damage or healing formula yet.' : 'Could not roll that spell right now.';
            state.messageTone = 'warn';
            _renderSpellsTab(container, state);
          }
        });
        return;
      }

      const attackBtn = e.target.closest('[data-spell-attack]');
      if (attackBtn) {
        _pulseRowFromTrigger(attackBtn);
        e.preventDefault();
        e.stopPropagation();
        const spellId = String(attackBtn.getAttribute('data-spell-attack') || '');
        const pool = _mergeSpellArrays(_safeArray(state.librarySpells), _mergeSpellArrays(_safeArray(state.manifest && state.manifest.cards), state.linkedSpells));
        const spell = pool.find(function (s) { return String(s.id || _spellName(s) || '') === spellId; });
        const rolled = _rollSpellAttackFromUi(spell, state);
        if (!rolled.ok) {
          state.message = rolled.reason === 'weapon_attack_spell' ? 'That spell rides on a weapon attack, so use the matching weapon attack card instead.' : 'That spell does not use an attack roll.';
          state.messageTone = 'warn';
          _renderSpellsTab(container, state);
        }
        return;
      }
      const mapJump = e.target.closest('[data-map-panel-open]');
      if (mapJump) {
        e.preventDefault();
        e.stopPropagation();
        if (global.CSContainer && typeof global.CSContainer.openMapPanelFromSheet === 'function') {
          global.CSContainer.openMapPanelFromSheet(String(mapJump.getAttribute('data-map-panel-open') || ''));
        }
        return;
      }
      const row = e.target.closest('.cs-spell-row, .cs-spell-card-row');
      if (!row) return;
      const id = row.getAttribute('data-spell-id') || '';
      const pool = _mergeSpellArrays(_safeArray(state.castableSpellRows), _mergeSpellArrays(_safeArray(state.librarySpells), _mergeSpellArrays(_safeArray(state.manifest && state.manifest.cards), state.linkedSpells)));
      const spell = pool.find(function (s) { return String(s.id || _spellName(s) || '') === id; });
      if (spell) _openSpellDetails(spell, state.charData);
    });
    container.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const row = e.target.closest('.cs-spell-row, .cs-spell-card-row');
      if (!row) return;
      e.preventDefault();
      row.click();
    });
  }

  function _bindFilterControls(container, state) {
    container.addEventListener('click', function (e) {
      const chip = e.target.closest('.cs-filter-chip');
      if (!chip) return;
      state.filter = chip.getAttribute('data-filter') || 'ALL';
      _renderSpellsTab(container, state);
    });
    let timer = null;
    container.addEventListener('input', function (e) {
      const searchInput = e.target.closest('.cs-spell-search');
      if (!searchInput) return;
      clearTimeout(timer);
      timer = setTimeout(function () {
        state.query = searchInput.value.trim();
        _fetchSpells(state, function () { _renderSpellsTab(container, state); });
      }, 180);
    });
  }

  function initSpellsTab(container, charData) {
    if (!container) return;
    const state = _createState(charData || {});
    _bindSlotPips(container);
    _bindSpellRows(container, state);
    _bindFilterControls(container, state);
    _loadState(container, state);
    if (!container.__spellSyncListenerBound) {
      container.__spellSyncListenerBound = true;
      global.addEventListener('character:spell-state-updated', function () {
        const sheet = global._charSheet && typeof global._charSheet === 'object' ? global._charSheet : null;
        if (sheet && sheet.spellState && typeof sheet.spellState === 'object') {
          state.charData.spellState = {
            known: _safeArray(sheet.spellState.known),
            prepared: _safeArray(sheet.spellState.prepared),
          };
        }
        state.message = 'Spellbook synced from level-up.';
        state.messageTone = 'good';
        _loadState(container, state);
      });
    }
  }

  global.SpellsTab = {
    initSpellsTab: initSpellsTab,
    __test: {
      spellRollExpressionForLevel: _spellRollExpressionForLevel,
      rollSpellFromUi: _rollSpellFromUi,
      showRolledSpellResult: _showRolledSpellResult,
      renderSpellCombatResult: _renderSpellCombatResult,
      renderFallbackLocalDiceResult: _renderFallbackLocalDiceResult,
      spellBaseLevel: _spellBaseLevel,
      spellDisplayCastLevel: _spellDisplayCastLevel,
      renderSpellRow: _renderSpellRow,
    }
  };
}(window));
