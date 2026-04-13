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
  const GENDER_ALIASES = {
    male: 'masculine', hehim: 'masculine', masculine: 'masculine',
    female: 'feminine', sheher: 'feminine', feminine: 'feminine',
    neutral: 'neutral', theythem: 'neutral', androgynous: 'neutral', nonbinary: 'neutral',
  };

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
    return GENDER_ALIASES[key] || key || 'neutral';
  }

  const base = '/static/importer/portraits';
  const defaultManifest = {
    combos: {
      'human__fighter__masculine': `${base}/combos/human__fighter__masculine.png`,
      'human__fighter__feminine': `${base}/combos/human__fighter__feminine.png`,
      'human__fighter__neutral': `${base}/combos/human__fighter__neutral.png`,
      'elf__warlock__masculine': `${base}/combos/elf__warlock__masculine.png`,
      'elf__warlock__feminine': `${base}/combos/elf__warlock__feminine.png`,
      'elf__warlock__neutral': `${base}/combos/elf__warlock__neutral.png`,
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
    presentation_order: ['masculine','feminine','neutral']
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
    const exact = `${sp}__${cls}__${gender}`;
    if (manifest.combos[exact]) return manifest.combos[exact];
    const neutralCombo = `${sp}__${cls}__neutral`;
    if (manifest.combos[neutralCombo]) return manifest.combos[neutralCombo];
    if (manifest.species[sp]) return manifest.species[sp];
    if (manifest.classes[cls]) return manifest.classes[cls];
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
    renderImgMarkup,
    speciesKey,
    classKey,
    genderKey,
    get manifest() { return currentManifest(); },
  };

  ensureManifest();
}());
