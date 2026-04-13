(function (global) {
  'use strict';
  // Live ownership boundary:
  // - This module is compatibility/handoff glue only.
  // - It adapts store + play.html globals into env contracts for live shell modules.
  // - It must not become a second gameplay source-of-truth.

  function pick(name, fallback) {
    const value = global[name];
    return typeof value === 'function' ? value.bind(global) : (fallback || function () {});
  }

  function getStore() {
    return global.AppStateStore || global.AppStore || null;
  }

  function storeGet(path, fallback) {
    const store = getStore();
    return store && typeof store.get === 'function' ? store.get(path, fallback) : fallback;
  }

  function storeSet(path, value) {
    const store = getStore();
    return store && typeof store.set === 'function' ? store.set(path, value) : value;
  }

  function createMessageDispatchEnv() {
    return {
      reportClientRuntimeError: pick('reportClientRuntimeError'),
      handleLegacyMessage: pick('handleLegacyMessage', pick('handleMessage')),
    };
  }

  function createWsConfig() {
    return {
      getSessionId: function () { return storeGet('session.id', global.SESSION_ID || ''); },
      getUserId: function () { return storeGet('user.id', global.USER_ID || ''); },
      getRole: function () { return storeGet('user.role', global.ROLE || 'viewer'); },
      getSocket: function () { return storeGet('socket.instance', global.ws || null); },
      setSocket: function (value) { storeSet('socket.instance', value); global.ws = value; },
      getReconnectTimer: function () { return storeGet('socket.reconnectTimer', global.wsReconnectTimer || null); },
      setReconnectTimer: function (value) { storeSet('socket.reconnectTimer', value); global.wsReconnectTimer = value; },
      getPendingMessages: function () { return storeGet('socket.pendingMessages', Array.isArray(global._pendingWSMessages) ? global._pendingWSMessages : []); },
      setPendingMessages: function (value) { const next = Array.isArray(value) ? value : []; storeSet('socket.pendingMessages', next); global._pendingWSMessages = next; },
      getQueuedEditorTypes: function () { return global._queuedEditorTypes || new Set(); },
      onMessage: function (msg) {
        if (global.AppMessageDispatch && typeof global.AppMessageDispatch.handleIncoming === 'function') {
          global.AppMessageDispatch.handleIncoming(msg, createMessageDispatchEnv());
          return;
        }
        const legacy = pick('handleLegacyMessage', pick('handleMessage'));
        legacy(msg);
      },
      onOpen: function () {
        const status = global.document.getElementById('ws-status');
        if (status) status.classList.add('connected');
        if (typeof global._setWsStatus === 'function') global._setWsStatus('connected');
        storeSet('socket.connected', true);
        storeSet('socket.status', 'connected');
        if (global.ROLE === 'dm' && typeof global._resyncDmMapNav === 'function') global.setTimeout(global._resyncDmMapNav, 0);
        if (global.ROLE === 'dm' || global.ROLE === 'player') {
          if (global.AppWS && typeof global.AppWS.send === 'function') global.AppWS.send({ type: 'treasury_get', payload: {} });
          else if (typeof global.sendWS === 'function') global.sendWS({ type: 'treasury_get', payload: {} });
        }
      },
      onClose: function (_event) {
        const status = global.document.getElementById('ws-status');
        if (status) status.classList.remove('connected');
        if (typeof global._setWsStatus === 'function') global._setWsStatus('reconnecting');
        storeSet('socket.connected', false);
        storeSet('socket.status', 'disconnected');
      },
      onCloseExpired: function () {
        const status = global.document.getElementById('ws-status');
        if (status) {
          status.classList.remove('connected');
          status.title = 'Session expired — please return to lobby';
        }
        if (typeof global._setWsStatus === 'function') global._setWsStatus('expired');
        storeSet('socket.connected', false);
        storeSet('socket.status', 'expired');
        if (typeof global.showToast === 'function') global.showToast('Session expired. Please start a new session.');
        global.setTimeout(function () { global.location.href = '/'; }, 3000);
      },
    };
  }

  function createBootEnv() {
    return {
      window: global,
      document: global.document,
      location: global.location,
      SESSION_ID: storeGet('session.id', global.SESSION_ID),
      USER_ID: storeGet('user.id', global.USER_ID),
      ROLE: storeGet('user.role', global.ROLE),
      NAME: storeGet('user.name', global.NAME),
      RETURNING: storeGet('session.returning', global.RETURNING),
      safeClientCall: pick('safeClientCall'),
      reportClientRuntimeError: pick('reportClientRuntimeError'),
      runLegacyInitUI: pick('initUI'),
      initCanvas: pick('initCanvas'),
      connectWS: pick('connectWS'),
      syncSessionAuthority: pick('syncSessionAuthority'),
      applyRoleVisibility: pick('__bootApplyRoleVisibility'),
      updateSpellTip: pick('_updateSpellTip'),
      initJournalUI: pick('initJournalPanel'),
      initLibraryUI: pick('initLogsUI'),
      renderItemLibraryList: pick('renderItemLibraryList'),
      renderItemLibraryEditor: pick('renderItemLibraryEditor'),
      refreshInventoryTransferTargets: pick('refreshInventoryTransferTargets'),
      refreshCharProfileSelect: pick('refreshCharProfileSelect'),
      getCharSheet: function () { return global._charSheet || null; },
      buildClassGrid: pick('buildClassGrid'),
      buildPlayerColorSwatches: pick('buildPlayerColorSwatches'),
      getTokens: function () { return global.tokens || {}; },
      toggleFlyout: pick('toggleFlyout'),
      fetchSessionInvites: function (sessionId, userId) {
        return global.fetch(`/api/session/${encodeURIComponent(sessionId)}/invites?user_id=${encodeURIComponent(userId)}`).then(function (resp) {
          if (!resp.ok) throw new Error('Invite fetch failed: ' + resp.status);
          return resp.json();
        });
      },
      sendChat: pick('sendChat'),
      ensureEditorLayerLoaded: pick('ensureEditorLayerLoaded'),
      ensureEditorWallsLoaded: pick('ensureEditorWallsLoaded'),
      ensureEditorPropsLoaded: pick('ensureEditorPropsLoaded'),
      ensureEditorPathsLoaded: pick('ensureEditorPathsLoaded'),
      ensureEditorLabelsLoaded: pick('ensureEditorLabelsLoaded'),
      ensureEditorMarkersLoaded: pick('ensureEditorMarkersLoaded'),
      handleGlobalContextClick: pick('handleGlobalContextClick'),
      getIgnorePropPopupOutsideClickUntil: function () { return Number(global._ignorePropPopupOutsideClickUntil || 0); },
      propPopupClose: pick('propPopupClose'),
    };
  }

  global.AppRuntimeBridge = {
    createBootEnv: createBootEnv,
    createMessageDispatchEnv: createMessageDispatchEnv,
    createWsConfig: createWsConfig,
  };
})(window);
