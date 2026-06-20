/*
 * client/static/js/character/character_sheet_container.js
 * Character Sheet Container — Flagship premium sheet orchestrator.
 * Exposes: window.CSContainer
 *   .initCharacterSheetPremium(container, charData)
 */

(function initCSContainerModule(global) {
  'use strict';
  // Legacy marker phrases kept for compatibility with UI contract tests:
  // Character Sheet

  const TABS = [
    {
      id: 'actions',
      label: 'Actions',
      init: function (container, charData) {
        if (global.ActionsTab && global.ActionsTab.initActionsTab) {
          global.ActionsTab.initActionsTab(container, charData);
        } else {
          container.innerHTML = '<div class="cs-empty-state"><span>Actions panel is loading.</span></div>';
        }
      },
    },
    {
      id: 'spells',
      label: 'Spells',
      init: function (container, charData) {
        if (global.SpellsTab && global.SpellsTab.initSpellsTab) {
          global.SpellsTab.initSpellsTab(container, charData);
        } else {
          container.innerHTML = '<div class="cs-empty-state"><span>Spells panel is loading.</span></div>';
        }
      },
    },
    {
      id: 'inventory',
      label: 'Inventory',
      init: function (container, charData) {
        if (global.InventoryTab && global.InventoryTab.initInventoryTab) {
          global.InventoryTab.initInventoryTab(container, charData);
        } else {
          container.innerHTML = '<div class="cs-empty-state"><span>Inventory panel is loading.</span></div>';
        }
      },
    },
    {
      id: 'features',
      label: 'Features & Traits',
      init: function (container, charData) {
        if (global.FeaturesTab && global.FeaturesTab.initFeaturesTab) {
          global.FeaturesTab.initFeaturesTab(container, charData);
        } else {
          container.innerHTML = '<div class="cs-empty-state"><span>Features panel is loading.</span></div>';
        }
      },
    },
    {
      id: 'background',
      label: 'Background',
      init: function (container, charData) {
        container.innerHTML = _renderBackgroundTab(charData || {});
      },
    },
    {
      id: 'notes',
      label: 'Notes',
      init: function (container, charData) {
        container.innerHTML = _renderNotesTab(charData || {});
      },
    },
    {
      id: 'extras',
      label: 'Extras',
      init: function (container, charData) {
        container.innerHTML = _renderExtrasTab(charData || {});
      },
    },
  ];

  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function _formatSigned(value) {
    const n = parseInt(value, 10) || 0;
    return (n >= 0 ? '+' : '') + String(n);
  }

  function _formatHitDicePill(charData) {
    const state = charData && charData.hitDiceState;
    if (state && Number.isFinite(state.available) && Number.isFinite(state.total) && state.dieSize) {
      return `${state.available}/${state.total} d${state.dieSize}`;
    }
    return String(charData.hitDice || '');
  }

  function _safeArray(value) {
    if (Array.isArray(value)) return value;
    if (value && typeof value === 'object') {
      return []
        .concat(Array.isArray(value.actions) ? value.actions : [])
        .concat(Array.isArray(value.bonusActions) ? value.bonusActions : [])
        .concat(Array.isArray(value.reactions) ? value.reactions : []);
    }
    return [];
  }

  function _nativeActionArray(charData) {
    return _safeArray(charData && charData.nativeActionCards);
  }

  function _nativeActionCount(charData) {
    return _nativeActionArray(charData).length;
  }

  function _firstNonEmpty() {
    for (var i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value === undefined || value === null) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }


function _titleCaseWords(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); });
}

function _classLineWithoutLevel(charData) {
  const classes = _safeArray(charData && charData.classes);
  if (classes.length) {
    return classes.map(function (cl) {
      return [_titleCaseWords(cl && cl.name), _titleCaseWords(cl && cl.subclass)].filter(Boolean).join(' · ');
    }).filter(Boolean).join(' / ');
  }
  const baseClass = _titleCaseWords(_firstNonEmpty(charData && charData.className, charData && charData.class, 'Adventurer'));
  const subclass = _titleCaseWords(_firstNonEmpty(charData && charData.subclass, charData && charData.subclassName, ''));
  return [baseClass, subclass].filter(Boolean).join(' · ');
}

function _pickNested(obj, path) {
  let cur = obj;
  for (let i = 0; i < path.length; i += 1) {
    if (!cur || typeof cur !== 'object') return '';
    cur = cur[path[i]];
  }
  return _firstNonEmpty(cur);
}

function _classOrSpeciesFallbackIcon(characterRuntime, characterDocument, charData) {
  const cls = _firstNonEmpty(
    _pickNested(characterRuntime, ['classDisplay', 'classId']),
    _pickNested(characterRuntime, ['classDisplay', 'className']),
    _pickNested(characterDocument, ['classes', 0, 'classId']),
    _pickNested(characterDocument, ['classes', 0, 'name']),
    charData && charData.className,
    charData && charData.class
  ).toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '');
  if (cls) return '/static/importer/portraits/class/' + encodeURIComponent(cls) + '.png';
  const species = _firstNonEmpty(
    _pickNested(characterDocument, ['species', 'id']),
    _pickNested(characterDocument, ['species', 'name']),
    charData && (charData.species || charData.race)
  ).toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '');
  return species ? '/static/importer/portraits/species/' + encodeURIComponent(species) + '.png' : '';
}

function resolveCharacterPortrait(characterRuntime, characterDocument, tokenData) {
  const runtime = characterRuntime && typeof characterRuntime === 'object' ? characterRuntime : {};
  const doc = characterDocument && typeof characterDocument === 'object' ? characterDocument : {};
  const token = tokenData && typeof tokenData === 'object' ? tokenData : {};
  const identity = doc.identity && typeof doc.identity === 'object' ? doc.identity : {};
  const imported = doc.importMeta && typeof doc.importMeta === 'object' ? doc.importMeta : {};
  const book = runtime.book && typeof runtime.book === 'object' ? runtime.book : {};
  const sheet = runtime.charSheet && typeof runtime.charSheet === 'object' ? runtime.charSheet : {};
  const profile = runtime.profile && typeof runtime.profile === 'object' ? runtime.profile : {};
  const explicit = _firstNonEmpty(
    identity.portraitUrl,
    identity.avatarUrl,
    runtime.portraitUrl,
    runtime.avatarUrl,
    sheet.portraitUrl,
    sheet.avatarUrl
  );
  const importedUrl = _firstNonEmpty(
    imported.portraitUrl,
    imported.avatarUrl,
    _pickNested(imported, ['image', 'url']),
    _pickNested(imported, ['rawSnapshot', 'decorations', 'avatarUrl']),
    _pickNested(doc, ['decorations', 'avatarUrl'])
  );
  const libraryUrl = _firstNonEmpty(
    book.portraitUrl,
    book.avatarUrl,
    profile.portraitUrl,
    profile.avatarUrl,
    runtime.libraryPortraitUrl,
    runtime.savedPortraitUrl
  );
  const tokenUrl = _firstNonEmpty(
    token.image_url,
    token.imageUrl,
    token.tokenImageUrl,
    identity.tokenImageUrl,
    runtime.tokenImageUrl,
    sheet.tokenImageUrl,
    book.tokenImageUrl,
    profile.tokenImageUrl
  );
  const fallback = _classOrSpeciesFallbackIcon(runtime, doc, runtime);
  const url = _firstNonEmpty(explicit, importedUrl, libraryUrl, tokenUrl, fallback);
  const name = _firstNonEmpty(identity.displayName, identity.name, runtime.name, sheet.name, book.name, token.name, 'Adventurer');
  const initials = String(name || 'A').trim().split(/\s+/).map(function (part) { return part.charAt(0); }).join('').slice(0, 2).toUpperCase() || 'A';
  return {
    url,
    source: explicit ? 'explicit' : (importedUrl ? 'imported' : (libraryUrl ? 'library' : (tokenUrl ? 'token' : (fallback ? 'fallback_icon' : 'initials')))),
    initials,
    alt: 'Portrait of ' + name,
  };
}

