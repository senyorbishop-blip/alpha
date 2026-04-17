(function initCharacterBuilderStepEquipment(global) {
  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
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
    var loadout = getSelectedLoadout(choices, classId);
    if (!choices.starterLoadoutId && loadout) choices.starterLoadoutId = loadout.id;

    var inventory = [];
    if (loadout && Array.isArray(loadout.items)) {
      loadout.items.forEach(function (line) {
        var item = toInventoryItem(line);
        if (item) inventory.push(item);
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

        '<div class="field"><label>Starting Currency</label>',
        '<div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;">',
        ['cp', 'sp', 'ep', 'gp', 'pp'].map(function toCoin(coin) {
          return '<label style="display:flex;flex-direction:column;gap:3px;font-size:0.65rem;">'
            + escHtml(coin.toUpperCase())
            + '<input type="number" min="0" max="99999" step="1" data-builder-path="equipment.currency.' + coin + '" value="' + escHtml(equipment.currency[coin] != null ? equipment.currency[coin] : 0) + '" />'
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

      commitEquipment();
    },
  });
})(window);
