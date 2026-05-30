(function initCharacterImportModal(global) {
  const MODAL_ID = 'character-import-modal';

  function getSessionId(preferred) {
    const direct = String(preferred || '').trim();
    if (direct) return direct;
    const fromGlobal = String(global.SESSION_ID || '').trim();
    if (fromGlobal) return fromGlobal;
    try {
      const params = new URLSearchParams(global.location && global.location.search ? global.location.search : '');
      return String(params.get('session') || '').trim();
    } catch (_) {
      return '';
    }
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function ensureModalDom() {
    let root = document.getElementById(MODAL_ID);
    if (root) return root;

    root = document.createElement('div');
    root.id = MODAL_ID;
    root.style.position = 'fixed';
    root.style.inset = '0';
    root.style.background = 'rgba(0,0,0,0.65)';
    root.style.display = 'none';
    root.style.alignItems = 'center';
    root.style.justifyContent = 'center';
    root.style.zIndex = '15000';
    root.style.pointerEvents = 'none';

    root.innerHTML = ''
      + '<div style="width:min(760px, calc(100vw - 24px)); max-height:calc(100vh - 24px); overflow:auto;'
      + ' background:#13100a; border:1px solid rgba(0,229,204,0.28); border-radius:8px; padding:16px; color:#e8dcc8; box-shadow:0 14px 44px rgba(0,0,0,0.45);">'
      + '  <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:10px;">'
      + '    <div>'
      + '      <div style="font-family:Cinzel, serif; letter-spacing:0.1em; text-transform:uppercase; color:#00e5cc; font-size:0.72rem;">Import Character</div>'
      + '      <div style="font-size:0.85rem; opacity:0.85; margin-top:2px;">Preview imports before saving them to your native profile library.</div>'
      + '    </div>'
      + '    <button type="button" id="character-import-close" style="background:transparent; color:#e8dcc8; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:4px 8px; cursor:pointer;">Close</button>'
      + '  </div>'
      + '  <div id="character-import-source-panel" style="display:grid; gap:12px;">'
      + '    <section style="border:1px solid rgba(0,229,204,0.16); border-radius:6px; padding:10px;">'
      + '      <div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:#00e5cc; margin-bottom:6px;">D&amp;D Beyond Character ID</div>'
      + '      <div style="display:flex; gap:8px; flex-wrap:wrap;">'
      + '        <input type="text" id="character-import-ddb-id" placeholder="e.g. 1234567" style="flex:1; min-width:220px; background:#21190d; border:1px solid rgba(0,229,204,0.2); color:#e8dcc8; border-radius:4px; padding:7px 10px;" />'
      + '        <button type="button" id="character-import-ddb-id-btn" style="background:#00b4a0; color:#02110f; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Preview by ID</button>'
      + '      </div>'
      + '    </section>'
      + '    <section style="border:1px solid rgba(0,229,204,0.16); border-radius:6px; padding:10px;">'
      + '      <div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:#00e5cc; margin-bottom:6px;">D&amp;D Beyond JSON</div>'
      + '      <textarea id="character-import-json" placeholder="Paste exported D&amp;D Beyond JSON here…" style="width:100%; min-height:120px; resize:vertical; background:#21190d; border:1px solid rgba(0,229,204,0.2); color:#e8dcc8; border-radius:4px; padding:8px;"></textarea>'
      + '      <div style="display:flex; gap:8px; margin-top:8px; flex-wrap:wrap;">'
      + '        <button type="button" id="character-import-json-btn" style="background:#00b4a0; color:#02110f; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Preview JSON Text</button>'
      + '        <label style="display:inline-flex; align-items:center; gap:6px; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:6px 10px; cursor:pointer;">'
      + '          <span>JSON File</span>'
      + '          <input id="character-import-json-file" type="file" accept=".json,application/json" style="display:none;" />'
      + '        </label>'
      + '      </div>'
      + '    </section>'
      + '    <section style="border:1px solid rgba(0,229,204,0.16); border-radius:6px; padding:10px;">'
      + '      <div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:#00e5cc; margin-bottom:6px;">D&amp;D Beyond PDF</div>'
      + '      <div style="display:flex; gap:8px; flex-wrap:wrap;">'
      + '        <label style="display:inline-flex; align-items:center; gap:6px; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:6px 10px; cursor:pointer;">'
      + '          <span>Choose PDF</span>'
      + '          <input id="character-import-pdf-file" type="file" accept="application/pdf" style="display:none;" />'
      + '        </label>'
      + '      </div>'
      + '      <div id="character-import-pdf-preview-wrap" style="display:none; margin-top:8px; border:1px solid rgba(0,229,204,0.2); border-radius:6px; overflow:hidden; background:#0a0f11;">'
      + '        <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding:6px 8px; border-bottom:1px solid rgba(0,229,204,0.14);">'
      + '          <span style="font-size:0.72rem; opacity:0.9;">PDF Preview (contained)</span>'
      + '          <button type="button" id="character-import-pdf-clear-btn" style="background:transparent; color:#e8dcc8; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:3px 8px; cursor:pointer;">Clear Preview</button>'
      + '        </div>'
      + '        <div id="character-import-pdf-preview-host" style="height:280px; overflow:auto; position:relative;"></div>'
      + '      </div>'
      + '    </section>'
      + '  </div>'
      + '  <div id="character-import-status" style="display:none; margin-top:12px; border-radius:4px; padding:8px 10px; font-size:0.84rem;"></div>'
      + '  <div id="character-import-review" style="display:none; margin-top:12px; border:1px solid rgba(201,162,39,0.4); border-radius:6px; padding:10px; background:rgba(201,162,39,0.12);">'
      + '    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px;">'
      + '      <div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:#f5ddb0;">Import Review</div>'
      + '      <div id="character-import-review-source" style="font-size:0.7rem; opacity:0.75;"></div>'
      + '    </div>'
      + '    <div id="character-import-summary" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; margin-bottom:10px;"></div>'
      + '    <div id="character-import-review-list" style="display:grid; gap:8px;"></div>'
      + '    <div id="character-import-resolution-actions" style="display:none; margin-top:10px; gap:8px; flex-wrap:wrap;">'
      + '      <button type="button" id="character-import-resolve-preview-btn" style="background:#c9a227; color:#1a1204; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Update Preview With Fixes</button>'
      + '    </div>'
      + '    <div id="character-import-final-actions" style="display:flex; margin-top:10px; gap:8px; flex-wrap:wrap;">'
      + '      <button type="button" id="character-import-save-btn" style="background:#00b4a0; color:#02110f; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Save Imported Character</button>'
      + '      <button type="button" id="character-import-edit-btn" style="background:transparent; color:#e8dcc8; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:7px 12px; cursor:pointer;">Edit Before Saving</button>'
      + '      <button type="button" id="character-import-cancel-btn" style="background:transparent; color:#e8dcc8; border:1px solid rgba(229,90,90,0.35); border-radius:4px; padding:7px 12px; cursor:pointer;">Cancel</button>'
      + '    </div>'
      + '  </div>'
      + '</div>';

    document.body.appendChild(root);
    return root;
  }

  function setStatus(root, message, kind) {
    const status = root.querySelector('#character-import-status');
    if (!status) return;
    if (!message) {
      status.style.display = 'none';
      status.textContent = '';
      return;
    }
    status.style.display = 'block';
    status.textContent = message;

    const tone = String(kind || 'info').toLowerCase();
    if (tone === 'error') {
      status.style.background = 'rgba(160,45,45,0.2)';
      status.style.border = '1px solid rgba(220,90,90,0.45)';
      status.style.color = '#ffb9b9';
      return;
    }
    if (tone === 'success') {
      status.style.background = 'rgba(0,170,130,0.2)';
      status.style.border = '1px solid rgba(0,229,204,0.35)';
      status.style.color = '#a9ffe7';
      return;
    }
    status.style.background = 'rgba(201,162,39,0.2)';
    status.style.border = '1px solid rgba(201,162,39,0.4)';
    status.style.color = '#f5ddb0';
  }

  function toErrorMessage(payload, fallback) {
    if (!payload || typeof payload !== 'object') return fallback;
    return String(payload.detail || payload.error || fallback || 'Import failed.');
  }

  function getCsrfToken() {
    if (global.AppAPI && typeof global.AppAPI.getCsrfToken === 'function') {
      return global.AppAPI.getCsrfToken();
    }
    if (typeof global.getCsrfToken === 'function') {
      return global.getCsrfToken();
    }
    const match = document.cookie ? document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/) : null;
    return match ? decodeURIComponent(match[1]) : '';
  }

  function withCsrfHeaders(headers) {
    const token = getCsrfToken();
    return token ? Object.assign({ 'X-CSRF-Token': token }, headers || {}) : (headers || {});
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: withCsrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body || {}),
    });
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }
    if (!res.ok || !data || data.ok !== true) {
      throw new Error(toErrorMessage(data, 'Import request failed.'));
    }
    return data;
  }

  async function postForm(url, formData) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: withCsrfHeaders(),
      body: formData,
    });
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }
    if (!res.ok || !data || data.ok !== true) {
      throw new Error(toErrorMessage(data, 'Upload import failed.'));
    }
    return data;
  }

  function normalizeWarningItem(item) {
    if (!item || typeof item !== 'object') {
      return {
        code: '',
        message: String(item || '').trim(),
        blocking: false,
        details: {},
      };
    }
    return {
      code: String(item.code || '').trim(),
      message: String(item.message || item.code || 'Import warning').trim(),
      blocking: Boolean(item.blocking),
      details: item.details && typeof item.details === 'object' ? item.details : {},
    };
  }

  function normalizedWarnings(payload) {
    const warnings = Array.isArray(payload && payload.warnings) ? payload.warnings : [];
    const required = Array.isArray(payload && payload.required_choices) ? payload.required_choices : [];
    const rows = warnings.concat(required).map(normalizeWarningItem).filter(function keep(row) {
      return row.message || row.code;
    });
    const seen = new Set();
    return rows.filter(function unique(row) {
      const key = [row.code, row.message, Boolean(row.blocking)].join('|');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function arrayCount(value) {
    return Array.isArray(value) ? value.length : 0;
  }

  function countObjectValues(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return 0;
    return Object.keys(value).filter(function hasValue(key) {
      const row = value[key];
      if (Array.isArray(row)) return row.length > 0;
      return row != null && row !== '';
    }).length;
  }

  function summarizeDocument(document) {
    const doc = document && typeof document === 'object' ? document : {};
    const identity = doc.identity && typeof doc.identity === 'object' ? doc.identity : {};
    const species = doc.species && typeof doc.species === 'object' ? doc.species : {};
    const background = doc.background && typeof doc.background === 'object' ? doc.background : {};
    const classes = Array.isArray(doc.classes) ? doc.classes : [];
    const classLabels = classes.map(function labelClass(cls) {
      if (!cls || typeof cls !== 'object') return '';
      const name = String(cls.name || cls.className || cls.classId || '').trim();
      const level = cls.level == null ? '' : String(cls.level).trim();
      return name ? (name + (level ? ' ' + level : '')) : '';
    }).filter(Boolean);
    const totalLevel = classes.reduce(function sum(acc, cls) {
      const level = parseInt(cls && cls.level, 10);
      return acc + (Number.isFinite(level) ? level : 0);
    }, 0);
    const abilities = doc.abilities && typeof doc.abilities === 'object' ? doc.abilities : {};
    const scores = abilities.scores && typeof abilities.scores === 'object' ? abilities.scores : {};
    const equipment = doc.equipment && typeof doc.equipment === 'object' ? doc.equipment : {};
    const spellState = doc.spellState && typeof doc.spellState === 'object' ? doc.spellState : {};
    const importMeta = doc.importMeta && typeof doc.importMeta === 'object' ? doc.importMeta : {};
    const importedSpells = arrayCount(importMeta.importedSpells);
    const preparedSpells = arrayCount(spellState.knownSpells) + arrayCount(spellState.preparedSpells) + arrayCount(spellState.spells);
    const importedActions = arrayCount(importMeta.importedActions);
    const importedFeatures = arrayCount(importMeta.importedFeatures);

    return {
      name: String(identity.name || identity.displayName || doc.name || 'Unnamed Character').trim() || 'Unnamed Character',
      classLevel: classLabels.length ? classLabels.join(' / ') : (totalLevel ? 'Level ' + String(totalLevel) : 'Unknown'),
      species: String(species.name || species.id || 'Unknown').trim() || 'Unknown',
      background: String(background.name || background.id || 'Unknown').trim() || 'Unknown',
      statsFound: countObjectValues(scores),
      inventoryCount: arrayCount(equipment.inventory),
      spellCount: importedSpells || preparedSpells,
      actionFeatureCount: importedActions + importedFeatures + arrayCount(doc.actions) + arrayCount(doc.features),
    };
  }

  function clearReview(root) {
    const review = root.querySelector('#character-import-review');
    const summary = root.querySelector('#character-import-summary');
    const reviewList = root.querySelector('#character-import-review-list');
    const actionRow = root.querySelector('#character-import-resolution-actions');
    const sourceLabel = root.querySelector('#character-import-review-source');
    if (review) review.style.display = 'none';
    if (summary) summary.innerHTML = '';
    if (reviewList) reviewList.innerHTML = '';
    if (actionRow) actionRow.style.display = 'none';
    if (sourceLabel) sourceLabel.textContent = '';
  }

  function renderSummaryCard(label, value) {
    return '<div style="border:1px solid rgba(245,221,176,0.18); border-radius:4px; padding:8px; background:rgba(0,0,0,0.12);">'
      + '<div style="font-size:0.62rem; letter-spacing:0.08em; text-transform:uppercase; color:#f5ddb0; opacity:0.75;">' + escapeHtml(label) + '</div>'
      + '<div style="margin-top:3px; font-size:0.9rem;">' + escapeHtml(value) + '</div>'
      + '</div>';
  }

  function renderReview(root, payload, allowResolve) {
    const review = root.querySelector('#character-import-review');
    const summary = root.querySelector('#character-import-summary');
    const reviewList = root.querySelector('#character-import-review-list');
    const actionRow = root.querySelector('#character-import-resolution-actions');
    const finalActions = root.querySelector('#character-import-final-actions');
    const saveBtn = root.querySelector('#character-import-save-btn');
    const sourceLabel = root.querySelector('#character-import-review-source');
    if (!review || !summary || !reviewList || !actionRow || !finalActions || !saveBtn) return;

    const document = payload && payload.preview_document && typeof payload.preview_document === 'object'
      ? payload.preview_document
      : {};
    const summaryData = summarizeDocument(document);
    const items = normalizedWarnings(payload);
    const hasBlocking = Boolean(payload && payload.requires_resolution) || items.some(function (item) { return item.blocking; });

    if (sourceLabel) {
      sourceLabel.textContent = payload && payload.source ? String(payload.source).replace(/_/g, ' ') : '';
    }
    summary.innerHTML = [
      renderSummaryCard('Character name', summaryData.name),
      renderSummaryCard('Class/level', summaryData.classLevel),
      renderSummaryCard('Species', summaryData.species),
      renderSummaryCard('Background', summaryData.background),
      renderSummaryCard('Stats found', String(summaryData.statsFound) + '/6'),
      renderSummaryCard('Inventory count', String(summaryData.inventoryCount)),
      renderSummaryCard('Spell count', String(summaryData.spellCount)),
      renderSummaryCard('Actions/features count', String(summaryData.actionFeatureCount)),
    ].join('');

    const warningsHtml = items.length ? items.map(function renderRow(item, idx) {
      const resolutionKey = String(item.details && item.details.resolutionKey || '').trim();
      const options = Array.isArray(item.details && item.details.options) ? item.details.options : [];
      const select = item.blocking && allowResolve && resolutionKey
        ? (
          '<div style="margin-top:6px;">'
          + '<label style="font-size:0.75rem; opacity:0.9;">Required fix:</label>'
          + '<select data-resolution-key="' + escapeHtml(resolutionKey) + '" data-warning-index="' + String(idx) + '"'
          + ' style="display:block; margin-top:4px; width:100%; background:#21190d; border:1px solid rgba(0,229,204,0.25); color:#e8dcc8; border-radius:4px; padding:6px;">'
          + '<option value="">Select…</option>'
          + options.map(function (opt) {
            const value = String(opt || '').trim();
            return '<option value="' + escapeHtml(value) + '">' + escapeHtml(value) + '</option>';
          }).join('')
          + '</select>'
          + '</div>'
        )
        : '';
      return '<div style="border:1px solid rgba(245,221,176,0.2); border-radius:4px; padding:8px;">'
        + '<div style="font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:' + (item.blocking ? '#ffd6a2' : '#f5ddb0') + ';">'
        + (item.blocking ? 'Required fix' : 'Warning')
        + '</div>'
        + '<div style="font-size:0.84rem; margin-top:3px;">' + escapeHtml(item.message) + '</div>'
        + select
        + '</div>';
    }).join('') : '<div style="border:1px solid rgba(0,229,204,0.16); border-radius:4px; padding:8px; color:#a9ffe7;">No warnings found.</div>';

    reviewList.innerHTML = warningsHtml;
    actionRow.style.display = (allowResolve && hasBlocking) ? 'flex' : 'none';
    saveBtn.style.display = hasBlocking ? 'none' : '';
    finalActions.style.display = 'flex';
    review.style.display = 'block';
  }

  function open(config) {
    const cfg = Object.assign({
      sessionId: '',
      onImported: null,
      onClose: null,
    }, config || {});

    const root = ensureModalDom();
    const closeBtn = root.querySelector('#character-import-close');
    const ddbIdInput = root.querySelector('#character-import-ddb-id');
    const ddbIdBtn = root.querySelector('#character-import-ddb-id-btn');
    const jsonText = root.querySelector('#character-import-json');
    const jsonBtn = root.querySelector('#character-import-json-btn');
    const jsonFileInput = root.querySelector('#character-import-json-file');
    const pdfFileInput = root.querySelector('#character-import-pdf-file');
    const pdfPreviewWrap = root.querySelector('#character-import-pdf-preview-wrap');
    const pdfPreviewHost = root.querySelector('#character-import-pdf-preview-host');
    const pdfPreviewClearBtn = root.querySelector('#character-import-pdf-clear-btn');
    const resolvePreviewBtn = root.querySelector('#character-import-resolve-preview-btn');
    const saveBtn = root.querySelector('#character-import-save-btn');
    const editBtn = root.querySelector('#character-import-edit-btn');
    const cancelBtn = root.querySelector('#character-import-cancel-btn');

    const sessionId = getSessionId(cfg.sessionId);
    let activePdfPreviewUrl = '';
    let pendingImport = null;

    function clearPdfPreview() {
      if (pdfPreviewHost) {
        pdfPreviewHost.innerHTML = '';
      }
      if (pdfPreviewWrap) {
        pdfPreviewWrap.style.display = 'none';
      }
      if (activePdfPreviewUrl) {
        try {
          URL.revokeObjectURL(activePdfPreviewUrl);
        } catch (_) {
          // ignore revoke failures; browser may have already reclaimed it
        }
      }
      activePdfPreviewUrl = '';
    }

    function renderPdfPreview(file) {
      if (!pdfPreviewHost || !pdfPreviewWrap || !file) return;
      clearPdfPreview();
      activePdfPreviewUrl = URL.createObjectURL(file);
      const iframe = document.createElement('iframe');
      iframe.src = activePdfPreviewUrl;
      iframe.setAttribute('title', 'Character PDF Preview');
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.style.minHeight = '280px';
      iframe.style.border = '0';
      iframe.style.display = 'block';
      iframe.style.position = 'relative';
      iframe.style.zIndex = '1';
      pdfPreviewHost.appendChild(iframe);
      pdfPreviewWrap.style.display = 'block';
    }

    function close() {
      clearPdfPreview();
      pendingImport = null;
      root.style.display = 'none';
      root.style.pointerEvents = 'none';
      if (typeof cfg.onClose === 'function') cfg.onClose();
    }

    function getResolution() {
      const selects = Array.from(root.querySelectorAll('select[data-resolution-key]'));
      const resolution = {};
      for (const sel of selects) {
        const key = String(sel && sel.getAttribute('data-resolution-key') || '').trim().toLowerCase();
        const value = String(sel && sel.value || '').trim();
        if (!key) continue;
        if (!value) {
          setStatus(root, 'Resolve all required choices before continuing.', 'error');
          return null;
        }
        resolution[key] = value;
      }
      return resolution;
    }

    async function previewImport(importConfig, resolution) {
      if (!importConfig) return;
      const label = importConfig.previewingLabel || 'Building import preview…';
      setStatus(root, label, 'info');
      clearReview(root);
      try {
        let data;
        if (typeof importConfig.buildPreviewForm === 'function') {
          data = await postForm(importConfig.previewUrl, importConfig.buildPreviewForm(resolution || {}));
        } else {
          data = await postJson(importConfig.previewUrl, importConfig.buildPreviewBody(resolution || {}));
        }
        pendingImport = Object.assign({}, importConfig, { previewPayload: data });
        renderReview(root, data, true);
        if (data.requires_resolution) {
          setStatus(root, 'Review the preview and fix required choices before saving.', 'error');
          return;
        }
        setStatus(root, 'Preview ready. Review the character, then save or edit before saving.', 'success');
      } catch (err) {
        setStatus(root, String(err && err.message || 'Import preview failed.'), 'error');
      }
    }

    async function commitPendingImport() {
      if (!pendingImport || !pendingImport.previewPayload) {
        setStatus(root, 'Preview an imported character before saving.', 'error');
        return;
      }
      if (pendingImport.previewPayload.requires_resolution) {
        setStatus(root, 'Fix required import choices before saving.', 'error');
        return;
      }
      setStatus(root, 'Saving imported character…', 'info');
      try {
        const previewDocument = pendingImport.previewPayload.preview_document || {};
        let data;
        if (typeof pendingImport.buildCommitForm === 'function') {
          data = await postForm(pendingImport.commitUrl, pendingImport.buildCommitForm(previewDocument));
        } else {
          data = await postJson(pendingImport.commitUrl, pendingImport.buildCommitBody(previewDocument));
        }
        setStatus(root, 'Imported character saved.', 'success');
        if (typeof cfg.onImported === 'function') {
          await cfg.onImported(data);
        }
      } catch (err) {
        setStatus(root, String(err && err.message || 'Import save failed.'), 'error');
      }
    }

    if (closeBtn) {
      closeBtn.onclick = close;
    }
    if (cancelBtn) {
      cancelBtn.onclick = close;
    }
    if (editBtn) {
      editBtn.onclick = function onEditBeforeSaving() {
        pendingImport = null;
        clearReview(root);
        setStatus(root, 'Make changes to the import source, then preview again.', 'info');
        if (jsonText) jsonText.focus();
      };
    }
    if (saveBtn) {
      saveBtn.onclick = commitPendingImport;
    }
    if (resolvePreviewBtn) {
      resolvePreviewBtn.onclick = function onResolvePreview() {
        const resolution = getResolution();
        if (!resolution || !pendingImport) return;
        previewImport(pendingImport, resolution);
      };
    }
    if (pdfPreviewClearBtn) {
      pdfPreviewClearBtn.onclick = function onClearPdfPreview() {
        clearPdfPreview();
      };
    }

    root.onclick = function onRootClick(event) {
      if (event.target === root) {
        close();
      }
    };

    if (ddbIdBtn) {
      ddbIdBtn.onclick = async function onPreviewById() {
        const characterId = String(ddbIdInput && ddbIdInput.value || '').trim();
        if (!sessionId) {
          setStatus(root, 'Missing session_id in join URL.', 'error');
          return;
        }
        if (!characterId) {
          setStatus(root, 'Enter a D&D Beyond character ID first.', 'error');
          return;
        }
        await previewImport({
          previewUrl: '/api/character/import/ddb-id/preview',
          commitUrl: '/api/character/import/ddb-id/commit',
          previewingLabel: 'Building D&D Beyond ID preview…',
          buildPreviewBody: function buildPreviewBody(resolution) {
            return {
              session_id: sessionId,
              character_id: characterId,
              import_resolution: resolution,
            };
          },
          buildCommitBody: function buildCommitBody(previewDocument) {
            return {
              session_id: sessionId,
              character_id: characterId,
              preview_document: previewDocument,
            };
          },
        });
      };
    }

    function jsonImportConfig(parsed, label) {
      return {
        previewUrl: '/api/character/import/json/preview',
        commitUrl: '/api/character/import/json/commit',
        previewingLabel: label || 'Building JSON import preview…',
        buildPreviewBody: function buildPreviewBody(resolution) {
          return {
            session_id: sessionId,
            ddb_json: parsed,
            import_resolution: resolution,
          };
        },
        buildCommitBody: function buildCommitBody(previewDocument) {
          return {
            session_id: sessionId,
            ddb_json: parsed,
            preview_document: previewDocument,
          };
        },
      };
    }

    if (jsonBtn) {
      jsonBtn.onclick = async function onPreviewJsonText() {
        const raw = String(jsonText && jsonText.value || '').trim();
        if (!sessionId) {
          setStatus(root, 'Missing session_id in join URL.', 'error');
          return;
        }
        if (!raw) {
          setStatus(root, 'Paste JSON first.', 'error');
          return;
        }

        let parsed;
        try {
          parsed = JSON.parse(raw);
        } catch (_) {
          setStatus(root, 'Invalid JSON payload.', 'error');
          return;
        }

        await previewImport(jsonImportConfig(parsed, 'Building pasted JSON preview…'));
      };
    }

    if (jsonFileInput) {
      jsonFileInput.onchange = async function onJsonFileChange() {
        const file = jsonFileInput.files && jsonFileInput.files[0];
        if (!file) return;
        if (!sessionId) {
          setStatus(root, 'Missing session_id in join URL.', 'error');
          jsonFileInput.value = '';
          return;
        }

        setStatus(root, 'Reading JSON file…', 'info');
        clearReview(root);
        try {
          const text = await file.text();
          const parsed = JSON.parse(text);
          await previewImport(jsonImportConfig(parsed, 'Building JSON file preview…'));
        } catch (err) {
          setStatus(root, String(err && err.message || 'JSON file preview failed.'), 'error');
        } finally {
          jsonFileInput.value = '';
        }
      };
    }

    if (pdfFileInput) {
      pdfFileInput.onchange = async function onPdfFileChange() {
        const file = pdfFileInput.files && pdfFileInput.files[0];
        if (!file) return;
        renderPdfPreview(file);
        if (!sessionId) {
          setStatus(root, 'Missing session_id in join URL.', 'error');
          pdfFileInput.value = '';
          return;
        }

        const config = {
          previewUrl: '/api/character/import/pdf/preview',
          commitUrl: '/api/character/import/pdf/commit',
          previewingLabel: 'Uploading PDF for import preview…',
          buildPreviewForm: function buildPreviewForm(resolution) {
            const fd = new FormData();
            fd.set('session_id', sessionId);
            if (resolution && Object.keys(resolution).length) {
              fd.set('import_resolution', JSON.stringify(resolution));
            }
            fd.set('file', file);
            return fd;
          },
          buildCommitForm: function buildCommitForm(previewDocument) {
            const fd = new FormData();
            fd.set('session_id', sessionId);
            fd.set('preview_document', JSON.stringify(previewDocument || {}));
            return fd;
          },
        };

        try {
          await previewImport(config);
        } finally {
          pdfFileInput.value = '';
        }
      };
    }

    setStatus(root, '', 'info');
    clearReview(root);
    pendingImport = null;
    root.style.pointerEvents = 'auto';
    root.style.display = 'flex';
  }

  global.CharacterImportModal = {
    open,
  };
})(window);
