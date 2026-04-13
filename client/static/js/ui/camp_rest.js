/**
 * camp_rest.js — Camp / rest mode UI
 *
 * Renders a full-screen atmospheric overlay when the DM starts a camp or rest
 * scene.  Players choose a downtime activity from a grid of cards.  The DM
 * gets extra controls to configure available activities and end the scene.
 *
 * Depends on: env.sendWS, env.ROLE, env.USER_ID, env.USER_NAME
 */

'use strict';

// ─── Activity catalogue (mirrors server/handlers/camp_rest.py) ─────────────
const CAMP_ACTIVITIES = {
  cook:          { label: 'Cook',           icon: '🍲', description: 'Prepare a hearty meal to restore spirits.' },
  keep_watch:    { label: 'Keep Watch',     icon: '👁',  description: 'Stand guard and keep the camp safe through the night.' },
  tell_story:    { label: 'Tell Story',     icon: '📖', description: 'Share a tale from your past around the fire.' },
  identify_item: { label: 'Identify Item',  icon: '🔍', description: 'Study a mysterious item and uncover its properties.' },
  train:         { label: 'Train',          icon: '⚔️',  description: 'Practice your combat or class techniques.' },
  pray:          { label: 'Pray',           icon: '🙏', description: 'Commune with your deity or meditate in quiet.' },
  gamble:        { label: 'Gamble',         icon: '🎲', description: 'Play dice or cards with fellow adventurers.' },
  bond_with_ally:{ label: 'Bond with Ally', icon: '🤝', description: 'Strengthen a connection with a companion.' },
};

// ─── State ─────────────────────────────────────────────────────────────────
let _state = {
  active: false,
  label: '',
  available_activities: Object.keys(CAMP_ACTIVITIES),
  player_activities: {},
  activity_defs: CAMP_ACTIVITIES,
};
let _myActivity = null;       // activity_id chosen by this player this scene
let _hitDiceSpent = 0;        // track hit dice spent this short rest
let _lastRestType = '';       // "short" | "long" from latest DM action

// ─── Public API ────────────────────────────────────────────────────────────

/**
 * Called from the WS dispatcher when a camp_rest_sync message arrives.
 * @param {object} env  – shared env object with sendWS, ROLE, USER_ID, etc.
 * @param {object} data – payload from server
 */
export function applyCampRestState(env, data) {
  const wasActive = _state.active;
  _state = Object.assign({}, _state, data);

  // Track our own choice
  const myEntry = (_state.player_activities || {})[env.USER_ID];
  _myActivity = myEntry ? myEntry.activity_id : null;

  if (_state.active) {
    _renderOverlay(env);
    if (!wasActive) _animateOpen();
  } else {
    _closeOverlay();
  }
}

/**
 * DM shortcut: open a "start camp/rest" dialog.
 * Wired to the DM toolbar button.
 */
export function openCampRestDmDialog(env) {
  if (_state.active) {
    // Scene already running — offer to end it
    _renderDmControlPanel(env);
    return;
  }
  _renderDmStartDialog(env);
}

// ─── Overlay rendering ─────────────────────────────────────────────────────

function _getOrCreateOverlay() {
  let el = document.getElementById('camp-rest-overlay');
  if (!el) {
    el = document.createElement('div');
    el.id = 'camp-rest-overlay';
    el.className = 'camp-rest-overlay';
    document.body.appendChild(el);
  }
  return el;
}

function _closeOverlay() {
  const el = document.getElementById('camp-rest-overlay');
  if (!el) return;
  el.classList.add('camp-rest-closing');
  setTimeout(() => el.remove(), 400);
}

function _animateOpen() {
  const el = document.getElementById('camp-rest-overlay');
  if (!el) return;
  el.classList.remove('camp-rest-closing');
  void el.offsetWidth; // force reflow
  el.classList.add('camp-rest-open');
}

