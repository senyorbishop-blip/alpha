(function initCharacterBuilderStepSpells(global) {
  var _state = {
    key: '',
    data: null,
    loading: false,
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

  function normalizeId(value) {
    return String(value || '').trim().toLowerCase();
  }

  function ensureStyles() {
    if (document.getElementById('character-builder-step-spells-style')) return;
    var style = document.createElement('style');
    style.id = 'character-builder-step-spells-style';
    style.textContent = [
      '.cb-spell-shell{border:1px solid rgba(91,163,208,.25);border-radius:12px;padding:10px 12px;background:rgba(8,14,22,.78)}',
      '.cb-spell-counts{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}',
      '.cb-spell-pill{font-size:.6rem;border:1px solid rgba(91,163,208,.28);border-radius:999px;padding:3px 8px;background:rgba(0,0,0,.2);color:#c9ecff}',
      '.cb-spell-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}',
      '.cb-spell-tab{font-size:.6rem;padding:4px 8px;border-radius:999px;border:1px solid rgba(201,168,76,.3);background:rgba(0,0,0,.3);color:#e4d2a3;cursor:pointer}',
      '.cb-spell-tab.active{background:rgba(201,168,76,.18);border-color:rgba(201,168,76,.75);color:#ffe4a1}',
      '.cb-spell-group{display:none}',
      '.cb-spell-group.active{display:block}',
      '.cb-spell-card{padding:8px 10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(0,0,0,.22);margin-bottom:8px;cursor:pointer}',
      '.cb-spell-card:hover{border-color:rgba(91,163,208,.55)}',
      '.cb-spell-card.selected{border-color:rgba(0,229,204,.85);background:rgba(0,229,204,.12)}',
      '.cb-spell-card.blocked{opacity:.55;cursor:not-allowed}',
      '.cb-spell-name{font-size:.72rem;color:#e8f6ff;font-weight:600}',
      '.cb-spell-meta{font-size:.58rem;color:rgba(194,227,221,.88);margin-top:3px;display:flex;gap:8px;flex-wrap:wrap}',
      '.cb-spell-desc{font-size:.58rem;color:rgba(205,219,232,.84);margin-top:5px;line-height:1.45}',
      '.cb-spell-toolbar{display:flex;gap:8px;align-items:center;justify-content:space-between;margin-bottom:10px}',
      '.cb-spell-search{max-width:260px;width:100%}',
      '.cb-spell-detail{font-size:.6rem;color:rgba(210,220,230,.88);margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.08)}',
    ].join('');
    document.head.appendChild(style);
  }

  function levelLabel(level) {
    if (level === 0) return 'Cantrips';
    if (level === 1) return '1st';
    if (level === 2) return '2nd';
    if (level === 3) return '3rd';
    return level + 'th';
  }

  function parseLevel(key) {
    var val = parseInt(key, 10);
    return Number.isFinite(val) ? val : 0;
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function toCsv(rows) {
    return asArray(rows).map(function(v){ return String(v || '').trim(); }).filter(Boolean).join(', ');
  }

  function buildRequestKey(draft) {
    var classData = draft.class && typeof draft.class === 'object' ? draft.class : {};
    var progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
    var spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
    return [
      normalizeId(classData.id),
      normalizeId(classData.subclassId),
      parseInt(progression.level, 10) || 1,
      toCsv(spellbook.known),
      toCsv(spellbook.prepared),
    ].join('|');
  }

  function fetchOptions(draft) {
    var classData = draft.class && typeof draft.class === 'object' ? draft.class : {};
    var progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
    var spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
    var classId = String(classData.id || '').trim();
    if (!classId) {
      _state = { key: '', data: null, loading: false };
      return Promise.resolve(null);
    }
    var q = new URLSearchParams();
    q.set('class_id', classId);
    q.set('subclass_id', String(classData.subclassId || '').trim());
    q.set('level', String(parseInt(progression.level, 10) || 1));
    q.set('known', toCsv(spellbook.known));
    q.set('prepared', toCsv(spellbook.prepared));
    var key = buildRequestKey(draft);
    if (_state.data && _state.key === key) return Promise.resolve(_state.data);
    _state.loading = true;
    return fetch('/api/character/builder/spells/options?' + q.toString(), { credentials: 'same-origin' })
      .then(function(res) {
        if (!res.ok) throw new Error('spell_options_failed');
        return res.json();
      })
      .then(function(data) {
        _state = { key: key, data: data || null, loading: false };
        return _state.data;
      })
      .catch(function() {
        _state = { key: key, data: null, loading: false };
        return null;
      });
  }

  function groupCards(cards, highestUnlocked) {
    var groups = {};
    asArray(cards).forEach(function(card) {
      var level = parseInt(card && card.level, 10);
      if (!Number.isFinite(level) || level < 0) level = 0;
      if (level > 0 && highestUnlocked > 0 && level > highestUnlocked) return;
      if (!groups[level]) groups[level] = [];
      groups[level].push(card);
    });
    return groups;
  }

  function getCounts(data) {
    var validation = data && typeof data.validation === 'object' ? data.validation : {};
    var limits = data && typeof data.limits === 'object' ? data.limits : {};
    var known = asArray(validation.known);
    var prepared = asArray(validation.prepared);
    var cardsById = {};
    asArray(data && data.cards).forEach(function(card) {
      var id = String(card && card.id || '').trim();
      if (id) cardsById[id] = card;
    });

    var cantripsKnown = known.filter(function(id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) === 0;
    }).length;
    var levelledKnown = known.filter(function(id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) > 0;
    }).length;
    var preparedLevelled = prepared.filter(function(id) {
      return parseInt(cardsById[id] && cardsById[id].level, 10) > 0;
    }).length;

    return {
      cantripsKnown: cantripsKnown,
      cantripsMax: limits.cantripsKnown,
      spellsKnown: levelledKnown,
      spellsKnownMax: limits.spellsKnown,
      preparedCount: preparedLevelled,
      preparedMax: limits.preparedLimit,
    };
  }

  registerStep({
    id: 'spells',
    label: 'Spells',
    render: function renderSpellsStep(context) {
      ensureStyles();
      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
      fetchOptions(draft);
      var data = _state.data;
      var loading = _state.loading;

      var limits = data && typeof data.limits === 'object' ? data.limits : {};
      var counts = getCounts(data);
      var highestUnlocked = parseInt(data && data.highestUnlockedSpellLevel, 10) || 0;
      var cards = asArray(data && data.cards);
      var grouped = groupCards(cards, highestUnlocked);
      var levelKeys = Object.keys(grouped).map(parseLevel).sort(function(a, b) { return a - b; });
      var activeLevel = levelKeys.length ? levelKeys[0] : 0;

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Choose Your Spells</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Character-aware spell rules are enforced live based on class, subclass, and level.</div>',
        '</div>',
        '<div class="cb-spell-shell">',
        '<div class="cb-spell-counts">',
        '<span class="cb-spell-pill">Cantrips: ' + escHtml(String(counts.cantripsKnown)) + (counts.cantripsMax != null ? (' / ' + escHtml(String(counts.cantripsMax))) : '') + '</span>',
        '<span class="cb-spell-pill">Known: ' + escHtml(String(counts.spellsKnown)) + (counts.spellsKnownMax != null ? (' / ' + escHtml(String(counts.spellsKnownMax))) : '') + '</span>',
        '<span class="cb-spell-pill">Prepared: ' + escHtml(String(counts.preparedCount)) + (counts.preparedMax != null ? (' / ' + escHtml(String(counts.preparedMax))) : '') + '</span>',
        '<span class="cb-spell-pill">Max spell tier: ' + escHtml(highestUnlocked > 0 ? levelLabel(highestUnlocked) : 'Cantrips only') + '</span>',
        '</div>',
        '<div class="cb-spell-toolbar">',
        '<input type="search" class="cb-spell-search" data-builder-spell-search="1" placeholder="Search unlocked spells…" />',
        '<div class="builder-help-text" style="margin:0;">Click a spell card to add/remove it.</div>',
        '</div>',
        '<div class="cb-spell-tabs">',
        levelKeys.map(function(level) {
          return '<button type="button" class="cb-spell-tab' + (level === activeLevel ? ' active' : '') + '" data-spell-level-tab="' + escHtml(String(level)) + '">' + escHtml(levelLabel(level)) + '</button>';
        }).join('') || '<span class="builder-help-text">No legal spell levels available for current class/level.</span>',
        '</div>',
        levelKeys.map(function(level) {
          var rows = grouped[level] || [];
          return '<section class="cb-spell-group' + (level === activeLevel ? ' active' : '') + '" data-spell-level-group="' + escHtml(String(level)) + '">'
            + (rows.map(function(card) {
              var id = String(card && card.id || '').trim();
              var selected = !!(card && (card.isKnown || card.isPrepared));
              var blocked = card && card.isAccessible === false;
              var classes = ['cb-spell-card'];
              if (selected) classes.push('selected');
              if (blocked) classes.push('blocked');
              return '<article class="' + classes.join(' ') + '"'
                + ' data-spell-id="' + escHtml(id) + '"'
                + ' data-spell-level="' + escHtml(String(level)) + '"'
                + ' data-spell-selected="' + (selected ? '1' : '0') + '"'
                + ' data-spell-search="' + escHtml(String([card.displayName, card.school, card.description, card.summary].join(' ')).toLowerCase()) + '"'
                + ' data-spell-accessible="' + (blocked ? '0' : '1') + '">'
                + '<div class="cb-spell-name">' + escHtml(card.displayName || card.name || id || 'Spell') + '</div>'
                + '<div class="cb-spell-meta"><span>' + escHtml(card.school || '—') + '</span><span>' + escHtml(card.castingTime || '—') + '</span><span>' + escHtml(card.range || '—') + '</span>' + (card.stateLabel ? '<span>' + escHtml(card.stateLabel) + '</span>' : '') + '</div>'
                + '<div class="cb-spell-desc">' + escHtml(card.summary || card.description || 'No details available.') + '</div>'
                + (blocked && card.blockedReason ? '<div class="cb-spell-detail">Locked: ' + escHtml(card.blockedReason) + '</div>' : '')
                + '</article>';
            }).join('') || '<div class="builder-help-text">No legal spells in this tier.</div>')
            + '</section>';
        }).join(''),
        '<div class="cb-spell-detail">',
        '<div><strong>Known IDs:</strong> <span data-spell-known-display="1">' + escHtml(toCsv(spellbook.known)) + '</span></div>',
        '<div><strong>Prepared IDs:</strong> <span data-spell-prepared-display="1">' + escHtml(toCsv(spellbook.prepared)) + '</span></div>',
        '</div>',
        loading ? '<div class="builder-help-text">Refreshing spell options for your class and level…</div>' : '',
        '</div>',
      ].join('');
    },
    bind: function bindSpellStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      var draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
      var spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
      var data = _state.data;
      var limits = data && typeof data.limits === 'object' ? data.limits : {};
      var cardById = {};
      asArray(data && data.cards).forEach(function(card) {
        var id = String(card && card.id || '').trim();
        if (id) cardById[id] = card;
      });

      function rerenderWith(nextKnown, nextPrepared) {
        context.onSetField(['spellbook', 'known'], nextKnown);
        context.onSetField(['spellbook', 'prepared'], nextPrepared);
      }

      function canAddSpell(spellId, spellLevel, targetList, knownList, preparedList) {
        if (targetList === 'known' && knownList.indexOf(spellId) >= 0) return true;
        if (targetList === 'prepared' && preparedList.indexOf(spellId) >= 0) return true;

        if (spellLevel === 0) {
          if (limits.cantripsKnown != null) {
            var currentCantrips = knownList.filter(function(id) { return parseInt(cardById[id] && cardById[id].level, 10) === 0; }).length;
            if (currentCantrips >= parseInt(limits.cantripsKnown, 10)) return false;
          }
          return true;
        }

        if (targetList === 'known' && limits.spellsKnown != null) {
          var currentKnownLevelled = knownList.filter(function(id) { return parseInt(cardById[id] && cardById[id].level, 10) > 0; }).length;
          if (currentKnownLevelled >= parseInt(limits.spellsKnown, 10)) return false;
        }
        if (targetList === 'prepared' && limits.preparedLimit != null) {
          var currentPrepared = preparedList.filter(function(id) { return parseInt(cardById[id] && cardById[id].level, 10) > 0; }).length;
          if (currentPrepared >= parseInt(limits.preparedLimit, 10)) return false;
        }
        return true;
      }

      root.querySelectorAll('[data-spell-level-tab]').forEach(function(tab) {
        tab.addEventListener('click', function() {
          var level = String(tab.dataset.spellLevelTab || '').trim();
          root.querySelectorAll('[data-spell-level-tab]').forEach(function(el){ el.classList.toggle('active', el === tab); });
          root.querySelectorAll('[data-spell-level-group]').forEach(function(group) {
            group.classList.toggle('active', String(group.dataset.spellLevelGroup || '').trim() === level);
          });
        });
      });

      var search = root.querySelector('[data-builder-spell-search="1"]');
      if (search) {
        search.addEventListener('input', function() {
          var query = normalizeId(search.value);
          root.querySelectorAll('[data-spell-search]').forEach(function(cardEl) {
            var haystack = String(cardEl.dataset.spellSearch || '');
            cardEl.style.display = !query || haystack.indexOf(query) >= 0 ? '' : 'none';
          });
        });
      }

      root.querySelectorAll('[data-spell-id]').forEach(function(cardEl) {
        cardEl.addEventListener('click', function() {
          var accessible = String(cardEl.dataset.spellAccessible || '1') !== '0';
          if (!accessible) return;
          var spellId = String(cardEl.dataset.spellId || '').trim();
          if (!spellId) return;
          var spellLevel = parseInt(cardEl.dataset.spellLevel, 10) || 0;
          var knownList = asArray(spellbook.known).slice();
          var preparedList = asArray(spellbook.prepared).slice();
          var targetList = limits.preparedLimit != null && spellLevel > 0 ? 'prepared' : 'known';

          if (knownList.indexOf(spellId) >= 0) {
            knownList = knownList.filter(function(id){ return id !== spellId; });
            preparedList = preparedList.filter(function(id){ return id !== spellId; });
            rerenderWith(knownList, preparedList);
            return;
          }
          if (preparedList.indexOf(spellId) >= 0) {
            preparedList = preparedList.filter(function(id){ return id !== spellId; });
            rerenderWith(knownList, preparedList);
            return;
          }

          if (!canAddSpell(spellId, spellLevel, targetList, knownList, preparedList)) return;
          if (spellLevel === 0) {
            knownList.push(spellId);
          } else if (targetList === 'prepared') {
            preparedList.push(spellId);
          } else {
            knownList.push(spellId);
          }
          rerenderWith(knownList, preparedList);
        });
      });
    },
  });
})(window);