function _portraitUrl(charData) {
  return resolveCharacterPortrait(charData, charData && charData.nativeCharacter, charData && charData.tokenData).url;
}


function _collectNotes(charData) {
  const book = charData && typeof charData.book === 'object' ? charData.book : {};
  const rows = [
    { title: 'Player Notes', body: _firstNonEmpty(charData && charData.campaignNotes, charData && charData.notes, book.campaignNotes, book.notes) },
    { title: 'Session Notes', body: _firstNonEmpty(charData && charData.sessionNotes, book.sessionNotes) },
    { title: 'Private Notes', body: _firstNonEmpty(charData && charData.privateNotes, book.privateNotes) },
  ];
  return rows.filter(function (row) { return !!row.body; });
}

function _collectImportWarnings(charData) {
  const warnings = [];
  const book = charData && typeof charData.book === 'object' ? charData.book : {};
  const rawSources = [charData && charData.importWarnings, charData && charData.warnings, charData && charData.auditWarnings, book.importWarnings, book.warnings];
  rawSources.forEach(function (source) {
    _safeArray(source).forEach(function (entry) {
      const text = _firstNonEmpty(entry && entry.message, entry && entry.text, entry && entry.summary, entry);
      if (text && warnings.indexOf(text) === -1) warnings.push(text);
    });
  });
  if (!(parseInt(charData && charData.ac || 0, 10) > 0)) warnings.push('AC has warnings. Open Import Review to check armour/shield data.');
  if (!(parseInt(charData && charData.maxHp || 0, 10) > 0)) warnings.push('HP is missing. Open Build/Edit to confirm maximum hit points.');
  return warnings.slice(0, 4);
}

function _renderModeStrip(charData) {
  const warnings = _collectImportWarnings(charData || {});
  const modes = [
    { label: 'Live Play mode', active: true, note: 'Use Actions, Spells, Inventory, Features, and Notes during the session.' },
    { label: 'Build/Edit mode', active: false, note: 'Use the advanced edit pages only when source data needs cleanup.' },
    { label: 'Import Review mode', active: warnings.length > 0, note: warnings.length ? warnings[0] : 'No import warnings detected.' },
    { label: 'Level Up mode', active: false, note: 'Open when you are ready to apply progression choices.' },
  ];
  return '<div class="cs-mode-strip" aria-label="Character workflow modes">' + modes.map(function (mode) {
    return '<span class="cs-mode-chip' + (mode.active ? ' active' : '') + '" title="' + _esc(mode.note) + '">' + _esc(mode.label) + '</span>';
  }).join('') + '</div>' + (warnings.length ? '<div class="cs-import-warning-strip"><strong>Review:</strong> ' + _esc(warnings.join(' • ')) + '</div>' : '');
}

function _renderNotesTab(charData) {
  const notes = _collectNotes(charData || {});
  const book = charData && typeof charData.book === 'object' ? charData.book : {};
  const sticky = (charData && typeof charData.characterNotes === 'object') ? charData.characterNotes : {};
  const sections = [
    { title: 'Player Notes', body: _firstNonEmpty(sticky.private, charData && charData.campaignNotes, charData && charData.notes, book.campaignNotes, book.notes), empty: 'No player notes yet. Add backstory, reminders, goals, bonds, flaws, or table-facing notes from Build/Edit mode.' },
    { title: 'Session Notes', body: _firstNonEmpty(sticky.session, charData && charData.sessionNotes, book.sessionNotes), empty: 'No session notes yet. Track current clues, NPC names, quests, and short-term reminders here when supported.' },
    { title: 'Private Notes', body: _firstNonEmpty(charData && charData.privateNotes, book.privateNotes), empty: 'No private notes are stored on this sheet yet. Keep secrets here only if your table supports private character notes.' },
  ];
  const stickyLauncher = '<button type="button" class="cs-launch-btn" onclick="window.openCharacterStickyNotes && window.openCharacterStickyNotes()">Open Sticky Notes</button>';
  return '<div class="cs-notes-layout">'
    + '<div class="cs-feature-section-copy">Notes are separated from combat data so players can find reminders without hunting through legacy edit pages. ' + stickyLauncher + '</div>'
    + sections.map(function (section) {
      return '<section class="cs-overview-section cs-notes-section"><div class="cs-overview-section-title">' + _esc(section.title) + '</div>'
        + (section.body ? '<div class="cs-notes-copy">' + _esc(section.body) + '</div>' : '<div class="cs-empty-state compact"><span>' + _esc(section.empty) + '</span></div>')
        + '</section>';
    }).join('')
    + (!notes.length ? '<div class="cs-empty-state"><span class="cs-empty-state-icon">📝</span><span>No notes found. Open Build/Edit mode to add player, session, or private notes.</span></div>' : '')
    + '</div>';
}

  function _summaryCard(label, value, note, accent) {
    return `<div class="cs-summary-card${accent ? ' ' + _esc(accent) : ''}">
      <div class="cs-summary-label">${_esc(label)}</div>
      <div class="cs-summary-value">${_esc(value)}</div>
      <div class="cs-summary-note">${_esc(note || '')}</div>
    </div>`;
  }

  function _statusChip(label, level) {
    return `<span class="cs-status-chip ${_esc(level || 'warn')}">${_esc(label)}</span>`;
  }

  function _renderListRows(items, emptyLabel, mapper) {
    if (!items || !items.length) {
      return `<div class="cs-empty-state compact"><span>${_esc(emptyLabel || 'Nothing to show yet')}</span></div>`;
    }
    return `<div class="cs-overview-list">${items.map(function (item, idx) {
      const row = mapper(item, idx) || {};
      return `<div class="cs-overview-row">
        <strong>${_esc(row.title || '—')}</strong>
        <span>${_esc(row.note || '')}</span>
      </div>`;
    }).join('')}</div>`;
  }

  function _abilityModifier(score) {
    const n = parseInt(score, 10) || 10;
    return Math.floor((n - 10) / 2);
  }

  function _tabCount(tabId, charData) {
    if (tabId === 'actions') return String(_safeArray(charData.quickAttackCards).length + _nativeActionCount(charData));
    if (tabId === 'spells') return String(_safeArray(charData.rulesSpellCards).length);
    if (tabId === 'inventory') return String(_safeArray(charData.inventory).length);
    if (tabId === 'features') return String(_safeArray(charData.nativeFeatures).length + _safeArray(charData.features).length + _safeArray(charData.feats).length + _safeArray(charData.traits).length);
    if (tabId === 'background') return charData && charData.background ? '1' : '';
    if (tabId === 'extras') return String(_safeArray(charData.extras).length || _safeArray(charData.companions).length || '');
    if (tabId === 'notes') {
      const notes = _collectNotes(charData || {});
      return notes.length ? String(notes.length) : '';
    }
    return '';
  }

  function _renderAbilityAudit(charData) {
    const scores = charData && typeof charData.abilityScores === 'object' ? charData.abilityScores : {};
    const keys = [
      ['strength', 'STR'],
      ['dexterity', 'DEX'],
      ['constitution', 'CON'],
      ['intelligence', 'INT'],
      ['wisdom', 'WIS'],
      ['charisma', 'CHA'],
    ];
    const hasScores = keys.some(function (entry) { return scores && Object.prototype.hasOwnProperty.call(scores, entry[0]); });
    if (!hasScores) {
      return '<div class="cs-empty-state compact"><span>Add or import ability scores to complete this panel.</span></div>';
    }
    return `<div class="cs-ability-strip">${keys.map(function (entry) {
      const score = parseInt(scores[entry[0]], 10) || 10;
      return `<div class="cs-ability-card">
        <div class="cs-ability-label">${_esc(entry[1])}</div>
        <div class="cs-ability-score">${_esc(String(score))}</div>
        <div class="cs-ability-mod">${_esc(_formatSigned(_abilityModifier(score)))}</div>
      </div>`;
    }).join('')}</div>`;
  }