function _renderOverlay(env) {
  const overlay = _getOrCreateOverlay();
  const available = _state.available_activities || Object.keys(CAMP_ACTIVITIES);
  const playerActs = _state.player_activities || {};
  const label = _state.label || 'Making Camp';

  // Build roster of connected-user selections (shown as soft badges)
  const rosterHtml = _buildRosterHtml(playerActs, env);
  const playerRecoveryHtml = env.ROLE === 'player' ? _buildPlayerRecoveryHtml() : '';

  overlay.innerHTML = `
    <div class="cr-backdrop"></div>
    <div class="cr-panel">
      <div class="cr-header">
        <span class="cr-fire-icon">🔥</span>
        <div class="cr-header-text">
          <div class="cr-title">${_esc(label)}</div>
          <div class="cr-subtitle">Choose how to spend the rest</div>
        </div>
        ${env.ROLE === 'dm' ? `<button class="cr-dm-end-btn" id="cr-dm-end-btn" title="End camp/rest scene">✕ End Scene</button>` : ''}
      </div>

      <div class="cr-activity-grid" id="cr-activity-grid">
        ${available.map(id => _buildActivityCard(id, env)).join('')}
      </div>

      ${rosterHtml ? `<div class="cr-roster">${rosterHtml}</div>` : ''}
      ${playerRecoveryHtml}

      <div class="cr-rest-actions">
        ${env.ROLE === 'dm' ? `
          <button class="cr-rest-btn cr-short-rest-btn" id="cr-short-rest-btn" title="Short rest: party may spend hit dice to heal">☀ Short Rest</button>
          <button class="cr-rest-btn cr-long-rest-btn" id="cr-long-rest-btn" title="Long rest: full HP restored, spell slots refreshed">🌙 Long Rest</button>
        ` : `
          <button class="cr-rest-btn cr-spend-hitdie-btn" id="cr-spend-hitdie-btn" title="Spend a hit die to heal HP">${_playerSpendHitDieBtnLabel()}</button>
        `}
      </div>

      ${env.ROLE === 'dm' ? _buildDmActivityControls(available) : ''}
    </div>
  `;

  // Wire click handlers
  overlay.querySelectorAll('.cr-activity-card').forEach(card => {
    card.addEventListener('click', () => _onActivityClick(env, card.dataset.activityId));
  });

  const endBtn = overlay.querySelector('#cr-dm-end-btn');
  if (endBtn) endBtn.addEventListener('click', () => _onDmEnd(env));

  const saveActsBtn = overlay.querySelector('#cr-save-acts-btn');
  if (saveActsBtn) saveActsBtn.addEventListener('click', () => _onDmSaveActivities(env, overlay));

  const shortRestBtn = overlay.querySelector('#cr-short-rest-btn');
  if (shortRestBtn) shortRestBtn.addEventListener('click', () => _onTakeRest(env, 'short'));

  const longRestBtn = overlay.querySelector('#cr-long-rest-btn');
  if (longRestBtn) longRestBtn.addEventListener('click', () => _onTakeRest(env, 'long'));

  const spendHdBtn = overlay.querySelector('#cr-spend-hitdie-btn');
  if (spendHdBtn) {
    const death = _getOwnedDeathSaveState();
    if (death?.dead) spendHdBtn.setAttribute('disabled', 'disabled');
    spendHdBtn.addEventListener('click', () => _onSpendHitDie(env));
  }
}

function _buildActivityCard(id, env) {
  const def = CAMP_ACTIVITIES[id] || { label: id, icon: '?', description: '' };
  const isMine = _myActivity === id;
  const cls = 'cr-activity-card' + (isMine ? ' selected' : '');
  return `
    <div class="${cls}" data-activity-id="${id}" title="${_esc(def.description)}">
      <div class="cr-act-icon">${def.icon}</div>
      <div class="cr-act-label">${_esc(def.label)}</div>
    </div>
  `;
}

function _buildRosterHtml(playerActs, env) {
  const entries = Object.values(playerActs);
  if (!entries.length) return '';
  const chips = entries.map(e => {
    const def = CAMP_ACTIVITIES[e.activity_id] || { icon: '?', label: e.activity_id };
    const noteHtml = e.note ? ` <span class="cr-roster-note">"${_esc(e.note)}"</span>` : '';
    return `<div class="cr-roster-chip">${def.icon} <strong>${_esc(e.user_name)}</strong> — ${_esc(def.label)}${noteHtml}</div>`;
  }).join('');
  return `<div class="cr-roster-label">Party Activities</div>${chips}`;
}

