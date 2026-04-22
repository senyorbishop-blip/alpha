(function (global) {
  'use strict';

  let config = {
    getSessionId: () => '',
    getUserId: () => '',
    getRole: () => 'viewer',
    getSocket: () => null,
    setSocket: () => {},
    getReconnectTimer: () => null,
    setReconnectTimer: () => {},
    getPendingMessages: () => [],
    setPendingMessages: () => {},
    getQueuedEditorTypes: () => new Set(),
    onMessage: () => {},
    onOpen: () => {},
    onClose: () => {},
    onCloseExpired: () => {},
    showToast: () => {},
  };
  let lifecycleHooksInstalled = false;

  function closeSocket(socket, code = 1000, reason = 'Client reconnect cleanup') {
    if (!socket) return;
    try {
      if (socket.readyState === global.WebSocket.OPEN || socket.readyState === global.WebSocket.CONNECTING) {
        socket.close(code, reason);
      }
    } catch (_err) {}
  }

  function clearReconnectTimer() {
    const timer = config.getReconnectTimer();
    if (timer) global.clearTimeout(timer);
    config.setReconnectTimer(null);
  }

  function scheduleReconnect() {
    if (config.getReconnectTimer()) return;
    const timer = global.setTimeout(() => {
      config.setReconnectTimer(null);
      connectWS();
    }, 3000);
    config.setReconnectTimer(timer);
  }

  function installLifecycleHooks() {
    if (lifecycleHooksInstalled) return;
    lifecycleHooksInstalled = true;
    const stopSocketLifecycle = () => {
      clearReconnectTimer();
      const socket = config.getSocket();
      if (socket) {
        config.setSocket(null);
        closeSocket(socket, 1000, 'Page lifecycle teardown');
      }
    };
    global.addEventListener('beforeunload', stopSocketLifecycle);
    global.addEventListener('pagehide', stopSocketLifecycle);
  }

  function configure(nextConfig = {}) {
    config = { ...config, ...nextConfig };
    installLifecycleHooks();
  }

  function buildMessage(msg) {
    return {
      ...msg,
      session_id: config.getSessionId(),
      user_id: config.getUserId(),
    };
  }

  function queueMessage(msg) {
    const built = buildMessage(msg);
    const type = String(built.type || '');
    let pending = Array.isArray(config.getPendingMessages()) ? config.getPendingMessages().slice() : [];
    if (type === 'local_map_enter' || type === 'local_map_exit') {
      pending = pending.filter((entry) => {
        const t = String(entry?.type || '');
        return t !== 'local_map_enter' && t !== 'local_map_exit';
      });
    } else if (config.getQueuedEditorTypes().has(type)) {
      const ctx = String(built?.payload?.map_context || 'world');
      pending = pending.filter((entry) => !(String(entry?.type || '') === type && String(entry?.payload?.map_context || 'world') === ctx));
    }
    pending.push(built);
    if (pending.length > 200) pending = pending.slice(-200);
    config.setPendingMessages(pending);
  }

  function flushPendingMessages() {
    const socket = config.getSocket();
    const pending = Array.isArray(config.getPendingMessages()) ? config.getPendingMessages() : [];
    if (!socket || socket.readyState !== global.WebSocket.OPEN || !pending.length) return;
    config.setPendingMessages([]);
    pending.forEach((msg) => {
      try {
        socket.send(JSON.stringify(msg));
      } catch (_err) {
        queueMessage(msg);
      }
    });
  }

  function connectWS() {
    const sessionId = String(config.getSessionId() || '').trim();
    const userId = String(config.getUserId() || '').trim();
    if (!sessionId || !userId) {
      console.warn('[WS] Missing session or user id, skipping connect', { sessionId, userId });
      config.setSocket(null);
      return null;
    }
    const proto = global.location.protocol === 'https:' ? 'wss' : 'ws';
    // Attach JWT token as query param when available (Part 5.1)
    const token = (global.sessionStorage && global.sessionStorage.getItem('dnd_token')) || '';
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
    clearReconnectTimer();
    const priorSocket = config.getSocket();
    if (priorSocket) {
      if (priorSocket.readyState === global.WebSocket.OPEN || priorSocket.readyState === global.WebSocket.CONNECTING) {
        return priorSocket;
      }
      closeSocket(priorSocket, 1000, 'Replacing stale socket');
    }

    const socket = new global.WebSocket(`${proto}://${global.location.host}/ws/${sessionId}/${userId}${tokenParam}`);
    config.setSocket(socket);

    socket.onopen = () => {
      if (config.getSocket() !== socket) {
        closeSocket(socket, 1000, 'Superseded socket on open');
        return;
      }
      config.onOpen();
      clearReconnectTimer();
      flushPendingMessages();
    };

    socket.onclose = (event) => {
      if (config.getSocket() !== socket) return;
      config.setSocket(null);
      config.onClose(event);
      if (event.code === 4001 || event.code === 4003 || event.code === 4004) {
        config.onCloseExpired(event);
        return;
      }
      scheduleReconnect();
    };

    socket.onerror = () => {
      if (config.getSocket() !== socket) return;
      socket.close();
    };
    socket.onmessage = (event) => {
      if (config.getSocket() !== socket) return;
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (_err) {
        return;
      }
      config.onMessage(msg);
    };
    return socket;
  }

  function send(msg) {
    const socket = config.getSocket();
    if (!socket || socket.readyState !== global.WebSocket.OPEN) {
      console.warn('[WS] Not connected, queueing message:', msg.type);
      queueMessage(msg);
      return;
    }
    try {
      socket.send(JSON.stringify(buildMessage(msg)));
    } catch (err) {
      console.warn('[WS] Send failed, queueing message:', msg.type, err);
      queueMessage(msg);
    }
  }

  global.AppWS = {
    configure,
    connectWS,
    buildMessage,
    queueMessage,
    flushPendingMessages,
    send,
  };
})(window);
