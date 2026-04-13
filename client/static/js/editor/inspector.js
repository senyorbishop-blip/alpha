/**
 * inspector.js
 * Selected-object inspector panel (fixed, bottom-right).
 *
 * Renders context-sensitive property fields for the currently selected
 * token, prop, VFX marker, or POI.
 *
 * Changes from v1:
 *  - Reduced polling from 350 ms → 120 ms; rebuild only when selection key changes.
 *  - Exposed AppEditorInspector.refresh() for call-site push updates.
 *  - Inspector visibility is suppressed when the panel container is hidden.
 *  - Improved layout: two-column grids for compact fields, consistent row style.
 *  - Save button title / keyboard hint.
 */
(function () {
  'use strict';

  /* ── Helpers ─────────────────────────────────────────────────────────── */

  function el(id)   { return document.getElementById(id); }

  function clamp(n, min, max, fb) {
    const v = Number(n);
    return Number.isFinite(v) ? Math.max(min, Math.min(max, v)) : fb;
  }

  /* ── Panel DOM creation ──────────────────────────────────────────────── */

  function ensurePanel() {
    let panel = el('selected-object-inspector');
    if (panel) return panel;

    panel = document.createElement('div');
    panel.id = 'selected-object-inspector';
    Object.assign(panel.style, {
      position:        'fixed',
      right:           '18px',
      bottom:          '18px',
      width:           '300px',
      maxWidth:        'calc(100vw - 32px)',
      zIndex:          '2500',
      background:      'linear-gradient(180deg, rgba(18,21,14,0.97), rgba(12,14,9,0.97))',
      border:          '1px solid rgba(92,63,24,0.55)',
      borderRadius:    '12px',
      boxShadow:       '0 16px 42px rgba(0,0,0,0.55), 0 0 0 1px rgba(201,162,39,0.10) inset',
      color:           'var(--ep-text, #ddd0b8)',
      fontFamily:      'inherit',
      fontSize:        '13px',
      display:         'none',
      overflow:        'hidden',
    });

    panel.innerHTML = `
      <div id="soi-header" style="
        padding:0.75rem 0.9rem 0.65rem;
        background:rgba(0,0,0,0.22);
        border-bottom:1px solid rgba(92,63,24,0.40);
        display:flex;align-items:center;justify-content:space-between;gap:0.5rem;">
        <div>
          <div style="font-family:'Cinzel','Georgia',serif;font-size:0.60rem;letter-spacing:0.14em;
                      text-transform:uppercase;color:rgba(201,162,39,0.72);">Selected</div>
          <div id="selected-object-inspector-title"
               style="font-weight:700;font-size:0.88rem;color:var(--ep-text,#ddd0b8);"></div>
        </div>
        <button id="selected-object-inspector-hide" title="Close inspector"
                style="appearance:none;background:transparent;border:none;
                       color:rgba(160,144,112,0.7);cursor:pointer;font-size:1rem;
                       padding:4px 6px;border-radius:6px;line-height:1;
                       transition:color 0.14s,background 0.14s;"
                onmouseover="this.style.color='#ddd0b8';this.style.background='rgba(255,255,255,0.06)'"
                onmouseout="this.style.color='rgba(160,144,112,0.7)';this.style.background='transparent'">
          ✕
        </button>
      </div>
      <div id="selected-object-inspector-body"
           style="padding:0.85rem 0.9rem;display:grid;gap:0.60rem;"></div>
      <div style="padding:0 0.9rem 0.85rem;display:flex;justify-content:flex-end;gap:0.5rem;">
        <button id="selected-object-inspector-save"
                title="Save changes (Enter)"
                style="
                  appearance:none;padding:0.50rem 0.85rem;min-width:100px;
                  background:rgba(201,162,39,0.16);
                  border:1px solid rgba(201,162,39,0.42);
                  border-radius:8px;color:#c9a227;font-size:0.80rem;font-weight:700;
                  cursor:pointer;letter-spacing:0.03em;
                  transition:background 0.14s,border-color 0.14s;"
                onmouseover="this.style.background='rgba(201,162,39,0.28)'"
                onmouseout="this.style.background='rgba(201,162,39,0.16)'">
          Save Changes
        </button>
      </div>`;

    document.body.appendChild(panel);

    el('selected-object-inspector-hide').addEventListener('click', () => {
      panel.style.display = 'none';
    });

    return panel;
  }

  /* ── Row builders ────────────────────────────────────────────────────── */

  const FIELD_STYLE = `
    width:100%;background:rgba(0,0,0,0.28);
    border:1px solid rgba(92,63,24,0.50);border-radius:7px;
    color:var(--ep-text,#ddd0b8);padding:5px 8px;font-size:0.79rem;
    box-sizing:border-box;outline:none;
    transition:border-color 0.14s,box-shadow 0.14s;
  `;

  const FOCUS_STYLE = `border-color:rgba(201,162,39,0.60);box-shadow:0 0 0 2px rgba(201,162,39,0.14);`;

  function addFocus(inputEl) {
    inputEl.setAttribute('onfocus', `this.style.cssText += '${FOCUS_STYLE}'`);
    inputEl.setAttribute('onblur',  `this.style.removeProperty('box-shadow');
      this.style.borderColor='rgba(92,63,24,0.50)';`);
    return inputEl;
  }

  function row(label, inputHtml) {
    return `<label style="display:grid;gap:0.22rem;">
      <span style="font-family:'Cinzel','Georgia',serif;font-size:0.60rem;
                   letter-spacing:0.10em;text-transform:uppercase;
                   color:rgba(160,144,112,0.80);">${label}</span>
      ${inputHtml}
    </label>`;
  }

  function twoCol(a, b) {
    return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.55rem;">${a}${b}</div>`;
  }

  function inputHtml(id, type, attrs) {
    return `<input id="${id}" type="${type}" style="${FIELD_STYLE}" ${attrs} />`;
  }

  function selectHtml(id, options) {
    const opts = options.map(o =>
      `<option value="${o.value}">${o.label}</option>`
    ).join('');
    return `<select id="${id}" style="${FIELD_STYLE}">${opts}</select>`;
  }

  function textareaHtml(id, rows, content) {
    return `<textarea id="${id}" rows="${rows}"
      style="${FIELD_STYLE}resize:vertical;">${content}</textarea>`;
  }

  /* ── Field renderers ──────────────────────────────────────────────────── */

  function renderToken(token) {
    const zoom = clamp(
      token.imageFit ? token.imageZoom : (token.image_zoom ?? token.imageZoom),
      0.5, 3, 1
    );
    const offX = clamp(token.imageOffsetX ?? token.image_offset_x, -1, 1, 0);
    const offY = clamp(token.imageOffsetY ?? token.image_offset_y, -1, 1, 0);
    return [
      row('Image Fit', selectHtml('soi-token-fit', [
        { value: 'cover',    label: 'Cover'    },
        { value: 'contain',  label: 'Contain'  },
        { value: 'portrait', label: 'Portrait' },
      ])),
      twoCol(
        row('Zoom',     inputHtml('soi-token-zoom', 'number', `min="0.5" max="3"   step="0.05" value="${zoom}"`)),
        row('Offset X', inputHtml('soi-token-offx', 'number', `min="-1"  max="1"   step="0.05" value="${offX}"`))
      ),
      row('Offset Y', inputHtml('soi-token-offy', 'number', `min="-1" max="1" step="0.05" value="${offY}"`)),
    ].join('');
  }

  function renderProp(item) {
    return twoCol(
      row('Scale', inputHtml('soi-prop-scale', 'number',
        `min="0.25" max="4" step="0.05" value="${clamp(item.asset_scale, 0.25, 4, 1)}"`)),
      row('Anchor', selectHtml('soi-prop-anchor', [
        { value: 'center', label: 'Center' },
        { value: 'bottom', label: 'Bottom' },
      ]))
    );
  }

  function renderVfx(item) {
    return [
      row('Name', `<input id="soi-vfx-name" type="text" maxlength="48"
        style="${FIELD_STYLE}"
        value="${String(item.asset_name || 'VFX').replace(/"/g, '&quot;')}" />`),
      twoCol(
        row('Scale', inputHtml('soi-vfx-scale', 'number',
          `min="0.25" max="4" step="0.05" value="${clamp(item.asset_scale, 0.25, 4, 1)}"`)),
        row('Anchor', selectHtml('soi-vfx-anchor', [
          { value: 'center', label: 'Center' },
          { value: 'bottom', label: 'Bottom' },
        ]))
      ),
      row('Duration (ms)', inputHtml('soi-vfx-duration', 'number',
        `min="500" max="30000" step="100" value="${clamp(item.asset_duration_ms, 500, 30000, 8000)}"`)),
    ].join('');
  }

  function renderPoi(item) {
    const descSafe = String(item.description || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const dmSafe   = String(item.dm_notes    || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return [
      row('Name', `<input id="soi-poi-name" type="text" maxlength="60"
        style="${FIELD_STYLE}"
        value="${String(item.name || '').replace(/"/g, '&quot;')}" />`),
      row('Type', selectHtml('soi-poi-type', [
        { value: 'city',       label: 'City'       },
        { value: 'settlement', label: 'Settlement' },
        { value: 'kingdom',    label: 'Kingdom'    },
        { value: 'dungeon',    label: 'Dungeon'    },
        { value: 'forest',     label: 'Forest'     },
        { value: 'mountain',   label: 'Mountain'   },
        { value: 'port',       label: 'Port'       },
        { value: 'ruin',       label: 'Ruin'       },
        { value: 'other',      label: 'Other'      },
      ])),
      `<label style="display:flex;align-items:center;gap:0.55rem;
                     padding:0.50rem 0.65rem;
                     background:rgba(0,0,0,0.20);
                     border:1px solid rgba(92,63,24,0.40);border-radius:8px;cursor:pointer;">
         <input id="soi-poi-revealed" type="checkbox"
                style="accent-color:#c9a227;cursor:pointer;width:14px;height:14px;" />
         <span style="font-size:0.77rem;">Revealed to players</span>
       </label>`,
      row('Description', textareaHtml('soi-poi-desc', 3, descSafe)),
      row('DM Notes',    textareaHtml('soi-poi-dm',   3, dmSafe)),
    ].join('');
  }

  /* ── Selection helpers ───────────────────────────────────────────────── */

  function currentSelection(env) {
    const token = env.getSelectedToken?.();
    const prop  = env.getOpenPropItem?.();
    const vfx   = env.getOpenVfxMarker?.();
    const poi   = env.getOpenPoiEditor?.();
    if (vfx)   return { type: 'vfx',   item: vfx,   key: 'vfx:' + vfx.id,   title: vfx.asset_name || 'Placed VFX' };
    if (prop && String(prop.kind || '') === 'custom_asset')
               return { type: 'prop',  item: prop,  key: 'prop:' + prop.id,  title: prop.name || 'Custom Prop' };
    if (poi)   return { type: 'poi',   item: poi,   key: 'poi:' + poi.poi_id, title: poi.name || 'Location' };
    if (token) return { type: 'token', item: token, key: 'token:' + token.id, title: token.name || 'Token' };
    return null;
  }

  function applyValues(sel) {
    if (!sel) return;
    if (sel.type === 'token') {
      const fitEl = el('soi-token-fit');
      if (fitEl) fitEl.value = String(sel.item.imageFit || sel.item.image_fit || 'cover').toLowerCase();
    }
    if (sel.type === 'prop') {
      const anchorEl = el('soi-prop-anchor');
      if (anchorEl) anchorEl.value = String(sel.item.asset_anchor || 'center').toLowerCase() === 'bottom' ? 'bottom' : 'center';
    }
    if (sel.type === 'vfx') {
      const anchorEl = el('soi-vfx-anchor');
      if (anchorEl) anchorEl.value = String(sel.item.asset_anchor || 'center').toLowerCase() === 'bottom' ? 'bottom' : 'center';
    }
    if (sel.type === 'poi') {
      const typeEl  = el('soi-poi-type');
      const revealEl = el('soi-poi-revealed');
      if (typeEl)   typeEl.value   = sel.item.poi_type || 'other';
      if (revealEl) revealEl.checked = sel.item.revealed_to_players !== false;
    }
  }

  function collect(sel) {
    if (!sel) return null;
    if (sel.type === 'token') return {
      imageFit:     el('soi-token-fit')?.value  || 'cover',
      imageZoom:    clamp(el('soi-token-zoom')?.value, 0.5,  3,    1),
      imageOffsetX: clamp(el('soi-token-offx')?.value, -1,   1,    0),
      imageOffsetY: clamp(el('soi-token-offy')?.value, -1,   1,    0),
    };
    if (sel.type === 'prop') return {
      asset_scale:  clamp(el('soi-prop-scale')?.value,  0.25, 4,    1),
      asset_anchor: el('soi-prop-anchor')?.value || 'center',
    };
    if (sel.type === 'vfx') return {
      asset_name:        el('soi-vfx-name')?.value     || 'VFX',
      asset_scale:       clamp(el('soi-vfx-scale')?.value,    0.25, 4,     1),
      asset_anchor:      el('soi-vfx-anchor')?.value   || 'center',
      asset_duration_ms: clamp(el('soi-vfx-duration')?.value, 500,  30000, 8000),
    };
    if (sel.type === 'poi') return {
      name:                 el('soi-poi-name')?.value  || '',
      poi_type:             el('soi-poi-type')?.value  || 'other',
      description:          el('soi-poi-desc')?.value  || '',
      dm_notes:             el('soi-poi-dm')?.value    || '',
      revealed_to_players:  !!el('soi-poi-revealed')?.checked,
    };
    return null;
  }

  /* ── Mount ────────────────────────────────────────────────────────────── */

  function mount(env) {
    const panel   = ensurePanel();
    const saveBtn = el('selected-object-inspector-save');
    let lastKey   = '';
    let _intervalId = null;

    saveBtn.addEventListener('click', () => {
      const sel   = currentSelection(env);
      if (!sel) return;
      const patch = collect(sel);
      if (!patch) return;
      if (sel.type === 'token') env.saveSelectedTokenFrame?.(sel.item.id, patch);
      else if (sel.type === 'prop') env.saveOpenPropAsset?.(patch);
      else if (sel.type === 'vfx')  env.saveOpenVfxMarker?.(patch);
      else if (sel.type === 'poi')  env.saveOpenPoiEditor?.(patch);
    });

    function tick() {
      const sel = currentSelection(env);

      // If panel container is hidden, skip
      if (panel.offsetParent === null && panel.style.display !== 'block') {
        return;
      }

      if (!sel) {
        panel.style.display = 'none';
        lastKey = '';
        return;
      }

      panel.style.display = 'block';

      if (sel.key !== lastKey) {
        const titleEl = el('selected-object-inspector-title');
        const bodyEl  = el('selected-object-inspector-body');
        if (titleEl) titleEl.textContent = sel.title;
        if (bodyEl) {
          bodyEl.innerHTML =
            sel.type === 'token' ? renderToken(sel.item) :
            sel.type === 'prop'  ? renderProp(sel.item)  :
            sel.type === 'vfx'   ? renderVfx(sel.item)   :
            renderPoi(sel.item);
        }
        applyValues(sel);
        lastKey = sel.key;
      }
    }

    tick();
    _intervalId = setInterval(tick, 120);

    // Expose a push-refresh method for call-sites that know the selection changed
    window.AppEditorInspectorRefresh = () => {
      lastKey = '';   // force rebuild on next tick
      tick();
    };

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
      if (_intervalId !== null) clearInterval(_intervalId);
    }, { once: true });
  }

  window.AppEditorInspector = { mount };
})();
