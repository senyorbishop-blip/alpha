/**
 * placement_controller.js
 * Terrain brush, prop stamp, Shift+Drag multi-prop batching, and undo/redo
 * for the DnD tactical map editor.
 *
 * Attach to the editor canvas by calling:
 *   PlacementController.attach(canvasEl, env)
 *
 * `env` must expose:
 *   env.editorActiveLayer  — 'terrain' | 'props'
 *   env.editorTerrain      — numeric terrain id
 *   env.editorBrush        — 1–12 (grid squares)
 *   env.editorPropKind     — string prop kind
 *   env.editorPropRotation — 0 / 90 / 180 / 270
 *   env.editorPropSize     — 1–4
 *   env.pushEditorUndo(fn) — push a reversible action onto the undo stack
 *   env.applyTerrainPaint(cells) — [{gx,gy,terrain}]
 *   env.stampProp(item)    — place a single normalised prop item
 *   env.screenToWorld(x,y) — {wx,wy}
 *   env.worldToCell(wx,wy) — {gx,gy}
 *   env.cellToWorld(gx,gy) — {wx,wy}
 *   env.drawFrame()
 */
(function () {
  'use strict';

  let _attached = false;
  let _canvas = null;
  let _env = null;

  // ── Terrain paint state ──────────────────────────────────────────────────
  let _painting = false;
  let _paintedCells = null;   // Set of 'gx,gy' keys painted in current stroke

  // ── Prop stamp / shift-drag state ───────────────────────────────────────
  let _stampBatch = null;     // Array of prop items in the current shift-drag batch
  let _stampBatchCells = null;// Set of 'gx,gy' keys already stamped
  let _stampDragging = false;

  // ─────────────────────────────────────────────────────────────────────────

  /**
   * @param {PointerEvent} e
   * @returns {{wx:number, wy:number}|null}
   */
  function eventWorld(e) {
    if (!_env || typeof _env.screenToWorld !== 'function') return null;
    const rect = _canvas.getBoundingClientRect();
    return _env.screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
  }

  function eventCell(e) {
    const wc = eventWorld(e);
    if (!wc) return null;
    if (typeof _env.worldToCell !== 'function') return null;
    return _env.worldToCell(wc.wx, wc.wy);
  }

  // ── Terrain handlers ─────────────────────────────────────────────────────

  function terrainDown(e) {
    _painting = true;
    _paintedCells = new Set();
    terrainMove(e);
  }

  function terrainMove(e) {
    if (!_painting) return;
    const cell = eventCell(e);
    if (!cell) return;
    const { gx, gy } = cell;
    const brush = Math.max(1, Math.min(12, Number(_env.editorBrush || _env.editorBrushSize) || 1));
    const terrain = Number(_env.editorTerrain) || 1;
    const cells = [];
    const half = Math.floor(brush / 2);
    for (let dy = 0; dy < brush; dy++) {
      for (let dx = 0; dx < brush; dx++) {
        const cx = gx - half + dx;
        const cy = gy - half + dy;
        const key = `${cx},${cy}`;
        if (!_paintedCells.has(key)) {
          _paintedCells.add(key);
          cells.push({ gx: cx, gy: cy, terrain });
        }
      }
    }
    if (cells.length && typeof _env.applyTerrainPaint === 'function') {
      _env.applyTerrainPaint(cells);
    }
  }

  function terrainUp() {
    if (!_painting) return;
    _painting = false;
    if (_paintedCells && _paintedCells.size > 0 && typeof _env.pushEditorUndo === 'function') {
      const snapshot = Array.from(_paintedCells);
      _env.pushEditorUndo({ type: 'terrain_paint', cells: snapshot });
    }
    _paintedCells = null;
  }

  // ── Prop stamp handlers ──────────────────────────────────────────────────

  /**
   * @param {PointerEvent} e
   * @returns {Object|null} normalised prop item
   */
  function buildPropItem(e) {
    if (!_env) return null;
    const wc = eventWorld(e);
    if (!wc) return null;
    if (typeof _env.buildEditorPropItem !== 'function') return null;
    return _env.buildEditorPropItem(_env.editorPropKind, wc.wx, wc.wy, _env.editorPropSize || 1);
  }

  function propDown(e) {
    const item = buildPropItem(e);
    if (!item) return;

    if (e.shiftKey) {
      // Begin batch
      _stampBatch = [item];
      _stampBatchCells = new Set();
      const cell = eventCell(e);
      if (cell) _stampBatchCells.add(`${cell.gx},${cell.gy}`);
      _stampDragging = true;
      if (typeof _env.stampProp === 'function') _env.stampProp(item);
    } else {
      // Single stamp with its own undo entry
      if (typeof _env.stampProp === 'function') _env.stampProp(item);
      if (typeof _env.pushEditorUndo === 'function') {
        _env.pushEditorUndo({ type: 'prop_stamp', items: [item] });
      }
    }
  }

  function propMove(e) {
    if (!_stampDragging || !_stampBatch) return;
    const cell = eventCell(e);
    if (!cell) return;
    const key = `${cell.gx},${cell.gy}`;
    if (_stampBatchCells.has(key)) return;
    _stampBatchCells.add(key);
    const item = buildPropItem(e);
    if (!item) return;
    _stampBatch.push(item);
    if (typeof _env.stampProp === 'function') _env.stampProp(item);
  }

  function propUp() {
    if (!_stampDragging || !_stampBatch) return;
    _stampDragging = false;
    if (_stampBatch.length > 0 && typeof _env.pushEditorUndo === 'function') {
      const batch = _stampBatch.slice();
      _env.pushEditorUndo({ type: 'prop_stamp', items: batch });
    }
    _stampBatch = null;
    _stampBatchCells = null;
  }

  // ── Pointer event router ─────────────────────────────────────────────────

  function onPointerDown(e) {
    if (!_env) return;
    const layer = _env.editorActiveLayer;
    if (layer === 'terrain') terrainDown(e);
    else if (layer === 'props') propDown(e);
  }

  function onPointerMove(e) {
    if (!_env) return;
    const layer = _env.editorActiveLayer;
    if (layer === 'terrain') terrainMove(e);
    else if (layer === 'props') propMove(e);
  }

  function onPointerUp() {
    if (!_env) return;
    const layer = _env.editorActiveLayer;
    if (layer === 'terrain') terrainUp();
    else if (layer === 'props') propUp();
  }

  function onKeyUp(e) {
    // If Shift is released mid-drag, commit the batch
    if (!e.shiftKey && _stampDragging) propUp();
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /**
   * Attach the placement controller to a canvas element.
   * @param {HTMLCanvasElement} canvasEl
   * @param {Object} env
   */
  function attach(canvasEl, env) {
    if (_attached) detach();
    _canvas = canvasEl;
    _env = env;
    _canvas.addEventListener('pointerdown', onPointerDown);
    _canvas.addEventListener('pointermove', onPointerMove);
    _canvas.addEventListener('pointerup',   onPointerUp);
    _canvas.addEventListener('pointercancel', onPointerUp);
    window.addEventListener('keyup', onKeyUp);
    _attached = true;
  }

  /**
   * Detach all listeners from the current canvas.
   */
  function detach() {
    if (_canvas) {
      _canvas.removeEventListener('pointerdown', onPointerDown);
      _canvas.removeEventListener('pointermove', onPointerMove);
      _canvas.removeEventListener('pointerup',   onPointerUp);
      _canvas.removeEventListener('pointercancel', onPointerUp);
    }
    window.removeEventListener('keyup', onKeyUp);
    _canvas = null;
    _env = null;
    _attached = false;
    _painting = false;
    _paintedCells = null;
    _stampBatch = null;
    _stampBatchCells = null;
    _stampDragging = false;
  }

  window.PlacementController = Object.freeze({ attach, detach });
})();