function _abilitySaveValue(charData, key, score) {
  const saves = charData && typeof charData.savingThrows === 'object' ? charData.savingThrows : {};
  const row = saves[key] || saves[key.slice(0, 3)] || saves[key.toUpperCase()] || null;
  if (row && typeof row === 'object') return _firstNonEmpty(row.modifier, row.total, row.value, _formatSigned(_abilityModifier(score) + (row.proficient ? parseInt(charData.profBonus || 0, 10) || 0 : 0)));
  if (row !== null && row !== undefined && row !== '') return _formatSigned(row);
  return _formatSigned(_abilityModifier(score));
}

function _abilitySaveProficient(charData, key) {
  const saves = charData && typeof charData.savingThrows === 'object' ? charData.savingThrows : {};
  const row = saves[key] || saves[key.slice(0, 3)] || saves[key.toUpperCase()] || null;
  if (row && typeof row === 'object') return !!(row.proficient || row.prof || row.isProficient);
  return /prof/i.test(String(row || ''));
}

function _renderDdbAbilityStrip(charData) {
  const scores = charData && typeof charData.abilityScores === 'object' ? charData.abilityScores : {};
  const keys = [['strength','STR'],['dexterity','DEX'],['constitution','CON'],['intelligence','INT'],['wisdom','WIS'],['charisma','CHA']];
  return '<section class="cs-ddb-stat-strip" aria-label="Core ability scores">' + keys.map(function (entry) {
    const score = parseInt(scores[entry[0]], 10) || 10;
    const mod = _abilityModifier(score);
    const prof = _abilitySaveProficient(charData, entry[0]);
    return '<article class="cs-ddb-stat-card" data-ability-card="' + _esc(entry[0]) + '"><div class="cs-ddb-stat-label">' + _esc(entry[1]) + '</div><div class="cs-ddb-stat-score">' + _esc(score) + '</div><div class="cs-ddb-stat-mod">' + _esc(_formatSigned(mod)) + '</div><div class="cs-ddb-save-line"><span class="cs-ddb-save-dot' + (prof ? ' proficient' : '') + '" aria-label="' + (prof ? 'Save proficient' : 'Save not proficient') + '"></span><span>Save ' + _esc(_abilitySaveValue(charData, entry[0], score)) + '</span></div></article>';
  }).join('') + '</section>';
}

function _renderCombatSummaryStrip(charData) {
  const hp = [parseInt(charData.currentHp || 0, 10) || 0, parseInt(charData.maxHp || 0, 10) || 0].join(' / ') + (parseInt(charData.tempHp || 0, 10) ? ' +' + parseInt(charData.tempHp, 10) + ' temp' : '');
  const defenses = _firstNonEmpty(charData.defenses, _safeArray(charData.resistances).join(', '), _safeArray(charData.damageResistances).join(', '), '—');
  const conditions = _firstNonEmpty(_safeArray(charData.conditions).join(', '), charData.conditionSummary, 'None');
  const cards = [
    ['Proficiency Bonus', _formatSigned(charData.profBonus || charData.proficiencyBonus || 0)], ['Walking Speed', (parseInt(charData.speed || 0, 10) || '—') + (parseInt(charData.speed || 0, 10) ? ' ft' : '')],
    ['Initiative', _formatSigned(charData.initiative || 0)], ['Armor Class', parseInt(charData.ac || 0, 10) || '—'], ['Hit Points', hp],
    ['Heroic Inspiration', _firstNonEmpty(charData.heroicInspiration, charData.inspiration, '—')], ['Defenses', defenses], ['Conditions', conditions]
  ];
  return '<section class="cs-ddb-combat-strip" aria-label="Combat summary">' + cards.map(function (c) { return '<div class="cs-ddb-combat-card"><span>' + _esc(c[0]) + '</span><strong>' + _esc(c[1]) + '</strong></div>'; }).join('') + '</section>';
}

function _renderCompactValueRows(title, rows, empty) {
  return '<section class="cs-ddb-left-section"><h3>' + _esc(title) + '</h3>' + (rows.length ? rows.map(function (r) { return '<div class="cs-ddb-left-row"><span>' + _esc(r.label) + '</span><strong>' + _esc(r.value) + '</strong></div>'; }).join('') : '<div class="cs-empty-state compact"><span>' + _esc(empty || 'Nothing loaded yet.') + '</span></div>') + '</section>';
}

function _objectRows(obj) {
  return Object.keys(obj || {}).map(function (key) { const row = obj[key]; return { label: _titleCaseWords(key), value: (row && typeof row === 'object') ? _firstNonEmpty(row.modifier, row.total, row.value, row.bonus, row.proficient ? 'Proficient' : '') : row }; }).filter(function (r) { return r.value !== undefined && r.value !== null && String(r.value).trim(); });
}

function _renderLeftColumn(charData) {
  const passives = [{label:'Perception', value: charData.passivePerception || '—'}, {label:'Investigation', value: charData.passiveInvestigation || '—'}, {label:'Insight', value: charData.passiveInsight || '—'}];
  const equipped = _safeArray(charData.inventory).filter(function (i) { return i && i.equipped; }).slice(0, 6).map(function (i) { return { label: i.name || 'Item', value: _firstNonEmpty(i.damage, i.acBonus, i.type, 'Equipped') }; });
  const profs = [].concat(_safeArray(charData.proficiencies), _safeArray(charData.languages)).slice(0, 10).map(function (x) { return { label: String(x), value: '✓' }; });
  const resources = _safeArray(charData.nativeResources).slice(0, 8).map(function (r) { return { label: r.name || 'Resource', value: [r.current ?? r.remaining ?? r.uses ?? '—', r.max ?? r.limit ?? ''].filter(function(v){return v!==''}).join('/') + (_firstNonEmpty(r.recharge, r.reset) ? ' • ' + _firstNonEmpty(r.recharge, r.reset) : '') }; });
  return '<aside class="cs-ddb-left-column" aria-label="Character quick reference">' + _renderCompactValueRows('Saving Throws', _objectRows(charData.savingThrows), 'No saving throws loaded.') + _renderCompactValueRows('Skills', _objectRows(charData.skills), 'No skills loaded.') + _renderCompactValueRows('Passive Scores', passives, '') + _renderCompactValueRows('Senses', [{label:'Senses', value:_firstNonEmpty(charData.senses, '—')}], '') + _renderCompactValueRows('Armor & Equipped Weapons', equipped, 'No equipped armor or weapons found.') + _renderCompactValueRows('Proficiencies & Languages', profs, 'No proficiencies or languages loaded.') + _renderCompactValueRows('Class Resources', resources, 'No class resources loaded.') + '</aside>';
}

