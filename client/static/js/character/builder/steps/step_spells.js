(function initCharacterBuilderStepSpells(global) {
  'use strict';

  var _state = {
    cacheKey: '',
    data: null,
    loading: false,
    inflight: null,
    pendingRerenderKey: '',
    activeLevelByKey: {},
    searchByKey: {},
    statusByKey: {},
  };

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
    global.CharacterBuilderStepModules[step.id] = step;
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function normalizeId(value) {
    return String(value || '').trim().toLowerCase();
  }

  function toCsv(rows) {
    return asArray(rows)
      .map(function mapEntry(v) { return String(v || '').trim(); })
      .filter(Boolean)
      .join(',');
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
      '.cb-spell-reason{margin-top:6px;font-size:.56rem;color:#ffc6c6;}',
    ].join('');
    document.head.appendChild(style);
  }

  function buildRequestKey(draft) {
    var classData = asObject(draft && draft.class);
    var progression = asObject(draft && draft.progression);
    var spellbook = asObject(draft && draft.spellbook);
    return [
      normalizeId(classData.id),
      normalizeId(classData.subclassId),
      parseInt(progression.level, 10) || 1,
      toCsv(spellbook.known),
      toCsv(spellbook.prepared),
    ].join('|');
  }

  function fetchOptions(draft) {
    var classData = asObject(draft && draft.class);
    var classId = String(classData.id || '').trim();
    if (!classId) {
      _state.cacheKey = '';
      _state.data = null;
      _state.loading = false;
      _state.inflight = null;
      return Promise.resolve(null);
    }

    var key = buildRequestKey(draft);
    if (_state.cacheKey === key && _state.data) return Promise.resolve(_state.data);
    if (_state.cacheKey === key && _state.loading && _state.inflight) return _state.inflight;

    var progression = asObject(draft && draft.progression);
    var spellbook = asObject(draft && draft.spellbook);
    var q = new URLSearchParams();
    q.set('class_id', classId);
    q.set('subclass_id', String(classData.subclassId || '').trim());
    q.set('level', String(parseInt(progression.level, 10) || 1));
    q.set('known', toCsv(spellbook.known));
    q.set('prepared', toCsv(spellbook.prepared));

    _state.cacheKey = key;
    _state.loading = true;
    _state.inflight = fetch('/api/character/builder/spells/options?' + q.toString(), { credentials: 'same-origin' })
      .then(function onResponse(res) {
        if (!res.ok) throw new Error('spell_options_failed');
        return res.json();
      })
      .then(function onData(data) {
        _state.data = data || null;
        _state.loading = false;
        _state.inflight = null;
        return _state.data;
      })
      .catch(function onErr() {
        _state.data = null;
        _state.loading = false;
        _state.inflight = null;
        return null;
      });

    return _state.inflight;
  }

  function getMode(limits) {
    if (limits && limits.preparedLimit != null) return 'prepared';
    if (limits && (limits.spellsKnown != null || limits.cantripsKnown != null)) return 'known';
    return 'library';
  }

  function indexCards(cards) {
    var byId = {};
    asArray(cards).forEach(function each(card) {
      var id = String(card && card.id || '').trim();
      if (id) byId[id] = card;
    });
    return byId;
  }

  function selectedCounts(data, spellbook) {
    var limits = asObject(data && data.limits);
    var mode = getMode(limits);
    var cardsById = indexCards(data && data.cards);
    var known = asArray(spellbook && spellbook.known);
    var prepared = asArray(spellbook && spellbook.prepared);

    var cantrips = known.filter(function(id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) === 0;
    }).length;

    var knownLevelled = known.filter(function(id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) > 0;
    }).length;

    var preparedLevelled = prepared.filter(function(id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) > 0;
    }).length;

    return {
      mode: mode,
      cantrips: cantrips,
      cantripLimit: limits.cantripsKnown,
      knownLevelled: knownLevelled,
      knownLimit: limits.spellsKnown,
      preparedLevelled: preparedLevelled,
      preparedLimit: limits.preparedLimit,
    };
  }

  function groupedCards(data, draft) {
    var cards = asArray(data && data.cards);
    var limits = asObject(data && data.limits);
    var highest = parseInt(data && data.highestUnlockedSpellLevel, 10);
    if (!Number.isFinite(highest) || highest < 0) highest = 0;
    var mode = getMode(limits);

    var groups = {};
    cards.forEach(function mapCard(card) {
      var lvl = parseInt(card && card.level, 10);
      if (!Number.isFinite(lvl) || lvl < 0) lvl = 0;
      var selected = !!(card && (card.isKnown || card.isPrepared));
      if (lvl > 0 && highest > 0 && lvl > highest && !selected) return;
      if (!groups[lvl]) groups[lvl] = [];
      groups[lvl].push(card);
    });

    var keys = Object.keys(groups).map(function(v) { return parseInt(v, 10); }).filter(Number.isFinite).sort(function(a, b) { return a - b; });
    if (keys.indexOf(0) === -1) {
      var hasCantrips = cards.some(function(c) { return parseInt(c && c.level, 10) === 0; });
      if (hasCantrips) keys.unshift(0);
    }

    return {
      groups: groups,
      levelKeys: keys,
      highest: highest,
      mode: mode,
      levelCapLabel: highest > 0 ? levelLabel(highest) : 'Cantrips only',
      className: String(limits.className || asObject(draft && draft.class).id || '').trim(),
    };
  }

  function renderSelectedChips(spellbook, cardById, mode) {
    var known = asArray(spellbook && spellbook.known);
    var prepared = asArray(spellbook && spellbook.prepared);

    function chips(ids, listKey, title, includeLevelledOnly) {
      var visibleIds = ids.filter(function(id) {
        var level = parseInt(cardById[id] && cardById[id].level, 10);
        if (includeLevelledOnly) return level > 0;
        return true;
      });
      if (!visibleIds.length) return '';
      return '<h4>' + escHtml(title) + '</h4><div class="cb-spell-chip-row">' + visibleIds.map(function(id) {
        var row = cardById[id] || {};
        var name = String(row.displayName || row.name || id).trim() || id;
        return '<span class="cb-spell-chip" data-builder-spell-remove="' + escHtml(id) + '" data-builder-spell-remove-list="' + escHtml(listKey) + '">' +
          escHtml(name) +
          '<button type="button" aria-label="Remove ' + escHtml(name) + '">×</button>' +
        '</span>';
      }).join('') + '</div>';
    }

    var out = '';
    out += chips(known, 'known', mode === 'prepared' ? 'Known Cantrips' : 'Known Spells', mode === 'prepared');
    if (mode === 'prepared') {
      out += chips(prepared, 'prepared', 'Prepared Spells', true);
    }
    return out || '<div class="builder-help-text" style="margin:0">No spells selected yet.</div>';
  }

  function renderSpellCard(card, selected, blocked, reason) {
    var id = String(card && card.id || '').trim();
    var spellName = String(card && (card.displayName || card.name || id) || 'Spell');
    var meta = [card && card.school, card && card.castingTime, card && card.range].filter(Boolean);
    var stateLabel = String(card && card.stateLabel || '').trim();
    if (stateLabel) meta.push(stateLabel);

    var classes = ['cb-spell-card'];
    if (selected) classes.push('selected');
    if (blocked) classes.push('blocked');

    return [
      '<article class="' + classes.join(' ') + '"',
      ' data-builder-spell-id="' + escHtml(id) + '"',
      ' data-builder-spell-level="' + escHtml(String(parseInt(card && card.level, 10) || 0)) + '"',
      ' data-builder-spell-search="' + escHtml([spellName, card && card.description, card && card.summary, card && card.school].join(' ').toLowerCase()) + '"',
      ' data-builder-spell-blocked="' + (blocked ? '1' : '0') + '">',
      '<div class="cb-spell-head"><div class="cb-spell-name">' + escHtml(spellName) + '</div><span class="cb-spell-badge">' + escHtml(levelLabel(card && card.level)) + '</span></div>',
      '<div class="cb-spell-meta">' + (meta.length ? meta.map(function(m) { return '<span>' + escHtml(m) + '</span>'; }).join('') : '<span>No metadata</span>') + '</div>',
      '<div class="cb-spell-desc">' + escHtml(String(card && (card.summary || card.description) || 'No details available.')) + '</div>',
      reason ? '<div class="cb-spell-reason">' + escHtml(reason) + '</div>' : '',
      '</article>',
    ].join('');
  }

  function render(context) {
    ensureStyles();
    var draft = asObject(context && context.draft);
    var classData = asObject(draft.class);
    var progression = asObject(draft.progression);
    var classId = String(classData.id || '').trim();
    if (!classId) {
      return '<div class="builder-help-text">Pick a class first to configure spellcasting.</div>';
    }

    var key = buildRequestKey(draft);
    if (_state.cacheKey !== key || !_state.data) {
      fetchOptions(draft);
    }

    var data = _state.cacheKey === key ? _state.data : null;
    var loading = _state.cacheKey === key ? _state.loading : true;
    if (loading && !data) {
      return '<div class="loading-msg" style="text-align:left;padding:0">Loading spell options…</div>';
    }

    var spellbook = asObject(draft.spellbook);
    var structured = groupedCards(data, draft);
    var groups = structured.groups;
    var levelKeys = structured.levelKeys;
    var counts = selectedCounts(data, spellbook);
    var cardById = indexCards(data && data.cards);
    var activeLevel = _state.activeLevelByKey[key];
    if (levelKeys.indexOf(activeLevel) === -1) activeLevel = levelKeys.length ? levelKeys[0] : 0;
    _state.activeLevelByKey[key] = activeLevel;

    var searchValue = String(_state.searchByKey[key] || '').trim();
    var status = String(_state.statusByKey[key] || '').trim();
    var statusTone = status.indexOf('Limit reached') >= 0 || status.indexOf('locked') >= 0 ? ' warn' : '';

    return [
      '<div class="screen-header">',
      '<div class="screen-title">Spells</div>',
      '<div class="screen-divider"></div>',
      '<div class="screen-subtitle">Select spells exactly like the spellbook flow: legal tiers only, clear counts, and hard cap enforcement.</div>',
      '</div>',
      '<div class="cb-spells-shell">',
      '<div class="cb-spells-topline">',
      '<div class="cb-spells-count"><span class="k">Class</span><span class="v">' + escHtml(structured.className || classId) + ' Lv ' + escHtml(String(parseInt(progression.level, 10) || 1)) + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Cantrips</span><span class="v">' + escHtml(String(counts.cantrips)) + (counts.cantripLimit != null ? (' / ' + escHtml(String(counts.cantripLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Known</span><span class="v">' + escHtml(String(counts.knownLevelled)) + (counts.knownLimit != null ? (' / ' + escHtml(String(counts.knownLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Prepared</span><span class="v">' + escHtml(String(counts.preparedLevelled)) + (counts.preparedLimit != null ? (' / ' + escHtml(String(counts.preparedLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Unlocked Tier</span><span class="v">' + escHtml(structured.levelCapLabel) + '</span></div>',
      '</div>',
      '<div class="cb-spells-status' + statusTone + '">' + escHtml(status) + '</div>',
      '<div class="cb-spells-selected">' + renderSelectedChips(spellbook, cardById, structured.mode) + '</div>',
      '<div class="cb-spells-toolbar">',
      '<div class="builder-help-text" style="margin:0">Click a card to select/unselect. Remove chips to quickly undo.</div>',
      '<input type="search" class="cb-spells-search" data-builder-spell-search-input="1" value="' + escHtml(searchValue) + '" placeholder="Search unlocked spells…" />',
      '</div>',
      '<div class="cb-spells-tabs">',
      levelKeys.length
        ? levelKeys.map(function(level) {
            return '<button type="button" class="cb-spells-tab' + (level === activeLevel ? ' active' : '') + '" data-builder-spell-tab="' + escHtml(String(level)) + '">' + escHtml(levelLabel(level)) + '</button>';
          }).join('')
        : '<span class="builder-help-text">No legal spell tiers available for this class and level.</span>',
      '</div>',
      levelKeys.map(function(level) {
        var rows = asArray(groups[level]);
        var filteredRows = rows.filter(function(card) {
          if (!searchValue) return true;
          var hay = String([card && card.displayName, card && card.description, card && card.summary, card && card.school].join(' ')).toLowerCase();
          return hay.indexOf(searchValue.toLowerCase()) >= 0;
        });
        return '<section class="cb-spells-group' + (level === activeLevel ? ' active' : '') + '" data-builder-spell-group="' + escHtml(String(level)) + '">' +
          (filteredRows.length ? filteredRows.map(function(card) {
            var spellId = String(card && card.id || '').trim();
            var spellLevel = parseInt(card && card.level, 10) || 0;
            var isSelected = spellLevel === 0
              ? asArray(spellbook.known).indexOf(spellId) >= 0
              : (structured.mode === 'prepared'
                ? asArray(spellbook.prepared).indexOf(spellId) >= 0
                : asArray(spellbook.known).indexOf(spellId) >= 0);
            var cardBlocked = card && card.isAccessible === false && !isSelected;
            var blockedReason = cardBlocked ? (card.blockedReason || 'This spell is currently locked.') : '';
            return renderSpellCard(card, isSelected, cardBlocked, blockedReason);
          }).join('') : '<div class="builder-help-text">No spells match the current search for this tier.</div>') +
        '</section>';
      }).join(''),
      '</div>',
    ].join('');
  }

  function bind(root, context) {
    if (!root || !context || typeof context.onSetField !== 'function') return;
    var draft = asObject(context.draft);
    var key = buildRequestKey(draft);

    if ((_state.cacheKey !== key || !_state.data) && _state.pendingRerenderKey !== key) {
      _state.pendingRerenderKey = key;
      fetchOptions(draft).then(function done() {
        _state.pendingRerenderKey = '';
        if (!root.isConnected) return;
        var currentKnown = asArray(asObject(context.draft && context.draft.spellbook).known).slice();
        context.onSetField(['spellbook', 'known'], currentKnown);
      });
    }

    function commit(nextKnown, nextPrepared, statusMsg) {
      _state.statusByKey[key] = statusMsg || '';
      context.onSetField(['spellbook', 'known'], nextKnown);
      context.onSetField(['spellbook', 'prepared'], nextPrepared);
    }

    function cardById() {
      return indexCards(_state.data && _state.data.cards);
    }

    function toggleSpell(spellId, spellLevel) {
      var spellbook = asObject(context.draft && context.draft.spellbook);
      var known = asArray(spellbook.known).slice();
      var prepared = asArray(spellbook.prepared).slice();
      var limits = asObject(_state.data && _state.data.limits);
      var mode = getMode(limits);
      var counts = selectedCounts(_state.data, spellbook);

      if (spellLevel === 0) {
        var knownIdx = known.indexOf(spellId);
        if (knownIdx >= 0) {
          known.splice(knownIdx, 1);
          prepared = prepared.filter(function(id) { return id !== spellId; });
          commit(known, prepared, 'Cantrip removed.');
          return;
        }
        if (counts.cantripLimit != null && counts.cantrips >= parseInt(counts.cantripLimit, 10)) {
          commit(known, prepared, 'Limit reached: cantrip cap is ' + counts.cantripLimit + '.');
          return;
        }
        known.push(spellId);
        commit(known, prepared, 'Cantrip learned.');
        return;
      }

      if (mode === 'prepared') {
        var prepIdx = prepared.indexOf(spellId);
        if (prepIdx >= 0) {
          prepared.splice(prepIdx, 1);
          commit(known, prepared, 'Spell unprepared.');
          return;
        }
        if (counts.preparedLimit != null && counts.preparedLevelled >= parseInt(counts.preparedLimit, 10)) {
          commit(known, prepared, 'Limit reached: prepared cap is ' + counts.preparedLimit + '.');
          return;
        }
        prepared.push(spellId);
        commit(known, prepared, 'Spell prepared.');
        return;
      }

      var knownIdxLevelled = known.indexOf(spellId);
      if (knownIdxLevelled >= 0) {
        known.splice(knownIdxLevelled, 1);
        prepared = prepared.filter(function(id) { return id !== spellId; });
        commit(known, prepared, 'Spell removed.');
        return;
      }
      if (counts.knownLimit != null && counts.knownLevelled >= parseInt(counts.knownLimit, 10)) {
        commit(known, prepared, 'Limit reached: known cap is ' + counts.knownLimit + '.');
        return;
      }
      known.push(spellId);
      commit(known, prepared, 'Spell learned.');
    }

    root.querySelectorAll('[data-builder-spell-tab]').forEach(function(tabEl) {
      tabEl.addEventListener('click', function onTabClick() {
        _state.activeLevelByKey[key] = parseInt(tabEl.dataset.builderSpellTab, 10) || 0;
        var known = asArray(asObject(context.draft && context.draft.spellbook).known).slice();
        context.onSetField(['spellbook', 'known'], known);
      });
    });

    var searchInput = root.querySelector('[data-builder-spell-search-input="1"]');
    if (searchInput) {
      searchInput.addEventListener('input', function onSearch() {
        _state.searchByKey[key] = String(searchInput.value || '');
        var known = asArray(asObject(context.draft && context.draft.spellbook).known).slice();
        context.onSetField(['spellbook', 'known'], known);
      });
    }

    root.querySelectorAll('[data-builder-spell-remove]').forEach(function(chipEl) {
      chipEl.addEventListener('click', function onRemove(evt) {
        evt.preventDefault();
        evt.stopPropagation();
        var spellId = String(chipEl.dataset.builderSpellRemove || '').trim();
        var listKey = String(chipEl.dataset.builderSpellRemoveList || 'known').trim();
        if (!spellId || (listKey !== 'known' && listKey !== 'prepared')) return;

        var spellbook = asObject(context.draft && context.draft.spellbook);
        var known = asArray(spellbook.known).slice().filter(function(id) { return id !== spellId; });
        var prepared = asArray(spellbook.prepared).slice();
        if (listKey === 'prepared' || listKey === 'known') {
          prepared = prepared.filter(function(id) { return id !== spellId; });
        }
        commit(known, prepared, 'Spell removed.');
      });
    });

    root.querySelectorAll('[data-builder-spell-id]').forEach(function(cardEl) {
      cardEl.addEventListener('click', function onSpellCardClick() {
        if (String(cardEl.dataset.builderSpellBlocked || '') === '1') {
          _state.statusByKey[key] = 'This spell is locked for your current class level.';
          var known = asArray(asObject(context.draft && context.draft.spellbook).known).slice();
          context.onSetField(['spellbook', 'known'], known);
          return;
        }
        var spellId = String(cardEl.dataset.builderSpellId || '').trim();
        var spellLevel = parseInt(cardEl.dataset.builderSpellLevel, 10) || 0;
        var spell = cardById()[spellId];
        if (!spellId || !spell) return;
        toggleSpell(spellId, spellLevel);
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
