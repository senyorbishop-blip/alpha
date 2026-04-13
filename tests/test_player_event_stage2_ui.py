import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_player_shell_exposes_scoped_event_handler():
    shell_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "ui", "player_shell.js")
    with open(shell_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "function handleScopedEvent(env, msg)" in src
    assert "recordScopedEvent(env, msg)" in src
    assert "function renderDashboard(env)" in src
    assert "data-player-emote-id" in src
    assert "env?.triggerTokenEmote?.(emoteId)" in src
    assert "env?.getTokenEmoteDefs?.() || {}" in src
    assert "window.AppUIPlayerShell = { applyCharacterBookToQuickPanel, openMyTokenPanel, handleScopedEvent, renderDashboard }" in src
    assert "function buildMomentEvent(type, payload = {}, msg = {})" in src
    assert "if (type === 'quest_update' || type === 'session_quest_accept_result' || type === 'session_quest_objective_result' || type === 'session_quest_turn_in_result' || type === 'session_event_notice' || type === 'world_event_notice')" in src
    assert "payload.dm_only === true || payload.player_safe === false" in src
    assert "Recent moments" in src
    assert "data-moment-type=" in src


def test_token_emote_module_exposes_live_helpers():
    module_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "ui", "token_emotes.js")
    with open(module_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "const TOKEN_EMOTE_DEFS = {" in src
    assert "function getMyReactableToken(env)" in src
    assert "const activeTokenId = String(env?.activeTokenId || '')" in src
    assert "function renderPanel(env)" in src
    assert "function trigger(env, emoteId)" in src
    assert "function apply(env, payload = {})" in src
    assert "function getRenderState(tokenId)" in src
    assert "window.AppUITokenEmotes = {" in src


def test_play_page_routes_player_only_ui_messages_through_player_shell():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "function __createPlayerShellEnv()" in src
    assert '/static/js/ui/token_emotes.js"></script>' in src
    assert '/static/js/ui/player_shell.js"></script>' in src
    assert "function __renderPlayerDashboardShell()" in src
    assert "function __handlePlayerScopedUiEvent(msg)" in src
    assert "getTokenEmoteDefs: () => TOKEN_EMOTE_DEFS" in src
    assert "getTokenEmoteCooldownRemainingMs: () => _tokenEmoteCooldownRemainingMs()" in src
    assert "triggerTokenEmote," in src
    assert "id=\"player-dashboard-shell\"" in src
    assert "case 'handout_received': {" in src
    assert "case 'discovery_card': {" in src
    assert "case 'prop_action_result': {" in src
    assert "case 'inventory_action_result': {" in src
    assert src.count("__handlePlayerScopedUiEvent(msg)") >= 3
    assert "__renderPlayerDashboardShell();" in src
    assert "loadSavedDiscoveries(p.saved_discoveries || []);" in src
    assert "__loadPlayerRecentMoments((p.world_state && Array.isArray(p.world_state.recent_events)) ? p.world_state.recent_events : []);" in src
    assert "getRecentMomentEvents: () => {" in src
    assert "case 'world_event_notice': {" in src


def test_play_page_exposes_loot_reveal_and_inventory_inspect_flow():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'id="loot-reveal-modal"' in src
    assert "function openLootRevealModal(payload = {})" in src
    assert "function findLootRevealSourceItem(items, target)" in src
    assert "function syncLootRevealStateWithInventory()" in src
    assert "function inspectInventoryItem(index)" in src
    assert "function openLootDistributionInspect(index)" in src
    assert "switchToInventoryFromLootReveal()" in src
    assert 'id="party-stash-widget"' in src
    assert 'id="party-stash-target-row"' in src
    assert 'id="party-stash-target"' in src
    assert "function sendInventoryItemToStash(index, qty)" in src
    assert "function getPartyStashTargetUserId()" in src
    assert "function claimPartyStashItem(index, qty, targetUserId = '')" in src
    assert "function claimSelectedLootRevealStashItem(qty)" in src
    assert "function renderPartyStashWidget()" in src
    assert "openLootRevealModal({" in src
    assert "syncLootRevealStateWithInventory();" in src
    assert "findLootRevealSourceItem(sourceItems, selectedItem)" in src
    assert 'id="inventory-action-feedback"' in src
    assert "function setInventoryActionFeedback(message = '', kind = 'info')" in src
    assert "function inventoryMessageLooksError(message)" in src
    assert "Attunement:" in src
    assert "Quest / Special" in src


def test_player_shell_handles_discovery_cards():
    shell_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "ui", "player_shell.js")
    with open(shell_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "if (type === 'discovery_card')" in src
    assert "env.showDiscoveryCard?.(discovery);" in src
    assert "discoveryTitle" in src
    assert "getLatestDiscoveryMeta" in src
    assert "getSavedDiscoveries" in src
    assert "Saved discoveries" in src
    assert "You personally uncovered" in src
    assert "getPrivateStoryHooks" in src
    assert "Private prompts & objectives" in src
    assert "window.ChestView.showTakeResult?.(payload.message || '', payload.success !== false);" in src
    assert "momentType" in src
    assert "player-dashboard-moments" in src


def test_play_page_exposes_dm_discovery_composer_hooks():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'id="discovery-composer-section"' in src
    assert 'id="discovery-admin-list"' in src
    assert "function sendDiscoveryCardFromComposer()" in src
    assert "function renderDMDiscoveryList()" in src
    assert "function revealQueuedDiscovery(id)" in src


def test_play_page_exposes_private_story_hook_dm_hooks():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'id="private-story-hook-section"' in src
    assert 'id="private-story-hook-admin-list"' in src
    assert "function togglePrivateStoryHookComposer()" in src
    assert "function refreshPrivateStoryHookPlayerDropdown()" in src
    assert "function savePrivateStoryHookFromComposer()" in src
    assert "function renderPrivateStoryHookAdminList()" in src
    assert "case 'private_story_hooks_sync': {" in src
    assert "case 'private_story_hook_admin_status': {" in src


def test_state_store_tracks_last_player_scoped_event_shell_state():
    store_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "state", "store.js")
    with open(store_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "lastScopedEvent" in src
    assert "dashboard" in src
    assert "latestTitle" in src
    assert "latestKind" in src
    assert "savedCount" in src
    assert "storyHooks" in src
    assert "objectiveCount" in src


def test_play_page_exposes_reusable_prop_interaction_hooks():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "function getEditorPropInteractionModel(item)" in src
    assert "function getEditorPropInteractionAction(item, actionId)" in src
    assert "function triggerEditorPropInteraction(item, actionId)" in src
    assert "triggerEditorPropInteraction(item, 'open_contents')" in src


def test_play_page_exposes_player_token_emote_ui():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'id="token-emote-panel"' in src
    assert "const TOKEN_EMOTE_DEFS =" in src
    assert "function __createTokenEmoteEnv()" in src
    assert "activeTokenId: _tokenEmotePalette.tokenId || ''" in src
    assert "function getOwnedReactableTokens()" in src
    assert "function hitTestTokenEmoteActivator(wx, wy)" in src
    assert "function hitTestTokenEmotePalette(wx, wy)" in src
    assert "function closeTokenEmotePalette()" in src
    assert "function syncTokenEmotePaletteState()" in src
    assert "function renderTokenEmotePanel()" in src
    assert "function triggerTokenEmote(emoteId)" in src
    assert "case 'token_emote': {" in src


def test_play_page_exposes_offturn_combat_tray_hooks():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert 'id="combat-offturn-row"' in src
    assert ".combat-offturn-row" in src
    assert "function offturnReact()" in src
    assert "function offturnReadyAction()" in src
    assert "function offturnMarkTarget()" in src
    assert "function offturnRequestAssist()" in src
    assert "function offturnInspectEnemy()" in src
    assert "function offturnSuggestMove()" in src
    assert "function offturnPingDanger()" in src
    assert "Off-turn actions while" in src


def test_render_player_list_escapes_names_and_guards_role_markup():
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "const safeRole = (u && (u.role === 'dm' || u.role === 'player' || u.role === 'viewer')) ? u.role : 'player';" in src
    assert "const safeName = escapeHtml(String((u && u.name) || 'Unknown'));" in src
    assert '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${safeName}</span>' in src
    assert '<span class="role-tag ${safeRole}">${safeRole.toUpperCase()}</span>' in src
    assert "if (safeRole === 'viewer')" in src


def test_server_session_exposes_prop_interaction_model():
    session_path = os.path.join(PROJECT_ROOT, "server", "session.py")
    with open(session_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "def build_editor_prop_interaction_model(item: dict, role: str) -> dict:" in src
    assert 'item_copy["interactable"] = build_editor_prop_interaction_model(item_copy, role)' in src
