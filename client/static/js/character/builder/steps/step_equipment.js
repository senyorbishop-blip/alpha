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
        '<div class="field"><label>Starting Equipment Pack</label>',
        '<input type="text" data-builder-path="equipment.startingPack" value="' + escHtml(equipment.startingPack || '') + '" maxlength="120" placeholder="Explorer\'s Pack" /></div>',
        '<div class="field"><label>Equipment Choices (comma-separated)</label>',
        '<input type="text" data-builder-equipment-choices="1" value="' + escHtml(choices.join(', ')) + '" maxlength="420" placeholder="Longsword, Shield, Chain Shirt" /></div>',
        '<div class="field"><label>Starting Currency</label>',
        '<div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;">',
        ['cp', 'sp', 'ep', 'gp', 'pp'].map(function toCoin(coin) {
          return '<label style="display:flex;flex-direction:column;gap:3px;font-size:0.65rem;">'
            + escHtml(coin.toUpperCase())
            + '<input type="number" min="0" max="99999" step="1" data-builder-path="equipment.currency.' + coin + '" value="' + escHtml(currency[coin] != null ? currency[coin] : 0) + '" />'
            + '</label>';
        }).join(''),
        '</div></div>',
        '<div class="builder-help-text">Equipment and currency are mapped into canonical inventory fields and legacy charBook/charSheet compatibility exports.</div>',
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
