(function initCharacterBuilderStepSpecies(global) {
  var FALLBACK_SPECIES_CATALOG = {
    catalogVersion: 1,
    entries: [],
  };

  var DEFAULT_SPECIES_COLOR = '#C9A84C';
  var DEFAULT_SPECIES_ICON = '🧬';

  var SPECIES_ICONS = {
    human: '👤', elf: '🌙', dwarf: '⛏', halfling: '🍀',
    dragonborn: '🐉', tiefling: '😈', gnome: '🔬', 'half-elf': '🌙',
    'half-orc': '💪', 'wood-elf': '🌲', aasimar: '✨', goliath: '⛰️', orc: '💚'
  };

  var SPECIES_COLORS = {
    human: '#C9A84C', elf: '#7FB3D3', 'wood-elf': '#58D68D', dwarf: '#A0826D',
    halfling: '#82E0AA', dragonborn: '#E74C3C', tiefling: '#C0392B',
    gnome: '#48C9B0', 'half-elf': '#85C1E9', 'half-orc': '#27AE60',
    aasimar: '#F7DC6F', goliath: '#AAB7B8', orc: '#58D68D'
  };

  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function escAttr(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
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

  function getSpeciesCatalogEntries() {
    var api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') {
      return FALLBACK_SPECIES_CATALOG.entries;
    }
    var catalog = api.getCachedCatalog();
    var rows = catalog && Array.isArray(catalog.species) ? catalog.species : [];
    return rows.map(function toEntry(row) {
      var movement = row && typeof row.movement === 'object' ? row.movement : {};
      var walk = parseInt(movement.walk, 10);
      var senses = row && typeof row.senses === 'object' ? row.senses : {};
      var darkvision = parseInt(senses.darkvision, 10);
      var traits = Array.isArray(row && row.traits) ? row.traits : [];
      return {
        id: String(row && row.id || '').trim(),
        name: String(row && row.displayName || row && row.id || '').trim(),
        icon: row && row.icon || '',
        size: String(row && row.size || '').trim(),
        speed: Number.isFinite(walk) && walk > 0 ? walk : 0,
        darkvision: Number.isFinite(darkvision) && darkvision > 0 ? darkvision : 0,
        flavorText: String(row && row.flavorText || '').trim(),
        traits: traits,
        abilityBonuses: row && row.abilityBonuses,
        languages: Array.isArray(row && row.languages) ? row.languages : [],
        proficiencies: row && row.proficiencies,
      };
    }).filter(function validEntry(entry) {
      return !!entry.id;
    });
  }

  function getTraitName(trait) {
    if (!trait || typeof trait !== 'object') return 'Trait';
    return trait.displayName || trait.n || trait.id || 'Trait';
  }

  function getTraitDesc(trait) {
    if (!trait || typeof trait !== 'object') return 'No description available.';
    return trait.description || trait.d || trait.summary || 'No description available.';
  }

  function getTraitMech(trait) {
    if (!trait || typeof trait !== 'object') return '';
    if (typeof trait.m === 'string' && trait.m) return trait.m;
    var mech = trait.mechanics;
    if (!mech || typeof mech !== 'object') return '';
    var parts = [mech.actionType, mech.usesPerRest, mech.damage].filter(Boolean);
    return parts.join(' \u00b7 ');
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

  function renderPreviewTile(draft) {
    var identity = draft && draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
    var combo = resolveComboPortrait(draft);
    var hasComboSelections = !!(
      draft
      && draft.species
      && String(draft.species.id || draft.species.name || '').trim()
      && draft.class
      && String(draft.class.id || '').trim()
    );
    var finalPortrait = hasComboSelections ? combo : '';
    var markup = finalPortrait
      ? '<img class="avatar-render portrait" src="' + escAttr(finalPortrait) + '" alt="Preview portrait" style="width:100%;height:100%;object-fit:contain;object-position:center;" />'
      : '<div style="font-size:.62rem;color:rgba(180,170,150,.92);line-height:1.5;text-align:center;padding:0 6px;">Portrait preview will appear once species and class are selected.</div>';
    return '<div style="margin:10px 0 14px;padding:9px 12px;border:1px solid rgba(201,168,76,.16);border-radius:10px;background:rgba(7,10,14,.58);display:flex;gap:12px;align-items:center;">'
      + '<div style="width:62px;height:62px;border-radius:10px;overflow:hidden;background:rgba(255,255,255,.04);border:1px solid rgba(201,168,76,.24);display:flex;align-items:center;justify-content:center;">' + markup + '</div>'
      + '<div style="font-size:.66rem;color:rgba(231,223,206,.92);line-height:1.45;"><div style="font-family:var(--cb-font-display);font-size:.72rem;color:#E8C97A;">Live Portrait Preview</div><div>' + escHtml(combo ? 'Combo art active for current species/class.' : (hasComboSelections ? 'No combo portrait was found for this species/class yet.' : 'Combo art will appear when species + class are set.')) + '</div></div>'
      + '</div>';
  }

  function showSpeciesDetailPanel(root, speciesId, currentDraft) {
    var entries = getSpeciesCatalogEntries();
    var entry = null;
    for (var i = 0; i < entries.length; i++) {
      if (normalizeId(entries[i].id) === normalizeId(speciesId)) { entry = entries[i]; break; }
    }
    if (!entry) return;

    var panel = root.querySelector('#builder-species-detail');
    if (!panel) return;

    var color = SPECIES_COLORS[normalizeId(entry.id)] || DEFAULT_SPECIES_COLOR;
    var icon = entry.icon || SPECIES_ICONS[normalizeId(entry.id)] || DEFAULT_SPECIES_ICON;
    var traits = Array.isArray(entry.traits) ? entry.traits : [];

    // Combo portrait preview using the resolved species + current class + gender
    var speciesPortraitHtml = '';
    var portraitLib = global.CasualDnDPortraitLibrary;
    if (portraitLib && typeof portraitLib.resolve === 'function') {
      var previewDraft = currentDraft && typeof currentDraft === 'object' ? currentDraft : {};
      var previewUrl = portraitLib.resolve({
        speciesId: speciesId,
        classId: previewDraft && previewDraft.class && previewDraft.class.id,
        gender: previewDraft && previewDraft.identity && previewDraft.identity.gender,
      });
      if (previewUrl) {
        speciesPortraitHtml = '<div style="float:right;width:72px;height:80px;border-radius:10px;overflow:hidden;' +
          'border:1px solid rgba(201,168,76,0.25);margin:0 0 8px 10px;flex-shrink:0;">' +
          '<img src="' + escAttr(previewUrl) + '" style="width:100%;height:100%;object-fit:contain;object-position:center;background:rgba(4,8,12,.45);" alt="Hero preview"></div>';
      }
    }

    var traitCards = traits.map(function toTraitCard(trait) {
      if (!trait || typeof trait !== 'object') return '';
      var mechStr = getTraitMech(trait);
      return [
        '<div class="sd-trait">',
        '<div class="sd-trait-name">\u25C6 ' + escHtml(getTraitName(trait)) + '</div>',
        '<div class="sd-trait-desc">' + escHtml(getTraitDesc(trait)) + '</div>',
        mechStr ? '<div class="sd-trait-mech">' + escHtml(mechStr) + '</div>' : '',
        '</div>',
      ].join('');
    }).join('');

    panel.innerHTML = [
      '<div class="sd-header">',
      speciesPortraitHtml,
      '<div>',
      '<div class="sd-name" style="color:' + escAttr(color) + '">' + escHtml(icon) + ' ' + escHtml(entry.name) + '</div>',
      '<div class="sd-meta">',
      entry.speed > 0 ? '<span class="sc-badge speed">\u26A1 ' + escHtml(entry.speed) + ' ft walk</span>' : '',
      entry.darkvision > 0 ? '<span class="sc-badge darkvision">\uD83D\uDC41 Darkvision ' + escHtml(entry.darkvision) + ' ft</span>' : '',
      entry.size ? '<span class="sc-badge size">' + escHtml(entry.size) + '</span>' : '',
      '</div>',
      '</div>',
      '<div style="font-size:0.7rem;color:var(--cb-text-secondary);font-style:italic;max-width:300px;line-height:1.6">' + escHtml(entry.flavorText || '') + '</div>',
      '</div>',
      '<div class="sd-traits-grid">',
      traitCards || '<div class="sd-trait"><div class="sd-trait-desc">No traits defined.</div></div>',
      '</div>',
    ].join('');

    panel.className = 'species-detail visible';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  registerStep({
    id: 'species',
    label: 'Species',
    render: function renderSpeciesStep(context) {
      ensureBuilderStyles();
      ensureCatalogLoaded();
      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var species = draft.species && typeof draft.species === 'object' ? draft.species : {};
      var selectedId = String(species.id || '').trim();
      var entries = getSpeciesCatalogEntries();

      // --- screen header ---
      var header = [
        '<div class="screen-header">',
        '<div class="screen-title">Choose Your Species</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Your ancestry shapes your innate traits, senses, and place in the world. <button class="help-btn" data-help-topic="species">?</button></div>',
        '</div>',
      ].join('');

      // --- hidden input ---
      var hiddenInput = '<input type="hidden" data-builder-path="species.id" value="' + escAttr(selectedId) + '" />';

      // --- species cards ---
      var cards = entries.map(function toCard(entry) {
        var nid = normalizeId(entry.id);
        var isSelected = nid === normalizeId(selectedId);
        var color = SPECIES_COLORS[nid] || DEFAULT_SPECIES_COLOR;
        var icon = entry.icon || SPECIES_ICONS[nid] || DEFAULT_SPECIES_ICON;
        var traitPreview = Array.isArray(entry.traits) ? entry.traits.slice(0, 3) : [];

        return [
          '<div class="species-card' + (isSelected ? ' selected' : '') + '" data-species-id="' + escAttr(entry.id) + '">',
          '<div class="sc-selected-check">\u2713</div>',
          '<div class="sc-icon" style="border-color:' + escAttr(color) + '33;background:' + escAttr(color) + '11">' + escHtml(icon) + '</div>',
          '<div class="sc-name">' + escHtml(entry.name) + '</div>',
          '<div class="sc-badges">',
          entry.speed > 0 ? '<span class="sc-badge speed">\u26A1 ' + escHtml(entry.speed) + ' ft</span>' : '',
          entry.darkvision > 0 ? '<span class="sc-badge darkvision">\uD83D\uDC41 ' + escHtml(entry.darkvision) + ' ft</span>' : '',
          entry.size ? '<span class="sc-badge size">' + escHtml(entry.size) + '</span>' : '',
          '</div>',
          '<div class="sc-flavor">' + escHtml(entry.flavorText || 'No lore text available for this species yet.') + '</div>',
          '<div class="sc-traits">',
          traitPreview.map(function toTrait(trait) {
            return '<div class="sc-trait">' + escHtml(getTraitName(trait)) + '</div>';
          }).join(''),
          '</div>',
          '</div>',
        ].join('');
      }).join('');

      // --- detail panel placeholder ---
      var detailPanel = '<div class="species-detail" id="builder-species-detail"></div>';

      // --- lineage field ---
      var lineageField = [
        '<div class="field"><label>Lineage / Heritage Notes (optional)</label>',
        '<input type="text" data-builder-path="species.lineage" value="' + escAttr(species.lineage || '') + '" maxlength="80" placeholder="High Elf, Hill Dwarf, etc." /></div>',
      ].join('');

      return [
        header,
        hiddenInput,
        renderPreviewTile(draft),
        '<div class="species-grid">' + cards + '</div>',
        detailPanel,
        lineageField,
      ].join('');
    },
    bind: function bindSpeciesStep(root, context) {
      // 1. Card click handler
      var bindDraft = context && context.draft || {};
      root.querySelectorAll('.species-card').forEach(function(card) {
        card.addEventListener('click', function() {
          var id = card.dataset.speciesId;
          var hiddenInput = root.querySelector('[data-builder-path="species.id"]');
          if (hiddenInput) hiddenInput.value = id;
          if (context && typeof context.onSetField === 'function') {
            context.onSetField(['species', 'id'], id);
          }
          root.querySelectorAll('.species-card').forEach(function(c) {
            var cardId = c && c.dataset ? c.dataset.speciesId : '';
            var selected = normalizeId(cardId) === normalizeId(id);
            c.classList.toggle('selected', selected);
          });
          var currentDraft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
          var nextDraft = Object.assign({}, currentDraft, {
            species: Object.assign({}, currentDraft.species || {}, { id: id }),
          });
          showSpeciesDetailPanel(root, id, nextDraft);
        });
      });
      // 2. Auto-show detail for already-selected species
      var currentId = bindDraft.species && bindDraft.species.id;
      if (currentId) {
        showSpeciesDetailPanel(root, currentId, bindDraft);
      }
      // 3. Help button
      var helpBtn = root.querySelector('.help-btn[data-help-topic]');

      if (helpBtn) {
        helpBtn.addEventListener('click', function() {
          if (typeof global.showHelp === 'function') {
            global.showHelp(helpBtn.dataset.helpTopic);
          }
        });
      }
    },
    getCatalog: function getCatalog() {
      return {
        catalogVersion: 1,
        entries: getSpeciesCatalogEntries(),
      };
    },
  });
})(window);
