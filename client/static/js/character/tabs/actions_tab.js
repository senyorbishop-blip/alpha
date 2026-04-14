/*
 * client/static/js/character/tabs/actions_tab.js
 * Actions Tab — Displays quick attacks, native actions, and tracked combat resources.
 *
 * Exposes: window.ActionsTab
 *   .initActionsTab(container, charData)
 */

(function initActionsTabModule(global) {
  'use strict';

  function _esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }



  const CUSTOM_ACTION_SURFACES = {
    barbarian: {
      title: 'Barbarian Combat Surface',
      copy: 'Open with Rage, then stay in melee and pressure with bonus-action and reaction tools. Your Rage loop should be obvious at a glance.',
      checks: ['Rage uses visible', 'Rage damage bonus visible', 'Subclass Rage riders visible'],
    },
    tinker: {
      title: 'Tinker Combat Surface',
      copy: 'Your best turns usually start with Gadget Charges or rig actions, then branch into specialty spells or subclass devices. This tab should feel like a field kit, not just a list of attacks.',
      checks: ['Gadget Charges visible', 'Deployment / countermeasure actions visible', 'Specialty spells linked from spell surface'],
    },
    pirate: {
      title: 'Pirate Combat Surface',
      copy: 'Pirate should feel aggressive and mobile here: Swagger Dice, dirty tricks, bonus-action pressure, and your equipped attacks should all read as one fighting style.',
      checks: ['Swagger Dice visible', 'Dirty trick cards visible', 'Bonus-action pressure tools loaded'],
    },
    monk: {
      title: 'Monk Combat Surface',
      copy: 'Monk should read as a live action-economy loop: Attack action cadence, Martial Arts follow-up, Focus spenders, and reaction defenses all visible together.',
      checks: ['Focus Points visible', 'Martial Arts / Flurry / Patient Defense cards visible', 'Reaction defenses visible'],
    },
    bard: {
      title: 'Bard Combat Surface',
      copy: 'Bard should feel like live support tempo: Bardic Inspiration spenders, reaction/control options, and spell tempo should all be visible from this tab.',
      checks: ['Bardic Inspiration die + uses visible', 'Subclass spenders visible (Glamour/Lore/Valor)', 'Spell + support flow visible in combat turns'],
    },
    paladin: {
      title: 'Paladin Combat Surface',
      copy: 'Paladin should feel like a hybrid frontline engine: weapon hits, smite timing, Lay on Hands triage, Channel Divinity options, and aura positioning cues all visible together.',
      checks: ['Lay on Hands visible', 'Channel Divinity visible', 'Smite + spell slot decision surface visible'],
    },
  };


  const CUSTOM_CLASS_ACTIONS = {
    tinker: {
      actions: [
        {
          key: 'quick deployment',
          name: 'Quick Deployment',
          summary: 'Deploy or swap a prepared device quickly so your battlefield kit comes online without wasting your whole turn.',
          actionType: 'bonus',
          resourceName: 'Gadget Charges',
          resourceSummary: 'Rig / gadget tempo tool',
          range: 'Self / deployed device',
          tags: ['Tinker', 'Rig'],
        },
        {
          key: 'overclocked device',
          name: 'Overclocked Device',
          summary: 'Push a tuned device past safe limits for a stronger burst of offense, protection, or reach.',
          actionType: 'action',
          resourceName: 'Gadget Charges',
          resourceSummary: 'Spend Gadget Charges',
          range: 'Device-dependent',
          tags: ['Tinker', 'Burst'],
        },
        {
          key: 'reactive countermeasure',
          name: 'Reactive Countermeasure',
          summary: 'Answer incoming danger with a prepared defensive trick, interruption, or stabilizing field tool.',
          actionType: 'reaction',
          resourceName: 'Gadget Charges',
          resourceSummary: 'Reaction countermeasure',
          range: 'Self / nearby ally',
          tags: ['Tinker', 'Defense'],
        },
        {
          key: 'emergency repairs',
          name: 'Emergency Repairs',
          summary: 'Patch an ally, construct, or device fast enough to matter in the middle of a fight.',
          actionType: 'action',
          resourceName: 'Gadget Charges',
          resourceSummary: 'Repair / stabilise',
          range: 'Touch / short reach',
          tags: ['Tinker', 'Support'],
        },
        {
          key: 'overcharge',
          name: 'Overcharge',
          summary: 'Spend deep reserves to unleash a dramatic high-output version of one of your devices.',
          actionType: 'action',
          resourceName: 'Gadget Charges',
          resourceSummary: 'Heavy charge spend',
          range: 'Device-dependent',
          tags: ['Tinker', 'Capstone Burst'],
        },
      ],
      subclassActions: {
        artillerist: [
          { key: 'arc cannon', name: 'Arc Cannon', summary: 'Fire or reposition your cannon-style rig for repeatable artillery pressure.', actionType: 'action', resourceName: 'Gadget Charges', resourceSummary: 'Artillery module', range: 'Long range', tags: ['Artillerist', 'Deployable'] },
          { key: 'shatter field', name: 'Shatter Field', summary: 'Turn your deployed tech into an area-denial and cover-breaking problem for the enemy.', actionType: 'action', resourceName: 'Gadget Charges', range: 'Area effect', tags: ['Artillerist', 'Area Control'] },
        ],
        alchemist: [
          { key: 'experimental elixirs', name: 'Experimental Elixirs', summary: 'Apply a prepared brew for healing, mobility, resistance, or an emergency answer.', actionType: 'action', resourceName: 'Gadget Charges', range: 'Touch / ally', tags: ['Alchemist', 'Support'] },
          { key: 'panacea kit', name: 'Panacea Kit', summary: 'Deliver a premium recovery / cleansing package when attrition is starting to matter.', actionType: 'action', resourceName: 'Gadget Charges', range: 'Touch / ally', tags: ['Alchemist', 'Recovery'] },
        ],
        mechanist: [
          { key: 'companion frame', name: 'Companion Frame', summary: 'Command or redirect your mechanical partner so it acts like a real second body on the field.', actionType: 'bonus', resourceName: 'Gadget Charges', range: 'Companion / command range', tags: ['Mechanist', 'Companion'] },
          { key: 'linked actions', name: 'Linked Actions', summary: 'Chain your turn with your frame so your command and its follow-up feel like one system.', actionType: 'bonus', resourceName: 'Gadget Charges', range: 'Companion / command range', tags: ['Mechanist', 'Tempo'] },
        ],
        saboteur: [
          { key: 'ghost tools', name: 'Ghost Tools', summary: 'Use hidden rigging and subtle devices to set up stealth pressure or a clean breach.', actionType: 'bonus', resourceName: 'Gadget Charges', range: 'Self / setup zone', tags: ['Saboteur', 'Stealth'] },
          { key: 'chain reaction', name: 'Chain Reaction', summary: 'Turn one successful disruption into follow-up battlefield pressure.', actionType: 'reaction', resourceName: 'Gadget Charges', range: 'Triggered rider', tags: ['Saboteur', 'Control'] },
        ],
      },
    },
    pirate: {
      actions: [
        { key: 'dirty fighting', name: 'Dirty Fighting', summary: 'Exploit distraction, footing, or timing to create ugly little advantages that swing a duel.', actionType: 'bonus', resourceName: 'Swagger Dice', resourceSummary: 'Spend Swagger Dice', range: 'Melee / nearby target', tags: ['Pirate', 'Control'] },
        { key: 'boarding action', name: 'Boarding Action', summary: 'Burst into the fight with movement and immediate pressure when you close the distance.', actionType: 'bonus', resourceName: 'Swagger Dice', resourceSummary: 'Pressure opener', range: 'Self movement', tags: ['Pirate', 'Mobility'] },
        { key: 'marked quarry', name: 'Marked Quarry', summary: 'Call out the enemy you are hunting so your pressure tools focus on one target.', actionType: 'bonus', resourceName: 'Swagger Dice', resourceSummary: 'Target priority', range: 'Sight / target mark', tags: ['Pirate', 'Mark'] },
        { key: 'press the advantage', name: 'Press the Advantage', summary: 'Once your side gains momentum, turn it into extra pressure or support before the enemy recovers.', actionType: 'reaction', resourceName: 'Swagger Dice', resourceSummary: 'Triggered swagger spend', range: 'Triggered rider', tags: ['Pirate', 'Momentum'] },
        { key: 'dread volley', name: 'Dread Volley', summary: 'Unload a decisive flurry of attacks, shots, or thrown steel when the moment opens up.', actionType: 'action', resourceName: 'Swagger Dice', resourceSummary: 'Heavy swagger spend', range: 'Weapon-dependent', tags: ['Pirate', 'Burst'] },
      ],
      subclassActions: {
        corsair: [
          { key: 'boarding flurry', name: 'Boarding Flurry', summary: 'Explode into close-quarters pressure the moment you hit the rail or close the gap.', actionType: 'bonus', resourceName: 'Swagger Dice', tags: ['Corsair', 'Burst'] },
          { key: 'duelist instinct', name: 'Duelist Instinct', summary: 'Read the duel and answer with sharper one-on-one pressure.', actionType: 'reaction', resourceName: 'Swagger Dice', tags: ['Corsair', 'Duel'] },
        ],
        privateer: [
          { key: 'command presence', name: 'Command Presence', summary: 'Spend swagger to improve an ally’s movement, confidence, or attack quality.', actionType: 'bonus', resourceName: 'Swagger Dice', tags: ['Privateer', 'Support'] },
          { key: 'ordered volley', name: 'Ordered Volley', summary: 'Call the timing so your side gets a cleaner coordinated hit window.', actionType: 'action', resourceName: 'Swagger Dice', tags: ['Privateer', 'Support'] },
        ],
        smuggler: [
          { key: 'slip away', name: 'Slip Away', summary: 'Break line of sight and disappear from the obvious response lane.', actionType: 'reaction', resourceName: 'Swagger Dice', tags: ['Smuggler', 'Escape'] },
          { key: 'smoke and salt', name: 'Smoke and Salt', summary: 'Use clutter, smoke, and bad footing as the cover for your best turn.', actionType: 'bonus', resourceName: 'Swagger Dice', tags: ['Smuggler', 'Stealth'] },
        ],
        'dread captain': [
          { key: 'fearsome boarding', name: 'Fearsome Boarding', summary: 'Open with raw intimidation and direct pressure so the enemy line starts to crack immediately.', actionType: 'bonus', resourceName: 'Swagger Dice', tags: ['Dread Captain', 'Fear'] },
          { key: 'crack their will', name: 'Crack Their Will', summary: 'Exploit hesitation or fear once the target starts to break.', actionType: 'reaction', resourceName: 'Swagger Dice', tags: ['Dread Captain', 'Fear'] },
        ],
      },
    },
    monk: {
      actions: [
        { key: 'martial arts', name: 'Martial Arts Follow-Up', summary: 'After taking the Attack action with an unarmed strike or monk weapon, make one unarmed strike as a bonus action.', actionType: 'bonus', resourceName: '', resourceSummary: 'No Focus cost', range: '5 ft', tags: ['Monk', 'Unarmed'] },
        { key: 'flurry of blows', name: 'Flurry of Blows', summary: 'Spend Focus to convert your turn into two extra unarmed strikes as a bonus action.', actionType: 'bonus', resourceName: 'Focus Points', resourceSummary: 'Spend 1 Focus Point', range: '5 ft', tags: ['Monk', 'Burst'] },
        { key: 'patient defense', name: 'Patient Defense', summary: 'Spend Focus to Disengage and become harder to hit until your next turn.', actionType: 'bonus', resourceName: 'Focus Points', resourceSummary: 'Spend 1 Focus Point', range: 'Self', tags: ['Monk', 'Defense'] },
        { key: 'step of the wind', name: 'Step of the Wind', summary: 'Spend Focus to Dash/Disengage as a bonus action and extend jump mobility.', actionType: 'bonus', resourceName: 'Focus Points', resourceSummary: 'Spend 1 Focus Point', range: 'Self', tags: ['Monk', 'Mobility'] },
        { key: 'stunning strike', name: 'Stunning Strike', summary: 'On a melee hit, spend Focus to force a Constitution save and potentially Stun the target.', actionType: 'action', resourceName: 'Focus Points', resourceSummary: 'Spend 1 Focus Point on hit', range: 'Melee hit trigger', tags: ['Monk', 'Control'] },
        { key: 'deflect attacks', name: 'Deflect Attacks', summary: 'Use your reaction to reduce incoming attack damage, then optionally redirect.', actionType: 'reaction', resourceName: 'Focus Points', resourceSummary: 'Reaction; optional Focus to redirect', range: 'Self / returned attack', tags: ['Monk', 'Reaction'] },
        { key: 'slow fall', name: 'Slow Fall', summary: 'Use your reaction when falling to heavily reduce fall damage.', actionType: 'reaction', resourceName: '', resourceSummary: 'Reaction on fall', range: 'Self', tags: ['Monk', 'Reaction'] },
        { key: 'deflect energy', name: 'Deflect Energy', summary: 'Use your reaction to reduce elemental/force burst damage from visible sources.', actionType: 'reaction', resourceName: '', resourceSummary: 'Reaction to incoming energy damage', range: 'Self', tags: ['Monk', 'Reaction'] },
        { key: 'superior defense', name: 'Superior Defense', summary: 'Spend Focus for a short defensive spike that resists most damage types.', actionType: 'bonus', resourceName: 'Focus Points', resourceSummary: 'Spend 3 Focus Points', range: 'Self', tags: ['Monk', 'Defense'] },
      ],
      subclassActions: {
        'way of the open hand': [
          { key: 'open hand technique', name: 'Open Hand Technique Riders', summary: 'Your Flurry hits can push, prone, or disrupt reactions, turning pressure into control.', actionType: 'bonus', resourceName: 'Focus Points', range: 'Melee hit rider', tags: ['Open Hand', 'Control'] },
          { key: 'wholeness of body', name: 'Wholeness of Body', summary: 'Use an action to self-heal and stabilize your frontline presence.', actionType: 'action', resourceName: 'Wholeness of Body', range: 'Self', tags: ['Open Hand', 'Sustain'] },
          { key: 'quivering palm', name: 'Quivering Palm', summary: 'Plant a delayed finisher on a hit, then trigger it later for a lethal payoff.', actionType: 'action', resourceName: 'Focus Points', range: 'Melee hit / later trigger', tags: ['Open Hand', 'Finisher'] },
        ],
        'way of shadow': [
          { key: 'shadow arts', name: 'Shadow Arts', summary: 'Spend Focus on darkness and infiltration techniques to shape engagement terms.', actionType: 'action', resourceName: 'Focus Points', range: 'Technique-dependent', tags: ['Shadow', 'Stealth'] },
          { key: 'shadow step', name: 'Shadow Step', summary: 'Teleport through darkness as a bonus action to set ambush angles.', actionType: 'bonus', resourceName: '', range: 'Shadow-to-shadow', tags: ['Shadow', 'Mobility'] },
          { key: 'opportunist', name: 'Opportunist', summary: 'When an opening appears, use your reaction to punish instantly.', actionType: 'reaction', resourceName: '', range: 'Triggered melee attack', tags: ['Shadow', 'Reaction'] },
        ],
        'way of the four elements': [
          { key: 'disciple of the elements', name: 'Disciple of the Elements', summary: 'Spend Focus to access elemental techniques beyond standard strikes.', actionType: 'action', resourceName: 'Focus Points', range: 'Technique-dependent', tags: ['Four Elements', 'Elemental'] },
          { key: 'elemental disciplines', name: 'Elemental Disciplines', summary: 'Use elemental blasts and control options as part of your class loop.', actionType: 'action', resourceName: 'Focus Points', range: 'Technique-dependent', tags: ['Four Elements', 'Control'] },
          { key: 'avatar of the four winds', name: 'Avatar of the Four Winds', summary: 'Spend Focus for a high-tier elemental transformation/burst mode.', actionType: 'action', resourceName: 'Focus Points', range: 'Self / area', tags: ['Four Elements', 'Capstone'] },
        ],
      },
    },
    bard: {
      actions: [
        { key: 'bardic inspiration', name: 'Bardic Inspiration', summary: 'Use a bonus action to grant an ally your current Bardic Inspiration die for attacks, checks, or saves.', actionType: 'bonus', resourceName: 'Bardic Inspiration', resourceSummary: 'Spend 1 Bardic Inspiration use', range: '60 ft', tags: ['Bard', 'Support'] },
        { key: 'countercharm', name: 'Countercharm', summary: 'Use your performance to help allies resist fear and charm pressure when control effects start landing.', actionType: 'action', resourceName: '', resourceSummary: 'No resource cost', range: 'Aura / nearby allies', tags: ['Bard', 'Defense'] },
        { key: 'magical secrets', name: 'Magical Secrets Spell Pick', summary: 'Use your off-list Magical Secrets picks to cover missing party roles with non-bard spell access.', actionType: 'action', resourceName: '', resourceSummary: 'Spell cast from known list', range: 'Spell-dependent', tags: ['Bard', 'Spellcasting'] },
      ],
      subclassActions: {
        'college-of-glamour': [
          { key: 'mantle of inspiration', name: 'Mantle of Inspiration', summary: 'Spend Bardic Inspiration as a bonus action to grant temporary hit points and reaction movement without opportunity attacks.', actionType: 'bonus', resourceName: 'Bardic Inspiration', range: '60 ft', tags: ['Glamour', 'Support'] },
          { key: 'mantle of majesty', name: 'Mantle of Majesty', summary: 'Enter a command-focused state and pressure enemies with repeated bonus-action Command casts.', actionType: 'bonus', resourceName: '', range: 'Spell range', tags: ['Glamour', 'Control'] },
        ],
        'college-of-lore': [
          { key: 'cutting words', name: 'Cutting Words', summary: 'Spend Bardic Inspiration as a reaction to reduce an enemy attack, ability check, or damage roll.', actionType: 'reaction', resourceName: 'Bardic Inspiration', range: '60 ft', tags: ['Lore', 'Reaction'] },
          { key: 'peerless skill', name: 'Peerless Skill', summary: 'Spend Bardic Inspiration on yourself when a critical ability check must land.', actionType: 'reaction', resourceName: 'Bardic Inspiration', range: 'Self', tags: ['Lore', 'Skills'] },
        ],
        'college-of-valor': [
          { key: 'combat inspiration', name: 'Combat Inspiration', summary: 'Your inspiration die now boosts weapon damage or can be spent as a reaction to increase AC against one attack.', actionType: 'reaction', resourceName: 'Bardic Inspiration', range: 'Ally with inspiration', tags: ['Valor', 'Combat'] },
          { key: 'battle magic', name: 'Battle Magic', summary: 'After casting a bard spell with your action, make one weapon attack as a bonus action.', actionType: 'bonus', resourceName: '', range: 'Weapon range', tags: ['Valor', 'Tempo'] },
        ],
      },
    },
    paladin: {
      actions: [
        {
          key: 'lay on hands',
          name: 'Lay on Hands',
          summary: 'Spend points from your healing pool to restore allies, revive downed teammates, or stabilize the front line without using a spell slot.',
          actionType: 'action',
          resourceName: 'Lay on Hands',
          resourceSummary: 'Spend pool points',
          range: 'Touch',
          tags: ['Paladin', 'Healing'],
        },
        {
          key: 'divine smite',
          name: 'Divine Smite',
          summary: 'After a weapon hit lands, spend a spell slot to convert that hit into premium radiant burst damage.',
          actionType: 'action',
          resourceName: 'Spell Slots',
          resourceSummary: 'Spend slot on hit',
          range: 'Melee hit trigger',
          tags: ['Paladin', 'Burst'],
        },
        {
          key: 'channel divinity',
          name: 'Channel Divinity',
          summary: 'Spend Channel Divinity to fuel oath actions such as Sacred Weapon, Nature’s Wrath, or Vow of Enmity.',
          actionType: 'action',
          resourceName: 'Channel Divinity',
          resourceSummary: 'Spend 1 use',
          range: 'Feature dependent',
          tags: ['Paladin', 'Oath'],
        },
      ],
      subclassActions: {
        'oath of devotion': [
          { key: 'channel divinity: sacred weapon', name: 'Sacred Weapon', summary: 'Bless your weapon for a minute of high-confidence attacks and radiant authority.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Devotion', 'Accuracy'] },
          { key: 'holy nimbus', name: 'Holy Nimbus', summary: 'Erupt in radiant presence that punishes nearby foes and marks you as the party’s holy center.', actionType: 'action', tags: ['Devotion', 'Radiant'] },
        ],
        'oath of the ancients': [
          { key: 'channel divinity: nature\'s wrath', name: 'Nature’s Wrath', summary: 'Lock down a priority foe with primal restraints to protect your line.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Ancients', 'Control'] },
          { key: 'channel divinity: turn the faithless', name: 'Turn the Faithless', summary: 'Repel fey and fiends when corrupted threats are pressing your formation.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Ancients', 'Anti-Fiend'] },
        ],
        'oath of vengeance': [
          { key: 'channel divinity: vow of enmity', name: 'Vow of Enmity', summary: 'Mark one enemy for focused pursuit so your attack pressure stays glued to the target.', actionType: 'bonus', resourceName: 'Channel Divinity', tags: ['Vengeance', 'Mark'] },
          { key: 'channel divinity: abjure enemy', name: 'Abjure Enemy', summary: 'Break an enemy’s momentum with fear and forced control before it can dominate the round.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Vengeance', 'Control'] },
        ],
      },
    },
  };

  const ECON_META = {
    action:   { css: 'action-main',  label: 'Action' },
    bonus:    { css: 'action-bonus', label: 'Bonus' },
    reaction: { css: 'action-react', label: 'Reaction' },
    free:     { css: 'action-free',  label: 'Free' },
  };

  function _safeArray(value) {
    if (Array.isArray(value)) return value.filter(Boolean);
    if (value && typeof value === 'object') {
      return []
        .concat(Array.isArray(value.actions) ? value.actions : [])
        .concat(Array.isArray(value.bonusActions) ? value.bonusActions : [])
        .concat(Array.isArray(value.reactions) ? value.reactions : [])
        .filter(Boolean);
    }
    return [];
  }

  function _firstText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value === undefined || value === null) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }

  function _num(value, fallback = 0) {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function _abilityMod(score) {
    return Math.floor((_num(score, 10) - 10) / 2);
  }

  function _charAbilityScores(charData) {
    const scores = charData && charData.abilityScores && typeof charData.abilityScores === 'object'
      ? charData.abilityScores
      : {};
    return {
      str: _num(scores.str ?? scores.strength, 10),
      dex: _num(scores.dex ?? scores.dexterity, 10),
      con: _num(scores.con ?? scores.constitution, 10),
      int: _num(scores.int ?? scores.intelligence, 10),
      wis: _num(scores.wis ?? scores.wisdom, 10),
      cha: _num(scores.cha ?? scores.charisma, 10),
    };
  }

  function _charProfBonus(charData) {
    return _num(charData && (charData.profBonus ?? charData.proficiencyBonus), 2);
  }

  function _isHiddenFeatureCard(feature) {
    const rawName = _firstText(feature && feature.name, feature && feature.label, '');
    const cleanName = rawName.replace(/\[[^\]]+\]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
    const haystack = [cleanName, _firstText(feature && feature.summary, feature && feature.description, ''), _firstText(feature && feature.section, ''), _firstText(feature && feature.kind, '')].join(' ').toLowerCase();
    if (/^ability score improvement$/.test(cleanName)) return true;
    if (/^cantrips known\b/.test(cleanName) || /^spells known\b/.test(cleanName)) return true;
    if (/\b\d+(st|nd|rd|th)-level spells?\b/.test(cleanName)) return true;
    if (/\b\d+(st|nd|rd|th)-level spell slots?\b/.test(cleanName)) return true;
    if (/^subclass feature$/.test(cleanName) && /progression|unlock/.test(haystack)) return true;
    if (/spellcasting progression|native spellcasting progression/.test(haystack)) return true;
    return false;
  }

  function _inventoryWeaponCards(charData) {
    const inventory = _safeArray(charData && charData.inventory);
    const profBonus = _charProfBonus(charData);
    const stats = _charAbilityScores(charData);
    return inventory.filter(function (item) {
      return item && /weapon/i.test(String(item.kind || item.type || item.category || ''));
    }).map(function (item) {
      const propertyText = Array.isArray(item.properties) ? item.properties.join(' ') : String(item.properties || '');
      const finesse = /finesse/i.test(propertyText);
      const ranged = /ranged|bow|crossbow|sling/i.test(String(item.kind || '') + ' ' + String(item.name || '') + ' ' + String(item.range || ''));
      const abilityMod = ranged ? _abilityMod(stats.dex) : (finesse ? Math.max(_abilityMod(stats.str), _abilityMod(stats.dex)) : _abilityMod(stats.str));
      const attackBonus = profBonus + abilityMod;
      const damage = _firstText(item.damage, item.damageDice, item.damage_dice, item.notes, item.note, 'Weapon attack');
      return {
        id: String(item.id || item.name || '').trim() || ('inventory-' + String(item.name || 'weapon').toLowerCase().replace(/[^a-z0-9]+/g, '-')),
        source: item.equipped ? 'equip_only' : 'weapon',
        name: item.name || 'Weapon',
        desc: _firstText(item.note, item.notes, item.range, 'Inventory weapon'),
        description: _firstText(item.note, item.notes, item.range, 'Inventory weapon'),
        economy: ['action'],
        icon: String(item.range || '').match(/ft|range/i) ? '[R]' : '[M]',
        attackBonus: attackBonus >= 0 ? '+' + attackBonus : String(attackBonus),
        damage: damage,
        range: _firstText(item.range, item.reach),
        resourceName: '',
        tags: [item.equipped ? 'Equipped' : 'Inventory', item.kind || item.type || 'Weapon'].filter(Boolean),
        longText: [item.note, item.notes, item.damage, item.range].filter(Boolean).join('\n\n'),
      };
    });
  }

  function _unarmedStrikeCard(charData) {
    const stats = _charAbilityScores(charData);
    const profBonus = _charProfBonus(charData);
    const strMod = _abilityMod(stats.str);
    const attackBonus = profBonus + strMod;
    const damage = strMod === 0 ? '1 bludgeoning' : ('1' + (strMod > 0 ? '+' + strMod : strMod) + ' bludgeoning');
    return {
      id: 'system_unarmed_strike',
      source: 'system_unarmed',
      name: 'Unarmed Strike',
      desc: 'Default melee strike available even when you have no weapon equipped.',
      description: 'Default melee strike available even when you have no weapon equipped.',
      economy: ['action'],
      icon: '[U]',
      attackBonus: attackBonus >= 0 ? '+' + attackBonus : String(attackBonus),
      damage: damage,
      range: '5 ft',
      resourceName: '',
      tags: ['Default', 'Melee'],
      longText: 'Every character can still make an unarmed strike even without a weapon equipped.',
    };
  }

  function _featureActionFallbacks(charData) {
    const source = _safeArray(charData && charData.nativeFeatures)
      .concat(_safeArray(charData && charData.nativeClassFeatures))
      .concat(_safeArray(charData && charData.features));
    const groups = { actions: [], bonusActions: [], reactions: [] };
    const seen = new Set();
    function pushTextFallback(line, bucket, sourceLabel) {
      const clean = _firstText(line, '').trim();
      if (!clean) return;
      groups[bucket].push({
        name: clean.split(/[—:-]/)[0].trim() || clean,
        summary: clean,
        description: clean,
        text: clean,
        actionType: bucket === 'bonusActions' ? 'bonus' : (bucket === 'reactions' ? 'reaction' : 'action'),
        type: bucket === 'bonusActions' ? 'bonus action' : (bucket === 'reactions' ? 'reaction' : 'action'),
        tags: ['Feature', sourceLabel],
        source: 'feature-fallback',
      });
    }
    source.forEach(function (entry) {
      if (!entry || _isHiddenFeatureCard(entry)) return;
      const section = _firstText(entry.section, entry.actionType, entry.type).toLowerCase();
      let bucket = '';
      if (/bonus/.test(section)) bucket = 'bonusActions';
      else if (/reaction/.test(section)) bucket = 'reactions';
      else if (/action/.test(section)) bucket = 'actions';
      if (!bucket) {
        const text = _firstText(entry.summary, entry.description, entry.effect, '').toLowerCase();
        if (/\bbonus action\b/.test(text)) bucket = 'bonusActions';
        else if (/\breaction\b|use your reaction|as a reaction/.test(text)) bucket = 'reactions';
        else if (/\baction\b|use your action|as an action/.test(text)) bucket = 'actions';
      }
      if (!bucket) return;
      const name = _firstText(entry.name, entry.label, '');
      const key = bucket + '::' + name.toLowerCase();
      if (!name || seen.has(key)) return;
      seen.add(key);
      groups[bucket].push({
        name: name,
        summary: _firstText(entry.summary, entry.effect, ''),
        description: _firstText(entry.summary, entry.description, entry.effect, 'Feature action'),
        text: _firstText(entry.description, entry.longText, entry.effect, entry.summary),
        actionType: bucket === 'bonusActions' ? 'bonus' : (bucket === 'reactions' ? 'reaction' : 'action'),
        type: bucket === 'bonusActions' ? 'bonus action' : (bucket === 'reactions' ? 'reaction' : 'action'),
        range: _firstText(entry.range, ''),
        saveDC: _firstText(entry.save, ''),
        resourceName: _firstText(entry.resourceName, entry.usage, ''),
        resourceSummary: [_firstText(entry.usage, ''), _firstText(entry.recovery, '')].filter(Boolean).join(' • '),
        tags: ['Feature', _firstText(entry.className, entry.source, '')].filter(Boolean),
        source: 'feature-fallback',
      });
    });
    [_firstText(charData && charData.book && charData.book.features, ''), _firstText(charData && charData.book && charData.book.actions, '')].forEach(function (block, idx) {
      String(block || '').split(/\n+/).map(function (line) { return String(line || '').trim(); }).filter(Boolean).forEach(function (line) {
        var lower = line.toLowerCase();
        if (/\bbonus action\b/.test(lower)) pushTextFallback(line, 'bonusActions', idx === 0 ? 'Book Features' : 'Book Actions');
        else if (/\breaction\b|opportunity attack|as a reaction|use your reaction/.test(lower)) pushTextFallback(line, 'reactions', idx === 0 ? 'Book Features' : 'Book Actions');
      });
    });
    return groups;
  }

  function _econPip(type) {
    const meta = ECON_META[String(type || 'action').toLowerCase()] || ECON_META.action;
    return `<span class="cs-action-econ-pip ${_esc(meta.css)}">${_esc(meta.label)}</span>`;
  }

  function _actionIcon(action) {
    const raw = String(action && (action.icon || action.emoji || action.actionIcon || '')).trim();
    if (raw) return raw;
    const name = String(action && action.name || '').toLowerCase();
    const desc = String(action && (action.desc || action.description || '')).toLowerCase();
    if (/heal|lay on hands|second wind/.test(name + ' ' + desc)) return '✚';
    if (/spell|arcane|magic|eldritch|smite/.test(name + ' ' + desc)) return '✨';
    if (/bow|arrow|crossbow|ranged/.test(name + ' ' + desc)) return '🏹';
    if (/reaction/.test(name + ' ' + desc)) return '↺';
    if (/shield|defen/.test(name + ' ' + desc)) return '🛡️';
    return '⚔️';
  }


  function _actionTestingGuidance(action) {
    const text = `${String(action && action.name || '')} ${String(action && (action.desc || action.description || '') || '')}`.toLowerCase();
    if (/heal|lay on hands|second wind|healing/.test(text)) {
      return [
        'Trigger the action from Combat and confirm the roll matches the shown formula.',
        'With a friendly target selected, confirm HP increases and never exceeds max HP.',
        'Check any linked resource or use count changes after the action resolves.',
      ];
    }
    if (/save|stun|topple|push|prone|trip/.test(text) || action.saveDC || action.hitDc || action.save) {
      return [
        'Use the action with a target selected and confirm the save / DC data is visible in the inspector.',
        'Verify the action reports the correct rider or state change after resolution.',
        'Confirm linked target updates or chat output match the save-based result.',
      ];
    }
    if (/reaction/.test(text) || (Array.isArray(action.economy) && action.economy.some(function (entry) { return String(entry).toLowerCase() === 'reaction'; }))) {
      return [
        'Open the action from the Combat tab and verify it is grouped under Reactions.',
        'Confirm the inspector explains when to trigger it and whether it spends a resource.',
        'Check that the action remains available only in the correct timing window during play.',
      ];
    }
    return [
      'Click the action from the Combat tab and confirm the attack / damage data in the inspector matches the card.',
      'Resolve the action against a selected target and check hit, damage, or rider output in chat.',
      'Verify any linked resource spend, ammo use, or concentration / state update happens after resolution.',
    ];
  }

  function _actionConnectedSystems(action) {
    const systems = ['Combat tab'];
    if (action.attackBonus != null || action.damage || action.damageText) systems.push('Attack / damage flow');
    if (action.range || action.reach) systems.push('Target selection');
    if (action.saveDC || action.hitDc || action.save) systems.push('Save / DC handling');
    if (action.resourceName || action.resource || action.cost || action.resourceSummary) systems.push('Tracked resources');
    if (/ammo|ammunition/i.test(String(action.resourceName || '') + ' ' + String(action.longText || ''))) systems.push('Inventory / ammo');
    if (/concentration|spell|magic|smite|arcane|eldritch/i.test(String(action.name || '') + ' ' + String(action.description || ''))) systems.push('Spell / concentration layer');
    return systems;
  }

  function _actionExpectedResults(action) {
    const items = [];
    if (action.attackBonus != null) items.push({ label: 'Attack roll', value: `Uses attack bonus ${action.attackBonus}` });
    if (action.damage || action.damageText) items.push({ label: 'Damage', value: action.damage || action.damageText });
    if (action.saveDC || action.hitDc || action.save) items.push({ label: 'Save / DC', value: action.saveDC || action.hitDc || action.save });
    if (action.resourceSummary || action.resourceName || action.cost) items.push({ label: 'Resource impact', value: action.resourceSummary || action.resourceName || action.cost });
    if (action.range || action.reach) items.push({ label: 'Targeting', value: action.range || action.reach });
    if (action.duration) items.push({ label: 'Duration', value: action.duration });
    if (action.recovery) items.push({ label: 'Recovery', value: action.recovery });
    return items;
  }

  function _actionRulesBreakdown(action) {
    const rows = [];
    rows.push({ label: 'Resolution', value: action.attackBonus != null ? 'Attack roll → hit check → damage / rider' : (action.saveDC || action.hitDc || action.save) ? 'Save / DC check → outcome / rider' : 'Direct use / effect action' });
    rows.push({ label: 'Action economy', value: (Array.isArray(action.economy) ? action.economy : [action.economy || 'action']).filter(Boolean).join(' / ') || 'Action' });
    rows.push({ label: 'Primary output', value: action.damage || action.damageText || action.effect || action.desc || action.description || 'Rules text / state change' });
    rows.push({ label: 'Target model', value: action.range || action.reach ? 'Selected target expected' : 'May be self / state driven' });
    rows.push({ label: 'Range', value: action.range || action.reach || '—' });
    rows.push({ label: 'Duration', value: action.duration || '—' });
    rows.push({ label: 'Trigger / Save', value: action.trigger || action.saveDC || action.hitDc || action.save || '—' });
    rows.push({ label: 'Uses', value: action.usage || '—' });
    rows.push({ label: 'Recovery', value: action.recovery || '—' });
    if (action.resourceSummary || action.resourceName || action.resource || action.cost) rows.push({ label: 'Resource hook', value: action.resourceSummary || action.resourceName || action.resource || action.cost });
    return rows;
  }

  function _actionAutomationCoverage(action) {
    return [
      { label: 'Inspector depth', value: 'Ready' },
      { label: 'Roll surface', value: (action.attackBonus != null || action.damage || action.damageText || action.saveDC || action.hitDc || action.save) ? 'Structured' : 'Text / note only' },
      { label: 'Target application', value: action.range || action.reach || action.attackBonus != null || action.damage || action.damageText ? 'Target-aware path available' : 'May stay informational' },
      { label: 'Resource tracking', value: (action.resourceSummary || action.resourceName || action.resource || action.cost) ? 'Tracked / linked' : 'No linked resource detected' },
    ];
  }

  function _actionCommonBlockers(action) {
    const blockers = [];
    if ((action.attackBonus != null || action.damage || action.damageText || action.range || action.reach) && !(action.range || action.reach)) blockers.push({ label: 'Targeting', value: 'This action may need manual target selection / validation during testing.' });
    if (action.resourceSummary || action.resourceName || action.resource || action.cost) blockers.push({ label: 'Spend / recovery', value: 'Confirm the linked pool changes on use and rest recovery.' });
    if (action.saveDC || action.hitDc || action.save) blockers.push({ label: 'Save outcome', value: 'Verify the UI explains the save result clearly and the target state updates match it.' });
    if (!blockers.length) blockers.push({ label: 'Coverage', value: 'No obvious blockers detected from the current card data.' });
    return blockers;
  }

  function _openActionDetails(action) {
    if (!action || !global.CSContainer || typeof global.CSContainer.openDetailDrawer !== 'function') return false;
    const economy = (Array.isArray(action.economy) ? action.economy : [action.economy || 'action']).map(function (entry) {
      const meta = ECON_META[String(entry || 'action').toLowerCase()] || ECON_META.action;
      return meta.label;
    });
    global.CSContainer.openDetailDrawer({
      kicker: action.drawerKicker || 'Combat',
      title: action.name || 'Action',
      subtitle: action.desc || action.description || 'Combat option',
      chips: economy.concat((action.tags || []).filter(Boolean)).slice(0, 6),
      sections: [
        { title: 'Summary', body: action.longText || action.desc || action.description || 'No description yet.' },
        { title: 'Combat Data', items: [
          { label: 'Economy', value: economy.join(' / ') || 'Action' },
          { label: 'Attack Bonus', value: action.attackBonus != null ? String(action.attackBonus) : '—' },
          { label: 'Damage', value: action.damage || action.damageText || '—' },
          { label: 'Range', value: action.range || action.reach || '—' },
          { label: 'Save / DC', value: action.saveDC || action.hitDc || action.save || '—' },
          { label: 'Resource', value: action.resourceName || action.resource || action.cost || '—' },
        ] },
        { title: 'What Happens', items: _actionExpectedResults(action) },
      ],
    });
    return true;
  }



  function _classKey(charData) {
    return _firstText(charData && charData.className, charData && charData.class, '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function _customActionSurface(charData) {
    return CUSTOM_ACTION_SURFACES[_classKey(charData)] || null;
  }

  function _featureResourceRows(charData) {
    const source = []
      .concat(_safeArray(charData && charData.nativeFeatures))
      .concat(_safeArray(charData && charData.nativeClassFeatures))
      .concat(_safeArray(charData && charData.features));
    const seen = new Set();
    return source.map(function (entry) {
      const name = _firstText(entry && entry.resourceName, entry && entry.resource, '');
      if (!name) return null;
      const key = name.toLowerCase();
      if (seen.has(key)) return null;
      seen.add(key);
      return {
        name: name,
        current: entry && (entry.remaining ?? entry.current),
        max: entry && entry.max,
        summary: _firstText(entry && entry.usage, entry && entry.recovery, entry && entry.summary, 'Tracked feature resource'),
        note: _firstText(entry && entry.description, entry && entry.summary, ''),
      };
    }).filter(Boolean);
  }

  function _renderCustomSurfaceCallout(charData, resources) {
    const guide = _customActionSurface(charData);
    if (!guide) return '';
    const resourceLine = resources.length ? resources.map(function (item) { return item.name; }).join(' • ') : 'No structured resource row loaded yet';
    const classMechanics = charData && charData.classMechanics && typeof charData.classMechanics === 'object'
      ? charData.classMechanics
      : {};
    const barbarianLine = _classKey(charData) === 'barbarian'
      ? [
          classMechanics.rageUses != null ? ('Rage uses: ' + classMechanics.rageUses) : '',
          classMechanics.rageDamageBonus != null ? ('Rage damage: +' + classMechanics.rageDamageBonus) : '',
          classMechanics.extraAttacks != null ? ('Attacks per Attack action: ' + classMechanics.extraAttacks) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const paladinLine = _classKey(charData) === 'paladin'
      ? [
          classMechanics.layOnHandsPool != null ? ('Lay on Hands pool: ' + classMechanics.layOnHandsPool) : '',
          classMechanics.channelDivinityUses != null ? ('Channel Divinity uses: ' + classMechanics.channelDivinityUses) : '',
          classMechanics.auraRangeFeet != null ? ('Aura range: ' + classMechanics.auraRangeFeet + ' ft') : '',
          classMechanics.extraAttacks != null ? ('Attacks per Attack action: ' + classMechanics.extraAttacks) : '',
        ].filter(Boolean).join(' • ')
      : '';
    return `<div class="cs-combat-callout-grid">
      <div class="cs-combat-callout">
        <div class="cs-combat-callout-title">${_esc(guide.title)}</div>
        <div class="cs-combat-callout-copy">${_esc(guide.copy)}</div>
        ${barbarianLine ? `<div class="cs-combat-callout-copy">${_esc(barbarianLine)}</div>` : ''}
        ${paladinLine ? `<div class="cs-combat-callout-copy">${_esc(paladinLine)}</div>` : ''}
      </div>
      <div class="cs-combat-callout muted">
        <div class="cs-combat-callout-title">What should be visible</div>
        <div class="cs-combat-callout-copy">${_esc(resourceLine)}${guide.checks && guide.checks.length ? ' — ' + _esc(guide.checks.join(' • ')) : ''}</div>
      </div>
    </div>`;
  }
  function _pulseRowFromTrigger(trigger) {
    const row = trigger && trigger.closest ? trigger.closest('.cs-action-row, .cs-resource-row, .cs-spell-card-row, .cs-feature-item') : null;
    if (!row) return;
    row.classList.remove('cs-row-pulse');
    void row.offsetWidth;
    row.classList.add('cs-row-pulse');
    setTimeout(function () { row.classList.remove('cs-row-pulse'); }, 520);
  }

  function _renderSurfaceNavButtons() {
    return `<div class="cs-surface-nav">
      <button type="button" class="cs-launch-btn" data-map-panel-open="combat">Open map combat</button>
      <button type="button" class="cs-launch-btn muted" data-map-panel-open="inventory">Open map inventory</button>
    </div>`;
  }

  function _renderSummaryCard(label, value, note, accent) {
    return `<div class="cs-combat-summary-card${accent ? ' ' + _esc(accent) : ''}">
      <div class="cs-combat-summary-label">${_esc(label)}</div>
      <div class="cs-combat-summary-value">${_esc(value)}</div>
      <div class="cs-combat-summary-note">${_esc(note || '')}</div>
    </div>`;
  }

  function _renderSection(title, items, opts = {}) {
    if (!items || !items.length) {
      return `<div class="cs-action-section">
        <div class="cs-action-section-title">${_esc(title)}</div>
        <div class="cs-empty-state compact"><span>${_esc(opts.emptyLabel || 'Nothing to show yet')}</span></div>
      </div>`;
    }
    return `<div class="cs-action-section">
      <div class="cs-action-section-title">${_esc(title)}</div>
      <div class="cs-action-stack">${items.map(_renderActionRow).join('')}</div>
    </div>`;
  }

  function _renderActionRow(action) {
    const econ = Array.isArray(action.economy) ? action.economy : [action.economy || 'action'];
    const sourceTag = _firstText(action.source, '').replace(/_/g, ' ').trim();
    const summary = _firstText(action.desc, action.description, 'No summary loaded yet.');
    const bestUse = _firstText(action.longText, action.description, action.desc, 'Use this when the action helps your turn right now.');
    const toHit = action.attackBonus != null ? `+${String(action.attackBonus).replace(/^\+/, '')}` : '';
    const effect = _firstText(action.damage, action.damageText, action.effect, action.resourceSummary, action.resourceName, action.cost, '—');
    const range = _firstText(action.range, action.reach, '—');
    const spend = _firstText(action.resourceSummary, action.resourceName, action.cost, action.usesText, 'At will');
    const laneRows = [
      { label: 'To hit', value: toHit || '—' },
      { label: 'Effect', value: effect },
      { label: 'Range', value: range },
      { label: 'Spend', value: spend }
    ];
    const leadBadges = [];
    if (toHit) leadBadges.push('<span class="cs-action-mini-pill accent">Attack roll</span>');
    if (/save/i.test(String(action.saveText || action.effect || ''))) leadBadges.push('<span class="cs-action-mini-pill">Save effect</span>');
    if (/bonus/i.test(String(econ.join(' ')))) leadBadges.push('<span class="cs-action-mini-pill">Bonus action</span>');
    if (/reaction/i.test(String(econ.join(' ')))) leadBadges.push('<span class="cs-action-mini-pill">Reaction</span>');
    if (!leadBadges.length) leadBadges.push('<span class="cs-action-mini-pill ready">Usable now</span>');
    const useLabel = (function () {
      const src = String(action.source || '').toLowerCase();
      const text = `${String(action.name || '')} ${String(action.resourceName || '')} ${String(action.resourceSummary || '')}`.toLowerCase();
      if (src === 'spell') return 'Cast';
      if (src === 'weapon' || src === 'equip_only' || src === 'system_unarmed') return 'Attack';
      if (/swagger/.test(text)) return 'Spend Swagger';
      if (/gadget/.test(text)) return 'Use Device';
      return 'Use';
    }());
    return `<div class="cs-action-row" tabindex="0" role="button" data-action-name="${_esc(action.name || '')}" aria-label="${_esc(action.name || 'Action')} details">
      <div class="cs-action-icon" aria-hidden="true">${_esc(_actionIcon(action))}</div>
      <div class="cs-action-maincopy">
        <div class="cs-action-topline">
          <div>
            <div class="cs-action-name">${_esc(action.name || '—')}</div>
            ${sourceTag ? `<div class="cs-action-kicker">${_esc(sourceTag)}</div>` : ''}
          </div>
          <div class="cs-action-chip-row">${leadBadges.join('')}</div>
        </div>
        <div class="cs-action-desc"><strong>${_esc(summary)}</strong></div>
        <div class="cs-action-lanes">${laneRows.map(function (lane) {
          return `<div class="cs-action-lane"><span class="cs-action-lane-label">${_esc(lane.label)}</span><span class="cs-action-lane-value">${_esc(lane.value || '—')}</span></div>`;
        }).join('')}</div>
        <div class="cs-action-bestuse">${_esc(bestUse)}</div>
        <div class="cs-action-controls" style="margin-top:.55rem;display:flex;gap:.4rem;flex-wrap:wrap;">
          <button type="button" class="cs-feature-inspect" data-action-use="${_esc(String(action.id || action.name || ''))}" data-action-source="${_esc(String(action.source || 'weapon'))}">${_esc(useLabel)}</button>
        </div>
      </div>
      <div class="cs-action-side">${econ.map(_econPip).join('')}</div>
    </div>`;
  }

  function _renderResourceRow(resource) {
    const summary = _firstText(resource.summary, (Number.isFinite(resource.current) && Number.isFinite(resource.max)) ? `${resource.current}/${resource.max}` : '', resource.note);
    return `<div class="cs-resource-row" tabindex="0" role="button" data-resource-name="${_esc(resource.name || '')}" aria-label="${_esc(resource.name || 'Resource')} details">
      <div class="cs-resource-main">
        <div class="cs-resource-name">${_esc(resource.name || 'Resource')}</div>
        <div class="cs-resource-note">${_esc(summary || 'No tracked summary')}</div>
      </div>
      <div class="cs-resource-side">
        <span class="cs-resource-pill">${_esc(summary || '—')}</span>
      </div>
    </div>`;
  }

  function _renderResourceSection(resources) {
    if (!resources || !resources.length) {
      return `<div class="cs-action-section"><div class="cs-action-section-title">Tracked Resources</div><div class="cs-empty-state compact"><span>No native resource cards are loaded yet.</span></div></div>`;
    }
    return `<div class="cs-action-section"><div class="cs-action-section-title">Tracked Resources</div><div class="cs-resource-stack">${resources.map(_renderResourceRow).join('')}</div></div>`;
  }

  function _buildQuickAttackCards(charData) {
    return _safeArray(charData && charData.quickAttackCards).map(function (card) {
      return {
        id: String(card.id || card.name || '').trim() || ('attack-' + String(card.name || 'attack').toLowerCase().replace(/[^a-z0-9]+/g, '-')),
        source: String(card.source || 'weapon').trim() || 'weapon',
        name: card.name || 'Attack',
        desc: _firstText(card.summary, card.note, card.text, 'Generated quick attack card.'),
        description: _firstText(card.summary, card.note, card.text, 'Generated quick attack card.'),
        economy: ['action'],
        icon: card.icon || (String(card.range || '').match(/ft|range/i) ? '🏹' : '⚔️'),
        attackBonus: card.attackBonus != null ? card.attackBonus : _firstText(card.toHit, card.hit),
        damage: _firstText(card.damage, card.damageText, card.effect),
        range: _firstText(card.range, card.reach),
        resourceName: _firstText(card.ammoKind, card.ammoNote),
        tags: [card.source === 'equip_only' ? 'Equipped Loadout' : '', card.modeLabel || '', card.mastery_label || card.masteryLabel || ''].filter(Boolean),
        longText: [card.summary, card.note, card.modeNote, card.mastery_text].filter(Boolean).join('\n\n'),
      };
    });
  }


  function _featureSourceEntries(charData) {
    return []
      .concat(_safeArray(charData && charData.nativeFeatures))
      .concat(_safeArray(charData && charData.nativeClassFeatures))
      .concat(_safeArray(charData && charData.features));
  }

  function _featureLookup(charData) {
    const map = new Map();
    _featureSourceEntries(charData).forEach(function (entry) {
      if (!entry || _isHiddenFeatureCard(entry)) return;
      [_firstText(entry.name, entry.label, ''), _firstText(entry.id, entry.sourceId, entry.key, '')].forEach(function (value) {
        const key = String(value || '').trim().toLowerCase();
        if (!key || map.has(key)) return;
        map.set(key, entry);
      });
    });
    return map;
  }

  function _customSubclassKey(charData) {
    return _firstText(charData && charData.subclassName, charData && charData.subclass, '').toLowerCase().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function _findFeatureMatch(lookup, key) {
    const needle = String(key || '').toLowerCase().trim();
    if (!needle) return null;
    if (lookup.has(needle)) return lookup.get(needle);
    let found = null;
    lookup.forEach(function (value, entryKey) {
      if (found) return;
      if (entryKey.includes(needle) || needle.includes(entryKey)) found = value;
    });
    return found;
  }

  function _buildCustomClassActionCards(charData) {
    const classKey = _classKey(charData);
    const config = CUSTOM_CLASS_ACTIONS[classKey];
    if (!config) return { actions: [], bonusActions: [], reactions: [] };
    const lookup = _featureLookup(charData);
    const subclassKey = _customSubclassKey(charData);
    const candidateDefs = []
      .concat(Array.isArray(config.actions) ? config.actions : [])
      .concat((config.subclassActions && config.subclassActions[subclassKey]) || []);
    const groups = { actions: [], bonusActions: [], reactions: [] };
    const seen = new Set();
    candidateDefs.forEach(function (def, index) {
      const feature = _findFeatureMatch(lookup, def && def.key);
      if (!feature) return;
      const actionType = String(def.actionType || feature.actionType || feature.type || 'action').toLowerCase();
      const bucket = /reaction/.test(actionType) ? 'reactions' : /bonus/.test(actionType) ? 'bonusActions' : 'actions';
      const id = `custom_${classKey}_${String(def.key || index).replace(/[^a-z0-9]+/gi, '_').toLowerCase()}`;
      if (seen.has(id)) return;
      seen.add(id);
      const usageBits = [_firstText(feature.usage, ''), _firstText(feature.recovery, '')].filter(Boolean).join(' • ');
      groups[bucket].push({
        id: id,
        source: 'native_action',
        name: def.name || feature.name || 'Custom Action',
        summary: _firstText(def.summary, feature.summary, feature.description, 'Class action'),
        description: _firstText(def.summary, feature.summary, feature.description, 'Class action'),
        text: [_firstText(feature.description, ''), _firstText(feature.longText, '')].filter(Boolean).join('\n\n'),
        actionType: actionType,
        type: actionType,
        range: _firstText(def.range, feature.range, ''),
        resourceName: _firstText(def.resourceName, feature.resourceName, ''),
        resourceSummary: _firstText(def.resourceSummary, usageBits, ''),
        tags: (Array.isArray(def.tags) ? def.tags : []).concat([_firstText(feature.source, classKey)]).filter(Boolean),
        note: _firstText(feature.summary, feature.usage, feature.recovery, ''),
        effectText: _firstText(feature.effect, ''),
      });
    });
    return groups;
  }

  function _nativeActionGroups(charData) {
    const groups = charData && charData.nativeActionCards && typeof charData.nativeActionCards === 'object'
      ? charData.nativeActionCards
      : { actions: [], bonusActions: [], reactions: [] };
    const fallback = _featureActionFallbacks(charData);
    const custom = _buildCustomClassActionCards(charData);
    const out = {
      actions: _safeArray(groups.actions).concat(custom.actions).concat(fallback.actions).map(function (card, index) { return _normalizeNativeAction(card, 'action', index); }),
      bonusActions: _safeArray(groups.bonusActions).concat(custom.bonusActions).concat(fallback.bonusActions).map(function (card, index) { return _normalizeNativeAction(card, 'bonus', index); }),
      reactions: _safeArray(groups.reactions).concat(custom.reactions).concat(fallback.reactions).map(function (card, index) { return _normalizeNativeAction(card, 'reaction', index); }),
    };
    if (!out.reactions.length) {
      out.reactions.push(_normalizeNativeAction({
        name: 'Opportunity Attack',
        summary: 'Make one melee attack when a creature you can reach leaves your reach.',
        description: 'Use your reaction to make one melee attack against a creature that leaves your reach without disengaging.',
        range: 'Melee reach',
        tags: ['Core Rule'],
        source: 'system-fallback'
      }, 'reaction'));
    }
    return out;
  }

  function _stableNativeActionId(card, fallbackEconomy, index) {
    const entry = card && typeof card === 'object' ? card : {};
    const details = entry.details && typeof entry.details === 'object' ? entry.details : {};
    const signature = [
      _firstText(entry.name, entry.label, ''),
      _firstText(entry.type, entry.kind, fallbackEconomy, ''),
      _firstText(entry.source, details.source, ''),
      _firstText(entry.range, details.range, ''),
      _firstText(entry.damage, details.damage, details.damageFormula, ''),
      _firstText(entry.save, details.save, ''),
    ].join('::').toLowerCase();
    const slug = signature.replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 96);
    return slug || ('native_' + String(fallbackEconomy || 'action').replace(/[^a-z0-9]+/gi, '_') + '_' + String(index || 0));
  }

  function _normalizeNativeAction(card, fallbackEconomy, index) {
    const costSummary = _firstText(card.resourceSummary, card.resourceName ? `${card.resourceName}${card.remaining != null && card.max != null ? ` ${card.remaining}/${card.max}` : ''}` : '', card.cost);
    return {
      id: _stableNativeActionId(card, fallbackEconomy, index),
      source: 'native_action',
      name: card.name || 'Native Action',
      desc: _firstText(card.summary, card.description, card.text, 'Structured action card.'),
      description: _firstText(card.summary, card.description, card.text, 'Structured action card.'),
      economy: [String(card.economy || card.actionType || fallbackEconomy || 'action').toLowerCase()],
      icon: card.icon || card.emoji || '',
      attackBonus: card.attackBonus != null ? card.attackBonus : '',
      damage: _firstText(card.damage, card.damageText, card.effect),
      range: _firstText(card.range, card.reach),
      saveDC: _firstText(card.saveDC, card.hitDc, card.save),
      resourceName: card.resourceName || card.resource || '',
      resourceSummary: costSummary,
      tags: [card.kind || card.type || '', card.source || 'Native'].filter(Boolean),
      longText: [card.text, card.note, card.effectText].filter(Boolean).join('\n\n'),
      drawerKicker: 'Action Inspector',
    };
  }


  function _parseTextAttacks(charData) {
    const text = (charData && charData.book && charData.book.attacks) || '';
    if (!text || typeof text !== 'string') return [];
    return text.split(/\n+/).map(function (line) {
      const clean = line.trim();
      if (!clean) return null;
      const parts = clean.split(/[—–]/).map(p => p.trim());
      return {
        name: parts[0] || clean,
        desc: parts.slice(1).join(' — ') || 'Imported attack line',
        description: parts.slice(1).join(' — ') || 'Imported attack line',
        economy: ['action'],
        icon: '⚔️',
        longText: clean,
      };
    }).filter(Boolean);
  }

  function _resourceRows(charData) {
    const base = _safeArray(charData && charData.nativeResources).map(function (resource) {
      return {
        name: resource.name || resource.label || 'Resource',
        current: resource.current,
        max: resource.max,
        summary: _firstText(resource.summary, (Number.isFinite(resource.current) && Number.isFinite(resource.max)) ? `${resource.current}/${resource.max}` : '', resource.note),
        note: _firstText(resource.note, resource.reset, resource.recharge),
      };
    });
    const seen = new Set(base.map(function (row) { return String(row && row.name || '').toLowerCase(); }));
    _featureResourceRows(charData).forEach(function (row) {
      const key = String(row && row.name || '').toLowerCase();
      if (!key || seen.has(key)) return;
      seen.add(key);
      base.push(row);
    });
    return base;
  }

  function _bindDetails(container, model) {
    container.addEventListener('click', function (e) {
      const useBtn = e.target.closest('[data-action-use]');
      if (useBtn) {
        e.preventDefault();
        e.stopPropagation();
        const actionId = String(useBtn.getAttribute('data-action-use') || '');
        const actionSource = String(useBtn.getAttribute('data-action-source') || '');
        _pulseRowFromTrigger(useBtn);
        if (typeof global.playerUseAction === 'function') {
          global.playerUseAction(actionSource, actionId);
        } else if (typeof global.showToast === 'function') {
          const all = [].concat(model.quickAttacks, model.native.actions, model.native.bonusActions, model.native.reactions, model.textAttacks);
          const action = all.find(function (entry) { return String(entry && entry.id || '') === actionId || String(entry && entry.name || '').toLowerCase() === actionId.toLowerCase(); });
          const label = action && action.name ? action.name : 'Action';
          const cost = action && (action.resourceSummary || action.resourceName) ? ` — ${action.resourceSummary || action.resourceName}` : '';
          global.showToast(`${label} triggered${cost}`);
        }
        return;
      }
      const mapJump = e.target.closest('[data-map-panel-open]');
      if (mapJump) {
        e.preventDefault();
        e.stopPropagation();
        if (global.CSContainer && typeof global.CSContainer.openMapPanelFromSheet === 'function') {
          global.CSContainer.openMapPanelFromSheet(String(mapJump.getAttribute('data-map-panel-open') || ''));
        }
        return;
      }
      const actionRow = e.target.closest('.cs-action-row');
      if (actionRow) {
        const name = String(actionRow.getAttribute('data-action-name') || '').toLowerCase();
        const all = [].concat(model.quickAttacks, model.native.actions, model.native.bonusActions, model.native.reactions, model.textAttacks);
        const action = all.find(function (entry) { return String(entry && entry.name || '').toLowerCase() === name; });
        if (action) _openActionDetails(action);
        return;
      }
      const resourceRow = e.target.closest('.cs-resource-row');
      if (resourceRow) {
        const name = String(resourceRow.getAttribute('data-resource-name') || '').toLowerCase();
        const resource = model.resources.find(function (entry) { return String(entry && entry.name || '').toLowerCase() === name; });
        if (resource && global.CSContainer && typeof global.CSContainer.openDetailDrawer === 'function') {
          global.CSContainer.openDetailDrawer({
            kicker: 'Resource',
            title: resource.name || 'Resource',
            subtitle: resource.note || 'Tracked character resource',
            chips: [resource.summary || 'Tracked'],
            sections: [
              { title: 'Summary', body: resource.note || 'This resource is tracked on the character sheet.' },
              { title: 'Resource Data', items: [
                { label: 'Current', value: Number.isFinite(resource.current) ? String(resource.current) : '—' },
                { label: 'Max', value: Number.isFinite(resource.max) ? String(resource.max) : '—' },
                { label: 'Summary', value: resource.summary || '—' },
              ] },
            ],
          });
        }
      }
    });
    container.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const row = e.target.closest('.cs-action-row, .cs-resource-row');
      if (!row) return;
      e.preventDefault();
      row.click();
    });
  }

  function initActionsTab(container, charData) {
    if (!container) return;

    const quickAttacks = _buildQuickAttackCards(charData || {});
    const native = _nativeActionGroups(charData || {});
    const resources = _resourceRows(charData || {});
    const textAttacks = _parseTextAttacks(charData || {});
    const selectedTarget = charData && charData.selectedTarget ? charData.selectedTarget : null;
    const concentration = _firstText(charData && charData.activeConcentration, '');
    const totalActions = quickAttacks.length + native.actions.length + native.bonusActions.length + native.reactions.length + textAttacks.length;

    container.innerHTML = `
      <div class="cs-combat-hero-grid">
        ${_renderSummaryCard('Combat Surface', String(totalActions), totalActions ? 'Usable attacks and action cards' : 'Still missing attack/action inputs', totalActions ? 'teal' : '')}
        ${_renderSummaryCard('Tracked Resources', String(resources.length), resources.length ? 'Linked class pools and spendable uses' : 'No structured pools loaded yet', resources.length ? 'gold' : '')}
        ${_renderSummaryCard('Target State', selectedTarget && selectedTarget.name ? selectedTarget.name : 'No target', selectedTarget ? 'Damage / heal apply will use this target.' : 'Click a token on the map to set the current target.', selectedTarget ? 'violet' : '')}
        ${_renderSummaryCard('Concentration', concentration || 'None', concentration ? 'Spell state is active on your token.' : 'Cast a concentration spell to track it automatically.', concentration ? 'violet' : '')}
      </div>
      <div class="cs-combat-callout-grid">
        <div class="cs-combat-callout">
          <div class="cs-combat-callout-title">Combat flow</div>
          <div class="cs-combat-callout-copy">Use attack cards, actions, bonus actions, and reactions from here. Open any row to read the full rules text and resource details.</div>
        </div>
        <div class="cs-combat-callout muted">
          <div class="cs-combat-callout-title">Tracked resources</div>
          <div class="cs-combat-callout-copy">Spendable class resources appear below so you can quickly see what is ready, what is spent, and what will recharge later.</div>
        </div>
      </div>
      ${_renderSurfaceNavButtons()}
      ${_renderCustomSurfaceCallout(charData || {}, resources)}
      ${_renderSection('Quick Attacks', quickAttacks, { emptyLabel: 'No quick attack cards are loaded yet.' })}
      ${_renderSection('Native Actions', native.actions, { emptyLabel: 'No structured main actions are loaded yet.' })}
      ${_renderSection('Bonus Actions', native.bonusActions, { emptyLabel: 'No structured bonus actions are loaded yet.' })}
      ${_renderSection('Reactions', native.reactions, { emptyLabel: 'No structured reactions are loaded yet.' })}
      ${_renderResourceSection(resources)}
    `;

    _bindDetails(container, { quickAttacks, native, resources, textAttacks });
  }

  global.ActionsTab = { initActionsTab };
}(window));
