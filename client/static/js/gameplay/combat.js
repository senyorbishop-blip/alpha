/**
 * gameplay/combat.js — dormant env-injected combat module.
 *
 * Stage 3 note:
 * - `client/templates/play.html` still owns the live combat UI, state application,
 *   and client-side combat actions.
 * - This file is a preserved alternate module from the modularization effort and is
 *   not loaded by `play.html` today.
 * - Do not treat `window.AppGameplayCombat` as runtime authority unless the page
 *   explicitly loads this module and migrates combat ownership to it.
 */
(function(){
  function _signed(value) { const n = parseInt(value, 10) || 0; return `${n >= 0 ? '+' : ''}${n}`; }
  function _runtimeCombat(env) {
    const storeRuntime = env && typeof env.getStore === 'function' ? (env.getStore()?.get?.('charRuntime') || null) : null;
    const nativeRuntime = env?._activeNativeCharacterRuntime || null;
    return (storeRuntime && typeof storeRuntime === 'object') ? storeRuntime.combat || {} : ((nativeRuntime && typeof nativeRuntime === 'object') ? nativeRuntime.combat || {} : {});
  }
  function _resolveCombatModifier(env, kind) {
    const combat = _runtimeCombat(env);
    const attackBonus = combat.attackBonus || {};
    const saves = combat.savingThrows || {};
    if (kind === 'initiative') return parseInt(combat.initiative, 10) || 0;
    if (kind === 'attack_spell') return parseInt(attackBonus.spell, 10) || 0;
    if (kind === 'attack_dex') return parseInt(attackBonus.dex, 10) || 0;
    if (kind === 'attack_str') return parseInt(attackBonus.str, 10) || 0;
    if (kind && String(kind).startsWith('save_')) {
      const key = String(kind).slice(5);
      return parseInt(saves[key], 10) || 0;
    }
    return 0;
  }
  function setDisplay(el, value) { if (el && el.style) el.style.display = value; return el; }
  function isMyToken(env, tokenId) { if (!tokenId) return false; const t = env.tokens[tokenId]; return !!(t && t.owner_id === env.USER_ID); }
  function canRollInitiative(env, com, idx) {
    const combat = env.getCombat(); if (!combat.active) return false; if (env.ROLE === 'dm') return true;
    const hasRolled = com.initiative !== null && com.initiative !== undefined; const isCurrent = idx === combat.turn;
    if (!isMyToken(env, com.token_id)) return false; return !hasRolled || isCurrent;
  }

  function getCurrentCombatant(env) {
    const combat = env.getCombat();
    const combatants = Array.isArray(combat.combatants) ? combat.combatants : [];
    const idx = Math.max(0, Number(combat.turn) || 0);
    return combat.active ? (combatants[idx] || null) : null;
  }
  function canActCurrentTurn(env) {
    const current = getCurrentCombatant(env);
    if (!current) return false;
    if (env.ROLE === 'dm') return true;
    const tok = current.token_id ? env.tokens[current.token_id] : null;
    return !!(tok && tok.owner_id === env.USER_ID);
  }
  function getSelectedTarget(env) {
    const combat = env.getCombat();
    const targetId = String(combat.selected_target_id || '');
    return targetId ? (env.tokens[targetId] || null) : null;
  }
  function clearAttackTargeting(env) { env.setCombatTargeting(false); }
  function combatApplyState(env, state) {
    if (!state || typeof state !== 'object') return;
    const prev = env.getCombat();
    env.setCombat({ active: !!state.active, turn: state.turn ?? 0, combatants: state.combatants ?? [], round: state.round ?? 1, movement: state.movement ?? null, selected_target_id: state.selected_target_id || '', pending_attack: state.pending_attack || null });
    env.setCombatRound(env.getCombat().round);
    env.renderCombat();
    const combat = env.getCombat();
    if (combat.active && (combat.turn !== prev.turn || !prev.active)) {
      const cur = combat.combatants[combat.turn];
      if (cur) {
        const badge = env.document.getElementById('rtab-combat-badge');
        if (badge) { badge.textContent = '!'; badge.classList.add('show'); }
        setTimeout(() => { const b = env.document.getElementById('rtab-combat-badge'); if (b) { b.textContent=''; b.classList.remove('show'); } }, 2500);
      }
    }
  }
  function renderCombat(env) {
    const combat = env.getCombat();
    const list = env.document.getElementById('combat-list'); const empty = env.document.getElementById('combat-empty'); const controls = env.document.getElementById('combat-controls'); const moveRow = env.document.getElementById('combat-move-row'); const pre = env.document.getElementById('combat-pre'); const addRow = env.document.getElementById('combat-add-row'); const roundLbl = env.document.getElementById('combat-round-label'); const prevBtn = env.document.getElementById('combat-prev-btn'); const nextBtn = env.document.getElementById('combat-next-btn'); const endBtn = env.document.getElementById('combat-end-btn'); if (!list) return;
    const coms = combat.combatants || []; const isActive = combat.active;
    if (pre) setDisplay(pre, (env.ROLE === 'dm' && !isActive) ? 'flex' : 'none'); if (controls) setDisplay(controls, isActive ? 'flex' : 'none'); if (addRow) setDisplay(addRow, (env.ROLE === 'dm' && isActive) ? 'flex' : 'none'); if (roundLbl) roundLbl.textContent = isActive ? `Round ${combat.round ?? env.getCombatRound()}` : 'Round —'; if (prevBtn) setDisplay(prevBtn, (env.ROLE === 'dm' && isActive) ? '' : 'none'); if (nextBtn) setDisplay(nextBtn, (env.ROLE === 'dm' && isActive) ? '' : 'none'); if (endBtn) setDisplay(endBtn, (env.ROLE === 'dm' && isActive) ? '' : 'none');
    if (moveRow) {
      const turnIndex = Math.max(0, Number(combat.turn) || 0); const current = isActive ? (coms[turnIndex] || null) : null; const isMyTurn = !!(current && isMyToken(env, current.token_id)); const deathSaves = current?.death_saves || current?.deathSaves || null; const needsDeathSave = !!(current && current.owner_id && Number(current.hp ?? 1) <= 0 && !deathSaves?.dead); const moveState = (combat && combat.movement && current && String(combat.movement.token_id || '') === String(current.token_id || '')) ? combat.movement : null; const speedFt = Number(moveState?.speed_ft ?? 0); const bonusFt = Number(moveState?.bonus_ft ?? 0); const spentFt = Number(moveState?.spent_ft ?? 0); const totalFt = Math.max(0, speedFt + bonusFt); const diffOn = !!moveState?.difficult_terrain; const dashUsed = !!moveState?.dash_used; const disengaged = !!moveState?.disengaged; const canShow = !!(isActive && current && (env.ROLE === 'dm' || isMyTurn)); setDisplay(moveRow, canShow ? 'flex' : 'none');
      if (canShow) {
        const canPlayerAct = !!isMyTurn; const canEndTurn = !!(env.ROLE === 'dm' || canPlayerAct);
        if (needsDeathSave) {
          const dsSuccess = Math.max(0, Number(deathSaves?.successes ?? 0) || 0); const dsFails = Math.max(0, Number(deathSaves?.fails ?? 0) || 0);
          moveRow.innerHTML = `<button class="combat-btn small primary" onclick="combatRollDeathSave()" ${(env.ROLE !== 'dm' && !canPlayerAct) ? 'disabled' : ''}>Roll Death Save</button>${canEndTurn ? '<button class="combat-btn small" onclick="combatEndTurn()">End Turn</button>' : ''}<span style="margin-left:auto;font-size:0.62rem;color:var(--parchment-dim);white-space:nowrap;">Death Saves ${dsSuccess}/3 ✓ • ${dsFails}/3 ✗</span>`;
        } else {
          const selectedTarget = getSelectedTarget(env);
          const selectedTargetName = selectedTarget ? (selectedTarget.name || 'Selected target') : 'No target';
          const pendingAttack = combat.pending_attack || null;
          const pendingHtml = (env.ROLE === 'dm' && pendingAttack)
            ? `<span class="combat-btn small" style="pointer-events:none;opacity:0.85;">${pendingAttack.attacker_name || 'Attacker'} → ${pendingAttack.target_name || 'Target'} · ${String(pendingAttack.attack_kind || 'weapon').replace('_',' ')}</span><button class="combat-btn small primary" onclick="combatResolvePending('hit')">Succeed</button><button class="combat-btn small" onclick="combatResolvePending('miss')">Fail</button>`
            : '';
          const attackHtml = `<button class="combat-btn small" onclick="combatArmTarget()" ${(env.ROLE !== 'dm' && !canPlayerAct) ? 'disabled' : ''}>${env.getCombatTargeting() ? 'Pick Target…' : 'Select Target'}</button><button class="combat-btn small primary" onclick="combatAttackSelected('weapon')" ${(env.ROLE !== 'dm' && !canPlayerAct) || !selectedTarget ? 'disabled' : ''}>Weapon Attack</button><button class="combat-btn small" onclick="combatAttackSelected('spell')" ${(env.ROLE !== 'dm' && !canPlayerAct) || !selectedTarget ? 'disabled' : ''}>Spell Attack</button><span style="font-size:0.62rem;color:var(--parchment-dim);white-space:nowrap;">Target: ${selectedTargetName}</span>${pendingHtml}`;
          moveRow.innerHTML = `<button class="combat-btn small primary" onclick="combatDash()" ${(env.ROLE !== 'dm' && !canPlayerAct) || dashUsed || speedFt <= 0 ? 'disabled' : ''}>Dash +${Math.round(speedFt || 0)} ft</button><button class="combat-btn small ${diffOn ? 'primary' : ''}" onclick="combatToggleDifficultTerrain()" ${(env.ROLE !== 'dm' && !canPlayerAct) ? 'disabled' : ''}>${diffOn ? 'Difficult Terrain: ON' : 'Difficult Terrain'}</button><button class="combat-btn small ${disengaged ? 'primary' : ''}" onclick="combatToggleDisengage()" ${(env.ROLE !== 'dm' && !canPlayerAct) ? 'disabled' : ''}>${disengaged ? 'Disengaged' : 'Disengage'}</button>${env.ROLE === 'dm' ? '<button class="combat-btn small" onclick="combatResetMovement()">Reset Move</button>' : ''}${canEndTurn ? '<button class="combat-btn small primary" onclick="combatEndTurn()">End Turn</button>' : ''}<span style="margin-left:auto;font-size:0.62rem;color:var(--parchment-dim);white-space:nowrap;">${Math.round(spentFt)}/${Math.round(totalFt)} ft${bonusFt > 0 ? ' • dash' : ''}${diffOn ? ' • x2 cost' : ''}${disengaged ? ' • disengaged' : ''}</span><div style="display:flex;gap:0.35rem;flex-wrap:wrap;width:100%;margin-top:0.35rem;align-items:center;">${attackHtml}</div>`;
        }
      } else moveRow.innerHTML = '';
    }
    if (!coms.length) { list.innerHTML = ''; if (empty) { setDisplay(empty, 'block'); list.appendChild(empty); } return; }
    if (empty) setDisplay(empty, 'none'); list.innerHTML = '';
    coms.forEach((com, i) => {
      const isCurrent = isActive && i === combat.turn; const canRoll = canRollInitiative(env, com, i); const entry = env.document.createElement('div'); entry.className = 'combat-entry' + (isCurrent ? ' current' : '');
      let initCell = ''; const hasRolled = com.initiative !== null && com.initiative !== undefined;
      if (canRoll && !hasRolled) initCell = `<span class="ce-init ce-roll" onclick="combatRollInitiative('${com.id}')" title="Roll d20 initiative">🎲</span>`;
      else if (canRoll && hasRolled) initCell = `<span class="ce-init ce-editable" onclick="combatRollInitiative('${com.id}')" title="Reroll initiative">${com.initiative}</span>`;
      else if (env.ROLE === 'dm') initCell = `<span class="ce-init ce-editable" onclick="combatEditInit(${i})" title="Edit initiative">${com.initiative ?? '—'}</span>`;
      else initCell = `<span class="ce-init">${com.initiative ?? '—'}</span>`;
      const _isDmToken = !com.owner_id; const _showCombatHp = (com.hp !== undefined && com.hp !== null && com.max_hp) && ((env.ROLE === 'dm' && _isDmToken) || (env.ROLE === 'player' && com.owner_id === env.USER_ID)); const hpStr = _showCombatHp ? `<span class="ce-hp">${com.hp}/${com.max_hp}</span>` : ''; const deathSaves = com.death_saves || com.deathSaves || null; const dsStr = deathSaves ? `<span class="ce-hp" style="border-color:rgba(224,112,112,0.28);color:#f0b0b0;">DS ${Math.max(0, Number(deathSaves.successes ?? 0) || 0)}/3 ✓ • ${Math.max(0, Number(deathSaves.fails ?? 0) || 0)}/3 ✗${deathSaves.dead ? ' • Dead' : ''}</span>` : '';
      const isTargeted = String(com.token_id || '') && String(com.token_id || '') === String(combat.selected_target_id || ''); const targetStr = isTargeted ? `<span class="ce-hp" style="border-color:rgba(255,210,90,0.45);color:#ffe9a6;">Targeted</span>` : ''; const moveState = (isCurrent && combat?.movement && String(combat.movement.token_id || '') === String(com.token_id || '')) ? combat.movement : null; const speedFt = Number(moveState?.speed_ft ?? 0); const bonusFt = Number(moveState?.bonus_ft ?? 0); const spentFt = Number(moveState?.spent_ft ?? 0); const totalFt = Math.max(0, speedFt + bonusFt); const moveExtras = `${bonusFt > 0 ? ' • Dash' : ''}${moveState?.difficult_terrain ? ' • DT x2' : ''}${moveState?.disengaged ? ' • Disengaged' : ''}`; const moveStr = (moveState && totalFt > 0) ? `<span class="ce-hp" style="border-color:rgba(0,212,212,0.25);color:var(--cyan);">Move ${Math.round(spentFt)}/${Math.round(totalFt)} ft${moveExtras}</span>` : ''; const arrow = isCurrent ? '<span class="ce-arrow">◀</span>' : ''; const delBtn = env.ROLE === 'dm' ? `<span class="ce-del" onclick="combatRemove(${i})">✕</span>` : '';
      entry.innerHTML = `${initCell}<span class="ce-color" style="background:${com.color||'#888'};box-shadow:0 0 4px ${com.color||'#888'}88;"></span><span class="ce-name">${com.name}</span>${targetStr}${hpStr}${dsStr}${moveStr}${arrow}${delBtn}`;
      if (isCurrent) setTimeout(() => entry.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 50);
      list.appendChild(entry);
    });
  }
  function combatStart(env) {
    if (env.ROLE !== 'dm') return; const mapCtx = env._currentPoi ? (env._currentPoi.id || '__local__') : 'world'; const mapTokens = Object.values(env.tokens).filter(t => (t.map_context || 'world') === mapCtx && !t.hidden); if (!mapTokens.length) { env.showToast('No tokens on this map'); return; }
    const coms = mapTokens.map(t => { let initMod = 0; if (t.initiativeMod !== undefined) initMod = parseInt(t.initiativeMod) || 0; else if (t.owner_id === env.USER_ID && env._charSheet?.initiative) initMod = parseInt(env._charSheet.initiative) || 0; return { id: Math.random().toString(36).slice(2), token_id: t.id, name: t.name, color: t.color, initiative: null, modifier: initMod, hp: t.hp ?? null, max_hp: t.maxHp ?? null, speed: (t.speed !== undefined && t.speed !== null && t.speed !== '') ? (parseInt(t.speed, 10) || 0) : null, is_player: !!t.owner_id, owner_id: t.owner_id || null }; });
    env.setCombat({ active: true, turn: 0, combatants: coms, round: 1 }); env.setCombatRound(1); env.sendWS({ type: 'combat_update', payload: { ...env.getCombat(), round: 1 } }); env.showToast('Combat started — roll initiative!');
  }
  function combatNext(env) { if (!env.getCombat().combatants.length) return; env.sendWS({ type: 'combat_next', payload: {} }); }
  function combatPrev(env) { if (!env.getCombat().combatants.length) return; env.sendWS({ type: 'combat_prev', payload: {} }); }
  function combatClear(env) { if (!env.confirm('End combat and clear the initiative order?')) return; env.sendWS({ type: 'combat_clear', payload: {} }); }
  function combatDash(env) { env.sendWS({ type: 'combat_dash', payload: {} }); }
  function combatToggleDifficultTerrain(env) { const enabled = !(env.getCombat()?.movement?.difficult_terrain); env.sendWS({ type: 'combat_toggle_difficult_terrain', payload: { enabled } }); }
  function combatResetMovement(env) { if (env.ROLE !== 'dm') return; env.sendWS({ type: 'combat_reset_movement', payload: {} }); }
  function combatToggleDisengage(env) { env.sendWS({ type: 'combat_toggle_disengage', payload: { enabled: !(env.getCombat()?.movement?.disengaged) } }); }
  function combatEndTurn(env) { env.sendWS({ type: 'combat_end_turn', payload: {} }); }
  function combatRollDeathSave(env) { env.sendWS({ type: 'combat_death_save', payload: {} }); }
  function combatRollInitiative(env, combatantId) {
    const combat = env.getCombat(); const com = combat.combatants.find(c => c.id === combatantId); if (!com) return; let modifier = parseInt(com.modifier) || 0; const combatTok = com.token_id ? env.tokens[com.token_id] : null; if (combatTok && combatTok.initiativeMod !== undefined) { modifier = parseInt(combatTok.initiativeMod) || 0; com.modifier = modifier; } else if (com.token_id && env.tokens[com.token_id]?.owner_id === env.USER_ID && env._charSheet?.initiative !== undefined) { modifier = parseInt(env._charSheet.initiative) || 0; com.modifier = modifier; } else if (com.token_id && env.tokens[com.token_id]?.owner_id === env.USER_ID) { modifier = _resolveCombatModifier(env, 'initiative'); com.modifier = modifier; }
    const roll = Math.floor(Math.random() * 20) + 1; const total = roll + modifier; com.initiative = total; const presentLocalInitiative = (globalThis.AppDice && typeof globalThis.AppDice.showLocalResult === 'function') ? globalThis.AppDice.showLocalResult.bind(globalThis.AppDice) : (typeof globalThis.appDiceShowLocalResult === 'function' ? globalThis.appDiceShowLocalResult : (typeof env.appDiceShowLocalResult === 'function' ? env.appDiceShowLocalResult : null)); if (presentLocalInitiative) presentLocalInitiative({ diceType: 20, qty: 1, rolls: [roll], total, modifier, rollLabel: 'Initiative', source: 'combat-initiative-module' }); env.renderCombat(); env.sendWS({ type: 'combat_roll_initiative', payload: { combatant_id: combatantId, roll, modifier } });
  }
  function combatAddManual(env) { const combat = env.getCombat(); const nameEl = env.document.getElementById('ca-name'); const initEl = env.document.getElementById('ca-init'); const name = (nameEl?.value || '').trim(); if (!name) { nameEl?.focus(); return; } const init = parseInt(initEl?.value) || null; combat.combatants.push({ id: Math.random().toString(36).slice(2), token_id: null, name, color: '#888888', initiative: init, hp: null, max_hp: null, is_player: false }); if (init !== null) sortCombatants(env); if (nameEl) nameEl.value = ''; if (initEl) initEl.value = ''; pushCombat(env); }
  function combatRemove(env, idx) { const combat = env.getCombat(); combat.combatants.splice(idx, 1); if (combat.turn >= combat.combatants.length) combat.turn = Math.max(0, combat.combatants.length - 1); pushCombat(env); }
  function combatEditInit(env, idx) { const combat = env.getCombat(); const com = combat.combatants[idx]; if (!com) return; const val = env.prompt(`Initiative for ${com.name}:`, com.initiative ?? ''); if (val === null) return; const n = parseInt(val); com.initiative = isNaN(n) ? null : n; sortCombatants(env); pushCombat(env); }
  function sortCombatants(env) { const combat = env.getCombat(); combat.combatants.sort((a, b) => (b.initiative ?? -99) - (a.initiative ?? -99)); }
  function pushCombat(env) { env.sendWS({ type: 'combat_update', payload: { ...env.getCombat(), round: env.getCombatRound() } }); }
  function combatArmTarget(env) {
    if (!canActCurrentTurn(env)) { env.showToast('Only the active combatant can pick a target.'); return false; }
    env.setCombatTargeting(true);
    env.showToast('Click a token on the map to target it.');
    env.renderCombat();
    return true;
  }
  function combatSelectTarget(env, tokenId) {
    if (!canActCurrentTurn(env)) return false;
    const target = tokenId ? env.tokens[tokenId] : null;
    if (!target) { env.showToast('No valid target there.'); return false; }
    env.setCombatTargeting(false);
    env.sendWS({ type: 'combat_select_target', payload: { target_id: tokenId } });
    env.pulseCombatTarget(tokenId);
    return true;
  }
  function combatAttackSelected(env, attackKind) {
    if (!canActCurrentTurn(env)) { env.showToast('Only the active combatant can attack.'); return false; }
    const target = getSelectedTarget(env);
    if (!target) { env.showToast('Select a target first.'); return false; }
    const useSpell = attackKind === 'spell';
    const attackModifier = useSpell ? _resolveCombatModifier(env, 'attack_spell') : _resolveCombatModifier(env, 'attack_str');
    const profBonus = parseInt((_runtimeCombat(env).proficiencyBonus), 10) || 0;
    const abilityBonus = useSpell ? (attackModifier - profBonus) : (parseInt((_runtimeCombat(env).attackBonus || {}).str, 10) || attackModifier - profBonus);
    const roll = Math.floor(Math.random() * 20) + 1;
    const total = roll + attackModifier;
    env.addLogEntry({
      id: 'combat_attack_preview_' + Date.now(),
      type: 'combat',
      user: env.getUserName ? env.getUserName() : 'Combat',
      message: `Attack: d20 (${roll}) + ${useSpell ? 'Spell' : 'STR'} (${_signed(abilityBonus)}) + Prof (${_signed(profBonus)}) = ${total} — HIT`,
      timestamp: Date.now() / 1000,
    });
    env.sendWS({ type: 'combat_attack_request', payload: { target_id: target.id, attack_kind: String(attackKind || 'weapon') } });
    env.showToast(`Attack sent: ${attackKind === 'spell' ? 'Spell' : 'Weapon'} → ${target.name || 'target'}`);
    return true;
  }
  function combatResolvePending(env, outcome) {
    if (env.ROLE !== 'dm') return false;
    env.sendWS({ type: 'combat_attack_override', payload: { result: outcome === 'hit' ? 'hit' : 'miss' } });
    return true;
  }
  window.AppGameplayCombat = { isMyToken, canRollInitiative, combatApplyState, renderCombat, combatStart, combatNext, combatPrev, combatClear, combatDash, combatToggleDifficultTerrain, combatResetMovement, combatToggleDisengage, combatEndTurn, combatRollDeathSave, combatRollInitiative, combatAddManual, combatRemove, combatEditInit, sortCombatants, pushCombat, combatArmTarget, combatSelectTarget, combatAttackSelected, combatResolvePending };
})();