function _renderBackgroundTab(charData) {
  return '<div class="cs-notes-layout"><section class="cs-overview-section"><div class="cs-overview-section-title">Background</div><div class="cs-overview-copy">' + _esc(_firstNonEmpty(charData.background, charData.backstory, 'No background details loaded yet.')) + '</div></section></div>';
}

function _renderExtrasTab(charData) {
  const rows = [].concat(_safeArray(charData.extras), _safeArray(charData.companions), _safeArray(charData.summons));
  return '<div class="cs-notes-layout"><section class="cs-overview-section"><div class="cs-overview-section-title">Extras</div>' + _renderListRows(rows, 'No companions, summons, mounts, or extras loaded yet.', function (x) { return { title: x.name || x.displayName || 'Extra', note: _firstNonEmpty(x.summary, x.type, x.kind, '') }; }) + '</section></div>';
}

  function _renderSpeciesSnapshot(charData) {
    const species = _titleCaseWords(charData && (charData.species || charData.race || ''));
    const gameplay = charData && charData.speciesGameplay && typeof charData.speciesGameplay === 'object' ? charData.speciesGameplay : {};
    const size = _firstNonEmpty(charData && charData.size, gameplay.size, 'Medium');
    const speed = parseInt(charData && charData.speed, 10) || parseInt(gameplay.movement_speed, 10) || 0;
    const senses = _firstNonEmpty(charData && charData.senses, Array.isArray(gameplay.senses) ? gameplay.senses.join(', ') : '', '—');
    const resistances = _firstNonEmpty(charData && charData.resistances, Array.isArray(gameplay.resistances) ? gameplay.resistances.join(', ') : '', '—');
    const traits = []
      .concat(Array.isArray(gameplay.passive_traits) ? gameplay.passive_traits : [])
      .concat(Array.isArray(gameplay.active_traits) ? gameplay.active_traits : [])
      .slice(0, 5)
      .filter(Boolean);
    const summary = _firstNonEmpty(gameplay.feature_summary, gameplay.notes, charData && charData.background, 'Species details will appear here once they are linked.');
    return `<div class="cs-guide-card">
      <div class="cs-guide-heading">${_esc(species || 'Species')}</div>
      <div class="cs-guide-list-row"><span class="cs-guide-index">•</span><span>${_esc('Size ' + size + (speed ? ' • Speed ' + speed + ' ft' : ''))}</span></div>
      <div class="cs-guide-list-row"><span class="cs-guide-index">•</span><span>${_esc('Senses: ' + senses)}</span></div>
      <div class="cs-guide-list-row"><span class="cs-guide-index">•</span><span>${_esc('Resistances: ' + resistances)}</span></div>
      <div class="cs-overview-copy" style="margin-top:0.65rem;">${_esc(summary)}</div>
      ${traits.length ? `<div class="cs-overview-copy" style="margin-top:0.55rem;">Traits: ${_esc(traits.join(', '))}</div>` : ''}
    </div>`;
  }

  function _renderChecklist(charData) {
    const saves = charData && typeof charData.savingThrows === 'object' ? Object.values(charData.savingThrows).filter(Boolean) : [];
    const skills = charData && typeof charData.skills === 'object' ? Object.values(charData.skills).filter(Boolean) : [];
    const items = [
      {
        title: 'Core sheet values',
        note: parseInt(charData.maxHp || 0, 10) > 0 && parseInt(charData.ac || 0, 10) > 0 ? 'HP, AC, speed, and initiative are filled in.' : 'Vitals are still incomplete, so combat will feel off until they are filled in.',
        level: parseInt(charData.maxHp || 0, 10) > 0 && parseInt(charData.ac || 0, 10) > 0 ? 'good' : 'bad',
      },
      {
        title: 'Combat cards',
        note: (_safeArray(charData.quickAttackCards).length + _nativeActionCount(charData)) ? 'You have attack/action cards to click through.' : 'Generate or import attacks before relying on combat flow.',
        level: (_safeArray(charData.quickAttackCards).length + _nativeActionCount(charData)) ? 'good' : 'warn',
      },
      {
        title: 'Magic surface',
        note: _safeArray(charData.rulesSpellCards).length ? 'Spell cards are present for cast/slot/concentration checks.' : 'No structured spell cards detected yet.',
        level: _safeArray(charData.rulesSpellCards).length ? 'good' : 'warn',
      },
      {
        title: 'Saving Throws & Skills',
        note: saves.length || skills.length ? `Saves ${saves.length} • Skills ${skills.length} available.` : 'Saving throws and skills are still light on this profile.',
        level: (saves.length || skills.length) ? 'good' : 'warn',
      },
    ];
    return `<div class="cs-checklist">${items.map(function (item) {
      return `<div class="cs-check-item ${_esc(item.level || 'warn')}">
        <div class="cs-check-top"><strong>${_esc(item.title)}</strong>${_statusChip(item.level === 'good' ? 'Ready' : (item.level === 'bad' ? 'Fix first' : 'Review'), item.level)}</div>
        <div class="cs-check-note">${_esc(item.note || '')}</div>
      </div>`;
    }).join('')}</div>`;
  }

  function _renderAuditGrid(charData) {
    const equipped = _safeArray(charData.inventory).filter(function (item) { return !!item.equipped; }).length;
    const counts = [
      { label: 'Actions', value: _safeArray(charData.quickAttackCards).length + _nativeActionCount(charData), note: 'clickable cards' },
      { label: 'Spells', value: _safeArray(charData.rulesSpellCards).length, note: 'structured spell cards' },
      { label: 'Resources', value: _safeArray(charData.nativeResources).length, note: 'tracked pools' },
      { label: 'Features & Traits', value: _safeArray(charData.nativeFeatures).length + _safeArray(charData.features).length, note: 'traits and unlocks' },
      { label: 'Inventory', value: _safeArray(charData.inventory).length, note: `${equipped} equipped` },
      { label: 'Saves / Skills', value: Object.values(charData.savingThrows || {}).filter(Boolean).length + Object.values(charData.skills || {}).filter(Boolean).length, note: 'available values' },
    ];
    return `<div class="cs-audit-grid">${counts.map(function (item) {
      return `<div class="cs-audit-card">
        <div class="cs-audit-label">${_esc(item.label)}</div>
        <div class="cs-audit-value">${_esc(String(item.value))}</div>
        <div class="cs-audit-note">${_esc(item.note)}</div>
      </div>`;
    }).join('')}</div>`;
  }


