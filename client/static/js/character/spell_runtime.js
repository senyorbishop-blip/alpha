/* Universal spell runtime resolver – every spell surface uses this single source of truth.
 * Loaded by play.html, character sheet tabs, and spell modals.
 * Exposes: window.resolveSpellRuntime, window.AppSpellRuntime
 */
(function initSpellRuntime(global) {
  'use strict';

  /* ── cantrip tier helper ─────────────────────────────────────────────────── */
  function _cantripTiers(die) {
    return [
      { level: 1,  formula: '1d' + die },
      { level: 5,  formula: '2d' + die },
      { level: 11, formula: '3d' + die },
      { level: 17, formula: '4d' + die },
    ];
  }

  /* ── BUILTIN spell metadata ──────────────────────────────────────────────── */
  /* Keys are normalised slugs matching the card's id/name after _slug().
   * Card null values NEVER override these (see _smartMerge).                   */
  const BUILTIN = {
    /* ── Cantrips ────────────────────────────────────────────────────────── */
    'fire-bolt':       { level:0, attackType:'ranged-spell', damageFormula:'1d10', damageType:'fire',      scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(10) } },
    'ray-of-frost':    { level:0, attackType:'ranged-spell', damageFormula:'1d8',  damageType:'cold',      scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8)  } },
    'sacred-flame':    { level:0, savingThrow:'DEX',         damageFormula:'1d8',  damageType:'radiant',   scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8)  } },
    'shocking-grasp':  { level:0, attackType:'melee-spell',  damageFormula:'1d8',  damageType:'lightning', scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8)  } },
    'chill-touch':     { level:0, attackType:'ranged-spell', damageFormula:'1d8',  damageType:'necrotic',  scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8)  } },
    'poison-spray':    { level:0, savingThrow:'CON',         damageFormula:'1d12', damageType:'poison',    scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(12) } },
    'thorn-whip':      { level:0, attackType:'melee-spell',  damageFormula:'1d6',  damageType:'piercing',  scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6)  } },
    'vicious-mockery': { level:0, savingThrow:'WIS',         damageFormula:'1d6',  damageType:'psychic',   scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6)  } },
    'produce-flame':   { level:0, attackType:'ranged-spell', damageFormula:'1d8',  damageType:'fire',      scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8)  } },
    'toll-the-dead':   { level:0, savingThrow:'WIS',         damageFormula:'1d8',  damageType:'necrotic',  scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8)  } },
    'eldritch-blast':  { level:0, attackType:'ranged-spell', damageFormula:'1d10', damageType:'force',     scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(10) } },
    'booming-blade':   { level:0, attackType:'melee-spell',  damageFormula:'0 + weapon damage',            damageType:'thunder', scaling_type:'cantrip_level', scaling_data:{ tiers:[{level:1,formula:'0 + weapon damage'},{level:5,formula:'1d8 rider + weapon damage'},{level:11,formula:'2d8 rider + weapon damage'},{level:17,formula:'3d8 rider + weapon damage'}] } },
    'green-flame-blade':{ level:0, attackType:'melee-spell', damageFormula:'weapon damage',                damageType:'fire',   scaling_type:'cantrip_level', scaling_data:{ tiers:[{level:1,formula:'weapon damage'},{level:5,formula:'weapon damage + 1d8 fire'},{level:11,formula:'weapon damage + 2d8 fire'},{level:17,formula:'weapon damage + 3d8 fire'}] } },
    'word-of-radiance':{ level:0, savingThrow:'CON', damageFormula:'1d6', damageType:'radiant', scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'acid-splash':     { level:0, savingThrow:'DEX', damageFormula:'1d6', damageType:'acid',    scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'mind-sliver':     { level:0, savingThrow:'INT', damageFormula:'1d6', damageType:'psychic', scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'thunderclap':     { level:0, savingThrow:'CON', damageFormula:'1d6', damageType:'thunder', scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'infestation':     { level:0, savingThrow:'CON', damageFormula:'1d6', damageType:'poison',  scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'sword-burst':     { level:0, savingThrow:'DEX', damageFormula:'1d6', damageType:'force',   scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'create-bonfire':  { level:0, savingThrow:'DEX', damageFormula:'1d8', damageType:'fire',    concentration:true, scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8) } },
    'frostbite':       { level:0, savingThrow:'CON', damageFormula:'1d6', damageType:'cold',    scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(6) } },
    'lightning-lure':  { level:0, savingThrow:'STR', damageFormula:'1d8', damageType:'lightning', scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(8) } },
    'primal-savagery': { level:0, attackType:'melee-spell', damageFormula:'1d10', damageType:'acid', scaling_type:'cantrip_level', scaling_data:{ tiers:_cantripTiers(10) } },

    /* ── 1st-level spells ────────────────────────────────────────────────── */
    'cure-wounds':       { level:1, healingFormula:'1d8 + spellcasting modifier', healingType:'healing',
                           scaling_type:'slot_healing', scaling_data:{ base_slot:1, base_formula:'1d8 + spellcasting modifier', per_slot_formula:'1d8' } },
    'healing-word':      { level:1, healingFormula:'1d4 + spellcasting modifier', healingType:'healing', castingTime:'Bonus Action',
                           scaling_type:'slot_healing', scaling_data:{ base_slot:1, base_formula:'1d4 + spellcasting modifier', per_slot_formula:'1d4' } },
    'magic-missile':     { level:1, damageFormula:'3 × (1d4+1)', damageType:'force',
                           scaling_type:'extra_dart_per_slot', scaling_data:{ base_slot:1, base_darts:3, per_slot:1, dart_formula:'1d4+1' } },
    'thunderwave':       { level:1, savingThrow:'CON', damageFormula:'2d8',  damageType:'thunder',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'2d8', per_slot_formula:'1d8' } },
    'burning-hands':     { level:1, savingThrow:'DEX', damageFormula:'3d6',  damageType:'fire',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'3d6', per_slot_formula:'1d6' } },
    'inflict-wounds':    { level:1, attackType:'melee-spell', damageFormula:'3d10', damageType:'necrotic',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'3d10', per_slot_formula:'1d10' } },
    'guiding-bolt':      { level:1, attackType:'ranged-spell', damageFormula:'4d6', damageType:'radiant',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'4d6', per_slot_formula:'1d6' } },
    'hellish-rebuke':    { level:1, savingThrow:'DEX', damageFormula:'2d10', damageType:'fire',    castingTime:'Reaction',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'2d10', per_slot_formula:'1d10' } },
    'absorb-elements':   { level:1, damageFormula:'1d6', damageType:'elemental', castingTime:'Reaction',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'1d6', per_slot_formula:'1d6' } },
    'witch-bolt':        { level:1, attackType:'ranged-spell', damageFormula:'1d12', damageType:'lightning', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'1d12', per_slot_formula:'1d12' } },
    'dissonant-whispers':{ level:1, savingThrow:'WIS', damageFormula:'3d6', damageType:'psychic',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'3d6', per_slot_formula:'1d6' } },
    'chromatic-orb':     { level:1, attackType:'ranged-spell', damageFormula:'3d8', damageType:'elemental',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'3d8', per_slot_formula:'1d8' } },
    'ice-knife':         { level:1, savingThrow:'DEX', damageFormula:'1d10 + 2d6', damageType:'cold',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'1d10 + 2d6', per_slot_formula:'1d6' } },
    'arms-of-hadar':     { level:1, savingThrow:'STR', damageFormula:'2d6', damageType:'necrotic',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'2d6', per_slot_formula:'1d6' } },
    'catapult':          { level:1, savingThrow:'DEX', damageFormula:'3d8', damageType:'bludgeoning',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'3d8', per_slot_formula:'1d8' } },
    'earth-tremor':      { level:1, savingThrow:'DEX', damageFormula:'1d6', damageType:'bludgeoning',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'1d6', per_slot_formula:'1d6' } },
    'ray-of-sickness':   { level:1, attackType:'ranged-spell', damageFormula:'2d8', damageType:'poison',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'2d8', per_slot_formula:'1d8' } },
    'chaos-bolt':        { level:1, attackType:'ranged-spell', damageFormula:'2d8 + 1d6', damageType:'chaotic',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:1, base_formula:'2d8 + 1d6', per_slot_formula:'1d6' } },
    'shield':            { level:1, castingTime:'Reaction' },
    'detect-magic':      { level:1, ritual:true, concentration:true },
    'mage-armor':        { level:1 },

    /* ── 2nd-level spells ────────────────────────────────────────────────── */
    'scorching-ray':     { level:2, attackType:'ranged-spell', damageFormula:'3 rays × 2d6', damageType:'fire',
                           scaling_type:'extra_ray_per_slot', scaling_data:{ base_slot:2, base_rays:3, per_slot:1, ray_formula:'2d6' } },
    'shatter':           { level:2, savingThrow:'CON', damageFormula:'3d8',  damageType:'thunder',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:2, base_formula:'3d8', per_slot_formula:'1d8' } },
    'spiritual-weapon':  { level:2, attackType:'melee-spell', damageFormula:'1d8 + spellcasting modifier', damageType:'force',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:2, base_formula:'1d8 + spellcasting modifier', per_slot_formula:'1d8' } },
    'moonbeam':          { level:2, savingThrow:'CON', damageFormula:'2d10', damageType:'radiant', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:2, base_formula:'2d10', per_slot_formula:'1d10' } },
    'flaming-sphere':    { level:2, savingThrow:'DEX', damageFormula:'2d6',  damageType:'fire', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:2, base_formula:'2d6', per_slot_formula:'1d6' } },
    'prayer-of-healing': { level:2, healingFormula:'2d8 + spellcasting modifier', healingType:'healing',
                           scaling_type:'slot_healing', scaling_data:{ base_slot:2, base_formula:'2d8 + spellcasting modifier', per_slot_formula:'1d8' } },
    'acid-arrow':        { level:2, attackType:'ranged-spell', damageFormula:'4d4', damageType:'acid',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:2, base_formula:'4d4', per_slot_formula:'1d4' } },
    'ray-of-enfeeblement':{ level:2, attackType:'ranged-spell', concentration:true },
    'misty-step':        { level:2, castingTime:'Bonus Action' },

    /* ── 3rd-level spells ────────────────────────────────────────────────── */
    'fireball':          { level:3, savingThrow:'DEX', damageFormula:'8d6',  damageType:'fire',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:3, base_formula:'8d6', per_slot_formula:'1d6' },
                           areaData:{ shape:'sphere', radius_ft:20 } },
    'call-lightning':    { level:3, savingThrow:'DEX', damageFormula:'3d10', damageType:'lightning', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:3, base_formula:'3d10', per_slot_formula:'1d10' } },
    'lightning-bolt':    { level:3, savingThrow:'DEX', damageFormula:'8d6',  damageType:'lightning',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:3, base_formula:'8d6', per_slot_formula:'1d6' } },
    'vampiric-touch':    { level:3, attackType:'melee-spell', damageFormula:'3d6', damageType:'necrotic', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:3, base_formula:'3d6', per_slot_formula:'1d6' } },
    'mass-healing-word': { level:3, healingFormula:'1d4 + spellcasting modifier', healingType:'healing', castingTime:'Bonus Action',
                           scaling_type:'slot_healing', scaling_data:{ base_slot:3, base_formula:'1d4 + spellcasting modifier', per_slot_formula:'1d4' } },
    'spirit-guardians':  { level:3, savingThrow:'WIS', damageFormula:'3d8', damageType:'radiant', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:3, base_formula:'3d8', per_slot_formula:'1d8' } },
    'counterspell':      { level:3, castingTime:'Reaction' },
    'hypnotic-pattern':  { level:3, savingThrow:'WIS', concentration:true },
    'dispel-magic':      { level:3 },
    'haste':             { level:3, concentration:true },

    /* ── 4th-level spells ────────────────────────────────────────────────── */
    'blight':            { level:4, savingThrow:'CON', damageFormula:'8d8',  damageType:'necrotic',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:4, base_formula:'8d8', per_slot_formula:'2d8' } },
    'wall-of-fire':      { level:4, savingThrow:'DEX', damageFormula:'5d8',  damageType:'fire', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:4, base_formula:'5d8', per_slot_formula:'1d8' } },
    'banishment':        { level:4, savingThrow:'CHA', concentration:true },
    'polymorph':         { level:4, savingThrow:'WIS', concentration:true },
    'ice-storm':         { level:4, savingThrow:'DEX', damageFormula:'2d8 + 4d6', damageType:'cold',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:4, base_formula:'2d8 + 4d6', per_slot_formula:'1d8' } },
    'sickening-radiance':{ level:4, savingThrow:'CON', damageFormula:'4d10', damageType:'radiant', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:4, base_formula:'4d10', per_slot_formula:'1d10' } },

    /* ── 5th-level spells ────────────────────────────────────────────────── */
    'cone-of-cold':      { level:5, savingThrow:'CON', damageFormula:'8d8', damageType:'cold',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:5, base_formula:'8d8', per_slot_formula:'1d8' } },
    'mass-cure-wounds':  { level:5, healingFormula:'3d8 + spellcasting modifier', healingType:'healing',
                           scaling_type:'slot_healing', scaling_data:{ base_slot:5, base_formula:'3d8 + spellcasting modifier', per_slot_formula:'1d8' } },
    'flame-strike':      { level:5, savingThrow:'DEX', damageFormula:'4d6 fire + 4d6 radiant', damageType:'fire',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:5, base_formula:'4d6 fire + 4d6 radiant', per_slot_formula:'1d6 fire + 1d6 radiant' } },
    'insect-plague':     { level:5, savingThrow:'CON', damageFormula:'4d10', damageType:'piercing', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:5, base_formula:'4d10', per_slot_formula:'1d10' } },
    'mass-healing-words':{ level:5, healingFormula:'3d4 + spellcasting modifier', healingType:'healing',
                           scaling_type:'slot_healing', scaling_data:{ base_slot:5, base_formula:'3d4 + spellcasting modifier', per_slot_formula:'1d4' } },

    /* ── 6th-level spells ────────────────────────────────────────────────── */
    'disintegrate':      { level:6, attackType:'ranged-spell', damageFormula:'10d6 + 40', damageType:'force',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:6, base_formula:'10d6 + 40', per_slot_formula:'3d6' } },
    'sunbeam':           { level:6, savingThrow:'CON', damageFormula:'6d8', damageType:'radiant', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:6, base_formula:'6d8', per_slot_formula:'0' } },
    'chain-lightning':   { level:6, attackType:'ranged-spell', damageFormula:'10d8', damageType:'lightning',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:6, base_formula:'10d8', per_slot_formula:'1d8' } },

    /* ── 7th-level spells ────────────────────────────────────────────────── */
    'delayed-blast-fireball':{ level:7, savingThrow:'DEX', damageFormula:'12d6', damageType:'fire',
                               scaling_type:'slot_damage', scaling_data:{ base_slot:7, base_formula:'12d6', per_slot_formula:'1d6' } },
    'finger-of-death':   { level:7, savingThrow:'CON', damageFormula:'7d8 + 30', damageType:'necrotic',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:7, base_formula:'7d8 + 30', per_slot_formula:'0' } },

    /* ── 8th-level spells ────────────────────────────────────────────────── */
    'sunburst':          { level:8, savingThrow:'CON', damageFormula:'12d6', damageType:'radiant',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:8, base_formula:'12d6', per_slot_formula:'0' } },
    'incendiary-cloud':  { level:8, savingThrow:'DEX', damageFormula:'10d8', damageType:'fire', concentration:true,
                           scaling_type:'slot_damage', scaling_data:{ base_slot:8, base_formula:'10d8', per_slot_formula:'0' } },

    /* ── 9th-level spells ────────────────────────────────────────────────── */
    'meteor-swarm':      { level:9, savingThrow:'DEX', damageFormula:'20d6 fire + 20d6 bludgeoning', damageType:'fire',
                           scaling_type:'slot_damage', scaling_data:{ base_slot:9, base_formula:'20d6 fire + 20d6 bludgeoning', per_slot_formula:'0' } },
  };

  /* ── Pure helpers ────────────────────────────────────────────────────────── */
  function _slug(v) { return String(v || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); }
  function first() { for (var i = 0; i < arguments.length; i++) { var v = arguments[i]; if (v !== undefined && v !== null && String(v).trim()) return String(v).trim(); } return ''; }
  function num(v, fb) { if (fb === undefined) fb = null; if (v === null || v === undefined || v === '') return fb; var n = Number(v); return Number.isFinite(n) ? Math.floor(n) : fb; }
  function obj(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
  function signed(n) { return n == null ? '' : (n >= 0 ? '+' + n : String(n)); }

  /* Smart merge: start with card values, fill in from builtin where card has
   * null / undefined / empty string.  This prevents the server JSON sending
   * null for damageFormula from erasing the curated BUILTIN value.             */
  function _smartMerge(builtin, card) {
    var merged = Object.assign({}, card);
    var bkeys = Object.keys(builtin);
    for (var i = 0; i < bkeys.length; i++) {
      var k = bkeys[i];
      var cv = merged[k];
      if (cv === null || cv === undefined || cv === '') merged[k] = builtin[k];
    }
    return merged;
  }

  function levelOf(card, merged) {
    var raw = card.level !== undefined ? card.level : (card.spell_level !== undefined ? card.spell_level : (card.spellLevel !== undefined ? card.spellLevel : (card.slotLevel !== undefined ? card.slotLevel : merged.level)));
    if (raw === null || raw === undefined || raw === '') return null;
    if (String(raw).toLowerCase() === 'cantrip') return 0;
    return num(raw, null);
  }

  function spellMod(options) {
    var direct = num(options.spellcastingModifier !== undefined ? options.spellcastingModifier : options.spellMod, null);
    if (direct !== null) return direct;
    var ability = String(options.spellcastingAbility || options.spellAbility || '').toUpperCase().slice(0, 3);
    var scores = obj(options.abilityScores || options.scores);
    var map = { STR: 'strength', DEX: 'dexterity', CON: 'constitution', INT: 'intelligence', WIS: 'wisdom', CHA: 'charisma' };
    var score = num(scores[ability] !== undefined ? scores[ability] : scores[map[ability]], null);
    return score === null ? null : Math.floor((score - 10) / 2);
  }

  function replaceMod(formula, options, warnings) {
    var text = String(formula || '').trim();
    if (!text) return '';
    var m = spellMod(options || {});
    if (m === null) {
      if (/spellcasting\s+modifier|\bmod\b/i.test(text)) warnings.push('Spellcasting modifier is not numeric; formula shown but not safely rollable until modifier is known.');
      return text.replace(/\bmod\b/gi, 'spellcasting modifier');
    }
    return text
      .replace(/spellcasting\s+modifier/gi, signed(m))
      .replace(/\bmod\b/gi, signed(m))
      .replace(/\+\s*\+/g, '+')
      .replace(/-\s*-/g, '+');
  }

  function parseSimpleDice(formula) {
    var m = String(formula || '').trim().match(/^(\d+)\s*d\s*(\d+)(.*)$/i);
    return m ? { count: num(m[1], 0), sides: num(m[2], 0), tail: String(m[3] || '').trim() } : null;
  }

  /* Combine base dice formula with per-slot additional dice.
   * Examples:
   *   combine('8d6',  '1d6', 5)                       → '13d6'
   *   combine('3d10', '1d10', 1)                       → '4d10'
   *   combine('1d8 + spellcasting modifier', '1d8', 4) → '5d8 + spellcasting modifier'
   *   combine('3d8',  '1d8', 0)                        → '3d8'
   */
  function combine(base, per, delta) {
    if (delta <= 0 || !per) return base;
    var b = parseSimpleDice(base), p = parseSimpleDice(per);
    if (b && p && b.sides === p.sides && !p.tail) {
      /* Same die type – just bump the count and keep any tail from base */
      var newCount = b.count + delta * p.count;
      return String(base).replace(/^(\d+)\s*d\s*(\d+)/i, newCount + 'd' + b.sides);
    }
    /* Different dice or complex expression – append extra terms */
    return [base].concat(Array(delta).fill(per)).join(' + ');
  }

  /* ── Scaling inference ───────────────────────────────────────────────────── */
  /* Precedence:
   *  1. Explicit scaling_type / scalingType on the card
   *  2. cast_options dictionary (imported / PDF per-level rows)
   *  3. scalingNote text parsing
   *  4. Cantrip default
   *  5. 'none'
   */
  function inferScaling(merged, baseLevel, baseFormula, healing) {
    var st = first(merged.scaling_type, merged.scalingType, '');
    var sd = obj(merged.scaling_data || merged.scalingData);
    if (st && st !== 'none') return { type: st, data: sd };

    /* cast_options: imported / PDF spell rows carry per-level formulae */
    var castOpts = obj(merged.cast_options || merged.castOptions);
    var castOptKeys = Object.keys(castOpts);
    if (castOptKeys.length > 1 || (castOptKeys.length === 1 && castOptKeys[0] !== String(baseLevel))) {
      return { type: 'cast_options', data: castOpts };
    }

    /* Parse scalingNote / higher_level_text */
    var note = first(merged.scalingNote, merged.higher_level_text, merged.higherLevel, merged.atHigherLevels, merged.higher_levels, '');
    /* "add[s] Xd6" or "adding Xd6" */
    var m = note.match(/\badds?\s+(\d+d\d+)/i) ||
            /* "each slot level above Xth adds Yd6" */
            note.match(/(?:each|for each|per)\s+slot\s+level\s+above[^,]*.?\s+(\d+d\d+)/i) ||
            /* "1d6 per slot level above Xth" */
            note.match(/(\d+d\d+)\s+(?:per|for each|for every)\s+(?:slot|spell)\s+level/i) ||
            /* "for each level above Xth, add Yd6" */
            note.match(/add\s+(\d+d\d+)\s+(?:\w+\s+)?damage/i);
    if (m) {
      return {
        type: healing ? 'slot_healing' : 'slot_damage',
        data: { base_slot: baseLevel || 1, base_formula: baseFormula, per_slot_formula: m[1] },
      };
    }

    /* Cantrip default */
    if (baseLevel === 0 && parseSimpleDice(baseFormula)) {
      var sides = parseSimpleDice(baseFormula).sides;
      return {
        type: 'cantrip_level',
        data: { tiers: [1, 5, 11, 17].map(function (lvl, i) { return { level: lvl, formula: (i + 1) + 'd' + sides }; }) },
      };
    }

    return { type: 'none', data: sd };
  }

  function cantripFormula(data, baseFormula, level) {
    var tiers = Array.isArray(data.tiers) ? data.tiers.slice().sort(function (a, b) { return num(a.level, 1) - num(b.level, 1); }) : [];
    var out = baseFormula;
    tiers.forEach(function (t) { if ((level || 1) >= num(t.level, 1)) out = first(t.formula, out); });
    return out;
  }

  function normalizeRollable(formula) {
    return String(formula || '').replace(/×/g, 'x').replace(/(\d+)\s*(?:darts?|rays?)\s*x\s*\(?\s*(\d+d\d+\s*(?:[+\-]\s*\d+)?)\s*\)?/gi, function (match, n, f) {
      var dm = String(f).replace(/\s+/g, '').match(/^(\d+)d(\d+)([+\-]\d+)?$/i);
      if (!dm) return match;
      var mult = num(n, 1), count = num(dm[1], 1) * mult, bonus = (num(dm[3], 0) || 0) * mult;
      return count + 'd' + dm[2] + (bonus ? signed(bonus) : '');
    });
  }

  function isRollable(formula) {
    var t = normalizeRollable(formula);
    return /\d+d\d+/i.test(t) && !/spellcasting modifier|\bmod\b/i.test(t);
  }

  /* ── Main resolver ───────────────────────────────────────────────────────── */
  function resolveSpellRuntime(spellCard, options) {
    options = options || {};
    var card = obj(spellCard);

    /* Identify spell via id, then name, then stripped prefixes */
    var id = _slug(first(card.spellId, card.id, card.name, card.displayName));
    var idStripped = id.replace(/^(?:spell|ability|action)-/, '');
    var idByName  = _slug(first(card.name, card.displayName));
    var builtin   = BUILTIN[id] || BUILTIN[idStripped] || BUILTIN[idByName] || {};

    /* Merge: card wins for non-null values; BUILTIN fills null gaps */
    var merged = _smartMerge(builtin, card);

    /* Restore BUILTIN scaling when card omits it */
    if (!first(merged.scaling_type, merged.scalingType) && first(builtin.scaling_type)) {
      merged.scaling_type = builtin.scaling_type;
      if (!merged.scaling_data && !merged.scalingData && builtin.scaling_data) {
        merged.scaling_data = builtin.scaling_data;
      }
    }

    var warnings = [];
    var debugParts = [];

    var baseLevel = levelOf(card, merged);
    if (baseLevel === null) warnings.push('Unknown spell level');

    /* importedSlotRow: explicit formula for a given cast level (highest priority) */
    var importedSlotRow = obj(options.importedSlotRow);
    var importedFormula = first(importedSlotRow.formula, importedSlotRow.damage, '');

    var castLevel = num(
      options.castLevel !== undefined ? options.castLevel : (options.slotLevel !== undefined ? options.slotLevel : (merged.default_cast_level !== undefined ? merged.default_cast_level : (merged.current && merged.current.cast_level !== undefined ? merged.current.cast_level : undefined))),
      baseLevel === null ? null : baseLevel
    );
    if (baseLevel === 0) castLevel = 0;
    if (baseLevel !== null && baseLevel > 0 && (castLevel === null || castLevel < baseLevel)) castLevel = baseLevel;

    var healing = !!(
      first(merged.healingFormula, merged.healing_formula, merged.healingType, merged.healing_type) ||
      /\bheal|cure wounds|healing word|regain hit/i.test(first(merged.name, merged.displayName, merged.description, ''))
    );

    var baseFormula = first(
      healing ? (merged.healingFormula || merged.healing_formula) : '',
      merged.damageFormula, merged.damage_formula, merged.base_damage_formula,
      merged.damage_dice, merged.damage,
      merged.current && merged.current.formula,
      ''
    );

    var scaling = inferScaling(merged, baseLevel, baseFormula, healing);
    var delta   = Math.max(0, (castLevel || 0) - (num(scaling.data.base_slot, baseLevel || 0) || 0));

    var finalDamageFormula = '', finalHealingFormula = '', displayFormula = '';

    /* importedSlotRow always wins for the formula */
    if (importedFormula) {
      displayFormula = importedFormula;
    } else if (scaling.type === 'cast_options') {
      var opts = scaling.data;
      var clKey = String(castLevel);
      var opt = opts[clKey] || opts[String(baseLevel)];
      displayFormula = opt ? String(opt.formula || opt.damage || opt.damage_formula || '').trim() : baseFormula;
    } else if (scaling.type === 'cantrip_level') {
      displayFormula = cantripFormula(scaling.data, baseFormula, num(options.characterLevel !== undefined ? options.characterLevel : options.charLevel, 1));
    } else if (scaling.type === 'slot_damage' || scaling.type === 'slot_healing') {
      displayFormula = combine(first(scaling.data.base_formula, baseFormula), first(scaling.data.per_slot_formula, ''), delta);
    } else if (scaling.type === 'extra_dart_per_slot') {
      var darts = num(scaling.data.base_darts, 3) + delta * num(scaling.data.per_slot, 1);
      displayFormula = darts + ' darts × (' + first(scaling.data.dart_formula, '1d4+1') + ')';
      debugParts.push('darts=' + darts);
    } else if (scaling.type === 'extra_ray_per_slot') {
      var rays = num(scaling.data.base_rays, 3) + delta * num(scaling.data.per_slot, 1);
      displayFormula = rays + ' rays × ' + first(scaling.data.ray_formula, '2d6');
      debugParts.push('rays=' + rays);
    } else if (scaling.type === 'extra_target_per_slot') {
      displayFormula = baseFormula;
      var targets = num(scaling.data.base_targets, 1) + delta * num(scaling.data.per_slot, 1);
      if (targets > 1) warnings.push('Targets at this level: ' + targets);
    } else {
      displayFormula = baseFormula;
    }

    displayFormula = replaceMod(displayFormula, options, warnings);
    if (healing) finalHealingFormula = displayFormula; else finalDamageFormula = displayFormula;

    if (displayFormula && /\d+d\d+/i.test(displayFormula) && !isRollable(displayFormula)) {
      warnings.push('Formula is not safely rollable without more metadata.');
    }
    if (!displayFormula && (healing || first(merged.damageType, merged.damage_type, merged.healingType, merged.healing_type, '') || /damage|healing|hit points/i.test(first(merged.description, merged.effect, '')))) {
      warnings.push('Missing damage/healing formula; no fake dice will be rolled.');
    }

    var attackType  = first(merged.attackType, merged.attack_type, '');
    var saveAbility = first(merged.savingThrow, merged.saveAbility, merged.save_ability, merged.save, '').toUpperCase();

    /* Spells with a saving throw must not also show Roll Attack */
    var requiresAttackRoll = !!attackType && /ranged|melee/i.test(attackType) && !/save/i.test(attackType) && !saveAbility;

    return {
      spellId:  id,
      name:     first(merged.displayName, merged.name, id || 'Spell'),
      baseLevel: baseLevel,
      castLevel: castLevel,
      school:       first(merged.school, ''),
      castingTime:  first(merged.castingTime, merged.casting_time, ''),
      range:        first(merged.range, ''),
      duration:     first(merged.duration, ''),
      concentration: !!(merged.concentration || merged.is_concentration),
      ritual:        !!(merged.ritual || merged.is_ritual),
      attackType:         attackType,
      requiresAttackRoll: requiresAttackRoll,
      saveAbility: saveAbility,
      saveDc:      first(options.saveDc, options.saveDC, merged.save_dc, merged.saveDC, ''),
      attackBonus: first(options.spellAttackBonus, merged.attack_bonus, merged.attackBonus, ''),
      damageType:  healing ? '' : first(merged.damageType, merged.damage_type, ''),
      healingType: healing ? first(merged.healingType, merged.healing_type, 'healing') : '',
      baseFormula:        baseFormula,
      scalingType:        scaling.type,
      scalingData:        scaling.data,
      finalDamageFormula: finalDamageFormula,
      finalHealingFormula: finalHealingFormula,
      displayFormula:     displayFormula,
      targetType:    first(merged.targetType, merged.target, ''),
      areaData:      obj(merged.areaData || merged.area_data),
      consumesSpellSlot:  baseLevel !== 0 && !options.item,
      consumesItemCharge: !!options.item,
      itemChargeCost:     num(options.itemChargeCost !== undefined ? options.itemChargeCost : merged.itemChargeCost, options.item ? 1 : 0),
      source:  first(options.source, merged.source, options.item ? 'item' : 'spell'),
      debugParts: debugParts,
      warnings:   warnings,
    };
  }

  /* ── Build cast options for a spell card (slot 1–9) ────────────────────── */
  /* Returns array of { value, label, formula, disabled } objects.            */
  function buildCastOptions(spellCard, opts) {
    opts = opts || {};
    var card = obj(spellCard);
    var id    = _slug(first(card.spellId, card.id, card.name, card.displayName));
    var idS   = id.replace(/^(?:spell|ability|action)-/, '');
    var idN   = _slug(first(card.name, card.displayName));
    var builtin = BUILTIN[id] || BUILTIN[idS] || BUILTIN[idN] || {};
    var merged  = _smartMerge(builtin, card);
    var baseLevel = levelOf(card, merged);
    if (baseLevel === null || baseLevel === 0) return [];
    var ordinals = ['', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th'];
    var options = [];
    for (var lvl = baseLevel; lvl <= 9; lvl++) {
      var rt = resolveSpellRuntime(spellCard, Object.assign({}, opts, { castLevel: lvl }));
      options.push({
        value:   lvl,
        label:   (ordinals[lvl] || (lvl + 'th')) + ' — ' + (rt.displayFormula || '(no formula)'),
        formula: rt.displayFormula,
        disabled: false,
      });
    }
    return options;
  }

  /* ── Exports ─────────────────────────────────────────────────────────────── */
  global.resolveSpellRuntime = resolveSpellRuntime;
  global.buildSpellCastOptions = buildCastOptions;
  global.AppSpellRuntime = {
    resolveSpellRuntime:      resolveSpellRuntime,
    buildSpellCastOptions:    buildCastOptions,
    normalizeRollableFormula: normalizeRollable,
    isRollableFormula:        isRollable,
    combineSpellFormula:      combine,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AppSpellRuntime;

})(typeof window !== 'undefined' ? window : globalThis);
