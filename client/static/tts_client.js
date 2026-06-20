/**
 * tts_client.js — Frontend TTS client for Tavern Tabletop GPU narration.
 *
 * Integrates with the existing DM panel without modifying button IDs,
 * class names, or CSS variables.
 *
 * Responsibilities:
 *   1. Fetch voices from /api/tts/voices → populate narration dropdown
 *   2. Fetch warmup phrases → render clickable chips below textarea
 *   3. Override dmNarrationPreview() / dmNarrationSpeak() / dmNarrationStop()
 *      to use the new GPU TTS API
 *   4. Show generation time + engine name in status row
 *   5. Handle WebSocket tts_narration / tts_narration_stop messages
 *   6. Audio unlock overlay (browser AudioContext gate)
 *   7. Track per-player audio readiness, shown in DM panel
 *   8. Expose window.tavernTTS namespace
 *   9. Instantiate window.tavernAmbient (AmbientEngine) +
 *      window.tavernSFX (SFXEngine) and wire to existing DM buttons
 */

'use strict';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TTS_API   = '/api/tts';
const TTS_LOG   = '[TavernTTS]';
const RUNE_ANIM = 'tts-rune-pulse';   // CSS animation class

// ---------------------------------------------------------------------------
// Audio unlock overlay (browser requires user gesture before AudioContext)
// ---------------------------------------------------------------------------

let _audioCtx          = null;
let _audioCtxReady     = false;
const _audioQueue      = [];   // WAV blobs queued before user unlocks audio
let _playerReadyMap    = {};   // { userId: { displayName, ready } }
let _htmlAudioEl       = null; // iOS/Safari fallback path when decodeAudioData fails

function _ensureAudioCtx() {
  if (_audioCtx) return _audioCtx;
  _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return _audioCtx;
}

function _showAudioUnlockOverlay() {
  if (document.getElementById('tts-audio-unlock-overlay')) return;

  const overlay = document.createElement('div');
  overlay.id = 'tts-audio-unlock-overlay';
  overlay.style.cssText = `
    position: fixed; inset: 0;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    z-index: 9998; pointer-events: none;
  `;

  const card = document.createElement('div');
  card.style.cssText = `
    background: var(--bg-primary, #1a1a2e);
    border: 1px solid var(--accent-gold, #d4a637);
    border-radius: 12px;
    padding: 2rem 2.5rem;
    text-align: center;
    color: var(--text-primary, #e8dcc8);
    max-width: 320px;
    pointer-events: all;
    opacity: 0.92;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  `;

  card.innerHTML = `
    <div id="tts-rune-icon" style="font-size:2.8rem;margin-bottom:1rem;animation:${RUNE_ANIM} 2s ease-in-out infinite;">᛭</div>
    <div style="font-size:1.05rem;font-family:'Cinzel',serif;color:var(--accent-gold,#d4a637);margin-bottom:0.6rem;">Click to enable tavern audio</div>
    <div style="font-size:0.75rem;opacity:0.7;line-height:1.4;">Ambient sounds &amp; narration require a user interaction to activate.</div>
  `;

  // Inject keyframe animation if not already present
  if (!document.getElementById('tts-rune-style')) {
    const style = document.createElement('style');
    style.id = 'tts-rune-style';
    style.textContent = `
      @keyframes ${RUNE_ANIM} {
        0%,100% { opacity:0.5; transform:scale(1); }
        50%      { opacity:1.0; transform:scale(1.18); text-shadow:0 0 14px var(--accent-gold,#d4a637); }
      }
    `;
    document.head.appendChild(style);
  }

  overlay.appendChild(card);
  document.body.appendChild(overlay);
}

