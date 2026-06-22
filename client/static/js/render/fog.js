(function(){
  // Stage 5 fog shell owner:
  // - owns map-context fog selection, UI sync, batching, toggle/reveal helpers,
  //   and fog overlay rendering through env/state compatibility wrappers
  // - deliberately does NOT own gameplay collections or the broader draw loop,
  //   which still live in play.html during the staged migration
  function _debugFogPlayer(message, data, env) {
    const flag = (env && env.DEBUG_PLAYER_FOG) || (typeof window !== 'undefined' && window.DEBUG_PLAYER_FOG);
    if (flag && typeof console !== 'undefined' && console.debug) console.debug('[fog/player] ' + message, data || {});
  }
  function _payloadMapCtx(p, env) {
    if (!p || typeof p !== 'object') return _resolveAuthoritativeMapContext(env);
    return p.map_ctx || p.map_context || p.dm_map_context || p.current_map || p.currentMap || p.context || p.map || _resolveAuthoritativeMapContext(env);
  }
  function _normalizeMapCtx(value, env) {
    const raw = String(value || 'world').trim() || 'world';
    if (raw === 'default' || raw === 'main' || raw === 'world_map') return 'world';
    if (raw !== '__local__') return raw;
    if (env && typeof env.getDmMapContext === 'function') {
      const dmCtx = String(env.getDmMapContext() || 'world').trim() || 'world';
      if (dmCtx && dmCtx !== '__local__') return dmCtx;
    }
    return 'world';
  }
  function _resolveAuthoritativeMapContext(env) {
    if (env && typeof env.getCurrentMapContext === 'function') {
      return _normalizeMapCtx(env.getCurrentMapContext(), env);
    }
    if (env && env.currentPoi && env.currentPoi.id) return _normalizeMapCtx(env.currentPoi.id, env);
    if (env && typeof env.getDmMapContext === 'function') {
      const dmCtx = _normalizeMapCtx(env.getDmMapContext(), env);
      if (dmCtx && dmCtx !== 'world') return dmCtx;
    }
    return 'world';
  }
  function fogCurrentCtx(env) {
    return _resolveAuthoritativeMapContext(env);
  }
  function fogSaveCurrentMap(state) {
    if (!state.fogMaps[state.fogMapCtx]) state.fogMaps[state.fogMapCtx] = {};
    state.fogMaps[state.fogMapCtx].enabled = state.fogEnabled;
    state.fogMaps[state.fogMapCtx].cols = state.fogCols;
    state.fogMaps[state.fogMapCtx].rows = state.fogRows;
    if (state.fogCells) state.fogMaps[state.fogMapCtx].cells = state.fogCells.slice();
  }
  function _fogRevealPercent(state) {
    if (!state.fogEnabled || !state.fogCells || !state.fogCells.length) return 100;
    let revealed = 0;
    for (let i = 0; i < state.fogCells.length; i++) if (state.fogCells[i] === 1) revealed += 1;
    return Math.round((revealed / state.fogCells.length) * 100);
  }
  function _isFogPainterActive(state, env) {
    if (!_canEditFog(env) || !state.fogEnabled || !state.fogMouseWorld) return false;
    const mode = String((env && typeof env.getFogSystemMode === 'function' ? env.getFogSystemMode() : '') || '').toLowerCase();
    if (!(mode === 'manual' || mode === 'hybrid')) return false;
    if (String(state.fogMapCtx || 'world') !== _resolveAuthoritativeMapContext(env)) return false;
    if (String(state.fogPaintTool || 'brush') !== 'brush') return false;
    const doc = (env && env.document) || document;
    const fogFlyout = doc.getElementById('flyout-fog');
    return !!(fogFlyout && fogFlyout.classList && fogFlyout.classList.contains('open'));
  }
  function _manualFogEditingAllowed(env) {
    const mode = String((env && typeof env.getFogSystemMode === 'function' ? env.getFogSystemMode() : '') || '').toLowerCase();
    return mode === 'manual' || mode === 'hybrid';
  }
  function _canEditFog(env) {
    if (env && typeof env.canEditFog === 'function') return !!env.canEditFog();
    return !!(env && env.ROLE === 'dm');
  }
  function _fogContextLabel(state, env) {
    const ctx = String(state.fogMapCtx || 'world');
    if (env && typeof env.getMapContextLabel === 'function') return env.getMapContextLabel(ctx);
    return ctx === 'world' ? 'World Map' : `POI / Local Map · ${ctx}`;
  }
  function _syncFogStatus(state, env) {
    const doc = (env && env.document) || document;
    const statusEl = doc.getElementById('fog-status-text');
    const mapEl = doc.getElementById('fog-map-context-text');
    const modelEl = doc.getElementById('fog-visibility-model-text');
    if (mapEl) mapEl.textContent = `Editing: ${_fogContextLabel(state, env)}`;
    if (modelEl) {
      modelEl.textContent = 'Visibility model: Off = unrestricted, Manual = DM-painted fog, Vision = token LOS, Hybrid = both manual + LOS.';
    }
    if (!statusEl) return;
    const mode = String((env && typeof env.getFogSystemMode === 'function' ? env.getFogSystemMode() : '') || '').toLowerCase();
    if (mode === 'off') {
      statusEl.textContent = 'Fog Off · manual fog hidden; players see full map unless vision mode applies.';
      return;
    }
    if (mode === 'vision') {
      statusEl.textContent = 'Vision Fog · token line-of-sight is authoritative on this map.';
      return;
    }
    if (!state.fogEnabled) {
      statusEl.textContent = mode === 'hybrid'
        ? 'Hybrid Fog · manual layer is currently disabled for this map.'
        : 'Manual Fog · currently disabled for this map.';
      return;
    }
    const pct = _fogRevealPercent(state);
    statusEl.textContent = `Fog is ON · players can currently see about ${pct}% of this map. DM view stays mostly visible; use player preview to verify exactly what players see.`;
  }
  function syncFogUI(state, env, handlers) {
    const doc = (env && env.document) || document;
    const chk = doc.getElementById('fog-enable-chk');
    const toolsDiv = doc.getElementById('fog-tools');
    const brushDiv = doc.getElementById('fog-brush-row');
    const manualAllowed = _manualFogEditingAllowed(env);
    const canEdit = _canEditFog(env);
    if (chk) {
      chk.removeEventListener('change', handlers.onFogCheckboxChange);
      chk.checked = state.fogEnabled;
      chk.disabled = !(manualAllowed && canEdit);
      chk.addEventListener('change', handlers.onFogCheckboxChange);
    }
    if (toolsDiv) toolsDiv.style.display = state.fogEnabled && manualAllowed && canEdit ? 'flex' : 'none';
    if (brushDiv) brushDiv.style.display = state.fogEnabled && manualAllowed && canEdit ? 'block' : 'none';
    const toolGrid = doc.getElementById('fog-tool-grid');
    if (toolGrid) toolGrid.style.display = state.fogEnabled && manualAllowed && canEdit ? 'grid' : 'none';
    const advancedTools = doc.getElementById('fog-advanced-tools');
    if (advancedTools) advancedTools.style.display = state.fogEnabled && manualAllowed && canEdit ? 'block' : 'none';
    const revealBtn = doc.getElementById('fog-btn-reveal');
    const hideBtn = doc.getElementById('fog-btn-hide');
    if (revealBtn) revealBtn.classList.toggle('active', !!state.fogReveal);
    if (hideBtn) hideBtn.classList.toggle('active', !state.fogReveal);
    _syncFogStatus(state, env);
  }
  function _coerceFogEntry(entry, fallbackCols, fallbackRows) {
    const cols = Math.max(1, Number(entry && entry.cols) || fallbackCols || 64);
    const rows = Math.max(1, Number(entry && entry.rows) || fallbackRows || 64);
    const total = cols * rows;
    let cells = entry && entry.cells;
    const arr = new Uint8Array(total);
    if (cells instanceof Uint8Array) {
      arr.set(cells.slice(0, total));
    } else if (cells && typeof cells.length === 'number') {
      for (let i = 0; i < Math.min(cells.length, total); i++) arr[i] = cells[i] === 1 || cells[i] === '1' ? 1 : 0;
    }
    return { enabled: !!(entry && entry.enabled), cols, rows, cells: arr, revision: Number(entry && entry.revision) || 0, map_context: entry && entry.map_context };
  }
  function _findFogEntry(state, env, ctx) {
    const target = _normalizeMapCtx(ctx, env);
    if (state.fogMaps[target]) return { key: target, entry: state.fogMaps[target], reason: 'exact' };
    for (const [key, entry] of Object.entries(state.fogMaps || {})) {
      if (_normalizeMapCtx(key, env) === target || _normalizeMapCtx(entry && entry.map_context, env) === target) {
        return { key, entry, reason: 'alias' };
      }
    }
    return null;
  }
  function _ensureEnabledCells(entry) {
    if (!entry || !entry.enabled) return entry;
    const total = (Number(entry.cols) || 64) * (Number(entry.rows) || 64);
    if (!(entry.cells instanceof Uint8Array) || entry.cells.length !== total) entry.cells = _coerceFogEntry(entry, entry.cols, entry.rows).cells;
    return entry;
  }

  function fogLoadMap(state, env, ctx) {
    const normalizedCtx = _normalizeMapCtx(ctx, env);
    state.fogMapCtx = normalizedCtx;
    const found = _findFogEntry(state, env, normalizedCtx);
    if (found && found.key !== normalizedCtx) {
      state.fogMaps[normalizedCtx] = found.entry;
    }
    const entry = found ? _ensureEnabledCells(_coerceFogEntry(found.entry, state.fogCols, state.fogRows)) : null;
    state.lastFogNotDrawingReason = '';
    if (entry) {
      state.fogMaps[normalizedCtx] = entry;
      state.fogEnabled = !!entry.enabled;
      state.fogCols = entry.cols || 64;
      state.fogRows = entry.rows || 64;
      state.fogCells = state.fogEnabled ? (entry.cells || new Uint8Array(state.fogCols * state.fogRows)) : null;
      if (state.fogCanvas && state.fogEnabled) { state.fogCanvas.width = state.fogCols; state.fogCanvas.height = state.fogRows; }
    } else {
      const hasAnyFog = Object.keys(state.fogMaps || {}).length > 0;
      state.fogEnabled = false;
      state.fogCols = state.fogCols || 64; state.fogRows = state.fogRows || 64;
      state.fogCells = null;
      state.lastFogNotDrawingReason = hasAnyFog ? `no fog entry for active context ${normalizedCtx}; known keys: ${Object.keys(state.fogMaps || {}).join(', ')}` : 'no fog state received from server';
    }
    state.fogImageDirty = true;
    env.invalidateFogCache();
    syncFogUI(state, env, env.handlers);
    if (typeof env.syncShellState === 'function') env.syncShellState(state);
    if (env && typeof env.requestRenderFrame === 'function') env.requestRenderFrame('fog load map');
  }

  function fogInitCells(state, cols, rows, cells) {
    state.fogCols = cols || 64;
    state.fogRows = rows || 64;
    const total = state.fogCols * state.fogRows;
    state.fogCells = new Uint8Array(total);
    if (cells) {
      const len = Math.min(cells.length, total);
      for (let i = 0; i < len; i++) state.fogCells[i] = cells[i] === '1' ? 1 : 0;
    }
    if (state.fogCanvas) {
      state.fogCanvas.width = state.fogCols;
      state.fogCanvas.height = state.fogRows;
    }
  }
  function drawFogOverlay(state, env, W, H) {
    const bgImage = env.activeBackgroundImage();
    if (!state.fogEnabled) { state.lastFogNotDrawingReason = 'fog disabled for active context'; return; }
    if (!state.fogCells) { state.lastFogNotDrawingReason = 'fog enabled but no cells'; return; }
    if (!bgImage) { state.lastFogNotDrawingReason = 'no active background image'; return; }
    state.lastFogNotDrawingReason = '';
    _debugFogPlayer('draw overlay enabled active_ctx...', { enabled: state.fogEnabled, active_ctx: state.fogMapCtx, cols: state.fogCols, rows: state.fogRows }, env);
    const mw = bgImage.naturalWidth;
    const mh = bgImage.naturalHeight;
    const ctx = env.ctx;
    const cam = env.cam;
    const fogCanvas = state.fogCanvas;
    const fogCtx = state.fogCtx;
    if (fogCanvas.width !== state.fogCols || fogCanvas.height !== state.fogRows) {
      fogCanvas.width = state.fogCols;
      fogCanvas.height = state.fogRows;
      state.fogImageDirty = true;
    }
    if (state.fogImageDirty) {
      const idata = fogCtx.createImageData(state.fogCols, state.fogRows);
      const buf = idata.data;
      const isDM = env.ROLE === 'dm';
      const settings = env.currentMapSettings();
      const dmAlpha = Math.max(0, Math.min(1, Number(settings.fog_dm_alpha ?? 0.66)));
      // Keep unrevealed fog fully opaque for players to avoid accidental map leakage.
      const playerAlpha = 1.0;
      const alpha = Math.round((isDM ? dmAlpha : playerAlpha) * 255);
      for (let i = 0; i < state.fogCols * state.fogRows; i++) {
        const base = i * 4;
        if (state.fogCells[i] === 1) {
          buf[base + 0] = 0; buf[base + 1] = 0; buf[base + 2] = 0; buf[base + 3] = 0;
        } else if (isDM) {
          buf[base + 0] = 30; buf[base + 1] = 40; buf[base + 2] = 55; buf[base + 3] = alpha;
        } else {
          buf[base + 0] = 0; buf[base + 1] = 0; buf[base + 2] = 0; buf[base + 3] = alpha;
        }
      }
      fogCtx.putImageData(idata, 0, 0);
      state.fogImageDirty = false;
    }
    ctx.save();
    ctx.translate(W/2, H/2);
    ctx.scale(cam.zoom, cam.zoom);
    ctx.translate(cam.x, cam.y);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(fogCanvas, -mw/2, -mh/2, mw, mh);
    ctx.imageSmoothingEnabled = true;
    ctx.restore();

    const doc = env.document || document;
    if (_isFogPainterActive(state, env)) {
      const cellW = (mw / state.fogCols) * cam.zoom;
      const brushR = Math.max(state.fogBrushSize - 1, 0);
      const brushPx = (brushR + 0.5) * cellW;
      const sw = env.worldToScreen(state.fogMouseWorld.x, state.fogMouseWorld.y);
      ctx.save();
      ctx.beginPath();
      ctx.arc(sw.x, sw.y, brushPx, 0, Math.PI*2);
      ctx.strokeStyle = state.fogReveal ? 'rgba(46,204,113,0.9)' : 'rgba(231,76,60,0.9)';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([5, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 0.12;
      ctx.fillStyle = state.fogReveal ? '#2ecc71' : '#e74c3c';
      ctx.fill();
      ctx.restore();
    }
  }
  function fogWorldToCell(state, env, wx, wy) {
    const bgImage = env.activeBackgroundImage();
    if (!bgImage) return null;
    const mw = bgImage.naturalWidth, mh = bgImage.naturalHeight;
    const col = Math.floor((wx + mw/2) / mw * state.fogCols);
    const row = Math.floor((wy + mh/2) / mh * state.fogRows);
    if (col < 0 || col >= state.fogCols || row < 0 || row >= state.fogRows) return null;
    return { col, row, idx: row * state.fogCols + col };
  }
  function fogPaintAt(state, env, wx, wy) {
    if (!state.fogEnabled || !state.fogCells || !env.mapImage) return;
    const center = fogWorldToCell(state, env, wx, wy);
    if (!center) return;
    const r = Math.max(0, state.fogBrushSize - 1);
    let changed = false;
    for (let dr = -r; dr <= r; dr++) {
      for (let dc = -r; dc <= r; dc++) {
        if (dc*dc + dr*dr > r*r + r*0.5) continue;
        const col = center.col + dc, row = center.row + dr;
        if (col < 0 || col >= state.fogCols || row < 0 || row >= state.fogRows) continue;
        const idx = row * state.fogCols + col;
        const newVal = state.fogReveal ? 1 : 0;
        if (state.fogCells[idx] !== newVal) {
          state.fogCells[idx] = newVal;
          state.fogDirtyBatch.add(idx);
          changed = true;
        }
      }
    }
    if (changed) env.invalidateFogCache();
    if (state.fogPaintTimer) clearTimeout(state.fogPaintTimer);
    state.fogPaintTimer = setTimeout(() => fogFlushBatch(state, env), 80);
  }
  function fogFlushBatch(state, env) {
    if (state.fogDirtyBatch.size === 0) return;
    const cells = Array.from(state.fogDirtyBatch);
    state.fogDirtyBatch.clear();
    env.sendWS({ type: 'fog_paint', payload: { reveal: state.fogReveal, cells, map_ctx: state.fogMapCtx } });
    if (typeof window.requestCombatFogSyncDebounced === 'function') window.requestCombatFogSyncDebounced('fog_changed');
  }
  function fogToggle(state, env, enabled) {
    const manualAllowed = _manualFogEditingAllowed(env);
    if (enabled && !manualAllowed) enabled = false;
    state.fogEnabled = enabled;
    if (typeof env.syncShellState === 'function') env.syncShellState(state);
    if (!state.fogMaps[state.fogMapCtx]) state.fogMaps[state.fogMapCtx] = { enabled: false, cols: 64, rows: 64, cells: null };
    state.fogMaps[state.fogMapCtx].enabled = enabled;
    if (enabled) {
      const entry = state.fogMaps[state.fogMapCtx];
      state.fogCols = entry.cols || state.fogCols || 64;
      state.fogRows = entry.rows || state.fogRows || 64;
      if (!entry.cells) {
        entry.cells = new Uint8Array(state.fogCols * state.fogRows);
      }
      state.fogCells = entry.cells;
      if (state.fogCanvas) { state.fogCanvas.width = state.fogCols; state.fogCanvas.height = state.fogRows; }
    } else if (!enabled) {
      state.fogCells = null;
    }
    env.invalidateFogCache();
    syncFogUI(state, env, env.handlers);
    env.sendWS({
      type: 'fog_toggle',
      payload: {
        enabled,
        map_ctx: state.fogMapCtx,
        map_context: state.fogMapCtx,
      },
    });
  }
  function setFogMode(state, env, reveal) {
    state.fogReveal = reveal;
    const doc = (env && env.document) || document;
    const revealBtn = doc.getElementById('fog-btn-reveal');
    const hideBtn = doc.getElementById('fog-btn-hide');
    if (revealBtn) revealBtn.classList.toggle('active', !!reveal);
    if (hideBtn) hideBtn.classList.toggle('active', !reveal);
    if (env && typeof env.syncShellState === 'function') env.syncShellState(state);
  }
  function fogRevealAll(state, env) {
    if (!state.fogCells) fogInitCells(state, state.fogCols, state.fogRows, '');
    const all = Array.from({length: state.fogCols * state.fogRows}, (_, i) => i);
    state.fogCells.fill(1);
    env.invalidateFogCache();
    env.sendWS({ type: 'fog_paint', payload: { reveal: true, cells: all, map_ctx: state.fogMapCtx } });
  }
  function fogHideAll(state, env) {
    if (!state.fogCells) fogInitCells(state, state.fogCols, state.fogRows, '');
    const all = Array.from({length: state.fogCols * state.fogRows}, (_, i) => i);
    state.fogCells.fill(0);
    env.invalidateFogCache();
    env.sendWS({ type: 'fog_paint', payload: { reveal: false, cells: all, map_ctx: state.fogMapCtx } });
  }
  function fogApplyState(state, env, p) {
    if (p.fog_maps) {
      _debugFogPlayer('state_sync map_ctx...', { map_ctx: _resolveAuthoritativeMapContext(env), maps: Object.keys(p.fog_maps || {}) }, env);
      const nextFogMaps = { ...(state.fogMaps || {}) };
      Object.entries(p.fog_maps).forEach(([ctx, entry]) => {
        const mapCtx = _normalizeMapCtx(ctx, env);
        const incomingRevision = Number(entry && entry.revision) || 0;
        const localEntry = nextFogMaps[mapCtx] || null;
        const localRevision = Number(localEntry && localEntry.revision) || 0;
        if (localEntry && incomingRevision < localRevision) {
          _debugFogPlayer('fog_state ignored stale fog_map revision', { map_ctx: mapCtx, incoming_revision: incomingRevision, local_revision: localRevision }, env);
          return;
        }
        const total = (entry.cols || 64) * (entry.rows || 64);
        const arr = new Uint8Array(total);
        const str = entry.cells || '';
        for (let i = 0; i < Math.min(str.length, total); i++) arr[i] = str[i] === '1' ? 1 : 0;
        nextFogMaps[mapCtx] = { enabled: !!entry.enabled, cols: entry.cols || 64, rows: entry.rows || 64, cells: arr, revision: incomingRevision, map_context: _normalizeMapCtx(entry.map_context || ctx, env) };
      });
      state.fogMaps = nextFogMaps;
    }
    const stateMapCtx = _payloadMapCtx(p, env);
    if (p.map_ctx !== undefined || p.map_context !== undefined || p.dm_map_context !== undefined || p.current_map !== undefined || p.fog_cells !== undefined) {
      const total = (p.fog_cols || 64) * (p.fog_rows || 64);
      const arr = new Uint8Array(total);
      const str = p.fog_cells || '';
      for (let i = 0; i < Math.min(str.length, total); i++) arr[i] = str[i] === '1' ? 1 : 0;
      const mapCtx = _normalizeMapCtx(stateMapCtx, env);
      state.fogMaps[mapCtx] = { enabled: p.fog_enabled !== undefined ? !!p.fog_enabled : true, cols: p.fog_cols || 64, rows: p.fog_rows || 64, cells: arr, revision: Number(p.revision) || 0, map_context: mapCtx };
      _debugFogPlayer('fog_state map_ctx enabled cols rows revealed_count', { map_ctx: mapCtx, enabled: state.fogMaps[mapCtx].enabled, cols: state.fogMaps[mapCtx].cols, rows: state.fogMaps[mapCtx].rows, revealed_count: Array.from(arr).filter(Boolean).length }, env);
    }
    const ctx = fogCurrentCtx(env);
    if ((p.map_ctx !== undefined || p.map_context !== undefined || p.dm_map_context !== undefined || p.current_map !== undefined || p.currentMap !== undefined || p.context !== undefined || p.map !== undefined || p.fog_cells !== undefined) && _normalizeMapCtx(stateMapCtx, env) !== ctx) { state.lastFogPayloadMapContext = _normalizeMapCtx(stateMapCtx, env); return; }
    fogLoadMap(state, env, ctx);
    state.lastFogStateRevision = Number(p && p.revision) || Number(state.lastFogStateRevision) || 0;
    if (env && typeof env.requestRenderFrame === 'function') env.requestRenderFrame('fog state apply');
    else if (env && typeof env.drawFrame === 'function') env.drawFrame();
  }
  function fogApplyUpdate(state, env, p) {
    const updCtx = _normalizeMapCtx(_payloadMapCtx(p, env), env);
    const val = p && p.reveal ? 1 : 0;
    state.lastFogPayloadMapContext = updCtx;
    const incomingRevision = Number(p && p.revision) || 0;
    const localRevision = Number(state.fogMaps && state.fogMaps[updCtx] && state.fogMaps[updCtx].revision) || 0;
    if (state.fogMaps && state.fogMaps[updCtx] && incomingRevision < localRevision) {
      _debugFogPlayer('fog_update ignored stale revision', { map_ctx: updCtx, incoming_revision: incomingRevision, local_revision: localRevision }, env);
      return;
    }
    state.lastFogUpdateRevision = incomingRevision || ((Number(state.lastFogUpdateRevision) || 0) + 1);
    if (!state.fogMaps[updCtx]) state.fogMaps[updCtx] = { enabled: true, cols: Number(p && p.fog_cols) || 64, rows: Number(p && p.fog_rows) || 64, cells: new Uint8Array((Number(p && p.fog_cols) || 64) * (Number(p && p.fog_rows) || 64)), revision: incomingRevision, map_context: updCtx };
    const entry = state.fogMaps[updCtx];
    entry.revision = Math.max(Number(entry.revision) || 0, incomingRevision);
    if (Number(p && p.fog_cols) > 0) entry.cols = Number(p.fog_cols);
    if (Number(p && p.fog_rows) > 0) entry.rows = Number(p.fog_rows);
    // A sparse paint update is only emitted by the server after that map's
    // manual fog is enabled. If this client missed the prior fog_state (common
    // during map-entry races), promote the local entry to enabled so the newly
    // synced cells actually render instead of waiting for a refresh.
    entry.enabled = true;
    if (!entry.cells || !(entry.cells instanceof Uint8Array)) {
      entry.cells = new Uint8Array((entry.cols || 64) * (entry.rows || 64));
    }
    (p && p.cells ? p.cells : []).forEach(idx => {
      if (idx >= 0 && idx < entry.cells.length) entry.cells[idx] = val;
    });
    const activeCtx = fogCurrentCtx(env);
    if (updCtx === activeCtx) {
      fogLoadMap(state, env, activeCtx);
      env.invalidateFogCache();
      _debugFogPlayer('fog_update map_ctx active_ctx applied cells count', { map_ctx: updCtx, active_ctx: activeCtx, applied: true, cells: (p && p.cells ? p.cells.length : 0) }, env);
      if (env && typeof env.requestRenderFrame === 'function') env.requestRenderFrame('fog update apply');
      else if (env && typeof env.drawFrame === 'function') env.drawFrame();
    }
  }
  function debugFog(state, env) {
    const cells = state.fogCells;
    let revealed = 0;
    if (cells) for (let i = 0; i < cells.length; i++) if (cells[i] === 1) revealed++;
    return { role: env && env.ROLE, activeMapContext: fogCurrentCtx(env), fogMapCtx: state.fogMapCtx, knownFogMapKeys: Object.keys(state.fogMaps || {}), fogEnabled: !!state.fogEnabled, fogCols: state.fogCols, fogRows: state.fogRows, hasFogCells: !!cells, fogCellsLength: cells ? cells.length : 0, revealedCount: revealed, lastFogStateRevision: Number(state.lastFogStateRevision) || 0, lastFogUpdateRevision: Number(state.lastFogUpdateRevision) || 0, lastFogPayloadMapContext: state.lastFogPayloadMapContext || '', notDrawingReason: state.lastFogNotDrawingReason || (!state.fogEnabled ? 'fog disabled for active context' : (!cells ? 'fog enabled but no cells' : '')) };
  }
  window.AppFog = { debugFog, normalizeMapCtx: _normalizeMapCtx, payloadMapCtx: _payloadMapCtx, fogCurrentCtx, fogSaveCurrentMap, syncFogUI, fogLoadMap, fogInitCells, drawFogOverlay, fogWorldToCell, fogPaintAt, fogFlushBatch, fogToggle, setFogMode, fogRevealAll, fogHideAll, fogApplyState, fogApplyUpdate };
})();
