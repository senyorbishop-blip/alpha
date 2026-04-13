/**
 * asset_initializer.js
 * Calls every terrain and prop function in DndAssets once on startup
 * and caches the resulting canvases in `window.DndAssetCache`.
 *
 * Call `initDndAssets()` once during editor boot before the first draw.
 */
(function () {
  'use strict';

  /** @type {Object.<string, HTMLCanvasElement|OffscreenCanvas|null>} */
  const assetCache = {};

  /**
   * Initialise and cache all procedural terrain and prop canvases.
   * Safe to call multiple times — subsequent calls are no-ops.
   * @returns {boolean} true if assets were loaded for the first time
   */
  function initDndAssets() {
    if (assetCache._ready) return false;
    const assets = window.DndAssets;
    if (!assets) {
      console.warn('[asset-init] DndAssets not loaded');
      return false;
    }
    const { terrain, props, assetManifest } = assets;
    for (const entry of assetManifest.terrain) {
      try {
        assetCache[entry.id] = (typeof terrain[entry.id] === 'function')
          ? terrain[entry.id]()
          : null;
      } catch (err) {
        console.warn('[asset-init] terrain', entry.id, err);
        assetCache[entry.id] = null;
      }
    }
    for (const entry of assetManifest.props) {
      try {
        assetCache[entry.id] = (typeof props[entry.id] === 'function')
          ? props[entry.id]()
          : null;
      } catch (err) {
        console.warn('[asset-init] prop', entry.id, err);
        assetCache[entry.id] = null;
      }
    }
    assetCache._ready = true;
    return true;
  }

  /**
   * Returns the cached canvas for `id`, or null if not found / not ready.
   * @param {string} id
   * @returns {HTMLCanvasElement|OffscreenCanvas|null}
   */
  function getDndAsset(id) {
    return assetCache[id] ?? null;
  }

  /**
   * Returns true if assets have been initialised.
   * @returns {boolean}
   */
  function isDndAssetsReady() {
    return !!assetCache._ready;
  }

  /**
   * Returns a manifest entry by id, or the full manifest if no id is given.
   * @param {string} [id]  - asset id (terrain or prop)
   * @returns {Object|null}
   */
  function getAssetManifest(id) {
    const manifest = window.DndAssets && window.DndAssets.assetManifest;
    if (!manifest) return null;
    if (id === undefined) return manifest;
    const terrain = Array.isArray(manifest.terrain) ? manifest.terrain : [];
    const props = Array.isArray(manifest.props) ? manifest.props : [];
    return terrain.find(function (e) { return e.id === id; }) ||
           props.find(function (e) { return e.id === id; }) ||
           null;
  }

  window.DndAssetCache = assetCache;
  window.DndAssetInit = Object.freeze({ initDndAssets, getDndAsset, isDndAssetsReady, getAssetManifest });
})();
