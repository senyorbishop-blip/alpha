(function initCharacterBuilderApi(global) {
  const CACHE_TTL_MS = 5 * 60 * 1000;
  let _catalogCache = null;
  let _catalogFetchPromise = null;

  function normalizeRulesMode(value) {
    const mode = String(value || '').trim().toLowerCase();
    if (mode === 'classic' || mode === 'custom') return mode;
    return 'casual';
  }

  function dispatchCatalogUpdated(catalog) {
    try {
      global.dispatchEvent(new CustomEvent('character-builder-catalog-updated', {
        detail: { catalog: catalog || null },
      }));
    } catch (_) {
      // No-op; rendering will refresh on next user state interaction.
    }
  }

  function hasFreshCache(rulesMode) {
    if (!_catalogCache || typeof _catalogCache !== 'object') return false;
    if (_catalogCache.rulesMode !== rulesMode) return false;
    const loadedAt = Number(_catalogCache.loadedAt || 0);
    if (!Number.isFinite(loadedAt) || loadedAt <= 0) return false;
    return (Date.now() - loadedAt) < CACHE_TTL_MS;
  }

  function getEmptyCatalog(rulesMode) {
    return {
      ok: false,
      rulesMode: normalizeRulesMode(rulesMode),
      rulesetId: '',
      species: [],
      classes: [],
      subclasses: [],
      subclassesByClass: {},
      futureContent: { feats: [], spells: [] },
      loadedAt: Date.now(),
    };
  }

  function normalizeCatalogPayload(payload, rulesMode) {
    const src = payload && typeof payload === 'object' ? payload : {};
    const species = Array.isArray(src.species) ? src.species : [];
    const classes = Array.isArray(src.classes) ? src.classes : [];
    const subclasses = Array.isArray(src.subclasses) ? src.subclasses : [];
    const byClass = src.subclassesByClass && typeof src.subclassesByClass === 'object'
      ? src.subclassesByClass
      : {};

    return {
      ok: src.ok === true,
      rulesMode: normalizeRulesMode(src.rulesMode || rulesMode),
      rulesetId: String(src.rulesetId || ''),
      species,
      classes,
      subclasses,
      subclassesByClass: byClass,
      futureContent: src.futureContent && typeof src.futureContent === 'object'
        ? src.futureContent
        : { feats: [], spells: [] },
      loadedAt: Date.now(),
    };
  }

  async function fetchCatalog(options) {
    const opts = options && typeof options === 'object' ? options : {};
    const rulesMode = normalizeRulesMode(opts.rulesMode);

    if (hasFreshCache(rulesMode)) {
      return _catalogCache;
    }

    if (_catalogFetchPromise) {
      return _catalogFetchPromise;
    }

    const qs = new URLSearchParams();
    qs.set('rules_mode', rulesMode);

    _catalogFetchPromise = fetch('/api/character/content/catalog?' + qs.toString(), {
      method: 'GET',
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    })
      .then(async function onResponse(res) {
        if (!res.ok) throw new Error('catalog_fetch_failed');
        const json = await res.json();
        _catalogCache = normalizeCatalogPayload(json, rulesMode);
        dispatchCatalogUpdated(_catalogCache);
        return _catalogCache;
      })
      .catch(function onCatalogError() {
        _catalogCache = getEmptyCatalog(rulesMode);
        dispatchCatalogUpdated(_catalogCache);
        return _catalogCache;
      })
      .finally(function clearPromise() {
        _catalogFetchPromise = null;
      });

    return _catalogFetchPromise;
  }

  function getCachedCatalog() {
    return _catalogCache;
  }

  function getSubclassesForClass(classId) {
    const catalog = _catalogCache || getEmptyCatalog('casual');
    const key = String(classId || '').trim().toLowerCase();
    if (!key) return [];
    const byClass = catalog.subclassesByClass && typeof catalog.subclassesByClass === 'object'
      ? catalog.subclassesByClass
      : {};
    const rows = Array.isArray(byClass[key]) ? byClass[key] : [];
    return rows.slice();
  }

  global.CharacterBuilderAPI = {
    fetchCatalog,
    getCachedCatalog,
    getSubclassesForClass,
  };
})(window);
