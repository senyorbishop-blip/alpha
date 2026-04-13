(function () {
  const state = {
    manifest: null,
    loaded: false,
    loadingPromise: null,
    listeners: new Set(),
  };

  const PROP_KINDS = [
    // furniture
    'table', 'chair', 'bookshelf', 'desk', 'throne', 'bench',
    // containers / loot
    'barrel', 'crate', 'chest', 'sack', 'lockbox', 'loot_pile',
    // lighting
    'torch', 'brazier', 'lantern', 'campfire',
    // religious / ritual
    'altar', 'ritual_circle', 'shrine',
    // structures
    'door',
    // clutter
    'bones', 'rubble',
    // hazards
    'spike_trap', 'pressure_plate', 'poison_vent',
    // camp
    'bedroll', 'cooking_pot', 'tent',
    // arcane
    'magic_portal',
    // legacy / generic
    'tree', 'rock',
  ];
  const MARKER_KINDS = ['city', 'town', 'settlement', 'ruin', 'shop', 'tavern', 'camp', 'landmark', 'blacksmith', 'market', 'castle', 'harbor', 'forest', 'mountain'];

  function normalizeAsset(asset) { return cloneAsset(asset); }

  function cloneAsset(asset) {
    return asset ? { ...asset, tags: Array.isArray(asset.tags) ? [...asset.tags] : [] } : null;
  }

  function versionAssetPath(path, version) {
    const raw = String(path || '').trim();
    const v = Number(version || 0) || 0;
    if (!raw || !v || raw.startsWith('data:') || raw.startsWith('blob:')) return raw;
    return `${raw}${raw.includes('?') ? '&' : '?'}v=${v}`;
  }

  function applyManifestVersion(asset, version) {
    if (!asset) return null;
    const next = cloneAsset(asset);
    if (next.file) next.file = versionAssetPath(next.file, version);
    if (next.thumbnail) next.thumbnail = versionAssetPath(next.thumbnail, version);
    return next;
  }

  function notify() {
    state.listeners.forEach((listener) => {
      try { listener(state.manifest); } catch (err) { console.warn('[editor-assets] listener failed', err); }
    });
  }

  async function loadManifest(env = {}) {
    if (state.loadingPromise) return state.loadingPromise;
    const fetchImpl = env.fetch || window.fetch?.bind(window);
    if (!fetchImpl) throw new Error('fetch unavailable for asset manifest');
    state.loadingPromise = fetchImpl('/api/assets/manifest', { cache: 'no-store' })
      .then((res) => {
        if (!res.ok) throw new Error(`asset manifest ${res.status}`);
        return res.json();
      })
      .then((manifest) => {
        const version = Number(manifest?.version || 1);
        const assets = Array.isArray(manifest?.assets) ? manifest.assets.map((asset) => applyManifestVersion(asset, version)).filter(Boolean) : [];
        const packs = Array.isArray(manifest?.packs) ? manifest.packs.map((pack) => ({ ...pack })) : [];
        state.manifest = { version, packs, assets };
        state.loaded = true;
        notify();
        return state.manifest;
      })
      .catch((err) => {
        state.loadingPromise = null;
        if (typeof env.reportError === 'function') env.reportError('editor asset manifest', err);
        throw err;
      });
    return state.loadingPromise;
  }

  function getManifest() { return state.manifest; }

  function getEntries(filter = {}) {
    const assets = state.manifest?.assets || [];
    const category = String(filter.category || '').trim().toLowerCase();
    const stylePack = String(filter.stylePack || '').trim().toLowerCase();
    const query = String(filter.query || '').trim().toLowerCase();
    const tag = String(filter.tag || '').trim().toLowerCase();
    const sort = String(filter.sort || 'relevance').trim().toLowerCase();
    const uploadedOnly = !!filter.uploadedOnly;
    const filtered = assets.filter((asset) => {
      if (uploadedOnly && String(asset.license || '').toLowerCase() !== 'user_imported') return false;
      if (category && String(asset.category || '').toLowerCase() !== category) return false;
      if (stylePack && String(asset.style_pack || '').toLowerCase() !== stylePack) return false;
      const tags = Array.isArray(asset.tags) ? asset.tags.map((v) => String(v).toLowerCase()) : [];
      if (tag && !tags.includes(tag)) return false;
      if (!query) return true;
      const hay = [asset.id, asset.name, asset.subtype, ...(asset.tags || [])].join(' ').toLowerCase();
      return hay.includes(query);
    }).map(cloneAsset);

    const relevanceScore = (asset) => {
      if (!query) return 0;
      const q = query;
      const id = String(asset.id || '').toLowerCase();
      const name = String(asset.name || '').toLowerCase();
      const subtype = String(asset.subtype || '').toLowerCase();
      const tags = Array.isArray(asset.tags) ? asset.tags.map((v) => String(v).toLowerCase()) : [];
      if (name === q) return 100;
      if (id === q) return 95;
      if (tags.includes(q)) return 90;
      if (name.startsWith(q)) return 80;
      if (subtype.startsWith(q)) return 70;
      if (tags.some((entry) => entry.startsWith(q))) return 60;
      if (name.includes(q)) return 50;
      if (subtype.includes(q)) return 40;
      if (id.includes(q)) return 30;
      return 10;
    };

    const byName = (a, b) => String(a.name || a.id || '').localeCompare(String(b.name || b.id || ''), undefined, { sensitivity: 'base' });

    filtered.sort((a, b) => {
      if (sort === 'name_asc') return byName(a, b);
      if (sort === 'name_desc') return byName(b, a);
      if (sort === 'pack') {
        const packCompare = String(a.style_pack || '').localeCompare(String(b.style_pack || ''), undefined, { sensitivity: 'base' });
        return packCompare || byName(a, b);
      }
      if (sort === 'category') {
        const categoryCompare = String(a.category || '').localeCompare(String(b.category || ''), undefined, { sensitivity: 'base' });
        return categoryCompare || byName(a, b);
      }
      return relevanceScore(b) - relevanceScore(a) || byName(a, b);
    });
    return filtered;
  }

  function getPopularTags(filter = {}) {
    const counts = new Map();
    const category = String(filter.category || '').trim().toLowerCase();
    const stylePack = String(filter.stylePack || '').trim().toLowerCase();
    const query = String(filter.query || '').trim().toLowerCase();
    (state.manifest?.assets || []).forEach((asset) => {
      if (category && String(asset.category || '').toLowerCase() !== category) return;
      if (stylePack && String(asset.style_pack || '').toLowerCase() !== stylePack) return;
      const hay = [asset.id, asset.name, asset.subtype, ...(asset.tags || [])].join(' ').toLowerCase();
      if (query && !hay.includes(query)) return;
      (asset.tags || []).forEach((tag) => {
        const key = String(tag || '').trim().toLowerCase();
        if (!key) return;
        counts.set(key, (counts.get(key) || 0) + 1);
      });
    });
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 12)
      .map(([tag, count]) => ({ tag, count }));
  }

  function getEntry(assetId) {
    const match = (state.manifest?.assets || []).find((asset) => asset.id === assetId);
    return cloneAsset(match || null);
  }

  function getPacks() { return (state.manifest?.packs || []).map((pack) => ({ ...pack })); }

  function getCategories() {
    const values = new Set(['terrain', 'props', 'markers', 'vfx', 'tokens', 'images']);
    (state.manifest?.assets || []).forEach((asset) => { if (asset?.category) values.add(String(asset.category).toLowerCase()); });
    return Array.from(values).map((id) => ({ id, name: id === 'vfx' ? 'VFX' : id.charAt(0).toUpperCase() + id.slice(1) }));
  }

  function getPackShortcuts() {
    const packIds = new Set((state.manifest?.packs || []).map((pack) => String(pack.id || '').toLowerCase()).filter(Boolean));
    const shortcuts = [
      { id: 'all', label: 'All', category: '', stylePack: '', query: '' },
      { id: 'world_map', label: 'World Map', category: 'terrain', stylePack: packIds.has('world_map') ? 'world_map' : '', query: '' },
      { id: 'tactical', label: 'Tactical', category: 'terrain', stylePack: packIds.has('base_fantasy') ? 'base_fantasy' : '', query: packIds.has('base_fantasy') ? '' : 'battle dungeon' },
      { id: 'props', label: 'Props', category: 'props', stylePack: packIds.has('fantasy_props') ? 'fantasy_props' : '', query: '' },
      { id: 'markers', label: 'Markers', category: 'markers', stylePack: packIds.has('world_markers') ? 'world_markers' : '', query: '' },
      { id: 'city', label: 'City', category: 'markers', stylePack: '', query: 'city town market harbor castle' },
      { id: 'cave', label: 'Cave', category: 'terrain', stylePack: '', query: 'cave stone dungeon' },
      { id: 'uploaded', label: 'Uploaded', category: '', stylePack: '', query: '', uploadedOnly: true },
    ];
    return shortcuts.filter((shortcut) => shortcut.id === 'all' || shortcut.id === 'uploaded' || shortcut.stylePack || shortcut.query || shortcut.category);
  }

  function bestMatch(asset, allowedKinds) {
    const terms = [asset?.subtype, asset?.id, asset?.name, ...(asset?.tags || [])].filter(Boolean).map((v) => String(v).toLowerCase());
    for (const kind of allowedKinds) {
      if (terms.some((term) => term.includes(kind))) return kind;
    }
    return '';
  }

  function applyTerrainAsset(env = {}, assetId) {
    const asset = getEntry(assetId);
    if (!asset) return { ok: false, message: 'Asset not found.' };
    // Custom uploaded images must be placed as image stamps, not painted as terrain
    // tiles — terrain transforms would distort them.  Detect by license (most
    // reliable), style_pack, or the presence of a 'custom' tag.
    const isCustomImport = asset.file && (
      String(asset.license || '').toLowerCase() === 'user_imported' ||
      String(asset.style_pack || '').toLowerCase() === 'custom_imports' ||
      (asset.tags || []).some(t => String(t).toLowerCase() === 'custom')
    );
    if (isCustomImport) return applyImageAsset(env, assetId);
    if (Number(asset.terrain_id || 0) <= 0) return { ok: false, message: 'That terrain asset cannot be applied yet.' };
    // If the asset has a file (custom terrain), use setEditorTerrainAsset to register it
    if (asset.file && typeof env.setEditorTerrainAsset === 'function') {
      const success = env.setEditorTerrainAsset(normalizeAsset(asset));
      if (success) {
        return { ok: true, message: `${asset.name || 'Terrain'} is now the active terrain brush.` };
      }
    }
    // Fall back to the simple setEditorTerrain for built-in terrains
    if (typeof env.setEditorTerrain !== 'function') return { ok: false, message: 'Terrain tool unavailable.' };
    env.setEditorTerrain(Number(asset.terrain_id));
    return { ok: true, message: `${asset.name || 'Terrain'} is now the active terrain brush.` };
  }

  // Prop kinds that support interactive inventory (chest loot / shop stock).
  // File-based assets matching these kinds should be placed as the native kind
  // so that the inventory popup works, rather than as a non-interactive custom_asset.
  const INTERACTIVE_PROP_KINDS = ['chest', 'merchant', 'store', 'shop', 'tavern', 'blacksmith', 'market_stall', 'inn'];
  const NATIVE_FILE_PROP_KINDS = [...INTERACTIVE_PROP_KINDS, 'barrel', 'crate', 'bookshelf', 'table', 'torch', 'campfire', 'door', 'guild_board', 'mimic'];

  function applyPropAsset(env = {}, assetId) {
    const asset = getEntry(assetId);
    if (!asset) return { ok: false, message: 'Prop asset not found.' };
    if (typeof env.setEditorLayerMode === 'function') env.setEditorLayerMode('props');
    // For file-based assets, check whether they match an interactive prop kind first.
    // Interactive kinds (chest, shops) need to use the native prop kind so the inventory
    // popup works. Non-interactive file assets fall through to custom_asset placement.
    if (asset.file) {
      const interactiveKind = bestMatch(asset, NATIVE_FILE_PROP_KINDS);
      if (interactiveKind && typeof env.setEditorPropKind === 'function') {
        const normalized = normalizeAsset(asset);
        if (typeof env.setSelectedEditorPropAsset === 'function') {
          // Preserve the selected file asset so native interactive props (e.g. chest/shop)
          // can keep gameplay behavior while drawing the imported image.
          env.setSelectedEditorPropAsset(normalized);
        }
        env.setEditorPropKind(interactiveKind);
        if (typeof env.onInteractivePropAssetApplied === 'function') {
          env.onInteractivePropAssetApplied(normalized, interactiveKind);
        }
        return { ok: true, message: `${asset.name || 'Prop'} mapped to the ${interactiveKind} prop tool.` };
      }
      if (typeof env.setSelectedEditorPropAsset === 'function' && typeof env.setEditorPropKind === 'function') {
        env.setSelectedEditorPropAsset(normalizeAsset(asset));
        env.setEditorPropKind('custom_asset');
        return { ok: true, message: `${asset.name || 'Prop'} is now the active custom prop stamp.` };
      }
      return { ok: false, message: 'Custom prop placement is unavailable in this build.' };
    }
    // For assets without a file, fall back to matching a procedural prop kind.
    const kind = bestMatch(asset, PROP_KINDS);
    if (kind && typeof env.setEditorPropKind === 'function') {
      if (typeof env.setSelectedEditorPropAsset === 'function') env.setSelectedEditorPropAsset(null);
      env.setEditorPropKind(kind);
      return { ok: true, message: `${asset.name || 'Prop'} mapped to the ${kind} prop tool.` };
    }
    if (typeof env.setSelectedEditorPropAsset === 'function' && typeof env.setEditorPropKind === 'function') {
      env.setSelectedEditorPropAsset(normalizeAsset(asset));
      env.setEditorPropKind('custom_asset');
      return { ok: true, message: `${asset.name || 'Prop'} is now the active custom prop stamp.` };
    }
    return { ok: false, message: 'Custom prop placement is unavailable in this build.' };
  }

  function applyMarkerAsset(env = {}, assetId) {
    const asset = getEntry(assetId);
    if (!asset) return { ok: false, message: 'Marker asset not found.' };
    const kind = bestMatch(asset, MARKER_KINDS);
    if (kind && typeof env.setEditorMarkerKind === 'function') {
      if (typeof env.setSelectedEditorMarkerAsset === 'function') env.setSelectedEditorMarkerAsset(null);
      env.setEditorMarkerKind(kind);
      return { ok: true, message: `${asset.name || 'Marker'} mapped to the ${kind} marker tool.` };
    }
    if (typeof env.setSelectedEditorMarkerAsset === 'function' && typeof env.setEditorMarkerKind === 'function') {
      env.setSelectedEditorMarkerAsset(normalizeAsset(asset));
      env.setEditorMarkerKind('custom_asset');
      return { ok: true, message: `${asset.name || 'Marker'} is now the active custom marker stamp.` };
    }
    return { ok: false, message: 'Custom marker placement is unavailable in this build.' };
  }

  function applyImageAsset(env = {}, assetId) {
    const asset = getEntry(assetId);
    if (!asset) return { ok: false, message: 'Image asset not found.' };
    const normalizedAsset = normalizeAsset(asset);
    // Auto-detect WxH size from asset name (e.g. "Wall_Stone_B_2x1" → inject tag "2x1")
    // so buildEditorPropItem can size the stamp correctly without manual tagging.
    const hasExplicitSizeTag = normalizedAsset.tags.some(t => /^\d+x\d+$/i.test(String(t)));
    if (!hasExplicitSizeTag) {
      const m = String(asset.name || '').match(/(?:^|[_\-\s])(\d+)x(\d+)(?:[_\-\s]|$)/i);
      if (m) {
        normalizedAsset.tags = [...normalizedAsset.tags, `${m[1]}x${m[2]}`];
      } else if (Number(asset.img_w) > 0 && Number(asset.img_h) > 0) {
        // Derive grid dimensions from stored pixel size — use actual grid cell counts,
        // not a simplified aspect ratio, so a 400×200 px image stamps as 4×2 cells.
        const w = Math.max(1, Math.round(Number(asset.img_w) / 100));
        const h = Math.max(1, Math.round(Number(asset.img_h) / 100));
        normalizedAsset.tags = [...normalizedAsset.tags, `${w}x${h}`];
      }
    }
    if (typeof env.setSelectedEditorImageAsset === 'function' && typeof env.setEditorLayerMode === 'function' && typeof env.setEditorPropKind === 'function') {
      env.setSelectedEditorImageAsset(normalizedAsset);
      env.setEditorLayerMode('images');
      env.setEditorPropKind('custom_asset');
      return { ok: true, message: `${asset.name || 'Image'} is ready to place. Click the map to position it.` };
    }
    return { ok: false, message: 'Image placement is unavailable in this build.' };
  }

  function applyAsset(env = {}, assetId) {
    const asset = getEntry(assetId);
    if (!asset) return { ok: false, message: 'Asset not found.' };
    const category = String(asset.category || '').toLowerCase();
    if (category === 'terrain') return applyTerrainAsset(env, assetId);
    if (category === 'props') return applyPropAsset(env, assetId);
    if (category === 'markers') return applyMarkerAsset(env, assetId);
    if (category === 'images') return applyImageAsset(env, assetId);
    if (category === 'vfx') {
      if (typeof env.setSelectedEditorVfxAsset === 'function' && typeof env.beginCustomVfxPlacement === 'function') {
        env.setSelectedEditorVfxAsset(normalizeAsset(asset));
        env.beginCustomVfxPlacement();
        return { ok: true, message: `${asset.name || 'VFX'} is armed. Click the map to place the effect.` };
      }
      return { ok: false, message: 'Custom VFX placement is unavailable in this build.' };
    }
    if (category === 'tokens') {
      if (typeof env.assignTokenAsset === 'function') return env.assignTokenAsset(normalizeAsset(asset)) || { ok: false, message: 'Token art assignment unavailable.' };
      return { ok: false, message: 'Token art assignment is unavailable in this build.' };
    }
    return { ok: false, message: 'This asset category is not wired for direct apply yet.' };
  }

  async function updateAsset(env = {}, assetId, payload = {}) {
    const fetchImpl = env.fetch || window.fetch?.bind(window);
    const formDataImpl = env.FormData || window.FormData;
    if (!fetchImpl || !formDataImpl) throw new Error('asset update unavailable');
    const form = new formDataImpl();
    form.append('asset_id', String(assetId || ''));
    form.append('name', String(payload.name || ''));
    form.append('category', String(payload.category || ''));
    form.append('subtype', String(payload.subtype || ''));
    form.append('style_pack', String(payload.stylePack || ''));
    form.append('tags', String(payload.tags || ''));
    form.append('tileable', payload.tileable === false ? 'false' : 'true');
    form.append('scale', String(payload.scale || 1));
    form.append('anchor', String(payload.anchor || 'center'));
    form.append('duration_ms', String(payload.durationMs || 8000));
    form.append('footprint', String(payload.footprint || 1));
    form.append('token_fit', String(payload.tokenFit || 'cover'));
    form.append('token_zoom', String(payload.tokenZoom || 1));
    form.append('token_offset_x', String(payload.tokenOffsetX || 0));
    form.append('token_offset_y', String(payload.tokenOffsetY || 0));
    const res = await fetchImpl('/api/assets/update', { method: 'POST', body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data?.ok) throw new Error(String(data?.error || `asset update ${res.status}`));
    state.loadingPromise = null;
    await loadManifest(env);
    return data.asset || null;
  }


  async function uploadAssetBatch(env = {}, payload = {}) {
    const fetchImpl = env.fetch || window.fetch?.bind(window);
    const formDataImpl = env.FormData || window.FormData;
    if (!fetchImpl || !formDataImpl) throw new Error('asset batch upload unavailable');
    const file = payload.file;
    if (!file) throw new Error('No zip selected');
    const form = new formDataImpl();
    form.append('file', file);
    form.append('category', String(payload.category || 'terrain'));
    form.append('subtype', String(payload.subtype || 'custom'));
    form.append('style_pack', String(payload.stylePack || 'custom_imports'));
    form.append('tags', String(payload.tags || ''));
    form.append('tileable', payload.tileable === false ? 'false' : 'true');
    form.append('scale', String(payload.scale || 1));
    form.append('anchor', String(payload.anchor || 'center'));
    form.append('duration_ms', String(payload.durationMs || 8000));
    form.append('footprint', String(payload.footprint || 1));
    const res = await fetchImpl('/api/assets/upload-batch', { method: 'POST', body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data?.ok) throw new Error(String(data?.error || `asset batch upload ${res.status}`));
    state.loadingPromise = null;
    await loadManifest(env);
    return data;
  }

  async function uploadAsset(env = {}, payload = {}) {
    const fetchImpl = env.fetch || window.fetch?.bind(window);
    const formDataImpl = env.FormData || window.FormData;
    if (!fetchImpl || !formDataImpl) throw new Error('asset upload unavailable');
    const file = payload.file;
    if (!file) throw new Error('No file selected');
    const form = new formDataImpl();
    form.append('file', file);
    form.append('category', String(payload.category || 'terrain'));
    form.append('subtype', String(payload.subtype || 'custom'));
    form.append('style_pack', String(payload.stylePack || 'custom_imports'));
    form.append('name', String(payload.name || file.name || 'Imported Asset'));
    form.append('tags', String(payload.tags || ''));
    form.append('tileable', payload.tileable === false ? 'false' : 'true');
    form.append('scale', String(payload.scale || 1));
    form.append('anchor', String(payload.anchor || 'center'));
    form.append('duration_ms', String(payload.durationMs || 8000));
    form.append('footprint', String(payload.footprint || 1));
    const res = await fetchImpl('/api/assets/upload', { method: 'POST', body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data?.ok) throw new Error(String(data?.error || `asset upload ${res.status}`));
    state.loadingPromise = null;
    await loadManifest(env);
    return data || null;
  }

  function subscribe(listener) {
    if (typeof listener !== 'function') return () => {};
    state.listeners.add(listener);
    return () => state.listeners.delete(listener);
  }

  window.AppEditorAssets = Object.freeze({
    loadManifest,
    getManifest,
    getEntries,
    getEntry,
    getPacks,
    getCategories,
    getPackShortcuts,
    getPopularTags,
    applyTerrainAsset,
    applyAsset,
    uploadAsset,
    uploadAssetBatch,
    updateAsset,
    subscribe,
  });
})();