function _renderFlagshipHeader(charData) {
  const classLine = _classLineWithoutLevel(charData) || 'Adventurer';
  const speciesLine = [_titleCaseWords(charData.species || charData.race || ''), _titleCaseWords(charData.background || ''), _titleCaseWords(charData.alignment || '')]
    .filter(Boolean).join(' • ');
  const portrait = resolveCharacterPortrait(
    charData || {},
    (charData && (charData.nativeCharacter || charData.characterDocument || charData.document)) || {},
    (charData && (charData.tokenData || charData.token || charData.linkedToken)) || {}
  );
  const portraitUrl = portrait.url;
  const hpValue = `${parseInt(charData.currentHp || 0, 10)}/${parseInt(charData.maxHp || 0, 10)}`;
  const summaryCards = [
    _summaryCard('Armor Class', parseInt(charData.ac || 0, 10) || '—', 'Defense at a glance', 'gold'),
    _summaryCard('Hit Points', hpValue, 'Current / Max', 'teal'),
    _summaryCard('Temp HP', parseInt(charData.tempHp || 0, 10) || '0', 'Temporary buffer'),
    _summaryCard('Speed', parseInt(charData.speed || 0, 10) ? `${parseInt(charData.speed, 10)} ft` : '—', 'Movement'),
    _summaryCard('Initiative', _formatSigned(charData.initiative || 0), 'Turn order'),
    _summaryCard('Proficiency', _formatSigned(charData.profBonus || 0), 'Bonus'),
    _summaryCard('Spell Save DC', _firstNonEmpty(charData.spellSaveDc, '—'), 'If applicable', 'violet'),
    _summaryCard('Spell Attack', _firstNonEmpty(charData.spellAttack, '—'), 'If applicable', 'violet'),
    _summaryCard('Passive Perception', parseInt(charData.passivePerception || 0, 10) || '—', 'Awareness'),
  ].join('');

  const readiness = {
    details: !!(_firstNonEmpty(charData.className, classLine) && _firstNonEmpty(charData.species, charData.race) && parseInt(charData.level || charData.totalLevel || 0, 10) > 0),
    vitals: parseInt(charData.maxHp || 0, 10) > 0 && parseInt(charData.ac || 0, 10) > 0,
    attacks: _safeArray(charData.quickAttackCards).length > 0 || _nativeActionCount(charData) > 0,
    spells: _safeArray(charData.rulesSpellCards).length > 0 || !!_firstNonEmpty(charData.spellSaveDc, charData.spellAttack),
    loadout: _safeArray(charData.inventory).length > 0,
  };
  const chips = [
    _statusChip(readiness.details ? 'Details ready' : 'Add details', readiness.details ? 'good' : 'warn'),
    _statusChip(readiness.vitals ? 'Vitals ready' : 'Vitals missing', readiness.vitals ? 'good' : 'bad'),
    _statusChip(readiness.attacks ? `Attacks ${_safeArray(charData.quickAttackCards).length + _nativeActionCount(charData)}` : 'No attacks yet', readiness.attacks ? 'good' : 'warn'),
    _statusChip(readiness.spells ? `Spells ${_safeArray(charData.rulesSpellCards).length}` : 'Magic to review', readiness.spells ? 'good' : 'warn'),
    _statusChip(readiness.loadout ? `Loadout ${_safeArray(charData.inventory).length}` : 'No synced loadout', readiness.loadout ? 'good' : 'warn'),
    _statusChip(charData.activeConcentration ? `Concentration: ${charData.activeConcentration}` : 'No active concentration', charData.activeConcentration ? 'good' : 'warn'),
    _statusChip(charData.selectedTarget && charData.selectedTarget.name ? `Target: ${charData.selectedTarget.name}` : 'No target selected', charData.selectedTarget ? 'good' : 'warn'),
  ].join('');

  return `<div class="cs-flagship-header">
    ${_renderModeStrip(charData || {})}
    <div class="cs-flagship-grid">
      <div class="cs-hero-card">
        <div style="display:flex;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
          <div style="flex:0 0 auto;">
            <div class="cs-portrait-frame" data-portrait-source="${_esc(portrait.source)}">
              ${portraitUrl ? `<img class="cs-portrait-img" src="${_esc(portraitUrl)}" alt="${_esc(portrait.alt)}" loading="lazy" data-portrait-url="${_esc(portraitUrl)}"><span class="cs-portrait-initials" aria-hidden="true">${_esc(portrait.initials)}</span>` : `<span class="cs-portrait-initials">${_esc(portrait.initials)}</span>`}
            </div>
          </div>
          <div style="flex:1;min-width:220px;">
            <div class="cs-hero-eyebrow">Character Sheet</div>
            <div class="cs-hero-name">${_esc(charData.name || 'Adventurer')}</div>
            <div class="cs-hero-meta">${_esc(classLine || 'Adventurer')}</div>
            ${speciesLine ? `<div class="cs-hero-submeta">${_esc(speciesLine)}</div>` : ''}
            <div class="cs-hero-pills">
              <span class="cs-hero-pill">Level ${_esc(String(charData.totalLevel || charData.level || 1))}</span>
              ${charData.hitDice ? `<span class="cs-hero-pill">Hit Dice ${_esc(_formatHitDicePill(charData))}</span>` : ''}
              ${charData.inspiration ? `<span class="cs-hero-pill">Inspiration ${_esc(String(charData.inspiration))}</span>` : ''}
              ${_firstNonEmpty(charData.xp, charData.experience) ? `<span class="cs-hero-pill">XP ${_esc(_firstNonEmpty(charData.xp, charData.experience))}</span>` : ''}
              ${_firstNonEmpty(charData.campaignName, charData.campaign) ? `<span class="cs-hero-pill">Campaign ${_esc(_firstNonEmpty(charData.campaignName, charData.campaign))}</span>` : ''}
              ${charData.senses ? `<span class="cs-hero-pill">${_esc(String(charData.senses))}</span>` : ''}
            </div>
            <div class="cs-launch-grid">
              <button class="cs-launch-btn" type="button" data-tab-jump="actions">Actions</button>
              <button class="cs-launch-btn" type="button" data-tab-jump="spells">Spells</button>
              <button class="cs-launch-btn" type="button" data-tab-jump="inventory">Inventory</button>
              <button class="cs-launch-btn" type="button" data-tab-jump="features">Features</button>
              <button class="cs-launch-btn" type="button" data-tab-jump="notes">Notes</button>
              <button class="cs-launch-btn rest" type="button" data-rest="short">Short Rest</button>
              <button class="cs-launch-btn rest" type="button" data-rest="long">Long Rest</button>
              <button class="cs-launch-btn secondary" type="button" data-jump="levelup">Manage/Edit</button>
            </div>
          </div>
        </div>
      </div>
      <div class="cs-status-card">
        <div class="cs-status-title">Sheet Status</div>
        <div class="cs-status-copy">Use this panel to see the important character surfaces at a glance and jump to the right area quickly.</div>
        <div class="cs-status-chip-row">${chips}</div>
      </div>
    </div>
    <div class="cs-summary-grid">${summaryCards}</div>
    ${_renderDdbAbilityStrip(charData || {})}
    ${_renderCombatSummaryStrip(charData || {})}
  </div>`;
}



  const CLASS_OVERVIEW_GUIDES = {
    barbarian: {
      heading: 'Rage-first frontliner',
      summary: 'Rage, weapon attacks, and durability should stay obvious before anything else. If those three surfaces feel thin, the build is missing key front-line information.',
      essentials: ['Open Combat first', 'Validate Rage resource and recovery', 'Check attack cards and rider notes'],
      weakSpots: ['Rest recovery on Rage-like resources', 'Attack rider clarity', 'Target/result feedback'],
    },
    bard: {
      heading: 'Support caster / tempo utility',
      summary: 'Bardic Inspiration, spellcasting, and support tools should stay easy to find together so the class feels flexible instead of buried in notes.',
      essentials: ['Check spell save / attack math', 'Spend Bardic Inspiration cleanly', 'Verify concentration swaps'],
      weakSpots: ['Support effect visibility', 'Resource spend feedback', 'Linked spell detail'],
    },
    cleric: {
      heading: 'Prepared divine caster',
      summary: 'This build should feel spell-first with Channel Divinity clearly tracked. Healing, save DCs, and domain-flavored actions should all be easy to find.',
      essentials: ['Check prepared spell surface', 'Validate Channel Divinity', 'Verify healing / damage spell flow'],
      weakSpots: ['Domain flavor surfacing', 'Save spell expectations', 'Healing target feedback'],
    },
    druid: {
      heading: 'Primal prepared caster / shapeshifter',
      summary: 'Druid should clearly show three lanes together: prepared Wisdom spellcasting, Wild Shape resource + form limits, and circle identity (Moon battle-shifter vs Land terrain caster).',
      essentials: ['Check prepared formula and current prepared count', 'Check Wild Shape uses + max form CR', 'Check circle-specific lane (Moon transform pressure or Land recovery/circle spells)'],
      weakSpots: ['Cast-vs-shift timing clarity', 'Wild Companion visibility', 'High-level Beast Spells / Archdruid expectations'],
    },
    fighter: {
      heading: 'Weapon loadout specialist',
      summary: 'Combat should be the strongest surface here. Equipped attacks, Action Surge, and Second Wind should all be visible without digging.',
      essentials: ['Check equipped attacks', 'Use Action Surge / Second Wind', 'Verify mastery / weapon notes'],
      weakSpots: ['Weapon rider clarity', 'Action economy messaging', 'Loadout sync'],
    },
    monk: {
      heading: 'Mobile action-economy striker',
      summary: 'Monk play falls apart fast if Focus, attacks, and bonus-action techniques are not connected. The core loop should stay obvious.',
      essentials: ['Check Focus pool', 'Validate attacks and bonus actions', 'Confirm movement / utility notes'],
      weakSpots: ['Resource spend clarity', 'Bonus-action visibility', 'Feature explanation depth'],
    },
    paladin: {
      heading: 'Burst defender / divine striker',
      summary: 'Weapon attacks, Lay on Hands, Channel Divinity, aura range, and spell/smite choices should read like one connected loop instead of separate systems.',
      essentials: ['Check attack cards and smite timing', 'Validate Lay on Hands + Channel Divinity', 'Inspect aura range + spell slot messaging'],
      weakSpots: ['Hybrid combat/magic clarity', 'Healing workflow', 'Aura positioning visibility'],
    },
    ranger: {
      heading: 'Hunter skirmisher / half-caster',
      summary: 'Ranger should read as a blended martial + Wisdom-caster class: weapon cadence, Hunt/Mark pressure, mobility tools, and subclass tactics should all be visible together.',
      essentials: ['Check equipped attacks + Extra Attack cadence', 'Validate Hunter’s Mark + spell slot surface', 'Confirm mobility/scout features and subclass tools'],
      weakSpots: ['Half-caster slot/known clarity', 'Subclass tactic visibility', 'Companion command clarity (Beast Master)'],
    },
    rogue: {
      heading: 'Precision opportunist',
      summary: 'Attacks, bonus-action mobility, and Sneak Attack-facing expectations should all be obvious if the sheet is healthy.',
      essentials: ['Check attack cards', 'Inspect bonus actions', 'Verify burst-damage notes and target flow'],
      weakSpots: ['Conditional damage explanation', 'Targeting clarity', 'Action grouping'],
    },
    sorcerer: {
      heading: 'Flexible slot / point caster',
      summary: 'Sorcerer should read as a known-spell caster with a visible point engine: spells known, slots, Sorcery Points, Flexible Casting, and Metamagic should connect cleanly.',
      essentials: ['Check known cantrip/spell limits', 'Validate Sorcery Points and conversion tools', 'Inspect metamagic and subclass action surfaces'],
      weakSpots: ['Point / slot conversion clarity', 'Metamagic option visibility', 'Subclass spike visibility (Wild/Draconic)'],
    },
    warlock: {
      heading: 'Pact magic specialist',
      summary: 'Short-rest slot identity and class feature flavor need to be visible or the sheet risks feeling like a generic caster.',
      essentials: ['Check pact spell rows', 'Inspect short-rest resource hints', 'Review feature drawer depth'],
      weakSpots: ['Pact slot clarity', 'Invocation explanation', 'Rest identity messaging'],
    },
    wizard: {
      heading: 'Prepared arcane toolkit',
      summary: 'The build should feel like a spell-first control panel with clear prepared spell depth and reliable slot math.',
      essentials: ['Check spell library and linked rows', 'Validate save/attack math', 'Inspect arcane feature detail'],
      weakSpots: ['Prepared vs available clarity', 'Library readability', 'Feature explanation depth'],
    },
  };

  function _classGuideKey(charData) {
    const raw = _firstNonEmpty(charData && charData.className, charData && charData.class, '').toLowerCase();
    return raw.split(/[^a-z]+/).find(Boolean) || '';
  }

  function _classOverviewGuide(charData) {
    return CLASS_OVERVIEW_GUIDES[_classGuideKey(charData)] || null;
  }

  function _renderClassEssentials(charData) {
    const guide = _classOverviewGuide(charData);
    if (!guide) {
      return '<div class="cs-empty-state compact"><span>No class summary is loaded for this build yet.</span></div>';
    }
    const details = []
      .concat(Array.isArray(guide.weakSpots) ? guide.weakSpots.slice(0, 3) : [])
      .filter(Boolean)
      .map(function (item) {
        return `<div class="cs-guide-list-row"><span class="cs-guide-index">•</span><span>${_esc(item)}</span></div>`;
      }).join('');
    return `<div class="cs-guide-card">
      <div class="cs-guide-heading">${_esc(guide.heading || 'Class summary')}</div>
      <div class="cs-overview-copy">${_esc(guide.summary || 'This class summary will help keep the most important tools easy to find.')}</div>
      ${details ? `<div class="cs-guide-list">${details}</div>` : ''}
    </div>`;
  }

  function _renderSuggestedRoute(charData) {
    const guide = _classOverviewGuide(charData);
    const attacksReady = _safeArray(charData.quickAttackCards).length > 0 || _nativeActionCount(charData) > 0;
    const spellsReady = _safeArray(charData.rulesSpellCards).length > 0 || !!_firstNonEmpty(charData.spellSaveDc, charData.spellAttack);
    const loadoutReady = _safeArray(charData.inventory).length > 0;
    const route = [];
    route.push(attacksReady ? 'Go to Combat and click a real attack/action card.' : 'Build or import combat cards before trusting attacks.');
    route.push(spellsReady ? 'Open Magic and inspect one linked spell in the drawer.' : 'Spell layer is still light; add spells from builder/import before play.');
    route.push(loadoutReady ? 'Open Loadout and confirm equipped gear matches the attack surface.' : 'No synced loadout yet; inventory-driven tests may be misleading.');
    if (guide && guide.weakSpots && guide.weakSpots.length) route.push('Watch these thin areas: ' + guide.weakSpots.join(', ') + '.');
    return `<div class="cs-guide-list">${route.map(function (item, idx) { return `<div class="cs-guide-list-row"><span class="cs-guide-index">${idx + 1}</span><span>${_esc(item)}</span></div>`; }).join('')}</div>`;
  }

  function _renderDetailDrawer() {
    return `<div class="cs-detail-overlay" hidden data-cs-detail-overlay>
      <aside class="cs-detail-drawer" role="dialog" aria-modal="true" aria-label="Item details" data-cs-detail-drawer>
        <div class="cs-detail-head">
          <div>
            <div class="cs-detail-eyebrow" data-cs-detail-kicker>Details</div>
            <div class="cs-detail-title" data-cs-detail-title>Choose an action, spell, or feature</div>
            <div class="cs-detail-subtitle" data-cs-detail-subtitle>Open any card or row to inspect the rules text in one place.</div>
          </div>
          <button class="cs-detail-close" type="button" aria-label="Close details" data-cs-detail-close>×</button>
        </div>
        <div class="cs-detail-chip-row" data-cs-detail-chips></div>
        <div class="cs-detail-body" data-cs-detail-body>
          <div class="cs-empty-state compact"><span>Click a combat card, spell row, or feature entry to inspect its details here.</span></div>
        </div>
      </aside>
    </div>`;
  }

  function _detailSectionsToHtml(sections) {
    const rows = Array.isArray(sections) ? sections : [];
    if (!rows.length) {
      return '<div class="cs-empty-state compact"><span>No extra detail supplied for this entry yet.</span></div>';
    }
    return rows.map(function (section) {
      const items = Array.isArray(section && section.items) ? section.items.filter(Boolean) : [];
      const body = section && section.body ? `<div class="cs-detail-copy">${_esc(section.body)}</div>` : '';
      const list = items.length ? `<div class="cs-detail-meta-grid">${items.map(function (item) {
        return `<div class="cs-detail-meta-card"><div class="cs-detail-meta-label">${_esc(item.label || 'Detail')}</div><div class="cs-detail-meta-value">${_esc(item.value || '—')}</div></div>`;
      }).join('')}</div>` : '';
      return `<section class="cs-detail-section"><div class="cs-detail-section-title">${_esc(section && section.title || 'Details')}</div>${body}${list}</section>`;
    }).join('');
  }

  function openDetailDrawer(payload) {
    const overlay = document.querySelector('[data-cs-detail-overlay]');
    if (!overlay) return;
    const titleEl = overlay.querySelector('[data-cs-detail-title]');
    const subtitleEl = overlay.querySelector('[data-cs-detail-subtitle]');
    const kickerEl = overlay.querySelector('[data-cs-detail-kicker]');
    const chipsEl = overlay.querySelector('[data-cs-detail-chips]');
    const bodyEl = overlay.querySelector('[data-cs-detail-body]');
    const data = payload && typeof payload === 'object' ? payload : {};
    if (titleEl) titleEl.textContent = data.title || 'Details';
    if (subtitleEl) subtitleEl.textContent = data.subtitle || data.description || 'Rules summary';
    if (kickerEl) kickerEl.textContent = data.kicker || 'Inspector';
    if (chipsEl) {
      const chips = Array.isArray(data.chips) ? data.chips.filter(Boolean) : [];
      chipsEl.innerHTML = chips.length ? chips.map(function (chip) { return `<span class="cs-status-chip good">${_esc(chip)}</span>`; }).join('') : '';
    }
    if (bodyEl) bodyEl.innerHTML = _detailSectionsToHtml(data.sections);
    overlay.hidden = false;
    document.body.classList.add('cs-detail-open');
  }

  function closeDetailDrawer() {
    const overlay = document.querySelector('[data-cs-detail-overlay]');
    if (!overlay) return;
    overlay.hidden = true;
    document.body.classList.remove('cs-detail-open');
  }

  function _bindDetailDrawer(container) {
    const overlay = container.querySelector('[data-cs-detail-overlay]');
    if (!overlay || overlay.__csBound) return;
    overlay.__csBound = true;
    const closeBtn = overlay.querySelector('[data-cs-detail-close]');
    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        closeDetailDrawer();
      });
    }
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) {
        closeDetailDrawer();
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !overlay.hidden) closeDetailDrawer();
    });
  }


