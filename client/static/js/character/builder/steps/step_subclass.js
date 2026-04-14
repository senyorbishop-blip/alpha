(function initCharacterBuilderStepSubclass(global) {
  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function normalizeId(value) {
    return String(value || '').trim().toLowerCase();
  }

  function registerStep(step) {
    if (!global.CharacterBuilderStepModules || typeof global.CharacterBuilderStepModules !== 'object') {
      global.CharacterBuilderStepModules = {};
    }
    global.CharacterBuilderStepModules[step.id] = step;
  }

  function ensureCatalogLoaded() {
    const api = global.CharacterBuilderAPI;
    if (!api || typeof api.fetchCatalog !== 'function') return;
    api.fetchCatalog({ rulesMode: 'casual' }).catch(function ignoreFailure() {});
  }

  function ensureSubclassStyles() {
    if (document.getElementById('character-builder-step-subclass-style')) return;
    var style = document.createElement('style');
    style.id = 'character-builder-step-subclass-style';
    style.textContent = [
      '.builder-subclass-layout { display:grid; grid-template-columns: minmax(240px, 0.95fr) minmax(320px, 1.15fr); gap:16px; align-items:start; }',
      '.builder-subclass-column { min-width:0; }',
      '.builder-subclass-select-wrap { margin-bottom:12px; }',
      '.builder-subclass-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap:12px; }',
      '.builder-subclass-card { position:relative; border:1px solid rgba(42,51,64,0.9); border-radius:14px; background:linear-gradient(180deg, rgba(18,22,28,0.96), rgba(10,13,18,0.98)); padding:14px 14px 12px; cursor:pointer; transition:transform 0.2s ease,border-color 0.2s ease,box-shadow 0.2s ease; min-height:180px; }',
      '.builder-subclass-card:hover { transform:translateY(-2px); border-color:rgba(201,168,76,0.42); box-shadow:0 12px 28px rgba(0,0,0,0.35); }',
      '.builder-subclass-card.selected { border-color:rgba(0,212,184,0.55); box-shadow:0 0 0 1px rgba(0,212,184,0.18), 0 16px 34px rgba(0,0,0,0.38); }',
      '.builder-subclass-card h4 { margin:0 0 6px; font-family:"Cinzel",serif; font-size:0.82rem; letter-spacing:0.04em; color:#f3e7c4; }',
      '.builder-subclass-flavor { font-size:0.68rem; line-height:1.5; color:rgba(220,214,200,0.84); min-height:42px; margin-bottom:10px; }',
      '.builder-subclass-tags { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }',
      '.builder-subclass-tag { border:1px solid rgba(201,168,76,0.22); border-radius:999px; padding:2px 7px; font-size:0.56rem; color:#c9a84c; font-family:"Cinzel",serif; letter-spacing:0.04em; }',
      '.builder-subclass-signatures { display:flex; flex-direction:column; gap:5px; }',
      '.builder-subclass-signature { font-size:0.62rem; color:rgba(168,159,142,0.94); display:flex; gap:6px; line-height:1.45; }',
      '.builder-subclass-signature::before { content:"◆"; color:rgba(0,212,184,0.72); font-size:0.42rem; margin-top:0.35rem; flex-shrink:0; }',
      '.builder-subclass-card .builder-subclass-check { position:absolute; top:10px; right:10px; width:18px; height:18px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:rgba(0,212,184,0.16); border:1px solid rgba(0,212,184,0.35); color:#00d4b8; opacity:0; transition:opacity 0.18s ease; font-size:0.7rem; }',
      '.builder-subclass-card.selected .builder-subclass-check { opacity:1; }',
      '.builder-subclass-detail { border:1px solid rgba(201,168,76,0.22); border-radius:16px; background:linear-gradient(180deg, rgba(12,16,21,0.98), rgba(7,10,14,0.99)); min-height:420px; overflow:hidden; }',
      '.builder-subclass-detail.empty { display:flex; align-items:center; justify-content:center; text-align:center; padding:24px; color:rgba(168,159,142,0.78); font-size:0.74rem; }',
      '.builder-subclass-detail-head { padding:18px 18px 14px; border-bottom:1px solid rgba(201,168,76,0.14); }',
      '.builder-subclass-detail-kicker { font-size:0.58rem; text-transform:uppercase; letter-spacing:0.12em; color:rgba(0,212,184,0.76); margin-bottom:7px; font-family:"Cinzel",serif; }',
      '.builder-subclass-detail-title { font-family:"Cinzel",serif; font-size:1.18rem; color:#f3e7c4; margin:0 0 8px; }',
      '.builder-subclass-detail-flavor { font-size:0.75rem; line-height:1.65; color:rgba(220,214,200,0.88); margin-bottom:12px; }',
      '.builder-subclass-detail-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:10px; }',
      '.builder-subclass-detail-stat { border:1px solid rgba(42,51,64,0.82); border-radius:12px; padding:10px 12px; background:rgba(255,255,255,0.02); }',
      '.builder-subclass-detail-stat strong { display:block; color:#f3e7c4; font-size:0.74rem; margin-bottom:3px; }',
      '.builder-subclass-detail-stat span { font-size:0.64rem; color:rgba(168,159,142,0.92); line-height:1.45; }',
      '.builder-subclass-detail-body { padding:16px 18px 18px; display:flex; flex-direction:column; gap:14px; }',
      '.builder-subclass-section { border:1px solid rgba(42,51,64,0.82); border-radius:14px; background:rgba(255,255,255,0.02); overflow:hidden; }',
      '.builder-subclass-section-head { padding:10px 12px; border-bottom:1px solid rgba(42,51,64,0.78); font-family:"Cinzel",serif; font-size:0.68rem; letter-spacing:0.08em; color:#c9a84c; text-transform:uppercase; }',
      '.builder-subclass-section-body { padding:12px; }',
      '.builder-subclass-roadmap { display:flex; flex-direction:column; gap:10px; }',
      '.builder-subclass-roadmap-row { display:grid; grid-template-columns: 52px 1fr; gap:10px; align-items:start; }',
      '.builder-subclass-roadmap-level { border:1px solid rgba(0,212,184,0.24); border-radius:999px; color:#00d4b8; font-family:"Cinzel",serif; font-size:0.66rem; padding:5px 8px; text-align:center; }',
      '.builder-subclass-roadmap-content { display:flex; flex-direction:column; gap:7px; }',
      '.builder-subclass-feature-card { border:1px solid rgba(42,51,64,0.7); border-radius:12px; padding:10px 11px; background:rgba(6,8,10,0.34); }',
      '.builder-subclass-feature-card strong { display:block; font-size:0.74rem; color:#f3e7c4; margin-bottom:5px; }',
      '.builder-subclass-feature-card div { font-size:0.67rem; line-height:1.58; color:rgba(213,208,198,0.9); }',
      '.builder-subclass-chooser-copy { font-size:0.68rem; line-height:1.6; color:rgba(168,159,142,0.9); }',
      '@media (max-width: 1100px) { .builder-subclass-layout { grid-template-columns: 1fr; } .builder-subclass-detail { min-height:0; } }',
      '@media (max-width: 720px) { .builder-subclass-detail-grid { grid-template-columns: 1fr; } .builder-subclass-grid { grid-template-columns: 1fr; } }'
    ].join('\n');
    document.head.appendChild(style);
  }

  function getCurrentClassId(draft) {
    const classData = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    const direct = String(classData.id || '').trim();
    if (direct) return direct;

    const classes = Array.isArray(draft && draft.classes) ? draft.classes : [];
    if (!classes.length || !classes[0] || typeof classes[0] !== 'object') return '';
    return String(classes[0].classId || classes[0].id || '').trim();
  }

  function getClassRow(classId) {
    const api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') return null;
    const catalog = api.getCachedCatalog();
    const rows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const key = normalizeId(classId);
    if (!key) return null;
    return rows.find(function findRow(row) {
      return normalizeId(row && row.id) === key;
    }) || null;
  }

  function getBuilderLevel(draft) {
    const progression = draft && draft.progression && typeof draft.progression === 'object'
      ? draft.progression
      : {};
    const parsed = parseInt(progression.level, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
  }

  function getSubclassUnlockLevel(classId) {
    const row = getClassRow(classId);
    const parsed = parseInt(row && row.subclassLevel, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function getSubclassRows(classId) {
    const api = global.CharacterBuilderAPI;
    if (!api || typeof api.getSubclassesForClass !== 'function') return [];
    const rows = api.getSubclassesForClass(classId);
    return rows.map(function toEntry(row) {
      return {
        id: String(row && row.id || '').trim(),
        name: String(row && row.displayName || row && row.id || '').trim(),
        classId: String(row && (row.classId || row.parentClassId) || '').trim(),
        flavorText: String(row && row.flavorText || '').trim(),
        featureUnlocksByLevel: row && row.featureUnlocksByLevel && typeof row.featureUnlocksByLevel === 'object'
          ? row.featureUnlocksByLevel
          : {},
        features: Array.isArray(row && row.features) ? row.features : [],
        featureDefinitions: row && row.featureDefinitions && typeof row.featureDefinitions === 'object'
          ? row.featureDefinitions
          : {},
      };
    }).filter(function validEntry(entry) {
      return !!entry.id;
    });
  }

  function getSelectedSubclassId(draft) {
    const classData = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    return String(classData.subclassId || classData.subclass || '').trim();
  }

  var SUBCLASS_PROFILE_OVERRIDES = {
    'wild-magic': {
      tags: ['Chaos Engine', 'Risk / Reward', 'Fate Twisting'],
      chooserSummary: 'Wild Magic is the volatility path: surge events, advantage pressure through Tides of Chaos, and reactive fate-twisting with Bend Luck.',
      fantasy: 'Pick Wild Magic if you want your sorcerer turns to feel unpredictable, explosive, and tactical around chaos management rather than pure consistency.',
    },
    'draconic-bloodline': {
      tags: ['Elemental Bloodline', 'Durable Caster', 'Draconic Presence'],
      chooserSummary: 'Draconic Bloodline is the focused power path: elemental identity, extra durability from draconic resilience, and a late-game battlefield presence aura.',
      fantasy: 'Pick Draconic Bloodline if you want a clearer elemental identity, sturdier sorcerer baseline, and visible dragon-themed power spikes as you level.',
    },
    'life-domain': {
      tags: ['Healing Specialist', 'Emergency Recovery', 'Support Anchor'],
      chooserSummary: 'Life Domain turns every healing spell into a stronger investment and adds a mass-stabilization Channel Divinity that can rescue multiple allies at once.',
      fantasy: 'Pick Life Domain if you want to be the party\'s reliable recovery anchor: bigger healing numbers from level 1, an emergency tool that stabilizes the whole group, and a passive that keeps you functional while you keep everyone else alive.',
    },
    'light-domain': {
      tags: ['Radiant Blaster', 'Anti-Darkness', 'Reactive Defense'],
      chooserSummary: 'Light Domain trades healing focus for solar aggression: a blinding reaction to protect allies, a Channel Divinity that clears magical darkness and punishes clusters, and cantrips that hit harder at level 8.',
      fantasy: 'Pick Light Domain if you want your cleric to be an active threat: dispel shadows, scorch packed formations with Radiance of the Dawn, and protect allies with a defensive flare that can deflect dangerous swings.',
    },
    'trickery-domain': {
      tags: ['Illusion & Misdirection', 'Stealth Support', 'Slippery Caster'],
      chooserSummary: 'Trickery Domain adds misdirection and positioning tricks to the divine toolkit: stealth buffs for allies, an illusory double that bends where spells appear to come from, and short-window invisibility for resets.',
      fantasy: 'Pick Trickery Domain if you want a cleric who operates through deception and setup: hand out stealth advantage before infiltrations, use your duplicate to split enemy attention, and vanish when the battlefield needs to be reset around you.',
    },
    'war-domain': {
      tags: ['Battle Priest', 'Frontline Divine', 'Accuracy Support'],
      chooserSummary: 'War Domain is a full martial upgrade for the cleric: heavy armor, martial weapons, a bonus-action weapon attack, and Channel Divinity options that convert near-misses into hits for you and your allies.',
      fantasy: 'Pick War Domain if you want your cleric on the front line trading real blows: heavier equipment, extra weapon pressure on strong turns, and divine accuracy that makes your team\'s most important attacks land more often.',
    },
    assassin: {
      tags: ['Ambush Burst', 'Infiltration', 'Surprise Payoff'],
      chooserSummary: 'Assassin is the opener rogue: win mission setup, strike before enemies settle, and convert surprise windows into lethal burst turns.',
      fantasy: 'Pick Assassin if you want first-round timing, infiltration prep, and ruthless single-target elimination to define your play.',
    },
    champion: {
      tags: ['Crit Pressure', 'Athletic Resilience', 'Polished Fundamentals'],
      chooserSummary: 'Champion keeps your fighter loop clean and reliable: better critical pressure, superior athletic presence, and late-fight durability.',
      fantasy: 'Pick Champion if you want a dependable front-line identity that wins through excellent weapon fundamentals instead of resource-heavy complexity.',
    },
    battlemaster: {
      tags: ['Maneuver Tactics', 'Superiority Dice', 'Battlefield Control'],
      chooserSummary: 'Battle Master turns your fighter into a tactical controller with maneuver picks, superiority dice pacing, and explicit combat timing decisions.',
      fantasy: 'Pick Battle Master if you want active turn-by-turn decision making: spend dice deliberately, pressure positioning, and shape the battlefield around your team.',
    },
    'eldritch-knight': {
      tags: ['Weapon + Spell Weave', 'Arcane Defense', 'Hybrid Pressure'],
      chooserSummary: 'Eldritch Knight layers one-third casting onto fighter fundamentals so you can weave cantrips, leveled spells, and weapon attacks in the same fight.',
      fantasy: 'Pick Eldritch Knight if you want an armored battle-mage loop with bonded weapons, magical control pressure, and clear spell-plus-steel turn planning.',
    },
    thief: {
      tags: ['Fast Hands', 'Mobility', 'Object Tempo'],
      chooserSummary: 'Thief is the opportunist rogue: fast object interaction, vertical movement, and utility tempo that wins fights through positioning and tools.',
      fantasy: 'Pick Thief if you want climbing, item exploitation, and quick-turn opportunism to matter every session.',
    },
    'arcane-trickster': {
      tags: ['Stealth Magic', 'Mage Hand Utility', 'Hybrid Control'],
      chooserSummary: 'Arcane Trickster blends rogue setup with magic: stealth casting, mage hand manipulation, and control tools that feed precision attacks.',
      fantasy: 'Pick Arcane Trickster if you want a rogue-caster loop where spells, deception, and Sneak Attack setups all reinforce each other.',
    },
    'college-of-glamour': {
      tags: ['Fey Presence', 'Ally Reposition', 'Social Control'],
      chooserSummary: 'Glamour bards spend inspiration on battlefield staging: temporary hit points, reaction movement, and command-pressure turns.',
      fantasy: 'Pick Glamour if you want your bard to feel like a fey battle director who protects allies, repositions the team, and dominates social scenes.',
    },
    'college-of-lore': {
      tags: ['Skill Mastery', 'Reaction Disruption', 'Off-List Magic'],
      chooserSummary: 'Lore bards focus on broad expertise and clutch reactions, then widen spell identity through Magical Discoveries and late-game skill spikes.',
      fantasy: 'Pick Lore if you want maximum flexibility: stronger checks, Cutting Words timing, and extra cross-list spell access that adapts to party gaps.',
    },
    'college-of-valor': {
      tags: ['Martial Bard', 'Combat Inspiration', 'Spell + Steel'],
      chooserSummary: 'Valor bards add medium armor, shields, and martial weapons, then evolve into a spell-and-weapon tempo class with Extra Attack and Battle Magic.',
      fantasy: 'Pick Valor if you want your bard closer to the front line, supporting allies while still trading attacks and keeping combat pressure visible.',
    },
    'oath-of-devotion': {
      tags: ['Knightly Virtue', 'Radiant Presence', 'Protective Aura'],
      chooserSummary: 'A classic holy guardian path focused on sacred weapon certainty, anti-charm protection, and radiant battlefield leadership.',
      fantasy: 'Devotion rewards steadfast frontline play: hold formation, keep allies stable, and punish evil with unwavering divine pressure.',
    },
    'oath-of-the-ancients': {
      tags: ['Nature & Hope', 'Spell Defense', 'Resilient Warden'],
      chooserSummary: 'A luminous warden path that protects life and joy, with anti-magic resilience and elder-champion staying power.',
      fantasy: 'Ancients fights like a living bulwark: blunt hostile magic, endure attrition, and keep the party alive through pressure.',
    },
    'oath-of-vengeance': {
      tags: ['Relentless Pursuit', 'Target Lockdown', 'Execution Pressure'],
      chooserSummary: 'An aggressive avenger path built around mark-and-execute pressure, pursuit tools, and punishing single-target focus.',
      fantasy: 'Vengeance is for players who want to hunt priority threats, force duels, and finish key enemies before they recover.',
    },
    hunter: {
      tags: ['Anti-Prey Specialist', 'Tactical Forks', 'Veteran Slayer'],
      chooserSummary: 'Hunter is the clean tactical ranger: pick offensive prey style, defensive counter-patterns, and a late multiattack mode that defines your battlefield lane.',
      fantasy: 'Pick Hunter if you want practical combat branching with clear prey pressure, survival tools, and veteran slayer identity rather than companion play.',
    },
    'beast-master': {
      tags: ['Companion Partnership', 'Command Economy', 'Shared Hunt'],
      chooserSummary: 'Beast Master is a two-body ranger loop: choose your primal beast frame, manage command cadence, and scale coordinated pressure across levels.',
      fantasy: 'Pick Beast Master if you want your turns to include companion command decisions, partner positioning, and shared magic synergy.',
    },
    'gloom-stalker': {
      tags: ['Ambush Opener', 'Darkness Control', 'Reaction Survival'],
      chooserSummary: 'Gloom Stalker is an opening-turn predator: initiative tempo, first-round damage spike, darkness stealth leverage, and reactive survival tools.',
      fantasy: 'Pick Gloom Stalker if you want first-round impact, shadow-map advantage, and relentless opener pressure.',
    },
    'fiend-patron': {
      tags: ['Infernal Aggression', 'Temp HP Snowball', 'Punishing Finisher'],
      chooserSummary: 'Fiend warlocks convert kills into survivability, push infernal damage pressure, and end fights with brutal punishment tools.',
      fantasy: 'Pick The Fiend if you want your warlock to feel relentless: snowball temporary hit points, adapt resistances, and slam priority targets with nightmare-level punishment.',
    },
    'archfey-patron': {
      tags: ['Glamour Control', 'Reactive Escape', 'Fey Mobility'],
      chooserSummary: 'Archfey warlocks lean on charm/fear pressure, slippery reaction escapes, and psychological control over battlefield flow.',
      fantasy: 'Pick The Archfey if you want a tricky controller: disrupt minds, vanish when threatened, and win fights through slippery repositioning and social menace.',
    },
    'great-old-one-patron': {
      tags: ['Telepathy', 'Psychic Weirdness', 'Reality-Bending Defense'],
      chooserSummary: 'Great Old One warlocks specialize in telepathic influence, unsettling psychic pressure, and strange defensive manipulation.',
      fantasy: 'Pick The Great Old One if you want your warlock to feel alien and invasive: silent communication, warped defense timing, and eerie mind-control identity.',
    },
  };

  function subclassProfile(entry) {
    var key = normalizeId(entry && entry.id);
    if (!key) return null;
    return SUBCLASS_PROFILE_OVERRIDES[key] || null;
  }

  function classifySubclass(entry) {
    var profile = subclassProfile(entry);
    if (profile && Array.isArray(profile.tags) && profile.tags.length) {
      return profile.tags.slice(0, 3);
    }
    const haystack = [entry && entry.flavorText, (entry && entry.features || []).map(function (f) { return f && (f.displayName + ' ' + (f.description || '')); }).join(' ')].join(' ').toLowerCase();
    const tags = [];
    if (/(heal|ward|protect|aura|defense|shield|resistance)/.test(haystack)) tags.push('Support / Defense');
    if (/(stealth|hidden|assassin|trick|illusion|infiltrat|deceiv)/.test(haystack)) tags.push('Stealth / Trickery');
    if (/(summon|companion|beast|pet|wild shape)/.test(haystack)) tags.push('Companion / Forms');
    if (/(teleport|misty|mobility|speed|leap|movement|flight)/.test(haystack)) tags.push('Mobility');
    if (/(spell|magic|arcane|divine|ritual|caster|sorcer|wizard|warlock)/.test(haystack)) tags.push('Magic');
    if (/(fright|charm|restrain|prone|save|control|push|slow)/.test(haystack)) tags.push('Control');
    if (/(critical|damage|smite|strike|attack|burst|weapon)/.test(haystack)) tags.push('Damage / Burst');
    if (!tags.length) tags.push('Specialist');
    return tags.slice(0, 3);
  }

  function buildSignatureRows(entry) {
    var features = Array.isArray(entry && entry.features) ? entry.features : [];
    var defs = entry && entry.featureDefinitions && typeof entry.featureDefinitions === 'object'
      ? entry.featureDefinitions
      : {};
    return features.slice(0, 3).map(function (feature) {
      var id = String(feature && feature.id || '').trim();
      var def = id && defs[id] && typeof defs[id] === 'object' ? defs[id] : {};
      return {
        title: String(feature && feature.displayName || '').trim(),
        text: String(def.summary || feature && feature.description || '').trim(),
        actionType: String(def.type || '').trim(),
      };
    }).filter(function (row) { return !!row.title; });
  }

  function buildRoadmapRows(entry) {
    var features = Array.isArray(entry && entry.features) ? entry.features.slice() : [];
    var defs = entry && entry.featureDefinitions && typeof entry.featureDefinitions === 'object'
      ? entry.featureDefinitions
      : {};
    features.sort(function (a, b) {
      return (parseInt(a && a.level, 10) || 0) - (parseInt(b && b.level, 10) || 0);
    });
    var grouped = {};
    features.forEach(function (feature) {
      var level = String(parseInt(feature && feature.level, 10) || 0);
      if (!grouped[level]) grouped[level] = [];
      grouped[level].push(feature);
    });
    return Object.keys(grouped).sort(function (a, b) { return parseInt(a, 10) - parseInt(b, 10); }).map(function (level) {
      var rows = grouped[level].map(function (feature) {
        var id = String(feature && feature.id || '').trim();
        var def = id && defs[id] && typeof defs[id] === 'object' ? defs[id] : {};
        return {
          displayName: String(feature && feature.displayName || '').trim() || 'Feature',
          description: String(def.description || feature && feature.description || '').trim() || 'Feature text not available yet.',
          type: String(def.type || '').trim(),
          section: String(def.section || '').trim(),
          usage: String(def.usage || '').trim(),
          resourceName: String(def.resourceName || '').trim(),
        };
      });
      return {
        level: level,
        features: rows,
      };
    });
  }

  function buildChooserSummary(entry, className) {
    var tags = classifySubclass(entry);
    var signatures = buildSignatureRows(entry);
    var unlocks = buildRoadmapRows(entry);
    var firstLevel = unlocks.length ? unlocks[0].level : '—';
    var endgame = unlocks.length ? unlocks[unlocks.length - 1].level : '—';
    var profile = subclassProfile(entry);
    return {
      tags: tags,
      signatures: signatures,
      firstLevel: firstLevel,
      endgame: endgame,
      className: className || 'Class',
      chooserSummary: profile && profile.chooserSummary ? profile.chooserSummary : '',
      fantasy: profile && profile.fantasy ? profile.fantasy : '',
    };
  }

  function renderSubclassSelect(subclassRows, currentSubclassId) {
    if (!subclassRows.length) {
      return '<input type="text" data-builder-path="class.subclassId" value="' + escHtml(currentSubclassId || '') + '" maxlength="80" placeholder="Subclass id (future content compatible)" />';
    }

    const options = [{ id: '', name: 'Choose subclass…' }].concat(subclassRows.map(function (row) {
      return { id: row.id, name: row.name };
    }));
    const hasCurrent = options.some(function hasOption(entry) {
      return normalizeId(entry.id) === normalizeId(currentSubclassId);
    });
    if (currentSubclassId && !hasCurrent) {
      options.push({ id: currentSubclassId, name: currentSubclassId + ' (Imported)' });
    }

    const html = options.map(function toOption(entry) {
      const selected = normalizeId(entry.id) === normalizeId(currentSubclassId) ? ' selected' : '';
      return '<option value="' + escHtml(entry.id) + '"' + selected + '>' + escHtml(entry.name) + '</option>';
    }).join('');
    return '<select data-builder-path="class.subclassId">' + html + '</select>';
  }

  function renderSubclassCards(subclassRows, currentSubclassId, className) {
    if (!subclassRows.length) {
      return '<div class="builder-help-text">No subclass entries are loaded for this class yet.</div>';
    }
    return '<div class="builder-subclass-grid">' + subclassRows.map(function (row) {
      var summary = buildChooserSummary(row, className);
      var selected = normalizeId(row.id) === normalizeId(currentSubclassId) ? ' selected' : '';
      var tags = summary.tags.map(function (tag) {
        return '<span class="builder-subclass-tag">' + escHtml(tag) + '</span>';
      }).join('');
      var signatures = summary.signatures.map(function (sig) {
        var typeBadge = sig.actionType ? '<span style="border:1px solid rgba(0,212,184,0.3);border-radius:999px;padding:1px 6px;font-size:0.52rem;color:#00d4b8;margin-left:6px;">' + escHtml(sig.actionType) + '</span>' : '';
        return '<div class="builder-subclass-signature"><span><strong style="color:#f3e7c4">' + escHtml(sig.title) + '.</strong>' + typeBadge + ' ' + escHtml(sig.text || 'Signature feature.') + '</span></div>';
      }).join('');
      return [
        '<button type="button" class="builder-subclass-card' + selected + '" data-builder-subclass-card="1" data-subclass-id="' + escHtml(row.id) + '">',
        '<div class="builder-subclass-check">✓</div>',
        '<h4>' + escHtml(row.name) + '</h4>',
        '<div class="builder-subclass-flavor">' + escHtml(summary.chooserSummary || row.flavorText || ('A ' + className + ' path with its own identity and unlocks.')) + '</div>',
        '<div class="builder-subclass-tags">' + tags + '</div>',
        '<div class="builder-subclass-signatures">' + signatures + '</div>',
        '</button>'
      ].join('');
    }).join('') + '</div>';
  }

  function renderSubclassDetail(entry, className) {
    if (!entry) {
      return '<div class="builder-subclass-detail empty">Choose a subclass card to inspect its playstyle, level-by-level unlocks, and signature features before you commit.</div>';
    }
    var summary = buildChooserSummary(entry, className);
    var roadmap = buildRoadmapRows(entry);
    var keyThemes = summary.tags.join(' · ');
    var firstMajor = summary.signatures[0] ? summary.signatures[0].title : 'Signature feature';
    var featuresCount = Array.isArray(entry.features) ? entry.features.length : 0;
    return [
      '<div class="builder-subclass-detail">',
      '<div class="builder-subclass-detail-head">',
      '<div class="builder-subclass-detail-kicker">Subclass choice preview</div>',
      '<div class="builder-subclass-detail-title">' + escHtml(entry.name) + '</div>',
      '<div class="builder-subclass-detail-flavor">' + escHtml(entry.flavorText || ('This ' + className + ' specialization adds its own feature lane and decision hooks.')) + '</div>',
      '<div class="builder-subclass-detail-grid">',
      '<div class="builder-subclass-detail-stat"><strong>How it feels</strong><span>' + escHtml(keyThemes || 'Specialist path with a unique gameplay loop.') + '</span></div>',
      '<div class="builder-subclass-detail-stat"><strong>First unlock</strong><span>Level ' + escHtml(summary.firstLevel) + ' · ' + escHtml(firstMajor) + '</span></div>',
      '<div class="builder-subclass-detail-stat"><strong>Depth surface</strong><span>' + escHtml(String(featuresCount)) + ' feature entries mapped through level ' + escHtml(summary.endgame) + '</span></div>',
      '</div>',
      '</div>',
      '<div class="builder-subclass-detail-body">',
      '<div class="builder-subclass-section">',
      '<div class="builder-subclass-section-head">Why pick this path</div>',
      '<div class="builder-subclass-section-body"><div class="builder-subclass-chooser-copy">' + escHtml(summary.fantasy || ('Choose ' + entry.name + ' if you want your ' + className.toLowerCase() + ' to lean into ' + (keyThemes || 'its signature theme') + '.')) + '</div></div>',
      '</div>',
      '<div class="builder-subclass-section">',
      '<div class="builder-subclass-section-head">Signature features</div>',
      '<div class="builder-subclass-section-body">' + summary.signatures.map(function (sig) {
        return '<div class="builder-subclass-feature-card"><strong>' + escHtml(sig.title) + '</strong><div>' + escHtml(sig.text || 'Signature feature.') + '</div></div>';
      }).join('') + '</div>',
      '</div>',
      '<div class="builder-subclass-section">',
      '<div class="builder-subclass-section-head">Level roadmap</div>',
      '<div class="builder-subclass-section-body"><div class="builder-subclass-roadmap">' + roadmap.map(function (row) {
        return '<div class="builder-subclass-roadmap-row"><div class="builder-subclass-roadmap-level">Lv ' + escHtml(row.level) + '</div><div class="builder-subclass-roadmap-content">' + row.features.map(function (feature) {
          var chips = [feature.type, feature.section, feature.resourceName].filter(Boolean).map(function (chip) {
            return '<span class="builder-subclass-tag" style="font-size:0.52rem;padding:1px 6px;">' + escHtml(chip) + '</span>';
          }).join('');
          return '<div class="builder-subclass-feature-card"><strong>' + escHtml(feature && feature.displayName || 'Feature') + '</strong>' + (chips ? '<div style="display:flex;flex-wrap:wrap;gap:4px;margin:4px 0 6px">' + chips + '</div>' : '') + '<div>' + escHtml(feature && feature.description || 'Feature text not available yet.') + '</div></div>';
        }).join('') + '</div></div>';
      }).join('') + '</div></div>',
      '</div>',
      '</div>',
      '</div>'
    ].join('');
  }

  function syncSubclassSelection(root, subclassId) {
    root.querySelectorAll('[data-builder-subclass-card="1"]').forEach(function (card) {
      var selected = normalizeId(card.dataset.subclassId) === normalizeId(subclassId);
      card.classList.toggle('selected', selected);
    });
    var selectEl = root.querySelector('[data-builder-path="class.subclassId"]');
    if (selectEl && normalizeId(selectEl.value) !== normalizeId(subclassId)) {
      selectEl.value = subclassId || '';
    }
  }

  function showSubclassDetail(root, classId, subclassId) {
    var subclassRows = getSubclassRows(classId);
    var entry = subclassRows.find(function (row) {
      return normalizeId(row.id) === normalizeId(subclassId);
    }) || null;
    var classRow = getClassRow(classId);
    var className = String(classRow && (classRow.displayName || classRow.id) || 'Class').trim();
    var panel = root.querySelector('[data-builder-subclass-detail="1"]');
    if (!panel) return;
    panel.innerHTML = renderSubclassDetail(entry, className);
  }

  registerStep({
    id: 'subclass',
    label: 'Subclass',
    render: function renderSubclassStep(context) {
      ensureCatalogLoaded();
      ensureSubclassStyles();
      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const classId = getCurrentClassId(draft);
      const subclassId = getSelectedSubclassId(draft);
      const unlockLevel = getSubclassUnlockLevel(classId);
      const currentLevel = getBuilderLevel(draft);
      const classRow = getClassRow(classId);
      const className = String(classRow && (classRow.displayName || classRow.id) || '').trim();
      const subclassRows = getSubclassRows(classId);

      if (!classId) {
        return '<div class="builder-help-text">Choose a class before selecting a subclass.</div>';
      }

      if (unlockLevel > 0 && currentLevel < unlockLevel) {
        return '<div class="builder-help-text">Subclass unlocks at level ' + escHtml(unlockLevel) + ' for this class. Current level: ' + escHtml(currentLevel) + '.</div>';
      }

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Choose Your Subclass</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Compare each ' + escHtml(className || 'class') + ' path, read what it actually does, and click the one that matches the player fantasy you want.</div>',
        '</div>',
        '<div class="builder-subclass-layout">',
        '<div class="builder-subclass-column">',
        '<div class="field builder-subclass-select-wrap"><label>Subclass</label>' + renderSubclassSelect(subclassRows, subclassId) + '</div>',
        '<div class="builder-help-text">Click any card below to read its flavor, signature features, and the level-by-level unlock roadmap before choosing.</div>',
        renderSubclassCards(subclassRows, subclassId, className),
        '</div>',
        '<div class="builder-subclass-column" data-builder-subclass-detail="1">' + renderSubclassDetail(subclassRows.find(function (row) { return normalizeId(row.id) === normalizeId(subclassId); }) || null, className) + '</div>',
        '</div>',
        '<div class="builder-help-text">Stored as <code>classes[0].subclassId</code> in canonical data. The detail panel is intentionally verbose so players can read what each subclass does before they lock it in.</div>'
      ].join('');
    },
    bind: function bindSubclassStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      const draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
      const classId = getCurrentClassId(draft);
      const applySelection = function (subclassId) {
        syncSubclassSelection(root, subclassId);
        showSubclassDetail(root, classId, subclassId);
        context.onSetField(['class', 'subclassId'], subclassId || '');
      };
      root.querySelectorAll('[data-builder-subclass-card="1"]').forEach(function (card) {
        card.addEventListener('click', function () {
          applySelection(String(card.dataset.subclassId || '').trim());
        });
      });
      var selectEl = root.querySelector('[data-builder-path="class.subclassId"]');
      if (selectEl) {
        selectEl.addEventListener('change', function () {
          applySelection(String(selectEl.value || '').trim());
        });
      }
      var current = getSelectedSubclassId(draft);
      syncSubclassSelection(root, current);
      showSubclassDetail(root, classId, current);
    },
  });
})(window);
