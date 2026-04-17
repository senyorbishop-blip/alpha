(function initCharacterBuilderStepSpells(global) {
  'use strict';

  var state = {
    cacheByKey: Object.create(null),
    inflightByKey: Object.create(null),
    tabByKey: Object.create(null),
    searchByKey: Object.create(null),
    statusByKey: Object.create(null),
  };

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function norm(value) {
    return String(value || '').trim().toLowerCase();
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function dedupeIds(rows) {
    var seen = Object.create(null);
    var out = [];
    asArray(rows).forEach(function (entry) {
      var id = String(entry || '').trim();
      if (!id || seen[id]) return;
      seen[id] = true;
      out.push(id);
    });
    return out;
  }

  function levelLabel(level) {
    var n = parseInt(level, 10);
    if (!Number.isFinite(n) || n <= 0) return 'Cantrips';
    if (n === 1) return '1st Level';
    if (n === 2) return '2nd Level';
    if (n === 3) return '3rd Level';
    return String(n) + 'th Level';
  }

  function sortByNameAndLevel(cards) {
    return asArray(cards).slice().sort(function (a, b) {
      var la = parseInt(a && a.level, 10) || 0;
      var lb = parseInt(b && b.level, 10) || 0;
      if (la !== lb) return la - lb;
      var na = String((a && (a.displayName || a.name)) || '').toLowerCase();
      var nb = String((b && (b.displayName || b.name)) || '').toLowerCase();
      if (na < nb) return -1;
      if (na > nb) return 1;
      return 0;
    });
  }

  function requestKey(draft) {
    var cls = asObject(draft && draft.class);
    var progression = asObject(draft && draft.progression);
    var subclassId = String(cls.subclassId || '').trim().toLowerCase();
    var level = parseInt(progression.level, 10) || 1;
    return [norm(cls.id), subclassId, level].join('|');
  }

  function buildAbilityPayload(draft) {
    var abilities = asObject(draft && draft.abilities);
    var scores = asObject(abilities.scores);
    var payload = {
      scores: {
        str: parseInt(scores.str, 10) || 10,
        dex: parseInt(scores.dex, 10) || 10,
        con: parseInt(scores.con, 10) || 10,
        int: parseInt(scores.int, 10) || 10,
        wis: parseInt(scores.wis, 10) || 10,
        cha: parseInt(scores.cha, 10) || 10,
      },
    };
    return payload;
  }

  function fetchOptions(draft) {
    var cls = asObject(draft && draft.class);
    var classId = String(cls.id || '').trim();
    if (!classId) return Promise.resolve(null);

    var progression = asObject(draft && draft.progression);
    var spellbook = asObject(draft && draft.spellbook);
    var key = requestKey(draft);

    if (state.cacheByKey[key]) return Promise.resolve(state.cacheByKey[key]);
    if (state.inflightByKey[key]) return state.inflightByKey[key];

    var params = new URLSearchParams();
    params.set('class_id', classId);
    params.set('subclass_id', String(cls.subclassId || '').trim());
    params.set('level', String(parseInt(progression.level, 10) || 1));
    params.set('known', dedupeIds(spellbook.known).join(','));
    params.set('prepared', dedupeIds(spellbook.prepared).join(','));
    params.set('abilities', JSON.stringify(buildAbilityPayload(draft)));

    state.inflightByKey[key] = fetch('/api/character/builder/spells/options?' + params.toString(), {
      method: 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(function (res) {
        if (!res.ok) throw new Error('spell_options_failed');
        return res.json();
      })
      .then(function (payload) {
        state.cacheByKey[key] = payload && typeof payload === 'object' ? payload : null;
        return state.cacheByKey[key];
      })
      .catch(function () {
        state.cacheByKey[key] = null;
        return null;
      })
      .finally(function () {
        state.inflightByKey[key] = null;
      });

    return state.inflightByKey[key];
  }

  function ensureStyles() {
    if (document.getElementById('character-builder-step-spells-style')) return;
    var style = document.createElement('style');
    style.id = 'character-builder-step-spells-style';
    style.textContent = [
      '.cb-spells-shell{border:1px solid rgba(201,168,76,.22);border-radius:12px;padding:12px;background:linear-gradient(180deg,rgba(10,16,24,.82),rgba(8,12,18,.86));}',
      '.cb-spells-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:8px;margin-bottom:10px;}',
      '.cb-spells-pill{border:1px solid rgba(91,163,208,.24);border-radius:9px;background:rgba(0,0,0,.28);padding:7px 9px;}',
      '.cb-spells-pill .k{display:block;font-size:.55rem;text-transform:uppercase;letter-spacing:.05em;color:rgba(188,208,226,.88);}',
      '.cb-spells-pill .v{display:block;font-size:.72rem;color:#e7f5ff;font-weight:600;}',
      '.cb-spells-status{font-size:.62rem;color:#d9ecf8;min-height:16px;margin:0 0 8px;}',
      '.cb-spells-status.warn{color:#ffb0b0;}',
      '.cb-spells-legend{font-size:.6rem;color:rgba(190,222,236,.86);margin:0 0 10px;}',
      '.cb-spells-toolbar{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:10px;}',
      '.cb-spells-search{max-width:300px;width:100%;}',
      '.cb-spells-count-badge{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(0,229,204,.28);border-radius:999px;background:rgba(0,229,204,.12);padding:3px 10px;font-size:.62rem;color:#dffaf7;}',
      '.cb-spells-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;}',
      '.cb-spells-tab{font-size:.62rem;padding:4px 8px;border-radius:999px;border:1px solid rgba(201,168,76,.35);background:rgba(0,0,0,.28);color:#e6d1a0;cursor:pointer;}',
      '.cb-spells-tab.active{background:rgba(201,168,76,.18);border-color:rgba(201,168,76,.8);color:#ffe5a3;}',
      '.cb-spells-group{display:none;}',
      '.cb-spells-group.active{display:block;}',
      '.cb-spells-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;}',
      '.cb-spell-card{border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:8px;background:rgba(0,0,0,.24);cursor:pointer;}',
      '.cb-spell-card.selected{border-color:rgba(0,229,204,.9);background:rgba(0,229,204,.14);}',
      '.cb-spell-card.granted{border-color:rgba(201,168,76,.62);background:rgba(201,168,76,.11);}',
      '.cb-spell-card.blocked{opacity:.52;cursor:not-allowed;}',
      '.cb-spell-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;}',
      '.cb-spell-name{font-size:.72rem;font-weight:600;color:#ebf7ff;}',
      '.cb-spell-level{font-size:.55rem;padding:2px 7px;border-radius:999px;border:1px solid rgba(201,168,76,.42);background:rgba(201,168,76,.14);color:#ffe3a1;white-space:nowrap;}',
      '.cb-spell-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;font-size:.58rem;color:rgba(188,222,238,.9);}',
      '.cb-spell-summary{margin-top:6px;font-size:.6rem;line-height:1.42;color:rgba(220,232,244,.86);}',
      '.cb-spell-note{margin-top:6px;font-size:.56rem;color:#ffe0a7;}',
      '.cb-selected-pane{border:1px solid rgba(0,229,204,.28);border-radius:10px;padding:8px;background:rgba(0,0,0,.26);margin:0 0 10px;}',
      '.cb-selected-pane h4{margin:0 0 6px;font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;color:#9ce7dc;}',
      '.cb-spell-chip-row{display:flex;flex-wrap:wrap;gap:6px;}',
      '.cb-spell-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(0,229,204,.38);background:rgba(0,229,204,.12);border-radius:999px;padding:2px 8px;font-size:.62rem;color:#dffaf7;cursor:pointer;}',
      '.cb-spell-chip button{all:unset;cursor:pointer;color:#bdf5ef;font-size:.68rem;line-height:1;}',
      '.cb-granted-pane{border:1px dashed rgba(201,168,76,.42);border-radius:10px;padding:8px;background:rgba(201,168,76,.08);margin-bottom:10px;}',
      '.cb-granted-pane h4{margin:0 0 6px;font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;color:#ffe3a1;}',
      '.cb-granted-list{display:flex;flex-wrap:wrap;gap:6px;}',
      '.cb-granted-tag{display:inline-flex;align-items:center;border:1px solid rgba(201,168,76,.5);border-radius:999px;padding:2px 8px;font-size:.6rem;color:#ffe8bc;background:rgba(201,168,76,.14);}',
      '.cb-spells-empty{font-size:.64rem;color:rgba(190,222,236,.85);padding:6px 0;}',
    ].join('');
    document.head.appendChild(style);
  }

  function modeFromLimits(limits) {
    var row = asObject(limits);
    if (row.preparedLimit != null) return 'prepared';
    if (row.spellsKnown != null || row.cantripsKnown != null) return 'known';
    return 'library';
  }

  function indexCards(cards) {
    var out = Object.create(null);
    asArray(cards).forEach(function (card) {
      var id = String(card && card.id || '').trim();
      if (id) out[id] = card;
    });
    return out;
  }

  function grantedSets(validation) {
    var row = asObject(validation);
    var subclass = asObject(row.subclassGrants);
    var classBonus = asObject(row.classBonusGrants);
    return {
      alwaysPrepared: new Set(asArray(subclass.alwaysPrepared).map(function (v) { return String(v || '').trim(); }).filter(Boolean)),
      alwaysKnown: new Set(asArray(subclass.alwaysKnown).map(function (v) { return String(v || '').trim(); }).filter(Boolean)),
      classAlwaysKnown: new Set(asArray(classBonus.alwaysKnown).map(function (v) { return String(v || '').trim(); }).filter(Boolean)),
    };
  }

  function sanitizeSelection(draft, payload) {
    var validation = asObject(payload && payload.validation);
    var fallback = asObject(draft && draft.spellbook);
    var known = dedupeIds(validation.known && validation.known.length ? validation.known : fallback.known);
    var prepared = dedupeIds(validation.prepared && validation.prepared.length ? validation.prepared : fallback.prepared);
    return { known: known, prepared: prepared };
  }

  function computeCounts(payload, selected) {
    var limits = asObject(payload && payload.limits);
    var cardById = indexCards(payload && payload.cards);
    var grants = grantedSets(payload && payload.validation);
    var knownCantrips = 0;
    var knownLevelled = 0;
    var preparedLevelled = 0;

    selected.known.forEach(function (spellId) {
      var level = parseInt(cardById[spellId] && cardById[spellId].level, 10) || 0;
      if (level <= 0) {
        knownCantrips += 1;
      } else if (!grants.alwaysKnown.has(spellId) && !grants.classAlwaysKnown.has(spellId)) {
        knownLevelled += 1;
      }
    });

    selected.prepared.forEach(function (spellId) {
      var level = parseInt(cardById[spellId] && cardById[spellId].level, 10) || 0;
      if (level > 0 && !grants.alwaysPrepared.has(spellId)) {
        preparedLevelled += 1;
      }
    });

    return {
      mode: modeFromLimits(limits),
      knownCantrips: knownCantrips,
      knownLevelled: knownLevelled,
      preparedLevelled: preparedLevelled,
      cantripLimit: limits.cantripsKnown,
      knownLimit: limits.spellsKnown,
      preparedLimit: limits.preparedLimit,
      grants: grants,
    };
  }

  function setSelection(context, known, prepared, status) {
    context.onSetField(['spellbook', 'known'], dedupeIds(known));
    context.onSetField(['spellbook', 'prepared'], dedupeIds(prepared));
    state.statusByKey[requestKey(context.draft)] = String(status || '');
  }

  function applySanitizedSelection(context, payload) {
    var selected = sanitizeSelection(context.draft, payload);
    var currentSpellbook = asObject(context.draft && context.draft.spellbook);
    var currentKnown = dedupeIds(currentSpellbook.known);
    var currentPrepared = dedupeIds(currentSpellbook.prepared);
    var changed = currentKnown.join('|') !== selected.known.join('|') || currentPrepared.join('|') !== selected.prepared.join('|');
    if (changed) {
      setSelection(context, selected.known, selected.prepared, 'Invalid legacy spell picks were repaired to legal class options.');
    }
  }

  function filterCardsForUnlockedTiers(cards, highestUnlocked) {
    return sortByNameAndLevel(asArray(cards).filter(function (card) {
      var level = parseInt(card && card.level, 10);
      if (!Number.isFinite(level) || level < 0) level = 0;
      if (level <= 0) return true;
      return level <= highestUnlocked;
    }));
  }

  function renderSpellCard(card, opts) {
    var options = asObject(opts);
    var classes = ['cb-spell-card'];
    if (options.selected) classes.push('selected');
    if (options.granted) classes.push('granted');
    if (options.blocked) classes.push('blocked');

    var spellId = String(card && card.id || '').trim();
    var name = String(card && (card.displayName || card.name || spellId) || 'Spell');
    var summary = String(card && (card.summary || card.description) || '').trim();

    return [
      '<article class="' + classes.join(' ') + '" data-builder-spell-card="1" data-builder-spell-id="' + esc(spellId) + '" data-builder-spell-level="' + esc(String(parseInt(card && card.level, 10) || 0)) + '" data-builder-spell-blocked="' + (options.blocked ? '1' : '0') + '">',
      '<div class="cb-spell-head"><div class="cb-spell-name">' + esc(name) + '</div><div class="cb-spell-level">' + esc(levelLabel(card && card.level)) + '</div></div>',
      '<div class="cb-spell-meta"><span>' + esc(String(card && card.school || '')) + '</span><span>' + esc(String(card && card.castingTime || '')) + '</span><span>' + esc(String(card && card.range || '')) + '</span></div>',
      summary ? '<div class="cb-spell-summary">' + esc(summary) + '</div>' : '',
      options.note ? '<div class="cb-spell-note">' + esc(options.note) + '</div>' : '',
      '</article>'
    ].join('');
  }

  function renderMain(context, payload) {
    var draft = asObject(context && context.draft);
    var classRow = asObject(draft.class);
    var classId = String(classRow.id || '').trim();
    if (!classId) {
      return '<div class="builder-help-text">Choose a class first to configure spellcasting.</div>';
    }

    var validation = asObject(payload && payload.validation);
    var limits = asObject(payload && payload.limits);
    var selected = sanitizeSelection(draft, payload);
    var counts = computeCounts(payload, selected);
    var grants = grantedSets(validation);
    var highestUnlocked = parseInt(payload && payload.highestUnlockedSpellLevel, 10);
    if (!Number.isFinite(highestUnlocked) || highestUnlocked < 0) highestUnlocked = 0;

    var visibleCards = filterCardsForUnlockedTiers(payload && payload.cards, highestUnlocked);
    var cardsByLevel = Object.create(null);
    visibleCards.forEach(function (card) {
      var level = parseInt(card && card.level, 10);
      if (!Number.isFinite(level) || level < 0) level = 0;
      if (!cardsByLevel[level]) cardsByLevel[level] = [];
      cardsByLevel[level].push(card);
    });

    var levels = Object.keys(cardsByLevel).map(function (v) { return parseInt(v, 10); }).filter(function (v) { return Number.isFinite(v); }).sort(function (a, b) { return a - b; });

    var key = requestKey(draft);
    var activeLevel = state.tabByKey[key];
    if (levels.indexOf(activeLevel) < 0) activeLevel = levels.length ? levels[0] : 0;
    state.tabByKey[key] = activeLevel;

    var search = String(state.searchByKey[key] || '').trim().toLowerCase();
    var status = String(state.statusByKey[key] || '').trim();
    var warnClass = /limit reached|not unlocked|illegal|only|exceeded/i.test(status) ? ' warn' : '';

    var cardById = indexCards(visibleCards);
    var chipKnown = selected.known.map(function (id) { return cardById[id]; }).filter(Boolean);
    var chipPrepared = selected.prepared.map(function (id) { return cardById[id]; }).filter(Boolean);

    var grantedIds = [];
    grants.alwaysPrepared.forEach(function (spellId) { grantedIds.push(spellId + '|always-prepared'); });
    grants.alwaysKnown.forEach(function (spellId) { grantedIds.push(spellId + '|always-known'); });
    grants.classAlwaysKnown.forEach(function (spellId) { grantedIds.push(spellId + '|class-always-known'); });

    var grantedRows = grantedIds.map(function (entry) {
      var parts = String(entry || '').split('|');
      var spellId = parts[0] || '';
      var mode = parts[1] || '';
      var card = cardById[spellId] || {};
      var label = String(card.displayName || card.name || spellId || 'Spell');
      var suffix = mode === 'always-prepared' ? 'Always Prepared' : 'Always Known';
      return '<span class="cb-granted-tag">' + esc(label) + ' · ' + esc(suffix) + '</span>';
    });

    return [
      '<div class="screen-header"><div class="screen-title">Spells</div><div class="screen-divider"></div><div class="screen-subtitle">Only legal class and subclass spell options are shown for your current level and unlocked tiers.</div></div>',
      '<div class="cb-spells-shell">',
      '<div class="cb-spells-summary">',
      '<div class="cb-spells-pill"><span class="k">Class</span><span class="v">' + esc(String(limits.className || classId)) + ' Lv ' + esc(String(parseInt(asObject(draft.progression).level, 10) || 1)) + '</span></div>',
      '<div class="cb-spells-pill"><span class="k">Cantrips</span><span class="v">' + esc(String(counts.knownCantrips)) + (counts.cantripLimit != null ? (' / ' + esc(String(counts.cantripLimit))) : '') + '</span></div>',
      '<div class="cb-spells-pill"><span class="k">Known</span><span class="v">' + esc(String(counts.knownLevelled)) + (counts.knownLimit != null ? (' / ' + esc(String(counts.knownLimit))) : '') + '</span></div>',
      '<div class="cb-spells-pill"><span class="k">Prepared</span><span class="v">' + esc(String(counts.preparedLevelled)) + (counts.preparedLimit != null ? (' / ' + esc(String(counts.preparedLimit))) : '') + '</span></div>',
      '<div class="cb-spells-pill"><span class="k">Unlocked Tier</span><span class="v">' + esc(highestUnlocked > 0 ? levelLabel(highestUnlocked) : 'Cantrips only') + '</span></div>',
      '</div>',
      '<div class="cb-spells-status' + warnClass + '">' + esc(status) + '</div>',
      '<div class="cb-spells-legend">Once you reach your legal pick cap, additional non-granted picks are blocked. Granted subclass/class spells do not consume your normal limit.</div>',
      '<div class="cb-selected-pane">',
      '<h4>' + esc(counts.mode === 'prepared' ? 'Known Spells & Cantrips' : 'Selected Spells') + '</h4>',
      chipKnown.length ? ('<div class="cb-spell-chip-row">' + chipKnown.map(function (row) { return '<span class="cb-spell-chip" data-builder-spell-remove="' + esc(String(row.id || '')) + '">' + esc(String(row.displayName || row.name || row.id || '')) + '<button type="button">×</button></span>'; }).join('') + '</div>') : '<div class="cb-spells-empty">No spells selected yet.</div>',
      counts.mode === 'prepared' ? '<h4 style="margin-top:8px">Prepared Spells</h4>' : '',
      counts.mode === 'prepared'
        ? (chipPrepared.length ? ('<div class="cb-spell-chip-row">' + chipPrepared.map(function (row) { return '<span class="cb-spell-chip" data-builder-spell-remove="' + esc(String(row.id || '')) + '">' + esc(String(row.displayName || row.name || row.id || '')) + '<button type="button">×</button></span>'; }).join('') + '</div>') : '<div class="cb-spells-empty">No prepared spells selected.</div>')
        : '',
      '</div>',
      grantedRows.length ? ('<div class="cb-granted-pane"><h4>Granted Class/Subclass Spells</h4><div class="cb-granted-list">' + grantedRows.join('') + '</div></div>') : '',
      '<div class="cb-spells-toolbar">',
      '<span class="cb-spells-count-badge">Selected: ' + esc(String(counts.mode === 'prepared' ? counts.preparedLevelled : counts.knownLevelled)) + (counts.mode === 'prepared' && counts.preparedLimit != null ? (' / ' + esc(String(counts.preparedLimit))) : (counts.mode !== 'prepared' && counts.knownLimit != null ? (' / ' + esc(String(counts.knownLimit))) : '')) + '</span>',
      '<input type="search" class="cb-spells-search" data-builder-spell-search="1" value="' + esc(search) + '" placeholder="Search legal spells…" />',
      '</div>',
      '<div class="cb-spells-tabs">',
      levels.map(function (lvl) {
        var total = asArray(cardsByLevel[lvl]).length;
        return '<button type="button" class="cb-spells-tab' + (lvl === activeLevel ? ' active' : '') + '" data-builder-spell-tab="' + esc(String(lvl)) + '">' + esc(levelLabel(lvl)) + ' (' + esc(String(total)) + ')</button>';
      }).join(''),
      '</div>',
      levels.map(function (lvl) {
        var rows = asArray(cardsByLevel[lvl]).filter(function (card) {
          if (!search) return true;
          var haystack = String([
            card && card.displayName,
            card && card.name,
            card && card.summary,
            card && card.description,
            card && card.school
          ].join(' ')).toLowerCase();
          return haystack.indexOf(search) >= 0;
        });

        var sectionBody = rows.length
          ? ('<div class="cb-spells-grid">' + rows.map(function (card) {
            var spellId = String(card && card.id || '').trim();
            var spellLevel = parseInt(card && card.level, 10) || 0;
            var selectedNow = spellLevel <= 0
              ? selected.known.indexOf(spellId) >= 0
              : (counts.mode === 'prepared' ? selected.prepared.indexOf(spellId) >= 0 : selected.known.indexOf(spellId) >= 0);
            var granted = grants.alwaysPrepared.has(spellId) || grants.alwaysKnown.has(spellId) || grants.classAlwaysKnown.has(spellId);
            var blocked = !selectedNow && card && card.isAccessible === false;
            var note = '';
            if (granted && counts.mode === 'prepared' && grants.alwaysPrepared.has(spellId)) {
              note = 'Granted (always prepared, no slot cost in pick limit).';
            } else if (granted) {
              note = 'Granted (always known, no slot cost in pick limit).';
            } else if (blocked) {
              note = String(card.blockedReason || 'Not unlocked for this class and level.');
            }
            return renderSpellCard(card, {
              selected: selectedNow,
              blocked: blocked,
              granted: granted,
              note: note,
            });
          }).join('') + '</div>')
          : '<div class="cb-spells-empty">No spells match this filter.</div>';

        return '<section class="cb-spells-group' + (lvl === activeLevel ? ' active' : '') + '" data-builder-spell-group="' + esc(String(lvl)) + '">' + sectionBody + '</section>';
      }).join(''),
      '</div>'
    ].join('');
  }

  function render(context) {
    ensureStyles();
    var draft = asObject(context && context.draft);
    var classId = String(asObject(draft.class).id || '').trim();
    if (!classId) return '<div class="builder-help-text">Pick a class first to configure spellcasting.</div>';

    var key = requestKey(draft);
    var cached = state.cacheByKey[key];
    if (!cached && !state.inflightByKey[key]) {
      fetchOptions(draft);
    }

    if (state.inflightByKey[key] && !cached) {
      return '<div class="loading-msg" style="text-align:left;padding:0">Loading spell options...</div>';
    }

    if (!cached) {
      return '<div class="builder-help-text">Could not load legal spell options for this class/level. Re-open this step after confirming class/subclass selections.</div>';
    }

    return renderMain(context, cached);
  }

  function wireTabAndSearch(root, draft) {
    var key = requestKey(draft);

    root.querySelectorAll('[data-builder-spell-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var level = parseInt(btn.getAttribute('data-builder-spell-tab'), 10);
        if (!Number.isFinite(level)) level = 0;
        state.tabByKey[key] = level;

        root.querySelectorAll('[data-builder-spell-tab]').forEach(function (tab) {
          tab.classList.toggle('active', tab === btn);
        });
        root.querySelectorAll('[data-builder-spell-group]').forEach(function (groupEl) {
          var groupLevel = parseInt(groupEl.getAttribute('data-builder-spell-group'), 10);
          groupEl.classList.toggle('active', groupLevel === level);
        });
      });
    });

    var searchInput = root.querySelector('[data-builder-spell-search="1"]');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        var query = String(searchInput.value || '').trim().toLowerCase();
        state.searchByKey[key] = query;

        root.querySelectorAll('[data-builder-spell-group]').forEach(function (groupEl) {
          var cards = groupEl.querySelectorAll('[data-builder-spell-card="1"]');
          var visibleCount = 0;
          cards.forEach(function (cardEl) {
            var haystack = String(cardEl.textContent || '').toLowerCase();
            var visible = !query || haystack.indexOf(query) >= 0;
            cardEl.style.display = visible ? '' : 'none';
            if (visible) visibleCount += 1;
          });

          var empty = groupEl.querySelector('.cb-spells-empty[data-filter-empty="1"]');
          if (visibleCount === 0) {
            if (!empty) {
              empty = document.createElement('div');
              empty.className = 'cb-spells-empty';
              empty.setAttribute('data-filter-empty', '1');
              empty.textContent = 'No spells match this filter.';
              groupEl.appendChild(empty);
            }
          } else if (empty && empty.parentNode) {
            empty.parentNode.removeChild(empty);
          }
        });
      });
    }
  }

  function bind(root, context) {
    if (!root || !context || typeof context.onSetField !== 'function') return;

    var draft = asObject(context.draft);
    var key = requestKey(draft);

    var maybePayload = state.cacheByKey[key];
    if (maybePayload) {
      applySanitizedSelection(context, maybePayload);
    }

    fetchOptions(draft).then(function (payload) {
      if (!payload || !root.isConnected) return;

      applySanitizedSelection(context, payload);
      var body = root.querySelector('.builder-body');
      if (body && body.querySelector('.loading-msg')) {
        body.innerHTML = renderMain(context, payload);
      }

      var selected = sanitizeSelection(context.draft, payload);
      var counts = computeCounts(payload, selected);
      var mode = counts.mode;

      function toggleSpell(spellId, spellLevel) {
        var known = selected.known.slice();
        var prepared = selected.prepared.slice();

        if (spellLevel <= 0) {
          if (known.indexOf(spellId) >= 0) {
            setSelection(context, known.filter(function (id) { return id !== spellId; }), prepared.filter(function (id) { return id !== spellId; }), 'Cantrip removed.');
            return;
          }
          if (counts.cantripLimit != null && counts.knownCantrips >= parseInt(counts.cantripLimit, 10)) {
            setSelection(context, known, prepared, 'Limit reached: cantrip cap is ' + counts.cantripLimit + '.');
            return;
          }
          known.push(spellId);
          setSelection(context, known, prepared, 'Cantrip learned.');
          return;
        }

        if (mode === 'prepared') {
          if (prepared.indexOf(spellId) >= 0) {
            setSelection(context, known, prepared.filter(function (id) { return id !== spellId; }), 'Spell unprepared.');
            return;
          }
          if (counts.preparedLimit != null && counts.preparedLevelled >= parseInt(counts.preparedLimit, 10) && !counts.grants.alwaysPrepared.has(spellId)) {
            setSelection(context, known, prepared, 'Limit reached: prepared cap is ' + counts.preparedLimit + '.');
            return;
          }
          prepared.push(spellId);
          setSelection(context, known, prepared, counts.grants.alwaysPrepared.has(spellId)
            ? 'Granted spell prepared (no prepared-slot cost).'
            : 'Spell prepared.');
          return;
        }

        if (known.indexOf(spellId) >= 0) {
          setSelection(context, known.filter(function (id) { return id !== spellId; }), prepared.filter(function (id) { return id !== spellId; }), 'Spell removed.');
          return;
        }

        if (counts.knownLimit != null && counts.knownLevelled >= parseInt(counts.knownLimit, 10) && !counts.grants.alwaysKnown.has(spellId) && !counts.grants.classAlwaysKnown.has(spellId)) {
          setSelection(context, known, prepared, 'Limit reached: known spell cap is ' + counts.knownLimit + '.');
          return;
        }

        known.push(spellId);
        var isGrantedKnown = counts.grants.alwaysKnown.has(spellId) || counts.grants.classAlwaysKnown.has(spellId);
        setSelection(context, known, prepared, isGrantedKnown
          ? 'Granted spell known (no known-slot cost).'
          : 'Spell learned.');
      }

      root.querySelectorAll('[data-builder-spell-remove]').forEach(function (chip) {
        chip.addEventListener('click', function (event) {
          event.preventDefault();
          var spellId = String(chip.getAttribute('data-builder-spell-remove') || '').trim();
          if (!spellId) return;
          setSelection(
            context,
            selected.known.filter(function (id) { return id !== spellId; }),
            selected.prepared.filter(function (id) { return id !== spellId; }),
            'Spell removed.'
          );
        });
      });

      root.querySelectorAll('[data-builder-spell-card="1"]').forEach(function (card) {
        card.addEventListener('click', function () {
          if (String(card.getAttribute('data-builder-spell-blocked') || '') === '1') {
            state.statusByKey[key] = 'This spell is not currently legal for your class/subclass/level.';
            return;
          }
          var spellId = String(card.getAttribute('data-builder-spell-id') || '').trim();
          var spellLevel = parseInt(card.getAttribute('data-builder-spell-level'), 10) || 0;
          if (!spellId) return;
          toggleSpell(spellId, spellLevel);
        });
      });

      wireTabAndSearch(root, draft);
    });
  }

  if (!global.CharacterBuilderStepModules || typeof global.CharacterBuilderStepModules !== 'object') {
    global.CharacterBuilderStepModules = {};
  }

  global.CharacterBuilderStepModules.spells = {
    id: 'spells',
    label: 'Spells',
    render: render,
    bind: bind,
  };
})(window);
