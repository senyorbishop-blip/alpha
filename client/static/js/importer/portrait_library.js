(function () {
  const SPECIES_ALIASES = {
    'dragon-born': 'dragonborn',
    'half-elf': 'halfelf',
    woodelf: 'elf',
    highelf: 'elf',
    halfelf: 'elf',
    'half-orc': 'halforc',
    'genasi-air': 'airgenasi',
    halfling: 'halfling',
  };
  const CLASS_ALIASES = {
    warrior: 'fighter',
    mage: 'wizard',
    bowman: 'ranger',
    thief: 'rogue',
  };
  // Gender system: male and female only. All aliases resolve to 'male' or 'female'.
  const GENDER_ALIASES = {
    male: 'masculine', he: 'masculine', him: 'masculine', hehim: 'masculine', masculine: 'masculine', man: 'masculine',
    female: 'feminine', she: 'feminine', her: 'feminine', sheher: 'feminine', feminine: 'feminine', woman: 'feminine',
    neutral: 'neutral', theythem: 'neutral', androgynous: 'neutral', nonbinary: 'neutral',
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
      'human__barbarian__masculine': `${base}/combos/Human Male Barbarian.png`,
      'human__barbarian__feminine': `${base}/combos/Human Female Barbarian.png`,
      'human__bard__masculine': `${base}/combos/Human Male Bard.png`,
      'human__bard__feminine': `${base}/combos/Human Female Bard.png`,
      'human__cleric__masculine': `${base}/combos/Human Male Cleric.png`,
      'human__cleric__feminine': `${base}/combos/Human Female Cleric.png`,
      'human__druid__masculine': `${base}/combos/Human Male Druid.png`,
      'human__druid__feminine': `${base}/combos/Human Female Druid.png`,
      'human__fighter__masculine': `${base}/combos/Human Male Fighter.png`,
      'human__fighter__feminine': `${base}/combos/Human Female Fighter.png`,
      'human__monk__masculine': `${base}/combos/Human Male Monk.png`,
      'human__monk__feminine': `${base}/combos/Human Female Monk.png`,
      'human__paladin__masculine': `${base}/combos/Human Male Paladin.png`,
      'human__paladin__feminine': `${base}/combos/Human Female Paladin.png`,
      'human__pirate__masculine': `${base}/combos/Human Male Pirate.png`,
      'human__ranger__masculine': `${base}/combos/Human Male Ranger.png`,
      'human__ranger__feminine': `${base}/combos/Human Female Ranger.png`,
      'human__rogue__masculine': `${base}/combos/Human Male Rogue.png`,
      'human__rogue__feminine': `${base}/combos/Human Female Rogue.png`,
      'human__sorcerer__masculine': `${base}/combos/Human Male Sorcerer.png`,
      'human__sorcerer__feminine': `${base}/combos/Human Female Sorcerer.png`,
      'human__tinker__masculine': `${base}/combos/Human Tinker Male.png`,
      'human__tinker__feminine': `${base}/combos/Human Female Tinker.png`,
      'human__warlock__masculine': `${base}/combos/Human Male Warlock.png`,
      'human__warlock__feminine': `${base}/combos/Human Female Warlock.png`,
      'human__wizard__masculine': `${base}/combos/Human Wizard Male.png`,
      'human__wizard__feminine': `${base}/combos/Human Female Wizard.png`,
      'elf__barbarian__masculine': `${base}/combos/Elf Male Barbarian.png`,
      'elf__barbarian__feminine': `${base}/combos/Elf Female Barbarian.png`,
      'elf__fighter__masculine': `${base}/combos/Elf Male Fighter.png`,
      'elf__monk__masculine': `${base}/combos/Elf Male Monk.png`,
      'dragonborn__fighter__masculine': `${base}/combos/Dragonborn Male Fighter.png`,
      'halfling__pirate__feminine': `${base}/combos/Halfling Female Pirate.png`,
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
    presentation_order: ['feminine', 'masculine', 'neutral'],
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

    // 2. Feminine or neutral → fall back to masculine if no match found
    if (gender === 'feminine' || gender === 'neutral') {
      const mascFallback = `${sp}__${cls}__masculine`;
      if (manifest.combos[mascFallback]) return manifest.combos[mascFallback];
    }

    // 3. Try any combo for this species+class regardless of gender
    const anyGenderKey = Object.keys(manifest.combos).find(function(k) {
      return k.startsWith(`${sp}__${cls}__`);
    });
    if (anyGenderKey) return manifest.combos[anyGenderKey];

    // 4. Species-only portrait
    if (manifest.species[sp]) return manifest.species[sp];
    // 5. Class-only portrait fallback (legacy manifest support)
    if (manifest.classes[cls]) return manifest.classes[cls];
    // 6. Conventional species portrait drop-in path
    return `${base}/species/${sp}.png`;
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
      const femaleKey = `__${cls}__feminine`;
      const match = Object.keys(manifest.combos).find(function(k) { return k.indexOf(femaleKey) !== -1; });
      if (match) return manifest.combos[match];
      if (manifest.classes[cls]) return manifest.classes[cls];
    }
    return '';
  }

  function renderImgMarkup(options, size, variant, className) {
    const src = resolve(options);
    const manifest = currentManifest();
    const cls = classKey(options && (options.classId || options.className));
    const classFallback = manifest.classes && manifest.classes[cls] ? manifest.classes[cls] : '';
    const fallbackList = [classFallback].filter(Boolean).join('|');
    if (src) {
      const cls = ['avatar-render', className || '', variant || 'portrait'].filter(Boolean).join(' ');
      const label = String(options && (options.name || options.className || options.species || 'Hero portrait')).replace(/"/g, '&quot;');
      return `<img class="${cls}" alt="${label}" src="${src}" data-fallbacks="${fallbackList}" onerror="(function(img){var list=(img.dataset.fallbacks||'').split('|').filter(Boolean);var next=list.shift();img.dataset.fallbacks=list.join('|');if(next){img.src=next;return;}img.onerror=null;img.style.display='none';})(this)">`;
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
