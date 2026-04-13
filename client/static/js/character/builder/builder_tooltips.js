(function initBuilderTooltips(global) {
  'use strict';

  var TOOLTIPS = {
    'species': {
      title: 'What is a Species?',
      body: 'Your species (called "race" in older editions) determines your character\'s ancestry. It grants permanent traits, affects your speed and senses, and shapes your innate abilities. Species traits don\'t change as you level up.'
    },
    'class': {
      title: 'What is a Class?',
      body: 'Your class is your character\'s profession and primary power source. A Fighter masters weapons; a Wizard commands arcane magic; a Rogue excels at stealth and precision. Your class determines which abilities you gain as you level up, your hit points, and whether you can cast spells.'
    },
    'abilities': {
      title: 'What are Ability Scores?',
      body: 'Six scores \u2014 Strength, Dexterity, Constitution, Intelligence, Wisdom, and Charisma \u2014 measure your natural aptitudes. Each score generates a modifier: (score \u2212 10) \u00f7 2, rounded down. STR 15 = +2 modifier. Modifiers are what actually affect your dice rolls.'
    },
    'standard-array': {
      title: 'Standard Array',
      body: 'The standard array is 15, 14, 13, 12, 10, 8 \u2014 assign these six values to your six abilities in any order you choose. Recommended for new players because it creates a fair, balanced character without luck.'
    },
    'point-buy': {
      title: 'Point Buy',
      body: 'You have 27 points to spend. Every ability starts at 8 and costs points to raise. Maximum score before species bonuses is 15. Scores of 14 and 15 cost extra: 14 costs 7 total, 15 costs 9 total. Great for precise character optimization.'
    },
    'hit-die': {
      title: 'Hit Die',
      body: 'Your hit die determines hit points per level. At 1st level you get the maximum value. At later levels you roll it (or take the average) and add your Constitution modifier. Barbarians have d12 (most HP), Wizards have d6 (fewest HP).'
    },
    'saving-throws': {
      title: 'Saving Throws',
      body: 'Saving throws represent your ability to resist effects like fireballs, charm spells, and pit traps. Each class is proficient in two saving throw types, adding their proficiency bonus to those rolls. Fighters save with Strength and Constitution; Wizards with Intelligence and Wisdom.'
    },
    'subclass': {
      title: 'What is a Subclass?',
      body: 'At 3rd level (or 1st for Warlocks), you choose a subclass \u2014 a specialization within your class. A Fighter chooses between Battlemaster (tactical maneuvers), Champion (raw power), and Eldritch Knight (fighter + wizard spells). Subclasses dramatically shape your playstyle.'
    },
    'asi': {
      title: 'Ability Score Improvement',
      body: 'At certain levels (4, 8, 12, 16, 19 for most classes), you can raise one ability score by 2, raise two different scores by 1 each, or take a Feat instead. Feats are powerful special abilities that can define your combat style.'
    },
    'feat': {
      title: 'What is a Feat?',
      body: 'Feats are optional special abilities taken instead of an Ability Score Improvement. Lucky gives you 3 rerolls per day. Great Weapon Master lets you trade \u22125 to hit for +10 damage. Sentinel stops fleeing enemies. Feats are powerful choices that define your style.'
    },
    'proficiency-bonus': {
      title: 'Proficiency Bonus',
      body: 'Starts at +2 at level 1 and increases to +6 at level 17. Added to: attack rolls with weapons you\'re proficient with, spell attack rolls, saving throws your class is proficient in, and ability checks using skills or tools you\'re proficient with.'
    },
    'spellcasting': {
      title: 'How does Spellcasting work?',
      body: 'Spell casters use a spellcasting ability (INT for Wizards, WIS for Druids/Clerics, CHA for Bards/Sorcerers/Warlocks/Paladins). Spell Save DC = 8 + proficiency + casting modifier. Spell Attack Bonus = proficiency + casting modifier. Higher ability scores make your spells harder to resist.'
    },
    'background': {
      title: 'What is a Background?',
      body: 'Your background defines who your character was before becoming an adventurer. Each background grants two skill proficiencies, one tool proficiency, a starting language, an Origin feat, and starting equipment and gold. The Origin feat is one of the most powerful benefits \u2014 choose a background that grants a feat that fits your build.'
    },
    'rage': {
      title: 'What is Rage?',
      body: 'Rage is the Barbarian\'s signature feature. As a Bonus Action, you enter a Rage that lasts 1 minute: +2 to STR damage rolls (scales to +4 at 16), resistance to bludgeoning/piercing/slashing damage, and you can\'t cast or concentrate on spells. Number of uses scales from 2 at level 1 to unlimited at level 20.'
    },
    'sneak-attack': {
      title: 'What is Sneak Attack?',
      body: 'The Rogue\'s signature burst damage. Once per turn, if you hit a creature with a finesse or ranged weapon and you either have Advantage on the roll OR an ally is adjacent to the target, you deal extra damage. Starts at 1d6 at level 1 and scales to 10d6 at level 19. This is why Rogues are terrifying.'
    },
    'bardic-inspiration': {
      title: 'What is Bardic Inspiration?',
      body: 'As a Bonus Action, grant a creature within 60 ft a Bardic Inspiration die. They can add it to any ability check, attack roll, or saving throw in the next 10 minutes. Starts as a d6 at level 1, scales to a d12 at level 15. Uses per long rest = your CHA modifier. At level 5, you recover uses on short rests too.'
    },
    'builder-basics': {
      title: 'Builder Help',
      body: 'Use this section to fill out your character details step by step. If you are unsure, focus on class identity first, then ability scores, and keep your first character simple.'
    }
  };

  function escHtml(v) {
    return String(v || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function showTooltip(key) {
    var tip = TOOLTIPS[key];
    if (!tip) return;
    closeTooltip();
    var overlay = document.createElement('div');
    overlay.id = 'builder-tooltip-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center';
    overlay.onclick = closeTooltip;
    var panel = document.createElement('div');
    panel.style.cssText = 'background:#1a2028;border:1px solid rgba(201,168,76,0.4);border-radius:16px;padding:24px;max-width:400px;margin:20px;position:relative';
    panel.onclick = function(e) { e.stopPropagation(); };
    panel.innerHTML = '<div style="font-family:\'Cinzel\',serif;font-size:1rem;color:#E8C97A;margin-bottom:10px;padding-right:24px">' + escHtml(tip.title) + '</div>'
      + '<div style="font-size:0.82rem;color:#a89f8e;line-height:1.75">' + escHtml(tip.body) + '</div>'
      + '<button onclick="window.BuilderTooltips.close()" style="position:absolute;top:12px;right:14px;background:none;border:none;color:#6b6258;font-size:1.3rem;cursor:pointer;line-height:1">\u00d7</button>';
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
  }

  function closeTooltip() {
    var el = document.getElementById('builder-tooltip-overlay');
    if (el) el.remove();
  }

  global.BuilderTooltips = { show: showTooltip, showTooltip: showTooltip, close: closeTooltip, TOOLTIPS: TOOLTIPS };
})(window);
