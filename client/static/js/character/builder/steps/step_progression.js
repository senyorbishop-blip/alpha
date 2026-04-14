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

  // Track advanced section open state across re-renders
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

      // Milestone unlocks hint
      var milestoneHtml = '';
      if (featureText) {
        milestoneHtml = [
          '<div class="cb-level-unlock">',
          '<span class="cb-level-unlock-label">Level ' + safeLevel + ' Unlocks</span>',
          '<span class="cb-level-unlock-text">' + escHtml(featureText) + '</span>',
          '</div>',
        ].join('');
      } else if (classId) {
        milestoneHtml = '<div class="cb-level-unlock cb-level-unlock--empty">Level ' + safeLevel + ' \u2014 choose your starting level.</div>';
      } else {
        milestoneHtml = '<div class="cb-level-unlock cb-level-unlock--empty">Select a class first to preview level features.</div>';
      }

      // Hidden bound input — keeps data-builder-path binding intact
      var hiddenLevelInput = '<input type="hidden" data-builder-path="progression.level" value="' + safeLevel + '" id="cb-progression-level-hidden" />';

      // Class context line
      var classLine = className
        ? '<div class="cb-prog-class-line">' + escHtml(className) + ' \u00b7 Level ' + safeLevel + '</div>'
        : '';

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

        '<details class="cb-optional-section" data-section-key="progression-advanced"'
          + (_advancedOpen ? ' open' : '') + '>',
        '<summary class="cb-optional-section-summary">Advanced Options <span class="cb-optional">feats &amp; talents</span></summary>',
        '<div class="cb-optional-section-body">',

        '<div class="field">',
        '<label>Starting Feats <span class="cb-optional">comma-separated</span></label>',
        '<input type="text" data-builder-progression-feats="1"',
        ' value="' + escHtml(Array.isArray(progression.feats) ? progression.feats.join(', ') : '') + '"',
        ' maxlength="280" placeholder="alert, war-caster, tough\u2026" />',
        '<div class="builder-help-text">Leave blank for most characters. Your DM may grant feats at certain levels.</div>',
        '</div>',

        '<div class="field">',
        '<label>Starting Talents <span class="cb-optional">comma-separated</span></label>',
        '<input type="text" data-builder-progression-talents="1"',
        ' value="' + escHtml(Array.isArray(progression.talents) ? progression.talents.join(', ') : '') + '"',
        ' maxlength="280" placeholder="fighter-bulwark-stance\u2026" />',
        '</div>',

        '</div>',
        '</details>',
      ].join('');
    },

    bind: function bindProgression(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;

      // Track advanced section toggle
      var advancedDetails = root.querySelector('details[data-section-key="progression-advanced"]');
      if (advancedDetails) {
        advancedDetails.addEventListener('toggle', function() {
          _advancedOpen = advancedDetails.open;
        });
      }

      // Level picker buttons
      root.querySelectorAll('.cb-level-btn[data-level-pick]').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var picked = parseInt(btn.dataset.levelPick, 10);
          if (!Number.isFinite(picked) || picked < 1 || picked > 20) return;
          // Update the hidden input so data-builder-path binding stays in sync
          var hiddenInput = root.querySelector('#cb-progression-level-hidden');
          if (hiddenInput) {
            hiddenInput.value = String(picked);
          }
          context.onSetField(['progression', 'level'], picked);
        });
      });

      // Feats / talents CSV inputs
      var featsInput = root.querySelector('[data-builder-progression-feats="1"]');
      var talentsInput = root.querySelector('[data-builder-progression-talents="1"]');

      function parseCsv(value) {
        return String(value || '')
          .split(',')
          .map(function(item) { return String(item || '').trim(); })
          .filter(Boolean);
      }

      if (featsInput) {
        featsInput.addEventListener('input', function() {
          context.onSetField(['progression', 'feats'], parseCsv(featsInput.value));
        });
      }
      if (talentsInput) {
        talentsInput.addEventListener('input', function() {
          context.onSetField(['progression', 'talents'], parseCsv(talentsInput.value));
        });
      }
    },
  });
})(window);
