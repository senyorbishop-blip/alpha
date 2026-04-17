/*
 * client/static/js/character/tabs/features_tab.js
 * Features & Traits Tab — high-readability player reference cards.
 *
 * Exposes: window.FeaturesTab
 *   .initFeaturesTab(container, charData)
 */

(function initFeaturesTabModule(global) {
  'use strict';

  function _esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])
    );
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

  function _descHtml(text) {
    if (!text) return '<em>No detailed rules text is available for this feature yet.</em>';
    return String(text)
      .split(/\n{2,}/)
      .map(p => `<p>${_esc(p.trim()).replace(/\n/g, '<br>')}</p>`)
      .join('');
  }

  function _previewText(text, limit) {
    const maxLen = Number.isFinite(limit) ? Math.max(60, limit) : 220;
    const raw = String(text || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    return raw.length > maxLen ? raw.slice(0, maxLen - 1).trim() + '…' : raw;
  }

  function _firstSentence(text) {
    const raw = String(text || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    const match = raw.match(/^[^.!?]+[.!?]?/);
    return (match ? match[0] : raw).trim();
  }

  function _normalizeActionType(feature) {
    const raw = String(_firstText(
      feature && feature.actionType,
      feature && feature.type,
      feature && feature.raw && feature.raw.actionType,
      feature && feature.raw && feature.raw.type
    )).toLowerCase().trim();
    if (!raw) return 'Passive';
    if (raw === 'bonus' || raw === 'bonus action') return 'Bonus Action';
    if (raw === 'reaction') return 'Reaction';
    if (raw === 'action') return 'Action';
    if (raw === 'passive' || raw === 'always on' || raw === 'always-on') return 'Passive';
    return raw.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function _isPassive(feature) {
    return _normalizeActionType(feature).toLowerCase() === 'passive';
  }

  function _coerceFeature(entry, defaults) {
    const base = defaults && typeof defaults === 'object' ? defaults : {};
    if (!entry) return null;
    if (typeof entry === 'string') {
      return {
        name: entry,
        summary: '',
        description: '',
        level: Number(base.level || 0),
        source: _firstText(base.source, ''),
        kind: _firstText(base.kind, ''),
        section: _firstText(base.section, ''),
        isSubclass: !!base.isSubclass,
        subclassName: _firstText(base.subclassName, ''),
        className: _firstText(base.className, ''),
        actionType: _firstText(base.actionType, ''),
        resourceName: _firstText(base.resourceName, ''),
        range: _firstText(base.range, ''),
        duration: _firstText(base.duration, ''),
        save: _firstText(base.save, ''),
        trigger: _firstText(base.trigger, ''),
        usage: _firstText(base.usage, ''),
        recovery: _firstText(base.recovery, ''),
        effect: _firstText(base.effect, ''),
        tags: _safeArray(base.tags),
      };
    }

    const obj = typeof entry === 'object' ? entry : { name: String(entry) };
    const mechanics = obj.mechanics && typeof obj.mechanics === 'object' ? obj.mechanics : {};

    return {
      id: _firstText(obj.id, obj.featureId),
      name: _firstText(obj.name, obj.displayName, obj.title, obj.label, base.name, 'Feature'),
      summary: _firstText(obj.summary, obj.effect, obj.note, mechanics.summary, base.summary),
      description: _firstText(obj.description, obj.desc, obj.text, obj.longDescription, mechanics.description, base.description),
      level: Number(obj.level || obj.minLevel || base.level || 0),
      source: _firstText(obj.source, base.source),
      kind: _firstText(obj.kind, obj.sourceKind, obj.typeCategory, base.kind),
      section: _firstText(obj.section, base.section),
      className: _firstText(obj.className, base.className),
      subclassName: _firstText(obj.subclassName, base.subclassName),
      isSubclass: !!(obj.isSubclass || base.isSubclass),
      actionType: _firstText(obj.actionType, mechanics.actionType, obj.type, base.actionType),
      resourceName: _firstText(obj.resourceName, obj.resource, mechanics.resourceName, base.resourceName),
      range: _firstText(obj.range, mechanics.range, base.range),
      duration: _firstText(obj.duration, mechanics.duration, base.duration),
      save: _firstText(obj.save, mechanics.saveDC, mechanics.save, base.save),
      trigger: _firstText(obj.trigger, mechanics.trigger, base.trigger),
      usage: _firstText(obj.usage, mechanics.usesPerRest, base.usage),
      recovery: _firstText(obj.recovery, mechanics.recovery, base.recovery),
      effect: _firstText(obj.effect, mechanics.effect, mechanics.damageFormula, base.effect),
      tags: _safeArray(obj.tags || mechanics.tags || base.tags),
      raw: obj,
    };
  }

  function _dedupeFeatures(features) {
    const seen = new Set();
    return _safeArray(features).filter(function (feature) {
      if (!feature || !feature.name) return false;
      const key = [String(feature.name).toLowerCase(), feature.level || 0, String(feature.source || '').toLowerCase(), feature.isSubclass ? 'sub' : 'core'].join('::');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function _cleanFeatureSummary(feature) {
    return _firstText(
      feature && feature.summary,
      feature && feature.effect,
      _firstSentence(feature && feature.description),
      _previewText(feature && feature.description, 220),
      'Open to read the full details for this feature.'
    );
  }

  function _featureTypeKey(feature) {
    const normalizedKind = String(feature && feature.kind || '').toLowerCase();
    if (normalizedKind === 'feat') return 'feats';
    if (normalizedKind === 'trait' || normalizedKind === 'origin' || normalizedKind === 'species') return 'traits';
    if (feature && feature.isSubclass) return 'subclass';
    return 'class';
  }

  function _buildFilterTokens(feature) {
    const tokens = new Set();
    const featureType = _featureTypeKey(feature);
    tokens.add('all');
    tokens.add(featureType);
    tokens.add(_isPassive(feature) ? 'passive' : 'active');
    if (feature && feature.resourceName) tokens.add('resource');
    return Array.from(tokens);
  }

  function _featureSearchBlob(feature) {
    const values = [
      feature && feature.name,
      feature && feature.summary,
      feature && feature.description,
      feature && feature.effect,
      feature && feature.source,
      feature && feature.className,
      feature && feature.subclassName,
      feature && feature.resourceName,
      feature && feature.actionType,
      _safeArray(feature && feature.tags).join(' '),
      _buildFilterTokens(feature).join(' '),
    ];
    return values.filter(Boolean).join(' ').toLowerCase();
  }

  function _featureTagPills(feature) {
    const pills = [];
    const actionType = _normalizeActionType(feature);
    pills.push(actionType);
    if (feature && feature.resourceName) pills.push(feature.resourceName);
    if (feature && feature.usage) pills.push('Resource');
    if (feature && feature.recovery) pills.push('Rest Recharge');
    if (feature && feature.isSubclass) pills.push('Subclass');
    if (/aura/i.test(String(feature && feature.name || ''))) pills.push('Aura');
    if (/once per turn/i.test(String(feature && feature.description || ''))) pills.push('Once Per Turn');
    return Array.from(new Set(pills)).slice(0, 5);
  }

  function _featureSourceLine(feature) {
    const from = _firstText(feature && feature.source, feature && feature.className, 'Character feature');
    const level = feature && feature.level ? ('Level ' + feature.level) : '';
    return [from, level].filter(Boolean).join(' • ');
  }

  function _featureFacts(feature) {
    const rows = [];
    rows.push({ label: 'Action Type', value: _normalizeActionType(feature) });
    if (feature && feature.resourceName) rows.push({ label: 'Resource', value: feature.resourceName });
    if (feature && feature.usage) rows.push({ label: 'Use Cost', value: feature.usage });
    if (feature && feature.recovery) rows.push({ label: 'Recharge', value: feature.recovery });
    if (feature && feature.range) rows.push({ label: 'Range', value: feature.range });
    if (feature && feature.duration) rows.push({ label: 'Duration', value: feature.duration });
    if (feature && feature.save) rows.push({ label: 'Save', value: feature.save });
    if (feature && feature.trigger) rows.push({ label: 'Trigger', value: feature.trigger });
    if (feature && feature.effect) rows.push({ label: 'Effect', value: feature.effect });
    return rows;
  }

  function _renderFeatureBody(feature) {
    const summary = _cleanFeatureSummary(feature);
    const details = _firstText(feature && feature.description, '');
    const facts = _featureFacts(feature);

    return `<div class="cs-feature-body-shell">
      <div class="cs-feature-body-summary"><strong>${_esc(summary)}</strong></div>
      ${facts.length ? `<div class="cs-feature-facts">${facts.map(function (fact) {
        return `<div class="cs-feature-fact"><span class="cs-feature-fact-label">${_esc(fact.label)}</span><span class="cs-feature-fact-value">${_esc(fact.value)}</span></div>`;
      }).join('')}</div>` : ''}
      <div class="cs-feature-body-rules">${_descHtml(details || 'Rules details have not been fully authored for this entry yet.')}</div>
    </div>`;
  }

  function _renderFeatureItem(feature, idx) {
    const summary = _cleanFeatureSummary(feature);
    const tags = _featureTagPills(feature);
    const sourceLine = _featureSourceLine(feature);
    const filterTokens = _buildFilterTokens(feature).join(' ');
    const searchBlob = _featureSearchBlob(feature);
    const featureId = _firstText(feature && feature.id, feature && feature.name, 'feature-' + idx).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

    return `<article class="cs-feature-item" data-feature-id="${_esc(featureId)}" data-feature-type="${_esc(_featureTypeKey(feature))}" data-feature-filters="${_esc(filterTokens)}" data-feature-search="${_esc(searchBlob)}" data-feature-level="${_esc(String(feature.level || 0))}">
      <header class="cs-feature-header" role="button" tabindex="0" aria-expanded="false" aria-label="${_esc(feature.name || 'Feature')}">
        <div class="cs-feature-maincopy">
          <div class="cs-feature-title-row"><span class="cs-feature-name">${_esc(feature.name || 'Feature')}</span></div>
          <div class="cs-feature-inline-meta">${_esc(sourceLine)}</div>
          <div class="cs-feature-preview"><strong>${_esc(summary)}</strong></div>
        </div>
        <span class="cs-feature-meta">${tags.map(function (tag) {
          return `<span class="cs-feature-kind-badge">${_esc(tag)}</span>`;
        }).join('')}<span class="cs-feature-chevron" aria-hidden="true">&#9658;</span></span>
      </header>
      <div class="cs-feature-body">${_renderFeatureBody(feature)}</div>
    </article>`;
  }

  function _renderSection(title, items, opts) {
    const options = opts && typeof opts === 'object' ? opts : {};
    const list = _safeArray(items);
    const copy = _firstText(options.copy, '');
    if (!list.length) {
      return `<section class="cs-feature-section" data-feature-section="${_esc(options.sectionKey || 'all')}">
        <div class="cs-feature-section-title">${_esc(title)}</div>
        ${copy ? `<div class="cs-feature-section-copy">${_esc(copy)}</div>` : ''}
        <div class="cs-feature-list">
          <div class="cs-empty-state"><span class="cs-empty-state-icon">📜</span><span>${_esc(options.emptyLabel || 'No features found in this section.')}</span></div>
        </div>
      </section>`;
    }

    return `<section class="cs-feature-section" data-feature-section="${_esc(options.sectionKey || 'all')}">
      <div class="cs-feature-section-title">${_esc(title)}</div>
      ${copy ? `<div class="cs-feature-section-copy">${_esc(copy)}</div>` : ''}
      <div class="cs-feature-list">${list.map(function (feature, idx) { return _renderFeatureItem(feature, idx); }).join('')}</div>
    </section>`;
  }

  function _renderSummaryStrip(data) {
    const classFeatures = _safeArray(data.classFeatures);
    const subclassFeatures = classFeatures.filter(function (feature) { return !!feature.isSubclass; });
    const coreFeatures = classFeatures.filter(function (feature) { return !feature.isSubclass; });
    const traits = _safeArray(data.traits);
    const feats = _safeArray(data.feats);
    const activeCount = classFeatures.filter(function (feature) { return !_isPassive(feature); }).length;
    const resourceCount = classFeatures.filter(function (feature) { return !!feature.resourceName; }).length;

    function card(label, value, note) {
      return `<div class="cs-traits-summary-card"><div class="cs-traits-summary-label">${_esc(label)}</div><div class="cs-traits-summary-value">${_esc(String(value))}</div><div class="cs-traits-summary-note">${_esc(note)}</div></div>`;
    }

    return `<div class="cs-traits-summary-grid cs-features-redesign-summary">
      ${card('Core Features', coreFeatures.length, 'class fundamentals')}
      ${card('Subclass Features', subclassFeatures.length, 'build-specific unlocks')}
      ${card('Traits', traits.length, 'species/background traits')}
      ${card('Feats', feats.length, 'feat rules')}
      ${card('Active', activeCount, 'action / bonus / reaction tools')}
      ${card('Resource Linked', resourceCount, 'uses and recharge cadence')}
    </div>`;
  }

  function _renderFeatureControls() {
    return `<section class="cs-overview-section cs-feature-controls-section cs-features-redesign-controls">
      <div class="cs-overview-section-title">Features & Traits</div>
      <div class="cs-overview-copy">Scan quickly, then expand any card for full player-facing rules, costs, and timing.</div>
      <div class="cs-feature-toolbar">
        <input type="search" class="cs-feature-search" data-feature-search placeholder="Search by feature, resource, action type, or keyword…" aria-label="Search features" />
        <div class="cs-feature-filter-row" role="tablist" aria-label="Feature filters">
          <button type="button" class="cs-feature-filter-chip active" data-feature-filter="all">All</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="class">Class</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="subclass">Subclass</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="traits">Traits</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="feats">Feats</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="passive">Passive</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="active">Active</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="resource">Resource</button>
        </div>
      </div>
    </section>`;
  }

  function _extractSections(charData, sheetData) {
    const merged = Object.assign({}, charData || {}, sheetData || {});
    const nativeFeatures = _safeArray(charData && charData.nativeFeatures).map(function (item) {
      return _coerceFeature(item, { source: 'Native Runtime', kind: 'class' });
    }).filter(Boolean);

    const classFeatures = _dedupeFeatures(
      _safeArray(merged.features).map(function (item) {
        return _coerceFeature(item, { source: 'Class Feature', kind: 'class' });
      }).concat(
        _safeArray(charData && charData.nativeClassFeatures).map(function (item) {
          return _coerceFeature(item, { source: 'Class Feature', kind: 'class' });
        })
      ).filter(Boolean)
    );

    const traits = _dedupeFeatures(
      _safeArray(merged.traits).map(function (item) {
        return _coerceFeature(item, { source: 'Trait', kind: 'trait' });
      })
    );

    const feats = _dedupeFeatures(
      _safeArray(merged.feats).map(function (item) {
        return _coerceFeature(item, { source: 'Feat', kind: 'feat' });
      })
    );

    const mergedClassFeatures = _dedupeFeatures(nativeFeatures.concat(classFeatures));
    const coreClassFeatures = mergedClassFeatures.filter(function (feature) { return !feature.isSubclass; });
    const subclassFeatures = mergedClassFeatures.filter(function (feature) { return !!feature.isSubclass; });

    return {
      classFeatures: mergedClassFeatures,
      coreClassFeatures,
      subclassFeatures,
      traits,
      feats,
    };
  }

  function _fetchSheetFeatures(charData, cb) {
    const charId = charData && (charData.id || charData.charId || charData.characterId);
    if (!charId) {
      cb(null, null);
      return;
    }

    const params = new URLSearchParams();
    if (charData.sessionId) params.set('session_id', charData.sessionId);

    fetch(`/api/character/${encodeURIComponent(charId)}/sheet${params.toString() ? '?' + params.toString() : ''}`)
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (data) {
        if (!data || !data.character) {
          cb(null, null);
          return;
        }
        const character = data.character;
        const result = {};

        const rawFeatures = character.classFeatures;
        if (rawFeatures && typeof rawFeatures === 'object' && !Array.isArray(rawFeatures)) {
          const flat = [];
          Object.entries(rawFeatures).forEach(function (entry) {
            const lvl = entry[0];
            const items = entry[1];
            if (!Array.isArray(items)) return;
            items.forEach(function (item) {
              flat.push(_coerceFeature(item, { level: parseInt(lvl, 10) || 0, source: 'Character Sheet API', kind: 'class' }));
            });
          });
          result.features = flat.filter(Boolean);
        } else if (Array.isArray(rawFeatures)) {
          result.features = rawFeatures.map(function (item) {
            return _coerceFeature(item, { source: 'Character Sheet API', kind: 'class' });
          }).filter(Boolean);
        }

        if (Array.isArray(character.speciesTraits)) {
          result.traits = character.speciesTraits.map(function (trait) {
            return _coerceFeature(trait, { source: 'Species Trait', kind: 'trait' });
          }).filter(Boolean);
        }

        cb(null, result);
      })
      .catch(function (err) { cb(err, null); });
  }

  function _applyFeatureFilters(container) {
    if (!container) return;
    const query = String(container.__csFeatureQuery || '').trim().toLowerCase();
    const activeFilter = String(container.__csFeatureFilter || 'all').toLowerCase();

    const cards = Array.from(container.querySelectorAll('.cs-feature-item'));
    cards.forEach(function (card) {
      const filters = String(card.getAttribute('data-feature-filters') || '').toLowerCase().split(/\s+/).filter(Boolean);
      const searchBlob = String(card.getAttribute('data-feature-search') || '').toLowerCase();
      const filterMatch = activeFilter === 'all' || filters.indexOf(activeFilter) !== -1;
      const queryMatch = !query || searchBlob.indexOf(query) !== -1;
      card.hidden = !(filterMatch && queryMatch);
    });

    Array.from(container.querySelectorAll('.cs-feature-section')).forEach(function (section) {
      const visibleRows = Array.from(section.querySelectorAll('.cs-feature-item')).filter(function (row) { return !row.hidden; });
      const hasRows = section.querySelectorAll('.cs-feature-item').length > 0;
      if (hasRows) section.hidden = !visibleRows.length;
    });

    Array.from(container.querySelectorAll('.cs-feature-filter-chip')).forEach(function (chip) {
      chip.classList.toggle('active', String(chip.getAttribute('data-feature-filter') || '').toLowerCase() === activeFilter);
    });

    const empty = container.querySelector('[data-features-empty-state]');
    if (empty) {
      const anyVisible = cards.some(function (card) { return !card.hidden; });
      empty.hidden = anyVisible;
    }
  }

  function _bindInteractions(container) {
    if (!container || container.__csFeaturesBound) return;
    container.__csFeaturesBound = true;

    container.addEventListener('click', function (event) {
      const filterChip = event.target.closest('[data-feature-filter]');
      if (filterChip) {
        event.preventDefault();
        container.__csFeatureFilter = String(filterChip.getAttribute('data-feature-filter') || 'all');
        _applyFeatureFilters(container);
        return;
      }

      const header = event.target.closest('.cs-feature-header');
      if (!header) return;
      const item = header.closest('.cs-feature-item');
      if (!item) return;
      const featureId = String(item.getAttribute('data-feature-id') || '');

      if (!container.__csFeatureOpenSet) container.__csFeatureOpenSet = new Set();

      const isOpen = item.classList.toggle('open');
      header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');

      if (isOpen) container.__csFeatureOpenSet.add(featureId);
      else container.__csFeatureOpenSet.delete(featureId);
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

  function _restoreOpenState(container) {
    const openSet = container.__csFeatureOpenSet;
    if (!openSet || typeof openSet.has !== 'function') return;
    Array.from(container.querySelectorAll('.cs-feature-item')).forEach(function (item) {
      const featureId = String(item.getAttribute('data-feature-id') || '');
      if (!openSet.has(featureId)) return;
      item.classList.add('open');
      const header = item.querySelector('.cs-feature-header');
      if (header) header.setAttribute('aria-expanded', 'true');
    });
  }

  function _render(container, charData, sheetData) {
    const sections = _extractSections(charData, sheetData);

    const coreMarkup = _renderSection('Core Class Features', sections.coreClassFeatures, {
      sectionKey: 'class',
      copy: 'Your main class loop, fundamentals, and scaling features.',
      emptyLabel: 'No core class features found.',
    });

    const subclassMarkup = _renderSection('Subclass Features', sections.subclassFeatures, {
      sectionKey: 'subclass',
      copy: 'Build-specific features from your selected subclass.',
      emptyLabel: 'No subclass features are currently unlocked for this character.',
    });

    const traitsMarkup = _renderSection('Species / Origin Traits', sections.traits, {
      sectionKey: 'traits',
      copy: 'Lineage, species, and origin abilities that shape passive and active play.',
      emptyLabel: 'No species or origin traits are loaded.',
    });

    const featsMarkup = _renderSection('Feats', sections.feats, {
      sectionKey: 'feats',
      copy: 'Feat choices and their exact gameplay impact.',
      emptyLabel: 'No feats are recorded for this build.',
    });

    container.innerHTML = `<div class="cs-traits-shell cs-traits-shell-readable cs-features-redesign-shell">
      ${_renderFeatureControls()}
      ${_renderSummaryStrip(sections)}
      ${coreMarkup}
      ${subclassMarkup}
      ${traitsMarkup}
      ${featsMarkup}
      <div class="cs-empty-state" data-features-empty-state hidden><span class="cs-empty-state-icon">🔎</span><span>No matching features for the current search and filter.</span></div>
    </div>`;

    container.__csCharData = charData || {};
    container.__csFeaturesCache = _safeArray(sections.classFeatures).concat(_safeArray(sections.traits)).concat(_safeArray(sections.feats));
    container.__csFeatureFilter = container.__csFeatureFilter || 'all';
    container.__csFeatureQuery = container.__csFeatureQuery || '';

    _bindInteractions(container);
    _restoreOpenState(container);
    _applyFeatureFilters(container);
  }

  function initFeaturesTab(container, charData) {
    if (!container) return;
    _render(container, charData, null);
    _fetchSheetFeatures(charData, function (err, sheetData) {
      if (!err && sheetData) _render(container, charData, sheetData);
    });
  }

  global.FeaturesTab = { initFeaturesTab: initFeaturesTab };

}(window));
