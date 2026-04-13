(function(global){
  'use strict';

  function isPresenceLogEntry(entry) {
    if (!entry || entry.type !== 'system' || !entry.message) return false;
    const msg = String(entry.message).toLowerCase();
    return msg.includes(' joined as ') || msg.includes(' connected.') || msg.includes(' disconnected.') || msg.includes(' returned to the session.');
  }
  function addLogEntry(env, entry) {
    if (isPresenceLogEntry(entry)) return;
    if (!entry || entry.type !== 'chat') return;
    const feed = env.document.getElementById('log-feed');
    if (!feed || !entry) return;
    const div = env.document.createElement('div');
    const channel = entry.channel || '';
    div.className = `log-entry chat${channel === 'viewers' ? ' channel-viewers' : channel === 'whisper' ? ' channel-whisper' : ''}`;
    let channelTag = '';
    if (channel === 'viewers') channelTag = '<span style="margin-left:0.35rem;font-size:0.62rem;color:rgba(155,89,182,0.85);">👁</span>';
    else if (channel === 'whisper') channelTag = '<span style="margin-left:0.35rem;font-size:0.62rem;color:var(--parchment-dim);">🤫</span>';
    const whisperTag = entry.private ? '<span style="margin-left:0.35rem;font-size:0.62rem;color:#f0c674;">(private)</span>' : '';
    div.innerHTML = `<span class="log-user ${env.escHtml(entry.role || '')}">${env.escHtml(entry.user || '')}:</span> ${env.escHtml(entry.message || '')}${channelTag}${whisperTag}`;
    feed.appendChild(div);
    feed.scrollTop = feed.scrollHeight;
    env.bumpLogBadge();
  }
  global.AppUIChatLog = { isPresenceLogEntry, addLogEntry };
})(window);
