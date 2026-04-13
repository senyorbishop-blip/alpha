(function (global) {
  'use strict';

  function drawGrid(opts) {
    const ctx = opts.ctx;
    const cam = opts.cam;
    const W = Number(opts.width) || 0;
    const H = Number(opts.height) || 0;
    const worldMode = !!opts.worldMode;
    const showWorldGrid = !!opts.showWorldGrid;
    const hasMapImage = !!opts.hasMapImage;
    if (worldMode && !showWorldGrid) return;
    const gridSize = (Number(opts.gridPx) || 50) * cam.zoom;
    if (gridSize < (worldMode ? 16 : 8)) return;
    const offX = ((cam.x * cam.zoom) + W / 2) % gridSize;
    const offY = ((cam.y * cam.zoom) + H / 2) % gridSize;
    ctx.strokeStyle = worldMode
      ? (hasMapImage ? 'rgba(255,240,200,0.045)' : 'rgba(120,180,180,0.04)')
      : (hasMapImage ? 'rgba(0,212,212,0.12)' : 'rgba(0,212,212,0.07)');
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = offX; x < W; x += gridSize) { ctx.moveTo(x, 0); ctx.lineTo(x, H); }
    for (let y = offY; y < H; y += gridSize) { ctx.moveTo(0, y); ctx.lineTo(W, y); }
    ctx.stroke();
  }

  global.AppGrid = { drawGrid };
})(window);
