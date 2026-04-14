(function initCharacterBuilderShell(global) {
  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function checkForPersistedDraft() {
    var CBS = global.CharacterBuilderState;
    if (CBS && typeof CBS.getPersistedDraft === 'function') {
      return CBS.getPersistedDraft();
    }
    return null;
  }

  function getStepModule(stepId) {
    const registry = global.CharacterBuilderStepModules;
    if (!registry || typeof registry !== 'object') return null;
    const mod = registry[stepId];
    return mod && typeof mod.render === 'function' ? mod : null;
  }

  function renderStepBody(stepId, snapshot) {
    const stepModule = getStepModule(stepId);
    if (!stepModule) {
      return '<div class="loading-msg" style="text-align:left;padding:0;">Step module unavailable for <strong>'
        + escHtml(stepId)
        + '</strong>.</div>';
    }
    return stepModule.render(snapshot);
  }



  function getRoadmapRows(snapshot) {
    var draft = snapshot && snapshot.draft && typeof snapshot.draft === 'object' ? snapshot.draft : {};
    var classData = draft.class && typeof draft.class === 'object' ? draft.class : {};
    var classId = String(classData.id || '').trim().toLowerCase();
    var progression = draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
    var level = parseInt(progression.level, 10);
    var startLevel = Number.isFinite(level) && level > 0 ? level : 1;

    var api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') {
      return { className: '', startLevel: startLevel, rows: [] };
    }
    var catalog = api.getCachedCatalog();
    var classes = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    var classRow = classes.find(function findRow(row) {
      return String(row && row.id || '').trim().toLowerCase() === classId;
    }) || null;
    if (!classRow) {
      return { className: '', startLevel: startLevel, rows: [] };
    }

    var table = Array.isArray(classRow.progressionTable) ? classRow.progressionTable : [];
    var rows = [];
    for (var i = 0; i < 5; i += 1) {
      var nextLevel = Math.min(startLevel + i, 20);
      var row = table.find(function findLevel(entry) {
        return parseInt(entry && entry.level, 10) === nextLevel;
      }) || null;
      var features = row && Array.isArray(row.features) && row.features.length
        ? row.features.join(', ')
        : '—';
      var lower = String(features || '').toLowerCase();
      rows.push({
        level: nextLevel,
        features: features,
        isCurrent: nextLevel === startLevel,
        isAsi: lower.includes('ability score improvement') || lower.includes(' feat') || lower.includes('epic boon'),
      });
      if (nextLevel >= 20) break;
    }

    return {
      className: String(classRow.displayName || classRow.id || '').trim(),
      startLevel: startLevel,
      rows: rows,
    };
  }

  function inferTooltipKey(stepId, labelText) {
    var lower = String(labelText || '').trim().toLowerCase();
    if (lower.includes('species')) return 'species';
    if (lower.includes('class')) return 'class';
    if (lower.includes('subclass')) return 'subclass';
    if (lower.includes('ability')) return 'abilities';
    if (lower.includes('standard array')) return 'standard-array';
    if (lower.includes('point buy')) return 'point-buy';
    if (lower.includes('feat')) return 'feat';
    if (lower.includes('spellcasting') || lower.includes('spell')) return 'spellcasting';
    if (lower.includes('saving throw')) return 'saving-throws';
    if (lower.includes('hit die')) return 'hit-die';
    if (lower.includes('proficiency')) return 'proficiency-bonus';

    if (stepId === 'species') return 'species';
    if (stepId === 'class') return 'class';
    if (stepId === 'abilities') return 'abilities';
    if (stepId === 'subclass') return 'subclass';
    if (stepId === 'progression') return 'asi';
    if (stepId === 'spells') return 'spellcasting';
    return 'builder-basics';
  }

  function wireTooltipButtons(root, stepId) {
    root.querySelectorAll('.field > label').forEach(function attachTooltip(labelEl) {
      if (labelEl.querySelector('.builder-tooltip-btn')) return;
      var key = String(labelEl.dataset.builderTooltip || inferTooltipKey(stepId, labelEl.textContent) || '').trim();
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'builder-tooltip-btn';
      btn.textContent = '?';
      btn.setAttribute('aria-label', 'What\'s this?');
      btn.dataset.builderTooltipKey = key;
      btn.addEventListener('click', function onTipClick(evt) {
        evt.preventDefault();
        evt.stopPropagation();
        if (global.BuilderTooltips && typeof global.BuilderTooltips.showTooltip === 'function') {
          global.BuilderTooltips.showTooltip(key);
        }
      });
      labelEl.appendChild(btn);
    });
  }

  function applyInputBindings(root, state) {
    root.querySelectorAll('[data-builder-path]').forEach((inputEl) => {
      inputEl.addEventListener('input', function onInput() {
        const rawPath = String(inputEl.dataset.builderPath || '').trim();
        if (!rawPath) return;
        const path = rawPath.split('.').filter(Boolean);
        if (!path.length) return;

        let value = inputEl.value;
        if (inputEl.type === 'number') {
          const parsed = parseInt(value, 10);
          value = Number.isFinite(parsed) ? parsed : '';
        }

        state.setField(path, value);
      });
    });
  }

  function getFocusableSnapshot(root) {
    const active = document.activeElement;
    if (!active || !root.contains(active)) return null;
    const path = String(active.dataset && active.dataset.builderPath || '').trim();
    if (!path) return null;
    const snapshot = { path };
    if (typeof active.selectionStart === 'number') snapshot.selectionStart = active.selectionStart;
    if (typeof active.selectionEnd === 'number') snapshot.selectionEnd = active.selectionEnd;
    return snapshot;
  }

  function restoreFocusableSnapshot(root, snapshot) {
    if (!snapshot || !snapshot.path) return;
    const selector = '[data-builder-path="' + snapshot.path.replace(/"/g, '\\"') + '"]';
    const target = root.querySelector(selector);
    if (!target || typeof target.focus !== 'function') return;
    target.focus({ preventScroll: true });
    if (
      typeof snapshot.selectionStart === 'number'
      && typeof snapshot.selectionEnd === 'number'
      && typeof target.setSelectionRange === 'function'
    ) {
      target.setSelectionRange(snapshot.selectionStart, snapshot.selectionEnd);
    }
  }

  function ensureShellStyles() {
    if (document.getElementById('character-builder-shell-style')) return;
    const style = document.createElement('style');
    style.id = 'character-builder-shell-style';
    style.textContent = [
      /* ── Shell Container ── */
      '.character-builder-shell { margin-top: 14px; border: 1px solid rgba(201,168,76,0.28); border-radius: 12px; padding: 16px 18px; background: linear-gradient(180deg, rgba(11,14,18,0.96), rgba(8,11,15,0.98)); box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(255,255,255,0.02); }',

      /* ── Shell Branding Header ── */
      '.character-builder-shell .cb-shell-branding { display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid rgba(201,168,76,0.15); }',
      '.character-builder-shell .cb-shell-badge { width:32px; height:32px; border-radius:8px; background:linear-gradient(135deg,rgba(201,168,76,0.18),rgba(0,212,184,0.1)); border:1px solid rgba(201,168,76,0.35); display:flex; align-items:center; justify-content:center; font-size:1rem; color:#C9A84C; flex-shrink:0; }',
      '.character-builder-shell .cb-shell-title-text { font-family:"Cinzel",serif; font-size:0.82rem; font-weight:600; letter-spacing:0.07em; color:#E8C97A; }',
      '.character-builder-shell .cb-shell-title-sub { font-size:0.58rem; color:rgba(107,98,88,0.9); letter-spacing:0.03em; margin-top:1px; }',

      /* ── Field Styles ── */
      '.character-builder-shell .field { margin-bottom: 10px; }',
      '.character-builder-shell .field label { display: flex; align-items: center; gap: 4px; font-family:"Cinzel",serif; font-size: 0.66rem; letter-spacing:0.05em; margin-bottom: 5px; color: rgba(168,159,142,0.95); text-transform:uppercase; }',
      '.character-builder-shell input:not(.cb-input-hero), .character-builder-shell select, .character-builder-shell textarea { width: 100%; border-radius: 7px; border: 1px solid rgba(42,51,64,0.9); background: rgba(6,8,10,0.55); color: #e8e0d0; padding: 8px 10px; font-family:"Crimson Pro",serif; font-size:0.88rem; transition:border-color 0.2s,box-shadow 0.2s; outline:none; }',
      '.character-builder-shell input:not(.cb-input-hero):focus, .character-builder-shell select:focus, .character-builder-shell textarea:focus { border-color: rgba(201,168,76,0.55); box-shadow: 0 0 0 2px rgba(201,168,76,0.1); }',
      '.character-builder-shell input::placeholder, .character-builder-shell textarea::placeholder { color: rgba(107,98,88,0.7); }',
      '.character-builder-shell textarea { resize: vertical; min-height: 96px; }',

      /* ── Actions Row ── */
      '.character-builder-shell .builder-actions { display: flex; align-items:center; justify-content:space-between; gap: 8px; flex-wrap: wrap; margin-top: 12px; padding-top:10px; border-top:1px solid rgba(42,51,64,0.7); }',

      /* ── Error & Help ── */
      '.character-builder-shell .builder-error { color: #fc9090; font-size: 0.68rem; min-height: 18px; margin-top: 4px; font-style:italic; }',
      '.character-builder-shell .builder-help-text { margin-top: 6px; font-size: 0.64rem; color: rgba(107,98,88,0.85); }',

      /* ── Class Hint ── */
      '.character-builder-shell .builder-class-hint { margin: 8px 0 10px; border: 1px solid rgba(0,212,184,0.22); border-radius: 8px; background: rgba(0,212,184,0.06); padding: 9px 12px; font-size: 0.68rem; line-height: 1.5; color: rgba(213,249,244,0.88); }',

      /* ── Roadmap ── */
      '.character-builder-shell .builder-roadmap { margin-bottom: 12px; border: 1px solid rgba(201,168,76,0.18); border-radius: 9px; background: rgba(6,8,10,0.6); overflow:hidden; }',
      '.character-builder-shell .builder-roadmap-toggle { width: 100%; text-align: left; background: none; border: 0; color: #b09060; font-family: "Cinzel", serif; font-size: 0.68rem; letter-spacing: 0.05em; padding: 9px 12px; cursor: pointer; display:flex; align-items:center; justify-content:space-between; transition:color 0.2s; }',
      '.character-builder-shell .builder-roadmap-toggle:hover { color: #E8C97A; }',
      '.character-builder-shell .builder-roadmap-content { border-top: 1px solid rgba(201,168,76,0.14); padding: 8px 12px; }',
      '.character-builder-shell .roadmap-row { display: grid; grid-template-columns: 52px 1fr; gap: 8px; padding: 5px 0; font-size: 0.65rem; color: rgba(168,159,142,0.88); border-bottom:1px solid rgba(255,255,255,0.025); }',
      '.character-builder-shell .roadmap-row:last-child { border-bottom:none; }',
      '.character-builder-shell .roadmap-row.highlight .roadmap-level { color: #00D4B8; font-weight: 700; }',
      '.character-builder-shell .roadmap-row.asi .roadmap-features { color: #E8C97A; }',
      '.character-builder-shell .roadmap-level { color: rgba(0,212,184,0.75); font-family: "Share Tech Mono", monospace; }',

      /* ── Builder Meta ── */
      '.character-builder-shell .builder-meta { margin-top: 6px; font-size: 0.61rem; color: rgba(107,98,88,0.8); display:flex; align-items:center; gap:6px; }',

      /* ── Step Progress Track ── */
      '.character-builder-shell .step-track { padding-bottom: 44px; }',
      '.character-builder-shell .step-dot { width: 30px; height: 30px; }',
      '.character-builder-shell .step-label { font-size: 0.52rem; }',

      /* ── Step Counter ── */
      '.character-builder-shell .step-counter { font-size:0.63rem; color:rgba(107,98,88,0.85); font-family:"Cinzel",serif; letter-spacing:0.05em; text-align:center; }',

      /* ── Tooltip ── */
      '.builder-tooltip-btn { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(201,168,76,0.4); font-size: 0.55rem; color: rgba(201,168,76,0.7); cursor: pointer; margin-left: 4px; background: none; vertical-align: middle; transition:all 0.15s; }',
      '.builder-tooltip-btn:hover { border-color:rgba(201,168,76,0.8); color:rgba(201,168,76,1); background:rgba(201,168,76,0.08); }',
      '.builder-tooltip-panel { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(8,11,15,0.98); border: 1px solid rgba(201,168,76,0.35); border-radius: 12px; padding: 18px 20px; max-width: 360px; z-index: 9999; color: #e8e0d0; box-shadow:0 24px 60px rgba(0,0,0,0.7); }',
      '.builder-tooltip-title { font-family: "Cinzel", serif; font-size: 0.88rem; color: #E8C97A; margin-bottom: 10px; letter-spacing:0.04em; }',
      '.builder-tooltip-body { font-size: 0.72rem; line-height: 1.65; color: rgba(168,159,142,0.95); }',
      '.builder-tooltip-close { position: absolute; top: 10px; right: 12px; background: none; border: none; color: rgba(168,159,142,0.6); font-size: 1rem; cursor: pointer; transition:color 0.15s; }',
      '.builder-tooltip-close:hover { color:#E8C97A; }',

      /* ── Resume Draft Banner ── */
      '.character-builder-shell .cb-resume-banner { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-bottom:12px; padding:10px 14px; border:1px solid rgba(201,168,76,0.35); border-radius:8px; background:rgba(201,168,76,0.07); font-size:0.7rem; color:rgba(232,201,122,0.95); }',
      '.character-builder-shell .cb-resume-banner-text { flex:1; min-width:0; }',
      '.character-builder-shell .cb-resume-banner-actions { display:flex; gap:6px; flex-shrink:0; }',
      '.character-builder-shell .cb-resume-btn { padding:5px 10px; border-radius:6px; font-size:0.68rem; font-family:"Cinzel",serif; letter-spacing:0.04em; cursor:pointer; transition:all 0.15s; }',
      '.character-builder-shell .cb-resume-btn-yes { background:rgba(201,168,76,0.18); border:1px solid rgba(201,168,76,0.5); color:#E8C97A; }',
      '.character-builder-shell .cb-resume-btn-yes:hover { background:rgba(201,168,76,0.28); border-color:rgba(201,168,76,0.75); }',
      '.character-builder-shell .cb-resume-btn-no { background:none; border:1px solid rgba(107,98,88,0.4); color:rgba(107,98,88,0.9); }',
      '.character-builder-shell .cb-resume-btn-no:hover { border-color:rgba(107,98,88,0.7); color:rgba(168,159,142,0.9); }',
    ].join('\n');
    document.head.appendChild(style);
  }

  function createBuilderShell(config) {
    const cfg = Object.assign({
      mountEl: null,
      state: null,
      router: null,
      onClose: null,
      onSaveCharacter: null,
    }, config || {});

    const mountEl = cfg.mountEl;
    const state = cfg.state;
    const router = cfg.router;

    if (!mountEl || !state || !router) {
      return {
        open: function noop() {},
        close: function noop() {},
      };
    }

    ensureShellStyles();

    const root = document.createElement('section');
    root.className = 'character-builder-shell';
    root.style.display = 'none';
    mountEl.appendChild(root);

    let isOpen = false;
    let roadmapExpanded = false;
    let _bannerDismissed = false;

    async function runSaveCharacterHook() {
      const validation = typeof state.validateDraft === 'function' ? state.validateDraft() : { ok: true, issues: [] };
      if (!validation.ok) {
        return false;
      }

      const snapshot = state.getState();
      const draft = snapshot && snapshot.draft ? snapshot.draft : null;
      if (!draft) return false;

      if (typeof cfg.onSaveCharacter === 'function') {
        try {
          const maybePromise = cfg.onSaveCharacter(draft);
          if (maybePromise && typeof maybePromise.then === 'function') {
            await maybePromise;
          }
        } catch (_) {
          return false;
        }
      }

      state.saveDraftToMemory();
      if (global.CharacterBuilderState && typeof global.CharacterBuilderState.clearPersistedDraft === 'function') {
        global.CharacterBuilderState.clearPersistedDraft();
      }
      close();
      return true;
    }

    function renderStepProgress(steps, currentStepId) {
      var currentIndex = -1;
      for (var si = 0; si < steps.length; si++) {
        if (steps[si].id === currentStepId) { currentIndex = si; break; }
      }
      return [
        '<div class="step-track">',
        steps.map(function(step, i) {
          var isDone = i < currentIndex;
          var isActive = i === currentIndex;
          var dotClass = 'step-dot' + (isDone ? ' done' : isActive ? ' active' : '');
          var label = router && typeof router.getStepLabel === 'function'
            ? router.getStepLabel(step.id)
            : step.id;
          return [
            '<div class="step-item">',
            '<button class="' + dotClass + '" data-step-id="' + escHtml(step.id) + '">',
            isDone ? '' : String(i + 1),
            '<span class="step-label">' + escHtml(label) + '</span>',
            '</button>',
            i < steps.length - 1 ? '<div class="step-connector' + (isDone ? ' done' : '') + '"></div>' : '',
            '</div>',
          ].join('');
        }).join(''),
        '</div>',
        '<div class="step-progress-bar" style="width:' + (currentIndex / Math.max(1, steps.length - 1) * 100) + '%"></div>',
      ].join('');
    }

    function render(snapshot) {
      if (!isOpen) return;
      const focusSnapshot = getFocusableSnapshot(root);
      const stepOrder = Array.isArray(snapshot.stepOrder) ? snapshot.stepOrder : [];
      var stepItems = stepOrder.map(function(stepId) {
        return { id: stepId };
      });

      const onReview = snapshot.currentStepId === 'review';
      const roadmap = getRoadmapRows(snapshot);
      const roadmapRows = roadmap.rows.map(function toRoadmapRow(row) {
        var cls = [
          'roadmap-row',
          row.isCurrent ? 'highlight' : '',
          row.isAsi ? 'asi' : '',
        ].filter(Boolean).join(' ');
        return '<div class="' + cls + '"><span class="roadmap-level">Lv.' + escHtml(row.level) + '</span><span class="roadmap-features">' + escHtml(row.features) + '</span></div>';
      }).join('');

      var stepCounter = '';
      for (var sci = 0; sci < stepOrder.length; sci++) {
        if (stepOrder[sci] === snapshot.currentStepId) {
          stepCounter = 'Step <span style="color:var(--cb-gold,#C9A84C)">' + (sci + 1) + '</span> of ' + stepOrder.length;
          break;
        }
      }

      var draftName = (snapshot.draft && snapshot.draft.identity && snapshot.draft.identity.name)
        ? escHtml(String(snapshot.draft.identity.name).trim())
        : '';
      var metaDotClass = snapshot.isDirty ? 'cb-meta-dot dirty' : 'cb-meta-dot saved';
      var metaText = snapshot.isDirty ? 'Unsaved changes' : 'Draft saved';
      if (snapshot.saveStatus) metaText += ' · ' + snapshot.saveStatus;

      var isOnIdentityStep = snapshot.currentStepId === 'identity';
      var resumeBannerHtml = '';
      if (isOnIdentityStep && !_bannerDismissed) {
        var persistedDraft = checkForPersistedDraft();
        if (persistedDraft) {
          var savedName = persistedDraft.identity && String(persistedDraft.identity.name || '').trim();
          var savedClass = persistedDraft.class && String(persistedDraft.class.id || '').trim();
          var savedDesc = savedName ? escHtml(savedName) : (savedClass ? 'class: ' + escHtml(savedClass) : 'a previous draft');
          resumeBannerHtml = [
            '<div class="cb-resume-banner">',
            '<div class="cb-resume-banner-text">📄 Resume saved draft: <strong>' + savedDesc + '</strong>?</div>',
            '<div class="cb-resume-banner-actions">',
            '<button type="button" class="cb-resume-btn cb-resume-btn-yes" data-builder-action="resume-draft">Resume</button>',
            '<button type="button" class="cb-resume-btn cb-resume-btn-no" data-builder-action="discard-draft">Start Fresh</button>',
            '</div>',
            '</div>',
          ].join('');
        }
      }

      root.innerHTML = [
        // ── Branding Header ──
        '<div class="cb-shell-branding">',
        '<div class="cb-shell-badge">⚔</div>',
        '<div>',
        '<div class="cb-shell-title-text">Character Builder</div>',
        draftName
          ? '<div class="cb-shell-title-sub">' + draftName + '</div>'
          : '<div class="cb-shell-title-sub">Forge your legend</div>',
        '</div>',
        '</div>',

        // ── Step Progress ──
        renderStepProgress(stepItems, snapshot.currentStepId),

        // ── Level Roadmap ──
        '<div class="builder-roadmap">',
        '<button class="builder-roadmap-toggle" data-builder-roadmap-toggle="1">',
        'Level Roadmap',
        roadmap.className ? ' · ' + escHtml(roadmap.className) : '',
        roadmapExpanded ? ' ▲' : ' ▼',
        '</button>',
        '<div class="builder-roadmap-content"' + (roadmapExpanded ? '' : ' hidden') + '>',
        roadmap.rows.length
          ? roadmapRows
          : '<div class="builder-help-text" style="margin:0;font-size:0.63rem;">Choose a class to preview upcoming level features.</div>',
        '</div>',
        '</div>',

        // ── Step Body ──
        resumeBannerHtml,
        '<div class="builder-body">' + renderStepBody(snapshot.currentStepId, snapshot) + '</div>',

        // ── Validation Error ──
        snapshot.validationError
          ? '<div class="builder-error">' + escHtml(snapshot.validationError) + '</div>'
          : '',

        // ── Navigation Actions ──
        '<div class="builder-actions">',
        '<button class="btn-nav btn-prev" data-builder-action="back"'
          + (snapshot.currentStepIndex <= 0 ? ' style="visibility:hidden"' : '') + '>← Back</button>',
        '<div class="step-counter">' + stepCounter + '</div>',
        onReview
          ? '<button class="btn-nav btn-save" data-builder-action="save-character">⚔ Enter the World</button>'
          : '<button class="btn-nav btn-next" data-builder-action="next">Continue →</button>',
        '</div>',

        // ── Meta Bar ──
        '<div class="builder-meta">',
        '<div class="' + metaDotClass + '"></div>',
        '<span>' + metaText + '</span>',
        '</div>',
      ].join('');

      applyInputBindings(root, state);
      const stepModule = getStepModule(snapshot.currentStepId);
      if (stepModule && typeof stepModule.bind === 'function') {
        try {
          stepModule.bind(root, {
            draft: snapshot.draft,
            snapshot,
            onSetField: function onSetField(path, value) {
              state.setField(path, value);
            },
          });
        } catch (_) {
          // keep builder interactive even if optional bind hook fails
        }
      }

      wireTooltipButtons(root, snapshot.currentStepId);

      var roadmapToggle = root.querySelector('[data-builder-roadmap-toggle="1"]');
      if (roadmapToggle) {
        roadmapToggle.addEventListener('click', function onRoadmapToggle() {
          roadmapExpanded = !roadmapExpanded;
          var contentEl = root.querySelector('.builder-roadmap-content');
          if (contentEl) contentEl.hidden = !roadmapExpanded;
        });
      }

      // Wire step dot navigation
      root.querySelectorAll('.step-dot[data-step-id]').forEach(function(dotEl) {
        dotEl.addEventListener('click', function onStepDotClick() {
          var targetStepId = String(dotEl.dataset.stepId || '').trim();
          if (targetStepId && typeof state.setStep === 'function') {
            state.setStep(targetStepId);
          }
        });
      });

      restoreFocusableSnapshot(root, focusSnapshot);

      root.querySelectorAll('[data-builder-action]').forEach((buttonEl) => {
        buttonEl.addEventListener('click', function onActionClick() {
          const action = buttonEl.dataset.builderAction;
          if (action === 'resume-draft') {
            var draftToResume = checkForPersistedDraft();
            _bannerDismissed = true;
            if (draftToResume && typeof state.replaceDraft === 'function') {
              state.replaceDraft(draftToResume, { markDirty: true });
            }
            return;
          }
          if (action === 'discard-draft') {
            _bannerDismissed = true;
            if (global.CharacterBuilderState && typeof global.CharacterBuilderState.clearPersistedDraft === 'function') {
              global.CharacterBuilderState.clearPersistedDraft();
            }
            render(state.getState());
            return;
          }
          if (action === 'cancel') {
            close();
            return;
          }
          if (action === 'save') {
            state.saveDraftToMemory();
            return;
          }
          if (action === 'back') {
            state.previousStep();
            return;
          }
          if (action === 'save-character') {
            runSaveCharacterHook();
            return;
          }
          if (action === 'next') {
            state.nextStep();
          }
        });
      });
    }

    function open() {
      isOpen = true;
      _bannerDismissed = false;
      root.style.display = '';
      render(state.getState());
    }

    function close() {
      isOpen = false;
      root.style.display = 'none';
      if (typeof cfg.onClose === 'function') {
        cfg.onClose();
      }
    }

    state.subscribe(render);

    global.addEventListener('character-builder-catalog-updated', function onCatalogUpdated() {
      if (!isOpen) return;
      render(state.getState());
    });

    return {
      open,
      close,
    };
  }

  global.CharacterBuilderShell = {
    createBuilderShell,
    checkForPersistedDraft,
  };
})(window);
