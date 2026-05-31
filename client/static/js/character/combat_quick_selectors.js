/*
 * Shared selectors for the movable combat quick bar.
 *
 * This module intentionally does not calculate attack bonuses, spell damage, slot
 * math, or action economy by itself. It consumes the live play.html/player action
 * helpers so the quick bar and full character sheet stay on the same data path.
 */
(function (global) {
  'use strict';

  const MAX_PRIMARY = 3;
  const MAX_SECONDARY = 3;
  const MAX_SPELLS = 4;
  const MAX_RESOURCES = 4;

  function _arr(value) {
    return Array.isArray(value) ? value : [];
  }

  function _text(value, fallback = '') {
    return String(value == null ? fallback : value).trim();
  }

  function _num(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function _dedupeByName(rows) {
    const seen = new Set();
    const out = [];
    _arr(rows).forEach(function (row) {
      const key = _text(row && (row.name || row.id)).toLowerCase();
      if (!key || seen.has(key)) return;
      seen.add(key);
      out.push(row);
    });
    return out;
  }

  function _slotLabel(level, getRemaining) {
    const lvl = _num(level, 0);
    if (lvl <= 0) return 'Cantrip';
    const ordinals = ['', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th'];
    const rem = typeof getRemaining === 'function' ? getRemaining(lvl) : null;
    return `${ordinals[lvl] || `${lvl}th`} level${Number.isFinite(rem) ? ` · ${Math.max(0, rem)} left` : ''}`;
  }

  function _actionGate(action, sectionName, env, economyState) {
    if (env && typeof env.evaluateActionAvailability === 'function') {
      const gate = env.evaluateActionAvailability(action, sectionName, economyState) || {};
      return { disabled: !!gate.disabled, reason: _text(gate.reason) };
    }
    return { disabled: false, reason: '' };
  }

  function _normaliseAction(row, type, sectionName, env, economyState) {
    const gate = _actionGate(row, sectionName, env, economyState);
    const resourceText = _text(row && (row.resource || row.cost || row.uses || row.summary));
    const states = [];
    if (gate.disabled) {
      const reason = gate.reason.toLowerCase();
      if (reason.includes('slot')) states.push('needs_spell_slot');
      else if (reason.includes('target')) states.push('needs_target');
      else if (reason.includes('use') || reason.includes('spent') || reason.includes('remaining')) states.push('used_this_turn');
      else states.push('disabled');
    }
    if (/0\s*(?:left|remaining)|no uses|0\//i.test(resourceText + ' ' + gate.reason)) states.push('out_of_uses');
    return {
      id: _text(row && (row.id || row.key || row.name)),
      name: _text(row && row.name, 'Action'),
      type: type,
      source: _text(row && row.source, type),
      actionSection: sectionName,
      attackBonus: _text(row && row.attackBonus),
      damage: _text(row && row.damage),
      damageType: _text(row && row.damageType),
      range: _text(row && row.range),
      resource: resourceText,
      uses: resourceText,
      description: _text(row && (row.desc || row.description)),
      badges: _arr(row && row.badges).map(function (b) { return _text(b); }).filter(Boolean),
      disabled: gate.disabled,
      disabledReason: gate.reason,
      states: Array.from(new Set(states)),
      raw: row || null,
    };
  }

  function _spellHasUsefulRoll(spell) {
    const card = spell && spell.card ? spell.card : {};
    return !!(
      card.damage_dice || card.damage || card.damage_formula || card.base_damage_formula ||
      card.attack_type || card.save_ability || card.save || card.healing_formula || card.current?.formula
    );
  }

  function _normaliseSpell(spell, env, economyState) {
    const level = _num(spell && spell.level, 0);
    const getRemaining = env && env.getSpellSlotRemaining;
    const remaining = level > 0 && typeof getRemaining === 'function' ? getRemaining(level) : null;
    const card = spell && spell.card ? spell.card : {};
    const castTime = _text(card.casting_time || spell.casting_time || '1 action');
    const sectionName = castTime.toLowerCase().includes('bonus action') ? 'Bonus Actions' : (castTime.toLowerCase().includes('reaction') ? 'Reactions' : 'Spells');
    const base = _normaliseAction({
      id: spell && (spell.id || spell.name),
      name: spell && spell.name,
      source: 'spell',
      resource: _slotLabel(level, getRemaining),
      desc: card.base_effect_text || card.description || card.current?.effect || '',
      badges: [level === 0 ? 'Cantrip' : `Level ${level}`, castTime, (card.concentration || card.is_concentration) ? 'Concentration' : ''].filter(Boolean),
      range: spell && spell.range,
      damage: card.damage_dice || card.damage || card.damage_formula || card.current?.formula || '',
    }, 'spell', sectionName, env, economyState);
    base.level = level;
    base.slotRequirement = level > 0 ? level : null;
    base.slotLabel = _slotLabel(level, getRemaining);
    base.needsSpellSlot = level > 0 && Number.isFinite(remaining) && remaining <= 0;
    base.isConcentration = !!(card.concentration || card.is_concentration);
    if (base.needsSpellSlot) {
      base.disabled = true;
      base.disabledReason = base.disabledReason || 'No spell slot remaining.';
      base.states.push('needs_spell_slot');
    }
    if (base.isConcentration) base.states.push('concentration_active');
    base.states = Array.from(new Set(base.states));
    return base;
  }

  function _resourceFromEconomySource(row, type) {
    return {
      id: `economy_${type}_${_text(row && row.source).toLowerCase().replace(/[^a-z0-9]+/g, '_')}`,
      name: _text(row && row.source, type === 'bonus' ? 'Bonus Action' : 'Resource'),
      type: 'resource',
      source: type,
      resource: _text(row && row.detail),
      uses: _text(row && row.detail),
      description: _text(row && row.detail),
      badges: [type === 'bonus' ? 'Bonus' : 'Class'].filter(Boolean),
      disabled: false,
      disabledReason: '',
      states: [],
      raw: row || null,
    };
  }

  function _resourceFromAction(row, env, economyState) {
    const normalised = _normaliseAction(row, 'resource', 'Class Features', env, economyState);
    normalised.badges = Array.from(new Set(['Resource'].concat(normalised.badges || [])));
    return normalised;
  }

  function selectCombatQuickActions(env) {
    env = env || {};
    const sections = typeof env.getPlayerActionsSections === 'function' ? (env.getPlayerActionsSections() || {}) : {};
    const economyState = typeof env.getActionEconomyState === 'function' ? env.getActionEconomyState() : null;
    const attacks = _arr(sections.Attacks);
    const bonus = _arr(sections['Bonus Actions']);
    const reactions = _arr(sections.Reactions);
    const classFeatures = _arr(sections['Class Features']);
    const rawSpells = typeof env.getCombatQuickSpells === 'function' ? _arr(env.getCombatQuickSpells()) : _arr(sections.Spells);

    const primaryActions = _dedupeByName(attacks)
      .slice(0, MAX_PRIMARY)
      .map(function (row) { return _normaliseAction(row, row.source === 'spell' ? 'spell' : 'action', 'Attacks', env, economyState); });

    const bonusActions = _dedupeByName(bonus)
      .slice(0, MAX_SECONDARY)
      .map(function (row) { return _normaliseAction(row, 'bonus action', 'Bonus Actions', env, economyState); });

    const reactionRows = _dedupeByName(reactions).slice(0, MAX_SECONDARY);
    if (!reactionRows.length) {
      reactionRows.push({ id: 'system_opportunity_attack', source: 'system_reaction', name: 'Opportunity Attack', desc: 'Use your reaction when a creature leaves your reach.', badges: ['Reaction'] });
    }
    const normalisedReactions = reactionRows
      .slice(0, MAX_SECONDARY)
      .map(function (row) { return _normaliseAction(row, 'reaction', 'Reactions', env, economyState); });

    const usefulSpells = _dedupeByName(rawSpells)
      .filter(function (spell) { return _num(spell && spell.level, 0) === 0 || _spellHasUsefulRoll(spell); })
      .sort(function (a, b) {
        const al = _num(a && a.level, 0);
        const bl = _num(b && b.level, 0);
        if (al !== bl) return al - bl;
        return _text(a && a.name).localeCompare(_text(b && b.name));
      })
      .slice(0, MAX_SPELLS)
      .map(function (spell) { return _normaliseSpell(spell, env, economyState); });

    const resources = [];
    _arr(economyState && economyState.extra_action_sources).forEach(function (row) { resources.push(_resourceFromEconomySource(row, 'action')); });
    _arr(economyState && economyState.bonus_action_sources).forEach(function (row) { resources.push(_resourceFromEconomySource(row, 'bonus')); });
    classFeatures.filter(function (row) {
      const text = `${_text(row && row.name)} ${_text(row && row.resource)} ${_text(row && row.desc)}`;
      return /ki|martial arts|focus point|action surge|rage|bardic inspiration|sorcery point|wild shape|second wind|channel divinity|superiority dice|lay on hands/i.test(text);
    }).forEach(function (row) { resources.push(_resourceFromAction(row, env, economyState)); });

    const concentrationName = _text(env.getActiveConcentration ? env.getActiveConcentration() : (env.charData && env.charData.activeConcentration));
    const spellSlots = [];
    const slotMap = env.charData && env.charData.spellSlots && typeof env.charData.spellSlots === 'object' ? env.charData.spellSlots : {};
    Object.keys(slotMap).sort(function (a, b) { return Number(a) - Number(b); }).forEach(function (level) {
      const total = _num(slotMap[level], 0);
      if (total <= 0) return;
      const remaining = typeof env.getSpellSlotRemaining === 'function' ? env.getSpellSlotRemaining(Number(level)) : total;
      spellSlots.push({ level: Number(level), total: total, remaining: Math.max(0, remaining) });
    });

    return {
      primaryActions: primaryActions,
      bonusActions: bonusActions,
      reactions: normalisedReactions,
      topSpells: usefulSpells,
      resources: _dedupeByName(resources).slice(0, MAX_RESOURCES),
      concentration: concentrationName ? { name: concentrationName, active: true } : null,
      spellSlots: spellSlots,
      economy: economyState,
      generatedAt: Date.now(),
    };
  }

  global.CombatQuickSelectors = { selectCombatQuickActions: selectCombatQuickActions };
}(window));
