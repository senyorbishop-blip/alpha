(function initCharacterImportModal(global) {
  const MODAL_ID = 'character-import-modal';

  function getSessionId(preferred) {
    const direct = String(preferred || '').trim();
    if (direct) return direct;
    const fromGlobal = String(global.SESSION_ID || '').trim();
    if (fromGlobal) return fromGlobal;
    try {
      const params = new URLSearchParams(global.location && global.location.search ? global.location.search : '');
      return String(params.get('session') || params.get('session_id') || '').trim();
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
      + '      <div style="font-size:0.85rem; opacity:0.85; margin-top:2px;">Preview imports before saving them to your native profile library. JSON import gives best results; PDF import may need review.</div>'
      + '    </div>'
      + '    <button type="button" id="character-import-close" style="background:transparent; color:#e8dcc8; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:4px 8px; cursor:pointer;">Close</button>'
      + '  </div>'
      + '  <div id="character-import-source-panel" style="display:grid; gap:12px;">'
      + '    <section style="border:1px solid rgba(0,229,204,0.16); border-radius:6px; padding:10px;">'
      + '      <div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:#00e5cc; margin-bottom:6px;">D&amp;D Beyond Character ID</div>'
      + '      <div style="font-size:0.78rem; opacity:0.78; margin-bottom:8px;">Your D&amp;D Beyond character must be public. Paste the numeric ID, a public /characters/ URL, or a sheet PDF URL; private sheets cannot be imported by ID.</div>'
      + '      <div style="display:flex; gap:8px; flex-wrap:wrap;">'
      + '        <input type="text" id="character-import-ddb-id" placeholder="e.g. 1234567 or dndbeyond.com/characters/1234567" style="flex:1; min-width:220px; background:#21190d; border:1px solid rgba(0,229,204,0.2); color:#e8dcc8; border-radius:4px; padding:7px 10px;" />'
      + '        <button type="button" id="character-import-ddb-id-btn" style="background:#00b4a0; color:#02110f; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Preview by ID</button>'
      + '      </div>'
      + '    </section>'
      + '    <section style="border:1px solid rgba(0,229,204,0.16); border-radius:6px; padding:10px;">'
      + '      <div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:#00e5cc; margin-bottom:6px;">D&amp;D Beyond JSON</div>'
      + '      <div style="font-size:0.78rem; opacity:0.78; margin-bottom:8px;">Best quality: name, class, stats, items, spells, and actions are usually preserved.</div>'
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
      + '      <div style="font-size:0.78rem; opacity:0.78; margin-bottom:8px;">PDF import may be partial and works only with fillable form-field sheets.</div>'
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
      + '    <details id="character-import-debug-wrap" style="display:none; margin-top:10px; border:1px solid rgba(245,221,176,0.2); border-radius:4px; padding:8px;">'
      + '      <summary style="cursor:pointer; color:#f5ddb0; font-size:0.78rem;">Import review JSON</summary>'
      + '      <pre id="character-import-debug-json" style="white-space:pre-wrap; overflow:auto; max-height:260px; font-size:0.72rem; background:#0a0f11; border-radius:4px; padding:8px;"></pre>'
      + '    </details>'
      + '    <div id="character-import-edit-wrap" style="display:none; margin-top:10px;">'
      + '      <label for="character-import-edit-json" style="display:block; font-size:0.74rem; opacity:0.9; margin-bottom:4px;">Edit imported character document before saving</label>'
      + '      <textarea id="character-import-edit-json" style="width:100%; min-height:180px; resize:vertical; background:#21190d; border:1px solid rgba(0,229,204,0.2); color:#e8dcc8; border-radius:4px; padding:8px; font-family:monospace; font-size:0.78rem;"></textarea>'
      + '    </div>'
      + '    <div id="character-import-resolution-actions" style="display:none; margin-top:10px; gap:8px; flex-wrap:wrap;">'
      + '      <button type="button" id="character-import-resolve-save-btn" style="background:#c9a227; color:#1a1204; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Update Preview With Fixes</button>'
      + '      <button type="button" id="character-import-save-btn" style="background:#00b4a0; color:#02110f; border:0; border-radius:4px; padding:7px 12px; cursor:pointer;">Continue to Play</button>'
      + '      <button type="button" id="character-import-review-later-btn" style="background:#c9a227; color:#1a1204; border:0; border-radius:4px; padding:7px 12px; cursor:pointer; display:none;">Review Later</button>'
      + '      <button type="button" id="character-import-edit-btn" style="background:transparent; color:#e8dcc8; border:1px solid rgba(0,229,204,0.25); border-radius:4px; padding:7px 12px; cursor:pointer;">Edit Before Saving</button>'
      + '      <button type="button" id="character-import-debug-btn" style="background:transparent; color:#f5ddb0; border:1px solid rgba(245,221,176,0.25); border-radius:4px; padding:7px 12px; cursor:pointer;">Show Review JSON</button>'
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
    return friendlyErrorMessage(payload.detail || payload.error || payload.message || fallback || 'Import failed.');
  }

  function friendlyErrorMessage(message) {
    const raw = String(message || '').trim();
    const lower = raw.toLowerCase();
    if (!raw) return 'Import failed.';
    if (lower.includes('session_id')) return 'Missing session_id. Open your player invite link again before importing.';
    if (lower.includes('invalid json') || lower.includes('valid json') || lower.includes('json payload')) return 'Invalid JSON. Paste the full D&D Beyond JSON export or choose a .json file.';
    if (lower.includes('no form fields') || lower.includes('form-field') || lower.includes('fillable')) return 'PDF has no form fields. Export a fillable D&D Beyond PDF or use JSON import.';
    if (lower.includes('403') || lower.includes('401') || lower.includes('409') || lower.includes('private') || lower.includes('could not return that character')) return 'Private D&D Beyond character or unavailable link. Make the sheet public, then paste the numeric ID, a /characters/ URL, or the ID from the sheet PDF link.';
    if (lower.includes('unsupported_species') || lower.includes('unsupported species')) return 'Unsupported species. Pick the closest supported species in the required choices, or edit before saving.';
    if (lower.includes('unsupported_subclass') || lower.includes('unsupported subclass')) return 'Unsupported subclass. Pick the closest supported subclass in the required choices, or edit before saving.';
    return raw;
  }

  function getCsrfToken() {
    const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function withCsrfHeaders(headers) {
    const token = getCsrfToken();
    return Object.assign({}, headers || {}, token ? { 'X-CSRF-Token': token } : {});
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
      hasName: Boolean(String(identity.name || identity.displayName || doc.name || '').trim()),
      hasClass: classLabels.length > 0 || totalLevel > 0,
      statsFound: countObjectValues(scores),
      inventoryCount: arrayCount(equipment.inventory),
      spellCount: importedSpells || preparedSpells,
      actionFeatureCount: importedActions + importedFeatures + arrayCount(doc.actions) + arrayCount(doc.features),
    };
  }

  function sourceBadgeLabel(source) {
    const key = String(source || '').trim().toLowerCase();
    if (key === 'native') return 'Casual D&D';
    if (key.includes('pdf')) return 'PDF';
    if (key.includes('dndbeyond') || key.includes('ddb') || key.includes('json')) return 'D&D Beyond';
    if (key === 'legacy') return 'Legacy';
    return key ? key.replace(/_/g, ' ') : 'Legacy';
  }

  function importQualitySummary(summaryData, items, hasBlocking) {
    const missingCore = [];
    if (!summaryData.hasName) missingCore.push('name');
    if (!summaryData.hasClass) missingCore.push('class');
    if (summaryData.statsFound < 6) missingCore.push('stats');
    if (summaryData.inventoryCount < 1) missingCore.push('items');
    if (summaryData.spellCount < 1) missingCore.push('spells');
    if (summaryData.actionFeatureCount < 1) missingCore.push('actions');

    if (hasBlocking) {
      return {
        label: 'Needs review',
        detail: 'Blocking choices required before saving.',
        tone: '#ffd6a2',
      };
    }
    if (missingCore.includes('items') || missingCore.includes('spells') || missingCore.includes('actions')) {
      return {
        label: 'Partial',
        detail: 'Missing items/spells/actions. Save is allowed, but review before play.',
        tone: '#ffd6a2',
      };
    }
    if (items.length || missingCore.length) {
      return {
        label: 'Good',
        detail: 'Main sheet found with minor warnings.',
        tone: '#f5ddb0',
      };
    }
    return {
      label: 'Excellent',
      detail: 'Name/class/stats/items/spells/actions found.',
      tone: '#a9ffe7',
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


  function importReviewFromPayload(payload) {
    const direct = payload && payload.import_review && typeof payload.import_review === 'object' ? payload.import_review : null;
    if (direct) return direct;
    const doc = getPreviewDocument(payload);
    const meta = doc && doc.importMeta && typeof doc.importMeta === 'object' ? doc.importMeta : {};
    return meta.importReview && typeof meta.importReview === 'object' ? meta.importReview : {};
  }

  function reviewTone(status) {
    const key = String(status || '').toLowerCase();
    if (key === 'blocked') return { label: 'Blocked', color: '#ff8b8b', border: 'rgba(220,90,90,0.55)', bg: 'rgba(160,45,45,0.18)' };
    if (key === 'needs_review') return { label: 'Needs review', color: '#ffd36a', border: 'rgba(201,162,39,0.55)', bg: 'rgba(201,162,39,0.14)' };
    if (key === 'playable_with_warnings') return { label: 'Playable with warnings', color: '#ffd36a', border: 'rgba(201,162,39,0.55)', bg: 'rgba(201,162,39,0.14)' };
    return { label: 'Exact', color: '#72f0b4', border: 'rgba(70,210,140,0.55)', bg: 'rgba(30,150,90,0.14)' };
  }

  function renderPillList(items, emptyText, tone) {
    const color = tone === 'red' ? '#ffb9b9' : tone === 'yellow' ? '#f5ddb0' : '#a9ffe7';
    const border = tone === 'red' ? 'rgba(220,90,90,0.4)' : tone === 'yellow' ? 'rgba(201,162,39,0.4)' : 'rgba(0,229,204,0.28)';
    const bg = tone === 'red' ? 'rgba(160,45,45,0.16)' : tone === 'yellow' ? 'rgba(201,162,39,0.12)' : 'rgba(0,170,130,0.12)';
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) return '<div style="color:' + color + '; opacity:0.86;">' + escapeHtml(emptyText) + '</div>';
    return rows.slice(0, 24).map(function (item) {
      return '<span style="display:inline-block; margin:2px 4px 2px 0; padding:3px 7px; border:1px solid ' + border + '; border-radius:999px; background:' + bg + '; color:' + color + '; font-size:0.74rem;">' + escapeHtml(item) + '</span>';
    }).join('') + (rows.length > 24 ? '<span style="opacity:0.75;"> +' + String(rows.length - 24) + ' more</span>' : '');
  }

  function renderReviewSection(title, html, tone) {
    const border = tone === 'red' ? 'rgba(220,90,90,0.48)' : tone === 'yellow' ? 'rgba(201,162,39,0.45)' : 'rgba(0,229,204,0.24)';
    const color = tone === 'red' ? '#ffb9b9' : tone === 'yellow' ? '#f5ddb0' : '#a9ffe7';
    return '<section style="border:1px solid ' + border + '; border-radius:5px; padding:9px; background:rgba(0,0,0,0.12);">'
      + '<div style="font-family:Cinzel, serif; font-size:0.64rem; letter-spacing:0.08em; text-transform:uppercase; color:' + color + '; margin-bottom:6px;">' + escapeHtml(title) + '</div>'
      + '<div style="font-size:0.82rem; line-height:1.42;">' + html + '</div>'
      + '</section>';
  }

  function renderReview(root, payload, allowResolve) {
    const review = root.querySelector('#character-import-review');
    const summary = root.querySelector('#character-import-summary');
    const reviewList = root.querySelector('#character-import-review-list');
    const actionRow = root.querySelector('#character-import-resolution-actions');
    const finalActions = root.querySelector('#character-import-final-actions');
    const saveBtn = root.querySelector('#character-import-save-btn');
    const sourceLabel = root.querySelector('#character-import-review-source');
    if (!review || !summary || !reviewList || !actionRow || !saveBtn) return;

    const data = payload && typeof payload === 'object' ? payload : {};
    const document = data.preview_document && typeof data.preview_document === 'object'
      ? data.preview_document
      : {};
    const summaryData = summarizeDocument(document);
    const items = normalizedWarnings(payload);
    const hasBlocking = Boolean(data.requires_resolution) || items.some(function (item) { return item.blocking; });
    const quality = importQualitySummary(summaryData, items, hasBlocking);
    const reviewData = importReviewFromPayload(data);
    const tone = reviewTone(reviewData.reviewStatus || (hasBlocking ? 'blocked' : 'needs_review'));

    if (sourceLabel) {
      sourceLabel.textContent = sourceBadgeLabel(reviewData.sourceType || data.source_type || data.source);
    }
    summary.innerHTML = [
      '<div style="grid-column:1 / -1; border:1px solid ' + tone.border + '; border-radius:6px; padding:10px; background:' + tone.bg + ';">'
        + '<div style="font-family:Cinzel, serif; font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:' + tone.color + ';">Review status: ' + escapeHtml(tone.label) + '</div>'
        + '<div style="margin-top:4px; font-size:0.84rem;">' + (reviewData.canContinueToPlay ? 'Safe to continue to play.' : 'Not safe to continue until blocking issues are fixed.') + '</div>'
      + '</div>',
      '<div style="grid-column:1 / -1; border:1px solid rgba(245,221,176,0.26); border-radius:6px; padding:10px; background:rgba(0,0,0,0.16);">'
        + '<div style="font-family:Cinzel, serif; font-size:0.7rem; letter-spacing:0.08em; text-transform:uppercase; color:' + quality.tone + ';">Import quality: ' + escapeHtml(quality.label) + '</div>'
        + '<div style="margin-top:4px; font-size:0.86rem; color:#e8dcc8; opacity:0.9;">' + escapeHtml(quality.detail) + '</div>'
      + '</div>',
      renderSummaryCard('Character name', summaryData.name),
      renderSummaryCard('Class/level', summaryData.classLevel),
      renderSummaryCard('Species', summaryData.species),
      renderSummaryCard('Background', summaryData.background),
      renderSummaryCard('Stats found', String(summaryData.statsFound) + '/6'),
      renderSummaryCard('Inventory count', String(summaryData.inventoryCount)),
      renderSummaryCard('Spell count', String(summaryData.spellCount)),
      renderSummaryCard('Actions/features count', String(summaryData.actionFeatureCount)),
    ].join('');

    const ac = reviewData.acComparison || {};
    const hp = reviewData.hpComparison || {};
    const reviewSections = [
      renderReviewSection('Character basics', [
        'Name: ' + escapeHtml(reviewData.characterName || summaryData.name),
        'Class: ' + escapeHtml(reviewData.class || summaryData.classLevel),
        'Subclass: ' + escapeHtml(reviewData.subclass || '—'),
        'Level: ' + escapeHtml(reviewData.level || ''),
        'Species/Race: ' + escapeHtml(reviewData.speciesRace || summaryData.species),
        'Background: ' + escapeHtml(reviewData.background || summaryData.background),
      ].filter(Boolean).join('<br>'), (reviewData.blockingIssues || []).length ? 'red' : 'green'),
      renderReviewSection('AC/HP', [
        'AC source/resolved: ' + escapeHtml((ac.source == null ? '—' : ac.source) + ' / ' + (ac.resolved == null ? '—' : ac.resolved) + ' (' + (ac.status || 'unknown') + ')'),
        'HP source/resolved: ' + escapeHtml((hp.source == null ? '—' : hp.source) + ' / ' + (hp.resolved == null ? '—' : hp.resolved) + ' (' + (hp.status || 'unknown') + ')'),
      ].join('<br>'), (reviewData.hasAC && reviewData.hasHP) ? 'green' : 'red'),
      renderReviewSection('Equipment', renderPillList(reviewData.itemsMatched, 'No matched equipment found.', 'green'), 'green'),
      renderReviewSection('Inventory', renderPillList(reviewData.itemsMissing, 'No missing inventory reported.', (reviewData.itemsMissing || []).length ? 'red' : 'green'), (reviewData.itemsMissing || []).length ? 'red' : 'green'),
      renderReviewSection('Spells', '<div>Matched:</div>' + renderPillList(reviewData.spellsMatched, 'No matched spells found.', 'green') + '<div style="margin-top:6px;">Missing / unmatched:</div>' + renderPillList(reviewData.spellsMissing, 'No missing spells reported.', (reviewData.spellsMissing || []).length ? 'yellow' : 'green'), (reviewData.spellsMissing || []).length ? 'yellow' : 'green'),
      renderReviewSection('Features', '<div>Matched:</div>' + renderPillList(reviewData.featuresMatched, 'No matched features found.', 'green') + '<div style="margin-top:6px;">Missing / unmatched:</div>' + renderPillList(reviewData.featuresMissing, 'No missing features reported.', (reviewData.featuresMissing || []).length ? 'yellow' : 'green'), (reviewData.featuresMissing || []).length ? 'yellow' : 'green'),
      renderReviewSection('Warnings', renderPillList(reviewData.warnings, 'No warnings reported.', (reviewData.warnings || []).length ? 'yellow' : 'green'), (reviewData.warnings || []).length ? 'yellow' : 'green'),
      renderReviewSection('Blocking issues', renderPillList(reviewData.blockingIssues, 'No blocking issues.', (reviewData.blockingIssues || []).length ? 'red' : 'green'), (reviewData.blockingIssues || []).length ? 'red' : 'green'),
    ].join('');

    const warningsHtml = reviewSections + (items.length ? items.map(function renderRow(item, idx) {
      const resolutionKey = String(item.details && item.details.resolutionKey || '').trim();
      const options = Array.isArray(item.details && item.details.options) ? item.details.options : [];
      const resolutionControl = item.blocking && allowResolve && resolutionKey
        ? (
          '<div style="margin-top:6px;">'
          + '<label style="font-size:0.75rem; opacity:0.9;">Required choice:</label>'
          + (options.length
            ? ('<select data-resolution-key="' + resolutionKey.replace(/"/g, '&quot;') + '" data-warning-index="' + String(idx) + '"'
              + ' style="display:block; margin-top:4px; width:100%; background:#21190d; border:1px solid rgba(0,229,204,0.25); color:#e8dcc8; border-radius:4px; padding:6px;">'
              + '<option value="">Select…</option>'
              + options.map(function (opt) {
                const value = String(opt || '').trim();
                const esc = value.replace(/"/g, '&quot;');
                return '<option value="' + esc + '">' + value + '</option>';
              }).join('')
              + '</select>')
            : ('<input data-resolution-key="' + resolutionKey.replace(/"/g, '&quot;') + '" data-warning-index="' + String(idx) + '" placeholder="Type the required choice"'
              + ' style="display:block; margin-top:4px; width:100%; background:#21190d; border:1px solid rgba(0,229,204,0.25); color:#e8dcc8; border-radius:4px; padding:6px;" />'))
          + '</div>'
        )
        : '';
      return '<div style="border:1px solid rgba(245,221,176,0.2); border-radius:4px; padding:8px;">'
        + '<div style="font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:' + (item.blocking ? '#ffd6a2' : '#f5ddb0') + ';">'
        + (item.blocking ? 'Required fix' : 'Warning')
        + '</div>'
        + '<div style="margin-top:4px; line-height:1.35;">' + escapeHtml(item.message || item.code || 'Review this imported field.') + '</div>'
        + resolutionControl
        + '</div>';
    }).join('') : '<div style="border:1px solid rgba(0,229,204,0.16); border-radius:4px; padding:8px; color:#a9ffe7;">No legacy warning rows found.</div>');

    reviewList.innerHTML = warningsHtml;
    actionRow.style.display = (allowResolve && hasBlocking) ? 'flex' : 'none';
    saveBtn.style.display = (!hasBlocking && reviewData.canContinueToPlay) ? '' : 'none';
    const reviewLaterBtn = root.querySelector('#character-import-review-later-btn');
    if (reviewLaterBtn) reviewLaterBtn.style.display = (!hasBlocking && reviewData.canReviewLater) ? 'inline-block' : 'none';
    const debugWrap = root.querySelector('#character-import-debug-wrap');
    const debugJson = root.querySelector('#character-import-debug-json');
    if (debugJson) debugJson.textContent = JSON.stringify(reviewData || {}, null, 2);
    if (debugWrap) debugWrap.style.display = 'none';
    if (finalActions) finalActions.style.display = 'flex';
    review.style.display = 'block';
  }

  function getPreviewDocument(payload) {
    if (!payload || typeof payload !== 'object') return {};
    const doc = payload.preview_document || payload.character_document || payload.document || payload.nativeCharacter;
    return doc && typeof doc === 'object' ? doc : {};
  }

  function getReviewItems(payload) {
    const seen = new Set();
    const rows = [];
    function add(item) {
      const normalized = normalizeWarningItem(item);
      const key = [normalized.code, normalized.message, normalized.blocking ? '1' : '0'].join('|');
      if (seen.has(key)) return;
      seen.add(key);
      rows.push(normalized);
    }
    (Array.isArray(payload && payload.warnings) ? payload.warnings : []).forEach(add);
    (Array.isArray(payload && payload.required_choices) ? payload.required_choices : []).forEach(function (item) {
      if (item && typeof item === 'object') add(Object.assign({}, item, { blocking: true }));
      else add({ message: item, blocking: true });
    });
    return rows;
  }

  function open(config) {
    const cfg = Object.assign({
      sessionId: '',
      onImported: null,
      onPreview: null,
      onEditBeforeSave: null,
      onClose: null,
      initialMethod: '',
      autoCloseOnImported: false,
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
    const resolveSaveBtn = root.querySelector('#character-import-resolve-save-btn');
    const saveBtn = root.querySelector('#character-import-save-btn');
    const editBtn = root.querySelector('#character-import-edit-btn');
    const reviewLaterBtn = root.querySelector('#character-import-review-later-btn');
    const debugBtn = root.querySelector('#character-import-debug-btn');
    const editWrap = root.querySelector('#character-import-edit-wrap');
    const editJson = root.querySelector('#character-import-edit-json');

    const sessionId = getSessionId(cfg.sessionId);
    let pendingPreview = null;
    let pendingCommitter = null;
    let pendingResolver = null;
    let activePdfPreviewUrl = '';
    let pendingImport = null;

    function clearPdfPreview() {
      if (pdfPreviewHost) pdfPreviewHost.innerHTML = '';
      if (pdfPreviewWrap) pdfPreviewWrap.style.display = 'none';
      if (activePdfPreviewUrl) {
        try { URL.revokeObjectURL(activePdfPreviewUrl); } catch (_) {}
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

    function resetPending() {
      pendingPreview = null;
      pendingCommitter = null;
      pendingResolver = null;
      if (editWrap) editWrap.style.display = 'none';
      if (editJson) editJson.value = '';
      if (saveBtn) saveBtn.onclick = null;
      if (editBtn) editBtn.onclick = null;
      if (reviewLaterBtn) reviewLaterBtn.onclick = null;
      if (debugBtn) debugBtn.onclick = null;
      if (resolveSaveBtn) resolveSaveBtn.onclick = null;
    }

    function setActionVisibility(hasBlocking, hasPreview) {
      const actionRow = root.querySelector('#character-import-resolution-actions');
      if (!actionRow) return;
      actionRow.style.display = (hasBlocking || hasPreview) ? 'flex' : 'none';
      if (resolveSaveBtn) resolveSaveBtn.style.display = hasBlocking ? 'inline-block' : 'none';
      const reviewData = importReviewFromPayload(pendingPreview || {});
      if (saveBtn) saveBtn.style.display = (!hasBlocking && hasPreview && reviewData.canContinueToPlay) ? 'inline-block' : 'none';
      if (editBtn) editBtn.style.display = (!hasBlocking && hasPreview) ? 'inline-block' : 'none';
      if (reviewLaterBtn) reviewLaterBtn.style.display = (!hasBlocking && hasPreview && reviewData.canReviewLater) ? 'inline-block' : 'none';
      if (debugBtn) debugBtn.style.display = hasPreview ? 'inline-block' : 'none';
    }

    function renderPreviewReview(payload, committer, resolver) {
      const review = root.querySelector('#character-import-review');
      const reviewList = root.querySelector('#character-import-review-list');
      const items = getReviewItems(payload);
      const hasBlocking = items.some(function (item) { return item.blocking; }) || Boolean(payload && payload.requires_resolution);
      const doc = getPreviewDocument(payload);
      const identity = doc && doc.identity && typeof doc.identity === 'object' ? doc.identity : {};
      const classes = Array.isArray(doc && doc.classes) ? doc.classes : [];
      const primaryClass = classes[0] && typeof classes[0] === 'object' ? classes[0] : {};
      const species = doc && doc.species && typeof doc.species === 'object' ? doc.species : {};
      const summaryRow = {
        code: 'preview_ready',
        message: 'Preview ready: ' + [
          String(identity.name || identity.displayName || doc.name || 'Imported Hero').trim(),
          String(species.name || species.id || '').trim(),
          String(primaryClass.name || primaryClass.classId || '').trim(),
          primaryClass.level ? ('Level ' + primaryClass.level) : '',
        ].filter(Boolean).join(' · '),
        blocking: false,
        details: {},
      };
      const rows = [summaryRow].concat(items);
      if (review && reviewList) {
        reviewList.innerHTML = '';
        renderReview(root, payload, Boolean(resolver));
        review.style.display = 'block';
      }
      pendingPreview = payload;
      pendingCommitter = committer;
      pendingResolver = resolver;
      setActionVisibility(hasBlocking, true);
      if (resolveSaveBtn) resolveSaveBtn.onclick = pendingResolver;
      if (saveBtn) saveBtn.onclick = savePendingPreview;
      if (reviewLaterBtn) reviewLaterBtn.onclick = savePendingPreview;
      if (debugBtn) debugBtn.onclick = toggleReviewDebug;
      if (editBtn) editBtn.onclick = openBuilderForPendingPreview;
      if (typeof cfg.onPreview === 'function') cfg.onPreview(payload);
      setStatus(root, hasBlocking ? 'Import preview needs required choices before saving.' : 'Import review is ready. Continue to Play, Review Later when allowed, or edit before saving.', hasBlocking ? 'error' : 'success');
    }

    function toggleReviewDebug() {
      const debugWrap = root.querySelector('#character-import-debug-wrap');
      if (!debugWrap) return;
      const isOpen = debugWrap.style.display !== 'none';
      debugWrap.style.display = isOpen ? 'none' : 'block';
      if (debugBtn) debugBtn.textContent = isOpen ? 'Show Review JSON' : 'Hide Review JSON';
    }

    async function savePendingPreview() {
      if (!pendingCommitter) return;
      let editedDoc = null;
      if (editWrap && editWrap.style.display !== 'none' && editJson && String(editJson.value || '').trim()) {
        try {
          editedDoc = JSON.parse(editJson.value);
        } catch (_) {
          setStatus(root, 'Edited character JSON is invalid.', 'error');
          return;
        }
      }
      try {
        setStatus(root, 'Continuing with imported character…', 'info');
        const result = await pendingCommitter(editedDoc || getPreviewDocument(pendingPreview));
        setStatus(root, 'Imported character saved; you can continue to play.', 'success');
        if (typeof cfg.onImported === 'function') await cfg.onImported(result);
        if (cfg.autoCloseOnImported) close();
      } catch (err) {
        setStatus(root, friendlyErrorMessage(err && err.message || 'Imported character save failed.'), 'error');
      }
    }

    function toggleEditPreview() {
      if (!editWrap || !editJson) return;
      const isOpen = editWrap.style.display !== 'none';
      if (isOpen) {
        editWrap.style.display = 'none';
        if (editBtn) editBtn.textContent = 'Edit Before Saving';
        return;
      }
      editJson.value = JSON.stringify(getPreviewDocument(pendingPreview), null, 2);
      editWrap.style.display = 'block';
      if (editBtn) editBtn.textContent = 'Hide Raw JSON';
    }

    async function openBuilderForPendingPreview() {
      const doc = getPreviewDocument(pendingPreview);
      if (!doc || typeof doc !== 'object' || Object.keys(doc).length === 0) {
        setStatus(root, 'No import preview is available to edit.', 'error');
        return;
      }
      if (typeof cfg.onEditBeforeSave !== 'function') {
        toggleEditPreview();
        return;
      }
      try {
        setStatus(root, 'Opening native character builder with imported fields…', 'info');
        await cfg.onEditBeforeSave(doc, pendingPreview);
        close();
      } catch (err) {
        setStatus(root, friendlyErrorMessage(err && err.message || 'Unable to open the character builder.'), 'error');
      }
    }

    function jsonCommitter(source) {
      return function commitJson(previewDocument) {
        return postJson(source === 'ddb-id' ? '/api/character/import/ddb-id/commit' : '/api/character/import/json/commit', {
          session_id: sessionId,
          preview_document: previewDocument,
        });
      };
    }

    function pdfCommitter() {
      return function commitPdf(previewDocument) {
        const fd = new FormData();
        fd.set('session_id', sessionId);
        fd.set('preview_document', JSON.stringify(previewDocument || {}));
        return postForm('/api/character/import/pdf/commit', fd);
      };
    }

    function buildResolutionAndPreview(buildRequest) {
      return async function onResolveRetry() {
        if (typeof buildRequest !== 'function') return;
        const controls = Array.from(root.querySelectorAll('[data-resolution-key]'));
        const resolution = {};
        for (const sel of controls) {
          const key = String(sel && sel.getAttribute('data-resolution-key') || '').trim().toLowerCase();
          const value = String(sel && sel.value || '').trim();
          if (!key) continue;
          if (!value) {
            setStatus(root, 'Resolve all required choices before continuing.', 'error');
            return;
          }
          resolution[key] = value;
        }
        try {
          setStatus(root, 'Refreshing import preview with selected choices…', 'info');
          const req = buildRequest(resolution);
          const preview = req.formData ? await postForm(req.url, req.formData) : await postJson(req.url, req.body);
          renderPreviewReview(preview, req.committer, buildResolutionAndPreview(buildRequest));
        } catch (err) {
          setStatus(root, friendlyErrorMessage(err && err.message || 'Import preview failed.'), 'error');
        }
      };
    }

    async function previewDdbId() {
      const characterId = String(ddbIdInput && ddbIdInput.value || '').trim();
      if (!sessionId) return setStatus(root, 'Missing session_id in join URL.', 'error');
      if (!characterId) return setStatus(root, 'Enter a D&D Beyond character ID first.', 'error');
      setStatus(root, 'Building D&D Beyond import preview…', 'info');
      clearReview(root);
      resetPending();
      try {
        const buildRequest = function (resolution) {
          return {
            url: '/api/character/import/ddb-id/preview',
            body: { session_id: sessionId, character_id: characterId, import_resolution: resolution || {} },
            committer: jsonCommitter('ddb-id'),
          };
        };
        const req = buildRequest({});
        const preview = await postJson(req.url, req.body);
        renderPreviewReview(preview, req.committer, buildResolutionAndPreview(buildRequest));
      } catch (err) {
        setStatus(root, friendlyErrorMessage(err && err.message || 'Import preview failed.'), 'error');
      }
    }

    async function previewJsonPayload(parsed, successSource) {
      if (!sessionId) return setStatus(root, 'Missing session_id in join URL.', 'error');
      setStatus(root, 'Building JSON import preview…', 'info');
      clearReview(root);
      resetPending();
      try {
        const buildRequest = function (resolution) {
          return {
            url: '/api/character/import/json/preview',
            body: { session_id: sessionId, ddb_json: parsed, import_resolution: resolution || {} },
            committer: jsonCommitter('json'),
            successSource,
          };
        };
        const req = buildRequest({});
        const preview = await postJson(req.url, req.body);
        renderPreviewReview(preview, req.committer, buildResolutionAndPreview(buildRequest));
      } catch (err) {
        setStatus(root, friendlyErrorMessage(err && err.message || 'Import preview failed.'), 'error');
      }
    }

    async function previewPdfFile(file) {
      if (!sessionId) return setStatus(root, 'Missing session_id in join URL.', 'error');
      setStatus(root, 'Uploading PDF for import preview…', 'info');
      clearReview(root);
      resetPending();
      try {
        const buildRequest = function () {
          const fd = new FormData();
          fd.set('session_id', sessionId);
          fd.set('file', file);
          return { url: '/api/character/import/pdf/preview', formData: fd, committer: pdfCommitter() };
        };
        const req = buildRequest({});
        const preview = await postForm(req.url, req.formData);
        renderPreviewReview(preview, req.committer, null);
      } catch (err) {
        setStatus(root, friendlyErrorMessage(err && err.message || 'PDF import preview failed.'), 'error');
      }
    }

    if (closeBtn) closeBtn.onclick = close;
    if (pdfPreviewClearBtn) pdfPreviewClearBtn.onclick = clearPdfPreview;
    root.onclick = function onRootClick(event) { if (event.target === root) close(); };
    if (ddbIdBtn) ddbIdBtn.onclick = previewDdbId;
    if (jsonBtn) {
      jsonBtn.onclick = async function onPreviewJsonText() {
        const raw = String(jsonText && jsonText.value || '').trim();
        if (!raw) return setStatus(root, 'Paste JSON first.', 'error');
        try { await previewJsonPayload(JSON.parse(raw), 'pasted JSON'); }
        catch (_) { setStatus(root, friendlyErrorMessage('Invalid JSON payload.'), 'error'); }
      };
    }
    if (jsonFileInput) {
      jsonFileInput.onchange = async function onJsonFileChange() {
        const file = jsonFileInput.files && jsonFileInput.files[0];
        if (!file) return;
        try {
          const parsed = JSON.parse(await file.text());
          await previewJsonPayload(parsed, 'JSON file');
        } catch (err) {
          setStatus(root, friendlyErrorMessage(err && err.message || 'JSON file preview failed.'), 'error');
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
        await previewPdfFile(file);
        pdfFileInput.value = '';
      };
    }

    setStatus(root, '', 'info');
    clearReview(root);
    resetPending();
    setActionVisibility(false, false);
    root.style.pointerEvents = 'auto';
    root.style.display = 'flex';

    const initial = String(cfg.initialMethod || '').trim().toLowerCase();
    setTimeout(function focusInitialMethod() {
      if (initial === 'ddb-id' && ddbIdInput) ddbIdInput.focus();
      if (initial === 'paste-json' && jsonText) jsonText.focus();
      if (initial === 'upload-json' && jsonFileInput) jsonFileInput.click();
      if (initial === 'upload-pdf' && pdfFileInput) pdfFileInput.click();
    }, 0);
  }

  global.CharacterImportModal = {
    open,
  };
})(window);