function _unlockAudio() {
  if (_audioCtxReady) return;
  try {
    _ensureAudioCtx();
  } catch (err) {
    console.warn(`${TTS_LOG} AudioContext unavailable:`, err);
    return;
  }
  if (!_audioCtx) return;
  if (_audioCtx.state === 'suspended') {
    _audioCtx.resume().catch(() => {});
  }
  _audioCtxReady = true;

  // Remove overlay
  const ol = document.getElementById('tts-audio-unlock-overlay');
  if (ol) ol.remove();

  // Flush queued audio
  _audioQueue.forEach(fn => fn());
  _audioQueue.length = 0;

  // Notify server
  _wsSend({ type: 'player_audio_ready', payload: {} });

  console.info(`${TTS_LOG} AudioContext unlocked`);
}

// One-time user-gesture listeners (touch/pointer added for mobile Safari/Chrome)
document.addEventListener('pointerdown', _unlockAudio, { once: true });
document.addEventListener('touchend', _unlockAudio, { once: true });
document.addEventListener('click', _unlockAudio, { once: true });
document.addEventListener('keydown', _unlockAudio, { once: true });


// ---------------------------------------------------------------------------
// Core audio playback helper
// ---------------------------------------------------------------------------

/**
 * Decode and play a WAV ArrayBuffer via the shared AudioContext.
 * Returns a Promise that resolves to duration_ms when decode succeeds.
 */
async function _playWavBytes(arrayBuffer, onEnded) {
  const ctx = _ensureAudioCtx();
  if (ctx.state === 'suspended') await ctx.resume();

  try {
    return await new Promise((resolve, reject) => {
      ctx.decodeAudioData(arrayBuffer.slice(0), (decoded) => {
        const src = ctx.createBufferSource();
        src.buffer = decoded;
        src.connect(ctx.destination);
        src.onended = () => { if (onEnded) onEnded(); };
        src.start();
        resolve(Math.round(decoded.duration * 1000));
      }, reject);
    });
  } catch (err) {
    console.warn(`${TTS_LOG} decodeAudioData failed; using <audio> fallback`, err);
    if (_htmlAudioEl) {
      try { _htmlAudioEl.pause(); } catch {}
      _htmlAudioEl = null;
    }
    return new Promise((resolve, reject) => {
      const blob = new Blob([arrayBuffer], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audioEl = new Audio(url);
      _htmlAudioEl = audioEl;
      audioEl.preload = 'auto';
      audioEl.onended = () => {
        if (_htmlAudioEl === audioEl) _htmlAudioEl = null;
        URL.revokeObjectURL(url);
        if (onEnded) onEnded();
      };
      audioEl.onerror = (e) => {
        if (_htmlAudioEl === audioEl) _htmlAudioEl = null;
        URL.revokeObjectURL(url);
        reject(e);
      };
      audioEl.onloadedmetadata = () => {
        resolve(Math.round((audioEl.duration || 0) * 1000));
      };
      audioEl.play().catch((playErr) => {
        if (_htmlAudioEl === audioEl) _htmlAudioEl = null;
        URL.revokeObjectURL(url);
        reject(playErr);
      });
    });
  }
}

// Convert wav bytes to base64 string
function _arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary  = '';
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

// Convert base64 string to ArrayBuffer
function _base64ToArrayBuffer(b64) {
  const bin = atob(b64);
  const buf = new ArrayBuffer(bin.length);
  const u8  = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return buf;
}

// Estimate WAV duration from header bytes
function _wavDurationMs(buffer) {
  try {
    const view     = new DataView(buffer);
    const byteRate = view.getUint32(28, true);  // bytes/sec from WAV header
    const dataSize = view.getUint32(40, true);  // data chunk size
    return Math.round((dataSize / byteRate) * 1000);
  } catch { return 0; }
}


// ---------------------------------------------------------------------------
// TTS fetch helpers
// ---------------------------------------------------------------------------

async function _fetchTTS(text, voicePreset, speed = 1.0, emotion = 'neutral') {
  const resp = await fetch(`${TTS_API}/speak`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ text, voice_preset: voicePreset, speed, emotion }),
  });
  if (!resp.ok) throw new Error(`TTS API ${resp.status}: ${await resp.text()}`);

  const engine    = resp.headers.get('X-TTS-Engine')     || 'unknown';
  const latencyMs = resp.headers.get('X-TTS-Latency-Ms') || '?';
  const cacheHit  = resp.headers.get('X-TTS-Cache')      === 'hit';

  const arrayBuf = await resp.arrayBuffer();
  return { arrayBuf, engine, latencyMs: parseInt(latencyMs, 10) || 0, cacheHit };
}


