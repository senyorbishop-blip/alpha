(function () {
  const imageCache = new Map();

  /**
   * Maps numeric terrain IDs to DndAssets procedural terrain keys.
   * @type {Object.<number, string>}
   */
  const PROCEDURAL_KEY_MAP = {
    1: 'stone', 2: 'dirt', 3: 'grass', 4: 'water',
    5: 'forestGround', 6: 'caveStone', 7: 'shallows',
    8: 'hills', 9: 'mountains', 10: 'sand', 11: 'swamp',
    12: 'snow', 13: 'lava',
  };

  /**
   * Try to paint the cell using a cached procedural canvas from DndAssets.
   * UV origin is anchored to (worldX, worldY) so identical coordinates
   * always produce identical output.
   *
   * @param {CanvasRenderingContext2D} g
   * @param {number} terrain  - numeric terrain id
   * @param {number} size     - cell size in pixels
   * @param {number} worldX   - world-space left edge of the cell
   * @param {number} worldY   - world-space top edge of the cell
   * @returns {boolean} true if the procedural tile was applied
   */
  function paintProceduralTerrain(g, terrain, size, worldX, worldY) {
    const init = window.DndAssetInit;
    if (!init || !init.isDndAssetsReady()) return false;
    const key = PROCEDURAL_KEY_MAP[Number(terrain)] || null;
    if (!key) return false;
    const terrainCanvas = init.getDndAsset(key);
    if (!terrainCanvas) return false;
    try {
      const pattern = g.createPattern(terrainCanvas, 'repeat');
      if (!pattern) return false;
      const tileSize = terrainCanvas.width || 96;
      const mat = new DOMMatrix();
      mat.translateSelf(-(worldX % tileSize), -(worldY % tileSize));
      pattern.setTransform(mat);
      g.save();
      g.fillStyle = pattern;
      g.globalAlpha = 0.94;
      g.fillRect(worldX, worldY, size, size);
      g.restore();
      return true;
    } catch (_) {
      return false;
    }
  }

  function resolveTexturePath(terrain, options = {}) {
    const manifestPaths = window.EditorTerrainManifest && window.EditorTerrainManifest.texturePaths;
    const paths = options.paths || manifestPaths || {};
    return paths[Number(terrain) || 0] || null;
  }

  function getTextureImage(terrain, options = {}) {
    const path = resolveTexturePath(terrain, options);
    if (!path) return null;
    const cached = imageCache.get(path);
    if (cached) return (cached.complete && cached.naturalWidth) ? cached : null;
    const img = new Image();
    img.decoding = 'async';
    img.loading = 'eager';
    img.onload = () => {
      if (typeof options.onload === 'function') options.onload(img, path);
    };
    img.onerror = () => {
      imageCache.delete(path);
      if (typeof options.onerror === 'function') options.onerror(path);
    };
    img.src = path;
    imageCache.set(path, img);
    return null;
  }

  /**
   * Paint a terrain cell texture.  Procedural canvas is preferred when
   * DndAssetInit is ready; image-based rendering is used as a fallback.
   *
   * When `options.worldX` / `options.worldY` are provided the procedural path
   * UV-anchors the tile to the world grid (no random rotation/offset).
   *
   * @param {CanvasRenderingContext2D} g
   * @param {number} terrain
   * @param {number} size
   * @param {Object} palette
   * @param {Object} [options]
   * @param {number} [options.worldX]
   * @param {number} [options.worldY]
   * @returns {boolean}
   */
  function paintTextureOverride(g, terrain, size, palette = {}, options = {}) {
    // Prefer procedural canvas when asset cache is ready
    const wx = typeof options.worldX === 'number' ? options.worldX : 0;
    const wy = typeof options.worldY === 'number' ? options.worldY : 0;
    if (paintProceduralTerrain(g, terrain, size, wx, wy)) return true;

    // Fallback: image-based rendering (existing behaviour)
    const img = getTextureImage(terrain, options);
    if (!(img && img.complete && img.naturalWidth)) return false;
    const pattern = g.createPattern(img, 'repeat');
    if (!pattern) return false;
    const lightRgb = palette.lightRgb || { r: 255, g: 255, b: 255 };
    const baseRgb = palette.baseRgb || { r: 136, g: 136, b: 136 };
    const deepRgb = palette.deepRgb || { r: 0, g: 0, b: 0 };
    const rgba = (rgb, alpha = 1) => `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
    g.save();
    g.fillStyle = pattern;
    g.globalAlpha = typeof options.patternAlpha === 'number' ? options.patternAlpha : 0.92;
    g.fillRect(0, 0, size, size);
    g.globalCompositeOperation = 'multiply';
    g.fillStyle = rgba(baseRgb, typeof options.baseAlpha === 'number' ? options.baseAlpha : 0.24);
    g.fillRect(0, 0, size, size);
    g.globalCompositeOperation = 'soft-light';
    g.fillStyle = rgba(lightRgb, typeof options.lightAlpha === 'number' ? options.lightAlpha : 0.18);
    g.fillRect(0, 0, size, size);
    g.globalCompositeOperation = 'overlay';
    g.fillStyle = rgba(deepRgb, typeof options.deepAlpha === 'number' ? options.deepAlpha : 0.12);
    g.fillRect(0, 0, size, size);
    g.restore();
    return true;
  }

  function clearImageCache() {
    imageCache.clear();
  }

  window.EditorTerrainRenderer = {
    imageCache,
    PROCEDURAL_KEY_MAP,   // exported so asset_renderer.js can share it
    getTextureImage,
    paintProceduralTerrain,
    paintTextureOverride,
    clearImageCache,
  };
})();
