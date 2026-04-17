(function initCharacterBuilderValidators(global) {
  const ABILITY_KEYS = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  const REQUIRED_STEPS = ['identity', 'species', 'origins', 'abilities', 'class', 'progression'];

  function safeInt(value, fallback) {
    const parsed = parseInt(value, 10);
    if (Number.isFinite(parsed)) return parsed;
    return fallback;
  }

  function validateIdentity(draft) {
    const identity = draft && draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
    const name = String(identity.name || '').trim();
    if (!name) return { ok: false, error: 'Character name is required.' };
    return { ok: true, error: '' };
  }

  function validateSpecies(draft) {
    const species = draft && draft.species && typeof draft.species === 'object' ? draft.species : {};
    if (!String(species.id || '').trim()) {
      return { ok: false, error: 'Choose a species to continue.' };
    }
    return { ok: true, error: '' };
  }


  function pointBuyCost(score) {
    if (score <= 8) return 0;
    if (score === 9) return 1;
    if (score === 10) return 2;
    if (score === 11) return 3;
    if (score === 12) return 4;
    if (score === 13) return 5;
    if (score === 14) return 7;
    if (score === 15) return 9;
    return 99;
  }

  function validateAbilities(draft) {
    const abilities = draft && draft.abilities && typeof draft.abilities === 'object' ? draft.abilities : {};
    const generationMode = String((draft && draft.abilityGenerationMode) || 'manual').trim();
    for (let i = 0; i < ABILITY_KEYS.length; i += 1) {
      const key = ABILITY_KEYS[i];
      const value = safeInt(abilities[key], NaN);
      if (!Number.isFinite(value)) {
        return { ok: false, error: 'All ability scores must be set.' };
      }
      if (value < 3 || value > 20) {
        return { ok: false, error: 'Ability scores must be between 3 and 20.' };
      }
      if (generationMode === 'point_buy' && (value < 8 || value > 15)) {
        return { ok: false, error: 'Point buy scores must stay between 8 and 15.' };
      }
    }
    return { ok: true, error: '' };
  }

  function validateOrigins(draft) {
    const origins = draft && draft.origins && typeof draft.origins === 'object' ? draft.origins : {};
    const backgroundId = String(origins.backgroundId || '').trim();
    const backgroundName = String(origins.backgroundName || '').trim();
    if (!backgroundId && !backgroundName) {
      return { ok: false, error: 'Choose or enter a background to continue.' };
    }
    return { ok: true, error: '' };
  }

  function getPrimaryClass(draft) {
    const classes = Array.isArray(draft && draft.classes) ? draft.classes : [];
    if (classes.length > 0 && classes[0] && typeof classes[0] === 'object') {
      return classes[0];
    }
    const classData = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    if (classData.id) {
      return {
        classId: classData.id,
        level: 1,
      };
    }
    return {};
  }

  function validateClass(draft) {
    const primaryClass = getPrimaryClass(draft);
    const classId = String(primaryClass.classId || '').trim();
    if (!classId) {
      return { ok: false, error: 'Choose a class to continue.' };
    }
    const level = safeInt(primaryClass.level, 0);
    if (level < 1) {
      return { ok: false, error: 'Class level must be at least 1.' };
    }
    return { ok: true, error: '' };
  }

  function shouldRequireSubclass(draft) {
    const router = global.CharacterBuilderRouter;
    if (!router || typeof router.shouldIncludeSubclassStep !== 'function') {
      return false;
    }
    return router.shouldIncludeSubclassStep(draft);
  }

  function getSelectedSubclassId(draft) {
    const classData = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    const directId = String(classData.subclassId || '').trim();
    if (directId) return directId;
    const fallback = String(classData.subclass || '').trim();
    if (fallback) return fallback;

    const primaryClass = getPrimaryClass(draft);
    const rowId = String(primaryClass.subclassId || '').trim();
    if (rowId) return rowId;
    return String(primaryClass.subclass || '').trim();
  }

  function validateSubclass(draft) {
    if (!shouldRequireSubclass(draft)) {
      return { ok: true, error: '' };
    }
    const subclassId = getSelectedSubclassId(draft);
    if (!subclassId) {
      return { ok: false, error: 'Choose a subclass to continue.' };
    }
    return { ok: true, error: '' };
  }

  function validateProgression(draft) {
    const progression = draft && draft.progression && typeof draft.progression === 'object' ? draft.progression : {};
    const level = safeInt(progression.level, 0);
    if (!Number.isFinite(level) || level < 1 || level > 20) {
      return { ok: false, error: 'Character level must be between 1 and 20.' };
    }
    const progressionRequirements = global.CharacterBuilderProgressionRequirements;
    if (progressionRequirements && typeof progressionRequirements.compute === 'function') {
      const requirements = progressionRequirements.compute(draft);
      const pending = Array.isArray(requirements && requirements.required) ? requirements.required : [];
      if (pending.length > 0) {
        const first = pending[0] || {};
        if (first.type === 'subclass') {
          return { ok: false, error: 'Choose your subclass to resolve required progression choices.' };
        }
        return { ok: false, error: 'Resolve required progression choices (ASI/Feat) before continuing.' };
      }
    }
    return { ok: true, error: '' };
  }

  function validateStep(stepId, draft) {
    if (stepId === 'identity') return validateIdentity(draft);
    if (stepId === 'species') return validateSpecies(draft);
    if (stepId === 'origins') return validateOrigins(draft);
    if (stepId === 'abilities') return validateAbilities(draft);
    if (stepId === 'class') return validateClass(draft);
    if (stepId === 'subclass') return validateSubclass(draft);
    if (stepId === 'progression') return validateProgression(draft);
    return { ok: true, error: '' };
  }

  function validateDraft(draft) {
    const requiredSteps = REQUIRED_STEPS.slice();
    if (shouldRequireSubclass(draft)) {
      requiredSteps.push('subclass');
    }

    const issues = [];
    requiredSteps.forEach(function validateRequired(stepId) {
      const result = validateStep(stepId, draft);
      if (!result.ok && result.error) {
        issues.push(result.error);
      }
    });
    return {
      ok: issues.length === 0,
      issues,
    };
  }

  global.CharacterBuilderValidators = {
    ABILITY_KEYS,
    REQUIRED_STEPS,
    validateStep,
    validateDraft,
  };
})(window);
