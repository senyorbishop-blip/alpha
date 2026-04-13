(function(){
  function closeMenu(env) {
    env.document.getElementById('ctx-menu')?.classList.remove('open');
    env.setContextToken(null);
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function openTokenMenu(env, event, hit) {
    if (!event || !hit) {
      closeMenu(env);
      return;
    }
    env.setContextToken(hit);
    const document = env.document;
    const isDm = env.getRole() === 'dm';
    const isOwner = !!(hit && hit.owner_id && hit.owner_id === env.getUserId());
    const editEl = document.getElementById('ctx-edit-token');
    const editSep = document.getElementById('ctx-edit-sep');
    if (editEl) editEl.style.display = isDm ? 'flex' : 'none';
    if (editSep) editSep.style.display = isDm ? 'block' : 'none';

    const hideBtn = document.getElementById('ctx-toggle-hidden');
    if (hideBtn) {
      if (isDm) {
        hideBtn.style.display = 'flex';
        hideBtn.innerHTML = hit.hidden ? '<span>👁</span> Reveal to players' : '<span>🚫</span> Hide from players';
        hideBtn.style.color = hit.hidden ? '#2ecc71' : '#e74c3c';
      } else {
        hideBtn.style.display = 'none';
      }
    }

    const canAdjHp = !!(hit.maxHp && (isDm || isOwner));
    const hpBtn = document.getElementById('ctx-adjust-hp');
    const hpSep = document.getElementById('ctx-hp-sep');
    if (hpBtn) hpBtn.style.display = canAdjHp ? 'flex' : 'none';
    if (hpSep) hpSep.style.display = canAdjHp ? 'block' : 'none';

    const canCond = isDm || isOwner;
    const condBtn = document.getElementById('ctx-cond-btn');
    if (condBtn) condBtn.style.display = canCond ? 'flex' : 'none';

    const hasStagingContext = env.getCurrentPoi() !== null || env.getStagingTokenCount() > 0;
    const stagingBtn = document.getElementById('ctx-to-staging');
    if (stagingBtn) stagingBtn.style.display = hasStagingContext ? 'flex' : 'none';

    const menu = document.getElementById('ctx-menu');
    if (!menu) return;
    const viewportW = window.innerWidth || document.documentElement?.clientWidth || 0;
    const viewportH = window.innerHeight || document.documentElement?.clientHeight || 0;
    menu.classList.add('open');
    const rect = menu.getBoundingClientRect();
    const left = clamp(event.clientX, 8, Math.max(8, viewportW - rect.width - 8));
    const top = clamp(event.clientY, 8, Math.max(8, viewportH - rect.height - 8));
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }

  function handleGlobalClick(env, event) {
    const menu = env.document.getElementById('ctx-menu');
    if (!menu || !menu.classList.contains('open')) return;
    if (event && !menu.contains(event.target)) closeMenu(env);
  }

  window.AppUIContextMenu = {
    closeMenu,
    openTokenMenu,
    handleGlobalClick,
  };
})();
