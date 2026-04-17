(function initCharacterBuilderStepSpells(global) {
  var _state = {
    key: '',
    data: null,
    loading: false,
    pendingRerenderKey: '',
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

  function getMaxUnlockedSpellLevel(classRow, classLevel) {
    var slots = classRow && classRow.spellSlots && typeof classRow.spellSlots === 'object'
      ? classRow.spellSlots
      : {};
    var levelKey = String(Number.isFinite(classLevel) && classLevel > 0 ? classLevel : 1);
    var levelSlots = slots[levelKey] && typeof slots[levelKey] === 'object' ? slots[levelKey] : {};
    var highest = 0;
    Object.keys(levelSlots).forEach(function checkSlot(key) {
      var count = parseInt(levelSlots[key], 10);
      if (!Number.isFinite(count) || count <= 0) return;
      var level = parseInt(key, 10);
      if (Number.isFinite(level) && level > highest) highest = level;
    });
    if (highest > 0) return highest;

    // Fallback: derive max spell level from caster type + class level
    var casterType = normalizeId(classRow && classRow.spellcastingType);
    if (!casterType || casterType === 'none') return 0;
    var lvl = Number.isFinite(classLevel) && classLevel > 0 ? classLevel : 1;
    if (casterType === 'pact') {
      if (lvl <= 2) return 1;
      if (lvl <= 4) return 2;
      if (lvl <= 6) return 3;
      if (lvl <= 8) return 4;
      return 5;
    }
    if (casterType === 'half') {
      if (lvl <= 2) return 1;
      if (lvl <= 4) return 2;
      if (lvl <= 6) return 3;
      if (lvl <= 8) return 4;
      if (lvl <= 10) return 5;
      return Math.min(Math.ceil(lvl / 2), 9);
    }
    // Full caster table
    if (lvl <= 2) return 1;
    if (lvl <= 4) return 2;
    if (lvl <= 6) return 3;
    if (lvl <= 8) return 4;
    if (lvl <= 10) return 5;
    if (lvl <= 12) return 6;
    if (lvl <= 14) return 7;
    if (lvl <= 16) return 8;
    return 9;
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

      const knownSpells = Array.isArray(spellbook.known) ? spellbook.known : [];
      const preparedSpells = Array.isArray(spellbook.prepared) ? spellbook.prepared : [];

      // Count cantrips and levelled known spells for live caps
      const currentCantrips = knownSpells.filter(function isCantrip(id) {
        const row = _spellRows.find(function findSpell(r) { return r && r.id === id; });
        return row && parseInt(row.level, 10) === 0;
      }).length;
      const currentKnownLevelled = knownSpells.filter(function isLevelled(id) {
        const row = _spellRows.find(function findSpell(r) { return r && r.id === id; });
        return row && parseInt(row.level, 10) > 0;
      }).length;

      // Build selected spell chips (known + prepared)
      function buildSelectedChips(ids, label) {
        if (!ids.length) return '';
        return '<div class="spell-slot-row" style="margin-bottom:6px"><strong>' + escHtml(label) + ':</strong> ' +
          ids.map(function(id) {
            var r = _spellRows.find(function(s) { return s && s.id === id; });
            var name = (r && r.displayName) || id;
            return '<span class="spell-dmg-tag" style="margin:0 2px;padding:2px 7px;border-radius:999px;background:rgba(0,229,204,0.12);border:1px solid rgba(0,229,204,0.3);cursor:pointer;" ' +
              'data-builder-spell-remove="' + escHtml(id) + '" data-builder-spell-remove-list="' + escHtml(label === 'Cantrips / Known' ? 'known' : 'prepared') + '" title="Click to remove">' +
              escHtml(name) + ' ×</span>';
          }).join('') +
          '</div>';
      }

      const selectedKnownChips = buildSelectedChips(knownSpells, 'Cantrips / Known');
      const selectedPreparedChips = buildSelectedChips(preparedSpells, 'Prepared');

      // Counter display
      const cantripCapHtml = cantripsAllowed !== null
        ? '<span style="color:' + (currentCantrips >= cantripsAllowed ? '#ff8d8d' : 'rgba(0,229,204,0.9)') + '">' + currentCantrips + '/' + cantripsAllowed + ' cantrips</span>'
        : '';
      const knownCapHtml = spellsKnownAllowed !== null
        ? '<span style="color:' + (currentKnownLevelled >= spellsKnownAllowed ? '#ff8d8d' : 'rgba(0,229,204,0.9)') + '">' + currentKnownLevelled + '/' + spellsKnownAllowed + ' spells known</span>'
        : '';

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
        '</select></div>',
        castingMode === 'none'
          ? '<div class="builder-help-text">Select a casting style above to browse and pick class spells.</div>'
          : [
            // Caps + selected spells display
            (cantripCapHtml || knownCapHtml)
              ? '<div class="spell-slot-row" style="display:flex;gap:14px;margin-bottom:8px">' + cantripCapHtml + knownCapHtml + '</div>'
              : '',
            spellSlots
              ? '<div class="spell-slot-row"><strong>Spell Slots at Lv ' + safeClassLevel + ':</strong> ' + escHtml(Object.keys(spellSlots).map(function toSlot(key) { return key + ' ×' + spellSlots[key]; }).join(' · ')) + '</div>'
              : '',
            selectedKnownChips,
            selectedPreparedChips,
            '<div class="spell-browser-shell">',
            '<input class="spell-browser-search" type="search" data-builder-spell-search="1" placeholder="Search ' + escHtml(className || 'class') + ' spells…" />',
            '<div class="spell-level-tabs">',
            filteredLevelKeys.map(function toTab(levelKey) {
              const activeClass = levelKey === activeLevel ? ' active' : '';
              return '<button type="button" class="spell-level-tab' + activeClass + '" data-spell-level-tab="' + escHtml(levelKey) + '">' + escHtml(levelLabel(levelKey)) + '</button>';
            }).join(''),
            '</div>',
            filteredLevelKeys.map(function toGroup(levelKey) {
              const rows = groups[levelKey] || [];
              const activeClass = levelKey === activeLevel ? ' active' : '';
              return [
                '<section class="spell-level-group' + activeClass + '" data-spell-level-group="' + escHtml(levelKey) + '">',
                rows.map(function toSpellEntry(spell) {
                  const damageType = String(spell && spell.damageType || '').trim();
                  const isSelected = knownSpells.includes(spell.id) || preparedSpells.includes(spell.id);
                  return [
                    '<div class="spell-entry' + (isSelected ? '" style="border-color:rgba(0,229,204,0.55);background:rgba(0,229,204,0.07)' : '') + '"',
                    ' data-builder-spell-add="' + escHtml(spell.id || spell.displayName || '') + '"',
                    ' data-builder-spell-name="' + escHtml(spell.displayName || spell.id || '') + '"',
                    ' data-builder-spell-id="' + escHtml(spell.id || '') + '"',
                    ' data-builder-spell-level="' + escHtml(String(spell.level || 0)) + '"',
                    ' data-builder-spell-search-text="' + escHtml([spell.displayName, spell.school, spell.castingTime, spell.range, damageType, spell.description, spell.damageFormula].join(' ').toLowerCase()) + '">',
                    '<div class="spell-entry-name">' + (isSelected ? '✓ ' : '') + escHtml(spell.displayName || spell.id || 'Spell') + '</div>',
                    '<div class="spell-entry-meta">',
                    '<span>' + escHtml(spell.school || '—') + '</span>',
                    '<span>' + escHtml(spell.castingTime || '—') + '</span>',
                    '<span>Range ' + escHtml(spell.range || '—') + '</span>',
                    damageType ? ('<span class="spell-dmg-tag' + getDamageTypeClass(damageType) + '">' + escHtml(damageType) + '</span>') : '',
                    '</div>',
                    '</div>',
                  ].join('');
                }).join('') || '<div class="builder-help-text">No spells found for this level.</div>',
                '</section>',
              ].join('');
            }).join(''),
            filtered.length ? '' : '<div class="builder-help-text">No spells available for your current class and level selection.</div>',
            '</div>',
          ].join(''),
        '<div class="builder-help-text">Click spells to add them. Click the × chip above to remove. Your selections carry into gameplay.</div>',
      ].join('');
    },
    bind: function bindSpellStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      var draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
      var spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
      var data = _state.data;
      var limits = data && typeof data.limits === 'object' ? data.limits : {};
      var requestKey = buildRequestKey(draft);
      if ((!_state.data || _state.key !== requestKey) && _state.pendingRerenderKey !== requestKey) {
        _state.pendingRerenderKey = requestKey;
        fetchOptions(draft).then(function() {
          if (!root || !root.isConnected) return;
          var knownCopy = asArray(spellbook.known).slice();
          context.onSetField(['spellbook', 'known'], knownCopy);
        });
      }
      var cardById = {};
      asArray(data && data.cards).forEach(function(card) {
        var id = String(card && card.id || '').trim();
        if (id) cardById[id] = card;
      });

      function rerenderWith(nextKnown, nextPrepared) {
        context.onSetField(['spellbook', 'known'], nextKnown);
        context.onSetField(['spellbook', 'prepared'], nextPrepared);
      }

      const classLevelBind = parseInt(draft.progression && draft.progression.level, 10);
      const safeClassLevelBind = Number.isFinite(classLevelBind) && classLevelBind > 0 ? classLevelBind : 1;
      const cantripsAllowedBind = getCantripsAllowed(classRow, safeClassLevelBind);
      const spellsKnownAllowedBind = getSpellsKnownAllowed(classRow, safeClassLevelBind);

      // Remove-chip handler: click the × chip to remove a spell
      root.querySelectorAll('[data-builder-spell-remove]').forEach(function bindRemove(chipEl) {
        chipEl.addEventListener('click', function onRemove(evt) {
          evt.stopPropagation();
          const spellId = String(chipEl.dataset.builderSpellRemove || '').trim();
          const listKey = String(chipEl.dataset.builderSpellRemoveList || 'known').trim();
          if (!spellId) return;
          const current = Array.isArray(spellbook[listKey]) ? spellbook[listKey].slice() : [];
          const idx = current.indexOf(spellId);
          if (idx !== -1) {
            current.splice(idx, 1);
            context.onSetField(['spellbook', listKey], current);
          }
        });
      });

      // Tab navigation
      root.querySelectorAll('[data-spell-level-tab]').forEach(function bindTab(tabEl) {
        tabEl.addEventListener('click', function onTabClick() {
          const targetLevel = String(tabEl.dataset.spellLevelTab || '').trim();
          root.querySelectorAll('[data-spell-level-tab]').forEach(function clearTab(other) {
            other.classList.toggle('active', other === tabEl);
          });
          root.querySelectorAll('[data-spell-level-group]').forEach(function toggleGroup(groupEl) {
            groupEl.classList.toggle('active', String(groupEl.dataset.spellLevelGroup || '').trim() === targetLevel);
          });
        });
      });

      // Search filter
      if (searchInput) {
        searchInput.addEventListener('input', function onSearch() {
          const query = normalizeId(searchInput.value);
          root.querySelectorAll('.spell-entry[data-builder-spell-search-text]').forEach(function filterEntry(entryEl) {
            const haystack = String(entryEl.dataset.builderSpellSearchText || '');
            const visible = !query || haystack.indexOf(query) >= 0;
            entryEl.style.display = visible ? '' : 'none';
          });
        });
      }

      // Click-to-add spell entries
      root.querySelectorAll('.spell-entry[data-builder-spell-name]').forEach(function bindSpellEntry(entryEl) {
        entryEl.addEventListener('click', function onSpellAdd() {
          const spellId = String(entryEl.dataset.builderSpellId || '').trim();
          const spellLevel = parseInt(entryEl.dataset.builderSpellLevel || '0', 10);
          if (!spellId) return;
          var spellLevel = parseInt(cardEl.dataset.spellLevel, 10) || 0;
          var knownList = asArray(spellbook.known).slice();
          var preparedList = asArray(spellbook.prepared).slice();
          var selectionMode = String(cardById[spellId] && cardById[spellId].selectionMode || '').trim().toLowerCase();
          var targetList = 'known';
          if (spellLevel > 0 && selectionMode === 'prepared' && limits.preparedLimit != null) {
            targetList = 'prepared';
          }

          if (knownList.indexOf(spellId) >= 0) {
            knownList = knownList.filter(function(id){ return id !== spellId; });
            preparedList = preparedList.filter(function(id){ return id !== spellId; });
            rerenderWith(knownList, preparedList);
            return;
          }
          const current = target === 'known' ? knownList : preparedList;
          if (target === 'prepared' && spellLevel === 0) return;
          // Enforce cantrip limit
          if (spellLevel === 0 && cantripsAllowedBind !== null) {
            const cantripCount = knownList.filter(function isCantrip(id) {
              var row = _spellRows.find(function findSpell(r) { return r && r.id === id; });
              return row && parseInt(row.level, 10) === 0;
            }).length;
            if (cantripCount >= cantripsAllowedBind) return;
          }
          // Enforce known spell limit
          if (target === 'known' && spellLevel > 0 && spellsKnownAllowedBind !== null) {
            const levelledCount = knownList.filter(function isLevelled(id) {
              var row = _spellRows.find(function findSpell(r) { return r && r.id === id; });
              return row && parseInt(row.level, 10) > 0;
            }).length;
            if (levelledCount >= spellsKnownAllowedBind) return;
          }
          rerenderWith(knownList, preparedList);
        });
      });
    },
  });
})(window);
