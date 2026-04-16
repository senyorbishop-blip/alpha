(function initGatewayModal(global) {
  function escHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function renderCharacterCards(opts) {
    const gridEl = opts.gridEl;
    const chars = Array.isArray(opts.characters) ? opts.characters : [];

    if (!gridEl) return;
    gridEl.innerHTML = '';

    if (!chars.length) {
      gridEl.innerHTML = '<div class="loading-msg">No existing characters in your profile library yet.</div>';
      return;
    }

    chars.forEach((item) => {
      if (!item || !item.id) return;
      const card = document.createElement('div');
      card.className = 'char-card';
      card.dataset.profileId = item.id;
      card.setAttribute('role', 'button');
      card.setAttribute('aria-pressed', opts.selectedProfileId === item.id ? 'true' : 'false');
      if (opts.selectedProfileId === item.id) {
        card.classList.add('selected');
      }

      const shape = item.shape === 'rect' ? 'rect' : '';
      const initials = String(item.name || '?').slice(0, 2).toUpperCase();
      const ownerLabel = item.ownerLabel || 'Existing profile';
      const ownerClass = item.mine ? 'mine' : '';
      const color = item.color || '#3b5f7a';
      const classSummary = item.classSummary ? String(item.classSummary) : '';
      const levelLabel = (item.level === null || item.level === undefined || item.level === '') ? '' : ('Level ' + item.level);
      const sourceBadge = item.sourceBadge ? String(item.sourceBadge) : '';

      const isDeletable = item.kind === 'library-profile' || (item.kind === 'session-token' && item.mine);

      card.innerHTML = [
        '<div class="char-token ' + shape + '" style="background:' + escHtml(color) + '">',
        escHtml(initials),
        '</div>',
        '<div class="char-info">',
        '<div class="char-name">' + escHtml(item.name || 'Unnamed Character') + '</div>',
        '<div class="char-owner ' + ownerClass + '">' + escHtml(ownerLabel) + '</div>',
        classSummary ? ('<div class="char-owner">' + escHtml(classSummary) + '</div>') : '',
        (levelLabel || sourceBadge)
          ? ('<div class="char-owner">'
              + (levelLabel ? ('<span>' + escHtml(levelLabel) + '</span>') : '')
              + (sourceBadge ? ('<span style="margin-left:8px;opacity:0.9">' + escHtml(sourceBadge) + '</span>') : '')
              + '</div>')
          : '',
        '</div>',
        '<span class="check">' + (opts.selectedProfileId === item.id ? '✓ Selected' : '✓') + '</span>',
        (opts.enableLevelupPreview && item.nativeCharacter && item.sourceMode === 'native')
          ? '<button type="button" class="btn btn-ghost" data-levelup-preview="1" style="margin-left:auto; padding:4px 8px; font-size:0.68rem;">Level-Up Preview</button>'
          : '',
        isDeletable
          ? '<button type="button" class="btn btn-ghost" data-delete-profile="1" aria-label="Delete character" title="Delete from library" style="padding:4px 8px; font-size:0.68rem; margin-left:4px; color:#c0392b;">🗑 Delete</button>'
          : '',
      ].join('');

      const levelupBtn = card.querySelector('[data-levelup-preview="1"]');
      if (levelupBtn && typeof opts.onLevelupPreview === 'function') {
        levelupBtn.addEventListener('click', function onLevelupClick(event) {
          event.preventDefault();
          event.stopPropagation();
          opts.onLevelupPreview(item);
        });
      }

      const deleteBtn = card.querySelector('[data-delete-profile="1"]');
      if (deleteBtn && typeof opts.onDelete === 'function') {
        deleteBtn.addEventListener('click', function onDeleteClick(event) {
          event.preventDefault();
          event.stopPropagation();
          opts.onDelete(item);
        });
      }

      card.addEventListener('click', function onCardClick() {
        if (typeof opts.onSelect === 'function') {
          opts.onSelect(item.id);
        }
      });

      gridEl.appendChild(card);
    });
  }

  function setHasExistingState(opts) {
    if (!opts || !opts.emptyHintEl || !opts.existingSectionEl || !opts.actionsSectionEl) return;
    const hasExisting = Array.isArray(opts.characters) && opts.characters.length > 0;
    opts.existingSectionEl.style.display = hasExisting ? '' : 'none';
    opts.emptyHintEl.style.display = hasExisting ? 'none' : '';
    opts.actionsSectionEl.classList.toggle('gateway-actions-prominent', !hasExisting);
  }

  global.CharacterGatewayModal = {
    renderCharacterCards,
    setHasExistingState,
  };
})(window);
