/*
 * client/static/js/character/tabs/features_tab.js
 * Features & Traits Tab — D&D Beyond-style class feature codex with level roadmap.
 * short rules summary
 *
 * Exposes: window.FeaturesTab
 *   .initFeaturesTab(container, charData)
 */

(function initFeaturesTabModule(global) {
  'use strict';

  const CLASS_PLAYBOOKS = {
    barbarian: {
      title: 'Barbarian Class Guide',
      loop: 'Enter Rage early, stay in melee, and turn high durability into momentum.',
      resources: ['Rage uses', 'Weapon Mastery riders', 'Subclass activators'],
      spotlight: ['Open with Rage on high-threat rounds.', 'Use Reckless Attack when your AC trade is acceptable.'],
    },
    bard: {
      title: 'Bard Class Guide',
      loop: 'Support and control through Bardic Inspiration, spells, and subclass utility.',
      resources: ['Bardic Inspiration', 'Spell slots', 'Magical Secrets picks'],
      spotlight: ['Spend inspiration proactively before pivotal checks.', 'Anchor concentration with safe positioning.'],
    },
    cleric: {
      title: 'Cleric Class Guide',
      loop: 'Prepared casting plus divine subclass tools for healing, control, and radiant pressure.',
      resources: ['Channel Divinity', 'Spell slots', 'Domain features'],
      spotlight: ['Use domain identity every encounter.', 'Reserve high slots for turning points.'],
    },
    druid: {
      title: 'Druid Class Guide',
      loop: 'Prepared spellcasting and form/terrain control define your turn economy.',
      resources: ['Wild Shape', 'Spell slots', 'Subclass cadence'],
      spotlight: ['Separate Wild Shape plan from spell slot plan.', 'Frontload battlefield control effects.'],
    },
    fighter: {
      title: 'Fighter Class Guide',
      loop: 'Consistent attack volume plus burst rounds through Action Surge and subclass spikes.',
      resources: ['Action Surge', 'Second Wind', 'Subclass dice/charges'],
      spotlight: ['Save Action Surge for decisive rounds.', 'Track subclass riders every attack sequence.'],
    },
    monk: {
      title: 'Monk Class Guide',
      loop: 'Mobility plus Focus/Ki economy defines offense and defense windows.',
      resources: ['Focus/Ki points', 'Bonus action discipline options', 'Defensive reactions'],
      spotlight: ['Plan your bonus action each round.', 'Budget points for both offense and defense.'],
    },
    paladin: {
      title: 'Paladin Class Guide',
      loop: 'Aura pressure and divine burst damage shape frontline leadership.',
      resources: ['Spell slots for smites', 'Channel Divinity', 'Lay on Hands'],
      spotlight: ['Maintain aura coverage for allies.', 'Smite on confirmed/high-value hits.'],
    },
    ranger: {
      title: 'Ranger Class Guide',
      loop: 'Precision attacks plus terrain/hunter tools and utility casting.',
      resources: ['Spell slots', 'Subclass hunt mechanics', 'Exploration features'],
      spotlight: ['Mark priority targets early.', 'Use concentration spells that fit map geometry.'],
    },
    rogue: {
      title: 'Rogue Class Guide',
      loop: 'Secure Sneak Attack every round while preserving action economy.',
      resources: ['Sneak Attack trigger setup', 'Cunning Action choices', 'Subclass tricks'],
      spotlight: ['Enter turns with advantage/allied adjacency plans.', 'Use bonus action for position control.'],
    },
    sorcerer: {
      title: 'Sorcerer Class Guide',
      loop: 'Convert Sorcery Points and Metamagic into high-impact spell turns.',
      resources: ['Sorcery Points', 'Spell slots', 'Subclass surge features'],
      spotlight: ['Treat points as turn-shaping currency.', 'Use Metamagic on spells that swing outcomes.'],
    },
    warlock: {
      title: 'Warlock Class Guide',
      loop: 'At-will cantrip pressure between pact-slot spikes and invocation utility.',
      resources: ['Pact slots', 'Mystic Arcanum', 'Invocation choices'],
      spotlight: ['Spend pact slots aggressively each short-rest cycle.', 'Build around your patron identity.'],
    },
    wizard: {
      title: 'Wizard Class Guide',
      loop: 'Spellbook preparation and battlefield control solve encounters through planning.',
      resources: ['Spell slots', 'Arcane Recovery', 'Subclass school features'],
      spotlight: ['Prepare a balanced daily toolkit.', 'Sequence concentration and reaction spells deliberately.'],
    },
    tinker: {
      title: 'Tinker Surface Guide',
      loop: 'Rotate gadget pressure and specialty tools while preserving action economy.',
      resources: ['Gadget Charges', 'Prototype actions', 'Subclass engineering features'],
      spotlight: ['Open with setup tools then convert to pressure.', 'Keep one charge reserve for emergencies.'],
    },
    pirate: {
      title: 'Pirate Surface Guide',
      loop: 'Use swagger-fueled tempo swings to control target priority and momentum.',
      resources: ['Swagger Dice', 'Boarding tools', 'Subclass stunts'],
      spotlight: ['Spend swagger for decisive exchanges.', 'Use movement to isolate marked targets.'],
    },
  };

  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }

  function _safeArray(value) {
    return Array.isArray(value) ? value.filter(Boolean) : [];
  }

  function _firstText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value == null) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }

  function _normalizeActionType(feature) {
    const raw = String(_firstText(feature && feature.actionType, feature && feature.type)).toLowerCase();
    if (!raw || raw === 'passive' || raw === 'always on') return 'Passive';
    if (raw === 'bonus' || raw === 'bonus action') return 'Bonus Action';
    if (raw === 'reaction') return 'Reaction';
    if (raw === 'action') return 'Action';
    return raw.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function _coerceFeature(entry, defaults) {
    const base = defaults && typeof defaults === 'object' ? defaults : {};
    if (!entry) return null;
    if (typeof entry === 'string') {
      return {
        id: entry.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        name: entry,
        level: Number(base.level || 0),
        className: _firstText(base.className),
        subclassName: _firstText(base.subclassName),
        isSubclass: !!base.isSubclass,
        kind: _firstText(base.kind, 'class'),
        source: _firstText(base.source, 'Class Feature'),
        section: _firstText(base.section, 'Class Features'),
        summary: '',
        description: '',
        actionType: _firstText(base.actionType, 'passive'),
        usage: _firstText(base.usage),
        recovery: _firstText(base.recovery),
        resourceName: _firstText(base.resourceName),
        tags: _safeArray(base.tags),
      };
    }
    const obj = typeof entry === 'object' ? entry : {};
    return {
      id: _firstText(obj.id, obj.featureId, obj.name).toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      name: _firstText(obj.name, obj.displayName, 'Feature'),
      level: Number(obj.level || obj.minLevel || base.level || 0),
      className: _firstText(obj.className, base.className),
      subclassName: _firstText(obj.subclassName, base.subclassName),
      isSubclass: !!(obj.isSubclass || base.isSubclass),
      kind: _firstText(obj.kind, base.kind, 'class'),
      source: _firstText(obj.source, base.source, 'Class Feature'),
      section: _firstText(obj.section, base.section, 'Class Features'),
      summary: _firstText(obj.summary, obj.effect),
      description: _firstText(obj.description, obj.text),
      actionType: _firstText(obj.actionType, obj.type, base.actionType, 'passive'),
      usage: _firstText(obj.usage, base.usage),
      recovery: _firstText(obj.recovery, base.recovery),
      resourceName: _firstText(obj.resourceName, base.resourceName),
      trigger: _firstText(obj.trigger),
      range: _firstText(obj.range),
      duration: _firstText(obj.duration),
      save: _firstText(obj.save),
      effect: _firstText(obj.effect),
      tags: _safeArray(obj.tags || base.tags),
    };
  }

  function _dedupeFeatures(features) {
    const seen = new Set();
    return _safeArray(features).filter(function (feature) {
      const key = [String(feature.name || '').toLowerCase(), feature.level || 0, String(feature.className || '').toLowerCase(), feature.isSubclass ? 'sub' : 'core'].join('::');
      if (!feature.name || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function _isBookkeepingFeature(feature) {
    const text = [feature && feature.name, feature && feature.summary, feature && feature.description].join(' ').toLowerCase();
    if (/spellcasting progression/.test(text)) return true;
    if (/cantrip|spell/.test(text) && /known|prepared|slot level|slots?\s*\d/.test(text)) return true;
    return false;
  }

  function _featureTypeKey(feature) {
    if (feature && feature.kind === 'feat') return 'feats';
    if (feature && (feature.kind === 'trait' || feature.kind === 'origin')) return 'traits';
    if (feature && feature.isSubclass) return 'subclass';
    return 'class';
  }

  function _featureConnectedSystems(feature) {
    const out = [];
    const txt = [feature.name, feature.summary, feature.description, feature.resourceName].join(' ').toLowerCase();
    if (/short rest|long rest|recharge|recover/.test(txt)) out.push('Rest tracking + resource reset');
    if (/save|dc|advantage|disadvantage/.test(txt)) out.push('Roll resolution + save workflow');
    if (/reaction|trigger/.test(txt)) out.push('Turn order + reaction timing');
    if (/spell|slot|cantrip|metamagic/.test(txt)) out.push('Spell panel + casting economy');
    if (/rage|inspiration|ki|focus|sorcery|pact|swagger|gadget/.test(txt)) out.push('Class resource counters');
    return out.length ? out : ['Core feature resolution path'];
  }

  function _featureTestingGuidance(feature, charData) {
    const className = String((charData && charData.className) || feature.className || '').trim() || 'your class';
    return [
      'Trigger this feature in a live turn where its action timing matters.',
      'Verify uses/costs decrement correctly and recover at the listed rest cadence.',
      'Confirm ' + className + ' sheet text matches runtime behavior for the same feature.',
    ];
  }

  function _featureWhenItMatters(feature) {
    const actionType = _normalizeActionType(feature).toLowerCase();
    if (actionType === 'reaction') return 'Best Time to Use It: hold this for enemy-triggered events where timing changes outcomes.';
    if (actionType === 'bonus action') return 'Best Time to Use It: pair this with your Action to maximize round efficiency.';
    if (actionType === 'action') return 'Best Time to Use It: spend your Action when this feature creates a stronger swing than a basic attack/cantrip.';
    return 'Best Time to Use It: keep this feature in mind for every encounter; it is an always-on rule modifier.';
  }

  function _featureRulesBreakdown(feature) {
    return [
      'Action Type: ' + _normalizeActionType(feature),
      'Level Unlock: ' + (feature.level || 0),
      'Source: ' + _firstText(feature.source, feature.className, 'Class Feature'),
      'Resource: ' + _firstText(feature.resourceName, 'None'),
    ];
  }

  function _featureAutomationCoverage(feature) {
    return [
      feature.usage ? 'Usage text is surfaced in the feature card.' : 'Usage is descriptive only; no explicit cost text found.',
      feature.recovery ? 'Recovery cadence is surfaced in detail view.' : 'Recovery cadence not explicitly authored for this row.',
      'Search/filter tags include action type, subclass/core state, and resource linkage.',
    ];
  }

  function _featureCommonBlockers(feature) {
    return [
      'Missing trigger context in combat round order.',
      feature.resourceName ? 'Resource counter not initialized for ' + feature.resourceName + '.' : 'No named resource linked for automatic tracking.',
      'Feature text depends on subclass selection not yet applied.',
    ];
  }

  function _featureTagPills(feature) {
    const tags = [_normalizeActionType(feature)];
    if (feature.isSubclass) tags.push('Subclass');
    if (feature.resourceName) tags.push(feature.resourceName);
    return Array.from(new Set(tags));
  }

  function _descHtml(text) {
    if (!text) return '<p><em>Rules details have not been fully authored for this entry yet.</em></p>';
    return String(text).split(/\n{2,}/).map((p) => '<p>' + _esc(p).replace(/\n/g, '<br>') + '</p>').join('');
  }

  function _featureSectionsForDrawer(feature, charData) {
    return [
      { title: 'At a Glance', items: _featureRulesBreakdown(feature) },
      { title: 'How to Use It', items: _featureTestingGuidance(feature, charData) },
      { title: 'Rules Breakdown', items: _featureRulesBreakdown(feature) },
      { title: 'Automation Coverage', items: _featureAutomationCoverage(feature) },
      { title: 'Common Blockers', items: _featureCommonBlockers(feature) },
      { title: 'Connected Systems', items: _featureConnectedSystems(feature) },
    ];
  }

  function _featureSearchBlob(feature) {
    return [
      feature.name,
      feature.summary,
      feature.description,
      feature.className,
      feature.subclassName,
      feature.resourceName,
      _featureTypeKey(feature),
      _normalizeActionType(feature),
      _safeArray(feature.tags).join(' '),
    ].filter(Boolean).join(' ').toLowerCase();
  }

  function _renderFeatureItem(feature, idx, charData) {
    const id = _firstText(feature.id, feature.name, 'feature-' + idx);
    const summary = _firstText(feature.summary, 'Open to read the full details for this feature.');
    const sections = _featureSectionsForDrawer(feature, charData);
    const whenText = _featureWhenItMatters(feature);

    return `<article class="cs-feature-item" data-feature-id="${_esc(id)}" data-feature-filters="all ${_esc(_featureTypeKey(feature))} ${_esc(_normalizeActionType(feature).toLowerCase().replace(/\s+/g, '-'))} ${feature.resourceName ? 'resource' : ''}" data-feature-search="${_esc(_featureSearchBlob(feature))}">
      <header class="cs-feature-header" role="button" tabindex="0" aria-expanded="false">
        <div class="cs-feature-maincopy">
          <div class="cs-feature-title-row"><span class="cs-feature-name">${_esc(feature.name)}</span></div>
          <div class="cs-feature-inline-meta">${_esc(_firstText(feature.className, feature.source, 'Class Feature'))} • Level ${_esc(String(feature.level || 0))}</div>
          <div class="cs-feature-preview"><strong>${_esc(summary)}</strong></div>
        </div>
        <div class="cs-feature-meta">${_featureTagPills(feature).map((t) => `<span class="cs-feature-kind-badge">${_esc(t)}</span>`).join('')}<span class="cs-feature-chevron" aria-hidden="true">&#9658;</span></div>
      </header>
      <div class="cs-feature-body">
        <div class="cs-feature-body-shell">
          <div class="cs-feature-body-summary"><strong>${_esc(whenText)}</strong></div>
          <div class="cs-feature-facts">${sections.map((section) => `<div class="cs-feature-fact"><span class="cs-feature-fact-label">${_esc(section.title)}</span><span class="cs-feature-fact-value">${section.items.map((it) => _esc(it)).join('<br>')}</span></div>`).join('')}</div>
          <div class="cs-feature-body-rules">${_descHtml(_firstText(feature.description, feature.summary))}</div>
          <button type="button" class="cs-feature-inspect" data-feature-inspect="${_esc(id)}">Inspect</button>
        </div>
      </div>
    </article>`;
  }

  function _groupFeaturesByLevel(items) {
    const buckets = new Map();
    _safeArray(items).forEach(function (feature) {
      const level = Number(feature.level || 0);
      if (!buckets.has(level)) buckets.set(level, []);
      buckets.get(level).push(feature);
    });
    return Array.from(buckets.entries()).sort(function (a, b) { return a[0] - b[0]; }).map(function (row) {
      return { level: row[0], items: row[1] };
    });
  }

  function _renderLevelRoadmap(allByLevel, currentLevel) {
    return `<section class="cs-overview-section"><div class="cs-overview-section-title">Level Roadmap</div>
      <div class="cs-overview-copy">Every class level feature is listed below so players can read what unlocks now and later.</div>
      <div class="cs-roadmap-grid">${allByLevel.map(function (row) {
        const stateClass = row.level === currentLevel ? 'current' : row.level > currentLevel ? 'upcoming' : 'past';
        return `<article class="cs-roadmap-card ${stateClass}" data-roadmap-level="${_esc(String(row.level))}"><div class="cs-roadmap-level">Level ${_esc(String(row.level))}</div><div class="cs-roadmap-count">${_esc(String(row.items.length))} features</div><div class="cs-roadmap-preview">${_esc(row.items.slice(0, 2).map((f) => f.name).join(' • ') || 'Feature details authored in class data')}</div></article>`;
      }).join('')}</div></section>`;
  }

  function _renderSpotlight(allByLevel, currentLevel) {
    const current = allByLevel.find(function (row) { return row.level === currentLevel; });
    const next = allByLevel.find(function (row) { return row.level > currentLevel; });
    return `<section class="cs-overview-section"><div class="cs-overview-section-title">Current & Next Unlocks</div><div class="cs-spotlight-grid">
      <article class="cs-overview-card"><div class="cs-overview-card-title">Current Level ${_esc(String(currentLevel))}</div><div class="cs-overview-card-copy">${_esc((current && current.items.map((f) => f.name).join(', ')) || 'No newly-authored unlocks at this level.')}</div></article>
      <article class="cs-overview-card"><div class="cs-overview-card-title">Next Unlock${next ? ' (Level ' + _esc(String(next.level)) + ')' : ''}</div><div class="cs-overview-card-copy">${_esc((next && next.items.map((f) => f.name).join(', ')) || 'No future class entries found.')}</div></article>
    </div></section>`;
  }

  function _renderPlaybook(charData, sections) {
    const classKey = String((charData && charData.className) || '').toLowerCase().replace(/\s+/g, '-');
    const playbook = CLASS_PLAYBOOKS[classKey] || { title: 'Class Guide', loop: 'Use your class features in sequence and track resource cadence.', resources: ['Class features'], spotlight: [] };
    const trackedResources = _safeArray(sections.classFeatures).map((f) => f.resourceName).filter(Boolean);
    return `<section class="cs-overview-section"><div class="cs-overview-section-title">Class Guide</div>
      <div class="cs-playbook-grid">
        <article class="cs-playbook-card highlight"><div class="cs-playbook-title">${_esc(playbook.title)}</div><div class="cs-playbook-copy">${_esc(playbook.loop)}</div></article>
        <article class="cs-playbook-card"><div class="cs-playbook-title">Tracked resources</div><div class="cs-playbook-chip-row">${Array.from(new Set(playbook.resources.concat(trackedResources))).map((r) => `<span class="cs-playbook-chip">${_esc(r)}</span>`).join('')}</div></article>
      </div></section>`;
  }

  function _renderCustomClassGuide(charData) {
    const classKey = String((charData && charData.className) || '').toLowerCase().replace(/\s+/g, '-');
    if (classKey === 'tinker') return '<section class="cs-overview-section"><div class="cs-overview-section-title">Tinker Surface Guide</div><div class="cs-overview-copy">Use gadget charges as your pacing tool and read each level unlock before committing resources.</div></section>';
    if (classKey === 'pirate') return '<section class="cs-overview-section"><div class="cs-overview-section-title">Pirate Surface Guide</div><div class="cs-overview-copy">Swagger Dice define your burst windows; line up movement and marked-target pressure every round.</div></section>';
    return '';
  }

  function _renderFeatureControls() {
    return `<section class="cs-overview-section cs-feature-controls-section cs-features-redesign-controls"><div class="cs-overview-section-title">Find a Feature</div><div class="cs-overview-copy">Search by class feature name, action type, resource, or keyword.</div><div class="cs-feature-toolbar"><input type="search" class="cs-feature-search" data-feature-search placeholder="Find a Feature" /><div class="cs-feature-filter-row"><button type="button" class="cs-feature-filter-chip active" data-feature-filter="all">All</button><button type="button" class="cs-feature-filter-chip" data-feature-filter="class">Class Features</button><button type="button" class="cs-feature-filter-chip" data-feature-filter="subclass">Subclass</button><button type="button" class="cs-feature-filter-chip" data-feature-filter="traits">Species Traits</button><button type="button" class="cs-feature-filter-chip" data-feature-filter="feats">Feats</button><button type="button" class="cs-feature-filter-chip" data-feature-filter="resource">Resource</button></div></div></section>`;
  }

  function _renderSection(title, items, sectionKey, charData, emptyCopy) {
    const list = _safeArray(items);
    return `<section class="cs-feature-section" data-feature-section="${_esc(sectionKey)}"><div class="cs-feature-section-title">${_esc(title)}</div><div class="cs-feature-section-copy">${_esc(emptyCopy)}</div><div class="cs-feature-list">${list.length ? list.map((f, idx) => _renderFeatureItem(f, idx, charData)).join('') : '<div class="cs-empty-state">No entries currently available.</div>'}</div></section>`;
  }

  function _extractFeatureRows(charData, sheetData) {
    const merged = Object.assign({}, charData || {}, sheetData || {});
    const classFeatures = _dedupeFeatures(_safeArray(merged.features).map((f) => _coerceFeature(f, { kind: 'class', className: merged.className || '' })).filter(Boolean)).filter((f) => !_isBookkeepingFeature(f));
    const traits = _dedupeFeatures(_safeArray(merged.traits).map((f) => _coerceFeature(f, { kind: 'trait' })).filter(Boolean));
    const feats = _dedupeFeatures(_safeArray(merged.feats).map((f) => _coerceFeature(f, { kind: 'feat' })).filter(Boolean));
    return { classFeatures, traits, feats };
  }

  function _extractClassRoadmap(sheetData, charData) {
    const classData = sheetData && sheetData.classData && typeof sheetData.classData === 'object' ? sheetData.classData : {};
    const byLevel = _safeArray(classData.featuresByLevel).map(function (row) {
      const level = Number((row && row.level) || 0);
      const features = _safeArray(row && row.features).map(function (item) {
        const definition = typeof item === 'string' ? ((classData.featureDefinitions || {})[item] || { name: item, level: level }) : item;
        return _coerceFeature(definition, {
          level: level,
          className: _firstText(classData.displayName, charData && charData.className),
          source: 'Class Roadmap',
          kind: 'class',
        });
      }).filter(Boolean);
      return { level: level, items: features };
    }).filter((r) => r.level > 0);

    if (byLevel.length) return byLevel;
    return _groupFeaturesByLevel(_safeArray(charData && charData.features).map((f) => _coerceFeature(f, { kind: 'class' })).filter(Boolean));
  }

  function _applyFeatureFilters(container) {
    const filter = String(container.__csFeatureFilter || 'all').toLowerCase();
    const query = String(container.__csFeatureQuery || '').toLowerCase().trim();
    const rows = Array.from(container.querySelectorAll('.cs-feature-item'));
    rows.forEach(function (row) {
      const hay = String(row.getAttribute('data-feature-search') || '');
      const filters = String(row.getAttribute('data-feature-filters') || '').toLowerCase().split(/\s+/);
      const filterMatch = filter === 'all' || filters.includes(filter);
      const queryMatch = !query || hay.indexOf(query) !== -1;
      row.hidden = !(filterMatch && queryMatch);
    });

    Array.from(container.querySelectorAll('.cs-feature-section')).forEach(function (section) {
      const items = Array.from(section.querySelectorAll('.cs-feature-item'));
      section.hidden = items.length > 0 && items.every((item) => item.hidden);
    });

    const chips = container.querySelectorAll('.cs-feature-filter-chip');
    Array.from(chips).forEach((chip) => chip.classList.toggle('active', String(chip.getAttribute('data-feature-filter') || '').toLowerCase() === filter));
  }

  function _bindInteractions(container) {
    if (container.__csFeaturesBound) return;
    container.__csFeaturesBound = true;

    container.addEventListener('click', function (event) {
      const chip = event.target.closest('[data-feature-filter]');
      if (chip) {
        container.__csFeatureFilter = String(chip.getAttribute('data-feature-filter') || 'all');
        _applyFeatureFilters(container);
        return;
      }

      const header = event.target.closest('.cs-feature-header');
      if (header) {
        const row = header.closest('.cs-feature-item');
        if (!row) return;
        row.classList.toggle('open');
        const isOpen = row.classList.contains('open');
        header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        const opened = Array.from(container.querySelectorAll('.cs-feature-item.open')).map((it) => it.getAttribute('data-feature-id'));
        container.__csFeatureOpenSet = new Set(opened);
        return;
      }

      const inspectBtn = event.target.closest('[data-feature-inspect]');
      if (inspectBtn) {
        const targetId = String(inspectBtn.getAttribute('data-feature-inspect') || '');
        const featureRow = container.querySelector('.cs-feature-item[data-feature-id="' + CSS.escape(targetId) + '"]');
        if (featureRow && !featureRow.classList.contains('open')) {
          const targetHeader = featureRow.querySelector('.cs-feature-header');
          if (targetHeader) targetHeader.click();
        }
      }
    });

    container.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const header = event.target.closest('.cs-feature-header');
      if (!header) return;
      event.preventDefault();
      header.click();
    });

    container.addEventListener('input', function (event) {
      const search = event.target.closest('[data-feature-search]');
      if (!search) return;
      container.__csFeatureQuery = String(search.value || '');
      _applyFeatureFilters(container);
    });
  }

  function _render(container, charData, sheetData) {
    const sections = _extractFeatureRows(charData, sheetData);
    const allByLevel = _extractClassRoadmap(sheetData, charData);
    const level = Number((charData && charData.level) || (sheetData && sheetData.level) || 1);

    const overviewCounts = `<section class="cs-overview-section"><div class="cs-overview-section-title">Features at a Glance</div><div class="cs-traits-summary-grid cs-features-redesign-summary"><div class="cs-traits-summary-card"><div class="cs-traits-summary-label">Class & Subclass Features</div><div class="cs-traits-summary-value">${_esc(String(sections.classFeatures.length))}</div><div class="cs-traits-summary-note">core and subclass rules</div></div><div class="cs-traits-summary-card"><div class="cs-traits-summary-label">Species Traits</div><div class="cs-traits-summary-value">${_esc(String(sections.traits.length))}</div><div class="cs-traits-summary-note">origin and lineage traits</div></div><div class="cs-traits-summary-card"><div class="cs-traits-summary-label">Character Snapshot</div><div class="cs-traits-summary-value">Level ${_esc(String(level))}</div><div class="cs-traits-summary-note">full class roadmap visible below</div></div></div></section>`;

    container.innerHTML = `<div class="cs-traits-shell cs-traits-shell-readable cs-features-redesign-shell">${_renderFeatureControls()}${overviewCounts}${_renderPlaybook(charData, sections)}${_renderCustomClassGuide(charData)}${_renderSpotlight(allByLevel, level)}${_renderLevelRoadmap(allByLevel, level)}${_renderSection('Class & Subclass Features', sections.classFeatures, 'class', charData, 'All unlocked class and subclass features with detailed player-facing text.')}${_renderSection('Species Traits', sections.traits, 'traits', charData, 'Lineage and species traits affecting passives, actions, and saves.')}${_renderSection('Feats', sections.feats, 'feats', charData, 'Feat choices and exact rule impact.')}</div>`;

    container.__csCharData = charData || {};
    container.__csFeatureFilter = container.__csFeatureFilter || 'all';
    container.__csFeatureQuery = container.__csFeatureQuery || '';
    _bindInteractions(container);
    _applyFeatureFilters(container);
  }

  function _fetchSheetFeatures(charData, cb) {
    const charId = charData && (charData.id || charData.charId || charData.characterId);
    if (!charId) return cb(null, null);
    const params = new URLSearchParams();
    if (charData.sessionId) params.set('session_id', charData.sessionId);

    fetch('/api/character/' + encodeURIComponent(charId) + '/sheet' + (params.toString() ? '?' + params.toString() : ''))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (payload) {
        const character = payload && payload.character && typeof payload.character === 'object' ? payload.character : {};
        cb(null, {
          level: payload && payload.level,
          classData: payload && payload.classData,
          features: _safeArray(character.classFeatures).map((f) => _coerceFeature(f, { kind: 'class' })).filter(Boolean),
          traits: _safeArray(character.speciesTraits).map((f) => _coerceFeature(f, { kind: 'trait' })).filter(Boolean),
        });
      })
      .catch(function (err) { cb(err, null); });
  }

  function initFeaturesTab(container, charData) {
    if (!container) return;
    _render(container, charData || {}, null);
    _fetchSheetFeatures(charData || {}, function (err, payload) {
      if (err || !payload) return;
      _render(container, Object.assign({}, charData || {}, { features: payload.features, traits: payload.traits, level: payload.level }), payload);
    });
  }

  global.FeaturesTab = { initFeaturesTab: initFeaturesTab };
}(window));
