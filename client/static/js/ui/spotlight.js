/**
 * ui/spotlight.js — Spotlight moment presentation & class-flavored styling.
 *
 * Provides a lightweight presentation layer that celebrates key player moments
 * (critical hits, clutch saves, boss kills, etc.) and adds class-flavored
 * visual accents without touching the combat engine.
 *
 * API:
 *   AppUISpotlight.fireSpotlight(opts)    — show a spotlight banner
 *   AppUISpotlight.classTagForName(name)  — resolve class key from name
 *   AppUISpotlight.getClassFlavor(key)    — get flavor text / icon / label
 *   AppUISpotlight.onCombatAttackResult(payload, env) — hook for attack results
 *   AppUISpotlight.onDiceResult(payload, env)         — hook for dice rolls
 *   AppUISpotlight.onCombatStateChange(state, prev, env) — hook for combat state
 *   AppUISpotlight.applyCombatEntryAccent(entryEl, combatant, env) — class tint
 */
(function () {
  'use strict';

  /* ── Throttle: prevent spotlight spam ──────────────────────────────────── */
  let _lastSpotlightAt = 0;
  const SPOTLIGHT_COOLDOWN_MS = 3200; // minimum gap between spotlights

  function _canFire() {
    const now = Date.now();
    if (now - _lastSpotlightAt < SPOTLIGHT_COOLDOWN_MS) return false;
    _lastSpotlightAt = now;
    return true;
  }

  /* ── Class flavor registry ─────────────────────────────────────────────── */
  const CLASS_FLAVOR = {
    fighter:   { key: 'fighter',   icon: '⚔️',  label: 'Fighter',   verb: 'strikes',   style: 'impact',      actionWord: 'Steel' },
    wizard:    { key: 'wizard',    icon: '🔮',  label: 'Wizard',    verb: 'invokes',    style: 'arcane',      actionWord: 'Arcana' },
    rogue:     { key: 'rogue',     icon: '🗡️',  label: 'Rogue',     verb: 'strikes',    style: 'precision',   actionWord: 'Shadow' },
    cleric:    { key: 'cleric',    icon: '✨',  label: 'Cleric',    verb: 'channels',   style: 'blessing',    actionWord: 'Grace' },
    ranger:    { key: 'ranger',    icon: '🏹',  label: 'Ranger',    verb: 'looses',     style: 'hunt',        actionWord: 'Hunt' },
    bard:      { key: 'bard',      icon: '🎵',  label: 'Bard',      verb: 'performs',   style: 'flourish',    actionWord: 'Verse' },
    paladin:   { key: 'paladin',   icon: '🛡️',  label: 'Paladin',   verb: 'smites',     style: 'valor',       actionWord: 'Oath' },
    druid:     { key: 'druid',     icon: '🌿',  label: 'Druid',     verb: 'calls upon', style: 'wild',        actionWord: 'Grove' },
    barbarian: { key: 'barbarian', icon: '🪓',  label: 'Barbarian', verb: 'unleashes',  style: 'fury',        actionWord: 'Fury' },
    sorcerer:  { key: 'sorcerer',  icon: '🌀',  label: 'Sorcerer',  verb: 'unleashes',  style: 'raw',         actionWord: 'Surge' },
    warlock:   { key: 'warlock',   icon: '👁',  label: 'Warlock',   verb: 'commands',   style: 'eldritch',    actionWord: 'Pact' },
    monk:      { key: 'monk',      icon: '👊',  label: 'Monk',      verb: 'channels',   style: 'discipline',  actionWord: 'Flow' },
  };

  const DEFAULT_FLAVOR = { key: 'default', icon: '⚡', label: 'Adventurer', verb: 'delivers', style: 'neutral', actionWord: 'Moment' };

  function classTagForName(className) {
    if (!className) return 'default';
    return (String(className).toLowerCase().split(' ')[0]) || 'default';
  }

  function getClassFlavor(classKey) {
    return CLASS_FLAVOR[classKey] || DEFAULT_FLAVOR;
  }

  /* ── Resolve actor class from env ──────────────────────────────────────── */
  function _resolveActorClass(env, tokenId) {
    if (!env || !tokenId) return 'default';

    // Check if the token belongs to the local player and we have a charSheet
    const tok = (env.tokens || {})[tokenId] || (env.stagingTokens || {})[tokenId];
    if (!tok) return 'default';

    // If token has explicit class data
    if (tok.charClass) return classTagForName(tok.charClass);
    if (tok.className) return classTagForName(tok.className);

    // If it's the local player's token, check _charSheet
    if (tok.owner_id && tok.owner_id === env.userId) {
      const cs = env.charSheet;
      if (cs && cs.classes && cs.classes.length) {
        return classTagForName(cs.classes[0].name);
      }
    }

    // Try selectedClass
    if (tok.owner_id && tok.owner_id === env.userId && env.selectedClass) {
      return classTagForName(env.selectedClass.name);
    }

    // Check token color against CLASS_COLORS to infer
    if (tok.color && env.classColors) {
      for (const [cls, col] of Object.entries(env.classColors)) {
        if (col === tok.color) return cls;
      }
    }

    return 'default';
  }

  /* ── Spotlight banner ──────────────────────────────────────────────────── */

  function fireSpotlight(opts) {
    if (!_canFire()) return;
    opts = opts || {};
    const classKey   = opts.classKey || 'default';
    const flavor     = getClassFlavor(classKey);
    const icon       = opts.icon || flavor.icon;
    const title      = opts.title || 'Spotlight Moment';
    const subtitle   = opts.subtitle || '';
    const duration   = Math.max(1800, Math.min(5500, Number(opts.duration || 3200)));
    const vignette   = opts.vignette !== false; // default true

    // Create banner
    const banner = document.createElement('div');
    banner.className = 'spotlight-banner';
    banner.setAttribute('data-class', classKey);

    banner.innerHTML =
      '<span class="spotlight-banner-icon">' + _escHtml(icon) + '</span>' +
      '<div class="spotlight-banner-body">' +
        '<span class="spotlight-banner-title">' + _escHtml(title) + '</span>' +
        (subtitle ? '<span class="spotlight-banner-subtitle">' + _escHtml(subtitle) + '</span>' : '') +
      '</div>';

    document.body.appendChild(banner);

    // Entrance
    requestAnimationFrame(function () {
      banner.classList.add('spotlight-banner--enter');
    });

    // Vignette overlay
    let vignetteEl = null;
    if (vignette) {
      vignetteEl = document.createElement('div');
      vignetteEl.className = 'spotlight-vignette';
      const classVar = _getClassColor(classKey);
      vignetteEl.style.background =
        'radial-gradient(ellipse at center, transparent 50%, ' + classVar + '22 100%)';
      document.body.appendChild(vignetteEl);
      requestAnimationFrame(function () {
        vignetteEl.classList.add('spotlight-vignette--active');
      });
    }

    // Exit
    var exitTimer = setTimeout(function () {
      banner.classList.remove('spotlight-banner--enter');
      banner.classList.add('spotlight-banner--exit');
      banner.addEventListener('animationend', function () { banner.remove(); }, { once: true });
      setTimeout(function () { if (banner.parentNode) banner.remove(); }, 500);

      if (vignetteEl) {
        vignetteEl.classList.remove('spotlight-vignette--active');
        setTimeout(function () { if (vignetteEl.parentNode) vignetteEl.remove(); }, 400);
      }
    }, duration);

    // Allow click-dismiss
    banner.style.pointerEvents = 'auto';
    banner.style.cursor = 'pointer';
    banner.addEventListener('click', function () {
      clearTimeout(exitTimer);
      banner.classList.remove('spotlight-banner--enter');
      banner.classList.add('spotlight-banner--exit');
      banner.addEventListener('animationend', function () { banner.remove(); }, { once: true });
      setTimeout(function () { if (banner.parentNode) banner.remove(); }, 500);
      if (vignetteEl) {
        vignetteEl.classList.remove('spotlight-vignette--active');
        setTimeout(function () { if (vignetteEl.parentNode) vignetteEl.remove(); }, 400);
      }
    });
  }

  /* ── Event hooks ───────────────────────────────────────────────────────── */

  /**
   * Hook: combat attack result.
   * Fires spotlight for critical hits (nat 20 on attack).
   */
  function onCombatAttackResult(payload, env) {
    if (!payload) return;
    var result = String(payload.result || '');
    var attackKind = String(payload.attack_kind || 'weapon');
    var attackerName = String(payload.attacker_name || 'Attacker');
    var targetName = String(payload.target_name || 'Target');
    var attackerTokenId = String(payload.attacker_token_id || '');

    var classKey = _resolveActorClass(env, attackerTokenId);
    var flavor = getClassFlavor(classKey);

    // Critical hit spotlight (result contains 'crit' or server signals nat 20)
    if (result === 'hit' && payload.critical) {
      var critTitle = attackKind === 'spell'
        ? flavor.actionWord + ' — Critical Spell!'
        : flavor.actionWord + ' — Critical Hit!';
      fireSpotlight({
        classKey: classKey,
        icon: attackKind === 'spell' ? '🌟' : '💥',
        title: critTitle,
        subtitle: attackerName + ' ' + flavor.verb + ' a devastating blow against ' + targetName,
        duration: 3600,
      });
    }
  }

  /**
   * Hook: dice result — detect nat 20s and nat 1s on d20 rolls.
   * The existing showNat20FX / showNat1FX still fire; this adds a class-flavored banner.
   */
  function onDiceResult(payload, env) {
    if (!payload) return;
    var diceType = Number(payload.dice_type || 0);
    var qty = Number(payload.quantity || 0);
    var rolls = Array.isArray(payload.rolls) ? payload.rolls : [];
    var rollLabel = String(payload.roll_label || '').toLowerCase();
    var userName = String(payload.user_name || '');

    // Only single d20 rolls, and only for explicit labeled gameplay rolls.
    // Random Dice Vault/manual rolls were producing misleading banners when the
    // visual die/result were still being tuned, so skip unlabeled/general rolls.
    if (diceType !== 20 || qty !== 1 || rolls.length !== 1) return;
    if (!rollLabel || rollLabel === 'initiative' || rollLabel === 'random' || rollLabel === 'manual') return;

    var classKey = _resolveLocalClass(env);
    var flavor = getClassFlavor(classKey);

    if (rolls[0] === 20) {
      var label = rollLabel;
      fireSpotlight({
        classKey: classKey,
        icon: '✦',
        title: flavor.actionWord + ' — Natural 20!',
        subtitle: (userName || 'A hero') + ' rolls a perfect ' + label,
        duration: 3400,
      });
    } else if (rolls[0] === 1) {
      if (rollLabel === 'initiative') return;
      // Nat 1 — fumble moment (more subdued, no class theming)
      fireSpotlight({
        classKey: 'default',
        icon: '💀',
        title: 'Critical Fumble',
        subtitle: (userName || 'A hero') + ' rolls a natural 1...',
        duration: 2800,
        vignette: false,
      });
    }
  }

  /**
   * Hook: combat state changes.
   * Detects: boss finishing blow (HP → 0), death save success (3/3), combat end.
   */
  function onCombatStateChange(state, prev, env) {
    if (!state || !prev) return;

    var combatants = state.combatants || [];
    var prevCombatants = prev.combatants || [];

    // Detect: finishing blow — a non-player combatant went from HP > 0 to HP <= 0
    combatants.forEach(function (com, i) {
      if (!com || com.is_player) return;
      var hp = Number(com.hp);
      if (isNaN(hp) || hp > 0) return;

      var prevCom = prevCombatants[i];
      if (!prevCom) return;
      var prevHp = Number(prevCom.hp);
      if (isNaN(prevHp) || prevHp <= 0) return;

      // This combatant just dropped to 0 — finishing blow!
      var classKey = _resolveLocalClass(env);
      var flavor = getClassFlavor(classKey);
      fireSpotlight({
        classKey: classKey,
        icon: '⚔️',
        title: 'Finishing Blow!',
        subtitle: (com.name || 'Enemy') + ' has been felled',
        duration: 3400,
      });
    });

    // Detect: clutch death save — a player combatant reached 3 successes
    combatants.forEach(function (com, i) {
      if (!com) return;
      var ds = com.death_saves || com.deathSaves;
      if (!ds) return;
      var successes = Number(ds.successes || 0);
      if (successes < 3) return;

      var prevCom = prevCombatants[i];
      if (!prevCom) return;
      var prevDs = prevCom.death_saves || prevCom.deathSaves;
      var prevSuccesses = Number((prevDs || {}).successes || 0);
      if (prevSuccesses >= 3) return;

      // Just survived death saves!
      var classKey = _resolveActorClass(env, com.token_id);
      var flavor = getClassFlavor(classKey);
      fireSpotlight({
        classKey: classKey,
        icon: '🛡️',
        title: 'Clutch Save!',
        subtitle: (com.name || 'A hero') + ' defies death',
        duration: 3600,
      });
    });
  }

  /**
   * Hook: apply class-flavored accent to a combat entry element.
   * Called from renderCombat if available.
   */
  function applyCombatEntryAccent(entryEl, combatant, env) {
    if (!entryEl || !combatant) return;
    var classKey = _resolveActorClass(env, combatant.token_id);
    if (classKey && classKey !== 'default') {
      entryEl.classList.add('class-accent-' + classKey);
    }
  }

  /**
   * Hook: add class-flavored parchment notification for key ability checks.
   * Called for dramatic social success, trap disarm, hidden clue discovery.
   */
  function showClassFlavoredNotice(opts, env) {
    opts = opts || {};
    var classKey = opts.classKey || _resolveLocalClass(env);
    var flavor = getClassFlavor(classKey);

    if (window.AppUINotifications && window.AppUINotifications.showParchmentNotification) {
      window.AppUINotifications.showParchmentNotification(
        opts.message || '',
        {
          variant: 'spotlight',
          title: opts.title || (flavor.icon + ' ' + flavor.actionWord),
          duration: opts.duration || 3800,
        }
      );
    }
  }

  /* ── Helpers ───────────────────────────────────────────────────────────── */

  function _resolveLocalClass(env) {
    if (!env) return 'default';
    if (env.selectedClass) return classTagForName(env.selectedClass.name);
    if (env.charSheet && env.charSheet.classes && env.charSheet.classes.length) {
      return classTagForName(env.charSheet.classes[0].name);
    }
    return 'default';
  }

  function _getClassColor(classKey) {
    var map = {
      fighter: '#c0392b', wizard: '#8e44ad', rogue: '#16a085',
      cleric: '#f39c12', ranger: '#27ae60', bard: '#2980b9',
      paladin: '#d4ac0d', barbarian: '#e74c3c', druid: '#1e8449',
      sorcerer: '#9b59b6', warlock: '#6c3483', monk: '#3498db',
      default: '#00e5cc',
    };
    return map[classKey] || map.default;
  }

  function _escHtml(str) {
    var d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
  }

  /* ── Public API ────────────────────────────────────────────────────────── */

  window.AppUISpotlight = {
    fireSpotlight: fireSpotlight,
    classTagForName: classTagForName,
    getClassFlavor: getClassFlavor,
    onCombatAttackResult: onCombatAttackResult,
    onDiceResult: onDiceResult,
    onCombatStateChange: onCombatStateChange,
    applyCombatEntryAccent: applyCombatEntryAccent,
    showClassFlavoredNotice: showClassFlavoredNotice,
  };
})();
