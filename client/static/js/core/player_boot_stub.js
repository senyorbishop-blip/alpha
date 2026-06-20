// Minimal player/viewer boot shell and checkpoint initialiser.
// Loaded by play.html in the player/viewer branch in place of the full DM runtime.
(function () {
  var params = new URLSearchParams(location.search);
  window.__PLAY_BOOT_ROLE = (params.get('role') || 'viewer').toLowerCase();
  window.__PLAY_BOOT_MANIFEST = params.get('boot_manifest') || 'viewer';
  window.__playerBootState = window.__playerBootState || { checkpoint: 'PLAYER_BOOT_HTML_LOADED', scriptsStarted: false, wsOpened: false };
  window.__playerBootCheckpoint = function (checkpoint) {
    window.__playerBootState = window.__playerBootState || {};
    window.__playerBootState.checkpoint = checkpoint;
    window.__playerBootState.lastAt = Date.now();
    if (window.__PLAY_BOOT_ROLE === 'player') console.info('[PlayerBoot]', checkpoint);
    var cp = document.getElementById('player-boot-checkpoint');
    if (cp) cp.textContent = checkpoint;
  };
  window.__showPlayerBootFailure = function (message) {
    if (window.__PLAY_BOOT_ROLE !== 'player') return;
    var overlay = document.getElementById('player-boot-failure-overlay');
    if (!overlay) return;
    var state = window.__playerBootState || {};
    overlay.style.display = 'block';
    var msg = document.getElementById('player-boot-failure-message');
    if (msg) msg.textContent = message;
    var cp = document.getElementById('player-boot-checkpoint');
    if (cp) cp.textContent = state.checkpoint || 'unknown';
  };
  window.__playerBootCheckpoint('PLAYER_BOOT_HTML_LOADED');
  setTimeout(function () {
    if (window.__PLAY_BOOT_ROLE === 'player' && !(window.__playerBootState || {}).scriptsStarted) {
      window.__showPlayerBootFailure('Player boot failed before scripts loaded.');
    }
  }, 5000);
  setTimeout(function () {
    if (window.__PLAY_BOOT_ROLE === 'player' && !(window.__playerBootState || {}).wsOpened) {
      window.__showPlayerBootFailure('Player boot failed before WebSocket.');
    }
  }, 10000);
})();

var _pbParams = new URLSearchParams(location.search);
var SESSION_ID = _pbParams.get('session_id') || '';
var USER_ID = _pbParams.get('user_id') || '';
var ROLE = ((_pbParams.get('role') || 'viewer')).toLowerCase();
var NAME = _pbParams.get('name') || '';
var RETURNING = _pbParams.get('returning') || '';
var ws = null;
var wsReconnectTimer = null;
var _pendingWSMessages = [];
var _queuedEditorTypes = new Set();
var tokens = {};
function getEffectiveUserId(){ return USER_ID; }
function getEffectiveRole(){ return ROLE; }
function reportClientRuntimeError(label, err){ console.error('[CLIENT RUNTIME]', label, err); }
function safeClientCall(label, fn, fallback){ if (fallback === undefined) fallback = null; try { return fn(); } catch (err) { reportClientRuntimeError(label, err); return fallback; } }
function showToast(msg){ console.info('[Toast]', msg); }
function _setWsStatus(status){ console.info('[WS status]', status); }
function syncSessionAuthority(){ return Promise.resolve(null); }
function initUI(){}
function initCanvas(){}
function __bootApplyRoleVisibility(){}
function _updateSpellTip(){}
function initJournalPanel(){}
function initLogsUI(){}
function renderItemLibraryList(){}
function renderItemLibraryEditor(){}
function refreshInventoryTransferTargets(){}
function refreshCharProfileSelect(){}
function buildClassGrid(){}
function buildPlayerColorSwatches(){}
function toggleFlyout(){}
function sendChat(){ var input=document.getElementById('chat-input'); var text=(input&&input.value||'').trim(); if(text) sendWS({type:'chat', payload:{text}}); }
function handleLegacyMessage(msg){
  if (msg && msg.type === 'state_sync' && window.__PLAY_BOOT_ROLE === 'player' && typeof window.__playerBootCheckpoint === 'function') {
    window.__playerBootCheckpoint('PLAYER_BOOT_STATE_SYNC_APPLIED');
  }
}
function connectWS(){
  if (!(window.AppWS && window.AppRuntimeBridge && typeof window.AppRuntimeBridge.createWsConfig === 'function')) return null;
  window.AppWS.configure(window.AppRuntimeBridge.createWsConfig());
  _setWsStatus('connecting');
  ws = window.AppWS.ensureConnected({ reason: 'boot' });
  return ws;
}
function sendWS(msg){ if (window.AppWS && typeof window.AppWS.send === 'function') return window.AppWS.send(msg); }
document.addEventListener('DOMContentLoaded', function () {
  if (window.AppBootShell && window.AppRuntimeBridge && typeof window.AppRuntimeBridge.createBootEnv === 'function') {
    window.AppBootShell.runDOMContentLoaded(window.AppRuntimeBridge.createBootEnv());
  } else {
    connectWS();
  }
});

if (window.__playerBootCheckpoint) window.__playerBootCheckpoint('PLAYER_BOOT_CORE_LOADED');
