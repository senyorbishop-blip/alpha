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
    return CLASS_ALIASES[key] || key || '';
  }
  function genderKey(value) {
    const key = norm(value);
    return GENDER_ALIASES[key] || 'female';
  }

  const base = '/static/importer/portraits';
  const defaultManifest = {
    combos: {
      'aasimar__barbarian__masculine': `${base}/combos/Aasimar Male Barbarian.png`,
      'aasimar__bard__masculine': `${base}/combos/Aasimar Male Bard.png`,
      'aasimar__cleric__masculine': `${base}/combos/Aasimar Male Cleric.png`,
      'aasimar__druid__masculine': `${base}/combos/Aasimar Male Druid.png`,
      'aasimar__fighter__masculine': `${base}/combos/Aasimar Male Fighter.png`,
      'aasimar__monk__masculine': `${base}/combos/Aasimar Male Monk.png`,
      'aasimar__paladin__masculine': `${base}/combos/Aasimar Male Paladin.png`,
      'aasimar__pirate__masculine': `${base}/combos/Aasimar Male Pirate.png`,
      'aasimar__ranger__masculine': `${base}/combos/Aasimar Male Ranger.png`,
      'aasimar__rogue__masculine': `${base}/combos/Aasimar Male Rogue.png`,
      'aasimar__sorcerer__masculine': `${base}/combos/Aasimar Male Sorcerer.png`,
      'aasimar__tinker__masculine': `${base}/combos/Aasimar Male Tinker.png`,
      'aasimar__warlock__masculine': `${base}/combos/Aasimar Male Warlock.png`,
      'aasimar__wizard__masculine': `${base}/combos/Aasimar Male Wizard.png`,
      'dragonborn__bard__masculine': `${base}/combos/Dragonborn Male Bard.png`,
      'dragonborn__cleric__masculine': `${base}/combos/Dragonborn Male Cleric.png`,
      'dragonborn__druid__masculine': `${base}/combos/Dragonborn Male Druid.png`,
      'dragonborn__fighter__masculine': `${base}/combos/Dragonborn Male Fighter.png`,
      'dragonborn__monk__masculine': `${base}/combos/Dragonborn Male Monk.png`,
      'dragonborn__paladin__masculine': `${base}/combos/Dragonborn Male Paladin.png`,
      'dragonborn__pirate__masculine': `${base}/combos/Dragonborn Male Pirate.png`,
      'dragonborn__ranger__masculine': `${base}/combos/Dragonborn Male Ranger.png`,
      'dragonborn__rogue__masculine': `${base}/combos/Dragonborn Male Rogue.png`,
      'dragonborn__sorcerer__masculine': `${base}/combos/Dragonborn Male Sorcerer.png`,
      'dragonborn__tinker__masculine': `${base}/combos/Dragonborn Male Tinker.png`,
      'dragonborn__warlock__masculine': `${base}/combos/Dragonborn Male Warlock.png`,
      'dragonborn__wizard__masculine': `${base}/combos/Dragonborn Male Wizard.png`,
      'dwarf__barbarian__masculine': `${base}/combos/Dwarf Male Barbarian.png`,
      'dwarf__bard__masculine': `${base}/combos/Dwarf Male Bard.png`,
      'dwarf__cleric__masculine': `${base}/combos/Dwarf Male Cleric.png`,
      'dwarf__druid__masculine': `${base}/combos/Dwarf Male Druid.png`,
      'dwarf__fighter__masculine': `${base}/combos/Dwarf Male Fighter.png`,
      'dwarf__monk__masculine': `${base}/combos/Dwarf Male Monk.png`,
      'dwarf__paladin__masculine': `${base}/combos/Dwarf Male Paladin.png`,
      'dwarf__pirate__masculine': `${base}/combos/Dwarf Male Pirate.png`,
      'dwarf__ranger__masculine': `${base}/combos/Dwarf Male Ranger.png`,
      'dwarf__rogue__masculine': `${base}/combos/Dwarf Male Rogue.png`,
      'dwarf__sorcerer__masculine': `${base}/combos/Dwarf Male Sorcerer.png`,
      'dwarf__tinker__masculine': `${base}/combos/Dwarf Male Tinker.png`,
      'dwarf__warlock__masculine': `${base}/combos/Dwarf Male Warlock.png`,
      'dwarf__wizard__masculine': `${base}/combos/Dwarf Male Wizard.png`,
      'elf__barbarian__feminine': `${base}/combos/Elf Female Barbarian.png`,
      'elf__barbarian__masculine': `${base}/combos/Elf Male Barbarian.png`,
      'elf__bard__masculine': `${base}/combos/Elf Male Bard.png`,
      'elf__cleric__masculine': `${base}/combos/Elf Male Cleric.png`,
      'elf__druid__masculine': `${base}/combos/Elf Male Druid.png`,
      'elf__fighter__masculine': `${base}/combos/Elf Male Fighter.png`,
      'elf__monk__masculine': `${base}/combos/Elf Male Monk.png`,
      'elf__paladin__masculine': `${base}/combos/Elf Male Paladin.png`,
      'elf__pirate__masculine': `${base}/combos/Elf Male Pirate.png`,
      'elf__ranger__masculine': `${base}/combos/Elf Male Ranger.png`,
      'elf__rogue__masculine': `${base}/combos/Elf Male Rogue.png`,
      'elf__sorcerer__masculine': `${base}/combos/Elf Male Sorcerer.png`,
      'elf__tinker__masculine': `${base}/combos/Elf Male Tinker.png`,
      'elf__warlock__masculine': `${base}/combos/Elf Male Warlock.png`,
      'elf__wizard__masculine': `${base}/combos/Elf Male Wizard.png`,
      'goliath__barbarian__masculine': `${base}/combos/Goliath Male Barbarian.png`,
      'goliath__bard__masculine': `${base}/combos/Goliath Male Bard.png`,
      'goliath__cleric__masculine': `${base}/combos/Goliath Male Cleric.png`,
      'goliath__druid__masculine': `${base}/combos/Goliath Male Druid.png`,
      'goliath__fighter__masculine': `${base}/combos/Goliath Male Fighter.png`,
      'goliath__monk__masculine': `${base}/combos/Goliath Male Monk.png`,
      'goliath__paladin__masculine': `${base}/combos/Goliath Male Paladin.png`,
      'goliath__pirate__masculine': `${base}/combos/Goliath Male Pirate.png`,
      'goliath__ranger__feminine': `${base}/combos/Goliath Female Ranger.png`,
      'goliath__ranger__masculine': `${base}/combos/Goliath Male Ranger.png`,
      'goliath__rogue__masculine': `${base}/combos/Goliath Male Rogue.png`,
      'goliath__sorcerer__masculine': `${base}/combos/Goliath Male Sorcerer.png`,
      'goliath__tinker__masculine': `${base}/combos/Goliath Male Tinker.png`,
      'goliath__warlock__masculine': `${base}/combos/Goliath Male Warlock.png`,
      'goliath__wizard__masculine': `${base}/combos/Goliath Male Wizard.png`,
      'halfling__barbarian__feminine': `${base}/combos/Halfling Female Barbarian.png`,
      'halfling__barbarian__masculine': `${base}/combos/Halfling Male Barbarian.png`,
      'halfling__bard__masculine': `${base}/combos/Halfling Male Bard.png`,
      'halfling__cleric__masculine': `${base}/combos/Halfling Male Cleric.png`,
      'halfling__druid__masculine': `${base}/combos/Halfling Male Druid.png`,
      'halfling__fighter__masculine': `${base}/combos/Halfling Male Fighter.png`,
      'halfling__monk__masculine': `${base}/combos/Halfling Male Monk.png`,
      'halfling__paladin__masculine': `${base}/combos/Halfling Male Paladin.png`,
      'halfling__pirate__feminine': `${base}/combos/Halfling Female Pirate.png`,
      'halfling__pirate__masculine': `${base}/combos/Halfling Male Pirate.png`,
      'halfling__ranger__feminine': `${base}/combos/Halfling Female Ranger.png`,
      'halfling__ranger__masculine': `${base}/combos/Halfling Male Ranger.png`,
      'halfling__rogue__masculine': `${base}/combos/Halfling Male Rogue.png`,
      'halfling__sorcerer__masculine': `${base}/combos/Halfling Male Sorcerer.png`,
      'halfling__tinker__masculine': `${base}/combos/Halfling Male Tinker.png`,
      'halfling__warlock__masculine': `${base}/combos/Halfling Male Warlock.png`,
      'halfling__wizard__masculine': `${base}/combos/Halfling Male Wizard.png`,
      'halforc__barbarian__masculine': `${base}/combos/Half-Orc Male Barbarian.png`,
      'human__barbarian__feminine': `${base}/combos/Human Female Barbarian.png`,
      'human__barbarian__masculine': `${base}/combos/Human Male Barbarian.png`,
      'human__bard__feminine': `${base}/combos/Human Female Bard.png`,
      'human__bard__masculine': `${base}/combos/Human Male Bard.png`,
      'human__cleric__feminine': `${base}/combos/Human Female Cleric.png`,
      'human__cleric__masculine': `${base}/combos/Human Male Cleric.png`,
      'human__druid__feminine': `${base}/combos/Human Female Druid.png`,
      'human__druid__masculine': `${base}/combos/Human Male Druid.png`,
      'human__fighter__feminine': `${base}/combos/Human Female Fighter.png`,
      'human__fighter__masculine': `${base}/combos/Human Male Fighter.png`,
      'human__monk__feminine': `${base}/combos/Human Female Monk.png`,
      'human__monk__masculine': `${base}/combos/Human Male Monk.png`,
      'human__paladin__feminine': `${base}/combos/Human Female Paladin.png`,
      'human__paladin__masculine': `${base}/combos/Human Male Paladin.png`,
      'human__pirate__masculine': `${base}/combos/Human Male Pirate.png`,
      'human__ranger__feminine': `${base}/combos/Human Female Ranger.png`,
      'human__ranger__masculine': `${base}/combos/Human Male Ranger.png`,
      'human__rogue__feminine': `${base}/combos/Human Female Rogue.png`,
      'human__rogue__masculine': `${base}/combos/Human Male Rogue.png`,
      'human__sorcerer__feminine': `${base}/combos/Human Female Sorcerer.png`,
      'human__sorcerer__masculine': `${base}/combos/Human Male Sorcerer.png`,
      'human__tinker__feminine': `${base}/combos/Human Female Tinker.png`,
      'human__tinker__masculine': `${base}/combos/Human Tinker Male.png`,
      'human__warlock__feminine': `${base}/combos/Human Female Warlock.png`,
      'human__warlock__masculine': `${base}/combos/Human Male Warlock.png`,
      'human__wizard__feminine': `${base}/combos/Human Female Wizard.png`,
      'human__wizard__masculine': `${base}/combos/Human Wizard Male.png`,
      'tiefling__barbarian__masculine': `${base}/combos/Tiefling Male Barbarian.png`,
      'tiefling__bard__masculine': `${base}/combos/Tiefling Male Bard.png`,
      'tiefling__cleric__masculine': `${base}/combos/Tiefling Male Cleric.png`,
      'tiefling__druid__masculine': `${base}/combos/Tiefling Male Druid.png`,
      'tiefling__fighter__masculine': `${base}/combos/Tiefling Male Fighter.png`,
      'tiefling__monk__masculine': `${base}/combos/Tiefling Male Monk.png`,
      'tiefling__paladin__masculine': `${base}/combos/Tiefling Male Paladin.png`,
      'tiefling__pirate__masculine': `${base}/combos/Tiefling Male Pirate.png`,
      'tiefling__ranger__masculine': `${base}/combos/Tiefling Male Ranger.png`,
      'tiefling__rogue__masculine': `${base}/combos/Tiefling Male Rogue.png`,
      'tiefling__sorcerer__masculine': `${base}/combos/Tiefling Male Sorcerer.png`,
      'tiefling__tinker__masculine': `${base}/combos/Tiefling Male Tinker.png`,
      'tiefling__warlock__masculine': `${base}/combos/Tiefling Male Warlock.png`,
      'tiefling__wizard__masculine': `${base}/combos/Tiefling Male Wizard.png`,
    },
    species: {
      'human': `${base}/species/human.png`,
      'elf': `${base}/species/elf.png`,
    },
    classes: {
      'barbarian': `${base}/combos/Human Female Barbarian.png`,
      'bard': `${base}/combos/Human Female Bard.png`,
      'cleric': `${base}/combos/Human Female Cleric.png`,
      'druid': `${base}/combos/Human Female Druid.png`,
      'fighter': `${base}/combos/Human Female Fighter.png`,
      'monk': `${base}/combos/Human Female Monk.png`,
      'paladin': `${base}/combos/Human Female Paladin.png`,
      'pirate': `${base}/combos/Human Male Pirate.png`,
      'ranger': `${base}/combos/Human Female Ranger.png`,
      'rogue': `${base}/combos/Human Female Rogue.png`,
      'sorcerer': `${base}/combos/Human Female Sorcerer.png`,
      'tinker': `${base}/combos/Human Female Tinker.png`,
      'warlock': `${base}/combos/Human Female Warlock.png`,
      'wizard': `${base}/combos/Human Female Wizard.png`,
    },
    species_order: ['human', 'elf', 'aasimar', 'dwarf', 'dragonborn', 'tiefling', 'goliath'],
    class_order: ['barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk', 'paladin', 'ranger', 'rogue', 'sorcerer', 'warlock', 'wizard'],
    presentation_order: ['masculine', 'feminine', 'neutral'],
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
    const allowSpeciesFallback = !(options && options.allowSpeciesFallback === false);
    const allowClassFallback = !(options && options.allowClassFallback === false);
    const neutralFallback = String((options && options.neutralFallback) || '').trim();

    if (!cls) return neutralFallback;

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

    // 4. Class-only portrait fallback (legacy manifest support)
    if (allowClassFallback && manifest.classes[cls]) return manifest.classes[cls];
    // 5. Species-only portrait fallback (legacy behavior)
    if (allowSpeciesFallback && manifest.species[sp]) return manifest.species[sp];
    // 6. Conventional species portrait drop-in path (legacy behavior)
    if (allowSpeciesFallback) return `${base}/species/${sp}.png`;
    // 7. Explicit neutral/blank fallback
    return neutralFallback;
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
