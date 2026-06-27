(function () {
  function getConditionEnv(deps) {
    return {
      document: deps.document,
      CONDITIONS_MAP: deps.CONDITIONS_MAP,
      escapeHtml: deps.escapeHtml,
      tokens: deps.tokens,
      _stagingTokens: deps._stagingTokens,
      USER_ID: deps.USER_ID,
      _teTokenId: deps.getActiveTokenEditorId(),
      ctxToken: deps.getContextToken(),
    };
  }
  function getViewerEnv(deps) {
    return {
      viewerProfiles: deps.viewerProfiles,
      viewerPowerCatalog: deps.viewerPowerCatalog,
      formatShortDurationSeconds: deps.formatShortDurationSeconds,
      sendWS: deps.sendWS,
    };
  }
  function getHazardEnv(deps) {
    return {
      document: deps.document,
      cam: deps.cam,
      ROLE: deps.ROLE,
      hazardZones: deps.hazardZones,
      drawFrame: deps.drawFrame,
      showToast: deps.showToast,
      sendWS: deps.sendWS,
      getCurrentMapContext: deps.getCurrentMapContext,
      getHazardEditZoneId: deps.getHazardEditZoneId,
      setHazardEditZoneId: deps.setHazardEditZoneId,
      getHazardPlacementMode: deps.getHazardPlacementMode,
      setHazardPlacementMode: deps.setHazardPlacementMode,
      getHazardPlacementDraft: deps.getHazardPlacementDraft,
      setHazardPlacementDraft: deps.setHazardPlacementDraft,
    };
  }
  function getInventoryEnv(deps) {
    return {
      users: deps.users,
      USER_ID: deps.USER_ID,
      ROLE: deps.ROLE,
      getPlayerInventory: () => deps.playerInventory,
      setPlayerInventory: deps.setPlayerInventory,
      getPlayerInventories: () => deps.playerInventories,
      setPlayerInventories: deps.setPlayerInventories,
      getPlayerGold: () => deps.playerGold,
      setPlayerGold: deps.setPlayerGold,
      getPartyLootLog: () => deps.partyLootLog,
      setPartyLootLog: deps.setPartyLootLog,
    };
  }
  function getCombatEnv(deps) {
    return {
      document: deps.document,
      ROLE: deps.ROLE,
      USER_ID: deps.USER_ID,
      tokens: deps.tokens,
      _currentPoi: deps.getCurrentPoi(),
      _charSheet: deps.getCharSheet(),
      addLogEntry: deps.addLogEntry,
      getStore: deps.getStore,
      getUserName: deps.getUserName,
      showToast: deps.showToast,
      sendWS: deps.sendWS,
      showDiceAnimation: deps.showDiceAnimation,
      fillDiceResult: deps.fillDiceResult,
      appDiceSyncResult: deps.appDiceSyncResult,
      appDiceSyncAuthoritativePayload: deps.appDiceSyncAuthoritativePayload,
      appDiceShowLocalResult: deps.appDiceShowLocalResult,
      confirm: deps.confirm,
      prompt: deps.prompt,
      getCombat: deps.getCombat,
      setCombat: deps.setCombat,
      getCombatRound: deps.getCombatRound,
      setCombatRound: deps.setCombatRound,
      renderCombat: deps.renderCombat,
      getCombatTargeting: deps.getCombatTargeting,
      setCombatTargeting: deps.setCombatTargeting,
      pulseCombatTarget: deps.pulseCombatTarget,
    };
  }
  window.AppEnvBuildersGameplay = { getConditionEnv, getViewerEnv, getHazardEnv, getInventoryEnv, getCombatEnv };
})();
