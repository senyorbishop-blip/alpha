(function () {
  // Live ownership boundary:
  // - This module owns startup sequencing only.
  // - It does not own gameplay-domain behavior.
  // - Domain init/render logic still lives in play.html and is invoked via bridge callbacks.
  function setDisplay(el, value) { if (el && el.style) el.style.display = value; return el; }
  function applyTopbar(env) {
    const roleEl = env.document.getElementById('topbar-role');
    if (roleEl) {
      roleEl.textContent = String(env.ROLE || '').toUpperCase();
      roleEl.className = `role-${env.ROLE}`;
    }
    const sessionInfo = env.document.getElementById('session-info');
    if (sessionInfo) {
      sessionInfo.textContent = `${env.NAME} · ${env.SESSION_ID}`;
    }
  }

  function initSharedUIShell(env) {
    env.applyRoleVisibility();
    env.updateSpellTip();
    env.initJournalUI();
    env.initLibraryUI();
    env.renderItemLibraryList();
    env.renderItemLibraryEditor();
    env.refreshInventoryTransferTargets();
  }

  function initPlayerShell(env) {
    if (env.ROLE !== 'player') return;
    const charBtn = env.document.getElementById('rail-char-btn');
    if (charBtn) setDisplay(charBtn, 'flex');
    env.refreshCharProfileSelect();
    if (env.getCharSheet()) {
      const sheetToggleBtn = env.document.getElementById('sheet-toggle-btn');
      if (sheetToggleBtn) setDisplay(sheetToggleBtn, 'block');
    }
    env.buildClassGrid();
    env.buildPlayerColorSwatches();
    setTimeout(() => {
      const hasMyToken = Object.values(env.getTokens() || {}).some(t => t && t.owner_id === env.USER_ID);
      if (!hasMyToken) env.toggleFlyout('flyout-char');
    }, 800);
  }

  function loadDmInvites(env) {
    if (env.ROLE !== 'dm') return;
    env.fetchSessionInvites(env.SESSION_ID, env.USER_ID)
      .then(d => {
        if (!d || !d.player_invite) return;
        const base = env.location.origin;
        const playerChip = env.document.getElementById('chip-player-invite');
        const viewerChip = env.document.getElementById('chip-viewer-invite');
        const inviteWrap = env.document.getElementById('invite-codes');
        if (playerChip) {
          playerChip.textContent = `${base}/join?session=${env.SESSION_ID}&code=${d.player_invite}&role=player`;
        }
        if (viewerChip) {
          viewerChip.textContent = `${base}/join?session=${env.SESSION_ID}&code=${d.viewer_invite}&role=viewer`;
        }
        if (inviteWrap) inviteWrap.classList.add('visible');
      })
      .catch(err => env.reportClientRuntimeError('Invite fetch', err));
  }

  function bindChatEnter(env) {
    const chatInput = env.document.getElementById('chat-input');
    if (!chatInput || chatInput.dataset.bootBoundEnter === '1') return;
    chatInput.dataset.bootBoundEnter = '1';
    chatInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') env.sendChat();
    });
  }

  function preloadEditorShell(env) {
    env.ensureEditorLayerLoaded?.(true);
    env.ensureEditorWallsLoaded?.(true);
    env.ensureEditorPropsLoaded?.(true);
    env.ensureEditorPathsLoaded?.(true);
    env.ensureEditorLabelsLoaded?.(true);
    env.ensureEditorMarkersLoaded?.(true);
  }

  function bindOutsideShellClose(env) {
    if (env.document.body.dataset.bootBoundOutsideClick === '1') return;
    env.document.body.dataset.bootBoundOutsideClick = '1';
    env.document.addEventListener('click', e => {
      env.handleGlobalContextClick(e);
      const propPopup = env.document.getElementById('prop-popup');
      if (Date.now() < env.getIgnorePropPopupOutsideClickUntil()) return;
      if (propPopup && propPopup.style.display === 'block' && !propPopup.contains(e.target)) {
        env.propPopupClose();
      }
    });
  }

  function initUI(env) {
    // Compatibility path: while play.html remains gameplay/UI authority,
    // keep its full init path as the primary implementation.
    if (typeof env.runLegacyInitUI === 'function') {
      env.runLegacyInitUI();
      return;
    }
    applyTopbar(env);
    initSharedUIShell(env);
    initPlayerShell(env);
    loadDmInvites(env);
    bindChatEnter(env);
    preloadEditorShell(env);
    bindOutsideShellClose(env);
  }

  function runDOMContentLoaded(env) {
    // Explicit, ordered startup owner for the live page shell.
    env.safeClientCall('boot:initUI', () => initUI(env));
    env.safeClientCall('boot:initCanvas', () => env.initCanvas());
    env.safeClientCall('boot:connectWS', () => env.connectWS());
    env.safeClientCall('boot:syncSessionAuthority', () => env.syncSessionAuthority('domcontentloaded'));
  }

  window.AppBootShell = {
    initUI,
    runDOMContentLoaded,
  };
})();
