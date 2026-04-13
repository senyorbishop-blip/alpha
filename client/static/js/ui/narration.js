/**
 * narration.js — authoritative storyteller narration manager.
 *
 * Root-cause summary:
 * - play.html still contained an older inline narration implementation, so there were
 *   competing code paths and inconsistent fallback behaviour.
 * - Browser speech fallback was not clearly marked and could reuse near-identical voices.
 * - ElevenLabs success/failure/cache state was not surfaced in the client.
 */

class NarrationManager {
  constructor(soundEngine) {
    this._se = soundEngine;
    this._state = 'idle';
    this._queue = [];
    this._revealTimer = null;
    this._fullText = '';
    this._wordTokens = [];
    this._wordIdx = 0;
    this._busGain = null;
    this._reverbConv = null;
    this._reverbSend = null;
    this._dryGain = null;
    this._srcNode = null;
    this._utter = null;
    this._autoCloseTimer = null;
    this._currentVoicePreset = 'deep_narrator';
    this._previewCache = new Map();
  }

  speak(opts = {}) {
    const policy = opts.policy || 'replace_current';
    if (this._state !== 'idle') {
      if (policy === 'ignore_if_busy') return;
      if (policy === 'queue_next') {
        this._queue.push(opts);
        console.info('[NarrationManager] queued narration item');
        return;
      }
      this._fadeOutAndStop(() => this._begin(opts));
      return;
    }
    this._begin(opts);
  }

  showHook(opts = {}) {
    const title = String(opts.title || 'Narration Hook').trim();
    const prompt = String(opts.prompt || opts.text || '').trim();
    if (!title && !prompt) return;
    if (typeof window.showToast === 'function') {
      window.showToast(`🪶 ${title}${prompt ? `: ${prompt.slice(0, 140)}` : ''}`);
    }
  }

  stop() {
    this._clearReveal();
    this._stopAudio(220);
    this._closeOverlay();
    this._state = 'idle';
    this._queue = [];
    this._clearAutoClose();
  }

  _openOverlay(text, browserFallback) {
    const overlay = document.getElementById('narration-scroll-overlay');
    const badge = document.getElementById('narration-browser-badge');
    const textEl = document.getElementById('narration-scroll-text');
    if (!overlay || !textEl) return;
    textEl.textContent = '';
    if (badge) badge.classList.toggle('visible', !!browserFallback);
    overlay.classList.add('narration-open');
  }

  _closeOverlay() {
    const overlay = document.getElementById('narration-scroll-overlay');
    const textEl = document.getElementById('narration-scroll-text');
    if (overlay) overlay.classList.remove('narration-open');
    if (textEl) textEl.classList.remove('narration-revealing');
    this._clearAutoClose();
  }

  _clearAutoClose() {
    if (this._autoCloseTimer !== null) {
      clearTimeout(this._autoCloseTimer);
      this._autoCloseTimer = null;
    }
  }

  _scheduleAutoClose(delayMs = 900) {
    this._clearAutoClose();
    this._autoCloseTimer = setTimeout(() => {
      if (this._state === 'idle') this._closeOverlay();
    }, Math.max(150, delayMs));
  }