// ---------------------------------------------------------------------------
// DM panel status helpers
// ---------------------------------------------------------------------------

function _setStatus(msg, color = 'var(--text-primary, #e8dcc8)') {
  const el = document.getElementById('narration-integration-status');
  if (!el) return;
  el.textContent  = msg;
  el.style.color  = color;
  el.style.display = msg ? 'block' : 'none';
}

function _setPreviewStatus(msg) {
  const el = document.getElementById('narration-preview-status');
  if (!el) return;
  el.textContent   = msg;
  el.style.display = msg ? 'block' : 'none';
}

function _startRunePulse() {
  const el = document.querySelector('.sidebar-label, #flyout-sound .sidebar-label');
  if (el) el.classList.add('tts-narrating');
  _showNarrationIndicator();
}

function _stopRunePulse() {
  document.querySelectorAll('.tts-narrating').forEach(el => el.classList.remove('tts-narrating'));
  _hideNarrationIndicator();
}

function _showNarrationIndicator() {
  let ind = document.getElementById('tts-narration-indicator');
  if (!ind) {
    ind = document.createElement('div');
    ind.id = 'tts-narration-indicator';
    ind.style.cssText = `
      position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
      background: rgba(30,25,20,0.92); color: #d4a637; border: 1px solid #d4a637;
      border-radius: 8px; padding: 6px 18px; font-size: 0.85rem; z-index: 9999;
      pointer-events: none; display: flex; align-items: center; gap: 6px;
      box-shadow: 0 0 12px rgba(212,166,55,0.3);
      animation: tts-rune-header 1.2s ease-in-out infinite;
    `;
    ind.textContent = '\u{1F50A} Narration playing\u2026';
    document.body.appendChild(ind);
  }
  ind.style.display = 'flex';
}

function _hideNarrationIndicator() {
  const ind = document.getElementById('tts-narration-indicator');
  if (ind) ind.style.display = 'none';
}

// Inject keyframe for rune pulse on panel header
(function _injectPanelRuneStyle() {
  if (document.getElementById('tts-panel-rune-style')) return;
  const style = document.createElement('style');
  style.id = 'tts-panel-rune-style';
  style.textContent = `
    @keyframes tts-rune-header {
      0%,100% { box-shadow: none; }
      50%      { box-shadow: 0 0 8px 2px var(--accent-gold,#d4a637); }
    }
    .tts-narrating {
      animation: tts-rune-header 1.2s ease-in-out infinite;
    }
  `;
  document.head.appendChild(style);
})();


// ---------------------------------------------------------------------------
// Voice dropdown population
// ---------------------------------------------------------------------------