function _renderOverviewPanel(charData) {
  const quickAttacks = _safeArray(charData.quickAttackCards).slice(0, 5);
  const nativeActions = _nativeActionArray(charData).slice(0, 5);
  const spotlightActions = quickAttacks.length ? quickAttacks : nativeActions;
  const spells = _safeArray(charData.rulesSpellCards).slice(0, 5);
  const resources = _safeArray(charData.nativeResources).slice(0, 6);
  const features = _safeArray(charData.nativeFeatures).slice(0, 6);
  const equipped = _safeArray(charData.inventory).filter(function (item) { return !!item.equipped; }).slice(0, 6);
  const notes = _firstNonEmpty(charData.campaignNotes, charData.notes, '');

  return `
    <div class="cs-overview-columns">
      <div class="cs-overview-main">
        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Actions Overview</div>
          ${_renderListRows(spotlightActions, 'No equipped weapon found. Go to Inventory to equip one, or add/import action cards in Build/Edit mode.', function (item) {
            const badge = item.attackBonus ? `Atk ${item.attackBonus}` : (item.actionType || item.action_type || item.kind || 'Action');
            const damage = item.damage || item.damageText || item.damage_formula || item.subtitle || item.summary || '';
            return { title: item.name || 'Action', note: [badge, damage].filter(Boolean).join(' • ') };
          })}
        </section>

        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Spell Highlights</div>
          ${_renderListRows(spells, 'No spells found. This character may not cast spells, or the import needs review.', function (spell) {
            return {
              title: spell.displayName || spell.name || 'Spell',
              note: [spell.levelLabel || spell.level || '', spell.castingTime || '', spell.range || '', spell.attackType || spell.savingThrow || spell.saveDC || '', spell.effect || spell.playerFacingEffectSummary || spell.damageText || spell.school || ''].filter(Boolean).join(' • '),
            };
          })}
        </section>

        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Feature Highlights</div>
          ${_renderListRows(features, 'No structured features surfaced yet.', function (feature) {
            return {
              title: feature.name || 'Feature',
              note: [feature.level ? `Level ${feature.level}` : '', feature.actionType || feature.resourceName || feature.kind || '', feature.summary || feature.effect || ''].filter(Boolean).join(' • '),
            };
          })}
        </section>

        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Ability Scores</div>
          <div class="cs-overview-copy">Your core scores and modifiers for fast checks and roll confidence.</div>
          ${_renderAbilityAudit(charData)}
        </section>
      </div>

      <div class="cs-overview-rail">
        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Resource Tracker</div>
          ${_renderListRows(resources, 'No tracked class resources yet.', function (resource) {
            const current = resource.current ?? resource.remaining ?? resource.uses ?? '—';
            const max = resource.max ?? resource.limit ?? '';
            const summary = max !== '' ? `${current}/${max}` : String(current);
            return { title: resource.name || 'Resource', note: [summary, resource.recharge || resource.reset || resource.note || ''].filter(Boolean).join(' • ') };
          })}
        </section>

        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Equipped Gear</div>
          ${_renderListRows(equipped, 'No equipped weapon found. Go to Inventory to equip one.', function (item) {
            return { title: item.name || 'Item', note: [item.damage || item.damage_dice || '', item.range || '', item.properties && item.properties.length ? item.properties.join(', ') : ''].filter(Boolean).join(' • ') };
          })}
        </section>

        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Traits / Notes</div>
          <div class="cs-overview-copy">Reference traits and class identity without leaving the main sheet.</div>
          ${_renderSpeciesSnapshot(charData)}
          ${_renderClassEssentials(charData)}
        </section>

        <section class="cs-overview-section">
          <div class="cs-overview-section-title">Player Notes</div>
          ${notes ? `<div class="cs-overview-copy">${_esc(String(notes))}</div>` : '<div class="cs-empty-state compact"><span>No notes found. Open the Notes tab or Build/Edit mode to add player notes.</span></div>'}
        </section>
      </div>
    </div>`;
}

