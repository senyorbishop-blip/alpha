(function initCharacterBuilderRouter(global) {
  const STEPS = [
    { id: 'identity', label: 'Identity' },
    { id: 'species', label: 'Species' },
    { id: 'origins', label: 'Origins' },
    { id: 'abilities', label: 'Abilities' },
    { id: 'class', label: 'Class' },
    { id: 'subclass', label: 'Subclass' },
    { id: 'progression', label: 'Progression' },
    { id: 'spells', label: 'Spells' },
    { id: 'equipment', label: 'Equipment' },
    { id: 'review', label: 'Review' },
  ];

  function normalizeId(value) {
    return String(value || '').trim().toLowerCase();
  }

  function getStepLabel(stepId) {
    const hit = STEPS.find((step) => step.id === stepId);
    return hit ? hit.label : '';
  }

  function getClassRowForDraft(draft) {
    const draftObj = draft && typeof draft === 'object' ? draft : {};
    const direct = draftObj.class && typeof draftObj.class === 'object' ? draftObj.class : {};
    const directClassId = String(direct.id || '').trim();
    if (directClassId) {
      return {
        classId: directClassId,
      };
    }

    const classes = Array.isArray(draftObj.classes) ? draftObj.classes : [];
    if (classes.length > 0 && classes[0] && typeof classes[0] === 'object') {
      return classes[0];
    }
    return {};
  }

  function getBuilderLevel(draft) {
    const progression = draft && draft.progression && typeof draft.progression === 'object'
      ? draft.progression
      : {};
    const parsed = parseInt(progression.level, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
  }

  function getClassSubclassUnlockLevel(classId) {
    const api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') return 0;
    const catalog = api.getCachedCatalog();
    const rows = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    const key = normalizeId(classId);
    if (!key) return 0;
    const row = rows.find((item) => normalizeId(item && item.id) === key);
    if (!row) return 0;
    const parsed = parseInt(row.subclassLevel, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function shouldIncludeSubclassStep(draft) {
    const classRow = getClassRowForDraft(draft);
    const classId = String(classRow.classId || classRow.id || '').trim();
    if (!classId) return false;

    const api = global.CharacterBuilderAPI;
    const catalog = api && typeof api.getCachedCatalog === 'function'
      ? api.getCachedCatalog()
      : null;

    // Safe default: if catalog is not yet loaded, include the step
    if (!catalog) return true;

    // Class must have at least one subclass available in the catalog
    const byClass = catalog.subclassesByClass && typeof catalog.subclassesByClass === 'object'
      ? catalog.subclassesByClass
      : {};
    const key = normalizeId(classId);
    if (!Array.isArray(byClass[key]) || byClass[key].length === 0) return false;

    // Level must meet or exceed the subclass unlock threshold
    const unlockLevel = getClassSubclassUnlockLevel(classId);
    if (!unlockLevel) return false;

    const currentLevel = getBuilderLevel(draft);
    return currentLevel >= unlockLevel;
  }

  function clearSubclassFromDraft(draft) {
    if (!draft || typeof draft !== 'object') return;
    if (!draft.class || typeof draft.class !== 'object') return;
    draft.class.subclassId = '';
    draft.class.subclass = '';
  }

  function getStepOrder(draft) {
    const order = STEPS
      .filter((step) => {
        if (step.id !== 'subclass') return true;
        return shouldIncludeSubclassStep(draft);
      })
      .map((step) => step.id);

    if (!order.includes('subclass')) {
      clearSubclassFromDraft(draft);
    }

    return order;
  }

  function indexForStep(stepId, draft) {
    return getStepOrder(draft).findIndex((id) => id === stepId);
  }

  function normalizeStep(stepId, draft) {
    const stepOrder = getStepOrder(draft);
    return stepOrder.includes(stepId) ? stepId : stepOrder[0];
  }

  function nextStep(stepId, draft) {
    const stepOrder = getStepOrder(draft);
    const current = normalizeStep(stepId, draft);
    const index = stepOrder.findIndex((id) => id === current);
    if (index < 0) return stepOrder[0];
    return stepOrder[Math.min(index + 1, stepOrder.length - 1)];
  }

  function previousStep(stepId, draft) {
    const stepOrder = getStepOrder(draft);
    const current = normalizeStep(stepId, draft);
    const index = stepOrder.findIndex((id) => id === current);
    if (index < 0) return stepOrder[0];
    return stepOrder[Math.max(index - 1, 0)];
  }

  global.CharacterBuilderRouter = {
    STEPS,
    getStepLabel,
    getStepOrder,
    shouldIncludeSubclassStep,
    clearSubclassFromDraft,
    indexForStep,
    normalizeStep,
    nextStep,
    previousStep,
  };
})(window);
