(function () {
  const TOKEN_EMOTE_DEFS = {
    question: { icon: '❓', label: 'Question', bubbleLabel: 'Question', accent: '#7dd3fc' },
    danger: { icon: '⚠️', label: 'Danger', bubbleLabel: 'Danger', accent: '#f97316' },
    laugh: { icon: '😂', label: 'Laugh', bubbleLabel: 'Laugh', accent: '#facc15' },
    help: { icon: '🆘', label: 'Help', bubbleLabel: 'Help', accent: '#ef4444' },
    ready: { icon: '✅', label: 'Ready', bubbleLabel: 'Ready', accent: '#22c55e' },
    angry: { icon: '😠', label: 'Angry', bubbleLabel: 'Angry', accent: '#fb7185' },
    stealth: { icon: '🕵️', label: 'Stealth', bubbleLabel: 'Stealth', accent: '#a78bfa' },
    prayer: { icon: '🙏', label: 'Prayer', bubbleLabel: 'Prayer', accent: '#fde68a' },
    arcane_focus: { icon: '✨', label: 'Arcane Focus', bubbleLabel: 'Focus', accent: '#38bdf8' },
  };

  const TTL_MS = 2800;
  const COOLDOWN_MS = 2000;
  const state = {
    cooldownUntil: 0,
    cooldownTimer: null,
    emotes: new Map(),
  };

  function escapeHtml(env, value) {
    if (env?.escapeHtml) return env.escapeHtml(value);
    return String(value ?? '');
  }

  function syncDashboard(env) {
    env?.renderDashboardShell?.();
  }

  function getMyReactableToken(env) {
    if (String(env?.role || '').toLowerCase() !== 'player') return null;
    const userId = String(env?.userId || '');
    const activeTokenId = String(env?.activeTokenId || '');
    if (activeTokenId) {
      const active = env?.tokens?.[activeTokenId] || env?.stagingTokens?.[activeTokenId] || null;
      if (active && String(active.owner_id || '') === userId) return active;
    }
    const live = Object.values(env?.tokens || {}).find((t) => t && String(t.owner_id || '') === userId);
    if (live) return live;
    return Object.values(env?.stagingTokens || {}).find((t) => t && String(t.owner_id || '') === userId) || null;
  }

  function getCooldownRemainingMs() {
    return Math.max(0, Number(state.cooldownUntil || 0) - Date.now());
  }

  function getStatusElement(env) {
    return env?.document?.getElementById('token-emote-status') || null;
  }

  function getStatus(env) {
    return getStatusElement(env)?.textContent || '';
  }

  function setStatus(env, text) {
    const el = getStatusElement(env);
    if (el) el.textContent = text || 'Pick a reaction for your token.';
  }

  function getActive(tokenId) {
    const key = String(tokenId || '');
    const entry = state.emotes.get(key);
    if (!entry) return null;
    if (Number(entry.expiresAt || 0) <= Date.now()) {
      state.emotes.delete(key);
      return null;
    }
    return entry;
  }

  function getRenderState(tokenId) {
    const entry = getActive(tokenId);
    if (!entry) return null;
    const def = TOKEN_EMOTE_DEFS[String(entry.emoteId || '')] || {};
    const ttl = Math.max(1, TTL_MS);
    const remaining = Math.max(0, Number(entry.expiresAt || 0) - Date.now());
    const progress = Math.max(0, Math.min(1, remaining / ttl));
    return {
      ...entry,
      icon: String(entry.icon || def.icon || ''),
      label: String(def.bubbleLabel || entry.label || def.label || entry.emoteId || ''),
      accent: String(def.accent || '#ffffff'),
      progress,
    };
  }

  function renderPanel(env) {
    const panel = env?.document?.getElementById('token-emote-panel');
    const grid = env?.document?.getElementById('token-emote-grid');
    if (!panel || !grid) return;
    const active = String(env?.role || '').toLowerCase() === 'player';
    panel.classList.toggle('active', active);
    if (!active) return;
    const myToken = getMyReactableToken(env);
    const cooldownMs = getCooldownRemainingMs();
    if (!myToken) setStatus(env, 'Place your token to unlock quick reactions.');
    else if (cooldownMs > 0) setStatus(env, `Recharging… ${Math.max(1, Math.ceil(cooldownMs / 1000))}s`);
    else setStatus(env, `React as ${myToken.name || 'your token'}.`);

    grid.innerHTML = Object.entries(TOKEN_EMOTE_DEFS).map(([id, def]) => {
      const disabled = !myToken || cooldownMs > 0;
      const title = !myToken
        ? 'Place your token first'
        : (cooldownMs > 0 ? `Cooldown ${Math.max(1, Math.ceil(cooldownMs / 1000))}s` : `${def.label}`);
      return `<button class="token-emote-action" type="button" onclick="triggerTokenEmote('${escapeHtml(env, id)}')" ${disabled ? 'disabled' : ''} title="${escapeHtml(env, title)}" style="border-color:${def.accent}44;">
        <span class="token-emote-icon">${def.icon}</span>
        <span class="token-emote-label">${escapeHtml(env, def.label)}</span>
      </button>`;
    }).join('');
    syncDashboard(env);
  }

  function setCooldown(env, ms, options = {}) {
    const next = Date.now() + Math.max(0, Number(ms || 0));
    if (next > state.cooldownUntil) state.cooldownUntil = next;
    renderPanel(env);
    if (!options.silent && ms > 0) setStatus(env, `Recharging… ${Math.max(1, Math.ceil(ms / 1000))}s`);
    if (state.cooldownTimer) clearTimeout(state.cooldownTimer);
    if (getCooldownRemainingMs() > 0) {
      state.cooldownTimer = setTimeout(function tickCooldown() {
        renderPanel(env);
        const remain = getCooldownRemainingMs();
        if (remain > 0) {
          setStatus(env, `Recharging… ${Math.max(1, Math.ceil(remain / 1000))}s`);
          state.cooldownTimer = setTimeout(tickCooldown, 250);
        } else {
          state.cooldownTimer = null;
          renderPanel(env);
        }
      }, 250);
    } else {
      state.cooldownTimer = null;
    }
  }

  function trigger(env, emoteId) {
    const myToken = getMyReactableToken(env);
    if (!myToken) {
      env?.showToast?.('Place your token first.');
      renderPanel(env);
      return;
    }
    const def = TOKEN_EMOTE_DEFS[String(emoteId || '')];
    if (!def) return;
    const remain = getCooldownRemainingMs();
    if (remain > 0) {
      setStatus(env, `Recharging… ${Math.max(1, Math.ceil(remain / 1000))}s`);
      renderPanel(env);
      return;
    }
    env?.sendWS?.({ type: 'token_emote', payload: { token_id: myToken.id, emote_id: emoteId } });
    setCooldown(env, COOLDOWN_MS, { silent: true });
    setStatus(env, `${def.label} sent from ${myToken.name || 'your token'}.`);
    syncDashboard(env);
  }

  function apply(env, payload = {}) {
    const tokenId = String(payload.token_id || '');
    const emoteId = String(payload.emote_id || '');
    if (!tokenId || !TOKEN_EMOTE_DEFS[emoteId]) return;
    const expiresAtMs = Number(payload.expires_at || 0) > 1000000000
      ? Number(payload.expires_at) * 1000
      : (Date.now() + TTL_MS);
    state.emotes.set(tokenId, {
      tokenId,
      emoteId,
      icon: String(payload.icon || TOKEN_EMOTE_DEFS[emoteId].icon || ''),
      label: String(payload.label || TOKEN_EMOTE_DEFS[emoteId].label || emoteId),
      actorName: String(payload.actor_name || ''),
      expiresAt: expiresAtMs,
      mapContext: String(payload.map_context || ((env?.tokens?.[tokenId] || env?.stagingTokens?.[tokenId])?.map_context || 'world')),
    });
    const delay = Math.max(0, expiresAtMs - Date.now()) + 50;
    setTimeout(function () {
      const current = state.emotes.get(tokenId);
      if (current && Number(current.expiresAt || 0) <= Date.now()) {
        state.emotes.delete(tokenId);
        env?.drawFrame?.();
      }
    }, delay);
    env?.drawFrame?.();
  }

  window.AppUITokenEmotes = {
    getDefs: () => TOKEN_EMOTE_DEFS,
    getTTL: () => TTL_MS,
    getCooldownMs: () => COOLDOWN_MS,
    getMyReactableToken,
    getCooldownRemainingMs,
    getStatus,
    setStatus,
    setCooldown,
    renderPanel,
    trigger,
    apply,
    getActive,
    getRenderState,
  };
})();
