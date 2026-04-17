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
      const progressionSummary = getProgressionSummary(draft);
      const progressionTable = getProgressionTable(draft);
      const levelRow = getLevelRow(progressionTable, safeLevel);
      const featureText = getFeaturesAtLevel(progressionSummary, safeLevel);
      const featLevel = hasFeatOrAsiChoice(levelRow, progressionSummary, safeLevel);
      const featRows = getFeatRows();
      const talentRows = getTalentRowsForClass(classId).filter(function (row) {
        var minLevel = parseInt(row && row.minimumLevel, 10);
        if (!Number.isFinite(minLevel) || minLevel < 1) minLevel = 1;
        return safeLevel >= minLevel;
      });

      const asiChoice = progression.asiChoice && typeof progression.asiChoice === 'object' ? progression.asiChoice : {};
      const asiMode = String(asiChoice.mode || 'ability').toLowerCase() === 'feat' ? 'feat' : 'ability';
      const featChoice = String(asiChoice.featId || (Array.isArray(progression.feats) ? progression.feats[0] : '') || '').trim();
      const choiceState = progression.choiceState && typeof progression.choiceState === 'object' ? progression.choiceState : {};
      const asiAbilities = getAbilityChoiceState(progression, asiMode);
      const selectedTalents = Array.isArray(choiceState.talentIds)
        ? choiceState.talentIds.map(function (v) { return String(v || '').trim(); }).filter(Boolean)
        : (Array.isArray(progression.talents) ? progression.talents.map(function (v) { return String(v || '').trim(); }).filter(Boolean) : []);
      const subclassUnlockLevel = getSubclassUnlockLevel(draft);
      const subclassRequiredNow = !!(subclassUnlockLevel && safeLevel >= subclassUnlockLevel && !String(draft && draft.class && draft.class.subclassId || '').trim());
      const subclassSelection = String(draft && draft.class && draft.class.subclassId || '').trim();

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

      var featPickerHtml = featLevel
        ? [
            '<div class="field"><label>Level ' + safeLevel + ' Choice</label>',
            '<div class="builder-help-text">This level grants either an Ability Score Improvement or a Feat.</div>',
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-top:8px;">',
            '<button type="button" data-builder-asi-mode="ability" class="sheet-book-btn' + (asiMode === 'ability' ? ' active' : '') + '">Ability Score Improvement</button>',
            '<button type="button" data-builder-asi-mode="feat" class="sheet-book-btn' + (asiMode === 'feat' ? ' active' : '') + '">Choose a Feat</button>',
            '</div></div>',
            '<div class="field"><label>Ability Score Improvement</label>',
            '<div class="builder-help-text">Pick one ability for +2, or two different abilities for +1 each.</div>',
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-top:8px;">',
            ['str','dex','con','int','wis','cha'].map(function (abilityKey) {
              var names = { str: 'Strength', dex: 'Dexterity', con: 'Constitution', int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma' };
              var selected = asiAbilities.indexOf(abilityKey) >= 0;
              return '<button type="button" data-builder-asi-ability="' + abilityKey + '" class="sheet-book-btn' + (selected ? ' active' : '') + '" ' + (asiMode === 'ability' ? '' : 'disabled') + '>' + names[abilityKey] + '</button>';
            }).join(''),
            '</div>',
            '<div class="builder-help-text">Selected: ' + (asiAbilities.length ? escHtml(asiAbilities.map(function (k) { return ({ str: 'STR', dex: 'DEX', con: 'CON', int: 'INT', wis: 'WIS', cha: 'CHA' })[k] || k.toUpperCase(); }).join(', ')) : 'None yet') + '</div>',
            '</div>',
            '<div class="field"><label>Feat Selection</label>',
            '<select data-builder-progression-feat-pick="1" ' + (asiMode === 'feat' ? '' : 'disabled') + '>',
            '<option value="">Choose a feat…</option>',
            featRows.map(function (row) {
              var id = String(row.id || '').trim();
              var selected = id && id === featChoice ? ' selected' : '';
              return '<option value="' + escHtml(id) + '"' + selected + '>' + escHtml(String(row.displayName || row.name || id)) + '</option>';
            }).join(''),
            '</select>',
            '<div class="builder-help-text">Your feat selection saves automatically.</div>',
            '</div>',
          ].join('')
        : '<div class="builder-help-text">No feat or ASI choice is required at this level.</div>';

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

        '<details class="cb-optional-section cb-optional-section--muted" data-section-key="progression-advanced"' + (_advancedOpen ? ' open' : '') + '>',
        '<summary class="cb-optional-section-summary">Advanced Picks <span class="cb-optional">feats &amp; talents</span></summary>',
        '<div class="cb-optional-section-body">',
        featPickerHtml,
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

      root.querySelectorAll('[data-builder-asi-mode]').forEach(function(btn) {
        btn.addEventListener('click', function () {
          var mode = String(btn.getAttribute('data-builder-asi-mode') || 'ability').trim();
          var existing = context && context.draft && context.draft.progression && context.draft.progression.asiChoice
            ? context.draft.progression.asiChoice
            : {};
          var currentChoiceState = context.draft.progression && context.draft.progression.choiceState || {};
          var next = Object.assign({}, existing, { mode: mode === 'feat' ? 'feat' : 'ability' });
          if (mode === 'feat') {
            next.ability = '';
            next.abilities = [];
          } else {
            next.featId = '';
          }
          context.onSetField(['progression', 'asiChoice'], next);
          context.onSetField(['progression', 'choiceState'], Object.assign({}, currentChoiceState, { asiMode: next.mode }, mode === 'feat' ? {} : { featId: '' }));
          if (mode !== 'feat') context.onSetField(['progression', 'feats'], []);
        });
      });

      var featSelect = root.querySelector('[data-builder-progression-feat-pick="1"]');
      if (featSelect) {
        featSelect.addEventListener('change', function() {
          var featId = String(featSelect.value || '').trim();
          var existing = context && context.draft && context.draft.progression && context.draft.progression.asiChoice
            ? context.draft.progression.asiChoice
            : {};
          context.onSetField(['progression', 'asiChoice'], Object.assign({}, existing, { mode: 'feat', featId: featId }));
          context.onSetField(['progression', 'feats'], featId ? [featId] : []);
          context.onSetField(['progression', 'choiceState'], Object.assign({}, context.draft.progression && context.draft.progression.choiceState || {}, {
            asiMode: 'feat',
            featId: featId,
          }));
        });
      }
      root.querySelectorAll('[data-builder-asi-ability]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var ability = String(btn.getAttribute('data-builder-asi-ability') || '').trim().toLowerCase();
          if (!ability) return;
          var current = Array.isArray(context.draft.progression && context.draft.progression.choiceState && context.draft.progression.choiceState.asiAbilities)
            ? context.draft.progression.choiceState.asiAbilities.map(function (v) { return String(v || '').trim().toLowerCase(); }).filter(Boolean)
            : [];
          var has = current.indexOf(ability) >= 0;
          var next = has ? current.filter(function (id) { return id !== ability; }) : current.concat([ability]);
          if (next.length > 2) next = next.slice(next.length - 2);
          var asiChoice = context && context.draft && context.draft.progression && context.draft.progression.asiChoice
            ? Object.assign({}, context.draft.progression.asiChoice)
            : {};
          asiChoice.mode = 'ability';
          if (next.length === 1) {
            asiChoice.ability = next[0];
            asiChoice.abilities = [next[0]];
          } else {
            asiChoice.ability = '';
            asiChoice.abilities = next.slice();
          }
          context.onSetField(['progression', 'asiChoice'], asiChoice);
          context.onSetField(['progression', 'choiceState'], Object.assign({}, context.draft.progression && context.draft.progression.choiceState || {}, {
            asiMode: 'ability',
            asiAbilities: next,
          }));
          context.onSetField(['progression', 'feats'], []);
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
