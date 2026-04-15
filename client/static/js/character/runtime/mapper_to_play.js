(function initCharacterRuntimeMappers(global) {
  function clone(value) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return value;
    }
  }

  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function asInt(value, fallback) {
    var parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function hasNumber(value) {
    return Number.isFinite(parseInt(value, 10));
  }

  function resolveCanonicalHp(nativeCharacter, nativeRuntime, fallback) {
    var doc = asObject(nativeCharacter);
    var runtime = asObject(nativeRuntime);
    var fallbackHp = asObject(fallback);
    var rootHp = asObject(doc.hp);
    var vitals = asObject(doc.vitals);
    var combatVitals = asObject(vitals.combat);
    var runtimeHp = asObject(runtime.hp);
    var runtimeCombat = asObject(runtime.combat);

    var max = firstDefinedNumber(
      doc.maxHP,
      doc.maxHp,
      rootHp.max,
      vitals.maxHP,
      vitals.maxHp,
      combatVitals.maxHP,
      combatVitals.maxHp,
      runtimeHp.max,
      runtimeCombat.maxHP,
      runtimeCombat.maxHp,
      fallbackHp.max
    );
    max = max > 0 ? max : 1;

    var current = firstDefinedNumber(
      doc.currentHP,
      doc.currentHp,
      rootHp.current,
      vitals.currentHP,
      vitals.currentHp,
      combatVitals.currentHP,
      combatVitals.currentHp,
      runtimeHp.current,
      runtimeCombat.currentHP,
      runtimeCombat.currentHp,
      fallbackHp.current,
      max
    );
    current = Math.max(0, Math.min(max, current));

    var temp = firstDefinedNumber(
      doc.tempHP,
      doc.tempHp,
      rootHp.temp,
      vitals.tempHP,
      vitals.tempHp,
      combatVitals.tempHP,
      combatVitals.tempHp,
      runtimeHp.temp,
      runtimeCombat.tempHP,
      runtimeCombat.tempHp,
      fallbackHp.temp,
      0
    );
    temp = Math.max(0, temp);

    return { max: max, current: current, temp: temp };
  }

  function firstDefinedNumber() {
    for (var i = 0; i < arguments.length; i += 1) {
      if (hasNumber(arguments[i])) return parseInt(arguments[i], 10);
    }
    return 0;
  }

  function titleCaseWord(raw) {
    var text = String(raw || '').trim().toLowerCase();
    if (!text) return '';
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function signed(value) {
    var num = asInt(value, 0);
    return (num >= 0 ? '+' : '') + String(num);
  }

  var SKILL_TO_ABILITY = {
    'Acrobatics': 'dex',
    'Animal Handling': 'wis',
    'Arcana': 'int',
    'Athletics': 'str',
    'Deception': 'cha',
    'History': 'int',
    'Insight': 'wis',
    'Intimidation': 'cha',
    'Investigation': 'int',
    'Medicine': 'wis',
    'Nature': 'int',
    'Perception': 'wis',
    'Performance': 'cha',
    'Persuasion': 'cha',
    'Religion': 'int',
    'Sleight of Hand': 'dex',
    'Stealth': 'dex',
    'Survival': 'wis',
  };

  function normalizeSkillName(value) {
    return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
  }

  function abilityModifier(score) {
    return Math.floor((asInt(score, 10) - 10) / 2);
  }

  function buildNativeSkillMap(doc, runtime) {
    var abilities = asObject(asObject(doc.abilities).scores);
    var profBonus = asInt(runtime.proficiencyBonus, 2);
    var proficiencySet = new Set();

    asArray(asObject(doc.background).proficiencies).forEach(function addBackgroundSkill(name) {
      var normalized = normalizeSkillName(name);
      if (normalized) proficiencySet.add(normalized);
    });
    var abilitySkills = asObject(asObject(doc.abilities).skills);
    Object.keys(abilitySkills).forEach(function addAbilitySkill(name) {
      if (!abilitySkills[name]) return;
      var normalized = normalizeSkillName(name);
      if (normalized) proficiencySet.add(normalized);
    });

    var out = {};
    Object.keys(SKILL_TO_ABILITY).forEach(function mapSkill(skillName) {
      var abilityKey = SKILL_TO_ABILITY[skillName];
      var modifier = abilityModifier(abilities[abilityKey]);
      if (proficiencySet.has(normalizeSkillName(skillName))) {
        modifier += profBonus;
      }
      out[skillName] = signed(modifier);
    });
    return out;
  }


  function normalizeInventoryEntry(entry) {
    if (!entry) return null;
    if (typeof entry === 'string') {
      var clean = String(entry).trim();
      return clean ? { name: clean, qty: 1, kind: 'gear', equipment_kind: 'gear', equipped: false } : null;
    }
    if (typeof entry !== 'object') return null;
    var name = String(entry.name || entry.label || entry.id || '').trim();
    if (!name) return null;
    var kind = firstNonEmpty(entry.kind, entry.type, entry.category, entry.equipment_kind, entry.item_type, 'gear').toLowerCase();
    var out = {
      name: name,
      qty: asInt(entry.qty != null ? entry.qty : entry.quantity, 1),
      kind: kind,
      equipment_kind: firstNonEmpty(entry.equipment_kind, kind),
      item_type: firstNonEmpty(entry.item_type, entry.type, kind),
      category: firstNonEmpty(entry.category, kind),
      equipped: !!entry.equipped,
      damage: firstNonEmpty(entry.damage, entry.damage_dice, entry.notes, entry.note),
      damage_dice: firstNonEmpty(entry.damage_dice, entry.damage),
      damage_type: firstNonEmpty(entry.damage_type, ''),
      versatile_damage: firstNonEmpty(entry.versatile_damage, ''),
      notes: firstNonEmpty(entry.notes, entry.note),
      range: firstNonEmpty(entry.range, entry.reach),
      properties: Array.isArray(entry.properties) ? clone(entry.properties) : [],
      price: firstNonEmpty(entry.price, ''),
      ammo_kind: firstNonEmpty(entry.ammo_kind, entry.ammoKind, ''),
      equip_slot: firstNonEmpty(entry.equip_slot, ''),
      armor_type: firstNonEmpty(entry.armor_type, ''),
      handedness: firstNonEmpty(entry.handedness, ''),
    };
    ['base_ac', 'dex_cap', 'ac_bonus', 'strength_requirement', 'weight_lbs'].forEach(function copyNumber(key) {
      if (entry[key] == null || String(entry[key]).trim() === '') return;
      var parsed = parseInt(entry[key], 10);
      if (Number.isFinite(parsed)) out[key] = parsed;
    });
    if (entry.stealth_disadvantage != null) out.stealth_disadvantage = !!entry.stealth_disadvantage;
    if (Array.isArray(entry.weapon_properties)) out.weapon_properties = clone(entry.weapon_properties);
    return out;
  }

  function buildNativeInventoryEntries(doc) {
    var equipment = asObject(doc.equipment);
    var inventory = asArray(equipment.inventory).map(normalizeInventoryEntry).filter(Boolean);
    var equipped = asObject(equipment.equipped);
    Object.keys(equipped).forEach(function syncEquipped(slot) {
      var raw = equipped[slot];
      var normalized = normalizeInventoryEntry(raw);
      if (!normalized) return;
      normalized.equipped = true;
      normalized.equip_slot = normalized.equip_slot || String(slot || '').toLowerCase();
      var existing = inventory.find(function (entry) { return String(entry.name || '').toLowerCase() === String(normalized.name || '').toLowerCase(); });
      if (existing) {
        existing.equipped = true;
        existing.equip_slot = existing.equip_slot || normalized.equip_slot || existing.equip_slot;
        if (!existing.kind || existing.kind === 'gear') existing.kind = normalized.kind || existing.kind;
        if (!existing.equipment_kind) existing.equipment_kind = normalized.equipment_kind || existing.equipment_kind;
        if (!existing.item_type) existing.item_type = normalized.item_type || existing.item_type;
        if (!existing.damage) existing.damage = normalized.damage || existing.damage;
        if (!existing.damage_dice) existing.damage_dice = normalized.damage_dice || existing.damage_dice;
        if (!existing.damage_type) existing.damage_type = normalized.damage_type || existing.damage_type;
        if (!existing.versatile_damage) existing.versatile_damage = normalized.versatile_damage || existing.versatile_damage;
        if (!existing.range) existing.range = normalized.range || existing.range;
        if (!existing.handedness) existing.handedness = normalized.handedness || existing.handedness;
        if (!existing.armor_type) existing.armor_type = normalized.armor_type || existing.armor_type;
        ['base_ac', 'dex_cap', 'ac_bonus', 'strength_requirement'].forEach(function copyNumber(key) {
          if (existing[key] == null && normalized[key] != null) existing[key] = normalized[key];
        });
      } else {
        inventory.push(normalized);
      }
    });
    return inventory;
  }

  function buildNativeCurrency(doc) {
    var equipment = asObject(doc.equipment);
    var currency = asObject(equipment.currency);
    return { cp: asInt(currency.cp, 0), sp: asInt(currency.sp, 0), ep: asInt(currency.ep, 0), gp: asInt(currency.gp, 0), pp: asInt(currency.pp, 0) };
  }

  function buildNativeGearLines(doc) {
    var equipment = asObject(doc.equipment);
    var lines = [];
    var seen = new Set();

    function addLine(text) {
      var line = String(text || '').trim();
      if (!line) return;
      var key = line.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      lines.push(line);
    }

    asArray(equipment.inventory).forEach(function addInventoryRow(entry) {
      if (entry && typeof entry === 'object') {
        var name = String(entry.name || entry.label || entry.id || '').trim();
        if (!name) return;
        var qty = asInt(entry.quantity, 1);
        addLine(qty > 1 ? (name + ' ×' + qty) : name);
        return;
      }
      addLine(entry);
    });

    var equipped = asObject(equipment.equipped);
    Object.keys(equipped).forEach(function addEquipped(slot) {
      var row = equipped[slot];
      var label = '';
      if (row && typeof row === 'object') {
        label = String(row.name || row.label || row.id || '').trim();
      } else {
        label = String(row || '').trim();
      }
      if (label) addLine(label + ' (equipped)');
    });

    asArray(asObject(doc.background).equipmentPicks).forEach(function addBackgroundPick(value) {
      addLine(value);
    });

    return lines.join('\n');
  }

  function extractSpellName(entry) {
    if (entry && typeof entry === 'object') return String(entry.name || entry.label || entry.id || '').trim();
    return String(entry || '').trim();
  }

  function normalizeActionEntry(entry, fallbackType) {
    if (!entry || typeof entry !== 'object') return null;
    var id = String(entry.id || entry.key || entry.name || '').trim();
    var name = String(entry.name || entry.label || id || '').trim();
    if (!name) return null;
    var type = String(entry.type || entry.kind || fallbackType || 'action').trim().toLowerCase();
    var details = entry.details && typeof entry.details === 'object' ? entry.details : {};
    var resource = entry.resource && typeof entry.resource === 'object' ? entry.resource : {};
    var tags = asArray(entry.tags).map(function toTag(tag) { return String(tag || '').trim(); }).filter(Boolean);
    var cost = String(entry.cost || resource.cost || entry.usage || details.usage || '').trim();
    var summary = String(entry.summary || details.summary || '').trim();
    var description = String(entry.description || details.description || details.effect || summary).trim();
    var longText = [String(entry.text || '').trim(), String(details.description || '').trim(), String(entry.effect || details.effect || '').trim(), String(entry.recovery || details.recovery || '').trim()].filter(Boolean).join('\n\n');
    return {
      id: id || name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      name: name,
      source: String(entry.source || details.source || 'native').trim(),
      type: type,
      summary: summary,
      description: description,
      desc: summary || description,
      longText: longText || description,
      attackBonus: asInt(entry.attackBonus != null ? entry.attackBonus : details.attackBonus, NaN),
      damage: String(entry.damage || details.damage || details.damageFormula || '').trim(),
      damageType: String(entry.damageType || details.damageType || '').trim(),
      range: String(entry.range || details.range || '').trim(),
      duration: String(entry.duration || details.duration || '').trim(),
      save: String(entry.save || details.save || '').trim(),
      trigger: String(entry.trigger || details.trigger || '').trim(),
      usage: String(entry.usage || details.usage || '').trim(),
      recovery: String(entry.recovery || details.recovery || '').trim(),
      resourceName: String(entry.resourceName || details.resourceName || resource.name || '').trim(),
      resourceSummary: String(entry.resourceSummary || details.resourceSummary || entry.usage || details.usage || entry.recovery || details.recovery || '').trim(),
      concentration: !!(entry.concentration || details.concentration),
      ritual: !!(entry.ritual || details.ritual),
      tags: tags,
      cost: cost,
      saveDC: String(entry.saveDC || details.saveDC || '').trim(),
    };
  }

  function buildActionLine(entry) {
    if (!entry) return '';
    var pieces = [entry.name];
    var meta = [];
    if (Number.isFinite(entry.attackBonus)) meta.push('Attack ' + signed(entry.attackBonus));
    if (entry.damage) meta.push('Damage ' + entry.damage + (entry.damageType ? ' ' + entry.damageType : ''));
    if (entry.range) meta.push('Range ' + entry.range);
    if (entry.save) meta.push('Save ' + entry.save.toUpperCase());
    if (entry.cost) meta.push('Cost ' + entry.cost);
    if (entry.concentration) meta.push('Concentration');
    if (entry.ritual) meta.push('Ritual');
    if (meta.length) pieces.push('(' + meta.join(' · ') + ')');
    if (entry.description) pieces.push('— ' + entry.description);
    return pieces.join(' ').trim();
  }

  function buildPassiveLine(entry) {
    if (!entry || typeof entry !== 'object') return '';
    var name = String(entry.name || entry.label || entry.id || '').trim();
    if (!name) return '';
    var details = entry.details && typeof entry.details === 'object' ? entry.details : {};
    var summary = String(entry.description || details.description || details.effect || '').trim();
    var tags = asArray(entry.tags).map(function toTag(tag) { return String(tag || '').trim(); }).filter(Boolean);
    var notes = [];
    if (entry.source) notes.push(titleCaseWord(entry.source));
    if (entry.tier != null) notes.push('Tier ' + asInt(entry.tier, 1));
    if (tags.length) notes.push(tags.join(', '));
    var suffix = notes.length ? ' [' + notes.join(' · ') + ']' : '';
    return summary ? (name + suffix + ' — ' + summary) : (name + suffix);
  }

  function formatSpellSlotLines(slots) {
    var slotMap = slots && typeof slots === 'object' ? slots : {};
    var levels = Object.keys(slotMap).sort(function sortLevels(a, b) { return asInt(a, 0) - asInt(b, 0); });
    if (!levels.length) return '';
    return levels.map(function toLine(levelKey) {
      var max = Math.max(0, asInt(slotMap[levelKey], 0));
      return levelKey + ': ' + max + '/' + max;
    }).join('\n');
  }

  function buildRuntimeSpellCards(runtime) {
    var spellAccess = asObject(runtime.spellAccess);
    var known = asArray(spellAccess.known);
    var preparedSet = new Set(asArray(spellAccess.prepared).map(function toPrepared(name) { return String(name || '').trim().toLowerCase(); }));
    if (!known.length) return [];
    return known.map(function toCard(entry, idx) {
      if (entry && typeof entry === 'object') {
        var cardName = String(entry.name || entry.label || entry.id || '').trim();
        if (!cardName) return null;
        return {
          id: String(entry.id || ('native-runtime-spell-' + idx)),
          name: cardName,
          spell_level: Math.max(0, asInt(entry.level != null ? entry.level : entry.spell_level, 0)),
          range: String(entry.range || '').trim(),
          casting_time: String(entry.casting_time || entry.castingTime || '').trim(),
          concentration: !!entry.concentration,
          ritual: !!entry.ritual,
          prepared: preparedSet.has(cardName.toLowerCase()),
          base_effect_text: String(entry.description || entry.effect || '').trim(),
        };
      }
      var name = String(entry || '').trim();
      if (!name) return null;
      return {
        id: 'native-runtime-spell-' + idx,
        name: name,
        spell_level: 0,
        prepared: preparedSet.has(name.toLowerCase()),
      };
    }).filter(Boolean);
  }

  function mergeSpellCards(existingCards, runtimeCards) {
    var merged = [];
    var seen = new Set();
    asArray(existingCards).concat(asArray(runtimeCards)).forEach(function addCard(card) {
      if (!card || typeof card !== 'object') return;
      var key = String(card.id || card.name || '').trim().toLowerCase();
      if (!key || seen.has(key)) return;
      seen.add(key);
      merged.push(card);
    });
    return merged;
  }

  function firstNonEmpty() {
    for (var i = 0; i < arguments.length; i += 1) {
      var candidate = arguments[i];
      if (candidate === null || candidate === undefined) continue;
      var text = String(candidate).trim();
      if (text) return text;
    }
    return '';
  }

  function nativeToLegacyCharSheet(nativeCharacter, nativeRuntime, existing) {
    var doc = asObject(nativeCharacter);
    var runtime = asObject(nativeRuntime);
    var out = asObject(clone(existing || {}));

    var identity = asObject(doc.identity);
    var presentation = asObject(doc.presentation);
    var tokenDisplay = asObject(presentation.tokenDisplay);
    var species = asObject(doc.species);
    var background = asObject(doc.background);
    var hp = resolveCanonicalHp(doc, runtime, asObject(out.hp));
    var speed = asObject(runtime.speed);
    var spellAccess = asObject(runtime.spellAccess);
    var classDisplay = asObject(runtime.classDisplay);

    var levelTotal = asInt(runtime.levelTotal, asInt(out.totalLevel, asInt(out.level, 1)));
    var profBonus = asInt(runtime.proficiencyBonus, asInt(out.profBonus, asInt(out.proficiencyBonus, 2)));

    out.name = firstNonEmpty(identity.displayName, identity.name, out.name);
    out.displayName = firstNonEmpty(identity.displayName, out.displayName, out.name);
    out.pronouns = firstNonEmpty(identity.pronouns, out.pronouns);
    out.species = firstNonEmpty(species.name, out.species);
    out.background = firstNonEmpty(background.name, out.background);
    out.alignment = firstNonEmpty(identity.alignment, out.alignment);
    out.deity = firstNonEmpty(identity.deity, out.deity);
    out.notes = firstNonEmpty(identity.notes, out.notes);
    out.inventory = buildNativeInventoryEntries(doc);
    out.inventoryEntries = clone(out.inventory);
    out.currency = buildNativeCurrency(doc);
    out.spellState = clone(asObject(doc.spellState));

    out.avatarUrl = firstNonEmpty(identity.portraitUrl, out.avatarUrl);
    out.tokenImageUrl = firstNonEmpty(identity.tokenImageUrl, out.tokenImageUrl, out.avatarUrl);
    out.portraitFrame = firstNonEmpty(presentation.portraitFrame, out.portraitFrame, 'classic');
    out.tokenDisplay = Object.assign({}, asObject(out.tokenDisplay), tokenDisplay);
    out.inventory = buildNativeInventoryEntries(doc);
    out.inventoryEntries = clone(out.inventory);
    out.currency = buildNativeCurrency(doc);
    out.spellState = clone(asObject(doc.spellState));

    if (Array.isArray(doc.classes) && doc.classes.length) {
      out.classes = clone(doc.classes);
    }

    out.level = levelTotal;
    out.totalLevel = levelTotal;
    out.profBonus = profBonus;
    out.proficiencyBonus = profBonus;

    if (classDisplay.className) {
      out.className = classDisplay.className;
    }
    if (classDisplay.classId) {
      out.classId = classDisplay.classId;
    }
    if (classDisplay.subclassId) {
      out.subclassId = classDisplay.subclassId;
    }
    if (classDisplay.subclassName) {
      out.subclass = classDisplay.subclassName;
    }
    if (classDisplay.subclassUnlockLevel != null) {
      out.subclassUnlockLevel = asInt(classDisplay.subclassUnlockLevel, 0);
    }
    if (classDisplay.subclassPending != null) {
      out.subclassPending = !!classDisplay.subclassPending;
    }

    if (runtime.ac !== undefined && runtime.ac !== null) {
      out.ac = asInt(runtime.ac, asInt(out.ac, 10));
    }

    out.maxHp = asInt(hp.max, asInt(out.maxHp, asInt(asObject(out.hp).max, 1)));
    out.currentHp = asInt(hp.current, asInt(out.currentHp, asInt(asObject(out.hp).current, out.maxHp || 1)));
    out.tempHp = asInt(hp.temp, asInt(out.tempHp, asInt(asObject(out.hp).temp, 0)));
    out.hp = {
      max: out.maxHp,
      current: out.currentHp,
      temp: out.tempHp,
    };

    var walkSpeed = asInt(speed.walk, asInt(out.speed, 30));
    if (walkSpeed > 0) {
      out.speed = walkSpeed;
    }

    var abilities = asObject(asObject(doc.abilities).scores);
    var ordered = ['str', 'dex', 'con', 'int', 'wis', 'cha'].map(function mapScore(key) {
      return asInt(abilities[key], 10);
    });
    if (ordered.some(function hasNonDefault(score) { return score !== 10; })) {
      out.stats = ordered;
    }

    if (Object.keys(spellAccess).length) {
      out.spellAccess = clone(spellAccess);
      var slots = asObject(spellAccess.slots);
      if (Object.keys(slots).length) {
        out.spellSlots = clone(slots);
      }
    }

    var runtimeActions = asArray(runtime.actions).map(function normalizeAction(entry) { return normalizeActionEntry(entry, 'action'); }).filter(Boolean);
    var runtimeBonusActions = asArray(runtime.bonusActions).map(function normalizeAction(entry) { return normalizeActionEntry(entry, 'bonus action'); }).filter(Boolean);
    var runtimeReactions = asArray(runtime.reactions).map(function normalizeAction(entry) { return normalizeActionEntry(entry, 'reaction'); }).filter(Boolean);
    var runtimePassives = asArray(runtime.passives).filter(function onlyObjects(row) { return row && typeof row === 'object'; });

    if (runtimeActions.length || runtimeBonusActions.length || runtimeReactions.length) {
      out.nativeActionCards = {
        actions: runtimeActions,
        bonusActions: runtimeBonusActions,
        reactions: runtimeReactions,
      };
    }
    if (runtimePassives.length) {
      out.nativePassives = clone(runtimePassives);
    }

    var runtimeResources = asArray(runtime.resources).filter(function onlyResourceRows(row) { return row && typeof row === 'object'; });
    if (runtimeResources.length) {
      out.nativeResources = clone(runtimeResources);
    }
    var runtimeClassMechanics = asObject(runtime.classMechanics);
    if (Object.keys(runtimeClassMechanics).length) {
      out.classMechanics = clone(runtimeClassMechanics);
    }

    var runtimeClassFeatures = asArray(runtime.classFeatures).filter(function onlyFeatureRows(row) { return row && typeof row === 'object'; });
    if (runtimeClassFeatures.length) {
      out.nativeClassFeatures = clone(runtimeClassFeatures);
    }

    var runtimeOriginTraits = asArray(runtime.originTraits).filter(function onlyTraitRows(row) { return row && typeof row === 'object'; });
    var runtimeBackgroundFeatures = asArray(runtime.backgroundFeatures).filter(function onlyBackgroundRows(row) { return row && typeof row === 'object'; });
    var runtimeFeatFeatures = asArray(runtime.featFeatures).filter(function onlyFeatRows(row) { return row && typeof row === 'object'; });
    if (runtimeOriginTraits.length || runtimeBackgroundFeatures.length) {
      out.traits = clone(runtimeOriginTraits.concat(runtimeBackgroundFeatures));
    }
    if (runtimeFeatFeatures.length) {
      out.feats = clone(runtimeFeatFeatures);
    }

    var runtimeSpellCards = buildRuntimeSpellCards(runtime);
    if (runtimeSpellCards.length) {
      out.rulesSpellbook = mergeSpellCards(out.rulesSpellbook, runtimeSpellCards);
    }

    return out;
  }

  function nativeToLegacyCharBook(nativeCharacter, nativeRuntime, existing) {
    var doc = asObject(nativeCharacter);
    var runtime = asObject(nativeRuntime);
    var out = asObject(clone(existing || {}));

    var identity = asObject(doc.identity);
    var presentation = asObject(doc.presentation);
    var tokenDisplay = asObject(presentation.tokenDisplay);
    var species = asObject(doc.species);
    var background = asObject(doc.background);
    var hp = resolveCanonicalHp(doc, runtime, {
      max: out.maxHp,
      current: out.currentHp,
      temp: out.tempHp,
    });
    var speed = asObject(runtime.speed);
    var classDisplay = asObject(runtime.classDisplay);

    var primaryClass = (Array.isArray(doc.classes) && doc.classes[0] && typeof doc.classes[0] === 'object') ? doc.classes[0] : {};
    var level = asInt(runtime.levelTotal, asInt(out.level, 1));

    out.name = firstNonEmpty(identity.displayName, identity.name, out.name);
    out.species = firstNonEmpty(species.name, out.species);
    out.background = firstNonEmpty(background.name, out.background);
    out.className = firstNonEmpty(classDisplay.className, primaryClass.name, out.className);
    out.subclass = firstNonEmpty(classDisplay.subclassName, primaryClass.subclass, out.subclass);
    out.level = level;
    out.avatarUrl = firstNonEmpty(identity.portraitUrl, out.avatarUrl);
    out.tokenImageUrl = firstNonEmpty(identity.tokenImageUrl, out.tokenImageUrl);
    out.portraitFrame = firstNonEmpty(presentation.portraitFrame, out.portraitFrame, 'classic');
    out.tokenDisplay = Object.assign({}, asObject(out.tokenDisplay), tokenDisplay);

    if (runtime.ac !== undefined && runtime.ac !== null) {
      out.ac = asInt(runtime.ac, asInt(out.ac, 10));
    }

    out.maxHp = asInt(hp.max, asInt(out.maxHp, 1));
    out.currentHp = asInt(hp.current, asInt(out.currentHp, out.maxHp || 1));
    out.tempHp = asInt(hp.temp, asInt(out.tempHp, 0));

    var walkSpeed = asInt(speed.walk, asInt(out.speed, 30));
    if (walkSpeed > 0) {
      out.speed = walkSpeed;
    }

    var abilities = asObject(asObject(doc.abilities).scores);
    var abilityScores = asObject(out.abilityScores);
    abilityScores.strength = asInt(abilities.str, asInt(abilityScores.strength, 10));
    abilityScores.dexterity = asInt(abilities.dex, asInt(abilityScores.dexterity, 10));
    abilityScores.constitution = asInt(abilities.con, asInt(abilityScores.constitution, 10));
    abilityScores.intelligence = asInt(abilities.int, asInt(abilityScores.intelligence, 10));
    abilityScores.wisdom = asInt(abilities.wis, asInt(abilityScores.wisdom, 10));
    abilityScores.charisma = asInt(abilities.cha, asInt(abilityScores.charisma, 10));
    out.abilityScores = abilityScores;

    var spellAccess = asObject(runtime.spellAccess);
    if (Object.keys(spellAccess).length) {
      out.spellAccess = clone(spellAccess);
    }
    var slots = asObject(spellAccess.slots);
    if (Object.keys(slots).length) {
      out.spellSlots = formatSpellSlotLines(slots);
    }
    var spellAbility = String(spellAccess.ability || '').trim().toUpperCase();
    if (spellAbility) out.spellAbility = spellAbility;
    if (spellAccess.saveDc != null) out.spellSaveDc = String(asInt(spellAccess.saveDc, asInt(out.spellSaveDc, 8)));
    if (spellAccess.attackBonus != null) out.spellAttack = signed(spellAccess.attackBonus);

    var runtimeActions = asArray(runtime.actions).map(function normalizeAction(entry) { return normalizeActionEntry(entry, 'action'); }).filter(Boolean);
    var runtimeBonusActions = asArray(runtime.bonusActions).map(function normalizeAction(entry) { return normalizeActionEntry(entry, 'bonus action'); }).filter(Boolean);
    var runtimeReactions = asArray(runtime.reactions).map(function normalizeAction(entry) { return normalizeActionEntry(entry, 'reaction'); }).filter(Boolean);
    var actionLines = [];
    if (runtimeActions.length) {
      actionLines = actionLines.concat(runtimeActions.map(buildActionLine));
    }
    if (runtimeBonusActions.length) {
      actionLines.push('Bonus Actions:');
      actionLines = actionLines.concat(runtimeBonusActions.map(buildActionLine));
    }
    if (runtimeReactions.length) {
      actionLines.push('Reactions:');
      actionLines = actionLines.concat(runtimeReactions.map(buildActionLine));
    }
    if (actionLines.length) {
      out.actions = actionLines.filter(Boolean).join('\n');
    }

    var runtimePassives = asArray(runtime.passives);
    if (runtimePassives.length) {
      out.features = runtimePassives.map(buildPassiveLine).filter(Boolean).join('\n');
      out.nativePassives = clone(runtimePassives);
    }

    var runtimeResources = asArray(runtime.resources).filter(function onlyResourceRows(row) { return row && typeof row === 'object'; });
    if (runtimeResources.length) {
      out.nativeResources = clone(runtimeResources);
    }
    var runtimeClassMechanics = asObject(runtime.classMechanics);
    if (Object.keys(runtimeClassMechanics).length) {
      out.classMechanics = clone(runtimeClassMechanics);
    }

    var runtimeClassFeatures = asArray(runtime.classFeatures).filter(function onlyFeatureRows(row) { return row && typeof row === 'object'; });
    if (runtimeClassFeatures.length) {
      out.nativeClassFeatures = clone(runtimeClassFeatures);
    }

    var runtimeOriginTraits = asArray(runtime.originTraits).filter(function onlyTraitRows(row) { return row && typeof row === 'object'; });
    var runtimeBackgroundFeatures = asArray(runtime.backgroundFeatures).filter(function onlyBackgroundRows(row) { return row && typeof row === 'object'; });
    var runtimeFeatFeatures = asArray(runtime.featFeatures).filter(function onlyFeatRows(row) { return row && typeof row === 'object'; });
    if (runtimeOriginTraits.length || runtimeBackgroundFeatures.length) {
      out.traits = clone(runtimeOriginTraits.concat(runtimeBackgroundFeatures));
    }
    if (runtimeFeatFeatures.length) {
      out.feats = clone(runtimeFeatFeatures);
    }

    if (runtimeActions.length || runtimeBonusActions.length || runtimeReactions.length) {
      out.nativeActionCards = {
        actions: clone(runtimeActions),
        bonusActions: clone(runtimeBonusActions),
        reactions: clone(runtimeReactions),
      };
    }

    var existingSkills = asObject(out.skills);
    var hasExistingSkills = Object.keys(existingSkills).some(function hasSkillValue(skillKey) {
      return String(existingSkills[skillKey] || '').trim().length > 0;
    });
    if (!hasExistingSkills) {
      out.skills = buildNativeSkillMap(doc, runtime);
    }

    out.gear = buildNativeGearLines(doc);

    if (spellAccess.known != null || spellAccess.prepared != null) {
      var known = asArray(spellAccess.known).map(function toKnown(entry) {
        if (entry && typeof entry === 'object') return String(entry.name || entry.label || entry.id || '').trim();
        return String(entry || '').trim();
      }).filter(Boolean);
      var preparedSet = new Set(asArray(spellAccess.prepared).map(function toPrepared(entry) {
        if (entry && typeof entry === 'object') return String(entry.name || entry.label || entry.id || '').trim().toLowerCase();
        return String(entry || '').trim().toLowerCase();
      }).filter(Boolean));
      if (known.length) {
        out.spells = known.map(function mapKnown(name) {
          return preparedSet.has(String(name).toLowerCase()) ? (name + ' (Prepared)') : name;
        }).join('\n');
      }
    } else if (out.spells && typeof out.spells === 'object' && !Array.isArray(out.spells)) {
      // spells was stored as a structured object (Python charBook format: {known, prepared, slots}).
      // Normalize it to the plain-text list format expected by the Magic tab textarea.
      var spellsObj = out.spells;
      var existingKnown = asArray(spellsObj.known);
      var existingPrepared = new Set(asArray(spellsObj.prepared).map(function toPreparedEntry(e) {
        return extractSpellName(e).toLowerCase();
      }).filter(Boolean));
      out.spells = existingKnown.map(function toSpellLine(e) {
        var name = extractSpellName(e);
        if (!name) return null;
        return existingPrepared.has(name.toLowerCase()) ? (name + ' (Prepared)') : name;
      }).filter(Boolean).join('\n');
    }

    var combatData = asObject(runtime.combat);
    var runtimeSavingThrows = asObject(combatData.savingThrows);
    var abilityKeyToFullName = { str: 'Strength', dex: 'Dexterity', con: 'Constitution', int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma' };
    var existingSavingThrows = asObject(out.savingThrows);
    var hasExistingSaves = Object.keys(existingSavingThrows).some(function hasSave(k) { return !!existingSavingThrows[k]; });
    if (!hasExistingSaves && Object.keys(runtimeSavingThrows).length) {
      var computedSaves = {};
      Object.keys(runtimeSavingThrows).forEach(function toSaveLine(key) {
        var fullName = abilityKeyToFullName[key.toLowerCase()];
        if (!fullName) return;
        var val = asInt(runtimeSavingThrows[key], null);
        if (!Number.isFinite(val)) return;
        computedSaves[fullName] = (val >= 0 ? '+' : '') + String(val);
      });
      if (Object.keys(computedSaves).length) {
        out.savingThrows = computedSaves;
      }
    }

    return out;
  }

  function isNativeProfile(profile) {
    if (!profile || typeof profile !== 'object') return false;
    var nativeCharacter = asObject(profile.nativeCharacter);
    var nativeRuntime = asObject(profile.nativeRuntime);
    return Object.keys(nativeCharacter).length > 0 || Object.keys(nativeRuntime).length > 0;
  }

  function mapProfileToPlay(profile, opts) {
    var source = asObject(profile);
    var options = asObject(opts);
    var preferNative = options.preferNative !== false;

    var nativeCharacter = asObject(source.nativeCharacter);
    var nativeRuntime = asObject(source.nativeRuntime);

    var hasNative = Object.keys(nativeCharacter).length > 0 || Object.keys(nativeRuntime).length > 0;
    var out = clone(source) || {};

    if (!hasNative || !preferNative) {
      return out;
    }

    out.charSheet = nativeToLegacyCharSheet(nativeCharacter, nativeRuntime, source.charSheet);
    out.charBook = nativeToLegacyCharBook(nativeCharacter, nativeRuntime, source.charBook);
    var runtimeHp = resolveCanonicalHp(nativeCharacter, nativeRuntime, {
      max: asInt(out.charSheet && out.charSheet.maxHp, asInt(out.charBook && out.charBook.maxHp, asInt(out.hp, 1))),
      current: asInt(out.charSheet && out.charSheet.currentHp, asInt(out.charBook && out.charBook.currentHp, asInt(out.curhp, asInt(out.hp, 1)))),
      temp: asInt(out.charSheet && out.charSheet.tempHp, asInt(out.charBook && out.charBook.tempHp, asInt(out.tempHp, 0))),
    });
    var runtimeSpeed = asObject(nativeRuntime.speed);
    var mappedMaxHp = asInt(runtimeHp.max, asInt(out.charSheet && out.charSheet.maxHp, asInt(out.charBook && out.charBook.maxHp, asInt(out.hp, 0))));
    var mappedCurrentHp = asInt(runtimeHp.current, asInt(out.charSheet && out.charSheet.currentHp, asInt(out.charBook && out.charBook.currentHp, mappedMaxHp)));
    var mappedTempHp = asInt(runtimeHp.temp, asInt(out.charSheet && out.charSheet.tempHp, asInt(out.charBook && out.charBook.tempHp, asInt(out.tempHp, 0))));
    out.hp = mappedMaxHp;
    out.curhp = mappedCurrentHp;
    out.tempHp = mappedTempHp;
    out.nativeRuntime = Object.assign({}, asObject(out.nativeRuntime), {
      hp: { max: mappedMaxHp, current: mappedCurrentHp, temp: mappedTempHp },
      combat: Object.assign({}, asObject(asObject(out.nativeRuntime).combat), {
        maxHP: mappedMaxHp,
        currentHP: mappedCurrentHp,
      }),
    });
    var runtimeCombat = asObject(nativeRuntime.combat);
    if (runtimeCombat.ac !== undefined && runtimeCombat.ac !== null) {
      out.ac = asInt(runtimeCombat.ac, asInt(out.ac, 0));
    } else if (nativeRuntime.ac !== undefined && nativeRuntime.ac !== null) {
      out.ac = asInt(nativeRuntime.ac, asInt(out.ac, 0));
    }
    if (runtimeCombat.initiative !== undefined && runtimeCombat.initiative !== null) {
      out.initiative = asInt(runtimeCombat.initiative, asInt(out.initiative, 0));
    }
    var mappedSpeed = asInt(runtimeCombat.speed, asInt(runtimeSpeed.walk, asInt(out.speed, 0)));
    if (mappedSpeed > 0) out.speed = mappedSpeed;
    var mappedLevel = asInt(nativeRuntime.levelTotal, asInt(out.charSheet && out.charSheet.totalLevel, asInt(out.level, 0)));
    if (mappedLevel > 0) out.level = mappedLevel;
    out.__nativeMapped = true;
    return out;
  }

  function mapCharacterToToken(charDocument, existingTokenData) {
    var doc = asObject(charDocument);
    var token = asObject(existingTokenData);
    var runtime = asObject(doc.runtime);
    var combat = asObject(runtime.combat);
    var hp = resolveCanonicalHp(doc, runtime, {
      max: asInt(combat.maxHP, asInt(token.maxHP, 10)),
      current: asInt(combat.currentHP, asInt(token.currentHP, 10)),
      temp: asInt(token.tempHP, 0),
    });
    var species = asObject(runtime.species);
    var identity = asObject(doc.identity);

    var mappedMaxHp = asInt(hp.max, asInt(combat.maxHP, asInt(token.maxHP, 10)));
    var mappedCurrentHp = asInt(hp.current, asInt(combat.currentHP, asInt(hp.max, asInt(combat.maxHP, asInt(token.currentHP, 10)))));

    return {
      ...token,
      name: firstNonEmpty(doc.name, identity.name, token.name),
      portraitUrl: firstNonEmpty(identity.portraitUrl, doc.portraitUrl, token.portraitUrl),
      tokenImageUrl: firstNonEmpty(identity.tokenImageUrl, doc.tokenImageUrl, token.tokenImageUrl),
      maxHP: mappedMaxHp,
      currentHP: mappedCurrentHp,
      ac: asInt(combat.ac, asInt(token.ac, 10)),
      speed: asInt(combat.speed, asInt(species.speed, asInt(token.speed, 30))),
      initiative: asInt(combat.initiative, 0),
      darkvision: asInt(species.darkvision, 0),
      size: firstNonEmpty(species.size, token.size, 'Medium'),
      conditions: Array.isArray(token.conditions) ? token.conditions.slice() : [],
      spellSlots: asObject(runtime.spellSlots),
      spellSlotsUsed: asObject(doc.spellSlotsUsed),
    };
  }

  global.CharacterRuntimeMappers = {
    isNativeProfile: isNativeProfile,
    nativeToLegacyCharSheet: nativeToLegacyCharSheet,
    nativeToLegacyCharBook: nativeToLegacyCharBook,
    mapProfileToPlay: mapProfileToPlay,
    mapCharacterToToken: mapCharacterToToken,
  };
})(window);
