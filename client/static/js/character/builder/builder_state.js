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


  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeInt(value, fallback) {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function slugify(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/&/g, ' and ')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function resolveCatalogId(collectionName, rawId, rawName) {
    const direct = String(rawId || '').trim();
    const name = String(rawName || '').trim();
    const candidates = [direct, name, slugify(direct), slugify(name)]
      .map(function normalize(item) { return String(item || '').trim().toLowerCase(); })
      .filter(Boolean);
    const api = global.CharacterBuilderAPI;
    const catalog = api && typeof api.getCachedCatalog === 'function' ? api.getCachedCatalog() : null;
    const rows = catalog && Array.isArray(catalog[collectionName]) ? catalog[collectionName] : [];
    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i] && typeof rows[i] === 'object' ? rows[i] : {};
      const rowCandidates = [row.id, row.name, row.displayName, slugify(row.name), slugify(row.displayName)]
        .map(function normalize(item) { return String(item || '').trim().toLowerCase(); })
        .filter(Boolean);
      if (rowCandidates.some(function hasMatch(item) { return candidates.includes(item); })) {
        return String(row.id || direct || slugify(name)).trim();
      }
    }
    return direct || slugify(name);
  }

  function normalizeSpellIds(rows) {
    return asArray(rows).map(function toSpellId(row) {
      if (row && typeof row === 'object') {
        return String(row.id || row.spellId || row.name || '').trim();
      }
      return String(row || '').trim();
    }).filter(Boolean);
  }

  function normalizeInventoryRows(rows) {
    return asArray(rows).map(function cloneInventoryRow(row) {
      if (row && typeof row === 'object') return clone(row);
      const name = String(row || '').trim();
      return name ? { name: name, qty: 1 } : null;
    }).filter(Boolean);
  }

  function canonicalDocumentToDraft(document) {
    const doc = asObject(document);
    const draft = createDefaultDraft();
    const identity = asObject(doc.identity);
    const species = asObject(doc.species);
    const background = asObject(doc.background);
    const abilities = asObject(doc.abilities);
    const abilityScores = asObject(abilities.scores || abilities);
    const classes = asArray(doc.classes);
    const primaryClass = asObject(classes[0]);
    const equipment = asObject(doc.equipment);
    const spellState = asObject(doc.spellState);
    const focus = asObject(spellState.focus);
    const presentation = asObject(doc.presentation);
    const tokenDisplay = asObject(presentation.tokenDisplay);
    const awakening = asObject(doc.awakening);
    const importMeta = asObject(doc.importMeta);
    const audit = asObject(doc.audit);
    const runtime = asObject(doc.nativeRuntime || doc.runtime);
    const runtimeHp = asObject(runtime.hp);
    const runtimeSpeed = asObject(runtime.speed);

    const levelTotal = classes.reduce(function sumLevels(total, row) {
      const level = safeInt(row && row.level, 0);
      return total + (level > 0 ? level : 0);
    }, 0) || safeInt(primaryClass.level, 1);
    const subclassName = String(primaryClass.subclassId || primaryClass.subclass || primaryClass.subclassName || '').trim();

    draft.schemaVersion = safeInt(doc.schemaVersion, 1);
    draft.rulesMode = String(doc.rulesMode || draft.rulesMode || 'casual').trim() || 'casual';
    draft.ruleset = String(doc.ruleset || '').trim();
    draft.contentPackVersion = String(doc.contentPackVersion || '').trim();
    draft.sourceMode = String(doc.sourceMode || importMeta.origin || importMeta.source || 'native').trim().toLowerCase() || 'native';
    draft.importMeta = clone(importMeta);
    draft.audit = clone(audit);

    draft.identity = Object.assign({}, draft.identity, clone(identity), {
      name: String(identity.name || identity.displayName || doc.name || '').trim(),
      displayName: String(identity.displayName || identity.name || doc.name || '').trim(),
      portraitUrl: String(identity.portraitUrl || identity.avatarUrl || '').trim(),
      tokenImageUrl: String(identity.tokenImageUrl || identity.portraitUrl || identity.avatarUrl || '').trim(),
    });

    draft.presentation = Object.assign({}, draft.presentation, clone(presentation));
    draft.presentation.tokenDisplay = Object.assign({}, createDefaultDraft().presentation.tokenDisplay, clone(tokenDisplay));

    draft.species = Object.assign({}, clone(species), {
      id: resolveCatalogId('species', species.id, species.name),
      name: String(species.name || species.id || '').trim(),
      lineage: String(species.lineage || species.subrace || '').trim(),
    });

    draft.origins = {
      backgroundId: resolveCatalogId('backgrounds', background.id, background.name) || String(background.id || '').trim(),
      backgroundName: String(background.name || background.id || '').trim(),
      languages: asArray(background.languages).slice(),
      proficiencies: asArray(background.proficiencies).slice(),
    };
    draft.background = clone(background);

    draft.abilityGenerationMode = String(abilities.generationMode || doc.abilityGenerationMode || 'manual').trim() || 'manual';
    draft.abilities = {
      str: safeInt(abilityScores.str, 10),
      dex: safeInt(abilityScores.dex, 10),
      con: safeInt(abilityScores.con, 10),
      int: safeInt(abilityScores.int, 10),
      wis: safeInt(abilityScores.wis, 10),
      cha: safeInt(abilityScores.cha, 10),
    };
    draft.abilityDetails = clone(abilities);

    draft.class = {
      id: resolveCatalogId('classes', primaryClass.classId || primaryClass.id || primaryClass.name, primaryClass.name || primaryClass.className),
      name: String(primaryClass.name || primaryClass.className || primaryClass.classId || '').trim(),
      subclassId: subclassName,
      subclass: String(primaryClass.subclass || primaryClass.subclassName || primaryClass.subclassId || '').trim(),
    };
    draft.classes = classes.length ? clone(classes) : [];
    draft.progression = Object.assign({}, draft.progression, {
      level: Math.max(1, Math.min(20, safeInt(levelTotal, 1))),
      xp: safeInt(doc.xp || asObject(doc.progression).xp, 0),
      feats: asArray(doc.feats).slice(),
      talents: asArray(doc.talents).slice(),
      awakening: {
        track: String(awakening.pathId || awakening.track || '').trim(),
        tier: safeInt(awakening.stage || awakening.tier, 0),
      },
    });

    const equipmentChoices = asObject(equipment.builderChoices || equipment.choices);
    const inventory = normalizeInventoryRows(equipment.inventory);
    draft.equipment = {
      startingPack: String(equipmentChoices.startingPackId || equipment.startingPack || '').trim(),
      choices: Object.assign({
        starterLoadoutId: '',
        startingPackId: String(equipmentChoices.startingPackId || equipment.startingPack || '').trim(),
        additionalItems: inventory.map(function itemName(row) { return String(row.name || '').trim(); }).filter(Boolean),
        libraryItems: [],
      }, clone(equipmentChoices)),
      currency: Object.assign({}, draft.equipment.currency, clone(asObject(equipment.currency))),
      inventory: inventory,
      equipped: clone(asObject(equipment.equipped)),
      containers: asArray(equipment.containers).slice(),
    };

    draft.spellbook = {
      castingMode: String(focus.castingMode || spellState.castingMode || 'none').trim() || 'none',
      spellcastingAbility: String(focus.spellcastingAbility || spellState.spellcastingAbility || '').trim(),
      known: normalizeSpellIds(spellState.known || spellState.knownSpells || spellState.spells),
      prepared: normalizeSpellIds(spellState.prepared || spellState.preparedSpells),
      slots: clone(asObject(spellState.slots)),
      rituals: asArray(spellState.rituals).slice(),
      entries: asArray(spellState.spellbookEntries).slice(),
      classSources: asArray(spellState.classSources).slice(),
    };

    draft.compatibility = Object.assign({}, draft.compatibility, {
      charSheet: clone(asObject(doc.charSheet)),
      charBook: clone(asObject(doc.charBook)),
      importedStats: {
        hp: runtimeHp.max != null ? clone(runtimeHp) : clone(asObject(doc.hp)),
        ac: runtime.ac != null ? runtime.ac : doc.ac,
        speed: runtimeSpeed.walk != null ? runtimeSpeed.walk : species.speed,
      },
      canonicalDocument: clone(doc),
    });
    draft.meta = Object.assign({}, draft.meta, {
      status: 'draft',
      createdAt: audit.createdAt || draft.meta.createdAt,
      updatedAt: new Date().toISOString(),
      importedAt: importMeta.importedAt || null,
    });
    return draft;
  }

  function normalizeDraftInput(input) {
    if (!input || typeof input !== 'object') return createDefaultDraft();
    const row = input.character_document || input.document || input.nativeCharacter || input;
    const looksCanonical = row && typeof row === 'object' && (
      row.schema || row.spellState || row.background || (row.abilities && row.abilities.scores)
    );
    return looksCanonical ? canonicalDocumentToDraft(row) : clone(row);
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
        asiChoicesByLevel: {},
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
      draft.progression = { level: 1, xp: 0, feats: [], talents: [], asiChoicesByLevel: {}, awakening: { track: '', tier: 0 } };
    }
    if (!Array.isArray(draft.progression.feats)) {
      draft.progression.feats = [];
    }
    if (!Array.isArray(draft.progression.talents)) {
      draft.progression.talents = [];
    }
    if (!draft.progression.asiChoicesByLevel || typeof draft.progression.asiChoicesByLevel !== 'object' || Array.isArray(draft.progression.asiChoicesByLevel)) {
      draft.progression.asiChoicesByLevel = {};
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
    const existingPrimary = draft.classes[0] && typeof draft.classes[0] === 'object' ? draft.classes[0] : {};
    const primary = Object.assign({}, existingPrimary, {
      classId,
      level,
    });
    if (draft.class.name && !primary.name) {
      primary.name = String(draft.class.name || '').trim();
    }
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

    const startingDraft = normalizeDraftInput(createOpts.initialDraft
      || (createOpts.resumeMemoryDraft ? _memoryDraft : null)
      || (createOpts.loadPersistedDraft ? loadPersistedDraft() : null)
      || createDefaultDraft());

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

    function firstMissingRequiredStep() {
      const stepOrder = getStepOrder();
      if (!validators || typeof validators.validateStep !== 'function') return '';
      for (let i = 0; i < stepOrder.length; i += 1) {
        const stepId = stepOrder[i];
        if (stepId === 'review') continue;
        const result = validators.validateStep(stepId, state.draft);
        if (result && result.ok === false) return stepId;
      }
      return '';
    }

    function replaceDraft(nextDraft, opts) {
      const options = opts && typeof opts === 'object' ? opts : {};
      state.draft = normalizeDraftInput(nextDraft || createDefaultDraft());
      syncCanonicalClassEntry(state.draft);
      const stepOrder = getStepOrder();
      const missingStep = options.routeTo === 'review_or_first_missing' ? firstMissingRequiredStep() : '';
      const preferredStep = String(options.stepId || '').trim();
      if (missingStep) {
        state.currentStepId = missingStep;
      } else if (preferredStep && stepOrder.includes(preferredStep)) {
        state.currentStepId = preferredStep;
      } else if (options.routeTo === 'review_or_first_missing' && stepOrder.includes('review')) {
        state.currentStepId = 'review';
      } else {
        state.currentStepId = (stepOrder[0] || 'identity');
      }
      state.validationError = '';
      state.saveStatus = '';
      state.isDirty = !!options.markDirty;
      if (state.isDirty) {
        try {
          localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(state.draft));
        } catch (_) {}
      }
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
    canonicalDocumentToDraft,
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
