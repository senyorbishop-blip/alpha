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
    return direct;
  }

  function _equippableItems(items) {
    return (Array.isArray(items) ? items : []).filter(function (item) {
      return ['weapon', 'armor', 'shield'].includes(_itemKind(item));
    });
  }

  function _backpackItems(items) {
    return (Array.isArray(items) ? items : []).filter(function (item) {
      return !_equippableItems([item]).length;
    });
  }

  function _renderBackpack(items) {
    const backpack = _backpackItems(items).slice(0, 10);
    if (!backpack.length) {
      return '<div class="cs-action-section"><div class="cs-action-section-title">Backpack</div><div class="cs-empty-state compact"><span>No backpack items found. Imported non-equipped gear will appear here when supported.</span></div></div>';
    }
    return '<div class="cs-action-section"><div class="cs-action-section-title">Backpack</div><div class="cs-overview-list">' + backpack.map(function (item) {
      const qty = parseInt(item && (item.quantity || item.qty || item.count) || 0, 10);
      const note = [qty > 1 ? ('Qty ' + qty) : '', item && (item.notes || item.description || item.category || item.item_type) || ''].filter(Boolean).join(' • ');
      return '<div class="cs-overview-row"><strong>' + _esc(item && item.name || 'Item') + '</strong><span>' + _esc(note) + '</span></div>';
    }).join('') + '</div></div>';
  }

  function _renderAttunement(items) {
    const attuned = (Array.isArray(items) ? items : []).filter(function (item) { return !!(item && (item.attuned || item.requires_attunement || item.attunement)); });
    const count = attuned.filter(function (item) { return !!(item && item.attuned); }).length;
    const label = attuned.length ? (String(count) + ' attuned / ' + String(attuned.length) + ' attunement-capable') : 'No attunement items found';
    return '<div class="cs-action-section"><div class="cs-action-section-title">Attunement</div><div class="cs-feature-section-copy">' + _esc(label) + '</div></div>';
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

  function _extractItemSpellNames(item) {
    const explicit = [];
    [item && item.spell, item && item.spells, item && item.spell_name, item && item.spell_names, item && item.granted_spells].forEach(function (value) {
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

  function _renderEquippedActions(item) {
    if (!item || !item.equipped) return '';
    const pieces = [];
    const attackCard = _findAttackCardForItem(item);
    if (attackCard) {
      pieces.push(
        '<button type="button" class="cs-feature-inspect" data-item-action="attack" data-action-source="' + _esc(String(attackCard.source || 'equip_only')) + '" data-action-id="' + _esc(String(attackCard.id || '')) + '">Attack / Roll</button>' +
        '<button type="button" class="cs-feature-inspect muted" data-item-action="attack-info" data-action-source="' + _esc(String(attackCard.source || 'equip_only')) + '" data-action-id="' + _esc(String(attackCard.id || '')) + '">Info</button>'
      );
    }
    _extractItemSpellNames(item).forEach(function (spellName) {
      pieces.push(
        '<button type="button" class="cs-feature-inspect" data-item-action="cast-spell" data-spell-name="' + _esc(spellName) + '">Cast ' + _esc(spellName) + '</button>' +
        '<button type="button" class="cs-feature-inspect muted" data-item-action="spell-info" data-spell-name="' + _esc(spellName) + '">Spell Info</button>'
      );
    });
    if (!pieces.length) return '';
    return '<div class="cs-combat-chip-row" style="margin-top:0.45rem;flex-wrap:wrap;">' + pieces.join('') + '</div>';
  }

  function _renderItem(item, itemIndex) {
    const equipped = Boolean(item.equipped);
    const meta = _itemMeta(item);
    return `<div class="cs-inv-item" data-item-index="${_esc(String(itemIndex))}" style="display:block;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:0.65rem;">
        <div style="min-width:0;flex:1;">
          <div style="display:flex;align-items:center;gap:0.45rem;flex-wrap:wrap;">
            <span class="cs-inv-item-name">${_esc(item.name || '—')}</span>
            <span class="cs-inv-item-qty">×${_esc(String(item.qty || item.quantity || 1))}</span>
            ${equipped ? '<span class="cs-status-chip good">Equipped</span>' : ''}
          </div>
          ${meta ? `<div class="cs-summary-note" style="margin-top:0.18rem;">${_esc(meta)}</div>` : ''}
        </div>
        <button class="cs-inv-equip-btn${equipped ? ' equipped' : ''}"
                data-item-index="${_esc(String(itemIndex))}"
                aria-pressed="${equipped}"
                aria-label="${equipped ? 'Unequip' : 'Equip'} ${_esc(item.name || 'item')}">
          ${equipped ? 'Unequip' : 'Equip'}
        </button>
      </div>
      ${_renderEquippedActions(item)}
    </div>`;
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

  function _bindInteractions(container, charData) {
    container.addEventListener('click', function (e) {
      const equipBtn = e.target.closest('.cs-inv-equip-btn');
      if (equipBtn) {
        const idx = parseInt(equipBtn.getAttribute('data-item-index'), 10);
        const inv = _equippableItems(_inventorySourceItems(charData || {}));
        const item = inv[idx];
        if (!item) return;
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
      if (action === 'attack' && actionId && typeof global.playerUseAction === 'function') {
        global.playerUseAction(actionSource, actionId);
        return;
      }
      if (action === 'attack-info' && actionId && typeof global.playerInspectAction === 'function') {
        global.playerInspectAction(actionSource, actionId);
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
    const inventory = _equippableItems(sourceItems);

    if (!inventory.length) {
      container.innerHTML = `${_renderCurrency(currency)}
        <div class="cs-empty-state">
          <span class="cs-empty-state-icon">🛡️</span>
          <span>No equipped weapon found. Go to Inventory to equip one.</span>
          <span class="cs-summary-note">Equipped weapons, armour, and shields appear here when the import or inventory has equippable gear.</span>
        </div>
        ${_renderBackpack(sourceItems)}
        ${_renderAttunement(sourceItems)}`;
      return;
    }

    const groups = {};
    CATEGORY_ORDER.forEach(function (cat) { groups[cat] = []; });
    inventory.forEach(function (item, i) {
      const category = _categoryForItem(item);
      groups[category].push({ item: item, originalIndex: i });
    });

    const sections = CATEGORY_ORDER.map(function (cat) {
      const entries = groups[cat] || [];
      if (!entries.length) return '';
      return `<div class="cs-inv-category">
        <div class="cs-inv-category-title">${_esc(cat)}</div>
        ${entries.map(function (entry) { return _renderItem(entry.item, entry.originalIndex); }).join('')}
      </div>`;
    }).join('');

    container.innerHTML = `
      <div class="cs-action-section"><div class="cs-action-section-title">Currency</div>${_renderCurrency(currency) || '<div class="cs-empty-state compact"><span>No currency found.</span></div>'}</div>
      <div class="cs-feature-section-copy" style="margin-bottom:0.65rem;">Inventory is grouped as Equipped, Backpack, Currency, and Attunement so the live play loadout is easy to scan without losing imported items.</div>
      <div class="cs-action-section"><div class="cs-action-section-title">Equipped</div>${sections || '<div class="cs-empty-state compact"><span>No equipped weapon found. Go to Inventory to equip one.</span></div>'}</div>
      ${_renderBackpack(sourceItems)}
      ${_renderAttunement(sourceItems)}
    `;

    if (!container.__inventoryTabBound) {
      container.__inventoryTabBound = true;
      _bindInteractions(container, charData);
    }
  }

  global.InventoryTab = { initInventoryTab };
}(window));
