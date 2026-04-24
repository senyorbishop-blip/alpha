/**
 * editor_panel.js
 * Premium DnD Tactical Map Editor — Left Sidebar Panel
 *
 * Renders a collapsible left sidebar with:
 *  - Tab bar: Terrain · Walls · Props
 *  - Terrain tab: paint/erase toggle, all 13 terrain types (grouped by family),
 *    brush-size slider with visual swatch preview
 *  - Walls tab: tool buttons with active state, straight-assist toggle
 *  - Props tab: filter chips, search, rotation control, 4-column asset grid
 *  - Sticky footer: Save & Clear buttons (Clear requires confirmation)
 *
 * State is kept locally and synced out through global function calls that
 * already exist in play.html (setEditorLayerMode, setEditorTerrain, etc.).
 */
(function () {
  'use strict';

  // ── Terrain palette (all 13 types) ───────────────────────────────────

  const TERRAIN_ENTRIES = [
    // Hardscape
    { id: 1,  key: 'stone',     label: 'Stone',       assetKey: 'stone',        family: 'hardscape' },
    { id: 6,  key: 'caveStone', label: 'Cave Stone',  assetKey: 'caveStone',    family: 'hardscape' },
    // Path
    { id: 2,  key: 'dirt',      label: 'Dirt / Road', assetKey: 'dirt',         family: 'path'      },
    // Biome
    { id: 3,  key: 'grass',     label: 'Grasslands',  assetKey: 'grass',        family: 'biome'     },
    { id: 5,  key: 'forest',    label: 'Forest',      assetKey: 'forestGround', family: 'biome'     },
    { id: 8,  key: 'hills',     label: 'Hills',       assetKey: 'hills',        family: 'biome'     },
    { id: 9,  key: 'mountains', label: 'Mountains',   assetKey: 'mountains',    family: 'biome'     },
    { id: 10, key: 'desert',    label: 'Desert Sand', assetKey: 'sand',         family: 'biome'     },
    { id: 11, key: 'swamp',     label: 'Swamp',       assetKey: 'swamp',        family: 'biome'     },
    { id: 12, key: 'snow',      label: 'Snow / Ice',  assetKey: 'snow',         family: 'biome'     },
    // Water
    { id: 4,  key: 'water',     label: 'Water',       assetKey: 'water',        family: 'water'     },
    { id: 7,  key: 'shallows',  label: 'Shallows',    assetKey: 'shallows',     family: 'water'     },
    // Hazard
    { id: 13, key: 'lava',      label: 'Lava',        assetKey: 'lava',         family: 'hazard'    },
  ];

  // Fallback colours when neither procedural canvas nor texture image loads
  const TERRAIN_FALLBACK = {
    hardscape: '#5a5868',
    biome:     '#3d6a30',
    water:     '#1e5a90',
    hazard:    '#7a2a18',
    path:      '#7a5a2c',
  };

  const WALL_TOOLS = [
    { id: 'segment', label: 'Segment',  title: 'Click once to start a wall, click again to place' },
    { id: 'room',    label: 'Room',     title: 'Click two corners to draw a four-wall room' },
    { id: 'door',    label: 'Door',     title: 'Click a wall segment to cut a door gap' },
    { id: 'opening', label: 'Opening',  title: 'Click a wall segment to cut an open gap' },
    { id: 'stamp',   label: 'Stamp',    title: 'Select a preset and stamp walls/doors/structures' },
  ];

  const PROP_FILTER_CHIPS = ['All', 'Walls', 'Furniture', 'Chest', 'Doors', 'Lighting', 'Store'];

  const SORT_OPTIONS = [
    { id: 'best',   label: 'Best Match'     },
    { id: 'az',     label: 'A – Z'          },
    { id: 'za',     label: 'Z – A'          },
    { id: 'recent', label: 'Recently Added' },
  ];

  // ── Panel state ────────────────────────────────────────────────────────

  let _state = {
    tab:         'terrain',
    terrain:     1,
    paintMode:   'paint',   // 'paint' | 'erase'
    brush:       1,
    wallTool:    'segment',
    stampPreset: '',
    wallAssist:  true,
    propFilter:  'All',
    propSearch:  '',
    propSort:    'best',
    propSize:    1,
    propRotation: 0,
    propPlacementMode: 'place',
    sortOpen:    false,
    sections: { terrain: true, brush: true, assets: true },
  };

  let _rootEl = null;

  // ─── Helpers ──────────────────────────────────────────────────────────

  function esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function call(fn, ...args) {
    if (typeof window[fn] === 'function') window[fn](...args);
  }


  function ensurePropHoverPreview() {
    let node = document.getElementById('ep-prop-hover-preview');
    if (!node) {
      node = document.createElement('div');
      node.id = 'ep-prop-hover-preview';
      node.setAttribute('aria-hidden', 'true');
      node.style.cssText = 'display:none;position:fixed;z-index:1200;pointer-events:none;width:min(280px, calc(100vw - 24px));padding:0.65rem;border-radius:14px;border:1px solid rgba(201,162,39,0.34);background:linear-gradient(180deg, rgba(8,12,16,0.98), rgba(12,18,24,0.96));box-shadow:0 24px 48px rgba(0,0,0,0.45);backdrop-filter:blur(5px);';
      node.innerHTML = '<div id="ep-prop-hover-preview-img" style="width:100%;height:176px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);background:#14181f center/contain no-repeat;"></div><div id="ep-prop-hover-preview-name" style="margin-top:0.52rem;font-size:0.82rem;font-weight:700;color:var(--ep-text);line-height:1.25;"></div><div id="ep-prop-hover-preview-meta" style="margin-top:0.22rem;font-size:0.64rem;color:var(--ep-text-dim);line-height:1.35;"></div>';
      document.body.appendChild(node);
    }
    return node;
  }

  function hidePropHoverPreview() {
    const node = document.getElementById('ep-prop-hover-preview');
    if (!node) return;
    node.style.display = 'none';
    node.setAttribute('aria-hidden', 'true');
  }

  function positionPropHoverPreview(evt) {
    const node = document.getElementById('ep-prop-hover-preview');
    if (!node || node.style.display === 'none') return;
    const margin = 12;
    const viewportW = window.innerWidth || 1280;
    const viewportH = window.innerHeight || 720;
    const x = Math.max(margin, Math.min((evt?.clientX || margin) + 18, viewportW - node.offsetWidth - margin));
    const y = Math.max(margin, Math.min((evt?.clientY || margin) + 18, viewportH - node.offsetHeight - margin));
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
  }

  function showPropHoverPreview(entry, evt) {
    if (!entry) return;
    const node = ensurePropHoverPreview();
    const img = document.getElementById('ep-prop-hover-preview-img');
    const name = document.getElementById('ep-prop-hover-preview-name');
    const meta = document.getElementById('ep-prop-hover-preview-meta');
    const url = String(entry.fileUrl || '').trim();
    if (img) {
      if (url) {
        img.style.backgroundImage = `url('${url.replace(/'/g, "\'")}')`;
        img.style.backgroundSize = 'contain';
      } else {
        img.style.backgroundImage = 'none';
      }
    }
    if (name) name.textContent = entry.label || entry.assetKey || 'Prop';
    if (meta) {
      const bits = [entry.family, entry.key, url ? 'Image asset' : 'Built-in prop'].filter(Boolean);
      meta.textContent = bits.join(' · ');
    }
    node.style.display = 'block';
    node.setAttribute('aria-hidden', 'false');
    positionPropHoverPreview(evt);
  }

  function attachAssetGridWheelScroll(gridEl) {
    if (!gridEl || gridEl.__epWheelBound) return;
    gridEl.__epWheelBound = true;
    gridEl.addEventListener('wheel', (evt) => {
      const maxScroll = Math.max(0, gridEl.scrollHeight - gridEl.clientHeight);
      if (maxScroll <= 0) return;
      const next = Math.max(0, Math.min(maxScroll, gridEl.scrollTop + evt.deltaY));
      if (next === gridEl.scrollTop) return;
      gridEl.scrollTop = next;
      evt.preventDefault();
      evt.stopPropagation();
    }, { passive: false });
  }

  function setPanelTab(tab, root = _rootEl) {
    if (!root) return;
    _state.tab = tab === 'walls' ? 'walls' : (tab === 'props' ? 'props' : 'terrain');
    root.querySelectorAll('.ep-tab').forEach((b) => {
      b.classList.toggle('ep-active', b.dataset.tab === _state.tab);
    });
    root.querySelectorAll('.ep-workspace-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.workspace === _state.tab);
    });
    const body = root.querySelector('.ep-body');
    if (!body) return;
    body.innerHTML = '';
    const tabContent =
      _state.tab === 'terrain' ? buildTerrainTab() :
      _state.tab === 'walls'   ? buildWallsTab()   :
      buildPropsTab();
    body.appendChild(tabContent);
    const layerMap = { terrain: 'terrain', walls: 'walls', props: 'props' };
    call('setEditorLayerMode', layerMap[_state.tab]);
    refreshEditorStatus();
  }

  function detectSessionMode() {
    try {
      const ctx = (typeof window._getCurrentMapContext === 'function')
        ? String(window._getCurrentMapContext() || 'world')
        : 'world';
      return ctx === 'world' ? 'Prep · World Map' : 'Live DM · Scene Map';
    } catch (_err) {
      return 'Prep · World Map';
    }
  }

  function refreshEditorStatus() {
    const status = document.getElementById('ep-status-strip');
    if (!status) return;
    const layerLabel = _state.tab === 'walls' ? 'Walls & Doors' : (_state.tab === 'props' ? 'Props' : 'Terrain');
    const modeLabel = _state.paintMode === 'erase' ? 'Erase' : 'Place';
    const brushLabel = _state.tab === 'props' ? `Size ${_state.propSize}` : `Brush ${_state.brush}`;
    status.innerHTML = `
      <span class="ep-status-pill ep-status-mode">${esc(detectSessionMode())}</span>
      <span class="ep-status-pill"><strong>Layer:</strong> ${esc(layerLabel)}</span>
      <span class="ep-status-pill"><strong>Tool:</strong> ${esc(modeLabel)}</span>
      <span class="ep-status-pill"><strong>Context:</strong> ${esc(brushLabel)}</span>
    `;
  }

  function openWorkspaceTarget(kind) {
    if (kind === 'terrain' || kind === 'walls' || kind === 'props') {
      setPanelTab(kind);
      return;
    }
    if (kind === 'fog') {
      call('toggleFlyout', 'flyout-fog');
      return;
    }
    if (kind === 'markers') {
      call('setTool', 'poi');
      return;
    }
    if (kind === 'tokens') {
      call('toggleFlyout', 'flyout-token');
      return;
    }
    if (kind === 'utilities') {
      call('toggleFlyout', 'flyout-map');
    }
  }

  function buildWorkspaceGrid() {
    const wrap = document.createElement('div');
    wrap.className = 'ep-workspace-grid';
    [
      { id: 'terrain', label: 'Terrain' },
      { id: 'props', label: 'Props' },
      { id: 'walls', label: 'Walls & Doors' },
      { id: 'fog', label: 'Fog' },
      { id: 'markers', label: 'Markers / POIs' },
      { id: 'tokens', label: 'Tokens' },
      { id: 'utilities', label: 'Utilities' },
    ].forEach((entry) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ep-workspace-btn' + ((_state.tab === entry.id) ? ' active' : '');
      btn.dataset.workspace = entry.id;
      btn.textContent = entry.label;
      btn.addEventListener('click', () => openWorkspaceTarget(entry.id));
      wrap.appendChild(btn);
    });
    return wrap;
  }

  // ─── Terrain thumbnail ────────────────────────────────────────────────

  /**
   * Returns a DOM element (img or canvas) for the terrain thumbnail.
   * Priority: actual texture image → procedural canvas → flat colour.
   */
  function terrainThumb(entry) {
    const texPath = window.EditorTerrainManifest
      ? window.EditorTerrainManifest.getTexturePath(entry.id)
      : null;

    if (texPath) {
      const img = document.createElement('img');
      img.className = 'ep-terrain-thumb';
      img.src = texPath;
      img.alt = entry.label;
      img.loading = 'eager';
      img.decoding = 'async';
      img.onerror = () => {
        // Try procedural canvas on image load failure
        const src = window.DndAssetInit && window.DndAssetInit.getDndAsset(entry.assetKey);
        const c = _makeThumbCanvas(src, entry.family);
        img.replaceWith(c);
      };
      return img;
    }

    const src = window.DndAssetInit && window.DndAssetInit.getDndAsset(entry.assetKey);
    return _makeThumbCanvas(src, entry.family);
  }

  function _makeThumbCanvas(src, family) {
    const c = document.createElement('canvas');
    c.className = 'ep-terrain-thumb';
    c.width = 44; c.height = 44;
    const g = c.getContext('2d');
    if (src) {
      g.drawImage(src, 0, 0, 44, 44);
      // Subtle inner vignette for depth
      const vignette = g.createRadialGradient(22, 22, 10, 22, 22, 26);
      vignette.addColorStop(0, 'rgba(0,0,0,0)');
      vignette.addColorStop(1, 'rgba(0,0,0,0.30)');
      g.fillStyle = vignette;
      g.fillRect(0, 0, 44, 44);
    } else {
      g.fillStyle = TERRAIN_FALLBACK[family] || '#3a3a4a';
      g.fillRect(0, 0, 44, 44);
    }
    return c;
  }

  // ─── Prop thumbnail ───────────────────────────────────────────────────

  function propThumb(assetKey, fileUrl) {
    if (fileUrl) {
      const img = document.createElement('img');
      img.src = fileUrl;
      img.alt = assetKey;
      img.style.cssText = 'width:80%;height:80%;object-fit:contain;display:block;';
      return img;
    }
    const c = document.createElement('canvas');
    c.width = 56; c.height = 56;
    const src = window.DndAssetInit && window.DndAssetInit.getDndAsset(assetKey);
    if (src) {
      const g = c.getContext('2d');
      const scale = Math.min(56 / src.width, 56 / src.height) * 0.80;
      const dw = src.width * scale, dh = src.height * scale;
      g.drawImage(src, (56 - dw) / 2, (56 - dh) / 2, dw, dh);
    }
    return c;
  }

  // ─── Prop entries ─────────────────────────────────────────────────────


  function getPropReplacementKey(entry = {}) {
    const assetKey = String(entry.assetKey || '').toLowerCase();
    const label = String(entry.label || '').toLowerCase();
    const tags = Array.isArray(entry.tags) ? entry.tags.map((tag) => String(tag).toLowerCase()) : [];
    const haystack = `${assetKey} ${label} ${tags.join(' ')}`;
    if (/\bmimic\b/.test(haystack)) return 'mimic';
    if (/guild[_ -]?board|quest[_ -]?board/.test(haystack)) return 'guild_board';
    if (/shop[_ -]?stall|shop[_ -]?front|market[_ -]?stall|\bmerchant\b|\bstore\b|\bshop\b/.test(haystack)) return 'shop';
    if (/bookshelf|bookcase/.test(haystack)) return 'bookshelf';
    if (/\bchest\b/.test(haystack)) return 'chest';
    if (/\bbarrel\b/.test(haystack)) return 'barrel';
    if (/\bcrate\b/.test(haystack)) return 'crate';
    if (/\btable\b/.test(haystack)) return 'table';
    if (/\btorch\b/.test(haystack)) return 'torch';
    if (/\bcampfire\b/.test(haystack)) return 'campfire';
    if (/\bdoor\b/.test(haystack)) return 'door';
    return assetKey.replace(/^prop_/, '');
  }

  function getPropEntries() {
    const seen = new Set();
    const merged = [];
    const pushEntry = (entry) => {
      if (!entry || typeof entry !== 'object') return;
      const key = String(entry.assetKey || '').trim();
      if (!key || seen.has(key)) return;
      seen.add(key);
      merged.push(entry);
    };

    const fileReplacementKeys = new Set();
    if (window.AppEditorAssets) {
      const fileEntries = window.AppEditorAssets.getEntries({ category: 'props' });
      if (fileEntries.length > 0) {
        fileEntries.forEach((e) => {
          const entry = {
            assetKey: e.id,
            label: e.name || e.id,
            tags: Array.isArray(e.tags) ? e.tags : [],
            fileUrl: e.thumbnail || e.file || '',
            addedAt: e.added_at || 0,
          };
          pushEntry(entry);
          if (entry.fileUrl) fileReplacementKeys.add(getPropReplacementKey(entry));
        });
      }
    }

    const manifest = window.DndAssets && window.DndAssets.assetManifest;
    if (manifest && Array.isArray(manifest.props)) {
      manifest.props.forEach((e, i) => {
        const entry = {
          assetKey: e.id,
          label: e.label,
          tags: e.tags || [],
          fileUrl: '',
          addedAt: i,
        };
        if (fileReplacementKeys.has(getPropReplacementKey(entry))) return;
        pushEntry(entry);
      });
    }
    return merged;
  }

  function filterProps(entries) {
    const { propFilter, propSearch, propSort } = _state;
    let result = entries.slice();

    if (propFilter !== 'All') {
      const f = propFilter.toLowerCase();
      result = result.filter(e =>
        e.tags.some(t => t.toLowerCase().includes(f)) ||
        e.label.toLowerCase().includes(f)
      );
    }

    if (propSearch) {
      const q = propSearch.toLowerCase();
      result = result.filter(e =>
        e.label.toLowerCase().includes(q) ||
        e.assetKey.toLowerCase().includes(q) ||
        e.tags.some(t => t.toLowerCase().includes(q))
      );
    }

    if (propSort === 'az')     result.sort((a, b) => a.label.localeCompare(b.label));
    else if (propSort === 'za')result.sort((a, b) => b.label.localeCompare(a.label));
    else if (propSort === 'recent') result.sort((a, b) => b.addedAt - a.addedAt);

    return result;
  }

  // ─── Section collapse helper ──────────────────────────────────────────

  function makeSectionHeader(label, key) {
    const header = document.createElement('div');
    header.className = 'ep-section-header' + (_state.sections[key] ? '' : ' collapsed');
    header.innerHTML = `<span>${esc(label)}</span><span class="ep-chevron">▾</span>`;
    header.addEventListener('click', () => {
      _state.sections[key] = !_state.sections[key];
      header.classList.toggle('collapsed', !_state.sections[key]);
      const body = header.nextElementSibling;
      if (body) body.style.display = _state.sections[key] ? (body.dataset.openDisplay || '') : 'none';
    });
    return header;
  }

  // ─── Terrain tab ──────────────────────────────────────────────────────

  function buildTerrainTab() {
    const frag = document.createDocumentFragment();

    // Paint / Erase toggle (IDs match AppEditorState.setEditorMode targets)
    const modeRow = document.createElement('div');
    modeRow.className = 'ep-mode-row';
    [
      { id: 'editor-tool-paint', value: 'paint', label: '✏ Paint' },
      { id: 'editor-tool-erase', value: 'erase', label: '✕ Erase' },
    ].forEach(m => {
      const btn = document.createElement('button');
      btn.id = m.id;
      btn.className = 'ep-mode-btn' +
        (m.value === 'erase' ? ' ep-mode-erase' : '') +
        (_state.paintMode === m.value ? ' ep-mode-active' : '');
      btn.textContent = m.label;
      btn.title = m.value === 'paint'
        ? 'Paint selected terrain onto the map (P)'
        : 'Erase terrain cells (E)';
      btn.dataset.mode = m.value;
      btn.addEventListener('click', () => {
        _state.paintMode = m.value;
        modeRow.querySelectorAll('.ep-mode-btn').forEach(b =>
          b.classList.toggle('ep-mode-active', b.dataset.mode === m.value)
        );
        call('setEditorMode', m.value);
      });
      modeRow.appendChild(btn);
    });
    frag.appendChild(modeRow);

    // Terrain section
    const th = makeSectionHeader('Terrain Type', 'terrain');
    frag.appendChild(th);
    const terrainBody = document.createElement('div');
    terrainBody.className = 'ep-section-body';
    terrainBody.style.display = _state.sections.terrain ? '' : 'none';

    const grid = document.createElement('div');
    grid.className = 'ep-terrain-grid';

    TERRAIN_ENTRIES.forEach(entry => {
      const card = document.createElement('div');
      card.className = 'ep-terrain-card' + (_state.terrain === entry.id ? ' ep-selected' : '');
      card.dataset.tid    = entry.id;
      card.dataset.family = entry.family;
      card.title = entry.label + ' — ' + entry.family;

      const thumb = terrainThumb(entry);
      const nameEl = document.createElement('span');
      nameEl.className = 'ep-terrain-name';
      nameEl.textContent = entry.label;

      card.appendChild(thumb);
      card.appendChild(nameEl);

      card.addEventListener('click', () => {
        _state.terrain = entry.id;
        grid.querySelectorAll('.ep-terrain-card').forEach(c =>
          c.classList.toggle('ep-selected', Number(c.dataset.tid) === entry.id)
        );
        call('setEditorTerrain', entry.id);
      });

      grid.appendChild(card);
    });

    terrainBody.appendChild(grid);
    frag.appendChild(terrainBody);

    // Brush section
    const bh = makeSectionHeader('Brush Size', 'brush');
    frag.appendChild(bh);
    const brushBody = document.createElement('div');
    brushBody.className = 'ep-section-body';
    brushBody.style.display = _state.sections.brush ? '' : 'none';

    const brushRow = document.createElement('div');
    brushRow.className = 'ep-brush-row';
    brushRow.innerHTML = `
      <span class="ep-brush-label">Size</span>
      <input id="editor-brush-size" class="ep-brush-slider" type="range" min="1" max="12" value="${esc(_state.brush)}" />
      <span id="editor-brush-val" class="ep-brush-val">${esc(_state.brush)}</span>
    `;
    const slider = brushRow.querySelector('input');
    slider.addEventListener('input', e => {
      _state.brush = Number(e.target.value);
      brushRow.querySelector('.ep-brush-val').textContent = _state.brush;
      _updateBrushSwatch(swatchEl, _state.brush);
      call('setEditorBrush', _state.brush);
    });
    brushBody.appendChild(brushRow);

    // Brush size visual swatch
    const swatchWrap = document.createElement('div');
    swatchWrap.className = 'ep-brush-preview';
    const swatchEl = document.createElement('div');
    swatchEl.className = 'ep-brush-swatch';
    _updateBrushSwatch(swatchEl, _state.brush);
    swatchWrap.appendChild(swatchEl);
    brushBody.appendChild(swatchWrap);

    frag.appendChild(brushBody);
    return frag;
  }

  /** Update the visual brush swatch to reflect current brush size. */
  function _updateBrushSwatch(el, brushSize) {
    const sz = Math.max(8, Math.min(72, brushSize * 8));
    el.style.width  = sz + 'px';
    el.style.height = sz + 'px';
  }

  // ─── Walls tab ────────────────────────────────────────────────────────

  function buildWallsTab() {
    const frag = document.createDocumentFragment();

    // Wall tool section
    const th = makeSectionHeader('Wall Tool', 'wallTools');
    frag.appendChild(th);

    const grid = document.createElement('div');
    grid.className = 'ep-wall-grid';

    WALL_TOOLS.forEach(t => {
      const btn = document.createElement('button');
      // Use the legacy IDs so AppEditorState.setEditorWallTool can update .active directly
      btn.id = `editor-wall-tool-${t.id}`;
      btn.className = 'ep-wall-btn' + (_state.wallTool === t.id ? ' active' : '');
      btn.textContent = t.label;
      btn.title = t.title;
      btn.dataset.wallTool = t.id;
      btn.addEventListener('click', () => {
        _state.wallTool = t.id;
        grid.querySelectorAll('.ep-wall-btn').forEach(b =>
          b.classList.toggle('active', b.dataset.wallTool === t.id)
        );
        call('setEditorWallTool', t.id);
      });
      grid.appendChild(btn);
    });

    frag.appendChild(grid);

    const stampPresets = (window.EditorStampPresets && typeof window.EditorStampPresets.list === 'function')
      ? window.EditorStampPresets.list()
      : [];
    if (stampPresets.length) {
      const byCategory = new Map();
      stampPresets.forEach((preset) => {
        const key = String(preset.category || 'Misc');
        if (!byCategory.has(key)) byCategory.set(key, []);
        byCategory.get(key).push(preset);
      });
      const stampWrap = document.createElement('div');
      stampWrap.className = 'ep-stamp-wrap';
      const hint = document.createElement('div');
      hint.className = 'ep-wall-note';
      hint.textContent = 'Stamp workflow: select preset → ghost preview follows cursor → click to place. Esc or right-click cancels.';
      stampWrap.appendChild(hint);
      byCategory.forEach((entries, category) => {
        const sub = document.createElement('details');
        sub.className = 'ep-collapsible';
        sub.open = category === 'Rooms';
        const summary = document.createElement('summary');
        summary.textContent = category;
        sub.appendChild(summary);
        const body = document.createElement('div');
        body.className = 'ep-collapsible-body';
        const stampGrid = document.createElement('div');
        stampGrid.className = 'ep-stamp-grid';
        entries.forEach((preset) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'ep-stamp-btn' + (_state.stampPreset === preset.id ? ' active' : '');
          btn.dataset.stampPreset = preset.id;
          btn.innerHTML = `<span class="ep-stamp-name">${esc(preset.name)}</span><span class="ep-stamp-meta">${esc((preset.widthCells || 1) + '×' + (preset.heightCells || 1))}</span>`;
          btn.addEventListener('click', () => {
            _state.stampPreset = preset.id;
            _state.wallTool = 'stamp';
            call('setEditorWallStampPreset', preset.id);
            call('setEditorWallTool', 'stamp');
            stampGrid.querySelectorAll('.ep-stamp-btn').forEach((node) =>
              node.classList.toggle('active', node.dataset.stampPreset === preset.id)
            );
            grid.querySelectorAll('.ep-wall-btn').forEach((node) =>
              node.classList.toggle('active', node.dataset.wallTool === 'stamp')
            );
          });
          stampGrid.appendChild(btn);
        });
        body.appendChild(stampGrid);
        sub.appendChild(body);
        stampWrap.appendChild(sub);
      });
      frag.appendChild(stampWrap);
    }

    // Straight-assist + wall-mode guidance (collapsed by default on mobile)
    const advanced = document.createElement('details');
    advanced.className = 'ep-collapsible';
    if (!window.matchMedia('(max-width: 900px)').matches) advanced.open = true;
    const advancedSummary = document.createElement('summary');
    advancedSummary.textContent = 'Advanced Wall Options';
    advanced.appendChild(advancedSummary);
    const advancedBody = document.createElement('div');
    advancedBody.className = 'ep-collapsible-body';

    // Straight-assist toggle
    const assistRow = document.createElement('label');
    assistRow.className = 'ep-assist-row';
    assistRow.title = 'Constrain new wall segments to horizontal or vertical lines';
    const assistCb = document.createElement('input');
    assistCb.type = 'checkbox';
    assistCb.id = 'editor-wall-straight-assist';
    assistCb.checked = _state.wallAssist;
    assistCb.addEventListener('change', e => {
      _state.wallAssist = e.target.checked;
      call('setEditorWallStraightAssist', e.target.checked);
    });
    const assistLabel = document.createElement('span');
    assistLabel.className = 'ep-assist-label';
    assistLabel.textContent = 'Straight Assist';
    const kbdHint = document.createElement('span');
    kbdHint.className = 'ep-kbd';
    kbdHint.textContent = 'Shift';
    assistRow.appendChild(assistCb);
    assistRow.appendChild(assistLabel);
    assistRow.appendChild(kbdHint);
    advancedBody.appendChild(assistRow);

    // Mode note (updated by AppEditorState.setEditorWallTool via legacy id)
    const note = document.createElement('div');
    note.id = 'editor-wall-mode-note';
    note.className = 'ep-wall-note';
    note.textContent = 'Segment mode: click once to start a wall, then click again to finish.';
    advancedBody.appendChild(note);
    advanced.appendChild(advancedBody);
    frag.appendChild(advanced);

    // Paint / Erase toggle for walls (erase mode deletes hovered wall)
    const modeRow = document.createElement('div');
    modeRow.className = 'ep-mode-row';
    [
      { id: 'editor-tool-paint', value: 'paint', label: '✏ Place' },
      { id: 'editor-tool-erase', value: 'erase', label: '✕ Erase' },
    ].forEach(m => {
      const btn = document.createElement('button');
      btn.className = 'ep-mode-btn' +
        (m.value === 'erase' ? ' ep-mode-erase' : '') +
        (_state.paintMode === m.value ? ' ep-mode-active' : '');
      btn.textContent = m.label;
      btn.dataset.mode = m.value;
      btn.addEventListener('click', () => {
        _state.paintMode = m.value;
        modeRow.querySelectorAll('.ep-mode-btn').forEach(b =>
          b.classList.toggle('ep-mode-active', b.dataset.mode === m.value)
        );
        call('setEditorMode', m.value);
      });
      modeRow.appendChild(btn);
    });
    frag.appendChild(modeRow);

    const doorNote = document.createElement('div');
    doorNote.className = 'ep-wall-door-note';
    doorNote.innerHTML = '<strong>Door state:</strong> click a placed door prop on the map to Open/Close or Lock/Unlock.';
    frag.appendChild(doorNote);

    return frag;
  }

  // ─── Props tab ────────────────────────────────────────────────────────

  function buildPropsTab() {
    const frag = document.createDocumentFragment();

    const placementRow = document.createElement('div');
    placementRow.className = 'ep-placement-row';
    [
      { id: 'place', label: 'Place', onClick: () => { _state.propPlacementMode = 'place'; _state.paintMode = 'paint'; call('setEditorLayerMode', 'props'); call('setEditorMode', 'paint'); setPanelTab('props'); } },
      { id: 'move', label: 'Move', onClick: () => { _state.propPlacementMode = 'move'; _state.paintMode = 'paint'; call('setEditorLayerMode', 'props'); call('setEditorMode', 'paint'); call('setTool', 'select'); refreshEditorStatus(); } },
      { id: 'delete', label: 'Delete', onClick: () => { _state.propPlacementMode = 'delete'; _state.paintMode = 'erase'; call('setEditorLayerMode', 'props'); call('setEditorMode', 'erase'); refreshEditorStatus(); } },
    ].forEach((entry) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ep-placement-btn' + (_state.propPlacementMode === entry.id ? ' active' : '');
      btn.dataset.placeMode = entry.id;
      btn.textContent = entry.label;
      btn.addEventListener('click', () => {
        entry.onClick();
        placementRow.querySelectorAll('.ep-placement-btn').forEach((node) => {
          node.classList.toggle('active', node.dataset.placeMode === entry.id);
        });
      });
      placementRow.appendChild(btn);
    });
    frag.appendChild(placementRow);

    // Search
    const searchEl = document.createElement('input');
    searchEl.type = 'search';
    searchEl.className = 'ep-search';
    searchEl.placeholder = '🔍 Search props…';
    searchEl.value = _state.propSearch;
    searchEl.addEventListener('input', e => {
      _state.propSearch = e.target.value;
      refreshAssetGrid(assetGridEl);
    });
    frag.appendChild(searchEl);

    // Filter chips + sort button row
    const filterWrap = document.createElement('div');
    filterWrap.style.cssText = 'display:flex;align-items:center;gap:5px;flex-wrap:wrap;';

    const chipRow = document.createElement('div');
    chipRow.className = 'ep-filter-row';
    chipRow.style.flex = '1';

    PROP_FILTER_CHIPS.forEach(chip => {
      const chipEl = document.createElement('button');
      chipEl.className = 'ep-chip' + (_state.propFilter === chip ? ' ep-chip-active' : '');
      chipEl.textContent = chip;
      chipEl.dataset.chip = chip;
      chipEl.addEventListener('click', () => {
        _state.propFilter = chip;
        chipRow.querySelectorAll('.ep-chip').forEach(c =>
          c.classList.toggle('ep-chip-active', c.dataset.chip === chip)
        );
        refreshAssetGrid(assetGridEl);
      });
      chipRow.appendChild(chipEl);
    });
    filterWrap.appendChild(chipRow);

    // Sort popover
    const sortWrap = document.createElement('div');
    sortWrap.className = 'ep-sort-wrap';
    const sortBtn = document.createElement('button');
    sortBtn.className = 'ep-sort-btn';
    sortBtn.textContent = '⇅ Sort';
    const sortPop = document.createElement('div');
    sortPop.className = 'ep-sort-popover' + (_state.sortOpen ? ' ep-open' : '');
    SORT_OPTIONS.forEach(opt => {
      const optEl = document.createElement('div');
      optEl.className = 'ep-sort-option' + (_state.propSort === opt.id ? ' ep-sort-active' : '');
      optEl.textContent = opt.label;
      optEl.addEventListener('click', () => {
        _state.propSort = opt.id;
        _state.sortOpen = false;
        sortPop.classList.remove('ep-open');
        sortPop.querySelectorAll('.ep-sort-option').forEach(o =>
          o.classList.toggle('ep-sort-active', o === optEl)
        );
        refreshAssetGrid(assetGridEl);
      });
      sortPop.appendChild(optEl);
    });
    sortBtn.addEventListener('click', e => {
      e.stopPropagation();
      _state.sortOpen = !_state.sortOpen;
      sortPop.classList.toggle('ep-open', _state.sortOpen);
    });
    document.addEventListener('click', () => {
      if (_state.sortOpen) { _state.sortOpen = false; sortPop.classList.remove('ep-open'); }
    }, { capture: true, passive: true });
    sortWrap.appendChild(sortBtn);
    sortWrap.appendChild(sortPop);
    filterWrap.appendChild(sortWrap);
    frag.appendChild(filterWrap);

    // Prop size slider
    const sizeRow = document.createElement('div');
    sizeRow.className = 'ep-brush-row';
    sizeRow.innerHTML = `
      <span class="ep-brush-label">Prop Size</span>
      <input class="ep-brush-slider" type="range" min="1" max="4" value="${esc(_state.propSize)}" />
      <span class="ep-brush-val">${esc(_state.propSize)}</span>
    `;
    sizeRow.querySelector('input').addEventListener('input', e => {
      _state.propSize = Number(e.target.value);
      sizeRow.querySelector('.ep-brush-val').textContent = _state.propSize;
      call('setEditorPropSize', _state.propSize);
    });
    frag.appendChild(sizeRow);

    // Rotation stepper
    const rotRow = document.createElement('div');
    rotRow.className = 'ep-rotation-row';

    const rotLabel = document.createElement('span');
    rotLabel.className = 'ep-rotation-label';
    rotLabel.textContent = 'Rotation';

    const rotCCW = document.createElement('button');
    rotCCW.className = 'ep-rotation-btn';
    rotCCW.title = 'Rotate 90° counter-clockwise';
    rotCCW.textContent = '↺';

    const rotVal = document.createElement('span');
    rotVal.id = 'editor-prop-rotation-val';
    rotVal.className = 'ep-rotation-val';
    rotVal.textContent = _state.propRotation + '°';

    const rotCW = document.createElement('button');
    rotCW.className = 'ep-rotation-btn';
    rotCW.title = 'Rotate 90° clockwise';
    rotCW.textContent = '↻';

    rotCCW.addEventListener('click', () => {
      _state.propRotation = ((_state.propRotation - 90) + 360) % 360;
      rotVal.textContent = _state.propRotation + '°';
      call('setEditorPropRotation', _state.propRotation);
    });
    rotCW.addEventListener('click', () => {
      _state.propRotation = (_state.propRotation + 90) % 360;
      rotVal.textContent = _state.propRotation + '°';
      call('setEditorPropRotation', _state.propRotation);
    });

    rotRow.appendChild(rotLabel);
    rotRow.appendChild(rotCCW);
    rotRow.appendChild(rotVal);
    rotRow.appendChild(rotCW);
    frag.appendChild(rotRow);

    frag.appendChild(document.createElement('div')).className = 'ep-divider';

    // Asset library section
    const ah = makeSectionHeader('Asset Library', 'assets');
    frag.appendChild(ah);
    const assetsBody = document.createElement('div');
    assetsBody.className = 'ep-section-body';
    assetsBody.dataset.openDisplay = 'flex';
    assetsBody.style.display = _state.sections.assets ? 'flex' : 'none';
    assetsBody.style.flexDirection = 'column';
    assetsBody.style.minHeight = '0';

    const assetGridEl = document.createElement('div');
    assetGridEl.className = 'ep-asset-grid';
    assetGridEl.title = 'Scroll here to browse more props';
    attachAssetGridWheelScroll(assetGridEl);
    refreshAssetGrid(assetGridEl);
    assetsBody.appendChild(assetGridEl);

    // Import button
    const importBtn = document.createElement('button');
    importBtn.className = 'ep-import-btn';
    importBtn.style.marginTop = '6px';
    importBtn.textContent = '⬆ Import Asset';
    importBtn.addEventListener('click', () => {
      const fileInput = document.getElementById('editor-asset-import-file');
      if (fileInput) {
        const onFileChosen = () => {
          fileInput.removeEventListener('change', onFileChosen);
          // Defer click so the `change` handler in asset_library.js (stageImportFile)
          // finishes updating preview and form state before the upload is triggered.
          setTimeout(() => {
            const uploadBtn = document.getElementById('editor-asset-import-upload');
            if (uploadBtn) uploadBtn.click();
          }, 80);
        };
        fileInput.addEventListener('change', onFileChosen);
        fileInput.click();
        return;
      }
      call('openEditorAssetImport');
    });
    assetsBody.appendChild(importBtn);
    frag.appendChild(assetsBody);

    return frag;
  }

  function refreshAssetGrid(gridEl) {
    hidePropHoverPreview();
    gridEl.innerHTML = '';
    const all     = getPropEntries();
    const visible = filterProps(all);

    if (visible.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'ep-empty-state';
      const icon = document.createElement('div');
      icon.className = 'ep-empty-state-icon';
      icon.textContent = all.length === 0 ? '📦' : '🔍';
      const msg = document.createElement('div');
      msg.textContent = all.length === 0
        ? 'No assets loaded yet'
        : 'No props match your search';
      empty.appendChild(icon);
      empty.appendChild(msg);
      gridEl.appendChild(empty);
      return;
    }

    visible.forEach(entry => {
      const card = document.createElement('div');
      card.className = 'ep-asset-card';
      const thumb = propThumb(entry.assetKey, entry.fileUrl || '');
      card.appendChild(thumb);
      const name = document.createElement('span');
      name.className = 'ep-asset-name';
      name.textContent = entry.label;
      card.appendChild(name);
      card.title = `${entry.label} · hover to preview larger`;
      card.addEventListener('mouseenter', (evt) => showPropHoverPreview(entry, evt));
      card.addEventListener('mousemove', positionPropHoverPreview);
      card.addEventListener('mouseleave', hidePropHoverPreview);
      card.addEventListener('focus', () => showPropHoverPreview(entry, { clientX: window.innerWidth * 0.5, clientY: window.innerHeight * 0.3 }));
      card.addEventListener('blur', hidePropHoverPreview);
      card.addEventListener('click', () => {
        if (entry.fileUrl) {
          call('setEditorFileAsset', entry.assetKey);
        } else {
          call('setEditorDndPropAsset', entry.assetKey);
        }
        gridEl.querySelectorAll('.ep-asset-card').forEach(c => c.classList.remove('ep-selected'));
        card.classList.add('ep-selected');
      });
      gridEl.appendChild(card);
    });
  }

  // ─── Panel render ─────────────────────────────────────────────────────

  function buildPanel() {
    const root = document.createElement('div');
    root.id = 'editor-panel-root';

    // Compact header
    const header = document.createElement('div');
    header.className = 'ep-header';
    const title = document.createElement('div');
    title.className = 'ep-header-title';
    title.textContent = 'Map Editor';

    // Unsaved indicator (hidden by default)
    const unsavedDot = document.createElement('span');
    unsavedDot.id = 'ep-unsaved-dot';
    unsavedDot.className = 'ep-unsaved-dot';
    unsavedDot.style.display = 'none';
    unsavedDot.title = 'Unsaved changes';
    header.appendChild(title);
    header.appendChild(unsavedDot);
    root.appendChild(header);

    root.appendChild(buildWorkspaceGrid());

    const statusStrip = document.createElement('div');
    statusStrip.id = 'ep-status-strip';
    statusStrip.className = 'ep-status-strip';
    root.appendChild(statusStrip);

    // Tab bar
    const tabBar = document.createElement('div');
    tabBar.className = 'ep-tab-bar';
    [
      { id: 'terrain', label: 'Terrain' },
      { id: 'walls',   label: 'Walls'   },
      { id: 'props',   label: 'Props'   },
    ].forEach(t => {
      const btn = document.createElement('button');
      btn.id = `editor-layer-${t.id}`;   // legacy ID for AppEditorState.setEditorLayerMode
      btn.className = 'ep-tab' + (_state.tab === t.id ? ' ep-active' : '');
      btn.textContent = t.label;
      btn.dataset.tab = t.id;
      btn.addEventListener('click', () => setPanelTab(t.id, root));
      tabBar.appendChild(btn);
    });
    root.appendChild(tabBar);

    // Tab-bottom border strip (visual connector between tabs and body)
    const strip = document.createElement('div');
    strip.className = 'ep-tab-strip';
    root.appendChild(strip);

    // Scrollable body
    const body = document.createElement('div');
    body.className = 'ep-body';
    body.id = 'ep-body';
    const tabContent =
      _state.tab === 'terrain' ? buildTerrainTab() :
      _state.tab === 'walls'   ? buildWallsTab()   :
      buildPropsTab();
    body.appendChild(tabContent);
    root.appendChild(body);

    // Sticky footer
    const footer = document.createElement('div');
    footer.className = 'ep-footer';
    footer.innerHTML = `
      <button class="ep-footer-btn ep-save"  id="ep-save-btn"  title="Save map changes (Ctrl+S)">💾 Save</button>
      <button class="ep-footer-btn ep-clear" id="ep-clear-btn" title="Clear active layer">🗑 Clear</button>
    `;
    footer.querySelector('#ep-save-btn').addEventListener('click', () => {
      call('saveEditorMap');
      // Hide unsaved dot
      const dot = document.getElementById('ep-unsaved-dot');
      if (dot) dot.style.display = 'none';
    });
    footer.querySelector('#ep-clear-btn').addEventListener('click', () => {
      const layer = _state.tab;
      const confirmed = window.confirm(
        `Clear all ${layer} from the current map?\n\nThis cannot be undone.`
      );
      if (confirmed) call('clearEditorMap');
    });
    root.appendChild(footer);
    refreshEditorStatus();

    return root;
  }

  // ─── Public API ───────────────────────────────────────────────────────

  /**
   * Mount the editor panel into the DOM. Safe to call multiple times.
   * @param {HTMLElement} [container] - parent element; defaults to document.body
   */
  function mountEditorPanel(container) {
    const parent = container || document.body;
    const existing = document.getElementById('editor-panel-root');
    if (existing) existing.remove();
    _rootEl = buildPanel();
    parent.appendChild(_rootEl);
  }

  /**
   * Sync panel state from current editor globals (call after external changes).
   * Only rebuilds the body content, not the entire panel.
   */
  function syncEditorPanel() {
    if (typeof window.editorTerrain === 'number')    _state.terrain  = window.editorTerrain;
    if (typeof window.editorBrush   === 'number')    _state.brush    = window.editorBrush;
    if (typeof window.editorPropSize === 'number')   _state.propSize = window.editorPropSize;
    if (typeof window.editorPropRotation === 'number') _state.propRotation = window.editorPropRotation;
    if (typeof window.editorPaintMode === 'string')  _state.paintMode = window.editorPaintMode;
    if (typeof window.editorWallTool  === 'string')  _state.wallTool  = window.editorWallTool;
    if (typeof window.editorWallStampPresetId === 'string') _state.stampPreset = window.editorWallStampPresetId;
    if (typeof window.editorActiveLayer === 'string') {
      const l = window.editorActiveLayer;
      _state.tab = l === 'walls' ? 'walls' : (l === 'props' || l === 'images') ? 'props' : 'terrain';
    }
    if (!_rootEl || !_rootEl.parentNode) return;
    // Rebuild tab body only to preserve scroll position
    const body = _rootEl.querySelector('.ep-body');
    if (!body) return;
    body.innerHTML = '';
    const tabContent =
      _state.tab === 'terrain' ? buildTerrainTab() :
      _state.tab === 'walls'   ? buildWallsTab()   :
      buildPropsTab();
    body.appendChild(tabContent);
    // Sync tab active class
    _rootEl.querySelectorAll('.ep-tab').forEach(b =>
      b.classList.toggle('ep-active', b.dataset.tab === _state.tab)
    );
    _rootEl.querySelectorAll('.ep-workspace-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.workspace === _state.tab);
    });
    refreshEditorStatus();
  }

  /**
   * Mark the map as having unsaved changes (shows pulsing dot in header).
   */
  function markUnsaved() {
    const dot = document.getElementById('ep-unsaved-dot');
    if (dot) dot.style.display = 'inline-block';
  }

  window.EditorPanel = Object.freeze({ mountEditorPanel, syncEditorPanel, markUnsaved });

  // Re-render asset grid when the manifest loads
  if (window.AppEditorAssets && typeof window.AppEditorAssets.subscribe === 'function') {
    window.AppEditorAssets.subscribe(() => {
      if (_state.tab === 'props' && _rootEl) {
        const gridEl = _rootEl.querySelector('.ep-asset-grid');
        if (gridEl) refreshAssetGrid(gridEl);
      }
    });
  }
})();
