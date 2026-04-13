/**
 * asset_renderer.js
 * Centralised canvas rendering helpers for procedural terrain tiles and props.
 *
 * UV-tiling contract:
 *   The pattern origin is shifted so that all tiles with the same world
 *   coordinates look identical regardless of viewport scroll.
 *   No random rotation or offset is applied at paint time.
 */
(function () {
  'use strict';

  /**
   * Paint a single terrain cell using a procedural tile canvas as a repeating
   * pattern, UV-anchored to the world grid.
   *
   * @param {CanvasRenderingContext2D} mapCtx  - destination context
   * @param {HTMLCanvasElement|OffscreenCanvas} terrainCanvas - source tile (96×96)
   * @param {number} worldX   - world-space X of the cell top-left corner
   * @param {number} worldY   - world-space Y of the cell top-left corner
   * @param {number} [cellSize=96] - cell size in world pixels
   * @returns {boolean} true if the pattern was applied
   */
  function paintTerrain(mapCtx, terrainCanvas, worldX, worldY, cellSize) {
    if (!terrainCanvas) return false;
    const size = cellSize || 96;
    try {
      const pattern = mapCtx.createPattern(terrainCanvas, 'repeat');
      if (!pattern) return false;
      const mat = new DOMMatrix();
      mat.translateSelf(-(worldX % size), -(worldY % size));
      pattern.setTransform(mat);
      mapCtx.save();
      mapCtx.fillStyle = pattern;
      mapCtx.fillRect(worldX, worldY, size, size);
      mapCtx.restore();
      return true;
    } catch (_) {
      return false;
    }
  }

  /**
   * Draw a prop canvas centred on (cx, cy) with an optional rotation in degrees.
   * Rotation should only be applied when the user explicitly presses Rotate.
   *
   * @param {CanvasRenderingContext2D} ctx
   * @param {HTMLCanvasElement|OffscreenCanvas} propCanvas
   * @param {number} cx        - centre X in world coordinates
   * @param {number} cy        - centre Y in world coordinates
   * @param {number} [scale=1] - draw scale multiplier
   * @param {number} [rotationDeg=0] - clockwise rotation in degrees (0/90/180/270)
   */
  function paintProp(ctx, propCanvas, cx, cy, scale, rotationDeg) {
    if (!propCanvas) return;
    const sc = scale || 1;
    const rot = rotationDeg || 0;
    const dw = propCanvas.width * sc;
    const dh = propCanvas.height * sc;
    ctx.save();
    ctx.translate(cx, cy);
    if (rot) ctx.rotate(rot * Math.PI / 180);
    ctx.drawImage(propCanvas, -dw / 2, -dh / 2, dw, dh);
    ctx.restore();
  }

  /**
   * Get the procedural terrain canvas for a terrain id,
   * falling back to null if not cached or DndAssetInit unavailable.
   *
   * Uses EditorTerrainRenderer.PROCEDURAL_KEY_MAP as the single source of truth
   * so the mapping is not duplicated across files.
   *
   * @param {string|number} terrainId
   * @returns {HTMLCanvasElement|OffscreenCanvas|null}
   */
  function getTerrainCanvas(terrainId) {
    if (window.DndAssetInit && typeof window.DndAssetInit.getDndAsset === 'function') {
      // Prefer the shared map from terrain_renderer.js; fall back to inline copy
      const SHARED = window.EditorTerrainRenderer && window.EditorTerrainRenderer.PROCEDURAL_KEY_MAP;
      const KEY_MAP = SHARED || {
        1: 'stone', 2: 'dirt', 3: 'grass', 4: 'water',
        5: 'forestGround', 6: 'caveStone', 7: 'sand',
        8: 'sand', 9: 'stone', 10: 'sand', 11: 'grass',
        12: 'stone', 13: 'lava',
      };
      const key = typeof terrainId === 'number'
        ? (KEY_MAP[terrainId] || 'stone')
        : String(terrainId);
      return window.DndAssetInit.getDndAsset(key);
    }
    return null;
  }

  /**
   * Get the procedural prop canvas for a prop asset id.
   *
   * @param {string} assetId
   * @returns {HTMLCanvasElement|OffscreenCanvas|null}
   */
  function getPropCanvas(assetId) {
    if (window.DndAssetInit && typeof window.DndAssetInit.getDndAsset === 'function') {
      return window.DndAssetInit.getDndAsset(String(assetId || ''));
    }
    return null;
  }

  window.AssetRenderer = Object.freeze({
    paintTerrain,
    paintProp,
    getTerrainCanvas,
    getPropCanvas,
  });
})();
