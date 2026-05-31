(function (global) {
  'use strict';

  function closeCharacterBook(env) {
    env.document.getElementById('char-sheet-panel')?.classList.remove('open');
  }

  function updateCharacterBookModeRibbon(env, page) {
    const ribbon = env.document.getElementById('char-book-mode-ribbon');
    if (!ribbon) return;
    const labels = {
      premiumsheet: ['Live Play mode', 'The Sheet ✦ dashboard keeps Actions, Spells, Inventory, Features, and Notes easy to find during the session.'],
      import: ['Import Review mode', 'Review pasted, JSON, or PDF import data here before trusting AC, HP, spells, or equipment.'],
      levelup: ['Level Up mode', 'Use this progression flow after the live sheet and source data look correct.'],
      identity: ['Build/Edit mode', 'Edit notes and identity source data here; the live player dashboard remains on Sheet ✦.'],
      abilities: ['Build/Edit mode', 'Confirm vitals, proficiency, passive perception, and ability scores here.'],
      skills: ['Build/Edit mode', 'Confirm saves and skill math here.'],
      combat: ['Build/Edit mode', 'Review legacy action source data here; use the Sheet ✦ Actions tab during live play.'],
      inventory: ['Build/Edit mode', 'Review imported carried gear here; use the Sheet ✦ Inventory tab during live play.'],
      spelllibrary: ['Build/Edit mode', 'Manage spell library details here; use the Sheet ✦ Spells tab during live play.'],
    };
    const entry = labels[page] || labels.premiumsheet;
    ribbon.innerHTML = '<strong>' + entry[0] + '</strong><span>' + entry[1] + '</span>';
  }

  function updateCharacterBookTabs(env, page) {
    env.document.querySelectorAll('.sheet-page-tab').forEach(btn => btn.classList.toggle('active', btn.dataset.page === page));
    env.document.querySelectorAll('.sheet-workflow-btn').forEach(btn => {
      const target = String(btn.dataset.page || '').trim();
      btn.classList.toggle('active', target === page);
    });
    updateCharacterBookModeRibbon(env, page);
  }

  function goCharacterBookPage(env, page, instant = false) {
    const strip = env.document.getElementById('char-book-pages');
    const pageEl = strip?.querySelector(`.sheet-page[data-page="${page}"]`);
    if (!strip || !pageEl) return;
    env.setActiveCharBookPage(page);
    pageEl.scrollIntoView({ behavior: instant ? 'auto' : 'smooth', block: 'nearest', inline: 'start' });
    updateCharacterBookTabs(env, page);
  }

  function handleCharacterBookScroll(env) {
    const strip = env.document.getElementById('char-book-pages');
    if (!strip) return;
    const pageOrder = env.getPageOrder() || [];
    const idx = Math.round(strip.scrollLeft / Math.max(1, strip.clientWidth));
    const page = pageOrder[Math.min(pageOrder.length - 1, Math.max(0, idx))] || 'premiumsheet';
    if (page !== env.getActiveCharBookPage()) {
      env.setActiveCharBookPage(page);
      updateCharacterBookTabs(env, page);
    }
  }

  function openCharacterBook(env, page = 'premiumsheet') {
    env.initCharacterBook();
    const charSheet = env.getCharSheet();
    if (charSheet && (Object.keys(charSheet.book || {}).length || (charSheet.name && charSheet.name !== 'Unknown Hero') || (charSheet.classes && charSheet.classes.length))) {
      env.applyCharSheetToBook(charSheet);
    } else {
      env.seedCharacterBookFromCurrentState();
    }
    env.syncCharSheetFromBookData(env.getCharacterBookDataFromUI());
    const panel = env.document.getElementById('char-sheet-panel');
    if (panel && panel.parentElement !== env.document.body) env.document.body.appendChild(panel);
    if (panel) panel.classList.add('open');
    env.setCharacterBookSaveState('saved');
    goCharacterBookPage(env, page, true);
    try {
      env.ensureCharSheetRuntimeDefaults();
      env.requestCharacterBookOverviewRender('openCharacterBook');
      env.renderImportedSpellbookPreview();
      env.renderRulesSpellbook();
      env.updateSpellRulesButtons();
    } catch (err) {
      env.console.error('Character Book open failed', err);
      env.showToast('Character Book opened with a sheet warning.');
    }
  }

  function openCharacterLevelupPlanner(env) {
    if (env.getRole() !== 'player') return;
    if (!(global.CharacterLevelupModal && typeof global.CharacterLevelupModal.open === 'function')) {
      env.showToast('Level Up Planner is still loading. Try again in a moment.');
      return;
    }

    const profileId = env.resolveActiveCharProfileId();
    const charProfiles = env.getCharProfiles();
    const selectedProfile = charProfiles.find(p => String(p?.id || '') === String(profileId || '')) || null;
    const activeDoc = env.getActiveNativeCharacterDocument();
    const characterDocument = (activeDoc && typeof activeDoc === 'object')
      ? JSON.parse(JSON.stringify(activeDoc))
      : (selectedProfile && selectedProfile.nativeCharacter && typeof selectedProfile.nativeCharacter === 'object'
        ? JSON.parse(JSON.stringify(selectedProfile.nativeCharacter))
        : null);

    if (!(characterDocument && typeof characterDocument === 'object' && Object.keys(characterDocument).length)) {
      env.showToast('Level Up Planner requires an imported character. Use the Import tab to import from D&D Beyond (PDF or JSON) first.');
      // Navigate to import tab so the player knows what to do
      goCharacterBookPage(env, 'import');
      return;
    }

    global.CharacterLevelupModal.open({
      sessionId: env.getSessionId(),
      profile: selectedProfile || { id: profileId },
      characterDocument,
      onApplied: (data) => {
        const profilePayload = data?.profile && typeof data.profile === 'object' ? data.profile : null;
        const resolvedProfileId = String((profilePayload && profilePayload.id) || profileId || '').trim();
        const existingProfile = charProfiles.find(p => String(p?.id || '') === resolvedProfileId) || null;

        if (data?.nativeCharacter && typeof data.nativeCharacter === 'object') {
          env.setActiveNativeCharacterDocument(JSON.parse(JSON.stringify(data.nativeCharacter)));
        }
        if (data?.nativeRuntime && typeof data.nativeRuntime === 'object') {
          env.setActiveNativeCharacterRuntime(JSON.parse(JSON.stringify(data.nativeRuntime)));
        }

        let nextProfile = null;
        if (profilePayload && (profilePayload.charBook || profilePayload.charSheet || profilePayload.nativeCharacter)) {
          nextProfile = JSON.parse(JSON.stringify(profilePayload));
        } else if (existingProfile && typeof existingProfile === 'object') {
          nextProfile = JSON.parse(JSON.stringify(existingProfile));
        } else {
          nextProfile = env.collectCurrentCharProfile({ profileId: resolvedProfileId || profileId });
        }

        if (nextProfile && data?.nativeCharacter && typeof data.nativeCharacter === 'object') {
          nextProfile.nativeCharacter = JSON.parse(JSON.stringify(data.nativeCharacter));
        }
        if (nextProfile && data?.nativeRuntime && typeof data.nativeRuntime === 'object') {
          nextProfile.nativeRuntime = JSON.parse(JSON.stringify(data.nativeRuntime));
        }
        if (nextProfile && !nextProfile.id) nextProfile.id = resolvedProfileId || profileId;

        if (nextProfile) {
          nextProfile.sourceMode = String(nextProfile?.nativeCharacter?.sourceMode || nextProfile.sourceMode || 'native').trim() || 'native';
          const mapped = env.mapProfileToPlay(nextProfile);
          const saveId = String(mapped?.id || nextProfile.id || profileId || '').trim();
          env.upsertCharProfile(saveId, mapped);
          env.refreshCharProfileSelect();
          env.applyCharProfileRecord(mapped, { silent: true });
          try { if (typeof global.updateMyChar === 'function') global.updateMyChar(); } catch (_) {}
          try { if (typeof env.renderImportedSpellbookPreview === 'function') env.renderImportedSpellbookPreview(); } catch (_) {}
          try { if (typeof env.renderRulesSpellbook === 'function') env.renderRulesSpellbook(); } catch (_) {}
          try { if (typeof env.updateSpellRulesButtons === 'function') env.updateSpellRulesButtons(); } catch (_) {}
          try { if (typeof env.requestCharacterBookOverviewRender === 'function') env.requestCharacterBookOverviewRender('levelup-applied'); } catch (_) {}
          try { if (typeof global.renderCombat === 'function') global.renderCombat(); } catch (_) {}
          try { if (typeof global.renderPartyStatusPanel === 'function') global.renderPartyStatusPanel(); } catch (_) {}
          try { setTimeout(function () { if (typeof global.updateMyChar === 'function') global.updateMyChar(); }, 0); } catch (_) {}
          try { setTimeout(function () { if (typeof env.requestCharacterBookOverviewRender === 'function') env.requestCharacterBookOverviewRender('levelup-applied'); }, 50); } catch (_) {}
        }

        env.showToast('Level up applied and profile saved.');
      },
    });
  }

  global.AppUICharacterBook = {
    closeCharacterBook,
    openCharacterBook,
    goCharacterBookPage,
    handleCharacterBookScroll,
    updateCharacterBookTabs,
    openCharacterLevelupPlanner,
  };
})(window);