async function _populateVoiceDropdown() {
  const select = document.getElementById('narration-voice-preset');
  if (!select) return;

  let data;
  try {
    const resp = await fetch(`${TTS_API}/voices`);
    if (!resp.ok) throw new Error(`voices API ${resp.status}`);
    data = await resp.json();
  } catch (err) {
    console.warn(`${TTS_LOG} could not fetch voices:`, err);
    return;
  }

  // Clear existing options and rebuild grouped
  select.innerHTML = '';

  const groups = [
    { key: 'narrator', label: '── NARRATORS (Kokoro) ──' },
    { key: 'npc',      label: '── NPC VOICES (Kokoro) ──' },
    { key: 'system',   label: '── SYSTEM (Kokoro) ──' },
  ];

  groups.forEach(({ key, label }) => {
    const presets = (data.grouped || {})[key] || [];
    if (!presets.length) return;
    const group = document.createElement('optgroup');
    group.label = label;
    presets.forEach(p => {
      const opt       = document.createElement('option');
      opt.value       = p.id;
      opt.textContent = p.label;
      opt.title       = p.description || '';
      group.appendChild(opt);
    });
    select.appendChild(group);
  });

  // Engine status in integration-status row
  const engines = data.engines || {};
  if (engines.kokoro?.ready) {
    _setStatus('✓ Kokoro TTS ready', '#4ade80');
  } else {
    _setStatus('⚠ Kokoro TTS not ready  •  check server logs', '#f87171');
  }
}


// ---------------------------------------------------------------------------
// Warmup phrase chips
// ---------------------------------------------------------------------------

async function _renderWarmupPhrases() {
  const textarea = document.getElementById('narration-text-input');
  if (!textarea) return;

  let phrases;
  try {
    const resp = await fetch(`${TTS_API}/warmup-phrases`);
    if (!resp.ok) return;
    const data = await resp.json();
    phrases    = data.phrases || [];
  } catch { return; }

  if (!phrases.length) return;

  // Container inserted directly after the textarea (additive only)
  if (document.getElementById('tts-phrase-chips')) return;
  const container = document.createElement('div');
  container.id = 'tts-phrase-chips';
  container.style.cssText = `
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin-bottom: 0.4rem;
    margin-top: 0.2rem;
  `;

  phrases.forEach(phrase => {
    const chip = document.createElement('button');
    chip.textContent = phrase;
    chip.title       = 'Insert phrase';
    chip.style.cssText = `
      padding: 0.18rem 0.45rem;
      background: rgba(0,0,0,0.25);
      border: 1px solid var(--border-color, rgba(139,105,20,0.3));
      border-radius: 3px;
      color: var(--text-primary, #e8dcc8);
      font-size: 0.55rem;
      cursor: pointer;
      font-family: 'Georgia', serif;
      line-height: 1.3;
    `;
    chip.addEventListener('click', () => {
      const ta  = document.getElementById('narration-text-input');
      if (ta) ta.value = phrase;
    });
    chip.addEventListener('mouseover', () => {
      chip.style.borderColor = 'var(--accent-gold, #d4a637)';
    });
    chip.addEventListener('mouseout', () => {
      chip.style.borderColor = 'var(--border-color, rgba(139,105,20,0.3))';
    });
    container.appendChild(chip);
  });

  textarea.parentNode.insertBefore(container, textarea.nextSibling);
}


// ---------------------------------------------------------------------------
// Override DM narration functions (additive — these are called by onclick=)
// ---------------------------------------------------------------------------

window.dmNarrationPreview = async function () {
  const textarea = document.getElementById('narration-text-input');
  const select   = document.getElementById('narration-voice-preset');
  if (!textarea || !select) return;

  const text   = textarea.value.trim();
  const preset = select.value;
  if (!text) { _setPreviewStatus('Enter text first.'); return; }

  _setPreviewStatus('Generating…');
  const t0 = performance.now();

  try {
    const { arrayBuf, engine, latencyMs, cacheHit } = await _fetchTTS(text, preset);
    const totalMs = Math.round(performance.now() - t0);

    _setPreviewStatus(
      `Generated in ${latencyMs}ms (${engine.toUpperCase()})` +
      (cacheHit ? ' [cache]' : '')
    );

    _startRunePulse();
    const playFn = async () => {
      try {
        await _playWavBytes(arrayBuf, _stopRunePulse);
      } catch (err) {
        console.warn(`${TTS_LOG} playback failed:`, err);
        _stopRunePulse();
      }
    };

    if (_audioCtxReady) {
      playFn();
    } else {
      _audioQueue.push(playFn);
      _unlockAudio(); // prompt user to click
    }
  } catch (err) {
    _setPreviewStatus(`Error: ${err.message}`);
    console.error(`${TTS_LOG} preview error:`, err);
  }
};

