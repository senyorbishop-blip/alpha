(function initCharacterBuilderStepReview(global) {
  var ABILITY_ORDER = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  var ABILITY_LABELS = {
    str: 'STR',
    dex: 'DEX',
    con: 'CON',
    int: 'INT',
    wis: 'WIS',
    cha: 'CHA',
  };
  var ABILITY_FULL_NAMES = ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma'];
  var SPELL_SLOT_ORDINALS = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th'];

  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function registerStep(step) {
    if (!global.CharacterBuilderStepModules || typeof global.CharacterBuilderStepModules !== 'object') {
      global.CharacterBuilderStepModules = {};
    }
    global.CharacterBuilderStepModules[step.id] = step;
  }

  function ensureBuilderStyles() {
    if (document.getElementById('character-builder-css')) return;
    var link = document.createElement('link');
    link.id = 'character-builder-css';
    link.rel = 'stylesheet';
    link.href = '/static/css/character-builder.css';
    document.head.appendChild(link);
  }

  function buildValidationList(draft) {
    var validators = global.CharacterBuilderValidators || null;
    if (!validators || typeof validators.validateDraft !== 'function') return [];
    var result = validators.validateDraft(draft);
    if (result.ok) return [];
    return Array.isArray(result.issues) ? result.issues : [];
  }

  function normalizeRowName(row, fallback) {
    if (!row || typeof row !== 'object') return fallback;
    return row.displayName || row.name || row.id || fallback;
  }

  function getCatalogClassRow(classId) {
    var catalog = global.CharacterBuilderAPI && typeof global.CharacterBuilderAPI.getCachedCatalog === 'function'
      ? global.CharacterBuilderAPI.getCachedCatalog()
      : {};
    var rows = catalog && Array.isArray(catalog.classes) ? catalog.classes : [];
    return rows.find(function findClass(row) {
      return String(row && row.id || '').trim().toLowerCase() === String(classId || '').trim().toLowerCase();
    }) || {};
  }

  function toAbilityMod(score) {
    var parsed = parseInt(score, 10);
    var safeScore = Number.isFinite(parsed) ? parsed : 10;
    return Math.floor((safeScore - 10) / 2);
  }

  function formatSigned(value) {
    var n = Number.isFinite(value) ? value : 0;
    return (n >= 0 ? '+' : '') + n;
  }

  function getLevelOneFeatures(classRow) {
    var fromTable = Array.isArray(classRow.progressionTable)
      ? classRow.progressionTable.find(function rowForLevel(row) {
        return row && parseInt(row.level, 10) === 1;
      })
      : null;
    var fromTableFeatures = fromTable && Array.isArray(fromTable.features) ? fromTable.features : [];
    if (fromTableFeatures.length) return fromTableFeatures;
    return Array.isArray(classRow.level1Features) ? classRow.level1Features : [];
  }

  function buildInitials(name) {
    var words = String(name || '').trim().split(/\s+/).filter(Boolean);
    if (!words.length) return '??';
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  function resolveComboPortrait(draft) {
    var portraitLib = global.CasualDnDPortraitLibrary;
    if (!portraitLib || typeof portraitLib.resolve !== 'function') return '';
    var species = draft && draft.species && typeof draft.species === 'object' ? draft.species : {};
    var classData = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    var identity = draft && draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
    return String(portraitLib.resolve({
      speciesId: species.id || species.name || '',
      classId: classData.id || '',
      gender: identity.gender || 'neutral',
      neutralFallback: '',
    }) || '').trim();
  }

  function getSpeciesRow(speciesId) {
    var api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') return null;
    var catalog = api.getCachedCatalog();
    var species = Array.isArray(catalog && catalog.species) ? catalog.species : [];
    return species.find(function(s) { return String(s && s.id || '').trim().toLowerCase() === speciesId; }) || null;
  }

  function computeStatBlock(draft) {
    var abilities = (draft.abilities && typeof draft.abilities === 'object') ? draft.abilities : {};
    var classData = (draft.class && typeof draft.class === 'object') ? draft.class : {};
    var progression = (draft.progression && typeof draft.progression === 'object') ? draft.progression : {};
    var speciesData = (draft.species && typeof draft.species === 'object') ? draft.species : {};

    var classId = String(classData.id || '').trim().toLowerCase();
    var speciesId = String(speciesData.id || '').trim().toLowerCase();
    var level = parseInt(progression.level, 10) || 1;
    var profBonus = 2 + Math.floor((Math.max(1, level) - 1) / 4);

    var classRow = getCatalogClassRow(classId);
    var speciesRow = getSpeciesRow(speciesId);

    var hitDie = parseInt(classRow.hitDie, 10) || 8;
    var conMod = toAbilityMod(abilities.con);
    var dexMod = toAbilityMod(abilities.dex);
    var wisMod = toAbilityMod(abilities.wis);

    var ac = 10 + dexMod;
    if (classId === 'barbarian') ac = 10 + dexMod + toAbilityMod(abilities.con);
    if (classId === 'monk') ac = 10 + dexMod + wisMod;

    var maxHP = hitDie + conMod + (Math.max(0, level - 1) * (Math.floor(hitDie / 2) + 1 + conMod));
    var speed = speciesRow && speciesRow.movement ? parseInt(speciesRow.movement.walk, 10) || 30 : (parseInt(speciesData.speed, 10) || 30);
    var importedStats = draft.compatibility && typeof draft.compatibility === 'object' && draft.compatibility.importedStats && typeof draft.compatibility.importedStats === 'object'
      ? draft.compatibility.importedStats
      : {};
    var importedHp = importedStats.hp && typeof importedStats.hp === 'object' ? importedStats.hp : {};
    if (parseInt(importedHp.max, 10) > 0) maxHP = parseInt(importedHp.max, 10);
    if (parseInt(importedStats.ac, 10) > 0) ac = parseInt(importedStats.ac, 10);
    if (parseInt(importedStats.speed, 10) > 0) speed = parseInt(importedStats.speed, 10);
    var darkvision = speciesRow && speciesRow.senses ? parseInt(speciesRow.senses.darkvision, 10) || 0 : 0;

    var savingThrows = Array.isArray(classRow.savingThrows) ? classRow.savingThrows : [];
    var saves = {};
    ABILITY_ORDER.forEach(function(k) {
      var mod = toAbilityMod(abilities[k]);
      saves[k] = savingThrows.includes(k) ? mod + profBonus : mod;
    });

    var spellcastingAbility = classRow.spellcastingAbility || null;
    var spellMod = spellcastingAbility ? toAbilityMod(abilities[spellcastingAbility]) : 0;
    var spellSaveDC = spellcastingAbility ? (8 + profBonus + spellMod) : null;
    var spellAttackBonus = spellcastingAbility ? (profBonus + spellMod) : null;

    var spellSlots = {};
    if (classRow.spellSlots && classRow.spellSlots[String(level)]) {
      spellSlots = classRow.spellSlots[String(level)];
    }

    var passivePerception = 10 + wisMod + profBonus;
    var initiative = dexMod;

    return {
      level: level, profBonus: profBonus, ac: ac, maxHP: maxHP, speed: speed,
      initiative: initiative, passivePerception: passivePerception,
      saves: saves, savingThrows: savingThrows,
      spellcastingAbility: spellcastingAbility, spellSaveDC: spellSaveDC,
      spellAttackBonus: spellAttackBonus, spellSlots: spellSlots,
      darkvision: darkvision, hitDie: hitDie,
      classId: classId, speciesId: speciesId,
      classRow: classRow, speciesRow: speciesRow,
      abilityMod: toAbilityMod,
    };
  }

  registerStep({
    id: 'review',
    label: 'Review',
    render: function renderReviewStep(context) {
      ensureBuilderStyles();
      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var identity = draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
      var species = draft.species && typeof draft.species === 'object' ? draft.species : {};
      var origins = draft.origins && typeof draft.origins === 'object' ? draft.origins : {};
      var classData = draft.class && typeof draft.class === 'object' ? draft.class : {};
      var abilities = draft.abilities && typeof draft.abilities === 'object' ? draft.abilities : {};
      var issues = buildValidationList(draft);
      var sb = computeStatBlock(draft);

      var classRow = sb.classRow || {};
      var speciesRow = sb.speciesRow;
      var className = normalizeRowName(classRow, classData.id || 'Class');
      var speciesName = normalizeRowName(species, species.id || 'Species');
      var speciesSize = (speciesRow && speciesRow.size) || 'Medium';
      var levelOneFeatures = getLevelOneFeatures(classRow);
      var characterName = identity.name || 'Unnamed Adventurer';
      var portrait = identity.portraitUrl || identity.tokenImageUrl || resolveComboPortrait(draft) || '';
      var bgName = origins.backgroundName || origins.backgroundId || 'No background';

      // --- Banner ---
      var bannerHtml = [
        '<div class="sb-banner">',
        '<div class="sb-portrait">',
        portrait ? '<img src="' + escHtml(portrait) + '" alt="Portrait" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />' : escHtml(buildInitials(characterName)),
        '</div>',
        '<div class="sb-identity">',
        '<div class="sb-char-name">' + escHtml(characterName) + '</div>',
        '<div class="sb-char-sub">' + escHtml(speciesName) + ' ' + escHtml(className) + ' \u00b7 Level ' + sb.level + '</div>',
        '<div class="sb-xp-bar"><div class="sb-xp-fill" style="width:' + Math.round(((Math.max(1, sb.level) - 1) / 19) * 100) + '%"></div></div>',
        '</div>',
        '</div>',
      ].join('');

      // --- Spell bar (only for casters) ---
      var spellBarHtml = '';
      if (sb.spellSaveDC !== null) {
        spellBarHtml = [
          '<div class="sb-spell-bar">',
          '<div class="sbs-item"><div class="sbs-val">' + sb.spellSaveDC + '</div><div class="sbs-lbl">Spell Save DC</div></div>',
          '<div class="sbs-item"><div class="sbs-val">' + formatSigned(sb.spellAttackBonus) + '</div><div class="sbs-lbl">Spell Attack</div></div>',
          '<div class="sbs-item"><div class="sbs-val">' + escHtml(String(sb.spellcastingAbility || '').toUpperCase()) + '</div><div class="sbs-lbl">Casting Ability</div></div>',
          '</div>',
        ].join('');
      }

      // --- Combat bar ---
      var combatStats = [
        { label: 'AC', value: sb.ac, sub: '' },
        { label: 'HP', value: sb.maxHP, sub: 'Max' },
        { label: 'Initiative', value: formatSigned(sb.initiative), sub: '', rawVal: sb.initiative },
        { label: 'Speed', value: sb.speed + ' ft', sub: '', rawVal: sb.speed },
        { label: 'Passive\u00a0Perc.', value: sb.passivePerception, sub: '' },
        { label: 'Prof.', value: formatSigned(sb.profBonus), sub: 'Bonus', rawVal: sb.profBonus },
      ];
      var combatBarHtml = '<div class="sb-combat-bar">';
      combatStats.forEach(function(stat) {
        var numVal = typeof stat.rawVal === 'number' ? stat.rawVal : (typeof stat.value === 'number' ? stat.value : 0);
        var goodClass = numVal >= 15 ? ' good' : '';
        combatBarHtml += '<div class="sb-stat">';
        combatBarHtml += '<div class="sb-stat-val' + goodClass + '">' + stat.value + '</div>';
        combatBarHtml += '<div class="sb-stat-lbl">' + stat.label + '</div>';
        if (stat.sub) combatBarHtml += '<div class="sb-stat-sub">' + stat.sub + '</div>';
        combatBarHtml += '</div>';
      });
      combatBarHtml += '</div>';

      // --- Body column 1: Ability Scores ---
      var abilityHtml = '';
      ABILITY_ORDER.forEach(function(key) {
        var raw = parseInt(abilities[key], 10);
        var safeRaw = Number.isFinite(raw) ? raw : 10;
        var mod = toAbilityMod(safeRaw);
        var modClass = mod >= 0 ? 'pos' : 'neg';
        abilityHtml += '<div class="ability-row-sb">';
        abilityHtml += '<span class="ars-name">' + ABILITY_LABELS[key] + '</span>';
        abilityHtml += '<span class="ars-score">' + safeRaw + '</span>';
        abilityHtml += '<span class="ars-mod ' + modClass + '">' + formatSigned(mod) + '</span>';
        abilityHtml += '</div>';
      });

      // --- Body column 2: Saving Throws ---
      var savesHtml = '';
      ABILITY_ORDER.forEach(function(key, idx) {
        var proficient = sb.savingThrows.includes(key);
        var dotClass = proficient ? 'proficient' : 'normal';
        var valClass = proficient ? ' prof' : '';
        savesHtml += '<div class="save-row">';
        savesHtml += '<div class="save-dot ' + dotClass + '"></div>';
        savesHtml += '<span class="save-name">' + ABILITY_FULL_NAMES[idx] + '</span>';
        savesHtml += '<span class="save-val' + valClass + '">' + formatSigned(sb.saves[key]) + '</span>';
        savesHtml += '</div>';
      });
      if (sb.darkvision > 0) {
        savesHtml += '<div style="margin-top:10px;font-size:0.62rem;color:#b07fd4;background:rgba(108,52,131,0.1);border:1px solid rgba(108,52,131,0.2);border-radius:4px;padding:5px 8px">\uD83D\uDC41 Darkvision ' + sb.darkvision + ' ft</div>';
      }

      // --- Body column 3: Level 1 Features ---
      var featureHtml = '';
      if (levelOneFeatures.length) {
        levelOneFeatures.forEach(function(feature) {
          featureHtml += '<div class="fl-feature">';
          featureHtml += '<div class="fl-dot"></div>';
          featureHtml += '<div class="fl-name"><strong>' + escHtml(feature) + '</strong></div>';
          featureHtml += '</div>';
        });
      } else {
        featureHtml = '<div style="font-size:0.64rem;color:var(--text-dim);font-style:italic">Select a class to see starting features.</div>';
      }

      var bodyHtml = [
        '<div class="sb-body">',
        '<div class="sb-section">',
        '<div class="sb-section-title">Ability Scores</div>',
        abilityHtml,
        '</div>',
        '<div class="sb-section">',
        '<div class="sb-section-title">Saving Throws</div>',
        savesHtml,
        '</div>',
        '<div class="sb-section">',
        '<div class="sb-section-title">Level 1 Features</div>',
        '<div class="feature-list-sb">',
        featureHtml,
        '</div>',
        '</div>',
        '</div>',
      ].join('');

      // --- Spell slots (only if any slots exist) ---
      var spellSlotHtml = '';
      var slotKeys = Object.keys(sb.spellSlots || {});
      var hasSlots = slotKeys.some(function(k) { return parseInt(sb.spellSlots[k], 10) > 0; });
      if (hasSlots) {
        spellSlotHtml = '<div class="spell-slot-bar">';
        slotKeys.forEach(function(k) {
          var count = parseInt(sb.spellSlots[k], 10) || 0;
          if (count <= 0) return;
          var lvlIdx = parseInt(k, 10) - 1;
          var ordinal = (lvlIdx >= 0 && lvlIdx < SPELL_SLOT_ORDINALS.length) ? SPELL_SLOT_ORDINALS[lvlIdx] : k;
          spellSlotHtml += '<div class="ss-level-group">';
          spellSlotHtml += '<div class="ss-level-lbl">' + ordinal + '</div>';
          spellSlotHtml += '<div class="ss-slots">';
          for (var i = 0; i < count; i++) {
            spellSlotHtml += '<div class="ss-slot"></div>';
          }
          spellSlotHtml += '</div>';
          spellSlotHtml += '</div>';
        });
        spellSlotHtml += '</div>';
      }

      // --- Validation panel ---
      var validationHtml = '';
      if (!issues.length) {
        validationHtml = [
          '<div class="sb-validation">',
          '<div class="val-icon ready">\u2713</div>',
          '<div class="val-text">',
          '<strong>Ready to Forge</strong>',
          escHtml(speciesName) + ' ' + escHtml(className) + ' is ready for adventure.',
          '</div>',
          '</div>',
        ].join('');
      } else {
        validationHtml = [
          '<div class="sb-validation">',
          '<div class="val-icon" style="background:rgba(192,57,43,0.15);border-color:rgba(192,57,43,0.4);color:#fc8181">\u2717</div>',
          '<div class="val-text">',
          '<strong style="color:#fc8181">Needs Attention</strong>',
          '<ul style="margin:4px 0 0 16px;padding:0;font-size:0.66rem;color:#ffcbcb">',
          issues.map(function(issue) { return '<li>' + escHtml(issue) + '</li>'; }).join(''),
          '</ul>',
          '</div>',
          '</div>',
        ].join('');
      }

      return [
        '<div class="statblock">',
        bannerHtml,
        spellBarHtml,
        combatBarHtml,
        bodyHtml,
        spellSlotHtml,
        validationHtml,
        '</div>',
        '<div class="builder-help-text">Everything looks right? Hit <strong>Enter the World</strong> to save your character and begin your adventure.</div>',
      ].join('');
    },
  });
})(window);
