/**
 * client/static/js/ui/conversation.js — NPC Conversation Mode UI
 *
 * Manages the conversation HUD that appears when the DM opens a social scene
 * with a named NPC.  Players can:
 *   • set their approach tone
 *   • perform social actions (persuade, intimidate, etc.)
 *   • join / leave the optional speak queue
 *
 * The DM can additionally:
 *   • set the NPC reaction cue
 *   • advance the speak queue
 *   • exit conversation mode
 *
 * Freeform chat is never blocked.  This is purely additive.
 */
(function (global) {
  'use strict';

  const TONES = [
    { value: 'polite',      label: 'Polite',      icon: '🤝' },
    { value: 'charming',    label: 'Charming',    icon: '✨' },
    { value: 'cautious',    label: 'Cautious',    icon: '👀' },
    { value: 'sympathetic', label: 'Sympathetic', icon: '💛' },
    { value: 'deceptive',   label: 'Deceptive',   icon: '🎭' },
    { value: 'hostile',     label: 'Hostile',     icon: '⚡' },
  ];

  const ACTIONS = [
    { value: 'persuade',    label: 'Persuade',    icon: '🗣' },
    { value: 'charm',       label: 'Charm',       icon: '💖' },
    { value: 'insight',     label: 'Insight',     icon: '🔍' },
    { value: 'intimidate',  label: 'Intimidate',  icon: '😤' },
    { value: 'deceive',     label: 'Deceive',     icon: '🃏' },
    { value: 'appeal',      label: 'Appeal',      icon: '🙏' },
  ];

  let _env = null;
  let _state = null;     // last conversation_state payload

  // ── Public API ──────────────────────────────────────────────────────────────

  function init(env) {
    _env = env;
    _ensureHud();
  }

  /** Apply an incoming conversation_state broadcast. */
  function applyState(convState) {
    _state = convState || { active: false };
    _render();
  }

  // Client-side actions (send WS messages)
  function enterConversation(npcId, npcName) {
    _env.sendWS({ type: 'conversation_enter', payload: { npc_id: npcId, npc_name: npcName } });
  }
  function exitConversation() {
    _env.sendWS({ type: 'conversation_exit', payload: {} });
  }
  function setTone(tone) {
    _env.sendWS({ type: 'conversation_set_tone', payload: { tone } });
  }
  function socialAction(action) {
    _env.sendWS({ type: 'conversation_social_action', payload: { action } });
  }
  function joinQueue() {
    _env.sendWS({ type: 'conversation_queue_join', payload: {} });
  }
  function leaveQueue() {
    _env.sendWS({ type: 'conversation_queue_leave', payload: {} });
  }
  function advanceQueue() {
    _env.sendWS({ type: 'conversation_queue_advance', payload: {} });
  }
  function setReactionCue(cue) {
    _env.sendWS({ type: 'conversation_reaction_set', payload: { reaction_cue: cue } });
  }

  // ── DOM helpers ─────────────────────────────────────────────────────────────

  function _ensureHud() {
    if (document.getElementById('conversation-hud')) return;
    const hud = document.createElement('div');
    hud.id = 'conversation-hud';
    hud.setAttribute('aria-live', 'polite');
    hud.setAttribute('aria-label', 'Conversation mode');
    document.body.appendChild(hud);
  }

  function _esc(str) {
    return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  function _render() {
    const hud = document.getElementById('conversation-hud');
    if (!hud) return;

    const cm = _state;
    if (!cm || !cm.active) {
      hud.classList.remove('conv-open');
      hud.innerHTML = '';
      return;
    }

    const role      = _env.getRole ? _env.getRole() : 'player';
    const userId    = _env.getUserId ? _env.getUserId() : '';
    const userName  = _env.getName ? _env.getName() : '';
    const isDM      = role === 'dm';

    const participants  = cm.participants  || {};
    const queue         = cm.speak_queue   || [];
    const myTone        = (participants[userId] || {}).tone || '';
    const inQueue       = queue.includes(userId);
    const reactionCue   = cm.reaction_cue || '';

    // Build participant tone list
    const partEntries = Object.values(participants);
    const partHtml = partEntries.length
      ? partEntries.map(p => {
          const t = TONES.find(t => t.value === p.tone);
          return `<span class="conv-part-chip" title="${_esc(p.name)}: ${_esc(p.tone)}">
            ${t ? t.icon : '⬜'} <span class="conv-part-name">${_esc(p.name)}</span>
          </span>`;
        }).join('')
      : '<span class="conv-no-part">No tones set yet</span>';

    // Build tone selector
    const toneHtml = TONES.map(t => `
      <button class="conv-tone-btn${myTone === t.value ? ' active' : ''}"
              title="${_esc(t.label)}"
              onclick="AppConversation.setTone('${t.value}')">
        ${t.icon} ${_esc(t.label)}
      </button>`).join('');

    // Build action buttons
    const actionHtml = ACTIONS.map(a => `
      <button class="conv-action-btn"
              title="${_esc(a.label)}"
              onclick="AppConversation.socialAction('${a.value}')">
        ${a.icon} ${_esc(a.label)}
      </button>`).join('');

    // Build speak queue display
    let queueHtml = '';
    if (queue.length) {
      const users = _env.getUsers ? _env.getUsers() : {};
      const names = queue.map(uid => {
        const u = users[uid];
        return u ? _esc(u.name) : _esc(uid);
      });
      queueHtml = `<div class="conv-queue-row">
        <span class="conv-queue-label">Queue:</span>
        ${names.map((n, i) => `<span class="conv-queue-chip${i === 0 ? ' first' : ''}">${n}</span>`).join('')}
        ${isDM && queue.length ? `<button class="conv-queue-advance" onclick="AppConversation.advanceQueue()">Give floor ▶</button>` : ''}
      </div>`;
    }

    // Build NPC reaction cue
    const cueHtml = (isDM || reactionCue) ? `
      <div class="conv-cue-row">
        <span class="conv-cue-label">NPC:</span>
        ${isDM
          ? `<input id="conv-reaction-input" class="conv-reaction-input"
                   value="${_esc(reactionCue)}"
                   maxlength="120"
                   placeholder="e.g. seems nervous, warming up…"
                   onchange="AppConversation.setReactionCue(this.value)"
                   onblur="AppConversation.setReactionCue(this.value)" />`
          : (reactionCue ? `<span class="conv-cue-text">${_esc(reactionCue)}</span>` : '')
        }
      </div>` : '';

    hud.innerHTML = `
      <div class="conv-header">
        <span class="conv-npc-icon">💬</span>
        <span class="conv-npc-name">${_esc(cm.npc_name)}</span>
        <span class="conv-scene-label">Social Scene</span>
        ${isDM ? `<button class="conv-exit-btn" title="End conversation" onclick="AppConversation.exitConversation()">✕ End Scene</button>` : ''}
      </div>

      ${cueHtml}

      <div class="conv-section-label">Your Approach</div>
      <div class="conv-tone-row">${toneHtml}</div>

      <div class="conv-section-label">Social Actions</div>
      <div class="conv-action-row">${actionHtml}</div>

      <div class="conv-participants-row">${partHtml}</div>

      ${queueHtml}

      <div class="conv-queue-controls">
        ${!inQueue
          ? `<button class="conv-queue-btn join" onclick="AppConversation.joinQueue()">✋ Request to Speak</button>`
          : `<button class="conv-queue-btn leave" onclick="AppConversation.leaveQueue()">↩ Withdraw</button>`
        }
      </div>
    `;

    hud.classList.add('conv-open');
  }

  // ── Export ───────────────────────────────────────────────────────────────────

  global.AppConversation = {
    init,
    applyState,
    enterConversation,
    exitConversation,
    setTone,
    socialAction,
    joinQueue,
    leaveQueue,
    advanceQueue,
    setReactionCue,
  };

})(window);
