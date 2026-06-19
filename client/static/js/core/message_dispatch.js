(function (global) {
  'use strict';
  // Live runtime guardrail:
  // This module is intentionally only the first-hop dispatcher.
  // Final gameplay message application remains in play.html via
  // `handleLegacyMessage()` until an explicit wiring migration.
  //
  // Phase 3 ownership reduction:
  // - Keep gameplay source-of-truth in play.html.
  // - Move low-risk websocket/message shell routing here by
  //   delegating to explicit env callbacks.

  const recentMessageTypes = [];
  const dispatchChain = [];
  let dispatchDepth = 0;

  function rememberMessageType(type) {
    recentMessageTypes.push(String(type || '(missing)'));
    if (recentMessageTypes.length > 30) recentMessageTypes.splice(0, recentMessageTypes.length - 30);
  }

  function logDispatchDiagnostics(reason, err) {
    const payload = {
      reason,
      depth: dispatchDepth,
      chain: dispatchChain.slice(),
      recentMessageTypes: recentMessageTypes.slice(),
    };
    console.error('[AppMessageDispatch] dispatch diagnostics', payload, err || '');
    return payload;
  }

  function handleIncoming(msg, env) {
    if (!msg || typeof msg !== 'object') return false;
    const runtimeEnv = env || {};
    if (typeof runtimeEnv.handleLegacyMessage !== 'function') return false;
    const msgType = String(msg.type || '(missing)');
    rememberMessageType(msgType);
    if (dispatchDepth >= 20) {
      const diagnostics = logDispatchDiagnostics('nested dispatch depth exceeded', null);
      const err = new Error('Nested websocket dispatch depth exceeded 20; refusing recursive message dispatch.');
      err.dispatchDiagnostics = diagnostics;
      if (typeof runtimeEnv.reportClientRuntimeError === 'function') runtimeEnv.reportClientRuntimeError('Message dispatch', err);
      return false;
    }
    dispatchDepth += 1;
    dispatchChain.push(msgType);
    try {
      runtimeEnv.handleLegacyMessage(msg);
      return true;
    } catch (err) {
      const diagnostics = logDispatchDiagnostics(err && /Maximum call stack size exceeded/i.test(String(err.message || err)) ? 'stack overflow' : 'handler exception', err);
      try { err.dispatchDiagnostics = diagnostics; } catch (_err) {}
      if (typeof runtimeEnv.reportClientRuntimeError === 'function') {
        runtimeEnv.reportClientRuntimeError('Message dispatch', err);
      } else {
        console.error('[AppMessageDispatch] Message dispatch failed', err);
      }
      return false;
    } finally {
      dispatchChain.pop();
      dispatchDepth = Math.max(0, dispatchDepth - 1);
    }
  }

  function getDispatchDiagnostics() {
    return {
      depth: dispatchDepth,
      chain: dispatchChain.slice(),
      recentMessageTypes: recentMessageTypes.slice(),
    };
  }

  function handleLegacyDomainMessage(msg, env) {
    if (!msg || typeof msg !== 'object') return false;
    const runtimeEnv = env || {};
    const p = msg.payload || {};
    switch (msg.type) {
      case 'journal_sync':
        if (typeof runtimeEnv.loadJournalEntries === 'function') runtimeEnv.loadJournalEntries(p.entries || []);
        return true;
      case 'party_memory_sync':
        if (typeof runtimeEnv.loadPartyMemory === 'function') runtimeEnv.loadPartyMemory(p.entries || []);
        return true;
      case 'handout_sync':
        if (typeof runtimeEnv.loadHandouts === 'function') runtimeEnv.loadHandouts(p.handouts || []);
        return true;
      case 'private_story_hooks_sync':
        if (typeof runtimeEnv.loadPrivateStoryHooks === 'function') runtimeEnv.loadPrivateStoryHooks(p.hooks || []);
        return true;
      case 'encounter_templates_sync':
        if (typeof runtimeEnv.loadEncounterTemplates === 'function') runtimeEnv.loadEncounterTemplates(p.templates || []);
        return true;
      case 'quest_template_library_sync': {
        if (typeof runtimeEnv.setQuestTemplateLibrary === 'function') {
          runtimeEnv.setQuestTemplateLibrary(Array.isArray(p.templates) ? p.templates.filter(function (entry) {
            return !!entry && typeof entry === 'object';
          }) : []);
        }
        if (typeof runtimeEnv.refreshGuildBoardIfOpen === 'function') runtimeEnv.refreshGuildBoardIfOpen();
        return true;
      }
      case 'prep_pack_library_sync': {
        if (typeof runtimeEnv.setPrepPackLibrary === 'function') {
          runtimeEnv.setPrepPackLibrary(Array.isArray(p.packs) ? p.packs.filter(function (entry) {
            return !!entry && typeof entry === 'object';
          }) : []);
        }
        if (typeof runtimeEnv.refreshGuildBoardIfOpen === 'function') runtimeEnv.refreshGuildBoardIfOpen();
        return true;
      }
      case 'session_quests_sync': {
        if (typeof runtimeEnv.loadSessionQuests === 'function') runtimeEnv.loadSessionQuests(p.session_quests || []);
        if (typeof runtimeEnv.setQuestBoardBindings === 'function' && Array.isArray(p.quest_board_bindings)) {
          runtimeEnv.setQuestBoardBindings(p.quest_board_bindings.slice());
        }
        if (typeof runtimeEnv.setPremiumQuestProgression === 'function' && p.premium_progression && typeof p.premium_progression === 'object') {
          runtimeEnv.setPremiumQuestProgression(p.premium_progression);
        }
        if (typeof runtimeEnv.refreshGuildBoardIfOpen === 'function') runtimeEnv.refreshGuildBoardIfOpen();
        return true;
      }
      default:
        return false;
    }
  }

  global.AppMessageDispatch = {
    handleIncoming,
    handleLegacyDomainMessage,
    getDispatchDiagnostics,
  };
})(window);