window.dmNarrationSpeak = async function () {
  const textarea = document.getElementById('narration-text-input');
  const select   = document.getElementById('narration-voice-preset');
  const policy   = document.getElementById('narration-policy-select');
  if (!textarea || !select) return;

  const text        = textarea.value.trim();
  const preset      = select.value;
  const mode        = policy?.value === 'queue_next' ? 'queue' : 'replace';
  if (!text) { _setPreviewStatus('Enter text first.'); return; }

  _setPreviewStatus('Generating for broadcast…');

  try {
    const { arrayBuf, engine, latencyMs, cacheHit } = await _fetchTTS(text, preset);
    const durationMs = _wavDurationMs(arrayBuf);
    const b64        = _arrayBufferToBase64(arrayBuf);

    _setPreviewStatus(
      `Broadcast via ${engine.toUpperCase()}  ${latencyMs}ms` +
      (cacheHit ? ' [cache]' : '')
    );

    // Send over WebSocket so all players receive it
    _wsSend({
      type: 'tts_narration',
      payload: {
        audio_b64:    b64,
        voice_preset: preset,
        duration_ms:  durationMs,
        text:         text,
        mode:         mode,
      },
    });
  } catch (err) {
    _setPreviewStatus(`Broadcast error: ${err.message}`);
    console.error(`${TTS_LOG} broadcast error:`, err);
  }
};

window.dmNarrationStop = function () {
  // Stop local playback
  if (_htmlAudioEl) {
    try {
      _htmlAudioEl.pause();
      _htmlAudioEl.currentTime = 0;
    } catch {}
    _htmlAudioEl = null;
  }
  if (_audioCtx) {
    try { _audioCtx.suspend(); } catch {}
    setTimeout(() => { try { _audioCtx.resume(); } catch {} }, 80);
  }
  _stopRunePulse();
  _setPreviewStatus('');

  // Tell all players to stop
  _wsSend({ type: 'tts_narration_stop', payload: {} });
};


// ---------------------------------------------------------------------------
// Receive tts_narration WebSocket messages (players side)
// ---------------------------------------------------------------------------

function _handleTTSNarration(payload) {
  const { audio_b64, voice_preset, duration_ms, text, mode } = payload;

  if (!audio_b64) return;

  const playFn = async () => {
    try {
      const buf = _base64ToArrayBuffer(audio_b64);
      _startRunePulse();
      await _playWavBytes(buf, _stopRunePulse);
    } catch (err) {
      console.warn(`${TTS_LOG} player playback error:`, err);
      _stopRunePulse();
    }
  };

  // Also show text overlay via existing NarrationManager if available
  if (window._narrationManager && text) {
    // Trigger text reveal via existing overlay without audio
    // (audio is handled here in tts_client)
    const nm = window._narrationManager;
    nm._openOverlay(text, false);
    nm._startReveal(text, duration_ms || 4000);
  }

  if (_audioCtxReady) {
    playFn();
  } else {
    _audioQueue.push(playFn);
  }
}

function _handleTTSNarrationStop() {
  _stopRunePulse();
  if (_htmlAudioEl) {
    try {
      _htmlAudioEl.pause();
      _htmlAudioEl.currentTime = 0;
    } catch {}
    _htmlAudioEl = null;
  }
  if (_audioCtx) {
    try { _audioCtx.suspend(); } catch {}
    setTimeout(() => { try { _audioCtx.resume(); } catch {} }, 80);
  }
  if (window._narrationManager) {
    window._narrationManager.stop();
  }
}


// ---------------------------------------------------------------------------
// Player audio-ready tracking (DM panel indicators)
// ---------------------------------------------------------------------------