function _buildDmActivityControls(available) {
  const allIds = Object.keys(CAMP_ACTIVITIES);
  const checkboxes = allIds.map(id => {
    const def = CAMP_ACTIVITIES[id];
    const checked = available.includes(id) ? 'checked' : '';
    return `<label class="cr-act-check"><input type="checkbox" data-act="${id}" ${checked}> ${def.icon} ${def.label}</label>`;
  }).join('');
  return `
    <details class="cr-dm-controls">
      <summary>DM: Configure Activities</summary>
      <div class="cr-act-checklist">${checkboxes}</div>
      <button class="cr-dm-save-btn" id="cr-save-acts-btn">Update Available Activities</button>
    </details>
  `;
}

// ─── DM Start Dialog ────────────────────────────────────────────────────────

function _renderDmStartDialog(env) {
  let modal = document.getElementById('cr-start-modal');
  if (modal) modal.remove();
  modal = document.createElement('div');
  modal.id = 'cr-start-modal';
  modal.className = 'cr-modal-wrap';

  const allIds = Object.keys(CAMP_ACTIVITIES);
  const checkboxes = allIds.map(id => {
    const def = CAMP_ACTIVITIES[id];
    return `<label class="cr-act-check"><input type="checkbox" data-act="${id}" checked> ${def.icon} ${def.label}</label>`;
  }).join('');

  modal.innerHTML = `
    <div class="cr-modal">
      <div class="cr-modal-header">🔥 Start Camp / Rest Scene</div>
      <label class="cr-modal-label">Scene label (shown to players)
        <input id="cr-scene-label" class="cr-modal-input" type="text" maxlength="120" placeholder="Making camp at the Crossroads Inn" value="Making Camp">
      </label>
      <div class="cr-modal-label">Available activities</div>
      <div class="cr-act-checklist">${checkboxes}</div>
      <div class="cr-modal-actions">
        <button class="cr-modal-cancel" id="cr-start-cancel">Cancel</button>
        <button class="cr-modal-confirm" id="cr-start-confirm">🔥 Begin Scene</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.querySelector('#cr-start-cancel').addEventListener('click', () => modal.remove());
  modal.querySelector('#cr-start-confirm').addEventListener('click', () => {
    const label = modal.querySelector('#cr-scene-label').value.trim() || 'Making Camp';
    const selected = [...modal.querySelectorAll('.cr-act-check input:checked')].map(cb => cb.dataset.act);
    env.sendWS({ type: 'camp_rest_start', payload: { label, available_activities: selected } });
    modal.remove();
  });

  // Click outside to dismiss
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

function _renderDmControlPanel(env) {
  // Scene is already active; overlay handles DM controls inline
  const overlay = document.getElementById('camp-rest-overlay');
  if (overlay) overlay.scrollIntoView({ behavior: 'smooth' });
}

// ─── Event handlers ─────────────────────────────────────────────────────────

function _onActivityClick(env, activityId) {
  if (!activityId) return;
  if (_myActivity === activityId) {
    // Deselect
    env.sendWS({ type: 'camp_rest_clear_activity', payload: { user_id: env.USER_ID } });
    return;
  }
  // Optionally prompt for a note (simple inline prompt)
  const note = ''; // keep frictionless — note optional
  env.sendWS({
    type: 'camp_rest_activity_select',
    payload: { activity_id: activityId, note },
  });
}

function _onDmEnd(env) {
  env.sendWS({ type: 'camp_rest_end', payload: {} });
}

function _onDmSaveActivities(env, overlay) {
  const selected = [...overlay.querySelectorAll('.cr-act-checklist input:checked')].map(cb => cb.dataset.act);
  env.sendWS({ type: 'camp_rest_update_activities', payload: { available_activities: selected } });
}

function _onTakeRest(env, restType) {
  const label = restType === 'long' ? 'Long Rest' : 'Short Rest';
  const detail = restType === 'long'
    ? 'All party members will be restored to full HP and spell slots refreshed.'
    : 'Party members may spend hit dice to recover HP.';
  if (!confirm(`Trigger ${label}?\n\n${detail}`)) return;
  env.sendWS({ type: 'camp_rest_take_rest', payload: { rest_type: restType } });
}

function _onSpendHitDie(env) {
  if (_lastRestType && _lastRestType !== 'short') {
    if (typeof showToast === 'function') showToast('Hit dice are usually spent during a short rest.');
  }
  const death = _getOwnedDeathSaveState();
  if (death?.dead) {
    if (typeof showToast === 'function') showToast('This character is dead and cannot spend hit dice.');
    return;
  }
  // Build a modal letting the player roll their hit die + CON mod
  const existing = document.getElementById('cr-hit-die-modal');
  if (existing) existing.remove();

  // Try to get hit dice info from the character sheet
  const charSheet = (typeof _charSheet !== 'undefined' ? _charSheet : null) || {};
  const hitDiceStr = charSheet.hitDice || '';
  // hitDice might be "1d8" or "4d8" or "2d10" etc — use the die size
  const hdMatch = hitDiceStr.match(/(\d*)d(\d+)/i);
  const dieSides = hdMatch ? parseInt(hdMatch[2], 10) : 8;

  // CON modifier
  let conMod = 0;
  if (typeof _abilityModifierFromLabel === 'function') {
    conMod = _abilityModifierFromLabel('CON') || 0;
  } else if (charSheet.stats && charSheet.stats.length >= 3) {
    const conScore = parseInt(charSheet.stats[2], 10) || 10;
    conMod = Math.floor((conScore - 10) / 2);
  }
  const conModStr = conMod >= 0 ? `+${conMod}` : String(conMod);

  const modal = document.createElement('div');
  modal.id = 'cr-hit-die-modal';
  modal.className = 'cr-hit-die-modal';
  const hitDiceMeta = hitDiceStr ? ` • Sheet: ${_esc(hitDiceStr)}` : '';
  const restMeta = _lastRestType ? ` • ${_lastRestType === 'short' ? 'Short Rest Active' : 'Last Rest: Long'}` : '';
  modal.innerHTML = `
    <div class="cr-hit-die-card">
      <div class="cr-hit-die-title">☀ Spend Hit Die</div>
      <div class="cr-hit-die-subtitle">
        Roll 1d${dieSides} ${conModStr} CON and recover that much HP.
        <span>${hitDiceMeta}${restMeta}</span>
      </div>
      <button id="cr-hd-roll-btn" class="cr-hit-die-btn roll-btn">🎲 Roll d${dieSides} ${conModStr}</button>
      <div id="cr-hd-result" class="cr-hit-die-result"></div>
      <button id="cr-hd-apply-btn" class="cr-hit-die-btn apply-btn" style="display:none;">✓ Apply Healing</button>
      <button id="cr-hd-cancel-btn" class="cr-hit-die-btn cancel-btn">Cancel</button>
    </div>`;
  document.body.appendChild(modal);

  let rolledTotal = 0;
  modal.querySelector('#cr-hd-roll-btn').addEventListener('click', () => {
    const roll = Math.floor(Math.random() * dieSides) + 1;
    rolledTotal = Math.max(1, roll + conMod);
    modal.querySelector('#cr-hd-result').textContent = `d${dieSides}: ${roll} ${conModStr} = ${rolledTotal} HP`;
    modal.querySelector('#cr-hd-apply-btn').style.display = 'block';
  });
  modal.querySelector('#cr-hd-apply-btn').addEventListener('click', () => {
    modal.remove();
    env.sendWS({ type: 'camp_rest_spend_hit_die', payload: { heal_amount: rolledTotal } });
  });
  modal.querySelector('#cr-hd-cancel-btn').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

/**
 * Called when the server sends a camp_rest_rest_applied event.
 * env: shared env; data: payload from server.
 * Note: spell slot reset for long rest is handled directly in play.html.
 */
export function applyCampRestResult(env, data) {
  const restType = data.rest_type || 'long';
  _lastRestType = String(restType || '').toLowerCase();
  if (_lastRestType === 'short') _hitDiceSpent = 0;
  // For short rest, open the hit die modal so the player can spend dice
  if (restType === 'short' && env.ROLE === 'player') {
    _onSpendHitDie(env);
  }
}

/**
 * Called when server confirms a hit die was spent (camp_rest_hit_die_result).
 */
export function applyCampRestHitDieResult(env, data) {
  const heal = data.heal_amount || 0;
  const newHp = data.new_hp;
  const maxHp = data.max_hp;
  _hitDiceSpent = Math.max(0, Number(_hitDiceSpent || 0) + 1);
  const hpStr = (newHp !== undefined && maxHp !== undefined) ? ` (${newHp}/${maxHp})` : '';
  if (typeof showToast === 'function') showToast(`Hit die: recovered ${heal} HP${hpStr}`);
  if (_state.active && env.ROLE === 'player') _renderOverlay(env);
}

// ─── Utility ────────────────────────────────────────────────────────────────

function _getOwnedToken() {
  if (typeof tokens !== 'object' || !tokens) return null;
  const mine = Object.values(tokens).find(t => t && String(t.owner_id || '') === String(USER_ID || ''));
  if (mine) return mine;
  if (typeof _stagingTokens !== 'object' || !_stagingTokens) return null;
  return Object.values(_stagingTokens).find(t => t && String(t.owner_id || '') === String(USER_ID || '')) || null;
}

function _getOwnedDeathSaveState() {
  const list = Array.isArray(_combat?.combatants) ? _combat.combatants : [];
  const mine = _getOwnedToken();
  const me = list.find(com =>
    (mine && String(com?.token_id || '') === String(mine?.id || '')) ||
    (com?.owner_id && String(com.owner_id) === String(USER_ID || ''))
  );
  const ds = me?.death_saves || me?.deathSaves || null;
  if (!ds) return null;
  return {
    successes: Math.max(0, Number(ds.successes || 0) || 0),
    fails: Math.max(0, Number(ds.fails || 0) || 0),
    stable: !!ds.stable,
    dead: !!ds.dead,
  };
}

function _buildPlayerRecoveryHtml() {
  const mine = _getOwnedToken();
  if (!mine) return '';
  const hp = Number(mine.hp);
  const maxHp = Number(mine.maxHp);
  const hpKnown = Number.isFinite(hp) && Number.isFinite(maxHp) && maxHp > 0;
  const downed = hpKnown && hp <= 0;
  const ds = _getOwnedDeathSaveState();
  const deathStateLabel = ds?.dead
    ? 'Dead'
    : ds?.stable
      ? 'Stable at 0 HP'
      : downed
        ? 'Downed at 0 HP'
        : 'Conscious';
  const deathStateClass = ds?.dead ? 'is-dead' : (downed ? 'is-downed' : (ds?.stable ? 'is-stable' : ''));
  return `
    <section class="cr-player-recovery ${deathStateClass}">
      <div class="cr-player-recovery-top">
        <strong>Recovery</strong>
        <span>${hpKnown ? `${Math.max(0, Math.round(hp))}/${Math.max(1, Math.round(maxHp))} HP` : 'HP unavailable'}</span>
      </div>
      <div class="cr-player-recovery-state">${_esc(deathStateLabel)}${_lastRestType ? ` • Last rest: ${_esc(_lastRestType)}` : ''}</div>
      ${_buildDeathSaveTrackHtml(ds)}
      <div class="cr-player-recovery-hint">Hit dice spent this rest: ${Math.max(0, Number(_hitDiceSpent || 0))}</div>
    </section>
  `;
}

function _buildDeathSaveTrackHtml(ds) {
  if (!ds) return '<div class="cr-death-track-note">No death saves active.</div>';
  const successPips = Array.from({ length: 3 }).map((_, i) => `<span class="cr-death-pip success ${i < ds.successes ? 'on' : ''}">${i < ds.successes ? '✓' : '·'}</span>`).join('');
  const failPips = Array.from({ length: 3 }).map((_, i) => `<span class="cr-death-pip fail ${i < ds.fails ? 'on' : ''}">${i < ds.fails ? '✗' : '·'}</span>`).join('');
  return `<div class="cr-death-track"><div><span>Success</span>${successPips}</div><div><span>Fail</span>${failPips}</div></div>`;
}

function _playerSpendHitDieBtnLabel() {
  if (_lastRestType === 'short') return '🎲 Spend Hit Die';
  if (_lastRestType === 'long') return '🎲 Spend Hit Die (Manual)';
  return '🎲 Spend Hit Die';
}

function _esc(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
