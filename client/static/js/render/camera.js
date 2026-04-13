(function (global) {
  'use strict';

  function worldToScreen(wx, wy, cam, canvas) {
    return {
      x: (wx + cam.x) * cam.zoom + canvas.width / 2,
      y: (wy + cam.y) * cam.zoom + canvas.height / 2,
    };
  }

  function screenToWorld(sx, sy, cam, canvas) {
    return {
      x: (sx - canvas.width / 2) / cam.zoom - cam.x,
      y: (sy - canvas.height / 2) / cam.zoom - cam.y,
    };
  }

  function zoomAtScreenPoint(opts) {
    const cam = opts.cam;
    const canvas = opts.canvas;
    const sx = Number(opts.sx) || 0;
    const sy = Number(opts.sy) || 0;
    const factor = Number(opts.factor) || 1;
    const minZoom = Number.isFinite(opts.minZoom) ? Number(opts.minZoom) : 0.1;
    const maxZoom = Number.isFinite(opts.maxZoom) ? Number(opts.maxZoom) : 8;
    const world = screenToWorld(sx, sy, cam, canvas);
    cam.zoom = Math.max(minZoom, Math.min(maxZoom, cam.zoom * factor));
    cam.x = (sx - canvas.width / 2) / cam.zoom - world.x;
    cam.y = (sy - canvas.height / 2) / cam.zoom - world.y;
    return cam;
  }

  function clampCameraToBounds(opts) {
    const cam = opts.cam;
    const canvas = opts.canvas;
    const bounds = opts.bounds;
    const minPx = Number.isFinite(opts.minPx) ? Number(opts.minPx) : 120;
    if (!(cam && canvas && bounds)) return cam;
    const W = canvas.width;
    const H = canvas.height;
    const mapL = W / 2 + (cam.x + bounds.minX) * cam.zoom;
    const mapR = W / 2 + (cam.x + bounds.maxX) * cam.zoom;
    const mapT = H / 2 + (cam.y + bounds.minY) * cam.zoom;
    const mapB = H / 2 + (cam.y + bounds.maxY) * cam.zoom;
    if (mapR < minPx) cam.x += (minPx - mapR) / cam.zoom;
    if (mapL > W - minPx) cam.x -= (mapL - (W - minPx)) / cam.zoom;
    if (mapB < minPx) cam.y += (minPx - mapB) / cam.zoom;
    if (mapT > H - minPx) cam.y -= (mapT - (H - minPx)) / cam.zoom;
    return cam;
  }

  function resetView(cam, defaults) {
    const src = defaults || { x: 0, y: 0, zoom: 1 };
    cam.x = Number(src.x) || 0;
    cam.y = Number(src.y) || 0;
    cam.zoom = Number(src.zoom) || 1;
    return cam;
  }

  global.AppCamera = {
    worldToScreen,
    screenToWorld,
    zoomAtScreenPoint,
    clampCameraToBounds,
    resetView,
  };
})(window);
