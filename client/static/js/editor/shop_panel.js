/**
 * shop_panel.js
 * DM-side shop configuration + inventory editor panel.
 *
 * Usage:
 *   ShopPanel.open(instance, onSave)
 *   ShopPanel.close()
 *
 * `instance` — prop item (kind: shop / merchant / etc.) with optional fields:
 *   { id, name, shopkeeper_name, shop_type, description, inventory[] }
 * `onSave(config)` — called when DM clicks Save with full config object.
 *
 * Inventory item schema sent to server:
 *   { item_name, item_type, description, price_gp, price_sp, price_cp, quantity, item_data }
 */
(function () {
  'use strict';

  let _panelEl = null;
  let _onSave  = null;
  let _propId  = null;

  const PANEL_ID = 'dnd-shop-panel';

  const SHOPKEEPER_PERSONALITIES = [
    { value: 'friendly', label: 'Friendly' },
    { value: 'gruff', label: 'Gruff' },
    { value: 'greedy', label: 'Greedy' },
    { value: 'shifty', label: 'Shifty' },
    { value: 'scholarly', label: 'Scholarly' },
  ];

  const SHOPKEEPER_VOICES = [
    { value: 'grand_narrator', label: 'Grand Narrator' },
    { value: 'warm_storyteller', label: 'Warm Storyteller' },
    { value: 'gruff_merchant', label: 'Gruff Merchant' },
    { value: 'mysterious_oracle', label: 'Mysterious Oracle' },
  ];

  const SHOP_TYPES = [
    { value: 'general',      label: 'General Store' },
    { value: 'blacksmith',   label: 'Blacksmith'    },
    { value: 'alchemist',    label: 'Alchemist'     },
    { value: 'magic',        label: 'Magic Shop'    },
    { value: 'black_market', label: 'Black Market'  },
  ];

  const SHOP_STOCK_TEMPLATES = {
    general: [
      ['Rations', 0, 5, 0, 'Travel-ready dry food for one day.'],
      ['Torch', 0, 1, 0, 'Burns for 1 hour.'],
      ['Rope (50 ft.)', 1, 0, 0, 'Hempen rope bundle.'],
      ['Lantern, Hooded', 5, 0, 0, 'Reliable lantern with shutters.'],
      ['Oil Flask', 0, 1, 0, 'Lamp oil or improvised fire starter.'],
      ['Bedroll', 1, 0, 0, 'Simple field bedding.'],
      ['Healing Herb Poultice', 2, 5, 0, 'Common herbal wrap sold by travelers.'],
      ['Glowmoss Lantern', 20, 0, 0, 'Smokeless moss lantern for caves and crypts.'],
      ['Field Repair Kit', 15, 0, 0, 'Needle, rivets, and wax cord for camp repairs.'],
      ['Cured Hide Bundle', 4, 0, 0, 'Tanned strips useful for leatherwork recipes.'],
    ],
    blacksmith: [
      ['Longsword', 15, 0, 0, 'Balanced steel blade with leather grip.'],
      ['Shield', 10, 0, 0, 'Wood and steel-rimmed shield.'],
      ['Chain Shirt', 50, 0, 0, 'Light mail shirt for seasoned guards.'],
      ['Warhammer', 15, 0, 0, 'Solid head with reinforced haft.'],
      ['Bundle of 20 Arrows', 1, 0, 0, 'Goose-feather fletching.'],
      ['Smithing Repair Kit', 8, 0, 0, 'Patches, rivets, and leather ties.'],
      ['Bloomsteel Ingot', 15, 0, 0, 'Guild-marked ingot used for forged equipment.'],
      ['Bone-Reinforced Buckler', 20, 0, 0, 'Compact shield laminated with bone ribs.'],
    ],
    alchemist: [
      ['Healing Potion', 50, 0, 0, 'Red restorative in a stoppered vial.'],
      ['Antitoxin', 50, 0, 0, 'Bitter draught that steadies the body.'],
      ['Alchemist’s Fire', 50, 0, 0, 'Sticky burning flask.'],
      ['Acid Flask', 25, 0, 0, 'Corrosive green liquid.'],
      ['Smelling Salts', 3, 0, 0, 'Sharp salts to rouse the faint.'],
      ['Bandage Roll', 0, 8, 0, 'Sterile linen wrap.'],
      ['Stitchleaf Salve', 8, 0, 0, 'Herbal salve for field treatment.'],
      ['Minor Vigor Tonic', 18, 0, 0, 'Bitter tonic used by caravan medics.'],
      ['Venom Sac', 12, 0, 0, 'Monster reagent for poison and antidote work.'],
    ],
    magic: [
      ['Spell Scroll (1st Level)', 75, 0, 0, 'A neatly scribed novice scroll.'],
      ['Arcane Focus Crystal', 12, 0, 0, 'Clear crystal tuned for spellwork.'],
      ['Potion of Climbing', 180, 0, 0, 'Sticky amber potion.'],
      ['Moon-Touched Blade', 120, 0, 0, 'Sheds moonlight in darkness.'],
      ['Wand of Sparks', 35, 0, 0, 'Minor cantrip wand for apprentices.'],
    ],
    black_market: [
      ['Lockpick Roll', 25, 0, 0, 'Slim picks wrapped in oilcloth.'],
      ['Poison Vial (Weak)', 65, 0, 0, 'Illegal venom in smoked glass.'],
      ['False Papers', 30, 0, 0, 'Stamped travel papers of dubious quality.'],
      ['Concealed Dagger', 4, 0, 0, 'Flat blade made for sleeves and boots.'],
      ['Silent Shoes', 45, 0, 0, 'Soft-soled shoes favored by burglars.'],
      ['Smoke Capsule', 6, 0, 0, 'Break to create fast-covering smoke.'],
      ['Aether Dust', 45, 0, 0, 'Rare contraband arcane residue.'],
    ],
  };

  const PROFESSION_CHOICES = [
    { id: 'blacksmithing', label: 'Blacksmithing' },
    { id: 'leatherworking', label: 'Leatherworking' },
    { id: 'alchemy', label: 'Potion Crafting / Alchemy' },
    { id: 'woodworking', label: 'Woodworking' },
    { id: 'tailoring', label: 'Tailoring' },
  ];
  const BUY_CATEGORIES = [
    { id: 'consumable', label: 'Consumables' },
    { id: 'material', label: 'Materials' },
    { id: 'weapon', label: 'Weapons' },
    { id: 'armor', label: 'Armor' },
    { id: 'tool', label: 'Tools' },
    { id: 'gear', label: 'General Gear' },
  ];

  const DEFAULT_PROF_BY_TYPE = {
    blacksmith: ['blacksmithing'],
    alchemist: ['alchemy'],
    general: ['woodworking'],
    magic: ['tailoring'],
    black_market: ['leatherworking'],
  };

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function genId() {
    return `shop_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
  }

  function normalizeInventoryItem(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const item_name = String(raw.item_name || raw.name || '').trim();
    if (!item_name) return null;
    const priceFromUnits = Number(raw.price_units);
    const hasUnitPrice = Number.isFinite(priceFromUnits) && priceFromUnits >= 0;
    const gp = hasUnitPrice ? Math.floor(priceFromUnits / 100) : Math.max(0, parseInt(raw.price_gp, 10) || 0);
    const sp = hasUnitPrice ? Math.floor((priceFromUnits % 100) / 10) : Math.max(0, parseInt(raw.price_sp, 10) || 0);
    const cp = hasUnitPrice ? Math.floor(priceFromUnits % 10) : Math.max(0, parseInt(raw.price_cp, 10) || 0);
    let quantity = raw.quantity;
    if (quantity == null && raw.qty != null) quantity = raw.qty;
    if (raw.infinite || raw.unlimited) quantity = null;
    return {
      item_name,
      item_type: String(raw.item_type || 'misc').trim().toLowerCase() || 'misc',
      description: String(raw.description || raw.notes || '').trim(),
      price_gp: gp,
      price_sp: sp,
      price_cp: cp,
      quantity: quantity === '' || quantity == null ? null : Math.max(0, parseInt(quantity, 10) || 0),
      item_data: raw.item_data && typeof raw.item_data === 'object' ? raw.item_data : {},
    };
  }

  /** @param {Array} items */
  function renderRows(items) {
    if (!items.length) {
      return '<tr><td colspan="8" style="text-align:center;color:var(--sp-muted);padding:0.8rem;">No items yet.</td></tr>';
    }
    return items.map((item, i) => `
      <tr data-idx="${i}">
        <td><input class="sp-input" data-field="item_name" value="${esc(item.item_name)}" placeholder="Item name" /></td>
        <td><input class="sp-input sp-num" data-field="price_gp" type="number" min="0" value="${Number(item.price_gp) || 0}" /></td>
        <td><input class="sp-input sp-num" data-field="price_sp" type="number" min="0" value="${Number(item.price_sp) || 0}" /></td>
        <td><input class="sp-input sp-num" data-field="price_cp" type="number" min="0" value="${Number(item.price_cp) || 0}" /></td>
        <td><input class="sp-input sp-num" data-field="quantity" type="number" min="0" value="${item.quantity == null ? '' : Number(item.quantity)}" placeholder="∞" /></td>
        <td><input class="sp-input" data-field="description" value="${esc(item.description || '')}" placeholder="Description" /></td>
        <td><button class="sp-remove-btn" data-idx="${i}" title="Remove">✕</button></td>
      </tr>
    `).join('');
  }

  function collectInventory() {
    if (!_panelEl) return [];
    const rows = _panelEl.querySelectorAll('tbody tr[data-idx]');
    const result = [];
    rows.forEach(row => {
      const get = field => row.querySelector(`[data-field="${field}"]`)?.value?.trim() ?? '';
      const name = get('item_name');
      if (!name) return;
      const qtyRaw = get('quantity');
      result.push({
        item_name:   name,
        item_type:   'misc',
        description: get('description'),
        price_gp:    Math.max(0, parseInt(get('price_gp'), 10) || 0),
        price_sp:    Math.max(0, parseInt(get('price_sp'), 10) || 0),
        price_cp:    Math.max(0, parseInt(get('price_cp'), 10) || 0),
        quantity:    qtyRaw === '' ? null : Math.max(0, parseInt(qtyRaw, 10) || 0),
        item_data:   {},
      });
    });
    return result;
  }

  const ALL_ITEM_TYPES = ['weapon', 'armour', 'consumable', 'tool', 'material', 'trinket', 'magic', 'misc'];

  function collectConfig() {
    if (!_panelEl) return null;
    const taught_profession_ids = Array.from(_panelEl.querySelectorAll('input[name="sp-prof"]:checked'))
      .map(el => String(el.value || '').trim())
      .filter(Boolean);
    const accepted_item_types = Array.from(_panelEl.querySelectorAll('input[name="sp-item-type"]:checked'))
      .map(el => String(el.value || '').trim())
      .filter(Boolean);
    const rawBuyRate = parseInt(_panelEl.querySelector('#sp-buy-rate')?.value ?? '50', 10);
    const buy_rate_pct = Math.max(5, Math.min(95, isNaN(rawBuyRate) ? 50 : rawBuyRate));
    const rawCash = _panelEl.querySelector('#sp-vendor-cash')?.value?.trim() ?? '';
    const vendor_cash_units = rawCash === '' ? null : Math.max(0, parseInt(rawCash, 10) || 0) * 100;
    const shop_sales_enabled = !!(_panelEl.querySelector('#sp-shop-sales-enabled')?.checked);
    const player_sell_enabled = !!(_panelEl.querySelector('#sp-player-sell-enabled')?.checked);
    const buyback_enabled = !!(_panelEl.querySelector('#sp-buyback-enabled')?.checked);
    return {
      prop_id:         _propId,
      name:            _panelEl.querySelector('#sp-shop-name')?.value?.trim() || 'Shop',
      shopkeeper_name: _panelEl.querySelector('#sp-shopkeeper-name')?.value?.trim() || 'Shopkeeper',
      shop_type:       _panelEl.querySelector('#sp-shop-type')?.value || 'general',
      personality:     _panelEl.querySelector('#sp-personality')?.value || 'friendly',
      dialogue_enabled: !!_panelEl.querySelector('#sp-dialogue-enabled')?.checked,
      voice:           _panelEl.querySelector('#sp-voice')?.value || 'grand_narrator',
      tts_enabled:     !!_panelEl.querySelector('#sp-tts-enabled')?.checked,
      greeting_override: _panelEl.querySelector('#sp-greeting-override')?.value?.trim() || '',
      description:     _panelEl.querySelector('#sp-description')?.value?.trim() || '',
      taught_profession_ids,
      crafting_enabled: !!_panelEl.querySelector('#sp-crafting-enabled')?.checked,
      shop_sales_enabled,
      player_sell_enabled,
      // Backward-compat field for older backend paths.
      selling_enabled: player_sell_enabled,
      buy_categories: Array.from(_panelEl.querySelectorAll('input[name="sp-buy-cat"]:checked'))
        .map(el => String(el.value || '').trim())
        .filter(Boolean),
      inventory:       collectInventory(),
      buy_rate_pct,
      vendor_cash_units,
      accepted_item_types,
      buyback_enabled,
    };
  }

  function buildGeneratedStock(shopType) {
    const template = SHOP_STOCK_TEMPLATES[shopType] || SHOP_STOCK_TEMPLATES.general;
    return template.map(([item_name, price_gp, price_sp, price_cp, description], idx) => ({
      item_name,
      item_type: 'misc',
      description,
      price_gp,
      price_sp,
      price_cp,
      quantity: idx < 2 ? 3 : null,
      item_data: {},
    }));
  }

  /**
   * Open (or reopen) the DM shop editor panel.
   * @param {Object} instance  - prop item (id, name, inventory, shopkeeper_name, shop_type, description)
   * @param {Function} onSave  - called with full config on Save (also sends dm_configure_shop WS)
   */
  function open(instance, onSave) {
    close();
    _onSave = typeof onSave === 'function' ? onSave : null;
    _propId = instance.id || null;

    const inventory = (Array.isArray(instance.inventory) ? instance.inventory : [])
      .map(normalizeInventoryItem)
      .filter(Boolean);
    const propName     = String(instance.name || 'Shop');
    const shopkeeper   = String(instance.shopkeeper_name || '');
    const shopType     = String(instance.shop_type || 'general');
    const description  = String(instance.description || '');
    const personality = String(instance.personality || 'friendly');
    const dialogueEnabled = instance.dialogue_enabled !== false;
    const voice = String(instance.voice || 'grand_narrator');
    const ttsEnabled = !!instance.tts_enabled;
    const greetingOverride = String(instance.greeting_override || '');
    const craftingEnabled = instance.crafting_enabled !== false;
    const shopSalesEnabled = instance.shop_sales_enabled !== false;
    const playerSellEnabled = (instance.player_sell_enabled ?? instance.selling_enabled) !== false;
    const buybackEnabled = !!instance.buyback_enabled;
    const buyCats = Array.isArray(instance.buy_categories_json) ? instance.buy_categories_json : [];
    const acceptedTypesRaw = Array.isArray(instance.accepted_item_types)
      ? instance.accepted_item_types
      : (Array.isArray(instance.accepted_item_types_json) ? instance.accepted_item_types_json : []);
    const acceptedSet = new Set(acceptedTypesRaw.map(v => String(v || '').trim().toLowerCase()).filter(Boolean));
    const vendorCashGp = Math.max(0, Math.round((Number(instance.vendor_cash_units) || 0) / 100));
    const buyRatePct = Math.max(0, Math.min(100, Number(instance.buy_rate_pct) || 50));
    const taughtRaw = Array.isArray(instance.taught_profession_ids)
      ? instance.taught_profession_ids
      : (Array.isArray(instance.taught_professions_json) ? instance.taught_professions_json : []);
    const taughtInitial = taughtRaw.length ? taughtRaw : (DEFAULT_PROF_BY_TYPE[shopType] || []);

    const personalityOptions = SHOPKEEPER_PERSONALITIES.map(p =>
      `<option value="${p.value}"${personality === p.value ? ' selected' : ''}>${p.label}</option>`
    ).join('');
    const voiceOptions = SHOPKEEPER_VOICES.map(v =>
      `<option value="${v.value}"${voice === v.value ? ' selected' : ''}>${v.label}</option>`
    ).join('');
    const typeOptions = SHOP_TYPES.map(t =>
      `<option value="${t.value}"${shopType === t.value ? ' selected' : ''}>${t.label}</option>`
    ).join('');
    const profOptions = PROFESSION_CHOICES.map(prof => `
      <label class="sp-prof-chip">
        <input type="checkbox" name="sp-prof" value="${esc(prof.id)}"${taughtInitial.includes(prof.id) ? ' checked' : ''} />
        <span>${esc(prof.label)}</span>
      </label>
    `).join('');
    const buyCatOptions = BUY_CATEGORIES.map(cat => `
      <label class="sp-prof-chip">
        <input type="checkbox" name="sp-buy-cat" value="${esc(cat.id)}"${buyCats.includes(cat.id) ? ' checked' : ''} />
        <span>${esc(cat.label)}</span>
      </label>
    `).join('');

    const panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.innerHTML = `
      <div class="sp-header">
        <span class="sp-title">🏪 Configure Shop</span>
        <button class="sp-close-btn" title="Close">✕</button>
      </div>
      <div class="sp-body">
        <div class="sp-meta-grid">
          <label class="sp-label">Shop Name
            <input class="sp-input" id="sp-shop-name" placeholder="Shop name" maxlength="80" />
          </label>
          <label class="sp-label">Shopkeeper
            <input class="sp-input" id="sp-shopkeeper-name" placeholder="Shopkeeper name" maxlength="80" />
          </label>
          <label class="sp-label">Type
            <select class="sp-input" id="sp-shop-type">${typeOptions}</select>
          </label>
          <label class="sp-label">Personality
            <select class="sp-input" id="sp-personality">${personalityOptions}</select>
          </label>
          <label class="sp-label">Voice
            <select class="sp-input" id="sp-voice">${voiceOptions}</select>
          </label>
          <label class="sp-label sp-checkbox-label">
            <input type="checkbox" id="sp-dialogue-enabled" ${dialogueEnabled ? 'checked' : ''} />
            <span>Dialogue enabled</span>
          </label>
          <label class="sp-label sp-checkbox-label">
            <input type="checkbox" id="sp-tts-enabled" ${ttsEnabled ? 'checked' : ''} />
            <span>Speak greeting (TTS)</span>
          </label>
          <label class="sp-label sp-full">Greeting override
            <input class="sp-input" id="sp-greeting-override" maxlength="220" placeholder="Optional custom greeting line…" />
          </label>
          <label class="sp-label sp-full">Description
            <textarea class="sp-input" id="sp-description" rows="2" maxlength="500" placeholder="Flavor text shown to players…"></textarea>
          </label>
          <div class="sp-label sp-full">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;">
              <span>Teaches Professions</span>
              <button type="button" class="sp-gen-btn" id="sp-prof-defaults-btn">Apply Type Defaults</button>
            </div>
            <div class="sp-prof-grid">${profOptions}</div>
          </div>
          <div class="sp-label sp-full">
            <span>Economy Controls</span>
            <div class="sp-prof-grid" style="margin-top:0.2rem;">
              <label class="sp-prof-chip"><input type="checkbox" id="sp-crafting-enabled"${craftingEnabled ? ' checked' : ''} /><span>Crafting Enabled</span></label>
              <label class="sp-prof-chip"><input type="checkbox" id="sp-shop-sales-enabled"${shopSalesEnabled ? ' checked' : ''} /><span>Shop Sales Enabled</span></label>
            </div>
            <div class="sp-prof-grid">${buyCatOptions}</div>
          </div>
        </div>
        <div class="sp-section-label">Sell / Buy-Back Settings</div>
        <div class="sp-sell-grid">
          <label class="sp-label">
            <span>Buy Rate %</span>
            <input class="sp-input sp-num" id="sp-buy-rate" type="number" min="5" max="95" value="${buyRatePct}" title="% of item value the shop offers when buying from players (5–95)" />
          </label>
          <label class="sp-label">
            <span>Vendor Cash (GP, blank=∞)</span>
            <input class="sp-input sp-num" id="sp-vendor-cash" type="number" min="0" value="${vendorCashGp}" placeholder="∞" title="Max gold the vendor can spend buying from players" />
          </label>
          <label class="sp-label sp-checkbox-label">
            <input type="checkbox" id="sp-player-sell-enabled" ${playerSellEnabled ? 'checked' : ''} />
            <span>Players can sell to this shop</span>
          </label>
          <label class="sp-label sp-checkbox-label">
            <input type="checkbox" id="sp-buyback-enabled" ${buybackEnabled ? 'checked' : ''} />
            <span>Buyback enabled (allow resale of recently bought items)</span>
          </label>
          <div class="sp-label sp-full">
            <span>Accepted item categories</span>
            <div class="sp-type-grid">
              ${ALL_ITEM_TYPES.map(t => `
                <label class="sp-prof-chip">
                  <input type="checkbox" name="sp-item-type" value="${esc(t)}" ${acceptedSet.has(t) ? 'checked' : ''} />
                  <span>${esc(t.charAt(0).toUpperCase() + t.slice(1))}</span>
                </label>
              `).join('')}
            </div>
          </div>
        </div>
        <div class="sp-section-label">Inventory</div>
        <table class="sp-table">
          <thead>
            <tr>
              <th>Name</th><th>GP</th><th>SP</th><th>CP</th><th>Qty (blank=∞)</th><th>Description</th><th></th>
            </tr>
          </thead>
          <tbody>${renderRows(inventory)}</tbody>
        </table>
        <div class="sp-add-row">
          <input class="sp-input" id="sp-add-name"  placeholder="New item name" />
          <input class="sp-input sp-num" id="sp-add-gp"   type="number" min="0" value="0" placeholder="GP" />
          <input class="sp-input sp-num" id="sp-add-sp"   type="number" min="0" value="0" placeholder="SP" />
          <input class="sp-input sp-num" id="sp-add-cp"   type="number" min="0" value="0" placeholder="CP" />
          <input class="sp-input sp-num" id="sp-add-qty"  type="number" min="0" value="" placeholder="∞" />
          <input class="sp-input" id="sp-add-desc"  placeholder="Description" />
          <button class="sp-add-btn" id="sp-add-item-btn">+ Add</button>
          <button class="sp-gen-btn" id="sp-generate-stock-btn" title="Generate a starter shop inventory from the selected type">✨ Generate Stock</button>
          <button class="sp-lib-btn" id="sp-import-lib-btn" title="Import from item library">📚 Import</button>
        </div>
      </div>
      <div class="sp-footer">
        <button class="sp-save-btn" id="sp-save-btn">💾 Save Shop</button>
        <button class="sp-cancel-btn" id="sp-cancel-btn">Cancel</button>
      </div>
    `;
    _applyStyles(panel);
    document.body.appendChild(panel);
    _panelEl = panel;

    // Set user-supplied text values via DOM to avoid innerHTML injection
    panel.querySelector('#sp-shop-name').value = propName;
    panel.querySelector('#sp-shopkeeper-name').value = shopkeeper;
    panel.querySelector('#sp-description').value = description;
    panel.querySelector('#sp-greeting-override').value = greetingOverride;

    panel.querySelector('.sp-close-btn').addEventListener('click', close);
    panel.querySelector('#sp-cancel-btn').addEventListener('click', close);

    panel.querySelector('tbody').addEventListener('click', e => {
      const btn = e.target.closest('.sp-remove-btn');
      if (!btn) return;
      const idx = parseInt(btn.dataset.idx, 10);
      const current = collectInventory();
      current.splice(idx, 1);
      panel.querySelector('tbody').innerHTML = renderRows(current);
    });

    panel.querySelector('#sp-add-item-btn').addEventListener('click', () => {
      const addNameEl = panel.querySelector('#sp-add-name');
      const addQtyEl  = panel.querySelector('#sp-add-qty');
      const addDescEl = panel.querySelector('#sp-add-desc');
      const addGpEl   = panel.querySelector('#sp-add-gp');
      const addSpEl   = panel.querySelector('#sp-add-sp');
      const addCpEl   = panel.querySelector('#sp-add-cp');
      if (!addNameEl) return;
      const nameVal = addNameEl.value.trim();
      if (!nameVal) return;
      const current = collectInventory();
      const qtyRaw = addQtyEl?.value.trim() ?? '';
      current.push({
        item_name:   nameVal,
        item_type:   'misc',
        description: addDescEl?.value.trim() ?? '',
        price_gp:    Math.max(0, parseInt(addGpEl?.value ?? '0', 10) || 0),
        price_sp:    Math.max(0, parseInt(addSpEl?.value ?? '0', 10) || 0),
        price_cp:    Math.max(0, parseInt(addCpEl?.value ?? '0', 10) || 0),
        quantity:    qtyRaw === '' ? null : Math.max(0, parseInt(qtyRaw, 10) || 0),
        item_data:   {},
      });
      panel.querySelector('tbody').innerHTML = renderRows(current);
      addNameEl.value = '';
      if (addGpEl)   addGpEl.value   = '0';
      if (addSpEl)   addSpEl.value   = '0';
      if (addCpEl)   addCpEl.value   = '0';
      if (addQtyEl)  addQtyEl.value  = '';
      if (addDescEl) addDescEl.value = '';
    });

    panel.querySelector('#sp-generate-stock-btn').addEventListener('click', () => {
      const type = panel.querySelector('#sp-shop-type')?.value || 'general';
      const generated = buildGeneratedStock(type);
      panel.querySelector('tbody').innerHTML = renderRows(generated);
    });
    panel.querySelector('#sp-prof-defaults-btn')?.addEventListener('click', () => {
      const type = panel.querySelector('#sp-shop-type')?.value || 'general';
      const defaults = new Set(DEFAULT_PROF_BY_TYPE[type] || []);
      panel.querySelectorAll('input[name="sp-prof"]').forEach(el => { el.checked = defaults.has(el.value); });
    });

    // Import from item library
    panel.querySelector('#sp-import-lib-btn').addEventListener('click', () => {
      if (typeof openItemLibraryPicker === 'function') {
        openItemLibraryPicker('shop_panel', entry => {
          if (!entry || !entry.name) return;
          const current = collectInventory();
          current.push({
            item_name:   String(entry.name || '').slice(0, 80),
            item_type:   String(entry.item_type || 'misc').slice(0, 40),
            description: String(entry.description || '').slice(0, 500),
            price_gp:    Math.max(0, parseInt(entry.price_gp || entry.priceGP || 0, 10) || 0),
            price_sp:    Math.max(0, parseInt(entry.price_sp || 0, 10) || 0),
            price_cp:    Math.max(0, parseInt(entry.price_cp || 0, 10) || 0),
            quantity:    entry.quantity != null ? Math.max(0, parseInt(entry.quantity, 10) || 1) : null,
            item_data:   entry.item_data || {},
          });
          panel.querySelector('tbody').innerHTML = renderRows(current);
        });
      } else {
        // Fallback: show a small notice
        const notice = panel.querySelector('#sp-lib-notice');
        if (notice) { notice.textContent = 'Item library not available in this context.'; notice.style.display = 'block'; }
      }
    });

    panel.querySelector('#sp-save-btn').addEventListener('click', () => {
      const config = collectConfig();
      if (_onSave) _onSave(config);
      // Send over WS if available
      if (typeof sendWS === 'function') {
        sendWS({ type: 'dm_configure_shop', payload: config });
      }
      close();
    });
  }

  function close() {
    if (_panelEl) {
      _panelEl.remove();
      _panelEl = null;
    }
    _onSave = null;
    _propId = null;
  }

  function _applyStyles(panel) {
    Object.assign(panel.style, {
      position:    'fixed',
      top:         '10%',
      left:        '50%',
      transform:   'translateX(-50%)',
      zIndex:      '9900',
      width:       '780px',
      maxWidth:    '96vw',
      maxHeight:   '80vh',
      display:     'flex',
      flexDirection: 'column',
      background:  '#1e1e30',
      border:      '1px solid rgba(255,255,255,0.10)',
      borderRadius: '10px',
      boxShadow:   '0 12px 44px rgba(0,0,0,0.72)',
      color:       '#d0d0e8',
      fontFamily:  'inherit',
      fontSize:    '14px',
      overflow:    'hidden',
    });

    const style = document.createElement('style');
    style.textContent = `
      #${PANEL_ID} .sp-header {
        display:flex;align-items:center;justify-content:space-between;
        padding:0.65rem 1rem;background:#141420;border-bottom:1px solid rgba(255,255,255,0.07);
        flex-shrink:0;
      }
      #${PANEL_ID} .sp-title { font-weight:700;font-size:15px;color:#d0d0e8; }
      #${PANEL_ID} .sp-close-btn, #${PANEL_ID} .sp-remove-btn {
        background:none;border:none;color:#7070a0;cursor:pointer;font-size:16px;padding:0 4px;
      }
      #${PANEL_ID} .sp-close-btn:hover, #${PANEL_ID} .sp-remove-btn:hover { color:#ff6b6b; }
      #${PANEL_ID} .sp-body { flex:1;overflow-y:auto;padding:0.8rem 1rem; }
      #${PANEL_ID} .sp-meta-grid {
        display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.55rem;margin-bottom:0.8rem;
      }
      #${PANEL_ID} .sp-full { grid-column:1/-1; }
      #${PANEL_ID} .sp-label {
        display:flex;flex-direction:column;gap:0.22rem;font-size:11px;
        color:#7070a0;text-transform:uppercase;letter-spacing:0.06em;
      }
      #${PANEL_ID} .sp-section-label {
        font-size:11px;color:#7070a0;text-transform:uppercase;letter-spacing:0.08em;
        margin-bottom:0.4rem;margin-top:0.1rem;
      }
      #${PANEL_ID} .sp-table { width:100%;border-collapse:collapse; }
      #${PANEL_ID} .sp-table th {
        font-size:11px;color:#7070a0;text-transform:uppercase;letter-spacing:0.06em;
        padding:0.3rem 0.5rem;border-bottom:1px solid rgba(255,255,255,0.07);text-align:left;
      }
      #${PANEL_ID} .sp-table td { padding:0.28rem 0.4rem;border-bottom:1px solid rgba(255,255,255,0.04); }
      #${PANEL_ID} .sp-input {
        background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.10);border-radius:5px;
        color:#d0d0e8;padding:0.3rem 0.5rem;width:100%;box-sizing:border-box;font-size:13px;
      }
      #${PANEL_ID} textarea.sp-input { resize:vertical;min-height:44px; }
      #${PANEL_ID} .sp-input:focus { outline:none;border-color:#00e5cc;box-shadow:0 0 0 2px rgba(0,229,204,0.18); }
      #${PANEL_ID} .sp-num { width:60px; }
      #${PANEL_ID} .sp-add-row {
        display:flex;gap:0.4rem;margin-top:0.65rem;align-items:center;flex-wrap:wrap;
      }
      #${PANEL_ID} .sp-add-row .sp-input { flex:1;min-width:80px; }
      #${PANEL_ID} .sp-add-row .sp-num { flex:0 0 58px; }
      #${PANEL_ID} .sp-add-btn, #${PANEL_ID} .sp-lib-btn, #${PANEL_ID} .sp-gen-btn {
        padding:0.34rem 0.8rem;border-radius:6px;cursor:pointer;font-size:13px;white-space:nowrap;flex-shrink:0;
      }
      #${PANEL_ID} .sp-add-btn {
        background:rgba(0,229,204,0.15);border:1px solid rgba(0,229,204,0.35);color:#00e5cc;
      }
      #${PANEL_ID} .sp-add-btn:hover { background:rgba(0,229,204,0.25); }
      #${PANEL_ID} .sp-gen-btn {
        background:rgba(212,175,55,0.12);border:1px solid rgba(212,175,55,0.28);color:#f2d27a;
      }
      #${PANEL_ID} .sp-gen-btn:hover { background:rgba(212,175,55,0.22); }
      #${PANEL_ID} .sp-lib-btn {
        background:rgba(212,166,39,0.12);border:1px solid rgba(212,166,39,0.28);color:#d4a637;
      }
      #${PANEL_ID} .sp-lib-btn:hover { background:rgba(212,166,39,0.22); }
      #${PANEL_ID} .sp-footer {
        display:flex;gap:0.5rem;padding:0.6rem 1rem;border-top:1px solid rgba(255,255,255,0.07);
        justify-content:flex-end;flex-shrink:0;background:#141420;
      }
      #${PANEL_ID} .sp-save-btn {
        padding:0.42rem 1rem;background:rgba(0,229,204,0.18);border:1px solid rgba(0,229,204,0.4);
        border-radius:6px;color:#00e5cc;cursor:pointer;font-size:13px;font-weight:600;
      }
      #${PANEL_ID} .sp-save-btn:hover { background:rgba(0,229,204,0.3); }
      #${PANEL_ID} .sp-cancel-btn {
        padding:0.42rem 0.8rem;background:none;border:1px solid rgba(255,255,255,0.12);
        border-radius:6px;color:#7070a0;cursor:pointer;font-size:13px;
      }
      #${PANEL_ID} .sp-cancel-btn:hover { color:#d0d0e8;border-color:rgba(255,255,255,0.25); }
      #${PANEL_ID} .sp-prof-grid {
        display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:0.4rem;margin-top:0.3rem;
      }
      #${PANEL_ID} .sp-prof-chip {
        display:flex;align-items:center;gap:0.5rem;padding:0.45rem 0.55rem;border-radius:8px;
        border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.03);
        min-height:44px;
      }
      #${PANEL_ID} .sp-prof-chip input { width:18px;height:18px; }
      #${PANEL_ID} .sp-sell-grid {
        display:grid;grid-template-columns:1fr 1fr;gap:0.55rem;margin-bottom:0.8rem;
      }
      #${PANEL_ID} .sp-type-grid {
        display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:0.4rem;margin-top:0.3rem;
      }
      #${PANEL_ID} .sp-checkbox-label {
        display:flex;flex-direction:row;align-items:center;gap:0.55rem;min-height:44px;
        padding:0.3rem 0.55rem;border-radius:8px;border:1px solid rgba(255,255,255,0.12);
        background:rgba(255,255,255,0.03);cursor:pointer;font-size:12px;color:#b0b0d0;
      }
      #${PANEL_ID} .sp-checkbox-label input { width:18px;height:18px;flex-shrink:0; }
    `;
    document.head.appendChild(style);
  }

  window.ShopPanel = Object.freeze({ open, close });
})();
