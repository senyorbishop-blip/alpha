(function initCharacterBuilderStepAbilities(global) {
  const ABILITY_KEYS = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];

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

  function safeInt(value, fallback) {
    var parsed = parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function abilityModifier(score) {
    return Math.floor((safeInt(score, 10) - 10) / 2);
  }

  function pointBuyCost(score) {
    var s = safeInt(score, 8);
    if (s <= 8) return 0;
    if (s === 9) return 1;
    if (s === 10) return 2;
    if (s === 11) return 3;
    if (s === 12) return 4;
    if (s === 13) return 5;
    if (s === 14) return 7;
    if (s === 15) return 9;
    return 99;
  }

  function pointBuyRemaining(abilities) {
    var spent = ABILITY_KEYS.reduce(function sum(total, key) {
      return total + pointBuyCost(abilities[key]);
    }, 0);
    return 27 - spent;
  }

  function rollAbilityScore() {
    var dice = [];
    for (var i = 0; i < 4; i += 1) {
      dice.push(Math.floor(Math.random() * 6) + 1);
    }
    dice.sort(function desc(a, b) { return b - a; });
    return dice[0] + dice[1] + dice[2];
  }

  function applyStandardArray(context) {
    if (!context || typeof context.onSetField !== 'function') return;
    ABILITY_KEYS.forEach(function applyScore(key, idx) {
      context.onSetField(['abilities', key], STANDARD_ARRAY[idx]);
    });
  }

  function getClassBuildTips(draft) {
    var classId = String(draft && draft.class && draft.class.id || '').trim().toLowerCase();
    if (!classId) return null;
    var api = global.CharacterBuilderAPI;
    if (!api || typeof api.getCachedCatalog !== 'function') return null;
    var catalog = api.getCachedCatalog();
    var classes = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
    var classRow = classes.find(function findRow(row) {
      return String(row && row.id || '').trim().toLowerCase() === classId;
    }) || null;
    if (!classRow) return null;
    var tips = classRow.buildTips && typeof classRow.buildTips === 'object' ? classRow.buildTips : null;
    if (!tips) return null;
    return {
      className: String(classRow.displayName || classRow.id || '').trim(),
      primaryFocus: String(tips.primaryFocus || '').trim(),
      primaryReason: String(tips.primaryReason || '').trim(),
      secondaryFocus: String(tips.secondaryFocus || '').trim(),
      secondaryReason: String(tips.secondaryReason || '').trim(),
      avoidDump: String(tips.avoidDump || '').trim(),
      avoidDumpReason: String(tips.avoidDumpReason || '').trim(),
    };
  }

  function wireButtons(root, context) {
    if (!context || typeof context.onSetField !== 'function') return;

    var rollBtn = root.querySelector('[data-builder-roll-action="roll-abilities"]');
    if (rollBtn) {
      rollBtn.addEventListener('click', function onRollClick() {
        ABILITY_KEYS.forEach(function setAbility(key) {
          context.onSetField(['abilities', key], rollAbilityScore());
        });
      });
    }

    var arrayBtn = root.querySelector('[data-builder-array-action="apply-standard-array"]');
    if (arrayBtn) {
      arrayBtn.addEventListener('click', function onArrayClick() {
        applyStandardArray(context);
      });
    }

    var pointBuyBtn = root.querySelector('[data-builder-point-buy-action="reset-point-buy"]');
    if (pointBuyBtn) {
      pointBuyBtn.addEventListener('click', function onPointBuyReset() {
        ABILITY_KEYS.forEach(function setScore(key) {
          context.onSetField(['abilities', key], 8);
        });
      });
    }
  }

  /* -- Premium visual helpers ---------------------------------------- */

  function ensureBuilderStyles() {
    if (document.getElementById('character-builder-css')) return;
    var link = document.createElement('link');
    link.id = 'character-builder-css';
    link.rel = 'stylesheet';
    link.href = '/static/css/character-builder.css';
    document.head.appendChild(link);
  }

  function renderAbilityCard(key, value, mode, pointBuyRemaining) {
    var mod = abilityModifier(value);
    var cost = pointBuyCost(value);
    var modStr = mod >= 0 ? '+' + mod : String(mod);
    var modClass = mod > 0 ? 'pos' : mod < 0 ? 'neg' : '';
    var canIncrease = mode === 'point_buy'
      ? value < 15 && pointBuyRemaining >= (pointBuyCost(value + 1) - cost)
      : value < 20;
    var canDecrease = mode === 'point_buy' ? value > 8 : value > 3;
    return [
      '<div class="ability-block' + (value >= 14 ? ' boosted' : '') + '">',
      '<div class="ability-label">' + key.toUpperCase() + '</div>',
      '<div class="ability-mod ' + modClass + '">' + escHtml(modStr) + '</div>',
      '<div class="ability-score-box">',
      '<button class="ability-btn" data-ability-key="' + key + '" data-ability-delta="-1"' + (!canDecrease ? ' disabled' : '') + '>\u2212</button>',
      '<span class="ability-score-val">' + escHtml(String(value)) + '</span>',
      '<button class="ability-btn" data-ability-key="' + key + '" data-ability-delta="1"' + (!canIncrease ? ' disabled' : '') + '>+</button>',
      '</div>',
      mode === 'point_buy' ? '<div class="ability-cost-indicator">' + cost + 'pt</div>' : '',
      '</div>',
    ].join('');
  }

  function renderPointBuyBudget(remaining) {
    var pct = Math.max(0, (remaining / 27) * 100);
    var barColor = pct > 50 ? 'var(--cb-teal)' : pct > 20 ? 'var(--cb-gold)' : '#E74C3C';
    return [
      '<div class="point-buy-budget" id="builder-pb-budget"',
      (remaining <= 0 ? ' style="border-color:rgba(231,76,60,0.4)"' : ''),
      '>',
      '<div class="pb-points">' + remaining + '<span> pts</span></div>',
      '<div class="pb-label">Remaining points: ' + remaining + '</div>',
      '<div class="pb-bar"><div class="pb-bar-fill" style="width:' + pct + '%;background:' + barColor + '"></div></div>',
      '</div>',
    ].join('');
  }

  function renderMethodTabs(mode) {
    return [
      '<div class="ability-method-tabs">',
      [['standard_array', 'Standard Array'], ['point_buy', 'Point Buy'], ['roll', 'Roll (4d6)'], ['manual', 'Manual Entry']]
        .map(function(pair) {
          return '<button class="method-tab' + (mode === pair[0] ? ' active' : '') + '" data-method="' + pair[0] + '">' + pair[1] + '</button>';
        }).join(''),
      '</div>',
      '<select data-builder-path="abilityGenerationMode" style="display:none">',
      '<option value="manual"' + (mode === 'manual' ? ' selected' : '') + '>Manual Entry</option>',
      '<option value="standard_array"' + (mode === 'standard_array' ? ' selected' : '') + '>Standard Array</option>',
      '<option value="point_buy"' + (mode === 'point_buy' ? ' selected' : '') + '>Point Buy</option>',
      '<option value="roll"' + (mode === 'roll' ? ' selected' : '') + '>Roll (4d6 drop lowest)</option>',
      '</select>',
    ].join('');
  }

  var CLASS_BUILD_TIPS = {
    fighter:   { p: 'Strength',     pr: 'weapon attacks & Athletics',      s: 'Constitution', sr: 'HP and Concentration saves',          d: 'Intelligence',  dr: 'Rarely used by Fighters'          },
    wizard:    { p: 'Intelligence', pr: 'spell save DC & attack bonus',    s: 'Constitution', sr: 'Concentration saving throws',         d: 'Strength',      dr: 'Wizards avoid melee entirely'     },
    rogue:     { p: 'Dexterity',    pr: 'attacks, stealth, and AC',        s: 'Constitution', sr: 'HP for survivability',                d: 'Strength',      dr: 'DEX rogues ignore STR entirely'   },
    barbarian: { p: 'Strength',     pr: 'weapon attacks and grappling',    s: 'Constitution', sr: 'HP, Rage defense, Concentration',     d: 'Intelligence',  dr: 'Barbarians are primal, not clever'},
    paladin:   { p: 'Strength',     pr: 'weapon attacks and Athletics',    s: 'Charisma',     sr: 'Aura of Protection + spells',         d: 'Intelligence',  dr: 'Safe to keep at 10 or below'     },
    bard:      { p: 'Charisma',     pr: 'Bardic Inspiration, spells, social', s: 'Dexterity', sr: 'AC, initiative, and DEX saves',      d: 'Strength',      dr: 'Bards rarely pick up weapons'     },
    cleric:    { p: 'Wisdom',       pr: 'spell save DC, Channel Divinity', s: 'Constitution', sr: 'Concentration spells and HP',         d: 'Strength',      dr: 'Unless you took Protector Order'  },
    monk:      { p: 'Dexterity',    pr: 'AC, attacks, and initiative',     s: 'Wisdom',       sr: 'Unarmored Defense AC + saves',        d: 'Strength',      dr: 'Monks use DEX for everything STR' },
    warlock:   { p: 'Charisma',     pr: 'Eldritch Blast, spells',          s: 'Constitution', sr: 'Concentration and HP',                d: 'Strength',      dr: 'You have Eldritch Blast at range'  },
    druid:     { p: 'Wisdom',       pr: 'spell save DC, attack, Wild Shape',s: 'Constitution',sr: 'Concentration spells',                d: 'Strength',      dr: 'You can Wild Shape for physical tasks'},
    sorcerer:  { p: 'Charisma',     pr: 'spell save DC and attack bonus',  s: 'Constitution', sr: 'Concentration \u2014 critical for Metamagic', d: 'Strength',   dr: 'Never need to be near an enemy'   },
    ranger:    { p: 'Dexterity',    pr: 'attacks, AC, and stealth',        s: 'Wisdom',       sr: 'spell save DC and Nature/Survival',   d: 'Intelligence',  dr: 'Rarely used in Ranger gameplay'   },
  };

  function renderClassTip(draft) {
    var classId = String(draft && draft.class && draft.class.id || '').trim().toLowerCase();
    var tip = CLASS_BUILD_TIPS[classId];
    if (!tip) return '';
    var className = classId.charAt(0).toUpperCase() + classId.slice(1);
    return [
      '<div class="class-tip">',
      '<div class="class-tip-header">\uD83D\uDCA1 ' + escHtml(className) + ' Build Tips</div>',
      '<div class="class-tip-row"><div class="class-tip-ability">Priority 1 \u2014 <strong>' + escHtml(tip.p) + '</strong></div><div class="class-tip-reason">' + escHtml(tip.pr) + '</div></div>',
      '<div class="class-tip-row"><div class="class-tip-ability">Priority 2 \u2014 <strong>' + escHtml(tip.s) + '</strong></div><div class="class-tip-reason">' + escHtml(tip.sr) + '</div></div>',
      '<div class="class-tip-row"><div class="class-tip-ability">Safe Dump \u2014 <strong>' + escHtml(tip.d) + '</strong></div><div class="class-tip-reason">' + escHtml(tip.dr) + '</div></div>',
      '</div>',
    ].join('');
  }

  /* -- Step registration --------------------------------------------- */

  registerStep({
    id: 'abilities',
    label: 'Abilities',
    render: function renderAbilitiesStep(context) {
      ensureBuilderStyles();

      var draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      var abilities = draft.abilities && typeof draft.abilities === 'object' ? draft.abilities : {};
      var mode = draft.abilityGenerationMode || 'manual';
      var remaining = pointBuyRemaining(abilities);

      var abilityCards = ABILITY_KEYS.map(function(key) {
        var value = abilities[key] != null ? abilities[key] : 10;
        return renderAbilityCard(key, value, mode, remaining);
      }).join('');

      return [
        /* Screen header */
        '<div class="screen-header">',
        '<div class="screen-title">Set Ability Scores</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">These six scores define your character\u2019s strengths and weaknesses <button class="help-btn" data-help-topic="abilities">?</button></div>',
        '</div>',

        /* Method tabs */
        renderMethodTabs(mode),

        /* Two-column layout */
        '<div class="ability-layout">',
        '<div><div class="ability-grid-6">' + abilityCards + '</div></div>',
        '<div>',
        mode === 'point_buy' ? renderPointBuyBudget(remaining) : '',
        renderClassTip(draft),
        '</div>',
        '</div>',

        /* Hidden legacy buttons for wireButtons compatibility */
        '<div style="display:none">',
        '<button type="button" data-builder-roll-action="roll-abilities">Roll</button>',
        '<button type="button" data-builder-array-action="apply-standard-array">Array</button>',
        '<button type="button" data-builder-point-buy-action="reset-point-buy">Reset</button>',
        '</div>',
      ].join('');
    },
    bind: function bindAbilitiesStep(root, context) {
      wireButtons(root, context);

      /* Wire +/- ability buttons */
      if (context && typeof context.onSetField === 'function') {
        var abilityBtns = root.querySelectorAll('.ability-btn[data-ability-key]');
        for (var i = 0; i < abilityBtns.length; i++) {
          (function(btn) {
            btn.addEventListener('click', function onAbilityClick() {
              var key = btn.getAttribute('data-ability-key');
              var delta = safeInt(btn.getAttribute('data-ability-delta'), 0);
              var draft = context.draft && typeof context.draft === 'object' ? context.draft : {};
              var abilities = draft.abilities && typeof draft.abilities === 'object' ? draft.abilities : {};
              var current = abilities[key] != null ? safeInt(abilities[key], 10) : 10;
              var next = current + delta;
              var mode = draft.abilityGenerationMode || 'manual';
              var min = mode === 'point_buy' ? 8 : 3;
              var max = mode === 'point_buy' ? 15 : 20;
              if (next < min || next > max) return;
              if (mode === 'point_buy' && delta > 0) {
                var costDiff = pointBuyCost(next) - pointBuyCost(current);
                if (pointBuyRemaining(abilities) < costDiff) return;
              }
              context.onSetField(['abilities', key], next);
            });
          })(abilityBtns[i]);
        }
      }

      /* Wire method tab buttons */
      var methodTabs = root.querySelectorAll('.method-tab[data-method]');
      for (var t = 0; t < methodTabs.length; t++) {
        (function(tab) {
          tab.addEventListener('click', function onMethodClick() {
            var method = tab.getAttribute('data-method');
            if (!context || typeof context.onSetField !== 'function') return;

            /* Update hidden select */
            var sel = root.querySelector('select[data-builder-path="abilityGenerationMode"]');
            if (sel) sel.value = method;

            context.onSetField(['abilityGenerationMode'], method);

            if (method === 'standard_array') {
              applyStandardArray(context);
            } else if (method === 'point_buy') {
              ABILITY_KEYS.forEach(function(key) {
                context.onSetField(['abilities', key], 8);
              });
            } else if (method === 'roll') {
              ABILITY_KEYS.forEach(function(key) {
                context.onSetField(['abilities', key], rollAbilityScore());
              });
            }
          });
        })(methodTabs[t]);
      }

      /* Wire help button */
      var helpBtn = root.querySelector('.help-btn[data-help-topic]');
      if (helpBtn) {
        helpBtn.addEventListener('click', function() {
          if (typeof global.showHelp === 'function') {
            global.showHelp(helpBtn.dataset.helpTopic);
          }
        });
      }
    },
  });
})(window);
