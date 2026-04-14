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

  // Module-level state: which optional sections are currently expanded.
  // This persists across re-renders so typing in a field doesn't collapse sections.
  var _expanded = {
    roleplay: false,
    artwork: false,
    backstory: false,
  };

  registerStep({
    id: 'identity',
    label: 'Identity',
    render: function renderIdentityStep(context) {
      const draft = context && context.draft && typeof context.draft === 'object' ? context.draft : {};
      const identity = draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
      const presentation = draft.presentation && typeof draft.presentation === 'object' ? draft.presentation : {};
      const portraitFrame = String(presentation.portraitFrame || 'classic');
      const GENDER_OPTIONS = ['male', 'female', 'nonbinary', 'custom'];
      const gender = GENDER_OPTIONS.includes(identity.gender) ? identity.gender : 'male';

      function detailsOpen(key) {
        return _expanded[key] ? ' open' : '';
      }

      return [
        // ── Primary: Name ─────────────────────────────────────────────
        '<div class="cb-section">',
        sectionHeader('✦', 'Your Character', 'Give your adventurer a name to begin.'),

        '<div class="cb-field-row cb-field-row--full" style="margin-bottom:10px;">',
        '<div class="field">',
        '<label data-builder-tooltip="identity">Character Name</label>',
        '<input type="text" class="cb-input-hero" data-builder-path="identity.name"',
        ' value="' + escHtml(identity.name || '') + '" maxlength="60"',
        ' placeholder="Enter your character\'s full name\u2026" autofocus />',
        '</div>',
        '</div>',

        '<div class="cb-field-row cb-field-row--2col">',

        '<div class="field">',
        '<label>Sex / Gender</label>',
        '<select data-builder-path="identity.gender" id="cb-gender-select">',
        '<option value="male"' + (gender === 'male' ? ' selected' : '') + '>Male</option>',
        '<option value="female"' + (gender === 'female' ? ' selected' : '') + '>Female</option>',
        '<option value="nonbinary"' + (gender === 'nonbinary' ? ' selected' : '') + '>Nonbinary</option>',
        '<option value="custom"' + (gender === 'custom' ? ' selected' : '') + '>Custom</option>',
        '</select>',
        '</div>',

        '<div class="field">',
        '<label>Alignment <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-path="identity.alignment"',
        ' value="' + escHtml(identity.alignment || '') + '" maxlength="60"',
        ' placeholder="Neutral Good" />',
        '</div>',

        '</div>',

        '<div class="cb-field-row cb-field-row--2col">',

        '<div class="field">',
        '<label>Pronouns <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-path="identity.pronouns"',
        ' value="' + escHtml(identity.pronouns || '') + '" maxlength="60"',
        ' placeholder="they/them, she/her, he/him\u2026" />',
        '</div>',

        '<div class="field">',
        '<label>Age <span class="cb-optional">optional</span></label>',
        '<input type="text" data-builder-path="identity.age"',
        ' value="' + escHtml(identity.age || '') + '" maxlength="40"',
        ' placeholder="Young adult, 30, etc." />',
        '</div>',

        '</div>',
        '</div>',

        // ── Optional: Roleplay Details ────────────────────────────────
        '<details class="cb-optional-section" data-section-key="roleplay"' + detailsOpen('roleplay') + '>',
        '<summary class="cb-optional-section-summary">Roleplay Details <span class="cb-optional">optional</span></summary>',
        '<div class="cb-optional-section-body">',

        '<div class="cb-field-row cb-field-row--2col">',

        '<div class="field">',
        '<label>Homeland</label>',
        '<input type="text" data-builder-path="identity.homeland"',
        ' value="' + escHtml(identity.homeland || '') + '" maxlength="80"',
        ' placeholder="Waterdeep, Neverwinter\u2026" />',
        '</div>',

        '<div class="field">',
        '<label>Deity</label>',
        '<input type="text" data-builder-path="identity.deity"',
        ' value="' + escHtml(identity.deity || '') + '" maxlength="80"',
        ' placeholder="Kelemvor, Sehanine\u2026" />',
        '</div>',

        '</div>',

        '<div class="field">',
        '<label>Display Name <span class="cb-optional">shown in party UI</span></label>',
        '<input type="text" data-builder-path="identity.displayName"',
        ' value="' + escHtml(identity.displayName || '') + '" maxlength="60"',
        ' placeholder="Short name shown to other players" />',
        '</div>',

        '</div>',
        '</details>',

        // ── Optional: Portrait & Artwork ──────────────────────────────
        '<details class="cb-optional-section" data-section-key="artwork"' + detailsOpen('artwork') + '>',
        '<summary class="cb-optional-section-summary">Portrait &amp; Artwork <span class="cb-optional">optional</span></summary>',
        '<div class="cb-optional-section-body">',

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
        '<label>Portrait URL</label>',
        '<input type="url" data-builder-path="identity.portraitUrl"',
        ' value="' + escHtml(identity.portraitUrl || '') + '" maxlength="500"',
        ' placeholder="https://\u2026" />',
        '</div>',
        '<div class="field">',
        '<label>Token URL</label>',
        '<input type="url" data-builder-path="identity.tokenImageUrl"',
        ' value="' + escHtml(identity.tokenImageUrl || '') + '" maxlength="500"',
        ' placeholder="https://\u2026" />',
        '</div>',
        '</div>',

        '</div>',
        '</details>',

        // ── Optional: Backstory ───────────────────────────────────────
        '<details class="cb-optional-section" data-section-key="backstory"' + detailsOpen('backstory') + '>',
        '<summary class="cb-optional-section-summary">Backstory &amp; Notes <span class="cb-optional">optional</span></summary>',
        '<div class="cb-optional-section-body">',

        '<div class="field">',
        '<label>Backstory</label>',
        '<textarea data-builder-path="identity.backstory" maxlength="1000"',
        ' placeholder="One-paragraph concept \u2014 origin, motivation, dark secret\u2026"',
        ' rows="4">' + escHtml(identity.backstory || '') + '</textarea>',
        '<div class="cb-char-count">' + String(identity.backstory || '').length + ' / 1000</div>',
        '</div>',

        '<div class="field">',
        '<label>Notes</label>',
        '<textarea data-builder-path="identity.notes" maxlength="600"',
        ' placeholder="Personality traits, bonds, flaws, roleplay reminders\u2026"',
        ' rows="3">' + escHtml(identity.notes || '') + '</textarea>',
        '<div class="cb-char-count">' + String(identity.notes || '').length + ' / 600</div>',
        '</div>',

        '</div>',
        '</details>',
      ].join('');
    },

    bind: function bindIdentityStep(root, ctx) {
      // Track open/closed state of each optional section so re-renders preserve it
      root.querySelectorAll('details[data-section-key]').forEach(function(details) {
        details.addEventListener('toggle', function() {
          var key = details.dataset.sectionKey;
          if (key && Object.prototype.hasOwnProperty.call(_expanded, key)) {
            _expanded[key] = details.open;
          }
        });
      });

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
