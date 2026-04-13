
(function(){
  function _setElVal(doc, id, v) { const e = doc.getElementById(id); if (e) e.value = v; }
  function _setElChecked(doc, id, v) { const e = doc.getElementById(id); if (e) e.checked = v; }
  function getHazardFormPayload(env) {
    return {
      name: env.document.getElementById('haz-name')?.value || 'Hazard Zone',
      trigger: env.document.getElementById('haz-trigger')?.value || 'enter',
      effect: env.document.getElementById('haz-effect')?.value || 'damage',
      radius_ft: Number(env.document.getElementById('haz-radius')?.value || 15),
      dice_num: Number(env.document.getElementById('haz-dice-num')?.value || 2),
      dice_sides: Number(env.document.getElementById('haz-dice-sides')?.value || 6),
      flat_bonus: Number(env.document.getElementById('haz-flat')?.value || 0),
      save: env.document.getElementById('haz-save')?.value || '',
      save_dc: Number(env.document.getElementById('haz-dc')?.value || 0),
      condition: env.document.getElementById('haz-condition')?.value || '',
      duration_sec: Number(env.document.getElementById('haz-duration')?.value || 0),
      once_per_round: !!env.document.getElementById('haz-once')?.checked,
      hidden_from_players: !!env.document.getElementById('haz-hidden')?.checked,
      color: env.document.getElementById('haz-color')?.value || '#e67e22',
      icon: env.document.getElementById('haz-icon')?.value || '',
      map_context: env.getCurrentMapContext(),
      x: -env.cam.x,
      y: -env.cam.y,
    };
  }
  function updateHazardFormUi(env) {
    const banner = env.document.getElementById('haz-edit-banner');
    const saveBtn = env.document.getElementById('haz-save-btn');
    const cancelBtn = env.document.getElementById('haz-cancel-btn');
    const editZoneId = env.getHazardEditZoneId();
    if (banner) {
      if (editZoneId) {
        const zone = env.hazardZones[editZoneId] || null;
        banner.style.display = '';
        banner.textContent = `Editing ${zone?.name || 'hazard zone'} — save changes, or use Click / Drag Place to move and resize it.`;
      } else {
        banner.style.display = 'none';
        banner.textContent = '';
      }
    }
    if (saveBtn) saveBtn.textContent = editZoneId ? 'Save Changes' : 'Create At View Center';
    if (cancelBtn) cancelBtn.style.display = editZoneId ? '' : 'none';
  }
  function populateHazardForm(env, zone) {
    if (!zone) return;
    const doc = env.document;
    _setElVal(doc, 'haz-name', zone.name || 'Hazard Zone');
    _setElVal(doc, 'haz-trigger', zone.trigger || 'enter');
    _setElVal(doc, 'haz-effect', zone.effect || 'damage');
    _setElVal(doc, 'haz-radius', Number(zone.radius_ft || 15));
    _setElVal(doc, 'haz-dice-num', Number(zone.dice_num || 2));
    _setElVal(doc, 'haz-dice-sides', Number(zone.dice_sides || 6));
    _setElVal(doc, 'haz-flat', Number(zone.flat_bonus || 0));
    _setElVal(doc, 'haz-save', zone.save || '');
    _setElVal(doc, 'haz-dc', Number(zone.save_dc || 0));
    _setElVal(doc, 'haz-condition', zone.condition || '');
    _setElVal(doc, 'haz-duration', Number(zone.duration_sec || 0));
    _setElChecked(doc, 'haz-once', !!zone.once_per_round);
    _setElChecked(doc, 'haz-hidden', !!zone.hidden_from_players);
    _setElVal(doc, 'haz-color', zone.color || '#e67e22');
    _setElVal(doc, 'haz-icon', zone.icon || '');
  }
  function resetHazardForm(env) {
    env.setHazardEditZoneId('');
    env.setHazardPlacementMode(null);
    env.setHazardPlacementDraft(null);
    const doc = env.document;
    _setElVal(doc, 'haz-name', '');
    _setElVal(doc, 'haz-trigger', 'enter');
    _setElVal(doc, 'haz-effect', 'damage');
    _setElVal(doc, 'haz-radius', 15);
    _setElVal(doc, 'haz-dice-num', 2);
    _setElVal(doc, 'haz-dice-sides', 6);
    _setElVal(doc, 'haz-flat', 0);
    _setElVal(doc, 'haz-save', '');
    _setElVal(doc, 'haz-dc', 0);
    _setElVal(doc, 'haz-condition', '');
    _setElVal(doc, 'haz-duration', 15);
    _setElChecked(doc, 'haz-once', false);
    _setElChecked(doc, 'haz-hidden', false);
    _setElVal(doc, 'haz-color', '#e67e22');
    _setElVal(doc, 'haz-icon', '');
    updateHazardFormUi(env);
    env.drawFrame();
  }
  function editHazardZone(env, zoneId) { const zone = env.hazardZones[zoneId]; if (!zone) return; env.setHazardEditZoneId(zoneId); populateHazardForm(env, zone); updateHazardFormUi(env); }
  function saveHazardZoneFromForm(env) {
    if (env.ROLE !== 'dm') return;
    const payload = getHazardFormPayload(env);
    const zoneId = env.getHazardEditZoneId();
    if (zoneId && env.hazardZones[zoneId]) {
      const existing = env.hazardZones[zoneId];
      payload.x = Number(existing.x || payload.x);
      payload.y = Number(existing.y || payload.y);
      env.sendWS({ type:'hazard_zone_update', payload:{ ...payload, zone_id: zoneId } });
    } else env.sendWS({ type:'hazard_zone_create', payload });
  }
  function useViewCenterForHazard(env) {
    if (env.ROLE !== 'dm') return;
    const payload = getHazardFormPayload(env); payload.x = -env.cam.x; payload.y = -env.cam.y;
    const zoneId = env.getHazardEditZoneId();
    if (zoneId && env.hazardZones[zoneId]) env.sendWS({ type:'hazard_zone_update', payload:{ ...payload, zone_id: zoneId } });
    else env.sendWS({ type:'hazard_zone_create', payload });
  }
  function beginHazardPlacement(env, zoneId = null) {
    if (env.ROLE !== 'dm') return;
    if (zoneId && env.hazardZones[zoneId]) { editHazardZone(env, zoneId); env.setHazardPlacementMode('edit'); }
    else env.setHazardPlacementMode(env.getHazardEditZoneId() ? 'edit' : 'create');
    env.setHazardPlacementDraft(null);
    env.showToast('Click to place hazard center, drag to size, release to save. Right-click cancels.');
    env.drawFrame();
  }
  function commitHazardPlacement(env) {
    const draft = env.getHazardPlacementDraft(); if (!draft) return;
    const payload = { ...getHazardFormPayload(env), x: Number(draft.x || 0), y: Number(draft.y || 0), radius_ft: Number(draft.radius_ft || 15) };
    const zoneId = env.getHazardEditZoneId();
    if ((env.getHazardPlacementMode() === 'edit' || zoneId) && env.hazardZones[zoneId]) env.sendWS({ type:'hazard_zone_update', payload:{ ...payload, zone_id: zoneId } });
    else env.sendWS({ type:'hazard_zone_create', payload });
    env.setHazardPlacementMode(null); env.setHazardPlacementDraft(null);
  }
  function cancelHazardPlacement(env, showMsg = true) { if (!env.getHazardPlacementMode() && !env.getHazardPlacementDraft()) return; env.setHazardPlacementMode(null); env.setHazardPlacementDraft(null); if (showMsg) env.showToast('Hazard placement cancelled.'); env.drawFrame(); }
  function createHazardZoneAtView(env) { saveHazardZoneFromForm(env); }
  function deleteHazardZone(env, zoneId) { if (!zoneId) return; env.sendWS({ type:'hazard_zone_delete', payload:{ zone_id: zoneId } }); }
  function applyHazardZone(env, zoneId) { if (!zoneId) return; env.sendWS({ type:'hazard_zone_apply', payload:{ zone_id: zoneId } }); }
  window.AppGameplayHazards = { getHazardFormPayload, updateHazardFormUi, populateHazardForm, resetHazardForm, editHazardZone, saveHazardZoneFromForm, useViewCenterForHazard, beginHazardPlacement, commitHazardPlacement, cancelHazardPlacement, createHazardZoneAtView, deleteHazardZone, applyHazardZone };
})();
