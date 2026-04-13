(function(){
  function _setElVal(doc, id, v) { const e = doc.getElementById(id); if (e) e.value = v; }
  const CLEAR_IDS = ['rules-custom-id','rules-custom-name','rules-custom-school','rules-custom-source','rules-custom-casting','rules-custom-range','rules-custom-components','rules-custom-duration','rules-custom-damage-type','rules-custom-healing-type','rules-custom-base-formula','rules-custom-effect','rules-custom-higher','rules-custom-scaling-data','rules-custom-tags','rules-custom-classes'];
  const DEFAULTS = {
    'rules-custom-level': '0', 'rules-custom-source': 'DM Custom', 'rules-custom-concentration': '0', 'rules-custom-ritual': '0',
    'rules-custom-attack-type': '', 'rules-custom-save': '', 'rules-custom-scaling-type': 'none'
  };
  function resetCustomSpellRuleForm(env) {
    const doc = env.document;
    CLEAR_IDS.forEach(id => { const el = doc.getElementById(id); if (el) el.value = ''; });
    Object.entries(DEFAULTS).forEach(([id, value]) => { const el = doc.getElementById(id); if (el) el.value = value; });
  }
  function prefillCustomSpellRule(env, name) {
    resetCustomSpellRuleForm(env);
    const el = env.document.getElementById('rules-custom-name');
    if (el) el.value = name || '';
  }
  function loadCustomSpellIntoForm(env, spellId) {
    const item = (env.getCustomSpells() || []).find(sp => String(sp.id) === String(spellId));
    if (!item) return;
    const doc = env.document;
    _setElVal(doc, 'rules-custom-id', item.id || '');
    _setElVal(doc, 'rules-custom-name', item.name || '');
    _setElVal(doc, 'rules-custom-level', item.spell_level ?? 0);
    _setElVal(doc, 'rules-custom-school', item.school || '');
    _setElVal(doc, 'rules-custom-source', item.source || 'DM Custom');
    _setElVal(doc, 'rules-custom-casting', item.casting_time || '');
    _setElVal(doc, 'rules-custom-range', item.range || '');
    _setElVal(doc, 'rules-custom-components', item.components || '');
    _setElVal(doc, 'rules-custom-duration', item.duration || '');
    _setElVal(doc, 'rules-custom-concentration', item.concentration ? '1' : '0');
    _setElVal(doc, 'rules-custom-ritual', item.ritual ? '1' : '0');
    _setElVal(doc, 'rules-custom-attack-type', item.attack_type || '');
    _setElVal(doc, 'rules-custom-save', item.save_ability || '');
    _setElVal(doc, 'rules-custom-damage-type', item.damage_type || '');
    _setElVal(doc, 'rules-custom-healing-type', item.healing_type || '');
    _setElVal(doc, 'rules-custom-base-formula', item.base_damage_formula || '');
    _setElVal(doc, 'rules-custom-effect', item.base_effect_text || '');
    _setElVal(doc, 'rules-custom-higher', item.higher_level_text || '');
    _setElVal(doc, 'rules-custom-scaling-type', item.scaling_type || 'none');
    _setElVal(doc, 'rules-custom-scaling-data', JSON.stringify(item.scaling_data || {}, null, 2));
    _setElVal(doc, 'rules-custom-tags', (item.tags || []).join(', '));
    _setElVal(doc, 'rules-custom-classes', (item.class_lists || []).join(', '));
  }
  function collectCustomSpellRuleForm(env) {
    const doc = env.document;
    let scalingData = {};
    const scalingRaw = String(doc.getElementById('rules-custom-scaling-data')?.value || '').trim();
    if (scalingRaw) {
      try { scalingData = JSON.parse(scalingRaw); }
      catch (err) { throw new Error('Scaling Data JSON is invalid'); }
    }
    return {
      id: String(doc.getElementById('rules-custom-id')?.value || '').trim() || undefined,
      name: String(doc.getElementById('rules-custom-name')?.value || '').trim(),
      spell_level: parseInt(doc.getElementById('rules-custom-level')?.value || '0', 10) || 0,
      school: String(doc.getElementById('rules-custom-school')?.value || '').trim(),
      source: String(doc.getElementById('rules-custom-source')?.value || 'DM Custom').trim(),
      casting_time: String(doc.getElementById('rules-custom-casting')?.value || '').trim(),
      range: String(doc.getElementById('rules-custom-range')?.value || '').trim(),
      components: String(doc.getElementById('rules-custom-components')?.value || '').trim(),
      duration: String(doc.getElementById('rules-custom-duration')?.value || '').trim(),
      concentration: doc.getElementById('rules-custom-concentration')?.value === '1',
      ritual: doc.getElementById('rules-custom-ritual')?.value === '1',
      attack_type: String(doc.getElementById('rules-custom-attack-type')?.value || '').trim(),
      save_ability: String(doc.getElementById('rules-custom-save')?.value || '').trim(),
      damage_type: String(doc.getElementById('rules-custom-damage-type')?.value || '').trim(),
      healing_type: String(doc.getElementById('rules-custom-healing-type')?.value || '').trim(),
      base_damage_formula: String(doc.getElementById('rules-custom-base-formula')?.value || '').trim(),
      base_effect_text: String(doc.getElementById('rules-custom-effect')?.value || '').trim(),
      higher_level_text: String(doc.getElementById('rules-custom-higher')?.value || '').trim(),
      scaling_type: String(doc.getElementById('rules-custom-scaling-type')?.value || 'none').trim(),
      scaling_data: scalingData,
      tags: String(doc.getElementById('rules-custom-tags')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
      class_lists: String(doc.getElementById('rules-custom-classes')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
    };
  }
  window.AppUISpellForm = { resetCustomSpellRuleForm, prefillCustomSpellRule, loadCustomSpellIntoForm, collectCustomSpellRuleForm };
})();
