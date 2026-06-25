/**
 * item_row.js
 * Single reusable item-row renderer for shop, sell, chest, loot, and
 * inventory surfaces — icon + name + "type · value" line + rarity chip,
 * with mode-specific right-side actions.
 *
 * Usage: ItemRow.renderItemRow(item, opts) -> HTMLElement
 */
(function () {
  'use strict';

  // Dark stop of each rarity's own color family — chip text is never plain black.
  const RARITY_STYLES = {
    common:     { bg: 'rgba(157,157,157,0.16)', border: 'rgba(107,114,128,0.45)', text: '#4b5563' },
    uncommon:   { bg: 'rgba(34,197,94,0.16)',   border: 'rgba(22,163,74,0.45)',   text: '#166534' },
    rare:       { bg: 'rgba(59,130,246,0.16)',  border: 'rgba(37,99,235,0.45)',   text: '#1e3a8a' },
    'very rare':{ bg: 'rgba(168,85,247,0.16)',  border: 'rgba(147,51,234,0.45)',  text: '#581c87' },
    legendary:  { bg: 'rgba(245,158,11,0.18)',  border: 'rgba(217,119,6,0.5)',    text: '#92400e' },
    artifact:   { bg: 'rgba(230,204,128,0.2)',  border: 'rgba(168,138,46,0.5)',   text: '#7c5e1e' },
  };

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _normRarity(raw) {
    return String(raw || 'common').trim().toLowerCase().replace(/_/g, ' ');
  }

  function _titleCase(raw) {
    return String(raw || '')
      .trim()
      .replace(/_/g, ' ')
      .split(/\s+/)
      .filter(Boolean)
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  function _typeLabel(item) {
    const raw = (item && (item.item_type || item.category || item.equipment_kind || item.kind)) || '';
    return _titleCase(raw) || 'Item';
  }

  function _priceCp(item, opts) {
    if (Number.isFinite(Number(opts && opts.priceCp))) return Math.max(0, Number(opts.priceCp));
    if (!item) return null;
    if (Number.isFinite(Number(item.priceCp))) return Math.max(0, Number(item.priceCp));
    const hasGsc = item.price_gp != null || item.price_sp != null || item.price_cp != null;
    if (hasGsc) {
      return (parseInt(item.price_gp) || 0) * 100 + (parseInt(item.price_sp) || 0) * 10 + (parseInt(item.price_cp) || 0);
    }
    if (Number.isFinite(Number(item.final_offer_units))) return Math.max(0, Number(item.final_offer_units));
    if (Number.isFinite(Number(item.base_price_units))) return Math.max(0, Number(item.base_price_units));
    return null;
  }

  function fmtGoldShort(units) {
    const total = Math.max(0, Math.round(Number(units) || 0));
    const gp = Math.floor(total / 100);
    const rem = total % 100;
    const sp = Math.floor(rem / 10);
    const cp = rem % 10;
    const parts = [];
    if (gp || (!sp && !cp)) parts.push(`${gp} gp`);
    if (sp) parts.push(`${sp} sp`);
    if (cp) parts.push(`${cp} cp`);
    return parts.join(' ');
  }

  function _valueLabel(item, opts) {
    if (opts && typeof opts.valueLabel === 'string') return opts.valueLabel;
    const cp = _priceCp(item, opts);
    if (cp == null) return '';
    return cp === 0 ? 'Free' : fmtGoldShort(cp);
  }

  function _rarityChipHtml(item) {
    const rarity = _normRarity(item && item.rarity);
    const style = RARITY_STYLES[rarity] || RARITY_STYLES.common;
    const label = _titleCase(rarity);
    return `<span class="item-row-rarity" style="background:${style.bg};border:1px solid ${style.border};color:${style.text};">${esc(label)}</span>`;
  }

  function _btn(action, fallbackClass) {
    if (!action) return '';
    const id = action.id ? ` id="${esc(action.id)}"` : '';
    const cls = esc(action.className || fallbackClass);
    const disabled = action.disabled ? ' disabled' : '';
    const onclick = action.onClick ? ` onclick="${action.onClick}"` : '';
    const extraAttrs = (action.attrs && typeof action.attrs === 'object')
      ? Object.keys(action.attrs).map(k => ` ${esc(k)}="${esc(action.attrs[k])}"`).join('')
      : '';
    return `<button type="button" class="${cls}"${id}${disabled}${onclick}${extraAttrs}>${action.label || ''}</button>`;
  }

  function _buyActionsHtml(item, opts) {
    const gold = Number(opts.gold) || 0;
    const priceCp = _priceCp(item, opts);
    const qty = item && item.quantity;
    const isOos = opts.stockState === 'oos' || (qty !== null && qty !== undefined && Number(qty) <= 0);
    const isInfinite = opts.stockState === 'inf' || (!isOos && (qty === null || qty === undefined));
    const stockLabel = opts.stockLabel || (
      isOos ? 'Out of stock' : isInfinite ? '∞ In stock' : `×${qty}`
    );
    const stockBadge = `<span class="item-row-badge${isOos ? ' item-row-badge-oos' : ''}">${esc(stockLabel)}</span>`;

    const canAfford = priceCp == null || priceCp === 0 || gold >= priceCp;
    const priceHtml = opts.priceHtml || `<span class="item-row-price">${esc(_valueLabel(item, opts))}</span>`;
    const needMore = (!canAfford && priceCp != null) ? Math.ceil((priceCp - gold) / 100) : 0;
    const needNote = needMore > 0 ? `<div class="item-row-need-note">Need ${needMore} more gp</div>` : '';

    const buyAction = Object.assign({ label: '🪙 Buy' }, opts.buy || {});
    buyAction.disabled = !!buyAction.disabled || isOos || !canAfford;
    const buyBtn = isOos ? '' : _btn(buyAction, 'item-row-buy-btn');

    const haggleAction = opts.haggle ? Object.assign({ label: opts.haggle.active ? '✅ Haggled' : '🗣 Haggle' }, opts.haggle) : null;
    const haggleBtn = (!isOos && haggleAction) ? _btn(haggleAction, 'item-row-haggle-btn') : '';

    return {
      dimmed: !isOos && !canAfford,
      html: `${priceHtml}${stockBadge}<div class="item-row-actions-buttons">${buyBtn}${haggleBtn}</div>${needNote}`,
    };
  }

  function _sellActionsHtml(item, opts) {
    const accepted = !!opts.accepted;
    let statusHtml;
    if (!accepted) {
      statusHtml = `<span class="item-row-badge item-row-badge-rejected" title="${esc(opts.rejectReason || 'Category not accepted')}">Not accepted${opts.rejectReason ? ' — ' + esc(opts.rejectReason) : ''}</span>`;
    } else if (opts.priceHtml) {
      statusHtml = opts.priceHtml;
    } else {
      statusHtml = `<span class="item-row-price">${esc(_valueLabel(item, opts))}</span>`;
    }
    const sellAction = opts.sell ? Object.assign({ label: '💰 Sell' }, opts.sell) : null;
    const sellBtn = (accepted && sellAction) ? _btn(sellAction, 'item-row-buy-btn') : '';
    const haggleAction = opts.haggle ? Object.assign({ label: opts.haggle.active ? '✅ Haggled' : '🗣 Haggle' }, opts.haggle) : null;
    const haggleBtn = (accepted && haggleAction) ? _btn(haggleAction, 'item-row-haggle-btn') : '';
    return {
      dimmed: !accepted,
      html: `${statusHtml}<div class="item-row-actions-buttons">${sellBtn}${haggleBtn}</div>`,
    };
  }

  function _chestActionsHtml(item, opts) {
    const qty = Math.max(1, Number(opts.qty != null ? opts.qty : item.qty) || 1);
    const qtyBadge = `<span class="item-row-badge">×${qty}</span>`;
    const takeOneAction = Object.assign({ label: '🎒 Take 1' }, opts.takeOne || {});
    const takeOneBtn = _btn(takeOneAction, 'item-row-take-btn');
    const takeAllBtn = (qty > 1 && opts.takeAll)
      ? _btn(Object.assign({ label: `Take All (${qty})` }, opts.takeAll), 'item-row-take-btn item-row-take-all')
      : '';
    return {
      dimmed: false,
      html: `${qtyBadge}<div class="item-row-actions-buttons">${takeOneBtn}${takeAllBtn}</div>`,
    };
  }

  function _lootActionsHtml(item, opts) {
    const locked = !!opts.locked;
    const toggle = opts.lockToggle || {};
    const label = locked ? (toggle.lockedLabel || '🔒 Locked') : (toggle.unlockedLabel || '🔓 Unlocked');
    const toggleBtn = _btn(Object.assign({}, toggle, { label }), 'item-row-lock-toggle');
    return {
      dimmed: false,
      html: `<div class="item-row-actions-buttons">${toggleBtn}</div>`,
    };
  }

  function _inventoryActionsHtml(item, opts) {
    const equipped = !!opts.equipped;
    const qty = Number(item.qty || item.quantity) || 1;
    const qtyBadge = `<span class="item-row-badge">×${qty}</span>`;
    const equipAction = Object.assign({ label: equipped ? 'Unequip' : 'Equip' }, opts.equip || {});
    const equipBtn = _btn(equipAction, 'item-row-equip-btn' + (equipped ? ' equipped' : ''));
    const equippedBadge = equipped ? '<span class="item-row-badge item-row-badge-equipped">Equipped</span>' : '';
    return {
      dimmed: false,
      html: `${qtyBadge}${equippedBadge}<div class="item-row-actions-buttons">${equipBtn}</div>`,
    };
  }

  function _buildActions(item, opts, mode) {
    if (mode === 'buy') return _buyActionsHtml(item, opts);
    if (mode === 'sell') return _sellActionsHtml(item, opts);
    if (mode === 'chest') return _chestActionsHtml(item, opts);
    if (mode === 'loot') return _lootActionsHtml(item, opts);
    if (mode === 'inventory') return _inventoryActionsHtml(item, opts);
    return { dimmed: false, html: '' };
  }

  function renderItemRow(item, opts) {
    item = item || {};
    opts = opts || {};
    const mode = opts.mode || 'view';

    _injectStyles();

    const row = document.createElement('div');
    row.className = `item-row item-row-${mode}${opts.rowClassName ? ' ' + opts.rowClassName : ''}`;
    if (opts.rowId) row.id = opts.rowId;
    if (opts.dataset && typeof opts.dataset === 'object') {
      Object.keys(opts.dataset).forEach(key => { row.dataset[key] = opts.dataset[key]; });
    }

    const name = opts.nameOverride || item.item_name || item.name || 'Item';
    const typeLabel = _typeLabel(item);
    const valueLabel = _valueLabel(item, opts);
    const secondaryParts = [typeLabel];
    if (valueLabel) secondaryParts.push(valueLabel);
    const secondaryLine = secondaryParts.join(' · ');

    const iconSize = Number(opts.iconSize) > 0 ? Number(opts.iconSize) : 26;
    const iconHtml = (window.AppItemImages && typeof window.AppItemImages.renderToken === 'function')
      ? window.AppItemImages.renderToken(item, { size: iconSize, radius: 7, label: name })
      : `<span class="item-row-icon-fallback">🧰</span>`;

    const { dimmed, html: actionsHtml } = _buildActions(item, opts, mode);
    if (dimmed || opts.dimmed) row.classList.add('item-row-dimmed');

    row.innerHTML = `
      <div class="item-row-icon">${iconHtml}</div>
      <div class="item-row-main">
        <div class="item-row-name-line">
          <span class="item-row-name">${esc(name)}</span>
          ${_rarityChipHtml(item)}
        </div>
        <div class="item-row-secondary">${esc(secondaryLine)}</div>
        ${opts.noteHtml || ''}
        ${opts.extraBadgesHtml || ''}
      </div>
      <div class="item-row-actions">${actionsHtml}</div>
    `;

    return row;
  }

  let _stylesInjected = false;
  function _injectStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    const style = document.createElement('style');
    style.textContent = `
      .item-row{display:flex;align-items:flex-start;gap:.55rem;padding:.5rem;border-radius:8px;}
      .item-row.item-row-dimmed{opacity:.55;}
      .item-row-icon{flex-shrink:0;}
      .item-row-main{flex:1;min-width:0;}
      .item-row-name-line{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;}
      .item-row-name{font-weight:700;font-size:14px;}
      .item-row-secondary{font-size:12px;opacity:.8;margin-top:.15rem;}
      .item-row-rarity{font-size:10px;font-weight:700;border-radius:999px;padding:1px 8px;text-transform:uppercase;letter-spacing:.03em;white-space:nowrap;}
      .item-row-actions{display:flex;flex-direction:column;align-items:flex-end;gap:.3rem;flex-shrink:0;}
      .item-row-actions-buttons{display:flex;gap:.35rem;flex-wrap:wrap;justify-content:flex-end;}
      .item-row-badge{font-size:11px;border-radius:10px;padding:1px 7px;background:rgba(128,128,128,.15);border:1px solid rgba(128,128,128,.3);}
      .item-row-badge-oos{opacity:.7;}
      .item-row-badge-rejected{color:#b91c1c;border-color:rgba(185,28,28,.4);background:rgba(185,28,28,.08);}
      .item-row-badge-equipped{color:#166534;border-color:rgba(22,101,52,.4);background:rgba(22,101,52,.1);}
      .item-row-price{font-weight:700;}
      .item-row-need-note{font-size:11px;color:#b91c1c;}
      .item-row-note{font-size:12px;opacity:.75;margin-top:.3rem;font-style:italic;}
    `;
    document.head.appendChild(style);
  }

  window.ItemRow = {
    renderItemRow,
    fmtGoldShort,
  };
})();
