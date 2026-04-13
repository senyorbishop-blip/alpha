/**
 * Parchment-style notification system for the D&D tabletop app.
 *
 * API:
 *   showToast(msg)                           — backward-compat bottom toast
 *   showCenterNotice(msg, tone, duration)    — backward-compat center notice
 *   showParchmentNotification(msg, opts)     — new stacking parchment card
 *     opts.variant : 'normal' | 'critical' | 'success' | 'info'  (default 'normal')
 *     opts.duration: ms  (default 4000)
 *     opts.title   : optional header text
 */
(function () {
  let centerNoticeTimer = null;

  /* ── Legacy toast (preserved) ── */
  function showToast(msg) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2500);
  }

  /* ── Legacy center notice (preserved) ── */
  function showCenterNotice(msg, tone, duration) {
    const box = document.getElementById('center-notice');
    const txt = document.getElementById('center-notice-text');
    if (!box || !txt) return;
    txt.textContent = msg || 'Notification';
    const themes = {
      info: ['rgba(72,193,181,0.42)', 'rgba(7,18,28,0.94)', '#dffdfa'],
      warn: ['rgba(255,196,92,0.42)', 'rgba(34,24,8,0.94)', '#ffe2a5'],
      blood: ['rgba(180,64,48,0.42)', 'rgba(34,10,10,0.94)', '#ffd2d2'],
    };
    const theme = themes[tone] || themes.info;
    box.style.borderColor = theme[0];
    box.style.background  = theme[1];
    box.style.color        = theme[2];
    box.style.display      = 'block';
    if (centerNoticeTimer) clearTimeout(centerNoticeTimer);
    centerNoticeTimer = setTimeout(() => {
      box.style.display = 'none';
    }, Math.max(1200, Number(duration || 2600)));
  }

  /* ── Parchment notification ── */
  const FLEUR_SVG = `<svg viewBox="0 0 32 32" width="18" height="18" xmlns="http://www.w3.org/2000/svg">` +
    `<path d="M16 2c-1.5 3-4 5-4 8 0 2 1.5 3.5 3 4-2.5.5-5 1-6.5 3.5-1 1.8-.5 3.5 1 4.5-1.8.2-3.5 1-4 3 ` +
    `-.3 1.5.5 3 2 3.5 1.8.8 3.5.2 4.5-1 .5 1.5 1.5 3 3.5 3.5h1c2 0 3-.8 3.5-2 .5 1.2 1.5 2 3.5 2h1c2-.5 ` +
    `3-2 3.5-3.5 1 1.2 2.7 1.8 4.5 1 1.5-.5 2.3-2 2-3.5-.5-2-2.2-2.8-4-3 1.5-1 2-2.7 1-4.5C29.5 15 27 ` +
    `14.5 24.5 14c1.5-.5 3-2 3-4 0-3-2.5-5-4-8-.8 2-2 4.2-3 5.5-.5.8-1 1.5-1 2.5 0 .8.2 1.5.5 2-1-.5-2.5` +
    `-.8-4-.8s-3 .3-4 .8c.3-.5.5-1.2.5-2 0-1-.5-1.7-1-2.5C10 6.2 8.8 4 8 2z" fill="currentColor"/>` +
    `</svg>`;

  function _ensureContainer() {
    let c = document.getElementById('parchment-notify-stack');
    if (!c) {
      c = document.createElement('div');
      c.id = 'parchment-notify-stack';
      document.body.appendChild(c);
    }
    return c;
  }

  function showParchmentNotification(msg, opts) {
    opts = opts || {};
    const variant  = opts.variant  || 'normal';
    const duration = Math.max(1200, Number(opts.duration || 4000));
    const title    = opts.title    || '';

    const container = _ensureContainer();
    const card = document.createElement('div');
    card.className = 'parchment-notif parchment-notif--' + variant;

    /* wax seal */
    const seal = document.createElement('span');
    seal.className = 'parchment-seal';
    seal.innerHTML = FLEUR_SVG;
    card.appendChild(seal);

    /* text body */
    const body = document.createElement('span');
    body.className = 'parchment-notif-body';
    if (title) {
      const h = document.createElement('strong');
      h.className = 'parchment-notif-title';
      h.textContent = title;
      body.appendChild(h);
    }
    const p = document.createElement('span');
    p.className = 'parchment-notif-msg';
    p.textContent = msg || '';
    body.appendChild(p);
    card.appendChild(body);

    container.appendChild(card);

    /* entrance — requestAnimationFrame lets the browser batch the initial style */
    requestAnimationFrame(() => { card.classList.add('parchment-notif--enter'); });

    /* exit */
    const timer = setTimeout(() => {
      card.classList.remove('parchment-notif--enter');
      card.classList.add('parchment-notif--exit');
      card.addEventListener('animationend', () => card.remove(), { once: true });
      /* safety fallback removal */
      setTimeout(() => { if (card.parentNode) card.remove(); }, 600);
    }, duration);

    /* allow manual dismiss */
    card.addEventListener('click', () => {
      clearTimeout(timer);
      card.classList.remove('parchment-notif--enter');
      card.classList.add('parchment-notif--exit');
      card.addEventListener('animationend', () => card.remove(), { once: true });
      setTimeout(() => { if (card.parentNode) card.remove(); }, 600);
    });
  }

  window.AppUINotifications = {
    showToast,
    showCenterNotice,
    showParchmentNotification,
  };
})();
