(function initCharacterBuilderStepOrigins(global) {
  var _backgrounds = [];
  var _backgroundFetchPromise = null;

  // Track which optional sections are open so re-renders don't collapse them.
  var _originsExpanded = false;

  /* ── helpers (preserved) ───────────────────────────────── */

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

  function ensureBuilderStyles() {
    if (document.getElementById('character-builder-css')) return;
    var link = document.createElement('link');
    link.id = 'character-builder-css';
    link.rel = 'stylesheet';
    link.href = '/static/css/character-builder.css';
    document.head.appendChild(link);
  }

  function getBackgroundRows() {
    return Array.isArray(_backgrounds) ? _backgrounds : [];
  }

  function ensureBackgroundCatalogLoaded() {
    if (getBackgroundRows().length) return Promise.resolve(getBackgroundRows());
    if (_backgroundFetchPromise) return _backgroundFetchPromise;

    _backgroundFetchPromise = fetch('/api/rules/backgrounds', {
      method: 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(async function onResponse(res) {
        if (!res.ok) throw new Error('backgrounds_fetch_failed');
        var data = await res.json();
        _backgrounds = Array.isArray(data && data.backgrounds) ? data.backgrounds : [];
        try {
          global.dispatchEvent(new CustomEvent('character-builder-catalog-updated', {
            detail: { backgrounds: _backgrounds.slice() },
          }));
        } catch (_) {
          // no-op
        }
        return _backgrounds;
      })
      .catch(function onError() {
        _backgrounds = [];
        return _backgrounds;
      })
      .finally(function onFinally() {
        _backgroundFetchPromise = null;
      });

    return _backgroundFetchPromise;
  }

  /* ── fallback data ─────────────────────────────────────── */

  var BACKGROUND_FALLBACK = [
    { id: 'soldier',    name: 'Soldier',    icon: '🪖', skills: ['Athletics', 'Intimidation'],      tool: "Gaming Set",                feat: 'Savage Attacker', gold: 50  },
    { id: 'criminal',   name: 'Criminal',   icon: '🗝️', skills: ['Sleight of Hand', 'Stealth'],      tool: "Thieves' Tools",            feat: 'Alert',           gold: 50  },
    { id: 'sage',       name: 'Sage',       icon: '📚', skills: ['Arcana', 'History'],              tool: "Calligrapher's Supplies",   feat: 'Magic Initiate',  gold: 50  },
    { id: 'acolyte',    name: 'Acolyte',    icon: '⛪', skills: ['Insight', 'Religion'],            tool: "Calligrapher's Supplies",   feat: 'Magic Initiate (Divine)', gold: 50 },
    { id: 'noble',      name: 'Noble',      icon: '👑', skills: ['History', 'Persuasion'],          tool: 'Musical Instrument',        feat: 'Skilled',         gold: 150 },
    { id: 'hermit',     name: 'Hermit',     icon: '🏔️', skills: ['Medicine', 'Religion'],           tool: 'Herbalism Kit',             feat: 'Magic Initiate (Primal)', gold: 25 },
    { id: 'entertainer',name: 'Entertainer',icon: '🎭', skills: ['Acrobatics', 'Performance'],      tool: 'Musical Instrument',        feat: 'Tavern Brawler',  gold: 50  },
    { id: 'farmer',     name: 'Farmer',     icon: '🌾', skills: ['Animal Handling', 'Nature'],      tool: "Carpenter's Tools",         feat: 'Tough',           gold: 30  },
    { id: 'guard',      name: 'Guard',      icon: '🛡️', skills: ['Athletics', 'Perception'],        tool: 'Musical Instrument',        feat: 'Alert',           gold: 50  },
    { id: 'sailor',     name: 'Sailor',     icon: '⚓', skills: ['Acrobatics', 'Perception'],       tool: "Navigator's Tools",         feat: 'Tavern Brawler',  gold: 50  },
    { id: 'merchant',   name: 'Merchant',   icon: '💰', skills: ['Animal Handling', 'Persuasion'],  tool: "Navigator's Tools",         feat: 'Lucky',           gold: 100 },
    { id: 'wayfarer',   name: 'Wayfarer',   icon: '🎒', skills: ['Insight', 'Stealth'],             tool: "Thieves' Tools",            feat: 'Lucky',           gold: 16  },
    { id: 'artisan',    name: 'Artisan',    icon: '🔨', skills: ['Investigation', 'Persuasion'],    tool: "Artisan's Tools",           feat: 'Crafter',         gold: 50  },
    { id: 'charlatan',  name: 'Charlatan',  icon: '🎪', skills: ['Deception', 'Sleight of Hand'],   tool: 'Forgery Kit',               feat: 'Skilled',         gold: 50  },
    { id: 'scribe',     name: 'Scribe',     icon: '📜', skills: ['Investigation', 'Perception'],    tool: "Calligrapher's Supplies",   feat: 'Skilled',         gold: 40  },
    { id: 'guide',      name: 'Guide',      icon: '🗺️', skills: ['Stealth', 'Survival'],            tool: "Cartographer's Tools",      feat: 'Magic Initiate (Primal)', gold: 50 },
  ];

  /* ── effective backgrounds (API → fallback) ────────────── */

  function getEffectiveBackgrounds() {
    var apiRows = getBackgroundRows();
    if (apiRows.length) {
      return apiRows.map(function(row) {
        return {
          id: String(row.id || '').trim(),
          name: String(row.displayName || row.id || '').trim(),
          icon: row.icon || '📋',
          skills: Array.isArray(row.skillProficiencies) ? row.skillProficiencies : [],
          tool: String(row.toolProficiency || '').trim(),
          feat: String(row.originFeat || '').trim(),
          gold: parseInt(row.startingGold, 10) || 0,
        };
      });
    }
    return BACKGROUND_FALLBACK;
  }

  /* ── card renderer ─────────────────────────────────────── */

  function renderBackgroundCard(bg, selectedId) {
    var isSelected = bg.id === selectedId;
    return [
      '<div class="species-card' + (isSelected ? ' selected' : '') + '" data-background-id="' + escHtml(bg.id) + '">',
      '<div class="sc-selected-check">✓</div>',
      '<div class="sc-icon" style="font-size:1.4rem;background:rgba(201,168,76,0.06);border-color:rgba(201,168,76,0.15)">' + bg.icon + '</div>',
      '<div class="sc-name">' + escHtml(bg.name) + '</div>',
      '<div class="sc-badges">',
      '<span class="sc-badge" style="background:rgba(201,168,76,0.08);border-color:rgba(201,168,76,0.2);color:var(--cb-gold-dim)">⭐ ' + escHtml(bg.feat) + '</span>',
      '</div>',
      '<div class="sc-traits">',
      bg.skills.map(function(s) { return '<div class="sc-trait">' + escHtml(s) + '</div>'; }).join(''),
      '<div class="sc-trait" style="color:var(--cb-text-dim)">' + escHtml(bg.tool) + '</div>',
      '<div class="sc-trait" style="color:var(--cb-gold-dim)">' + bg.gold + ' GP</div>',
      '</div>',
      '</div>',
    ].join('');
  }

  /* ── step registration ─────────────────────────────────── */

  registerStep({
    id: 'origins',
    label: 'Origins',
    render: function renderOriginsStep(context) {
      ensureBuilderStyles();
      ensureBackgroundCatalogLoaded();

      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var origins = draft.origins && typeof draft.origins === 'object' ? draft.origins : {};
      var currentBackgroundId = normalizeId(origins.backgroundId);
      var backgrounds = getEffectiveBackgrounds();

      var cards = backgrounds.map(function(bg) {
        return renderBackgroundCard(bg, normalizeId(bg.id) === currentBackgroundId ? bg.id : '');
      }).join('');

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Background &amp; Origins</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Your background shapes your history, starting skills, and origin feat.</div>',
        '</div>',

        '<input type="hidden" data-builder-path="origins.backgroundId" value="' + escHtml(String(origins.backgroundId || '').trim()) + '" />',

        '<div class="species-grid">' + cards + '</div>',

        '<details class="cb-optional-section" data-section-key="origins-extra"' + (_originsExpanded ? ' open' : '') + '>',
        '<summary class="cb-optional-section-summary">Additional Details <span class="cb-optional">optional</span></summary>',
        '<div class="cb-optional-section-body">',

        '<div class="field"><label>Additional Languages <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-origins-languages="1" value="' + escHtml(Array.isArray(origins.languages) ? origins.languages.join(', ') : '') + '" maxlength="220" placeholder="Common, Elvish, Dwarvish\u2026" /></div>',

        '<div class="field"><label>Extra Proficiencies <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-origins-proficiencies="1" value="' + escHtml(Array.isArray(origins.proficiencies) ? origins.proficiencies.join(', ') : '') + '" maxlength="260" placeholder="Perception, Stealth, Thieves\u2019 Tools\u2026" /></div>',

        '<div class="builder-help-text">Selecting a background auto-fills your skill proficiencies and origin feat. Use these fields to add extras from your DM.</div>',

        '</div>',
        '</details>',
      ].join('');
    },

    bind: function bindOriginsStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;

      // Preserve optional section open state across re-renders
      var extraDetails = root.querySelector('details[data-section-key="origins-extra"]');
      if (extraDetails) {
        extraDetails.addEventListener('toggle', function() {
          _originsExpanded = extraDetails.open;
        });
      }

      var hiddenInput = root.querySelector('[data-builder-path="origins.backgroundId"]');
      var langInput = root.querySelector('[data-builder-origins-languages="1"]');
      var profInput = root.querySelector('[data-builder-origins-proficiencies="1"]');
      var cardEls = Array.from(root.querySelectorAll('.species-card[data-background-id]'));
      var backgrounds = getEffectiveBackgrounds();

      cardEls.forEach(function bindCard(cardEl) {
        cardEl.addEventListener('click', function onCardClick() {
          var id = String(cardEl.dataset.backgroundId || '').trim();
          if (!id) return;

          var bg = backgrounds.find(function(b) { return normalizeId(b.id) === normalizeId(id); });
          if (!bg) return;

          if (hiddenInput) hiddenInput.value = id;

          cardEls.forEach(function(c) { c.classList.remove('selected'); });
          cardEl.classList.add('selected');

          context.onSetField(['origins', 'backgroundId'], id);
          context.onSetField(['origins', 'skillProficiencies'], bg.skills.slice());
          context.onSetField(['origins', 'originFeat'], bg.feat);
        });
      });

      if (langInput) {
        langInput.addEventListener('input', function onLangInput() {
          var list = String(langInput.value || '')
            .split(',')
            .map(function(v) { return String(v || '').trim(); })
            .filter(Boolean);
          context.onSetField(['origins', 'languages'], list);
        });
      }

      if (profInput) {
        profInput.addEventListener('input', function onProfInput() {
          var list = String(profInput.value || '')
            .split(',')
            .map(function(v) { return String(v || '').trim(); })
            .filter(Boolean);
          context.onSetField(['origins', 'proficiencies'], list);
        });
      }
    },
  });
})(window);
