(function () {
  function setDisplay(el, value) { if (el && el.style) el.style.display = value; return el; }
  function renderPlayerList(env) {
    const document = env.document;
    const users = env.getUsers();
    const partyUl = document.getElementById('player-list');
    const viewerUl = document.getElementById('viewer-list');
    const viewerEmpty = document.getElementById('viewer-empty');
    if (!partyUl || !viewerUl) return;
    partyUl.innerHTML = '';
    viewerUl.innerHTML = '';

    const sorted = Object.values(users || {}).filter((u) => u && u.connected).sort((a, b) => {
      const order = { dm: 0, player: 1, viewer: 2 };
      return (order[a.role] ?? 3) - (order[b.role] ?? 3);
    });

    let viewerCount = 0;
    let partyCount = 0;

    sorted.forEach((u) => {
      const li = document.createElement('li');
      li.className = 'player-item';
      li.innerHTML = `
        <span class="pip ${u.connected ? '' : 'offline'}"></span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${u.name}</span>
        <span class="role-tag ${u.role}">${u.role.toUpperCase()}</span>
      `;
      if (u.role === 'viewer') {
        viewerUl.appendChild(li);
        viewerCount += 1;
      } else {
        partyUl.appendChild(li);
        partyCount += 1;
      }
    });

    if (viewerEmpty) setDisplay(viewerEmpty, viewerCount === 0 ? 'block' : 'none');

    const partyBadge = document.getElementById('rtab-party-badge');
    const viewerBadge = document.getElementById('rtab-viewers-badge');
    if (partyBadge) {
      partyBadge.textContent = partyCount;
      partyBadge.classList.toggle('show', partyCount > 0);
    }
    if (viewerBadge) {
      viewerBadge.textContent = viewerCount;
      viewerBadge.classList.toggle('show', viewerCount > 0);
    }
  }

  function renderViewerPanel(env) {
    const document = env.document;
    const ROLE = env.getRole();
    const users = env.getUsers();
    const escapeHtml = env.getEscapeHtml();
    const viewerPowerDefs = env.getViewerPowerDefs();
    const viewerPowerName = env.getViewerPowerName;
    const viewerPowerDescription = env.getViewerPowerDescription;
    const viewerPowerNeedsMapTarget = env.getViewerPowerNeedsMapTarget;
    const viewerPowerNeedsSourceToken = env.getViewerPowerNeedsSourceToken;
    const viewerPowerActionLabel = env.getViewerPowerActionLabel;
    const viewerPowerCooldownLabel = env.getViewerPowerCooldownLabel;
    const viewerProfileEntries = env.getViewerProfileEntries();
    const currentViewerPendingEntries = env.getCurrentViewerPendingEntries();
    const dmBox = document.getElementById('viewer-power-controls');
    const selfBox = document.getElementById('viewer-power-self');
    if (!dmBox || !selfBox) return;
    setDisplay(dmBox, ROLE === 'dm' ? 'block' : 'none');
    setDisplay(selfBox, ROLE === 'viewer' ? 'block' : 'none');
    const defs = viewerPowerDefs || {};
    const powerOptions = Object.entries(defs).map(([id, def]) => `<option value="${escapeHtml(id)}">${escapeHtml(def.name || id)}${def.custom ? ' · Custom' : ''}</option>`).join('');
    if (ROLE === 'dm') {
      const viewers = Object.values(users || {}).filter((u) => u && u.role === 'viewer' && u.connected);
      if (!viewers.some((v) => v.id === env.getDmSelectedViewerId())) env.setDmSelectedViewerId(viewers[0]?.id || '');
      const selectedId = env.getDmSelectedViewerId();
      const selected = viewers.find((v) => v.id === selectedId) || null;
      const selectedProfile = selected ? (viewerProfileEntries.find((v) => String(v.user_id || '') === String(selected.id)) || { powers: {} }) : null;
      const granted = selectedProfile ? Object.values(selectedProfile.powers || {}).filter((entry) => Number(entry?.charges || 0) > 0) : [];
      const pending = currentViewerPendingEntries.sort((a, b) => (Number(b.created_at || 0) - Number(a.created_at || 0)));
      const conditions = env.getConditions();
      dmBox.innerHTML = `<div class="tab-section-label" style="margin-top:0;">Viewer Powers</div>
      <div style="font-size:0.66rem;color:var(--parchment-dim);margin-bottom:0.55rem;line-height:1.45;">Grant powers to one viewer at a time, add cooldowns, or make your own custom viewer powers.</div>
      <div style="display:flex;gap:0.45rem;flex-wrap:wrap;align-items:end;">
        <label style="flex:1;min-width:150px;font-size:0.62rem;color:var(--parchment-dim);">Viewer<select id="viewer-power-dm-target" onchange="_dmSelectedViewerId=this.value;renderViewerPanel()" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;">${viewers.map((v)=>`<option value="${escapeHtml(v.id)}" ${v.id===selectedId?'selected':''}>${escapeHtml(v.name)}</option>`).join('') || '<option value="">No viewers online</option>'}</select></label>
        <label style="flex:1;min-width:160px;font-size:0.62rem;color:var(--parchment-dim);">Power<select id="viewer-power-dm-power" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;">${powerOptions}</select></label>
        <label style="width:88px;font-size:0.62rem;color:var(--parchment-dim);">Charges<input id="viewer-power-dm-charges" type="number" min="1" max="99" value="1" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
        <label style="width:98px;font-size:0.62rem;color:var(--parchment-dim);">Cooldown<input id="viewer-power-dm-cooldown" type="number" min="0" max="86400" value="0" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
        <label style="display:flex;align-items:center;gap:0.36rem;padding:0.36rem 0.5rem;border-radius:8px;background:rgba(255,255,255,0.04);font-size:0.62rem;color:var(--parchment-dim);"><input id="viewer-power-dm-approval" type="checkbox"/> Require approval</label>
        <button onclick="grantViewerPower()" style="padding:0.46rem 0.7rem;background:rgba(201,162,39,0.14);border:1px solid rgba(201,162,39,0.32);border-radius:8px;color:var(--gold);cursor:pointer;">Grant</button>
      </div>
      <div style="display:flex;gap:0.45rem;flex-wrap:wrap;align-items:end;margin-top:0.55rem;">
        <label style="flex:1;min-width:180px;font-size:0.62rem;color:var(--parchment-dim);">Preset<select id="viewer-power-dm-preset" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;"><option value="support_pack">Support Pack</option><option value="chaos_pack">Chaos Pack</option><option value="boss_pack">Boss Fight Pack</option></select></label>
        <button onclick="grantViewerPowerPreset()" style="padding:0.46rem 0.7rem;background:rgba(93,122,255,0.14);border:1px solid rgba(93,122,255,0.28);border-radius:8px;color:var(--parchment);cursor:pointer;">Grant Preset</button>
      </div>
      <details id="viewer-power-custom-builder" style="margin-top:0.7rem;">
        <summary class="tab-section-label" style="margin-top:0;cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;user-select:none;">Custom Power Builder <span style="font-size:0.6rem;color:var(--parchment-dim);">▼</span></summary>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:0.42rem;align-items:end;margin-top:0.45rem;">
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Id<input id="viewer-power-custom-id" placeholder="chaos_bolt" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Name<input id="viewer-power-custom-name" placeholder="Chaos Bolt" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Kind<select id="viewer-power-custom-kind" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;"><option value="single_damage">Single Damage</option><option value="single_heal">Single Heal</option><option value="area_damage">Area Damage</option><option value="single_status">Single Status</option><option value="area_status">Area Status</option></select></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Dice #<input id="viewer-power-custom-num" type="number" min="1" max="20" value="1" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Dice sides<input id="viewer-power-custom-sides" type="number" min="2" max="100" value="6" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Flat<input id="viewer-power-custom-flat" type="number" min="-99" max="999" value="0" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Area shape<select id="viewer-power-custom-shape" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;"><option value="burst">Burst</option><option value="cone">Cone</option><option value="line">Line</option><option value="aura">Aura</option></select></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Size ft<input id="viewer-power-custom-radius" type="number" min="5" max="120" value="15" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Line width ft<input id="viewer-power-custom-width" type="number" min="5" max="60" value="5" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Save<select id="viewer-power-custom-save" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;"><option value="">None</option><option value="str">STR</option><option value="dex">DEX</option><option value="con">CON</option><option value="int">INT</option><option value="wis">WIS</option><option value="cha">CHA</option></select></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Save DC<input id="viewer-power-custom-save-dc" type="number" min="0" max="30" value="13" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Condition<select id="viewer-power-custom-condition" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;"><option value="">None</option>${conditions.map((c)=>`<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`).join('')}</select></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Duration s<input id="viewer-power-custom-duration" type="number" min="0" max="86400" value="0" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="font-size:0.62rem;color:var(--parchment-dim);">Cooldown s<input id="viewer-power-custom-cooldown" type="number" min="0" max="86400" value="0" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
          <label style="display:flex;align-items:center;gap:0.36rem;padding:0.36rem 0.5rem;border-radius:8px;background:rgba(255,255,255,0.04);font-size:0.62rem;color:var(--parchment-dim);"><input id="viewer-power-custom-save-negates" type="checkbox" checked/> Save negates</label>
          <label style="display:flex;align-items:center;gap:0.36rem;padding:0.36rem 0.5rem;border-radius:8px;background:rgba(255,255,255,0.04);font-size:0.62rem;color:var(--parchment-dim);"><input id="viewer-power-custom-approval" type="checkbox"/> Approval default</label>
        </div>
        <label style="display:block;font-size:0.62rem;color:var(--parchment-dim);margin-top:0.42rem;">Description<input id="viewer-power-custom-desc" placeholder="Describe what this power does" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;box-sizing:border-box;" /></label>
        <div style="margin-top:0.45rem;"><button onclick="createCustomViewerPower()" style="padding:0.42rem 0.66rem;background:rgba(110,231,183,0.12);border:1px solid rgba(110,231,183,0.28);border-radius:8px;color:#b8f5dc;cursor:pointer;">Save Custom Power</button></div>
      </details>
      <div style="margin-top:0.7rem;display:flex;flex-direction:column;gap:0.4rem;">${selected ? (granted.length ? granted.map((entry) => `<div style="display:flex;justify-content:space-between;gap:0.45rem;align-items:center;padding:0.5rem;border-radius:8px;background:rgba(0,0,0,0.2);"><div><div style="font-size:0.72rem;color:var(--parchment);">${escapeHtml(viewerPowerName(entry.power_id))}</div><div style="font-size:0.6rem;color:var(--parchment-dim);">${Number(entry.charges||0)} charge${Number(entry.charges||0)===1?'':'s'} remaining · ${escapeHtml(viewerPowerCooldownLabel(entry))}${entry.requires_approval?' · DM approval':''}</div></div><button onclick="revokeViewerPower('${escapeHtml(selected.id)}','${escapeHtml(entry.power_id)}')" style="padding:0.34rem 0.55rem;background:rgba(231,76,60,0.12);border:1px solid rgba(231,76,60,0.28);border-radius:7px;color:#ffb4ab;cursor:pointer;">Revoke</button></div>`).join('') : '<div style="font-size:0.66rem;color:var(--parchment-dim);">No powers granted yet for this viewer.</div>') : '<div style="font-size:0.66rem;color:var(--parchment-dim);">No viewer selected.</div>'}</div>
      <div class="tab-section-label" style="margin-top:0.9rem;">Pending Approvals</div><div style="display:flex;flex-direction:column;gap:0.42rem;">${pending.length ? pending.map((entry) => `<div style="padding:0.55rem;border-radius:9px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,163,86,0.22);"><div style="display:flex;justify-content:space-between;gap:0.5rem;"><div><div style="font-size:0.72rem;color:var(--parchment);">${escapeHtml(entry.viewer_name || 'Viewer')} · ${escapeHtml(entry.power_name || viewerPowerName(entry.power_id))}</div><div style="font-size:0.6rem;color:var(--parchment-dim);margin-top:0.16rem;">${entry.target && entry.target.mode==='point' ? `Point target on ${escapeHtml(String(entry.target.map_context || 'world'))}` : 'Target token'}</div></div><div style="display:flex;gap:0.34rem;"><button onclick="decideViewerPending('${escapeHtml(entry.id)}', true)" style="padding:0.34rem 0.5rem;background:rgba(110,231,183,0.12);border:1px solid rgba(110,231,183,0.32);border-radius:7px;color:#b8f5dc;cursor:pointer;">Approve</button><button onclick="decideViewerPending('${escapeHtml(entry.id)}', false)" style="padding:0.34rem 0.5rem;background:rgba(231,76,60,0.12);border:1px solid rgba(231,76,60,0.28);border-radius:7px;color:#ffb4ab;cursor:pointer;">Decline</button></div></div></div>`).join('') : '<div style="font-size:0.66rem;color:var(--parchment-dim);">No powers waiting for approval.</div>'}</div>`;
    } else if (ROLE === 'viewer') {
      const profile = env.getCurrentViewerProfile();
      const targetOptions = env.getVisibleTargetTokensForViewerPowers();
      const entries = profile ? Object.values(profile.powers || {}).filter((entry) => Number(entry?.charges || 0) > 0) : [];
      const queuedCount = currentViewerPendingEntries.length;
      const viewerPowerTargeting = env.getViewerPowerTargeting();
      selfBox.innerHTML = `<div class="tab-section-label" style="margin-top:0;">Your Powers</div><div style="font-size:0.66rem;color:var(--parchment-dim);margin-bottom:0.6rem;line-height:1.45;">The DM chooses what you can use. Charges and cooldowns save if you disconnect and return.</div>${viewerPowerTargeting ? `<div style="margin-bottom:0.55rem;padding:0.5rem 0.6rem;border-radius:9px;background:rgba(255,163,86,0.1);border:1px solid rgba(255,163,86,0.24);font-size:0.66rem;color:var(--parchment);display:flex;justify-content:space-between;gap:0.5rem;align-items:center;"><span>Targeting ${escapeHtml(viewerPowerName(viewerPowerTargeting.powerId))}: tap the map${viewerPowerNeedsSourceToken(viewerPowerTargeting.powerId) ? ' from the chosen token' : ''}.</span><button onclick="cancelViewerPowerTargeting(true)" style="padding:0.28rem 0.46rem;background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:7px;color:var(--parchment);cursor:pointer;">Cancel</button></div>` : ''}<label style="display:block;font-size:0.62rem;color:var(--parchment-dim);margin-bottom:0.5rem;">Target / source token<select id="viewer-power-target" style="width:100%;margin-top:0.18rem;background:rgba(0,0,0,0.35);border:1px solid var(--border);border-radius:6px;color:var(--parchment);padding:0.34rem;">${targetOptions.map((t)=>`<option value="${escapeHtml(t.id)}">${escapeHtml(t.name)}</option>`).join('') || '<option value="">No target on this map</option>'}</select></label><div style="font-size:0.62rem;color:var(--gold-dim);margin:-0.15rem 0 0.55rem;">Pending approvals: ${queuedCount}</div><div style="display:flex;flex-direction:column;gap:0.42rem;">${entries.length ? entries.map((entry) => `<div style="padding:0.55rem 0.62rem;background:rgba(255,255,255,0.04);border:1px solid rgba(93,122,255,0.26);border-radius:9px;color:var(--parchment);"><div style="display:flex;justify-content:space-between;gap:0.45rem;"><span style="font-size:0.74rem;font-weight:700;">${escapeHtml(viewerPowerName(entry.power_id))}</span><span style="font-size:0.64rem;color:var(--gold);">${Number(entry.charges||0)} left</span></div><div style="font-size:0.62rem;color:var(--parchment-dim);margin-top:0.15rem;">${escapeHtml(viewerPowerDescription(entry.power_id))}${entry.requires_approval ? ' · Needs DM approval.' : ''}</div><div style="font-size:0.6rem;color:var(--gold-dim);margin-top:0.14rem;">${escapeHtml(viewerPowerCooldownLabel(entry))}</div><div style="display:flex;gap:0.4rem;margin-top:0.48rem;">${viewerPowerNeedsMapTarget(entry.power_id) ? `<button onclick="beginViewerPowerTargeting('${escapeHtml(entry.power_id)}')" style="flex:1;padding:0.4rem 0.55rem;background:rgba(255,163,86,0.12);border:1px solid rgba(255,163,86,0.28);border-radius:8px;color:#ffd3ae;cursor:pointer;">${escapeHtml(viewerPowerActionLabel(entry.power_id))}</button>` : `<button onclick="useViewerPower('${escapeHtml(entry.power_id)}')" style="flex:1;padding:0.4rem 0.55rem;background:rgba(93,122,255,0.12);border:1px solid rgba(93,122,255,0.28);border-radius:8px;color:var(--parchment);cursor:pointer;">${escapeHtml(viewerPowerActionLabel(entry.power_id))}</button>`}</div></div>`).join('') : '<div style="font-size:0.68rem;color:var(--parchment-dim);">You have no powers yet.</div>'}</div>`;
    }
  }

  function buildInventoryActionRow(env, index, qty) {
    const canTransfer = !!env.getInventoryTransferTargetId();
    return `<div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.35rem;">
      <button class="poi-popup-btn" style="margin:0;min-width:82px;" onclick="removeInventoryItem(${index}, 1)">Use 1</button>
      ${qty > 1 ? `<button class="poi-popup-btn" style="margin:0;min-width:92px;" onclick="removeInventoryItem(${index}, ${qty})">Remove All</button>` : ''}
      <button class="poi-popup-btn" style="margin:0;min-width:82px;${canTransfer ? '' : 'opacity:0.55;'}" onclick="transferInventoryItem(${index}, 1)">Give 1</button>
      ${qty > 1 ? `<button class="poi-popup-btn" style="margin:0;min-width:92px;${canTransfer ? '' : 'opacity:0.55;'}" onclick="transferInventoryItem(${index}, ${qty})">Give All</button>` : ''}
    </div>`;
  }

  function renderInventoryPanel(env) {
    const document = env.document;
    const ROLE = env.getRole();
    const escapeHtml = env.getEscapeHtml();
    const list = document.getElementById('inventory-list');
    const empty = document.getElementById('inventory-empty');
    const subtitle = document.getElementById('inventory-subtitle');
    const logWrap = document.getElementById('party-loot-log');
    const logEmpty = document.getElementById('party-loot-empty');
    const badge = document.getElementById('rtab-inventory-badge');
    const tools = document.getElementById('inventory-tools');
    const toolsNote = document.getElementById('inventory-tools-note');
    const itemLibraryBtn = document.getElementById('inventory-item-library-btn');
    if (!list || !empty || !subtitle || !logWrap || !logEmpty) return;

    env.refreshInventoryTransferTargets();
    env.refreshInventoryGoldTargets();
    const dmFocusWrap = env.ensureDmInventoryViewerControl();
    const dmFocusSelect = document.getElementById('dm-inventory-focus');
    if (dmFocusWrap) setDisplay(dmFocusWrap, ROLE === 'dm' ? 'grid' : 'none');
    if (tools) setDisplay(tools, ROLE === 'viewer' ? 'none' : 'flex');
    if (itemLibraryBtn) setDisplay(itemLibraryBtn, ROLE === 'dm' ? 'inline-flex' : 'none');
    if (toolsNote) {
      toolsNote.textContent = ROLE === 'viewer'
        ? ''
        : (ROLE === 'dm'
          ? 'Add manual items to inventories, award gold directly, save reusable item-library entries, and give items to connected players.'
          : 'Add manual items to your own inventory, add gold directly to your purse, pull saved items from the item library, and give items to another connected player.');
    }

    let uniqueCount = 0;
    list.innerHTML = '';
    if (ROLE === 'viewer') {
      subtitle.textContent = 'Viewers cannot access player inventories.';
      setDisplay(empty, 'block');
      empty.textContent = 'Inventory access is available to the DM and players only.';
    } else if (ROLE === 'dm') {
      const allBuckets = env.getOnlinePlayerInventoryBuckets();
      if (dmFocusSelect) {
        dmFocusSelect.innerHTML = allBuckets.map((bucket) => `<option value="${escapeHtml(bucket.user_id)}">${escapeHtml(bucket.name)}</option>`).join('');
        if (!allBuckets.some((bucket) => String(bucket.user_id) === String(env.getDmInventoryFocusUserId()))) {
          env.setDmInventoryFocusUserId(allBuckets[0]?.user_id || '');
        }
        dmFocusSelect.value = env.getDmInventoryFocusUserId();
      }
      subtitle.textContent = allBuckets.length ? 'Select an online player to inspect their inventory.' : 'No players are currently online.';
      const buckets = allBuckets.filter((bucket) => !env.getDmInventoryFocusUserId() || String(bucket.user_id) === String(env.getDmInventoryFocusUserId()));
      uniqueCount = buckets.reduce((sum, bucket) => sum + ((bucket?.items || []).length), 0);
      setDisplay(empty, buckets.length ? 'none' : 'block');
      empty.textContent = allBuckets.length ? 'That player has no saved inventory yet.' : 'No online player inventories yet.';
      buckets.forEach((bucket) => {
        const totalQty = (bucket.items || []).reduce((sum, item) => sum + (parseInt(item.qty, 10) || 0), 0);
        const card = document.createElement('div');
        card.style.cssText = 'display:flex;flex-direction:column;gap:0.45rem;padding:0.72rem;border:1px solid rgba(201,162,39,0.18);border-radius:10px;background:rgba(255,255,255,0.03);';
        card.innerHTML = `<div style="display:flex;justify-content:space-between;gap:0.55rem;align-items:center;">
            <div style="min-width:0;">
              <div style="font-family:'Cinzel',serif;font-size:0.8rem;letter-spacing:0.05em;color:var(--gold);text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(bucket.name)}</div>
              <div style="font-size:0.66rem;color:var(--parchment-dim);">PLAYER · ${(bucket.items || []).length} unique item${(bucket.items || []).length === 1 ? '' : 's'} · ${totalQty} total · ${env.formatGoldUnits(bucket.gold || 0)} on hand</div>
            </div>
          </div>`;
        const body = document.createElement('div');
        body.style.cssText = 'display:flex;flex-direction:column;gap:0.38rem;';
        if (!(bucket.items || []).length) {
          body.innerHTML = '<div style="font-size:0.69rem;color:var(--parchment-dim);">Inventory empty.</div>';
        } else {
          (bucket.items || []).forEach((item) => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;justify-content:space-between;gap:0.5rem;align-items:flex-start;padding:0.48rem 0.55rem;border-radius:8px;background:rgba(10,18,28,0.32);';
            row.innerHTML = `<div style="min-width:0;flex:1;">
                <div style="font-size:0.74rem;color:var(--parchment);font-weight:600;">${escapeHtml(item.name)}</div>
                ${item.notes ? `<div style="font-size:0.64rem;color:var(--parchment-dim);line-height:1.4;">${escapeHtml(item.notes)}</div>` : ''}
                ${(item.price || item.source) ? `<div style="font-size:0.62rem;color:var(--gold-dim);">${escapeHtml([item.price && `Cost ${item.price}`, item.source && `From ${item.source}`].filter(Boolean).join(' · '))}</div>` : ''}
              </div>
              <div style="font-size:0.72rem;color:var(--gold);white-space:nowrap;">×${item.qty}</div>`;
            body.appendChild(row);
          });
        }
        card.appendChild(body);
        list.appendChild(card);
      });
    } else {
      subtitle.textContent = 'Items taken from revealed chests or bought from merchants appear here automatically. Shop purchases spend your gold on hand; chest loot and DM-awarded items do not.';
      const items = Array.isArray(env.getPlayerInventory()) ? env.getPlayerInventory() : [];
      uniqueCount = items.length;
      const goldCard = document.createElement('div');
      goldCard.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:0.6rem;padding:0.72rem;border:1px solid rgba(201,162,39,0.18);border-radius:10px;background:linear-gradient(180deg, rgba(212,175,55,0.08), rgba(255,255,255,0.03));';
      goldCard.innerHTML = `<div><div style="font-family:'Cinzel',serif;font-size:0.78rem;letter-spacing:0.06em;color:var(--gold);text-transform:uppercase;">Gold on Hand</div><div style="font-size:0.64rem;color:var(--parchment-dim);margin-top:0.12rem;">Shop purchases deduct from this automatically. Chests and DM-awarded items do not.</div></div><div style="font-size:0.9rem;color:var(--gold);white-space:nowrap;font-weight:700;">${escapeHtml(env.formatGoldUnits(env.getPlayerGold()))}</div>`;
      list.appendChild(goldCard);
      setDisplay(empty, items.length ? 'none' : 'block');
      empty.textContent = 'You have not taken or bought any items yet. Gold still shows above.';
      items.forEach((item, idx) => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;gap:0.6rem;align-items:flex-start;padding:0.7rem;border:1px solid rgba(201,162,39,0.15);border-radius:10px;background:rgba(255,255,255,0.03);';
        row.innerHTML = `<div style="min-width:0;flex:1;">
            <div style="font-size:0.78rem;color:var(--parchment);font-weight:600;">${escapeHtml(item.name)}</div>
            ${item.notes ? `<div style="font-size:0.66rem;color:var(--parchment-dim);line-height:1.45;margin-top:0.12rem;">${escapeHtml(item.notes)}</div>` : ''}
            ${(item.price || item.source) ? `<div style="font-size:0.63rem;color:var(--gold-dim);margin-top:0.15rem;">${escapeHtml([item.price && `Cost ${item.price}`, item.source && `From ${item.source}`].filter(Boolean).join(' · '))}</div>` : ''}
            ${buildInventoryActionRow(env, idx, item.qty)}
          </div>
          <div style="font-size:0.78rem;color:var(--gold);white-space:nowrap;">×${item.qty}</div>`;
        list.appendChild(row);
      });
    }
    if (badge) {
      badge.textContent = uniqueCount > 99 ? '99+' : String(uniqueCount || '');
      badge.classList.toggle('show', uniqueCount > 0);
    }

    logWrap.innerHTML = '';
    const logs = Array.isArray(env.getPartyLootLog()) ? env.getPartyLootLog().slice(-20).reverse() : [];
    setDisplay(logEmpty, logs.length ? 'none' : 'block');
    logs.forEach((entry) => {
      const qty = Math.max(1, parseInt(entry.qty, 10) || 1);
      const action = String(entry.action || 'take').trim().toLowerCase();
      const playerName = String(entry.player_name || 'Someone').trim() || 'Someone';
      const itemName = String(entry.item_name || 'Item').trim() || 'Item';
      const sourceName = String(entry.source_name || '').trim();
      const targetName = String(entry.target_name || '').trim();
      const price = String(entry.price || '').trim();
      const when = entry.timestamp ? new Date(Number(entry.timestamp) * 1000) : null;
      const timeLabel = when && !Number.isNaN(when.getTime()) ? when.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '';
      const line = document.createElement('div');
      line.style.cssText = 'padding:0.55rem 0.62rem;border-radius:8px;background:rgba(10,18,28,0.28);border:1px solid rgba(115,135,165,0.12);font-size:0.68rem;line-height:1.45;color:var(--parchment);';
      const verbMap = { buy: 'bought', take: 'took', add: 'added', remove: 'removed', give: 'gave' };
      const verb = verbMap[action] || 'moved';
      const qtyText = qty === 1 ? '' : `${qty}× `;
      let tail = '';
      if (action === 'give' && targetName) tail = ` to ${targetName}`;
      else if (sourceName) tail = ` from ${sourceName}`;
      const priceText = price ? ` for ${price}` : '';
      line.innerHTML = `<div><strong style="color:var(--gold);">${escapeHtml(playerName)}</strong> ${verb} ${escapeHtml(qtyText + itemName)}${escapeHtml(priceText + tail)}.</div>${timeLabel ? `<div style="font-size:0.6rem;color:var(--parchment-dim);margin-top:0.16rem;">${escapeHtml(timeLabel)}</div>` : ''}`;
      logWrap.appendChild(line);
    });
  }

  window.AppUIPanels = {
    renderPlayerList,
    renderViewerPanel,
    buildInventoryActionRow,
    renderInventoryPanel,
  };
})();
