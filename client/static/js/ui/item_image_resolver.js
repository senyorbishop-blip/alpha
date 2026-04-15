/**
 * item_image_resolver.js
 * Centralized image/icon resolver for inventory/shop/loot surfaces.
 *
 * Resolution order:
 * 1) explicit per-item image_url/image_path override
 * 2) explicit per-item image_key mapping override
 * 3) subtype/family mapping
 * 4) category mapping
 * 5) generic fallback
 */
(function () {
  'use strict';

  const KEY_TO_ASSET = {
    generic_item: { icon: '🧰', image_url: '' },
    sword_basic: { icon: '🗡️', image_url: '' },
    axe_basic: { icon: '🪓', image_url: '' },
    bow_basic: { icon: '🏹', image_url: '' },
    staff_basic: { icon: '🪄', image_url: '' },
    shield_basic: { icon: '🛡️', image_url: '' },
    armor_light_basic: { icon: '🦺', image_url: '' },
    armor_heavy_basic: { icon: '🥋', image_url: '' },
    potion_heal_basic: { icon: '🧪', image_url: '' },
    scroll_arcane_basic: { icon: '📜', image_url: '' },
    wand_basic: { icon: '✨', image_url: '' },
    ring_basic: { icon: '💍', image_url: '' },
    cloak_basic: { icon: '🧥', image_url: '' },
    boots_basic: { icon: '🥾', image_url: '' },
    ore_basic: { icon: '⛏️', image_url: '' },
    herb_basic: { icon: '🌿', image_url: '' },
    hide_basic: { icon: '🧵', image_url: '' },
    tool_basic: { icon: '🛠️', image_url: '' },
    gadget_tinker: { icon: '⚙️', image_url: '' },
    pirate_gear_basic: { icon: '🧭', image_url: '' },
    trinket_basic: { icon: '🎁', image_url: '' },
    legendary_named_basic: { icon: '🌟', image_url: '' },
  };

  const CATEGORY_TO_KEY = {
    weapon: 'sword_basic',
    armor: 'armor_light_basic',
    shield: 'shield_basic',
    potion: 'potion_heal_basic',
    consumable: 'potion_heal_basic',
    scroll: 'scroll_arcane_basic',
    wand: 'wand_basic',
    ring: 'ring_basic',
    cloak: 'cloak_basic',
    boots: 'boots_basic',
    tool: 'tool_basic',
    material: 'ore_basic',
    trinket: 'trinket_basic',
    treasure: 'trinket_basic',
    misc: 'generic_item',
    magic: 'legendary_named_basic',
  };

  const SUBTYPE_TO_KEY = {
    sword: 'sword_basic',
    longsword: 'sword_basic',
    shortsword: 'sword_basic',
    axe: 'axe_basic',
    bow: 'bow_basic',
    staff: 'staff_basic',
    shield: 'shield_basic',
    light_armor: 'armor_light_basic',
    heavy_armor: 'armor_heavy_basic',
    potion: 'potion_heal_basic',
    scroll: 'scroll_arcane_basic',
    wand: 'wand_basic',
    ring: 'ring_basic',
    cloak: 'cloak_basic',
    boots: 'boots_basic',
    ore: 'ore_basic',
    material: 'ore_basic',
    hide: 'hide_basic',
    leather: 'hide_basic',
    herb: 'herb_basic',
    reagent: 'herb_basic',
    tool: 'tool_basic',
    gadget: 'gadget_tinker',
    tinker_device: 'gadget_tinker',
    pirate_gear: 'pirate_gear_basic',
    treasure: 'trinket_basic',
    trinket: 'trinket_basic',
  };

  const ITEM_OVERRIDES = {
    // Future-ready: add exact-name or slug overrides here (e.g. 'holy_avenger').
  };

  function _clean(raw, max = 160) {
    return String(raw || '').trim().slice(0, max);
  }

  function _norm(raw) {
    return _clean(raw, 160).toLowerCase().replace(/\s+/g, '_');
  }

  function _fromKey(imageKey) {
    const key = _norm(imageKey);
    if (!key) return null;
    const row = KEY_TO_ASSET[key];
    if (!row) return null;
    return {
      key,
      imageUrl: _clean(row.image_url, 500),
      icon: _clean(row.icon, 8) || '🧰',
    };
  }

  function _explicitImage(item) {
    const imageUrl = _clean(item?.image_url || item?.image_path, 500);
    if (imageUrl) {
      return {
        key: _norm(item?.image_key) || 'explicit_image_url',
        imageUrl,
        icon: _clean(item?.icon, 8) || '🧰',
      };
    }
    return null;
  }

  function _itemOverrideKey(item) {
    const itemSlug = _norm(item?.slug || item?.id || item?.magic_item_id || item?.name);
    if (!itemSlug) return '';
    return _clean(ITEM_OVERRIDES[itemSlug], 120);
  }

  function _resolveImageKey(item) {
    const explicitKey = _clean(item?.image_key || item?.icon_key, 120);
    if (explicitKey) return explicitKey;

    const overrideKey = _itemOverrideKey(item);
    if (overrideKey) return overrideKey;

    const subtypeHint = _clean(item?.subtype_icon_key || item?.item_family || item?.subtype || item?.weapon_type || item?.material_type || item?.item_type, 120);
    const subtypeKey = _clean(SUBTYPE_TO_KEY[_norm(subtypeHint)], 120);
    if (subtypeKey) return subtypeKey;

    const categoryHint = _clean(item?.category_icon_key || item?.category, 120);
    const categoryKey = _clean(CATEGORY_TO_KEY[_norm(categoryHint)], 120);
    if (categoryKey) return categoryKey;

    if (item?.named_item_flag || item?.legendary_flag || _norm(item?.rarity) === 'legendary') {
      return 'legendary_named_basic';
    }

    return 'generic_item';
  }

  function resolveItemImage(item) {
    const explicit = _explicitImage(item);
    if (explicit) {
      return {
        ...explicit,
        source: 'explicit_image_url',
        named: !!item?.named_item_flag,
        legendary: !!item?.legendary_flag || _norm(item?.rarity) === 'legendary',
      };
    }

    const chosenKey = _resolveImageKey(item);
    const keyResolved = _fromKey(chosenKey) || _fromKey('generic_item');

    return {
      ...keyResolved,
      source: chosenKey === 'generic_item' ? 'generic_fallback' : 'key_mapping',
      named: !!item?.named_item_flag,
      legendary: !!item?.legendary_flag || _norm(item?.rarity) === 'legendary',
    };
  }

  function renderToken(item, options = {}) {
    const resolved = resolveItemImage(item);
    const size = Number(options.size) > 0 ? Number(options.size) : 20;
    const radius = Number(options.radius) > 0 ? Number(options.radius) : 6;
    const label = _clean(options.label || item?.name || 'Item', 80);

    if (resolved.imageUrl) {
      return `<span class="item-image-token" style="display:inline-flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;min-width:${size}px;border-radius:${radius}px;overflow:hidden;background:rgba(255,255,255,0.06);border:1px solid rgba(212,175,55,0.2);"><img src="${resolved.imageUrl}" alt="${label}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.style.display='none';this.parentNode.textContent='${resolved.icon || '🧰'}';" /></span>`;
    }

    return `<span class="item-image-token" style="display:inline-flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;min-width:${size}px;border-radius:${radius}px;background:rgba(255,255,255,0.06);border:1px solid rgba(212,175,55,0.2);font-size:${Math.max(11, Math.round(size * 0.62))}px;line-height:1;">${resolved.icon || '🧰'}</span>`;
  }

  window.AppItemImages = {
    resolve: resolveItemImage,
    renderToken,
    manifest: {
      keys: KEY_TO_ASSET,
      categories: CATEGORY_TO_KEY,
      subtypes: SUBTYPE_TO_KEY,
      itemOverrides: ITEM_OVERRIDES,
    },
  };
})();
