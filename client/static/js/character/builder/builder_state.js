(function initCharacterBuilderState(global) {
  const router = global.CharacterBuilderRouter || null;
  const validators = global.CharacterBuilderValidators || null;

  const DRAFT_STORAGE_KEY = 'dnd_builder_draft_v1';

  let _memoryDraft = null;

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function clearPersistedDraft() {
    _memoryDraft = null;
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch (_) {
      // Storage errors must not break the builder.
    }
  }

  function loadPersistedDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (
        parsed
        && typeof parsed === 'object'
        && parsed.schemaVersion === 1
        && (
          (parsed.identity && String(parsed.identity.name || '').trim())
          || (parsed.class && String(parsed.class.id || '').trim())
        )
      ) {
        return parsed;
      }
    } catch (_) {
      // Storage errors must not break the builder.
    }
    return null;
  }

  function createDefaultDraft() {
    return {
      schemaVersion: 1,
      sourceMode: 'native',
      identity: {
        name: '',
        displayName: '',
        gender: 'male',
        pronouns: '',
        age: '',
        height: '',
        weight: '',
        eyes: '',
        hair: '',
        skin: '',
        alignment: '',
        deity: '',
        homeland: '',
        notes: '',
        backstory: '',
        personalityTraits: '',
        ideals: '',
        bonds: '',
        flaws: '',
        portraitUrl: '',
        tokenImageUrl: '',
      },
      presentation: {
        tokenDisplay: {
          scale: 1,
          cropMode: 'cover',
          ringStyle: 'classic',
          accentColor: '#00e5cc',
          labelFormat: 'class_name',
        },
        portraitFrame: 'classic',
      },
      species: {
        id: '',
        lineage: '',
      },
      origins: {
        backgroundId: '',
        backgroundName: '',
        languages: [],
        proficiencies: [],
      },
      abilityGenerationMode: 'manual',
      abilities: {
        str: 10,
        dex: 10,
        con: 10,
        int: 10,
        wis: 10,
        cha: 10,
      },
      class: {
        id: '',
        subclassId: '',
        subclass: '',
      },
      classes: [],
      progression: {
        level: 1,
        xp: 0,
        feats: [],
        talents: [],
        awakening: {
          track: '',
          tier: 0,
        },
      },
      spellbook: {
        castingMode: 'none',
        spellcastingAbility: '',
        known: [],
        prepared: [],
      },
      equipment: {
        startingPack: '',
        choices: [],
        currency: {
          cp: 0,
          sp: 0,
          ep: 0,
          gp: 0,
          pp: 0,
        },
      },
      compatibility: {
        charSheet: {},
        charBook: {},
      },
      meta: {
        status: 'draft',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    };
  }

  function syncCanonicalClassEntry(draft) {
    if (!draft || typeof draft !== 'object') return;
    if (!draft.class || typeof draft.class !== 'object') {
      draft.class = { id: '', subclassId: '', subclass: '' };
    }
    if (!Array.isArray(draft.classes)) {
      draft.classes = [];
    }
    if (!draft.progression || typeof draft.progression !== 'object') {
      draft.progression = { level: 1, xp: 0, feats: [], talents: [], awakening: { track: '', tier: 0 } };
    }
    if (!Array.isArray(draft.progression.feats)) {
      draft.progression.feats = [];
    }
    if (!Array.isArray(draft.progression.talents)) {
      draft.progression.talents = [];
    }
    if (!draft.spellbook || typeof draft.spellbook !== 'object') {
      draft.spellbook = { castingMode: 'none', spellcastingAbility: '', known: [], prepared: [] };
    }
    if (!Array.isArray(draft.spellbook.known)) draft.spellbook.known = [];
    if (!Array.isArray(draft.spellbook.prepared)) draft.spellbook.prepared = [];
    if (!draft.equipment || typeof draft.equipment !== 'object') {
      draft.equipment = { startingPack: '', choices: [], currency: { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 } };
    }
    if (!Array.isArray(draft.equipment.choices)) draft.equipment.choices = [];
    if (!draft.origins || typeof draft.origins !== 'object') {
      draft.origins = { backgroundId: '', backgroundName: '', languages: [], proficiencies: [] };
    }
    if (!Array.isArray(draft.origins.languages)) draft.origins.languages = [];
    if (!Array.isArray(draft.origins.proficiencies)) draft.origins.proficiencies = [];

    const classId = String(draft.class.id || '').trim();
    const classSubclassId = String(draft.class.subclassId || '').trim();
    const classSubclass = String(draft.class.subclass || '').trim() || classSubclassId;
    if (!classId) {
      draft.classes = [];
      return;
    }

    const level = parseInt(draft.progression.level, 10) > 0 ? parseInt(draft.progression.level, 10) : 1;
    const primary = {
      classId,
      level,
    };
    if (classSubclassId) {
      primary.subclassId = classSubclassId;
    }
    if (classSubclass) {
      primary.subclass = classSubclass;
    }

    draft.classes = [primary];
  }

  function resolveCreateBuilderOpts(initialDraftOrOptions) {
    if (!initialDraftOrOptions || typeof initialDraftOrOptions !== 'object') {
      return { initialDraft: null, resumeMemoryDraft: false, loadPersistedDraft: false };
    }
    if ('initialDraft' in initialDraftOrOptions || 'resumeMemoryDraft' in initialDraftOrOptions || 'loadPersistedDraft' in initialDraftOrOptions) {
      return {
        initialDraft: initialDraftOrOptions.initialDraft || null,
        resumeMemoryDraft: initialDraftOrOptions.resumeMemoryDraft === true,
        loadPersistedDraft: initialDraftOrOptions.loadPersistedDraft === true,
      };
    }
    return { initialDraft: initialDraftOrOptions, resumeMemoryDraft: false, loadPersistedDraft: false };
  }

  function createBuilderState(initialDraftOrOptions) {
    const listeners = new Set();
    const createOpts = resolveCreateBuilderOpts(initialDraftOrOptions);
    function getStepOrder() {
      if (router && typeof router.getStepOrder === 'function') {
        return router.getStepOrder(state && state.draft ? state.draft : null);
      }
      return router && Array.isArray(router.STEPS) ? router.STEPS.map((item) => item.id) : ['identity'];
    }

    const startingDraft = createOpts.initialDraft
      || (createOpts.resumeMemoryDraft ? _memoryDraft : null)
      || (createOpts.loadPersistedDraft ? loadPersistedDraft() : null)
      || createDefaultDraft();

    const state = {
      draft: clone(startingDraft),
      currentStepId: 'identity',
      isDirty: false,
      validationError: '',
      saveStatus: '',
    };

    syncCanonicalClassEntry(state.draft);
    state.currentStepId = (getStepOrder()[0] || 'identity');

    function emit() {
      const stepOrder = getStepOrder();
      if (!stepOrder.includes(state.currentStepId)) {
        state.currentStepId = stepOrder[0] || 'identity';
      }
      const snapshot = {
        draft: clone(state.draft),
        currentStepId: state.currentStepId,
        currentStepIndex: stepOrder.indexOf(state.currentStepId),
        stepOrder: stepOrder.slice(),
        isDirty: state.isDirty,
        validationError: state.validationError,
        saveStatus: state.saveStatus,
      };
      listeners.forEach((listener) => {
        try {
          listener(snapshot);
        } catch (_) {
          // Keep builder alive if one listener fails.
        }
      });
    }

    function touchDraft() {
      if (!state.draft.meta || typeof state.draft.meta !== 'object') {
        state.draft.meta = {};
      }
      state.draft.meta.updatedAt = new Date().toISOString();
      state.isDirty = true;
      state.saveStatus = '';
      try {
        localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(state.draft));
      } catch (_) {
        // Storage errors must not break the builder.
      }
    }

    function setField(path, value) {
      if (!Array.isArray(path) || !path.length) return;
      let cursor = state.draft;
      for (let i = 0; i < path.length - 1; i += 1) {
        const key = path[i];
        if (!cursor[key] || typeof cursor[key] !== 'object') {
          cursor[key] = {};
        }
        cursor = cursor[key];
      }
      cursor[path[path.length - 1]] = value;

      if (path[0] === 'class' && path[1] === 'id') {
        state.draft.class.subclassId = '';
        state.draft.class.subclass = '';
      }
      if (path[0] === 'class' && path[1] === 'subclassId') {
        const normalizedSubclassId = String(value || '').trim();
        state.draft.class.subclass = normalizedSubclassId;
        if (!normalizedSubclassId) {
          state.draft.class.subclass = '';
        }
      }

      if (path[0] === 'class' || path[0] === 'classes' || path[0] === 'progression') {
        syncCanonicalClassEntry(state.draft);
      }

      touchDraft();
      emit();
    }

    function setStep(stepId) {
      const normalized = router && typeof router.normalizeStep === 'function'
        ? router.normalizeStep(stepId, state.draft)
        : getStepOrder()[0];
      state.currentStepId = normalized;
      state.validationError = '';
      emit();
    }

    function validateCurrent() {
      if (!validators || typeof validators.validateStep !== 'function') {
        state.validationError = '';
        return true;
      }
      const result = validators.validateStep(state.currentStepId, state.draft);
      const ok = !!(result && result.ok);
      state.validationError = ok ? '' : String((result && result.error) || 'Please complete required fields.');
      return ok;
    }

    function validateDraft() {
      if (!validators || typeof validators.validateDraft !== 'function') {
        state.validationError = '';
        return { ok: true, issues: [] };
      }
      const result = validators.validateDraft(state.draft);
      const ok = !!(result && result.ok);
      if (!ok) {
        const issues = Array.isArray(result.issues) ? result.issues : [];
        state.validationError = issues[0] || 'Please complete required fields.';
      } else {
        state.validationError = '';
      }
      emit();
      return {
        ok,
        issues: Array.isArray(result.issues) ? result.issues : [],
      };
    }

    function nextStep() {
      if (!validateCurrent()) {
        emit();
        return false;
      }
      if (router && typeof router.nextStep === 'function') {
        state.currentStepId = router.nextStep(state.currentStepId, state.draft);
      }
      state.validationError = '';
      emit();
      return true;
    }

    function previousStep() {
      if (router && typeof router.previousStep === 'function') {
        state.currentStepId = router.previousStep(state.currentStepId, state.draft);
      }
      state.validationError = '';
      emit();
    }

    function saveDraftToMemory() {
      _memoryDraft = clone(state.draft);
      state.saveStatus = 'Draft saved for this browser session.';
      state.isDirty = false;
      emit();
      return clone(_memoryDraft);
    }

    function replaceDraft(nextDraft, opts) {
      state.draft = clone(nextDraft || createDefaultDraft());
      syncCanonicalClassEntry(state.draft);
      state.currentStepId = (getStepOrder()[0] || 'identity');
      state.validationError = '';
      state.saveStatus = '';
      state.isDirty = !!(opts && opts.markDirty);
      emit();
    }

    return {
      getState() {
        const stepOrder = getStepOrder();
        const currentStepId = stepOrder.includes(state.currentStepId)
          ? state.currentStepId
          : (stepOrder[0] || 'identity');
        return {
          draft: clone(state.draft),
          currentStepId,
          currentStepIndex: stepOrder.indexOf(currentStepId),
          stepOrder: stepOrder.slice(),
          isDirty: state.isDirty,
          validationError: state.validationError,
          saveStatus: state.saveStatus,
        };
      },
      subscribe(listener) {
        if (typeof listener !== 'function') return function noop() {};
        listeners.add(listener);
        return function unsubscribe() {
          listeners.delete(listener);
        };
      },
      setField,
      setStep,
      nextStep,
      previousStep,
      saveDraftToMemory,
      replaceDraft,
      validateDraft,
    };
  }

  global.CharacterBuilderState = {
    createBuilderState,
    createDefaultDraft,
    clearPersistedDraft,
    getPersistedDraft: loadPersistedDraft,
    getMemoryDraft() {
      return _memoryDraft ? clone(_memoryDraft) : null;
    },
    clearMemoryDraft() {
      _memoryDraft = null;
    },
  };
})(window);
