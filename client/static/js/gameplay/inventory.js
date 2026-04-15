
(function(){
  // Extradimensional container name fragments mirroring server/encumbrance.py
  var _EXTRADIM_NAMES = ['bag of holding', 'handy haversack', 'portable hole', 'bag of devouring'];
  var _EXTRADIM_DEFAULTS = {
    'bag of holding':   { own_weight_lbs: 15, capacity_lbs: 500,  volume_ft3: 64,  is_devouring: false },
    'handy haversack':  { own_weight_lbs: 5,  capacity_lbs: 120,  volume_ft3: null, is_devouring: false },
    'portable hole':    { own_weight_lbs: 0,  capacity_lbs: 1000, volume_ft3: 282, is_devouring: false },
    'bag of devouring': { own_weight_lbs: 5,  capacity_lbs: 0,    volume_ft3: null, is_devouring: true  },
  };
  function _autoTagExtradimensional(item) {
    if (item.extradimensional) return item;
    var lower = String(item.name || '').toLowerCase();
    for (var i = 0; i < _EXTRADIM_NAMES.length; i++) {
      var key = _EXTRADIM_NAMES[i];
      if (lower.indexOf(key) !== -1) {
        var defs = _EXTRADIM_DEFAULTS[key];
        var tagged = Object.assign({}, item, { extradimensional: true });
        if (tagged.own_weight_lbs == null) tagged.own_weight_lbs = defs.own_weight_lbs;
        if (tagged.capacity_lbs   == null) tagged.capacity_lbs   = defs.capacity_lbs;
        if (tagged.volume_ft3     == null) tagged.volume_ft3     = defs.volume_ft3;
        if (tagged.is_devouring   == null) tagged.is_devouring   = defs.is_devouring;
        if (!tagged.bag_contents)          tagged.bag_contents   = [];
        return tagged;
      }
    }
    return item;
  }

  function dedupeImportedInventoryEntries(_env, entries = []) {
    const seen = new Set();
    const out = [];
    for (const raw of entries) {
      if (!raw || typeof raw !== 'object') continue;
      const name = String(raw.name || '').trim().toLowerCase();
      const source = String(raw.source || '').trim().toLowerCase();
      const notes = String(raw.notes || '').trim().toLowerCase();
      const key = [name, source, notes].join('|');
      if (!key || seen.has(key)) continue;
      seen.add(key); out.push(raw);
    }
    return out;
  }
  function buildInventoryEntryFromLibrary(_env, entry, opts={}) {
    const qty = Math.max(1, parseInt(opts.qty ?? entry?.qty ?? 1, 10) || 1);
    return {
      id: String(opts.id || entry?.id || Math.random().toString(36).slice(2)),
      name: String(opts.name || entry?.name || 'Item').trim() || 'Item',
      qty,
      price: String(opts.price ?? entry?.price ?? '').trim(),
      source: String(opts.source || entry?.source || 'Library').trim(),
      notes: String(opts.notes || entry?.notes || '').trim(),
      icon: String(opts.icon || entry?.icon || '').trim(),
      category: String(opts.category || entry?.category || '').trim(),
    };
  }
  function normalizePlayerInventoryEntry(_env, raw) {
    const item = raw && typeof raw === 'object' ? raw : {};
    const out = {
      id: String(item.id || Math.random().toString(36).slice(2)),
      name: String(item.name || 'Item').trim() || 'Item',
      qty: Math.max(1, parseInt(item.qty ?? 1, 10) || 1),
      price: String(item.price || '').trim(),
      source: String(item.source || '').trim(),
      notes: String(item.notes || '').trim(),
      icon: String(item.icon || '').trim(),
      category: String(item.category || '').trim(),
    };
    if (item.weight_lbs != null) out.weight_lbs = Math.max(0, Number(item.weight_lbs) || 0);
    if (item.extradimensional) {
      out.extradimensional = true;
      if (item.own_weight_lbs != null) out.own_weight_lbs = Number(item.own_weight_lbs) || 0;
      if (item.capacity_lbs   != null) out.capacity_lbs   = Number(item.capacity_lbs)   || 0;
      if (item.volume_ft3     != null) out.volume_ft3     = Number(item.volume_ft3)      || 0;
      if (item.is_devouring   != null) out.is_devouring   = !!item.is_devouring;
      out.bag_contents = Array.isArray(item.bag_contents)
        ? item.bag_contents.map(i => normalizePlayerInventoryEntry(_env, i)).filter(Boolean)
        : [];
    }
    return _autoTagExtradimensional(out);
  }
  function normalizePlayerInventoryBucket(env, raw) {
    const bucket = raw && typeof raw === 'object' ? raw : {};
    const ownerId = String(bucket.owner_id || bucket.user_id || '');
    const user = env.users?.[ownerId] || null;
    return {
      owner_id: ownerId,
      owner_name: String(bucket.owner_name || user?.name || 'Player'),
      gold: Math.max(0, Number(bucket.gold || 0) || 0),
      items: Array.isArray(bucket.items) ? bucket.items.map(it => normalizePlayerInventoryEntry(env, it)) : [],
    };
  }
  function applyPlayerInventoryState(env, payload) {
    const buckets = Array.isArray(payload)
      ? payload.map((value) => normalizePlayerInventoryBucket(env, value))
      : Object.entries(payload || {}).map(([key, value]) => normalizePlayerInventoryBucket(env, { ...(value || {}), user_id: value?.user_id || key, owner_id: value?.owner_id || key }));
    env.setPlayerInventories(buckets);
  }
  function applySelfInventoryState(env, payload) {
    env.setPlayerInventory(Array.isArray(payload) ? payload.map((it) => normalizePlayerInventoryEntry(env, it)) : []);
  }
  function applySelfGoldState(env, value) {
    env.setPlayerGold(Math.max(0, Number(value || 0) || 0));
  }
  function applyPartyLootLogState(env, payload) {
    env.setPartyLootLog(Array.isArray(payload) ? payload.slice() : []);
  }
  function getOnlinePlayerInventoryBuckets(env) {
    return (env.getPlayerInventories() || []).filter(bucket => bucket && bucket.owner_id && env.users?.[bucket.owner_id]?.connected);
  }
  function ensureDmInventoryViewerControl(env) {
    return !!(env.ROLE === 'dm' && env.USER_ID);
  }
  function buildCarryCapacitySummary(encumbrance) {
    const enc = encumbrance && typeof encumbrance === 'object' ? encumbrance : {};
    const current = Math.max(0, Number(enc.total_weight || 0) || 0);
    const capacity = Math.max(1, Number(enc.capacity || 0) || 1);
    const strength = Math.max(1, parseInt(enc.strength, 10) || 10);
    const pct = Math.max(0, Math.min(1, current / capacity));
    const barColor = pct >= 1 ? '#e74c3c' : (pct >= 0.66 ? '#f39c12' : '#2ecc71');
    const baseCapacity = Math.floor((15 * strength) * 1.25) + 10;
    return {
      label: `${current.toFixed(1)} / ${capacity.toFixed(0)} lbs`,
      fillPercent: Number((pct * 100).toFixed(1)),
      barColor,
      tooltip: `Based on STR ${strength} (floor((15 × ${strength}) × 1.25) + 10 = ${baseCapacity.toFixed(0)} lbs)`,
    };
  }

  window.AppGameplayInventory = {
    dedupeImportedInventoryEntries,
    buildInventoryEntryFromLibrary,
    normalizePlayerInventoryEntry,
    normalizePlayerInventoryBucket,
    applyPlayerInventoryState,
    applySelfInventoryState,
    applySelfGoldState,
    applyPartyLootLogState,
    getOnlinePlayerInventoryBuckets,
    ensureDmInventoryViewerControl,
    buildCarryCapacitySummary,
  };
})();
