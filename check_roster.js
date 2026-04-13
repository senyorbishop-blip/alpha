
    const params = new URLSearchParams(location.search);
    const SESSION_ID = String(params.get('session') || '').trim().toUpperCase();
    const INVITE = String(params.get('code') || '').trim();
    const ROLE = 'player';
    const CREATED_PROFILE = String(params.get('created') || '').trim();
    const NEXT_LOGIN = location.pathname + location.search;

    let authUser = null;
    let sessionTokens = [];
    let selectedTokenId = null;
    let selectedProfileId = '';
    let joinGateway = null;
    let gatewayState = null;
    let campaignName = 'Campaign';

    const els = {
      campaignName: document.getElementById('campaign-name'),
      accountStatus: document.getElementById('account-status'),
      inviteStatus: document.getElementById('invite-status'),
      feedback: document.getElementById('feedback'),
      characterList: document.getElementById('character-list'),
      enterBtn: document.getElementById('enter-btn'),
      createBtn: document.getElementById('create-btn'),
      importBtn: document.getElementById('import-btn'),
      refreshBtn: document.getElementById('refresh-btn'),
      builderHost: document.getElementById('builder-host'),
      actionButtons: document.getElementById('action-buttons'),
      panelTitle: document.getElementById('panel-title'),
      panelCopy: document.getElementById('panel-copy'),
      heroCopy: document.getElementById('hero-copy'),
      footerCopy: document.getElementById('footer-copy'),
    };

    function setFeedback(message, kind = 'info') {
      els.feedback.textContent = message;
      els.feedback.className = 'feedback' + (kind === 'error' ? ' error' : kind === 'success' ? ' success' : '');
    }

    function redirectToLogin() {
      sessionStorage.setItem('dnd_login_next', NEXT_LOGIN);
      location.href = '/player?next=' + encodeURIComponent(NEXT_LOGIN);
    }

    function getPlayerKey() {
      if (authUser && authUser.id) return 'auth_' + authUser.id;
      let key = localStorage.getItem('tavern_player_key');
      if (!key) {
        key = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
        localStorage.setItem('tavern_player_key', key);
      }
      return key;
    }

    async function fetchJson(url, options) {
      const res = await fetch(url, Object.assign({ credentials: 'same-origin' }, options || {}));
      let data = {};
      try { data = await res.json(); } catch (_) {}
      if (!res.ok) {
        throw new Error(data.error || data.detail || data.message || 'Request failed');
      }
      return data;
    }

    function tokenStyle(color) {
      return color ? `background:${color};` : 'background:linear-gradient(180deg,#6f5936,#342112);';
    }

    function renderCharacterCard(entry) {
      const card = document.createElement('button');
      card.type = 'button';
      const selectedId = joinGateway && joinGateway.getSelectedProfileId ? joinGateway.getSelectedProfileId() : '';
      card.className = 'character-card' + (entry.id === selectedId ? ' selected' : '');
      card.dataset.profileId = entry.id;
      card.innerHTML = `
        <div class="token" style="${tokenStyle(entry.color)}">${(entry.name || '?').slice(0, 2).toUpperCase()}</div>
        <div class="character-main">
          <div class="character-name">${escapeHtml(entry.name || 'Unnamed Hero')}</div>
          <div class="character-meta">
            <span class="character-tag">${escapeHtml(entry.ownerLabel || (entry.mine ? 'Your character' : 'Campaign character'))}</span>
            ${entry.libraryId ? '<span class="character-tag">Library</span>' : '<span class="character-tag">Session</span>'}
          </div>
        </div>
        <div class="character-check">✓</div>
      `;
      card.addEventListener('click', () => {
        if (joinGateway && typeof joinGateway.selectProfile === 'function') {
          joinGateway.selectProfile(entry.id);
          renderRosterFromState();
        }
      });
      return card;
    }

    function renderEmptyState(message) {
      els.characterList.innerHTML = `<div class="empty">${message}</div>`;
    }

    function setupJoinGateway() {
      if (joinGateway || !window.CharacterGatewayState || !window.CharacterGatewayModal || !window.CharacterJoinGateway) return;
      gatewayState = window.CharacterGatewayState.createGatewayState();
      joinGateway = window.CharacterJoinGateway.createJoinGateway({
        state: gatewayState,
        modal: window.CharacterGatewayModal,
        hooks: {
          onUseExisting(profileId, selectedEntry) {
            const selectedId = String(profileId || '').trim();
            const profileMatch = selectedId.match(/^profile:(.+)$/);
            const selectedLibraryProfileId = profileMatch ? String(profileMatch[1] || '').trim() : '';
            if (selectedLibraryProfileId) {
              selectedProfileId = selectedLibraryProfileId;
              selectedTokenId = null;
              joinAsNew();
              return;
            }
            selectedProfileId = selectedEntry && selectedEntry.libraryId ? String(selectedEntry.libraryId).trim() : '';
            selectedTokenId = selectedId;
            claimCharacter();
          },
          onCreateNative() {
            location.href = getCreateUrl();
          },
          onNativeSaved(savedProfile) {
            if (savedProfile && savedProfile.name) {
              setFeedback('Saved ' + savedProfile.name + ' to your character library.', 'success');
            }
          },
          onImportDDB() {
            setFeedback('Import ready. Finish the import and then choose the new hero to enter.', 'success');
          },
          onError(message) {
            setFeedback(message || 'Something went wrong in the hero gateway.', 'error');
          },
        },
        elements: {
          charGrid: els.characterList,
          useExistingBtn: els.enterBtn,
          createNativeBtn: els.createBtn,
          importDdbBtn: els.importBtn,
          existingSection: null,
          actionsSection: els.builderHost,
          gatewayButtonsWrap: els.actionButtons,
          emptyHint: null,
        },
      });
      const originalLoadCharacters = joinGateway.loadCharacters.bind(joinGateway);
      joinGateway.loadCharacters = function patchedLoadCharacters(entries, preferredId) {
        originalLoadCharacters(entries, preferredId);
        renderRosterFromState();
      };
      const originalSelectProfile = joinGateway.selectProfile ? joinGateway.selectProfile.bind(joinGateway) : null;
      if (originalSelectProfile) {
        joinGateway.selectProfile = function patchedSelectProfile(id) {
          originalSelectProfile(id);
          renderRosterFromState();
        };
      }
      joinGateway.init();
    }

    function renderRosterFromState() {
      if (!joinGateway || !gatewayState) return;
      const snapshot = gatewayState.getState ? gatewayState.getState() : { characters: [] };
      const entries = Array.isArray(snapshot.characters) ? snapshot.characters : [];
      const selectedId = joinGateway.getSelectedProfileId ? joinGateway.getSelectedProfileId() : '';
      els.enterBtn.disabled = !selectedId;
      if (!entries.length) {
        renderEmptyState('No existing hero matched this invite yet. Create a new one or import your build to continue.');
        return;
      }
      els.characterList.innerHTML = '';
      entries.forEach((entry) => {
        const row = renderCharacterCard(entry);
        if (entry.id === selectedId) row.classList.add('selected');
        els.characterList.appendChild(row);
      });
    }

    async function loadSessionInfo() {
      const qs = new URLSearchParams({ role: ROLE, player_key: getPlayerKey(), user_name: authUser ? (authUser.character_name || authUser.username || '') : '' });
      const data = await fetchJson(`/api/session/${encodeURIComponent(SESSION_ID)}/lobby?${qs.toString()}`);
      campaignName = data.campaign_name || 'Campaign';
      sessionTokens = Array.isArray(data.tokens) ? data.tokens : [];
      els.campaignName.textContent = campaignName;
      els.inviteStatus.textContent = 'Invite verified';
      els.panelTitle.textContent = 'Hero Roster for ' + campaignName;
      els.panelCopy.textContent = 'Choose the character you want to bring into ' + campaignName + ', or create/import one before entering.';
      els.heroCopy.textContent = 'The player invite now lands on the new hero page. Sign in, choose from native or homebrew-ready characters, then head straight into ' + campaignName + '.';
      els.footerCopy.textContent = 'Invite links now route players through this hero page instead of the old join screen.';
    }

    function mapCharacters() {
      const userName = String((authUser && (authUser.character_name || authUser.username)) || '').trim().toLowerCase();
      const mapped = sessionTokens.map((t) => {
        const ownerName = String(t.owner_name || '').trim().toLowerCase();
        const likelyMine = !ownerName || (userName && ownerName === userName);
        return {
          id: t.id,
          name: t.name,
          color: t.color,
          shape: t.shape,
          mine: likelyMine,
          ownerLabel: likelyMine ? 'Already linked to your account' : (t.owner_name ? ('Played by ' + t.owner_name) : 'Available in session'),
        };
      });
      const preferred = mapped.find((c) => c.mine) || mapped[0] || null;
      joinGateway.loadCharacters(mapped, preferred ? preferred.id : null);
    }

    async function claimCharacter() {
      try {
        setFeedback('Binding the selected hero to this session…');
        const data = await fetchJson('/api/session/join', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: SESSION_ID, invite_code: INVITE, claim_token: selectedTokenId }),
        });
        saveAndEnter(data);
      } catch (err) {
        setFeedback(err.message || 'Could not enter with that hero.', 'error');
      }
    }

    async function joinAsNew() {
      try {
        setFeedback('Creating your session entry…');
        const data = await fetchJson('/api/session/join', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: SESSION_ID, invite_code: INVITE, claim_token: null }),
        });
        saveAndEnter(data);
      } catch (err) {
        setFeedback(err.message || 'Could not join the session.', 'error');
      }
    }

    function rememberSelectedProfile(data) {
      const profileId = String(selectedProfileId || '').trim();
      if (!profileId || !data || !data.session_id) return;
      const identitySeed = String(data.user_id || data.name || (authUser && authUser.username) || 'player').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
      const identity = identitySeed || 'player';
      const key = `tavern_char_profile_${String(data.session_id).trim().toUpperCase()}_${identity}`;
      try { localStorage.setItem(key, profileId); } catch (_) {}
    }

    function saveAndEnter(data) {
      rememberSelectedProfile(data);
      localStorage.setItem('tavern_last_session', JSON.stringify({
        session_id: data.session_id,
        invite_code: INVITE,
        name: data.name,
        role: data.role,
      }));
      const search = new URLSearchParams({
        session_id: data.session_id,
        user_id: data.user_id,
        role: data.role,
        name: data.name,
        returning: data.returning ? '1' : '0',
      });
      location.href = '/play?' + search.toString();
    }

    function escapeHtml(input) {
      return String(input || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    async function init() {
      if (!SESSION_ID || !INVITE) {
        els.inviteStatus.textContent = 'Invalid link';
        els.campaignName.textContent = 'Unknown realm';
        setFeedback('This invite link is missing the session or invite code. Ask the DM for a fresh player link.', 'error');
        renderEmptyState('Open a valid player invite to choose a hero for that campaign.');
        return;
      }
      try {
        const me = await fetch('/api/auth/me', { credentials: 'same-origin' });
        if (!me.ok) {
          redirectToLogin();
          return;
        }
        const auth = await me.json();
        authUser = auth && auth.user ? auth.user : null;
        if (!authUser) {
          redirectToLogin();
          return;
        }
        els.accountStatus.textContent = (authUser.username || 'Signed in') + ' · ' + (authUser.role || 'player');
        setupJoinGateway();
        await loadSessionInfo();
        mapCharacters();
        if (CREATED_PROFILE) {
          selectedProfileId = CREATED_PROFILE;
          setFeedback('Your new hero has been forged. Choose them to enter the realm, or create another.', 'success');
        } else {
          setFeedback('Hero gateway ready. Pick your character or build one before entering.', 'success');
        }
      } catch (err) {
        setFeedback(err.message || 'Could not open the hero gateway.', 'error');
        renderEmptyState('The hero roster could not be loaded. Refresh the page or request a new invite link.');
      }
    }

    els.createBtn.addEventListener('click', () => {
      location.href = getCreateUrl();
    });

    els.refreshBtn.addEventListener('click', async () => {
      setFeedback('Refreshing roster…');
      try {
        await loadSessionInfo();
        mapCharacters();
        setFeedback('Roster refreshed.', 'success');
      } catch (err) {
        setFeedback(err.message || 'Could not refresh the roster.', 'error');
      }
    });

    init();
  