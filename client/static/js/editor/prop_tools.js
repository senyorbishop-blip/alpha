(function(){
  const AppEditorProps = {
    defaultEditorPropName(kind){
      const map = {
        crate: 'Crate', table: 'Table', tree: 'Tree', pine: 'Pine Tree', forest_cluster: 'Forest Cluster', rock: 'Rock', hill: 'Hill', mountain: 'Mountain', barrel: 'Barrel', torch: 'Torch', lamp: 'Lamp', stairs: 'Stairs',
        chest: 'Chest', merchant: 'Merchant', store: 'Store Stall', house: 'House', tavern: 'Tavern', blacksmith: 'Blacksmith', castle: 'Castle', inn: 'Inn', temple: 'Temple', watchtower: 'Watchtower', market_stall: 'Market Stall', barracks: 'Barracks', dock: 'Dock', windmill: 'Windmill', manor: 'Manor', townhall: 'Town Hall', guildhall: 'Guild Hall', stable: 'Stable', warehouse: 'Warehouse', gatehouse: 'Gatehouse', bridge: 'Bridge', market_district: 'Market District', temple_district: 'Temple District', farm_block: 'Farm Block', town_generator: 'Town Layout', city_generator: 'City Layout', harbor_generator: 'Harbor Layout', crossing_generator: 'Crossing', town_wall_ring: 'Town Wall Ring', door: 'Door', opening: 'Opening',
      };
      return map[kind] || (kind === 'custom_asset' ? 'Custom Prop' : 'Prop');
    },
    defaultEditorPropSlots(env, kind){ return env.editorPropDefaultSlots[kind] || 0; },
    editorPropIcon(kind){
      return ({ crate: '📦', table: '🪑', tree: '🌳', pine: '🌲', forest_cluster: '🌲', rock: '🪨', hill: '🟫', mountain: '⛰️', barrel: '🛢', torch: '🔥', lamp: '🏮', stairs: '🪜', chest: '🧰', merchant: '🧑‍🌾', store: '🏪', house: '🏠', tavern: '🍺', blacksmith: '⚒️', castle: '🏰', market_district: '🛍️', temple_district: '⛪', farm_block: '🌾', town_generator: '🏘️', city_generator: '🏙️', town_wall_ring: '🛡️', door: '🚪', opening: '⬚', custom_asset: '🖼️' })[kind] || '📍';
    },
    editorPropIsShopKind(kind){ return ['merchant','store','shop','tavern','blacksmith','market_stall','inn'].includes(String(kind || '').toLowerCase()); },
    editorPropUsesHiddenFlag(kind){
      const k = String(kind || '').toLowerCase();
      return k === 'door' || k === 'chest' || this.editorPropIsShopKind(k);
    },
    editorPropSupportsContentsKind(kind){ return kind === 'chest' || this.editorPropIsShopKind(kind); },
    editorPropSupportsContents(item){ return !!(item && this.editorPropSupportsContentsKind(String(item.kind || '').toLowerCase())); },
    normalizeEditorPropInventoryEntry(env, raw, kind){
      if (raw == null) return null;
      const isShop = this.editorPropIsShopKind(kind);
      let name = '';
      let qty = 1;
      let price = '';
      let notes = '';
      let infinite = false;
      if (typeof raw === 'object') {
        name = String(raw.name || '').trim().slice(0, 80);
        qty = Math.max(1, Math.min(999, Math.round(Number(raw.qty) || 1)));
        price = isShop ? String(raw.price || '').trim().slice(0, 32) : '';
        notes = String(raw.notes || raw.note || '').trim().slice(0, 160);
        infinite = isShop ? env.normalizeEditorBool(raw.infinite ?? raw.unlimited) : false;
      } else {
        name = String(raw || '').trim().slice(0, 80);
      }
      if (!name) return null;
      return { name, qty, price, notes, infinite };
    },
    editorPropSignature(item){
      if (!item) return '';
      return `${item.kind}:${item.x}:${item.y}:${item.w}:${item.h}:${item.facing || ''}:${item.rotation || 0}`;
    },
    normalizeEditorPropItem(env, item){
      if (!item || typeof item !== 'object') return null;
      const kind = env.editorPropKinds.has(String(item.kind || '').toLowerCase()) ? String(item.kind).toLowerCase() : 'crate';
      const base = env.editorPropBaseSize[kind] || { w: 1, h: 1 };
      const x = Math.round(Number(item.x) / 50) * 50;
      const y = Math.round(Number(item.y) / 50) * 50;
      const w = Math.max(1, Math.min(6, Math.round(Number(item.w) || base.w)));
      const h = Math.max(1, Math.min(6, Math.round(Number(item.h) || base.h)));
      if (![x, y, w, h].every(Number.isFinite)) return null;
      const hidden = this.editorPropUsesHiddenFlag(kind) ? env.normalizeEditorBool(item.hidden) : false;
      const rotation = ((Math.round(Number(item.rotation) || 0) % 360) + 360) % 360;
      const slotDefault = this.defaultEditorPropSlots(env, kind);
      const slotCount = this.editorPropSupportsContentsKind(kind)
        ? Math.max(1, Math.min(60, Math.round(Number(item.slot_count) || slotDefault || 1)))
        : Math.max(0, Math.min(60, Math.round(Number(item.slot_count) || slotDefault || 0)));
      const inventory = Array.isArray(item.inventory)
        ? item.inventory.slice(0, slotCount || 60).map(entry => this.normalizeEditorPropInventoryEntry(env, entry, kind)).filter(Boolean)
        : [];
      const facing = (kind === 'door' || kind === 'opening')
        ? (String(item.facing || item.orientation || 'h').trim().toLowerCase().startsWith('v') ? 'v' : 'h')
        : undefined;
      const state = (kind === 'door' || kind === 'opening')
        ? (String(item.state || (kind === 'opening' ? 'open' : 'closed')).trim().toLowerCase() === 'open' ? 'open' : 'closed')
        : undefined;
      const locked = kind === 'door' ? !!item.locked : false;
      const blocksMovement = kind === 'door' ? item.blocks_movement !== false : false;
      const blocksVision = kind === 'door' ? item.blocks_vision !== false : false;
      return {
        id: String(item.id || `prop_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`).slice(0, 48),
        kind, x, y, w, h, hidden, rotation, facing, state, locked,
        blocks_movement: blocksMovement,
        blocks_vision: blocksVision,
        name: String(item.name || this.defaultEditorPropName(kind)).trim().slice(0, 60) || this.defaultEditorPropName(kind),
        slot_count: slotCount,
        inventory,
        asset_id: kind === 'custom_asset' ? String(item.asset_id || '') : '',
        asset_file: kind === 'custom_asset' ? String(item.asset_file || '') : '',
        asset_thumbnail: kind === 'custom_asset' ? String(item.asset_thumbnail || item.asset_file || '') : '',
        asset_scale: kind === 'custom_asset' ? Math.max(0.25, Math.min(4, Number(item.asset_scale || 1) || 1)) : 1,
        asset_anchor: kind === 'custom_asset' ? String(item.asset_anchor || 'center') : 'center',
        asset_footprint: kind === 'custom_asset' ? Math.max(0.5, Math.min(4, Number(item.asset_footprint || 1) || 1)) : 1,
      };
    },
    buildEditorPropItem(env, kind, x, y, size){
      const k = env.editorPropKinds.has(kind) ? kind : 'crate';
      if (k === 'market_district' || k === 'temple_district' || k === 'farm_block' || k === 'town_generator' || k === 'city_generator' || k === 'harbor_generator' || k === 'crossing_generator' || k === 'town_wall_ring' || k === 'settlement_cluster') return null;
      const scale = Math.max(1, Math.min(4, Number(size) || 1));
      const base = env.editorPropBaseSize[k] || { w: 1, h: 1 };
      const selectedAsset = k === 'custom_asset' && typeof env.getSelectedEditorPropAsset === 'function' ? (env.getSelectedEditorPropAsset() || null) : null;
      const footprint = k === 'custom_asset' ? Math.max(0.5, Math.min(4, Number(selectedAsset?.footprint || 1) || 1)) : 1;
      return this.normalizeEditorPropItem(env, {
        kind: k, x, y, w: base.w * scale * footprint, h: base.h * scale * footprint,
        hidden: k === 'chest' ? env.editorChestHidden : false,
        rotation: env.editorPropRotation,
        slot_count: this.defaultEditorPropSlots(env, k),
        inventory: [],
        name: selectedAsset?.name || this.defaultEditorPropName(k),
        asset_id: selectedAsset?.id || '',
        asset_file: selectedAsset?.file || '',
        asset_thumbnail: selectedAsset?.thumbnail || selectedAsset?.file || '',
        asset_scale: Number(selectedAsset?.scale || 1) || 1,
        asset_anchor: selectedAsset?.anchor || 'center',
        asset_footprint: Number(selectedAsset?.footprint || 1) || 1,
      });
    },
    dedupeEditorProps(env, items){
      const seen = new Set();
      const out = [];
      (Array.isArray(items) ? items : []).forEach(raw => {
        const item = this.normalizeEditorPropItem(env, raw);
        if (!item) return;
        const sig = item.id || this.editorPropSignature(item);
        if (seen.has(sig)) return;
        seen.add(sig);
        out.push(item);
      });
      return out;
    },
    isDoorLikeEditorPropKind(kind){ return kind === 'door' || kind === 'opening'; },
    getEditorPropHitBounds(item){
      if (!item) return null;
      if (this.isDoorLikeEditorPropKind(item.kind)) {
        return { left: item.x, top: item.y, width: Math.max(1, Number(item.w || 1)) * 50, height: Math.max(1, Number(item.h || 1)) * 50 };
      }
      return { left: item.x, top: item.y, width: item.w * 50, height: item.h * 50 };
    },
    canUserInteractWithEditorProp(env, item){
      if (!item) return false;
      if (env.role === 'dm' && !env.previewEnabled()) return true;
      const kind = String(item.kind || '').toLowerCase();
      const hiddenProp = env.normalizeEditorBool(item.hidden);
      const x = Number(item.x || 0);
      const y = Number(item.y || 0);
      const w = Math.max(1, Number(item.w || 1)) * 50;
      const h = Math.max(1, Number(item.h || 1)) * 50;
      if (hiddenProp) return false;
      if (kind === 'chest') return env.isRectVisibleWithinRange(x, y, w, h, (60 / 5) * 50, 6);
      return env.isRectVisible(x, y, w, h, 6);
    },
    canUserSeeEditorProp(env, item){
      if (!item) return false;
      if (env.role === 'dm' && !env.previewEnabled()) return true;
      const hiddenProp = env.normalizeEditorBool(item.hidden);
      if (env.role !== 'dm' && hiddenProp) return false;
      const x = Number(item.x || 0);
      const y = Number(item.y || 0);
      const w = Math.max(1, Number(item.w || 1)) * 50;
      const h = Math.max(1, Number(item.h || 1)) * 50;
      if (this.editorPropUsesHiddenFlag(item.kind) && String(item.kind || '').toLowerCase() === 'chest') {
        return env.isRectVisibleWithinRange(x, y, w, h, (60 / 5) * 50, 6);
      }
      return env.isRectVisible(x, y, w, h, 6);
    },
    findEditorPropIndexAt(env, wx, wy, options){
      env.ensureEditorPropsLoaded();
      const visibleOnly = !!(options && options.visibleOnly);
      for (let i = (env.editorPropItems() || []).length - 1; i >= 0; i--) {
        const item = env.editorPropItems()[i];
        if (visibleOnly && !this.canUserSeeEditorProp(env, item)) continue;
        const bounds = this.getEditorPropHitBounds(item);
        if (!bounds) continue;
        if (wx >= bounds.left && wx <= bounds.left + bounds.width && wy >= bounds.top && wy <= bounds.top + bounds.height) return i;
      }
      return -1;
    },
    findInteractiveEditorProp(env, wx, wy){
      env.ensureEditorPropsLoaded();
      for (let i = (env.editorPropItems() || []).length - 1; i >= 0; i--) {
        const item = env.editorPropItems()[i];
        if (!this.canUserInteractWithEditorProp(env, item)) continue;
        const bounds = this.getEditorPropHitBounds(item);
        if (!bounds) continue;
        if (wx >= bounds.left && wx <= bounds.left + bounds.width && wy >= bounds.top && wy <= bounds.top + bounds.height) return item;
      }
      return null;
    },
    updateEditorPropHover(env, wx, wy){
      const next = (env.isEditorOpen() && env.editorActiveLayer === 'props') ? this.findEditorPropIndexAt(env, wx, wy) : -1;
      if (next !== env.editorPropHoverIndex()) {
        env.setEditorPropHoverIndex(next);
        env.drawFrame();
      }
    },
  };
  window.AppEditorProps = AppEditorProps;
})();
