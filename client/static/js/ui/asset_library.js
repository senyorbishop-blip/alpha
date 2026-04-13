(function () {
  let unsubscribe = null;
  let lastEnv = null;
  let selectedAssetId = '';
  let uploadBusy = false;
  let localPreviewUrl = '';
  let uploadedOnlyActive = false;

  function el(doc, id) { return doc ? doc.getElementById(id) : null; }
  function currentCategory(env) { return String(el(env.document, 'editor-asset-category')?.value || 'terrain').toLowerCase() || 'terrain'; }

  function currentTag(env) { return String(el(env.document, 'editor-asset-tag-filter')?.value || '').trim().toLowerCase(); }
  function currentSort(env) { return String(el(env.document, 'editor-asset-sort')?.value || 'relevance').trim().toLowerCase(); }

  function currentShortcutId(env) {
    if (uploadedOnlyActive) return 'uploaded';
    const doc = env.document;
    const category = String(el(doc, 'editor-asset-category')?.value || '').toLowerCase();
    const stylePack = String(el(doc, 'editor-asset-pack')?.value || '').toLowerCase();
    const query = String(el(doc, 'editor-asset-search')?.value || '').trim().toLowerCase();
    const shortcuts = typeof env.getPackShortcuts === 'function' ? env.getPackShortcuts() : [];
    const match = shortcuts.find((shortcut) =>
      !shortcut.uploadedOnly
      && String(shortcut.category || '').toLowerCase() === category
      && String(shortcut.stylePack || '').toLowerCase() === stylePack
      && String(shortcut.query || '').trim().toLowerCase() === query
    );
    return match?.id || '';
  }

  function renderPackShortcuts(env) {
    const host = el(env.document, 'editor-asset-pack-shortcuts');
    if (!host) return;
    const shortcuts = typeof env.getPackShortcuts === 'function' ? env.getPackShortcuts() : [];
    const activeId = currentShortcutId(env);
    host.innerHTML = shortcuts.map((shortcut) => {
      const active = shortcut.id === activeId;
      return `<button class="tool-btn" data-pack-shortcut-id="${shortcut.id}" style="margin:0;padding:0.35rem 0.55rem;font-size:0.68rem;min-width:auto;${active ? 'border-color:rgba(255,215,0,0.5);box-shadow:0 0 0 1px rgba(255,215,0,0.16) inset;color:var(--gold);' : ''}">${shortcut.label}</button>`;
    }).join('');
  }

  function applyPackShortcut(env, shortcutId) {
    const shortcuts = typeof env.getPackShortcuts === 'function' ? env.getPackShortcuts() : [];
    const shortcut = shortcuts.find((entry) => entry.id === shortcutId);
    if (!shortcut) return;
    const doc = env.document;
    const category = el(doc, 'editor-asset-category');
    const pack = el(doc, 'editor-asset-pack');
    const search = el(doc, 'editor-asset-search');
    if (shortcut.uploadedOnly) {
      uploadedOnlyActive = true;
      // Clear other filters so they don't conflict
      if (category) category.value = '';
      if (pack) pack.value = '';
      if (search) search.value = '';
    } else {
      uploadedOnlyActive = false;
      if (category) category.value = shortcut.category || '';
      if (pack) pack.value = shortcut.stylePack || '';
      if (search) search.value = shortcut.query || '';
    }
    selectedAssetId = '';
    render(env);
    setImportStatus(env, `${shortcut.label} filter applied.`, 'success');
  }

  function labelForCategory(category) {
    const map = { terrain: 'Terrain', props: 'Props', markers: 'Markers', vfx: 'VFX', tokens: 'Token Art', images: 'Images' };
    return map[String(category || '').toLowerCase()] || 'Asset';
  }

  const FAVORITES_KEY = 'cg_asset_favorites_v1';
  const RECENT_KEY = 'cg_asset_recent_v1';
  function readIds(env, key) {
    try { const raw = env.localStorage?.getItem(key) || '[]'; const arr = JSON.parse(raw); return Array.isArray(arr) ? arr.map((v) => String(v || '')).filter(Boolean) : []; } catch (_) { return []; }
  }
  function writeIds(env, key, ids) {
    try { env.localStorage?.setItem(key, JSON.stringify(ids)); } catch (_) {}
  }
  function getFavorites(env) { return readIds(env, FAVORITES_KEY); }
  function getRecent(env) { return readIds(env, RECENT_KEY); }
  function isFavorite(env, assetId) { return getFavorites(env).includes(String(assetId || '')); }
  function toggleFavorite(env, assetId) {
    const id = String(assetId || ''); if (!id) return false;
    const favs = getFavorites(env);
    const next = favs.includes(id) ? favs.filter((v) => v !== id) : [id, ...favs].slice(0, 16);
    writeIds(env, FAVORITES_KEY, next);
    return next.includes(id);
  }
  function pushRecent(env, assetId) {
    const id = String(assetId || ''); if (!id) return;
    const next = [id, ...getRecent(env).filter((v) => v !== id)].slice(0, 18);
    writeIds(env, RECENT_KEY, next);
  }
  function quickCard(asset, kind) {
    const border = kind === 'favorite' ? 'rgba(207,161,74,0.42)' : 'rgba(176,190,207,0.20)';
    return `<button type="button" data-asset-id="${asset.id}" style="flex:0 0 60px;height:60px;border-radius:12px;border:1px solid ${border};background:#1a1d23 url('${asset.thumbnail || asset.file || ''}') center/cover no-repeat;position:relative;overflow:hidden;" title="${asset.name || asset.id}">${kind === 'favorite' ? '<span style="position:absolute;right:5px;top:4px;font-size:0.72rem;color:#ffd86b;text-shadow:0 1px 3px rgba(0,0,0,0.6);">★</span>' : ''}</button>`;
  }
  function renderQuickBar(env) {
    const doc = env.document;
    const favNode = el(doc, 'editor-asset-favorites');
    const recNode = el(doc, 'editor-asset-recent');
    const favWrap = el(doc, 'editor-asset-favorites-wrap');
    const recWrap = el(doc, 'editor-asset-recent-wrap');
    if (!favNode || !recNode) return;
    const favorites = getFavorites(env).map((id) => env.getEntry(id)).filter(Boolean);
    const recent = getRecent(env).map((id) => env.getEntry(id)).filter(Boolean).filter((asset) => !favorites.some((f) => f.id === asset.id));
    if (favWrap) favWrap.style.display = favorites.length ? '' : 'none';
    if (recWrap) recWrap.style.display = recent.length ? '' : 'none';
    favNode.innerHTML = favorites.map((asset) => quickCard(asset, 'favorite')).join('');
    recNode.innerHTML = recent.slice(0,8).map((asset) => quickCard(asset, 'recent')).join('');
  }

  function assetCardHtml(asset, isSelected, currentTerrainId) {
    const tags = Array.isArray(asset.tags) ? asset.tags.slice(0, 3).join(' · ') : '';
    const isActiveTerrain = String(asset.category || '').toLowerCase() === 'terrain' && Number(asset.terrain_id || 0) === Number(currentTerrainId || 0);
    const activeChip = isActiveTerrain ? '<span style="font-size:0.62rem;padding:0.1rem 0.35rem;border-radius:999px;background:rgba(207,161,74,0.18);color:var(--gold);border:1px solid rgba(207,161,74,0.34);">Active</span>' : '';
    return `
      <button type="button" class="tool-btn editor-asset-card${isSelected ? ' selected' : ''}" data-asset-id="${asset.id}" title="${(asset.name || asset.id || 'Asset').replace(/"/g, '&quot;')}" style="margin:0;text-align:left;padding:0.35rem;border-color:${isSelected ? 'rgba(207,161,74,0.72)' : 'rgba(176,190,207,0.20)'};background:${isSelected ? 'rgba(207,161,74,0.12)' : 'rgba(24,28,34,0.55)'};display:flex;flex-direction:column;gap:0.32rem;min-height:134px;overflow:hidden;transform:translateY(0);transition:transform 0.14s ease,border-color 0.14s ease,box-shadow 0.14s ease;">
        <div style="height:76px;border-radius:8px;background:#1a1d23 url('${asset.thumbnail || asset.file || ''}') center/cover no-repeat;border:1px solid rgba(255,255,255,0.08);"></div>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:0.35rem;">
          <div style="font-size:0.76rem;font-weight:700;line-height:1.2;color:var(--parchment);">${asset.name || asset.id}</div>
          ${activeChip}
        </div>
        <div style="font-size:0.62rem;color:var(--parchment-dim);line-height:1.25;">${tags || (asset.subtype || labelForCategory(asset.category))}</div>
      </button>`;
  }

  function setImportStatus(env, message, kind = 'info') {
    const node = el(env.document, 'editor-asset-import-status');
    if (!node) return;
    node.textContent = message || '';
    node.style.color = kind === 'error' ? '#f2a6a6' : kind === 'success' ? '#9fe3b2' : 'var(--parchment-dim)';
  }


  function setDropActive(env, on) {
    const node = el(env.document, 'editor-asset-library-section');
    if (!node) return;
    node.style.outline = on ? '2px dashed rgba(207,161,74,0.78)' : '';
    node.style.outlineOffset = on ? '4px' : '';
    node.style.boxShadow = on ? '0 0 0 1px rgba(207,161,74,0.18), 0 0 22px rgba(207,161,74,0.12)' : '';
  }

  function updateApplyButton(env, asset) {
    const btn = el(env.document, 'editor-asset-apply');
    if (!btn) return;
    const category = String(asset?.category || currentCategory(env) || 'terrain').toLowerCase();
    const labels = {
      terrain: '✨ Apply Selected Terrain',
      props: '🪑 Use Selected Prop',
      markers: '📍 Use Selected Marker',
      vfx: '⚡ Place Selected VFX',
      tokens: '🧿 Assign Selected Token Art',
      images: '🖼️ Place Selected Image',
    };
    btn.innerHTML = `<span class="icon"></span> ${labels[category] || 'Apply Selected Asset'}`;
  }

  function renderPreview(env, asset) {
    const doc = env.document;
    const img = el(doc, 'editor-asset-preview-img');
    const name = el(doc, 'editor-asset-preview-name');
    const meta = el(doc, 'editor-asset-preview-meta');
    if (!img || !name || !meta) return;
    const favBtn = el(doc, 'editor-asset-favorite');
    if (!asset) {
      img.style.backgroundImage = localPreviewUrl ? `url('${localPreviewUrl}')` : 'none';
      img.style.backgroundSize = localPreviewUrl ? 'contain' : 'cover';
      name.textContent = localPreviewUrl ? (el(doc, 'editor-asset-import-name')?.value || 'Import Preview') : `Select a ${labelForCategory(currentCategory(env)).toLowerCase()} asset`;
      meta.textContent = localPreviewUrl ? 'Previewing your import before it is added to the manifest.' : 'Preview, tags, and pack info will show here.';
      if (favBtn) { favBtn.textContent = '☆'; favBtn.disabled = true; favBtn.style.opacity = '0.45'; }
      updateApplyButton(env, null);
      return;
    }
    img.style.backgroundImage = `url('${asset.thumbnail || asset.file || ''}')`;
    img.style.backgroundSize = 'cover';
    name.textContent = asset.name || asset.id || 'Asset';
    const bits = [labelForCategory(asset.category), asset.style_pack, asset.subtype, asset.tileable ? 'tileable' : 'single', asset.scale ? `x${Number(asset.scale).toFixed(2).replace(/\.00$/,'')}` : '', asset.anchor || '', String(asset.category||'').toLowerCase()==='vfx' && Number(asset.duration_ms||0) > 0 ? `${Math.round(Number(asset.duration_ms)/1000)}s` : '', ...(asset.tags || []).slice(0, 3)].filter(Boolean);
    meta.textContent = bits.join(' · ');
    if (favBtn) { favBtn.disabled = false; favBtn.style.opacity = '1'; favBtn.textContent = isFavorite(env, asset.id) ? '★' : '☆'; }
    updateApplyButton(env, asset);
  }


  function ensureHoverPreview(env) {
    const doc = env.document;
    let node = el(doc, 'editor-asset-hover-preview');
    if (!node) {
      node = doc.createElement('div');
      node.id = 'editor-asset-hover-preview';
      node.setAttribute('aria-hidden', 'true');
      node.style.cssText = 'display:none;position:fixed;z-index:10040;pointer-events:none;width:min(260px, calc(100vw - 24px));padding:0.6rem;border-radius:14px;border:1px solid rgba(207,161,74,0.32);background:linear-gradient(180deg, rgba(8,14,20,0.98), rgba(10,16,24,0.96));box-shadow:0 24px 48px rgba(0,0,0,0.46);backdrop-filter:blur(6px);';
      node.innerHTML = '<div id="editor-asset-hover-preview-img" style="width:100%;height:166px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);background:#14181f center/contain no-repeat;"></div><div id="editor-asset-hover-preview-name" style="margin-top:0.5rem;font-size:0.82rem;font-weight:700;color:var(--parchment);line-height:1.25;"></div><div id="editor-asset-hover-preview-meta" style="margin-top:0.2rem;font-size:0.64rem;color:var(--parchment-dim);line-height:1.35;"></div>';
      doc.body.appendChild(node);
    }
    return node;
  }

  function hideHoverPreview(env) {
    const node = el(env?.document, 'editor-asset-hover-preview');
    if (!node) return;
    node.style.display = 'none';
    node.setAttribute('aria-hidden', 'true');
  }

  function showHoverPreview(env, asset, pointerEvent) {
    if (!asset) return;
    const doc = env.document;
    const node = ensureHoverPreview(env);
    if (!node) return;
    const img = el(doc, 'editor-asset-hover-preview-img');
    const name = el(doc, 'editor-asset-hover-preview-name');
    const meta = el(doc, 'editor-asset-hover-preview-meta');
    if (img) img.style.backgroundImage = `url('${asset.thumbnail || asset.file || ''}')`;
    if (name) name.textContent = asset.name || asset.id || 'Asset';
    if (meta) {
      const bits = [labelForCategory(asset.category), asset.style_pack, asset.subtype, Array.isArray(asset.tags) ? asset.tags.slice(0, 3).join(' · ') : ''].filter(Boolean);
      meta.textContent = bits.join(' · ');
    }
    node.style.display = 'block';
    node.setAttribute('aria-hidden', 'false');
    syncHoverPreviewPosition(env, pointerEvent);
  }

  function syncHoverPreviewPosition(env, pointerEvent) {
    const node = el(env?.document, 'editor-asset-hover-preview');
    if (!node || node.style.display === 'none') return;
    const viewportW = env?.window?.innerWidth || window.innerWidth || 1280;
    const viewportH = env?.window?.innerHeight || window.innerHeight || 720;
    const margin = 12;
    const x = Math.max(margin, Math.min((pointerEvent?.clientX || margin) + 18, viewportW - node.offsetWidth - margin));
    const y = Math.max(margin, Math.min((pointerEvent?.clientY || margin) + 18, viewportH - node.offsetHeight - margin));
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
  }


  function syncInspectorControls(env, asset) {
    const doc = env.document;
    const wrap = el(doc, 'editor-asset-inspector');
    if (!wrap) return;
    wrap.style.display = asset ? 'block' : 'none';
    const setVal = (id, val) => { const node = el(doc, id); if (node) node.value = val == null ? '' : String(val); };
    const setChecked = (id, val) => { const node = el(doc, id); if (node) node.checked = !!val; };
    if (!asset) return;
    
    // Populate category dropdown
    const categorySelect = el(doc, 'editor-asset-inspector-category');
    if (categorySelect) {
      const categories = env.getCategories();
      categorySelect.innerHTML = categories.map((cat) => `<option value="${cat.id}">${cat.name}</option>`).join('');
      categorySelect.value = asset.category || 'terrain';
    }
    
    setVal('editor-asset-inspector-name', asset.name || '');
    setVal('editor-asset-inspector-subtype', asset.subtype || 'custom');
    setVal('editor-asset-inspector-pack', asset.style_pack || 'custom_imports');
    setVal('editor-asset-inspector-tags', Array.isArray(asset.tags) ? asset.tags.join(', ') : '');
    setChecked('editor-asset-inspector-tileable', !!asset.tileable);
    setVal('editor-asset-inspector-scale', asset.scale || 1);
    setVal('editor-asset-inspector-anchor', asset.anchor || 'center');
    setVal('editor-asset-inspector-duration', asset.duration_ms || 8000);
    setVal('editor-asset-inspector-footprint', asset.footprint || 1);
    setVal('editor-asset-inspector-token-fit', asset.token_fit || 'cover');
    setVal('editor-asset-inspector-token-zoom', asset.token_zoom || 1);
    setVal('editor-asset-inspector-token-offset-x', asset.token_offset_x || 0);
    setVal('editor-asset-inspector-token-offset-y', asset.token_offset_y || 0);
    const tokenWrap = el(doc, 'editor-asset-inspector-token-wrap');
    if (tokenWrap) tokenWrap.style.display = String(asset.category || '').toLowerCase() === 'tokens' ? 'grid' : 'none';
    const vfxWrap = el(doc, 'editor-asset-inspector-vfx-wrap');
    if (vfxWrap) vfxWrap.style.display = String(asset.category || '').toLowerCase() === 'vfx' ? 'grid' : 'none';
  }

  function syncRotationDisplay(env) {
    const doc = env.document;
    const valNode = el(doc, 'editor-asset-rotation-val');
    const propValNode = el(doc, 'editor-prop-rotation-val');
    if (valNode && propValNode) valNode.textContent = propValNode.textContent || '0°';
  }

  function getInspectorPayload(env, asset) {
    const doc = env.document;
    return {
      name: el(doc, 'editor-asset-inspector-name')?.value || asset?.name || '',
      category: el(doc, 'editor-asset-inspector-category')?.value || asset?.category || 'terrain',
      subtype: el(doc, 'editor-asset-inspector-subtype')?.value || asset?.subtype || 'custom',
      stylePack: el(doc, 'editor-asset-inspector-pack')?.value || asset?.style_pack || 'custom_imports',
      tags: el(doc, 'editor-asset-inspector-tags')?.value || '',
      tileable: !!el(doc, 'editor-asset-inspector-tileable')?.checked,
      scale: Number(el(doc, 'editor-asset-inspector-scale')?.value || asset?.scale || 1) || 1,
      anchor: el(doc, 'editor-asset-inspector-anchor')?.value || asset?.anchor || 'center',
      durationMs: Number(el(doc, 'editor-asset-inspector-duration')?.value || asset?.duration_ms || 8000) || 8000,
      footprint: Number(el(doc, 'editor-asset-inspector-footprint')?.value || asset?.footprint || 1) || 1,
      tokenFit: el(doc, 'editor-asset-inspector-token-fit')?.value || asset?.token_fit || 'cover',
      tokenZoom: Number(el(doc, 'editor-asset-inspector-token-zoom')?.value || asset?.token_zoom || 1) || 1,
      tokenOffsetX: Number(el(doc, 'editor-asset-inspector-token-offset-x')?.value || asset?.token_offset_x || 0) || 0,
      tokenOffsetY: Number(el(doc, 'editor-asset-inspector-token-offset-y')?.value || asset?.token_offset_y || 0) || 0,
    };
  }

  async function saveInspector(env) {
    const asset = env.getEntry(selectedAssetId);
    if (!asset) return;
    setImportStatus(env, `Saving ${asset.name || 'asset'} defaults...`);
    try {
      const updated = await env.updateAsset(selectedAssetId, getInspectorPayload(env, asset));
      if (updated?.id) selectedAssetId = updated.id;
      setImportStatus(env, `${updated?.name || asset.name || 'Asset'} defaults saved.`, 'success');
      render(env);
    } catch (err) {
      setImportStatus(env, err?.message || 'Asset save failed.', 'error');
    }
  }

  function renderTagChips(env) {
    const host = el(env.document, 'editor-asset-tag-chips');
    if (!host) return;
    const activeTag = currentTag(env);
    const tags = typeof env.getPopularTags === 'function' ? env.getPopularTags({
      category: String(el(env.document, 'editor-asset-category')?.value || '').toLowerCase(),
      stylePack: String(el(env.document, 'editor-asset-pack')?.value || ''),
      query: String(el(env.document, 'editor-asset-search')?.value || ''),
    }) : [];
    if (!tags.length) {
      host.innerHTML = '<div style="font-size:0.66rem;color:var(--parchment-dim);">No matching tags yet.</div>';
      return;
    }
    host.innerHTML = tags.map(({ tag, count }) => {
      const active = tag === activeTag;
      return `<button type="button" class="tool-btn" data-tag-chip="${tag}" style="margin:0;padding:0.28rem 0.5rem;font-size:0.66rem;min-width:auto;${active ? 'border-color:rgba(207,161,74,0.72);color:var(--gold);background:rgba(207,161,74,0.12);' : ''}">${tag} <span style="opacity:0.7">${count}</span></button>`;
    }).join('');
  }

  function renderResultSummary(env, count) {
    const node = el(env.document, 'editor-asset-results-summary');
    if (!node) return;
    const category = String(el(env.document, 'editor-asset-category')?.selectedOptions?.[0]?.textContent || 'All Categories');
    const pack = String(el(env.document, 'editor-asset-pack')?.selectedOptions?.[0]?.textContent || 'All Packs');
    const tag = currentTag(env);
    const query = String(el(env.document, 'editor-asset-search')?.value || '').trim();
    const bits = [`${count} result${count === 1 ? '' : 's'}`, category, pack];
    if (tag) bits.push(`#${tag}`);
    if (query) bits.push(`“${query}”`);
    node.textContent = bits.join(' · ');
  }

  function render(env) {
    lastEnv = env;
    const doc = env.document;
    const grid = el(doc, 'editor-asset-grid');
    const search = el(doc, 'editor-asset-search');
    const pack = el(doc, 'editor-asset-pack');
    if (!grid) return;
    const category = String(el(doc, 'editor-asset-category')?.value || '').toLowerCase();
    const query = search?.value || '';
    const stylePack = pack?.value || '';
    const tag = currentTag(env);
    const sort = currentSort(env);
    const entries = env.getEntries({ category, query, stylePack, tag, sort, uploadedOnly: uploadedOnlyActive });
    const currentTerrainId = env.getSelectedTerrainId();
    if (!selectedAssetId && entries.length) {
      const active = category === 'terrain' ? entries.find((entry) => Number(entry.terrain_id || 0) === Number(currentTerrainId || 0)) : null;
      selectedAssetId = active?.id || entries[0].id;
    }
    if (selectedAssetId && !entries.some((entry) => entry.id === selectedAssetId)) selectedAssetId = entries[0]?.id || '';
    const emptyLabel = uploadedOnlyActive ? 'uploaded' : labelForCategory(category || 'asset').toLowerCase();
    const emptyHint = uploadedOnlyActive
      ? 'Import images using the Import section below, or drag an image file onto this panel.'
      : 'Try clearing the tag filter, changing pack, or using a broader search word.';
    grid.innerHTML = entries.length ? entries.map((asset) => assetCardHtml(asset, asset.id === selectedAssetId, currentTerrainId)).join('') : `<div style="grid-column:1/-1;font-size:0.72rem;color:var(--parchment-dim);padding:0.55rem 0;display:flex;flex-direction:column;gap:0.28rem;"><div>No ${emptyLabel} assets match this filter yet.</div><div style="font-size:0.66rem;opacity:0.78;">${emptyHint}</div></div>`;
    const activeAsset = env.getEntry(selectedAssetId) || entries[0] || null;
    hideHoverPreview(env);
    renderPreview(env, activeAsset);
    renderPackShortcuts(env);
    renderQuickBar(env);
    renderTagChips(env);
    renderResultSummary(env, entries.length);
    syncInspectorControls(env, activeAsset);
    syncRotationDisplay(env);
  }

  function populatePacks(env) {
    const select = el(env.document, 'editor-asset-pack');
    const importPack = el(env.document, 'editor-asset-import-pack');
    const packs = env.getPacks();
    if (select) {
      const current = select.value;
      select.innerHTML = '<option value="">All Packs</option>' + packs.map((pack) => `<option value="${pack.id}">${pack.name}</option>`).join('');
      select.value = current && packs.some((pack) => pack.id === current) ? current : '';
    }
    if (importPack) {
      const currentImport = importPack.value;
      importPack.innerHTML = packs.map((pack) => `<option value="${pack.id}">${pack.name}</option>`).join('');
      importPack.value = currentImport && packs.some((pack) => pack.id === currentImport) ? currentImport : 'custom_imports';
    }
  }

  function populateCategories(env) {
    const select = el(env.document, 'editor-asset-category');
    const importCategory = el(env.document, 'editor-asset-import-category');
    const categories = env.getCategories();
    if (select) {
      const current = select.value || 'terrain';
      select.innerHTML = '<option value=>All Categories</option>' + categories.map((cat) => `<option value="${cat.id}">${cat.name}</option>`).join('');
      select.value = (current === '' || categories.some((cat) => cat.id === current)) ? current : 'terrain';
    }
    if (importCategory) {
      const currentImport = importCategory.value || 'terrain';
      importCategory.innerHTML = categories.map((cat) => `<option value="${cat.id}">${cat.name}</option>`).join('');
      importCategory.value = categories.some((cat) => cat.id === currentImport) ? currentImport : 'terrain';
    }
  }

  function syncImportControls(env) {
    const doc = env.document;
    const category = String(el(doc, 'editor-asset-import-category')?.value || 'terrain').toLowerCase();
    const subtype = el(doc, 'editor-asset-import-subtype');
    const tileableWrap = el(doc, 'editor-asset-import-tileable-wrap');
    const durationWrap = el(doc, 'editor-asset-import-duration-wrap');
    const footprintWrap = el(doc, 'editor-asset-import-footprint-wrap');
    const label = el(doc, 'editor-asset-import-upload');
    if (subtype) {
      const defaults = { terrain: 'custom', props: 'scatter', markers: 'landmark', vfx: 'impact', tokens: 'portrait' };
      if (!subtype.value || subtype.value === 'custom') subtype.value = defaults[category] || 'custom';
    }
    if (tileableWrap) tileableWrap.style.display = category === 'terrain' ? 'inline-flex' : 'none';
    if (durationWrap) durationWrap.style.display = category === 'vfx' ? 'inline-flex' : 'none';
    if (footprintWrap) footprintWrap.style.display = ['props','markers','vfx'].includes(category) ? 'inline-flex' : 'none';
    if (label) label.innerHTML = `<span class="icon">🪄</span> Import ${labelForCategory(category)}`;
  }

  function stageImportFile(env, file) {
    const doc = env.document;
    if (!file) return false;
    const ok = /\.(png|jpe?g|webp|gif|svg)$/i.test(String(file.name || '')) || /^image\//i.test(String(file.type || ''));
    if (!ok) {
      setImportStatus(env, 'Drop a PNG, JPG, WEBP, SVG, or GIF image.', 'error');
      return false;
    }
    const importInput = el(doc, 'editor-asset-import-file');
    const importName = el(doc, 'editor-asset-import-name');
    if (localPreviewUrl) { try { URL.revokeObjectURL(localPreviewUrl); } catch (_) {} localPreviewUrl = ''; }
    localPreviewUrl = URL.createObjectURL(file);
    if (importName && !importName.value.trim()) importName.value = String(file.name || '').replace(/\.[^.]+$/, '');
    if (importInput && window.DataTransfer) {
      try {
        const dt = new DataTransfer();
        dt.items.add(file);
        importInput.files = dt.files;
      } catch (_) {}
    }
    const previewImg = el(doc, 'editor-asset-import-preview');
    const previewWrap = el(doc, 'editor-asset-import-preview-wrap');
    if (previewImg) previewImg.src = localPreviewUrl;
    if (previewWrap) previewWrap.style.display = '';
    renderPreview(env, null);
    setImportStatus(env, `Staged ${file.name} for import. Review metadata, then click Import.`, 'success');
    return true;
  }

  function wireImportPreview(env) {
    const doc = env.document;
    const importInput = el(doc, 'editor-asset-import-file');
    const importName = el(doc, 'editor-asset-import-name');
    const refreshPreview = () => renderPreview(env, env.getEntry(selectedAssetId) || null);
    importInput?.addEventListener('change', () => {
      const file = importInput.files && importInput.files[0];
      if (file) stageImportFile(env, file);
      else refreshPreview();
    });
    importName?.addEventListener('input', refreshPreview);
    el(doc, 'editor-asset-import-category')?.addEventListener('change', () => { syncImportControls(env); refreshPreview(); });

    const dropZone = el(doc, 'editor-asset-library-section');
    if (dropZone) {
      const stop = (event) => { event.preventDefault(); event.stopPropagation(); };
      ['dragenter', 'dragover'].forEach((type) => dropZone.addEventListener(type, (event) => { stop(event); setDropActive(env, true); }));
      ['dragleave', 'dragend'].forEach((type) => dropZone.addEventListener(type, (event) => { stop(event); if (event.target === dropZone || !dropZone.contains(event.relatedTarget)) setDropActive(env, false); }));
      dropZone.addEventListener('drop', (event) => {
        stop(event);
        setDropActive(env, false);
        const file = event.dataTransfer?.files && event.dataTransfer.files[0];
        if (file) stageImportFile(env, file);
      });
    }
  }

  function getBatchImportPayload(env) {
    const doc = env.document;
    const input = el(doc, 'editor-asset-import-zip');
    const file = input?.files && input.files[0];
    if (!file) throw new Error('Choose a zip first');
    return {
      file,
      category: String(el(doc, 'editor-asset-import-category')?.value || 'terrain').toLowerCase(),
      subtype: el(doc, 'editor-asset-import-subtype')?.value || 'custom',
      stylePack: el(doc, 'editor-asset-import-pack')?.value || 'custom_imports',
      tags: el(doc, 'editor-asset-import-tags')?.value || 'imported,custom',
      tileable: !!el(doc, 'editor-asset-import-tileable')?.checked,
      scale: Number(el(doc, 'editor-asset-import-scale')?.value || 1) || 1,
      anchor: el(doc, 'editor-asset-import-anchor')?.value || 'center',
      durationMs: Number(el(doc, 'editor-asset-import-duration')?.value || 8000) || 8000,
      footprint: Number(el(doc, 'editor-asset-import-footprint')?.value || 1) || 1,
    };
  }

  function getImportPayload(env) {
    const doc = env.document;
    const importInput = el(doc, 'editor-asset-import-file');
    const file = importInput?.files && importInput.files[0];
    if (!file) throw new Error('Choose an image first');
    const category = String(el(doc, 'editor-asset-import-category')?.value || 'terrain').toLowerCase();
    return {
      file,
      category,
      subtype: el(doc, 'editor-asset-import-subtype')?.value || 'custom',
      stylePack: el(doc, 'editor-asset-import-pack')?.value || 'custom_imports',
      name: el(doc, 'editor-asset-import-name')?.value || String(file.name || '').replace(/\.[^.]+$/, ''),
      tags: el(doc, 'editor-asset-import-tags')?.value || 'imported,custom',
      tileable: !!el(doc, 'editor-asset-import-tileable')?.checked,
      scale: Number(el(doc, 'editor-asset-import-scale')?.value || 1) || 1,
      anchor: el(doc, 'editor-asset-import-anchor')?.value || 'center',
      durationMs: Number(el(doc, 'editor-asset-import-duration')?.value || 8000) || 8000,
      footprint: Number(el(doc, 'editor-asset-import-footprint')?.value || 1) || 1,
    };
  }

  function clearImportForm(env, keepStatus) {
    const doc = env.document;
    ['editor-asset-import-name', 'editor-asset-import-tags'].forEach((id) => { const node = el(doc, id); if (node) node.value = ''; });
    const scale = el(doc, 'editor-asset-import-scale'); if (scale) scale.value = '1';
    const duration = el(doc, 'editor-asset-import-duration'); if (duration) duration.value = '8000';
    const footprint = el(doc, 'editor-asset-import-footprint'); if (footprint) footprint.value = '1';
    const anchor = el(doc, 'editor-asset-import-anchor'); if (anchor) anchor.value = 'center';
    const subtype = el(doc, 'editor-asset-import-subtype');
    if (subtype) subtype.value = 'custom';
    const pack = el(doc, 'editor-asset-import-pack');
    if (pack) pack.value = 'custom_imports';
    const category = el(doc, 'editor-asset-import-category');
    if (category) category.value = currentCategory(env);
    const tileable = el(doc, 'editor-asset-import-tileable');
    if (tileable) tileable.checked = true;
    const input = el(doc, 'editor-asset-import-file');
    if (input) input.value = '';
    const zipInput = el(doc, 'editor-asset-import-zip');
    if (zipInput) zipInput.value = '';

    if (localPreviewUrl) { try { URL.revokeObjectURL(localPreviewUrl); } catch (_) {} localPreviewUrl = ''; }
    const previewImg = el(doc, 'editor-asset-import-preview');
    const previewWrap = el(doc, 'editor-asset-import-preview-wrap');
    if (previewImg) previewImg.src = '';
    if (previewWrap) previewWrap.style.display = 'none';
    syncImportControls(env);
    if (!keepStatus) setImportStatus(env, 'Import terrain, props, markers, VFX, or token art with pack metadata — or drag an image into this panel.');
  }

  function switchToUploadedView(env) {
    const doc = env.document;
    uploadedOnlyActive = true;
    const catSelect = el(doc, 'editor-asset-category');
    if (catSelect) catSelect.value = '';
    const packSelect = el(doc, 'editor-asset-pack');
    if (packSelect) packSelect.value = '';
    const searchInput = el(doc, 'editor-asset-search');
    if (searchInput) searchInput.value = '';
  }

  async function init(env) {
    if (!env || !env.document) return false;
    const doc = env.document;
    const grid = el(doc, 'editor-asset-grid');
    if (!grid) return false;
    populateCategories(env);
    populatePacks(env);
    syncImportControls(env);
    if (!el(doc, 'editor-asset-results-summary')) {
      const toolbar = el(doc, 'editor-asset-pack-shortcuts');
      toolbar?.insertAdjacentHTML('afterend', `<div id="editor-asset-results-summary" style="font-size:0.66rem;color:var(--parchment-dim);margin-top:0.4rem;"></div><div style="display:flex;gap:0.45rem;align-items:center;flex-wrap:wrap;margin-top:0.45rem;"><label class="small-label" style="margin:0;display:flex;align-items:center;gap:0.35rem;">Sort <select id="editor-asset-sort" class="small-input" style="min-width:150px;"><option value="relevance">Best Match</option><option value="name_asc">Name A-Z</option><option value="name_desc">Name Z-A</option><option value="pack">Pack</option><option value="category">Category</option></select></label><input id="editor-asset-tag-filter" class="small-input" placeholder="Filter by tag" style="max-width:160px;" /><button type="button" id="editor-asset-tag-clear" class="tool-btn" style="margin:0;padding:0.3rem 0.55rem;min-width:auto;">Clear Tag</button></div><div id="editor-asset-tag-chips" style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.45rem;"></div>`);
    }
    if (unsubscribe) unsubscribe();
    unsubscribe = env.subscribeManifest(() => { populateCategories(env); populatePacks(env); render(env); });
    const handleAssetPick = (event) => {
      const card = event.target.closest('[data-asset-id]');
      if (!card) return;
      selectedAssetId = card.getAttribute('data-asset-id') || '';
      render(env);
    };
    grid.addEventListener('click', handleAssetPick);
    const handleHoverPick = (event) => {
      const card = event.target.closest('[data-asset-id]');
      if (!card) return;
      const assetId = card.getAttribute('data-asset-id') || '';
      const asset = env.getEntry(assetId);
      if (!asset) return;
      card.style.transform = 'translateY(-4px) scale(1.06)';
      card.style.boxShadow = '0 18px 34px rgba(0,0,0,0.34)';
      card.style.zIndex = '3';
      showHoverPreview(env, asset, event);
      renderPreview(env, asset);
    };
    const clearHoverPick = (event) => {
      const card = event.target.closest('[data-asset-id]');
      if (card) {
        card.style.transform = '';
        card.style.boxShadow = '';
        card.style.zIndex = '';
      }
      hideHoverPreview(env);
      renderPreview(env, env.getEntry(selectedAssetId) || null);
    };
    grid.addEventListener('mouseover', handleHoverPick);
    grid.addEventListener('mousemove', (event) => syncHoverPreviewPosition(env, event));
    grid.addEventListener('mouseout', (event) => {
      const leaving = event.target.closest('[data-asset-id]');
      if (!leaving) return;
      if (event.relatedTarget && leaving.contains(event.relatedTarget)) return;
      clearHoverPick(event);
    });
    grid.addEventListener('mouseleave', () => { hideHoverPreview(env); renderPreview(env, env.getEntry(selectedAssetId) || null); });
    el(doc, 'editor-asset-favorites')?.addEventListener('click', handleAssetPick);
    el(doc, 'editor-asset-recent')?.addEventListener('click', handleAssetPick);
    el(doc, 'editor-asset-pack-shortcuts')?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-pack-shortcut-id]');
      if (!button) return;
      applyPackShortcut(env, button.getAttribute('data-pack-shortcut-id') || '');
    });
    el(doc, 'editor-asset-search')?.addEventListener('input', () => { uploadedOnlyActive = false; render(env); });
    el(doc, 'editor-asset-pack')?.addEventListener('change', () => { uploadedOnlyActive = false; render(env); });
    el(doc, 'editor-asset-sort')?.addEventListener('change', () => render(env));
    el(doc, 'editor-asset-tag-filter')?.addEventListener('input', () => render(env));
    el(doc, 'editor-asset-tag-clear')?.addEventListener('click', () => { const n = el(doc, 'editor-asset-tag-filter'); if (n) n.value = ''; render(env); });
    el(doc, 'editor-asset-tag-chips')?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-tag-chip]');
      if (!button) return;
      const tagInput = el(doc, 'editor-asset-tag-filter');
      if (tagInput) tagInput.value = button.getAttribute('data-tag-chip') || '';
      render(env);
    });
    el(doc, 'editor-asset-category')?.addEventListener('change', () => { uploadedOnlyActive = false; selectedAssetId = ''; clearImportForm(env, true); const t = el(doc, 'editor-asset-tag-filter'); if (t) t.value = ''; render(env); });
    el(doc, 'editor-asset-apply')?.addEventListener('click', () => {
      if (!selectedAssetId) return;
      const result = env.applyAsset(selectedAssetId) || {};
      if (result.ok) pushRecent(env, selectedAssetId);
      setImportStatus(env, result.message || (result.ok ? 'Applied.' : 'This asset is not wired for apply yet.'), result.ok ? 'success' : 'info');
      render(env);
    });
    el(doc, 'editor-asset-favorite')?.addEventListener('click', () => {
      if (!selectedAssetId) return;
      const on = toggleFavorite(env, selectedAssetId);
      setImportStatus(env, on ? 'Added to favorites.' : 'Removed from favorites.', 'success');
      render(env);
    });
    el(doc, 'editor-asset-rotate-left')?.addEventListener('click', () => {
      if (typeof env.rotateEditorProp === 'function') { env.rotateEditorProp(-90); syncRotationDisplay(env); }
    });
    el(doc, 'editor-asset-rotate-right')?.addEventListener('click', () => {
      if (typeof env.rotateEditorProp === 'function') { env.rotateEditorProp(90); syncRotationDisplay(env); }
    });
    const importBrowse = el(doc, 'editor-asset-import-browse');
    const importInput = el(doc, 'editor-asset-import-file');
    const batchBrowse = el(doc, 'editor-asset-import-zip-browse');
    const batchInput = el(doc, 'editor-asset-import-zip');
    importBrowse?.addEventListener('click', () => importInput?.click());
    batchBrowse?.addEventListener('click', () => batchInput?.click());
    batchInput?.addEventListener('change', () => {
      const file = batchInput.files && batchInput.files[0];
      const zipNameEl = el(doc, 'editor-asset-import-zip-name');
      if (!file) {
        if (zipNameEl) zipNameEl.textContent = '';
        return;
      }
      if (!/\.zip$/i.test(String(file.name || ''))) {
        setImportStatus(env, 'Choose a .zip file for batch import.', 'error');
        batchInput.value = '';
        if (zipNameEl) zipNameEl.textContent = '';
        return;
      }
      if (zipNameEl) zipNameEl.textContent = file.name;
      setImportStatus(env, `Staged ${file.name} for batch import. Click Batch Import Zip to add supported images.`, 'success');
    });
    wireImportPreview(env);
    el(doc, 'editor-asset-inspector-save')?.addEventListener('click', () => { saveInspector(env); });
    el(doc, 'editor-asset-import-upload-batch')?.addEventListener('click', async () => {
      if (uploadBusy) return;
      uploadBusy = true;
      setImportStatus(env, 'Importing zip and generating thumbnails...');
      try {
        const result = await env.uploadAssetBatch(getBatchImportPayload(env));
        const first = Array.isArray(result?.assets) ? result.assets[0] : null;
        selectedAssetId = first?.id || selectedAssetId;
        (result?.assets || []).forEach((asset) => asset?.id && pushRecent(env, asset.id));
        const skippedCount = Array.isArray(result?.skipped) ? result.skipped.length : 0;
        const duplicateCount = Array.isArray(result?.duplicates) ? result.duplicates.length : 0;
        const importedCount = result?.count || (result?.assets || []).length || 0;
        if (importedCount > 0) switchToUploadedView(env);
        setImportStatus(env, `Imported ${importedCount} assets${duplicateCount ? `, skipped ${duplicateCount} duplicates` : ''}${skippedCount ? `, skipped ${skippedCount} non-images` : ''}.`, duplicateCount ? 'info' : 'success');
        clearImportForm(env, true);
        render(env);
      } catch (err) {
        setImportStatus(env, err?.message || 'Batch import failed.', 'error');
      } finally { uploadBusy = false; }
    });
    el(doc, 'editor-asset-import-upload')?.addEventListener('click', async () => {
      if (uploadBusy) return;
      uploadBusy = true;
      setImportStatus(env, 'Importing asset and generating thumbnail...');
      try {
        const result = await env.uploadAsset(getImportPayload(env));
        const asset = result?.asset || null;
        selectedAssetId = asset?.id || selectedAssetId;
        if (asset?.id) pushRecent(env, asset.id);
        if (asset?.id) switchToUploadedView(env);
        const skippedDuplicate = !!result?.skipped || !!result?.duplicate;
        setImportStatus(env, asset ? (skippedDuplicate ? `Skipped duplicate ${asset.name || 'asset'}.` : `Imported ${asset.name}`) : 'Asset import complete.', skippedDuplicate ? 'info' : 'success');
        clearImportForm(env, true);
        render(env);
      } catch (err) {
        setImportStatus(env, err?.message || 'Import failed.', 'error');
      } finally { uploadBusy = false; }
    });
    await env.loadAssets();
    setImportStatus(env, 'Use theme shortcuts for fast browsing, import a single image with metadata, or batch import a zip of images.');
    render(env);
    return true;
  }

  function refresh(env) { render(env || lastEnv); }
  window.AppUIAssetLibrary = Object.freeze({ init, refresh });
})();
