(function initCharacterBuilderStepSpells(global) {
  let _spellRows = [];
  let _spellFetchPromise = null;

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

  function parseCsv(value) {
    return String(value || '')
      .split(',')
      .map(function normalize(item) { return String(item || '').trim(); })
      .filter(Boolean);
  }

  function normalizeId(value) {
    return String(value || '').trim().toLowerCase();
  }

  function ensureSpellStyles() {
    if (document.getElementById('character-builder-step-spells-style')) return;
    const style = document.createElement('style');
    style.id = 'character-builder-step-spells-style';
    style.textContent = [
      '.spell-browser-shell { margin-top: 10px; border: 1px solid rgba(0,229,204,0.2); border-radius: 8px; padding: 10px; background: rgba(8,14,18,0.9); }',
      '.spell-browser-search { margin-bottom: 8px; }',
      '.spell-level-tabs { display:flex; flex-wrap:wrap; gap: 6px; margin-bottom: 8px; }',
      '.spell-level-tab { font-size: 0.58rem; border: 1px solid rgba(0,229,204,0.25); border-radius: 999px; padding: 2px 7px; background: rgba(0,0,0,0.2); color: rgba(203,236,231,0.85); cursor: pointer; }',
      '.spell-level-tab.active { border-color: #00e5cc; color: #d8fff9; background: rgba(0,229,204,0.15); }',
      '.spell-level-group { display: none; }',
      '.spell-level-group.active { display: block; }',
      '.spell-entry { border: 1px solid rgba(0,229,204,0.15); border-radius: 8px; padding: 7px; margin-bottom: 6px; background: rgba(0,0,0,0.2); cursor: pointer; }',
      '.spell-entry:hover { border-color: rgba(0,229,204,0.55); background: rgba(0,229,204,0.07); }',
      '.spell-entry-name { font-size: 0.68rem; font-weight: 600; color: #cffff8; margin-bottom: 3px; }',
      '.spell-entry-meta { font-size: 0.58rem; color: rgba(194,227,221,0.82); display: flex; flex-wrap: wrap; gap: 8px; }',
      '.spell-dmg-tag { border-radius: 999px; padding: 1px 5px; border: 1px solid rgba(255,255,255,0.2); }',
      '.spell-dmg-fire { color: #ffb1a3; border-color: rgba(255,130,90,0.6); }',
      '.spell-dmg-cold { color: #a8d9ff; border-color: rgba(124,178,255,0.6); }',
      '.spell-dmg-lightning { color: #f1e89f; border-color: rgba(241,218,108,0.65); }',
      '.spell-dmg-necrotic { color: #c8b4ff; border-color: rgba(162,133,255,0.65); }',
      '.spell-dmg-radiant { color: #fff0a6; border-color: rgba(255,227,123,0.65); }',
      '.spell-slot-row { font-size: 0.6rem; color: rgba(192,228,223,0.92); margin-bottom: 8px; }',
    ].join('');
    document.head.appendChild(style);
  }

  function ensureSpellsLoaded() {
    if (_spellRows.length) return Promise.resolve(_spellRows);
    if (_spellFetchPromise) return _spellFetchPromise;
    _spellFetchPromise = fetch('/api/rules/spells', {
      method: 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(async function onResponse(res) {
        if (!res.ok) throw new Error('spells_fetch_failed');
        const json = await res.json();
        _spellRows = Array.isArray(json && json.spells) ? json.spells : [];
        global.__characterBuilderSpellManifest = json && json.manifest ? json.manifest : {};

        try {
          global.dispatchEvent(new CustomEvent('character-builder-catalog-updated', {
            detail: { spells: _spellRows.length },
          }));
        } catch (_) {
          // no-op
        }
        return _spellRows;
      })
      .catch(function onError() {
        _spellRows = [];
        return _spellRows;
      })
      .finally(function onFinally() {
        _spellFetchPromise = null;
      });
    return _spellFetchPromise;
  }

  function getClassRow(classId) {
    const api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') return null;
    const catalog = api.getCachedCatalog();
    const rows = catalog && Array.isArray(catalog.classes) ? catalog.classes : [];
    return rows.find(function findRow(row) {
      return normalizeId(row && row.id) === normalizeId(classId);
    }) || null;
  }

  function groupByLevel(rows) {
    const groups = {};
    rows.forEach(function pushRow(row) {
      const lvl = parseInt(row && row.level, 10);
      const key = Number.isFinite(lvl) && lvl >= 0 ? String(lvl) : '0';
      if (!groups[key]) groups[key] = [];
      groups[key].push(row);
    });
    return groups;
  }

  function levelLabel(levelKey) {
    const level = parseInt(levelKey, 10);
    if (level === 0) return 'Cantrips';
    if (level === 1) return '1st';
    if (level === 2) return '2nd';
    if (level === 3) return '3rd';
    return level + 'th';
  }

  function pickTargetList(castingMode, classRow) {
    if (castingMode === 'known') return 'known';
    if (castingMode === 'prepared') return 'prepared';
    if (castingMode === 'mixed') {
      const spellType = normalizeId(classRow && classRow.spellcastingType);
      if (spellType === 'pact') return 'known';
      if (spellType === 'none') return 'known';
      return 'prepared';
    }
    return 'known';
  }

  function getDamageTypeClass(damageType) {
    const key = normalizeId(damageType);
    if (!key) return '';
    if (['fire', 'cold', 'lightning', 'necrotic', 'radiant'].includes(key)) {
      return ' spell-dmg-' + key;
    }
    return '';
  }

  registerStep({
    id: 'spells',
    label: 'Spells',
    render: function renderSpellsStep(context) {
      ensureSpellStyles();
      ensureSpellsLoaded();

      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
      const castingMode = String(spellbook.castingMode || 'none');
      const classId = String(draft.class && draft.class.id || '').trim();
      const subclassId = String(draft.class && draft.class.subclassId || '').trim();
      const classRow = getClassRow(classId);
      const className = String(classRow && classRow.displayName || classId || '').trim();
      const classLevel = parseInt(draft.progression && draft.progression.level, 10);
      const spellSlots = classRow && classRow.spellSlots && classRow.spellSlots[String(Number.isFinite(classLevel) && classLevel > 0 ? classLevel : 1)]
        ? classRow.spellSlots[String(classLevel)]
        : null;

      const filtered = _spellRows.filter(function byClass(spell) {
        const classes = Array.isArray(spell && spell.classes) ? spell.classes : [];
        const subclassLists = []
          .concat(Array.isArray(spell && spell.subclass_lists) ? spell.subclass_lists : [])
          .concat(Array.isArray(spell && spell.subclassLists) ? spell.subclassLists : []);
        if (!className) return false;
        const classMatch = classes.some(function includesClass(entry) {
          return normalizeId(entry) === normalizeId(className) || normalizeId(entry) === normalizeId(classId);
        });
        if (classMatch) return true;
        return subclassId && subclassLists.some(function includesSubclass(entry) {
          return normalizeId(entry) === normalizeId(subclassId);
        });
      });
      const groups = groupByLevel(filtered);
      const levelKeys = Object.keys(groups).sort(function sortLevels(a, b) {
        return parseInt(a, 10) - parseInt(b, 10);
      });
      const activeLevel = levelKeys[0] || '0';

      return [
        '<div class="field"><label>Spellcasting Style</label>',
        '<select data-builder-path="spellbook.castingMode">',
        '<option value="none"' + (castingMode === 'none' ? ' selected' : '') + '>No Spellcasting</option>',
        '<option value="known"' + (castingMode === 'known' ? ' selected' : '') + '>Known Spells</option>',
        '<option value="prepared"' + (castingMode === 'prepared' ? ' selected' : '') + '>Prepared Spells</option>',
        '<option value="mixed"' + (castingMode === 'mixed' ? ' selected' : '') + '>Mixed / Class Specific</option>',
        '</select></div>',
        '<div class="field"><label>Spellcasting Ability</label>',
        '<select data-builder-path="spellbook.spellcastingAbility">',
        '<option value="">Auto/None</option>',
        ['str', 'dex', 'con', 'int', 'wis', 'cha'].map(function toOption(ability) {
          const selected = String(spellbook.spellcastingAbility || '') === ability ? ' selected' : '';
          return '<option value="' + ability + '"' + selected + '>' + ability.toUpperCase() + '</option>';
        }).join(''),
        '</select></div>',
        '<div class="field"><label>Known Spell IDs</label>',
        '<input type="text" data-builder-spells-known="1" value="' + escHtml(Array.isArray(spellbook.known) ? spellbook.known.join(', ') : '') + '" maxlength="500" placeholder="magic-missile, shield, detect-magic" /></div>',
        '<div class="field"><label>Prepared Spell IDs</label>',
        '<input type="text" data-builder-spells-prepared="1" value="' + escHtml(Array.isArray(spellbook.prepared) ? spellbook.prepared.join(', ') : '') + '" maxlength="500" placeholder="mage-armor, burning-hands" /></div>',
        castingMode === 'none'
          ? '<div class="builder-help-text">Select a casting style to browse class spells.</div>'
          : [
            '<div class="spell-browser-shell">',
            '<div class="spell-slot-row"><strong>Spell Slots:</strong> ' + escHtml(spellSlots ? Object.keys(spellSlots).map(function toSlot(key) { return key + ' ' + spellSlots[key]; }).join(' · ') : 'No slots at current level') + '</div>',
            '<div class="builder-help-text">Use spell IDs as the saved value. Cantrips belong in Known. Levelled spells go in Prepared for prepared casters or Known for known casters.</div>',
            '<input class="spell-browser-search" type="search" data-builder-spell-search="1" placeholder="Search ' + escHtml(className || 'class') + ' spells…" />',
            '<div class="spell-level-tabs">',
            levelKeys.map(function toTab(levelKey) {
              const activeClass = levelKey === activeLevel ? ' active' : '';
              return '<button type="button" class="spell-level-tab' + activeClass + '" data-spell-level-tab="' + escHtml(levelKey) + '">' + escHtml(levelLabel(levelKey)) + '</button>';
            }).join(''),
            '</div>',
            levelKeys.map(function toGroup(levelKey) {
              const rows = groups[levelKey] || [];
              const activeClass = levelKey === activeLevel ? ' active' : '';
              return [
                '<section class="spell-level-group' + activeClass + '" data-spell-level-group="' + escHtml(levelKey) + '">',
                rows.map(function toSpellEntry(spell) {
                  const damageType = String(spell && spell.damageType || '').trim();
                  return [
                    '<div class="spell-entry" data-builder-spell-add="' + escHtml(spell.id || spell.displayName || '') + '" data-builder-spell-name="' + escHtml(spell.displayName || spell.id || '') + '" data-builder-spell-id="' + escHtml(spell.id || '') + '" data-builder-spell-level="' + escHtml(String(spell.level || 0)) + '" data-builder-spell-search-text="' + escHtml([spell.displayName, spell.school, spell.castingTime, spell.range, damageType, spell.description, spell.damageFormula].join(' ').toLowerCase()) + '">',
                    '<div class="spell-entry-name">' + escHtml(spell.displayName || spell.id || 'Spell') + '</div>',
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
        '<div class="builder-help-text">Your selected spells will appear on your character sheet and be available during gameplay.</div>',
      ].join('');
    },
    bind: function bindSpellStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      const knownInput = root.querySelector('[data-builder-spells-known="1"]');
      const preparedInput = root.querySelector('[data-builder-spells-prepared="1"]');
      const searchInput = root.querySelector('[data-builder-spell-search="1"]');
      const draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
      const spellbook = draft.spellbook && typeof draft.spellbook === 'object' ? draft.spellbook : {};
      const classId = String(draft.class && draft.class.id || '').trim();
      const classRow = getClassRow(classId);

      if (knownInput) {
        knownInput.addEventListener('input', function onKnownInput() {
          context.onSetField(['spellbook', 'known'], parseCsv(knownInput.value));
        });
      }
      if (preparedInput) {
        preparedInput.addEventListener('input', function onPreparedInput() {
          context.onSetField(['spellbook', 'prepared'], parseCsv(preparedInput.value));
        });
      }

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

      root.querySelectorAll('.spell-entry[data-builder-spell-name]').forEach(function bindSpellEntry(entryEl) {
        entryEl.addEventListener('click', function onSpellAdd() {
          const spellId = String(entryEl.dataset.builderSpellId || '').trim();
          const spellName = String(entryEl.dataset.builderSpellName || '').trim();
          const spellLevel = parseInt(entryEl.dataset.builderSpellLevel || '0', 10);
          if (!spellId) return;
          const target = pickTargetList(String(spellbook.castingMode || 'none'), classRow);
          const current = Array.isArray(spellbook[target]) ? spellbook[target].slice() : [];
          if (target === 'prepared' && spellLevel === 0) return;
          if (!current.includes(spellId)) {
            current.push(spellId);
            context.onSetField(['spellbook', target], current);
          }
        });
      });
    },
  });
})(window);
