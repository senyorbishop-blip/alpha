/**
 * shop_view.js
 * Player-side shop modal — Buy/Haggle + staged tabs for Sell/Craft/Services.
 */
(function () {
  'use strict';

  let _modalEl = null;
  let _shopData = null;
  let _goldUnits = 0;
  let _priceState = {};
  let _activeTab = 'buy';
  let _craftState = { recipes: [], jobs: [], now: 0 };
  let _campaignEconomy = { crafting_enabled: true, selling_enabled: true };
  let _professionState = {
    catalog: [],
    player_profession_ids: [],
    teachable_profession_ids: [],
    max_professions: 2,
    open_slots: 2,
  };
  // Sell tab state
  let _sellOffers = [];         // array of offer objects from server
  let _sellLoading = false;     // waiting for sell_offers response
  let _greetingSpokenText = '';
  let _sellMeta = {             // shop sell config echoed from server
    selling_enabled: true,
    buy_rate_pct: 50,
    vendor_cash_units: null,
    accepted_item_types: [],
  };

  const MODAL_ID = 'dnd-shop-view';

  const SHOP_TYPE_LABELS = {
    general: 'General Store',
    blacksmith: 'Blacksmith',
    alchemist: 'Alchemist',
    magic: 'Magic Shop',
    black_market: 'Black Market',
  };

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }


  function renderItemToken(item, size = 22) {
    if (window.AppItemImages && typeof window.AppItemImages.renderToken === 'function') {
      return window.AppItemImages.renderToken(item || {}, { size, radius: 6, label: item?.item_name || item?.name || 'Item' });
    }
    return `<span style="display:inline-flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;min-width:${size}px;border-radius:6px;background:rgba(255,255,255,0.08);border:1px solid rgba(139,90,20,.25);font-size:${Math.max(12, Math.round(size * 0.62))}px;">🧰</span>`;
  }

  function _renderItemRow(item, opts) {
    if (window.ItemRow && typeof window.ItemRow.renderItemRow === 'function') {
      return window.ItemRow.renderItemRow(item, opts).outerHTML;
    }
    return renderItem(item);
  }

  function fmtGold(units) {
    const total = Math.max(0, Math.round(Number(units) || 0));
    const gp = Math.floor(total / 100);
    const rem = total % 100;
    const sp = Math.floor(rem / 10);
    const cp = rem % 10;
    const parts = [];
    if (gp || (!sp && !cp)) parts.push(`${gp} <span class="sv-coin sv-coin-gp" title="Gold">gp</span>`);
    if (sp) parts.push(`${sp} <span class="sv-coin sv-coin-sp" title="Silver">sp</span>`);
    if (cp) parts.push(`${cp} <span class="sv-coin sv-coin-cp" title="Copper">cp</span>`);
    return parts.join(' ');
  }

  function itemBaseUnits(item) {
    return (parseInt(item.price_gp) || 0) * 100 + (parseInt(item.price_sp) || 0) * 10 + (parseInt(item.price_cp) || 0);
  }

  function getServerPrice(item) {
    const row = (_priceState && _priceState[item.id]) || {};
    const baseUnits = Number.isFinite(Number(row.base_price_units)) ? Number(row.base_price_units) : itemBaseUnits(item);
    const finalUnits = Number.isFinite(Number(row.final_price_units)) ? Number(row.final_price_units) : baseUnits;
    const haggle = (row && typeof row.haggle === 'object' && row.haggle) || {};
    const discountPct = Math.max(0, Math.round(Number(haggle.discount_pct) || 0));
    return {
      baseUnits,
      finalUnits: Math.max(0, finalUnits),
      discountPct,
      haggleActive: !!haggle.active,
      haggleExpiresAt: Number(haggle.expires_at) || null,
    };
  }

  function priceBadge(priceInfo) {
    const totalUnits = priceInfo.baseUnits;
    if (totalUnits === 0) return '<span class="sv-price sv-free">Free</span>';
    if (priceInfo.haggleActive && priceInfo.discountPct > 0 && priceInfo.finalUnits < totalUnits) {
      return `<span class="sv-price sv-discounted"><s>${fmtGold(totalUnits)}</s> ${fmtGold(priceInfo.finalUnits)} <span class="sv-discount-badge">-${priceInfo.discountPct}%</span></span>`;
    }
    return `<span class="sv-price">${fmtGold(totalUnits)}</span>`;
  }

  function renderItem(item) {
    const priceInfo = getServerPrice(item);
    const haggledAlready = !!priceInfo.haggleActive;
    return _renderItemRow(item, {
      mode: 'buy',
      rowClassName: 'sv-item',
      gold: _goldUnits,
      priceCp: priceInfo.finalUnits,
      priceHtml: priceBadge(priceInfo),
      noteHtml: item.description ? `<div class="item-row-note">${esc(item.description)}</div>` : '',
      buy: { onClick: `ShopView._buy('${esc(item.id)}')` },
      haggle: { onClick: `ShopView._haggle('${esc(item.id)}')`, active: haggledAlready },
    });
  }

  function _getProfMap() {
    const map = {};
    (_professionState.catalog || []).forEach(p => {
      if (p && p.id) map[p.id] = p;
    });
    return map;
  }

  function _renderServices() {
    const profMap = _getProfMap();
    const learned = Array.isArray(_professionState.player_profession_ids) ? _professionState.player_profession_ids : [];
    const teachable = Array.isArray(_professionState.teachable_profession_ids) ? _professionState.teachable_profession_ids : [];
    const openSlots = Number(_professionState.open_slots) || 0;

    const learnedHtml = learned.length
      ? learned.map(id => `<span class="sv-prof-chip">${esc((profMap[id] || {}).name || id)}</span>`).join('')
      : '<span class="sv-muted">No professions learned yet.</span>';

    const replaceOptions = learned.map(id => `<option value="${esc(id)}">Replace ${esc((profMap[id] || {}).name || id)}</option>`).join('');
    const teachableHtml = teachable.length
      ? teachable.map(id => {
          const p = profMap[id] || { id, name: id, description: '' };
          const known = learned.includes(id);
          return `
            <div class="sv-service-row">
              <div>
                <div class="sv-item-name">${esc(p.name)}</div>
                <div class="sv-item-desc">${esc(p.description || '')}</div>
              </div>
              <div class="sv-service-actions">
                ${known ? '<span class="sv-badge sv-inf">Known</span>' : `
                  ${openSlots <= 0 ? `<select id="sv-replace-${esc(id)}" class="sv-replace-select">${replaceOptions}</select>` : ''}
                  <button class="sv-buy-btn" onclick="ShopView._learnProfession('${esc(id)}')">${openSlots <= 0 ? 'Replace & Learn' : 'Learn'}</button>
                `}
              </div>
            </div>
          `;
        }).join('')
      : '<div class="sv-empty">This merchant has no training services configured.</div>';

    return `
      <div class="sv-services-summary">
        <div><strong>Learned:</strong> ${learned.length}/${Number(_professionState.max_professions) || 2}</div>
        <div><strong>Open slots:</strong> ${openSlots}</div>
      </div>
      <div class="sv-prof-list">${learnedHtml}</div>
      <div class="sv-service-list">${teachableHtml}</div>
    `;
  }

  function _renderActiveTab() {
    if (!_modalEl) return;
    const body = _modalEl.querySelector('.sv-tab-body');
    if (!body) return;
    if (_activeTab === 'buy') {
      if (_shopData?.shop_sales_enabled === false) {
        body.innerHTML = '<div class="sv-empty">This vendor is not selling items right now.</div>';
        return;
      }
      const inv = Array.isArray(_shopData?.inventory) ? _shopData.inventory : [];
      body.innerHTML = inv.length ? inv.map(renderItem).join('') : '<div class="sv-empty">This shop has nothing for sale.</div>';
      return;
    }
    if (_activeTab === 'services') {
      body.innerHTML = _renderServices();
      return;
    }
    if (_activeTab === 'craft') {
      if (!_campaignEconomy.crafting_enabled) {
        body.innerHTML = '<div class="sv-empty">Crafting is disabled by the DM for this campaign.</div>';
        return;
      }
      if (_shopData && _shopData.crafting_enabled === false) {
        body.innerHTML = '<div class="sv-empty">Crafting is disabled at this station.</div>';
        return;
      }
      body.innerHTML = _renderCraft();
      return;
    }
    if (_activeTab === 'sell') {
      if (!_campaignEconomy.selling_enabled || _shopData?.player_sell_enabled === false || _shopData?.selling_enabled === false) {
        body.innerHTML = '<div class="sv-empty">Selling is disabled by DM or this vendor.</div>';
      } else {
        body.innerHTML = _renderSell();
      }
      return;
    }
    body.innerHTML = '<div class="sv-empty">No services available.</div>';
  }

  function _craftStatusLabel(job) {
    const status = String(job.status_display || job.status || 'crafting').toLowerCase();
    if (status === 'collected') return 'Collected';
    if (status === 'ready') return 'Ready';
    return 'Crafting';
  }

  function _renderCraftRecipe(recipe) {
    const mats = Array.isArray(recipe.requires_materials_view) ? recipe.requires_materials_view : [];
    const canCraft = mats.every(m => Number(m.owned_qty || 0) >= Number(m.required_qty || 0))
      && !!recipe.can_afford_fee;
    const lockReason = String(recipe.locked_reason || '');
    const lockText = lockReason === 'missing_profession' ? 'Missing profession.'
      : lockReason === 'wrong_station' ? 'Wrong crafting station.'
      : lockReason === 'missing_mats' ? 'Missing mats.'
      : '';
    return `
      <div class="sv-item">
        <div class="sv-item-top">
          ${renderItemToken((recipe.result_item_json || {}), 20)}
          <span class="sv-item-name">${esc((recipe.result_item_json || {}).name || recipe.name || 'Recipe')}</span>
          <span class="sv-badge">${esc(String(recipe.rarity || 'common'))}</span>
        </div>
        <div class="sv-item-desc">${esc((recipe.result_item_json || {}).notes || '')}</div>
        <div class="sv-item-desc">Fee: ${fmtGold(recipe.fee_units || 0)} · Time: ${Math.max(0, Math.round((Number(recipe.duration_seconds) || 0) / 60))} min</div>
        <div class="sv-item-desc">
          ${(mats.length ? mats.map(m => `${esc(m.name)} (${m.owned_qty}/${m.required_qty})`).join(' · ') : 'No materials required.')}
        </div>
        ${lockText ? `<div class="sv-item-desc" style="color:#8f4a31;font-weight:600;">${esc(lockText)}</div>` : ''}
        <div class="sv-item-actions">
          <button class="sv-buy-btn${(canCraft && !lockText) ? '' : ' sv-cant-afford'}" onclick="ShopView._startCraft('${esc(recipe.id)}')" ${(canCraft && !lockText) ? '' : 'disabled'}>Start</button>
        </div>
      </div>
    `;
  }

  function _renderCraftJob(job) {
    const status = _craftStatusLabel(job);
    const canCollect = String(status).toLowerCase() === 'ready';
    return `
      <div class="sv-service-row">
        <div>
          <div class="sv-item-name">${esc((job.result_json || {}).name || job.recipe_id || 'Craft Job')}</div>
          <div class="sv-item-desc">Status: ${esc(status)}</div>
        </div>
        <div class="sv-service-actions">
          <button class="sv-buy-btn" onclick="ShopView._collectCraft('${esc(job.job_id)}')" ${canCollect ? '' : 'disabled'}>Collect</button>
        </div>
      </div>
    `;
  }

  function _renderCraft() {
    const recipes = Array.isArray(_craftState.recipes) ? _craftState.recipes : [];
    const jobs = Array.isArray(_craftState.jobs) ? _craftState.jobs : [];
    const recipeHtml = recipes.length ? recipes.map(_renderCraftRecipe).join('') : `<div class="sv-empty">${esc(_craftState.locked_reason || 'No unlocked recipes at this station yet.')}</div>`;
    const jobsHtml = jobs.length ? jobs.map(_renderCraftJob).join('') : '<div class="sv-empty">No active crafting jobs here.</div>';
    return `
      <div class="sv-section-head">Recipes</div>
      ${recipeHtml}
      <div class="sv-section-head">Jobs</div>
      ${jobsHtml}
    `;
  }

  function _renderSellOffer(offer) {
    const accepted = !!offer.accepted;
    const locked = !!offer.resale_locked;
    const haggledAlready = !!(offer.haggle && offer.haggle.active);
    const finalUnits = Number(offer.final_offer_units) || 0;
    const baseUnits = Number(offer.base_offer_units) || 0;
    const item = Object.assign({}, offer.item_data || { name: offer.item_name, item_type: offer.item_type }, { priceCp: finalUnits });

    let priceHtml = null;
    let rejectReason = '';
    if (!accepted) {
      rejectReason = 'Category not accepted';
    } else if (locked) {
      rejectReason = 'Buyback not enabled (recently bought)';
    } else if (haggledAlready && finalUnits > baseUnits) {
      priceHtml = `<span class="item-row-price"><s>${fmtGold(baseUnits)}</s> ${fmtGold(finalUnits)} <span class="sv-discount-badge">+${offer.haggle.bonus_pct}%</span></span>`;
    }

    const canSell = accepted && !locked && finalUnits > 0;
    return _renderItemRow(item, {
      mode: 'sell',
      rowClassName: 'sv-item',
      nameOverride: offer.item_name,
      accepted: accepted && !locked,
      rejectReason,
      priceHtml,
      extraBadgesHtml: `<span class="item-row-badge">×${offer.qty}</span>`,
      sell: canSell ? { onClick: `ShopView._sell('${esc(offer.item_name)}')`, label: '💰 Sell ×1' } : null,
      haggle: canSell ? { onClick: `ShopView._haggleSell('${esc(offer.item_name)}')`, active: haggledAlready } : null,
    });
  }

  function _renderSell() {
    if (_sellLoading) {
      return '<div class="sv-empty">Loading sell offers…</div>';
    }
    if (!_sellMeta.selling_enabled) {
      return '<div class="sv-empty">This shop does not buy items.</div>';
    }
    const rateLabel = `Buy rate: ${_sellMeta.buy_rate_pct}%`;
    const cashLabel = _sellMeta.vendor_cash_units != null
      ? `Merchant cash: ${fmtGold(_sellMeta.vendor_cash_units)}`
      : 'Merchant cash: unlimited';
    if (!_sellOffers.length) {
      return `
        <div class="sv-sell-meta">${esc(rateLabel)} · ${esc(cashLabel)}</div>
        <div class="sv-empty">Your inventory has no items to sell here.</div>
      `;
    }
    return `
      <div class="sv-sell-meta">${esc(rateLabel)} · ${esc(cashLabel)}</div>
      ${_sellOffers.map(_renderSellOffer).join('')}
    `;
  }

  function _renderTreasury() {
    const el = _modalEl && _modalEl.querySelector('#sv-treasury');
    if (el) el.innerHTML = `<span class="sv-treasury-label">Your gold:</span> ${fmtGold(_goldUnits)}`;
  }

  function _setActiveTab(tab) {
    _activeTab = tab;
    _modalEl?.querySelectorAll('.sv-tab').forEach(btn => btn.classList.toggle('is-active', btn.dataset.tab === tab));
    if (tab === 'sell' && _shopData && typeof sendWS === 'function') {
      _sellLoading = true;
      _sellOffers = [];
      sendWS({ type: 'get_sell_offers', payload: { shop_id: _shopData.id } });
    }
    _renderActiveTab();
  }

  function open(shopData, playerGoldUnits, priceState, professionState, craftState, campaignEconomy) {
    close();
    _shopData = shopData || {};
    _goldUnits = Number(playerGoldUnits) || 0;
    _priceState = (priceState && typeof priceState === 'object') ? { ...priceState } : {};
    _professionState = {
      ..._professionState,
      ...(professionState && typeof professionState === 'object' ? professionState : {}),
    };
    _craftState = (craftState && typeof craftState === 'object') ? { ..._craftState, ...craftState } : { recipes: [], jobs: [], now: 0 };
    _campaignEconomy = (campaignEconomy && typeof campaignEconomy === 'object') ? { ..._campaignEconomy, ...campaignEconomy } : _campaignEconomy;
    const shopName = String(_shopData.name || 'Shop');
    const shopkeeper = String(_shopData.shopkeeper_name || 'Shopkeeper');
    const typeLabel = SHOP_TYPE_LABELS[_shopData.shop_type] || 'General Store';
    const dialogueCtx = _dialogueCtx();

    const modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.innerHTML = `
      <div class="sv-backdrop"></div>
      <div class="sv-dialog" role="dialog" aria-modal="true" aria-label="${esc(shopName)}">
        <div class="sv-wood-border">
          <div class="sv-header">
            <div class="sv-header-left">
              <div class="sv-shopkeeper-name">${esc(shopkeeper)}</div>
              <div class="sv-shop-type">${esc(typeLabel)}</div>
            </div>
            <div class="sv-header-right">
              <div id="sv-treasury" class="sv-treasury"></div>
              <button class="sv-close" title="Close" aria-label="Close">✕</button>
            </div>
          </div>
          <div class="sv-title-bar"><h2 class="sv-title">${esc(shopName)}</h2></div>
        </div>
        <div class="sv-tabs" role="tablist" aria-label="Shop sections">
          <button class="sv-tab is-active" data-tab="buy">Buy</button>
          <button class="sv-tab" data-tab="sell">Sell</button>
          <button class="sv-tab" data-tab="craft">Craft</button>
          <button class="sv-tab" data-tab="services">Services</button>
        </div>
        <div class="sv-tab-body"></div>
        <div id="sv-dice-tray" class="sv-dice-tray" style="display:none;"><div id="sv-dice-result"></div><div id="sv-flavor-text" class="sv-flavor-text"></div></div>
        <div class="sv-footer"><span class="sv-footer-note" id="sv-footer-note"></span><button class="sv-done">Come Back Later</button></div>
      </div>`;

    _injectStyles();
    document.body.appendChild(modal);
    _modalEl = modal;
    _renderTreasury();
    _setActiveTab('buy');

    modal.querySelector('.sv-backdrop').addEventListener('click', close);
    modal.querySelector('.sv-close').addEventListener('click', close);
    modal.querySelector('.sv-done').addEventListener('click', close);
    modal.querySelectorAll('.sv-tab').forEach(btn => btn.addEventListener('click', () => _setActiveTab(btn.dataset.tab || 'buy')));
    if (window.ShopkeeperDialogue && typeof window.ShopkeeperDialogue.say === 'function') {
      _greetingSpokenText = window.ShopkeeperDialogue.say('greeting', dialogueCtx);
      if (window.ShopkeeperDialogue.speakGreeting) window.ShopkeeperDialogue.speakGreeting(_greetingSpokenText, dialogueCtx);
      if (window.ShopkeeperDialogue.enrichGreeting) {
        window.ShopkeeperDialogue.enrichGreeting(dialogueCtx).then(text => {
          if (text && window.ShopkeeperDialogue.speakGreeting) window.ShopkeeperDialogue.speakGreeting(text, dialogueCtx);
        });
      }
    }
  }

  function _dialogueCtx() {
    const s = _shopData || {};
    return {
      shop_id: s.id,
      shopkeeper_name: s.shopkeeper_name || 'Shopkeeper',
      personality: s.personality || 'friendly',
      shop_type: s.shop_type || 'general',
      description: s.description || '',
      dialogue_enabled: s.dialogue_enabled !== false,
      voice: s.voice || 'grand_narrator',
      tts_enabled: s.tts_enabled === true,
      greeting_override: s.greeting_override || '',
    };
  }

  function updateInventory(items) {
    if (!_shopData) return;
    _shopData.inventory = items;
    _renderActiveTab();
  }

  function updatePriceState(priceState) {
    if (!priceState || typeof priceState !== 'object') return;
    _priceState = { ..._priceState, ...priceState };
    _renderActiveTab();
  }

  function updateGold(goldUnits) {
    _goldUnits = Number(goldUnits) || 0;
    _renderTreasury();
    _renderActiveTab();
  }

  function updateProfessionState(state) {
    if (!state || typeof state !== 'object') return;
    _professionState = { ..._professionState, ...state };
    if (_activeTab === 'services') _renderActiveTab();
  }

  function updateCraftState(state) {
    if (!state || typeof state !== 'object') return;
    _craftState = { ..._craftState, ...state };
    if (_activeTab === 'craft') _renderActiveTab();
  }

  function handleHaggleResult(result) {
    if (!_modalEl) return;
    const tray = _modalEl.querySelector('#sv-dice-tray');
    const diceEl = _modalEl.querySelector('#sv-dice-result');
    const flavor = _modalEl.querySelector('#sv-flavor-text');
    if (!tray || !diceEl || !flavor) return;
    tray.style.display = 'block';
    if (result.annoyed && result.roll === 0) {
      diceEl.innerHTML = '';
      flavor.textContent = result.flavor_text || 'The shopkeeper scowls at you.';
      return;
    }
    const rollDisplay = result.total !== undefined ? `d20 (${result.roll}) + ${result.modifier >= 0 ? '+' : ''}${result.modifier} = ${result.total}` : '';
    diceEl.innerHTML = `<span class="sv-roll-num${result.success ? ' sv-roll-success' : ' sv-roll-fail'}">${rollDisplay}</span>`;
    flavor.textContent = result.flavor_text || '';
    if (result.price_quote && result.item_id) {
      _priceState[result.item_id] = {
        base_price_units: result.price_quote.base_per_item_units,
        final_price_units: result.price_quote.final_per_item_units,
        haggle: result.price_quote.haggle || {},
      };
    }
    if (window.ShopkeeperDialogue) window.ShopkeeperDialogue.say(result.success ? 'haggle_win' : 'haggle_fail', _dialogueCtx());
    _renderActiveTab();
  }

  function handlePurchaseResult(result) {
    if (!_modalEl) return;
    const noteEl = _modalEl.querySelector('#sv-footer-note');
    if (noteEl) {
      noteEl.textContent = result.message || '';
      noteEl.className = 'sv-footer-note ' + (result.success ? 'sv-note-ok' : 'sv-note-err');
    }
    if (result.success && window.ShopkeeperDialogue) window.ShopkeeperDialogue.say('purchase', _dialogueCtx());
    if (!result.success && window.ShopkeeperDialogue) window.ShopkeeperDialogue.say('cannot_afford', _dialogueCtx());
    if (result.price_state && typeof result.price_state === 'object') _priceState = { ...result.price_state };
    if (result.player_gold_units != null) updateGold(result.player_gold_units);
  }

  function handleProfessionResult(result) {
    if (!_modalEl) return;
    const noteEl = _modalEl.querySelector('#sv-footer-note');
    if (noteEl) {
      noteEl.textContent = result.message || '';
      noteEl.className = 'sv-footer-note ' + (result.success ? 'sv-note-ok' : 'sv-note-err');
    }
    if (result.profession_state) updateProfessionState(result.profession_state);
    if (result.craft_state) updateCraftState(result.craft_state);
  }

  function handleCraftJobResult(result) {
    if (!_modalEl) return;
    const noteEl = _modalEl.querySelector('#sv-footer-note');
    if (noteEl) {
      noteEl.textContent = result.message || '';
      noteEl.className = 'sv-footer-note ' + (result.success ? 'sv-note-ok' : 'sv-note-err');
    }
    if (result.player_gold_units != null) updateGold(result.player_gold_units);
    if (result.craft_state) updateCraftState(result.craft_state);
  }

  function _buy(itemId) {
    if (!_shopData) return;
    const item = (_shopData.inventory || []).find(it => String(it.id) === String(itemId));
    const effUnits = item ? getServerPrice(item).finalUnits : 0;
    if (_goldUnits < effUnits && effUnits > 0) return;
    if (typeof sendWS === 'function') sendWS({ type: 'purchase_item', payload: { shop_id: _shopData.id, item_id: itemId, quantity: 1 } });
  }

  function _haggle(itemId) {
    if (!_shopData) return;
    const currentPrice = (_priceState && _priceState[itemId]) || {};
    if (currentPrice.haggle && currentPrice.haggle.active) return;
    const chaMod = (typeof window !== 'undefined' && window._playerCharismaMod != null) ? Number(window._playerCharismaMod) : 0;
    if (typeof sendWS === 'function') sendWS({ type: 'haggle_item', payload: { shop_id: _shopData.id, item_id: itemId, charisma_modifier: chaMod } });
  }

  function _learnProfession(professionId) {
    if (!_shopData || typeof sendWS !== 'function') return;
    let replaceId = null;
    const slotSel = _modalEl?.querySelector(`#sv-replace-${String(professionId).replace(/[^a-z0-9_-]/gi,'')}`);
    if (slotSel && slotSel.value) replaceId = slotSel.value;
    sendWS({ type: 'learn_profession', payload: { shop_id: _shopData.id, profession_id: professionId, replace_profession_id: replaceId } });
  }

  function _startCraft(recipeId) {
    if (!_shopData || typeof sendWS !== 'function') return;
    sendWS({ type: 'start_craft_job', payload: { shop_id: _shopData.id, recipe_id: recipeId } });
  }

  function _collectCraft(jobId) {
    if (!_shopData || typeof sendWS !== 'function') return;
    sendWS({ type: 'collect_craft_job', payload: { shop_id: _shopData.id, job_id: jobId } });
  }

  function _sell(itemName) {
    if (!_shopData || typeof sendWS !== 'function') return;
    sendWS({ type: 'sell_item', payload: { shop_id: _shopData.id, item_name: itemName, quantity: 1 } });
  }

  function _haggleSell(itemName) {
    if (!_shopData || typeof sendWS !== 'function') return;
    const chaMod = (typeof window !== 'undefined' && window._playerCharismaMod != null) ? Number(window._playerCharismaMod) : 0;
    sendWS({ type: 'haggle_sell_item', payload: { shop_id: _shopData.id, item_name: itemName, charisma_modifier: chaMod } });
  }

  function updateSellOffers(offersPayload) {
    if (!offersPayload || typeof offersPayload !== 'object') return;
    _sellLoading = false;
    _sellMeta = {
      selling_enabled: offersPayload.selling_enabled !== false,
      buy_rate_pct: Number(offersPayload.buy_rate_pct) || 50,
      vendor_cash_units: offersPayload.vendor_cash_units != null ? Number(offersPayload.vendor_cash_units) : null,
      accepted_item_types: Array.isArray(offersPayload.accepted_item_types) ? offersPayload.accepted_item_types : [],
    };
    _sellOffers = Array.isArray(offersPayload.offers) ? offersPayload.offers : [];
    if (_activeTab === 'sell') _renderActiveTab();
  }

  function handleSellResult(result) {
    if (!_modalEl) return;
    const noteEl = _modalEl.querySelector('#sv-footer-note');
    if (noteEl) {
      noteEl.textContent = result.message || '';
      noteEl.className = 'sv-footer-note ' + (result.success ? 'sv-note-ok' : 'sv-note-err');
    }
    if (window.ShopkeeperDialogue) window.ShopkeeperDialogue.say(result.success ? 'sell_accepted' : 'sell_rejected', _dialogueCtx());
    if (result.player_gold_units != null) updateGold(result.player_gold_units);
    if (result.success && _shopData && typeof sendWS === 'function') {
      // Refresh sell offers after a successful sale
      _sellLoading = true;
      sendWS({ type: 'get_sell_offers', payload: { shop_id: _shopData.id } });
    }
  }

  function handleSellHaggleResult(result) {
    if (!_modalEl) return;
    const tray = _modalEl.querySelector('#sv-dice-tray');
    const diceEl = _modalEl.querySelector('#sv-dice-result');
    const flavor = _modalEl.querySelector('#sv-flavor-text');
    if (!tray || !diceEl || !flavor) return;
    tray.style.display = 'block';
    if (result.annoyed && result.roll === 0) {
      diceEl.innerHTML = '';
      flavor.textContent = result.flavor_text || '';
      return;
    }
    const rollDisplay = result.total !== undefined
      ? `d20 (${result.roll}) + ${result.modifier >= 0 ? '+' : ''}${result.modifier} = ${result.total}`
      : '';
    diceEl.innerHTML = `<span class="sv-roll-num${result.success ? ' sv-roll-success' : ' sv-roll-fail'}">${rollDisplay}</span>`;
    flavor.textContent = result.flavor_text || '';
    // Update sell offers to reflect haggle bonus
    if (result.item_name && typeof result.final_offer_units === 'number') {
      const offer = _sellOffers.find(o => o.item_name === result.item_name);
      if (offer) {
        offer.final_offer_units = result.final_offer_units;
        offer.base_offer_units = result.base_offer_units;
        offer.haggle = {
          active: result.success && result.bonus_pct > 0,
          bonus_pct: result.bonus_pct || 0,
          expires_at: result.haggle_expires_at || null,
        };
      }
    }
    if (window.ShopkeeperDialogue) window.ShopkeeperDialogue.say(result.success ? 'haggle_win' : 'haggle_fail', _dialogueCtx());
    if (_activeTab === 'sell') _renderActiveTab();
  }

  function close() {
    if (_modalEl && _shopData && window.ShopkeeperDialogue) window.ShopkeeperDialogue.say('farewell', _dialogueCtx());
    if (_modalEl) _modalEl.remove();
    _modalEl = null;
    _shopData = null;
    _priceState = {};
    _sellOffers = [];
    _sellLoading = false;
    _sellMeta = { selling_enabled: true, buy_rate_pct: 50, vendor_cash_units: null, accepted_item_types: [] };
  }

  let _stylesInjected = false;
  function _injectStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    const style = document.createElement('style');
    style.textContent = `
      #${MODAL_ID}{position:fixed;inset:0;z-index:9800;display:flex;align-items:center;justify-content:center}
      #${MODAL_ID} .sv-backdrop{position:absolute;inset:0;background:rgba(0,0,0,.68);backdrop-filter:blur(3px)}
      #${MODAL_ID} .sv-dialog{position:relative;z-index:1;background:linear-gradient(175deg,#f5e8c8 0%,#e8d5a3 60%,#d4b87a 100%);border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.8);width:560px;max-width:94vw;max-height:88vh;display:flex;flex-direction:column;overflow:hidden}
      #${MODAL_ID} .sv-wood-border{background:linear-gradient(180deg,#5c3317 0%,#7a4822 50%,#5c3317 100%);padding:.6rem 1rem;border-bottom:3px solid #3d200a}
      #${MODAL_ID} .sv-header{display:flex;justify-content:space-between;gap:.5rem}
      #${MODAL_ID} .sv-shopkeeper-name{font-size:18px;font-weight:800;color:#f5e8c8}
      #${MODAL_ID} .sv-shop-type{font-size:12px;color:#d4c090;text-transform:uppercase}
      #${MODAL_ID} .sv-treasury{font-size:12px;color:#f5e8c8;background:rgba(0,0,0,.3);border:1px solid rgba(245,200,90,.4);border-radius:6px;padding:.25rem .55rem}
      #${MODAL_ID} .sv-close{min-height:40px;min-width:40px;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.15);color:#f5e8c8;border-radius:8px}
      #${MODAL_ID} .sv-title{margin:0;font-size:15px;color:#f5e8c8}
      #${MODAL_ID} .sv-tabs{position:sticky;top:0;z-index:3;display:grid;grid-template-columns:repeat(4,1fr);gap:.35rem;padding:.5rem .7rem;background:rgba(122,72,34,.18)}
      #${MODAL_ID} .sv-tab{min-height:44px;border-radius:10px;border:1px solid rgba(90,50,18,.25);background:rgba(255,255,255,.45);font-weight:700}
      #${MODAL_ID} .sv-tab.is-active{background:#8b4513;color:#fff}
      #${MODAL_ID} .sv-tab-body{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:.7rem .9rem;display:flex;flex-direction:column;gap:.55rem}
      #${MODAL_ID} .sv-item{background:rgba(255,255,255,.45);border:1px solid rgba(139,90,20,.25);border-radius:10px;padding:.6rem .8rem}
      #${MODAL_ID} .sv-item-top{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
      #${MODAL_ID} .sv-item-name{font-weight:700;font-size:14px;flex:1;color:#3f2511;text-shadow:0 1px 0 rgba(255,255,255,.2)}
      #${MODAL_ID} .sv-price{font-weight:700;color:#3f2511}
      #${MODAL_ID} .sv-price s{opacity:.72}
      #${MODAL_ID} .sv-coin{font-weight:800;color:#4d2d12}
      #${MODAL_ID} .sv-item-desc{font-size:12px;color:#6b4c2a;margin-top:.3rem}
      #${MODAL_ID} .sv-item-actions{display:flex;gap:.4rem;margin-top:.4rem;flex-wrap:wrap}
      #${MODAL_ID} .sv-buy-btn,#${MODAL_ID} .sv-haggle-btn{min-height:44px;padding:.4rem .95rem;border-radius:8px;font-size:13px;font-weight:600;border:none}
      #${MODAL_ID} .sv-buy-btn{background:#8b4513;color:#fff}
      #${MODAL_ID} .sv-haggle-btn{background:rgba(100,60,20,.12);color:#6b3d0a;border:1px solid rgba(100,60,20,.28)}
      #${MODAL_ID} .sv-empty{padding:1rem .2rem;color:#8b6b3d;font-style:italic}
      #${MODAL_ID} .sv-footer{display:flex;align-items:center;gap:.5rem;padding:.55rem .9rem;background:linear-gradient(180deg,#7a4822 0%,#5c3317 100%)}
      #${MODAL_ID} .sv-done{min-height:44px;padding:.42rem 1.1rem;background:rgba(245,232,200,.12);border:1px solid rgba(245,232,200,.3);border-radius:7px;color:#f5e8c8}
      #${MODAL_ID} .sv-note-ok{color:#a5d6a7} #${MODAL_ID} .sv-note-err{color:#ef9a9a}
      #${MODAL_ID} .sv-badge{font-size:11px;background:rgba(139,90,20,.12);border:1px solid rgba(139,90,20,.25);border-radius:10px;padding:1px 7px}
      #${MODAL_ID} .sv-badge,#${MODAL_ID} .sv-badge span{color:#4a2f18}
      #${MODAL_ID} .sv-badge.sv-inf{background:rgba(30,100,30,.1);color:#2a6f2a}
      #${MODAL_ID} .sv-services-summary{display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap}
      #${MODAL_ID} .sv-prof-list{display:flex;gap:.4rem;flex-wrap:wrap}
      #${MODAL_ID} .sv-prof-chip{display:inline-flex;align-items:center;min-height:36px;padding:.25rem .6rem;border-radius:999px;background:rgba(100,60,20,.12);border:1px solid rgba(100,60,20,.28)}
      #${MODAL_ID} .sv-service-row{display:flex;justify-content:space-between;align-items:center;gap:.6rem;padding:.55rem;border-radius:10px;border:1px solid rgba(139,90,20,.22);background:rgba(255,255,255,.36)}
      #${MODAL_ID} .sv-service-actions{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;justify-content:flex-end}
      #${MODAL_ID} .sv-replace-select{min-height:40px;border-radius:8px;padding:.25rem .45rem}
      #${MODAL_ID} .sv-muted{color:#6b4c2a}
      #${MODAL_ID} .sv-section-head{font-size:12px;font-weight:700;color:#5c3317;text-transform:uppercase;letter-spacing:.06em;margin:.3rem 0}
      @media (max-width: 680px){
        #${MODAL_ID}{align-items:stretch;justify-content:stretch}
        #${MODAL_ID} .sv-dialog{width:100vw;max-width:100vw;max-height:100vh;border-radius:0}
        #${MODAL_ID} .sv-item-name{word-break:break-word}
      }
    `;
    document.head.appendChild(style);
  }

  window.ShopView = Object.freeze({
    open, close, updateInventory, updatePriceState, updateGold, updateProfessionState, updateCraftState,
    handleHaggleResult, handlePurchaseResult, handleProfessionResult, handleCraftJobResult,
    updateSellOffers, handleSellResult, handleSellHaggleResult,
    _buy, _haggle, _learnProfession, _startCraft, _collectCraft, _sell, _haggleSell,
  });
})();
