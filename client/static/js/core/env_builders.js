(function(){
  function buildUIModalsEnv(deps) {
    return {
      document: deps.document,
      fetch: deps.fetchFn,
      getRole: () => deps.role,
      getSessionId: () => deps.sessionId,
      getUserId: () => deps.userId,
      showToast: deps.showToast,
      renderSpellRulesReviewModal: deps.renderSpellRulesReviewModal,
      prefillCustomSpellRule: deps.prefillCustomSpellRule,
      getRulesReviewQueue: deps.getRulesReviewQueue,
      setRulesReviewQueue: deps.setRulesReviewQueue,
      getRulesCustomSpells: deps.getRulesCustomSpells,
      setRulesCustomSpells: deps.setRulesCustomSpells,
      getItemLibraryModalMode: deps.getItemLibraryModalMode,
      setItemLibraryModalMode: deps.setItemLibraryModalMode,
      getItemLibrarySelectedId: deps.getItemLibrarySelectedId,
      setItemLibrarySelectedId: deps.setItemLibrarySelectedId,
      getItemLibraryEntries: deps.getItemLibraryEntries,
      getEscapeHtml: () => deps.escapeHtml,
      renderItemLibraryList: deps.renderItemLibraryList,
      renderItemLibraryEditor: deps.renderItemLibraryEditor,
      refreshItemLibraryPickerSummary: deps.refreshItemLibraryPickerSummary,
      refreshInventoryGoldTargets: deps.refreshInventoryGoldTargets,
    };
  }

  function buildUIItemLibraryActionsEnv(deps) {
    return {
      document: deps.document,
      showToast: deps.showToast,
      sendWS: deps.sendWS,
      getRole: () => deps.role,
      getSelectedId: deps.getSelectedId,
      setSelectedId: deps.setSelectedId,
      getEntries: deps.getEntries,
    };
  }

  function buildUIItemLibraryEnv(deps) {
    return {
      document: deps.document,
      escapeHtml: deps.escapeHtml,
      getEntries: deps.getEntries,
      getSelectedId: deps.getSelectedId,
      setSelectedId: deps.setSelectedId,
      refreshItemLibraryPickerSummary: deps.refreshItemLibraryPickerSummary,
    };
  }

  function buildUIFormsEnv(deps) {
    return {
      document: deps.document,
      escapeHtml: deps.escapeHtml,
      openItemLibraryModal: deps.openItemLibraryModal,
      getRole: () => deps.role,
      getUserId: () => deps.userId,
      getUsers: deps.getUsers,
      getInventoryTransferTargetIdState: deps.getInventoryTransferTargetIdState,
      setInventoryTransferTargetIdState: deps.setInventoryTransferTargetIdState,
    };
  }

  function buildUIItemLibraryPickerEnv(deps) {
    return {
      document: deps.document,
      escapeHtml: deps.escapeHtml,
      showToast: deps.showToast,
      sendWS: deps.sendWS,
      closeItemLibraryModal: deps.closeItemLibraryModal,
      buildInventoryEntryFromLibrary: deps.buildInventoryEntryFromLibrary,
      normalizeEditorPropInventoryEntry: deps.normalizeEditorPropInventoryEntry,
      editorPropSupportsContents: deps.editorPropSupportsContents,
      defaultEditorPropSlots: deps.defaultEditorPropSlots,
      getOpenPropInventoryItem: deps.getOpenPropInventoryItem,
      queueOpenPropInventorySave: deps.queueOpenPropInventorySave,
      refreshEditorPropPopup: deps.refreshEditorPropPopup,
      refreshPropInventoryModal: deps.refreshPropInventoryModal,
      getOpenPropPopupId: deps.getOpenPropPopupId,
      getRole: () => deps.role,
      getEntries: deps.getEntries,
      getSelectedId: deps.getSelectedId,
      getModalMode: deps.getModalMode,
    };
  }

  function buildUIModalActionsEnv(deps) {
    return {
      document: deps.document,
      fetch: deps.fetchFn,
      showToast: deps.showToast,
      sendWS: deps.sendWS,
      closeInventoryGoldModal: deps.closeInventoryGoldModal,
      closeInventoryManualAddModal: deps.closeInventoryManualAddModal,
      openSpellRulesReviewModal: deps.openSpellRulesReviewModal,
      refreshRulesSpellbook: deps.refreshRulesSpellbook,
      resetCustomSpellRuleForm: deps.resetCustomSpellRuleForm,
      loadCustomSpellIntoForm: deps.loadCustomSpellIntoForm,
      collectCustomSpellRuleForm: deps.collectCustomSpellRuleForm,
      getRole: () => deps.role,
      getSessionId: () => deps.sessionId,
      getUserId: () => deps.userId,
      confirm: deps.confirmFn,
    };
  }

  window.AppEnvBuilders = {
    buildUIModalsEnv,
    buildUIItemLibraryActionsEnv,
    buildUIItemLibraryEnv,
    buildUIFormsEnv,
    buildUIItemLibraryPickerEnv,
    buildUIModalActionsEnv,
  };
})();
