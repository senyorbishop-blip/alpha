(function initCharacterBuilderStepClass(global) {
  var FALLBACK_CLASS_CATALOG = {
    catalogVersion: 1,
    entries: [],
  };

  var CLASS_COLORS = {
    fighter: '#C0392B', wizard: '#2471A3', rogue: '#7F8C8D',
    barbarian: '#884EA0', paladin: '#F0B27A', bard: '#1ABC9C',
    cleric: '#F4D03F', monk: '#A9CCE3', warlock: '#8E44AD',
    druid: '#58D68D', sorcerer: '#E74C3C', ranger: '#27AE60',
    tinker: '#E67E22', pirate: '#2980B9',
  };

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

  function ensureCatalogLoaded() {
    var api = global.CharacterBuilderAPI;
    if (!api || typeof api.fetchCatalog !== 'function') return;
    api.fetchCatalog({ rulesMode: 'casual' }).catch(function ignoreFailure() {});
  }

  function normalizeId(value) {
    return String(value || '').trim().toLowerCase();
  }

  function ensureBuilderStyles() {
    if (document.getElementById('character-builder-css')) return;
    var link = document.createElement('link');
    link.id = 'character-builder-css';
    link.rel = 'stylesheet';
    link.href = '/static/css/character-builder.css';
    document.head.appendChild(link);
  }

  function getClassCatalogEntries() {
    var api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') {
      return FALLBACK_CLASS_CATALOG.entries;
    }
    var catalog = api.getCachedCatalog();
    var rows = catalog && Array.isArray(catalog.classes) ? catalog.classes : [];
    return rows.map(function toEntry(row) {
      var progressionTable = Array.isArray(row && row.progressionTable) ? row.progressionTable : [];
      var progressionSummary = Array.isArray(row && row.progressionSummary) ? row.progressionSummary : [];
      return {
        id: String(row && row.id || '').trim(),
        name: String(row && row.displayName || row && row.id || '').trim(),
        roleIdentity: String(row && row.roleIdentity || '').trim(),
        classDescription: String(row && row.classDescription || '').trim(),
        hitDie: parseInt(row && row.hitDie, 10),
        primaryAbilities: Array.isArray(row && row.primaryAbilities) ? row.primaryAbilities : [],
        savingThrows: Array.isArray(row && row.savingThrows) ? row.savingThrows : [],
        armorProficiencies: Array.isArray(row && row.armorProficiencies) ? row.armorProficiencies : [],
        weaponProficiencies: Array.isArray(row && row.weaponProficiencies) ? row.weaponProficiencies : [],
        toolProficiencies: Array.isArray(row && row.toolProficiencies) ? row.toolProficiencies : [],
        skillChoices: row && row.skillChoices && typeof row.skillChoices === 'object' ? row.skillChoices : {},
        subclassLevel: parseInt(row && row.subclassLevel, 10),
        subclassDisplayName: String(row && row.subclassDisplayName || 'Subclass').trim(),
        spellcastingType: String(row && row.spellcastingType || 'none').trim(),
        spellcastingAbility: String(row && row.spellcastingAbility || '').trim(),
        buildTips: row && row.buildTips && typeof row.buildTips === 'object' ? row.buildTips : {},
        featureDefinitions: (row && row.featureDefinitions && typeof row.featureDefinitions === 'object') ? row.featureDefinitions : {},
        featuresByLevel: Array.isArray(row && row.featuresByLevel) ? row.featuresByLevel : [],
        progressionTable: progressionTable,
        progressionSummary: progressionSummary,
      };
    }).filter(function validEntry(entry) {
      return !!entry.id;
    });
  }

  function getClassColor(entry) {
    var key = normalizeId(entry && entry.id);
    return CLASS_COLORS[key] || '#c9a84c';
  }

  function getFeatureDefinitionMap(entry) {
    return (entry && entry.featureDefinitions && typeof entry.featureDefinitions === 'object') ? entry.featureDefinitions : {};
  }

  function renderDetailPane(entry, draft) {
    var color = getClassColor(entry);

    // Combo portrait preview for the currently selected combo
    var portraitPreviewHtml = '';
    var portraitLib = global.CasualDnDPortraitLibrary;
    if (portraitLib && typeof portraitLib.resolve === 'function' && draft) {
      var previewUrl = portraitLib.resolve({
        classId: entry.id,
        speciesId: draft.species && draft.species.id,
        gender: draft.identity && draft.identity.gender,
      });
      if (previewUrl) {
        portraitPreviewHtml = '<div style="float:right;width:72px;height:80px;border-radius:10px;overflow:hidden;' +
          'border:1px solid rgba(201,168,76,0.25);margin:0 0 8px 10px;flex-shrink:0;">' +
          '<img src="' + escHtml(previewUrl) + '" style="width:100%;height:100%;object-fit:cover" alt="Hero preview"></div>';
      }
    }
    var casterType = normalizeId(entry.spellcastingType);
    var spellStatHtml;
    var spellAbility = String(entry.spellcastingAbility || '').trim().toUpperCase();
    if (casterType && casterType !== 'none') {
      var casterLabel = casterType === 'full' ? 'Full' : casterType === 'half' ? 'Half' : 'Pact';
      spellStatHtml = '<div class="cd-stat"><div class="cd-stat-val" style="color:#5ba3d0">' + escHtml(casterLabel) + '</div><div class="cd-stat-lbl">Caster</div></div>' +
        '<div class="cd-stat"><div class="cd-stat-val" style="color:#9dd7ff">' + escHtml(spellAbility || '—') + '</div><div class="cd-stat-lbl">Spell Ability</div></div>';
    } else {
      spellStatHtml = '<div class="cd-stat"><div class="cd-stat-val" style="color:var(--cb-text-dim)">None</div><div class="cd-stat-lbl">Spellcasting</div></div>';
    }

    var primaryStr = entry.primaryAbilities.map(function(a) { return String(a || '').toUpperCase(); }).join('/') || '—';
    var savesStr = entry.savingThrows.map(function(a) { return String(a || '').toUpperCase(); }).join('/') || '—';
    var armorStr = entry.armorProficiencies.map(function(v) { return String(v || '').replace(/(^|-)([a-z])/g, function(_, a, b){ return a + b.toUpperCase(); }); }).join(', ') || '—';
    var weaponStr = entry.weaponProficiencies.map(function(v) { return String(v || '').replace(/(^|-)([a-z])/g, function(_, a, b){ return a + b.toUpperCase(); }); }).join(', ') || '—';
    var toolStr = entry.toolProficiencies.map(function(v) { return String(v || '').replace(/(^|-)([a-z])/g, function(_, a, b){ return a + b.toUpperCase(); }); }).join(', ') || '—';
    var skillsFrom = Array.isArray(entry.skillChoices && entry.skillChoices.from) ? entry.skillChoices.from : [];
    var skillsCount = parseInt(entry.skillChoices && entry.skillChoices.count, 10) || 0;
    var skillsStr = skillsFrom.length ? ('Choose ' + skillsCount + ': ' + skillsFrom.join(', ')) : '—';
    var subclassText = entry.subclassLevel > 0 ? ('Level ' + entry.subclassLevel + ' ' + (entry.subclassDisplayName || 'Subclass')) : 'No subclass track';
    var descHtml = entry.classDescription
      ? '<div class="cd-desc">' + escHtml(entry.classDescription) + '</div>'
      : '';
    var buildTips = entry.buildTips && typeof entry.buildTips === 'object' ? entry.buildTips : {};
    var primaryFocus = String(buildTips.primaryFocus || '').trim();
    var secondaryFocus = String(buildTips.secondaryFocus || '').trim();
    var avoidDump = String(buildTips.avoidDump || '').trim();
    var buildTipsHtml = (primaryFocus || secondaryFocus || avoidDump)
      ? '<div style="margin:0 0 16px;padding:10px 12px;border:1px solid rgba(91,163,208,0.25);border-radius:10px;background:rgba(12,20,32,0.35)">' +
          '<div style="font-family:var(--cb-font-display);font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;color:#9dd7ff;margin-bottom:6px">Build tips</div>' +
          (primaryFocus ? '<div class="cd-desc" style="margin:0 0 4px 0"><strong style="color:#f3e7c4">Primary:</strong> ' + escHtml(primaryFocus + (buildTips.primaryReason ? (' — ' + buildTips.primaryReason) : '')) + '</div>' : '') +
          (secondaryFocus ? '<div class="cd-desc" style="margin:0 0 4px 0"><strong style="color:#f3e7c4">Secondary:</strong> ' + escHtml(secondaryFocus + (buildTips.secondaryReason ? (' — ' + buildTips.secondaryReason) : '')) + '</div>' : '') +
          (avoidDump ? '<div class="cd-desc" style="margin:0"><strong style="color:#f3e7c4">Avoid dumping:</strong> ' + escHtml(avoidDump + (buildTips.avoidDumpReason ? (' — ' + buildTips.avoidDumpReason) : '')) + '</div>' : '') +
        '</div>'
      : '';

    var progressionRows = Array.isArray(entry.progressionTable) ? entry.progressionTable : [];
    var tableBody = progressionRows.map(function toRow(levelRow) {
      if (!levelRow || typeof levelRow !== 'object') return '';
      var feats = Array.isArray(levelRow.features) ? levelRow.features : [];
      var featuresLower = feats.join(' ').toLowerCase();
      var isAsi = featuresLower.indexOf('ability score improvement') !== -1 || featuresLower.indexOf('epic boon') !== -1;
      var isSub = featuresLower.indexOf('subclass') !== -1 || featuresLower.indexOf('tradition') !== -1;
      var rowClass = isAsi ? 'asi-row' : isSub ? 'subclass-row' : '';

      var rowFeatureDefs = getFeatureDefinitionMap(entry);
      var featureTags = feats.map(function toTag(f, idx) {
        var fLower = String(f).toLowerCase();
        var tagClass = 'feature-tag';
        if (fLower.indexOf('ability score improvement') !== -1 || fLower.indexOf('epic boon') !== -1) {
          tagClass += ' asi';
        } else if (fLower.indexOf('subclass') !== -1 || fLower.indexOf('tradition') !== -1) {
          tagClass += ' subclass';
        }
        var unlockId = Array.isArray(levelRow.unlockIds) && levelRow.unlockIds[idx] ? String(levelRow.unlockIds[idx]) : '';
        var detail = unlockId && rowFeatureDefs[unlockId] && rowFeatureDefs[unlockId].description
          ? String(rowFeatureDefs[unlockId].description)
          : '';
        var detailAttr = detail ? ' title="' + escHtml(detail) + '"' : '';
        return '<span class="' + tagClass + '"' + detailAttr + '>' + escHtml(f) + '</span>';
      }).join('');

      return '<tr class="' + rowClass + '">' +
        '<td><span class="prog-level-badge">' + escHtml(levelRow.level) + '</span></td>' +
        '<td>+' + escHtml(levelRow.proficiencyBonus) + '</td>' +
        '<td>' + (featureTags || '—') + '</td>' +
        '</tr>';
    }).join('');

    var featureDefs = getFeatureDefinitionMap(entry);
    // Sort by level ascending so the spotlight shows level 1-2 features first,
    // giving players the most immediately relevant info about how the class plays.
    var spotlightIds = Object.keys(featureDefs).sort(function(a, b) {
      var la = parseInt((featureDefs[a] && featureDefs[a].level) || 99, 10);
      var lb = parseInt((featureDefs[b] && featureDefs[b].level) || 99, 10);
      return la - lb;
    }).slice(0, 6);
    var spotlight = spotlightIds.map(function(id) {
      var def = featureDefs[id] || {};
      var levelBadge = parseInt(def.level, 10) > 0 ? '<span class="cc-tag">Lv ' + escHtml(def.level) + '</span>' : '';
      var typeBadge = def.type ? '<span class="cc-tag">' + escHtml(String(def.type).replace(/_/g, ' ')) + '</span>' : '';
      var resourceBadge = def.resourceName ? '<span class="cc-tag">' + escHtml(def.resourceName) + '</span>' : '';
      return '<div style="padding:10px 12px;border-top:1px solid rgba(255,255,255,0.05)">' +
        '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:4px"><strong style="color:#f3e7c4">' + escHtml(def.displayName || id) + '</strong>' + levelBadge + typeBadge + resourceBadge + '</div>' +
        '<div style="font-size:0.7rem;line-height:1.55;color:rgba(220,214,200,0.88)">' + escHtml(def.description || 'Unlocks as part of this class progression.') + '</div>' +
      '</div>';
    }).join('');

    return '<div class="cls-detail-inner">' +
      portraitPreviewHtml +
      '<div class="cls-detail-title" style="color:' + color + '">' + escHtml(entry.name) + '</div>' +
      '<div class="cd-stats" style="margin:12px 0 16px">' +
        '<div class="cd-stat"><div class="cd-stat-val">d' + escHtml(entry.hitDie) + '</div><div class="cd-stat-lbl">Hit Die</div></div>' +
        '<div class="cd-stat"><div class="cd-stat-val">' + escHtml(primaryStr) + '</div><div class="cd-stat-lbl">Primary</div></div>' +
        '<div class="cd-stat"><div class="cd-stat-val">' + escHtml(savesStr) + '</div><div class="cd-stat-lbl">Saves</div></div>' +
        spellStatHtml +
      '</div>' +
      (descHtml ? '<div style="padding-bottom:16px;margin-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.06)">' + descHtml + '</div>' : '') +
      '<div style="overflow-x:auto;margin-bottom:20px">' +
        '<table class="prog-table">' +
          '<thead><tr><th>Lvl</th><th>Prof</th><th>Features</th></tr></thead>' +
          '<tbody>' + tableBody + '</tbody>' +
        '</table>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:14px">' +
        '<div class="cd-desc" style="margin:0"><strong style="color:#f3e7c4">Armor Proficiencies:</strong> ' + escHtml(armorStr) + '</div>' +
        '<div class="cd-desc" style="margin:0"><strong style="color:#f3e7c4">Weapon Proficiencies:</strong> ' + escHtml(weaponStr) + '</div>' +
        '<div class="cd-desc" style="margin:0"><strong style="color:#f3e7c4">Tool Proficiencies:</strong> ' + escHtml(toolStr) + '</div>' +
        '<div class="cd-desc" style="margin:0"><strong style="color:#f3e7c4">Skill Choices:</strong> ' + escHtml(skillsStr) + '</div>' +
        '<div class="cd-desc" style="margin:0"><strong style="color:#f3e7c4">Subclass Unlock:</strong> ' + escHtml(subclassText) + '</div>' +
      '</div>' +
      buildTipsHtml +
      '<div style="border:1px solid rgba(201,168,76,0.14);border-radius:10px;background:rgba(6,8,10,0.38)">' +
        '<div style="padding:10px 12px;border-bottom:1px solid rgba(201,168,76,0.12);font-family:var(--cb-font-display);font-size:0.82rem;color:#E8C97A">Feature Spotlight</div>' +
        (spotlight || '<div style="padding:10px 12px;color:rgba(168,159,142,0.88);font-size:0.7rem;">Detailed feature text will appear here as the class data expands.</div>') +
      '</div>' +
    '</div>';
  }

  function showClassDetailPanel(root, classId, draft) {
    var entries = getClassCatalogEntries();
    var entry = entries.find(function findEntry(e) { return normalizeId(e.id) === normalizeId(classId); });
    var panel = root.querySelector('#builder-class-detail');
    if (!panel) return;
    if (!entry) {
      panel.innerHTML = '<div class="cls-detail-empty"><div style="font-size:2.5rem;opacity:0.25">⚔</div><div>Select a class to view details</div></div>';
      return;
    }
    panel.innerHTML = renderDetailPane(entry, draft);
  }

  registerStep({
    id: 'class',
    label: 'Class',
    render: function renderClassStep(context) {
      ensureBuilderStyles();
      ensureCatalogLoaded();
      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var classData = draft.class && typeof draft.class === 'object' ? draft.class : {};
      var selectedId = String(classData.id || '').trim();
      var entries = getClassCatalogEntries();

      var listItems = entries.map(function toListItem(entry) {
        var isSelected = normalizeId(entry.id) === normalizeId(selectedId);
        var color = getClassColor(entry);
        var casterType = normalizeId(entry.spellcastingType);
        var casterDot = '';
        if (casterType === 'full') casterDot = '<span class="cls-caster-dot full" title="Full Caster"></span>';
        else if (casterType === 'half') casterDot = '<span class="cls-caster-dot half" title="Half Caster"></span>';
        else if (casterType === 'pact') casterDot = '<span class="cls-caster-dot pact" title="Pact Magic"></span>';

        return '<div class="cls-list-item' + (isSelected ? ' selected' : '') + '" data-class-id="' + escHtml(entry.id) + '" style="--class-color:' + color + '">' +
          '<span class="cls-list-dot" style="background:' + color + '"></span>' +
          '<span class="cls-list-name">' + escHtml(entry.name) + '</span>' +
          casterDot +
          '<span class="cls-list-die">d' + escHtml(entry.hitDie) + '</span>' +
        '</div>';
      }).join('');

      var detailContent = selectedId
        ? (function() {
            var sel = entries.find(function(e) { return normalizeId(e.id) === normalizeId(selectedId); });
            return sel ? renderDetailPane(sel, draft) : '<div class="cls-detail-empty"><div style="font-size:2.5rem;opacity:0.25">⚔</div><div>Select a class to view details</div></div>';
          })()
        : '<div class="cls-detail-empty"><div style="font-size:2.5rem;opacity:0.25">⚔</div><div>Select a class to view details</div></div>';

      return '<div class="screen-header">' +
          '<div class="screen-title">Choose Your Class</div>' +
          '<div class="screen-divider"></div>' +
          '<div class="screen-subtitle">Your class is your calling — it defines your powers, fighting style, and path forward</div>' +
        '</div>' +
        '<input type="hidden" data-builder-path="class.id" value="' + escHtml(selectedId) + '" />' +
        '<div class="cls-picker-layout">' +
          '<nav class="cls-sidebar" aria-label="Class list">' + listItems + '</nav>' +
          '<div class="cls-detail-pane" id="builder-class-detail">' + detailContent + '</div>' +
        '</div>';
    },
    bind: function bindClassStep(root, context) {
      root.querySelectorAll('.cls-list-item').forEach(function(item) {
        item.addEventListener('click', function() {
          var id = item.dataset.classId;
          var hiddenInput = root.querySelector('[data-builder-path="class.id"]');
          if (hiddenInput) hiddenInput.value = id;
          if (context && typeof context.onSetField === 'function') {
            context.onSetField(['class', 'id'], id);
          }
          root.querySelectorAll('.cls-list-item').forEach(function(i) { i.classList.remove('selected'); });
          item.classList.add('selected');
          showClassDetailPanel(root, id, context && context.draft);
        });
      });
    },
    getCatalog: function getCatalog() {
      return {
        catalogVersion: 1,
        entries: getClassCatalogEntries(),
      };
    },
  });
})(window);
