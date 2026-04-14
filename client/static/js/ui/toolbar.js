(function(){
  const FLYOUT_IDS = ['flyout-dice','flyout-ruler','flyout-spell','flyout-token','flyout-char','flyout-journal','flyout-editor','flyout-map','flyout-perm','flyout-fog','flyout-sound','flyout-cart'];
  const FLYOUT_BTN_MAP = {
    'flyout-dice': 'rail-dice-btn',
    'flyout-ruler': 'tool-ruler',
    'flyout-spell': 'tool-spell',
    'flyout-token': 'rail-token-btn',
    'flyout-char': 'rail-char-btn',
    'flyout-journal': 'rail-journal-btn',
    'flyout-editor': 'rail-editor-btn',
    'flyout-map': 'rail-map-btn',
    'flyout-perm': 'rail-perm-btn',
    'flyout-fog': 'rail-fog-btn',
    'flyout-sound': 'rail-sound-btn',
    'flyout-cart': 'rail-cart-btn',
  };

  function closeAllFlyouts(env) {
    FLYOUT_IDS.forEach((id) => env.document.getElementById(id)?.classList.remove('open'));
    Object.values(FLYOUT_BTN_MAP).forEach((btnId) => env.document.getElementById(btnId)?.classList.remove('active'));
  }

  function toggleFlyout(env, id) {
    const el = env.document.getElementById(id);
    if (!el) return;
    const isOpen = el.classList.contains('open');
    closeAllFlyouts(env);
    if (isOpen) return;
    el.classList.add('open');
    const btn = env.document.getElementById(FLYOUT_BTN_MAP[id]);
    if (btn) btn.classList.add('active');
    if (id === 'flyout-fog') {
      ['select','ruler','ping','spell','poi'].forEach((t) => env.document.getElementById(`tool-${t}`)?.classList.remove('active'));
    }
    if (id === 'flyout-editor') {
      env.ensureEditorLayerLoaded(true);
      env.ensureEditorWallsLoaded(true);
      env.ensureEditorPropsLoaded(true);
      env.setEditorMode(env.getEditorPaintMode());
      env.setEditorTerrain(env.getEditorTerrain());
      env.setEditorBrush(env.getEditorBrush());
      env.setEditorPropKind(env.getEditorPropKind());
      env.setEditorPropSize(env.getEditorPropSize());
    }
  }

  function bindCanvasFlyoutClose(env) {
    const wrap = env.document.getElementById('canvas-wrap');
    if (!wrap || wrap.dataset.flyoutCloseBound === '1') return;
    wrap.dataset.flyoutCloseBound = '1';
    wrap.addEventListener('mousedown', (e) => {
      if (e.target === wrap || e.target.id === 'map-canvas') {
        if (env.document.getElementById('flyout-editor')?.classList.contains('open')) return;
        const fogFlyoutOpen = env.document.getElementById('flyout-fog')?.classList.contains('open');
        const fogMode = String((typeof env.getFogSystemMode === 'function' ? env.getFogSystemMode() : '') || '').toLowerCase();
        if (fogFlyoutOpen && env.ROLE === 'dm' && !!env.fogEnabled && (fogMode === 'manual' || fogMode === 'hybrid')) return;
        closeAllFlyouts(env);
      }
    });
  }


  function applyRoleVisibility(env) {
    if (env.ROLE === 'dm') {
      env.document.getElementById('rail-token-btn')?.style.setProperty('display', 'flex');
      env.document.getElementById('rail-map-btn')?.style.setProperty('display', 'flex');
      env.document.getElementById('rail-perm-btn')?.style.setProperty('display', 'flex');
      env.document.getElementById('tool-poi')?.style.setProperty('display', 'flex');
      env.document.getElementById('save-btn')?.style.setProperty('display', 'block');
      env.document.getElementById('rail-fog-btn')?.style.setProperty('display', 'flex');
      env.document.getElementById('rail-library-btn')?.style.setProperty('display', 'flex');
      env.document.getElementById('rail-editor-btn')?.style.setProperty('display', 'flex');
      env.document.getElementById('perm-panel')?.classList.add('visible');
      env.buildColorSwatches();
      const fogChk = env.document.getElementById('fog-enable-chk');
      if (fogChk && fogChk.dataset.boundChange !== '1') {
        fogChk.dataset.boundChange = '1';
        fogChk.addEventListener('change', env.onFogToggleChange);
      }
    }

    if (env.ROLE === 'viewer') {
      env.document.getElementById('tool-ruler')?.style.setProperty('display', 'none');
      env.document.getElementById('tool-ping')?.style.setProperty('display', 'none');
      env.document.getElementById('tool-spell')?.style.setProperty('display', 'none');
    }
  }

  function bindToolbarControls(env) {
    const scaleInput = env.document.getElementById('ruler-scale-val');
    if (scaleInput && scaleInput.dataset.boundInput !== '1') {
      scaleInput.dataset.boundInput = '1';
      scaleInput.addEventListener('input', () => {
        env.setRulerScale(parseFloat(scaleInput.value) || 1);
      });
    }
  }

  function setRulerDiagonalRule(env, rule) {
    const nextRule = rule === 'straight' ? 'straight' : '5e';
    env.setRulerDiagonalRuleState(nextRule);
    env.document.getElementById('diag-straight')?.classList.toggle('active', nextRule === 'straight');
    env.document.getElementById('diag-5e')?.classList.toggle('active', nextRule === '5e');
  }

  function setTool(env, tool) {
    if (env.ROLE === 'viewer' && ['ruler', 'ping', 'spell', 'poi'].includes(tool)) return;
    if (tool !== 'spell') {
      env.setSpellDraft(null);
      const markers = env.getSpellMarkers();
      if (Array.isArray(markers) && markers.length > 0) {
        env.setSpellMarkers([]);
        env.sendWS({ type: 'spell_marker_clear', payload: {} });
      }
    }
    env.setCurrentTool(tool);
    env.setStoreTool(tool);
    ['select','ruler','ping','spell','poi'].forEach((t) => {
      env.document.getElementById(`tool-${t}`)?.classList.toggle('active', t === tool);
    });
    if (['ruler','ping','spell','poi'].includes(tool)) env.closeAllFlyouts();
    if (env.wrap) {
      env.wrap.className = tool === 'select' ? 'tool-select' : tool === 'ping' ? 'tool-grab' : '';
    }
    env.closePoiPopup();
    if (tool !== 'ruler' && env.ruler) {
      env.ruler.active = false;
      env.ruler.phase = 'idle';
      const readout = env.document.getElementById('ruler-readout');
      if (readout) readout.style.display = 'none';
    }
    if (tool === 'ruler') env.toggleFlyout('flyout-ruler');
    if (tool === 'spell') {
      env.toggleFlyout('flyout-spell');
      updateSpellTip(env);
      env.initJournalUI();
    }
  }

  function setRulerUnit(env, unit) {
    env.setRulerUnitState(unit);
    env.document.getElementById('unit-ft')?.classList.toggle('active', unit === 'ft');
    env.document.getElementById('unit-miles')?.classList.toggle('active', unit === 'miles');
    const scaleInput = env.document.getElementById('ruler-scale-val');
    const scaleLabel = env.document.getElementById('ruler-scale-unit-label');
    if (!scaleInput || !scaleLabel) return;
    if (unit === 'ft') {
      scaleInput.value = 5;
      env.setRulerScale(5);
      scaleLabel.textContent = 'ft/sq';
    } else {
      if (env.getRulerScale() < 10) {
        scaleInput.value = 100;
        env.setRulerScale(100);
      }
      scaleLabel.textContent = 'mi/sq';
      env.showToast('Adjust mi/sq to match your map scale bar');
    }
  }

  function updateSpellTip(env) {
    const shape = env.SPELL_SHAPES[env.getSpellShapeIdx()];
    const labels = { circle: 'Circle', cone: 'Cone', line: 'Line', square: 'Square', cube: 'Cube' };
    const icons = { circle: '🔮', cone: '📐', line: '📏', square: '◻️', cube: '🧊' };
    const tip = env.document.getElementById('spell-tool-tip');
    if (tip) tip.textContent = 'Spell: ' + labels[shape];
    const btn = env.document.getElementById('tool-spell');
    if (btn && btn.childNodes[0]) btn.childNodes[0].textContent = (icons[shape] || '🔮') + '​';
    ['circle','cone','line','square','cube'].forEach((k) => env.document.getElementById(`spell-shape-${k}`)?.classList.toggle('active', k === shape));
    renderSpellPresets(env);
  }

  function selectSpellTool(env) {
    if (env.ROLE === 'viewer') return;
    if (env.getCurrentTool() === 'spell') {
      env.setSpellShapeIdx((env.getSpellShapeIdx() + 1) % env.SPELL_SHAPES.length);
    }
    setTool(env, 'spell');
    updateSpellTip(env);
    env.initJournalUI();
  }

  function setSpellShape(env, shape) {
    const idx = env.SPELL_SHAPES.indexOf(shape);
    if (idx >= 0) env.setSpellShapeIdx(idx);
    updateSpellTip(env);
    env.initJournalUI();
  }

  function renderSpellPresets(env) {
    const wrap = env.document.getElementById('spell-preset-wrap');
    const label = env.document.getElementById('spell-preset-label');
    if (!wrap || !label) return;
    const shape = env.SPELL_SHAPES[env.getSpellShapeIdx()];
    const values = env.SPELL_PRESETS[shape] || [];
    wrap.innerHTML = '';
    values.forEach((ft) => {
      const btn = env.document.createElement('button');
      btn.type = 'button';
      btn.className = 'mini-btn' + (env.getSpellPresetFt() === ft ? ' active' : '');
      btn.textContent = `${ft} ft`;
      btn.onclick = () => setSpellPreset(env, ft);
      wrap.appendChild(btn);
    });
    label.textContent = 'Preset: ' + (env.getSpellPresetFt() ? `${env.getSpellPresetFt()} ft` : 'Off');
  }

  function setSpellPreset(env, ft) {
    env.setSpellPresetFt(Number(ft) || null);
    renderSpellPresets(env);
  }

  function clearSpellPreset(env) {
    env.setSpellPresetFt(null);
    renderSpellPresets(env);
  }

  window.AppUIToolbar = {
    toggleFlyout,
    closeAllFlyouts,
    bindCanvasFlyoutClose,
    applyRoleVisibility,
    bindToolbarControls,
    setTool,
    setRulerUnit,
    setRulerDiagonalRule,
    selectSpellTool,
    updateSpellTip,
    setSpellShape,
    renderSpellPresets,
    setSpellPreset,
    clearSpellPreset,
  };
})();
