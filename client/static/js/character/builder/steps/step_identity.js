(function initCharacterBuilderStepIdentity(global) {
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

  function sectionHeader(icon, title, subtitle) {
    return [
      '<div class="cb-section-header">',
      '<div class="cb-section-icon">' + icon + '</div>',
      '<div class="cb-section-header-text">',
      '<div class="cb-section-title">' + title + '</div>',
      subtitle ? '<div class="cb-section-subtitle">' + subtitle + '</div>' : '',
      '</div>',
      '</div>',
    ].join('');
  }

  registerStep({
    id: 'identity',
    label: 'Identity',
    render: function renderIdentityStep(context) {
      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const identity = draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
      const presentation = draft.presentation && typeof draft.presentation === 'object' ? draft.presentation : {};
      const portraitFrame = String(presentation.portraitFrame || 'classic');
      const gender = identity.gender === 'female' ? 'female' : 'male';

      return [
        // ── Core Identity ─────────────────────────────────────────────
        '<div class="cb-section">',
        sectionHeader('✦', 'Core Identity', 'Name your hero and set their defining traits.'),

        '<div class="cb-field-row cb-field-row--full" style="margin-bottom:12px;">',
        '<div class="field">',
        '<label data-builder-tooltip="identity">Character Name</label>',
        '<input type="text" class="cb-input-hero" data-builder-path="identity.name"',
        ' value="' + escHtml(identity.name || '') + '" maxlength="60"',
        ' placeholder="Enter your character\'s full name…" />',
        '</div>',
        '</div>',

        '<div class="cb-field-row cb-field-row--2col">',

        '<div class="field">',
        '<label>Sex</label>',
        '<select data-builder-path="identity.gender" id="cb-gender-select">',
        '<option value="male"' + (gender === 'male' ? ' selected' : '') + '>Male</option>',
        '<option value="female"' + (gender === 'female' ? ' selected' : '') + '>Female</option>',
        '</select>',
        '</div>',

        '<div class="field">',
        '<label>Homeland <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-path="identity.homeland"',
        ' value="' + escHtml(identity.homeland || '') + '" maxlength="80"',
        ' placeholder="Waterdeep, Neverwinter…" />',
        '</div>',

        '<div class="field">',
        '<label>Alignment <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-path="identity.alignment"',
        ' value="' + escHtml(identity.alignment || '') + '" maxlength="60"',
        ' placeholder="Neutral Good" />',
        '</div>',

        '<div class="field">',
        '<label>Deity <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-path="identity.deity"',
        ' value="' + escHtml(identity.deity || '') + '" maxlength="80"',
        ' placeholder="Kelemvor, Sehanine…" />',
        '</div>',

        '</div>',

        '<div class="cb-field-row cb-field-row--full" style="margin-top:4px;">',
        '<div class="field">',
        '<label>Display Name <span class="cb-optional">optional — shown in party UI</span></label>',
        '<input type="text" data-builder-path="identity.displayName"',
        ' value="' + escHtml(identity.displayName || '') + '" maxlength="60"',
        ' placeholder="Short name shown to other players" />',
        '</div>',
        '</div>',

        '</div>',

        // ── Presentation ──────────────────────────────────────────────
        '<div class="cb-section">',
        sectionHeader('◈', 'Portrait & Token', 'Choose a frame style and link your artwork.'),

        '<div class="cb-portrait-frame-row">',
        ['classic', 'rune', 'shadow'].map(function(frame) {
          var label = frame === 'classic' ? 'Classic' : frame === 'rune' ? 'Runic' : 'Shadow';
          var active = portraitFrame === frame ? ' cb-frame-opt--active' : '';
          return [
            '<button type="button" class="cb-frame-opt' + active + '"',
            ' data-cb-frame="' + frame + '">',
            '<div class="cb-frame-preview cb-frame-preview--' + frame + '"></div>',
            '<span>' + label + '</span>',
            '</button>',
          ].join('');
        }).join(''),
        '<input type="hidden" data-builder-path="presentation.portraitFrame"',
        ' value="' + escHtml(portraitFrame) + '" id="cb-portrait-frame-input" />',
        '</div>',

        '<div class="cb-field-row cb-field-row--2col">',
        '<div class="field">',
        '<label>Portrait URL <span class="cb-optional">optional</span></label>',
        '<input type="url" data-builder-path="identity.portraitUrl"',
        ' value="' + escHtml(identity.portraitUrl || '') + '" maxlength="500"',
        ' placeholder="https://…" />',
        '</div>',
        '<div class="field">',
        '<label>Token URL <span class="cb-optional">optional</span></label>',
        '<input type="url" data-builder-path="identity.tokenImageUrl"',
        ' value="' + escHtml(identity.tokenImageUrl || '') + '" maxlength="500"',
        ' placeholder="https://…" />',
        '</div>',
        '</div>',

        '</div>',

        // ── Backstory ─────────────────────────────────────────────────
        '<div class="cb-section">',
        sectionHeader('❧', 'Backstory', 'A short concept and any roleplay notes you want to keep handy.'),

        '<div class="cb-field-row cb-field-row--2col">',

        '<div class="field">',
        '<label>Backstory <span class="cb-optional">optional</span></label>',
        '<textarea data-builder-path="identity.backstory" maxlength="1000"',
        ' placeholder="One-paragraph concept — origin, motivation, dark secret…"',
        ' rows="5">' + escHtml(identity.backstory || '') + '</textarea>',
        '<div class="cb-char-count">' + String(identity.backstory || '').length + ' / 1000</div>',
        '</div>',

        '<div class="field">',
        '<label>Notes <span class="cb-optional">optional</span></label>',
        '<textarea data-builder-path="identity.notes" maxlength="600"',
        ' placeholder="Personality traits, bonds, flaws, roleplay reminders…"',
        ' rows="5">' + escHtml(identity.notes || '') + '</textarea>',
        '<div class="cb-char-count">' + String(identity.notes || '').length + ' / 600</div>',
        '</div>',

        '</div>',
        '</div>',
      ].join('');
    },

    bind: function bindIdentityStep(root, ctx) {
      // Portrait frame selector
      var frameButtons = root.querySelectorAll('.cb-frame-opt');
      var frameInput = root.querySelector('#cb-portrait-frame-input');
      frameButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
          var frame = btn.dataset.cbFrame;
          frameButtons.forEach(function(b) { b.classList.remove('cb-frame-opt--active'); });
          btn.classList.add('cb-frame-opt--active');
          if (frameInput) frameInput.value = frame;
          if (ctx && typeof ctx.onSetField === 'function') {
            ctx.onSetField(['presentation', 'portraitFrame'], frame);
          }
        });
      });

      // Live char count on textareas
      root.querySelectorAll('textarea[data-builder-path]').forEach(function(ta) {
        var counter = ta.nextElementSibling;
        if (!counter || !counter.classList.contains('cb-char-count')) return;
        var max = parseInt(ta.maxLength, 10) || 0;
        function updateCount() {
          counter.textContent = ta.value.length + (max ? ' / ' + max : '');
          counter.classList.toggle('cb-char-count--warn', max > 0 && ta.value.length > max * 0.85);
        }
        ta.addEventListener('input', updateCount);
      });
    },
  });
})(window);