function _handlePlayerAudioReady(payload) {
  const { user_id, display_name, ready } = payload;
  _playerReadyMap[user_id] = { displayName: display_name || user_id, ready };
  _renderPlayerAudioStatus();
}

function _renderPlayerAudioStatus() {
  // Find or create the player audio status container
  let container = document.getElementById('tts-player-audio-status');
  if (!container) {
    const statusEl = document.getElementById('narration-integration-status');
    if (!statusEl) return;
    container = document.createElement('div');
    container.id = 'tts-player-audio-status';
    container.style.cssText = `
      font-size: 0.58rem;
      margin-top: 0.3rem;
      line-height: 1.6;
      color: var(--text-primary, #e8dcc8);
    `;
    statusEl.parentNode.insertBefore(container, statusEl.nextSibling);
  }

  const lines = Object.values(_playerReadyMap).map(({ displayName, ready }) =>
    `${ready ? '🔊' : '🔇'} ${displayName}${ready ? '' : ' (click pending)'}`
  );
  container.textContent = lines.join('  ');
}


// ---------------------------------------------------------------------------
// WebSocket send helper (uses existing WS if available)
// ---------------------------------------------------------------------------

function _wsSend(msg) {
  // Try the global WebSocket reference used by the existing app
  const ws = window._ws || window.ws;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  } else {
    console.warn(`${TTS_LOG} WebSocket not ready — message dropped:`, msg.type);
  }
}


// ---------------------------------------------------------------------------
// Hook into existing WS message handler (non-destructive injection)
// ---------------------------------------------------------------------------

function _hookWebSocketMessages() {
  // Safe mode (?safe=1) disables TTS polling so a frozen player page can boot
  // without the relay probe loop.
  if (window.AppSafeMode && window.AppSafeMode.disabled('tts-polling')) {
    console.info(`${TTS_LOG} polling disabled (safe mode)`);
    return;
  }
  // The existing app uses a global _ws or registers via a callback.
  // We install a proxy after a short delay to let the app initialise first.
  const INTERVAL_MS = 500;
  const MAX_TRIES   = 30;
  let   tries       = 0;

  const probe = setInterval(() => {
    const ws = window._ws || window.ws;
    tries++;

    if (!ws) {
      if (tries >= MAX_TRIES) {
        clearInterval(probe);
        console.warn(`${TTS_LOG} WS not found after ${MAX_TRIES} attempts — TTS relay disabled`);
      }
      return;
    }

    clearInterval(probe);

    // Wrap the existing onmessage handler
    const original = ws.onmessage;
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'tts_narration') {
          _handleTTSNarration(msg.payload || {});
        } else if (msg.type === 'tts_narration_stop') {
          _handleTTSNarrationStop();
        } else if (msg.type === 'player_audio_ready') {
          _handlePlayerAudioReady(msg.payload || {});
        }
      } catch {}
      // Always call the original handler
      if (original) original.call(ws, event);
    };

    console.info(`${TTS_LOG} WS message handler hooked`);
  }, INTERVAL_MS);
}


// ---------------------------------------------------------------------------
// Wire existing DM sound buttons to new engines
// ---------------------------------------------------------------------------

function _wireSoundButtons() {
  // Keep the existing onclick contract, but route through the single authoritative
  // sound engine so ambience does not double-play from legacy/procedural stacks.
  window.dmSoundSetTrack = function (track) {
    const scene = String(track || 'silence').toLowerCase();
    if (window.audioManager) {
      if (scene === 'silence') window.audioManager.stopAmbient();
      else window.audioManager.playAmbient(scene, 1800);
    } else if (window._soundEngine) {
      window._soundEngine.setAmbient(scene, window._soundEngine._vol?.ambient ?? 0.7, 1800);
    }
    const lbl = document.getElementById('sound-track-label');
    if (lbl) lbl.textContent = scene.charAt(0).toUpperCase() + scene.slice(1);
  };

  window.dmSoundPlaySfx = function (sfx_id) {
    if (window.audioManager?.playSFX) window.audioManager.playSFX(sfx_id);
    else if (window._soundEngine) window._soundEngine.playSfx(sfx_id, 1.0);
  };

  window.dmSoundStopAll = function () {
    if (window.audioManager?.stopAll) window.audioManager.stopAll();
    else if (window._soundEngine) window._soundEngine.stopAll();
  };

  window.dmSoundAutoDetect = function () {
    const track = window._soundEngine?.autoDetectFromMap?.() || 'silence';
    window.dmSoundSetTrack(track);
  };
}


