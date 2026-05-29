(function initCharacterBuilderStepEquipment(global) {
  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function registerStep(step) {
    if (!global.CharacterBuilderStepModules || typeof global.CharacterBuilderStepModules !== 'object') {
      global.CharacterBuilderStepModules = {};
    }
    global.CharacterBuilderStepModules[step.id] = step;
  }
  var PACK_DEFS = {
    backpack: {
      id: 'backpack',
      name: 'Backpack',
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Bedroll', 'Mess Kit', 'Tinderbox', 'Torch ×10', 'Rations ×10 days', 'Waterskin', 'Rope (50 ft)'],
    },
    explorer_pack: {
      id: 'explorer_pack',
      name: "Explorer's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Bedroll', 'Mess Kit', 'Tinderbox', 'Torch ×10', 'Rations ×10 days', 'Waterskin', 'Rope (50 ft)'],
    },
    dungeoneer_pack: {
      id: 'dungeoneer_pack',
      name: "Dungeoneer's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Crowbar', 'Hammer', 'Pitons ×10', 'Torch ×10', 'Tinderbox', 'Rations ×10 days', 'Waterskin', 'Rope (50 ft)'],
    },
    burglar_pack: {
      id: 'burglar_pack',
      name: "Burglar's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Bag of Ball Bearings', 'String (10 ft)', 'Bell', 'Candles ×5', 'Crowbar', 'Hammer', 'Pitons ×10', 'Hooded Lantern', 'Oil Flasks ×2', 'Rations ×5 days', 'Tinderbox', 'Waterskin', 'Rope (50 ft)'],
    },
    diplomat_pack: {
      id: 'diplomat_pack',
      name: "Diplomat's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Chest', 'Cases for Maps and Scrolls ×2', 'Fine Clothes', 'Ink', 'Ink Pen', 'Lamp', 'Oil Flasks ×2', 'Paper ×5 sheets', 'Perfume', 'Sealing Wax', 'Soap'],
    },
    entertainer_pack: {
      id: 'entertainer_pack',
      name: "Entertainer's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Bedroll', 'Costume ×2', 'Candles ×5', 'Rations ×5 days', 'Waterskin', 'Disguise Kit'],
    },
    priest_pack: {
      id: 'priest_pack',
      name: "Priest's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Blanket', 'Candles ×10', 'Tinderbox', 'Alms Box', 'Incense ×2 blocks', 'Censer', 'Vestments', 'Rations ×2 days', 'Waterskin'],
    },
    scholar_pack: {
      id: 'scholar_pack',
      name: "Scholar's Pack",
      own_weight_lbs: 5,
      capacity_lbs: 30,
      contents: ['Book of Lore', 'Ink', 'Ink Pen', 'Parchment ×10 sheets', 'Little Bag of Sand', 'Small Knife'],
    },
    bag_of_holding: {
      id: 'bag_of_holding',
      name: 'Bag of Holding',
      own_weight_lbs: 15,
      capacity_lbs: 500,
      volume_ft3: 64,
      extradimensional: true,
      contents: [],
    },
  };

  var STARTER_LOADOUTS = {
    barbarian: [
      { id: 'barbarian_greataxe', label: 'Greataxe Bruiser', items: ['Greataxe', 'Handaxe ×2', 'Javelin ×4'] },
      { id: 'barbarian_maul', label: 'Maul Crusher', items: ['Maul', 'Handaxe ×2', 'Javelin ×4'] },
      { id: 'barbarian_shield', label: 'Axe & Shield', items: ['Battleaxe', 'Shield', 'Javelin ×4'] },
    ],
    bard: [
      { id: 'bard_rapier', label: 'Rapier Performer', items: ['Rapier', 'Dagger', 'Light Crossbow', 'Bolts ×20'] },
      { id: 'bard_longsword', label: 'Longsword Balladeer', items: ['Longsword', 'Dagger', 'Shortbow', 'Arrows ×20'] },
      { id: 'bard_dual', label: 'Dual Dagger Troubadour', items: ['Dagger ×2', 'Shortbow', 'Arrows ×20'] },
    ],
    cleric: [
      { id: 'cleric_mace', label: 'Mace & Shield', items: ['Mace', 'Shield', 'Light Crossbow', 'Bolts ×20'] },
      { id: 'cleric_warhammer', label: 'Warhammer Devotee', items: ['Warhammer', 'Shield', 'Javelin ×4'] },
      { id: 'cleric_spear', label: 'Spear Acolyte', items: ['Spear', 'Shield', 'Mace'] },
    ],
    druid: [
      { id: 'druid_staff', label: 'Quarterstaff Warden', items: ['Quarterstaff', 'Scimitar', 'Dagger'] },
      { id: 'druid_spear', label: 'Spear Keeper', items: ['Spear', 'Shield', 'Dagger'] },
      { id: 'druid_club', label: 'Club Mystic', items: ['Club', 'Dagger ×2', 'Sling', 'Sling Bullets ×20'] },
    ],
    fighter: [
      { id: 'fighter_greatsword', label: 'Greatsword Vanguard', items: ['Greatsword', 'Handaxe ×2', 'Javelin ×4'] },
      { id: 'fighter_longsword', label: 'Sword & Board', items: ['Longsword', 'Shield', 'Javelin ×4'] },
      { id: 'fighter_polearm', label: 'Polearm Sentinel', items: ['Halberd', 'Light Crossbow', 'Bolts ×20'] },
    ],
    monk: [
      { id: 'monk_staff', label: 'Bo Staff Adept', items: ['Quarterstaff', 'Dart ×10'] },
      { id: 'monk_shortsword', label: 'Shortblade Initiate', items: ['Shortsword', 'Dart ×10'] },
      { id: 'monk_spear', label: 'Spear Disciple', items: ['Spear', 'Dart ×10'] },
    ],
    paladin: [
      { id: 'paladin_longsword', label: 'Longsword Guardian', items: ['Longsword', 'Shield', 'Javelin ×5'] },
      { id: 'paladin_warhammer', label: 'Warhammer Defender', items: ['Warhammer', 'Shield', 'Javelin ×5'] },
      { id: 'paladin_greatweapon', label: 'Great Weapon Oathsworn', items: ['Greatsword', 'Javelin ×5'] },
    ],
    ranger: [
      { id: 'ranger_longsword_bow', label: 'Longsword Archer', items: ['Longsword', 'Longbow', 'Arrows ×20', 'Dagger ×2'] },
      { id: 'ranger_dual_scimitar', label: 'Dual Scimitar Stalker', items: ['Scimitar ×2', 'Longbow', 'Arrows ×20'] },
      { id: 'ranger_spear_shield', label: 'Spear Warden', items: ['Spear', 'Shield', 'Longbow', 'Arrows ×20'] },
    ],
    rogue: [
      { id: 'rogue_rapier', label: 'Rapier Cutpurse', items: ['Rapier', 'Shortbow', 'Arrows ×20', 'Dagger ×2'] },
      { id: 'rogue_shortsword', label: 'Dual Shortsword Sneak', items: ['Shortsword ×2', 'Shortbow', 'Arrows ×20'] },
      { id: 'rogue_dagger', label: 'Dagger Skirmisher', items: ['Dagger ×4', 'Shortbow', 'Arrows ×20'] },
    ],
    sorcerer: [
      { id: 'sorcerer_light_xbow', label: 'Crossbow Adept', items: ['Light Crossbow', 'Bolts ×20', 'Dagger ×2'] },
      { id: 'sorcerer_quarterstaff', label: 'Quarterstaff Channeler', items: ['Quarterstaff', 'Dagger ×2'] },
      { id: 'sorcerer_sling', label: 'Sling Arcanist', items: ['Sling', 'Sling Bullets ×20', 'Dagger ×2'] },
    ],
    warlock: [
      { id: 'warlock_light_xbow', label: 'Crossbow Pactbound', items: ['Light Crossbow', 'Bolts ×20', 'Dagger'] },
      { id: 'warlock_simple_blade', label: 'Blade Pact Initiate', items: ['Quarterstaff', 'Dagger ×2'] },
      { id: 'warlock_spear', label: 'Spear Hexer', items: ['Spear', 'Dagger', 'Light Crossbow', 'Bolts ×20'] },
    ],
    wizard: [
      { id: 'wizard_quarterstaff', label: 'Quarterstaff Savant', items: ['Quarterstaff', 'Dagger'] },
      { id: 'wizard_light_xbow', label: 'Crossbow Savant', items: ['Light Crossbow', 'Bolts ×20', 'Dagger'] },
      { id: 'wizard_sling', label: 'Sling Scholar', items: ['Sling', 'Sling Bullets ×20', 'Dagger'] },
    ],
    tinker: [
      { id: 'tinker_hand_crossbow', label: 'Bolt Rig Starter', items: ['Hand Crossbow', 'Bolts ×20', 'Light Hammer', "Tinker's Tools"] },
      { id: 'tinker_spear_shield', label: 'Field Engineer Kit', items: ['Spear', 'Shield', 'Light Crossbow', 'Bolts ×20', "Tinker's Tools"] },
      { id: 'tinker_throwing', label: 'Prototype Thrower', items: ['Dagger ×3', 'Light Hammer', "Tinker's Tools", 'Shield'] },
    ],
    pirate: [
      { id: 'pirate_cutlass', label: 'Cutlass Raider', items: ['Scimitar', 'Pistol', 'Bullets ×20', 'Dagger'] },
      { id: 'pirate_duel', label: 'Dueling Buccaneer', items: ['Rapier', 'Pistol', 'Bullets ×20', 'Dagger'] },
      { id: 'pirate_boarder', label: 'Boarding Specialist', items: ['Handaxe', 'Shield', 'Musket', 'Bullets ×20'] },
    ],
  };

  var STARTER_WEAPON_STATS = {
    'club': { damage_dice: '1d4', damage_type: 'bludgeoning', weapon_properties: ['Light'], range: 'Melee 5 ft' },
    'dagger': { damage_dice: '1d4', damage_type: 'piercing', weapon_properties: ['Finesse', 'Light', 'Thrown'], range: '20/60 ft' },
    'dart': { damage_dice: '1d4', damage_type: 'piercing', weapon_properties: ['Finesse', 'Thrown'], range: '20/60 ft' },
    'greatsword': { damage_dice: '2d6', damage_type: 'slashing', weapon_properties: ['Heavy', 'Two-Handed'], range: 'Melee 5 ft' },
    'greataxe': { damage_dice: '1d12', damage_type: 'slashing', weapon_properties: ['Heavy', 'Two-Handed'], range: 'Melee 5 ft' },
    'halberd': { damage_dice: '1d10', damage_type: 'slashing', weapon_properties: ['Heavy', 'Reach', 'Two-Handed'], range: 'Melee 10 ft' },
    'hand crossbow': { damage_dice: '1d6', damage_type: 'piercing', weapon_properties: ['Ammunition', 'Light', 'Loading'], range: '30/120 ft' },
    'handaxe': { damage_dice: '1d6', damage_type: 'slashing', weapon_properties: ['Light', 'Thrown'], range: '20/60 ft' },
    'javelin': { damage_dice: '1d6', damage_type: 'piercing', weapon_properties: ['Thrown'], range: '30/120 ft' },
    'light crossbow': { damage_dice: '1d8', damage_type: 'piercing', weapon_properties: ['Ammunition', 'Loading', 'Two-Handed'], range: '80/320 ft' },
    'light hammer': { damage_dice: '1d4', damage_type: 'bludgeoning', weapon_properties: ['Light', 'Thrown'], range: '20/60 ft' },
    'longbow': { damage_dice: '1d8', damage_type: 'piercing', weapon_properties: ['Ammunition', 'Heavy', 'Two-Handed'], range: '150/600 ft' },
    'longsword': { damage_dice: '1d8', damage_type: 'slashing', versatile_damage: '1d10', weapon_properties: ['Versatile'], range: 'Melee 5 ft' },
    'mace': { damage_dice: '1d6', damage_type: 'bludgeoning', weapon_properties: [], range: 'Melee 5 ft' },
    'maul': { damage_dice: '2d6', damage_type: 'bludgeoning', weapon_properties: ['Heavy', 'Two-Handed'], range: 'Melee 5 ft' },
    'musket': { damage_dice: '1d12', damage_type: 'piercing', weapon_properties: ['Ammunition', 'Loading', 'Two-Handed'], range: '40/120 ft' },
    'pistol': { damage_dice: '1d10', damage_type: 'piercing', weapon_properties: ['Ammunition', 'Loading'], range: '30/90 ft' },
    'quarterstaff': { damage_dice: '1d6', damage_type: 'bludgeoning', versatile_damage: '1d8', weapon_properties: ['Versatile'], range: 'Melee 5 ft' },
    'rapier': { damage_dice: '1d8', damage_type: 'piercing', weapon_properties: ['Finesse'], range: 'Melee 5 ft' },
    'scimitar': { damage_dice: '1d6', damage_type: 'slashing', weapon_properties: ['Finesse', 'Light'], range: 'Melee 5 ft' },
    'shortbow': { damage_dice: '1d6', damage_type: 'piercing', weapon_properties: ['Ammunition', 'Two-Handed'], range: '80/320 ft' },
    'shortsword': { damage_dice: '1d6', damage_type: 'piercing', weapon_properties: ['Finesse', 'Light'], range: 'Melee 5 ft' },
    'sling': { damage_dice: '1d4', damage_type: 'bludgeoning', weapon_properties: ['Ammunition'], range: '30/120 ft' },
    'spear': { damage_dice: '1d6', damage_type: 'piercing', versatile_damage: '1d8', weapon_properties: ['Thrown', 'Versatile'], range: '20/60 ft' },
    'warhammer': { damage_dice: '1d8', damage_type: 'bludgeoning', versatile_damage: '1d10', weapon_properties: ['Versatile'], range: 'Melee 5 ft' },
  };

  function parseQtyLine(raw) {
    var text = String(raw || '').trim();
    if (!text) return null;
    var qty = 1;
    var name = text;
    var m = text.match(/^(.*?)\s*[×x]\s*(\d+)$/i);
    if (m) {
      name = String(m[1] || '').trim();
      qty = Math.max(1, parseInt(m[2], 10) || 1);
    }
    if (!name) return null;
    return { name: name, qty: qty };
  }

  function inferEquipmentKind(name) {
    var lower = String(name || '').toLowerCase();
    if (/shield/.test(lower)) return 'shield';
    if (/armor|armour|mail|plate|leather|breastplate|splint|chain/.test(lower)) return 'armor';
    if (/sword|axe|mace|hammer|staff|spear|bow|crossbow|dagger|scimitar|rapier|halberd|maul|javelin|dart|sling|pistol|musket/.test(lower)) return 'weapon';
    return 'gear';
  }

  function weaponStatsForName(name) {
    var lower = String(name || '').trim().toLowerCase();
    if (!lower) return null;
    lower = lower.replace(/\s*[×x]\s*\d+$/, '').trim().replace(/\s*\(\d+\)$/, '').trim();
    var singular = lower.replace(/s$/, '').trim();
    return STARTER_WEAPON_STATS[lower] || STARTER_WEAPON_STATS[singular] || null;
  }

  function toInventoryItem(row) {
    var parsed = parseQtyLine(row);
    if (!parsed) return null;
    var out = {
      name: parsed.name,
      qty: parsed.qty,
      kind: inferEquipmentKind(parsed.name),
      type: inferEquipmentKind(parsed.name),
      equipment_kind: inferEquipmentKind(parsed.name),
      item_type: inferEquipmentKind(parsed.name),
      source: 'builder_starting_choice',
      equipped: false,
    };
    var weaponStats = weaponStatsForName(parsed.name);
    if (weaponStats) {
      out.damage_dice = String(weaponStats.damage_dice || '').trim();
      out.damage = out.damage_dice;
      out.damage_type = String(weaponStats.damage_type || '').trim();
      out.versatile_damage = String(weaponStats.versatile_damage || '').trim();
      out.range = String(weaponStats.range || '').trim();
      out.weapon_properties = Array.isArray(weaponStats.weapon_properties) ? weaponStats.weapon_properties.slice() : [];
    }
    return out;
  }

  function buildPackContainer(packId) {
    var def = PACK_DEFS[String(packId || '')];
    if (!def) return null;
    return {
      id: String(def.id || '').trim(),
      name: String(def.name || 'Pack').trim(),
      qty: 1,
      equipment_kind: 'gear',
      item_type: 'gear',
      is_container: true,
      extradimensional: !!def.extradimensional,
      own_weight_lbs: Number(def.own_weight_lbs || 0) || 0,
      capacity_lbs: Number(def.capacity_lbs || 0) || 0,
      volume_ft3: Number(def.volume_ft3 || 0) || 0,
      bag_contents: (Array.isArray(def.contents) ? def.contents : []).map(toInventoryItem).filter(Boolean),
      source: 'builder_starting_pack',
    };
  }

  function getClassId(draft) {
    var cls = draft && draft.class && typeof draft.class === 'object' ? draft.class : {};
    return String(cls.id || '').trim().toLowerCase();
  }

  function getSelectedLoadout(choices, classId) {
    var all = STARTER_LOADOUTS[classId] || [];
    var selectedId = String(choices && choices.starterLoadoutId || '').trim();
    if (!selectedId && all.length) selectedId = all[0].id;
    return all.find(function (row) { return String(row.id) === selectedId; }) || null;
  }


  function normalizeLibraryItem(raw) {
    if (!raw || typeof raw !== 'object') return null;
    var name = String(raw.name || '').trim().slice(0, 80);
    if (!name) return null;
    var id = String(raw.id || name).trim().slice(0, 80) || name;
    var qty = Math.max(1, Math.min(999, parseInt(raw.qty != null ? raw.qty : raw.default_qty, 10) || 1));
    var out = {
      id: id,
      name: name,
      qty: qty,
      category: String(raw.category || raw.type || 'Gear').trim().slice(0, 40) || 'Gear',
      rarity: String(raw.rarity || 'Common').trim().slice(0, 32) || 'Common',
      price: String(raw.price || raw.default_price || '').trim().slice(0, 32),
      notes: String(raw.notes || raw.description || '').trim().slice(0, 240),
    };
    ['equipment_kind','item_type','armor_type','handedness','damage_dice','damage_type','versatile_damage','source'].forEach(function (key) {
      var value = raw[key];
      if (value != null && String(value).trim() !== '') out[key] = String(value).trim();
    });
    ['base_ac','dex_cap','ac_bonus','strength_requirement','weight_lbs','own_weight_lbs','capacity_lbs','volume_ft3'].forEach(function (key) {
      if (raw[key] == null || String(raw[key]).trim() === '') return;
      var num = key.indexOf('_lbs') >= 0 || key === 'volume_ft3' ? parseFloat(raw[key]) : parseInt(raw[key], 10);
      if (Number.isFinite(num)) out[key] = num;
    });
    if ('stealth_disadvantage' in raw) out.stealth_disadvantage = !!raw.stealth_disadvantage;
    if (Array.isArray(raw.weapon_properties)) out.weapon_properties = raw.weapon_properties.map(function (v) { return String(v || '').trim(); }).filter(Boolean).slice(0, 12);
    return out;
  }

  function getLibraryEntries() {
    var source = global.CharacterBuilderItemLibrary;
    var rows = [];
    if (source && typeof source === 'object') {
      if (Array.isArray(source.entries)) rows = rows.concat(source.entries);
      if (Array.isArray(source.srdItems)) rows = rows.concat(source.srdItems);
    }
    if (!rows.length && global.itemLibraryEntries && typeof global.itemLibraryEntries === 'object') {
      rows = rows.concat(Object.keys(global.itemLibraryEntries).map(function (key) { return global.itemLibraryEntries[key]; }));
    }
    if (!rows.length && Array.isArray(global._srdItems)) rows = rows.concat(global._srdItems);
    var seen = {};
    return rows.map(normalizeLibraryItem).filter(function (entry) {
      if (!entry || !entry.id || seen[entry.id]) return false;
      seen[entry.id] = true;
      return true;
    });
  }

  function getSelectedLibraryItems(choices) {
    var selected = Array.isArray(choices && choices.libraryItems) ? choices.libraryItems : [];
    return selected.map(normalizeLibraryItem).filter(Boolean);
  }

  function libraryItemToInventoryItem(row) {
    var item = normalizeLibraryItem(row);
    if (!item) return null;
    var kind = String(item.equipment_kind || item.item_type || inferEquipmentKind(item.name) || 'gear').trim().toLowerCase() || 'gear';
    var out = {
      id: item.id,
      name: item.name,
      qty: item.qty,
      kind: kind,
      type: kind,
      equipment_kind: kind,
      item_type: kind,
      category: item.category,
      rarity: item.rarity,
      source: item.source || 'builder_item_library',
      equipped: false,
    };
    ['notes','price','armor_type','handedness','damage_dice','damage_type','versatile_damage','base_ac','dex_cap','ac_bonus','strength_requirement','stealth_disadvantage','weight_lbs','own_weight_lbs','capacity_lbs','volume_ft3'].forEach(function (key) {
      if (item[key] != null && item[key] !== '') out[key] = item[key];
    });
    if (Array.isArray(item.weapon_properties)) out.weapon_properties = item.weapon_properties.slice(0, 12);
    return out;
  }

  function renderLibraryPicker(choices) {
    var entries = getLibraryEntries();
    var selected = getSelectedLibraryItems(choices);
    var selectedIds = {};
    selected.forEach(function (item) { selectedIds[item.id] = true; });
    var visible = entries.slice();
    if (!entries.length) {
      return [
        '<div class="field"><label>Library Bonus Items</label>',
        '<div class="builder-help-text">No campaign/SRD item library entries are available yet. You can still type items above.</div>',
        '</div>',
      ].join('');
    }
    return [
      '<div class="field cb-library-field"><label>Library Bonus Items <span class="cb-optional">optional</span></label>',
      '<div class="builder-help-text">If the DM allows “one rare item” or extra starting gear, search here and tap Add. Selected items are saved into your starting inventory.</div>',
      '<div class="cb-library-toolbar">',
      '<input type="search" data-builder-library-search="1" placeholder="Search item library by name, rarity, or category…" autocomplete="off" />',
      '<select data-builder-library-rarity="1"><option value="">All rarities</option><option>Common</option><option>Uncommon</option><option>Rare</option><option>Very Rare</option><option>Legendary</option></select>',
      '</div>',
      '<div class="cb-library-selected" data-builder-library-selected="1">',
      selected.length ? selected.map(function (item) {
        return '<span class="cb-library-chip">' + escHtml(item.name) + ' ×' + escHtml(item.qty) + '<button type="button" data-builder-library-remove="' + escHtml(item.id) + '" aria-label="Remove ' + escHtml(item.name) + '">×</button></span>';
      }).join('') : '<span class="builder-help-text" style="margin:0;">No library items selected yet.</span>',
      '</div>',
      '<div class="cb-library-list" data-builder-library-list="1">',
      visible.map(function (entry) {
        var picked = selectedIds[entry.id];
        return '<button type="button" class="cb-library-card" data-builder-library-id="' + escHtml(entry.id) + '" data-builder-library-name="' + escHtml(entry.name) + '" data-builder-library-rarity-value="' + escHtml(entry.rarity) + '" data-builder-library-category="' + escHtml(entry.category) + '"' + (picked ? ' disabled' : '') + '>'
          + '<strong>' + escHtml(entry.name) + '</strong>'
          + '<span>' + escHtml(entry.rarity) + ' • ' + escHtml(entry.category) + (entry.price ? ' • ' + escHtml(entry.price) : '') + '</span>'
          + (entry.notes ? '<em>' + escHtml(entry.notes.slice(0, 110)) + '</em>' : '')
          + '<small>' + (picked ? 'Added' : 'Add') + '</small>'
          + '</button>';
      }).join(''),
      '</div>',
      '',
      '</div>',
    ].join('');
  }

  function hydrateEquipmentState(draft) {
    var equipment = draft && draft.equipment && typeof draft.equipment === 'object' ? draft.equipment : {};
    var currency = equipment.currency && typeof equipment.currency === 'object'
      ? equipment.currency
      : { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
    var classId = getClassId(draft);
    var choices = equipment.choices && typeof equipment.choices === 'object' && !Array.isArray(equipment.choices)
      ? equipment.choices
      : {
        starterLoadoutId: '',
        additionalItems: Array.isArray(equipment.choices) ? equipment.choices : [],
      };
    if (!Array.isArray(choices.additionalItems)) choices.additionalItems = [];
    if (!Array.isArray(choices.libraryItems)) choices.libraryItems = [];
    var loadout = getSelectedLoadout(choices, classId);
    if (!choices.starterLoadoutId && loadout) choices.starterLoadoutId = loadout.id;

    var inventory = [];
    if (loadout && Array.isArray(loadout.items)) {
      loadout.items.forEach(function (line) {
        var item = toInventoryItem(line);
        if (item) inventory.push(item);
      });
      var equippedPrimary = false;
      inventory.forEach(function markPrimaryWeapon(item) {
        if (equippedPrimary || !item || String(item.equipment_kind || '').toLowerCase() !== 'weapon') return;
        item.equipped = true;
        equippedPrimary = true;
      });
    }
    var packItem = buildPackContainer(choices.startingPackId || equipment.startingPack || '');
    if (packItem) inventory.push(packItem);
    (choices.additionalItems || []).forEach(function (line) {
      var maybeContainer = String(line || '').trim().toLowerCase() === 'bag of holding'
        ? buildPackContainer('bag_of_holding')
        : null;
      if (maybeContainer) {
        inventory.push(maybeContainer);
        return;
      }
      var item = toInventoryItem(line);
      if (item) inventory.push(item);
    });
    getSelectedLibraryItems(choices).forEach(function (row) {
      var libraryItem = libraryItemToInventoryItem(row);
      if (libraryItem) inventory.push(libraryItem);
    });

    return {
      equipment: {
        startingPack: choices.startingPackId || '',
        choices: choices,
        currency: {
          cp: Math.max(0, parseInt(currency.cp, 10) || 0),
          sp: Math.max(0, parseInt(currency.sp, 10) || 0),
          ep: Math.max(0, parseInt(currency.ep, 10) || 0),
          gp: Math.max(0, parseInt(currency.gp, 10) || 0),
          pp: Math.max(0, parseInt(currency.pp, 10) || 0),
        },
        inventory: inventory,
      },
      classId: classId,
      loadout: loadout,
      choices: choices,
    };
  }

  registerStep({
    id: 'equipment',
    label: 'Equipment',
    render: function renderEquipmentStep(context) {
      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var state = hydrateEquipmentState(draft);
      var equipment = state.equipment;
      var choices = state.choices;
      var loadoutOptions = STARTER_LOADOUTS[state.classId] || [];
      var loadout = state.loadout;

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Starting Equipment</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Choose a curated starter loadout, then pick a pack and coin. All selections become real inventory entries.</div>',
        '</div>',

        '<div class="field"><label>Starter Weapon Loadout</label>',
        '<select id="builder-starter-loadout" class="sheet-book-input">',
        loadoutOptions.length
          ? loadoutOptions.map(function (row) {
              var selected = String(choices.starterLoadoutId || '') === String(row.id || '') ? ' selected' : '';
              return '<option value="' + escHtml(row.id) + '"' + selected + '>' + escHtml(row.label) + '</option>';
            }).join('')
          : '<option value="">Choose a class first</option>',
        '</select>',
        loadout ? '<div class="builder-help-text">' + escHtml(loadout.items.join(' • ')) + '</div>' : '<div class="builder-help-text">Select your class to unlock class-appropriate starter sets.</div>',
        '</div>',

        '<div class="field"><label>Starting Equipment Pack</label>',
        '<select id="builder-starting-pack" class="sheet-book-input">',
        '<option value="">No pack</option>',
        Object.keys(PACK_DEFS).map(function (id) {
          var def = PACK_DEFS[id];
          var selected = String(choices.startingPackId || '') === id ? ' selected' : '';
          return '<option value="' + escHtml(id) + '"' + selected + '>' + escHtml(def.name) + '</option>';
        }).join(''),
        '</select></div>',

        '<div class="field"><label>Additional Equipment <span class="cb-optional">comma-separated</span></label>',
        '<input type="text" data-builder-equipment-choices="1" value="' + escHtml((choices.additionalItems || []).join(', ')) + '" maxlength="420" placeholder="Thieves\' Tools, Rope, Bag of Holding…" />',
        '<div class="builder-help-text">These are also converted into real inventory items. "Bag of Holding" becomes a container entry.</div>',
        '</div>',

        renderLibraryPicker(choices),

        '<div class="field"><label>Starting Currency</label>',
        '<div class="builder-help-text">Type normally, including 0. The builder saves coin after you pause typing or leave the field.</div>',
        '<div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;">',
        ['cp', 'sp', 'ep', 'gp', 'pp'].map(function toCoin(coin) {
          return '<label style="display:flex;flex-direction:column;gap:3px;font-size:0.65rem;">'
            + escHtml(coin.toUpperCase())
            + '<input type="text" inputmode="numeric" pattern="[0-9]*" maxlength="5" data-builder-equipment-currency="' + coin + '" value="' + escHtml(equipment.currency[coin] != null ? equipment.currency[coin] : 0) + '" />'
            + '</label>';
        }).join(''),
        '</div></div>',
      ].join('');
    },
    bind: function bindEquipmentStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      var draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
      var state = hydrateEquipmentState(draft);

      function commitEquipment() {
        context.onSetField(['equipment'], state.equipment);
      }

      var loadoutSelect = root.querySelector('#builder-starter-loadout');
      if (loadoutSelect) {
        loadoutSelect.addEventListener('change', function () {
          state.choices.starterLoadoutId = String(loadoutSelect.value || '').trim();
          state.equipment = hydrateEquipmentState({ class: draft.class, equipment: state.equipment }).equipment;
          commitEquipment();
        });
      }

      var packSelect = root.querySelector('#builder-starting-pack');
      if (packSelect) {
        packSelect.addEventListener('change', function () {
          state.choices.startingPackId = String(packSelect.value || '').trim();
          state.equipment = hydrateEquipmentState({ class: draft.class, equipment: state.equipment }).equipment;
          commitEquipment();
        });
      }

      var choicesInput = root.querySelector('[data-builder-equipment-choices="1"]');
      if (choicesInput) {
        choicesInput.addEventListener('input', function onChoicesInput() {
          state.choices.additionalItems = String(choicesInput.value || '')
            .split(',')
            .map(function normalize(v) { return String(v || '').trim(); })
            .filter(Boolean);
          state.equipment = hydrateEquipmentState({ class: draft.class, equipment: state.equipment }).equipment;
          commitEquipment();
        });
      }

      var currencyTimer = null;
      function commitCurrencySoon(delay) {
        if (currencyTimer) clearTimeout(currencyTimer);
        currencyTimer = setTimeout(function () {
          state.equipment = hydrateEquipmentState({ class: draft.class, equipment: state.equipment }).equipment;
          commitEquipment();
        }, delay == null ? 260 : delay);
      }
      root.querySelectorAll('[data-builder-equipment-currency]').forEach(function (input) {
        input.addEventListener('focus', function () {
          if (String(input.value || '') === '0' && typeof input.select === 'function') input.select();
        });
        input.addEventListener('input', function () {
          var coin = String(input.dataset.builderEquipmentCurrency || '').trim();
          if (!coin) return;
          var cleaned = String(input.value || '').replace(/[^0-9]/g, '').slice(0, 5);
          if (input.value !== cleaned) input.value = cleaned;
          state.equipment.currency[coin] = cleaned === '' ? 0 : Math.max(0, parseInt(cleaned, 10) || 0);
          commitCurrencySoon(260);
        });
        input.addEventListener('blur', function () {
          var coin = String(input.dataset.builderEquipmentCurrency || '').trim();
          var value = String(input.value || '').replace(/[^0-9]/g, '').slice(0, 5);
          if (value === '') value = '0';
          input.value = value;
          if (coin) state.equipment.currency[coin] = Math.max(0, parseInt(value, 10) || 0);
          commitCurrencySoon(0);
        });
      });

      function applyLibraryFilter() {
        var search = String(root.querySelector('[data-builder-library-search="1"]') && root.querySelector('[data-builder-library-search="1"]').value || '').trim().toLowerCase();
        var rarity = String(root.querySelector('[data-builder-library-rarity="1"]') && root.querySelector('[data-builder-library-rarity="1"]').value || '').trim().toLowerCase();
        root.querySelectorAll('[data-builder-library-id]').forEach(function (card) {
          var hay = [card.dataset.builderLibraryName, card.dataset.builderLibraryRarityValue, card.dataset.builderLibraryCategory].join(' ').toLowerCase();
          var cardRarity = String(card.dataset.builderLibraryRarityValue || '').trim().toLowerCase();
          card.hidden = !!((search && hay.indexOf(search) < 0) || (rarity && cardRarity !== rarity));
        });
      }
      var librarySearch = root.querySelector('[data-builder-library-search="1"]');
      var libraryRarity = root.querySelector('[data-builder-library-rarity="1"]');
      if (librarySearch) librarySearch.addEventListener('input', applyLibraryFilter);
      if (libraryRarity) libraryRarity.addEventListener('change', applyLibraryFilter);
      root.querySelectorAll('[data-builder-library-id]').forEach(function (card) {
        card.addEventListener('click', function () {
          var id = String(card.dataset.builderLibraryId || '').trim();
          var entry = getLibraryEntries().find(function (row) { return row.id === id; });
          if (!entry) return;
          state.choices.libraryItems = getSelectedLibraryItems(state.choices).concat([entry]);
          state.equipment = hydrateEquipmentState({ class: draft.class, equipment: state.equipment }).equipment;
          commitEquipment();
        });
      });
      root.querySelectorAll('[data-builder-library-remove]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var id = String(btn.dataset.builderLibraryRemove || '').trim();
          state.choices.libraryItems = getSelectedLibraryItems(state.choices).filter(function (row) { return row.id !== id; });
          state.equipment = hydrateEquipmentState({ class: draft.class, equipment: state.equipment }).equipment;
          commitEquipment();
        });
      });

      commitEquipment();
    },
  });
})(window);
