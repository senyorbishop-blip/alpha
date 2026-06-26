/*
 * dm_context_render.js
 * Casual D&D / Alpha — rich per-mode content for the DM map-first context panel.
 *
 * Replaces the old "navigation marker" lists with real, live content
 * (current turn, initiative order, party HP, quick actions, grouped tools).
 *
 * Design rules:
 *   - Reads LIVE state (_combat, _normalizeCombatRoster, charProfiles) defensively.
 *     Any missing global falls back to a friendly placeholder; never throws, never blanks.
 *   - Every control calls an EXISTING play.html global (combatNext, switchRTab,
 *     toggleFlyout, beginBestiarySpawn, …) via inline onclick — same convention
 *     as the rest of the page, so nothing new has to be wired.
 *
 * Public API (used by dm_panel_mode_bridge.js):
 *   AppUIDMContextRender.meta(mode)  -> { gly, title, note }
 *   AppUIDMContextRender.tabs(mode)  -> [[key,label,badge?], ...]
 *   AppUIDMContextRender.render(mode)-> html string
 *   AppUIDMContextRender.afterRender(container) -> wire dynamic bits (search input)
 */
(function () {
  'use strict';

  /* ---------- safe helpers ---------- */
  function g(name) { try { return window[name]; } catch (_e) { return undefined; } }
  function num(v, d) { v = Number(v); return Number.isFinite(v) ? v : d; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function pct(hp, max) {
    max = num(max, 0); hp = num(hp, 0);
    if (max <= 0) return 0;
    return Math.max(0, Math.min(100, Math.round((hp / max) * 100)));
  }
  function hpBar(hp, max, full) {
    var w = pct(hp, max);
    var fill = full ? ' data-full="true"' : '';
    return '<div class="dcx-hpbar"><i style="width:' + w + '%"' + fill + '></i></div>';
  }

  /* ---------- live state readers (all guarded) ---------- */
  function combat() { var c = g('_combat'); return (c && typeof c === 'object') ? c : null; }

  function roster() {
    // Preferred: the page's own normalizer (handles visibility, current turn, etc.)
    var fn = g('_normalizeCombatRoster');
    var c = combat();
    if (typeof fn === 'function') {
      try {
        var out = fn(c || undefined);
        if (Array.isArray(out)) return out;
        if (out && Array.isArray(out.rows)) return out.rows;       // tolerate {rows:[…]}
        if (out && Array.isArray(out.normalized)) return out.normalized;
      } catch (_e) { /* fall through */ }
    }
    // Fallback: raw combatants
    if (c && Array.isArray(c.combatants)) {
      var turn = num(c.turn, 0);
      return c.combatants.map(function (com, i) {
        return {
          name: com && com.name, color: (com && com.color) || '#888',
          initiative: com && com.initiative, isCurrent: c.active && i === turn,
          isPlayerOwned: !!(com && (com.is_player || com.owner_id)),
          combatant: com, token: null, defeated: num(com && com.hp, 1) <= 0,
        };
      });
    }
    return [];
  }

  function rowHp(r) {
    var com = r.combatant || {}; var tok = r.token || {};
    var hp = com.hp != null ? com.hp : (tok.hp != null ? tok.hp : (tok.currentHP != null ? tok.currentHP : null));
    var max = com.max_hp != null ? com.max_hp : (tok.max_hp != null ? tok.max_hp : (tok.maxHP != null ? tok.maxHP : null));
    return { hp: hp, max: max };
  }

  function modifier(v) {
    if (v == null || v === '') return '';
    v = Number(v); if (!Number.isFinite(v)) return '';
    return (v >= 0 ? '+' : '') + v;
  }

  function isLive() { var c = combat(); return !!(c && c.active && roster().length); }

  /* ---------- party rows ---------- */
  function partyRows() {
    var rows = roster().filter(function (r) { return r.isPlayerOwned; });
    if (rows.length) {
      return rows.map(function (r) {
        var h = rowHp(r);
        return { name: r.name || 'Adventurer', hp: h.hp, max: h.max, full: num(h.hp, 0) >= num(h.max, 0) && num(h.max, 0) > 0 };
      });
    }
    // Out of combat: try character profiles
    var cp = g('charProfiles');
    if (Array.isArray(cp) && cp.length) {
      return cp.map(function (p) {
        var n = p && (p.name || p.character_name || p.charName);
        var hp = p && (p.hp != null ? p.hp : (p.current_hp != null ? p.current_hp : null));
        var max = p && (p.max_hp != null ? p.max_hp : (p.maxHp != null ? p.maxHp : null));
        return { name: n || 'Adventurer', hp: hp, max: max, full: num(hp, 0) >= num(max, 0) && num(max, 0) > 0 };
      });
    }
    return [];
  }

  /* ---------- small templates ---------- */
  function block(title, inner, opts) {
    opts = opts || {};
    var act = opts.action
      ? '<button class="dcx-eyebrow-act" type="button" onclick="' + esc(opts.action) + '">' + esc(opts.actionLabel || 'Open') + '</button>'
      : '';
    var eb = title ? '<div class="dcx-eyebrow">' + esc(title) + act + '</div>' : '';
    return '<section class="dcx-section">' + eb + '<div class="' + (opts.cls || 'dcx-card') + '">' + inner + '</div></section>';
  }
  function action(ic, t, s, onclick) {
    return '<button class="dcx-action" type="button" onclick="' + esc(onclick) + '">' +
      '<span class="dcx-ai">' + ic + '</span><span class="dcx-al"><span class="t">' + esc(t) + '</span>' +
      '<span class="s">' + esc(s) + '</span></span></button>';
  }
  function tool(ic, t, s, onclick) {
    return '<button class="dcx-tl" type="button" onclick="' + esc(onclick) + '"><span class="dcx-ti">' + ic + '</span>' +
      '<span class="tt">' + esc(t) + '</span>' + (s ? '<span class="ts">' + esc(s) + '</span>' : '') + '</button>';
  }
  function stool(ic, l, onclick) {
    return '<button class="dcx-stool" type="button" onclick="' + esc(onclick) + '"><span class="g">' + ic + '</span>' + esc(l) + '</button>';
  }
  function empty(msg) { return '<div class="dcx-empty">' + msg + '</div>'; }

  /* ---------- shared blocks ---------- */
  function partyBlock() {
    var rows = partyRows();
    var inner;
    if (!rows.length) {
      inner = empty('No party loaded yet.');
    } else {
      inner = '<div class="dcx-party">' + rows.map(function (p) {
        var label = (p.hp != null && p.max != null) ? esc(p.hp) + '/' + esc(p.max) : '—';
        return '<div class="dcx-party-row' + (p.full ? ' full' : '') + '">' +
          '<span class="dcx-av"></span><span class="dcx-pn">' + esc(p.name) + '</span>' +
          '<span class="dcx-pcol">' + hpBar(p.hp, p.max, p.full) + '<span class="dcx-pnum">' + label + '</span></span></div>';
      }).join('') + '</div>';
    }
    return block('Party overview', inner, { action: "switchRTab('party')", actionLabel: 'Full party' });
  }

  function initiativeBlock() {
    var rows = roster();
    if (!isLive()) {
      return block('Initiative order',
        empty('Combat isn\u2019t running.<br><button class="dcx-start" type="button" onclick="combatStart()">\u2694 Start combat</button>'));
    }
    var inner = '<div class="dcx-init">' + rows.map(function (r, i) {
      var h = rowHp(r);
      var hpTxt = (h.hp != null && h.max != null) ? esc(h.hp) + '/' + esc(h.max) : '';
      var kind = r.isPlayerOwned ? 'Player' : (r.combatant && r.combatant.kind) || 'NPC';
      return '<div class="dcx-init-row" data-active="' + (!!r.isCurrent) + '" ' +
        'onclick="switchRTab(\'combat\')">' +
        '<span class="dcx-ord">' + (i + 1) + '</span>' +
        '<span class="dcx-who"><span class="n">' + esc(r.name || 'Combatant') + '</span><span class="k">' + esc(kind) + '</span></span>' +
        '<span class="dcx-mod">' + esc(modifier(r.initiative)) + '</span>' +
        '<span class="dcx-ihp">' + hpTxt + '</span></div>';
    }).join('') + '</div>';
    return block('Initiative order', inner, { action: "switchRTab('combat')", actionLabel: 'Open tracker' });
  }

  function currentTurnBlock() {
    if (!isLive()) {
      return block('Current turn', empty('Start combat to track turns.'), { cls: 'dcx-card glow' });
    }
    var rows = roster();
    var cur = rows.filter(function (r) { return r.isCurrent; })[0] || rows[0];
    var h = rowHp(cur);
    var inner =
      '<div class="dcx-turn">' +
        '<div class="dcx-portrait" style="background:radial-gradient(circle at 35% 30%,' + esc(cur.color || '#6fe0d2') + ',rgba(0,0,0,.35))"></div>' +
        '<div class="dcx-tinfo"><div class="r1"><span class="nm">' + esc(cur.name || 'Combatant') + '</span></div>' +
          '<div class="cls">' + (cur.isPlayerOwned ? 'Player turn' : 'NPC turn') + '</div>' +
          '<div class="dcx-chips"><span class="dcx-chip">Init <b>' + esc(modifier(cur.initiative) || '0') + '</b></span></div></div>' +
        '<div class="dcx-hpwrap"><span class="dcx-hpnum">' + (h.hp != null ? esc(h.hp) : '—') +
          '<span class="sm">' + (h.max != null ? '/' + esc(h.max) : '') + '</span></span>' + hpBar(h.hp, h.max) + '</div>' +
      '</div>' +
      '<div class="dcx-turn-cta"><button class="dcx-primary" type="button" onclick="combatNext()">End turn \u25B8</button></div>';
    return block('Current turn', inner, { cls: 'dcx-card glow' });
  }

  function sessionToolsBlock() {
    return block('Session tools',
      '<div class="dcx-stools">' +
        stool('\uD83D\uDCD3', 'Notes', "switchRTab('memory')") +
        stool('\uD83D\uDCDC', 'Handouts', "switchRTab('handouts')") +
        stool('\uD83C\uDFB5', 'Sound', "toggleFlyout('flyout-sound')") +
        stool('\uD83D\uDCD3', 'Journal', "toggleFlyout('flyout-journal')") +
      '</div>');
  }

  /* ---------- per-mode definitions ---------- */
  var META = {
    'run':           { gly: '\u25B6',     title: 'Live Table',    note: 'Map remains primary' },
    'combat':        { gly: '\u2694',     title: 'Combat',        note: 'Turn-based control' },
    'map-build':     { gly: '\uD83E\uDDF1', title: 'Map Build',   note: 'Editing layer \u00B7 DM only' },
    'npc-monster':   { gly: '\uD83D\uDC09', title: 'NPC / Monster', note: 'Bestiary \u00B7 spawn' },
    'loot-shop':     { gly: '\uD83C\uDFEA', title: 'Loot / Shop', note: 'Economy \u00B7 rewards' },
    'session-tools': { gly: '\uD83D\uDCDC', title: 'Session Tools', note: 'Story \u00B7 journal \u00B7 audio' },
    'viewer-powers': { gly: '\uD83D\uDC41', title: 'Viewer Powers', note: 'DM only \u00B7 chaos control' },
    'debug':         { gly: '\uD83D\uDC1E', title: 'Debug',       note: 'Troubleshooting' },
  };
  var TABS = {
    'run':           [['party', 'Party'], ['inventory', 'Inventory'], ['memory', 'Moments'], ['combat', 'Combat']],
    'combat':        [['combat', 'Turns'], ['party', 'Party'], ['memory', 'Log']],
    'map-build':     [['terrain', 'Terrain'], ['walls', 'Walls'], ['fog', 'Fog']],
    'npc-monster':   [['bestiary', 'Bestiary'], ['combat', 'Encounter']],
    'loot-shop':     [['shop', 'Items'], ['inventory', 'Party']],
    'session-tools': [['handouts', 'Handouts'], ['memory', 'Journal']],
    'viewer-powers': [['party', 'Viewers']],
    'debug':         [],
  };

  var RENDER = {
    'run': function () {
      return currentTurnBlock().replace('Current turn', 'Selected / current') + partyBlock() + sessionToolsBlock();
    },
    'combat': function () {
      return currentTurnBlock() + initiativeBlock() + partyBlock() +
        block('Quick actions',
          '<div class="dcx-actions">' +
            action('\u2694', 'Attack', 'selected token', "switchRTab('combat')") +
            action('\u2728', 'Cast spell', 'from sheet', "switchRTab('combat')") +
            action('\u271A', 'Heal', 'cure wounds', "switchRTab('combat')") +
            action('\u27F3', 'Reaction', 'hold / ready', "switchRTab('combat')") +
          '</div>') +
        sessionToolsBlock();
    },
    'map-build': function () {
      return block('Build tools',
        '<div class="dcx-toollist">' +
          tool('\u26F0', 'Terrain tools', 'paint', "toggleFlyout('flyout-editor')") +
          tool('\uD83E\uDDF1', 'Wall tools', 'collision', "toggleFlyout('flyout-editor')") +
          tool('\uD83D\uDEAA', 'Door tools', 'linked', "toggleFlyout('flyout-editor')") +
          tool('\uD83C\uDF2B', 'Fog tools', 'reveal/hide', "toggleFlyout('flyout-fog')") +
          tool('\uD83D\uDDFA', 'Token layer', '', "toggleFlyout('flyout-editor')") +
          tool('\uD83E\uDE91', 'Prop layer', '', "toggleFlyout('flyout-editor')") +
          tool('\u263C', 'Lighting / weather', '', "toggleFlyout('flyout-map')") +
          tool('\uD83D\uDCE6', 'Asset library', '', "initAssetLibrary()") +
        '</div>') +
        block('Apply', '<button class="dcx-primary wide" type="button" onclick="toggleFlyout(\'flyout-editor\')">Open map editor \u25B8</button>');
    },
    'npc-monster': function () {
      return block('Find a creature',
        '<div class="dcx-searchrow"><input id="dcx-bestiary-search" type="search" placeholder="Search bestiary\u2026" autocomplete="off">' +
          '<button class="dcx-filter" type="button" onclick="switchRTab(\'bestiary\')">Filters</button></div>' +
          '<div class="dcx-hint">Type to search, then pick a creature in the Bestiary tab.</div>') +
        block('Place on map',
          '<div class="dcx-primary-actions">' +
            '<button class="dcx-pa go" type="button" onclick="beginBestiarySpawn()">\u2295 Spawn</button>' +
            '<button class="dcx-pa" type="button" onclick="switchRTab(\'combat\')">+ Encounter</button>' +
            '<button class="dcx-pa" type="button" onclick="toggleFlyout(\'flyout-token\')">\u270E Edit stats</button>' +
            '<button class="dcx-pa" type="button" onclick="switchRTab(\'bestiary\')">\u25D0 Hide / reveal</button>' +
          '</div>');
    },
    'loot-shop': function () {
      return block('Economy tools',
        '<div class="dcx-toollist">' +
          tool('\uD83D\uDD0E', 'Item search', 'SRD + custom', "switchRTab('shop')") +
          tool('\uD83D\uDCE6', 'Loot containers', '', "switchRTab('shop')") +
          tool('\uD83C\uDFEA', 'Shop setup', '', "switchRTab('shop')") +
          tool('\uD83C\uDF81', 'Grant item', 'to party', "switchRTab('inventory')") +
          tool('\uD83E\uDE99', 'Grant gold', 'to party', "switchRTab('inventory')") +
          tool('\u26A1', 'Charges / attunement', '', "switchRTab('inventory')") +
        '</div>');
    },
    'session-tools': function () {
      return block('Story &amp; table',
        '<div class="dcx-toollist">' +
          tool('\uD83C\uDFAF', 'Quests', '', "toggleFlyout('flyout-journal')") +
          tool('\uD83D\uDCD3', 'Journal', '', "toggleFlyout('flyout-journal')") +
          tool('\uD83D\uDCDC', 'Handouts', 'share', "switchRTab('handouts')") +
          tool('\uD83C\uDF99', 'Narration', '', "toggleFlyout('flyout-sound')") +
          tool('\uD83C\uDFB5', 'Sound / ambience', '', "toggleFlyout('flyout-sound')") +
          tool('\uD83D\uDCAC', 'Party message', '', "switchRTab('chat')") +
        '</div>');
    },
    'viewer-powers': function () {
      return block('Connected viewers', empty('No viewers connected.<br>Share the viewer link to let spectators join.')) +
        block('Power controls',
          '<div class="dcx-toollist">' +
            tool('\uD83C\uDF81', 'Grant power', '', "toggleFlyout('flyout-perm')") +
            tool('\u23F3', 'Pending approvals', '', "toggleFlyout('flyout-perm')") +
            tool('\u2744', 'Cooldowns', '', "toggleFlyout('flyout-perm')") +
          '</div>');
    },
    'debug': function () {
      return block('Diagnostics',
        '<div class="dcx-toollist">' +
          tool('\uD83D\uDCE1', 'Stream readiness', 'live', "if(window.renderStreamReadinessPanel)renderStreamReadinessPanel()") +
          tool('\uD83D\uDD0C', 'WebSocket', 'status', "void 0") +
          tool('\uD83D\uDD04', 'Sync diagnostics', '', "void 0") +
        '</div>') +
        '<div id="stream-readiness-panel" aria-live="polite"></div>';
    },
  };

  /* ---------- public API ---------- */
  function meta(mode) { return META[mode] || META.run; }
  function tabs(mode) { return TABS[mode] || []; }
  function render(mode) {
    var fn = RENDER[mode] || RENDER.run;
    try { return fn(); } catch (e) {
      if (window.console) console.warn('[dm-context-render] render failed', mode, e);
      return empty('This panel hit a snag. Tools are still available from the rail.');
    }
  }
  function afterRender(container) {
    if (!container || !container.querySelector) return;
    var search = container.querySelector('#dcx-bestiary-search');
    if (search) {
      search.addEventListener('input', function () {
        var real = document.getElementById('bestiary-search');
        if (real) { real.value = search.value; real.dispatchEvent(new Event('input', { bubbles: true })); }
      });
    }
  }

  window.AppUIDMContextRender = Object.freeze({ meta: meta, tabs: tabs, render: render, afterRender: afterRender });
})();
