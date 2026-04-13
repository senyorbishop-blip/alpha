/**
 * editor_brush_cursor.js
 * Renders a live brush-size preview ring that follows the mouse cursor during
 * terrain painting.  The ring is drawn onto a transparent overlay canvas that
 * sits above the main map canvas and is completely non-interactive.
 *
 * Usage:
 *   EditorBrushCursor.attach(overlayCanvas, env);
 *   EditorBrushCursor.detach();
 *
 * `env` must expose:
 *   env.editorActiveLayer  — 'terrain' | 'walls' | 'props'
 *   env.editorBrush        — 1–12 (grid squares)
 *   env.camZoom            — current camera zoom (default 1)
 *   env.screenToWorld(sx, sy) → {wx, wy}  (optional — used for world-space coords)
 */
(function () {
  'use strict';

  let _canvas  = null;
  let _ctx     = null;
  let _env     = null;
  let _attached = false;
  let _frameId  = null;

  // Last known cursor position in CSS (screen) pixels relative to canvas
  let _cursorX = -1;
  let _cursorY = -1;
  let _visible  = false;

  const GRID_PX = 50;   // world pixels per grid cell

  /* ── Rendering ───────────────────────────────────────────────────────── */

  function draw() {
    if (!_ctx || !_canvas) return;
    const w = _canvas.width;
    const h = _canvas.height;
    _ctx.clearRect(0, 0, w, h);

    if (!_visible || !_env) return;

    // Only show cursor in terrain-paint mode
    const layer = String(_env.editorActiveLayer || 'terrain');
    if (layer !== 'terrain') return;

    const zoom      = Math.max(0.05, Number(_env.camZoom) || 1);
    const brush     = Math.max(1, Math.min(12, Number(_env.editorBrush) || 1));
    const cellWorld = GRID_PX;                       // world-space cell size
    const cellScreen = cellWorld * zoom;              // screen-space cell size
    const radius     = (brush * cellScreen) / 2;     // screen-space brush radius

    // Snap cursor position to nearest cell centre in screen space
    const snapCellX = (Math.floor(_cursorX / cellScreen) + 0.5) * cellScreen;
    const snapCellY = (Math.floor(_cursorY / cellScreen) + 0.5) * cellScreen;

    const cx = Math.round(snapCellX);
    const cy = Math.round(snapCellY);

    // Outer dashed ring
    _ctx.save();
    _ctx.beginPath();
    _ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    _ctx.strokeStyle = 'rgba(201, 162, 39, 0.70)';
    _ctx.lineWidth   = 1.5;
    _ctx.setLineDash([4, 3]);
    _ctx.stroke();

    // Thin solid inner ring
    _ctx.beginPath();
    _ctx.arc(cx, cy, Math.max(1, radius - 2), 0, Math.PI * 2);
    _ctx.strokeStyle = 'rgba(0,0,0,0.35)';
    _ctx.lineWidth   = 1;
    _ctx.setLineDash([]);
    _ctx.stroke();

    // Centre crosshair dot
    _ctx.beginPath();
    _ctx.arc(cx, cy, 2.5, 0, Math.PI * 2);
    _ctx.fillStyle = 'rgba(201, 162, 39, 0.85)';
    _ctx.fill();

    _ctx.restore();
  }

  /* ── Event handlers ─────────────────────────────────────────────────── */

  function onMouseMove(e) {
    if (!_canvas) return;
    const rect = _canvas.getBoundingClientRect();
    _cursorX = e.clientX - rect.left;
    _cursorY = e.clientY - rect.top;
    _visible  = true;
    draw();
  }

  function onMouseLeave() {
    _visible = false;
    draw();
  }

  function onMouseEnter() {
    _visible = true;
  }

  /* ── Public API ──────────────────────────────────────────────────────── */

  /**
   * Attach the brush cursor to an overlay canvas.
   * The overlay should be absolutely positioned above the main canvas and have
   * pointer-events: none so it does not intercept clicks.
   *
   * @param {HTMLCanvasElement} overlayCanvas
   * @param {Object} env
   */
  function attach(overlayCanvas, env) {
    if (_attached) detach();
    _canvas = overlayCanvas;
    _env    = env;
    _ctx    = _canvas.getContext('2d');

    // The overlay canvas should be non-interactive — set if not already set
    if (_canvas.style.pointerEvents !== 'none') {
      _canvas.style.pointerEvents = 'none';
    }

    _canvas.addEventListener('mousemove',  onMouseMove);
    _canvas.addEventListener('mouseleave', onMouseLeave);
    _canvas.addEventListener('mouseenter', onMouseEnter);

    // Also listen on the parent (main canvas) if the overlay doesn't receive events
    const parent = _canvas.parentElement;
    if (parent) {
      parent.addEventListener('mousemove',  onMouseMove);
      parent.addEventListener('mouseleave', onMouseLeave);
      parent.addEventListener('mouseenter', onMouseEnter);
    }

    _attached = true;
  }

  /**
   * Detach all listeners and clear the canvas.
   */
  function detach() {
    if (_canvas) {
      _canvas.removeEventListener('mousemove',  onMouseMove);
      _canvas.removeEventListener('mouseleave', onMouseLeave);
      _canvas.removeEventListener('mouseenter', onMouseEnter);
      const parent = _canvas.parentElement;
      if (parent) {
        parent.removeEventListener('mousemove',  onMouseMove);
        parent.removeEventListener('mouseleave', onMouseLeave);
        parent.removeEventListener('mouseenter', onMouseEnter);
      }
      if (_ctx) _ctx.clearRect(0, 0, _canvas.width, _canvas.height);
    }
    if (_frameId !== null) { cancelAnimationFrame(_frameId); _frameId = null; }
    _canvas   = null;
    _ctx      = null;
    _env      = null;
    _attached = false;
    _visible  = false;
  }

  /**
   * Force a redraw (call when brush size changes externally).
   */
  function redraw() {
    draw();
  }

  window.EditorBrushCursor = Object.freeze({ attach, detach, redraw });
})();
