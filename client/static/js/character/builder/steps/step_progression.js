(function initCharacterBuilderStepProgression(global) {
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

  function getClassId(draft) {
    const classData = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    return String(classData.id || '').trim().toLowerCase();
  }

  function getClassName(draft) {
    const api = global.CharacterBuilderAPI;
    const classId = getClassId(draft);
    if (!api || !classId) return '';
    const catalog = api.getCachedCatalog && api.getCachedCatalog();
    const rows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const row = rows.find(function(r) { return String(r && r.id || '').trim().toLowerCase() === classId; });
    return row ? String(row.displayName || row.id || '') : '';
  }

  function getProgressionSummary(draft) {
    const api = global.CharacterBuilderAPI;
    const classId = getClassId(draft);
    if (!api || !classId) return [];
    const catalog = api.getCachedCatalog && api.getCachedCatalog();
    const rows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const row = rows.find(function(r) { return String(r && r.id || '').trim().toLowerCase() === classId; });
    return Array.isArray(row && row.progressionSummary) ? row.progressionSummary.slice(0, 20) : [];
  }

  function getProgressionTable(draft) {
    const api = global.CharacterBuilderAPI;
    const classId = getClassId(draft);
    if (!api || !classId) return [];
    const catalog = api.getCachedCatalog && api.getCachedCatalog();
    const rows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const row = rows.find(function(r) { return String(r && r.id || '').trim().toLowerCase() === classId; });
    return Array.isArray(row && row.progressionTable) ? row.progressionTable.slice(0, 20) : [];
  }

  function getFeaturesAtLevel(progressionSummary, level) {
    const entry = progressionSummary.find(function(item) {
      return parseInt(item && item.level, 10) === level;
    });
    return entry && String(entry.summary || '').trim() || '';
  }

  function isFeatLevel(progressSummary, level) {
    const text = String(getFeaturesAtLevel(progressSummary, level) || '').toLowerCase();
    return /ability score improvement|epic boon|\bfeat\b/.test(text);
  }

  function getFeatRows() {
    const api = global.CharacterBuilderAPI;
    const catalog = api && typeof api.getCachedCatalog === 'function' ? api.getCachedCatalog() : {};
    const rows = Array.isArray(catalog && catalog.feats) ? catalog.feats : [];
    return rows.filter(function (row) {
      return row && typeof row === 'object' && String(row.id || '').trim();
    });
  }

  function getTalentRowsForClass(classId) {
    const api = global.CharacterBuilderAPI;
    const catalog = api && typeof api.getCachedCatalog === 'function' ? api.getCachedCatalog() : {};
    const rows = Array.isArray(catalog && catalog.talents) ? catalog.talents : [];
    return rows.filter(function (row) {
      if (!row || typeof row !== 'object') return false;
      const id = String(row.id || '').trim();
      if (!id) return false;
      const restrictions = Array.isArray(row.classRestrictions) ? row.classRestrictions : [];
      if (restrictions.length) {
        return restrictions.some(function(v) { return String(v || '').trim().toLowerCase() === classId; });
      }
      const cls = String(row.classId || row.class || '').trim().toLowerCase();
      return !cls || cls === classId;
    });
  }

  function getLevelRow(progressionTable, level) {
    return progressionTable.find(function(item) {
      return parseInt(item && item.level, 10) === level;
    }) || null;
  }

  function hasFeatOrAsiChoice(levelRow, progressionSummary, level) {
    if (levelRow && levelRow.asiOrFeat === true) return true;
    return isFeatLevel(progressionSummary, level);
  }

  function getSubclassUnlockLevel(draft) {
    const api = global.CharacterBuilderAPI;
    const classId = getClassId(draft);
    if (!api || !classId) return 0;
    const catalog = api.getCachedCatalog && api.getCachedCatalog();
    const rows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const row = rows.find(function(r) { return String(r && r.id || '').trim().toLowerCase() === classId; });
    const level = parseInt(row && row.subclassLevel, 10);
    return Number.isFinite(level) && level > 0 ? level : 0;
  }

  function getAbilityChoiceState(progression, defaultMode) {
    const state = progression && progression.choiceState && typeof progression.choiceState === 'object'
      ? progression.choiceState
      : {};
    const fromStructured = Array.isArray(state.asiAbilities)
      ? state.asiAbilities.map(function (v) { return String(v || '').trim().toLowerCase(); }).filter(Boolean)
      : [];
    if (fromStructured.length) return fromStructured;
    if (defaultMode !== 'ability') return [];
    const legacy = progression && progression.asiChoice && typeof progression.asiChoice === 'object'
      ? progression.asiChoice
      : {};
    const legacyAbilities = Array.isArray(legacy.abilities)
      ? legacy.abilities.map(function (v) { return String(v || '').trim().toLowerCase(); }).filter(Boolean)
      : [];
    if (legacyAbilities.length) return legacyAbilities;
    const single = String(legacy.ability || '').trim().toLowerCase();
    return single ? [single] : [];
  }

  function uniqueStrings(values) {
    var seen = Object.create(null);
    var out = [];
    (Array.isArray(values) ? values : []).forEach(function (value) {
      var token = String(value || '').trim();
      if (!token || seen[token]) return;
      seen[token] = true;
      out.push(token);
    });
    return out;
  }

  function normalizeAsiMode(value) {
    var mode = String(value || 'ability').trim().toLowerCase();
    return mode === 'feat' ? 'feat' : 'ability';
  }

  function normalizeAbilityList(values) {
    return uniqueStrings((Array.isArray(values) ? values : []).map(function (value) {
      return String(value || '').trim().toLowerCase();
    }).filter(function (value) {
      return ['str', 'dex', 'con', 'int', 'wis', 'cha'].indexOf(value) >= 0;
    })).slice(0, 2);
  }

  function getAsiChoicesByLevel(progression) {
    var row = progression && typeof progression === 'object' ? progression : {};
    var choiceState = row.choiceState && typeof row.choiceState === 'object' ? row.choiceState : {};
    var raw = row.asiChoicesByLevel && typeof row.asiChoicesByLevel === 'object'
      ? row.asiChoicesByLevel
      : (choiceState.asiChoicesByLevel && typeof choiceState.asiChoicesByLevel === 'object' ? choiceState.asiChoicesByLevel : {});
    var out = {};
    Object.keys(raw || {}).forEach(function (levelKey) {
      var level = parseInt(levelKey, 10);
      if (!Number.isFinite(level) || level < 1 || level > 20) return;
      var choice = raw[levelKey] && typeof raw[levelKey] === 'object' ? raw[levelKey] : {};
      var mode = normalizeAsiMode(choice.mode);
      var featId = String(choice.featId || '').trim();
      var abilities = normalizeAbilityList(choice.abilities || (choice.ability ? [choice.ability] : []));
      out[String(level)] = {
        level: level,
        mode: mode,
        featId: featId,
        abilities: abilities,
      };
    });
    return out;
  }

  function getLegacyAsiChoice(progression) {
    var row = progression && typeof progression === 'object' ? progression : {};
    var asiChoice = row.asiChoice && typeof row.asiChoice === 'object' ? row.asiChoice : {};
    var asiMode = normalizeAsiMode(asiChoice.mode || (row.choiceState && row.choiceState.asiMode));
    var asiAbilities = getAbilityChoiceState(row, asiMode);
    var featChoice = String(
      asiChoice.featId
      || (row.choiceState && row.choiceState.featId)
      || (Array.isArray(row.feats) ? row.feats[0] : '')
      || ''
    ).trim();
    return {
      mode: asiMode,
      featId: featChoice,
      abilities: normalizeAbilityList(asiAbilities),
    };
  }

  function isAsiChoiceResolved(choice) {
    var row = choice && typeof choice === 'object' ? choice : {};
    var mode = normalizeAsiMode(row.mode);
    if (mode === 'feat') return !!String(row.featId || '').trim();
    return normalizeAbilityList(row.abilities || (row.ability ? [row.ability] : [])).length > 0;
  }

  function resolvedAsiChoiceCount(progression) {
    var row = progression && typeof progression === 'object' ? progression : {};
    var byLevel = getAsiChoicesByLevel(row);
    var explicitLevels = Object.keys(byLevel).filter(function (levelKey) {
      return isAsiChoiceResolved(byLevel[levelKey]);
    }).length;
    var legacy = getLegacyAsiChoice(row);
    var explicitAsi = isAsiChoiceResolved(legacy) ? 1 : 0;
    var storedFeats = uniqueStrings(Array.isArray(row.feats) ? row.feats : []);
    return Math.max(storedFeats.length, explicitLevels, explicitAsi);
  }

  function getChoiceForAsiLevel(progression, asiLevels, level) {
    var byLevel = getAsiChoicesByLevel(progression);
    var key = String(level);
    if (byLevel[key]) return byLevel[key];
    var legacy = getLegacyAsiChoice(progression);
    if (asiLevels && asiLevels.length && level === asiLevels[0] && isAsiChoiceResolved(legacy)) {
      return Object.assign({ level: level }, legacy);
    }
    return { level: level, mode: 'ability', featId: '', abilities: [] };
  }

  function computeCumulativeRequirements(draft) {
    var progression = draft && draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
    var level = parseInt(progression.level, 10);
    var safeLevel = Number.isFinite(level) && level >= 1 ? Math.min(level, 20) : 1;
    var progressionSummary = getProgressionSummary(draft);
    var progressionTable = getProgressionTable(draft);
    var subclassUnlockLevel = getSubclassUnlockLevel(draft);
    var subclassSelection = String(draft && draft.class && draft.class.subclassId || '').trim();

    var asiLevels = [];
    for (var lvl = 1; lvl <= safeLevel; lvl += 1) {
      var levelRow = getLevelRow(progressionTable, lvl);
      if (hasFeatOrAsiChoice(levelRow, progressionSummary, lvl)) {
        asiLevels.push(lvl);
      }
    }

    var byLevelChoices = getAsiChoicesByLevel(progression);
    var hasPerLevelChoices = Object.keys(byLevelChoices).length > 0;
    var resolvedCount = resolvedAsiChoiceCount(progression);
    var unresolvedAsiLevels = hasPerLevelChoices
      ? asiLevels.filter(function (lvl) {
        return !isAsiChoiceResolved(byLevelChoices[String(lvl)]);
      })
      : asiLevels.slice(resolvedCount);
    var required = [];
    if (subclassUnlockLevel > 0 && safeLevel >= subclassUnlockLevel && !subclassSelection) {
      required.push({
        type: 'subclass',
        level: subclassUnlockLevel,
        title: 'Subclass choice required',
        detail: 'Subclass unlocks at level ' + subclassUnlockLevel + ' and is still unresolved.',
      });
    }
    unresolvedAsiLevels.forEach(function (lvl) {
      required.push({
        type: 'asi',
        level: lvl,
        title: 'ASI / Feat required',
        detail: 'Resolve your level ' + lvl + ' Ability Score Improvement or Feat choice.',
      });
    });

    return {
      safeLevel: safeLevel,
      progressionSummary: progressionSummary,
      progressionTable: progressionTable,
      subclassUnlockLevel: subclassUnlockLevel,
      subclassSelection: subclassSelection,
      asiLevels: asiLevels,
      unresolvedAsiLevels: unresolvedAsiLevels,
      required: required,
    };
  }

  global.CharacterBuilderProgressionRequirements = {
    compute: computeCumulativeRequirements,
  };

  function renderLevelPicker(safeLevel) {
    var buttons = '';
    for (var lvl = 1; lvl <= 20; lvl++) {
      var isActive = lvl === safeLevel;
      var isMilestone = lvl === 5 || lvl === 10 || lvl === 15 || lvl === 20;
      var cls = 'cb-level-btn'
        + (isActive ? ' active' : '')
        + (isMilestone && !isActive ? ' milestone' : '');
      buttons += '<button type="button" class="' + cls + '" data-level-pick="' + lvl + '">' + lvl + '</button>';
    }
    return '<div class="cb-level-picker">' + buttons + '</div>';
  }


  function sortLevelKeys(keys) {
    return (Array.isArray(keys) ? keys : []).slice().sort(function (a, b) {
      return parseInt(a, 10) - parseInt(b, 10);
    });
  }

  function collectFeatIdsFromChoices(byLevel) {
    var out = [];
    sortLevelKeys(Object.keys(byLevel || {})).forEach(function (levelKey) {
      var choice = byLevel[levelKey] && typeof byLevel[levelKey] === 'object' ? byLevel[levelKey] : {};
      var featId = String(choice.featId || '').trim();
      if (normalizeAsiMode(choice.mode) === 'feat' && featId && out.indexOf(featId) < 0) {
        out.push(featId);
      }
    });
    return out;
  }

  function writeAsiChoice(context, level, patch) {
    if (!context || typeof context.onSetField !== 'function') return;
    var draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
    var progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
    var requirements = computeCumulativeRequirements(draft);
    var levelKey = String(parseInt(level, 10));
    if (!levelKey || levelKey === 'NaN') return;

    var existing = getChoiceForAsiLevel(progression, requirements.asiLevels, parseInt(levelKey, 10));
    var next = Object.assign({}, existing, patch || {});
    next.level = parseInt(levelKey, 10);
    next.mode = normalizeAsiMode(next.mode);
    next.featId = next.mode === 'feat' ? String(next.featId || '').trim() : '';
    next.abilities = next.mode === 'ability'
      ? normalizeAbilityList(next.abilities || (next.ability ? [next.ability] : []))
      : [];
    next.ability = next.abilities.length === 1 ? next.abilities[0] : '';

    var byLevel = getAsiChoicesByLevel(progression);
    byLevel[levelKey] = next;
    var feats = collectFeatIdsFromChoices(byLevel);
    var currentChoiceState = progression.choiceState && typeof progression.choiceState === 'object' ? progression.choiceState : {};
    var compatibilityChoice = next.mode === 'feat'
      ? { mode: 'feat', featId: next.featId, ability: '', abilities: [] }
      : { mode: 'ability', featId: '', ability: next.ability, abilities: next.abilities.slice() };

    context.onSetField(['progression', 'asiChoicesByLevel'], byLevel);
    context.onSetField(['progression', 'choiceState'], Object.assign({}, currentChoiceState, {
      asiChoicesByLevel: byLevel,
      asiMode: next.mode,
      featId: next.featId,
      asiAbilities: next.abilities.slice(),
    }));
    context.onSetField(['progression', 'feats'], feats);
    context.onSetField(['progression', 'asiChoice'], compatibilityChoice);
  }

  var _advancedOpen = false;

  registerStep({
    id: 'progression',
    label: 'Progression',
    render: function renderProgressionStep(context) {
      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
      const level = parseInt(progression.level, 10);
      const safeLevel = Number.isFinite(level) && level >= 1 ? Math.min(level, 20) : 1;

      const classId = getClassId(draft);
      const className = getClassName(draft);
      const requirements = computeCumulativeRequirements(draft);
      const progressionSummary = requirements.progressionSummary;
      const progressionTable = requirements.progressionTable;
      const featureText = getFeaturesAtLevel(progressionSummary, safeLevel);
      const featRows = getFeatRows();
      const talentRows = getTalentRowsForClass(classId).filter(function (row) {
        var minLevel = parseInt(row && row.minimumLevel, 10);
        if (!Number.isFinite(minLevel) || minLevel < 1) minLevel = 1;
        return safeLevel >= minLevel;
      });

      const choiceState = progression.choiceState && typeof progression.choiceState === 'object' ? progression.choiceState : {};
      const selectedTalents = Array.isArray(choiceState.talentIds)
        ? choiceState.talentIds.map(function (v) { return String(v || '').trim(); }).filter(Boolean)
        : (Array.isArray(progression.talents) ? progression.talents.map(function (v) { return String(v || '').trim(); }).filter(Boolean) : []);
      const subclassUnlockLevel = requirements.subclassUnlockLevel;
      const subclassRequiredNow = requirements.required.some(function (item) { return item.type === 'subclass'; });
      const subclassSelection = requirements.subclassSelection;

      var milestoneHtml = '';
      if (featureText) {
        milestoneHtml = [
          '<div class="cb-level-unlock">',
          '<span class="cb-level-unlock-label">Level ' + safeLevel + ' Unlocks</span>',
          '<span class="cb-level-unlock-text">' + escHtml(featureText) + '</span>',
          '</div>',
        ].join('');
      } else if (classId) {
        milestoneHtml = '<div class="cb-level-unlock cb-level-unlock--empty">Level ' + safeLevel + ' — choose your starting level.</div>';
      } else {
        milestoneHtml = '<div class="cb-level-unlock cb-level-unlock--empty">Select a class first to preview level features.</div>';
      }

      var hiddenLevelInput = '<input type="hidden" data-builder-path="progression.level" value="' + safeLevel + '" id="cb-progression-level-hidden" />';
      var classLine = className
        ? '<div class="cb-prog-class-line">' + escHtml(className) + ' · Starting level ' + safeLevel + '</div>'
        : '';

      var autoUnlockRows = [];
      for (var unlockLevel = 1; unlockLevel <= safeLevel; unlockLevel += 1) {
        var rowText = getFeaturesAtLevel(progressionSummary, unlockLevel);
        if (!rowText) continue;
        autoUnlockRows.push('<div class="cb-level-unlock" style="margin-top:6px;"><span class="cb-level-unlock-label">Level ' + unlockLevel + '</span><span class="cb-level-unlock-text">' + escHtml(rowText) + '</span></div>');
      }
      var autoUnlockHtml = autoUnlockRows.length
        ? '<div style="margin-top:10px;"><div class="builder-help-text" style="margin:0 0 4px 0;">Automatic unlock summary (levels 1-' + safeLevel + ')</div>' + autoUnlockRows.join('') + '</div>'
        : '';

      var requiredChoicesHtml = requirements.required.length
        ? '<div style="margin-top:10px;"><div class="cb-level-unlock"><span class="cb-level-unlock-label">Required unresolved picks</span><span class="cb-level-unlock-text">' + requirements.required.map(function (item) { return 'Lv ' + item.level + ': ' + item.title; }).join(' · ') + '</span></div></div>'
        : '<div class="builder-help-text" style="margin-top:10px;">All mandatory progression choices through level ' + safeLevel + ' are resolved.</div>';

      var abilityNames = { str: 'Strength', dex: 'Dexterity', con: 'Constitution', int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma' };
      var abilityLabels = { str: 'STR', dex: 'DEX', con: 'CON', int: 'INT', wis: 'WIS', cha: 'CHA' };
      function renderFeatOptions(selectedFeatId) {
        var selectedKey = String(selectedFeatId || '').trim();
        return featRows.map(function (row) {
          var id = String(row.id || '').trim();
          var selected = id && id === selectedKey ? ' selected' : '';
          return '<option value="' + escHtml(id) + '"' + selected + '>' + escHtml(String(row.displayName || row.name || id)) + '</option>';
        }).join('');
      }

      var asiChoiceRowsHtml = requirements.asiLevels.length
        ? requirements.asiLevels.map(function (asiLevel) {
          var choice = getChoiceForAsiLevel(progression, requirements.asiLevels, asiLevel);
          var mode = normalizeAsiMode(choice.mode);
          var featChoice = String(choice.featId || '').trim();
          var asiAbilities = normalizeAbilityList(choice.abilities || (choice.ability ? [choice.ability] : []));
          var resolved = isAsiChoiceResolved(choice);
          var statusText = resolved
            ? (mode === 'feat'
              ? 'Feat selected: ' + (featChoice || '—')
              : 'ASI selected: ' + asiAbilities.map(function (k) { return abilityLabels[k] || k.toUpperCase(); }).join(', '))
            : 'Selection needed';
          return [
            '<section class="cb-asi-level-row" data-builder-asi-level="' + asiLevel + '" style="margin-top:10px;padding:12px;border:1px solid rgba(201,168,76,0.16);border-radius:12px;background:rgba(6,8,10,0.34);">',
            '<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap;">',
            '<div><label style="margin:0;color:#E8C97A;">Level ' + asiLevel + ' ASI / Feat</label><div class="builder-help-text" style="margin-top:4px;">Choose one ability for +2, two different abilities for +1 each, or take one feat.</div></div>',
            '<span class="cc-tag" style="align-self:center;">' + escHtml(statusText) + '</span>',
            '</div>',
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-top:10px;">',
            '<button type="button" data-builder-asi-mode="ability" data-builder-asi-level="' + asiLevel + '" class="sheet-book-btn' + (mode === 'ability' ? ' active' : '') + '">Ability Score Improvement</button>',
            '<button type="button" data-builder-asi-mode="feat" data-builder-asi-level="' + asiLevel + '" class="sheet-book-btn' + (mode === 'feat' ? ' active' : '') + '">Choose a Feat</button>',
            '</div>',
            '<div class="field" style="margin-top:10px;"><label>Ability Score Improvement</label>',
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-top:8px;">',
            ['str','dex','con','int','wis','cha'].map(function (abilityKey) {
              var selected = asiAbilities.indexOf(abilityKey) >= 0;
              return '<button type="button" data-builder-asi-ability="' + abilityKey + '" data-builder-asi-level="' + asiLevel + '" class="sheet-book-btn' + (selected ? ' active' : '') + '" ' + (mode === 'ability' ? '' : 'disabled') + '>' + abilityNames[abilityKey] + '</button>';
            }).join(''),
            '</div>',
            '<div class="builder-help-text">Selected: ' + (asiAbilities.length ? escHtml(asiAbilities.map(function (k) { return abilityLabels[k] || k.toUpperCase(); }).join(', ')) : 'None yet') + '</div>',
            '</div>',
            '<div class="field"><label>Feat Selection</label>',
            '<select data-builder-progression-feat-pick="' + asiLevel + '" ' + (mode === 'feat' ? '' : 'disabled') + '>',
            '<option value="">Choose a feat…</option>',
            renderFeatOptions(featChoice),
            '</select>',
            '</div>',
            '</section>',
          ].join('');
        }).join('')
        : '';

      var featPickerHtml = requirements.asiLevels.length
        ? [
            '<div class="field"><label>Level-by-Level ASI / Feat Choices</label>',
            '<div class="builder-help-text">For higher-level starts, work down this list like D&amp;D Beyond and resolve each ASI/feat level separately before continuing.</div>',
            asiChoiceRowsHtml,
            '</div>',
          ].join('')
        : '<div class="builder-help-text">No ASI/feat choices unlock up to this starting level.</div>';

      var talentPickerHtml = talentRows.length ? [
        '<div class="field"><label>Talents</label>',
        '<div class="builder-help-text">Choose any talent cards your table uses.</div>',
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-top:8px;">',
        talentRows.map(function (row) {
          var id = String(row.id || '').trim();
          var selected = selectedTalents.indexOf(id) >= 0;
          return '<button type="button" data-builder-talent-pick="' + escHtml(id) + '" class="sheet-book-btn' + (selected ? ' active' : '') + '">'
            + escHtml(String(row.displayName || row.name || id))
            + '</button>';
        }).join(''),
        '</div></div>',
      ].join('') : '';

      var subclassPromptHtml = '';
      if (subclassUnlockLevel > 0) {
        if (subclassRequiredNow) {
          subclassPromptHtml = '<div class="cb-level-unlock" style="margin-top:8px;"><span class="cb-level-unlock-label">Subclass Choice Required</span><span class="cb-level-unlock-text">Your class unlocks subclass selection at level ' + subclassUnlockLevel + '. Continue to the Subclass step to choose it now.</span></div>';
        } else if (subclassSelection) {
          subclassPromptHtml = '<div class="builder-help-text" style="margin-top:8px;">Subclass selected: <strong>' + escHtml(subclassSelection) + '</strong></div>';
        } else {
          subclassPromptHtml = '<div class="builder-help-text" style="margin-top:8px;">Subclass unlock level: ' + subclassUnlockLevel + '.</div>';
        }
      }

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Set Starting Level</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Start where your campaign begins. Most games begin at level 1.</div>',
        '</div>',

        classLine,
        hiddenLevelInput,
        renderLevelPicker(safeLevel),
        milestoneHtml,
        subclassPromptHtml,

        autoUnlockHtml,
        requiredChoicesHtml,
        featPickerHtml,
        '<details class="cb-optional-section cb-optional-section--muted" data-section-key="progression-advanced"' + (_advancedOpen ? ' open' : '') + '>',
        '<summary class="cb-optional-section-summary">Optional Picks <span class="cb-optional">talents</span></summary>',
        '<div class="cb-optional-section-body">',
        talentPickerHtml,
        '</div>',
        '</details>',
      ].join('');
    },

    bind: function bindProgression(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;

      var advancedDetails = root.querySelector('details[data-section-key="progression-advanced"]');
      if (advancedDetails) {
        advancedDetails.addEventListener('toggle', function() {
          _advancedOpen = advancedDetails.open;
        });
      }

      root.querySelectorAll('.cb-level-btn[data-level-pick]').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var picked = parseInt(btn.dataset.levelPick, 10);
          if (!Number.isFinite(picked) || picked < 1 || picked > 20) return;
          var hiddenInput = root.querySelector('#cb-progression-level-hidden');
          if (hiddenInput) {
            hiddenInput.value = String(picked);
          }
          context.onSetField(['progression', 'level'], picked);
        });
      });

      root.querySelectorAll('[data-builder-asi-mode][data-builder-asi-level]').forEach(function(btn) {
        btn.addEventListener('click', function () {
          var mode = String(btn.getAttribute('data-builder-asi-mode') || 'ability').trim();
          var levelKey = parseInt(btn.getAttribute('data-builder-asi-level'), 10);
          var patch = mode === 'feat'
            ? { mode: 'feat', abilities: [], ability: '' }
            : { mode: 'ability', featId: '' };
          writeAsiChoice(context, levelKey, patch);
        });
      });

      root.querySelectorAll('[data-builder-progression-feat-pick]').forEach(function(featSelect) {
        featSelect.addEventListener('change', function() {
          var levelKey = parseInt(featSelect.getAttribute('data-builder-progression-feat-pick'), 10);
          var featId = String(featSelect.value || '').trim();
          writeAsiChoice(context, levelKey, { mode: 'feat', featId: featId, abilities: [], ability: '' });
        });
      });
      root.querySelectorAll('[data-builder-asi-ability][data-builder-asi-level]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var levelKey = parseInt(btn.getAttribute('data-builder-asi-level'), 10);
          var ability = String(btn.getAttribute('data-builder-asi-ability') || '').trim().toLowerCase();
          if (!ability) return;
          var draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
          var progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
          var requirements = computeCumulativeRequirements(draft);
          var currentChoice = getChoiceForAsiLevel(progression, requirements.asiLevels, levelKey);
          var current = normalizeAbilityList(currentChoice.abilities || (currentChoice.ability ? [currentChoice.ability] : []));
          var has = current.indexOf(ability) >= 0;
          var next = has ? current.filter(function (id) { return id !== ability; }) : current.concat([ability]);
          if (next.length > 2) next = next.slice(next.length - 2);
          writeAsiChoice(context, levelKey, { mode: 'ability', abilities: next, ability: next.length === 1 ? next[0] : '', featId: '' });
        });
      });
      root.querySelectorAll('[data-builder-talent-pick]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var talentId = String(btn.getAttribute('data-builder-talent-pick') || '').trim();
          if (!talentId) return;
          var current = Array.isArray(context.draft.progression && context.draft.progression.choiceState && context.draft.progression.choiceState.talentIds)
            ? context.draft.progression.choiceState.talentIds.map(function (v) { return String(v || '').trim(); }).filter(Boolean)
            : [];
          var has = current.indexOf(talentId) >= 0;
          var next = has ? current.filter(function (id) { return id !== talentId; }) : current.concat([talentId]);
          context.onSetField(['progression', 'choiceState'], Object.assign({}, context.draft.progression && context.draft.progression.choiceState || {}, { talentIds: next }));
          context.onSetField(['progression', 'talents'], next);
        });
      });
    },
  });
})(window);