// ---------------------------------------------------------------------------
// window.tavernTTS — global API surface
// ---------------------------------------------------------------------------

window.tavernTTS = {
  /**
   * Speak text with a voice preset. Returns Promise<void>.
   * emotion: "neutral" | "dramatic" | "menacing" | "warm"
   */
  speak: async function (text, voicePresetId = 'grand_narrator', emotion = 'neutral') {
    try {
      const { arrayBuf, engine, latencyMs } = await _fetchTTS(text, voicePresetId, 1.0, emotion);
      _startRunePulse();
      await _playWavBytes(arrayBuf, _stopRunePulse);
    } catch (err) {
      console.error(`${TTS_LOG} tavernTTS.speak error:`, err);
    }
  },

  /** Speak a multi-line NPC conversation. lines: [{speaker, text, voice_preset}] */
  speakNPC: async function (lines) {
    try {
      const resp = await fetch(`${TTS_API}/speak-npc-conversation`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ lines }),
      });
      if (!resp.ok) throw new Error(`NPC API ${resp.status}`);
      const buf = await resp.arrayBuffer();
      _startRunePulse();
      await _playWavBytes(buf, _stopRunePulse);
    } catch (err) {
      console.error(`${TTS_LOG} tavernTTS.speakNPC error:`, err);
    }
  },

  /** Stop all TTS playback immediately. */
  stop: function () {
    window.dmNarrationStop();
  },

  /** Pre-warm the server cache with an array of phrases. */
  preload: async function (phraseArray) {
    const preset = 'grand_narrator';
    for (const phrase of phraseArray) {
      fetch(`${TTS_API}/speak`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ text: phrase, voice_preset: preset }),
      }).catch(() => {});
    }
  },
};


// ---------------------------------------------------------------------------
// Initialise on DOMContentLoaded
// ---------------------------------------------------------------------------

async function _init() {
  // Show audio unlock overlay for all users
  _showAudioUnlockOverlay();

  // Initialise ambient and SFX engines
  if (window.AmbientEngine && !window.tavernAmbient) {
    window.tavernAmbient = new AmbientEngine();
  }
  if (window.SFXEngine && !window.tavernSFX) {
    // Share AudioContext with existing SoundEngine if available
    window.tavernSFX = new SFXEngine(window._soundEngine || null);
  }

  // Wire existing DM buttons to new engines
  _wireSoundButtons();

  // Hook WebSocket for TTS message relay
  _hookWebSocketMessages();

  // DM-only panel setup (voice dropdown + phrase chips). The narration
  // controls exist in the shared play.html DOM, so element presence is not a
  // reliable role check. Gate network-heavy TTS metadata calls on ROLE/query
  // role so player/viewer boot never fetches /api/tts/voices or
  // /api/tts/warmup-phrases.
  let role = 'viewer';
  try {
    role = String(window.ROLE || new URLSearchParams(window.location.search || '').get('role') || 'viewer').toLowerCase();
  } catch (_err) {
    role = String(window.ROLE || 'viewer').toLowerCase();
  }
  const isDM = role === 'dm';
  if (isDM) {
    await _populateVoiceDropdown();
    await _renderWarmupPhrases();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _init);
} else {
  _init();
}
