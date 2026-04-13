(function (global) {
  'use strict';

  function parseCellKey(key) {
    const parts = String(key).includes(':') ? String(key).split(':') : String(key).split(',');
    const gx = Number(parts[0]);
    const gy = Number(parts[1]);
    if (!Number.isFinite(gx) || !Number.isFinite(gy)) return null;
    return { gx, gy };
  }

  function ensureCache(cache) {
    if (!cache.canvas) {
      cache.canvas = document.createElement('canvas');
      cache.ctx = cache.canvas.getContext('2d');
    }
    return cache;
  }

  function invalidate(cache) {
    cache.dirty = true;
    return cache;
  }

  function computeBounds(entries) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [key] of entries) {
      const cell = parseCellKey(key);
      if (!cell) continue;
      if (cell.gx < minX) minX = cell.gx;
      if (cell.gy < minY) minY = cell.gy;
      if (cell.gx > maxX) maxX = cell.gx;
      if (cell.gy > maxY) maxY = cell.gy;
    }
    if (!Number.isFinite(minX)) return null;
    return { minX, minY, maxX, maxY };
  }

  function rebuild(opts) {
    const cache = ensureCache(opts.cache);
    const entries = Array.isArray(opts.entries) ? opts.entries : [];
    cache.mode = opts.mode || 'tactical';
    cache.alpha = Number.isFinite(opts.alpha) ? opts.alpha : 1;
    cache.contextKey = String(opts.contextKey || 'world');
    if (!entries.length) {
      cache.canvas.width = 1;
      cache.canvas.height = 1;
      cache.bounds = null;
      cache.dirty = false;
      return cache;
    }
    const baseBounds = computeBounds(entries);
    if (!baseBounds) {
      cache.canvas.width = 1;
      cache.canvas.height = 1;
      cache.bounds = null;
      cache.dirty = false;
      return cache;
    }
    const pad = cache.mode === 'world' ? 3 : 1;
    const cellSize = Number(opts.cellSize) || 50;
    cache.bounds = {
      minX: baseBounds.minX - pad,
      minY: baseBounds.minY - pad,
      maxX: baseBounds.maxX + pad,
      maxY: baseBounds.maxY + pad,
    };
    const widthCells = (cache.bounds.maxX - cache.bounds.minX + 1);
    const heightCells = (cache.bounds.maxY - cache.bounds.minY + 1);
    cache.canvas.width = Math.max(1, widthCells * cellSize);
    cache.canvas.height = Math.max(1, heightCells * cellSize);
    cache.cellSize = cellSize;
    const g = cache.ctx;
    g.clearRect(0, 0, cache.canvas.width, cache.canvas.height);

    const drawCells = () => {
      for (const [key, terrain] of entries) {
        const cell = parseCellKey(key);
        if (!cell) continue;
        const x = (cell.gx - cache.bounds.minX) * cellSize;
        const y = (cell.gy - cache.bounds.minY) * cellSize;
        opts.drawCell(cell.gx, cell.gy, Number(terrain) || 1, x, y, cellSize);
      }
      if (typeof opts.postProcess === 'function') opts.postProcess(g, cache);
    };

    if (typeof opts.withRenderCtx === 'function') {
      opts.withRenderCtx(g, drawCells);
    } else {
      drawCells();
    }
    cache.dirty = false;
    return cache;
  }

  global.AppTerrainCache = {
    parseCellKey,
    ensureCache,
    invalidate,
    rebuild,
  };
})(window);
