(function initJoinGateway(global) {
  function createJoinGateway(config) {
    const cfg = Object.assign({
      state: null,
      modal: null,
      hooks: {},
      elements: {},
      externalRosterRenderer: false,
    }, config || {});

    const state = cfg.state;
    const modal = cfg.modal;
    const hooks = cfg.hooks || {};
    const els = cfg.elements || {};
    const panel = cfg.panel || (global.CharacterLibraryPanel || null);

    let sessionCharacters = [];
    let libraryCharacters = [];
    let builder = null;

    function getSessionId() {
      const explicit = String(cfg.sessionId || '').trim();
      if (explicit) return explicit;

      const fromGlobal = String((global.SESSION_ID || '')).trim();
      if (fromGlobal) return fromGlobal;

      try {
        const params = new URLSearchParams(global.location && global.location.search ? global.location.search : '');
        return String(params.get('session') || '').trim();
      } catch (_) {
        return '';
      }
    }

    function getSelectedCharacter() {
      const snapshot = state.getState();
      const chars = Array.isArray(snapshot.characters) ? snapshot.characters : [];
      return chars.find((item) => item && item.id === snapshot.selectedProfileId) || null;
    }

    function normalizeName(value) {
      return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    }

    function rebuildCharacters(preferredId) {
      const library = Array.isArray(libraryCharacters) ? libraryCharacters : [];
      const session = Array.isArray(sessionCharacters) ? sessionCharacters : [];
      const libraryNameKeys = new Set(library.map((item) => normalizeName(item && item.name)).filter(Boolean));
      const merged = []
        .concat(library)
        .concat(session.filter((item) => {
          if (!item) return false;
          if (!item.mine) return true;
          const key = normalizeName(item.name);
          if (!key || !libraryNameKeys.has(key)) return true;
          const hasImage = !!String(item.tokenImageUrl || '').trim();
          const hasClass = !!String(item.classSummary || '').trim();
          return hasImage && hasClass;
        }));
      const deduped = [];
      const seen = new Set();
      const seenSignature = new Set();
      merged.forEach(function appendUnique(item) {
        if (!item || !item.id || seen.has(item.id)) return;
        const signature = [
          normalizeName(item.name),
          normalizeName(item.classSummary),
          normalizeName(item.speciesLabel),
          String(item.classId || ''),
          String(item.speciesId || ''),
          String(item.tokenImageUrl || item.portraitUrl || ''),
          String(item.level || ''),
          String(item.libraryId || ''),
          String(item.claimTokenId || item.id || ''),
        ].join('|');
        if (signature && seenSignature.has(signature)) return;
        seen.add(item.id);
        if (signature) seenSignature.add(signature);
        deduped.push(item);
      });
      state.setCharacters(deduped);
      const candidate = preferredId || state.getState().selectedProfileId;
      if (candidate && deduped.some((item) => item && item.id === candidate)) {
        state.selectProfile(candidate);
      }
    }

    async function saveNativeCharacterToProfileLibrary(draft) {
      const sessionId = getSessionId();
      if (!sessionId) {
        throw new Error('Missing session_id for character save.');
      }

      const canonicalDraft = draft && typeof draft === 'object' ? JSON.parse(JSON.stringify(draft)) : {};
      const identity = canonicalDraft.identity && typeof canonicalDraft.identity === 'object' ? canonicalDraft.identity : {};
      const portraitLibrary = global.CasualDnDPortraitLibrary;
      const firstClass = Array.isArray(canonicalDraft.classes) && canonicalDraft.classes[0] && typeof canonicalDraft.classes[0] === 'object'
        ? canonicalDraft.classes[0]
        : {};
      const resolvedPortrait = portraitLibrary && typeof portraitLibrary.resolve === 'function'
        ? String(portraitLibrary.resolve({
            speciesId: canonicalDraft.species && (canonicalDraft.species.id || canonicalDraft.species.name) || '',
            classId: canonicalDraft.class && canonicalDraft.class.id || firstClass.classId || firstClass.name || '',
            gender: identity.gender || 'neutral',
            neutralFallback: '',
          }) || '').trim()
        : '';
      const rawPortrait = String(identity.portraitUrl || '').trim();
      const rawToken = String(identity.tokenImageUrl || '').trim();
      const hasManualPortrait = !!rawPortrait && (!resolvedPortrait || rawPortrait !== resolvedPortrait);
      const hasManualToken = !!rawToken && (!resolvedPortrait || rawToken !== resolvedPortrait);

      if (!hasManualPortrait && !hasManualToken && resolvedPortrait) {
        canonicalDraft.identity = Object.assign({}, identity, {
          portraitUrl: resolvedPortrait,
          tokenImageUrl: resolvedPortrait,
        });
      } else if (hasManualPortrait && !hasManualToken) {
        canonicalDraft.identity = Object.assign({}, identity, { tokenImageUrl: rawPortrait });
      } else if (!hasManualPortrait && hasManualToken) {
        canonicalDraft.identity = Object.assign({}, identity, { portraitUrl: rawToken });
      }

      const res = await fetch('/api/character/save', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          character_document: canonicalDraft,
        }),
      });
      if (!res.ok) {
        throw new Error('Native character save failed.');
      }
      const data = await res.json();
      if (!data || data.ok !== true) {
        throw new Error('Native character save failed.');
      }
      return data;
    }

    async function fetchLibraryCharacters() {
      const sessionId = getSessionId();
      const qs = new URLSearchParams();
      if (sessionId) qs.set('session_id', sessionId);
      qs.set('include_native', '1');

      const url = '/api/character/library' + (qs.toString() ? ('?' + qs.toString()) : '');
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) return [];

      const data = await res.json();
      const profiles = Array.isArray(data && data.profiles) ? data.profiles : [];
      if (panel && typeof panel.normalizeCharacterEntries === 'function') {
        return panel.normalizeCharacterEntries(profiles);
      }
      return profiles;
    }

    function loadScript(src) {
      return new Promise((resolve, reject) => {
        const existing = document.querySelector('script[data-builder-src="' + src + '"]');
        if (existing) {
          if (existing.dataset.builderLoaded === '1') {
            resolve();
            return;
          }
          existing.addEventListener('load', function onLoad() { resolve(); }, { once: true });
          existing.addEventListener('error', function onErr() { reject(new Error('failed:' + src)); }, { once: true });
          return;
        }

        const script = document.createElement('script');
        script.src = src;
        script.async = false;
        script.dataset.builderSrc = src;
        script.addEventListener('load', function onLoad() {
          script.dataset.builderLoaded = '1';
          resolve();
        }, { once: true });
        script.addEventListener('error', function onErr() {
          reject(new Error('failed:' + src));
        }, { once: true });
        document.head.appendChild(script);
      });
    }

    async function ensureBuilderReady() {
      if (builder) return builder;

      if (!global.CharacterBuilderAPI || !global.CharacterBuilderRouter || !global.CharacterBuilderValidators || !global.CharacterBuilderState || !global.CharacterBuilderShell || !global.CharacterBuilderStepModules) {
        await loadScript('/static/js/character/builder/builder_api.js');
        await loadScript('/static/js/character/builder/builder_router.js');
        await loadScript('/static/js/character/builder/builder_validators.js');
        await loadScript('/static/js/character/builder/builder_state.js');
        await loadScript('/static/js/character/builder/builder_tooltips.js');
        await loadScript('/static/js/character/builder/steps/step_identity.js');
        await loadScript('/static/js/character/builder/steps/step_species.js');
        await loadScript('/static/js/character/builder/steps/step_origins.js');
        await loadScript('/static/js/character/builder/steps/step_abilities.js');
        await loadScript('/static/js/character/builder/steps/step_class.js');
        await loadScript('/static/js/character/builder/steps/step_subclass.js');
        await loadScript('/static/js/character/builder/steps/step_progression.js');
        await loadScript('/static/js/character/builder/steps/step_spells.js');
        await loadScript('/static/js/character/builder/steps/step_equipment.js');
        await loadScript('/static/js/character/builder/steps/step_review.js');
        await loadScript('/static/js/character/builder/builder_shell.js');
      }

      if (!global.CharacterBuilderState || !global.CharacterBuilderShell || !global.CharacterBuilderRouter) {
        return null;
      }

      const builderState = global.CharacterBuilderState.createBuilderState({ resumeMemoryDraft: false });
      builder = global.CharacterBuilderShell.createBuilderShell({
        mountEl: els.actionsSection,
        state: builderState,
        router: global.CharacterBuilderRouter,
        onClose: function onCloseBuilder() {
          if (els.gatewayButtonsWrap) {
            els.gatewayButtonsWrap.style.display = '';
          }
        },
        onSaveCharacter: function onSaveCharacter(draft) {
          if (!draft || typeof draft !== 'object') {
            return;
          }

          // Resolve combo portrait URL and bake it into the draft so the saved
          // character carries the correct token/portrait image without needing a
          // manual URL. Respect any explicit portrait the player already entered.
          var draftToSave = draft;
          var portraitLib = global.CasualDnDPortraitLibrary;
          if (portraitLib && typeof portraitLib.resolve === 'function') {
            var draftIdentity = draft.identity && typeof draft.identity === 'object' ? draft.identity : {};
            var hasManualPortrait = !!String(draftIdentity.portraitUrl || '').trim();
            var hasManualToken = !!String(draftIdentity.tokenImageUrl || '').trim();
            if (!hasManualPortrait || !hasManualToken) {
              var firstClass = Array.isArray(draft.classes) && draft.classes[0] && typeof draft.classes[0] === 'object'
                ? draft.classes[0]
                : {};
              var resolvedPortrait = portraitLib.resolve({
                speciesId: draft.species && draft.species.id,
                classId: draft.class && draft.class.id || firstClass.classId || firstClass.name || '',
                gender: draftIdentity.gender,
              });
              if (resolvedPortrait) {
                draftToSave = Object.assign({}, draft, {
                  identity: Object.assign({}, draftIdentity, {
                    portraitUrl: hasManualPortrait ? draftIdentity.portraitUrl : resolvedPortrait,
                    tokenImageUrl: hasManualToken ? draftIdentity.tokenImageUrl : resolvedPortrait,
                  }),
                });
              }
            }
          }

          return saveNativeCharacterToProfileLibrary(draftToSave)
            .then(function onSaved(result) {
              const savedProfile = result && result.profile && typeof result.profile === 'object'
                ? result.profile
                : null;
              const preferredId = savedProfile && savedProfile.id
                ? ('library:' + savedProfile.id)
                : null;
              return fetchLibraryCharacters().then(function onRefetch(characters) {
                libraryCharacters = Array.isArray(characters) ? characters : [];
                rebuildCharacters(preferredId);
                if (global.CharacterBuilderState && typeof global.CharacterBuilderState.clearMemoryDraft === 'function') {
                  global.CharacterBuilderState.clearMemoryDraft();
                }
                if (builderState && typeof builderState.replaceDraft === 'function' && global.CharacterBuilderState && typeof global.CharacterBuilderState.createDefaultDraft === 'function') {
                  builderState.replaceDraft(global.CharacterBuilderState.createDefaultDraft(), { markDirty: false });
                }
                if (typeof hooks.onNativeSaved === 'function') {
                  hooks.onNativeSaved(savedProfile);
                }
              });
            });
        },
      });

      return builder;
    }

    async function ensureImportModalReady() {
      if (global.CharacterImportModal && typeof global.CharacterImportModal.open === 'function') {
        return global.CharacterImportModal;
      }
      await loadScript('/static/js/character/library/character_import_modal.js');
      if (global.CharacterImportModal && typeof global.CharacterImportModal.open === 'function') {
        return global.CharacterImportModal;
      }
      return null;
    }

    async function ensureLevelupModalReady() {
      if (global.CharacterLevelupModal && typeof global.CharacterLevelupModal.open === 'function') {
        return global.CharacterLevelupModal;
      }
      await loadScript('/static/js/character/library/character_levelup_modal.js');
      if (global.CharacterLevelupModal && typeof global.CharacterLevelupModal.open === 'function') {
        return global.CharacterLevelupModal;
      }
      return null;
    }

    async function openImportModal() {
      const modalApi = await ensureImportModalReady();
      if (!modalApi || typeof modalApi.open !== 'function') {
        throw new Error('Import modal unavailable');
      }

      modalApi.open({
        sessionId: getSessionId(),
        onImported: function onImported(result) {
          const savedProfile = result && result.profile && typeof result.profile === 'object'
            ? result.profile
            : null;
          const preferredId = savedProfile && savedProfile.id
            ? ('library:' + savedProfile.id)
            : null;

          return fetchLibraryCharacters().then(function onRefetch(characters) {
            libraryCharacters = Array.isArray(characters) ? characters : [];
            rebuildCharacters(preferredId);
            if (typeof hooks.onNativeSaved === 'function' && savedProfile) {
              hooks.onNativeSaved(savedProfile);
            }
            if (typeof hooks.onImportDDB === 'function') {
              hooks.onImportDDB(result);
            }
          });
        },
      });
    }

    async function openLevelupPreview(characterEntry) {
      const doc = characterEntry && characterEntry.nativeCharacter && typeof characterEntry.nativeCharacter === 'object'
        ? characterEntry.nativeCharacter
        : null;
      if (!doc) {
        throw new Error('No native character document available for level-up preview.');
      }
      const modalApi = await ensureLevelupModalReady();
      if (!modalApi || typeof modalApi.open !== 'function') {
        throw new Error('Level-up modal unavailable');
      }
      return modalApi.open({
        sessionId: getSessionId(),
        profile: characterEntry,
        characterDocument: doc,
      });
    }

    async function deleteLibraryCharacter(characterEntry) {
      const libraryId = characterEntry && characterEntry.libraryId
        ? String(characterEntry.libraryId).trim()
        : '';
      if (!libraryId) {
        if (typeof hooks.onError === 'function') {
          hooks.onError('Cannot delete: missing character ID.');
        }
        return;
      }

      const sessionId = getSessionId();
      const qs = new URLSearchParams();
      if (sessionId) qs.set('session_id', sessionId);

      const url = '/api/character/profile/' + encodeURIComponent(libraryId) + (qs.toString() ? ('?' + qs.toString()) : '');
      const res = await fetch(url, {
        method: 'DELETE',
        credentials: 'same-origin',
      });
      if (!res.ok) {
        throw new Error('Character delete failed: ' + res.status);
      }

      return fetchLibraryCharacters().then(function onRefetch(characters) {
        libraryCharacters = Array.isArray(characters) ? characters : [];
        if (state.getState().selectedProfileId === characterEntry.id) {
          state.selectProfile(null);
        }
        rebuildCharacters(null);
      });
    }

    async function deleteSessionToken(characterEntry) {
      const tokenId = characterEntry && characterEntry.claimTokenId
        ? String(characterEntry.claimTokenId).trim()
        : (characterEntry && characterEntry.id ? String(characterEntry.id).trim() : '');
      if (!tokenId) {
        if (typeof hooks.onError === 'function') {
          hooks.onError('Cannot delete: missing token ID.');
        }
        return;
      }

      const sessionId = getSessionId();
      if (!sessionId) {
        if (typeof hooks.onError === 'function') {
          hooks.onError('Cannot delete: missing session ID.');
        }
        return;
      }

      const url = '/api/session/' + encodeURIComponent(sessionId) + '/token/' + encodeURIComponent(tokenId);
      const res = await fetch(url, {
        method: 'DELETE',
        credentials: 'same-origin',
      });
      if (!res.ok) {
        throw new Error('Token delete failed: ' + res.status);
      }

      sessionCharacters = sessionCharacters.filter(function (item) {
        return item && (item.claimTokenId || item.id) !== tokenId;
      });
      if (state.getState().selectedProfileId === characterEntry.id ||
          state.getState().selectedProfileId === tokenId) {
        state.selectProfile(null);
      }
      rebuildCharacters(null);
    }

    function bindActions() {
      if (els.useExistingBtn) {
        els.useExistingBtn.addEventListener('click', function onUseExistingClick() {
          const selected = getSelectedCharacter();
          if (!selected || !selected.canUseExisting) return;
          if (typeof hooks.onUseExisting === 'function') {
            hooks.onUseExisting(selected.claimTokenId || selected.id, selected);
          }
        });
      }

      if (els.createNativeBtn) {
        els.createNativeBtn.addEventListener('click', async function onCreateClick() {
          try {
            const readyBuilder = await ensureBuilderReady();
            if (readyBuilder && typeof readyBuilder.open === 'function') {
              if (els.gatewayButtonsWrap) {
                els.gatewayButtonsWrap.style.display = 'none';
              }
              readyBuilder.open();
              return;
            }
          } catch (_) {
            // If shell loading fails, keep legacy fallback path.
          }

          if (typeof hooks.onCreateNative === 'function') {
            hooks.onCreateNative();
          }
        });
      }

      if (els.importDdbBtn) {
        els.importDdbBtn.addEventListener('click', async function onImportClick() {
          try {
            await openImportModal();
            return;
          } catch (_) {
            // Fallback to caller-provided legacy hook if modal boot fails.
          }
          if (typeof hooks.onImportDDB === 'function') {
            hooks.onImportDDB();
          }
        });
      }
    }

    function syncView(snapshot) {
      if (!cfg.externalRosterRenderer) {
        modal.renderCharacterCards({
        gridEl: els.charGrid,
        characters: snapshot.characters,
        selectedProfileId: snapshot.selectedProfileId,
        onSelect: state.selectProfile,
        onLevelupPreview: function onLevelupPreview(item) {
          openLevelupPreview(item).catch(function noop() {});
        },
        onDelete: function onDeleteCard(item) {
          const isSessionToken = item && item.kind === 'session-token';
          const deleteAction = isSessionToken
            ? deleteSessionToken(item)
            : deleteLibraryCharacter(item);
          deleteAction.catch(function onDeleteError(err) {
            if (typeof hooks.onError === 'function') {
              hooks.onError(String((err && err.message) || 'Delete failed.'));
            }
          });
        },
        });

        modal.setHasExistingState({
          characters: snapshot.characters,
          existingSectionEl: els.existingSection,
          actionsSectionEl: els.actionsSection,
          emptyHintEl: els.emptyHint,
        });
      }

      if (els.useExistingBtn) {
        const selected = Array.isArray(snapshot.characters)
          ? snapshot.characters.find((item) => item && item.id === snapshot.selectedProfileId)
          : null;
        const enabled = !!(selected && selected.canUseExisting);
        els.useExistingBtn.disabled = !enabled;
        els.useExistingBtn.style.opacity = enabled ? '1' : '0.4';
      }
    }

    function loadCharacters(characters, preferredId) {
      const incoming = Array.isArray(characters) ? characters : [];
      sessionCharacters = incoming.map(function mapSessionToken(item) {
        if (!item || !item.id) return null;
        return Object.assign({}, item, {
          kind: item.kind || 'session-token',
          canUseExisting: item.canUseExisting !== false,
          claimTokenId: item.claimTokenId || item.id,
          sourceMode: item.sourceMode || '',
          classSummary: item.classSummary || '',
          level: item.level != null ? item.level : null,
        });
      }).filter(Boolean);

      rebuildCharacters(preferredId || null);
    }

    function init() {
      bindActions();
      state.subscribe(syncView);
      syncView(state.getState());

      fetchLibraryCharacters()
        .then(function onLibrary(characters) {
          libraryCharacters = Array.isArray(characters) ? characters : [];
          rebuildCharacters(null);
        })
        .catch(function ignoreLibraryFailure() {
          libraryCharacters = [];
          rebuildCharacters(null);
        });
    }

    async function refreshLibraryCharacters() {
      const selectedBefore = state.getState().selectedProfileId || null;
      const characters = await fetchLibraryCharacters();
      libraryCharacters = Array.isArray(characters) ? characters : [];
      rebuildCharacters(selectedBefore);
    }

    return {
      init,
      loadCharacters,
      refreshLibraryCharacters,
      selectProfile: state.selectProfile,
      getSelectedProfileId: function getSelectedProfileId() {
        return state.getState().selectedProfileId;
      },
    };
  }

  global.CharacterJoinGateway = {
    createJoinGateway,
  };
})(window);
