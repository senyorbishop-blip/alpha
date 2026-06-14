/* Universal spell runtime resolver. Loaded by play.html and character sheet tabs. */
(function initSpellRuntime(global) {
  'use strict';

  const ABILS = ['STR','DEX','CON','INT','WIS','CHA'];
  const DAMAGE_TYPES = ['acid','bludgeoning','cold','fire','force','lightning','necrotic','piercing','poison','psychic','radiant','slashing','thunder'];
  const BUILTIN = {
    'fireball': { level:3, damageFormula:'8d6', damageType:'fire', savingThrow:'DEX', scaling_type:'slot_damage', scaling_data:{ base_slot:3, base_formula:'8d6', per_slot_formula:'1d6' }, areaData:{ shape:'sphere', radius_ft:20 } },
    'cure-wounds': { level:1, healingFormula:'1d8 + spellcasting modifier', healingType:'healing', scaling_type:'slot_healing', scaling_data:{ base_slot:1, base_formula:'1d8 + spellcasting modifier', per_slot_formula:'1d8' } },
    'magic-missile': { level:1, damageFormula:'3 × (1d4+1)', damageType:'force', scaling_type:'extra_dart_per_slot', scaling_data:{ base_slot:1, base_darts:3, per_slot:1, dart_formula:'1d4+1' } },
    'scorching-ray': { level:2, attackType:'ranged-spell', damageFormula:'3 rays × 2d6', damageType:'fire', scaling_type:'extra_ray_per_slot', scaling_data:{ base_slot:2, base_rays:3, per_slot:1, ray_formula:'2d6' } },
    'fire-bolt': { level:0, attackType:'ranged-spell', damageFormula:'1d10', damageType:'fire', scaling_type:'cantrip_level', scaling_data:{ tiers:[{level:1,formula:'1d10'},{level:5,formula:'2d10'},{level:11,formula:'3d10'},{level:17,formula:'4d10'}] } },
    'counterspell': { level:3 }, 'shield': { level:1, castingTime:'Reaction' }, 'detect-magic': { level:1, ritual:true, concentration:true }, 'misty-step': { level:2, castingTime:'Bonus Action' }
  };

  function slug(v){ return String(v||'').trim().toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,''); }
  function first(){ for (let i=0;i<arguments.length;i++){ const v=arguments[i]; if(v!==undefined&&v!==null&&String(v).trim()) return String(v).trim(); } return ''; }
  function num(v, fb=null){ if(v===null||v===undefined||v==='') return fb; const n=Number(v); return Number.isFinite(n) ? Math.floor(n) : fb; }
  function obj(v){ return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
  function signed(n){ return n == null ? '' : (n >= 0 ? '+'+n : String(n)); }
  function levelOf(card, merged){
    const raw = card.level ?? card.spell_level ?? card.spellLevel ?? card.slotLevel ?? merged.level;
    if (raw === null || raw === undefined || raw === '') return null;
    if (String(raw).toLowerCase() === 'cantrip') return 0;
    return num(raw, null);
  }
  function spellMod(options){
    const direct = num(options.spellcastingModifier ?? options.spellMod, null);
    if (direct !== null) return direct;
    const ability = String(options.spellcastingAbility || options.spellAbility || '').toUpperCase().slice(0,3);
    const scores = obj(options.abilityScores || options.scores);
    const map = {STR:'strength',DEX:'dexterity',CON:'constitution',INT:'intelligence',WIS:'wisdom',CHA:'charisma'};
    const score = num(scores[ability] ?? scores[map[ability]], null);
    return score === null ? null : Math.floor((score - 10) / 2);
  }
  function replaceMod(formula, options, warnings){
    let text = String(formula || '').trim();
    if (!text) return '';
    const m = spellMod(options || {});
    if (m === null) {
      if (/spellcasting\s+modifier|\bmod\b/i.test(text)) warnings.push('Spellcasting modifier is not numeric; formula is shown but not safely rollable until a modifier is known.');
      return text.replace(/\bmod\b/gi, 'spellcasting modifier');
    }
    return text.replace(/spellcasting\s+modifier/gi, signed(m)).replace(/\bmod\b/gi, signed(m)).replace(/\+\s*\+/g,'+').replace(/-\s*-/g,'+');
  }
  function parseSimpleDice(formula){
    const m = String(formula||'').trim().match(/^(\d+)\s*d\s*(\d+)(.*)$/i);
    return m ? { count:num(m[1],0), sides:num(m[2],0), tail:String(m[3]||'').trim() } : null;
  }
  function combine(base, per, delta){
    if (delta <= 0 || !per) return base;
    const b = parseSimpleDice(base), p = parseSimpleDice(per);
    if (b && p && b.sides === p.sides && !p.tail) return String(base).replace(/^(\d+)\s*d\s*(\d+)/i, (b.count + delta*p.count)+'d'+b.sides);
    return [base].concat(Array(delta).fill(per)).join(' + ');
  }
  function inferScaling(card, baseLevel, baseFormula, healing){
    const st = first(card.scaling_type, card.scalingType, '');
    const sd = obj(card.scaling_data || card.scalingData);
    if (st && st !== 'none') return { type:st, data:sd };
    const note = first(card.scalingNote, card.higher_level_text, card.higherLevel, card.atHigherLevels, '');
    let m = note.match(/(?:each|for each|per) slot level above[^\d]*(\d+d\d+)/i) || note.match(/add\s+(\d+d\d+)/i);
    if (m) return { type: healing ? 'slot_healing' : 'slot_damage', data:{ base_slot:baseLevel||1, base_formula:baseFormula, per_slot_formula:m[1] } };
    if (baseLevel === 0 && parseSimpleDice(baseFormula)) return { type:'cantrip_level', data:{ tiers:[1,5,11,17].map((lvl,i)=>({ level:lvl, formula:(i+1)+'d'+parseSimpleDice(baseFormula).sides })) } };
    return { type:'none', data:sd };
  }
  function cantripFormula(data, baseFormula, level){
    const tiers = Array.isArray(data.tiers) ? data.tiers.slice().sort((a,b)=>num(a.level,1)-num(b.level,1)) : [];
    let out = baseFormula;
    tiers.forEach(t => { if ((level||1) >= num(t.level,1)) out = first(t.formula, out); });
    return out;
  }
  function normalizeRollable(formula){
    return String(formula||'').replace(/×/g,'x').replace(/(\d+)\s*(?:darts?|rays?)\s*x\s*\(?\s*(\d+d\d+\s*(?:[+\-]\s*\d+)?)\s*\)?/gi, (m,n,f)=>{
      const dm=String(f).replace(/\s+/g,'').match(/^(\d+)d(\d+)([+\-]\d+)?$/i); if(!dm) return m;
      const mult=num(n,1), count=num(dm[1],1)*mult, bonus=(num(dm[3],0)||0)*mult;
      return count+'d'+dm[2]+(bonus? signed(bonus):'');
    });
  }
  function isRollable(formula){ const t=normalizeRollable(formula); return /\d+d\d+/i.test(t) && !/spellcasting modifier|\bmod\b/i.test(t); }

  function resolveSpellRuntime(spellCard, options) {
    options = options || {};
    const card = obj(spellCard);
    const id = slug(first(card.spellId, card.id, card.name, card.displayName));
    // Also try: strip "spell-" / "ability-" prefix, then fall back to name alone,
    // so that cards whose id is "spell-fireball" still match BUILTIN['fireball'].
    const idStripped = id.replace(/^(?:spell|ability|action)-/, '');
    const idByName = slug(first(card.name, card.displayName));
    const merged = Object.assign({}, BUILTIN[id] || BUILTIN[idStripped] || BUILTIN[idByName] || {}, card);
    const warnings = [];
    const debugParts = [];
    const baseLevel = levelOf(card, merged);
    if (baseLevel === null) warnings.push('Unknown spell level');
    let castLevel = num(options.castLevel ?? options.slotLevel ?? merged.default_cast_level ?? merged.current?.cast_level, baseLevel === null ? null : baseLevel);
    if (baseLevel === 0) castLevel = 0;
    if (baseLevel !== null && baseLevel > 0 && (castLevel === null || castLevel < baseLevel)) castLevel = baseLevel;
    const healing = !!first(merged.healingFormula, merged.healing_formula, merged.healingType, merged.healing_type) || /\bheal|cure wounds|healing word|regain hit/i.test(first(merged.name, merged.displayName, merged.description, ''));
    const baseFormula = first(healing ? (merged.healingFormula || merged.healing_formula) : '', merged.damageFormula, merged.damage_formula, merged.base_damage_formula, merged.damage_dice, merged.damage, merged.current?.formula, '');
    const scaling = inferScaling(merged, baseLevel, baseFormula, healing);
    let finalDamageFormula = '', finalHealingFormula = '', displayFormula = '';
    const delta = Math.max(0, (castLevel||0) - (num(scaling.data.base_slot, baseLevel||0)||0));
    if (scaling.type === 'cantrip_level') displayFormula = cantripFormula(scaling.data, baseFormula, num(options.characterLevel ?? options.charLevel, 1));
    else if (scaling.type === 'slot_damage' || scaling.type === 'slot_healing') displayFormula = combine(first(scaling.data.base_formula, baseFormula), first(scaling.data.per_slot_formula, ''), delta);
    else if (scaling.type === 'extra_dart_per_slot') { const darts=num(scaling.data.base_darts,3)+delta*num(scaling.data.per_slot,1); displayFormula = darts + ' darts × (' + first(scaling.data.dart_formula, '1d4+1') + ')'; debugParts.push('darts='+darts); }
    else if (scaling.type === 'extra_ray_per_slot') { const rays=num(scaling.data.base_rays,3)+delta*num(scaling.data.per_slot,1); displayFormula = rays + ' rays × ' + first(scaling.data.ray_formula, '2d6'); debugParts.push('rays='+rays); }
    else displayFormula = baseFormula;
    displayFormula = replaceMod(displayFormula, options, warnings);
    if (healing) finalHealingFormula = displayFormula; else finalDamageFormula = displayFormula;
    if (displayFormula && /\d+d\d+/i.test(displayFormula) && !isRollable(displayFormula)) warnings.push('Formula is not safely rollable without more metadata.');
    if (!displayFormula && (healing || first(merged.damageType, merged.damage_type, merged.healingType, merged.healing_type, '') || /damage|healing|hit points/i.test(first(merged.description, merged.effect, '')))) warnings.push('Missing damage/healing formula; no fake dice will be rolled.');
    const attackType = first(merged.attackType, merged.attack_type, '');
    const saveAbility = first(merged.savingThrow, merged.saveAbility, merged.save_ability, merged.save, '').toUpperCase();
    return {
      spellId:id, name:first(merged.displayName, merged.name, id || 'Spell'), baseLevel, castLevel,
      school:first(merged.school,''), castingTime:first(merged.castingTime, merged.casting_time,''), range:first(merged.range,''), duration:first(merged.duration,''), concentration:!!(merged.concentration||merged.is_concentration), ritual:!!(merged.ritual||merged.is_ritual),
      attackType, requiresAttackRoll:!!attackType && /attack|ranged|melee|spell/i.test(attackType), saveAbility, saveDc:first(options.saveDc, options.saveDC, merged.save_dc, merged.saveDC, ''),
      damageType: healing ? '' : first(merged.damageType, merged.damage_type,''), healingType: healing ? first(merged.healingType, merged.healing_type,'healing') : '',
      baseFormula, scalingType:scaling.type, scalingData:scaling.data, finalDamageFormula, finalHealingFormula, displayFormula,
      targetType:first(merged.targetType, merged.target, ''), areaData:obj(merged.areaData || merged.area_data), consumesSpellSlot:baseLevel !== 0 && !options.item, consumesItemCharge:!!options.item, itemChargeCost:num(options.itemChargeCost ?? merged.itemChargeCost, options.item ? 1 : 0), source:first(options.source, merged.source, options.item ? 'item' : 'spell'), debugParts, warnings
    };
  }
  global.resolveSpellRuntime = resolveSpellRuntime;
  global.AppSpellRuntime = { resolveSpellRuntime, normalizeRollableFormula: normalizeRollable, isRollableFormula: isRollable };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AppSpellRuntime;
})(typeof window !== 'undefined' ? window : globalThis);
