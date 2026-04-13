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

  function getCatalogRows(classId) {
    const api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') return [];
    const catalog = api.getCachedCatalog();
    const classRows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const row = classRows.find(function findClass(item) {
      return String(item && item.id || '').trim().toLowerCase() === classId;
    });
    const progression = Array.isArray(row && row.progressionSummary) ? row.progressionSummary : [];
    return progression.slice(0, 20);
  }

  registerStep({
    id: 'progression',
    label: 'Progression',
    render: function renderProgressionStep(context) {
      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
      const classId = getClassId(draft);
      const rows = getCatalogRows(classId);
      const level = parseInt(progression.level, 10);
      const safeLevel = Number.isFinite(level) ? level : 1;

      const unlocks = rows
        .filter(function byLevel(item) { return parseInt(item && item.level, 10) === safeLevel; })
        .map(function rowSummary(item) { return String(item && item.summary || '').trim(); })
        .filter(Boolean);

      return [
        '<div class="field"><label>Current Level</label>',
        '<input type="number" min="1" max="20" step="1" data-builder-path="progression.level" value="' + escHtml(safeLevel) + '" /></div>',
        '<div class="field"><label>Feat Picks (comma-separated ids or names)</label>',
        '<input type="text" data-builder-progression-feats="1" value="' + escHtml(Array.isArray(progression.feats) ? progression.feats.join(', ') : '') + '" maxlength="280" placeholder="alert, war-caster" /></div>',
        '<div class="field"><label>Talent Picks (comma-separated ids)</label>',
        '<input type="text" data-builder-progression-talents="1" value="' + escHtml(Array.isArray(progression.talents) ? progression.talents.join(', ') : '') + '" maxlength="280" placeholder="fighter-bulwark-stance" /></div>',
        '<div class="field"><label>Awakening Path (future system)</label>',
        '<input type="text" data-builder-path="progression.awakening.track" value="' + escHtml(progression.awakening && progression.awakening.track || '') + '" maxlength="120" placeholder="Leave blank until unlocked" /></div>',
        '<div class="builder-help-text">',
        unlocks.length
          ? ('Level ' + escHtml(safeLevel) + ' unlock preview: ' + escHtml(unlocks.join(' · ')))
          : 'No catalog unlock summary found for this class/level yet. Progression remains editable.',
        '</div>',
      ].join('');
    },
    bind: function bindProgression(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      const featsInput = root.querySelector('[data-builder-progression-feats="1"]');
      const talentsInput = root.querySelector('[data-builder-progression-talents="1"]');

      function parseCsv(value) {
        return String(value || '')
          .split(',')
          .map(function normalize(item) { return String(item || '').trim(); })
          .filter(Boolean);
      }

      if (featsInput) {
        featsInput.addEventListener('input', function onFeatInput() {
          context.onSetField(['progression', 'feats'], parseCsv(featsInput.value));
        });
      }
      if (talentsInput) {
        talentsInput.addEventListener('input', function onTalentInput() {
          context.onSetField(['progression', 'talents'], parseCsv(talentsInput.value));
        });
      }
    },
  });
})(window);
