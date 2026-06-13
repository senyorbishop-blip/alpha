(function () {
  function getSavedDiscoveries(env) {
    return Array.isArray(env?.getSavedDiscoveries?.()) ? env.getSavedDiscoveries() : [];
  }

  function getPrivateStoryHooks(env) {
    return Array.isArray(env?.getPrivateStoryHooks?.()) ? env.getPrivateStoryHooks() : [];
  }

  function getDiscoveryPayload(msg) {
    const payload = msg && msg.payload && typeof msg.payload === 'object' ? msg.payload : {};
    return payload.discovery && typeof payload.discovery === 'object' ? payload.discovery : payload;
  }

  function normalizeMomentType(type) {
    const raw = String(type || '').toLowerCase();
    if (!raw) return 'world';
    if (raw.includes('discovery')) return 'discovery';
    if (raw.includes('handout')) return 'handout';
    if (raw.includes('guild') || raw.includes('faction') || raw.includes('rank') || raw.includes('reputation')) return 'standing';
    if (raw.includes('quest')) return 'quest';
    if (raw.includes('reward') || raw.includes('loot')) return 'reward';
    if (raw.includes('interactable') || raw.includes('prop_action')) return 'world';
    return 'world';
  }

  function isoStamp(ts) {
    const n = Number(ts || Date.now());
    return Number.isFinite(n) ? new Date(n).toISOString() : new Date().toISOString();
  }

  function buildMomentEvent(type, payload = {}, msg = {}) {
    const eventType = String(type || '');
    const meta = msg && typeof msg === 'object' ? (msg.meta || {}) : {};
    const titleFromPayload = String(payload.title || payload.quest_title || payload.event_title || payload.label || '').trim();
    const summaryFromPayload = String(payload.summary || payload.message || payload.body || payload.public_text || '').trim();
    const event = {
      type: eventType,
      momentType: normalizeMomentType(eventType),
      title: titleFromPayload || 'World update',
      summary: summaryFromPayload || 'Something changed in the world.',
      stamp: isoStamp(payload.ts || payload.timestamp || Date.now()),
      relatedId: String(payload.quest_id || payload.handout_id || payload.discovery_id || payload.faction_id || payload.guild_rank_id || payload.id || ''),
      dedupeKey: String(payload.id || payload.event_id || `${eventType}:${titleFromPayload}:${summaryFromPayload}`).toLowerCase(),
      scope: String(meta.scope || ''),
      audience: String(meta.audience || ''),
    };
    return event;
  }

  function recordScopedEvent(env, msg) {
    if (!env || typeof env.setPlayerScopedEvent !== 'function') return;
    const meta = msg && typeof msg === 'object' ? (msg.meta || {}) : {};
    const discovery = String(msg && msg.type || '') === 'discovery_card' ? getDiscoveryPayload(msg) : null;
    const payload = msg && msg.payload && typeof msg.payload === 'object' ? msg.payload : {};
    const moment = buildMomentEvent(msg?.type || '', payload, msg);
    env.setPlayerScopedEvent({
      type: String(msg && msg.type || ''),
      scope: String(meta.scope || ''),
      audience: String(meta.audience || ''),
      uiChannel: String(meta.ui_channel || ''),
      discoveryId: String(discovery?.id || ''),
      discoveryTitle: String(discovery?.title || ''),
      discoveryKind: String(discovery?.kind || ''),
      discoveryVisibility: String(discovery?.visibility || ''),
      discoverySource: String(discovery?.source || ''),
      timestamp: Date.now(),
      moment,
    });
  }

  function handleScopedEvent(env, msg) {
    if (!env || !msg || typeof msg !== 'object') return false;
    const payload = msg.payload && typeof msg.payload === 'object' ? msg.payload : {};
    const type = String(msg.type || '');
    if (!type) return false;

    if (type === 'handout_received') {
      const handout = {
        id: payload.handout_id || '',
        title: payload.title || 'Untitled Handout',
        public_text: payload.public_text || '',
        received_at: Date.now(),
      };
      recordScopedEvent(env, msg);
      env.openHandoutOverlay?.(handout);
      env.addPlayerReceivedHandout?.(handout);
      env.showParchmentNotification?.(
        payload.title || 'Untitled Handout',
        { variant: 'info', title: '📜 New Handout', duration: 5000 }
      );
      return true;
    }

    if (type === 'discovery_card') {
      const discovery = getDiscoveryPayload(msg);
      recordScopedEvent(env, msg);
      env.showDiscoveryCard?.(discovery);
      return true;
    }

    if (type === 'prop_action_result') {
      recordScopedEvent(env, msg);
      if (payload.message) env.showToast?.(payload.message);
      if (window.ChestView && typeof window.ChestView.isOpen === 'function' && window.ChestView.isOpen()) {
        window.ChestView.showTakeResult?.(payload.message || '', payload.success !== false);
      }
      env.refreshPropInventoryModal?.();
      return true;
    }

    if (type === 'inventory_action_result') {
      recordScopedEvent(env, msg);
      if (payload.message) env.showToast?.(payload.message);
      env.renderInventoryPanel?.();
      return true;
    }

    if (type === 'quest_update' || type === 'session_quest_accept_result' || type === 'session_quest_objective_result' || type === 'session_quest_turn_in_result' || type === 'session_event_notice' || type === 'world_event_notice') {
      if (payload && (payload.dm_only === true || payload.player_safe === false)) return true;
      recordScopedEvent(env, msg);
      return true;
    }

    return false;
  }

  function _findOwnedToken(env) {
    const uid = String(env?.USER_ID || '');
    const matchByOwner = (token) => token && String(token.owner_id || '') === uid;
    return Object.values(env?.tokens || {}).find(matchByOwner)
      || Object.values(env?._stagingTokens || {}).find(matchByOwner)
      || null;
  }

  function _firstDefined() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value !== undefined && value !== null && value !== '') return value;
    }
    return '';
  }

  function getActiveCharacterState(env) {
    if (env && typeof env.getActiveCharacterState === 'function') {
      const external = env.getActiveCharacterState();
      if (external && typeof external === 'object') return external;
    }
    const runtimeSnapshot = (env && typeof env.getActivePlayerCharacterSnapshot === 'function')
      ? (env.getActivePlayerCharacterSnapshot() || {})
      : {};
    const token = _findOwnedToken(env);
    const bookData = (env && typeof env.getCharacterBookDataFromUI === 'function')
      ? (env.getCharacterBookDataFromUI() || {})
      : {};
    return {
      token,
      bookData,
      name: _firstDefined(runtimeSnapshot?.name, token?.name, bookData?.name, env?.NAME, 'My character'),
      currentHp: _firstDefined(runtimeSnapshot?.currentHp, token?.hp, bookData?.currentHp),
      maxHp: _firstDefined(runtimeSnapshot?.maxHp, token?.maxHp, bookData?.maxHp),
      tempHp: _firstDefined(runtimeSnapshot?.tempHp, token?.tempHp, bookData?.tempHp, 0),
      ac: _firstDefined(runtimeSnapshot?.ac, token?.ac, bookData?.ac),
      speed: _firstDefined(runtimeSnapshot?.speed, token?.speed, bookData?.speed),
      initiative: _firstDefined(runtimeSnapshot?.initiative, token?.initiativeMod, bookData?.initiative),
      passivePerception: _firstDefined(token?.passivePerception, bookData?.passivePerception),
      faction: _firstDefined(token?.faction, bookData?.faction),
      notes: _firstDefined(token?.notes, bookData?.campaignNotes),
      level: _firstDefined(token?.level, bookData?.level),
      className: _firstDefined(bookData?.className, ''),
      portraitUrl: _firstDefined(runtimeSnapshot?.portraitUrl, bookData?.avatarUrl, ''),
      tokenImageUrl: _firstDefined(runtimeSnapshot?.tokenImageUrl, token?.image_url, bookData?.tokenImageUrl, ''),
    };
  }

  function renderDashboard(env) {
    const doc = env?.document;
    const mount = doc && doc.getElementById('player-dashboard-shell');
    if (!mount) return false;
    const esc = (value) => String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
    const tokenEmoteDefs = env?.getTokenEmoteDefs?.() || {};
    const role = String(env?.getRole?.() || env?.ROLE || 'viewer').toLowerCase();
    const isPlayer = role === 'player';
    mount.classList.toggle('active', isPlayer);
    mount.setAttribute('aria-hidden', isPlayer ? 'false' : 'true');
    if (!isPlayer) {
      mount.innerHTML = '';
      env?.setPlayerDashboardState?.({ mounted: false, open: false });
      return false;
    }

    const lastEvent = env?.getLastPlayerScopedEvent?.() || {};
    const latestDiscovery = env?.getLatestDiscoveryMeta?.() || {};
    const type = String(lastEvent.type || '');
    const discoveryTitle = String(latestDiscovery.latestTitle || '').trim();
    const discoveryKind = String(latestDiscovery.latestKind || '').replace(/[_-]+/g, ' ').trim();
    const unreadCount = Math.max(0, Number(latestDiscovery.unreadCount || 0));
    const sessionQuests = Array.isArray(env?.getSessionQuests?.()) ? env.getSessionQuests() : [];
    const visibleQuests = sessionQuests.filter((quest) => {
      if (!quest || typeof quest !== 'object') return false;
      const visibility = String(quest.visibility || 'party');
      if (visibility === 'dm_only') return false;
      const assigned = Array.isArray(quest.assignees) ? quest.assignees.map((id) => String(id || '')) : [];
      return !assigned.length || assigned.includes(String(env?.USER_ID || ''));
    });
    const activeQuests = visibleQuests.filter((quest) => {
      const status = String(quest.status || 'active');
      return status !== 'completed' && status !== 'archived' && status !== 'turned_in';
    });
    const discoveryPrefix = discoveryKind ? `You personally uncovered a ${discoveryKind}.` : 'You personally uncovered something new.';
    const summaryMap = {
      discovery_card: discoveryTitle ? `${discoveryPrefix} ${discoveryTitle}` : discoveryPrefix,
      handout_received: 'New private handout received.',
      inventory_action_result: 'Inventory updated.',
      prop_action_result: 'World interaction resolved.',
    };
    const summary = summaryMap[type] || 'Ready for private prompts, handouts, and interaction updates.';
    const meta = type === 'discovery_card'
      ? `${unreadCount} discovery card${unreadCount === 1 ? '' : 's'} waiting in this session.`
      : type ? `Last event: ${type}` : 'No private player events yet.';
    const activeCharacter = getActiveCharacterState(env);
    const ownedToken = activeCharacter.token;
    const conditionCount = Array.isArray(ownedToken?.conditions) ? ownedToken.conditions.length : 0;
    const characterStatus = ownedToken
      ? `${activeCharacter.name || 'My character'}${conditionCount ? ` · ${conditionCount} effect${conditionCount === 1 ? '' : 's'}` : ''}`
      : 'No owned token on the map yet. Open My Character to place or claim your token.';
    const isFirstSession = !type && !ownedToken && !activeQuests.length;
    const savedDiscoveries = getSavedDiscoveries(env);
    const privateHooks = getPrivateStoryHooks(env);
    const savedDiscoveriesMarkup = savedDiscoveries.length
      ? `<div class="player-dashboard-discoveries"><div class="player-dashboard-discoveries-title">Saved discoveries</div>${savedDiscoveries.slice(0, 3).map((d) => `<div class="player-dashboard-discovery-item">${esc(String(d?.title || d || ''))}</div>`).join('')}</div>`
      : '';
    const privateHooksMarkup = privateHooks.length
      ? `<div class="player-dashboard-hooks"><div class="player-dashboard-hooks-title">Private prompts & objectives</div>${privateHooks.slice(0, 2).map((h) => `<div class="player-dashboard-hook-item">${esc(String(h?.text || h || ''))}</div>`).join('')}</div>`
      : '';

    mount.innerHTML = `
      <div class="player-dashboard-header">
        <div class="player-dashboard-title">${isFirstSession ? 'Welcome, adventurer' : 'Session shortcuts'}</div>
      </div>
      <div class="player-dashboard-summary">${summary}</div>
      <div class="player-dashboard-meta">${meta}</div>
      <div class="player-dashboard-meta">${characterStatus}</div>
      <div class="player-dashboard-actions">
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="party">Party<span class="btn-kicker">Position & roster</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="inventory">Inventory<span class="btn-kicker">Items, bags, gold</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="chat">Chat<span class="btn-kicker">Party comms</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="moments">Moments<span class="btn-kicker">Story timeline</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="combat">Combat<span class="btn-kicker">Turn order & status</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="spells">Spells<span class="btn-kicker">Prepared & granted</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="token">My Character<span class="btn-kicker">Place/claim token</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="rolls">Roll Dice<span class="btn-kicker">Checks & attacks</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="journal">Journal & Quests<span class="btn-kicker">Canon, clues, quest progress</span></button>
        <button type="button" class="player-dashboard-btn player-dashboard-btn--combat" data-player-dashboard-action="combat-guide">Combat Guide<span class="btn-kicker">Turn flow, movement, actions</span></button>
        <button type="button" class="player-dashboard-btn" data-player-dashboard-action="help">Help Hub<span class="btn-kicker">Tours, guides &amp; tips</span></button>
      </div>
      ${savedDiscoveriesMarkup}
      ${privateHooksMarkup}
    `;
    mount.querySelector('[data-player-dashboard-action="party"]')?.addEventListener('click', function () {
      env?.switchRightTab?.('party');
    });
    mount.querySelector('[data-player-dashboard-action="chat"]')?.addEventListener('click', function () {
      env?.switchRightTab?.('chat');
    });
    mount.querySelector('[data-player-dashboard-action="moments"]')?.addEventListener('click', function () {
      env?.switchRightTab?.('moments');
    });
    mount.querySelector('[data-player-dashboard-action="combat"]')?.addEventListener('click', function () {
      env?.switchRightTab?.('combat');
    });
    mount.querySelector('[data-player-dashboard-action="token"]')?.addEventListener('click', function () {
      openMyTokenPanel(env);
    });
    mount.querySelector('[data-player-dashboard-action="inventory"]')?.addEventListener('click', function () {
      env?.switchRightTab?.('inventory');
    });
    mount.querySelector('[data-player-dashboard-action="spells"]')?.addEventListener('click', function () {
      env?.switchRightTab?.('spelllib');
    });
    mount.querySelector('[data-player-dashboard-action="rolls"]')?.addEventListener('click', function () {
      env?.toggleFlyout?.('flyout-dice');
    });
    mount.querySelector('[data-player-dashboard-action="journal"]')?.addEventListener('click', function () {
      env?.toggleFlyout?.('flyout-journal');
    });
    mount.querySelector('[data-player-dashboard-action="combat-guide"]')?.addEventListener('click', function () {
      if (window.AppOnboarding && typeof AppOnboarding.showHelpHub === 'function') {
        AppOnboarding.showHelpHub('player');
      }
    });
    mount.querySelector('[data-player-dashboard-action="help"]')?.addEventListener('click', function () {
      if (window.AppOnboarding && typeof AppOnboarding.showHelpHub === 'function') {
        AppOnboarding.showHelpHub('player');
      }
    });
    mount.querySelectorAll('[data-player-emote-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const emoteId = btn.getAttribute('data-player-emote-id') || '';
        if (emoteId && tokenEmoteDefs[emoteId]) env?.triggerTokenEmote?.(emoteId);
      });
    });
    env?.setPlayerDashboardState?.({ mounted: true, open: true });
    return true;
  }

  function applyCharacterBookToQuickPanel(env, showDone = true) {
    const activeCharacter = getActiveCharacterState(env);
    const data = (activeCharacter && activeCharacter.bookData) || {};
    const set = (id, value) => {
      const el = env.document.getElementById(id);
      if (el) el.value = value ?? '';
    };
    set('char-name', _firstDefined(activeCharacter.name, data.name, env.NAME, ''));
    set('char-curhp', _firstDefined(activeCharacter.currentHp, data.currentHp, ''));
    set('char-hp', _firstDefined(activeCharacter.maxHp, data.maxHp, ''));
    set('char-temp-hp', _firstDefined(activeCharacter.tempHp, data.tempHp, 0));
    set('char-initiative', _firstDefined(activeCharacter.initiative, data.initiative, ''));
    set('char-ac', _firstDefined(activeCharacter.ac, data.ac, ''));
    set('char-speed', _firstDefined(activeCharacter.speed, data.speed, ''));
    set('char-level', _firstDefined(activeCharacter.level, data.level, ''));
    set('char-passive', _firstDefined(activeCharacter.passivePerception, data.passivePerception, ''));
    set('char-faction', _firstDefined(activeCharacter.faction, data.faction, ''));
    set('char-notes', _firstDefined(activeCharacter.notes, data.campaignNotes, ''));
    const bestClass = String(_firstDefined(activeCharacter.className, data.className, ''))
      .split(/[\/,&]/).map(x => x.trim()).filter(Boolean)[0] || '';
    if (bestClass) {
      const found = env.PLAYER_CLASSES.find(c => c.name.toLowerCase() === bestClass.toLowerCase());
      if (found) {
        env.setSelectedClass(found);
        env.setPlayerColor(found.color || env.getPlayerColor());
        env.buildClassGrid();
        env.refreshPlayerColorSwatches();
      }
    }
    env.syncCharSheetFromBookData(data);
    env.refreshCharSummary();
    env.scheduleCharProfileAutosave();
    if (showDone) env.showToast('Character Book synced to quick panel');
  }

  function openMyTokenPanel(env) {
    if (env.ROLE === 'dm') return;
    const activeCharacter = getActiveCharacterState(env);
    const myTok = activeCharacter.token;
    if (myTok) {
      env.openMyTokenStats(myTok);
      return;
    }
    const flyout = env.document.getElementById('flyout-char');
    if (flyout && !flyout.classList.contains('open')) env.toggleFlyout('flyout-char');
  }

  window.AppUIPlayerShell = { applyCharacterBookToQuickPanel, openMyTokenPanel, handleScopedEvent, renderDashboard };
})();
