(function (global) {
  'use strict';

  let channelInitialized = false;
  let bindingsInstalled = false;

  function setDisplay(el, value) { if (el && el.style) el.style.display = value; return el; }

  function syncChatModeUI(env) {
    const document = env.document;
    const modeSel = document.getElementById('chat-mode');
    const chatInput = document.getElementById('chat-input');
    const channelLabel = document.getElementById('chat-channel-label');
    const mode = modeSel ? String(modeSel.value || 'everyone') : 'everyone';
    if (chatInput) chatInput.classList.toggle('channel-viewers', mode === 'viewers');
    if (channelLabel) channelLabel.style.display = mode === 'viewers' ? 'inline' : 'none';
  }

  function updateChatTargetVisibility(env) {
    const document = env.document;
    const modeSel = document.getElementById('chat-mode');
    const targetSel = document.getElementById('chat-target');
    const modeWrap = document.getElementById('chat-mode-wrap');
    const targetWrap = document.getElementById('chat-target-wrap');
    if (!modeSel || !targetSel || !modeWrap || !targetWrap) return;
    setDisplay(modeWrap, 'inline-flex');
    setDisplay(targetWrap, (modeSel.value === 'private') ? 'inline-flex' : 'none');
    syncChatModeUI(env);
  }

  function renderChatTargets(env) {
    const document = env.document;
    const modeSel = document.getElementById('chat-mode');
    const sel = document.getElementById('chat-target');
    const modeWrap = document.getElementById('chat-mode-wrap');
    const targetWrap = document.getElementById('chat-target-wrap');
    if (!sel || !modeSel || !modeWrap || !targetWrap) return;
    const userId = env.getUserId();
    const users = env.getUsers() || {};
    const current = sel.value;
    if (!channelInitialized) {
      channelInitialized = true;
      if (env.getRole?.() === 'viewer') modeSel.value = 'viewers';
    }
    sel.innerHTML = '<option value="">Choose person…</option>';
    Object.values(users)
      .filter(u => u && u.id !== userId && u.connected)
      .sort((a, b) => {
        const roleCmp = String(a.role || '').localeCompare(String(b.role || ''));
        if (roleCmp !== 0) return roleCmp;
        return String(a.name || '').localeCompare(String(b.name || ''));
      })
      .forEach(u => {
        const o = document.createElement('option');
        o.value = u.id;
        const roleLabel = u.role === 'dm' ? 'DM' : u.role === 'player' ? 'Player' : 'Viewer';
        o.textContent = `${u.name || roleLabel} (${roleLabel})`;
        sel.appendChild(o);
      });
    if ([...sel.options].some(o => o.value === current)) sel.value = current;
    else sel.value = '';
    updateChatTargetVisibility(env);
  }

  function sendChat(env) {
    const document = env.document;
    const input = document.getElementById('chat-input');
    const msg = String(input?.value || '').trim();
    if (!msg) return;
    const modeSel = document.getElementById('chat-mode');
    const mode = modeSel ? modeSel.value : 'everyone';
    if (msg.startsWith('?') && mode === 'everyone') {
      const question = msg.slice(1).trim();
      if (question) {
        env.sendWS({ type: 'ai_rules_oracle', payload: { question, asker_name: env.getName?.() || '' } });
        input.value = '';
        return;
      }
    }
    if (mode === 'viewers') {
      env.sendWS({ type: 'chat_message', payload: { message: msg, channel: 'viewers' } });
      input.value = '';
      return;
    }
    const targetSel = document.getElementById('chat-target');
    if (modeSel && modeSel.value === 'private') {
      const targetUserId = (targetSel && targetSel.value) ? targetSel.value : '';
      if (!targetUserId) {
        env.showToast('Choose who to whisper to.');
        return;
      }
      env.sendWS({ type: 'chat_message', payload: { message: msg, channel: 'whisper', target_user_id: targetUserId } });
      input.value = '';
      return;
    }
    env.sendWS({ type: 'chat_message', payload: { message: msg } });
    input.value = '';
  }

  function installBindings(env) {
    if (bindingsInstalled) return;
    const document = env.document;
    document.getElementById('chat-mode')?.addEventListener('change', () => {
      updateChatTargetVisibility(env);
    });
    document.getElementById('chat-send')?.addEventListener('click', () => {
      sendChat(env);
    });
    document.getElementById('chat-input')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') sendChat(env);
    });
    bindingsInstalled = true;
  }

  function init(env) {
    installBindings(env);
    renderChatTargets(env);
    updateChatTargetVisibility(env);
  }

  global.AppUIChat = {
    init,
    updateChatTargetVisibility,
    renderChatTargets,
    sendChat,
  };
})(window);
