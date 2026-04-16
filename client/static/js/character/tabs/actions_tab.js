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
    fighter: {
      title: 'Fighter Combat Surface',
      copy: 'Fighter should read as a complete martial loop: clear attack cadence, visible core resources, and subclass tools that change round-to-round choices.',
      checks: ['Second Wind / Action Surge / Indomitable visible', 'Extra Attack cadence visible', 'Weapon Mastery + Fighting Style identity visible'],
    },
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
    cleric: {
      title: 'Cleric Combat Surface',
      copy: 'Cleric should read as a divine decision loop: prepared spells, Channel Divinity spenders, and domain-specific reactions/actions all visible in one place.',
      checks: ['Channel Divinity uses visible', 'Divine Spark / Turn Undead surfaced', 'Domain action identity visible'],
    },
    druid: {
      title: 'Druid Combat Surface',
      copy: 'Druid should read as a visible cast-vs-shift loop: prepared spell pressure, Wild Shape economy, and circle-specific turn tools all available without hunting through flavor text.',
      checks: ['Wild Shape uses + CR/form limits visible', 'Wild Companion spend option visible', 'Circle of the Moon vs Land combat lane clearly surfaced'],
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
    ranger: {
      title: 'Ranger Combat Surface',
      copy: 'Ranger should read as one hunt loop: weapon pressure, Hunter’s Mark / spell cadence, movement tools, and subclass tactics all visible without jumping through hidden tabs.',
      checks: ['Weapon attack cadence visible', 'Hunter’s Mark + slot economy visible', 'Subclass tactics / companion command cards visible'],
    },
    rogue: {
      title: 'Rogue Combat Surface',
      copy: 'Rogue should read as a precision loop: set up one decisive hit each turn with Cunning Action / Steady Aim, then decide whether Sneak Attack goes to pure damage or Cunning Strike control.',
      checks: ['Sneak Attack dice visible', 'Setup tools visible (Cunning Action / Steady Aim)', 'Subclass tempo tools visible'],
    },
    sorcerer: {
      title: 'Sorcerer Combat Surface',
      copy: 'Sorcerer should read as a two-layer caster loop: spell cards and slot access first, then Sorcery Point spenders like Metamagic and Flexible Casting.',
      checks: ['Sorcery Points visible', 'Metamagic options visible', 'Flexible Casting conversion options visible'],
    },
    warlock: {
      title: 'Warlock Combat Surface',
      copy: 'Warlock should show a clear at-will + pact-slot rhythm: Eldritch Blast pressure, pact slot tracking, short-rest recovery, and patron identity tools all visible together.',
      checks: ['Pact Slots + slot level visible', 'Eldritch Blast loop visible', 'Invocation / patron actions visible'],
    },
  };


  const CUSTOM_CLASS_ACTIONS = {
    fighter: {
      actions: [
        {
          key: 'action surge',
          name: 'Action Surge',
          summary: 'Spend Action Surge to take an additional action this turn and convert tempo into immediate battlefield swing.',
          actionType: 'special',
          resourceName: 'Action Surge',
          resourceSummary: 'Spend 1 use (Short/Long Rest)',
          range: 'Self',
          tags: ['Fighter', 'Burst'],
        },
        {
          key: 'second wind',
          name: 'Second Wind',
          summary: 'Use your bonus action self-heal to stabilize under pressure without ending your offensive turn plan.',
          actionType: 'bonus',
          resourceName: 'Second Wind',
          resourceSummary: 'Spend 1 use (Short/Long Rest)',
          range: 'Self',
          tags: ['Fighter', 'Sustain'],
        },
        {
          key: 'indomitable',
          name: 'Indomitable',
          summary: 'When a critical save fails, spend Indomitable to re-roll and keep your combat role online.',
          actionType: 'reaction',
          resourceName: 'Indomitable',
          resourceSummary: 'Spend 1 use (Long Rest)',
          range: 'Self',
          tags: ['Fighter', 'Defense'],
        },
      ],
      subclassActions: {
        battlemaster: [
          { key: 'combat superiority', name: 'Combat Superiority', summary: 'Spend Superiority Dice to add maneuver riders that control movement, accuracy, fear, and ally tempo.', actionType: 'special', resourceName: 'Superiority Dice', resourceSummary: '4d8 dice (Short/Long Rest)', tags: ['Battle Master', 'Resource'] },
          { key: 'maneuvering attack', name: 'Maneuvering Attack', summary: 'On hit, spend a die to reposition an ally safely and keep battlefield tempo in your favor.', actionType: 'action', resourceName: 'Superiority Dice', tags: ['Battle Master', 'Control'] },
          { key: 'parry', name: 'Parry', summary: 'Use your reaction and a superiority die to reduce incoming melee damage and survive focus fire.', actionType: 'reaction', resourceName: 'Superiority Dice', tags: ['Battle Master', 'Reaction'] },
          { key: 'feinting attack', name: 'Feinting Attack', summary: 'Spend a bonus action and die to line up advantage and convert setup into cleaner weapon spikes.', actionType: 'bonus', resourceName: 'Superiority Dice', tags: ['Battle Master', 'Setup'] },
        ],
        champion: [
          { key: 'improved critical', name: 'Improved Critical', summary: 'Your crit range is improved, so repeated weapon pressure converts into more explosive spikes over time.', actionType: 'passive', resourceName: '', tags: ['Champion', 'Passive'] },
          { key: 'survivor', name: 'Survivor', summary: 'In drawn-out fights, regenerate enough staying power to remain a constant front-line problem.', actionType: 'passive', resourceName: '', tags: ['Champion', 'Sustain'] },
        ],
        'eldritch knight': [
          { key: 'weapon bond', name: 'Weapon Bond Recall', summary: 'Recall a bonded weapon as a bonus action so disarms and distance do not break your pressure turn.', actionType: 'bonus', resourceName: '', tags: ['Eldritch Knight', 'Utility'] },
          { key: 'war magic', name: 'War Magic', summary: 'After a cantrip action, follow with one weapon attack as a bonus action to keep hybrid rhythm online.', actionType: 'bonus', resourceName: '', tags: ['Eldritch Knight', 'Hybrid'] },
          { key: 'eldritch strike', name: 'Eldritch Strike Setup', summary: 'Land a weapon hit, then pressure with a save spell while the target is softened for your magic.', actionType: 'special', resourceName: '', tags: ['Eldritch Knight', 'Combo'] },
          { key: 'arcane charge', name: 'Arcane Charge', summary: 'When you Action Surge, teleport up to 30 feet and turn burst turns into position-winning plays.', actionType: 'special', resourceName: 'Action Surge', tags: ['Eldritch Knight', 'Mobility'] },
        ],
      },
    },
    cleric: {
      actions: [
        {
          key: 'divine spark',
          name: 'Divine Spark',
          summary: 'Spend Channel Divinity for immediate healing or divine damage when one swing in momentum matters right now.',
          actionType: 'action',
          resourceName: 'Channel Divinity',
          resourceSummary: 'Spend 1 use',
          range: '30 ft',
          tags: ['Cleric', 'Core Divine'],
        },
        {
          key: 'turn undead',
          name: 'Turn Undead',
          summary: 'Spend Channel Divinity to force undead back and create breathing room for your party.',
          actionType: 'action',
          resourceName: 'Channel Divinity',
          resourceSummary: 'Spend 1 use',
          range: '30 ft',
          tags: ['Cleric', 'Control'],
        },
        {
          key: 'divine intervention',
          name: 'Divine Intervention',
          summary: 'Call directly on your deity for a major swing when ordinary spellcasting is not enough.',
          actionType: 'action',
          resourceName: '',
          resourceSummary: 'High-impact class feature',
          range: 'Special',
          tags: ['Cleric', 'Miracle'],
        },
      ],
      subclassActions: {
        'life domain': [
          { key: 'preserve life', name: 'Preserve Life', summary: 'Channel Divinity burst-heal spread across nearby allies in danger.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Life', 'Healing'] },
        ],
        'light domain': [
          { key: 'warding flare', name: 'Warding Flare', summary: 'Use your reaction to impose disadvantage and blunt an incoming attack.', actionType: 'reaction', resourceName: 'Warding Flare', tags: ['Light', 'Defense'] },
          { key: 'radiance of the dawn', name: 'Radiance of the Dawn', summary: 'Spend Channel Divinity for radiant burst and anti-darkness control.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Light', 'Radiant'] },
        ],
        'trickery domain': [
          { key: 'invoke duplicity', name: 'Invoke Duplicity', summary: 'Spend Channel Divinity to project an illusion double and reshape positioning pressure.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Trickery', 'Illusion'] },
          { key: 'cloak of shadows', name: 'Cloak of Shadows', summary: 'Spend Channel Divinity for a short invisibility reset and repositioning play.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['Trickery', 'Stealth'] },
        ],
        'war domain': [
          { key: 'war priest', name: 'War Priest', summary: 'Convert Attack action turns into bonus-action weapon pressure for frontline tempo.', actionType: 'bonus', resourceName: 'War Priest', tags: ['War', 'Frontline'] },
          { key: 'guided strike', name: 'Guided Strike', summary: 'Spend Channel Divinity to convert a key miss into a likely hit.', actionType: 'action', resourceName: 'Channel Divinity', tags: ['War', 'Accuracy'] },
          { key: "war god's blessing", name: "War God's Blessing", summary: 'Use your reaction and Channel Divinity to help an ally land a pivotal attack.', actionType: 'reaction', resourceName: 'Channel Divinity', tags: ['War', 'Support'] },
        ],
      },
    },
    druid: {
      actions: [
        {
          key: 'wild shape',
          name: 'Wild Shape',
          summary: 'Spend one Wild Shape use to transform for movement, scouting, utility, or combat pressure.',
          actionType: 'bonus',
          resourceName: 'Wild Shape',
          resourceSummary: 'Spend 1 Wild Shape use',
          range: 'Self',
          tags: ['Druid', 'Transformation'],
        },
        {
          key: 'wild companion',
          name: 'Wild Companion',
          summary: 'Spend one Wild Shape use on a familiar-style helper instead of transforming yourself.',
          actionType: 'action',
          resourceName: 'Wild Shape',
          resourceSummary: 'Spend 1 Wild Shape use',
          range: '30 ft',
          tags: ['Druid', 'Companion'],
        },
        {
          key: 'prepared druid spell',
          name: 'Prepared Spell Cast',
          summary: 'Use your prepared spell list and Wisdom casting to answer the current turn without committing Wild Shape.',
          actionType: 'action',
          resourceName: 'Spell Slots',
          resourceSummary: 'Consumes slot when cast',
          range: 'Spell-dependent',
          tags: ['Druid', 'Spellcasting'],
        },
      ],
      subclassActions: {
        'circle of the moon': [
          { key: 'combat wild shape', name: 'Combat Wild Shape', summary: 'Use Wild Shape as a fast battle-form switch and stabilize in-form with slot-powered healing when needed.', actionType: 'bonus', resourceName: 'Wild Shape', resourceSummary: 'Spend 1 Wild Shape use', range: 'Self', tags: ['Moon', 'Transformation'] },
          { key: 'elemental wild shape', name: 'Elemental Wild Shape', summary: 'Spend two Wild Shape uses for elemental forms that can redefine frontline pressure and resistances.', actionType: 'action', resourceName: 'Wild Shape', resourceSummary: 'Spend 2 Wild Shape uses', range: 'Self', tags: ['Moon', 'Elemental'] },
        ],
        'circle of the land': [
          { key: 'natural recovery', name: 'Natural Recovery', summary: 'Recover spell slot value on a short rest so your casting engine lasts through long adventuring days.', actionType: 'special', resourceName: 'Natural Recovery', resourceSummary: 'Short-rest recovery feature', range: 'Self', tags: ['Land', 'Recovery'] },
          { key: 'lands aid', name: "Land's Aid", summary: 'Call on your terrain bond for practical support and local momentum swings in active play.', actionType: 'action', resourceName: "Land's Aid", range: 'Local area', tags: ['Land', 'Support'] },
          { key: 'circle spells', name: 'Circle Spells', summary: 'Always-ready terrain spells extend your prepared toolkit and should stay distinct from Wild Shape resources.', actionType: 'passive', resourceName: '', range: 'Spell-dependent', tags: ['Land', 'Prepared Casting'] },
        ],
      },
    },
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
    sorcerer: {
      actions: [
        {
          key: 'innate sorcery',
          name: 'Innate Sorcery',
          summary: 'Enter your heightened casting state when the fight calls for an explosive spell turn.',
          actionType: 'bonus',
          resourceName: 'Innate Sorcery',
          resourceSummary: 'Long-rest class state',
          range: 'Self',
          tags: ['Sorcerer', 'Power State'],
        },
        {
          key: 'flexible casting',
          name: 'Flexible Casting',
          summary: 'Convert Sorcery Points and spell slots to rebalance endurance vs burst depending on encounter pressure.',
          actionType: 'special',
          resourceName: 'Sorcery Points',
          resourceSummary: 'Point/slot conversion economy',
          range: 'Self',
          tags: ['Sorcerer', 'Resource Engine'],
        },
        {
          key: 'metamagic',
          name: 'Metamagic',
          summary: 'Spend Sorcery Points to alter casting delivery with your chosen Metamagic options.',
          actionType: 'special',
          resourceName: 'Sorcery Points',
          resourceSummary: 'Metamagic cost varies by option',
          range: 'Spell-dependent',
          tags: ['Sorcerer', 'Spell Shaping'],
        },
      ],
      subclassActions: {
        'wild magic': [
          { key: 'wild-magic-surge', name: 'Wild Magic Surge', summary: 'Your leveled spell may trigger a surge event; keep this visible so chaos feels like a live system, not hidden text.', actionType: 'special', resourceName: 'Wild Magic Surge', tags: ['Wild Magic', 'Chaos'] },
          { key: 'wild-tides-of-chaos', name: 'Tides of Chaos', summary: 'Take advantage now, then expect the table to answer with surge pressure later.', actionType: 'special', resourceName: 'Tides of Chaos', tags: ['Wild Magic', 'Risk / Reward'] },
          { key: 'wild-bend-luck', name: 'Bend Luck', summary: 'Spend 2 Sorcery Points as a reaction to tilt a nearby creature’s roll in a clutch moment.', actionType: 'reaction', resourceName: 'Sorcery Points', tags: ['Wild Magic', 'Reaction'] },
          { key: 'wild-controlled-chaos', name: 'Controlled Chaos', summary: 'When surges trigger, roll twice and pick the better chaos result for the moment.', actionType: 'special', resourceName: 'Wild Magic Surge', tags: ['Wild Magic', 'Control'] },
        ],
        'draconic bloodline': [
          { key: 'draconic-dragon-ancestor', name: 'Dragon Ancestor', summary: 'Your ancestor element sets which spells and resistance spend patterns are most efficient for you.', actionType: 'passive', resourceName: 'Draconic Ancestry', tags: ['Draconic', 'Identity'] },
          { key: 'draconic-elemental-affinity', name: 'Elemental Affinity', summary: 'Add Charisma to matching element spells and optionally spend Sorcery Points for temporary resistance.', actionType: 'special', resourceName: 'Sorcery Points', tags: ['Draconic', 'Elemental'] },
          { key: 'draconic-dragon-wings', name: 'Dragon Wings', summary: 'Your bloodline manifests as flight, changing positioning and target access every round.', actionType: 'special', resourceName: 'Dragon Wings', tags: ['Draconic', 'Mobility'] },
          { key: 'draconic-presence', name: 'Draconic Presence', summary: 'Spend your long-rest aura to force charm/fear pressure across a wide area.', actionType: 'action', resourceName: 'Draconic Presence', tags: ['Draconic', 'Control'] },
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
    ranger: {
      actions: [
        { key: "hunter's mark", name: "Hunter's Mark", summary: 'Mark a priority target and keep pressure concentrated while tracking it through the encounter.', actionType: 'bonus', resourceName: 'Spell Slots', resourceSummary: 'Concentration spell', range: '90 ft', tags: ['Ranger', 'Mark'] },
        { key: 'conjure barrage', name: 'Conjure Barrage', summary: 'Spend a limited-use area volley when clustered enemies punish single-target routines.', actionType: 'action', resourceName: 'Conjure Barrage', resourceSummary: '1/LR feature action', range: 'Area effect', tags: ['Ranger', 'Area'] },
        { key: "nature's veil", name: "Nature's Veil", summary: 'Use bonus-action concealment to reposition, break focus fire, or open a cleaner attack line.', actionType: 'bonus', resourceName: '', resourceSummary: 'Class feature', range: 'Self', tags: ['Ranger', 'Stealth'] },
      ],
      subclassActions: {
        hunter: [
          { key: "hunter's prey", name: "Hunter's Prey Style", summary: 'Apply your chosen prey branch (Colossus Slayer, Giant Killer, or Horde Breaker) during weapon turns.', actionType: 'action', resourceName: '', range: 'Weapon-dependent', tags: ['Hunter', 'Branch'] },
          { key: 'multiattack', name: 'Hunter Multiattack', summary: 'Use Volley or Whirlwind when battlefield density makes standard attacks less efficient.', actionType: 'action', resourceName: '', range: 'Weapon / nearby area', tags: ['Hunter', 'Area Pressure'] },
          { key: 'stand against the tide', name: 'Stand Against the Tide', summary: 'Punish misses by redirecting enemy momentum through reaction timing.', actionType: 'reaction', resourceName: '', range: 'Triggered reaction', tags: ['Hunter', 'Reaction'] },
        ],
        'gloom stalker': [
          { key: 'dread ambusher', name: 'Dread Ambusher Opener', summary: 'Exploit first-round tempo: initiative edge, opening attack burst, and ambush pressure.', actionType: 'action', resourceName: '', range: 'Weapon-dependent', tags: ['Gloom Stalker', 'Opener'] },
          { key: "stalker's flurry", name: "Stalker's Flurry", summary: 'Recover tempo after a miss and keep opening pressure from collapsing.', actionType: 'action', resourceName: '', range: 'Triggered follow-up', tags: ['Gloom Stalker', 'Consistency'] },
          { key: 'shadowy dodge', name: 'Shadowy Dodge', summary: 'Use reaction defense to impose disadvantage when enemies finally line up a clean shot.', actionType: 'reaction', resourceName: '', range: 'Triggered reaction', tags: ['Gloom Stalker', 'Reaction'] },
        ],
        'beast master': [
          { key: "ranger's companion", name: "Companion Command", summary: 'Command your bonded beast so it contributes as a real partner in movement and attacks.', actionType: 'bonus', resourceName: 'Companion Command', range: 'Companion command range', tags: ['Beast Master', 'Companion'] },
          { key: 'exceptional training', name: 'Exceptional Training', summary: 'Issue cleaner utility and combat commands as companion reliability scales.', actionType: 'bonus', resourceName: 'Companion Command', range: 'Companion command range', tags: ['Beast Master', 'Companion'] },
          { key: 'bestial fury', name: 'Bestial Fury', summary: 'Leverage your companion’s upgraded offense so duo pressure remains relevant at higher tiers.', actionType: 'action', resourceName: 'Companion Command', range: 'Companion attacks', tags: ['Beast Master', 'Companion'] },
          { key: 'share spells', name: 'Share Spells', summary: 'Extend self-target spell support through both ranger and companion positioning.', actionType: 'action', resourceName: 'Spell Slots', range: 'Self + companion (30 ft)', tags: ['Beast Master', 'Spell Support'] },
        ],
      },
    },
    rogue: {
      actions: [
        {
          key: 'sneak attack',
          name: 'Sneak Attack Window',
          summary: 'Once per turn, when your hit meets the trigger, convert it into your current Sneak Attack precision burst.',
          actionType: 'action',
          resourceName: '',
          resourceSummary: 'Once per turn on a valid hit',
          range: 'Finesse / ranged weapon hit',
          tags: ['Rogue', 'Precision'],
        },
        {
          key: 'cunning action',
          name: 'Cunning Action',
          summary: 'Use Dash, Disengage, or Hide as a bonus action to create the angle you need before or after attacking.',
          actionType: 'bonus',
          resourceName: '',
          resourceSummary: 'At will',
          range: 'Self',
          tags: ['Rogue', 'Setup'],
        },
        {
          key: 'steady aim',
          name: 'Steady Aim',
          summary: 'Trade movement for accuracy so the attack that matters is more likely to land.',
          actionType: 'bonus',
          resourceName: '',
          resourceSummary: 'Speed becomes 0 this turn',
          range: 'Self',
          tags: ['Rogue', 'Setup'],
        },
        {
          key: 'cunning strike',
          name: 'Cunning Strike Riders',
          summary: 'When Sneak Attack lands, trade some dice for control or disruption instead of pure damage.',
          actionType: 'action',
          resourceName: 'Sneak Attack Dice',
          resourceSummary: 'Spend damage for rider effects',
          range: 'On Sneak Attack hit',
          tags: ['Rogue', 'Control'],
        },
      ],
      subclassActions: {
        assassin: [
          { key: 'assassinate', name: 'Assassinate', summary: 'Exploit first-turn and surprise timing for advantaged opener pressure and critical burst windows.', actionType: 'action', tags: ['Assassin', 'Ambush'] },
          { key: 'death strike', name: 'Death Strike', summary: 'Punish surprised targets with a high-stakes finisher that can double your attack damage.', actionType: 'action', tags: ['Assassin', 'Burst'] },
        ],
        thief: [
          { key: 'fast hands', name: 'Fast Hands', summary: 'Use your bonus action for object, tool, and pickpocket tempo that other rogues cannot match.', actionType: 'bonus', tags: ['Thief', 'Utility'] },
          { key: 'second-story work', name: 'Second-Story Work', summary: 'Turn climb and vertical movement into reliable combat positioning and escape lanes.', actionType: 'bonus', tags: ['Thief', 'Mobility'] },
        ],
        'arcane trickster': [
          { key: 'mage hand legerdemain', name: 'Mage Hand Legerdemain', summary: 'Run lock, trap, and theft interactions from range using invisible mage hand manipulation.', actionType: 'action', tags: ['Arcane Trickster', 'Utility'] },
          { key: 'versatile trickster', name: 'Versatile Trickster', summary: 'Use Mage Hand as a bonus-action distraction to set up advantaged weapon attacks.', actionType: 'bonus', tags: ['Arcane Trickster', 'Setup'] },
          { key: 'spell thief', name: 'Spell Thief', summary: 'When you resist a targeted spell, react to deny it and temporarily steal the magical edge.', actionType: 'reaction', tags: ['Arcane Trickster', 'Reaction'] },
        ],
      },
    },
    warlock: {
      actions: [
        { key: 'eldritch blast loop', name: 'Eldritch Blast Pressure', summary: 'Use Eldritch Blast as your default at-will pressure between pact-slot spikes.', actionType: 'action', resourceName: '', resourceSummary: 'At will cantrip pressure', range: '120 ft+', tags: ['Warlock', 'Signature'] },
        { key: 'pact slot cast', name: 'Pact Slot Cast', summary: 'Spend one pact slot; every pact-slot spell is cast at your current pact slot level.', actionType: 'action', resourceName: 'Pact Slots', resourceSummary: 'Short-rest slot economy', range: 'Spell-dependent', tags: ['Warlock', 'Pact Magic'] },
        { key: 'magical cunning', name: 'Magical Cunning', summary: 'Use your class recovery tool to stay relevant between short rests when the slot economy is tight.', actionType: 'special', resourceName: 'Pact Slots', resourceSummary: 'Recovery tempo', range: 'Self', tags: ['Warlock', 'Recovery'] },
      ],
      subclassActions: {
        'fiend-patron': [
          { key: 'dark ones blessing flow', name: 'Dark One’s Blessing Flow', summary: 'Track kill-trigger temporary hit points so infernal momentum stays visible in combat turns.', actionType: 'special', resourceName: 'Temp HP', tags: ['Fiend', 'Snowball'] },
          { key: 'hurl through hell', name: 'Hurl Through Hell', summary: 'Land your capstone punishment trigger when a key target must be removed from tempo.', actionType: 'special', resourceName: 'Long Rest feature', tags: ['Fiend', 'Punishment'] },
        ],
        'archfey-patron': [
          { key: 'fey presence', name: 'Fey Presence', summary: 'Burst charm/fear control to disrupt clustered enemies early in an exchange.', actionType: 'action', resourceName: 'Short Rest feature', tags: ['Archfey', 'Control'] },
          { key: 'misty escape', name: 'Misty Escape', summary: 'React to damage with invisibility + teleport so the warlock remains slippery under focus fire.', actionType: 'reaction', resourceName: 'Long Rest feature', tags: ['Archfey', 'Escape'] },
        ],
        'great-old-one-patron': [
          { key: 'awakened mind', name: 'Awakened Mind', summary: 'Use silent telepathy for scouting, coordination, and social pressure.', actionType: 'special', resourceName: '', tags: ['GOO', 'Telepathy'] },
          { key: 'entropic ward', name: 'Entropic Ward', summary: 'Reaction defense that bends attack flow and creates your counter-pressure window.', actionType: 'reaction', resourceName: 'Short Rest feature', tags: ['GOO', 'Defense'] },
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

  function _parseAttackBonusValue(raw) {
    if (raw == null || raw === '') return null;
    const direct = Number(raw);
    if (Number.isFinite(direct)) return direct;
    const match = String(raw).match(/[-+]?\d+/);
    if (!match) return null;
    const parsed = Number(match[0]);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function _resourceStateFromAction(action) {
    const readNum = function (value) {
      if (value == null || value === '') return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };
    let remaining = readNum(action && (action.remaining ?? action.current ?? action.usesRemaining));
    let max = readNum(action && (action.max ?? action.usesMax));
    const summary = _firstText(action && action.resourceSummary, action && action.resourceName, action && action.usage, action && action.recovery, '');
    const fraction = String(summary || '').match(/(\d+)\s*\/\s*(\d+)/);
    if (fraction) {
      if (remaining == null) remaining = Number(fraction[1]);
      if (max == null) max = Number(fraction[2]);
    }
    const rechargeSource = (function () {
      const text = `${String(action && action.recovery || '')} ${String(summary || '')}`.toLowerCase();
      if (/short\s*(?:\/|or\s+)\s*long\s*rest|short\s*rest.*long\s*rest|long\s*rest.*short\s*rest/.test(text)) return 'Short/Long Rest';
      if (/short\s*rest/.test(text)) return 'Short Rest';
      if (/long\s*rest/.test(text)) return 'Long Rest';
      if (/resource|pool|slot|charges?|points?|dice/.test(text)) return 'Resource pool';
      return '';
    }());
    const exhausted = remaining != null && max != null && max > 0 && remaining <= 0;
    return {
      remaining: remaining,
      max: max,
      exhausted: exhausted,
      rechargeSource: rechargeSource,
      summary: summary,
    };
  }


  function _renderSummonManager(summonActions) {
    const rows = _safeArray(summonActions);
    if (!rows.length) {
      return `<div class="cs-combat-callout muted"><div class="cs-combat-callout-title">Summon Manager</div><div class="cs-combat-callout-copy">No live summon families are currently unlocked for this character.</div></div>`;
    }
    const totalActive = rows.reduce(function (sum, action) {
      const meta = action && action.summonAction && typeof action.summonAction === 'object' ? action.summonAction : {};
      return sum + _safeArray(meta.activeSummons).length;
    }, 0);
    return `<div class="cs-combat-callout" style="margin-top:.55rem;">
      <div class="cs-combat-callout-title">Summon Manager</div>
      <div class="cs-combat-callout-copy">Unlocked families: ${rows.length} • Active summons: ${totalActive}. Choose variant, summon/deploy, focus, inspect, and dismiss from one compact panel.</div>
      <div style="display:grid;gap:.45rem;margin-top:.5rem;">
        ${rows.map(function (action) {
          const meta = action && action.summonAction && typeof action.summonAction === 'object' ? action.summonAction : {};
          const actionId = _firstText(action && action.id, '');
          const variants = _safeArray(meta.variants).filter(function (entry) { return entry && typeof entry === 'object'; });
          const activeRows = _safeArray(meta.activeSummons).filter(function (entry) { return entry && typeof entry === 'object'; });
          const selectedVariantId = _firstText(meta.selectedVariantId, variants[0] && variants[0].id, '').toLowerCase();
          const variantHint = meta.replaceOnResummon ? 'Switching variants replaces the existing summon when deployed again.' : 'Switching variants applies to your next summon/deploy.';
          const entityBadge = meta.isCreature ? 'Creature' : `Field ${_firstText(meta.entityKind, 'effect').replace(/_/g, ' ')}`;
          const interaction = meta && meta.interactionModel && typeof meta.interactionModel === 'object' ? meta.interactionModel : {};
          const interactionBits = [
            interaction.stationary ? 'stationary' : '',
            interaction.triggerable ? 'triggerable' : '',
            interaction.destructible ? 'destructible' : 'indestructible',
            interaction.ownerActivated ? 'owner-activated' : 'passive',
          ].filter(Boolean);
          return `<div style="border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:.45rem .52rem;background:rgba(0,0,0,.18);">
            <div style="display:flex;justify-content:space-between;gap:.45rem;align-items:flex-start;">
              <div>
                <div style="font-weight:700;font-size:.72rem;">${_esc(_firstText(action && action.name, 'Summon'))}</div>
                <div style="font-size:.6rem;color:rgba(235,230,210,.72);">${_esc(_firstText(meta.sourceFeatureName, 'Source unknown'))} • ${_esc(entityBadge)}</div>
              </div>
              <div style="font-size:.6rem;color:rgba(235,230,210,.72);">Active ${_num(meta.currentActiveCount, 0)}/${Math.max(0, _num(meta.maxActive, 1))}</div>
            </div>
            <div style="display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:.35rem;margin-top:.42rem;align-items:center;">
              <select data-summon-variant-for="${_esc(actionId)}" style="width:100%;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.16);border-radius:7px;color:#e8dcc8;padding:.28rem .35rem;font-size:.64rem;" ${variants.length > 1 ? '' : 'disabled'}>
                ${variants.map(function (variant) {
                  const id = _firstText(variant && variant.id, '').toLowerCase();
                  const selected = id === selectedVariantId ? 'selected' : '';
                  return `<option value="${_esc(id)}" ${selected}>${_esc(_firstText(variant && variant.displayName, id, 'Variant'))}</option>`;
                }).join('') || `<option value="${_esc(selectedVariantId)}">${_esc(_firstText(meta.selectedVariantName, 'Variant'))}</option>`}
              </select>
              <button type="button" class="cs-feature-inspect" data-action-use="${_esc(actionId)}" data-action-source="summon_action">${_esc(/deploy/i.test(String(action && action.actionType || '')) ? 'Deploy' : 'Summon')}</button>
              <button type="button" class="cs-feature-inspect" data-action-dismiss="${_esc(actionId)}" data-action-source="summon_action" ${activeRows.length ? '' : 'disabled'}>Dismiss</button>
            </div>
            <div style="font-size:.58rem;color:rgba(235,230,210,.68);margin-top:.3rem;">${_esc(_firstText(meta.commandModelSummary, 'Command model pending.'))} • ${_esc(variantHint)}${interactionBits.length ? ` • ${_esc(interactionBits.join(', '))}` : ''}</div>
            ${activeRows.length ? `<div style="display:grid;gap:.3rem;margin-top:.45rem;">${activeRows.map(function (row) {
              const tokenId = _firstText(row && row.tokenId, '');
              return `<div style="display:flex;justify-content:space-between;align-items:center;gap:.35rem;font-size:.6rem;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:7px;padding:.25rem .35rem;">
                <span>${_esc(_firstText(row && row.variantName, row && row.variantId, 'Summon'))} • ${_esc(_firstText(row && row.status, 'active'))}${tokenId ? ' • token linked' : ' • token missing'}</span>
                <span style="display:flex;gap:.25rem;">
                  <button type="button" class="cs-feature-inspect" data-summon-focus-token="${_esc(tokenId)}" ${tokenId ? '' : 'disabled'}>Focus</button>
                  <button type="button" class="cs-feature-inspect" data-summon-inspect-token="${_esc(tokenId)}" ${tokenId ? '' : 'disabled'}>Inspect</button>
                </span>
              </div>`;
            }).join('')}</div>` : ''}
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }

  function _summonActionRows(charData) {
    return _safeArray(charData && charData.summonActions).map(function (entry, index) {
      if (!entry || typeof entry !== 'object') return null;
      const actionTypeText = _firstText(entry.actionType, 'Summon');
      const selectedVariantName = _firstText(entry.selectedVariantName, entry.summonDisplayName, '');
      const variants = _safeArray(entry.variants);
      const variantLabel = variants.map(function (variant) {
        return _firstText(variant && variant.displayName, variant && variant.id, '');
      }).filter(Boolean);
      const activeCount = _num(entry.currentActiveCount, 0);
      const maxActive = Math.max(0, _num(entry.maxActive, 1));
      const isCreature = !!entry.isCreature;
      const entityKind = _firstText(entry.entityKind, isCreature ? 'creature' : 'effect');
      const id = _firstText(entry.id, entry.summonGroupId, entry.summonTemplateId, '') || (`summon-action-${index + 1}`);
      return {
        id: id,
        source: 'summon_action',
        name: _firstText(entry.displayName, selectedVariantName, 'Summon'),
        desc: _firstText(entry.shortSummary, `Use ${actionTypeText.toLowerCase()} when your ${isCreature ? 'companion creature' : 'field deployment'} is needed.`),
        description: _firstText(entry.shortSummary, `Use ${actionTypeText.toLowerCase()} when your ${isCreature ? 'companion creature' : 'field deployment'} is needed.`),
        economy: ['action'],
        icon: /deploy/i.test(actionTypeText) ? '🛠️' : '🧿',
        actionType: actionTypeText,
        resourceName: `Active ${activeCount}/${maxActive}`,
        resourceSummary: `Active ${activeCount}/${maxActive}${entry.replaceOnResummon ? ' • Replaces existing summon on re-use' : ''}`,
        range: _firstText(entry.commandModelSummary, ''),
        tags: []
          .concat(_safeArray(entry.tags))
          .concat([isCreature ? 'Creature Summon' : `Field ${entityKind.replace(/_/g, ' ')}`])
          .concat(variantLabel.length ? ['Variants: ' + variantLabel.join(', ')] : [])
          .concat(selectedVariantName ? ['Selected: ' + selectedVariantName] : []),
        longText: [
          _firstText(entry.shortSummary, ''),
          _firstText(entry.sourceFeatureName, '') ? `Source feature: ${_firstText(entry.sourceFeatureName, '')}` : '',
          selectedVariantName ? `Selected variant: ${selectedVariantName}` : '',
          variantLabel.length > 1 ? `Unlocked variants: ${variantLabel.join(', ')}` : '',
          `Command model: ${_firstText(entry.commandModelSummary, 'Runtime command model pending.')}`,
          `Active count: ${activeCount}/${maxActive}`,
          entry.replaceOnResummon ? 'Re-summoning will replace an existing summon.' : '',
        ].filter(Boolean).join('\n\n'),
        summonAction: entry,
      };
    }).filter(Boolean);
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

  function _cloneJsonSafe(value, fallback) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return fallback;
    }
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
    if ((action.attackBonus != null || action.damage || action.damageText || action.range || action.reach) && !(action.range || action.reach)) blockers.push({ label: 'Targeting', value: 'This action may need manual target selection when no range/reach metadata is provided.' });
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
        ...(action && action.source === 'summon_action' ? [{
          title: 'Summon / Deploy Metadata',
          items: [
            { label: 'Source feature', value: _firstText(action && action.summonAction && action.summonAction.sourceFeatureName, '—') },
            { label: 'Selected variant', value: _firstText(action && action.summonAction && action.summonAction.selectedVariantName, '—') },
            { label: 'Available variants', value: _safeArray(action && action.summonAction && action.summonAction.variants).map(function (variant) { return _firstText(variant && variant.displayName, variant && variant.id, ''); }).filter(Boolean).join(', ') || '—' },
            { label: 'Active count', value: `${_num(action && action.summonAction && action.summonAction.currentActiveCount, 0)}/${Math.max(0, _num(action && action.summonAction && action.summonAction.maxActive, 1))}` },
            { label: 'Replace on re-summon', value: action && action.summonAction && action.summonAction.replaceOnResummon ? 'Yes' : 'No' },
            { label: 'Command model', value: _firstText(action && action.summonAction && action.summonAction.commandModelSummary, 'Runtime command model pending.') },
          ],
        }] : []),
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
    const rogueLine = _classKey(charData) === 'rogue'
      ? [
          classMechanics.sneakAttackDice ? ('Sneak Attack: ' + classMechanics.sneakAttackDice) : '',
          classMechanics.cunningStrikeMaxOptions != null ? ('Cunning Strike riders: ' + classMechanics.cunningStrikeMaxOptions) : '',
          (charData && charData.subclassName && String(charData.subclassName).toLowerCase().indexOf('arcane trickster') >= 0 && charData.spellSaveDc)
            ? ('Arcane Trickster spell save DC: ' + charData.spellSaveDc)
            : '',
        ].filter(Boolean).join(' • ')
      : '';
    const warlockLine = _classKey(charData) === 'warlock'
      ? [
          classMechanics.pactSlots != null ? ('Pact slots: ' + classMechanics.pactSlots) : '',
          classMechanics.pactSlotLevel != null ? ('Pact slot level: ' + classMechanics.pactSlotLevel) : '',
          classMechanics.invocationsKnown != null ? ('Invocations known: ' + classMechanics.invocationsKnown) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const rangerLine = _classKey(charData) === 'ranger'
      ? [
          classMechanics.extraAttacks != null ? ('Attacks per Attack action: ' + classMechanics.extraAttacks) : '',
          classMechanics.spellsKnown != null ? ('Spells known: ' + classMechanics.spellsKnown) : '',
          (charData && charData.spellSaveDc) ? ('Spell save DC (WIS): ' + charData.spellSaveDc) : '',
          (charData && charData.spellAttackBonus != null) ? ('Spell attack: ' + charData.spellAttackBonus) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const druidLine = _classKey(charData) === 'druid'
      ? [
          classMechanics.wildShapeUses != null ? ('Wild Shape uses: ' + classMechanics.wildShapeUses) : '',
          classMechanics.wildShapeMaxCR != null ? ('Wild Shape max form CR: ' + classMechanics.wildShapeMaxCR) : '',
          classMechanics.spellsPreparedFormula ? ('Prepared formula: ' + classMechanics.spellsPreparedFormula.replace(/_/g, ' ')) : '',
          classMechanics.cantripsKnown != null ? ('Cantrips known: ' + classMechanics.cantripsKnown) : '',
          (charData && charData.spellSaveDc) ? ('Spell save DC (WIS): ' + charData.spellSaveDc) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const fighterLine = _classKey(charData) === 'fighter'
      ? [
          classMechanics.extraAttacks != null ? ('Attacks per Attack action: ' + classMechanics.extraAttacks) : '',
          classMechanics.weaponMasteryCount != null ? ('Weapon Masteries: ' + classMechanics.weaponMasteryCount) : '',
          classMechanics.secondWindUses != null ? ('Second Wind uses: ' + classMechanics.secondWindUses) : '',
          classMechanics.actionSurgeUses != null ? ('Action Surge uses: ' + classMechanics.actionSurgeUses) : '',
          classMechanics.indomitableUses != null ? ('Indomitable uses: ' + classMechanics.indomitableUses) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const pirateLine = _classKey(charData) === 'pirate'
      ? [
          classMechanics.swaggerUses != null ? ('Swagger Dice uses: ' + classMechanics.swaggerUses) : '',
          classMechanics.swaggerDice ? ('Swagger die: ' + String(classMechanics.swaggerDice).toUpperCase()) : '',
          classMechanics.trickOptions != null ? ('Dirty trick options: ' + classMechanics.trickOptions) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const tinkerLine = _classKey(charData) === 'tinker'
      ? [
          classMechanics.gadgetCharges != null ? ('Gadget Charges: ' + classMechanics.gadgetCharges) : '',
          classMechanics.infusionSlots != null ? ('Infusion slots: ' + classMechanics.infusionSlots) : '',
          classMechanics.spellsKnown != null ? ('Spells known: ' + classMechanics.spellsKnown) : '',
          classMechanics.cantripsKnown != null ? ('Cantrips known: ' + classMechanics.cantripsKnown) : '',
          (charData && charData.spellSaveDc) ? ('Spell save DC (INT): ' + charData.spellSaveDc) : '',
        ].filter(Boolean).join(' • ')
      : '';
    const tinkerSubclassLine = _classKey(charData) === 'tinker'
      ? (function () {
          const subclass = _customSubclassKey(charData);
          if (!subclass) return '';
          if (subclass === 'artillerist') return 'Artillerist: Arc Cannon and Shatter Field should read as active deployment pressure tools.';
          if (subclass === 'alchemist') return 'Alchemist: Elixir and Panacea actions should read as charge-backed support and recovery plays.';
          if (subclass === 'mechanist') return 'Mechanist: Companion Frame commands should feel like a second body with linked-action tempo.';
          if (subclass === 'saboteur') return 'Saboteur: Ghost Tools and Chain Reaction should surface stealth setup and reaction disruption rhythm.';
          return '';
        }())
      : '';
    const pirateSubclassLine = _classKey(charData) === 'pirate'
      ? (function () {
          const subclass = _customSubclassKey(charData);
          if (!subclass) return '';
          if (subclass === 'corsair') return 'Corsair: duel pressure, boarding bursts, and reaction tempo should be obvious.';
          if (subclass === 'privateer') return 'Privateer: command/support swagger should read as ally-facing tempo tools.';
          if (subclass === 'smuggler') return 'Smuggler: escape tools, concealment, and slippery reaction play should stand out.';
          if (subclass === 'dread captain') return 'Dread Captain: fear pressure, momentum punish, and intimidation rhythm should stand out.';
          return '';
        }())
      : '';
    const fighterSubclassLine = _classKey(charData) === 'fighter'
      ? (function () {
          const subclass = _customSubclassKey(charData);
          if (subclass === 'battlemaster' || subclass === 'battle master') {
            const abilityScores = _charAbilityScores(charData);
            const maneuverAbility = Math.max(_abilityMod(abilityScores.str), _abilityMod(abilityScores.dex));
            const saveDc = 8 + _charProfBonus(charData) + maneuverAbility;
            return 'Battle Master: Superiority Dice 4d8 • Maneuver save DC ' + saveDc + ' • Maneuvers should be visible in Actions.';
          }
          if (subclass === 'eldritch knight') {
            const abilityScores = _charAbilityScores(charData);
            const saveDc = 8 + _charProfBonus(charData) + _abilityMod(abilityScores.int);
            return 'Eldritch Knight: One-third caster flow • Spell save DC (INT) ' + saveDc + ' • War Magic / Weapon Bond cadence should be visible.';
          }
          if (subclass === 'champion') {
            return 'Champion: Improved Critical pressure, athletic identity, and late-fight durability should read as your subclass loop.';
          }
          return '';
        }())
      : '';
    return `<div class="cs-combat-callout-grid">
      <div class="cs-combat-callout">
        <div class="cs-combat-callout-title">${_esc(guide.title)}</div>
        <div class="cs-combat-callout-copy">${_esc(guide.copy)}</div>
        ${barbarianLine ? `<div class="cs-combat-callout-copy">${_esc(barbarianLine)}</div>` : ''}
        ${paladinLine ? `<div class="cs-combat-callout-copy">${_esc(paladinLine)}</div>` : ''}
        ${rogueLine ? `<div class="cs-combat-callout-copy">${_esc(rogueLine)}</div>` : ''}
        ${warlockLine ? `<div class="cs-combat-callout-copy">${_esc(warlockLine)}</div>` : ''}
        ${rangerLine ? `<div class="cs-combat-callout-copy">${_esc(rangerLine)}</div>` : ''}
        ${druidLine ? `<div class="cs-combat-callout-copy">${_esc(druidLine)}</div>` : ''}
        ${fighterLine ? `<div class="cs-combat-callout-copy">${_esc(fighterLine)}</div>` : ''}
        ${fighterSubclassLine ? `<div class="cs-combat-callout-copy">${_esc(fighterSubclassLine)}</div>` : ''}
        ${tinkerLine ? `<div class="cs-combat-callout-copy">${_esc(tinkerLine)}</div>` : ''}
        ${tinkerSubclassLine ? `<div class="cs-combat-callout-copy">${_esc(tinkerSubclassLine)}</div>` : ''}
        ${pirateLine ? `<div class="cs-combat-callout-copy">${_esc(pirateLine)}</div>` : ''}
        ${pirateSubclassLine ? `<div class="cs-combat-callout-copy">${_esc(pirateSubclassLine)}</div>` : ''}
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

  function _actionKind(action) {
    const text = `${String(action && action.name || '')} ${String(action && (action.desc || action.description || action.longText || '') || '')}`.toLowerCase();
    const economy = (Array.isArray(action && action.economy) ? action.economy : [action && action.economy || action && action.actionType || '']).join(' ').toLowerCase();
    const source = String(action && action.source || '').toLowerCase();
    const attackBonus = _parseAttackBonusValue(action && action.attackBonus);
    const hasAttackRoll = attackBonus != null;
    const hasDamage = !!_firstText(action && action.damage, action && action.damageText, '');
    const hasSave = !!_firstText(action && action.saveDC, action && action.hitDc, action && action.save, '');
    const hasActionLane = /(action|bonus|reaction|special|trigger)/.test(economy);
    if ((/subclass choice required|choose subclass|subclass required/.test(text)) || action && action.kind === 'subclass_gate') return 'subclass_gate';
    if (/passive|always on|always-on/.test(economy) || /passive/.test(text)) return 'passive';
    if (/wild shape|transform|shift form|beast form/.test(text) && !hasAttackRoll && !hasDamage) return 'transformation';
    if (source === 'weapon' || source === 'equip_only' || source === 'system_unarmed' || source === 'wild_shape_form') return 'attack';
    if (hasAttackRoll || (hasDamage && !hasSave)) return 'attack';
    if (hasSave && !hasAttackRoll) return 'save_effect';
    if (hasActionLane) return 'use';
    return 'use';
  }

  function _canUseAction(action, kind) {
    if (!action || kind === 'passive' || kind === 'subclass_gate') return false;
    const source = String(action.source || '').toLowerCase();
    if (source === 'feature-fallback') return false;
    if (source === 'summon_action' && !_summonActionRuntimeSupported(action)) return false;
    if (action.disabled) return false;
    const resourceState = _resourceStateFromAction(action);
    if (resourceState.exhausted) return false;
    return true;
  }

  function _summonActionRuntimeSupported(action) {
    const summonMeta = action && action.summonAction && typeof action.summonAction === 'object' ? action.summonAction : {};
    const sourceClassId = String((summonMeta.sourceClassId || '').toLowerCase());
    const sourceSubclassId = String((summonMeta.sourceSubclassId || '').toLowerCase());
    const summonGroupId = String((summonMeta.summonGroupId || '').toLowerCase());
    const summonTemplateId = String((summonMeta.summonTemplateId || '').toLowerCase());
    const isBeastMaster = sourceClassId === 'ranger' && sourceSubclassId === 'beast-master';
    const isWarlockChain = sourceClassId === 'warlock' && summonGroupId === 'warlock-pact-chain-familiar';
    const isTinkerMechanist = sourceClassId === 'tinker' && sourceSubclassId === 'mechanist' && summonTemplateId === 'tinker-mechanist-companion-frame';
    return !!(isBeastMaster || isWarlockChain || isTinkerMechanist);
  }

  function _renderActionRow(action) {
    const econ = Array.isArray(action.economy) ? action.economy : [action.economy || 'action'];
    const sourceTag = _firstText(action.source, '').replace(/_/g, ' ').trim();
    const summary = _firstText(action.desc, action.description, 'No summary loaded yet.');
    const bestUse = _firstText(action.longText, action.description, action.desc, 'Use this when the action helps your turn right now.');
    const kind = _actionKind(action);
    const attackBonusValue = _parseAttackBonusValue(action.attackBonus);
    const toHit = attackBonusValue != null ? (attackBonusValue >= 0 ? `+${attackBonusValue}` : String(attackBonusValue)) : '';
    const resourceState = _resourceStateFromAction(action);
    const laneRows = [];
    if (action && action.source === 'summon_action') {
      const summonMeta = action.summonAction && typeof action.summonAction === 'object' ? action.summonAction : {};
      const variants = _safeArray(summonMeta.variants).map(function (variant) {
        return _firstText(variant && variant.displayName, variant && variant.id, '');
      }).filter(Boolean);
      laneRows.push({ label: 'Source', value: _firstText(summonMeta.sourceFeatureName, '—') });
      laneRows.push({ label: 'Summons', value: _firstText(summonMeta.selectedVariantName, summonMeta.summonDisplayName, '—') });
      if (variants.length > 1) laneRows.push({ label: 'Variants', value: variants.join(', ') });
      laneRows.push({ label: 'Active', value: `${_num(summonMeta.currentActiveCount, 0)}/${Math.max(0, _num(summonMeta.maxActive, 1))}` });
      laneRows.push({ label: 'Re-summon', value: summonMeta.replaceOnResummon ? 'Replaces existing summon' : 'Adds without replacement' });
      laneRows.push({ label: 'Command', value: _firstText(summonMeta.commandModelSummary, 'Runtime command model pending.') });
    } else if (kind === 'attack') {
      const effect = _firstText(action.damage, action.damageText, action.effect, '');
      const range = _firstText(action.range, action.reach, '');
      const spend = _firstText(action.resourceSummary, action.resourceName, action.cost, action.usesText, '');
      if (toHit) laneRows.push({ label: 'To hit', value: toHit });
      if (_firstText(action.saveDC, action.hitDc, action.save, '')) laneRows.push({ label: 'Save / DC', value: _firstText(action.saveDC, action.hitDc, action.save, '') });
      if (effect) laneRows.push({ label: 'Effect', value: effect });
      if (range) laneRows.push({ label: 'Range', value: range });
      if (spend) laneRows.push({ label: 'Spend', value: spend });
      if (resourceState.rechargeSource) laneRows.push({ label: 'Recharge', value: resourceState.rechargeSource });
    } else {
      const actionType = _firstText(action.actionType, action.type, econ[0], 'Feature');
      const trigger = _firstText(action.trigger, action.usage, '');
      const spend = _firstText(action.resourceSummary, action.resourceName, action.cost, action.usesText, '');
      const range = _firstText(action.range, action.reach, '');
      laneRows.push({ label: 'Type', value: actionType.replace(/_/g, ' ') });
      if (trigger) laneRows.push({ label: 'When', value: trigger });
      if (spend) laneRows.push({ label: 'Spend', value: spend });
      if (resourceState.rechargeSource) laneRows.push({ label: 'Recharge', value: resourceState.rechargeSource });
      if (range) laneRows.push({ label: 'Range', value: range });
      if (_firstText(action.saveDC, action.hitDc, action.save, '')) laneRows.push({ label: 'Save / DC', value: _firstText(action.saveDC, action.hitDc, action.save, '') });
    }
    const leadBadges = [];
    if (kind === 'attack' && toHit) leadBadges.push('<span class="cs-action-mini-pill accent">Attack roll</span>');
    if (kind === 'save_effect' || /save/i.test(String(action.saveText || action.effect || action.saveDC || action.hitDc || action.save || ''))) leadBadges.push('<span class="cs-action-mini-pill">Save / effect</span>');
    if (/bonus/i.test(String(econ.join(' ')))) leadBadges.push('<span class="cs-action-mini-pill">Bonus action</span>');
    if (/reaction/i.test(String(econ.join(' ')))) leadBadges.push('<span class="cs-action-mini-pill">Reaction</span>');
    if (kind === 'passive') leadBadges.push('<span class="cs-action-mini-pill">Passive</span>');
    if (kind === 'transformation') leadBadges.push('<span class="cs-action-mini-pill">Transformation</span>');
    if (kind === 'subclass_gate') leadBadges.push('<span class="cs-action-mini-pill warn">Subclass choice required</span>');
    if (!leadBadges.length) leadBadges.push('<span class="cs-action-mini-pill ready">Usable now</span>');
    const useLabel = (function () {
      const src = String(action.source || '').toLowerCase();
      const text = `${String(action.name || '')} ${String(action.resourceName || '')} ${String(action.resourceSummary || '')}`.toLowerCase();
      if (src === 'summon_action') return /deploy/i.test(String(action.actionType || '')) ? 'Deploy' : 'Summon';
      if (src === 'spell') return 'Cast';
      if (kind === 'subclass_gate') return 'Choose subclass';
      if (src === 'weapon' || src === 'equip_only' || src === 'system_unarmed' || kind === 'attack') return 'Attack';
      if (kind === 'save_effect') return 'Use Effect';
      if (kind === 'transformation') return 'Transform';
      if (/swagger/.test(text)) return 'Spend Swagger';
      if (/gadget/.test(text)) return 'Use Device';
      return 'Use';
    }());
    const showUseButton = _canUseAction(action, kind);
    const activeSummons = _safeArray(action && action.summonAction && action.summonAction.activeSummons);
    const showDismissButton = action && action.source === 'summon_action' && activeSummons.length > 0;
    const disabledReason = action.disabledReason || (resourceState.exhausted ? `Out of uses${resourceState.rechargeSource ? ` · Recharges on ${resourceState.rechargeSource}` : ''}` : 'Unavailable');
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
        ${(showUseButton || resourceState.exhausted || action.disabled || showDismissButton) ? `<div class="cs-action-controls" style="margin-top:.55rem;display:flex;gap:.4rem;flex-wrap:wrap;">
          <button type="button" class="cs-feature-inspect" data-action-use="${_esc(String(action.id || action.name || ''))}" data-action-source="${_esc(String(action.source || 'weapon'))}" ${(showUseButton ? '' : `disabled title="${_esc(disabledReason)}"`)}>${_esc(useLabel)}</button>
          ${showDismissButton ? `<button type="button" class="cs-feature-inspect" data-action-dismiss="${_esc(String(action.id || action.name || ''))}" data-action-source="${_esc(String(action.source || 'weapon'))}">Dismiss</button>` : ''}
        </div>` : ''}
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
      const attackBonus = card.attackBonus != null
        ? card.attackBonus
        : (card.attack_bonus_value != null ? card.attack_bonus_value : _firstText(card.attack_bonus, card.toHit, card.hit));
      const damageText = _firstText(
        card.damage,
        card.damageText,
        card.damage_formula,
        card.base_damage_formula,
        card.effect
      );
      return {
        id: canonicalId || ('attack-' + fallbackId),
        combatCardId: canonicalId || String(card.name || '').trim(),
        source: String(card.source || 'weapon').trim() || 'weapon',
        name: card.name || 'Attack',
        desc: _firstText(card.summary, card.note, card.text, 'Generated quick attack card.'),
        description: _firstText(card.summary, card.note, card.text, 'Generated quick attack card.'),
        economy: ['action'],
        icon: card.icon || (String(card.range || '').match(/ft|range/i) ? '🏹' : '⚔️'),
        attackBonus: attackBonus,
        damage: damageText,
        damageText: damageText,
        range: _firstText(card.range, card.reach),
        resourceName: _firstText(card.ammoKind, card.ammoNote),
        tags: [card.source === 'equip_only' ? 'Equipped Loadout' : '', card.modeLabel || '', card.mastery_label || card.masteryLabel || ''].filter(Boolean),
        longText: [card.summary, card.note, card.modeNote, card.mastery_text].filter(Boolean).join('\n\n'),
      };
    });
  }

  function _buildItemActionCards() {
    const rows = Array.isArray(global._playerItemActions) ? global._playerItemActions : [];
    return rows.map(function (row, index) {
      const activation = String(row.activation_type || 'action').toLowerCase();
      const economy = activation === 'bonus_action' ? 'bonus' : activation === 'reaction' ? 'reaction' : 'action';
      const usageBits = [];
      if (Number.isFinite(Number(row.charges_current))) usageBits.push(`Charges ${row.charges_current}/${Number(row.charges_max || 0)}`);
      if (Number.isFinite(Number(row.quantity))) usageBits.push(`Qty ${row.quantity}`);
      if (row.disabled && row.disabled_reason) usageBits.push(row.disabled_reason);
      return {
        id: String(row.action_id || `item_action_${index}`),
        source: 'item_action',
        name: String(row.action_name || row.item_name || 'Item Action'),
        desc: String(row.effect_text || ''),
        description: String(row.effect_text || ''),
        economy: [economy],
        icon: '🧰',
        attackBonus: row.attack_bonus != null ? Number(row.attack_bonus) : '',
        damage: String(row.damage_formula || ''),
        range: String(row.range || ''),
        resourceName: usageBits.join(' • '),
        resourceSummary: usageBits.join(' • '),
        tags: ['Item', String(row.item_name || 'Item')],
        longText: String(row.effect_text || ''),
        disabled: !!row.disabled,
        disabledReason: String(row.disabled_reason || ''),
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

  function _normalizedActionIdentity(card, fallbackEconomy, classKey) {
    const entry = card && typeof card === 'object' ? card : {};
    const economy = _firstText(entry.economy, entry.actionType, entry.type, fallbackEconomy, 'action').toLowerCase();
    const name = _firstText(entry.name, entry.label, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    const sourceFeatureId = _firstText(entry.featureId, entry.sourceFeatureId, entry.id, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').trim();
    const normalizedClass = String(classKey || '').toLowerCase().trim();
    return [name, normalizedClass, economy, sourceFeatureId].join('::');
  }

  function _dedupeActionBucket(cards, fallbackEconomy, classKey) {
    const priorityForSource = function (source) {
      const text = String(source || '').toLowerCase();
      if (text === 'native_action') return 4;
      if (text === 'custom_druid_action') return 3;
      if (text === 'feature-fallback') return 1;
      return 2;
    };
    const byIdentity = new Map();
    _safeArray(cards).forEach(function (card) {
      const identity = _normalizedActionIdentity(card, fallbackEconomy, classKey);
      if (!identity) return;
      const prev = byIdentity.get(identity);
      if (!prev) {
        byIdentity.set(identity, card);
        return;
      }
      const prevPriority = priorityForSource(prev && prev.source);
      const nextPriority = priorityForSource(card && card.source);
      if (nextPriority > prevPriority) byIdentity.set(identity, card);
    });
    return Array.from(byIdentity.values());
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
      if (!feature && classKey !== 'druid') return;
      const actionType = String(def.actionType || (feature && feature.actionType) || (feature && feature.type) || 'action').toLowerCase();
      const bucket = /reaction/.test(actionType) ? 'reactions' : /bonus/.test(actionType) ? 'bonusActions' : 'actions';
      const id = `custom_${classKey}_${String(def.key || index).replace(/[^a-z0-9]+/gi, '_').toLowerCase()}`;
      if (seen.has(id)) return;
      seen.add(id);
      const usageBits = [_firstText(feature && feature.usage, ''), _firstText(feature && feature.recovery, '')].filter(Boolean).join(' • ');
      groups[bucket].push({
        id: id,
        source: classKey === 'druid' ? 'custom_druid_action' : 'native_action',
        name: def.name || feature.name || 'Custom Action',
        summary: _firstText(def.summary, feature && feature.summary, feature && feature.description, 'Class action'),
        description: _firstText(def.summary, feature && feature.summary, feature && feature.description, 'Class action'),
        text: [_firstText(feature && feature.description, ''), _firstText(feature && feature.longText, '')].filter(Boolean).join('\n\n'),
        actionType: actionType,
        type: actionType,
        range: _firstText(def.range, feature && feature.range, ''),
        resourceName: _firstText(def.resourceName, feature && feature.resourceName, ''),
        resourceSummary: _firstText(def.resourceSummary, usageBits, ''),
        tags: (Array.isArray(def.tags) ? def.tags : []).concat([_firstText(feature && feature.source, classKey)]).filter(Boolean),
        note: _firstText(feature && feature.summary, feature && feature.usage, feature && feature.recovery, ''),
        effectText: _firstText(feature && feature.effect, ''),
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
    const classKey = _classKey(charData);
    const isDruid = classKey === 'druid';
    const nativeCount = _safeArray(groups.actions).length + _safeArray(groups.bonusActions).length + _safeArray(groups.reactions).length;
    const fallbackFiltered = isDruid && nativeCount > 0
      ? {
          actions: _safeArray(fallback.actions).filter(function (card) {
            const name = _firstText(card && card.name, '').toLowerCase();
            return !(/wild shape|circle spells|prepared spell/.test(name));
          }),
          bonusActions: _safeArray(fallback.bonusActions).filter(function (card) {
            const name = _firstText(card && card.name, '').toLowerCase();
            return !(/wild shape|circle spells|prepared spell/.test(name));
          }),
          reactions: _safeArray(fallback.reactions).filter(function (card) {
            const name = _firstText(card && card.name, '').toLowerCase();
            return !(/wild shape|circle spells|prepared spell/.test(name));
          }),
        }
      : fallback;
    const subclassGate = (function () {
      const className = _firstText(charData && charData.className, charData && charData.classId, 'Class');
      const unlockLevel = _num(charData && charData.subclassUnlockLevel, 0);
      const isPending = !!(charData && charData.subclassPending);
      if (!isPending) return null;
      return _normalizeNativeAction({
        id: `subclass-choice-required-${String(className).toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        name: 'Subclass Choice Required',
        summary: `${className} chooses a subclass at level ${unlockLevel || 'this tier'}. Select your subclass to unlock class progression features.`,
        description: `Your ${className} is high enough level to require a subclass, but none is selected yet. Open the level-up flow and choose a subclass before continuing progression.`,
        text: 'Open Level Up and choose your subclass path.',
        actionType: 'feature',
        type: 'feature',
        tags: ['Subclass', 'Required Choice'],
        source: 'subclass-gate',
        kind: 'subclass_gate',
      }, 'action');
    }());
    const out = {
      actions: _dedupeActionBucket(_safeArray(groups.actions).concat(custom.actions).concat(fallbackFiltered.actions), 'action', classKey).map(function (card, index) { return _normalizeNativeAction(card, 'action', index); }),
      bonusActions: _dedupeActionBucket(_safeArray(groups.bonusActions).concat(custom.bonusActions).concat(fallbackFiltered.bonusActions), 'bonus', classKey).map(function (card, index) { return _normalizeNativeAction(card, 'bonus', index); }),
      reactions: _dedupeActionBucket(_safeArray(groups.reactions).concat(custom.reactions).concat(fallbackFiltered.reactions), 'reaction', classKey).map(function (card, index) { return _normalizeNativeAction(card, 'reaction', index); }),
    };
    if (isDruid) {
      const beastActions = _wildShapeActionCards(charData || {});
      if (beastActions.length) {
        out.actions = _dedupeActionBucket(_safeArray(out.actions).concat(beastActions), 'action', classKey).map(function (card, index) {
          return _normalizeNativeAction(card, 'action', index);
        });
      }
    }
    if (subclassGate) out.actions.unshift(subclassGate);
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
      remaining: card.remaining != null ? card.remaining : card.current,
      max: card.max,
      usage: card.usage || '',
      recovery: card.recovery || '',
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

  const DRUID_WILD_SHAPE_FORMS = [
    { id: 'wolf', name: 'Wolf', minLevel: 2, cr: 0.25, ac: 13, hp: 11, speed: 40, swim: 0, fly: 0, senses: 'Keen Hearing, Keen Smell', attacks: [{ name: 'Bite', attackBonus: 4, damage: '2d4+2 piercing', saveDC: 'STR DC 11 or prone', range: '5 ft', summary: 'Bite +4; on hit 2d4+2 piercing, target STR save or prone.' }] },
    { id: 'panther', name: 'Panther', minLevel: 2, cr: 0.25, ac: 12, hp: 13, speed: 50, swim: 0, fly: 0, senses: 'Keen Smell', attacks: [{ name: 'Bite', attackBonus: 4, damage: '1d6+2 piercing', range: '5 ft', summary: 'Bite +4 for 1d6+2 piercing.' }, { name: 'Claw', attackBonus: 4, damage: '1d4+2 slashing', range: '5 ft', summary: 'Claw +4 for 1d4+2 slashing.' }] },
    { id: 'brown_bear', name: 'Brown Bear', minLevel: 4, cr: 1, ac: 11, hp: 34, speed: 40, swim: 0, fly: 0, senses: 'Keen Smell', attacks: [{ name: 'Bite', attackBonus: 5, damage: '1d8+4 piercing', range: '5 ft', summary: 'Bite +5 for 1d8+4 piercing.' }, { name: 'Claws', attackBonus: 5, damage: '2d6+4 slashing', range: '5 ft', summary: 'Claws +5 for 2d6+4 slashing.' }] },
    { id: 'giant_spider', name: 'Giant Spider', minLevel: 4, cr: 1, ac: 14, hp: 26, speed: 30, swim: 0, fly: 0, senses: 'Blindsight 10 ft', attacks: [{ name: 'Bite', attackBonus: 5, damage: '1d8+3 piercing', saveDC: 'CON DC 11 vs poison', range: '5 ft', summary: 'Bite +5 for 1d8+3 piercing plus poison save.' }] },
    { id: 'saber_toothed_tiger', name: 'Saber-Toothed Tiger', minLevel: 8, cr: 2, ac: 12, hp: 52, speed: 40, swim: 0, fly: 0, senses: 'Keen Smell', attacks: [{ name: 'Bite', attackBonus: 6, damage: '1d10+5 piercing', range: '5 ft', summary: 'Bite +6 for 1d10+5 piercing.' }, { name: 'Claw', attackBonus: 6, damage: '2d6+5 slashing', range: '5 ft', summary: 'Claw +6 for 2d6+5 slashing.' }] },
  ];

  function _druidLevel(charData) {
    const classes = _safeArray(charData && charData.classes);
    const found = classes.find(function (row) {
      return String(row && row.name || '').toLowerCase().trim() === 'druid';
    });
    if (found) return _num(found.level, 0);
    const key = _classKey(charData);
    if (key === 'druid') return _num(charData && (charData.level || charData.totalLevel), 0);
    return 0;
  }

  function _druidWildShapeState(charData) {
    const mechanics = charData && charData.classMechanics && typeof charData.classMechanics === 'object' ? charData.classMechanics : {};
    const usesMax = _num(mechanics.wildShapeUses, 2) || 2;
    const spent = _num(mechanics.wildShapeSpent, 0) || 0;
    const usesLeft = Math.max(0, usesMax - spent);
    const maxCr = Number(mechanics.wildShapeMaxCR != null ? mechanics.wildShapeMaxCR : 0.25) || 0.25;
    const active = charData && charData.wildShapeState && typeof charData.wildShapeState === 'object' ? charData.wildShapeState : {};
    return {
      usesMax: usesMax,
      usesLeft: usesLeft,
      maxCr: maxCr,
      activeFormId: _firstText(active.formId, ''),
      activeFormName: _firstText(active.formName, ''),
      originalName: _firstText(active.originalName, charData && charData.name, ''),
      originalAvatarUrl: _firstText(active.originalAvatarUrl, charData && charData.avatarUrl, ''),
      originalSpeed: _num(active.originalSpeed, _num(charData && charData.speed, 30)),
      originalSenses: _firstText(active.originalSenses, charData && charData.senses, ''),
      originalHp: _num(active.originalHp, _num(charData && (charData.currentHp ?? charData.hp), 0)),
      originalMaxHp: _num(active.originalMaxHp, _num(charData && charData.maxHp, _num(charData && (charData.currentHp ?? charData.hp), 0))),
      originalAc: _num(active.originalAc, _num(charData && charData.ac, 10)),
      transformedHp: _num(active.transformedHp, _num(charData && (charData.currentHp ?? charData.hp), 0)),
      transformedMaxHp: _num(active.transformedMaxHp, _num(charData && charData.maxHp, 0)),
      transformedAc: _num(active.transformedAc, _num(charData && charData.ac, 0)),
      active: !!active.active,
    };
  }

  function _legalWildShapeForms(charData) {
    const level = _druidLevel(charData);
    const state = _druidWildShapeState(charData);
    const allowFly = level >= 8;
    const allowSwim = level >= 4;
    return DRUID_WILD_SHAPE_FORMS.filter(function (form) {
      if (!form || form.minLevel > level) return false;
      if (Number(form.cr || 0) > Number(state.maxCr || 0)) return false;
      if (!allowFly && Number(form.fly || 0) > 0) return false;
      if (!allowSwim && Number(form.swim || 0) > 0) return false;
      return true;
    });
  }

  function _wildShapeActionCards(charData) {
    const state = _druidWildShapeState(charData);
    if (!state.active) return [];
    const form = _legalWildShapeForms(charData).find(function (row) { return row.id === state.activeFormId; });
    if (!form) return [];
    return _safeArray(form.attacks).map(function (attack, idx) {
      const row = attack && typeof attack === 'object' ? attack : { summary: String(attack || '') };
      const attackBonus = _parseAttackBonusValue(row.attackBonus != null ? row.attackBonus : row.toHit);
      const saveDcText = _firstText(row.saveDC, row.saveDc, row.save, '');
      const damageText = _firstText(row.damage, row.damageText, row.effect, '');
      return {
        id: 'wild_shape_attack_' + String(form.id || idx) + '_' + String(idx),
        source: 'wild_shape_form',
        name: form.name + ' • ' + _firstText(row.name, 'Attack ' + String(idx + 1)),
        summary: _firstText(row.summary, damageText, ''),
        description: _firstText(row.summary, damageText, ''),
        actionType: 'action',
        type: 'action',
        attackBonus: attackBonus != null ? attackBonus : '',
        damage: damageText,
        damageText: damageText,
        saveDC: saveDcText,
        save: saveDcText,
        range: _firstText(row.range, '5 ft'),
        effectText: _firstText(row.summary, row.effect, ''),
        longText: [_firstText(row.summary, ''), damageText ? ('Damage: ' + damageText) : '', saveDcText ? ('Save/DC: ' + saveDcText) : ''].filter(Boolean).join('\n'),
        tags: ['Druid', 'Wild Shape', form.name],
      };
    });
  }

  function _isWildShapeAttackEntry(entry) {
    const src = String(entry && entry.source || '').toLowerCase();
    if (src === 'wild_shape_form') return true;
    const tags = _safeArray(entry && entry.tags).map(function (tag) { return String(tag || '').toLowerCase(); });
    return tags.some(function (tag) { return tag === 'wild shape' || tag === 'wild_shape_form'; });
  }

  function _setWildShapeCombatOverrides(charData, state, form) {
    if (!charData || !form) return;
    const beastCards = _wildShapeActionCards(charData);
    if (!beastCards.length) return;
    if (!charData.nativeActionCards || typeof charData.nativeActionCards !== 'object') {
      charData.nativeActionCards = { actions: [], bonusActions: [], reactions: [] };
    }
    const prior = charData.nativeActionCards;
    const mergedActions = _safeArray(prior.actions).filter(function (card) { return !_isWildShapeAttackEntry(card); }).concat(beastCards);
    charData.nativeActionCards = {
      actions: mergedActions,
      bonusActions: _safeArray(prior.bonusActions),
      reactions: _safeArray(prior.reactions),
    };
    state.originalQuickAttackCards = _cloneJsonSafe(charData.quickAttackCards, []);
    charData.quickAttackCards = beastCards.map(function (card) {
      return {
        id: card.id,
        source: 'native_action',
        name: card.name,
        summary: card.summary,
        attackBonus: card.attackBonus,
        damage: card.damage,
        damageText: card.damageText,
        range: card.range,
        note: card.longText,
      };
    });
  }

  function _restoreWildShapeCombatOverrides(charData, state) {
    if (!charData || !state) return;
    if (state.originalNativeActionCards) {
      charData.nativeActionCards = _cloneJsonSafe(state.originalNativeActionCards, { actions: [], bonusActions: [], reactions: [] });
    } else if (charData.nativeActionCards && typeof charData.nativeActionCards === 'object') {
      charData.nativeActionCards = {
        actions: _safeArray(charData.nativeActionCards.actions).filter(function (card) { return !_isWildShapeAttackEntry(card); }),
        bonusActions: _safeArray(charData.nativeActionCards.bonusActions),
        reactions: _safeArray(charData.nativeActionCards.reactions),
      };
    }
    if (state.originalQuickAttackCards) charData.quickAttackCards = _cloneJsonSafe(state.originalQuickAttackCards, []);
  }

  function _beastMasterCompanionProfile(charData) {
    const classKey = _classKey(charData);
    const subclassKey = _customSubclassKey(charData);
    if (classKey !== 'ranger' || subclassKey !== 'beast master') return null;
    const frames = {
      'primal-beast-land': { id: 'primal-beast-land', name: 'Primal Beast of the Land', tokenName: 'Beast Companion (Land)', hp: 25, ac: 13, speed: 40, size: 'medium' },
      'primal-beast-sea': { id: 'primal-beast-sea', name: 'Primal Beast of the Sea', tokenName: 'Beast Companion (Sea)', hp: 22, ac: 13, speed: 40, size: 'medium' },
      'primal-beast-sky': { id: 'primal-beast-sky', name: 'Primal Beast of the Sky', tokenName: 'Beast Companion (Sky)', hp: 20, ac: 13, speed: 10, size: 'small' },
    };
    let selectedChoice = '';
    const classes = _safeArray(charData && charData.classes);
    classes.forEach(function (cl) {
      const clSubclass = _firstText(cl && cl.subclass, cl && cl.subclassName, '').toLowerCase().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim();
      if (clSubclass !== 'beast master') return;
      const picks = _safeArray(cl && cl.selectedFeatures);
      picks.forEach(function (pick) {
        const pickId = String(pick && pick.id || '').toLowerCase();
        if (pickId !== 'beast-master-rangers-companion') return;
        selectedChoice = _firstText(pick && pick.selectedChoice, pick && pick.choiceId, '').toLowerCase();
      });
    });
    if (!selectedChoice) {
      const features = _featureSourceEntries(charData);
      const names = features.map(function (entry) { return String(_firstText(entry && entry.name, entry && entry.label, '')).toLowerCase(); });
      if (names.some(function (name) { return name.indexOf('primal beast') >= 0 && name.indexOf('land') >= 0; })) selectedChoice = 'primal-beast-land';
      else if (names.some(function (name) { return name.indexOf('primal beast') >= 0 && name.indexOf('sea') >= 0; })) selectedChoice = 'primal-beast-sea';
      else if (names.some(function (name) { return name.indexOf('primal beast') >= 0 && name.indexOf('sky') >= 0; })) selectedChoice = 'primal-beast-sky';
    }
    const picked = frames[selectedChoice] || frames['primal-beast-land'];
    return {
      id: picked.id,
      name: picked.name,
      tokenName: picked.tokenName,
      hp: picked.hp,
      maxHp: picked.hp,
      ac: picked.ac,
      speed: picked.speed,
      size: picked.size,
      source: 'beast_master_sheet',
    };
  }

  function _renderBeastMasterCompanionControls(companion) {
    if (!companion) return '';
    return `<div class="cs-combat-callout-grid">
      <div class="cs-combat-callout">
        <div class="cs-combat-callout-title">Beast Master Companion</div>
        <div class="cs-combat-callout-copy">${_esc(companion.name)} is selected on this sheet. Deploy it as a real in-session token when needed.</div>
      </div>
      <div class="cs-combat-callout muted">
        <div class="cs-combat-callout-title">Companion deployment</div>
        <div class="cs-combat-callout-copy">Frame: ${_esc(companion.name)} • HP ${_esc(String(companion.hp))} • AC ${_esc(String(companion.ac))} • Speed ${_esc(String(companion.speed))} ft</div>
        <div style="margin-top:.5rem;display:flex;gap:.4rem;flex-wrap:wrap;">
          <button type="button" class="cs-launch-btn" data-beast-master-companion-spawn="1">Place companion token</button>
        </div>
      </div>
    </div>`;
  }

  function _renderDruidWildShapeControls(charData) {
    if (_classKey(charData) !== 'druid') return '';
    const state = _druidWildShapeState(charData);
    const forms = _legalWildShapeForms(charData);
    const selected = String(charData && charData.wildShapeSelection || '');
    return `<div class="cs-combat-callout-grid">
      <div class="cs-combat-callout">
        <div class="cs-combat-callout-title">Wild Shape</div>
        <div class="cs-combat-callout-copy">Uses ${_esc(String(state.usesLeft))}/${_esc(String(state.usesMax))} • Max CR ${_esc(String(state.maxCr))}${state.active ? ` • Active form: ${_esc(state.activeFormName || state.activeFormId)}` : ''}</div>
      </div>
      <div class="cs-combat-callout muted">
        <div class="cs-combat-callout-title">Form picker</div>
        <div style="display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;">
          <select data-druid-wild-shape-select="1" style="background:#0f1716;color:#defcf8;border:1px solid rgba(0,229,204,.28);border-radius:8px;padding:6px 8px;min-width:220px;">
            <option value="">Choose legal form…</option>
            ${forms.map(function (form) { return `<option value="${_esc(form.id)}" ${selected === form.id ? 'selected' : ''}>${_esc(form.name)} (CR ${_esc(String(form.cr))})</option>`; }).join('')}
          </select>
          <button type="button" class="cs-launch-btn" data-druid-wild-shape-apply="1" ${state.usesLeft <= 0 || !forms.length ? 'disabled' : ''}>Transform</button>
          <button type="button" class="cs-launch-btn muted" data-druid-wild-shape-revert="1" ${state.active ? '' : 'disabled'}>Revert</button>
        </div>
      </div>
    </div>`;
  }

  function _resolveOwnedTokenId(charData) {
    const direct = _firstText(charData && charData.tokenId, charData && charData.token_id, '');
    if (direct) return direct;
    const userId = _firstText(global && global.USER_ID, '');
    const pool = global && typeof global.tokens === 'object' ? Object.values(global.tokens) : [];
    const owned = pool.find(function (token) { return token && String(token.owner_id || '') === String(userId || ''); });
    return _firstText(owned && owned.id, '');
  }

  function _broadcastWildShapeTokenUpdate(charData, state) {
    if (typeof global.sendWS !== 'function') return;
    const tokenId = _resolveOwnedTokenId(charData);
    if (!tokenId) return;
    const formName = _firstText(state && state.activeFormName, '');
    const nextName = formName ? `${_firstText(state && state.originalName, charData && charData.name, 'Druid')} (${formName})` : _firstText(state && state.originalName, charData && charData.name, 'Druid');
    try {
      global.sendWS({
        type: 'token_hp_update',
        payload: {
          token_id: tokenId,
          hp: _num(charData && (charData.currentHp ?? charData.hp), 0),
          max_hp: _num(charData && charData.maxHp, _num(charData && (charData.currentHp ?? charData.hp), 0)),
        },
      });
      global.sendWS({
        type: 'token_edit',
        payload: {
          token_id: tokenId,
          name: nextName,
          hp: _num(charData && (charData.currentHp ?? charData.hp), 0),
          maxHp: _num(charData && charData.maxHp, _num(charData && (charData.currentHp ?? charData.hp), 0)),
          tempHp: _num(charData && charData.tempHp, 0),
          ac: _num(charData && charData.ac, 0),
          speed: _num(charData && charData.speed, 0),
          senses: _firstText(charData && charData.senses, ''),
          image_url: _firstText(charData && charData.avatarUrl, ''),
          wild_shape: state || {},
        },
      });
    } catch (_) {}
  }

  function _bindDetails(container, model) {
    container.addEventListener('click', function (e) {
      const wildShapeApply = e.target.closest('[data-druid-wild-shape-apply]');
      if (wildShapeApply) {
        e.preventDefault();
        const charData = model && model.charData ? model.charData : {};
        const selectedFormId = String(charData && charData.wildShapeSelection || '');
        const selectedForm = _legalWildShapeForms(charData).find(function (row) { return row.id === selectedFormId; });
        const state = _druidWildShapeState(charData);
        if (!selectedForm || state.usesLeft <= 0) return;
        const baseCurrentHp = _num(charData && (charData.currentHp ?? charData.hp), 0);
        const baseMaxHp = _num(charData && charData.maxHp, baseCurrentHp);
        const baseTempHp = _num(charData && charData.tempHp, 0);
        const baseAc = _num(charData && charData.ac, 10);
        const nextState = {
          active: true,
          formId: selectedForm.id,
          formName: selectedForm.name,
          originalName: state.originalName || _firstText(charData && charData.name, ''),
          originalAvatarUrl: state.originalAvatarUrl || _firstText(charData && charData.avatarUrl, ''),
          originalSpeed: state.originalSpeed || _num(charData && charData.speed, 30),
          originalSenses: state.originalSenses || _firstText(charData && charData.senses, ''),
          originalHp: state.originalHp || baseCurrentHp,
          originalMaxHp: state.originalMaxHp || baseMaxHp,
          originalTempHp: state.originalTempHp || baseTempHp,
          originalAc: state.originalAc || baseAc,
          originalNativeActionCards: state.originalNativeActionCards || _cloneJsonSafe(charData && charData.nativeActionCards, { actions: [], bonusActions: [], reactions: [] }),
          originalQuickAttackCards: state.originalQuickAttackCards || _cloneJsonSafe(charData && charData.quickAttackCards, []),
          transformedHp: _num(selectedForm.hp, 1),
          transformedMaxHp: _num(selectedForm.hp, 1),
          transformedAc: _num(selectedForm.ac, baseAc),
          transformedTempHp: 0,
          transformedCombatProfile: {
            formId: selectedForm.id,
            formName: selectedForm.name,
            ac: _num(selectedForm.ac, baseAc),
            hp: _num(selectedForm.hp, 1),
            maxHp: _num(selectedForm.hp, 1),
            tempHp: 0,
            speed: _num(selectedForm.speed, charData.speed || 30),
            senses: _firstText(selectedForm.senses, charData.senses, ''),
          },
        };
        if (!charData.classMechanics || typeof charData.classMechanics !== 'object') charData.classMechanics = {};
        charData.classMechanics.wildShapeSpent = _num(charData.classMechanics.wildShapeSpent, 0) + 1;
        charData.wildShapeState = nextState;
        charData.speed = _num(selectedForm.speed, charData.speed || 30);
        charData.senses = _firstText(selectedForm.senses, charData.senses, '');
        charData.ac = _num(selectedForm.ac, charData.ac || 10);
        charData.maxHp = _num(selectedForm.hp, charData.maxHp || 1);
        charData.currentHp = _num(selectedForm.hp, charData.currentHp || charData.hp || 1);
        charData.tempHp = 0;
        charData.hp = charData.currentHp;
        _setWildShapeCombatOverrides(charData, nextState, selectedForm);
        if (global._charSheet && typeof global._charSheet === 'object') Object.assign(global._charSheet, charData);
        _broadcastWildShapeTokenUpdate(charData, nextState);
        if (typeof global.requestCharacterBookOverviewRender === 'function') global.requestCharacterBookOverviewRender('wild-shape-apply');
        if (typeof global.renderCharSheet === 'function') global.renderCharSheet();
        if (typeof model.rerender === 'function') model.rerender();
        return;
      }
      const wildShapeRevert = e.target.closest('[data-druid-wild-shape-revert]');
      if (wildShapeRevert) {
        e.preventDefault();
        const charData = model && model.charData ? model.charData : {};
        const state = _druidWildShapeState(charData);
        charData.wildShapeState = {
          active: false,
          formId: '',
          formName: '',
          originalName: state.originalName,
          originalAvatarUrl: state.originalAvatarUrl,
          originalSpeed: state.originalSpeed,
          originalSenses: state.originalSenses,
          originalHp: state.originalHp,
          originalMaxHp: state.originalMaxHp,
          originalTempHp: state.originalTempHp,
          originalAc: state.originalAc,
          originalNativeActionCards: state.originalNativeActionCards,
          originalQuickAttackCards: state.originalQuickAttackCards,
          transformedHp: state.transformedHp,
          transformedMaxHp: state.transformedMaxHp,
          transformedAc: state.transformedAc,
          transformedTempHp: state.transformedTempHp,
          transformedCombatProfile: state.transformedCombatProfile,
        };
        charData.speed = state.originalSpeed || _num(charData.speed, 30);
        charData.senses = state.originalSenses || _firstText(charData.senses, '');
        charData.ac = state.originalAc || _num(charData.ac, 10);
        charData.maxHp = state.originalMaxHp || _num(charData.maxHp, 1);
        charData.currentHp = state.originalHp || _num(charData.currentHp ?? charData.hp, 1);
        charData.tempHp = _num(state.originalTempHp, _num(charData.tempHp, 0));
        charData.hp = charData.currentHp;
        _restoreWildShapeCombatOverrides(charData, state);
        if (global._charSheet && typeof global._charSheet === 'object') Object.assign(global._charSheet, charData);
        _broadcastWildShapeTokenUpdate(charData, charData.wildShapeState);
        if (typeof global.requestCharacterBookOverviewRender === 'function') global.requestCharacterBookOverviewRender('wild-shape-revert');
        if (typeof global.renderCharSheet === 'function') global.renderCharSheet();
        if (typeof model.rerender === 'function') model.rerender();
        return;
      }
      const useBtn = e.target.closest('[data-action-use]');
      if (useBtn) {
        e.preventDefault();
        e.stopPropagation();
        const actionId = String(useBtn.getAttribute('data-action-use') || '');
        const actionSource = String(useBtn.getAttribute('data-action-source') || '');
        const all = [].concat(model.quickAttacks, model.itemActions, model.native.actions, model.native.bonusActions, model.native.reactions, model.textAttacks, model.summonActions || []);
        const action = all.find(function (entry) { return String(entry && entry.id || '') === actionId || String(entry && entry.name || '').toLowerCase() === actionId.toLowerCase(); });
        if (actionSource === 'summon_action') {
          const action = _safeArray(model && model.summonActions).find(function (entry) { return String(entry && entry.id || '') === actionId; });
          const summonMeta = action && action.summonAction && typeof action.summonAction === 'object' ? action.summonAction : {};
          const label = _firstText(action && action.name, 'Summon action');
          const sourceClassId = String((summonMeta.sourceClassId || '').toLowerCase());
          const sourceSubclassId = String((summonMeta.sourceSubclassId || '').toLowerCase());
          const isBeastMaster = sourceClassId === 'ranger' && sourceSubclassId === 'beast-master';
          const isWarlockChain = sourceClassId === 'warlock' && String(summonMeta.summonGroupId || '').toLowerCase() === 'warlock-pact-chain-familiar';
          const isTinkerMechanist = sourceClassId === 'tinker' && sourceSubclassId === 'mechanist' && String(summonMeta.summonTemplateId || '').toLowerCase() === 'tinker-mechanist-companion-frame';
          if (!isBeastMaster && !isWarlockChain && !isTinkerMechanist) {
            if (typeof global.showToast === 'function') global.showToast(`${label}: runtime path is not live for this class yet.`);
            return;
          }
          const variants = _safeArray(summonMeta.variants).map(function (entry) {
            return {
              id: _firstText(entry && entry.id, '').toLowerCase(),
              name: _firstText(entry && entry.displayName, entry && entry.id, ''),
            };
          }).filter(function (entry) { return !!entry.id; });
          const variantSelect = container.querySelector(`[data-summon-variant-for="${actionId.replace(/"/g, '\\"')}"]`);
          let selectedVariantId = _firstText(variantSelect && variantSelect.value, summonMeta.selectedVariantId, '').toLowerCase();
          if (!selectedVariantId && variants.length === 1) selectedVariantId = String(variants[0].id || '').toLowerCase();
          if (!selectedVariantId && variants.length > 1) {
            const variantMenu = variants.map(function (v, i) { return `${i + 1}. ${v.name}`; }).join('\n');
            const answer = (typeof global.prompt === 'function')
              ? String(global.prompt(`Choose summon variant:\n${variantMenu}\n\nType number or variant id:`, '1') || '').trim()
              : '';
            if (answer) {
              const byIndex = parseInt(answer, 10);
              if (Number.isFinite(byIndex) && byIndex >= 1 && byIndex <= variants.length) {
                selectedVariantId = String(variants[byIndex - 1].id || '').toLowerCase();
              } else {
                const normalized = answer.toLowerCase();
                const found = variants.find(function (v) { return v.id === normalized || String(v.name || '').toLowerCase() === normalized; });
                selectedVariantId = found ? String(found.id || '').toLowerCase() : '';
              }
            }
            if (!selectedVariantId && typeof global.showToast === 'function') {
              global.showToast(`${label}: summon variant selection was cancelled.`);
              return;
            }
          }
          if (!selectedVariantId) {
            if (typeof global.showToast === 'function') global.showToast(`${label}: no summon variant is configured.`);
            return;
          }
          if (typeof global.sendWS === 'function') {
            global.sendWS({
              type: 'summon_runtime_request',
              payload: {
                action_id: actionId,
                profile_id: _firstText(model && model.charData && model.charData.id, model && model.charData && model.charData.charId, ''),
                summon_group_id: _firstText(summonMeta.summonGroupId, ''),
                summon_template_id: _firstText(summonMeta.summonTemplateId, selectedVariantId),
                selected_variant: selectedVariantId,
              },
            });
            if (typeof global.showToast === 'function') {
              const variantName = (variants.find(function (v) { return v.id === selectedVariantId; }) || {}).name || summonMeta.selectedVariantName || selectedVariantId;
              global.showToast(`Summoning ${variantName}...`);
            }
          } else if (typeof global.showToast === 'function') {
            global.showToast(`${label}: websocket runtime unavailable.`);
          }
          return;
        }
        _pulseRowFromTrigger(useBtn);
        if (typeof global.playerUseAction === 'function') {
          let resolvedActionId = actionId;
          const weaponLike = /^(weapon|equip_only|system_unarmed|attack)$/i.test(actionSource);
          if (weaponLike && typeof global._getUnifiedQuickAttackCards === 'function') {
            const cards = _safeArray(global._getUnifiedQuickAttackCards());
            const hasDirect = cards.some(function (card) { return String(card && card.id || '') === resolvedActionId; });
            if (!hasDirect) {
              const byMapped = action && _firstText(action.combatCardId, action.name, '');
              if (byMapped) resolvedActionId = byMapped;
            }
          }
          global.playerUseAction(actionSource, resolvedActionId);
        } else if (typeof global.showToast === 'function') {
          const label = action && action.name ? action.name : 'Action';
          const cost = action && (action.resourceSummary || action.resourceName) ? ` — ${action.resourceSummary || action.resourceName}` : '';
          global.showToast(`${label} triggered${cost}`);
        }
        return;
      }
      const summonFocusBtn = e.target.closest('[data-summon-focus-token]');
      if (summonFocusBtn) {
        e.preventDefault();
        e.stopPropagation();
        const tokenId = String(summonFocusBtn.getAttribute('data-summon-focus-token') || '');
        if (tokenId && typeof global.focusSummonTokenById === 'function') {
          global.focusSummonTokenById(tokenId);
        } else if (typeof global.showToast === 'function') {
          global.showToast('Summon token is missing on this map.');
        }
        return;
      }
      const summonInspectBtn = e.target.closest('[data-summon-inspect-token]');
      if (summonInspectBtn) {
        e.preventDefault();
        e.stopPropagation();
        const tokenId = String(summonInspectBtn.getAttribute('data-summon-inspect-token') || '');
        if (tokenId && typeof global.inspectSummonTokenById === 'function') {
          global.inspectSummonTokenById(tokenId);
        } else if (typeof global.showToast === 'function') {
          global.showToast('Summon token is missing on this map.');
        }
        return;
      }
      const dismissBtn = e.target.closest('[data-action-dismiss]');
      if (dismissBtn) {
        e.preventDefault();
        e.stopPropagation();
        const actionId = String(dismissBtn.getAttribute('data-action-dismiss') || '');
        const action = _safeArray(model && model.summonActions).find(function (entry) { return String(entry && entry.id || '') === actionId; });
        const summonMeta = action && action.summonAction && typeof action.summonAction === 'object' ? action.summonAction : {};
        const activeRows = _safeArray(summonMeta.activeSummons).filter(function (row) { return row && typeof row === 'object'; });
        if (!activeRows.length) {
          if (typeof global.showToast === 'function') global.showToast('No active summon to dismiss.');
          return;
        }
        let selected = activeRows[0];
        if (activeRows.length > 1 && typeof global.prompt === 'function') {
          const menu = activeRows.map(function (row, i) { return `${i + 1}. ${_firstText(row.variantName, row.variantId, 'Summon')} (${_firstText(row.status, 'active')})`; }).join('\n');
          const answer = String(global.prompt(`Choose summon to dismiss:\n${menu}\n\nType number or active id/token id:`, '1') || '').trim();
          const byIndex = parseInt(answer, 10);
          if (Number.isFinite(byIndex) && byIndex >= 1 && byIndex <= activeRows.length) {
            selected = activeRows[byIndex - 1];
          } else if (answer) {
            const byId = activeRows.find(function (row) { return String(row.id || '') === answer || String(row.tokenId || '') === answer; });
            selected = byId || selected;
          }
        }
        if (typeof global.sendWS === 'function') {
          global.sendWS({
            type: 'summon_runtime_dismiss',
            payload: {
              action_id: actionId,
              profile_id: _firstText(model && model.charData && model.charData.id, model && model.charData && model.charData.charId, ''),
              summon_group_id: _firstText(summonMeta.summonGroupId, ''),
              source_feature_id: _firstText(summonMeta.sourceFeatureId, ''),
              active_id: _firstText(selected && selected.id, ''),
              token_id: _firstText(selected && selected.tokenId, ''),
            },
          });
          if (typeof global.showToast === 'function') global.showToast(`Dismissing ${_firstText(selected && selected.variantName, selected && selected.variantId, 'summon')}...`);
        } else if (typeof global.showToast === 'function') {
          global.showToast('Dismiss failed: websocket runtime unavailable.');
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
      const companionSpawnBtn = e.target.closest('[data-beast-master-companion-spawn]');
      if (companionSpawnBtn) {
        e.preventDefault();
        e.stopPropagation();
        if (model.beastMasterCompanion && typeof global.placeBeastMasterCompanionToken === 'function') {
          global.placeBeastMasterCompanionToken(model.beastMasterCompanion);
        } else if (typeof global.showToast === 'function') {
          global.showToast('Companion token deployment is unavailable in this runtime.');
        }
        return;
      }
      const actionRow = e.target.closest('.cs-action-row');
      if (actionRow) {
        const name = String(actionRow.getAttribute('data-action-name') || '').toLowerCase();
        const all = [].concat(model.quickAttacks, model.itemActions, model.native.actions, model.native.bonusActions, model.native.reactions, model.textAttacks, model.summonActions || []);
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
    container.addEventListener('change', function (e) {
      const selector = e.target.closest('[data-druid-wild-shape-select]');
      if (!selector) return;
      if (!model || !model.charData) return;
      model.charData.wildShapeSelection = String(selector.value || '');
      if (global._charSheet && typeof global._charSheet === 'object') global._charSheet.wildShapeSelection = model.charData.wildShapeSelection;
    });
  }

  function initActionsTab(container, charData) {
    if (!container) return;

    const native = _nativeActionGroups(charData || {});
    const isWildShapeActive = !!_druidWildShapeState(charData || {}).active;
    const quickAttacks = (function () {
      if (isWildShapeActive) {
        const transformed = _safeArray(native.actions).filter(function (entry) { return _isWildShapeAttackEntry(entry); });
        if (transformed.length) {
          return transformed.map(function (card) {
            return {
              id: card.id,
              source: 'native_action',
              name: card.name,
              desc: _firstText(card.desc, card.description, ''),
              description: _firstText(card.description, card.desc, ''),
              economy: ['action'],
              icon: '🐾',
              attackBonus: card.attackBonus,
              damage: _firstText(card.damage, card.damageText, ''),
              range: card.range || '5 ft',
              saveDC: _firstText(card.saveDC, card.hitDc, card.save, ''),
              tags: ['Wild Shape', 'Transformed'],
              longText: card.longText || '',
            };
          });
        }
      }
      const fromQuick = _buildQuickAttackCards(charData || {});
      const fromInventory = _inventoryWeaponCards(charData || {});
      const combined = [];
      const seen = new Set();
      function push(card) {
        const key = String(card && (card.id || card.name) || '').toLowerCase();
        if (!key || seen.has(key)) return;
        seen.add(key);
        combined.push(card);
      }
      fromQuick.forEach(push);
      fromInventory.forEach(push);
      if (!combined.some(function (entry) { return String(entry && entry.source || '').toLowerCase() === 'system_unarmed' || String(entry && entry.name || '').toLowerCase() === 'unarmed strike'; })) {
        push(_unarmedStrikeCard(charData || {}));
      }
      return combined;
    }());
    const itemActions = _buildItemActionCards();
    const nativeActionsForSection = isWildShapeActive
      ? _safeArray(native.actions).filter(function (entry) { return !_isWildShapeAttackEntry(entry); })
      : _safeArray(native.actions);
    const resources = _resourceRows(charData || {});
    const textAttacks = _parseTextAttacks(charData || {});
    const summonActions = _summonActionRows(charData || {});
    const beastMasterCompanion = _beastMasterCompanionProfile(charData || {});
    const selectedTarget = charData && charData.selectedTarget ? charData.selectedTarget : null;
    const concentration = _firstText(charData && charData.activeConcentration, '');
    const totalActions = quickAttacks.length + itemActions.length + native.actions.length + native.bonusActions.length + native.reactions.length + textAttacks.length + summonActions.length;

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
      ${_renderDruidWildShapeControls(charData || {})}
      ${_renderBeastMasterCompanionControls(beastMasterCompanion)}
      ${_renderSection('Quick Attacks', quickAttacks, { emptyLabel: 'No quick attack cards are loaded yet.' })}
      ${_renderSection('Imported / Legacy Attack Lines', textAttacks, { emptyLabel: 'No imported attack lines detected.' })}
      ${_renderSection('Item Actions', itemActions, { emptyLabel: 'No usable item actions are loaded yet.' })}
      ${_renderSummonManager(summonActions)}
      ${_renderSection('Summon / Deploy Actions', summonActions, { emptyLabel: 'No summon or deploy actions are unlocked for this character.' })}
      ${_renderSection('Native Actions', nativeActionsForSection, { emptyLabel: isWildShapeActive ? 'Wild Shape attacks are currently driving your attack surface.' : 'No structured main actions are loaded yet.' })}
      ${_renderSection('Bonus Actions', native.bonusActions, { emptyLabel: 'No structured bonus actions are loaded yet.' })}
      ${_renderSection('Reactions', native.reactions, { emptyLabel: 'No structured reactions are loaded yet.' })}
      ${_renderResourceSection(resources)}
    `;

    _bindDetails(container, {
      quickAttacks, itemActions, native, resources, textAttacks, summonActions, beastMasterCompanion,
      charData: charData || {},
      rerender: function rerenderActions() { initActionsTab(container, charData); }
    });
  }

  global.ActionsTab = { initActionsTab };
}(window));
