/**
 * client/static/js/ui/onboarding.js
 * Tavern Tabletop — Premium role-based onboarding walkthrough & contextual ? help system.
 *
 * Exposes: window.AppOnboarding
 *   .init(role, userId)            — call on page load; shows walkthrough if first visit
 *   .showWalkthrough(role)         — force-show the full walkthrough for a role
 *   .showHelp(topic)               — show a single contextual help card for a topic
 *   .showHelpHub(role)             — show the Help Hub topic selector
 *   .showCombatHint(message, dur)  — show a non-blocking transient inline hint
 *   .markSeen(role, userId)        — mark walkthrough as seen (skip future auto-show)
 *   .createHelpButton(topic, lbl)  — returns a ? <button> element
 *   .createHelpHubButton(role,lbl) — returns a Help Hub <button> element
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
        targetSelector: '#topbar-role',
        placement: 'bottom',
      },
      {
        icon: '🗺',
        title: 'Your Battlefield',
        body: 'The central canvas is your battle map. Use the <strong>Map Editor</strong> (🧱) on the left rail to paint terrain, place walls, add props, and sculpt points of interest. Enable <strong>Fog of War</strong> (🌫) to hide unexplored areas from players.',
        accent: '#00e5cc',
        tip: 'Scroll to zoom, right-click anywhere on the canvas for token & map options.',
        targetSelector: '[data-help="dm-map-editor"]',
        fallbackSelector: '#rail-editor-btn',
        placement: 'right',
      },
      {
        icon: '🪙',
        title: 'Tokens & Combat',
        body: 'Drop tokens onto the map with the <strong>Create Token</strong> panel (🪙). Right-click any token to adjust HP, apply conditions, open shops, or begin social scenes. The <strong>Combat Tracker</strong> in the right panel manages initiative automatically.',
        accent: '#e74c3c',
        tip: 'Drag tokens to move them. Hold Shift while clicking to multi-select.',
        targetSelector: '[data-help="dm-token-tools"]',
        fallbackSelector: '#rail-token-btn',
        placement: 'right',
      },
      {
        icon: '🛡',
        title: 'Invite Your Players',
        body: 'Share session links from the <strong>Invite</strong> chips in the top bar. There\'s a <strong>Player link</strong> for adventurers and a <strong>Chat / Viewer link</strong> for spectators. Links are copied to clipboard with one click.',
        accent: '#2ecc71',
        tip: 'You can regenerate or copy invite links any time from the top bar during a session.',
        targetSelector: '#invite-codes',
        placement: 'bottom',
      },
      {
        icon: '🧙',
        title: 'DM Power Tools',
        body: 'The left rail is now grouped by intent: <strong>prep tools</strong> (map/editor), <strong>live control tools</strong> (tokens/fog/combat), and <strong>storytelling tools</strong> (assistant/sound/journal). Use this order to reduce mid-session panel hopping.',
        accent: '#9b59b6',
        tip: 'When unsure mid-session, hit the panel <strong>?</strong> to open targeted help instead of leaving the map.',
        targetSelector: '#topbar-help-btn',
        placement: 'bottom',
      },
    ],
    player: [
      {
        icon: '🛡',
        title: 'Welcome, Adventurer',
        body: 'You\'ve entered the realm! This is your window into the adventure. Your Dungeon Master controls the world — your job is to explore it, fight in it, and shape its story through your character\'s choices.',
        accent: '#00e5cc',
        tip: 'Your role badge at the top-left shows <strong style="color:#00e5cc">PLAYER</strong>.',
        targetSelector: '#topbar-role',
        placement: 'bottom',
      },
      {
        icon: '🧝',
        title: 'Your Character',
        body: 'Click the <strong>My Character</strong> button (🛡) on the left rail to open your character sheet. Choose your class, set your name, pick a token colour, and place yourself on the map. Your stats, HP and conditions are tracked automatically.',
        accent: '#00e5cc',
        tip: 'Once you place your token, the character flyout closes automatically so you can see the map.',
        targetSelector: '[data-help="my-character"]',
        fallbackSelector: '#rail-char-btn',
        placement: 'right',
      },
      {
        icon: '🎲',
        title: 'Dice & Combat',
        body: 'Open the <strong>Dice Vault</strong> (🎲) on the left rail to roll any die — d4 through d100. During combat the DM will call for initiative; your rolls appear in the chat log and the combat tracker on the right.',
        accent: '#e74c3c',
        tip: 'Customise your dice colours and materials in the Dice Style section of the Dice Vault.',
        targetSelector: '[data-help="dice-quick-actions"]',
        fallbackSelector: '#rail-dice-btn',
        placement: 'right',
      },
      {
        icon: '🎒',
        title: 'Inventory & Spells',
        body: 'Your core loop is simple: <strong>character + dice on the left</strong>, then <strong>inventory/spells/journal on the right</strong>. The DM can send you items, gold, and private handouts at any time.',
        accent: '#d4a637',
        tip: 'If a panel feels noisy, keep Party open for live status, use Journal for quest/canon, and open Inventory/Spells only when needed.',
        targetSelector: '[data-help="inventory-spells"]',
        fallbackSelector: '#rtab-inventory',
        placement: 'left',
      },
      {
        icon: '💬',
        title: 'Chat & Emotes',
        body: 'Use the <strong>chat bar</strong> at the bottom-right to talk to everyone at the table. You can also use <strong>token emotes</strong> — right-click your token to react with emotions, victory poses, and more that appear as animated bubbles above your character.',
        accent: '#9b59b6',
        tip: 'Press Enter to send a chat message quickly. All rolls are logged in chat automatically.',
        targetSelector: '#rtab-log',
        placement: 'left',
      },
    ],
    viewer: [
      {
        icon: '👁',
        title: 'Welcome, Spectator',
        body: 'You\'re watching a live Dungeons & Dragons session. As a spectator you can see the battle map, follow the story in real-time, and enjoy every dice roll, dramatic moment, and plot twist as it unfolds.',
        accent: '#9b59b6',
        tip: 'Your role badge at the top-left shows <strong style="color:#9b59b6">VIEWER</strong>.',
        targetSelector: '#topbar-role',
        placement: 'bottom',
      },
      {
        icon: '🗺',
        title: 'The Battle Map',
        body: 'The central canvas shows the current battle map. Tokens represent characters and monsters. HP bars appear when tokens take damage. The <strong>Fog of War</strong> may hide unexplored areas — only the DM and players can see beyond it.',
        accent: '#00e5cc',
        tip: 'Scroll to zoom in and out. The map updates live as the DM and players make changes.',
        targetSelector: '#map',
        fallbackSelector: 'canvas',
        placement: 'center',
      },
      {
        icon: '💬',
        title: 'Chat & Reactions',
        body: 'Use <strong>chat</strong> to react live. You may also get lightweight viewer interactions, but only when the DM grants them for this scene.',
        accent: '#9b59b6',
        tip: 'If interaction controls are missing, that is expected until the DM grants viewer powers.',
        targetSelector: '#rtab-log',
        placement: 'left',
      },
      {
        icon: '⚡',
        title: 'Powers, Permissions, and Cooldowns',
        body: 'Granted powers appear in the <strong>Party panel</strong> with charge counts, cooldown timing, and explicit approval state. If a power is pending, the UI keeps it queued until the DM approves or declines.',
        accent: '#d4a637',
        tip: 'If an action is blocked, the UI tells you why (permission, no target, or cooldown) so you can recover quickly.',
        targetSelector: '[data-help="viewer-powers"]',
        fallbackSelector: '#rtab-party',
        placement: 'left',
      },
    ],
  };

  // ── Specialized guide definitions (independent of role tour) ─────────────
  var GUIDE_STEPS = {
    new_player: [
      {
        icon: '🛡',
        title: 'New Player: Getting Started',
        body: 'Welcome to Tavern Tabletop! Your first step is to open <strong>My Character</strong> on the left rail, fill in your name and class, then place your token on the map.',
        accent: '#00e5cc',
        tip: 'The DM can also place your token for you — just let them know your character\'s name.',
        targetSelector: '[data-help="my-character"]',
        fallbackSelector: '#rail-char-btn',
        placement: 'right',
      },
      {
        icon: '🎲',
        title: 'Rolls & Dice',
        body: 'All dice rolls happen through the <strong>Dice Vault</strong> (🎲) on the left. Click the die you need, or type a custom roll like <code style="color:#00e5cc">2d6+3</code>. Results appear in the chat log.',
        accent: '#e74c3c',
        tip: 'Your DM may ask for a specific roll (Perception, Athletics, etc.) — just find that die and roll it!',
        targetSelector: '[data-help="dice-quick-actions"]',
        fallbackSelector: '#rail-dice-btn',
        placement: 'right',
      },
      {
        icon: '⚡',
        title: 'Your First Combat',
        body: 'When combat starts, the <strong>Combat</strong> tab on the right will glow. Open it to see the initiative order. On your turn it will say <strong>YOUR TURN</strong>. Move your token, then pick an action — attack, spell, or ability.',
        accent: '#e74c3c',
        tip: 'End your turn with the "End Turn" button in the Combat panel. This passes to the next combatant.',
        targetSelector: '[data-help="combat-tab"]',
        fallbackSelector: '#rtab-combat',
        placement: 'left',
      },
      {
        icon: '🎒',
        title: 'Inventory & Items',
        body: 'Your gear lives in the <strong>Inventory</strong> tab on the right. The DM can drop items into your inventory. Equip weapons and armor here. Gold and currency are tracked at the bottom.',
        accent: '#d4a637',
        tip: 'Check the Journal & Quests flyout on the left for active quest objectives and canon notes.',
        targetSelector: '[data-help="inventory-spells"]',
        fallbackSelector: '#rtab-inventory',
        placement: 'left',
      },
    ],
    returning_player: [
      {
        icon: '⚔',
        title: 'Quick Refresh',
        body: 'Welcome back! Here\'s a fast refresher: your character sheet is in the left rail under <strong>My Character</strong>. The right panel holds Combat, Inventory, Spells, Party, and more via the tabs at the top.',
        accent: '#d4a637',
        tip: 'The topbar ? button always reopens this Help Hub whenever you need a refresher.',
      },
      {
        icon: '⚡',
        title: 'Combat Flow',
        body: 'Combat uses the right-panel <strong>Combat</strong> tab. On your turn: <strong>1)</strong> move your token, <strong>2)</strong> choose an action (attack, spell, ability), <strong>3)</strong> use a bonus action if available, then <strong>4)</strong> End Turn.',
        accent: '#e74c3c',
        tip: 'Dash doubles your movement. Disengage lets you leave melee without opportunity attacks.',
      },
      {
        icon: '🔮',
        title: 'Spell Slots & Casters',
        body: 'Open the <strong>Spells</strong> tab to see your prepared spells and remaining slots. Slots refresh on a long rest. Some classes use different resources (Pact Slots, Sorcery Points) — check your class features.',
        accent: '#9b59b6',
        tip: 'Concentration spells end early if you take damage and fail a Constitution save (DC 10 or half damage, whichever is higher).',
      },
    ],
    combat_guide: [
      {
        icon: '⚡',
        title: 'Combat Quick Guide',
        body: 'On your turn you have: one <strong>Action</strong>, one <strong>Bonus Action</strong>, one <strong>Reaction</strong> (off-turn), and movement up to your speed. Open the <strong>Combat</strong> tab to see the current initiative order.',
        accent: '#e74c3c',
        tip: 'You can split your movement — move, attack, then move again — as long as you don\'t exceed your total speed.',
      },
      {
        icon: '🎯',
        title: 'Attacking',
        body: 'In the Combat panel, click <strong>Select Target</strong> then <strong>Weapon Attack</strong> or <strong>Spell Attack</strong>. The DM will resolve the outcome. Attack rolls, damage, and saving throws are all logged in the chat.',
        accent: '#e74c3c',
        tip: 'Critical hits (natural 20) double the damage dice. Critical misses (natural 1) always miss.',
      },
      {
        icon: '🏃',
        title: 'Movement & Dash',
        body: 'Your movement is shown in the Combat panel: <strong>Speed / Used / Remaining</strong>. Use the <strong>Dash</strong> button to add your speed again as bonus movement. <strong>Disengage</strong> lets you leave an enemy\'s reach without provoking an opportunity attack.',
        accent: '#00e5cc',
        tip: 'Difficult terrain costs 2 ft of movement per 1 ft travelled. Toggle it in the Combat panel when your token enters difficult terrain.',
      },
      {
        icon: '🔚',
        title: 'Ending Your Turn',
        body: 'When you\'ve moved and acted, press <strong>End Turn</strong> in the Combat panel. If you forget, the DM can advance the turn. Unused movement and bonus actions are lost — they don\'t carry over.',
        accent: '#d4a637',
        tip: 'Your reaction resets at the start of your next turn. Common reactions: Opportunity Attack, Shield spell, Counterspell.',
      },
    ],
    movement_guide: [
      {
        icon: '🏃',
        title: 'Movement in Combat',
        body: 'Each combatant gets movement equal to their speed each turn. Drag your token on the map to move. The Combat panel shows <strong>Speed / Used / Remaining ft</strong>.',
        accent: '#00e5cc',
        tip: 'You can move before and after your action, as long as you don\'t exceed your speed total.',
      },
      {
        icon: '⛰',
        title: 'Difficult Terrain',
        body: 'Moving through difficult terrain costs 2 ft per 1 ft of actual distance. Toggle <strong>Difficult Terrain</strong> in the Combat panel when your token moves into it. This halves your effective movement.',
        accent: '#d4a637',
        tip: 'Common difficult terrain: deep snow, rubble, shallow water, dense foliage, and magical slow effects.',
      },
      {
        icon: '🏃',
        title: 'Dash & Disengage',
        body: '<strong>Dash</strong> is an action that grants extra movement equal to your speed. <strong>Disengage</strong> is an action that lets you move away from enemies without triggering Opportunity Attacks.',
        accent: '#e74c3c',
        tip: 'Rogues can Dash or Disengage as a Bonus Action via Cunning Action. Monks can spend Focus to Dash or Disengage as a Bonus Action.',
      },
      {
        icon: '🚫',
        title: 'Movement Denied',
        body: 'Movement can be blocked for several reasons: not your turn, speed is 0, you have no movement left, or you\'re Restrained/Grappled. The combat panel will explain which applies. Use <strong>Dash</strong> if you need more range.',
        accent: '#e74c3c',
        tip: 'If you\'re grappled, try the Athletics/Acrobatics check to escape before moving. Ask your DM.',
      },
    ],
    spells_guide: [
      {
        icon: '🔮',
        title: 'Your Spell Panel',
        body: 'Click the <strong>Spells</strong> tab in the right-side panel to see all your prepared or known spells, organised by level. Each row shows cast time, range, save/attack info, and a 🎲 button for instant damage rolls right in the list.',
        accent: '#9b59b6',
        tip: 'Cantrips (level 0) are always available and never use a slot. They scale with your character level automatically.',
        highlight: '#rtab-spelllib',
      },
      {
        icon: '🕯',
        title: 'Spell Slots & Upcasting',
        body: 'Your remaining spell slots appear as pip trackers at the top of the Spells panel. Casting a leveled spell uses one pip. You can cast at a <em>higher</em> slot level to <strong>upcast</strong> — spells that scale show the extra damage inline next to the base formula.',
        accent: '#9b59b6',
        tip: 'Slots refresh on a Long Rest. Warlocks recover Pact Slots on a Short Rest. Slot pips turn grey as you use them.',
        highlight: '#rtab-pane-spelllib .cs-slots-row',
      },
      {
        icon: '🎯',
        title: 'Concentration',
        body: 'Concentration spells show a <strong>●</strong> dot next to their name. You can only concentrate on one spell at a time. Taking damage forces a Constitution save (DC 10 or half damage taken, whichever is higher) to keep it active.',
        accent: '#e74c3c',
        tip: 'Click any spell to read its full card — it will tell you if concentration is needed before you commit.',
        highlight: '#rtab-pane-spelllib',
      },
      {
        icon: '⚡',
        title: 'Bonus Action & Reaction Spells',
        body: 'The <strong>Time</strong> column uses short codes: <strong>1A</strong> = Action, <strong>BA</strong> = Bonus Action, <strong>R</strong> = Reaction. Bonus Action spells (like Healing Word, Misty Step) let you cast with your off-hand action — but if you do, only cantrips are available for your main Action that turn.',
        accent: '#d4a637',
        tip: 'Quicken Spell (Sorcerer Metamagic) converts any spell\'s casting time to a Bonus Action for 2 Sorcery Points.',
        highlight: '#rtab-pane-spelllib .cs-spell-time',
      },
    ],
    inventory_guide: [
      {
        icon: '🎒',
        title: 'Your Inventory',
        body: 'The <strong>Inventory</strong> tab shows your equipped items, backpack contents, currency, and attuned magic items. Equip weapons and armor by clicking them. Your AC and attack bonuses update automatically.',
        accent: '#d4a637',
        tip: 'Drag items to the Equipped section to equip them. Items must be in your Backpack first.',
      },
      {
        icon: '💰',
        title: 'Loot & Gold',
        body: 'When the DM awards loot, items appear in your Inventory automatically. Gold is tracked in the Currency section. You can split gold with the party by right-clicking a gold entry.',
        accent: '#d4a637',
        tip: 'Shops let you buy and sell items if the DM has set one up. Right-click a shop token to open it.',
      },
      {
        icon: '⚗',
        title: 'Attunement',
        body: 'Powerful magic items require <strong>Attunement</strong>. You can attune to a maximum of 3 items at once. Attuned items appear in the Attunement section of your Inventory. Spending a Short Rest while holding an item attunes you to it.',
        accent: '#9b59b6',
        tip: 'Unattune by spending another Short Rest. You lose the item\'s benefits immediately.',
      },
      {
        icon: '⚖',
        title: 'Encumbrance',
        body: 'Your carrying capacity is your Strength score × 15 lbs. Exceeding it makes you Encumbered (speed –10 ft). Going over 2× your capacity makes you Heavily Encumbered (speed –20 ft, disadvantage on attacks). Track your load in the Inventory tab.',
        accent: '#e74c3c',
        tip: 'Pack saddles and mounts can carry far more weight than you can. Consider distributing heavy gear.',
      },
    ],
    dm_controls_guide: [
      {
        icon: '🎮',
        title: 'DM Controls Overview',
        body: 'You have full control of the session. The left rail groups your tools: <strong>Map/Editor</strong> for terrain, <strong>Tokens/Fog/Combat</strong> for live play, and <strong>Assistant/Sound/Journal</strong> for storytelling.',
        accent: '#d4a637',
        tip: 'Use Live Mode vs Prep Mode (toggle at the top of the left rail) to dim non-relevant tool groups during play.',
        targetSelector: '#dm-mode-switch',
        placement: 'right',
      },
      {
        icon: '⚔',
        title: 'Starting & Running Combat',
        body: 'Open the <strong>Combat</strong> tab on the right. Click <strong>Start Combat</strong> to pull all tokens on the current map into initiative. Use <strong>Next</strong> to advance turns. Click individual initiative values to edit them.',
        accent: '#e74c3c',
        tip: 'Right-click any combatant entry to adjust HP, conditions, or remove them from the tracker without ending combat.',
        targetSelector: '[data-help="combat-tab"]',
        fallbackSelector: '#rtab-combat',
        placement: 'left',
      },
      {
        icon: '🌫',
        title: 'Fog of War',
        body: 'Use the <strong>Fog of War</strong> flyout on the left rail to paint fog, reveal areas, and manage vision. Player tokens with vision enabled automatically reveal the area around them when Fog of War is active.',
        accent: '#00e5cc',
        tip: 'Enable "Reveal on token move" to automatically uncover fog when players move their tokens.',
        targetSelector: '[data-help="dm-fog"]',
        fallbackSelector: '#rail-fog-btn',
        placement: 'right',
      },
      {
        icon: '🧙',
        title: 'AI DM Assistant',
        body: 'The <strong>AI DM Assistant</strong> helps you generate NPCs, encounter descriptions, loot tables, and story hooks on the fly. It is aware of your current session context and players.',
        accent: '#9b59b6',
        tip: 'Click Assist in the left rail and ask anything — "describe a tense tavern scene" or "generate a CR 5 monster with a weakness to fire".',
        targetSelector: '#rail-assistant-btn',
        placement: 'right',
      },
    ],
    viewer_powers_guide: [
      {
        icon: '👁',
        title: 'Viewer Powers',
        body: 'As a Spectator, the DM may grant you special powers to interact with the session — reaction emotes, lair actions, environmental effects, or even controlling a minor creature.',
        accent: '#9b59b6',
        tip: 'Granted powers appear in the Party panel with charge counts and cooldown timers.',
        targetSelector: '[data-help="viewer-powers"]',
        fallbackSelector: '#rtab-party',
        placement: 'left',
      },
      {
        icon: '⚡',
        title: 'Using Powers',
        body: 'When a power is available, its card will be active in the Party panel. Click it to use it. Some powers require DM approval — they enter a pending state until the DM confirms or declines.',
        accent: '#d4a637',
        tip: 'If a power is greyed out, it is either on cooldown, out of charges, or not yet approved. Hover for the reason.',
        targetSelector: '[data-help="viewer-powers"]',
        fallbackSelector: '#rtab-party',
        placement: 'left',
      },
      {
        icon: '💬',
        title: 'Chat & Presence',
        body: 'Your chat messages appear in the shared log visible to everyone. Use the Party tab to see which players are connected. Your presence is shown to the DM at all times.',
        accent: '#9b59b6',
        tip: 'Viewer reactions in chat are a great way to engage during dramatic moments.',
        targetSelector: '#rtab-log',
        placement: 'left',
      },
    ],
  };

  // ── Help Hub topic catalog (shown per role) ────────────────────────────────
  var HUB_TOPICS = {
    dm: [
      { key: 'dm_tour',        label: 'DM Tour',          icon: '⚔', guide: null, tour: true },
      { key: 'combat_guide',   label: 'Combat Guide',     icon: '⚡', guide: 'combat_guide', tour: false },
      { key: 'movement_guide', label: 'Movement Guide',   icon: '🏃', guide: 'movement_guide', tour: false },
      { key: 'dm_controls_guide', label: 'DM Controls',  icon: '🎮', guide: 'dm_controls_guide', tour: false },
      { key: 'spells_guide',   label: 'Spells Guide',     icon: '🔮', guide: 'spells_guide', tour: false },
      { key: 'inventory_guide',label: 'Inventory Guide',  icon: '🎒', guide: 'inventory_guide', tour: false },
    ],
    player: [
      { key: 'new_player',     label: 'New Player Tour',  icon: '🛡', guide: 'new_player', tour: false },
      { key: 'returning_player', label: 'Quick Refresh',  icon: '⚔', guide: 'returning_player', tour: false },
      { key: 'combat_guide',   label: 'Combat Quick Guide', icon: '⚡', guide: 'combat_guide', tour: false },
      { key: 'movement_guide', label: 'Movement Guide',   icon: '🏃', guide: 'movement_guide', tour: false },
      { key: 'spells_guide',   label: 'Spells Guide',     icon: '🔮', guide: 'spells_guide', tour: false },
      { key: 'inventory_guide',label: 'Inventory Guide',  icon: '🎒', guide: 'inventory_guide', tour: false },
    ],
    viewer: [
      { key: 'viewer_tour',    label: 'Viewer Tour',      icon: '👁', guide: null, tour: true },
      { key: 'viewer_powers_guide', label: 'Viewer Powers', icon: '⚡', guide: 'viewer_powers_guide', tour: false },
      { key: 'combat_guide',   label: 'Combat Guide',     icon: '⚡', guide: 'combat_guide', tour: false },
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
  var _hubMode   = false; // true when showing the hub selector

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
      '    <div id="ob-hub" style="display:none;"></div>',
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
      '  pointer-events:none;',
      '  backdrop-filter:blur(3px);',
      '  animation:ob-fade-in 0.3s ease;',
      '}',
      '#ob-overlay.ob-open { display:flex; }',
      '#ob-overlay.ob-targeted { align-items:flex-start; justify-content:flex-start; }',
      '#ob-overlay.ob-targeted #ob-modal { position:fixed; width:min(440px, 92vw); }',

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
      '  pointer-events:auto;',
      '  max-height:min(86vh, 720px);',
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

      /* Hub styles */
      '#ob-hub {',
      '  position:relative; z-index:1; margin-bottom:1rem;',
      '}',
      '.ob-hub-title {',
      '  font-family:"Cinzel",serif; font-size:1.1rem; font-weight:700;',
      '  color:rgba(180,220,215,0.9); text-align:center;',
      '  margin-bottom:0.6rem; letter-spacing:0.04em;',
      '}',
      '.ob-hub-subtitle {',
      '  font-family:"Crimson Pro",Georgia,serif; font-size:0.88rem;',
      '  color:rgba(232,220,200,0.6); text-align:center; margin-bottom:1rem;',
      '}',
      '.ob-hub-grid {',
      '  display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;',
      '}',
      '.ob-hub-card {',
      '  display:flex; align-items:center; gap:0.5rem;',
      '  padding:0.6rem 0.7rem; cursor:pointer; border-radius:4px;',
      '  border:1px solid rgba(0,229,204,0.1);',
      '  background:rgba(255,255,255,0.025);',
      '  transition:all 0.15s; font-family:"Cinzel",serif;',
      '}',
      '.ob-hub-card:hover {',
      '  border-color:rgba(0,229,204,0.38);',
      '  background:rgba(0,229,204,0.07);',
      '  box-shadow:0 0 6px rgba(0,229,204,0.14);',
      '}',
      '.ob-hub-card-icon { font-size:1.2rem; flex-shrink:0; }',
      '.ob-hub-card-label {',
      '  font-size:0.62rem; letter-spacing:0.08em;',
      '  text-transform:uppercase; color:rgba(210,185,140,0.82);',
      '}',

      /* Element highlight for guided steps */
      '.ob-highlight {',
      '  outline:2px solid rgba(0,210,185,0.7) !important;',
      '  outline-offset:3px !important;',
      '  border-radius:4px !important;',
      '  animation:ob-hl-pulse 1.4s ease-in-out 4 !important;',
      '  position:relative; z-index:9994;',
      '}',
      '@keyframes ob-hl-pulse {',
      '  0%,100%{outline-color:rgba(0,210,185,0.4);}',
      '  50%{outline-color:rgba(0,210,185,0.9);box-shadow:0 0 14px rgba(0,210,185,0.35);}',
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
      '@keyframes ob-ring-pulse {',
      '  0%,100% { box-shadow:0 0 0 3px rgba(0,229,204,0.18),0 0 16px rgba(0,229,204,0.32); }',
      '  50%     { box-shadow:0 0 0 7px rgba(0,229,204,0.08),0 0 28px rgba(0,229,204,0.55); }',
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
    prevBtn.addEventListener('click', function () {
      if (_hubMode) return;
      if (_step > 0) _goTo(_step - 1);
    });
    nextBtn.addEventListener('click', function () {
      if (_hubMode) { _closeModal(); return; }
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
      if (_hubMode) return;
      if (e.key === 'ArrowRight' && !_helpMode && _step < _steps.length - 1) _goTo(_step + 1);
      if (e.key === 'ArrowLeft' && !_helpMode && _step > 0) _goTo(_step - 1);
    });
  }

  // ── Render hub mode ────────────────────────────────────────────────────────
  function _renderHub() {
    _ensureModal();
    var r = _role || 'viewer';
    var accent = ROLE_ACCENT[r] || '#00e5cc';
    var topics = HUB_TOPICS[r] || HUB_TOPICS.viewer;
    var modal = _el('ob-modal');
    modal.style.setProperty('--ob-accent', accent);
    modal.style.setProperty('--ob-accent-dim', _dimColor(accent));
    modal.style.setProperty('--ob-accent-glow', _glowColor(accent));
    // Hub mode uses a very dim glow so the modal background stays dark and readable
    _el('ob-glow').style.background = 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.05) 0%, transparent 70%)';

    // Hide step UI, show hub
    _el('ob-dots').innerHTML = '';
    _el('ob-body').style.display = 'none';
    _el('ob-footer').style.display = 'none';
    var hub = _el('ob-hub');
    hub.style.display = 'block';

    var cards = topics.map(function (topic) {
      return '<button class="ob-hub-card" data-hub-key="' + topic.key + '">' +
        '<span class="ob-hub-card-icon">' + topic.icon + '</span>' +
        '<span class="ob-hub-card-label">' + topic.label + '</span>' +
        '</button>';
    }).join('');

    hub.innerHTML = '<div class="ob-hub-title">Help Hub</div>' +
      '<div class="ob-hub-subtitle">Choose a guide or tour for ' + (ROLE_LABEL[r] || r) + '</div>' +
      '<div class="ob-hub-grid">' + cards + '</div>';

    hub.querySelectorAll('.ob-hub-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var key = card.getAttribute('data-hub-key');
        var topic = topics.find(function (t) { return t.key === key; });
        if (!topic) return;
        if (topic.tour) {
          _closeModal();
          setTimeout(function () { showWalkthrough(_role); }, 80);
        } else if (topic.guide && GUIDE_STEPS[topic.guide]) {
          _closeModal();
          setTimeout(function () { _showGuide(topic.guide); }, 80);
        }
      });
    });

    // Badge
    var badge = _el('ob-role-badge');
    badge.textContent = ROLE_LABEL[r] || r;
    badge.style.color = accent;
    badge.style.borderColor = accent;
  }

  // ── Show a named guide (GUIDE_STEPS entry) ────────────────────────────────
  function _showGuide(guideKey) {
    var steps = GUIDE_STEPS[guideKey];
    if (!steps || !steps.length) return;
    _steps    = steps.slice();
    _step     = 0;
    _helpMode = false;
    _hubMode  = false;
    _openModal();
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

    // Make sure non-hub UI is visible
    _el('ob-body').style.display = '';
    _el('ob-footer').style.display = '';
    _el('ob-hub').style.display = 'none';

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

    // Highlight the relevant UI element for this step. Legacy `highlight` is still
    // honored as an alias for the newer targetSelector field.
    _applyStepTarget(data);

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
      nextBtn.textContent = isLast ? 'Done ✓' : 'Next →';
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
    _hubMode = false;
    var overlay = _el('ob-overlay');
    overlay.classList.add('ob-open');

    // Role badge
    var badge = _el('ob-role-badge');
    badge.textContent = ROLE_LABEL[_role] || _role;
    badge.style.color = ROLE_ACCENT[_role] || '#00e5cc';
    badge.style.borderColor = ROLE_ACCENT[_role] || '#00e5cc';

    // Ensure step UI visible, hub hidden
    _el('ob-body').style.display = '';
    _el('ob-footer').style.display = '';
    _el('ob-hub').style.display = 'none';

    _goTo(_step);
  }

  function _resolveTarget(step) {
    var selectors = [step && step.targetSelector, step && step.fallbackSelector, step && step.highlightSelector, step && step.highlight]
      .filter(Boolean);
    for (var i = 0; i < selectors.length; i++) {
      try {
        var el = document.querySelector(selectors[i]);
        if (!el) continue;
        var rect = el.getBoundingClientRect();
        if (rect.width || rect.height) return { el: el, selector: selectors[i] };
      } catch (_e) {}
    }
    return null;
  }

  function _clearHighlight() {
    var overlay = _el('ob-overlay');
    var modal = _el('ob-modal');
    if (overlay) overlay.classList.remove('ob-targeted');
    if (modal) {
      modal.style.left = '';
      modal.style.top = '';
    }
    var ring = document.getElementById('ob-highlight-ring');
    if (ring) {
      if (ring._rafId) cancelAnimationFrame(ring._rafId);
      ring.remove();
    }
    document.querySelectorAll('.ob-highlight').forEach(function (el) { el.classList.remove('ob-highlight'); });
    if (_targetClickCleanup) { _targetClickCleanup(); _targetClickCleanup = null; }
  }

  var _targetClickCleanup = null;

  // ── UI element spotlight ring and card placement ─────────────────────────
  function _applyStepTarget(step) {
    _clearHighlight();
    var resolved = _resolveTarget(step || {});
    if (!resolved) return; // modal-only fallback
    var target = resolved.el;
    try { target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' }); } catch (_e) {}
    setTimeout(function () { _positionSpotlight(target, step || {}); }, 180);
    if (step && step.requireClick) {
      var onClick = function () {
        if (_helpMode) return;
        if (_step < _steps.length - 1) _goTo(_step + 1);
      };
      target.addEventListener('click', onClick, { once: true, capture: true });
      _targetClickCleanup = function () { target.removeEventListener('click', onClick, true); };
    }
  }

  function _positionSpotlight(target, step) {
    if (!_el('ob-overlay') || !_el('ob-modal') || !_el('ob-overlay').classList.contains('ob-open')) return;
    var rect = target.getBoundingClientRect();
    if (!(rect.width || rect.height)) return;
    var accent = (step && step.accent) || ROLE_ACCENT[_role] || '#00e5cc';
    var ring = document.createElement('div');
    ring.id = 'ob-highlight-ring';
    ring.style.cssText = 'position:fixed;pointer-events:none;z-index:20001;border:2px solid '+accent+';border-radius:10px;animation:ob-ring-pulse 1.6s ease-in-out infinite;box-shadow:0 0 0 9999px rgba(0,0,0,0.62);transition:all 0.18s;';
    document.body.appendChild(ring);
    _el('ob-overlay').classList.add('ob-targeted');
    target.classList.add('ob-highlight');
    var modal = _el('ob-modal');
    function update() {
      var r = target.getBoundingClientRect();
      ring.style.left = (r.left - 8) + 'px'; ring.style.top = (r.top - 8) + 'px';
      ring.style.width = (r.width + 16) + 'px'; ring.style.height = (r.height + 16) + 'px';
      var mw = modal.offsetWidth || 440, mh = modal.offsetHeight || 360, gap = 18;
      var placement = (step && step.placement) || 'auto';
      var left = r.right + gap, top = r.top;
      if (placement === 'left' || (placement === 'auto' && left + mw > window.innerWidth - 12)) left = r.left - mw - gap;
      if (placement === 'top') { left = r.left; top = r.top - mh - gap; }
      if (placement === 'bottom') { left = r.left; top = r.bottom + gap; }
      if (placement === 'center') { left = (window.innerWidth - mw) / 2; top = (window.innerHeight - mh) / 2; }
      left = Math.max(12, Math.min(left, window.innerWidth - mw - 12));
      top = Math.max(12, Math.min(top, window.innerHeight - mh - 12));
      modal.style.left = left + 'px'; modal.style.top = top + 'px';
      ring._rafId = requestAnimationFrame(update);
    }
    update();
  }

  // ── Colour helpers ────────────────────────────────────────────────────────
  function _dimColor(hex) {
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
   * showHelpHub(role) — show the Help Hub topic selector.
   */
  function showHelpHub(role) {
    _role   = role || _role || 'viewer';
    _hubMode = true;
    _ensureModal();
    var overlay = _el('ob-overlay');
    overlay.classList.add('ob-open');
    var badge = _el('ob-role-badge');
    badge.textContent = 'Help Hub';
    badge.style.color = ROLE_ACCENT[_role] || '#00e5cc';
    badge.style.borderColor = ROLE_ACCENT[_role] || '#00e5cc';
    _renderHub();
  }

  /**
   * showCombatHint(message, duration) — show a transient non-blocking inline hint bar.
   * Looks for #combat-hint-bar in the DOM; falls back to a simple toast if not present.
   * duration in ms (default 6000).
   */
  function showCombatHint(message, duration) {
    var ms = typeof duration === 'number' ? duration : 6000;
    var bar = document.getElementById('combat-hint-bar');
    if (bar) {
      bar.textContent = message;
      bar.style.display = 'flex';
      bar.classList.add('combat-hint-visible');
      clearTimeout(bar._hintTimer);
      bar._hintTimer = setTimeout(function () {
        bar.classList.remove('combat-hint-visible');
        setTimeout(function () { bar.style.display = 'none'; }, 300);
      }, ms);
      return;
    }
    // Fallback: use showToast if available
    if (typeof window.showToast === 'function') {
      window.showToast(message);
    }
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

  /**
   * createHelpHubButton(role, label) — returns a Help Hub <button> element.
   */
  function createHelpHubButton(role, label) {
    var btn = document.createElement('button');
    btn.className = 'ob-help-btn';
    btn.title = label || 'Help Hub';
    btn.setAttribute('aria-label', label || 'Help Hub');
    btn.textContent = '?';
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      showHelpHub(role || _role);
    });
    return btn;
  }

  window.AppOnboarding = {
    init:                init,
    showWalkthrough:     showWalkthrough,
    showHelp:            showHelp,
    showHelpHub:         showHelpHub,
    showCombatHint:      showCombatHint,
    markSeen:            markSeen,
    createHelpButton:    createHelpButton,
    createHelpHubButton: createHelpHubButton,
    STEPS:               STEPS,
    GUIDE_STEPS:         GUIDE_STEPS,
    HUB_TOPICS:          HUB_TOPICS,
  };

})();
