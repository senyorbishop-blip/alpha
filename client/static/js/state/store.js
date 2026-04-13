(function (global) {
  'use strict';
  // Live ownership boundary:
  // This store is intentionally limited to shell/runtime/session/socket/UI state.
  // Gameplay-domain collections (tokens, combat, map docs, etc.) remain owned by play.html
  // until an explicit migration stage promotes them.

  const state = {
    session: { id: '', returning: false },
    user: { id: '', name: '', role: 'viewer' },
    socket: { instance: null, reconnectTimer: null, pendingMessages: [], connected: false, status: 'idle' },
    map: { currentId: '', currentPoiId: '', currentContext: 'world', dmContext: 'world', navVersion: 0, clientNavIntent: 0 },
    ui: { activeRightTab: 'party', unreadLog: 0, currentTool: 'select', selectedDice: 20 },
    player: {
      dashboard: { mounted: false, open: false },
      lastScopedEvent: { type: '', scope: '', audience: '', uiChannel: '', timestamp: 0 },
      discovery: {
        latestId: '',
        latestTitle: '',
        latestKind: '',
        latestVisibility: '',
        latestSource: '',
        unreadCount: 0,
        savedCount: 0,
      },
      storyHooks: {
        totalCount: 0,
        activeCount: 0,
        objectiveCount: 0,
        promptCount: 0,
        latestTitle: '',
        latestKind: '',
      },
    },
    selection: { tokenId: '' },
    editor: { activeTool: 'select', mode: 'tactical' },
    fog: { enabled: false, preview: false, reveal: true, brushSize: 3, mapContext: 'world' },
    vision: { preview: { enabled: false, tokenId: '', ownerId: '' }, showFallbackBanner: false },
    viewer: { powerCatalog: {} },
    charSheet: {},
  };

  function deepMerge(target, source) {
    Object.keys(source || {}).forEach((key) => {
      const next = source[key];
      if (next && typeof next === 'object' && !Array.isArray(next)) {
        if (!target[key] || typeof target[key] !== 'object' || Array.isArray(target[key])) target[key] = {};
        deepMerge(target[key], next);
      } else {
        target[key] = next;
      }
    });
    return target;
  }

  function init(initialState = {}) {
    deepMerge(state, initialState);
    return state;
  }

  function patch(partial = {}) {
    return deepMerge(state, partial);
  }

  function set(path, value) {
    const parts = String(path || '').split('.').filter(Boolean);
    if (!parts.length) return value;
    let node = state;
    while (parts.length > 1) {
      const key = parts.shift();
      if (!node[key] || typeof node[key] !== 'object') node[key] = {};
      node = node[key];
    }
    node[parts[0]] = value;
    return value;
  }

  function get(path, fallback = undefined) {
    const parts = String(path || '').split('.').filter(Boolean);
    let node = state;
    for (const key of parts) {
      if (!node || typeof node !== 'object' || !(key in node)) return fallback;
      node = node[key];
    }
    return node === undefined ? fallback : node;
  }

  function getState() {
    return state;
  }

  function getCharacterModifiers() {
    const current = getState();
    const charSheet = (current && typeof current.charSheet === 'object' && current.charSheet) ? current.charSheet : {};
    const abilitiesRoot = (charSheet && typeof charSheet.abilities === 'object' && charSheet.abilities) ? charSheet.abilities : {};
    const abilities = (abilitiesRoot && typeof abilitiesRoot.scores === 'object' && abilitiesRoot.scores)
      ? abilitiesRoot.scores
      : abilitiesRoot;
    const abilityScores = (charSheet.book && typeof charSheet.book.abilityScores === 'object') ? charSheet.book.abilityScores : (charSheet.abilityScores || {});
    const readAbility = (shortKey, longKey) => {
      const direct = abilities && (abilities[shortKey] ?? abilities[longKey]);
      if (direct !== undefined && direct !== null && direct !== '') return direct;
      const fromBook = abilityScores && (abilityScores[shortKey] ?? abilityScores[longKey]);
      if (fromBook !== undefined && fromBook !== null && fromBook !== '') return fromBook;
      return 10;
    };
    const knownProficiencies = Array.isArray(charSheet.skillProficiencies)
      ? charSheet.skillProficiencies
      : (Array.isArray(charSheet.book?.skillProficiencies) ? charSheet.book.skillProficiencies : []);

    function mod(score) {
      return Math.floor(((parseInt(score, 10) || 10) - 10) / 2);
    }

    function hasSkill(skillName) {
      return knownProficiencies.includes(skillName);
    }

    const level = parseInt(charSheet.classes?.[0]?.level || charSheet.level || 1, 10);
    const profBonus = parseInt(charSheet.proficiencyBonus ?? charSheet.profBonus ?? charSheet.book?.proficiencyBonus ?? charSheet.book?.profBonus, 10) || (2 + Math.floor((Math.max(1, level || 1) - 1) / 4));
    const strMod = mod(readAbility('str', 'strength'));
    const dexMod = mod(readAbility('dex', 'dexterity'));
    const conMod = mod(readAbility('con', 'constitution'));
    const intMod = mod(readAbility('int', 'intelligence'));
    const wisMod = mod(readAbility('wis', 'wisdom'));
    const chaMod = mod(readAbility('cha', 'charisma'));

    return {
      str: strMod,
      dex: dexMod,
      con: conMod,
      int: intMod,
      wis: wisMod,
      cha: chaMod,
      profBonus,
      initiative: dexMod,
      skills: {
        acrobatics: dexMod + (hasSkill('Acrobatics') ? profBonus : 0),
        animalHandling: wisMod + (hasSkill('Animal Handling') ? profBonus : 0),
        arcana: intMod + (hasSkill('Arcana') ? profBonus : 0),
        athletics: strMod + (hasSkill('Athletics') ? profBonus : 0),
        deception: chaMod + (hasSkill('Deception') ? profBonus : 0),
        history: intMod + (hasSkill('History') ? profBonus : 0),
        insight: wisMod + (hasSkill('Insight') ? profBonus : 0),
        intimidation: chaMod + (hasSkill('Intimidation') ? profBonus : 0),
        investigation: intMod + (hasSkill('Investigation') ? profBonus : 0),
        medicine: wisMod + (hasSkill('Medicine') ? profBonus : 0),
        nature: intMod + (hasSkill('Nature') ? profBonus : 0),
        perception: wisMod + (hasSkill('Perception') ? profBonus : 0),
        performance: chaMod + (hasSkill('Performance') ? profBonus : 0),
        persuasion: chaMod + (hasSkill('Persuasion') ? profBonus : 0),
        religion: intMod + (hasSkill('Religion') ? profBonus : 0),
        sleightOfHand: dexMod + (hasSkill('Sleight of Hand') ? profBonus : 0),
        stealth: dexMod + (hasSkill('Stealth') ? profBonus : 0),
        survival: wisMod + (hasSkill('Survival') ? profBonus : 0),
      },
    };
  }

  const api = { init, patch, set, get, getState, getCharacterModifiers };
  global.AppStore = api;
  global.AppStateStore = api;
})(window);
