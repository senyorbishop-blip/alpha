(function initCharacterBuilderStepSpells(global) {
  'use strict';

  var _state = {
    cache: {},
    activeTabByKey: {},
    searchByKey: {},
    statusByKey: {},
    loadingByKey: {},
    inflightByKey: {},
  };

  function asArray(value) { return Array.isArray(value) ? value : []; }
  function asObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
  function norm(value) { return String(value || '').trim().toLowerCase(); }

  function escHtml(value) {
    return String(value == null ? '' : value)
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
    global.CharacterBuilderStepModules.spells = step;
  }

  function levelLabel(level) {
    var n = parseInt(level, 10);
    if (!Number.isFinite(n) || n <= 0) return 'Cantrips';
    if (n === 1) return '1st Level';
    if (n === 2) return '2nd Level';
    if (n === 3) return '3rd Level';
    return String(n) + 'th Level';
  }

  function ensureStyles() {
    if (document.getElementById('character-builder-step-spells-style')) return;
    var style = document.createElement('style');
    style.id = 'character-builder-step-spells-style';
    style.textContent = [
      '.cb-spells-shell{border:1px solid rgba(201,168,76,.22);border-radius:12px;padding:12px;background:linear-gradient(180deg,rgba(10,16,24,.82),rgba(8,12,18,.86));}',
      '.cb-spells-topline{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:10px;}',
      '.cb-spells-count{border:1px solid rgba(91,163,208,.22);background:rgba(0,0,0,.26);border-radius:9px;padding:6px 8px;}',
      '.cb-spells-count .k{display:block;font-size:.55rem;color:rgba(188,208,226,.88);text-transform:uppercase;letter-spacing:.05em;}',
      '.cb-spells-count .v{display:block;font-size:.72rem;color:#e7f5ff;font-weight:600;}',
      '.cb-spells-status{font-size:.62rem;color:#d9ecf8;margin:0 0 8px;min-height:16px;}',
      '.cb-spells-status.warn{color:#ffb0b0;}',
      '.cb-spells-selected{border:1px solid rgba(0,229,204,.28);border-radius:10px;padding:8px;background:rgba(0,0,0,.26);margin-bottom:10px;}',
      '.cb-spells-selected h4{margin:0 0 6px;font-size:.62rem;letter-spacing:.06em;color:#9ce7dc;text-transform:uppercase;}',
      '.cb-spell-chip-row{display:flex;flex-wrap:wrap;gap:6px;}',
      '.cb-spell-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(0,229,204,.38);background:rgba(0,229,204,.12);border-radius:999px;padding:2px 8px;font-size:.62rem;color:#dffaf7;cursor:pointer;}',
      '.cb-spell-chip button{all:unset;cursor:pointer;color:#bdf5ef;font-size:.68rem;line-height:1;}',
      '.cb-spells-toolbar{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:10px;}',
      '.cb-spells-search{max-width:300px;width:100%;}',
      '.cb-spells-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;}',
      '.cb-spells-tab{font-size:.62rem;padding:4px 8px;border-radius:999px;border:1px solid rgba(201,168,76,.35);background:rgba(0,0,0,.28);color:#e6d1a0;cursor:pointer;}',
      '.cb-spells-tab.active{background:rgba(201,168,76,.18);border-color:rgba(201,168,76,.8);color:#ffe5a3;}',
      '.cb-spells-group{display:none;}',
      '.cb-spells-group.active{display:block;}',
      '.cb-spell-card{border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:8px 10px;background:rgba(0,0,0,.24);margin-bottom:8px;cursor:pointer;}',
      '.cb-spell-card:hover{border-color:rgba(91,163,208,.58);}',
      '.cb-spell-card.selected{border-color:rgba(0,229,204,.88);background:rgba(0,229,204,.14);}',
      '.cb-spell-card.blocked{opacity:.56;cursor:not-allowed;}',
      '.cb-spell-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;}',
      '.cb-spell-name{font-size:.72rem;font-weight:600;color:#ebf7ff;}',
      '.cb-spell-badge{font-size:.55rem;padding:2px 7px;border-radius:999px;border:1px solid rgba(201,168,76,.42);background:rgba(201,168,76,.14);color:#ffe3a1;white-space:nowrap;}',
      '.cb-spell-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;font-size:.58rem;color:rgba(188,222,238,.9);}',
      '.cb-spell-desc{margin-top:6px;font-size:.6rem;line-height:1.45;color:rgba(220,232,244,.86);}',
      '.cb-spell-reason{margin-top:6px;font-size:.56rem;color:#ffc6c6;}'
    ].join('');
    document.head.appendChild(style);
  }

  function csvFrom(value) {
    return asArray(value).map(function (entry) { return String(entry || '').trim(); }).filter(Boolean).join(',');
  }

  function requestKey(draft) {
    var cls = asObject(draft && draft.class);
    var progression = asObject(draft && draft.progression);
    return [norm(cls.id), norm(cls.subclassId), parseInt(progression.level, 10) || 1].join('|');
  }

  function idsKey(draft) {
    var spellbook = asObject(draft && draft.spellbook);
    return [csvFrom(spellbook.known), csvFrom(spellbook.prepared)].join('|');
  }

  function modeFromLimits(limits) {
    if (limits && limits.preparedLimit != null) return 'prepared';
    if (limits && (limits.spellsKnown != null || limits.cantripsKnown != null)) return 'known';
    return 'library';
  }

  function fetchOptions(draft) {
    var cls = asObject(draft && draft.class);
    var classId = String(cls.id || '').trim();
    if (!classId) return Promise.resolve(null);

    var progression = asObject(draft && draft.progression);
    var spellbook = asObject(draft && draft.spellbook);
    var key = requestKey(draft) + '::' + idsKey(draft);

    if (_state.cache[key]) return Promise.resolve(_state.cache[key]);
    if (_state.inflightByKey[key]) return _state.inflightByKey[key];

    var params = new URLSearchParams();
    params.set('class_id', classId);
    params.set('subclass_id', String(cls.subclassId || '').trim());
    params.set('level', String(parseInt(progression.level, 10) || 1));
    params.set('known', csvFrom(spellbook.known));
    params.set('prepared', csvFrom(spellbook.prepared));

    _state.loadingByKey[key] = true;
    _state.inflightByKey[key] = fetch('/api/character/builder/spells/options?' + params.toString(), { credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('spell_options_failed');
        return res.json();
      })
      .then(function (payload) {
        _state.cache[key] = payload || null;
        return _state.cache[key];
      })
      .catch(function () {
        _state.cache[key] = null;
        return null;
      })
      .finally(function () {
        _state.loadingByKey[key] = false;
        _state.inflightByKey[key] = null;
      });

    return _state.inflightByKey[key];
  }

  function indexCards(cards) {
    var out = {};
    asArray(cards).forEach(function (card) {
      var id = String(card && card.id || '').trim();
      if (id) out[id] = card;
    });
    return out;
  }

  function dedupeIds(rows) {
    var seen = {};
    var out = [];
    asArray(rows).forEach(function (entry) {
      var id = String(entry || '').trim();
      if (!id || seen[id]) return;
      seen[id] = true;
      out.push(id);
    });
    return out;
  }

  function currentSelection(draft, data) {
    var spellbook = asObject(draft && draft.spellbook);
    if (data && data.validation && Array.isArray(data.validation.known)) {
      return {
        known: dedupeIds(data.validation.known),
        prepared: dedupeIds(data.validation.prepared),
      };
    }
    return {
      known: dedupeIds(spellbook.known),
      prepared: dedupeIds(spellbook.prepared),
    };
  }

  function countsForSelection(data, selected) {
    var limits = asObject(data && data.limits);
    var mode = modeFromLimits(limits);
    var cardsById = indexCards(data && data.cards);

    var cantrips = selected.known.filter(function (id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) === 0;
    }).length;
    var knownLevelled = selected.known.filter(function (id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) > 0;
    }).length;
    var preparedLevelled = selected.prepared.filter(function (id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) > 0;
    }).length;

    return {
      mode: mode,
      cantrips: cantrips,
      knownLevelled: knownLevelled,
      preparedLevelled: preparedLevelled,
      cantripLimit: limits.cantripsKnown,
      knownLimit: limits.spellsKnown,
      preparedLimit: limits.preparedLimit,
    };
  }

  function groupedRows(data, selected) {
    var cards = asArray(data && data.cards);
    var highest = parseInt(data && data.highestUnlockedSpellLevel, 10);
    if (!Number.isFinite(highest) || highest < 0) highest = 0;

    var groups = {};
    cards.forEach(function (card) {
      var level = parseInt(card && card.level, 10);
      if (!Number.isFinite(level) || level < 0) level = 0;
      var isSelected = selected.known.indexOf(String(card && card.id || '')) >= 0 || selected.prepared.indexOf(String(card && card.id || '')) >= 0;
      if (level > 0 && highest >= 0 && level > highest && !isSelected) return;
      if (!groups[level]) groups[level] = [];
      groups[level].push(card);
    });

    var levels = Object.keys(groups)
      .map(function (v) { return parseInt(v, 10); })
      .filter(function (v) { return Number.isFinite(v); })
      .sort(function (a, b) { return a - b; });

    return {
      groups: groups,
      levels: levels,
      highest: highest,
    };
  }

  function renderChipGroup(ids, key, heading, cardById, levelledOnly) {
    var filtered = ids.filter(function (id) {
      if (!levelledOnly) return true;
      return parseInt(cardById[id] && cardById[id].level, 10) > 0;
    });
    if (!filtered.length) return '';

    return '<h4>' + escHtml(heading) + '</h4><div class="cb-spell-chip-row">' + filtered.map(function (id) {
      var row = cardById[id] || {};
      var name = String(row.displayName || row.name || id).trim() || id;
      return '<span class="cb-spell-chip" data-builder-spell-remove="' + escHtml(id) + '" data-builder-spell-remove-list="' + escHtml(key) + '">' +
        escHtml(name) +
        '<button type="button" aria-label="Remove ' + escHtml(name) + '">×</button>' +
      '</span>';
    }).join('') + '</div>';
  }

  function renderCard(card, selected, blocked, reason) {
    var spellId = String(card && card.id || '').trim();
    var spellName = String(card && (card.displayName || card.name || spellId) || 'Spell');
    var classes = ['cb-spell-card'];
    if (selected) classes.push('selected');
    if (blocked) classes.push('blocked');

    var meta = [card && card.school, card && card.castingTime, card && card.range].filter(Boolean);

    return [
      '<article class="' + classes.join(' ') + '" data-builder-spell-id="' + escHtml(spellId) + '" data-builder-spell-level="' + escHtml(String(parseInt(card && card.level, 10) || 0)) + '" data-builder-spell-blocked="' + (blocked ? '1' : '0') + '">',
      '<div class="cb-spell-head"><div class="cb-spell-name">' + escHtml(spellName) + '</div><span class="cb-spell-badge">' + escHtml(levelLabel(card && card.level)) + '</span></div>',
      '<div class="cb-spell-meta">' + (meta.length ? meta.map(function (v) { return '<span>' + escHtml(v) + '</span>'; }).join('') : '<span>No metadata</span>') + '</div>',
      '<div class="cb-spell-desc">' + escHtml(String(card && (card.summary || card.description) || 'No details available.')) + '</div>',
      reason ? '<div class="cb-spell-reason">' + escHtml(reason) + '</div>' : '',
      '</article>'
    ].join('');
  }

  function render(context) {
    ensureStyles();
    var draft = asObject(context && context.draft);
    var cls = asObject(draft.class);
    var classId = String(cls.id || '').trim();
    if (!classId) {
      return '<div class="builder-help-text">Pick a class first to configure spellcasting.</div>';
    }

    var dataKey = requestKey(draft) + '::' + idsKey(draft);
    if (!_state.cache[dataKey] && !_state.loadingByKey[dataKey]) {
      fetchOptions(draft);
    }

    var data = _state.cache[dataKey] || null;
    if (_state.loadingByKey[dataKey] && !data) {
      return '<div class="loading-msg" style="text-align:left;padding:0">Loading spell options…</div>';
    }
    if (!data) {
      return '<div class="builder-help-text">Could not load spell options. Try changing class level and reopening this step.</div>';
    }

    var selected = currentSelection(draft, data);
    var counts = countsForSelection(data, selected);
    var grouped = groupedRows(data, selected);
    var levels = grouped.levels;

    var activeKey = requestKey(draft);
    var activeLevel = _state.activeTabByKey[activeKey];
    if (levels.indexOf(activeLevel) < 0) activeLevel = levels.length ? levels[0] : 0;
    _state.activeTabByKey[activeKey] = activeLevel;

    var search = String(_state.searchByKey[activeKey] || '').trim();
    var status = String(_state.statusByKey[activeKey] || '').trim();
    var statusTone = /limit reached|locked|illegal|only/i.test(status) ? ' warn' : '';
    var cardById = indexCards(data.cards);
    var mode = modeFromLimits(asObject(data.limits));

    var selectedMarkup = '';
    selectedMarkup += renderChipGroup(selected.known, 'known', mode === 'prepared' ? 'Known Cantrips' : 'Known Spells', cardById, mode === 'prepared');
    if (mode === 'prepared') {
      selectedMarkup += renderChipGroup(selected.prepared, 'prepared', 'Prepared Spells', cardById, true);
    }
    if (!selectedMarkup) selectedMarkup = '<div class="builder-help-text" style="margin:0">No spells selected yet.</div>';

    var classLabel = String((data.limits && data.limits.className) || classId).trim();
    var levelValue = parseInt(asObject(draft.progression).level, 10) || 1;
    var tierLabel = grouped.highest > 0 ? levelLabel(grouped.highest) : 'Cantrips only';

    return [
      '<div class="screen-header">',
      '<div class="screen-title">Spells</div>',
      '<div class="screen-divider"></div>',
      '<div class="screen-subtitle">Choose legal class spells only. Unlock tiers and pick limits are enforced by live rules.</div>',
      '</div>',
      '<div class="cb-spells-shell">',
      '<div class="cb-spells-topline">',
      '<div class="cb-spells-count"><span class="k">Class</span><span class="v">' + escHtml(classLabel) + ' Lv ' + escHtml(String(levelValue)) + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Cantrips</span><span class="v">' + escHtml(String(counts.cantrips)) + (counts.cantripLimit != null ? (' / ' + escHtml(String(counts.cantripLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Known</span><span class="v">' + escHtml(String(counts.knownLevelled)) + (counts.knownLimit != null ? (' / ' + escHtml(String(counts.knownLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Prepared</span><span class="v">' + escHtml(String(counts.preparedLevelled)) + (counts.preparedLimit != null ? (' / ' + escHtml(String(counts.preparedLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Unlocked Tier</span><span class="v">' + escHtml(tierLabel) + '</span></div>',
      '</div>',
      '<div class="cb-spells-status' + statusTone + '">' + escHtml(status) + '</div>',
      '<div class="cb-spells-selected">' + selectedMarkup + '</div>',
      '<div class="cb-spells-toolbar">',
      '<div class="builder-help-text" style="margin:0">Pick from cards below. When a limit is reached, additional picks are blocked immediately.</div>',
      '<input type="search" class="cb-spells-search" data-builder-spell-search-input="1" value="' + escHtml(search) + '" placeholder="Search legal spells…" />',
      '</div>',
      '<div class="cb-spells-tabs">',
      levels.length ? levels.map(function (lvl) {
        return '<button type="button" class="cb-spells-tab' + (lvl === activeLevel ? ' active' : '') + '" data-builder-spell-tab="' + escHtml(String(lvl)) + '">' + escHtml(levelLabel(lvl)) + '</button>';
      }).join('') : '<span class="builder-help-text">No legal spell tiers available for this class at this level.</span>',
      '</div>',
      levels.map(function (lvl) {
        var rows = asArray(grouped.groups[lvl]);
        var filtered = rows.filter(function (card) {
          if (!search) return true;
          var hay = String([card && card.displayName, card && card.description, card && card.summary, card && card.school].join(' ')).toLowerCase();
          return hay.indexOf(search.toLowerCase()) >= 0;
        });

        var block = filtered.length ? filtered.map(function (card) {
          var spellId = String(card && card.id || '').trim();
          var spellLevel = parseInt(card && card.level, 10) || 0;
          var isSelected = spellLevel === 0
            ? selected.known.indexOf(spellId) >= 0
            : (mode === 'prepared' ? selected.prepared.indexOf(spellId) >= 0 : selected.known.indexOf(spellId) >= 0);
          var isBlocked = !isSelected && card && card.isAccessible === false;
          var blockedReason = isBlocked ? (card.blockedReason || 'Not unlocked yet for this class/level.') : '';
          return renderCard(card, isSelected, isBlocked, blockedReason);
        }).join('') : '<div class="builder-help-text">No spells match the current search for this tier.</div>';

        return '<section class="cb-spells-group' + (lvl === activeLevel ? ' active' : '') + '" data-builder-spell-group="' + escHtml(String(lvl)) + '">' + block + '</section>';
      }).join(''),
      '</div>'
    ].join('');
  }

  function setSelection(context, nextKnown, nextPrepared, statusMsg) {
    var draft = asObject(context && context.draft);
    var currentSpellbook = asObject(draft.spellbook);
    var knownNow = dedupeIds(currentSpellbook.known);
    var preparedNow = dedupeIds(currentSpellbook.prepared);
    var knownNext = dedupeIds(nextKnown);
    var preparedNext = dedupeIds(nextPrepared);

    if (knownNow.join('|') !== knownNext.join('|')) {
      context.onSetField(['spellbook', 'known'], knownNext);
    }
    if (preparedNow.join('|') !== preparedNext.join('|')) {
      context.onSetField(['spellbook', 'prepared'], preparedNext);
    }

    var reqKey = requestKey(draft);
    _state.statusByKey[reqKey] = statusMsg || '';
  }

  function bind(root, context) {
    if (!root || !context || typeof context.onSetField !== 'function') return;

    var draft = asObject(context.draft);
    var reqKey = requestKey(draft);
    var fullKey = reqKey + '::' + idsKey(draft);

    fetchOptions(draft).then(function (data) {
      if (!data || !root.isConnected) return;
      var serverKnown = asArray(data.known && data.known.length ? data.known : (data.validation && data.validation.known));
      var serverPrepared = asArray(data.prepared && data.prepared.length ? data.prepared : (data.validation && data.validation.prepared));
      setSelection(context, serverKnown, serverPrepared, '');
    });

    function withData(fn) {
      var data = _state.cache[fullKey];
      if (data) {
        fn(data);
        return;
      }
      fetchOptions(context.draft).then(function (fresh) {
        if (fresh) fn(fresh);
      });
    }

    function toggleSpell(spellId, level) {
      withData(function (data) {
        var selection = currentSelection(context.draft, data);
        var limits = asObject(data.limits);
        var mode = modeFromLimits(limits);
        var counts = countsForSelection(data, selection);

        var known = selection.known.slice();
        var prepared = selection.prepared.slice();

        if (level === 0) {
          if (known.indexOf(spellId) >= 0) {
            known = known.filter(function (id) { return id !== spellId; });
            prepared = prepared.filter(function (id) { return id !== spellId; });
            setSelection(context, known, prepared, 'Cantrip removed.');
            return;
          }
          if (counts.cantripLimit != null && counts.cantrips >= parseInt(counts.cantripLimit, 10)) {
            setSelection(context, known, prepared, 'Limit reached: cantrip cap is ' + counts.cantripLimit + '.');
            return;
          }
          known.push(spellId);
          setSelection(context, known, prepared, 'Cantrip learned.');
          return;
        }

        if (mode === 'prepared') {
          if (prepared.indexOf(spellId) >= 0) {
            prepared = prepared.filter(function (id) { return id !== spellId; });
            setSelection(context, known, prepared, 'Spell unprepared.');
            return;
          }
          if (counts.preparedLimit != null && counts.preparedLevelled >= parseInt(counts.preparedLimit, 10)) {
            setSelection(context, known, prepared, 'Limit reached: prepared cap is ' + counts.preparedLimit + '.');
            return;
          }
          prepared.push(spellId);
          setSelection(context, known, prepared, 'Spell prepared.');
          return;
        }

        if (known.indexOf(spellId) >= 0) {
          known = known.filter(function (id) { return id !== spellId; });
          prepared = prepared.filter(function (id) { return id !== spellId; });
          setSelection(context, known, prepared, 'Spell removed.');
          return;
        }
        if (counts.knownLimit != null && counts.knownLevelled >= parseInt(counts.knownLimit, 10)) {
          setSelection(context, known, prepared, 'Limit reached: known cap is ' + counts.knownLimit + '.');
          return;
        }
        known.push(spellId);
        setSelection(context, known, prepared, 'Spell learned.');
      });
    }

    root.querySelectorAll('[data-builder-spell-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _state.activeTabByKey[reqKey] = parseInt(btn.dataset.builderSpellTab, 10) || 0;
        setSelection(context, asArray(asObject(context.draft && context.draft.spellbook).known), asArray(asObject(context.draft && context.draft.spellbook).prepared), '');
      });
    });

    var searchInput = root.querySelector('[data-builder-spell-search-input="1"]');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        _state.searchByKey[reqKey] = String(searchInput.value || '');
        setSelection(context, asArray(asObject(context.draft && context.draft.spellbook).known), asArray(asObject(context.draft && context.draft.spellbook).prepared), '');
      });
    }

    root.querySelectorAll('[data-builder-spell-remove]').forEach(function (chip) {
      chip.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        var spellId = String(chip.dataset.builderSpellRemove || '').trim();
        if (!spellId) return;
        var selection = currentSelection(context.draft, _state.cache[fullKey]);
        var known = selection.known.filter(function (id) { return id !== spellId; });
        var prepared = selection.prepared.filter(function (id) { return id !== spellId; });
        setSelection(context, known, prepared, 'Spell removed.');
      });
    });

    root.querySelectorAll('[data-builder-spell-id]').forEach(function (card) {
      card.addEventListener('click', function () {
        if (String(card.dataset.builderSpellBlocked || '') === '1') {
          _state.statusByKey[reqKey] = 'This spell is not unlocked for the current class/level.';
          setSelection(context, asArray(asObject(context.draft && context.draft.spellbook).known), asArray(asObject(context.draft && context.draft.spellbook).prepared), _state.statusByKey[reqKey]);
          return;
        }
        var spellId = String(card.dataset.builderSpellId || '').trim();
        var level = parseInt(card.dataset.builderSpellLevel, 10) || 0;
        if (!spellId) return;
        toggleSpell(spellId, level);
      });
    });
  }

  registerStep({
    id: 'spells',
    label: 'Spells',
    render: render,
    bind: bind,
  });
})(window);