function _buildSkeleton(wrapper, charData) {
    const header = document.createElement('div');
    header.className = 'cs-flagship-shell';
    header.innerHTML = _renderFlagshipHeader(charData);
    wrapper.appendChild(header);

    const tabBarWrap = document.createElement('div');
    tabBarWrap.className = 'cs-tab-bar-wrap';
    const tabBar = document.createElement('div');
    tabBar.className = 'cs-tab-bar';
    tabBar.setAttribute('role', 'tablist');
    tabBar.setAttribute('aria-label', 'Character sheet tabs');
    TABS.forEach(function (tab, i) {
      const btn = document.createElement('button');
      btn.className = 'cs-tab-btn' + (i === 0 ? ' active' : '');
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      btn.setAttribute('aria-controls', 'csp-panel-' + _esc(tab.id));
      btn.setAttribute('id', 'csp-tab-' + _esc(tab.id));
      btn.setAttribute('data-tab-id', tab.id);
      const count = _tabCount(tab.id, charData || {});
      btn.setAttribute('data-tab-count', count || '');
      btn.innerHTML = `<span class="cs-tab-btn-inner"><span class="cs-tab-label">${_esc(tab.label)}</span></span>`;
      tabBar.appendChild(btn);
    });
    tabBarWrap.appendChild(tabBar);
    const body = document.createElement('div');
    body.className = 'cs-ddb-body';
    body.innerHTML = _renderLeftColumn(charData || {});
    const main = document.createElement('main');
    main.className = 'cs-ddb-main-panel';
    main.appendChild(tabBarWrap);
    body.appendChild(main);
    wrapper.appendChild(body);

    const panels = {};
    TABS.forEach(function (tab, i) {
      const panel = document.createElement('div');
      panel.className = 'cs-tab-panel' + (i === 0 ? ' active' : '');
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('id', 'csp-panel-' + tab.id);
      panel.setAttribute('aria-labelledby', 'csp-tab-' + tab.id);
      if (i !== 0) panel.setAttribute('hidden', '');
      main.appendChild(panel);
      panels[tab.id] = panel;
    });

    wrapper.insertAdjacentHTML('beforeend', _renderDetailDrawer());

    return { tabBar, panels };
  }

  function _activateTab(tabId, refs, charData, initialised) {
    refs.tabBar.querySelectorAll('.cs-tab-btn').forEach(function (btn) {
      const isActive = btn.getAttribute('data-tab-id') === tabId;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    Object.keys(refs.panels).forEach(function (id) {
      const panel = refs.panels[id];
      const isActive = id === tabId;
      panel.classList.toggle('active', isActive);
      if (isActive) {
        panel.removeAttribute('hidden');
        void panel.offsetWidth;
        panel.style.animation = 'none';
        void panel.offsetWidth;
        panel.style.animation = '';
      } else {
        panel.setAttribute('hidden', '');
      }
    });

    if (!initialised[tabId]) {
      initialised[tabId] = true;
      const tabDef = TABS.find(function (t) { return t.id === tabId; });
      if (tabDef && refs.panels[tabId]) tabDef.init(refs.panels[tabId], charData);
    }
  }

  function initCharacterSheetPremium(container, charData) {
    if (!container) return;
    // The full sheet/builder is heavy and only ever built on demand (Open Full
    // Sheet / Characters), never during the light player boot — phase-timed so
    // its cost is observable when it does run.
    if (global.AppBoot && typeof global.AppBoot.phase === 'function') global.AppBoot.phase('character sheet', 'start');
    if (global.buildCharacterSheetRuntime && charData && typeof charData === 'object') {
      const sheetRuntime = global.buildCharacterSheetRuntime(charData);
      charData.characterSheetRuntime = sheetRuntime;
      charData.nativeResources = sheetRuntime.resources;
      charData.nativeActionCards = {
        actions: sheetRuntime.actions,
        bonusActions: sheetRuntime.bonusActions,
        reactions: sheetRuntime.reactions,
        passives: sheetRuntime.features,
      };
      charData.nativeClassFeatures = sheetRuntime.features;
      charData.nativeFeatures = sheetRuntime.features;
      charData.rulesSpellbook = sheetRuntime.spells;
      charData.attacks = sheetRuntime.attacks;
      charData.inventory = sheetRuntime.inventory;
    }
    container.classList.add('cs-premium-container');
    container.innerHTML = '';

    const refs = _buildSkeleton(container, charData || {});
    container.querySelectorAll('.cs-portrait-img').forEach(function (img) {
      img.addEventListener('error', function () {
        const frame = img.closest('.cs-portrait-frame');
        if (frame) frame.classList.add('image-failed');
        const url = img.getAttribute('data-portrait-url') || img.currentSrc || img.src || '';
        if (url && !img.dataset.warned) {
          img.dataset.warned = '1';
          if (global.console && typeof global.console.warn === 'function') {
            global.console.warn('[character-sheet] Portrait failed to load; showing initials fallback.', url);
          }
        }
        img.removeAttribute('src');
      }, { once: true });
    });
    const initialised = {};
    _bindDetailDrawer(container);
    _activateTab('actions', refs, charData, initialised);

    refs.tabBar.addEventListener('click', function (e) {
      const btn = e.target.closest('.cs-tab-btn');
      if (!btn) return;
      const tabId = btn.getAttribute('data-tab-id');
      if (tabId) _activateTab(tabId, refs, charData, initialised);
    });

    refs.tabBar.addEventListener('keydown', function (e) {
      const btns = Array.from(refs.tabBar.querySelectorAll('.cs-tab-btn'));
      const idx = btns.indexOf(document.activeElement);
      if (idx < 0) return;
      let next = -1;
      if (e.key === 'ArrowRight') next = (idx + 1) % btns.length;
      if (e.key === 'ArrowLeft') next = (idx - 1 + btns.length) % btns.length;
      if (next >= 0) {
        e.preventDefault();
        btns[next].focus();
        btns[next].click();
      }
    });

    container.addEventListener('click', function (e) {
      const jump = e.target.closest('.cs-launch-btn');
      if (!jump) return;
      const tabId = jump.getAttribute('data-tab-jump');
      if (tabId) {
        _activateTab(tabId, refs, charData, initialised);
        if (tabId === 'actions') {
          const firstActionRow = container.querySelector('#csp-panel-actions .cs-action-row');
          if (firstActionRow && typeof firstActionRow.focus === 'function') firstActionRow.focus();
        }
        return;
      }
      const restType = jump.getAttribute('data-rest');
      if (restType) {
        if (typeof global.openCharacterRestFlow === 'function') {
          global.openCharacterRestFlow(restType);
        } else if (typeof global.showToast === 'function') {
          global.showToast('Rest system is unavailable right now.');
        }
        return;
      }
      const page = jump.getAttribute('data-jump');
      if (page && typeof global.goCharacterBookPage === 'function') {
        global.goCharacterBookPage(page);
      }
    });
    if (global.AppBoot && typeof global.AppBoot.phase === 'function') global.AppBoot.phase('character sheet', 'end');
  }

  function openMapPanelFromSheet(tabId) {
    const key = String(tabId || '').trim();
    if (!key) return false;
    const safeKey = key.replace(/"/g, "");
    const trigger = document.querySelector(`[data-rtab-target="${safeKey}"]`);
    if (trigger && typeof trigger.click === 'function') {
      trigger.click();
      if (typeof global.showToast === 'function') global.showToast('Opened ' + key + ' on the map panel.');
      return true;
    }
    if (typeof global.showToast === 'function') global.showToast('That map panel is not available right now.');
    return false;
  }

  global.CSContainer = { initCharacterSheetPremium, openDetailDrawer, closeDetailDrawer, openMapPanelFromSheet, resolveCharacterPortrait };
  global.resolveCharacterPortrait = resolveCharacterPortrait;

  (function patchCharBookNav() {
    var _orig = global.goCharacterBookPage;
    if (typeof _orig !== 'function') return;
    global.goCharacterBookPage = function (page, instant) {
      _orig.call(this, page, instant);
      if (page === 'premiumsheet') {
        setTimeout(function () {
          if (typeof global.initPremiumSheetIfNeeded === 'function') {
            global.initPremiumSheetIfNeeded();
          }
        }, 80);
      }
    };
  }());

}(window));
