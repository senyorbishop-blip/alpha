
(function(){
  function formatSignedSummaryValue(_env, value) {
    const n = parseInt(value, 10);
    if (Number.isNaN(n)) return '+0';
    return n >= 0 ? `+${n}` : `${n}`;
  }
  function formatShortDurationSeconds(_env, totalSeconds) {
    const sec = Math.max(0, Math.ceil(Number(totalSeconds || 0)));
    if (!sec) return '0s';
    if (sec >= 3600) return `${Math.ceil(sec / 3600)}h`;
    if (sec >= 60) return `${Math.ceil(sec / 60)}m`;
    return `${sec}s`;
  }
  function renderConditionStrip(env, token, containerId, options = {}) {
    const host = env.document.getElementById(containerId);
    if (!host) return;
    const conds = Array.isArray(token?.conditions) ? token.conditions : [];
    const timers = (token && typeof token.condition_timers === 'object' && token.condition_timers) ? token.condition_timers : {};
    const now = Date.now() / 1000;
    host.innerHTML = '';
    if (!conds.length) {
      host.style.display = options.showEmpty ? 'flex' : 'none';
      if (options.showEmpty) {
        const empty = env.document.createElement('span');
        empty.textContent = options.emptyText || 'No conditions';
        empty.style.cssText = 'font-size:0.6rem;color:rgba(255,255,255,0.45);padding:0.18rem 0.45rem;border:1px dashed rgba(255,255,255,0.12);border-radius:999px;';
        host.appendChild(empty);
      }
      return;
    }
    host.style.display = 'flex';
    conds.forEach(id => {
      const meta = env.CONDITIONS_MAP[id] || { icon: '•', name: id, color: '#8b949e' };
      const chip = env.document.createElement('span');
      const expiry = Number(timers[id] || 0);
      const remaining = expiry > now ? Math.max(0, expiry - now) : 0;
      chip.title = remaining ? `${meta.name} (${formatShortDurationSeconds(env, remaining)} left)` : meta.name;
      chip.style.cssText = [
        'display:inline-flex','align-items:center','gap:0.24rem','padding:0.18rem 0.42rem','border-radius:999px',
        `border:1px solid ${meta.color}66`,`background:${meta.color}18`,'font-size:0.58rem','line-height:1','color:#fff','white-space:nowrap'
      ].join(';');
      chip.innerHTML = `<span style="font-size:0.72rem;line-height:1;">${meta.icon}</span><span>${meta.name}${remaining ? ` · ${env.escapeHtml(formatShortDurationSeconds(env, remaining))}` : ''}</span>`;
      host.appendChild(chip);
    });
  }
  function refreshConditionSummaries(env) {
    const myTok = Object.values(env.tokens).find(t => t.owner_id === env.USER_ID) || Object.values(env._stagingTokens).find(t => t.owner_id === env.USER_ID);
    renderConditionStrip(env, myTok, 'char-condition-strip');
    const editTok = (env._teTokenId && (env.tokens[env._teTokenId] || env._stagingTokens[env._teTokenId])) || env.ctxToken || null;
    renderConditionStrip(env, editTok, 'te-condition-strip');
  }
  function buildHpSummaryValues(_env, curValue, maxValue, tempValue) {
    const curNum = parseInt(curValue, 10);
    const maxNum = parseInt(maxValue, 10);
    const tempNum = Math.max(0, parseInt(tempValue, 10) || 0);
    const hasCur = !Number.isNaN(curNum);
    const hasMax = !Number.isNaN(maxNum);
    return {
      hpText: `${hasCur ? curNum : '—'} / ${hasMax ? maxNum : '—'}`,
      tempText: `${tempNum}`,
      totalText: (hasCur || hasMax) ? `${hasCur ? curNum + tempNum : '—'} / ${hasMax ? maxNum + tempNum : '—'}` : '—'
    };
  }
  window.AppGameplayConditions = { formatSignedSummaryValue, formatShortDurationSeconds, renderConditionStrip, refreshConditionSummaries, buildHpSummaryValues };
})();
