(function(){
  function normalizeWorldMapLayer(env, raw) {
    if (!raw || typeof raw !== 'object') return null;
    const url = String(raw.url || '').trim();
    if (!url) return null;
    return {
      id: String(raw.id || Math.random().toString(36).slice(2)),
      url,
      x: Number(raw.x || 0),
      y: Number(raw.y || 0),
      width: Math.max(1, Number(raw.width || 0) || 0),
      height: Math.max(1, Number(raw.height || 0) || 0),
      locked: raw.locked !== false,
      name: String(raw.name || 'World Map').slice(0, 160),
    };
  }
  function ensureWorldMapLayerImage(env, layer) {
    if (!layer || !layer.url) return null;
    const cache = env.getWorldMapLayerImages();
    const existing = cache[layer.url];
    if (existing) return existing;
    const img = new env.Image();
    img.onload = () => env.drawFrame();
    img.onerror = () => { env.console.warn('World map layer failed to load:', layer.url); };
    img.src = layer.url + '?t=' + env.Date.now();
    cache[layer.url] = img;
    return img;
  }
  function setWorldMapLayers(env, layers) {
    const normalized = Array.isArray(layers) ? layers.map((v) => normalizeWorldMapLayer(env, v)).filter(Boolean) : [];
    env.setWorldMapLayersState(normalized);
    normalized.forEach((layer) => ensureWorldMapLayerImage(env, layer));
    const latest = normalized.length ? normalized[normalized.length - 1] : null;
    if (latest && latest.url) env.setWorldMapImageUrl(latest.url);
    updateMapPreviewUI(env, latest ? latest.url : null);
    env.drawFrame();
  }
  function drawWorldMapLayers(env) {
    if (env.getEditorMapContextKey() !== 'world') return;
    const layers = env.getWorldMapLayers();
    if (!layers.length) return;
    const ctx = env.getCtx();
    for (const layer of layers) {
      const img = ensureWorldMapLayerImage(env, layer);
      if (!img || !img.complete) continue;
      const w = Number(layer.width || img.naturalWidth || 0);
      const h = Number(layer.height || img.naturalHeight || 0);
      if (w <= 0 || h <= 0) continue;
      ctx.drawImage(img, Number(layer.x || 0) - w / 2, Number(layer.y || 0) - h / 2, w, h);
    }
  }
  function activeBackgroundImage(env) {
    if (env.getEditorMapContextKey() === 'world' && env.getWorldMapLayers().length) return null;
    const img = env.getMapImage();
    return (img && img.complete) ? img : null;
  }
  function currentWorldMapBounds(env) {
    const layers = env.getWorldMapLayers();
    if (!layers.length) return null;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, found = false;
    for (const layer of layers) {
      const img = ensureWorldMapLayerImage(env, layer);
      const w = Number(layer.width || (img && img.naturalWidth) || 0);
      const h = Number(layer.height || (img && img.naturalHeight) || 0);
      if (w <= 0 || h <= 0) continue;
      const x = Number(layer.x || 0), y = Number(layer.y || 0);
      minX = Math.min(minX, x - w / 2); maxX = Math.max(maxX, x + w / 2);
      minY = Math.min(minY, y - h / 2); maxY = Math.max(maxY, y + h / 2);
      found = true;
    }
    return found ? { minX, minY, maxX, maxY } : null;
  }
  function updateMapPreviewUI(env, url) {
    const preview = env.document.getElementById('map-preview-img');
    const clearBtn = env.document.getElementById('map-clear-btn');
    const dropZone = env.document.getElementById('map-drop-zone');
    if (!preview || !clearBtn || !dropZone) return;
    const layers = env.getWorldMapLayers();
    const layerCount = Array.isArray(layers) ? layers.length : 0;
    const effectiveUrl = url || (layerCount ? layers[layerCount - 1].url : null);
    if (effectiveUrl) {
      if (String(effectiveUrl).startsWith('__blank__:')) {
        preview.removeAttribute('src');
        preview.style.display = 'none';
      } else {
        preview.style.display = '';
        preview.src = effectiveUrl;
      }
      preview.classList.add('visible');
      clearBtn.classList.add('visible');
      const suffix = layerCount > 0 ? `<br><span style="font-size:0.62rem;opacity:0.7;">${layerCount} locked world map${layerCount === 1 ? '' : 's'} placed</span>` : '';
      const text = dropZone.querySelector('.map-upload-text');
      if (text) text.innerHTML = 'Click or drop to add another world map' + suffix;
    } else {
      preview.classList.remove('visible');
      clearBtn.classList.remove('visible');
      const text = dropZone.querySelector('.map-upload-text');
      if (text) text.innerHTML = 'Click or drop an image<br><span style="font-size:0.62rem;opacity:0.5;">JPG, PNG, WebP</span>';
      env.setMapImage(null);
      env.setMapImageUrl(null);
    }
  }
  function handleMapFile(env, deps) {
    const file = deps.file;
    if (!file || !String(file.type || '').startsWith('image/')) { env.showToast('Please select an image file.'); return; }
    if (file.size > 100 * 1024 * 1024) { env.showToast('Image too large (max 100MB).'); return; }
    const uploading = env.document.getElementById('map-uploading');
    if (uploading) uploading.classList.add('visible');
    const cam = env.getCam();
    deps.uploadWorldMap(deps.sessionId, deps.userId, file, Number.isFinite(-cam.x) ? -cam.x : 0, Number.isFinite(-cam.y) ? -cam.y : 0)
      .then((d) => {
        if (uploading) uploading.classList.remove('visible');
        if (d.ok) {
          if (Array.isArray(d.world_map_layers)) setWorldMapLayers(env, d.world_map_layers);
          else if (d.url) deps.loadMapImage(d.url);
          env.showToast('World map placed and locked.');
        } else {
          env.showToast('Upload failed: ' + (d.error || '?'));
        }
      })
      .catch(() => {
        if (uploading) uploading.classList.remove('visible');
        env.showToast('Upload error.');
      });
  }
  function clearMap(env, deps) {
    return deps.clearWorldMaps(deps.sessionId, deps.userId).then((d) => {
      if (d.ok) {
        setWorldMapLayers(env, []);
        updateMapPreviewUI(env, null);
        env.showToast('World maps removed.');
      }
    });
  }
  window.AppUIWorldControls = {
    normalizeWorldMapLayer,
    ensureWorldMapLayerImage,
    setWorldMapLayers,
    drawWorldMapLayers,
    activeBackgroundImage,
    currentWorldMapBounds,
    updateMapPreviewUI,
    handleMapFile,
    clearMap,
  };
})();
