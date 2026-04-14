(function initCharacterBuilderStepEquipment(global) {
  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function registerStep(step) {
    if (!global.CharacterBuilderStepModules || typeof global.CharacterBuilderStepModules !== 'object') {
      global.CharacterBuilderStepModules = {};
    }
    global.CharacterBuilderStepModules[step.id] = step;
  }

  registerStep({
    id: 'equipment',
    label: 'Equipment',
    render: function renderEquipmentStep(context) {
      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const equipment = draft.equipment && typeof draft.equipment === 'object' ? draft.equipment : {};
      const currency = equipment.currency && typeof equipment.currency === 'object'
        ? equipment.currency
        : { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
      const choices = Array.isArray(equipment.choices) ? equipment.choices : [];

      return [
        '<div class="screen-header">',
        '<div class="screen-title">Starting Equipment</div>',
        '<div class="screen-divider"></div>',
        '<div class="screen-subtitle">Record your starting gear and gold. Your DM may adjust this based on campaign context.</div>',
        '</div>',

        '<div class="field"><label>Starting Equipment Pack</label>',
        '<input type="text" data-builder-path="equipment.startingPack" value="' + escHtml(equipment.startingPack || '') + '" maxlength="120" placeholder="Explorer\'s Pack, Dungeoneer\'s Pack\u2026" /></div>',

        '<div class="field"><label>Additional Equipment <span class="cb-optional">comma-separated</span></label>',
        '<input type="text" data-builder-equipment-choices="1" value="' + escHtml(choices.join(', ')) + '" maxlength="420" placeholder="Longsword, Shield, Chain Shirt\u2026" />',
        '<div class="builder-help-text">List any weapons, armor, or items not covered by your pack.</div>',
        '</div>',

        '<div class="field"><label>Starting Currency</label>',
        '<div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;">',
        ['cp', 'sp', 'ep', 'gp', 'pp'].map(function toCoin(coin) {
          return '<label style="display:flex;flex-direction:column;gap:3px;font-size:0.65rem;">'
            + escHtml(coin.toUpperCase())
            + '<input type="number" min="0" max="99999" step="1" data-builder-path="equipment.currency.' + coin + '" value="' + escHtml(currency[coin] != null ? currency[coin] : 0) + '" />'
            + '</label>';
        }).join(''),
        '</div></div>',
      ].join('');
    },
    bind: function bindEquipmentStep(root, context) {
      if (!context || typeof context.onSetField !== 'function') return;
      const choicesInput = root.querySelector('[data-builder-equipment-choices="1"]');
      if (!choicesInput) return;
      choicesInput.addEventListener('input', function onChoicesInput() {
        const list = String(choicesInput.value || '')
          .split(',')
          .map(function normalize(v) { return String(v || '').trim(); })
          .filter(Boolean);
        context.onSetField(['equipment', 'choices'], list);
      });
    },
  });
})(window);
