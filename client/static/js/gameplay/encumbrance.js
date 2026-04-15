/**
 * client/static/js/gameplay/encumbrance.js
 * D&D 5e Encumbrance system — client-side logic, weight bar, and bag UI.
 *
 * Exposed as window.AppEncumbrance.
 */
(function (global) {
  'use strict';

  // ─── Weight lookup tables (mirrors server/encumbrance.py) ──────────────────

  const ITEM_WEIGHT_BY_NAME = {
    dagger: 1, dart: 0.25, handaxe: 2, 'light hammer': 2, sickle: 2,
    club: 2, greatclub: 10, javelin: 2, quarterstaff: 4, spear: 3,
    shortsword: 2, 'short sword': 2, scimitar: 3, rapier: 2,
    longsword: 3, 'long sword': 3, battleaxe: 4, flail: 2,
    morningstar: 4, trident: 4, 'war pick': 2, warhammer: 2, whip: 3,
    greatsword: 6, 'great sword': 6, greataxe: 7, glaive: 6, halberd: 6,
    lance: 6, maul: 10, pike: 18,
    'heavy crossbow': 18, 'light crossbow': 5, 'hand crossbow': 3,
    shortbow: 2, 'short bow': 2, longbow: 2, 'long bow': 2,
    sling: 0, blowgun: 1, net: 3, shield: 6,
    arrow: 0.05, 'arrows (20)': 1, bolt: 0.075, 'bolts (20)': 1.5,
    'padded armour': 8, 'padded armor': 8,
    'leather armour': 10, 'leather armor': 10,
    'studded leather armour': 13, 'studded leather armor': 13,
    'hide armour': 12, 'hide armor': 12,
    'chain shirt': 20, 'scale mail': 45, breastplate: 20,
    'half plate armour': 40, 'half plate armor': 40,
    'ring mail': 40, 'chain mail': 55,
    'splint armour': 60, 'splint armor': 60,
    'plate armour': 65, 'plate armor': 65,
    backpack: 5, bedroll: 7, blanket: 3, book: 5,
    crowbar: 5, 'grappling hook': 4, lantern: 1, 'hooded lantern': 2,
    mirror: 0.5, 'steel mirror': 0.5, 'oil (flask)': 1,
    potion: 0.5, 'potion of healing': 0.5,
    rations: 2, ration: 2, 'iron rations': 2,
    rope: 10, 'rope (50 ft)': 10, 'rope (50ft)': 10,
    'hempen rope': 10, 'silk rope': 5,
    sack: 0.5, shovel: 5, spellbook: 3, tinderbox: 1, torch: 1,
    waterskin: 5, whetstone: 1, tent: 20,
  };

  const KEYWORD_WEIGHTS = [
    ['plate',       65], ['splint',      60], ['chain mail',  55],
    ['chain shirt', 20], ['scale mail',  45], ['ring mail',   40],
    ['half plate',  40], ['breastplate', 20], ['hide',        12],
    ['studded',     13], ['leather',     10], ['padded',       8],
    ['armour',      30], ['armor',       30], ['potion',      0.5],
    ['ration',       2], ['arrow',      0.05], ['bolt',      0.075],
    ['rope',        10], ['shield',       6], ['staff',        4],
    ['sword',        3], ['axe',          4], ['bow',          2],
    ['crossbow',     5], ['torch',        1], ['book',         5],
    ['pack',         5],
  ];

  const WEIGHT_BY_CATEGORY = {
    'light armor': 13, 'light armour': 13,
    'medium armor': 30, 'medium armour': 30,
    'heavy armor': 60, 'heavy armour': 60,
    shield: 6, weapon: 3, 'melee weapon': 3, 'ranged weapon': 2,
    ammunition: 0.05, potion: 0.5, scroll: 0, wand: 1, staff: 4,
    rod: 2, ring: 0, amulet: 0, trinket: 0, tool: 2,
    gear: 1, 'adventuring gear': 1, consumable: 0.5, misc: 0.5,
  };

  const WEIGHT_BY_TYPE = {
    light_armor: 13, light_armour: 13,
    medium_armor: 30, medium_armour: 30,
    heavy_armor: 60, heavy_armour: 60,
    shield: 6, melee_weapon: 3, ranged_weapon: 2, weapon: 3,
    potion: 0.5, scroll: 0, wand: 1, staff: 4, rod: 2,
    ring: 0, amulet: 0, trinket: 0, ammunition: 0.05,
    consumable: 0.5, misc: 0.5,
  };

  const DEFAULT_WEIGHT = 0.5;
  const WEIGHT_TEXT_RE = /(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds)\b/i;

  const SIZE_MULTIPLIERS = {
    tiny: 0.25, small: 0.5, medium: 1.0, large: 2.0,
    huge: 4.0, gargantuan: 8.0,
  };

  const ENC_NONE  = 'unencumbered';
  const ENC_LIGHT = 'encumbered';
  const ENC_HEAVY = 'heavily_encumbered';
  const ENC_OVER  = 'over_capacity';

  // ─── Calculation helpers ───────────────────────────────────────────────────

  function getItemWeight(item) {
    if (!item || typeof item !== 'object') return DEFAULT_WEIGHT;
    if (item.weight_lbs != null) return Math.max(0, Number(item.weight_lbs) || 0);
    for (const key of ['weight', 'notes', 'effect', 'unidentified_description']) {
      const raw = item[key];
      if (!raw) continue;
      const match = String(raw).match(WEIGHT_TEXT_RE);
      if (match) return Math.max(0, Number(match[1]) || 0);
    }

    const name = String(item.name || '').trim().toLowerCase();
    if (ITEM_WEIGHT_BY_NAME[name] != null) return ITEM_WEIGHT_BY_NAME[name];

    for (const [kw, w] of KEYWORD_WEIGHTS) {
      if (name.includes(kw)) return w;
    }
    const cat = String(item.category || '').trim().toLowerCase();
    if (WEIGHT_BY_CATEGORY[cat] != null) return WEIGHT_BY_CATEGORY[cat];

    const itype = String(item.item_type || '').trim().toLowerCase();
    if (WEIGHT_BY_TYPE[itype] != null) return WEIGHT_BY_TYPE[itype];

    return DEFAULT_WEIGHT;
  }

  function getSizeMultiplier(size) {
    return SIZE_MULTIPLIERS[String(size || 'medium').trim().toLowerCase()] || 1.0;
  }

  function getCarryCapacity(strength, size) {
    const s = Math.max(1, Math.min(30, parseInt(strength, 10) || 10));
    const baseCapacity = Math.floor((s * 15) * 1.5) + 20;
    return baseCapacity * getSizeMultiplier(size);
  }

  function getThresholds(strength, size) {
    const capacity = getCarryCapacity(strength, size);
    return {
      [ENC_LIGHT]: capacity / 3,
      [ENC_HEAVY]: (capacity * 2) / 3,
      [ENC_OVER]:  capacity,
    };
  }

  function getTotalCarriedWeight(inventory, goldUnits) {
    let total = 0;
    for (const item of (inventory || [])) {
      if (!item || typeof item !== 'object') continue;
      if (item.extradimensional) {
        total += Math.max(0, Number(item.own_weight_lbs) || 0);
      } else {
        const qty = Math.max(1, parseInt(item.qty, 10) || 1);
        total += getItemWeight(item) * qty;
      }
    }
    // 50 gp = 5000 units = 1 lb
    total += Math.max(0, Number(goldUnits) || 0) / 5000;
    return Math.round(total * 100) / 100;
  }

  function getEncumbranceState(strength, size, totalWeight) {
    const t = getThresholds(strength, size);
    if (totalWeight > t[ENC_OVER])  return ENC_OVER;
    if (totalWeight > t[ENC_HEAVY]) return ENC_HEAVY;
    if (totalWeight > t[ENC_LIGHT]) return ENC_LIGHT;
    return ENC_NONE;
  }

  function getSpeedPenalty(state) {
    return { [ENC_LIGHT]: -10, [ENC_HEAVY]: -20, [ENC_OVER]: -99 }[state] || 0;
  }

  // ─── State held from last server sync ─────────────────────────────────────

  let _lastEncData = null;  // the encumbrance object from the last sync

  function applyEncumbranceSync(encObj) {
    _lastEncData = encObj || null;
    renderEncumbranceBar();
  }

  function getLastEncData() { return _lastEncData; }

  // ─── Weight-bar rendering ──────────────────────────────────────────────────

  /**
   * Render / update the encumbrance weight bar inside #inventory-weight-bar.
   * The element must already exist in the DOM (injected by play.html).
   */
  function renderEncumbranceBar() {
    const wrap = document.getElementById('inventory-weight-bar');
    if (!wrap) return;

    const enc = _lastEncData;
    if (!enc || !enc.enabled) {
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = '';

    const current  = enc.total_weight || 0;
    const capacity = enc.capacity     || 1;
    const state    = enc.state        || ENC_NONE;
    const pct      = Math.min(1, current / capacity);
    const strScore = Math.max(1, parseInt(enc.strength, 10) || 10);

    // Bar colour
    let barColor = '#2ecc71';  // green
    if (pct >= 1 || state === ENC_OVER) barColor = '#e74c3c';
    else if (pct >= 0.66 || state === ENC_HEAVY) barColor = '#e67e22';
    else if (pct >= 0.33 || state === ENC_LIGHT) barColor = '#f1c40f';

    // Label
    const labels = {
      [ENC_NONE]:  'Unencumbered',
      [ENC_LIGHT]: '⚖ Encumbered',
      [ENC_HEAVY]: '⚖ Heavily Encumbered',
      [ENC_OVER]:  '🚫 Over Capacity',
    };
    const label = labels[state] || 'Unencumbered';

    // Threshold markers
    const t = enc.thresholds || {};
    const tLight = t[ENC_LIGHT] || t['encumbered']         || 0;
    const tHeavy = t[ENC_HEAVY] || t['heavily_encumbered'] || 0;
    const markerLight = capacity > 0 ? Math.min(1, tLight / capacity) * 100 : 0;
    const markerHeavy = capacity > 0 ? Math.min(1, tHeavy / capacity) * 100 : 0;

    const baseCapacity = Math.floor((strScore * 15) * 1.5) + 20;
    const tooltip = `Based on STR ${strScore} (floor((15 × ${strScore}) × 1.5) + 20 = ${baseCapacity.toFixed(0)} lbs)`;
    wrap.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.25rem;">
        <span style="font-size:0.62rem;color:${barColor};font-weight:700;letter-spacing:0.05em;">${escapeHtmlEnc(label)}</span>
        <span style="font-size:0.62rem;color:var(--parchment-dim);" title="${escapeHtmlEnc(tooltip)}">${current.toFixed(1)} / ${capacity.toFixed(0)} lbs</span>
      </div>
      <div style="position:relative;height:6px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden;">
        <div style="position:absolute;left:0;top:0;height:100%;width:${(pct*100).toFixed(1)}%;background:${barColor};border-radius:3px;transition:width 0.3s;"></div>
        ${markerLight > 0 ? `<div style="position:absolute;left:${markerLight.toFixed(1)}%;top:0;height:100%;width:1px;background:rgba(243,156,18,0.6);"></div>` : ''}
        ${markerHeavy > 0 ? `<div style="position:absolute;left:${markerHeavy.toFixed(1)}%;top:0;height:100%;width:1px;background:rgba(231,76,60,0.6);"></div>` : ''}
      </div>
      ${enc.coin_weight ? `<div style="font-size:0.59rem;color:var(--parchment-dim);margin-top:0.18rem;">Coins: ${enc.coin_weight.toFixed(2)} lbs</div>` : ''}
    `;
  }

  // ─── Bag rows in the inventory list ───────────────────────────────────────

  /**
   * Build and return the HTML string for an expanded bag-of-holding row.
   * @param {object} bag  - bag summary from enc.bags[]
   * @param {number} bagInventoryIndex - index in the full inventory array
   */
  function buildBagRowHtml(bag, bagInventoryIndex) {
    const fillPct  = Math.min(100, bag.fill_pct || 0);
    const fillColor = fillPct >= 90 ? '#e74c3c' : (fillPct >= 60 ? '#f39c12' : '#2ecc71');
    const contents  = bag.contents || [];
    const contentsHtml = contents.length
      ? contents.map((item, ci) => `
          <div style="display:flex;justify-content:space-between;gap:0.4rem;align-items:center;
                      padding:0.3rem 0.55rem;border-radius:6px;background:rgba(10,18,28,0.42);"
               data-bag-idx="${bagInventoryIndex}" data-content-idx="${ci}">
            <div style="font-size:0.7rem;color:var(--parchment);flex:1;min-width:0;">
              ${escapeHtmlEnc(item.name)}
              <span style="color:var(--parchment-dim);font-size:0.62rem;"> · ${getItemWeight(item).toFixed(1)} lbs</span>
            </div>
            <span style="font-size:0.68rem;color:var(--gold);white-space:nowrap;">×${item.qty}</span>
            <button onclick="encumbranceBagRemoveItem(${bagInventoryIndex},${ci})"
                    style="font-size:0.6rem;padding:0.15rem 0.4rem;border-radius:4px;
                           background:rgba(231,76,60,0.14);border:1px solid rgba(231,76,60,0.35);
                           color:#e57373;cursor:pointer;flex-shrink:0;">Out</button>
          </div>
        `).join('')
      : '<div style="font-size:0.67rem;color:var(--parchment-dim);padding:0.3rem 0.55rem;">Empty.</div>';

    return `
      <div style="margin-top:0.45rem;padding:0.55rem;border:1px solid rgba(0,229,204,0.2);
                  border-radius:8px;background:rgba(0,229,204,0.04);">
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
          <span style="font-size:0.68rem;color:var(--gold);font-weight:700;">🎒 ${escapeHtmlEnc(bag.name)}</span>
          <span style="font-size:0.6rem;color:var(--parchment-dim);">${bag.own_weight} lbs carried</span>
          <span style="font-size:0.6rem;color:var(--parchment-dim);">[${bag.contents_weight.toFixed(1)} / ${bag.capacity.toFixed(0)} lbs inside]</span>
        </div>
        <div style="height:4px;border-radius:2px;background:rgba(255,255,255,0.08);margin-bottom:0.45rem;overflow:hidden;">
          <div style="height:100%;width:${fillPct.toFixed(1)}%;background:${fillColor};border-radius:2px;"></div>
        </div>
        <div style="display:flex;flex-direction:column;gap:0.22rem;">${contentsHtml}</div>
      </div>
    `;
  }

  // ─── DM encumbrance settings panel ────────────────────────────────────────

  /**
   * Send updated encumbrance settings to the server.
   */
  function sendEncumbranceSettingsUpdate(settings) {
    if (typeof sendWS === 'function') {
      sendWS({ type: 'encumbrance_settings_update', payload: settings });
    } else if (typeof window.sendWS === 'function') {
      window.sendWS({ type: 'encumbrance_settings_update', payload: settings });
    }
  }

  // ─── Bag interaction helpers (called from inline onclick in play.html) ─────

  function bagAddItem(bagIndex, itemIndex, qty) {
    const sender = (typeof sendWS === 'function')
      ? sendWS
      : ((typeof window !== 'undefined' && typeof window.sendWS === 'function') ? window.sendWS : null);
    if (!sender) return;
    sender({
      type: 'bag_add_item',
      payload: {
        bag_index: Math.max(0, parseInt(bagIndex, 10) || 0),
        item_index: Math.max(0, parseInt(itemIndex, 10) || 0),
        qty: Math.max(1, parseInt(qty, 10) || 1),
      }
    });
  }

  function bagRemoveItem(bagIndex, contentIndex, qty) {
    const sender = (typeof sendWS === 'function')
      ? sendWS
      : ((typeof window !== 'undefined' && typeof window.sendWS === 'function') ? window.sendWS : null);
    if (!sender) return;
    sender({
      type: 'bag_remove_item',
      payload: {
        bag_index: Math.max(0, parseInt(bagIndex, 10) || 0),
        content_index: Math.max(0, parseInt(contentIndex, 10) || 0),
        qty: Math.max(1, parseInt(qty, 10) || 1),
      }
    });
  }

  function bagDestroyConfirm(targetUserId, bagIndex) {
    if (!confirm('Destroy this extradimensional container? ALL contents will be lost to the Astral Plane!')) return;
    const sender = (typeof sendWS === 'function')
      ? sendWS
      : ((typeof window !== 'undefined' && typeof window.sendWS === 'function') ? window.sendWS : null);
    if (!sender) return;
    sender({
      type: 'bag_destroy',
      payload: {
        target_user_id: String(targetUserId || '').trim(),
        bag_index: Math.max(0, parseInt(bagIndex, 10) || 0),
      }
    });
  }

  // ─── Pick-up warning toasts ────────────────────────────────────────────────

  /**
   * Check if adding an item would change encumbrance state; return a warning
   * message string or null.
   */
  function checkPickupWarning(item, inventory, goldUnits, strength, size, encSettings) {
    if (!encSettings || !encSettings.use_encumbrance) return null;
    const currentWeight = getTotalCarriedWeight(inventory, goldUnits);
    const addedWeight   = getItemWeight(item) * Math.max(1, parseInt(item.qty, 10) || 1);
    const newWeight     = currentWeight + addedWeight;
    const currentState  = getEncumbranceState(strength, size, currentWeight);
    const newState      = getEncumbranceState(strength, size, newWeight);

    if (newState === currentState) return null;
    if (newState === ENC_OVER)   return `Picking up ${item.name} will put you OVER CAPACITY. You cannot move!`;
    if (newState === ENC_HEAVY)  return `Picking up ${item.name} will leave you HEAVILY ENCUMBERED (−20 ft speed, disadvantage on STR/DEX/CON).`;
    if (newState === ENC_LIGHT)  return `Picking up ${item.name} will leave you ENCUMBERED (−10 ft speed).`;
    return null;
  }

  /**
   * Check if a Tiny/Small character can equip/carry an item.
   * Returns { blocked, reason } or null.
   */
  function checkSizeRestriction(item, characterSize, encSettings) {
    if (!encSettings || !encSettings.size_restrictions) return null;
    const size = String(characterSize || 'medium').toLowerCase();
    const name = String(item.name || '').toLowerCase();
    const itype = String(item.item_type || '').toLowerCase();
    const cat   = String(item.category || '').toLowerCase();

    const TINY_BLOCKED_KEYWORDS = [
      'greatsword', 'great sword', 'greataxe', 'maul', 'pike',
      'halberd', 'glaive', 'heavy crossbow', 'longbow', 'long bow',
      'lance', 'greatclub',
    ];
    if (size === 'tiny') {
      for (const kw of TINY_BLOCKED_KEYWORDS) {
        if (name.includes(kw)) {
          return { blocked: true, reason: `A ${item.name} is far too large for a Tiny creature to wield or carry.` };
        }
      }
      if (itype.includes('medium_arm') || itype.includes('heavy_arm') || cat.includes('shield')) {
        return { blocked: true, reason: `A Tiny creature cannot wear ${item.name}.` };
      }
    }
    if (size === 'small') {
      if (itype.includes('heavy_arm') || cat.includes('heavy arm')) {
        return { blocked: false, reason: `Small creatures cannot normally wear ${item.name} (check with your DM).` };
      }
    }
    return null;
  }

  // ─── Small utility ─────────────────────────────────────────────────────────

  function escapeHtmlEnc(text) {
    return String(text || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ─── Public API ────────────────────────────────────────────────────────────

  global.AppEncumbrance = {
    // Calculation
    getItemWeight,
    getSizeMultiplier,
    getCarryCapacity,
    getThresholds,
    getTotalCarriedWeight,
    getEncumbranceState,
    getSpeedPenalty,
    // State
    applyEncumbranceSync,
    getLastEncData,
    // Render
    renderEncumbranceBar,
    buildBagRowHtml,
    // Interactions
    sendEncumbranceSettingsUpdate,
    bagAddItem,
    bagRemoveItem,
    bagDestroyConfirm,
    // Warnings
    checkPickupWarning,
    checkSizeRestriction,
  };

  // Expose bag helpers globally for onclick= attrs in play.html
  global.encumbranceBagAddItem    = bagAddItem;
  global.encumbranceBagRemoveItem = bagRemoveItem;
  global.encumbranceBagDestroy    = bagDestroyConfirm;

})(window);
