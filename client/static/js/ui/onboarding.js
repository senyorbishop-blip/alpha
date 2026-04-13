/**
 * client/static/js/ui/onboarding.js
 * Tavern Tabletop — Premium role-based onboarding walkthrough & contextual ? help system.
 *
 * Exposes: window.AppOnboarding
 *   .init(role, userId)       — call on page load; shows walkthrough if first visit
 *   .showWalkthrough(role)    — force-show the full walkthrough for a role
 *   .showHelp(topic)          — show a single contextual help card for a topic
 *   .markSeen(role, userId)   — mark walkthrough as seen (skip future auto-show)
 */
(function () {
  'use strict';

  // ── Storage keys ──────────────────────────────────────────────────────────
  function _seenKey(role, userId) {
    return 'tavern_onboard_seen_' + role + (userId ? '_' + userId : '');
  }
  function _hasSeen(role, userId) {
    try { return !!localStorage.getItem(_seenKey(role, userId)); } catch (_) { return false; }
  }
  function _markSeen(role, userId) {
    try { localStorage.setItem(_seenKey(role, userId), '1'); } catch (_) {}
  }

  // ── Step definitions per role ─────────────────────────────────────────────
  var STEPS = {
    dm: [
      {
        icon: '⚔',
        title: 'Welcome, Dungeon Master',
        body: 'You hold the fate of this world in your hands. As the DM you control the map, the monsters, the weather, the story — everything your players experience is shaped by you.',
        accent: '#d4a637',
        tip: 'Your role badge at the top-left shows <strong style="color:#d4a637">DM</strong> so everyone knows who runs the table.',
      },
      {
        icon: '🗺',
        title: 'Your Battlefield',
        body: 'The central canvas is your battle map. Use the <strong>Map Editor</strong> (🧱) on the left rail to paint terrain, place walls, add props, and sculpt points of interest. Enable <strong>Fog of War</strong> (🌫) to hide unexplored areas from players.',
        accent: '#00e5cc',
        tip: 'Scroll to zoom, right-click anywhere on the canvas for token & map options.',
      },
      {
        icon: '🪙',
        title: 'Tokens & Combat',
        body: 'Drop tokens onto the map with the <strong>Create Token</strong> panel (🪙). Right-click any token to adjust HP, apply conditions, open shops, or begin social scenes. The <strong>Combat Tracker</strong> in the right panel manages initiative automatically.',
        accent: '#e74c3c',
        tip: 'Drag tokens to move them. Hold Shift while clicking to multi-select.',
      },
      {
        icon: '🛡',
        title: 'Invite Your Players',
        body: 'Share session links from the <strong>Invite</strong> chips in the top bar. There\'s a <strong>Player link</strong> for adventurers and a <strong>Chat / Viewer link</strong> for spectators. Links are copied to clipboard with one click.',
        accent: '#2ecc71',
        tip: 'You can regenerate or copy invite links any time from the top bar during a session.',
      },
      {
        icon: '🧙',
        title: 'DM Power Tools',
        body: 'The left rail is now grouped by intent: <strong>prep tools</strong> (map/editor), <strong>live control tools</strong> (tokens/fog/combat), and <strong>storytelling tools</strong> (assistant/sound/journal). Use this order to reduce mid-session panel hopping.',
        accent: '#9b59b6',
        tip: 'When unsure mid-session, hit the panel <strong>?</strong> to open targeted help instead of leaving the map.',
      },
    ],
    player: [
      {
        icon: '🛡',
        title: 'Welcome, Adventurer',
        body: 'You\'ve entered the realm! This is your window into the adventure. Your Dungeon Master controls the world — your job is to explore it, fight in it, and shape its story through your character\'s choices.',
        accent: '#00e5cc',
        tip: 'Your role badge at the top-left shows <strong style="color:#00e5cc">PLAYER</strong>.',
      },
      {
        icon: '🧝',
        title: 'Your Character',
        body: 'Click the <strong>My Character</strong> button (🛡) on the left rail to open your character sheet. Choose your class, set your name, pick a token colour, and place yourself on the map. Your stats, HP and conditions are tracked automatically.',
        accent: '#00e5cc',
        tip: 'Once you place your token, the character flyout closes automatically so you can see the map.',
      },
      {
        icon: '🎲',
        title: 'Dice & Combat',
        body: 'Open the <strong>Dice Vault</strong> (🎲) on the left rail to roll any die — d4 through d100. During combat the DM will call for initiative; your rolls appear in the chat log and the combat tracker on the right.',
        accent: '#e74c3c',
        tip: 'Customise your dice colours and materials in the Dice Style section of the Dice Vault.',
      },
      {
        icon: '🎒',
        title: 'Inventory & Spells',
        body: 'Your core loop is simple: <strong>character + dice on the left</strong>, then <strong>inventory/spells/journal on the right</strong>. The DM can send you items, gold, and private handouts at any time.',
        accent: '#d4a637',
        tip: 'If a panel feels noisy, keep Party open for live status, use Journal for quest/canon, and open Inventory/Spells only when needed.',
      },
      {
        icon: '💬',
        title: 'Chat & Emotes',
        body: 'Use the <strong>chat bar</strong> at the bottom-right to talk to everyone at the table. You can also use <strong>token emotes</strong> — right-click your token to react with emotions, victory poses, and more that appear as animated bubbles above your character.',
        accent: '#9b59b6',
        tip: 'Press Enter to send a chat message quickly. All rolls are logged in chat automatically.',
      },
    ],
    viewer: [
      {
        icon: '👁',
        title: 'Welcome, Spectator',
        body: 'You\'re watching a live Dungeons & Dragons session. As a spectator you can see the battle map, follow the story in real-time, and enjoy every dice roll, dramatic moment, and plot twist as it unfolds.',
        accent: '#9b59b6',
        tip: 'Your role badge at the top-left shows <strong style="color:#9b59b6">VIEWER</strong>.',
      },
      {
        icon: '🗺',
        title: 'The Battle Map',
        body: 'The central canvas shows the current battle map. Tokens represent characters and monsters. HP bars appear when tokens take damage. The <strong>Fog of War</strong> may hide unexplored areas — only the DM and players can see beyond it.',
        accent: '#00e5cc',
        tip: 'Scroll to zoom in and out. The map updates live as the DM and players make changes.',
      },
      {
        icon: '💬',
        title: 'Chat & Reactions',
        body: 'Use <strong>chat</strong> to react live. You may also get lightweight viewer interactions, but only when the DM grants them for this scene.',
        accent: '#9b59b6',
        tip: 'If interaction controls are missing, that is expected until the DM grants viewer powers.',
      },
      {
        icon: '⚡',
        title: 'Powers, Permissions, and Cooldowns',
        body: 'Granted powers appear in the <strong>Party panel</strong> with charge counts, cooldown timing, and explicit approval state. If a power is pending, the UI keeps it queued until the DM approves or declines.',
        accent: '#d4a637',
        tip: 'If an action is blocked, the UI tells you why (permission, no target, or cooldown) so you can recover quickly.',
      },
    ],
  };

  // ── Help topic map (topic → step index for that role) ─────────────────────
  var HELP_TOPICS = {
    dm: {
      welcome:  0,
      map:      1,
      editor:   1,
      tokens:   2,
      combat:   2,
      invites:  3,
      tools:    4,
      sound:    4,
      journal:  4,
    },
    player: {
      welcome:   0,
      character: 1,
      dice:      2,
      combat:    2,
      inventory: 3,
      spells:    3,
      chat:      4,
      emotes:    4,
    },
    viewer: {
      welcome: 0,
      map:     1,
      chat:    2,
      emotes:  2,
      combat:  3,
      permissions: 3,
      powers: 3,
    },
  };

  // ── Role accent colours ───────────────────────────────────────────────────
  var ROLE_ACCENT = { dm: '#d4a637', player: '#00e5cc', viewer: '#9b59b6' };
  var ROLE_LABEL  = { dm: 'Dungeon Master', player: 'Player', viewer: 'Spectator' };

  // ── Internal state ────────────────────────────────────────────────────────
  var _role      = null;
  var _userId    = null;
  var _step      = 0;
  var _steps     = [];
  var _helpMode  = false; // true when showing a single help topic (no navigation)

  // ── DOM helpers ───────────────────────────────────────────────────────────
  function _el(id) { return document.getElementById(id); }

  // ── Inject modal HTML (once) ──────────────────────────────────────────────
  function _ensureModal() {
    if (_el('ob-overlay')) return;

    var html = [
      '<div id="ob-overlay" aria-modal="true" role="dialog" aria-labelledby="ob-title">',
      '  <div id="ob-modal">',
      '    <div id="ob-glow"></div>',
      '    <div id="ob-header">',
      '      <div id="ob-role-badge"></div>',
      '      <button id="ob-close-btn" title="Close" aria-label="Close walkthrough">&times;</button>',
      '    </div>',
      '    <div id="ob-dots"></div>',
      '    <div id="ob-body">',
      '      <div id="ob-icon"></div>',
      '      <h2 id="ob-title"></h2>',
      '      <p id="ob-text"></p>',
      '      <div id="ob-tip-box"><span id="ob-tip-icon">💡</span><span id="ob-tip"></span></div>',
      '    </div>',
      '    <div id="ob-footer">',
      '      <button id="ob-prev-btn">← Back</button>',
      '      <button id="ob-skip-btn">Skip Tour</button>',
      '      <button id="ob-next-btn">Next →</button>',
      '    </div>',
      '    <div id="ob-progress-bar"><div id="ob-progress-fill"></div></div>',
      '  </div>',
      '</div>',
    ].join('\n');

    var wrap = document.createElement('div');
    wrap.innerHTML = html;
    while (wrap.firstChild) document.body.appendChild(wrap.firstChild);

    _injectStyles();
    _bindEvents();
  }

  function _injectStyles() {
    if (_el('ob-styles')) return;
    var s = document.createElement('style');
    s.id = 'ob-styles';
    s.textContent = [
      /* Overlay */
      '#ob-overlay {',
      '  display:none; position:fixed; inset:0; z-index:20000;',
      '  background:rgba(0,0,0,0.82);',
      '  align-items:center; justify-content:center;',
      '  backdrop-filter:blur(3px);',
      '  animation:ob-fade-in 0.3s ease;',
      '}',
      '#ob-overlay.ob-open { display:flex; }',

      /* Modal card */
      '#ob-modal {',
      '  position:relative;',
      '  width:min(520px, 94vw);',
      '  background:linear-gradient(160deg,#16120a 0%,#1c1608 45%,#13100a 100%);',
      '  border:1px solid rgba(0,229,204,0.22);',
      '  border-radius:8px;',
      '  padding:2rem 2rem 1.4rem;',
      '  box-shadow:',
      '    0 0 0 2px #2a1e08,',
      '    0 0 0 4px #1a1208,',
      '    0 32px 80px rgba(0,0,0,0.9),',
      '    inset 0 1px 0 rgba(255,255,255,0.04);',
      '  overflow:hidden;',
      '  animation:ob-slide-up 0.35s cubic-bezier(0.34,1.3,0.64,1);',
      '}',

      /* Ambient glow behind card */
      '#ob-glow {',
      '  position:absolute; inset:-40px; pointer-events:none;',
      '  border-radius:50%;',
      '  background:radial-gradient(ellipse at 50% 50%, var(--ob-accent,rgba(0,229,204,0.12)) 0%, transparent 70%);',
      '  filter:blur(30px); z-index:0; transition:background 0.5s;',
      '}',

      /* Header row */
      '#ob-header {',
      '  display:flex; align-items:center; justify-content:space-between;',
      '  margin-bottom:1rem; position:relative; z-index:1;',
      '}',
      '#ob-role-badge {',
      '  font-family:"Cinzel",serif; font-size:0.6rem; letter-spacing:0.22em;',
      '  text-transform:uppercase; padding:0.22rem 0.7rem;',
      '  border-radius:2px; border:1px solid currentColor;',
      '  color:var(--ob-accent,#00e5cc);',
      '  background:rgba(0,0,0,0.35);',
      '}',
      '#ob-close-btn {',
      '  background:none; border:none; color:rgba(200,169,110,0.4);',
      '  font-size:1.4rem; cursor:pointer; line-height:1;',
      '  transition:color 0.15s; padding:0 0.2rem;',
      '}',
      '#ob-close-btn:hover { color:rgba(200,169,110,0.9); }',

      /* Step dots */
      '#ob-dots {',
      '  display:flex; gap:0.45rem; justify-content:center;',
      '  margin-bottom:1.5rem; position:relative; z-index:1;',
      '}',
      '.ob-dot {',
      '  width:7px; height:7px; border-radius:50%;',
      '  background:rgba(200,169,110,0.18);',
      '  border:1px solid rgba(200,169,110,0.25);',
      '  transition:all 0.3s; cursor:pointer;',
      '}',
      '.ob-dot.ob-dot-active {',
      '  background:var(--ob-accent,#00e5cc);',
      '  border-color:var(--ob-accent,#00e5cc);',
      '  box-shadow:0 0 8px var(--ob-accent,#00e5cc);',
      '  transform:scale(1.25);',
      '}',
      '.ob-dot.ob-dot-done {',
      '  background:rgba(0,229,204,0.35);',
      '  border-color:rgba(0,229,204,0.4);',
      '}',

      /* Body */
      '#ob-body { text-align:center; position:relative; z-index:1; }',
      '#ob-icon {',
      '  font-size:3rem; line-height:1; margin-bottom:0.6rem;',
      '  filter:drop-shadow(0 0 12px var(--ob-accent,rgba(0,229,204,0.5)));',
      '  animation:ob-icon-pop 0.4s cubic-bezier(0.34,1.5,0.64,1);',
      '}',
      '#ob-title {',
      '  font-family:"Cinzel",serif; font-size:1.25rem; font-weight:700;',
      '  color:var(--ob-accent,#00e5cc);',
      '  text-shadow:0 0 20px var(--ob-accent-glow,rgba(0,229,204,0.3));',
      '  margin-bottom:0.75rem; letter-spacing:0.04em;',
      '}',
      '#ob-text {',
      '  font-family:"Crimson Pro",Georgia,serif; font-size:1rem;',
      '  color:rgba(232,220,200,0.88); line-height:1.65;',
      '  margin-bottom:1rem;',
      '}',
      '#ob-tip-box {',
      '  display:flex; align-items:flex-start; gap:0.5rem;',
      '  background:rgba(0,229,204,0.06); border:1px solid rgba(0,229,204,0.15);',
      '  border-radius:4px; padding:0.6rem 0.8rem; text-align:left;',
      '  font-family:"Crimson Pro",Georgia,serif; font-size:0.88rem;',
      '  color:rgba(200,169,110,0.75); line-height:1.5;',
      '}',
      '#ob-tip-icon { flex-shrink:0; font-size:0.9rem; margin-top:0.05rem; }',

      /* Footer */
      '#ob-footer {',
      '  display:flex; gap:0.6rem; margin-top:1.4rem;',
      '  align-items:center; position:relative; z-index:1;',
      '}',
      '#ob-prev-btn, #ob-next-btn {',
      '  flex:1; padding:0.6rem 0.8rem;',
      '  font-family:"Cinzel",serif; font-size:0.62rem;',
      '  letter-spacing:0.15em; text-transform:uppercase; cursor:pointer;',
      '  border-radius:3px; transition:all 0.2s; border:none;',
      '}',
      '#ob-next-btn {',
      '  background:linear-gradient(135deg,var(--ob-accent,#00e5cc) 0%,var(--ob-accent-dim,#008f80) 100%);',
      '  color:#001a17; font-weight:700;',
      '  box-shadow:0 2px 8px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.15);',
      '}',
      '#ob-next-btn:hover {',
      '  filter:brightness(1.12);',
      '  box-shadow:0 4px 16px rgba(0,229,204,0.35);',
      '  transform:translateY(-1px);',
      '}',
      '#ob-prev-btn {',
      '  background:linear-gradient(135deg,#3d2c10,#2a1e08);',
      '  color:rgba(200,169,110,0.7);',
      '  border:1px solid rgba(92,63,24,0.5);',
      '}',
      '#ob-prev-btn:hover { color:rgba(200,169,110,1); filter:brightness(1.1); }',
      '#ob-prev-btn:disabled { opacity:0.3; cursor:default; }',
      '#ob-skip-btn {',
      '  background:none; border:none;',
      '  color:rgba(200,169,110,0.35);',
      '  font-family:"Cinzel",serif; font-size:0.55rem;',
      '  letter-spacing:0.1em; text-transform:uppercase;',
      '  cursor:pointer; transition:color 0.15s; white-space:nowrap; padding:0.4rem;',
      '}',
      '#ob-skip-btn:hover { color:rgba(200,169,110,0.65); }',

      /* Progress bar */
      '#ob-progress-bar {',
      '  position:absolute; bottom:0; left:0; right:0; height:2px;',
      '  background:rgba(255,255,255,0.05);',
      '}',
      '#ob-progress-fill {',
      '  height:100%;',
      '  background:var(--ob-accent,#00e5cc);',
      '  transition:width 0.4s ease;',
      '  box-shadow:0 0 6px var(--ob-accent,#00e5cc);',
      '}',

      /* Step-change animation for body */
      '.ob-step-enter {',
      '  animation:ob-step-in 0.28s ease forwards;',
      '}',

      /* ? Help button */
      '.ob-help-btn {',
      '  display:inline-flex; align-items:center; justify-content:center;',
      '  width:16px; height:16px; border-radius:50%;',
      '  background:rgba(0,229,204,0.08); border:1px solid rgba(0,229,204,0.3);',
      '  color:rgba(0,229,204,0.65); font-size:0.6rem; font-family:"Cinzel",serif;',
      '  cursor:pointer; vertical-align:middle; margin-left:5px;',
      '  transition:all 0.15s; line-height:1; flex-shrink:0;',
      '  font-weight:700;',
      '}',
      '.ob-help-btn:hover {',
      '  background:rgba(0,229,204,0.18); border-color:rgba(0,229,204,0.7);',
      '  color:#00e5cc; box-shadow:0 0 6px rgba(0,229,204,0.35);',
      '}',

      /* Keyframes */
      '@keyframes ob-fade-in { from{opacity:0} to{opacity:1} }',
      '@keyframes ob-slide-up {',
      '  from { opacity:0; transform:translateY(24px) scale(0.96); }',
      '  to   { opacity:1; transform:translateY(0) scale(1); }',
      '}',
      '@keyframes ob-icon-pop {',
      '  from { transform:scale(0.4) rotate(-15deg); opacity:0; }',
      '  to   { transform:scale(1) rotate(0deg); opacity:1; }',
      '}',
      '@keyframes ob-step-in {',
      '  from { opacity:0; transform:translateX(14px); }',
      '  to   { opacity:1; transform:translateX(0); }',
      '}',
    ].join('\n');
    document.head.appendChild(s);
  }

  function _bindEvents() {
    var overlay = _el('ob-overlay');
    var closeBtn = _el('ob-close-btn');
    var prevBtn  = _el('ob-prev-btn');
    var nextBtn  = _el('ob-next-btn');
    var skipBtn  = _el('ob-skip-btn');

    closeBtn.addEventListener('click', _closeModal);
    skipBtn.addEventListener('click', function () { _markSeen(_role, _userId); _closeModal(); });
    prevBtn.addEventListener('click', function () { if (_step > 0) _goTo(_step - 1); });
    nextBtn.addEventListener('click', function () {
      if (_helpMode) { _closeModal(); return; }
      if (_step < _steps.length - 1) {
        _goTo(_step + 1);
      } else {
        _markSeen(_role, _userId);
        _closeModal();
      }
    });

    // Click backdrop to close
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) { _markSeen(_role, _userId); _closeModal(); }
    });

    // Keyboard nav
    document.addEventListener('keydown', function (e) {
      if (!overlay.classList.contains('ob-open')) return;
      if (e.key === 'Escape') { _markSeen(_role, _userId); _closeModal(); }
      if (e.key === 'ArrowRight' && !_helpMode && _step < _steps.length - 1) _goTo(_step + 1);
      if (e.key === 'ArrowLeft' && !_helpMode && _step > 0) _goTo(_step - 1);
    });
  }

  // ── Render a step ─────────────────────────────────────────────────────────
  function _goTo(index) {
    _step = Math.max(0, Math.min(index, _steps.length - 1));
    var data = _steps[_step];
    var accent = data.accent || ROLE_ACCENT[_role] || '#00e5cc';

    // CSS custom prop for accent threading through styles
    var modal = _el('ob-modal');
    modal.style.setProperty('--ob-accent', accent);
    modal.style.setProperty('--ob-accent-dim', _dimColor(accent));
    modal.style.setProperty('--ob-accent-glow', _glowColor(accent));

    // Glow
    _el('ob-glow').style.background = 'radial-gradient(ellipse at 50% 50%,' + _glowColor(accent) + ' 0%,transparent 70%)';

    // Icon (re-trigger animation)
    var iconEl = _el('ob-icon');
    iconEl.style.animation = 'none';
    iconEl.offsetHeight; // reflow
    iconEl.style.animation = '';
    iconEl.textContent = data.icon || '⚔';

    // Text (with step-enter animation)
    var body = _el('ob-body');
    body.classList.remove('ob-step-enter');
    body.offsetHeight;
    body.classList.add('ob-step-enter');

    _el('ob-title').textContent = data.title;
    _el('ob-text').innerHTML = data.body;
    _el('ob-tip').innerHTML = data.tip || '';
    _el('ob-tip-box').style.display = data.tip ? 'flex' : 'none';

    // Dots
    _renderDots();

    // Footer buttons
    var prevBtn = _el('ob-prev-btn');
    var nextBtn = _el('ob-next-btn');
    var skipBtn = _el('ob-skip-btn');

    if (_helpMode) {
      prevBtn.style.display = 'none';
      skipBtn.style.display = 'none';
      nextBtn.textContent   = 'Got It ✓';
    } else {
      prevBtn.style.display = '';
      skipBtn.style.display = '';
      prevBtn.disabled = (_step === 0);
      var isLast = (_step === _steps.length - 1);
      nextBtn.textContent = isLast ? 'Begin Adventure ⚔' : 'Next →';
    }

    // Progress bar
    var pct = _steps.length > 1 ? ((_step + 1) / _steps.length * 100) : 100;
    _el('ob-progress-fill').style.width = pct + '%';
    _el('ob-progress-fill').style.background = accent;
    _el('ob-progress-fill').style.boxShadow  = '0 0 6px ' + accent;
  }

  function _renderDots() {
    var container = _el('ob-dots');
    if (_helpMode || _steps.length <= 1) { container.innerHTML = ''; return; }
    var html = '';
    for (var i = 0; i < _steps.length; i++) {
      var cls = 'ob-dot';
      if (i === _step) cls += ' ob-dot-active';
      else if (i < _step) cls += ' ob-dot-done';
      html += '<span class="' + cls + '" data-step="' + i + '" title="Step ' + (i+1) + '"></span>';
    }
    container.innerHTML = html;
    container.querySelectorAll('.ob-dot').forEach(function (dot) {
      dot.addEventListener('click', function () { _goTo(parseInt(dot.dataset.step, 10)); });
    });
  }

  // ── Open / Close ──────────────────────────────────────────────────────────
  function _openModal() {
    _ensureModal();
    var overlay = _el('ob-overlay');
    overlay.classList.add('ob-open');

    // Role badge
    var badge = _el('ob-role-badge');
    badge.textContent = ROLE_LABEL[_role] || _role;
    badge.style.color = ROLE_ACCENT[_role] || '#00e5cc';
    badge.style.borderColor = ROLE_ACCENT[_role] || '#00e5cc';

    _goTo(_step);
  }

  function _closeModal() {
    var overlay = _el('ob-overlay');
    if (overlay) overlay.classList.remove('ob-open');
    _helpMode = false;
  }

  // ── Colour helpers ────────────────────────────────────────────────────────
  function _dimColor(hex) {
    // darken hex ~40% for button gradient end
    var n = parseInt(hex.replace('#',''), 16);
    var r = Math.floor(((n>>16)&0xff)*0.55);
    var g = Math.floor(((n>>8)&0xff)*0.55);
    var b = Math.floor((n&0xff)*0.55);
    return '#' + [r,g,b].map(function(v){ return v.toString(16).padStart(2,'0'); }).join('');
  }
  function _glowColor(hex) {
    return hex.replace('#','rgba(').replace(/(..)(..)(..)/, function(_,r,g,b){
      return parseInt(r,16)+','+parseInt(g,16)+','+parseInt(b,16);
    }) + ',0.18)';
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /**
   * init(role, userId) — call on page load.
   * Shows the walkthrough automatically if first visit.
   */
  function init(role, userId) {
    _role   = role   || 'viewer';
    _userId = userId || null;
    _steps  = (STEPS[_role] || STEPS.viewer).slice();

    if (!_hasSeen(_role, _userId)) {
      // Small delay so the page fully renders before overlay appears
      setTimeout(function () {
        _step     = 0;
        _helpMode = false;
        _openModal();
      }, 900);
    }
  }

  /**
   * showWalkthrough(role) — force-open the full walkthrough (e.g. from ? button in header).
   */
  function showWalkthrough(role) {
    _role   = role || _role || 'viewer';
    _userId = _userId;
    _steps  = (STEPS[_role] || STEPS.viewer).slice();
    _step     = 0;
    _helpMode = false;
    _openModal();
  }

  /**
   * showHelp(topic) — show a single contextual help step.
   * topic is a string like 'dice', 'map', 'invites', etc.
   */
  function showHelp(topic) {
    var r    = _role || 'viewer';
    var map  = HELP_TOPICS[r] || {};
    var idx  = (topic in map) ? map[topic] : 0;
    _steps   = (STEPS[r] || STEPS.viewer).slice();
    _step    = idx;
    _helpMode = true;
    _openModal();
  }

  /**
   * markSeen(role, userId) — externally mark as seen.
   */
  function markSeen(role, userId) {
    _markSeen(role || _role, userId || _userId);
  }

  /**
   * createHelpButton(topic, label) — returns a <button> element.
   * Use this to inject ? buttons next to panel headers.
   */
  function createHelpButton(topic, label) {
    var btn = document.createElement('button');
    btn.className = 'ob-help-btn';
    btn.title = label || 'Help';
    btn.setAttribute('aria-label', label || 'Help');
    btn.textContent = '?';
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      showHelp(topic);
    });
    return btn;
  }

  window.AppOnboarding = {
    init:             init,
    showWalkthrough:  showWalkthrough,
    showHelp:         showHelp,
    markSeen:         markSeen,
    createHelpButton: createHelpButton,
    STEPS:            STEPS,
  };

})();
