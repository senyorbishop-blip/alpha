/*
 * client/static/js/character/tabs/inventory_tab.js
 * Inventory Tab — Equipment and item management.
 *
 * Exposes: window.InventoryTab
 *   .initInventoryTab(container, charData)
 */

(function initInventoryTabModule(global) {
  'use strict';

  function _esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])
    );
  }

  const CURRENCY_ORDER = [
    { key: 'pp', label: 'PP', css: 'pp' },
    { key: 'gp', label: 'GP', css: 'gp' },
    { key: 'ep', label: 'EP', css: 'ep' },
    { key: 'sp', label: 'SP', css: 'sp' },
    { key: 'cp', label: 'CP', css: 'cp' },
  ];

  const CATEGORY_ORDER = ['Weapons', 'Armor', 'Shields'];

  function _renderCurrency(currency) {
    if (!currency || typeof currency !== 'object') return '';
    const chips = CURRENCY_ORDER.map(({ key, label, css }) => {
      const amount = parseInt(currency[key] || 0, 10);
      return `<div class="cs-currency-chip ${_esc(css)}">
        <span class="cs-currency-amount">${_esc(String(amount))}</span>
        <span class="cs-currency-label">${_esc(label)}</span>
      </div>`;
    }).join('');
    return `<div class="cs-currency-row" aria-label="Currency">${chips}</div>`;
  }

  function _itemKey(item) {
    return String(item && (item.id || item.magic_item_id || item.name || '') || '').trim().toLowerCase();
  }

  function _itemKind(item) {
    if (typeof global.inferEquipmentKindFromRaw === 'function') {
      const inferred = String(global.inferEquipmentKindFromRaw(item) || '').trim().toLowerCase();
      if (inferred) return inferred;
    }
    const direct = String(item && (item.equipment_kind || item.item_type || item.kind || item.category || '') || '').trim().toLowerCase();
    if (direct === 'armour') return 'armor';
    if (direct) return direct;
    // Name-based fallback for rings
    const name = String(item && item.name || '').trim().toLowerCase();
    if (/\bring\b/.test(name)) return 'ring';
    return '';
  }

  function _qty(item) {
    return Math.max(1, parseInt(item && (item.qty || item.quantity || item.count) || 1, 10) || 1);
  }

  function _weight(item) {
    const explicit = Number(item && (item.weight_lbs || item.weight || item.unit_weight_lbs));
    if (Number.isFinite(explicit) && explicit >= 0) return explicit;
    const name = String(item && item.name || '').toLowerCase();
    if (name.indexOf('rope') >= 0) return 10;
    if (name.indexOf('potion') >= 0) return 0.5;
    if (name.indexOf('quarterstaff') >= 0 || name.indexOf('staff') >= 0) return 4;
    if (name.indexOf('backpack') >= 0) return 5;
    return 0;
  }

  function _fmtWeight(value) {
    const n = Number(value) || 0;
    return (Math.round(n * 10) / 10).toString().replace(/\.0$/, '') + ' lb';
  }

  function _requiresAttunement(item) {
    return !!(item && (item.attunement_required || item.requires_attunement || item.requiresAttunement));
  }

  function _isContainer(item) {
    if (!item) return false;
    if (item.is_container || item.extradimensional || item.capacity_lbs || Array.isArray(item.bag_contents)) return true;
    const name = String(item.name || '').trim().toLowerCase();
    return /\b(backpack|bag of holding|handy haversack|portable hole|bag of devouring|cart|carts|wagon|chest|barrel|sack)\b/.test(name)
      || /\b(riding horse|draft horse|warhorse|mule|donkey|horse)\b/.test(name);
  }

  function _containerContentsWeight(item) {
    return (Array.isArray(item && item.bag_contents) ? item.bag_contents : []).reduce(function (sum, row) {
      return sum + (_weight(row) * _qty(row));
    }, 0);
  }

  function _containerCapacity(item) {
    return Math.max(0, Number(item && item.capacity_lbs) || (item && item.extradimensional ? 500 : 0));
  }

  function _containerLabel(item) {
    const bag = String(item && (item.container_name || item.container || item.location || '') || '').trim();
    return bag ? 'In ' + bag : '';
  }

  function _sendInventoryWs(type, payload) {
    if (typeof global.sendWS === 'function') global.sendWS({ type: type, payload: payload || {} });
  }

  function _actionButton(action, label, index, extraAttrs) {
    const attrs = Object.assign({ 'data-item-action': action, 'data-item-index': String(index) }, extraAttrs || {});
    return '<button type="button" class="cs-feature-inspect" ' + Object.keys(attrs).map(function (key) {
      return _esc(key) + '="' + _esc(attrs[key]) + '"';
    }).join(' ') + '>' + _esc(label) + '</button>';
  }

  function _equippableItems(items) {
    return (Array.isArray(items) ? items : []).filter(function (item) {
      return ['weapon', 'armor', 'shield', 'ring', 'accessory', 'wondrous'].includes(_itemKind(item));
    });
  }

  function _backpackItems(items) {
    return (Array.isArray(items) ? items : []).filter(function (item) {
      return !_equippableItems([item]).length;
    });
  }

  function _renderAttunement(items) {
    const capable = (Array.isArray(items) ? items : []).map(function (item, idx) { return { item: item, originalIndex: idx }; }).filter(function (entry) { return _requiresAttunement(entry.item); });
    const count = capable.filter(function (entry) { return !!(entry && entry.item && entry.item.attuned); }).length;
    return '<div class="cs-action-section"><div class="cs-action-section-title">Attunement ' + _esc(String(count)) + '/3</div>' +
      (capable.length ? capable.map(function (entry) { return _renderItem(entry.item, entry.originalIndex, { compact: true }); }).join('') : '<div class="cs-empty-state compact"><span>No attunement items found.</span></div>') +
      '</div>';
  }

  function _categoryForItem(item) {
    const kind = _itemKind(item);
    if (kind === 'weapon') return 'Weapons';
    if (kind === 'shield') return 'Shields';
    return 'Armor';
  }

  function _itemMeta(item) {
    const bits = [];
    const kind = _itemKind(item);
    if (kind === 'weapon') {
      if (item.damage_dice) bits.push(String(item.damage_dice) + (item.damage_type ? ' ' + String(item.damage_type) : ''));
      if (item.range) bits.push(String(item.range));
      if (Array.isArray(item.weapon_properties) && item.weapon_properties.length) bits.push(item.weapon_properties.slice(0, 3).join(', '));
    }
    if (kind === 'armor' && Number.isFinite(Number(item.base_ac))) bits.push('AC ' + String(item.base_ac));
    if (kind === 'shield' && Number.isFinite(Number(item.ac_bonus))) bits.push('AC +' + String(item.ac_bonus));
    if (item.equip_slot) bits.push(String(item.equip_slot).replace(/_/g, ' '));
    return bits.filter(Boolean).join(' • ');
  }

  function _knownSpellPool() {
    const cards = (typeof global._getStructuredRulesSpellbookCards === 'function') ? global._getStructuredRulesSpellbookCards() : [];
    const granted = Array.isArray(global._playerGrantedSpells) ? global._playerGrantedSpells : [];
    const pool = [];
    const seen = new Set();
    cards.concat(granted).forEach(function (spell) {
      const rawName = String(spell && (spell.displayName || spell.name || spell.id || '') || '').trim();
      if (!rawName) return;
      const name = (typeof global._prettyBookSpellName === 'function') ? global._prettyBookSpellName(rawName) : rawName;
      const key = name.toLowerCase();
      if (!key || seen.has(key)) return;
      seen.add(key);
      pool.push({ id: String(spell.id || name), name: name });
    });
    return pool;
  }

  function _extractItemSpellCards(item) {
    const effects = item && item.effects && typeof item.effects === 'object' ? item.effects : {};
    const gs = item && (item.granted_spells || item.grantedSpells || effects.granted_spells || effects.grantedSpells);
    if (!Array.isArray(gs) || !gs.length) return [];
    const cards = [];
    gs.slice(0, 12).forEach(function (entry) {
      if (typeof entry === 'string' && entry.trim()) {
        cards.push({ id: entry.trim().toLowerCase().replace(/\s+/g, '-'), name: entry.trim(), charge_cost: null, cast_level: 0 });
      } else if (entry && typeof entry === 'object') {
        const name = String(entry.name || entry.id || '').trim();
        if (name) cards.push({
          id: String(entry.id || '').trim() || name.toLowerCase().replace(/\s+/g, '-'),
          name: name,
          charge_cost: typeof entry.charge_cost === 'number' ? entry.charge_cost : null,
          cast_level: Number(entry.cast_level || 0),
          uses_item_dc: !!entry.uses_item_dc,
          uses_item_attack_bonus: !!entry.uses_item_attack_bonus,
          attack_preview: String(entry.attack_preview || entry.attackPreview || entry.attack_bonus || ''),
          save_preview: String(entry.save_preview || entry.savePreview || entry.save_dc || ''),
          damage_preview: String(entry.damage_preview || entry.damagePreview || entry.damage_formula || ''),
          description: String(entry.description || ''),
        });
      }
    });
    return cards;
  }

  function _extractItemSpellNames(item) {
    const cards = _extractItemSpellCards(item);
    if (cards.length) return Array.from(new Set(cards.map(function (c) { return c.name; }))).slice(0, 3);

    const explicit = [];
    [item && item.spell, item && item.spells, item && item.spell_name, item && item.spell_names].forEach(function (value) {
      if (Array.isArray(value)) explicit.push.apply(explicit, value);
      else if (typeof value === 'string' && value.trim()) explicit.push.apply(explicit, value.split(/[,;\n]+/));
    });
    const normalizedExplicit = explicit.map(function (entry) {
      const raw = typeof entry === 'object' ? (entry.name || entry.id || '') : entry;
      const name = String(raw || '').trim();
      return (typeof global._prettyBookSpellName === 'function') ? global._prettyBookSpellName(name) : name;
    }).filter(Boolean);
    if (normalizedExplicit.length) return Array.from(new Set(normalizedExplicit)).slice(0, 3);

    const sourceText = [item && item.effect, item && item.notes, item && item.unidentified_description].filter(Boolean).join(' • ').toLowerCase();
    if (!sourceText) return [];
    return _knownSpellPool()
      .filter(function (spell) { return spell && spell.name && sourceText.indexOf(String(spell.name).toLowerCase()) >= 0; })
      .map(function (spell) { return spell.name; })
      .slice(0, 3);
  }

  function _findAttackCardForItem(item) {
    if (typeof global._getUnifiedQuickAttackCards !== 'function') return null;
    const wanted = String(item && item.name || '').trim().toLowerCase();
    if (!wanted) return null;
    const cards = global._getUnifiedQuickAttackCards();
    return (Array.isArray(cards) ? cards : []).find(function (card) {
      if (!card) return false;
      return String(card.name || '').trim().toLowerCase() === wanted && String(card.source || '').toLowerCase() === 'equip_only';
    }) || null;
  }

  function _renderEquippedActions(item, itemIndex) {
    if (!item || !item.equipped) return '';
    const pieces = [];

    const needsAttunement = !!(item.attunement_required || item.requires_attunement || item.attuned === false);
    const isAttuned = !!(item.attuned);
    const attunementWarn = needsAttunement && !isAttuned
      ? '<div class="cs-summary-note" style="color:var(--gold,#c9a227);margin-top:0.2rem;">⚠ Requires attunement — item spells unavailable</div>'
      : '';

    const attackCard = _findAttackCardForItem(item);
    if (attackCard) {
      pieces.push(
        '<button type="button" class="cs-feature-inspect" data-item-action="attack" data-action-source="' + _esc(String(attackCard.source || 'equip_only')) + '" data-action-id="' + _esc(String(attackCard.id || '')) + '">Attack / Roll</button>' +
        '<button type="button" class="cs-feature-inspect muted" data-item-action="attack-info" data-action-source="' + _esc(String(attackCard.source || 'equip_only')) + '" data-action-id="' + _esc(String(attackCard.id || '')) + '">Info</button>'
      );
    }

    const charges_current = typeof item.charges_current === 'number' ? item.charges_current : -1;
    const charges_max = typeof item.charges_max === 'number' ? item.charges_max : 0;
    const chargeLabel = charges_max > 0 ? _esc(String(Math.max(0, charges_current)) + '/' + String(charges_max) + ' charges') : '';

    const spellCards = _extractItemSpellCards(item);
    if (spellCards.length && (!needsAttunement || isAttuned)) {
      spellCards.forEach(function (sc) {
        const chargeCost = typeof sc.charge_cost === 'number' ? sc.charge_cost : null;
        const canCast = chargeCost === null || chargeCost === 0 || charges_max === 0 || charges_current < 0 || charges_current >= chargeCost;
        const costLabel = chargeCost !== null && chargeCost > 0 ? ' (' + String(chargeCost) + ' charge' + (chargeCost !== 1 ? 's' : '') + ')' : '';
        const previewBits = [
          'Item: ' + String(item.name || 'Item'),
          chargeCost !== null ? ('Cost: ' + String(chargeCost) + ' charge' + (chargeCost === 1 ? '' : 's')) : '',
          sc.cast_level ? ('Cast level: ' + String(sc.cast_level)) : '',
          sc.uses_item_attack_bonus && item.item_spell_attack_bonus ? ('Attack: +' + String(item.item_spell_attack_bonus)) : (sc.attack_preview ? ('Attack: ' + sc.attack_preview) : ''),
          sc.uses_item_dc && item.item_spell_save_dc ? ('Save DC: ' + String(item.item_spell_save_dc)) : (sc.save_preview ? ('Save: ' + sc.save_preview) : ''),
          sc.damage_preview ? ('Damage: ' + sc.damage_preview) : '',
        ].filter(Boolean);
        const previewLabel = previewBits.join(' • ');
        const itemIdStr = _esc(String(item.id || item.magic_item_id || ''));
        const spellIdStr = _esc(String(sc.id || ''));
        const idxStr = _esc(String(itemIndex != null ? itemIndex : -1));
        const castLevelStr = _esc(String(sc.cast_level || 0));
        const chargeCostStr = _esc(String(chargeCost != null ? chargeCost : 1));
        pieces.push(
          '<button type="button" class="cs-feature-inspect' + (canCast ? '' : ' disabled') + '"' +
            (canCast ? '' : ' disabled') +
            ' data-item-action="cast-item-spell"' +
            ' data-spell-name="' + _esc(sc.name) + '"' +
            ' data-spell-id="' + spellIdStr + '"' +
            ' data-item-id="' + itemIdStr + '"' +
            ' data-item-index="' + idxStr + '"' +
            ' data-charge-cost="' + chargeCostStr + '"' +
            ' data-cast-level="' + castLevelStr + '"' +
            ' title="' + _esc((sc.description || sc.name) + (previewLabel ? ' • ' + previewLabel : '')) + '">' +
            'Cast ' + _esc(sc.name) + _esc(costLabel) + (previewLabel ? '<span class="cs-summary-note">' + _esc(previewLabel) + '</span>' : '') +
          '</button>' +
          '<button type="button" class="cs-feature-inspect muted" data-item-action="spell-info" data-spell-name="' + _esc(sc.name) + '">Spell Info</button>'
        );
      });
    } else if (spellCards.length === 0) {
      _extractItemSpellNames(item).forEach(function (spellName) {
        pieces.push(
          '<button type="button" class="cs-feature-inspect" data-item-action="cast-spell" data-spell-name="' + _esc(spellName) + '">Cast ' + _esc(spellName) + '</button>' +
          '<button type="button" class="cs-feature-inspect muted" data-item-action="spell-info" data-spell-name="' + _esc(spellName) + '">Spell Info</button>'
        );
      });
    }

    if (!pieces.length && !attunementWarn) return '';
    const chargeRow = chargeLabel ? '<div class="cs-summary-note" style="margin-top:0.18rem;">Charges: ' + chargeLabel + '</div>' : '';
    return attunementWarn + chargeRow + (pieces.length ? '<div class="cs-combat-chip-row" style="margin-top:0.45rem;flex-wrap:wrap;">' + pieces.join('') + '</div>' : '');
  }

  function _renderItem(item, itemIndex, opts) {
    opts = opts || {};
    const equipped = Boolean(item.equipped);
    const meta = _itemMeta(item);
    const name = item.name || 'Item';
    const needsAttune = _requiresAttunement(item);
    const chargesMax = Number(item.charges_max || item.uses_max || (item.charges && item.charges.max) || 0) || 0;
    const chargesCur = Number(item.charges_current || item.uses_current || (item.charges && item.charges.current) || 0) || 0;
    const badges = [
      equipped ? '<span class="item-row-badge item-row-badge-equipped">Equipped</span>' : '',
      needsAttune ? '<span class="item-row-badge">Requires Attunement</span>' : '',
      item.attuned ? '<span class="item-row-badge">Attuned</span>' : '',
      chargesMax > 0 ? '<span class="item-row-badge">Charges ' + _esc(String(chargesCur)) + '/' + _esc(String(chargesMax)) + '</span>' : '',
      _containerLabel(item) ? '<span class="item-row-badge">' + _esc(_containerLabel(item)) + '</span>' : '',
    ].filter(Boolean).join('');
    const useable = !!(item.grants_action || item.consumable || item.healing_formula || chargesMax > 0);
    const buttons = [
      _actionButton('inspect', 'Inspect', itemIndex),
      ['weapon', 'armor', 'shield', 'ring', 'accessory', 'wondrous'].includes(_itemKind(item)) ? _actionButton(equipped ? 'unequip' : 'equip', equipped ? 'Unequip' : 'Equip', itemIndex) : '',
      needsAttune ? _actionButton(item.attuned ? 'unattune' : 'attune', item.attuned ? 'Unattune' : 'Attune', itemIndex) : '',
      useable ? _actionButton('use', 'Use', itemIndex) : '',
      !_isContainer(item) ? _actionButton('move', 'Move', itemIndex) : '',
      !_isContainer(item) ? _actionButton('send-to-player', 'Send', itemIndex) : '',
      _actionButton('drop', 'Drop', itemIndex),
      _isContainer(item) ? _actionButton('open-container', 'Open', itemIndex) : '',
    ].filter(Boolean).join('');
    const metaBits = [
      meta,
      _fmtWeight(_weight(item)) + ' each',
      'Qty ' + _qty(item),
      item.item_type || item.category || item.equipment_kind || '',
    ].filter(Boolean).join(' • ');
    const row = window.ItemRow.renderItemRow(item, {
      mode: 'view',
      rowClassName: 'cs-inv-item',
      dataset: { itemIndex: String(itemIndex) },
      equipped,
      noteHtml: `<div class="cs-summary-note" style="margin-top:0.18rem;">${_esc(metaBits)}</div>`,
      extraBadgesHtml: badges ? '<div class="cs-combat-chip-row" style="margin-top:0.35rem;flex-wrap:wrap;">' + badges + '</div>' : '',
      equip: {
        className: `cs-inv-equip-btn${equipped ? ' equipped' : ''}`,
        attrs: {
          'data-item-index': String(itemIndex),
          'aria-pressed': String(equipped),
          'aria-label': `${equipped ? 'Unequip' : 'Equip'} ${name}`,
        },
      },
    });
    row.style.display = 'block';
    if (buttons) row.insertAdjacentHTML('beforeend', '<div class="cs-combat-chip-row" style="margin-top:0.45rem;flex-wrap:wrap;">' + buttons + '</div>');
    const equippedActionsHtml = _renderEquippedActions(item, itemIndex);
    if (equippedActionsHtml) row.insertAdjacentHTML('beforeend', equippedActionsHtml);
    return row.outerHTML;
  }

  function _renderSection(title, items, empty) {
    return '<div class="cs-action-section"><div class="cs-action-section-title">' + _esc(title) + '</div>' +
      (items.length ? items.map(function (entry) { return _renderItem(entry.item, entry.originalIndex); }).join('') : '<div class="cs-empty-state compact"><span>' + _esc(empty || 'No items.') + '</span></div>') +
      '</div>';
  }

  function _renderContainers(entries) {
    return '<div class="cs-action-section"><div class="cs-action-section-title">Containers</div>' +
      (entries.length ? entries.map(function (entry) {
        const item = entry.item;
        const fill = _containerContentsWeight(item);
        const cap = _containerCapacity(item);
        const pct = cap > 0 ? Math.min(100, Math.round((fill / cap) * 100)) : 0;
        return '<div class="cs-inv-container-card">' + _renderItem(item, entry.originalIndex) +
          '<div class="cs-summary-note">Bag weight: ' + _esc(_fmtWeight(_weight(item))) + ' • Contents: ' + _esc(_fmtWeight(fill)) + ' • Capacity: ' + _esc(cap ? _fmtWeight(cap) : '—') + '</div>' +
          '<div style="height:8px;border-radius:999px;background:rgba(128,128,128,.18);overflow:hidden;margin:.35rem 0;"><div style="height:100%;width:' + _esc(String(pct)) + '%;background:var(--gold,#c9a227);"></div></div>' +
          '<div class="cs-overview-list">' + (Array.isArray(item.bag_contents) && item.bag_contents.length ? item.bag_contents.map(function (row, ci) {
            return '<div class="cs-overview-row"><strong>' + _esc(row.name || 'Item') + '</strong><span>' + _esc('Qty ' + _qty(row) + ' • ' + _fmtWeight(_weight(row) * _qty(row))) + '</span>' +
              _actionButton('container-remove', 'Remove', entry.originalIndex, { 'data-content-index': String(ci) }) + '</div>';
          }).join('') : '<div class="cs-empty-state compact"><span>Empty.</span></div>') + '</div></div>';
      }).join('') : '<div class="cs-empty-state compact"><span>No containers found.</span></div>') +
      '</div>';
  }

  function _gearFallbackItems(charData) {
    const raw = (charData && (charData.gear || (charData.book && charData.book.gear))) || '';
    return String(raw || '').split(/\n+/).map(function (line) {
      const clean = String(line || '').trim();
      if (!clean) return null;
      const match = clean.match(/^(.*?)(?:\s*[×x]\s*(\d+))?$/);
      const name = String((match && match[1]) || clean).replace(/\(equipped\)/ig, '').trim();
      const qty = Math.max(1, parseInt((match && match[2]) || '1', 10) || 1);
      if (!name) return null;
      const kind = /shield/i.test(name) ? 'shield' : (/sword|axe|bow|crossbow|dagger|mace|staff|sling|hammer|spear|maul|rapier|scimitar|club/i.test(name) ? 'weapon' : (/armor|armour|mail|plate|leather|chain/i.test(name) ? 'armor' : 'gear'));
      return { name: name, qty: qty, equipped: /\(equipped\)/i.test(clean), kind: kind };
    }).filter(Boolean);
  }

  function _liveCurrency(charData) {
    const liveGold = (typeof global._getLivePlayerGoldValue === 'function') ? Number(global._getLivePlayerGoldValue() || 0) : 0;
    if (liveGold > 0) return { gp: Math.floor(liveGold / 100), sp: Math.floor((liveGold % 100) / 10), cp: liveGold % 10, ep: 0, pp: 0 };
    return (charData && charData.currency && typeof charData.currency === 'object') ? charData.currency : {};
  }

  function _mergeInventoryItems() {
    const merged = [];
    const byKey = new Map();
    function ingest(row) {
      const item = row && typeof row === 'object' ? Object.assign({}, row) : row;
      const normalized = (typeof global.normalizePlayerInventoryEntry === 'function') ? global.normalizePlayerInventoryEntry(item) : item;
      if (!normalized || typeof normalized !== 'object') return;
      const key = _itemKey(normalized);
      if (!key) return;
      const existing = byKey.get(key);
      if (!existing) {
        byKey.set(key, normalized);
        merged.push(normalized);
        return;
      }
      Object.keys(normalized).forEach(function (field) {
        const value = normalized[field];
        if (value == null || value === '' || (Array.isArray(value) && !value.length)) return;
        if (existing[field] == null || existing[field] === '' || field === 'equipped' || field === 'qty' || field === 'damage' || field === 'damage_dice' || field === 'equip_slot') existing[field] = value;
      });
      if (normalized.equipped) existing.equipped = true;
    }
    Array.prototype.slice.call(arguments).forEach(function (list) { (Array.isArray(list) ? list : []).forEach(ingest); });
    return merged;
  }

  function _nativeDocInventoryItems() {
    const nativeDoc = global._activeNativeCharacterDocument && typeof global._activeNativeCharacterDocument === 'object'
      ? global._activeNativeCharacterDocument
      : {};
    const equipment = nativeDoc.equipment && typeof nativeDoc.equipment === 'object' ? nativeDoc.equipment : {};
    const inventory = Array.isArray(equipment.inventory) ? equipment.inventory.slice() : [];
    const equipped = equipment.equipped && typeof equipment.equipped === 'object' ? equipment.equipped : {};
    Object.keys(equipped).forEach(function (slot) {
      const row = equipped[slot];
      if (!row || typeof row !== 'object') return;
      const name = String(row.name || row.label || row.id || '').trim().toLowerCase();
      const existing = inventory.find(function (entry) { return String(entry && (entry.name || entry.label || entry.id || '')).trim().toLowerCase() === name; });
      if (existing) {
        existing.equipped = true;
        if (!existing.equip_slot) existing.equip_slot = String(slot || '').toLowerCase();
      } else {
        inventory.push(Object.assign({}, row, { equipped: true, equip_slot: String(slot || '').toLowerCase() }));
      }
    });
    return inventory;
  }

  function _inventorySourceItems(charData) {
    const direct = Array.isArray(charData && charData.inventory) ? charData.inventory : [];
    const live = (typeof global._getLivePlayerInventoryEntries === 'function') ? global._getLivePlayerInventoryEntries() : (Array.isArray(global.playerInventory) ? global.playerInventory : []);
    const native = _nativeDocInventoryItems();
    const imported = Array.isArray(charData && charData.inventoryEntries) ? charData.inventoryEntries : [];
    const fallback = _gearFallbackItems(charData);
    return _mergeInventoryItems(live, native, direct, imported, fallback);
  }

  function _resolveLiveInventoryIndex(item) {
    const live = (typeof global._getLivePlayerInventoryEntries === 'function') ? global._getLivePlayerInventoryEntries() : (Array.isArray(global.playerInventory) ? global.playerInventory : []);
    const wantedKey = _itemKey(item);
    const wantedName = String(item && item.name || '').trim().toLowerCase();
    let found = -1;
    (Array.isArray(live) ? live : []).some(function (entry, idx) {
      const entryKey = _itemKey(entry);
      const entryName = String(entry && entry.name || '').trim().toLowerCase();
      if ((wantedKey && entryKey && wantedKey === entryKey) || (wantedName && entryName === wantedName)) {
        found = idx;
        return true;
      }
      return false;
    });
    return found;
  }

  function _patchEquippedState(item, nextEquipped, charData) {
    const wantedKey = _itemKey(item);
    const wantedName = String(item && item.name || '').trim().toLowerCase();
    const patchList = function (list) {
      (Array.isArray(list) ? list : []).forEach(function (entry) {
        const entryKey = _itemKey(entry);
        const entryName = String(entry && entry.name || '').trim().toLowerCase();
        if ((wantedKey && entryKey && wantedKey === entryKey) || (wantedName && entryName === wantedName)) {
          entry.equipped = !!nextEquipped;
        }
      });
    };
    patchList(charData && charData.inventory);
    patchList(charData && charData.inventoryEntries);
    patchList(global.playerInventory);
    if (global._charSheet && typeof global._charSheet === 'object') {
      if (!Array.isArray(global._charSheet.inventory)) global._charSheet.inventory = [];
      patchList(global._charSheet.inventory);
    }
  }

  function _requestOverviewRefresh() {
    if (global.AppCharacterSheetRuntime && typeof global.AppCharacterSheetRuntime.requestCharacterBookOverviewRender === 'function') {
      global.AppCharacterSheetRuntime.requestCharacterBookOverviewRender('updateMyChar');
      return;
    }
    if (typeof global.requestCharacterBookOverviewRender === 'function') {
      global.requestCharacterBookOverviewRender('updateMyChar');
    }
  }

  function _openContainerModal(bagIndex, charData) {
    const items = _inventorySourceItems(charData || {});
    const bagItem = items[bagIndex];
    if (!bagItem) return;
    // Resolve the live (server-side) index for the bag so bag_index sent over WS matches the server's array.
    const liveBagIndex = _resolveLiveInventoryIndex(bagItem);
    const serverBagIndex = liveBagIndex >= 0 ? liveBagIndex : bagIndex;
    const bagName = _esc(bagItem.name || 'Container');
    const contents = Array.isArray(bagItem.bag_contents) ? bagItem.bag_contents : [];
    const cap = _containerCapacity(bagItem);
    const fill = _containerContentsWeight(bagItem);
    const pct = cap > 0 ? Math.min(100, Math.round((fill / cap) * 100)) : 0;

    // Available items that can be put in (not the bag itself, not already inside).
    // Use the live index for each item so item_index sent over WS matches the server's array.
    const available = items.map(function (it, idx) {
      const liveIdx = _resolveLiveInventoryIndex(it);
      return { it: it, idx: liveIdx >= 0 ? liveIdx : idx };
    }).filter(function (e) {
      return e.idx !== serverBagIndex && !_isContainer(e.it) && !(e.it.container_name || e.it.container);
    });

    const contentsHtml = contents.length
      ? contents.map(function (row, ci) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:0.4rem 0.5rem;border-bottom:1px solid rgba(255,255,255,0.06);">' +
          '<span>' + _esc(row.name || 'Item') + ' <span style="color:rgba(255,255,255,0.45);font-size:0.8em;">×' + _esc(String(_qty(row))) + ' • ' + _esc(_fmtWeight(_weight(row) * _qty(row))) + '</span></span>' +
          '<button type="button" style="font-size:0.7rem;padding:0.2rem 0.5rem;background:rgba(220,60,60,0.15);border:1px solid rgba(220,60,60,0.35);color:#ff7070;border-radius:6px;cursor:pointer;" data-modal-remove-ci="' + String(ci) + '">Remove</button>' +
          '</div>';
      }).join('')
      : '<div style="color:rgba(255,255,255,0.4);padding:0.6rem 0.5rem;font-size:0.85em;">Empty.</div>';

    const addOptsHtml = available.length
      ? '<select id="rp-container-add-sel" style="flex:1;min-width:0;padding:0.3rem 0.5rem;background:rgba(8,20,28,0.7);border:1px solid rgba(201,162,39,0.3);color:#e8d5a3;border-radius:6px;font-size:0.82rem;">' +
        '<option value="">— select item —</option>' +
        available.map(function (e) { return '<option value="' + String(e.idx) + '">' + _esc(e.it.name || 'Item') + ' (' + _esc(_fmtWeight(_weight(e.it))) + ')</option>'; }).join('') +
        '</select>' +
        '<button type="button" id="rp-container-add-btn" style="padding:0.3rem 0.7rem;background:rgba(0,229,204,0.1);border:1px solid rgba(0,229,204,0.35);color:#00e5cc;border-radius:6px;cursor:pointer;white-space:nowrap;">Put In</button>'
      : '<span style="color:rgba(255,255,255,0.35);font-size:0.82em;">No items available to add.</span>';

    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.72);';
    overlay.innerHTML = '<div style="background:#0d1a22;border:1px solid rgba(201,162,39,0.35);border-radius:14px;min-width:320px;max-width:480px;width:90vw;max-height:80vh;display:flex;flex-direction:column;box-shadow:0 8px 40px rgba(0,0,0,0.7);">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;padding:0.8rem 1rem;border-bottom:1px solid rgba(201,162,39,0.2);">' +
      '<strong style="color:#c9a227;font-size:1rem;">' + bagName + '</strong>' +
      '<button type="button" id="rp-container-close" style="background:none;border:none;color:rgba(255,255,255,0.5);font-size:1.2rem;cursor:pointer;line-height:1;">✕</button>' +
      '</div>' +
      (cap > 0 ? '<div style="padding:0.5rem 1rem 0;">' +
        '<div style="font-size:0.75rem;color:rgba(255,255,255,0.45);margin-bottom:0.25rem;">Contents: ' + _esc(_fmtWeight(fill)) + ' / ' + _esc(_fmtWeight(cap)) + '</div>' +
        '<div style="height:6px;border-radius:999px;background:rgba(128,128,128,.18);overflow:hidden;"><div style="height:100%;width:' + _esc(String(pct)) + '%;background:#c9a227;"></div></div>' +
        '</div>' : '') +
      '<div style="overflow-y:auto;flex:1;padding:0.5rem 0;">' + contentsHtml + '</div>' +
      '<div style="padding:0.6rem 1rem;border-top:1px solid rgba(255,255,255,0.08);display:flex;gap:0.5rem;align-items:center;">' + addOptsHtml + '</div>' +
      '</div>';

    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) { document.body.removeChild(overlay); return; }
      const closeBtn = e.target.closest('#rp-container-close');
      if (closeBtn) { document.body.removeChild(overlay); return; }
      const removeBtn = e.target.closest('[data-modal-remove-ci]');
      if (removeBtn) {
        const ci = parseInt(removeBtn.getAttribute('data-modal-remove-ci') || '-1', 10);
        if (ci >= 0) _sendInventoryWs('bag_remove_item', { bag_index: serverBagIndex, content_index: ci, qty: 1 });
        document.body.removeChild(overlay);
        return;
      }
      const addBtn = e.target.closest('#rp-container-add-btn');
      if (addBtn) {
        const sel = overlay.querySelector('#rp-container-add-sel');
        const val = sel && sel.value;
        if (!val && val !== 0) return;
        _sendInventoryWs('bag_add_item', { bag_index: serverBagIndex, item_index: parseInt(String(val), 10), qty: 1 });
        document.body.removeChild(overlay);
        return;
      }
    });
  }

  function _bindInteractions(container, charData) {
    container.addEventListener('click', function (e) {
      const equipBtn = e.target.closest('.cs-inv-equip-btn');
      if (equipBtn) {
        const idx = parseInt(equipBtn.getAttribute('data-item-index'), 10);
        const allItems = _inventorySourceItems(charData || {});
        const item = allItems[idx];
        // Only process equip clicks for items that can actually be equipped
        if (!item || !['weapon', 'armor', 'shield', 'ring', 'accessory', 'wondrous'].includes(_itemKind(item))) return;
        const nextEquipped = !item.equipped;
        _patchEquippedState(item, nextEquipped, charData);
        const liveIndex = _resolveLiveInventoryIndex(item);
        if (liveIndex >= 0) {
          if (nextEquipped && typeof global.equipInventoryItem === 'function') global.equipInventoryItem(liveIndex);
          if (!nextEquipped && typeof global.unequipInventoryItem === 'function') global.unequipInventoryItem(liveIndex);
        }
        _requestOverviewRefresh();
        initInventoryTab(container, charData);
        return;
      }

      const actionBtn = e.target.closest('[data-item-action]');
      if (!actionBtn) return;
      e.preventDefault();
      e.stopPropagation();
      const action = String(actionBtn.getAttribute('data-item-action') || '');
      const actionId = String(actionBtn.getAttribute('data-action-id') || '');
      const actionSource = String(actionBtn.getAttribute('data-action-source') || 'equip_only');
      const spellName = String(actionBtn.getAttribute('data-spell-name') || '');
      const spellId = String(actionBtn.getAttribute('data-spell-id') || '');
      const itemId = String(actionBtn.getAttribute('data-item-id') || '');
      const itemIndex = parseInt(actionBtn.getAttribute('data-item-index') || '-1', 10);
      const chargeCost = parseInt(actionBtn.getAttribute('data-charge-cost') || '1', 10);
      const castLevel = parseInt(actionBtn.getAttribute('data-cast-level') || '0', 10);

      if (action === 'equip' || action === 'unequip') {
        _sendInventoryWs(action === 'equip' ? 'inventory_equip_item' : 'inventory_unequip_item', { item_index: Math.max(0, itemIndex) });
        return;
      }
      if (action === 'attune' || action === 'unattune') {
        _sendInventoryWs(action === 'attune' ? 'inventory_attune_item' : 'inventory_unattune_item', { item_index: Math.max(0, itemIndex) });
        return;
      }
      if (action === 'use') {
        _sendInventoryWs('inventory_use_item_action', { item_index: Math.max(0, itemIndex) });
        return;
      }
      if (action === 'drop') {
        _sendInventoryWs('inventory_remove_item', { item_index: Math.max(0, itemIndex), qty: 1 });
        return;
      }
      if (action === 'move') {
        const items = _inventorySourceItems(charData || {});
        const sourceItem = items[itemIndex];
        const liveItemIndex = sourceItem ? _resolveLiveInventoryIndex(sourceItem) : -1;
        const serverItemIndex = liveItemIndex >= 0 ? liveItemIndex : itemIndex;
        const containers = items.map(function (row, idx) {
          const liveIdx = _resolveLiveInventoryIndex(row);
          return { row: row, idx: liveIdx >= 0 ? liveIdx : idx };
        }).filter(function (entry) { return _isContainer(entry.row); });
        if (!containers.length) {
          alert('No available containers found.');
          return;
        }
        const choice = prompt('Move to container:\\n' + containers.map(function (entry, n) { return String(n + 1) + '. ' + (entry.row.name || 'Container'); }).join('\\n'), '1');
        const chosen = containers[(parseInt(choice || '0', 10) || 0) - 1];
        if (chosen) _sendInventoryWs('bag_add_item', { bag_index: chosen.idx, item_index: Math.max(0, serverItemIndex), qty: 1 });
        return;
      }
      if (action === 'send-to-player') {
        var players = Object.values(global.users && typeof global.users === 'object' ? global.users : {})
          .filter(function (u) { return u && u.role !== 'viewer' && String(u.user_id || u.id || '') !== String(global.USER_ID || ''); });
        if (!players.length) { alert('No other players in this session.'); return; }
        var playerList = players.map(function (p, n) { return String(n + 1) + '. ' + (p.name || p.display_name || p.username || 'Player'); }).join('\n');
        var allItems = _inventorySourceItems(charData || {});
        var theItem = allItems[itemIndex];
        var choice = prompt('Send "' + (theItem ? theItem.name || 'item' : 'item') + '" to which player?\n' + playerList, '1');
        if (choice === null) return;
        var chosen = players[(parseInt(choice || '0', 10) || 0) - 1];
        if (!chosen) { alert('Invalid selection.'); return; }
        var targetId = String(chosen.user_id || chosen.id || '');
        if (targetId) _sendInventoryWs('inventory_transfer_item', { item_index: Math.max(0, itemIndex), target_user_id: targetId, qty: 1 });
        return;
      }
      if (action === 'open-container') {
        _openContainerModal(itemIndex, charData);
        return;
      }
      if (action === 'container-remove') {
        const contentIndex = parseInt(actionBtn.getAttribute('data-content-index') || '-1', 10);
        _sendInventoryWs('bag_remove_item', { bag_index: Math.max(0, itemIndex), content_index: Math.max(0, contentIndex), qty: 1 });
        return;
      }
      if (action === 'inspect') {
        alert(String(actionBtn.closest('.cs-inv-item')?.querySelector('.item-row-name')?.textContent || 'Item'));
        return;
      }

      if (action === 'attack' && actionId && typeof global.playerUseAction === 'function') {
        global.playerUseAction(actionSource, actionId);
        return;
      }
      if (action === 'attack-info' && actionId && typeof global.playerInspectAction === 'function') {
        global.playerInspectAction(actionSource, actionId);
        return;
      }
      if (action === 'cast-item-spell' && (spellId || spellName)) {
        const targetId = String((typeof global._selectedTokenId !== 'undefined' ? global._selectedTokenId : '') || '');
        if (typeof global.sendWS === 'function') {
          global.sendWS({
            type: 'inventory_cast_item_spell',
            payload: {
              item_index: Math.max(0, itemIndex),
              item_id: itemId,
              spell_id: spellId || spellName.toLowerCase().replace(/\s+/g, '-'),
              target_id: targetId,
              charge_cost: Math.max(0, chargeCost),
              cast_level: Math.max(0, castLevel),
            },
          });
        } else if (typeof global.castRulesSpell === 'function') {
          global.castRulesSpell(spellName);
        }
        return;
      }
      if (action === 'cast-spell' && spellName && typeof global.castRulesSpell === 'function') {
        global.castRulesSpell(spellName);
        return;
      }
      if (action === 'spell-info' && spellName && typeof global.playerInspectSpell === 'function') {
        global.playerInspectSpell(spellName);
      }
    });
  }

  function initInventoryTab(container, charData) {
    if (!container) return;

    const currency = _liveCurrency(charData);
    const sourceItems = _inventorySourceItems(charData);
    const entries = sourceItems.map(function (item, idx) { return { item: item, originalIndex: idx }; });
    const equipped = entries.filter(function (entry) { return !!(entry.item && entry.item.equipped); });
    const containers = entries.filter(function (entry) { return _isContainer(entry.item); });
    const consumables = entries.filter(function (entry) { return !!(entry.item && (entry.item.consumable || entry.item.healing_formula || String(entry.item.item_type || '').toLowerCase() === 'potion')); });
    const carried = entries.filter(function (entry) { return !entry.item?.equipped && !_isContainer(entry.item) && !entry.item?.container && !entry.item?.container_name; });

    container.innerHTML = `
      <div class="cs-action-section"><div class="cs-action-section-title">Currency</div>${_renderCurrency(currency) || '<div class="cs-empty-state compact"><span>No currency found.</span></div>'}</div>
      <div class="cs-feature-section-copy" style="margin-bottom:0.65rem;">Inventory is grouped by Equipped, Attunement, Containers, Consumables, Carried Items, and All Items while reusing the live inventory websocket handlers.</div>
      ${_renderSection('Equipped', equipped, 'No equipped items.')}
      ${_renderAttunement(sourceItems)}
      ${_renderContainers(containers)}
      ${_renderSection('Consumables', consumables, 'No consumables.')}
      ${_renderSection('Carried Items', carried, 'No carried items.')}
      ${_renderSection('All Items', entries, 'No inventory items.')}
    `;

    if (!container.__inventoryTabBound) {
      container.__inventoryTabBound = true;
      _bindInteractions(container, charData);
    }
  }

  global.InventoryTab = { initInventoryTab };
}(window));
