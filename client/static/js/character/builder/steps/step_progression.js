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
      const featureText = getFeaturesAtLevel(progressionSummary, safeLevel);
      const featLevel = isFeatLevel(progressionSummary, safeLevel);
      const featRows = getFeatRows();

      const asiChoice = progression.asiChoice && typeof progression.asiChoice === 'object' ? progression.asiChoice : {};
      const asiMode = String(asiChoice.mode || 'ability').toLowerCase() === 'feat' ? 'feat' : 'ability';
      const featChoice = String(asiChoice.featId || (Array.isArray(progression.feats) ? progression.feats[0] : '') || '').trim();

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
        ? '<div class="cb-prog-class-line">' + escHtml(className) + ' · Level ' + safeLevel + '</div>'
        : '';

      var featPickerHtml = featLevel
        ? [
            '<div class="field"><label>Level ' + safeLevel + ' Choice</label>',
            '<div class="builder-help-text">This level grants an Ability Score Improvement or a Feat choice.</div>',
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-top:8px;">',
            '<button type="button" data-builder-asi-mode="ability" class="sheet-book-btn' + (asiMode === 'ability' ? ' active' : '') + '">Ability Score Improvement</button>',
            '<button type="button" data-builder-asi-mode="feat" class="sheet-book-btn' + (asiMode === 'feat' ? ' active' : '') + '">Choose a Feat</button>',
            '</div></div>',
            '<div class="field"><label>Feat Selection</label>',
            '<select data-builder-progression-feat-pick="1" ' + (asiMode === 'feat' ? '' : 'disabled') + '>',
            '<option value="">Choose a feat…</option>',
            featRows.map(function (row) {
              var id = String(row.id || '').trim();
              var selected = id && id === featChoice ? ' selected' : '';
              return '<option value="' + escHtml(id) + '"' + selected + '>' + escHtml(String(row.displayName || row.name || id)) + '</option>';
            }).join(''),
            '</select>',
            '<div class="builder-help-text">Structured feat choice is saved directly; no CSV typing required.</div>',
            '</div>',
          ].join('')
        : '<div class="builder-help-text">No feat/ASI pick is required at Level ' + safeLevel + '.</div>';

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Starting Level</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Most campaigns begin at Level 1. Your DM may tell you to start higher.</div>',
        '</div>',

        classLine,
        hiddenLevelInput,
        renderLevelPicker(safeLevel),
        milestoneHtml,

        '<details class="cb-optional-section" data-section-key="progression-advanced"' + (_advancedOpen ? ' open' : '') + '>',
        '<summary class="cb-optional-section-summary">Advanced Options <span class="cb-optional">feats &amp; talents</span></summary>',
        '<div class="cb-optional-section-body">',
        featPickerHtml,
        '<div class="field">',
        '<label>Talents <span class="cb-optional">comma-separated (optional)</span></label>',
        '<input type="text" data-builder-progression-talents="1"',
        ' value="' + escHtml(Array.isArray(progression.talents) ? progression.talents.join(', ') : '') + '"',
        ' maxlength="280" placeholder="fighter-bulwark-stance…" />',
        '</div>',
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
          var next = Object.assign({}, existing, { mode: mode === 'feat' ? 'feat' : 'ability' });
          context.onSetField(['progression', 'asiChoice'], next);
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
        });
      }

      var talentsInput = root.querySelector('[data-builder-progression-talents="1"]');
      function parseCsv(value) {
        return String(value || '')
          .split(',')
          .map(function(item) { return String(item || '').trim(); })
          .filter(Boolean);
      }
      if (talentsInput) {
        talentsInput.addEventListener('input', function() {
          context.onSetField(['progression', 'talents'], parseCsv(talentsInput.value));
        });
      }
    },
  });
})(window);
