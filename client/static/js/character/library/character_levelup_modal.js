(function initCharacterLevelupModal(global) {
  const MODAL_ID = 'character-levelup-modal';
  const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'];


  const CLASS_LEVELUP_GUIDES = {
    barbarian: {
      title: 'Barbarian Level-Up Focus',
      summary: 'Check how your Rage package improves: survivability, damage pressure, and any subclass rage riders should all be obvious before you confirm.',
      checks: ['Rage count or Rage rider change', 'Weapon or damage pressure feature', 'Subclass Rage interaction', 'Durability spike or movement gain'],
    },
    bard: {
      title: 'Bard Level-Up Focus',
      summary: 'Bard level-ups should show support growth clearly: inspiration scaling, subclass flourishes, and spell access should all read like real upgrades.',
      checks: ['Bardic Inspiration scaling', 'New support/control feature', 'Spell access or Magical Secrets style unlock', 'Subclass performance identity'],
    },
    cleric: {
      title: 'Cleric Level-Up Focus',
      summary: 'Cleric level-ups should make divine growth obvious: Channel Divinity, domain features, and new prepared spell power should all stand out immediately.',
      checks: ['Channel Divinity or uses', 'Domain feature or domain spell unlock', 'Prepared spell growth', 'Defensive or support spike'],
    },
    druid: {
      title: 'Druid Level-Up Focus',
      summary: 'Druid level-ups should read like stronger primal versatility: forms, summons, spell access, and circle identity all need to be easy to spot.',
      checks: ['Wild Shape or form-related change', 'Circle feature or circle spell unlock', 'Prepared spell growth', 'Battlefield control or support jump'],
    },
    fighter: {
      title: 'Fighter Level-Up Focus',
      summary: 'Fighter level-ups should make combat rhythm clearer: extra attacks, tactical resources, and subclass combat tools should be easy to compare before applying.',
      checks: ['Action economy upgrade', 'Subclass combat option', 'Resource refresh or scaling', 'Weapon/attack flow still matches build'],
    },
    monk: {
      title: 'Monk Level-Up Focus',
      summary: 'Monk level-ups should show mobility and discipline gains clearly: point economy, bonus-action tools, and subclass techniques should read cleanly.',
      checks: ['Discipline/Focus point change', 'Movement or defense gain', 'Bonus-action pressure tool', 'Subclass technique upgrade'],
    },
    paladin: {
      title: 'Paladin Level-Up Focus',
      summary: 'Paladin level-ups should make oath power and frontline support obvious: smite pressure, aura growth, and oath spells should be easy to read.',
      checks: ['Oath feature or oath spell unlock', 'Lay on Hands / Channel / support pool', 'Frontline damage or aura gain', 'Prepared spell growth'],
    },
    ranger: {
      title: 'Ranger Level-Up Focus',
      summary: 'Ranger level-ups should show tracking, pressure, and exploration gains together so the player can see both combat and utility growth at a glance.',
      checks: ['Mark/hunt feature change', 'Subclass tactic or companion gain', 'Spell access growth', 'Movement or exploration upgrade'],
    },
    rogue: {
      title: 'Rogue Level-Up Focus',
      summary: 'Rogue level-ups should make precision play clearer: Sneak Attack growth, evasive tools, and subclass tricks should all be easy to scan.',
      checks: ['Sneak Attack scaling', 'Cunning / survival tool', 'Subclass trick or rider', 'Action economy or reaction change'],
    },
    sorcerer: {
      title: 'Sorcerer Level-Up Focus',
      summary: 'Sorcerer level-ups should read like deeper spell expression: sorcery points, metamagic, subclass magic, and new spell access need to be obvious.',
      checks: ['Sorcery Point change', 'Metamagic or spell-expression gain', 'Subclass magic feature', 'Spell access growth'],
    },
    warlock: {
      title: 'Warlock Level-Up Focus',
      summary: 'Warlock level-ups should highlight pact identity, patron power, and invocation-style choices so players can immediately see what changed.',
      checks: ['Pact or patron feature', 'Invocation-style choice or passive', 'Spell slot tier / spell access', 'Short-rest resource identity'],
    },
    wizard: {
      title: 'Wizard Level-Up Focus',
      summary: 'Wizard level-ups should feel like expanding a real spellbook: new spells, subclass school identity, and utility depth should all read clearly.',
      checks: ['Spellbook additions', 'Subclass school feature', 'Prepared spell growth', 'Ritual or utility spike'],
    },
    tinker: {
      title: 'Tinker Level-Up Focus',
      summary: 'Tinker level-ups should feel like upgrading a real field kit: check rig upgrades, Gadget Charge-facing features, subclass devices, and specialty spell access together.',
      checks: ['Prototype Rig / rig upgrades', 'Gadget Charges or charge spenders', 'Subclass device package', 'Specialty spell unlocks'],
    },
    pirate: {
      title: 'Pirate Level-Up Focus',
      summary: 'Pirate level-ups should feel like sharpening a fighting style: Swagger Dice growth, dirty-trick pressure, movement tools, and subclass swagger all need to read clearly.',
      checks: ['Swagger Dice scaling', 'Bonus-action / reaction pressure tools', 'Subclass identity feature', 'Attack flow still matches new tricks'],
    },
  };

  function classGuide(preview) {
    const key = String(preview && (preview.classId || preview.className) || '').toLowerCase();
    return CLASS_LEVELUP_GUIDES[key] || null;
  }


  const CLASS_CHOICE_COACH = {
    barbarian: { title: 'Barbarian Choice Coach', bullets: ['Look for Rage-facing upgrades first.', 'Check whether the new level changes how often you are in melee.', 'If a subclass option appears, pick the one that matches your usual turn plan.'] },
    bard: { title: 'Bard Choice Coach', bullets: ['Prioritize options that improve support clarity at the table.', 'Check whether this level changes Inspiration, control, or Magical Secrets style access.', 'Pick features and spells that fit how you already help the party.'] },
    cleric: { title: 'Cleric Choice Coach', bullets: ['Check domain identity first, then prepared spell flexibility.', 'If you gain divine resources, note whether they refresh on a short or long rest.', 'Make sure support, defense, and offensive miracles are all still represented.'] },
    druid: { title: 'Druid Choice Coach', bullets: ['Decide whether this level is pushing forms, control, or support.', 'Read any circle feature for both combat use and exploration value.', 'Prepared spell changes matter more than raw spell count for Druids.'] },
    fighter: { title: 'Fighter Choice Coach', bullets: ['Start with action economy: attacks, reactions, and resource refreshes.', 'If a subclass choice appears, match it to your real combat rhythm.', 'Anything tactical should be easy to spot before you confirm.'] },
    monk: { title: 'Monk Choice Coach', bullets: ['Check mobility, defense, and point-spending together.', 'Subclass techniques should be readable as real turn options, not just lore.', 'If this level changes bonus-action flow, make sure that stands out.'] },
    paladin: { title: 'Paladin Choice Coach', bullets: ['Look at oath identity, support tools, and frontline pressure together.', 'Aura and smite-facing changes should be easy to compare before applying.', 'Prepared spell growth matters, but role clarity matters more.'] },
    ranger: { title: 'Ranger Choice Coach', bullets: ['Check how the new level changes tracking, pressure, and movement.', 'If you have a companion or subclass tactic, make sure it is still easy to read.', 'Spell picks should support your actual hunting or skirmish plan.'] },
    rogue: { title: 'Rogue Choice Coach', bullets: ['Sneak Attack play should stay obvious after this level-up.', 'Prioritize anything that improves setup, escape, or precision.', 'Subclass tricks should read as usable table tools, not vague flavor.'] },
    sorcerer: { title: 'Sorcerer Choice Coach', bullets: ['Think in terms of spell expression, not just raw spell count.', 'Metamagic-facing levels should clearly tell you what new tricks you can pull off.', 'Choose spells that pair well with your subclass magic and point economy.'] },
    warlock: { title: 'Warlock Choice Coach', bullets: ['Check patron identity, pact tools, and short-rest rhythm together.', 'Invocation-style choices should be compared by real play value, not only theme.', 'Spell picks should respect how few slots you have and how hard they hit.'] },
    wizard: { title: 'Wizard Choice Coach', bullets: ['Treat this like expanding a real spellbook.', 'Utility, rituals, and school identity should all be visible before you confirm.', 'New spells should fill actual holes in your prepared options.'] },
    tinker: { title: 'Tinker Choice Coach', bullets: ['Look for rig growth, charge spenders, and subclass devices together.', 'If a choice changes deployment or support tools, make that your priority.', 'Specialty spells should reinforce your kit, not distract from it.'] },
    pirate: { title: 'Pirate Choice Coach', bullets: ['Check swagger flow, movement tricks, and pressure tools together.', 'Subclass choices should sharpen your fighting style, not blur it.', 'If a level changes bonus-action or reaction pressure, that should be obvious.'] },
  };

  const CHOICE_PROFILE_OVERRIDES = {
    'life domain': { role: 'Divine healer', fantasy: 'Anchor the party with stronger recovery and protection.', now: 'Best when you want your cleric turns to feel reliable, protective, and restorative.', later: 'Later domain features deepen healing efficiency and defensive support.' },
    'light domain': { role: 'Radiant blaster', fantasy: 'Channel sunlight, fire, and radiant pressure.', now: 'Best when you want spell turns that clear space, punish swarms, and feel dramatic.', later: 'Later features lean harder into burst damage, vision control, and radiant pressure.' },
    'trickery domain': { role: 'Illusion support', fantasy: 'Use misdirection, stealth, and divine deceit to set up the party.', now: 'Best when you want mobility, illusion utility, and slippery support play.', later: 'Later features reward clever positioning and duplicate-based disruption.' },
    'war domain': { role: 'Battle priest', fantasy: 'Fight on the front line with divine aggression and martial support.', now: 'Best when you want weapon pressure and a more commanding frontline presence.', later: 'Later features reinforce battlefield authority and direct pressure.' },
    'battle master': { role: 'Tactical fighter', fantasy: 'Turn weapon mastery into precision, control, and maneuver play.', now: 'Best when you want a toolkit of active combat decisions instead of passive power.', later: 'Later maneuver picks and superiority growth reward planning your round.' },
    battlemaster: { role: 'Tactical fighter', fantasy: 'Turn weapon mastery into precision, control, and maneuver play.', now: 'Best when you want a toolkit of active combat decisions instead of passive power.', later: 'Later maneuver picks and superiority growth reward planning your round.' },
    'champion': { role: 'Pure martial striker', fantasy: 'Keep the fighter simple, durable, and immediately effective.', now: 'Best when you want a straightforward power curve with fewer moving parts.', later: 'Later features keep sharpening athletic dominance and dependable attacks.' },
    'eldritch knight': { role: 'Weapon mage', fantasy: 'Blend weapon routine with controlled arcane support.', now: 'Best when you want a fighter core with selective magical reach and defense.', later: 'Later features reward managing both spell timing and weapon pressure.' },
    'eldritch-knight': { role: 'Weapon mage', fantasy: 'Blend weapon routine with controlled arcane support.', now: 'Best when you want a fighter core with selective magical reach and defense.', later: 'Later features reward managing both spell timing and weapon pressure.' },
    'psi warrior': { role: 'Psychic controller', fantasy: 'Layer telekinetic force over martial turns.', now: 'Best when you want protective utility, force movement, and psionic style.', later: 'Later features deepen psi economy and battlefield manipulation.' },
    'abjurer': { role: 'Protective wizard', fantasy: 'Shape your spellbook around wards, denial, and magical resilience.', now: 'Best when you want your wizard to feel safer and more defensive.', later: 'Later features reinforce ward value and anti-magic identity.' },
    'diviner': { role: 'Fate wizard', fantasy: 'Change outcomes before they happen and steer the story through foresight.', now: 'Best when you want predictive control and strong dice influence.', later: 'Later features keep rewarding smart timing and encounter reading.' },
    'evoker': { role: 'Blasting wizard', fantasy: 'Turn your spellbook into a cleaner, harder-hitting damage engine.', now: 'Best when you want straightforward area damage without losing party safety.', later: 'Later features intensify spell damage and battlefield clearing.' },
    'illusionist': { role: 'Misdirection wizard', fantasy: 'Control perception, positioning, and enemy certainty.', now: 'Best when you want clever control and non-direct solutions.', later: 'Later features reward creativity, setup, and illusion value.' },
    'oath of devotion': { role: 'Holy guardian', fantasy: 'Be a classic paladin of conviction, defense, and righteous steadiness.', now: 'Best when you want a clear protector fantasy with dependable support.', later: 'Later oath features deepen sacred defense and party stability.' },
    'oath of the ancients': { role: 'Radiant warden', fantasy: 'Blend nature, hope, and anti-darkness protection.', now: 'Best when you want resilience and support with a brighter magical identity.', later: 'Later oath features lean into preservation and anti-magic endurance.' },
    'oath of vengeance': { role: 'Relentless hunter', fantasy: 'Commit to pressure, pursuit, and punishing high-value targets.', now: 'Best when you want aggressive pursuit and focused threat removal.', later: 'Later oath features reward momentum and single-target pressure.' },
    'arcane trickster': { role: 'Spell rogue', fantasy: 'Use magic to sharpen stealth, setup, and precision.', now: 'Best when you want trick play, utility, and clever setup tools.', later: 'Later features reward planning, positioning, and layered disruption.' },
    'assassin': { role: 'Burst rogue', fantasy: 'Hit first, hit hard, and turn preparation into damage.', now: 'Best when you want ambush identity and ruthless pressure.', later: 'Later features reinforce infiltration and decisive openers.' },
    'thief': { role: 'Utility rogue', fantasy: 'Outplay the field with speed, positioning, and object mastery.', now: 'Best when you want mobility and broad rogue utility every session.', later: 'Later features improve movement, interaction, and adaptability.' },
    'archfey patron': { role: 'Charm warlock', fantasy: 'Use glamour, confusion, and presence to control the field.', now: 'Best when you want fey trickery and movement pressure.', later: 'Later features deepen charm, escape, and social menace.' },
    'fiend patron': { role: 'Hellfire warlock', fantasy: 'Trade in fear, destruction, and infernal staying power.', now: 'Best when you want direct damage and darker endurance.', later: 'Later features keep rewarding aggression and infernal toughness.' },
    'great old one patron': { role: 'Mind warlock', fantasy: 'Play through psychic pressure, secrecy, and alien control.', now: 'Best when you want strange utility and unsettling battlefield influence.', later: 'Later features lean into psychic disruption and weird control.' },
    'circle of the land': { role: 'Terrain druid', fantasy: 'Let your magic feel anchored to place, terrain spells, and long-day slot recovery.', now: 'Best when you want adaptable prepared casting, zone control, and a clear Natural Recovery economy.', later: 'Later features keep rewarding terrain identity with Circle Spells, support tools, and durable casting flexibility.' },
    'circle of the moon': { role: 'Form druid', fantasy: 'Push Wild Shape into a true battle mode with stronger form scaling and elemental forms.', now: 'Best when you want frontline shift turns, cast-vs-shift decisions, and Combat Wild Shape pressure.', later: 'Later features dramatically strengthen form identity through Circle Forms scaling and Elemental Wild Shape spikes.' },
    'wild magic': { role: 'Chaos sorcerer', fantasy: 'Lean into swingy spell expression and high-variance pressure.', now: 'Best when you want unpredictable moments and magical volatility.', later: 'Later features reward embracing randomness instead of avoiding it.' },
    'draconic bloodline': { role: 'Dragon sorcerer', fantasy: 'Shape your magic around elemental force and draconic presence.', now: 'Best when you want stronger innate power and clearer elemental identity.', later: 'Later features reinforce durability, damage, and bloodline fantasy.' },
    'hunter': { role: 'Focused ranger', fantasy: 'Turn the ranger into a clean predator with direct combat lines.', now: 'Best when you want a straightforward skirmisher and target pressure.', later: 'Later features keep sharpening efficient hunting and encounter control.' },
    'gloom stalker': { role: 'Shadow ranger', fantasy: 'Own the first turn, darkness, and ambush pressure.', now: 'Best when you want stealth aggression and opening-round power.', later: 'Later features reward setup, darkness, and ambush rhythm.' },
    'beast master': { role: 'Companion ranger', fantasy: 'Fight as a coordinated pair with a visible battlefield partner.', now: 'Best when you want action planning around a companion instead of solo lines.', later: 'Later features deepen companion teamwork and coordinated pressure.' },
    'berserker': { role: 'Rage striker', fantasy: 'Commit fully to pressure and ferocity.', now: 'Best when you want Rage turns to stack extra offense and punish enemies who try to trade into you.', later: 'Later features add fear control and reaction punishment so your melee presence stays threatening all campaign.' },
    'path of the wild heart': { role: 'Primal adapter', fantasy: 'Let rage change with the spirit you channel.', now: 'Best when you want flexible rage identity instead of a single fixed lane.', later: 'Later features keep opening spirit-driven play patterns.' },
    'path of the world tree': { role: 'Guardian barbarian', fantasy: 'Pair primal toughness with protective reach and battlefield hold.', now: 'Best when you want Rage to add survivability and positional control, including reaction-based enemy repositioning.', later: 'Later features deepen map control and long-rest teleport utility for party repositioning plays.' },
    'college of glamour': { role: 'Presence bard', fantasy: 'Lead with charm, staging, and magnetic battlefield support.', now: 'Best when you want your bard to feel dazzling and socially dominant.', later: 'Later features reinforce presence, movement, and glamour pressure.' },
    'college of lore': { role: 'Scholar bard', fantasy: 'Win through versatility, knowledge, and broad magical reach.', now: 'Best when you want the widest utility and support options.', later: 'Later features reward flexible responses and bigger spell pivots.' },
    'college of valor': { role: 'Battle bard', fantasy: 'Stand closer to the front line while still supporting the team.', now: 'Best when you want a bard with stronger battlefield posture and martial confidence.', later: 'Later features deepen combat support and frontline credibility.' },
    'way of shadow': { role: 'Stealth monk', fantasy: 'Trade obvious force for darkness, movement, and disruption.', now: 'Best when you want stealthy pressure and tactical repositioning.', later: 'Later features reward ambush timing and shadow control.' },
    'way of the four elements': { role: 'Element monk', fantasy: 'Shape ki into visible elemental expressions.', now: 'Best when you want flashy ranged utility layered onto monk mobility.', later: 'Later features widen your elemental toolbox and control lines.' },
    'way of the open hand': { role: 'Control monk', fantasy: 'Use disciplined strikes to shape the battlefield around you.', now: 'Best when you want simple monk turns with stronger rider control.', later: 'Later features reward tempo, pressure, and clean control effects.' },
    'artillerist': { role: 'Siege tinker', fantasy: 'Turn gadgets into ranged pressure and explosive space control.', now: 'Best when you want device-driven offense and battlefield pressure.', later: 'Later features deepen cannon rhythm and ranged gadget identity.' },
    'alchemist': { role: 'Support tinker', fantasy: 'Solve fights and recovery with brews, compounds, and field chemistry.', now: 'Best when you want healing, buffs, and utility devices.', later: 'Later features strengthen elixirs and support chemistry play.' },
    'mechanist': { role: 'Companion tinker', fantasy: 'Use a frame or construct to share the battlefield with you.', now: 'Best when you want automation, positioning, and partner-style play.', later: 'Later features deepen construct teamwork and mechanical support.' },
    'saboteur': { role: 'Trap tinker', fantasy: 'Disrupt the field with stealth tech, setup, and denial.', now: 'Best when you want tricks, devices, and ambush utility.', later: 'Later features reward planning, disruption, and denial space.' },
    'corsair': { role: 'Duel pirate', fantasy: 'Win through speed, blade pressure, and boarding aggression.', now: 'Best when you want a pure swashbuckling combat identity.', later: 'Later features deepen dueling rhythm and direct pressure.' },
    'privateer': { role: 'Officer pirate', fantasy: 'Lead the crew with discipline, support, and tactical swagger.', now: 'Best when you want a more commanding and team-oriented pirate.', later: 'Later features strengthen leadership and coordinated assault play.' },
    'smuggler': { role: 'Escape pirate', fantasy: 'Outplay enemies with concealment, routes, and illicit tricks.', now: 'Best when you want stealth, repositioning, and slippery survival.', later: 'Later features reward escape plans and underworld utility.' },
    'dread captain': { role: 'Terror pirate', fantasy: 'Break morale and dominate space through fear and reputation.', now: 'Best when you want menace, intimidation, and pressure control.', later: 'Later features deepen battlefield fear and command presence.' },
    'archery': { role: 'Ranged style', fantasy: 'Push accuracy and consistency from a distance.', now: 'Best when your main plan is repeatable ranged pressure.', later: 'This keeps paying off as your ranged attack routine scales.' },
    'defense': { role: 'Defensive style', fantasy: 'Trade flash for steadier armor and survival.', now: 'Best when you expect to stand in danger often.', later: 'This style stays relevant because surviving extra rounds always matters.' },
    'dueling': { role: 'Single-weapon style', fantasy: 'Turn a one-weapon setup into sharper repeat damage.', now: 'Best when you want a cleaner one-hand weapon routine.', later: 'This style scales with every attack you make using that setup.' },
    'great weapon fighting': { role: 'Heavy weapon style', fantasy: 'Lean into two-handed aggression and bigger swings.', now: 'Best when your plan is high-pressure melee with large weapons.', later: 'This style keeps rewarding repeated heavy-weapon attacks.' },
    'protection': { role: 'Guardian style', fantasy: 'Spend your reactions protecting allies instead of only pushing damage.', now: 'Best when you want visible team defense on the front line.', later: 'This keeps mattering as allies become bigger enemy targets.' },
    'two-weapon fighting': { role: 'Dual-wield style', fantasy: 'Turn bonus actions into a true part of your weapon rhythm.', now: 'Best when you want faster-feeling melee turns and extra pressure.', later: 'This style stays strongest when your action economy already favors extra hits.' },
    'blind fighting': { role: 'Awareness style', fantasy: 'Fight confidently when sight or visibility gets messy.', now: 'Best when your campaign or build expects darkness, fog, or stealth threats.', later: 'This style keeps solving encounter problems other styles do not.' },
    'thrown weapon fighting': { role: 'Thrown style', fantasy: 'Keep pressure up while moving between melee and ranged lines.', now: 'Best when you want flexible range without changing weapon identity.', later: 'This style remains valuable because it preserves pressure while repositioning.' }
  };

  function classChoiceCoach(preview) {
    const key = String(preview && (preview.classId || preview.className) || '').toLowerCase();
    return CLASS_CHOICE_COACH[key] || null;
  }

  function spellPlanGuide(preview, spellPlan) {
    if (!spellPlan || typeof spellPlan !== 'object') return null;
    const mode = String(spellPlan.mode || 'known').toLowerCase();
    const classKey = String(preview && (preview.classId || preview.className) || '').toLowerCase();
    const isHalfCaster = ['paladin', 'ranger', 'tinker'].indexOf(classKey) >= 0;
    if (mode === 'prepared') {
      return {
        title: 'Prepared Caster Guidance',
        summary: 'You are not locking your whole spell list forever here. This level mostly expands what you can prepare after the level is applied.',
        bullets: [
          'Focus on role coverage: defense, healing, control, scouting, or damage.',
          'Always-prepared subclass spells should not eat into your normal prepared cap.',
          'After leveling, reopen Manage Spells to decide what is actually prepared for the day.'
        ]
      };
    }
    if (mode === 'spellbook') {
      return {
        title: 'Spellbook Guidance',
        summary: 'This level adds spells to your book, then your prepared list is chosen from that bigger library.',
        bullets: [
          'Add spells that solve problems you cannot already solve.',
          'Mix one reliable combat tool with one utility or ritual option when possible.',
          'Prepared capacity and spellbook growth are different; this screen is about expanding the book.'
        ]
      };
    }
    return {
      title: isHalfCaster ? 'Known Spell Guidance' : 'Learned Spell Guidance',
      summary: isHalfCaster
        ? 'Your spell picks are limited, so choose spells that stay useful for many levels.'
        : 'Known-spell classes need picks that match their real combat rhythm and role.',
      bullets: [
        'Avoid duplicate jobs unless the new spell is a clear upgrade.',
        'Check whether a swap is better than grabbing another situational spell.',
        'Use attack, save, support, and utility balance to keep the class flexible.'
      ]
    };
  }

  function guidancePanelHtml(title, summary, bullets) {
    const rows = Array.isArray(bullets) ? bullets.filter(Boolean) : [];
    return '<section class="lvlup-card" style="background:rgba(0,229,204,.05)">'
      + '<div class="lvlup-title">' + escHtml(title || 'Guidance') + '</div>'
      + (summary ? '<div style="font-size:.84rem;opacity:.92;margin-bottom:8px">' + escHtml(summary) + '</div>' : '')
      + reviewList(rows, 'No guidance available for this level.')
      + '</section>';
  }

  function featureMeaningBlock(feature) {
    if (!feature || typeof feature !== 'object') return '';
    const lines = [];
    const actionType = String(feature.actionType || feature.activationType || '').trim();
    const resource = String((feature.resource && feature.resource.name) || feature.resourceName || '').trim();
    const recovery = String((feature.resource && feature.resource.recovery) || feature.recovery || feature.recharge || '').trim();
    if (actionType) lines.push('Uses your ' + actionType.replace(/_/g, ' ') + '.');
    if (resource) lines.push('Tracks through ' + resource + (recovery ? ' (' + recovery.replace(/_/g, ' ') + ')' : '') + '.');
    if (feature.summary) lines.push('In play: ' + String(feature.summary));
    return lines.length
      ? '<div style="margin-top:8px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,.04)"><div class="lvlup-subtitle">What this means for your character</div>' + reviewList(lines, 'No extra guidance.') + '</div>'
      : '';
  }


  function inferChoiceRulePanels(preview, features, spellPlan) {
    const panels = [];
    const seen = new Set();
    function pushRule(key, title, summary, bullets) {
      if (!key || seen.has(key)) return;
      seen.add(key);
      panels.push({ title: title, summary: summary, bullets: bullets });
    }
    (Array.isArray(features) ? features : []).forEach(function (feature) {
      const featureName = String(feature && (feature.displayName || feature.name || feature.id) || '').toLowerCase();
      const choiceNames = (Array.isArray(feature && feature.choices) ? feature.choices : []).map(function (choice) {
        return String(choice && (choice.name || choice.id) || '').toLowerCase();
      }).join(' ');
      const hay = featureName + ' ' + choiceNames + ' ' + String(feature && (feature.description || feature.summary || '') || '').toLowerCase();
      if (/(subclass|domain|circle|primal path|bard college|arcane tradition|oath|patron|field specialization|pirate calling|monastic tradition)/.test(hay)) {
        pushRule(
          'subclass',
          'Subclass Choice Rule',
          'This choice usually defines your long-term identity. Pick the option that matches how you actually want this character to play every session, not just at this level.',
          ['Look for the subclass option that changes your normal turn plan the most.', 'Check whether it adds new actions, passives, spells, or tracked resources.', 'A subclass pick should still make sense five levels from now, not just right now.']
        );
      }
      if (/fighting style/.test(hay)) {
        pushRule(
          'fighting-style',
          'Fighting Style Rule',
          'Treat Fighting Style choices like permanent combat posture upgrades. Pick the style that supports the attacks, positioning, or defenses you use most often.',
          ['Do not pick a style for gear you rarely use.', 'Check whether it improves offense, defense, or consistency for your usual loadout.', 'A fighting style should make your most common turns cleaner, not more awkward.']
        );
      }
      if (/maneuver|superiority/.test(hay)) {
        pushRule(
          'maneuvers',
          'Maneuver Choice Rule',
          'Maneuvers are best when each pick fills a different tactical job at the table.',
          ['Aim for a mix of pressure, control, and reliability.', 'Prefer maneuvers you will remember to use in real turns.', 'Resource spenders should feel worth a superiority die, not just technically legal.']
        );
      }
      if (/invocation/.test(hay)) {
        pushRule(
          'invocations',
          'Invocation Choice Rule',
          'Invocation picks should sharpen your Warlock identity. Treat them as premium permanent build choices, not filler.',
          ['Check whether the invocation improves blasting, utility, pact tools, or survivability.', 'Avoid picks that duplicate something you already solve well.', 'Short-rest classes benefit most from invocations that matter in repeated encounters.']
        );
      }
      if (/metamagic/.test(hay)) {
        pushRule(
          'metamagic',
          'Metamagic Choice Rule',
          'Pick metamagic options that change how your best spells actually play, not options that sound good but never get used.',
          ['Look for one flexible option and one high-impact signature option.', 'Pair metamagic with the spell patterns you already rely on.', 'Sorcery Points are limited, so each metamagic should earn its place.']
        );
      }
      if (/eldritch canon|infusion|device|prototype rig|swagger|dirty fighting/.test(hay)) {
        pushRule(
          'signature-kit',
          'Signature Kit Rule',
          'When a choice is tied to your class kit, pick the option that strengthens your signature loop instead of spreading you too thin.',
          ['Tinker choices should reinforce deployment, support, or gadget rhythm.', 'Pirate choices should reinforce swagger flow, movement pressure, or dueling rhythm.', 'The right pick should make your main fantasy more obvious every round.']
        );
      }
    });
    if (spellPlan && spellPlan.swapAllowed) {
      pushRule(
        'spell-swap',
        'Spell Swap Rule',
        'A swap is best used to replace a spell that stopped earning its slot. This is not only about novelty; it is about cleaning up dead weight.',
        ['Drop spells you consistently skip in real play.', 'Learn a replacement that fills a genuine gap or upgrades a weak slot.', 'Do not swap into a spell you are also adding somewhere else in this same level-up.']
      );
    }
    if (spellPlan && (safeInt(spellPlan.cantripPicksRequired, 0) > 0 || safeInt(spellPlan.levelledPicksRequired, 0) > 0)) {
      pushRule(
        'spell-picks',
        'Spell Pick Rule',
        'Pick spells by the role they fill in actual sessions: damage, control, defense, support, travel, scouting, or utility.',
        ['Avoid stacking too many spells that solve the same problem.', 'Prepared casters can be broader; known-spell classes should stay tighter and more reliable.', 'A new spell should either upgrade your best turn or cover a problem the party still struggles with.']
      );
    }
    return panels;
  }

  function choiceRuleSummaryHtml(preview, features, spellPlan) {
    const panels = inferChoiceRulePanels(preview, features, spellPlan);
    if (!panels.length) return '';
    return '<section class="lvlup-card"><div class="lvlup-title">Choice Rules</div>'
      + '<div style="font-size:.84rem;opacity:.9;margin-bottom:8px">These rules explain what kind of choice you are making now and what to look for before you confirm.</div>'
      + '<div class="lvlup-review-grid">'
      + panels.map(function (panel) { return guidancePanelHtml(panel.title, panel.summary, panel.bullets); }).join('')
      + '</div></section>';
  }

  function featureChoiceLead(feature) {
    const featureName = String(feature && (feature.displayName || feature.name || feature.id) || '').toLowerCase();
    const hay = featureName + ' ' + String(feature && (feature.description || feature.summary || '') || '').toLowerCase();
    if (/(subclass|domain|circle|primal path|bard college|arcane tradition|oath|patron|field specialization|pirate calling|monastic tradition)/.test(hay)) {
      return 'This is a subclass-defining choice. Expect it to shape the rest of the build.';
    }
    if (/fighting style/.test(hay)) return 'This choice changes your default combat posture, so match it to the gear and attacks you really use.';
    if (/maneuver|superiority/.test(hay)) return 'These picks are tactical tools. Favor options you will remember and actually spend resources on.';
    if (/invocation/.test(hay)) return 'Invocations are long-term build picks. Choose the option that sharpens your pact identity most clearly.';
    if (/metamagic/.test(hay)) return 'Metamagic should pair with spells you cast often, not only niche tricks.';
    return 'Pick the version that best matches the way this character already fights, supports, or survives.';
  }

  function normalizeChoiceKey(value) {
    return String(value || '').trim().toLowerCase();
  }

  function genericChoiceProfile(feature, choice, preview) {
    const featureName = normalizeChoiceKey(feature && (feature.displayName || feature.name || feature.id));
    const className = String(preview && (preview.className || preview.classId) || 'your class');
    if (/(subclass|domain|circle|primal path|bard college|arcane tradition|oath|patron|field specialization|pirate calling|monastic tradition)/.test(featureName)) {
      return { role: 'Subclass path', fantasy: 'This choice defines the long-term fantasy and role of the class.', now: 'Compare which option best matches how you want this character to feel every session.', later: 'This pick unlocks later subclass features, so choose the path you want to keep building around.' };
    }
    if (/fighting style/.test(featureName)) {
      return { role: 'Combat posture', fantasy: 'This choice changes the default way you attack, defend, or control space.', now: 'Pick the style that matches the gear and attack loop you actually use.', later: 'Later levels reward the style you repeat most often, not the style that sounds coolest on paper.' };
    }
    if (/maneuver|superiority/.test(featureName)) {
      return { role: 'Tactical tool', fantasy: 'This is a resource-spending trick that changes how your rounds feel.', now: 'Prioritize picks you will remember and actively spend resources on.', later: 'A balanced set usually includes one reliable default option and one situational control option.' };
    }
    if (/invocation/.test(featureName)) {
      return { role: 'Build modifier', fantasy: 'This modifies your warlock package in a lasting way.', now: 'Choose the option that sharpens your pact play instead of scattering your strengths.', later: 'Invocations compound over time, so consistency matters more than novelty.' };
    }
    if (/metamagic/.test(featureName)) {
      return { role: 'Spell expression', fantasy: 'This changes how your best spells behave at the table.', now: 'Pick metamagic that improves spells you already cast often.', later: 'The strongest metamagic choices keep paying off once your spell list grows.' };
    }
    return { role: className + ' option', fantasy: 'This is a real build choice, not filler text.', now: 'Pick the option that most clearly improves your normal turn plan.', later: 'A good pick should still make sense several levels from now.' };
  }

  function inferChoiceProfile(feature, choice, preview) {
    const key = normalizeChoiceKey(choice && (choice.name || choice.id));
    return CHOICE_PROFILE_OVERRIDES[key] || genericChoiceProfile(feature, choice, preview);
  }

  function featureOptionTypeLabel(feature) {
    const featureName = normalizeChoiceKey(feature && (feature.displayName || feature.name || feature.id));
    if (/(subclass|domain|circle|primal path|bard college|arcane tradition|oath|patron|field specialization|pirate calling|monastic tradition)/.test(featureName)) return 'Subclass options';
    if (/fighting style/.test(featureName)) return 'Fighting styles';
    if (/maneuver|superiority/.test(featureName)) return 'Maneuver options';
    if (/invocation/.test(featureName)) return 'Invocation options';
    if (/metamagic/.test(featureName)) return 'Metamagic options';
    return 'Feature options';
  }

  function unlockLaterHint(feature) {
    const featureName = normalizeChoiceKey(feature && (feature.displayName || feature.name || feature.id));
    if (/(subclass|domain|circle|primal path|bard college|arcane tradition|oath|patron|field specialization|pirate calling|monastic tradition)/.test(featureName)) return 'Pick now, unlock later: this path changes later features, identity text, and often bonus actions or spell support.';
    if (/fighting style/.test(featureName)) return 'Pick now, reinforce later: this style shapes the value of later attacks, gear choices, and action economy.';
    if (/maneuver|superiority/.test(featureName)) return 'Pick now, combine later: later combat turns get better when your picks cover different tactical jobs.';
    if (/invocation/.test(featureName)) return 'Pick now, stack later: invocations become more valuable when they clearly support the same pact plan.';
    if (/metamagic/.test(featureName)) return 'Pick now, expand later: future spell picks should pair with the metamagic you commit to here.';
    return 'Pick now, grow later: choose the option that still feels right once more features start stacking on top of it.';
  }

  function choiceCompareIntro(feature, choices) {
    const count = Array.isArray(choices) ? choices.length : 0;
    if (!count) return '';
    return '<div class="lvlup-subsection" style="margin:10px 0 0 0"><div class="lvlup-subtitle">' + escHtml(featureOptionTypeLabel(feature)) + '</div><div style="font-size:.78rem;opacity:.84">Compare the ' + escHtml(String(count)) + ' option' + (count === 1 ? '' : 's') + ' below before you lock one in. ' + escHtml(unlockLaterHint(feature)) + '</div></div>';
  }

  function classifyFeature(feature) {
    const tags = [];
    const actionType = String(feature && (feature.actionType || feature.activationType || '') || '').trim();
    const recovery = String(feature && (feature.recovery || feature.recharge || '') || '').trim();
    const source = String(feature && (feature.sourceName || feature.source || '') || '').trim();
    const level = safeInt(feature && (feature.level || feature.sourceLevel), 0);
    if (actionType) tags.push(actionType.replace(/_/g, ' ').replace(/\b\w/g, function (m) { return m.toUpperCase(); }));
    if (recovery) tags.push(recovery.replace(/_/g, ' ').replace(/\b\w/g, function (m) { return m.toUpperCase(); }));
    if (source) tags.push(source);
    if (level > 0) tags.push('Level ' + String(level));
    return tags.slice(0, 4);
  }

  function reviewList(items, emptyText) {
    const rows = Array.isArray(items) ? items.filter(Boolean) : [];
    if (!rows.length) return '<div style="font-size:.82rem;opacity:.76">' + escHtml(emptyText) + '</div>';
    return '<ul style="margin:6px 0 0 18px;padding:0;display:grid;gap:5px">' + rows.map(function (row) { return '<li>' + escHtml(row) + '</li>'; }).join('') + '</ul>';
  }

  const modalState = {
    options: null,
    preview: null,
    applying: false,
    featureChoices: {},
    asiMode: 'plus2',
    asiPlus2Ability: 'str',
    asiPlus1Abilities: [],
    featChoice: '',
    featsCatalog: [],
    featSearch: '',
    activeStep: 'automatic',
    spellCantripAdds: [],
    spellLevelledAdds: [],
    spellMagicalSecretsAdds: [],
    spellSwapDrop: '',
    spellSwapLearn: '',
    spellSearch: '',
    spellFilterLevel: 'all',
    subclassChoice: '',
  };

  function escHtml(value) {
    return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function abilityLabel(key) {
    return String(key || '').toUpperCase();
  }

  function safeInt(value, fallback) {
    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function normalizeMechanics(value) {
    if (!value || typeof value !== 'object') return {};
    const out = {};
    Object.keys(value).forEach(function (key) {
      const label = String(key || '').trim();
      if (!label) return;
      out[label] = safeInt(value[key], 0);
    });
    return out;
  }

  function mechanicLabel(key) {
    const normalized = String(key || '').trim();
    const labels = {
      focusPoints: 'Focus Points',
      disciplinePoints: 'Focus Points',
      martialArtsDie: 'Martial Arts Die',
      extraAttacks: 'Attacks per Attack Action',
    };
    if (labels[normalized]) return labels[normalized];
    return normalized.replace(/_/g, ' ').replace(/\b\w/g, function (m) { return m.toUpperCase(); });
  }

  function uniqueIds(value) {
    const rows = Array.isArray(value) ? value : [];
    const out = [];
    const seen = new Set();
    rows.forEach(function (row) {
      const id = String(row || '').trim();
      if (!id || seen.has(id)) return;
      seen.add(id);
      out.push(id);
    });
    return out;
  }

  function togglePick(list, id, limit) {
    const current = uniqueIds(list);
    const idx = current.indexOf(id);
    if (idx >= 0) {
      current.splice(idx, 1);
      return current;
    }
    if (limit != null && current.length >= limit) return current;
    current.push(id);
    return current;
  }

  function spellLevelLabel(level) {
    const n = safeInt(level, 0);
    if (n <= 0) return 'Cantrip';
    const suffix = n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th';
    return n + suffix + ' Level';
  }

  function sortSpellRows(rows) {
    return (Array.isArray(rows) ? rows.slice() : []).sort(function (a, b) {
      const levelDiff = safeInt(a && a.level, 0) - safeInt(b && b.level, 0);
      if (levelDiff) return levelDiff;
      return String((a && (a.name || a.id)) || '').localeCompare(String((b && (b.name || b.id)) || ''));
    });
  }

  function filterSpellRows(rows) {
    const search = String(modalState.spellSearch || '').trim().toLowerCase();
    const filterLevel = String(modalState.spellFilterLevel || 'all').toLowerCase();
    return sortSpellRows(rows).filter(function (spell) {
      const level = String(safeInt(spell && spell.level, 0));
      if (filterLevel !== 'all' && level !== filterLevel) return false;
      if (!search) return true;
      const hay = [spell && spell.name, spell && spell.id, spell && spell.school, spell && spell.summary, spell && spell.range, spell && spell.castingTime].join(' ').toLowerCase();
      return hay.indexOf(search) >= 0;
    });
  }

  function levelFilterBar(rows) {
    const counts = {};
    (Array.isArray(rows) ? rows : []).forEach(function (spell) {
      const key = String(safeInt(spell && spell.level, 0));
      counts[key] = (counts[key] || 0) + 1;
    });
    const keys = Object.keys(counts).sort(function (a, b) { return safeInt(a, 0) - safeInt(b, 0); });
    if (!keys.length) return '';
    return '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">'
      + '<button type="button" class="lvlup-ability-btn ' + (String(modalState.spellFilterLevel || 'all') === 'all' ? 'active' : '') + '" data-spell-filter="all">All</button>'
      + keys.map(function (key) {
        return '<button type="button" class="lvlup-ability-btn ' + (String(modalState.spellFilterLevel || 'all') === key ? 'active' : '') + '" data-spell-filter="' + escHtml(key) + '">' + escHtml(spellLevelLabel(key)) + ' (' + escHtml(counts[key]) + ')</button>';
      }).join('')
      + '</div>';
  }

  function groupedSpellCards(rows, renderFn, emptyText, gridClass) {
    const grouped = {};
    filterSpellRows(rows).forEach(function (spell) {
      const key = String(safeInt(spell && spell.level, 0));
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(spell);
    });
    const keys = Object.keys(grouped).sort(function (a, b) { return safeInt(a, 0) - safeInt(b, 0); });
    if (!keys.length) return '<div style="font-size:.8rem;opacity:.76">' + escHtml(emptyText) + '</div>';
    return keys.map(function (key) {
      return '<div class="lvlup-subsection"><div class="lvlup-subtitle">' + escHtml(spellLevelLabel(key)) + '</div><div class="' + escHtml(gridClass || 'lvlup-choice-grid') + '">'
        + grouped[key].map(renderFn).join('')
        + '</div></div>';
    }).join('');
  }

  function spellStateBadge(label, tone) {
    return '<span class="lvlup-spell-badge ' + escHtml(tone || '') + '">' + escHtml(label || '') + '</span>';
  }

  function groupedSpellTable(rows, rowRenderer, emptyText) {
    const grouped = {};
    filterSpellRows(rows).forEach(function (spell) {
      const key = String(safeInt(spell && spell.level, 0));
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(spell);
    });
    const keys = Object.keys(grouped).sort(function (a, b) { return safeInt(a, 0) - safeInt(b, 0); });
    if (!keys.length) return '<div style="font-size:.8rem;opacity:.76">' + escHtml(emptyText) + '</div>';
    return keys.map(function (key) {
      const rowsHtml = grouped[key].map(function (spell) { return rowRenderer(spell); }).join('');
      return '<div class="lvlup-subsection"><div class="lvlup-subtitle">' + escHtml(spellLevelLabel(key)) + '</div>'
        + '<div class="lvlup-spell-table-wrap"><table class="lvlup-spell-table"><thead><tr><th>Spell</th><th>Level</th><th>School</th><th>Cast Time</th><th>Range</th><th>Summary</th><th>State</th><th></th></tr></thead><tbody>'
        + rowsHtml
        + '</tbody></table></div></div>';
    }).join('');
  }

  function spellChoiceToolbar(allRows) {
    if (!Array.isArray(allRows) || !allRows.length) return '';
    return '<div class="lvlup-card" style="padding:10px 12px;background:rgba(8,12,15,.6)">'
      + '<div style="font-size:.78rem;opacity:.8">Filter legal spell choices</div>'
      + '<input id="character-levelup-spell-search" type="search" value="' + escHtml(modalState.spellSearch) + '" placeholder="Search legal spells..." style="margin-top:7px;width:100%;padding:7px;border-radius:6px;border:1px solid rgba(0,229,204,.25);background:#0d1113;color:#ddf8f5" />'
      + levelFilterBar(allRows)
      + '</div>';
  }

  function diffRowsHtml(rows) {
    const resolved = Array.isArray(rows) ? rows.filter(Boolean) : [];
    if (!resolved.length) {
      return '<div style="font-size:.82rem;opacity:.8">No automatic gains detected for this level.</div>';
    }
    return '<table style="width:100%;border-collapse:collapse;font-size:.84rem">'
      + '<thead><tr><th style="text-align:left;padding:4px 8px">Category</th><th style="text-align:left;padding:4px 8px">Before</th><th style="text-align:left;padding:4px 8px">After</th><th style="text-align:left;padding:4px 8px">Delta</th></tr></thead>'
      + '<tbody>'
      + resolved.map(function (row) {
        const before = row.before == null ? '—' : row.before;
        const after = row.after == null ? '—' : row.after;
        const delta = row.delta == null ? '—' : row.delta;
        return '<tr>'
          + '<td style="padding:4px 8px;font-weight:600">' + escHtml(row.label || '') + '</td>'
          + '<td style="padding:4px 8px">' + escHtml(before) + '</td>'
          + '<td style="padding:4px 8px">' + escHtml(after) + '</td>'
          + '<td style="padding:4px 8px;color:#9ff6ea">' + escHtml(delta) + '</td>'
          + '</tr>';
      }).join('')
      + '</tbody></table>';
  }

  function ensureModalDom() {
    let root = document.getElementById(MODAL_ID);
    if (root) return root;

    root = document.createElement('div');
    root.id = MODAL_ID;
    root.style.cssText = 'position:fixed;inset:0;background:rgba(2,4,7,.72);display:none;align-items:center;justify-content:center;z-index:15000;';

    root.innerHTML = ''
      + '<style>'
      + '#character-levelup-modal .lvlup-card{border:1px solid rgba(0,229,204,.24);border-radius:10px;padding:12px;background:rgba(16,23,26,.75)}'
      + '#character-levelup-modal .lvlup-title{font-family:Cinzel,serif;color:#00e5cc;letter-spacing:.08em;text-transform:uppercase;font-size:.72rem;margin-bottom:6px}'
      + '#character-levelup-modal .lvlup-feature-name{font-family:Cinzel,serif;color:#4de3d2;font-size:1rem}'
      + '#character-levelup-modal .lvlup-choice-card{position:relative;border:1px solid rgba(0,229,204,.2);border-radius:10px;padding:10px;background:rgba(0,229,204,.06);cursor:pointer;transition:border-color .15s ease,box-shadow .15s ease,transform .12s ease}'
      + '#character-levelup-modal .lvlup-choice-card.active{border-color:rgba(0,229,204,.85);box-shadow:0 0 0 1px rgba(0,229,204,.35),0 0 18px rgba(0,229,204,.28);transform:translateY(-1px)}'
      + '#character-levelup-modal .lvlup-option-card{text-align:left;background:linear-gradient(180deg,rgba(0,229,204,.08),rgba(0,229,204,.03));padding:12px}'
      + '#character-levelup-modal .lvlup-step-button{min-width:150px;text-align:left}'
      + '#character-levelup-modal .lvlup-step-button.active{background:linear-gradient(180deg,rgba(0,229,204,.2),rgba(0,229,204,.08));border-color:rgba(0,229,204,.78)}'
      + '#character-levelup-modal .lvlup-selected-chip{display:inline-flex;align-items:center;gap:4px;border:1px solid rgba(0,229,204,.45);border-radius:999px;padding:2px 8px;font-size:.68rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#dffef8;background:rgba(0,229,204,.14)}'
      + '#character-levelup-modal .lvlup-confirm-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px}'
      + '#character-levelup-modal .lvlup-confirm-card{border:1px solid rgba(0,229,204,.18);border-radius:10px;padding:10px;background:linear-gradient(180deg,rgba(0,229,204,.08),rgba(0,229,204,.03))}'
      + '#character-levelup-modal .lvlup-option-block{margin-top:9px;padding-top:8px;border-top:1px solid rgba(0,229,204,.12)}'
      + '#character-levelup-modal .lvlup-option-label{font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;opacity:.72;color:#9efff2}'
      + '#character-levelup-modal .lvlup-option-text{font-size:.76rem;line-height:1.45;opacity:.92;margin-top:3px}'
      + '#character-levelup-modal .lvlup-choice-card[disabled]{opacity:.45;cursor:not-allowed}'
      + '#character-levelup-modal .lvlup-asi-card{border:1px solid rgba(0,229,204,.2);border-radius:8px;padding:10px;cursor:pointer;background:rgba(15,20,24,.72)}'
      + '#character-levelup-modal .lvlup-asi-card.active{border-color:rgba(0,229,204,.75);box-shadow:0 0 14px rgba(0,229,204,.2)}'
      + '#character-levelup-modal .lvlup-ability-btn{border:1px solid rgba(0,229,204,.25);background:rgba(0,229,204,.1);color:#d5fff9;border-radius:6px;padding:6px 8px;cursor:pointer;font-size:.76rem}'
      + '#character-levelup-modal .lvlup-ability-btn.active{background:#00e5cc;color:#021418;border-color:#00e5cc}'
      + '#character-levelup-modal .lvlup-banner{font-family:Cinzel,serif;font-size:1.5rem;color:#9efff2;text-shadow:0 0 6px rgba(0,229,204,.48),0 0 20px rgba(0,229,204,.26);animation:lvlupGlow 1.5s ease-in-out infinite alternate}'
      + '#character-levelup-modal .lvlup-pill{display:inline-flex;align-items:center;border:1px solid rgba(0,229,204,.28);border-radius:999px;padding:3px 8px;font-size:.72rem;color:#9df7eb;background:rgba(0,229,204,.08);margin-right:6px;margin-bottom:6px}'
      + '#character-levelup-modal .lvlup-step-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}'
      + '#character-levelup-modal .lvlup-review-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}'
      + '#character-levelup-modal .lvlup-choice-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px}'
      + '#character-levelup-modal .lvlup-spell-grid{grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}'
      + '#character-levelup-modal .lvlup-spell-grid .lvlup-choice-card{min-height:132px;text-align:left;padding:11px 12px;background:linear-gradient(180deg,rgba(0,229,204,.09),rgba(0,229,204,.035));border-color:rgba(0,229,204,.3)}'
      + '#character-levelup-modal .lvlup-spell-grid .lvlup-choice-card .lvlup-meta{font-size:.72rem;opacity:.7}'
      + '#character-levelup-modal .lvlup-spell-grid .lvlup-spell-name{font-size:.98rem;line-height:1.2}'
      + '#character-levelup-modal .lvlup-spell-grid .lvlup-spell-castline{font-size:.9rem}'
      + '#character-levelup-modal .lvlup-spell-grid .lvlup-spell-summary{color:rgba(223,254,249,.88)}'
      + '#character-levelup-modal .lvlup-spell-table-wrap{overflow:auto;border:1px solid rgba(0,229,204,.22);border-radius:8px;background:rgba(3,9,11,.48)}'
      + '#character-levelup-modal .lvlup-spell-table{width:100%;border-collapse:collapse;font-size:.76rem;min-width:840px}'
      + '#character-levelup-modal .lvlup-spell-table th,#character-levelup-modal .lvlup-spell-table td{padding:7px 8px;border-bottom:1px solid rgba(0,229,204,.12);text-align:left;vertical-align:top}'
      + '#character-levelup-modal .lvlup-spell-table thead th{font-size:.67rem;letter-spacing:.05em;text-transform:uppercase;color:#9ff8ed;background:rgba(0,229,204,.08);position:sticky;top:0;z-index:1}'
      + '#character-levelup-modal .lvlup-spell-table tbody tr.active{background:rgba(0,229,204,.12)}'
      + '#character-levelup-modal .lvlup-spell-table tbody tr.disabled{opacity:.6}'
      + '#character-levelup-modal .lvlup-spell-badge{display:inline-flex;align-items:center;border-radius:999px;border:1px solid rgba(0,229,204,.28);padding:2px 8px;font-size:.66rem;text-transform:uppercase;letter-spacing:.05em}'
      + '#character-levelup-modal .lvlup-spell-badge.good{background:rgba(41,180,121,.2);border-color:rgba(41,180,121,.55)}'
      + '#character-levelup-modal .lvlup-spell-badge.warn{background:rgba(201,56,56,.18);border-color:rgba(201,56,56,.55)}'
      + '#character-levelup-modal .lvlup-spell-badge.teal{background:rgba(0,229,204,.18);border-color:rgba(0,229,204,.55)}'
      + '#character-levelup-modal .lvlup-spell-badge.violet{background:rgba(155,89,182,.2);border-color:rgba(155,89,182,.55)}'
      + '#character-levelup-modal .lvlup-subsection{display:grid;gap:8px;margin-top:10px}'
      + '#character-levelup-modal .lvlup-subtitle{font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#9efff2;opacity:.95}'
      + '#character-levelup-modal .lvlup-choice-card .lvlup-meta{font-size:.72rem;opacity:.72}'
      + '#character-levelup-modal .lvlup-choice-card .lvlup-helper{font-size:.72rem;opacity:.62;margin-top:6px}'
      + '#character-levelup-modal .lvlup-stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:8px}'
      + '#character-levelup-modal .lvlup-stat{border:1px solid rgba(0,229,204,.16);border-radius:8px;padding:8px 10px;background:rgba(0,229,204,.05)}'
      + '#character-levelup-modal .lvlup-stat-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;opacity:.72;margin-bottom:4px}'
      + '#character-levelup-modal .lvlup-stat-value{font-size:.95rem;font-weight:700;color:#defcf8}'
      + '@keyframes lvlupGlow{from{text-shadow:0 0 6px rgba(0,229,204,.45),0 0 14px rgba(0,229,204,.15)}to{text-shadow:0 0 10px rgba(0,229,204,.85),0 0 24px rgba(0,229,204,.32)}}'
      + '</style>'
      + '<div style="width:min(960px,calc(100vw - 24px));max-height:calc(100vh - 24px);overflow:auto;background:#10140f;border:1px solid rgba(0,229,204,.3);border-radius:10px;padding:16px;color:#e8dcc8;box-shadow:0 18px 54px rgba(0,0,0,.55)">'
      + '  <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;">'
      + '    <div style="font-family:Cinzel,serif;letter-spacing:.1em;text-transform:uppercase;color:#00e5cc;font-size:.76rem;">Level Up</div>'
      + '    <button type="button" id="character-levelup-close" style="background:transparent;border:1px solid rgba(0,229,204,.35);border-radius:4px;color:#e8dcc8;padding:4px 8px;cursor:pointer;">Close</button>'
      + '  </div>'
      + '  <div id="character-levelup-status" style="display:none;margin:8px 0;padding:8px 10px;border-radius:6px;font-size:.84rem"></div>'
      + '  <div id="character-levelup-content" style="display:grid;gap:10px"></div>'
      + '  <div style="display:flex;justify-content:flex-end;margin-top:12px;">'
      + '    <button type="button" id="character-levelup-apply" disabled style="background:#665e50;color:#d4cab4;border:0;border-radius:6px;padding:9px 14px;cursor:not-allowed;">Level Up</button>'
      + '  </div>'
      + '</div>';

    document.body.appendChild(root);
    root.querySelector('#character-levelup-close')?.addEventListener('click', function onClose() { root.style.display = 'none'; });
    root.addEventListener('click', function onBackdrop(evt) { if (evt.target === root) root.style.display = 'none'; });
    root.querySelector('#character-levelup-apply')?.addEventListener('click', function onApply() {
      applyLevelup(root).catch(function onErr(err) {
        setStatus(root, (err && err.message) || 'Unable to apply level up.', 'error');
      });
    });
    return root;
  }

  function setStatus(root, message, kind) {
    const box = root.querySelector('#character-levelup-status');
    if (!box) return;
    if (!message) { box.style.display = 'none'; box.textContent = ''; return; }
    box.style.display = '';
    box.textContent = String(message);
    const pal = kind === 'error'
      ? ['rgba(201,56,56,.18)', 'rgba(201,56,56,.5)']
      : kind === 'success'
        ? ['rgba(38,173,122,.18)', 'rgba(38,173,122,.5)']
        : ['rgba(0,229,204,.12)', 'rgba(0,229,204,.4)'];
    box.style.background = pal[0];
    box.style.border = '1px solid ' + pal[1];
  }

  function setApplyEnabled(root, enabled, label) {
    const btn = root.querySelector('#character-levelup-apply');
    if (!btn) return;
    btn.disabled = !enabled;
    btn.textContent = label || 'Level Up';
    btn.style.cursor = enabled ? 'pointer' : 'not-allowed';
    btn.style.background = enabled ? '#00e5cc' : '#665e50';
    btn.style.color = enabled ? '#052121' : '#d4cab4';
  }

  async function fetchPreview(payload) {
    const res = await fetch('/api/character/levelup/preview', {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload || {}),
    });
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok || !data || data.ok !== true) throw new Error((data && data.detail) || 'Level-up preview failed');
    return data;
  }

  async function fetchFeats() {
    const res = await fetch('/api/rules/feats', { credentials: 'same-origin' });
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok || !data || data.ok !== true) return [];
    const origin = Array.isArray(data.origin) ? data.origin : [];
    const general = Array.isArray(data.general) ? data.general : [];
    return origin.concat(general);
  }

  function buildChoicesPayload(preview) {
    const payload = { featureChoices: {} };
    const features = Array.isArray(preview && preview.newFeatures) ? preview.newFeatures : [];
    features.forEach(function (feature) {
      if (!feature || !feature.id) return;
      const selected = modalState.featureChoices[String(feature.id)];
      if (selected) payload.featureChoices[String(feature.id)] = selected;
    });

    if (preview && preview.isAsiLevel) {
      if (modalState.asiMode === 'feat' && modalState.featChoice) {
        payload.featChoice = modalState.featChoice;
      } else if (modalState.asiMode === 'plus1x2') {
        payload.asiChoice = { mode: 'plus1x2', abilities: modalState.asiPlus1Abilities.slice(0, 2) };
      } else {
        payload.asiChoice = { mode: 'plus2', ability: modalState.asiPlus2Ability || 'str' };
      }
    }

    if (preview && preview.spellChoices) {
      payload.spellChoices = {
        cantripAdds: uniqueIds(modalState.spellCantripAdds),
        levelledAdds: uniqueIds(modalState.spellLevelledAdds),
        magicalSecretsAdds: uniqueIds(modalState.spellMagicalSecretsAdds),
        swap: {
          drop: modalState.spellSwapDrop || '',
          learn: modalState.spellSwapLearn || '',
        },
      };
    }
    if (preview && preview.subclassChoice && preview.subclassChoice.required) {
      payload.subclassChoice = String(modalState.subclassChoice || '').trim().toLowerCase();
    }
    return payload;
  }

  function renderSubclassChoiceSection(preview) {
    const choice = preview && preview.subclassChoice && typeof preview.subclassChoice === 'object' ? preview.subclassChoice : null;
    if (!choice || !choice.required) return '';
    const options = Array.isArray(choice.options) ? choice.options : [];
    if (!options.length) {
      return '<section class="lvlup-card"><div class="lvlup-title">Choices — Subclass</div>'
        + '<div style="font-size:.84rem;opacity:.9">Subclass choice is required at this level, but no legal subclass options were returned. Ask the DM to refresh the rules catalog for this class.</div>'
        + '</section>';
    }
    const cards = options.map(function (row) {
      const subclassId = String(row && row.id || '').trim().toLowerCase();
      const active = subclassId && modalState.subclassChoice === subclassId;
      return '<button type="button" class="lvlup-choice-card lvlup-option-card ' + (active ? 'active' : '') + '" data-subclass-choice="' + escHtml(subclassId) + '">'
        + '<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">'
        + '  <div><div style="font-weight:700;font-size:.95rem">' + escHtml(row && (row.name || row.id) || 'Subclass') + '</div><div class="lvlup-meta" style="margin-top:3px">Subclass path</div></div>'
        + '  <span class="lvlup-pill" style="margin:0">' + escHtml(active ? 'Selected' : 'Choose') + '</span>'
        + '</div>'
        + '<div style="font-size:.8rem;opacity:.9;margin-top:8px">' + escHtml(row && row.summary || 'No summary available for this subclass option.') + '</div>'
        + '</button>';
    }).join('');
    return '<section class="lvlup-card"><div class="lvlup-title">Choices — Subclass</div>'
      + '<div style="font-size:.84rem;opacity:.9;margin-bottom:8px">Level ' + escHtml(String(choice.unlockLevel || '?')) + ' unlocks your subclass. Choose one path to continue.</div>'
      + '<div class="lvlup-choice-grid">' + cards + '</div>'
      + '</section>';
  }

  function slotRowsHtml(oldSlots, newSlots) {
    const levels = Array.from(new Set(Object.keys(oldSlots || {}).concat(Object.keys(newSlots || {})))).sort();
    if (!levels.length) return '<div style="font-size:.82rem;opacity:.8">No spell slot progression at this level.</div>';
    return levels.map(function (lvl) {
      return '<tr>'
        + '<td style="padding:4px 8px">' + escHtml(lvl) + '</td>'
        + '<td style="padding:4px 8px">' + escHtml((oldSlots && oldSlots[lvl]) || 0) + '</td>'
        + '<td style="padding:4px 8px">' + escHtml((newSlots && newSlots[lvl]) || 0) + '</td>'
        + '</tr>';
    }).join('');
  }

  function spellChoiceRowHtml(spell, cfg) {
    const config = cfg && typeof cfg === 'object' ? cfg : {};
    const selectedNow = !!config.selectedNow;
    const alreadySelected = !!config.alreadySelected;
    const prepared = !!config.prepared;
    const disabled = !!config.disabled;
    const actionAttrs = config.actionAttrs || '';
    const actionLabel = selectedNow ? 'Unselect' : (alreadySelected ? 'Locked' : 'Select');
    const summary = String(spell && spell.summary || '').trim() || 'No short summary loaded yet.';
    let badge = '';
    if (disabled && !selectedNow) badge = spellStateBadge('illegal', 'warn');
    else if (selectedNow) badge = spellStateBadge('selected now', 'good');
    else if (prepared) badge = spellStateBadge('prepared', 'teal');
    else if (alreadySelected) badge = spellStateBadge('known', 'violet');
    else badge = spellStateBadge('legal', '');
    return '<tr class="' + (selectedNow ? 'active' : '') + (disabled ? ' disabled' : '') + '">'
      + '<td><strong>' + escHtml(spell && (spell.name || spell.id) || 'Spell') + '</strong></td>'
      + '<td>' + escHtml(spellLevelLabel(safeInt(spell && spell.level, 0))) + '</td>'
      + '<td>' + escHtml(spell && spell.school || '—') + '</td>'
      + '<td>' + escHtml(spell && (spell.castingTime || spell.casting_time) || '—') + '</td>'
      + '<td>' + escHtml(spell && spell.range || '—') + '</td>'
      + '<td>' + escHtml(summary) + '</td>'
      + '<td>' + badge + '</td>'
      + '<td><button type="button" class="lvlup-ability-btn ' + (selectedNow ? 'active' : '') + '" ' + actionAttrs + (disabled ? ' disabled' : '') + '>' + escHtml(actionLabel) + '</button></td>'
      + '</tr>';
  }

  function renderSpellChoiceSection(preview, spellPlan) {
    if (!spellPlan || typeof spellPlan !== 'object') return '';
    const cantripRequired = safeInt(spellPlan.cantripPicksRequired, 0);
    const levelledRequired = safeInt(spellPlan.levelledPicksRequired, 0);
    const magicalSecretsRequired = safeInt(spellPlan.magicalSecretsPicksRequired, 0);
    const mode = String(spellPlan.mode || 'known');
    if (cantripRequired <= 0 && levelledRequired <= 0 && magicalSecretsRequired <= 0 && !spellPlan.swapAllowed) return '';
    const cantripOptions = Array.isArray(spellPlan.cantripOptions) ? spellPlan.cantripOptions : [];
    const levelledOptions = Array.isArray(spellPlan.levelledOptions) ? spellPlan.levelledOptions : [];
    const replaceable = Array.isArray(spellPlan.replaceableKnown) ? spellPlan.replaceableKnown : [];
    const magicalSecretOptions = Array.isArray(spellPlan.magicalSecretOptions) ? spellPlan.magicalSecretOptions : [];
    const replaceableIds = new Set(replaceable.map(function (spell) { return String(spell && spell.id || ''); }).filter(Boolean));
    const combinedRows = [].concat(cantripOptions, levelledOptions, replaceable, magicalSecretOptions);
    if (!combinedRows.length && magicalSecretsRequired <= 0 && !spellPlan.swapAllowed) return '';

    const guide = spellPlanGuide(preview, spellPlan);
    let html = '<section class="lvlup-card"><div class="lvlup-title">Choices — Spell Picks</div>'
      + '<div style="font-size:.84rem;opacity:.9;margin-bottom:8px">This chooser only shows spells your class can legally take at the new level. Illegal tiers stay hidden and pick caps are enforced.</div>'
      + (guide ? '<div style="margin-bottom:10px;padding:10px;border-radius:10px;background:rgba(255,255,255,.04)"><div class="lvlup-subtitle">' + escHtml(guide.title) + '</div><div style="font-size:.8rem;opacity:.9;margin-top:4px">' + escHtml(guide.summary) + '</div>' + reviewList(guide.bullets, 'No spell guidance available.') + '</div>' : '')
      + '<div class="lvlup-stat-grid">'
      + '<div class="lvlup-stat"><div class="lvlup-stat-label">Known cantrips</div><div class="lvlup-stat-value">' + escHtml(spellPlan.currentKnownCantrips || 0) + '</div></div>'
      + '<div class="lvlup-stat"><div class="lvlup-stat-label">Known leveled spells</div><div class="lvlup-stat-value">' + escHtml(spellPlan.currentKnownLevelled || 0) + '</div></div>'
      + '<div class="lvlup-stat"><div class="lvlup-stat-label">Highest spell tier after level</div><div class="lvlup-stat-value">' + escHtml(spellPlan.nextHighestSpellLevel ? spellLevelLabel(spellPlan.nextHighestSpellLevel) : 'Cantrip only') + '</div></div>'
      + ((spellPlan.nextLimits && spellPlan.nextLimits.preparedLimit != null) ? '<div class="lvlup-stat"><div class="lvlup-stat-label">Prepared after level</div><div class="lvlup-stat-value">' + escHtml(spellPlan.nextLimits.preparedLimit) + '</div></div>' : '')
      + '</div>'
      + spellChoiceToolbar(combinedRows);

    if (mode === 'prepared' && cantripRequired === 0 && levelledRequired === 0 && !spellPlan.swapAllowed) {
      html += '<div class="lvlup-card" style="margin-top:10px;background:rgba(0,229,204,.05)"><div class="lvlup-subtitle">No spell picks required</div><div style="font-size:.8rem;opacity:.86">' + escHtml(spellPlan.noChoicesMessage || 'Your prepared caster automatically unlocks more legal spells at this level. After applying the level, open Manage Spells to choose what stays prepared.') + '</div></div>';
      html += '</section>';
      return html;
    }

    if (cantripRequired > 0) {
      html += '<div style="margin-top:12px"><div style="font-weight:600">Pick cantrips (' + modalState.spellCantripAdds.length + ' / ' + cantripRequired + ')</div>'
        + '<div style="font-size:.76rem;opacity:.78;margin:3px 0 8px">Choose the new at-will spells this level grants you.</div>'
        + groupedSpellTable(cantripOptions, function (spell) {
          const active = modalState.spellCantripAdds.indexOf(String(spell.id || '')) >= 0;
          const blocked = !active && modalState.spellCantripAdds.length >= cantripRequired;
          return spellChoiceRowHtml(spell, {
            selectedNow: active,
            alreadySelected: replaceableIds.has(String(spell.id || '')),
            prepared: false,
            disabled: blocked,
            actionAttrs: 'data-spell-pick="cantrip" data-spell-id="' + escHtml(String(spell.id || '')) + '"'
          });
        }, 'No unlocked cantrip options are available with the current filter.')
        + '</div>';
    }

    if (levelledRequired > 0) {
      const pickLabel = mode === 'spellbook' ? 'Add spellbook spells' : 'Learn spells';
      const pickHelp = mode === 'spellbook'
        ? 'These are the new leveled spells going into your spellbook at this level.'
        : 'These are the new leveled spells your character can learn now.';
      html += '<div style="margin-top:12px"><div style="font-weight:600">' + escHtml(pickLabel) + ' (' + modalState.spellLevelledAdds.length + ' / ' + levelledRequired + ')</div>'
        + '<div style="font-size:.76rem;opacity:.78;margin:3px 0 8px">' + escHtml(pickHelp) + '</div>'
        + groupedSpellTable(levelledOptions, function (spell) {
          const active = modalState.spellLevelledAdds.indexOf(String(spell.id || '')) >= 0;
          const blocked = !active && modalState.spellLevelledAdds.length >= levelledRequired;
          return spellChoiceRowHtml(spell, {
            selectedNow: active,
            alreadySelected: replaceableIds.has(String(spell.id || '')),
            prepared: mode === 'prepared',
            disabled: blocked,
            actionAttrs: 'data-spell-pick="levelled" data-spell-id="' + escHtml(String(spell.id || '')) + '"'
          });
        }, 'No unlocked leveled spell options are available with the current filter.')
        + '</div>';
    }

    if (magicalSecretsRequired > 0) {
      const magicalSecretOptions = Array.isArray(spellPlan.magicalSecretOptions) ? spellPlan.magicalSecretOptions : [];
      html += '<div style="margin-top:12px"><div style="font-weight:600">Pick Magical Secrets (' + modalState.spellMagicalSecretsAdds.length + ' / ' + magicalSecretsRequired + ')</div>'
        + '<div style="font-size:.76rem;opacity:.78;margin:3px 0 8px">Pick off-list spells unlocked by Magical Secrets at this level.</div>'
        + groupedSpellTable(magicalSecretOptions, function (spell) {
          const active = modalState.spellMagicalSecretsAdds.indexOf(String(spell.id || '')) >= 0;
          const blocked = !active && modalState.spellMagicalSecretsAdds.length >= magicalSecretsRequired;
          return spellChoiceRowHtml(spell, {
            selectedNow: active,
            alreadySelected: false,
            prepared: false,
            disabled: blocked,
            actionAttrs: 'data-spell-pick="magical-secret" data-spell-id="' + escHtml(String(spell.id || '')) + '"'
          });
        }, 'No off-list Magical Secrets options are available with the current filter.')
        + '</div>';
    }

    if (spellPlan.swapAllowed) {
      const replacementPool = levelledOptions.filter(function (spell) {
        return modalState.spellLevelledAdds.indexOf(String(spell.id || '')) < 0;
      });
      html += '<div style="margin-top:12px"><div style="font-weight:600">Optional swap</div>'
        + '<div style="font-size:.76rem;opacity:.78;margin:3px 0 8px">If this class can replace one spell when leveling, choose one old spell to drop and one new legal spell to learn. Newly added spells are hidden from the replacement pool.</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
        + '<div><div class="lvlup-subtitle">Drop one old spell</div>'
        + groupedSpellTable(replaceable, function (spell) {
          const active = modalState.spellSwapDrop === String(spell.id || '');
          return spellChoiceRowHtml(spell, {
            selectedNow: active,
            alreadySelected: true,
            prepared: mode === 'prepared',
            disabled: false,
            actionAttrs: 'data-spell-swap="drop" data-spell-id="' + escHtml(String(spell.id || '')) + '"'
          });
        }, 'No spells are eligible to swap out with the current filter.')
        + '</div>'
        + '<div><div class="lvlup-subtitle">Learn one replacement spell</div>'
        + groupedSpellTable(replacementPool, function (spell) {
          const active = modalState.spellSwapLearn === String(spell.id || '');
          return spellChoiceRowHtml(spell, {
            selectedNow: active,
            alreadySelected: replaceableIds.has(String(spell.id || '')),
            prepared: mode === 'prepared',
            disabled: false,
            actionAttrs: 'data-spell-swap="learn" data-spell-id="' + escHtml(String(spell.id || '')) + '"'
          });
        }, 'No legal replacement spells are unlocked with the current filter.')
        + '</div>'
        + '</div></div>';
    }

    html += '</section>';
    return html;
  }

  function renderPreview(root, preview) {
    const content = root.querySelector('#character-levelup-content');
    if (!content) return;

    const className = preview.className || preview.classId || 'Class';
    const currentLevel = safeInt(preview.currentLevel, 1);
    const nextLevel = safeInt(preview.nextLevel, currentLevel + 1);
    const hpGained = preview.hpGained || 1;
    const hitDie = preview.hitDie || 6;
    const conPart = hpGained - (Math.floor(hitDie / 2) + 1);
    const currentProf = safeInt(preview.currentProficiencyBonus, Math.ceil(currentLevel / 4) + 1);
    const nextProf = safeInt(preview.newProficiencyBonus, Math.ceil(nextLevel / 4) + 1);
    const fromTotalLevel = safeInt(preview?.nextLevelSummary?.fromTotalLevel, currentLevel);
    const toTotalLevel = safeInt(preview?.nextLevelSummary?.toTotalLevel, nextLevel);
    const spellPlan = preview && preview.spellChoices && typeof preview.spellChoices === 'object' ? preview.spellChoices : null;

    const features = Array.isArray(preview.newFeatures) ? preview.newFeatures : [];
    const featuresHtml = features.length
      ? features.map(function (feature) {
        const choices = Array.isArray(feature.choices) ? feature.choices : [];
        const tags = classifyFeature(feature);
        const featureSummary = feature.summary || feature.shortSummary || '';
        const choiceCards = choices.length
          ? choiceCompareIntro(feature, choices) + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin-top:10px">'
            + choices.map(function (choice) {
              const id = String(choice.id || '').toLowerCase();
              const isActive = modalState.featureChoices[String(feature.id)] === id;
              const profile = inferChoiceProfile(feature, choice, preview);
              return '<button type="button" class="lvlup-choice-card lvlup-option-card ' + (isActive ? 'active' : '') + '" data-feature-choice="' + escHtml(String(feature.id)) + '" data-choice-id="' + escHtml(id) + '">'
                + '<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">'
                + '  <div><div style="font-weight:700;font-size:.95rem">' + escHtml(choice.name || id) + '</div><div class="lvlup-meta" style="margin-top:3px">' + escHtml(profile.role || 'Option') + '</div></div>'
                + '  <span class="lvlup-pill" style="margin:0">' + escHtml(isActive ? 'Selected' : 'Compare') + '</span>'
                + '</div>'
                + (choice.summary || choice.description ? '<div style="font-size:.78rem;font-weight:700;color:#dffef8;margin-top:8px">' + escHtml(choice.summary || choice.description || '') + '</div>' : '')
                + '<div class="lvlup-option-block"><div class="lvlup-option-label">Fantasy</div><div class="lvlup-option-text">' + escHtml(profile.fantasy || '') + '</div></div>'
                + '<div class="lvlup-option-block"><div class="lvlup-option-label">Best fit now</div><div class="lvlup-option-text">' + escHtml(profile.now || '') + '</div></div>'
                + '<div class="lvlup-option-block"><div class="lvlup-option-label">Unlocks later</div><div class="lvlup-option-text">' + escHtml(profile.later || '') + '</div></div>'
                + '</button>';
            }).join('')
            + '</div>'
          : '';
        return '<div class="lvlup-card">'
          + '<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap">'
          + '  <div>'
          + '    <div class="lvlup-feature-name">' + escHtml(feature.displayName || feature.id || 'Feature') + '</div>'
          + '    ' + (featureSummary ? '<div style="font-size:.8rem;font-weight:700;color:#dffef8;margin-top:3px">' + escHtml(featureSummary) + '</div>' : '')
          + '  </div>'
          + '  <div>' + tags.map(function (tag) { return '<span class="lvlup-pill">' + escHtml(tag) + '</span>'; }).join('') + '</div>'
          + '</div>'
          + '<div style="font-size:.85rem;opacity:.9;margin-top:6px;line-height:1.45">' + escHtml(feature.description || 'No description provided.') + '</div>'
          + featureMeaningBlock(feature)
          + (choices.length ? '<div style="font-size:.76rem;opacity:.82;margin-top:8px">Choose one option for this level-up. ' + escHtml(featureChoiceLead(feature)) + '</div>' : '')
          + choiceCards
          + '</div>';
      }).join('')
      : '<div style="font-size:.83rem;opacity:.82">No class features listed for this level.</div>';

    const featRows = modalState.featsCatalog
      .filter(function (row) {
        if (!modalState.featSearch) return true;
        return JSON.stringify(row || {}).toLowerCase().indexOf(modalState.featSearch.toLowerCase()) >= 0;
      })
      .map(function (row) {
        const featId = String(row.id || '').toLowerCase();
        const prereq = row.prerequisite || '';
        const active = modalState.featChoice === featId;
        return '<button type="button" class="lvlup-choice-card ' + (active ? 'active' : '') + '" data-feat-id="' + escHtml(featId) + '" style="text-align:left">'
          + '<div style="display:flex;justify-content:space-between;gap:10px">'
          + '<span style="font-weight:600">' + escHtml(row.displayName || featId) + '</span>'
          + '<span style="font-size:.72rem;opacity:.6">' + escHtml(prereq ? ('Prereq: ' + prereq) : 'No prerequisite') + '</span>'
          + '</div>'
          + '<div style="font-size:.76rem;opacity:.85;margin-top:4px">' + escHtml(row.description || '') + '</div>'
          + '</button>';
      }).join('');

    const asiHtml = preview.isAsiLevel
      ? '<section class="lvlup-card">'
        + '<div class="lvlup-title">Choices — ASI / Feat Picker</div>'
        + '<div style="display:grid;grid-template-columns:1fr;gap:8px">'
        + '  <div class="lvlup-asi-card ' + (modalState.asiMode === 'plus2' ? 'active' : '') + '" data-asi-mode="plus2">'
        + '    <div style="font-weight:600">+2 to one ability</div>'
        + '    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">'
        + ABILITIES.map(function (ab) { return '<button type="button" class="lvlup-ability-btn ' + (modalState.asiPlus2Ability === ab ? 'active' : '') + '" data-asi-plus2="' + ab + '">' + abilityLabel(ab) + '</button>'; }).join('')
        + '    </div>'
        + '  </div>'
        + '  <div class="lvlup-asi-card ' + (modalState.asiMode === 'plus1x2' ? 'active' : '') + '" data-asi-mode="plus1x2">'
        + '    <div style="font-weight:600">+1 to two different abilities</div>'
        + '    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">'
        + ABILITIES.map(function (ab) { return '<button type="button" class="lvlup-ability-btn ' + (modalState.asiPlus1Abilities.indexOf(ab) >= 0 ? 'active' : '') + '" data-asi-plus1="' + ab + '">' + abilityLabel(ab) + '</button>'; }).join('')
        + '    </div>'
        + '  </div>'
        + '  <div class="lvlup-asi-card ' + (modalState.asiMode === 'feat' ? 'active' : '') + '" data-asi-mode="feat">'
        + '    <div style="font-weight:600">Take a Feat</div>'
        + '    <input id="character-levelup-feat-search" type="search" value="' + escHtml(modalState.featSearch) + '" placeholder="Search feats..." style="margin-top:7px;width:100%;padding:7px;border-radius:6px;border:1px solid rgba(0,229,204,.25);background:#0d1113;color:#ddf8f5" />'
        + '    <div style="display:grid;gap:6px;margin-top:7px;max-height:220px;overflow:auto">' + (featRows || '<div style="font-size:.8rem;opacity:.75">No feats match.</div>') + '</div>'
        + '  </div>'
        + '</div>'
        + '</section>'
      : '';

    const spellSlotsHtml = preview.hasNewSpellSlots
      ? '<section class="lvlup-card">'
        + '<div class="lvlup-title">Automatic Gains — Spell Slots (Before / After)</div>'
        + '<table style="width:100%;border-collapse:collapse;font-size:.84rem">'
        + '<thead><tr><th style="text-align:left;padding:4px 8px">Slot</th><th style="text-align:left;padding:4px 8px">Current</th><th style="text-align:left;padding:4px 8px">New</th></tr></thead>'
        + '<tbody>' + slotRowsHtml(preview.currentSpellSlots || {}, preview.newSpellSlots || {}) + '</tbody></table>'
        + '</section>'
      : '';

    const currentMechanics = normalizeMechanics(preview.currentClassMechanics || {});
    const newMechanics = normalizeMechanics(preview.classMechanics || {});
    const mechanicKeys = Array.from(new Set(Object.keys(currentMechanics).concat(Object.keys(newMechanics)))).sort();
    const mechanicsRows = mechanicKeys.map(function (key) {
      const before = safeInt(currentMechanics[key], 0);
      const after = safeInt(newMechanics[key], 0);
      const delta = after - before;
      return {
        label: mechanicLabel(key),
        before: String(before),
        after: String(after),
        delta: (delta >= 0 ? '+' : '') + String(delta),
      };
    });
    const automaticRows = [
      { label: 'Class Level', before: String(currentLevel), after: String(nextLevel), delta: '+' + String(Math.max(0, nextLevel - currentLevel)) },
      { label: 'Total Level', before: String(fromTotalLevel), after: String(toTotalLevel), delta: '+' + String(Math.max(0, toTotalLevel - fromTotalLevel)) },
      { label: 'Proficiency Bonus', before: '+' + String(currentProf), after: '+' + String(nextProf), delta: (nextProf - currentProf >= 0 ? '+' : '') + String(nextProf - currentProf) },
      { label: 'Level-Up HP Gain', before: '+0', after: '+' + String(hpGained), delta: '+' + String(hpGained) },
    ].concat(mechanicsRows);

    const step = modalState.activeStep || 'automatic';
    const isStepAutomatic = step === 'automatic';
    const isStepChoices = step === 'choices';
    const isStepReview = step === 'review';
    const guide = classGuide(preview);
    const choiceRequirementRows = [];
    features.forEach(function (feature) {
      if (Array.isArray(feature.choices) && feature.choices.length) {
        const selected = modalState.featureChoices[String(feature.id)] || '';
        choiceRequirementRows.push((feature.displayName || feature.id || 'Feature') + ': ' + (selected || 'Choose one'));
      }
    });
    if (preview.isAsiLevel) {
      choiceRequirementRows.push('ASI / Feat: ' + (modalState.asiMode === 'feat' ? (modalState.featChoice || 'Choose a feat') : (modalState.asiMode === 'plus1x2' ? ((modalState.asiPlus1Abilities.length ? modalState.asiPlus1Abilities.map(abilityLabel).join(' + ') : 'Choose two abilities')) : ('+' + '2 ' + abilityLabel(modalState.asiPlus2Ability || 'str')))));
    }
    const subclassChoice = preview && preview.subclassChoice && typeof preview.subclassChoice === 'object' ? preview.subclassChoice : null;
    if (subclassChoice && subclassChoice.required) {
      const selectedOption = (Array.isArray(subclassChoice.options) ? subclassChoice.options : []).find(function (row) {
        return String(row && row.id || '').trim().toLowerCase() === String(modalState.subclassChoice || '').toLowerCase();
      });
      choiceRequirementRows.push('Subclass: ' + (selectedOption ? (selectedOption.name || selectedOption.id || modalState.subclassChoice) : 'Choose one'));
    }
    if (spellPlan) {
      if (safeInt(spellPlan.cantripPicksRequired, 0) > 0) choiceRequirementRows.push('Cantrips: ' + String(modalState.spellCantripAdds.length) + ' / ' + String(safeInt(spellPlan.cantripPicksRequired, 0)));
      if (safeInt(spellPlan.levelledPicksRequired, 0) > 0) choiceRequirementRows.push('Levelled spells: ' + String(modalState.spellLevelledAdds.length) + ' / ' + String(safeInt(spellPlan.levelledPicksRequired, 0)));
      if (safeInt(spellPlan.magicalSecretsPicksRequired, 0) > 0) choiceRequirementRows.push('Magical Secrets: ' + String(modalState.spellMagicalSecretsAdds.length) + ' / ' + String(safeInt(spellPlan.magicalSecretsPicksRequired, 0)));
      if (spellPlan.swapAllowed) choiceRequirementRows.push('Optional swap: ' + ((modalState.spellSwapDrop && modalState.spellSwapLearn) ? 'Ready' : 'Not selected'));
    }

    content.innerHTML = ''
      + '<section class="lvlup-card">'
      + '<div class="lvlup-title">Guided Flow</div>'
      + '<div class="lvlup-step-summary" style="margin:0 0 10px 0">'
      + '  <div class="lvlup-card" style="padding:10px;background:rgba(0,229,204,.05)"><div class="lvlup-subtitle">Current</div><div style="font-size:1.05rem;font-weight:700">Level ' + escHtml(currentLevel) + ' ' + escHtml(className) + '</div></div>'
      + '  <div class="lvlup-card" style="padding:10px;background:rgba(0,229,204,.05)"><div class="lvlup-subtitle">Next</div><div style="font-size:1.05rem;font-weight:700">Level ' + escHtml(nextLevel) + '</div></div>'
      + '  <div class="lvlup-card" style="padding:10px;background:rgba(0,229,204,.05)"><div class="lvlup-subtitle">HP Gain</div><div style="font-size:1.05rem;font-weight:700">+' + escHtml(hpGained) + '</div></div>'
      + '  <div class="lvlup-card" style="padding:10px;background:rgba(0,229,204,.05)"><div class="lvlup-subtitle">Choices</div><div style="font-size:1.05rem;font-weight:700">' + escHtml(choiceRequirementRows.length || 0) + '</div></div>'
      + '</div>'
      + '<div style="display:flex;flex-wrap:wrap;gap:8px">'
      + '<button type="button" class="lvlup-choice-card lvlup-step-button ' + (isStepAutomatic ? 'active' : '') + '" data-levelup-step="automatic" style="flex:1"><div style="font-weight:600">Step 1 — Automatic Gains</div><div style="font-size:.74rem;opacity:.8">See the level-based changes you gain automatically.</div></button>'
      + '<button type="button" class="lvlup-choice-card lvlup-step-button ' + (isStepChoices ? 'active' : '') + '" data-levelup-step="choices" style="flex:1"><div style="font-weight:600">Step 2 — Choices</div><div style="font-size:.74rem;opacity:.8">Resolve required picks only.</div></button>'
      + '<button type="button" class="lvlup-choice-card lvlup-step-button ' + (isStepReview ? 'active' : '') + '" data-levelup-step="review" style="flex:1"><div style="font-weight:600">Step 3 — Finish</div><div style="font-size:.74rem;opacity:.8">Review your choices before applying the level up.</div></button>'
      + '</div>'
      + '</section>'
      + '<section class="lvlup-card">'
      + '<div class="lvlup-title">Level Banner</div>'
      + '<div class="lvlup-banner">Level ' + escHtml(nextLevel) + ' ' + escHtml(className) + '</div>'
      + '<div style="margin-top:4px;font-size:.9rem;opacity:.92">+' + escHtml(hpGained) + ' HP (d' + escHtml(hitDie) + ' average + CON modifier ' + (conPart >= 0 ? '+' : '') + escHtml(conPart) + ')</div>'
      + '</section>'
      + (guide ? '<section class="lvlup-card"><div class="lvlup-title">' + escHtml(guide.title) + '</div><div style="font-size:.84rem;opacity:.9">' + escHtml(guide.summary) + '</div><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">' + guide.checks.map(function (item) { return '<span class="lvlup-pill">' + escHtml(item) + '</span>'; }).join('') + '</div></section>' : '')
      + (isStepAutomatic ? '<section class="lvlup-card"><div class="lvlup-title">Automatic Gains — Before / After</div>' + diffRowsHtml(automaticRows) + '</section>' + spellSlotsHtml : '')
      + (isStepChoices
        ? renderSubclassChoiceSection(preview)
          + (classChoiceCoach(preview) ? guidancePanelHtml(classChoiceCoach(preview).title, 'Use this step to choose the upgrades that actually change how your turns feel.', classChoiceCoach(preview).bullets) : '')
          + choiceRuleSummaryHtml(preview, features, spellPlan)
          + '<section class="lvlup-card"><div class="lvlup-title">Choices — Feature Picks</div><div style="font-size:.84rem;opacity:.9;margin-bottom:8px">Read each card as: what you gain now, what it costs to use, and how it changes your normal turn plan.</div>' + featuresHtml + '</section>'
          + asiHtml
          + renderSpellChoiceSection(preview, spellPlan)
        : '')
      + (isStepReview
        ? '<section class="lvlup-card"><div class="lvlup-title">Finish</div>'
          + '<div style="font-size:.84rem;opacity:.9;margin-bottom:8px">What changes immediately after confirm: automatic gains and player choices are separated so you can quickly see what changes now and what still needs your input.</div>'
          + '<div class="lvlup-confirm-grid">'
          + '  <div class="lvlup-confirm-card"><div class="lvlup-subtitle">What updates now</div>' + reviewList([
          'Your class level becomes ' + String(nextLevel) + ' for ' + String(className) + '.',
          'Your total level becomes ' + String(toTotalLevel) + '.',
          'Your sheet and token should gain +' + String(hpGained) + ' HP.',
          'Any selected level-up choices are persisted into the character profile.'
          ], 'No immediate changes listed.') + '</div>'
          + '  <div class="lvlup-confirm-card"><div class="lvlup-subtitle">Automatic gains</div>' + reviewList(automaticRows.map(function (row) { return row.label + ': ' + row.before + ' → ' + row.after; }), 'No automatic changes.') + '</div>'
          + '  <div class="lvlup-confirm-card"><div class="lvlup-subtitle">Choices still needed</div>' + reviewList(choiceRequirementRows, 'No choices are required at this level.') + '</div>'
          + '  <div class="lvlup-confirm-card"><div class="lvlup-subtitle">Spell plan</div>' + reviewList([
          spellPlan ? ('Mode: ' + String(spellPlan.mode || 'known')) : '',
          spellPlan && safeInt(spellPlan.cantripPicksRequired, 0) > 0 ? ('Cantrips selected: ' + String(modalState.spellCantripAdds.length) + ' / ' + String(safeInt(spellPlan.cantripPicksRequired, 0))) : '',
          spellPlan && safeInt(spellPlan.levelledPicksRequired, 0) > 0 ? ('Levelled spells selected: ' + String(modalState.spellLevelledAdds.length) + ' / ' + String(safeInt(spellPlan.levelledPicksRequired, 0))) : '',
          spellPlan && safeInt(spellPlan.magicalSecretsPicksRequired, 0) > 0 ? ('Magical Secrets selected: ' + String(modalState.spellMagicalSecretsAdds.length) + ' / ' + String(safeInt(spellPlan.magicalSecretsPicksRequired, 0))) : '',
          spellPlan && spellPlan.swapAllowed ? ('Swap ready: ' + ((modalState.spellSwapDrop && modalState.spellSwapLearn) ? 'Yes' : 'No')) : '',
          spellPlan && spellPlan.nextHighestSpellLevel ? ('Highest legal spell tier after level: ' + String(spellLevelLabel(spellPlan.nextHighestSpellLevel))) : ''
          ], 'No spell choices are required at this level.') + '</div>'
          + '</div>'
          + '</section>'
        : '');

    const choicesNeeded = !!preview.requiresChoices;
    let canApply = !choicesNeeded;
    if (choicesNeeded) {
      canApply = true;
      features.forEach(function (feature) {
        if (Array.isArray(feature.choices) && feature.choices.length && !modalState.featureChoices[String(feature.id)]) canApply = false;
      });
      if (preview.isAsiLevel) {
        if (modalState.asiMode === 'feat') canApply = canApply && !!modalState.featChoice;
        else if (modalState.asiMode === 'plus1x2') canApply = canApply && modalState.asiPlus1Abilities.length === 2;
      }
      if (subclassChoice && subclassChoice.required) {
        canApply = canApply && !!modalState.subclassChoice;
      }
      if (spellPlan) {
        if (safeInt(spellPlan.cantripPicksRequired, 0) > 0) canApply = canApply && modalState.spellCantripAdds.length === safeInt(spellPlan.cantripPicksRequired, 0);
        if (safeInt(spellPlan.levelledPicksRequired, 0) > 0) canApply = canApply && modalState.spellLevelledAdds.length === safeInt(spellPlan.levelledPicksRequired, 0);
        if (safeInt(spellPlan.magicalSecretsPicksRequired, 0) > 0) canApply = canApply && modalState.spellMagicalSecretsAdds.length === safeInt(spellPlan.magicalSecretsPicksRequired, 0);
        const partialSwap = (!!modalState.spellSwapDrop && !modalState.spellSwapLearn) || (!modalState.spellSwapDrop && !!modalState.spellSwapLearn);
        const duplicateSwapLearn = !!modalState.spellSwapLearn && modalState.spellLevelledAdds.indexOf(modalState.spellSwapLearn) >= 0;
        if (partialSwap || duplicateSwapLearn) canApply = false;
      }
    }
    setApplyEnabled(root, canApply, 'Level Up to ' + String(nextLevel));

    bindDynamicEvents(root, preview);
  }

  function bindDynamicEvents(root, preview) {
    root.querySelectorAll('[data-levelup-step]').forEach(function (el) {
      el.addEventListener('click', function () {
        modalState.activeStep = String(el.getAttribute('data-levelup-step') || 'automatic');
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-feature-choice]').forEach(function (el) {
      el.addEventListener('click', function () {
        const featureId = String(el.getAttribute('data-feature-choice') || '');
        const choiceId = String(el.getAttribute('data-choice-id') || '');
        if (!featureId || !choiceId) return;
        modalState.featureChoices[featureId] = choiceId;
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-subclass-choice]').forEach(function (el) {
      el.addEventListener('click', function () {
        const subclassId = String(el.getAttribute('data-subclass-choice') || '').trim().toLowerCase();
        if (!subclassId) return;
        modalState.subclassChoice = subclassId;
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-asi-mode]').forEach(function (el) {
      el.addEventListener('click', function () {
        modalState.asiMode = String(el.getAttribute('data-asi-mode') || 'plus2');
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-asi-plus2]').forEach(function (el) {
      el.addEventListener('click', function (evt) {
        evt.stopPropagation();
        modalState.asiMode = 'plus2';
        modalState.asiPlus2Ability = String(el.getAttribute('data-asi-plus2') || 'str');
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-asi-plus1]').forEach(function (el) {
      el.addEventListener('click', function (evt) {
        evt.stopPropagation();
        modalState.asiMode = 'plus1x2';
        const ability = String(el.getAttribute('data-asi-plus1') || '');
        const has = modalState.asiPlus1Abilities.indexOf(ability) >= 0;
        if (has) modalState.asiPlus1Abilities = modalState.asiPlus1Abilities.filter(function (v) { return v !== ability; });
        else if (modalState.asiPlus1Abilities.length < 2) modalState.asiPlus1Abilities.push(ability);
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-feat-id]').forEach(function (el) {
      el.addEventListener('click', function (evt) {
        evt.stopPropagation();
        modalState.asiMode = 'feat';
        modalState.featChoice = String(el.getAttribute('data-feat-id') || '');
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-spell-pick]').forEach(function (el) {
      el.addEventListener('click', function () {
        const pickType = String(el.getAttribute('data-spell-pick') || '');
        const spellId = String(el.getAttribute('data-spell-id') || '');
        const spellPlan = preview && preview.spellChoices && typeof preview.spellChoices === 'object' ? preview.spellChoices : null;
        if (!pickType || !spellId || !spellPlan) return;
        if (pickType === 'cantrip') modalState.spellCantripAdds = togglePick(modalState.spellCantripAdds, spellId, safeInt(spellPlan.cantripPicksRequired, 0) || null);
        else if (pickType === 'levelled') modalState.spellLevelledAdds = togglePick(modalState.spellLevelledAdds, spellId, safeInt(spellPlan.levelledPicksRequired, 0) || null);
        else if (pickType === 'magical-secret') modalState.spellMagicalSecretsAdds = togglePick(modalState.spellMagicalSecretsAdds, spellId, safeInt(spellPlan.magicalSecretsPicksRequired, 0) || null);
        renderPreview(root, preview);
      });
    });

    root.querySelectorAll('[data-spell-swap]').forEach(function (el) {
      el.addEventListener('click', function () {
        const swapType = String(el.getAttribute('data-spell-swap') || '');
        const spellId = String(el.getAttribute('data-spell-id') || '');
        if (!swapType || !spellId) return;
        if (swapType === 'drop') modalState.spellSwapDrop = (modalState.spellSwapDrop === spellId ? '' : spellId);
        if (swapType === 'learn') modalState.spellSwapLearn = (modalState.spellSwapLearn === spellId ? '' : spellId);
        renderPreview(root, preview);
      });
    });

    const spellSearch = root.querySelector('#character-levelup-spell-search');
    if (spellSearch) {
      spellSearch.addEventListener('input', function () {
        modalState.spellSearch = spellSearch.value || '';
        renderPreview(root, preview);
      });
    }

    root.querySelectorAll('[data-spell-filter]').forEach(function (el) {
      el.addEventListener('click', function () {
        modalState.spellFilterLevel = String(el.getAttribute('data-spell-filter') || 'all');
        renderPreview(root, preview);
      });
    });

    const featSearch = root.querySelector('#character-levelup-feat-search');
    if (featSearch) {
      featSearch.addEventListener('input', function () {
        modalState.asiMode = 'feat';
        modalState.featSearch = featSearch.value || '';
        renderPreview(root, preview);
      });
    }
  }

  async function applyLevelup(root) {
    if (modalState.applying) return;
    const opts = modalState.options || {};
    const profile = opts.profile && typeof opts.profile === 'object' ? opts.profile : {};
    const preview = modalState.preview || {};
    if (!opts.sessionId) throw new Error('Missing session id for level up apply.');

    modalState.applying = true;
    setApplyEnabled(root, false, 'Applying…');
    setStatus(root, 'Applying level-up and saving profile…', 'info');
    try {
      const payload = {
        session_id: opts.sessionId,
        character_document: opts.characterDocument || {},
        profile_id: profile.id || '',
        choices: buildChoicesPayload(preview),
      };
      const res = await fetch('/api/character/levelup/apply', {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const data = await res.json().catch(function () { return {}; });
      if (!res.ok || !data || data.ok !== true) throw new Error((data && data.detail) || 'Level-up apply failed');
      if (data.nativeCharacter && typeof data.nativeCharacter === 'object') opts.characterDocument = data.nativeCharacter;
      if (data.nativeCharacter && typeof data.nativeCharacter === 'object' && global._charSheet && typeof global._charSheet === 'object') {
        Object.assign(global._charSheet, data.nativeCharacter);
      }
      const nextSpellState = (data && data.nativeCharacter && data.nativeCharacter.spellState && typeof data.nativeCharacter.spellState === 'object')
        ? data.nativeCharacter.spellState
        : ((data && data.spellState && typeof data.spellState === 'object') ? data.spellState : null);
      if (nextSpellState && global._charSheet && typeof global._charSheet === 'object') {
        global._charSheet.spellState = {
          known: uniqueIds(nextSpellState.known || []),
          prepared: uniqueIds(nextSpellState.prepared || []),
        };
      }
      modalState.options = opts;
      setStatus(root, 'Level-up applied and saved.', 'success');
      try {
        global.dispatchEvent(new CustomEvent('character:spell-state-updated', {
          detail: { source: 'levelup-apply', spellState: nextSpellState || null, nativeCharacter: data.nativeCharacter || null }
        }));
      } catch (_) {}
      if (typeof global.requestCharacterBookOverviewRender === 'function') {
        try { global.requestCharacterBookOverviewRender('levelup-apply'); } catch (_) {}
      }
      if (typeof opts.onApplied === 'function') {
        try { opts.onApplied(data); } catch (_) {}
      }
      const freshPreview = await fetchPreview({ session_id: opts.sessionId, character_document: opts.characterDocument || {} });
      modalState.preview = freshPreview;
      modalState.spellCantripAdds = [];
      modalState.spellLevelledAdds = [];
      modalState.spellMagicalSecretsAdds = [];
      modalState.spellSwapDrop = '';
      modalState.spellSwapLearn = '';
      renderPreview(root, freshPreview);
    } finally {
      modalState.applying = false;
    }
  }

  async function open(options) {
    const opts = options && typeof options === 'object' ? options : {};
    modalState.options = opts;
    modalState.preview = null;
    modalState.applying = false;
    modalState.featureChoices = {};
    modalState.asiMode = 'plus2';
    modalState.asiPlus2Ability = 'str';
    modalState.asiPlus1Abilities = [];
    modalState.featChoice = '';
    modalState.featSearch = '';
    modalState.activeStep = 'automatic';
    modalState.spellCantripAdds = [];
    modalState.spellLevelledAdds = [];
    modalState.spellMagicalSecretsAdds = [];
    modalState.spellSwapDrop = '';
    modalState.spellSwapLearn = '';
    modalState.spellSearch = '';
    modalState.spellFilterLevel = 'all';
    modalState.subclassChoice = '';

    const root = ensureModalDom();
    root.style.display = 'flex';
    setStatus(root, 'Preparing level-up preview…', 'info');
    setApplyEnabled(root, false, 'Level Up');

    try {
      const payload = { session_id: opts.sessionId || '', character_document: opts.characterDocument || {} };
      const results = await Promise.all([fetchPreview(payload), fetchFeats()]);
      modalState.preview = results[0];
      modalState.featsCatalog = Array.isArray(results[1]) ? results[1] : [];
      renderPreview(root, modalState.preview);
      setStatus(root, '', 'success');
    } catch (err) {
      setStatus(root, (err && err.message) || 'Unable to load level-up preview.', 'error');
      setApplyEnabled(root, false, 'Level Up');
    }
  }

  global.CharacterLevelupModal = { open };
})(window);
