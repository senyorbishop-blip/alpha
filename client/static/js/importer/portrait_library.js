(function () {
  const SPECIES_ALIASES = {
    'dragon-born': 'dragonborn',
    'half-elf': 'halfelf',
    'half-orc': 'halforc',
    'genasi-air': 'airgenasi',
  };
  const CLASS_ALIASES = {
    warrior: 'fighter',
    mage: 'wizard',
    bowman: 'ranger',
    thief: 'rogue',
    pirate: 'bard',
  };
  // Gender system: male and female only. All aliases resolve to 'male' or 'female'.
  const GENDER_ALIASES = {
    male: 'male', he: 'male', him: 'male', hehim: 'male', masculine: 'male', man: 'male',
    female: 'female', she: 'female', her: 'female', sheher: 'female', feminine: 'female', woman: 'female',
    // Neutral/non-binary aliases fall back to female for portrait purposes
    neutral: 'female', theythem: 'female', androgynous: 'female', nonbinary: 'female',
  };

  // Classes that have portraits for random female fallback on species step
  const FEMALE_CLASS_PORTRAIT_POOL = [
    'fighter', 'wizard', 'rogue', 'ranger', 'bard', 'cleric', 'paladin',
    'warlock', 'barbarian', 'druid', 'sorcerer', 'monk',
  ];

  function norm(value) {
    return String(value || '').trim().toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '');
  }
  function speciesKey(value) {
    const key = norm(value);
    return SPECIES_ALIASES[key] || key || 'human';
  }
  function classKey(value) {
    const key = norm(value);
    return CLASS_ALIASES[key] || key || 'fighter';
  }
  function genderKey(value) {
    const key = norm(value);
    return GENDER_ALIASES[key] || 'female';
  }

  const base = '/static/importer/portraits';
  const defaultManifest = {
    combos: {
      'human__fighter__male': `${base}/combos/human__fighter__male.png`,
      'human__fighter__female': `${base}/combos/human__fighter__female.png`,
      'elf__warlock__male': `${base}/combos/elf__warlock__male.png`,
      'elf__warlock__female': `${base}/combos/elf__warlock__female.png`,
    },
    species: {
      human: `${base}/species/human.png`,
      elf: `${base}/species/elf.png`,
    },
    classes: {
      fighter: `${base}/class/fighter.png`,
      warlock: `${base}/class/warlock.png`,
    },
    species_order: ['human', 'elf', 'aasimar', 'dwarf', 'dragonborn', 'tiefling', 'goliath'],
    class_order: ['barbarian','bard','cleric','druid','fighter','monk','paladin','ranger','rogue','sorcerer','warlock','wizard'],
    presentation_order: ['female', 'male'],
  };

  const state = { manifest: defaultManifest, loaded: false, loading: false };

  async function ensureManifest() {
    if (state.loaded || state.loading) return state.manifest;
    state.loading = true;
    try {
      const response = await fetch(`${base}/manifest.json`, { cache: 'no-store' });
      if (response.ok) {
        const remote = await response.json();
        state.manifest = {
          ...defaultManifest,
          ...remote,
          combos: { ...defaultManifest.combos, ...(remote.combos || {}) },
          species: { ...defaultManifest.species, ...(remote.species || {}) },
          classes: { ...defaultManifest.classes, ...(remote.classes || {}) },
        };
      }
    } catch (err) {
      console.warn('Portrait manifest fallback in use.', err);
    }
    state.loaded = true;
    state.loading = false;
    return state.manifest;
  }

  function currentManifest() { return state.manifest || defaultManifest; }

  function resolve(options) {
    const manifest = currentManifest();
    const sp = speciesKey(options && (options.speciesId || options.species));
    const cls = classKey(options && (options.classId || options.className));
    const gender = genderKey(options && options.gender);

    // 1. Try exact combo (e.g. human__fighter__female)
    const exact = `${sp}__${cls}__${gender}`;
    if (manifest.combos[exact]) return manifest.combos[exact];

    // 2. Female → fall back to male if no female portrait found
    if (gender === 'female') {
      const maleFallback = `${sp}__${cls}__male`;
      if (manifest.combos[maleFallback]) return manifest.combos[maleFallback];
    }

    // 3. Try any combo for this species+class regardless of gender
    const anyGenderKey = Object.keys(manifest.combos).find(function(k) {
      return k.startsWith(`${sp}__${cls}__`);
    });
    if (anyGenderKey) return manifest.combos[anyGenderKey];

    // 4. Species-only portrait
    if (manifest.species[sp]) return manifest.species[sp];

    // 5. Class-only portrait
    if (manifest.classes[cls]) return manifest.classes[cls];

    return '';
  }

  // Returns a random female class portrait URL for use on species step
  // when no species-specific image is available.
  function resolveRandomFemaleClassPortrait(seed) {
    const manifest = currentManifest();
    const pool = FEMALE_CLASS_PORTRAIT_POOL;
    // Use seed (e.g. species name) for deterministic but varied result
    let idx = 0;
    if (seed) {
      for (let i = 0; i < seed.length; i++) idx += seed.charCodeAt(i);
    }
    for (let attempt = 0; attempt < pool.length; attempt++) {
      const cls = pool[(idx + attempt) % pool.length];
      const femaleKey = `__${cls}__female`;
      const match = Object.keys(manifest.combos).find(function(k) { return k.indexOf(femaleKey) !== -1; });
      if (match) return manifest.combos[match];
      if (manifest.classes[cls]) return manifest.classes[cls];
    }
    return '';
  }

  function renderImgMarkup(options, size, variant, className) {
    const src = resolve(options);
    if (src) {
      const cls = ['avatar-render', className || '', variant || 'portrait'].filter(Boolean).join(' ');
      const label = String(options && (options.name || options.className || options.species || 'Hero portrait')).replace(/"/g, '&quot;');
      return `<img class="${cls}" alt="${label}" src="${src}">`;
    }
    const fallback = window.CasualDnDAvatarRenderer;
    return fallback
      ? fallback.renderImgMarkup(options || {}, size, variant, className)
      : `<div style="width:${size || 96}px;height:${Math.round((size || 96) * 1.1)}px;border-radius:18px;background:rgba(255,255,255,0.05)"></div>`;
  }

  window.CasualDnDPortraitLibrary = {
    ensureManifest,
    resolve,
    resolveRandomFemaleClassPortrait,
    renderImgMarkup,
    speciesKey,
    classKey,
    genderKey,
    get manifest() { return currentManifest(); },
  };

  ensureManifest();
}());
