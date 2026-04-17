(function initCharacterBuilderStepSpells(global) {
  'use strict';

  var _state = {
    cacheByKey: {},
    inflightByKey: {},
    activeTabByKey: {},
    searchByKey: {},
    statusByKey: {},
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

  function requestKey(draft) {
    var cls = asObject(draft && draft.class);
    var progression = asObject(draft && draft.progression);
    return [norm(cls.id), norm(cls.subclassId), parseInt(progression.level, 10) || 1].join('|');
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

  function fetchOptions(draft) {
    var cls = asObject(draft && draft.class);
    var classId = String(cls.id || '').trim();
    if (!classId) return Promise.resolve(null);
    var progression = asObject(draft && draft.progression);
    var key = requestKey(draft);
    if (_state.cacheByKey[key]) return Promise.resolve(_state.cacheByKey[key]);
    if (_state.inflightByKey[key]) return _state.inflightByKey[key];

    var spellbook = asObject(draft && draft.spellbook);
    var params = new URLSearchParams();
    params.set('class_id', classId);
    params.set('subclass_id', String(cls.subclassId || '').trim());
    params.set('level', String(parseInt(progression.level, 10) || 1));
    params.set('known', dedupeIds(spellbook.known).join(','));
    params.set('prepared', dedupeIds(spellbook.prepared).join(','));

    _state.inflightByKey[key] = fetch('/api/character/builder/spells/options?' + params.toString(), { credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('spell_options_failed');
        return res.json();
      })
      .then(function (payload) {
        _state.cacheByKey[key] = payload || null;
        return _state.cacheByKey[key];
      })
      .catch(function () {
        _state.cacheByKey[key] = null;
        return null;
      })
      .finally(function () {
        _state.inflightByKey[key] = null;
      });

    return _state.inflightByKey[key];
  }

  function modeFromLimits(limits) {
    if (limits && limits.preparedLimit != null) return 'prepared';
    if (limits && (limits.spellsKnown != null || limits.cantripsKnown != null)) return 'known';
    return 'library';
  }

  function indexCards(cards) {
    var out = {};
    asArray(cards).forEach(function (card) {
      var id = String(card && card.id || '').trim();
      if (id) out[id] = card;
    });
    return out;
  }

  function currentSelection(draft, data) {
    var validation = asObject(data && data.validation);
    if (Array.isArray(validation.known) || Array.isArray(validation.prepared)) {
      return { known: dedupeIds(validation.known), prepared: dedupeIds(validation.prepared) };
    }
    var spellbook = asObject(draft && draft.spellbook);
    return { known: dedupeIds(spellbook.known), prepared: dedupeIds(spellbook.prepared) };
  }

  function countsForSelection(data, selected) {
    var limits = asObject(data && data.limits);
    var cardById = indexCards(data && data.cards);
    var cantrips = selected.known.filter(function (id) { return parseInt(cardById[id] && cardById[id].level, 10) === 0; }).length;
    var knownLevelled = selected.known.filter(function (id) { return parseInt(cardById[id] && cardById[id].level, 10) > 0; }).length;
    var preparedLevelled = selected.prepared.filter(function (id) { return parseInt(cardById[id] && cardById[id].level, 10) > 0; }).length;
    return {
      mode: modeFromLimits(limits),
      cantrips: cantrips,
      knownLevelled: knownLevelled,
      preparedLevelled: preparedLevelled,
      cantripLimit: limits.cantripsKnown,
      knownLimit: limits.spellsKnown,
      preparedLimit: limits.preparedLimit,
    };
  }

  function renderCard(card, selected, blocked, reason) {
    var spellId = String(card && card.id || '').trim();
    var spellName = String(card && (card.displayName || card.name || spellId) || 'Spell');
    var classes = ['cb-spell-card'];
    if (selected) classes.push('selected');
    if (blocked) classes.push('blocked');
    return [
      '<article class="' + classes.join(' ') + '" data-builder-spell-id="' + escHtml(spellId) + '" data-builder-spell-level="' + escHtml(String(parseInt(card && card.level, 10) || 0)) + '" data-builder-spell-blocked="' + (blocked ? '1' : '0') + '">',
      '<div class="cb-spell-head"><div class="cb-spell-name">' + escHtml(spellName) + '</div><span class="cb-spell-badge">' + escHtml(levelLabel(card && card.level)) + '</span></div>',
      '<div class="cb-spell-meta"><span>' + escHtml(String(card && card.school || '')) + '</span><span>' + escHtml(String(card && card.castingTime || '')) + '</span><span>' + escHtml(String(card && card.range || '')) + '</span></div>',
      '<div class="cb-spell-desc">' + escHtml(String(card && (card.summary || card.description) || 'No details available.')) + '</div>',
      reason ? '<div class="cb-spell-reason">' + escHtml(reason) + '</div>' : '',
      '</article>'
    ].join('');
  }

  function setSelection(context, known, prepared, status) {
    var knownNext = dedupeIds(known);
    var preparedNext = dedupeIds(prepared);
    context.onSetField(['spellbook', 'known'], knownNext);
    context.onSetField(['spellbook', 'prepared'], preparedNext);
    _state.statusByKey[requestKey(context.draft)] = status || '';
  }

  function render(context) {
    ensureStyles();
    var draft = asObject(context && context.draft);
    var classId = String(asObject(draft.class).id || '').trim();
    if (!classId) return '<div class="builder-help-text">Pick a class first to configure spellcasting.</div>';

    var key = requestKey(draft);
    if (!_state.cacheByKey[key] && !_state.inflightByKey[key]) fetchOptions(draft);
    var data = _state.cacheByKey[key];
    if (_state.inflightByKey[key] && !data) return '<div class="loading-msg" style="text-align:left;padding:0">Loading spell options…</div>';
    if (!data) return '<div class="builder-help-text">Could not load spell options. Re-open this step after checking class/subclass selections.</div>';

    var selected = currentSelection(draft, data);
    var counts = countsForSelection(data, selected);
    var mode = counts.mode;
    var cards = asArray(data.cards);
    var cardById = indexCards(cards);
    var highestUnlocked = parseInt(data.highestUnlockedSpellLevel, 10);
    if (!Number.isFinite(highestUnlocked) || highestUnlocked < 0) highestUnlocked = 0;

    var groups = {};
    cards.forEach(function (card) {
      var lvl = parseInt(card && card.level, 10);
      if (!Number.isFinite(lvl) || lvl < 0) lvl = 0;
      var id = String(card && card.id || '').trim();
      var selectedNow = selected.known.indexOf(id) >= 0 || selected.prepared.indexOf(id) >= 0;
      if (lvl > 0 && lvl > highestUnlocked && !selectedNow) return;
      if (!groups[lvl]) groups[lvl] = [];
      groups[lvl].push(card);
    });
    var levels = Object.keys(groups).map(function (v) { return parseInt(v, 10); }).filter(function (v) { return Number.isFinite(v); }).sort(function (a, b) { return a - b; });
    var activeLevel = _state.activeTabByKey[key];
    if (levels.indexOf(activeLevel) < 0) activeLevel = levels.length ? levels[0] : 0;
    _state.activeTabByKey[key] = activeLevel;

    var search = String(_state.searchByKey[key] || '').trim().toLowerCase();
    var status = String(_state.statusByKey[key] || '').trim();
    var statusTone = /limit reached|locked|illegal|only|not unlocked/i.test(status) ? ' warn' : '';

    var knownChips = selected.known.map(function (id) { return cardById[id]; }).filter(Boolean);
    var preparedChips = selected.prepared.map(function (id) { return cardById[id]; }).filter(Boolean);

    return [
      '<div class="screen-header"><div class="screen-title">Spells</div><div class="screen-divider"></div><div class="screen-subtitle">Only legal class spells and unlocked tiers are shown. Invalid stale picks are auto-cleaned.</div></div>',
      '<div class="cb-spells-shell">',
      '<div class="cb-spells-topline">',
      '<div class="cb-spells-count"><span class="k">Class</span><span class="v">' + escHtml(String((asObject(data.limits).className || classId))) + ' Lv ' + escHtml(String(parseInt(asObject(draft.progression).level, 10) || 1)) + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Cantrips</span><span class="v">' + escHtml(String(counts.cantrips)) + (counts.cantripLimit != null ? (' / ' + escHtml(String(counts.cantripLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Known</span><span class="v">' + escHtml(String(counts.knownLevelled)) + (counts.knownLimit != null ? (' / ' + escHtml(String(counts.knownLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Prepared</span><span class="v">' + escHtml(String(counts.preparedLevelled)) + (counts.preparedLimit != null ? (' / ' + escHtml(String(counts.preparedLimit))) : '') + '</span></div>',
      '<div class="cb-spells-count"><span class="k">Unlocked Tier</span><span class="v">' + escHtml(highestUnlocked > 0 ? levelLabel(highestUnlocked) : 'Cantrips only') + '</span></div>',
      '</div>',
      '<div class="cb-spells-status' + statusTone + '">' + escHtml(status) + '</div>',
      '<div class="cb-spells-selected">',
      knownChips.length ? ('<h4>' + escHtml(mode === 'prepared' ? 'Known Cantrips / Always Known' : 'Known Spells') + '</h4><div class="cb-spell-chip-row">' + knownChips.map(function (row) { return '<span class="cb-spell-chip" data-builder-spell-remove="' + escHtml(String(row.id || '')) + '">' + escHtml(String(row.displayName || row.name || row.id || '')) + '<button type="button">×</button></span>'; }).join('') + '</div>') : '',
      mode === 'prepared' && preparedChips.length ? ('<h4>Prepared Spells</h4><div class="cb-spell-chip-row">' + preparedChips.map(function (row) { return '<span class="cb-spell-chip" data-builder-spell-remove="' + escHtml(String(row.id || '')) + '">' + escHtml(String(row.displayName || row.name || row.id || '')) + '<button type="button">×</button></span>'; }).join('') + '</div>') : '',
      (!knownChips.length && !preparedChips.length) ? '<div class="builder-help-text" style="margin:0">No spells selected yet.</div>' : '',
      '</div>',
      '<div class="cb-spells-toolbar"><div class="builder-help-text" style="margin:0">Click cards to select. Bonus/granted spells remain legal and do not consume manual prepared slots.</div><input type="search" class="cb-spells-search" data-builder-spell-search-input="1" value="' + escHtml(search) + '" placeholder="Search legal spells…" /></div>',
      '<div class="cb-spells-tabs">',
      levels.map(function (lvl) { return '<button type="button" class="cb-spells-tab' + (lvl === activeLevel ? ' active' : '') + '" data-builder-spell-tab="' + escHtml(String(lvl)) + '">' + escHtml(levelLabel(lvl)) + '</button>'; }).join(''),
      '</div>',
      levels.map(function (lvl) {
        var rows = asArray(groups[lvl]).filter(function (card) {
          if (!search) return true;
          var hay = String([card && card.displayName, card && card.summary, card && card.description, card && card.school].join(' ')).toLowerCase();
          return hay.indexOf(search) >= 0;
        });
        var html = rows.length ? rows.map(function (card) {
          var id = String(card && card.id || '').trim();
          var spellLevel = parseInt(card && card.level, 10) || 0;
          var isSelected = spellLevel === 0
            ? selected.known.indexOf(id) >= 0
            : (mode === 'prepared' ? selected.prepared.indexOf(id) >= 0 : selected.known.indexOf(id) >= 0);
          var blocked = !isSelected && card && card.isAccessible === false;
          return renderCard(card, isSelected, blocked, blocked ? (card.blockedReason || 'Not unlocked at current level.') : '');
        }).join('') : '<div class="builder-help-text">No spells match this filter.</div>';
        return '<section class="cb-spells-group' + (lvl === activeLevel ? ' active' : '') + '" data-builder-spell-group="' + escHtml(String(lvl)) + '">' + html + '</section>';
      }).join(''),
      '</div>'
    ].join('');
  }

  function bind(root, context) {
    if (!root || !context || typeof context.onSetField !== 'function') return;
    var draft = asObject(context.draft);
    var key = requestKey(draft);

    fetchOptions(draft).then(function (data) {
      if (!data || !root.isConnected) return;
      var validation = asObject(data.validation);
      setSelection(context, asArray(validation.known), asArray(validation.prepared), '');
    });

    function withData(fn) {
      var data = _state.cacheByKey[key];
      if (data) return fn(data);
      fetchOptions(context.draft).then(function (fresh) { if (fresh) fn(fresh); });
    }

    function toggleSpell(spellId, level) {
      withData(function (data) {
        var selected = currentSelection(context.draft, data);
        var counts = countsForSelection(data, selected);
        var mode = counts.mode;
        var known = selected.known.slice();
        var prepared = selected.prepared.slice();

        if (level === 0) {
          if (known.indexOf(spellId) >= 0) {
            setSelection(context, known.filter(function (id) { return id !== spellId; }), prepared.filter(function (id) { return id !== spellId; }), 'Cantrip removed.');
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
            setSelection(context, known, prepared.filter(function (id) { return id !== spellId; }), 'Spell unprepared.');
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
          setSelection(context, known.filter(function (id) { return id !== spellId; }), prepared.filter(function (id) { return id !== spellId; }), 'Spell removed.');
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
        _state.activeTabByKey[key] = parseInt(btn.getAttribute('data-builder-spell-tab'), 10) || 0;
        _state.statusByKey[key] = '';
      });
    });

    var searchInput = root.querySelector('[data-builder-spell-search-input="1"]');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        _state.searchByKey[key] = String(searchInput.value || '');
      });
    }

    root.querySelectorAll('[data-builder-spell-remove]').forEach(function (chip) {
      chip.addEventListener('click', function (event) {
        event.preventDefault();
        var spellId = String(chip.getAttribute('data-builder-spell-remove') || '').trim();
        if (!spellId) return;
        var current = asObject(context.draft && context.draft.spellbook);
        setSelection(
          context,
          dedupeIds(current.known).filter(function (id) { return id !== spellId; }),
          dedupeIds(current.prepared).filter(function (id) { return id !== spellId; }),
          'Spell removed.'
        );
      });
    });

    root.querySelectorAll('[data-builder-spell-id]').forEach(function (card) {
      card.addEventListener('click', function () {
        if (String(card.getAttribute('data-builder-spell-blocked') || '') === '1') {
          _state.statusByKey[key] = 'This spell is not unlocked for the current class/level.';
          return;
        }
        var spellId = String(card.getAttribute('data-builder-spell-id') || '').trim();
        var level = parseInt(card.getAttribute('data-builder-spell-level'), 10) || 0;
        if (spellId) toggleSpell(spellId, level);
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