  _startReveal(text, durationMs = 0) {
    this._clearReveal();
    this._fullText = text;
    const textEl = document.getElementById('narration-scroll-text');
    if (!textEl) return;
    textEl.classList.add('narration-revealing');
    const tokens = text.match(/\S+\s*/g) || [];
    this._wordTokens = tokens;
    this._wordIdx = 0;
    if (!tokens.length) return;
    const totalMs = durationMs > 200 ? durationMs * 0.92 : 0;
    const msPerWord = totalMs > 0 ? totalMs / tokens.length : (60000 / 128);
    const tick = () => {
      if (this._wordIdx >= tokens.length) {
        textEl.classList.remove('narration-revealing');
        textEl.textContent = tokens.join('');
        return;
      }
      // Build revealed text using DOM nodes to avoid innerHTML injection risks.
      // Previous words are a plain text node; the current word gets a span so we
      // can call scrollIntoView() to keep the reading position visible.
      const prevText = tokens.slice(0, this._wordIdx).join('');
      const currentToken = tokens[this._wordIdx];
      textEl.textContent = '';
      if (prevText) {
        textEl.appendChild(document.createTextNode(prevText));
      }
      const wordSpan = document.createElement('span');
      wordSpan.id = 'narration-current-word';
      wordSpan.textContent = currentToken;
      textEl.appendChild(wordSpan);

      // Scroll so the current word stays visible — teleprompter-style smooth scroll.
      const scrollBody = textEl.closest('.narration-scroll-body') || textEl.parentElement;
      if (scrollBody) {
        const spanRect = wordSpan.getBoundingClientRect();
        const bodyRect = scrollBody.getBoundingClientRect();
        // Scroll when the word is near (within 80 px of) or below the visible bottom.
        if (spanRect.bottom > bodyRect.bottom - 80) {
          wordSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }

      this._wordIdx += 1;
      this._revealTimer = setTimeout(tick, msPerWord);
    };
    this._revealTimer = setTimeout(tick, 70);
  }

  _clearReveal() {
    if (this._revealTimer !== null) {
      clearTimeout(this._revealTimer);
      this._revealTimer = null;
    }
    const textEl = document.getElementById('narration-scroll-text');
    if (textEl) {
      if (this._fullText) {
        textEl.textContent = this._fullText;
      }
      textEl.classList.remove('narration-revealing');
    }
  }

  _ensureBus() {
    this._se._init();
    const ctx = this._se._ctx;
    if (this._busGain && this._busGain.context === ctx) return ctx;
    this._busGain = ctx.createGain();
    this._busGain.gain.value = 0;
    this._busGain.connect(this._se._masterGain);
    // Shorter reverb (0.6 s) and low send gain to avoid audible echo on TTS speech
    const revLen = Math.ceil(ctx.sampleRate * 0.6);
    const revBuf = ctx.createBuffer(2, revLen, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = revBuf.getChannelData(c);
      for (let i = 0; i < revLen; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / revLen, 2.5);
    }
    this._reverbConv = ctx.createConvolver();
    this._reverbConv.buffer = revBuf;
    this._reverbSend = ctx.createGain();
    this._reverbSend.gain.value = 0.05;
    this._reverbSend.connect(this._reverbConv);
    this._reverbConv.connect(this._busGain);
    this._dryGain = ctx.createGain();
    this._dryGain.gain.value = 1.0;
    this._dryGain.connect(this._busGain);
    return ctx;
  }

  _playAudioData(dataUri, onDecodedDuration) {
    try {
      const ctx = this._ensureBus();
      const commaIdx = dataUri.indexOf(',');
      const header = commaIdx > 0 ? dataUri.slice(0, commaIdx) : '';
      const mimeMatch = header.match(/^data:([^;,]+)/);
      const mime = mimeMatch ? mimeMatch[1] : 'unknown';
      const b64 = commaIdx > 0 ? dataUri.slice(commaIdx + 1) : dataUri;
      const bin = atob(b64);
      const ab = new ArrayBuffer(bin.length);
      const u8 = new Uint8Array(ab);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      console.info(`[NarrationManager] _playAudioData mime=${mime} bytes=${ab.byteLength}`);
      ctx.decodeAudioData(ab, (decoded) => {
        console.info(`[NarrationManager] decodeAudioData success duration=${decoded.duration.toFixed(2)}s`);
        if (onDecodedDuration) onDecodedDuration(decoded.duration * 1000);
        this._srcNode = ctx.createBufferSource();
        this._srcNode.buffer = decoded;
        this._srcNode.connect(this._dryGain);
        this._srcNode.connect(this._reverbSend);
        const now = ctx.currentTime;
        this._busGain.gain.cancelScheduledValues(now);
        this._busGain.gain.setValueAtTime(0, now);
        this._busGain.gain.linearRampToValueAtTime(0.93, now + 0.2);
        this._duckAmbience(0.82);
        this._srcNode.onended = () => this._onAudioEnded();
        this._srcNode.start();
      }, (err) => {
        console.warn('[NarrationManager] decodeAudioData failed', err);
        this._onAudioEnded();
      });
    } catch (err) {
      console.warn('[NarrationManager] _playAudioData error', err);
      this._onAudioEnded();
    }
  }

  _stopAudio(fadeMs = 250) {
    if (this._utter && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      this._utter = null;
    }
    if (!this._busGain) return;
    try {
      const ctx = this._se._ctx;
      const now = ctx.currentTime;
      this._busGain.gain.cancelScheduledValues(now);
      this._busGain.gain.setValueAtTime(this._busGain.gain.value, now);
      this._busGain.gain.linearRampToValueAtTime(0, now + fadeMs / 1000);
      setTimeout(() => {
        try { this._srcNode?.stop(); } catch {}
        try { this._srcNode?.disconnect(); } catch {}
        this._srcNode = null;
        this._unduckAmbience();
      }, fadeMs + 30);
    } catch {}
  }

  _duckAmbience(targetGain) {
    if (!this._se._ambientGain) return;
    const now = this._se._ctx.currentTime;
    this._se._ambientGain.gain.cancelScheduledValues(now);
    this._se._ambientGain.gain.setValueAtTime(this._se._ambientGain.gain.value, now);
    this._se._ambientGain.gain.linearRampToValueAtTime(this._se._vol.ambient * this._se._personalAmbient * targetGain, now + 0.25);
  }

  _unduckAmbience() {
    if (!this._se._ambientGain) return;
    const now = this._se._ctx.currentTime;
    this._se._ambientGain.gain.cancelScheduledValues(now);
    this._se._ambientGain.gain.setValueAtTime(this._se._ambientGain.gain.value, now);
    this._se._ambientGain.gain.linearRampToValueAtTime(this._se._vol.ambient * this._se._personalAmbient, now + 0.35);
  }

  _scoreSpeechVoice(voice, hints = [], preset = '') {
    const haystack = `${voice?.name || ''} ${voice?.lang || ''}`.toLowerCase();
    let score = 0;
    hints.forEach((hint, idx) => {
      if (haystack.includes(hint)) score += (hints.length - idx) * 5;
    });
    if (/neural|natural|premium|enhanced|studio|wavenet|journey/.test(haystack)) score += 18;
    if (/whisper|pipe|novelty|robot|synth/.test(haystack)) score -= 16;
    if (voice?.localService) score += 3;
    if ((preset === 'deep_narrator' || preset === 'grim_villain') && /male|daniel|david|george/.test(haystack)) score += 5;
    if ((preset === 'mysterious_whisper' || preset === 'heroic_bard') && /female|zira|aria|serena|samantha/.test(haystack)) score += 5;
    return score;
  }

  _playBrowserSpeech(text, fallbackVoice = null) {
    if (!window.speechSynthesis) {
      this._scheduleAutoClose(Math.max(1600, text.length * 40));
      this._onAudioEnded();
      return;
    }
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    const cfg = fallbackVoice || {};
    utter.rate = Number(cfg.rate ?? 0.88);
    utter.pitch = Number(cfg.pitch ?? 0.92);
    utter.volume = 1.0;
    const hints = Array.isArray(cfg.voice_hints) ? cfg.voice_hints : [];
    const voices = window.speechSynthesis.getVoices?.() || [];
    if (voices.length && hints.length) {
      const ranked = voices.map((voice) => ({ voice, score: this._scoreSpeechVoice(voice, hints, this._currentVoicePreset) }))
        .sort((a, b) => b.score - a.score);
      if (ranked[0]?.score > 0) {
        utter.voice = ranked[0].voice;
        console.warn(`[NarrationManager] browser fallback using voice="${ranked[0].voice.name}" preset=${this._currentVoicePreset}`);
      } else {
        console.warn(`[NarrationManager] browser fallback could not find a strong system voice for preset=${this._currentVoicePreset}`);
      }
    }
    utter.onend = () => this._onAudioEnded();
    utter.onerror = () => this._onAudioEnded();
    this._utter = utter;
    this._duckAmbience(0.88);
    window.speechSynthesis.speak(utter);
  }

  _begin(opts) {
    this._state = 'playing';
    const text = (opts.text || '').slice(0, 2000);
    const audioDataUri = opts.audioDataUri || null;
    const audioDurationMs = Number(opts.audioDurationMs || 0);
    const browserFallback = opts.ttsProvider === 'browser_fallback' || !audioDataUri;
    const ttsProvider = opts.ttsProvider || (audioDataUri ? 'elevenlabs' : 'browser_fallback');
    this._currentVoicePreset = String(opts.voicePreset || 'deep_narrator');

    console.info(`[NarrationManager] begin preset=${this._currentVoicePreset} provider=${ttsProvider} cacheHit=${!!opts.ttsCacheHit} fallbackReason=${opts.fallbackReason || 'none'}`);
    console.info(`[NarrationManager] playback choice: ${audioDataUri ? 'real audio (' + ttsProvider + ')' : 'browser speech fallback'}`);
    this._openOverlay(text, browserFallback);

    if (audioDataUri) {
      this._startReveal(text, audioDurationMs);
      this._playAudioData(audioDataUri, (actualMs) => this._startReveal(text, actualMs));
      return;
    }

    const words = text.split(/\s+/).filter(Boolean).length;
    const estimatedMs = Math.max(1200, (words / 130) * 60000);
    this._startReveal(text, estimatedMs);
    this._playBrowserSpeech(text, opts.fallbackVoice || null);
  }

  _fadeOutAndStop(cb) {
    this._state = 'fading';
    this._clearReveal();
    this._stopAudio(250);
    this._closeOverlay();
    setTimeout(() => {
      this._state = 'idle';
      cb();
    }, 280);
  }

  _onAudioEnded() {
    this._unduckAmbience();
    if (this._queue.length) {
      const next = this._queue.shift();
      this._state = 'idle';
      this._begin(next);
      return;
    }
    this._state = 'idle';
    this._scheduleAutoClose();
  }
}

window.NarrationManager = NarrationManager;
