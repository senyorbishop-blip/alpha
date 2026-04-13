/**
 * sound_engine.js — authoritative ambient audio engine.
 *
 * Root-cause summary:
 * - The repo had no real ambient assets in client/static/assets/audio/, only a README.
 * - play.html still shipped an older inline sound engine stub alongside this file.
 * - The old flow silently dropped into procedural synthesis, which made ambience sound
 *   synthetic and hid missing-asset problems.
 *
 * This rebuild makes asset-backed playback the primary path, adds explicit manifest-based
 * resolution + cache-busting, logs every track decision, and keeps procedural audio as a
 * clearly logged emergency fallback only.
 */

const AUDIO_MANIFEST_URL = '/static/assets/audio/manifest.json?v=20260328';
const AUDIO_LOG_PREFIX = '[SoundEngine]';

function soundLog(level, message, extra) {
  const method = console[level] || console.log;
  if (extra !== undefined) method(`${AUDIO_LOG_PREFIX} ${message}`, extra);
  else method(`${AUDIO_LOG_PREFIX} ${message}`);
}

class SoundEngine {
  constructor() {
    this._ctx = null;
    this._masterGain = null;
    this._ambientGain = null;
    this._sfxGain = null;
    this._currentTrack = 'silence';
    this._currentSource = null;
    this._currentFallbackNodes = [];
    this._bufferCache = new Map();
    this._manifestPromise = null;
    this._manifest = null;
    this._requestToken = 0;
    this._trackTimers = [];
    this._oneShotNodes = [];
    this._ducking = 1.0;
    this._vol = { master: 0.8, ambient: 0.7, sfx: 1.0 };
    this._personalAmbient = 1.0;
    this._currentPlaybackMode = 'silence';
    this._lastResolvedPath = '';
  }

  _init() {
    if (this._ctx) {
      if (this._ctx.state === 'suspended') this._ctx.resume().catch(() => {});
      return;
    }
    this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    this._masterGain = this._ctx.createGain();
    this._masterGain.gain.value = this._vol.master;
    this._ambientGain = this._ctx.createGain();
    this._ambientGain.gain.value = this._vol.ambient * this._personalAmbient;
    this._sfxGain = this._ctx.createGain();
    this._sfxGain.gain.value = this._vol.sfx;
    this._ambientGain.connect(this._masterGain);
    this._sfxGain.connect(this._masterGain);
    this._masterGain.connect(this._ctx.destination);
  }

  async _loadManifest() {
    if (this._manifest) return this._manifest;
    if (!this._manifestPromise) {
      this._manifestPromise = fetch(AUDIO_MANIFEST_URL, { cache: 'no-store' })
        .then(async (resp) => {
          if (!resp.ok) throw new Error(`manifest http ${resp.status}`);
          const data = await resp.json();
          this._manifest = data;
          soundLog('info', `loaded audio manifest ${data.version || 'unknown'}`);
          return data;
        })
        .catch((err) => {
          soundLog('warn', `manifest load failed; fallback-only mode active (${err.message})`);
          this._manifest = { version: 'fallback-only', tracks: {} };
          return this._manifest;
        });
    }
    return this._manifestPromise;
  }

  async _resolveTrackAsset(track) {
    const manifest = await this._loadManifest();
    const entry = manifest?.tracks?.[track];
    if (!entry?.files?.length) {
      soundLog('warn', `track=${track} has no manifest-backed asset entry; using fallback`);
      return null;
    }
    for (const rawPath of entry.files) {
      const versionedPath = rawPath.includes('?') ? rawPath : `${rawPath}?v=${manifest.version || '0'}`;
      try {
        const resp = await fetch(versionedPath, { cache: 'reload' });
        if (!resp.ok) {
          soundLog('warn', `track=${track} asset probe failed path=${versionedPath} http=${resp.status}`);
          continue;
        }
        const arr = await resp.arrayBuffer();
        if (!this._bufferCache.has(versionedPath)) {
          const buf = await this._ctx.decodeAudioData(arr.slice(0));
          this._bufferCache.set(versionedPath, buf);
          soundLog('info', `track=${track} decoded asset path=${versionedPath} duration=${buf.duration.toFixed(2)}s`);
        }
        return { path: versionedPath, buffer: this._bufferCache.get(versionedPath) };
      } catch (err) {
        soundLog('error', `track=${track} decode/playback prep failed path=${versionedPath}`, err);
      }
    }
    return null;
  }

  _clearTrackTimers() {
    this._trackTimers.forEach((id) => clearTimeout(id));
    this._trackTimers = [];
  }

  _stopCurrentSource() {
    if (this._currentSource) {
      try { this._currentSource.stop(); } catch {}
      try { this._currentSource.disconnect(); } catch {}
      this._currentSource = null;
    }
    this._currentFallbackNodes.forEach((node) => {
      try { node.stop?.(); } catch {}
      try { node.disconnect?.(); } catch {}
    });
    this._currentFallbackNodes = [];
    this._oneShotNodes = this._oneShotNodes.filter((node) => {
      try { return node.playbackState !== node.FINISHED_STATE; } catch { return true; }
    });
    this._clearTrackTimers();
  }

  _startBufferLoop(buffer, path, track) {
    const src = this._ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    src.connect(this._ambientGain);
    src.start();
    this._currentSource = src;
    this._currentPlaybackMode = 'asset';
    this._lastResolvedPath = path;
    soundLog('info', `ambient started track=${track} path=${path} fallback=false`);
  }

  _makeNoiseBuffer(seconds = 8) {
    const sr = this._ctx.sampleRate;
    const len = Math.ceil(sr * seconds);
    const buf = this._ctx.createBuffer(1, len, sr);
    const d = buf.getChannelData(0);
    let prev = 0;
    for (let i = 0; i < len; i++) {
      const white = Math.random() * 2 - 1;
      prev = prev * 0.985 + white * 0.12;
      d[i] = prev;
    }
    return buf;
  }

  _noiseSource(seconds = 0.5, type = 'white') {
    const ctx = this._ctx;
    const sr  = ctx.sampleRate;
    const len = Math.ceil(sr * seconds);
    const buf = ctx.createBuffer(1, len, sr);
    const d   = buf.getChannelData(0);
    if (type === 'white') {
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    } else if (type === 'brown') {
      let last = 0;
      for (let i = 0; i < len; i++) {
        const w = Math.random() * 2 - 1;
        last    = (last + 0.02 * w) / 1.02;
        d[i]    = last * 3.5;
      }
    } else if (type === 'pink') {
      let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;
      for (let i = 0; i < len; i++) {
        const w = Math.random() * 2 - 1;
        b0=0.99886*b0+w*0.0555179; b1=0.99332*b1+w*0.0750759;
        b2=0.96900*b2+w*0.1538520; b3=0.86650*b3+w*0.3104856;
        b4=0.55000*b4+w*0.5329522; b5=-0.7616*b5-w*0.0168980;
        d[i] = (b0+b1+b2+b3+b4+b5+b6+w*0.5362)*0.11;
        b6 = w * 0.115926;
      }
    }
    const src = ctx.createBufferSource();
    src.buffer = buf;
    return src;
  }

  _makeConvolver(rt60Secs = 0.5) {
    const ctx = this._ctx;
    const sr  = ctx.sampleRate;
    const len = Math.ceil(sr * rt60Secs);
    const buf = ctx.createBuffer(2, len, sr);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.5);
      }
    }
    const conv = ctx.createConvolver();
    conv.buffer = buf;
    return conv;
  }

  _startProceduralFallback(track) {
    const ctx  = this._ctx;
    const dest = this._ambientGain;
    const fn   = this._currentFallbackNodes;
    const tt   = this._trackTimers;

    const addN  = (n) => { fn.push(n); return n; };
    const mkBQ  = (type, freq, Q = 1) => {
      const f = ctx.createBiquadFilter();
      f.type = type; f.frequency.value = freq; f.Q.value = Q;
      return addN(f);
    };
    const mkG = (val) => { const g = ctx.createGain(); g.gain.value = val; return addN(g); };
    const mkO = (type, freq) => {
      const o = ctx.createOscillator(); o.type = type; o.frequency.value = freq; return addN(o);
    };
    const mkLFO = (freq, depth) => {
      const lfo = mkO('sine', freq);
      const lg  = mkG(depth);
      lfo.connect(lg); lfo.start();
      return lg;
    };
    const mkNoise = (type, sec = 12) => {
      const src = this._noiseSource(sec, type);
      src.loop = true;
      return addN(src);
    };
    const ch = (...nodes) => { for (let i = 0; i < nodes.length - 1; i++) nodes[i].connect(nodes[i+1]); };

    if (track === 'tavern') {
      // Crowd voices: multiple oscillators at voice frequencies (200-500 Hz), each with
      // independent AM at speaking cadence rates (1.3-3 Hz). Sounds like conversation,
      // NOT like wind, ocean, or static.
      const voiceFreqs = [200, 280, 340, 420, 500, 370];
      const voiceRates = [1.3, 2.1, 1.6, 2.7, 3.0, 2.4];
      const voiceGains = [0.038, 0.036, 0.034, 0.030, 0.024, 0.022];
      voiceFreqs.forEach((freq, i) => {
        const osc  = mkO('sine', freq);
        const envG = mkG(voiceGains[i]);
        const lfo  = mkLFO(voiceRates[i], voiceGains[i] * 0.9);
        lfo.connect(envG.gain);
        osc.connect(envG); envG.connect(dest); osc.start();
      });

      // Fireplace: 55 Hz warmth + octave harmonic
      const fire = mkO('sine', 55); const fire2 = mkO('sine', 110);
      const fireG = mkG(0.04);
      fire.connect(fireG); fire2.connect(fireG); fireG.connect(dest);
      fire.start(); fire2.start();

      // Wood creaks
      const _creak = () => {
        const id = setTimeout(() => {
          if (this._currentTrack !== 'tavern') return;
          this._playFallbackClick(ctx, dest, 220 + Math.random()*110, 0.06 + Math.random()*0.05, 0.12);
          _creak();
        }, 4000 + Math.random() * 12000);
        tt.push(id);
      };
      _creak();

    } else if (track === 'dungeon') {
      // Stone rumble: brown noise → steep lowpass (keeps only deep sub rumble, cuts hiss)
      const stone  = mkNoise('brown', 10);
      const lp     = mkBQ('lowpass', 90, 0.7);
      const stoneG = mkG(0.20);
      ch(stone, lp, stoneG, dest); stone.start();

      // Reverb for drips
      const rev  = addN(this._makeConvolver(2.5));
      const revG = mkG(0.22);
      rev.connect(revG); revG.connect(dest);

      // Wind moan: sine → modulated bandpass
      const wind   = mkO('sine', 120);
      const windBP = mkBQ('bandpass', 120, 8);
      const windG  = mkG(0.09);
      ch(wind, windBP, windG, dest); wind.start();
      mkLFO(0.1, 40).connect(windBP.frequency);

      // Drip scheduler (Poisson, mean 4s)
      const _drip = () => {
        const delay = -Math.log(1 - Math.random()) * 4000;
        const id = setTimeout(() => {
          if (this._currentTrack !== 'dungeon') return;
          this._playFallbackDrip(ctx, dest, rev, 440 + Math.random() * 440);
          _drip();
        }, delay);
        tt.push(id);
      };
      _drip(); _drip();

    } else if (track === 'forest') {
      // Wind: brown noise (softer than white) → tight bandpass → lowpass to cut hiss
      const wind   = mkNoise('brown', 10);
      const windBP = mkBQ('bandpass', 700, 3.0);
      const windLP = mkBQ('lowpass', 1400);
      const windG  = mkG(0.22);
      ch(wind, windBP, windLP, windG, dest); wind.start();
      mkLFO(0.3, 250).connect(windBP.frequency);

      // Pink noise bed — very quiet, just presence
      const bed = mkNoise('pink', 12); const bedG = mkG(0.02);
      ch(bed, bedG, dest); bed.start();

      // Bird call scheduler
      const _bird = () => {
        const id = setTimeout(() => {
          if (this._currentTrack !== 'forest') return;
          this._playFallbackBirdCall(ctx, dest);
          _bird();
        }, 4000 + Math.random() * 16000);
        tt.push(id);
      };
      _bird();

      // Cricket layer after 30s
      tt.push(setTimeout(() => {
        if (this._currentTrack !== 'forest') return;
        const cn  = mkNoise('white', 8);
        const chp = mkBQ('highpass', 6000, 1.0);
        const clp = mkBQ('lowpass', 8000, 1.0);
        const cg  = mkG(0.12);
        ch(cn, chp, clp, cg, dest); cn.start();
        mkLFO(3.0, 0.5).connect(cg.gain);
      }, 30000));

    } else if (track === 'battle') {
      // Battle strings: D minor chord (D3-F3-A3-D4) with fast tremolo (7 Hz).
      // Tremolo strings = battle/combat music character. Sawtooths = industrial machine.
      const strG = mkG(0.07);
      [146.83, 174.61, 220.00, 293.66].forEach(freq => {
        const s = mkO('sine', freq); s.connect(strG); s.start();
      });
      strG.connect(dest);
      mkLFO(7.0, 0.055).connect(strG.gain);
      // Horn accent: A3 modulated at half-beat rate
      const horn = mkO('sine', 220); const hornG = mkG(0.06);
      ch(horn, hornG, dest); horn.start();
      mkLFO(0.5, 0.04).connect(hornG.gain);

      // Kick at 120 BPM via setTimeout chain
      const _kick = () => {
        if (this._currentTrack !== 'battle') return;
        this._playFallbackKick(ctx, dest);
        tt.push(setTimeout(_kick, 500));
      };
      this._playFallbackKick(ctx, dest);
      tt.push(setTimeout(_kick, 500));

      // Metallic shimmers
      const _shimmer = () => {
        const id = setTimeout(() => {
          if (this._currentTrack !== 'battle') return;
          this._playFallbackShimmer(ctx, dest);
          _shimmer();
        }, 800 + Math.random() * 2200);
        tt.push(id);
      };
      _shimmer();
    }

    this._currentPlaybackMode = 'procedural_fallback';
    this._lastResolvedPath    = 'procedural';
    soundLog('warn', `ambient started track=${track} path=procedural fallback=true`);
  }

  // ── Procedural ambient event helpers ──────────────────────────────────────

  _playFallbackClick(ctx, dest, freq, gain, dur) {
    const now = ctx.currentTime;
    const osc = ctx.createOscillator(); const env = ctx.createGain();
    osc.type = 'triangle'; osc.frequency.value = freq;
    env.gain.setValueAtTime(gain, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + dur);
    osc.connect(env); env.connect(dest);
    osc.start(now); osc.stop(now + dur + 0.01);
  }

  _playFallbackDrip(ctx, dest, reverbNode, freq) {
    const now = ctx.currentTime;
    const osc = ctx.createOscillator(); const env = ctx.createGain();
    osc.type = 'triangle'; osc.frequency.value = freq;
    env.gain.setValueAtTime(0, now);
    env.gain.linearRampToValueAtTime(0.18, now + 0.001);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.8);
    osc.connect(env);
    if (reverbNode) env.connect(reverbNode);
    env.connect(dest);
    osc.start(now); osc.stop(now + 0.85);
  }

  _playFallbackBirdCall(ctx, dest) {
    const now  = ctx.currentTime;
    const base = 1200 + Math.random() * 800;
    const dur  = 0.08 + Math.random() * 0.12;
    const n    = 2 + Math.floor(Math.random() * 3);
    for (let i = 0; i < n; i++) {
      const t    = now + i * (dur + 0.04);
      const freq = base * (1 + (Math.random() - 0.5) * 0.3);
      const osc  = ctx.createOscillator(); const env = ctx.createGain();
      osc.type = 'sine'; osc.frequency.value = freq;
      env.gain.setValueAtTime(0, t);
      env.gain.linearRampToValueAtTime(0.09, t + 0.01);
      env.gain.exponentialRampToValueAtTime(0.001, t + dur);
      osc.connect(env); env.connect(dest);
      osc.start(t); osc.stop(t + dur + 0.01);
    }
  }

  _playFallbackKick(ctx, dest) {
    const now = ctx.currentTime;
    const osc = ctx.createOscillator(); const env = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(60, now);
    osc.frequency.exponentialRampToValueAtTime(30, now + 0.2);
    env.gain.setValueAtTime(0.55, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
    osc.connect(env); env.connect(dest);
    osc.start(now); osc.stop(now + 0.25);
  }

  _playFallbackShimmer(ctx, dest) {
    const now  = ctx.currentTime;
    const dur  = 0.05 + Math.random() * 0.15;
    const sr   = ctx.sampleRate;
    const len  = Math.ceil(sr * 0.3);
    const buf  = ctx.createBuffer(1, len, sr);
    const d    = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    const noise = ctx.createBufferSource(); noise.buffer = buf;
    const bp    = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.value = 3000 + Math.random() * 5000; bp.Q.value = 8;
    const env   = ctx.createGain();
    env.gain.setValueAtTime(0, now);
    env.gain.linearRampToValueAtTime(0.08, now + 0.005);
    env.gain.exponentialRampToValueAtTime(0.001, now + dur);
    noise.connect(bp); bp.connect(env); env.connect(dest);
    noise.start(now); noise.stop(now + dur + 0.01);
  }

  async _startTrack(track, token) {
    if (track === 'silence') return;
    const resolved = await this._resolveTrackAsset(track);
    if (token !== this._requestToken) return;
    if (resolved?.buffer) {
      this._startBufferLoop(resolved.buffer, resolved.path, track);
      return;
    }
    this._startProceduralFallback(track);
  }

  async setAmbient(track, volume = 0.7, fade_ms = 1500) {
    this._init();
    const normalizedTrack = String(track || 'silence').toLowerCase();
    const token = ++this._requestToken;
    const fadeSec = Math.max(0.05, Number(fade_ms || 1500) / 1000);
    this._vol.ambient = Math.max(0, Math.min(1, Number(volume ?? 0.7)));
    soundLog('info', `ambient requested track=${normalizedTrack} volume=${this._vol.ambient.toFixed(2)} fadeMs=${fade_ms}`);

    const now = this._ctx.currentTime;
    this._ambientGain.gain.cancelScheduledValues(now);
    this._ambientGain.gain.setValueAtTime(this._ambientGain.gain.value, now);
    this._ambientGain.gain.linearRampToValueAtTime(0, now + fadeSec * 0.55);

    setTimeout(async () => {
      if (token !== this._requestToken) return;
      this._stopCurrentSource();
      this._currentTrack = normalizedTrack;
      if (normalizedTrack === 'silence') {
        this._currentPlaybackMode = 'silence';
        this._lastResolvedPath = '';
        this._updateIndicator('silence');
        soundLog('info', 'ambient stopped track=silence');
        return;
      }
      await this._startTrack(normalizedTrack, token);
      if (token !== this._requestToken) return;
      const t = this._ctx.currentTime;
      this._ambientGain.gain.setValueAtTime(0, t);
      this._ambientGain.gain.linearRampToValueAtTime(this._vol.ambient * this._personalAmbient, t + fadeSec * 0.45);
      this._updateIndicator(normalizedTrack);
    }, fade_ms * 0.55);
  }

  stopAll() {
    if (!this._ctx) return;
    this._requestToken += 1;
    const now = this._ctx.currentTime;
    this._ambientGain.gain.cancelScheduledValues(now);
    this._ambientGain.gain.setValueAtTime(this._ambientGain.gain.value, now);
    this._ambientGain.gain.linearRampToValueAtTime(0, now + 0.4);
    setTimeout(() => {
      this._stopCurrentSource();
      this._currentTrack = 'silence';
      this._currentPlaybackMode = 'silence';
      this._lastResolvedPath = '';
      this._updateIndicator('silence');
      soundLog('info', 'stopAll completed');
    }, 450);
  }

  playSfx(sfx_id, volume = 1.0) {
    this._init();
    const ctx = this._ctx;
    const now = ctx.currentTime;
    const dest = this._sfxGain;
    const vol = Math.max(0, Math.min(1, Number(volume ?? 1))) * this._vol.sfx;
    soundLog('info', `sfx requested id=${sfx_id} volume=${vol.toFixed(2)}`);

    // Dice sounds — kept as-is
    if (typeof sfx_id === 'string' && sfx_id.startsWith('dice_roll_')) {
      const noise = ctx.createBufferSource();
      noise.buffer = this._makeNoiseBuffer(0.6);
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass'; bp.frequency.value = 2400; bp.Q.value = 1.2;
      const g = ctx.createGain();
      g.gain.setValueAtTime(vol * 0.3, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
      noise.connect(bp); bp.connect(g); g.connect(dest);
      noise.start(now); noise.stop(now + 0.55);
      return;
    }
    if (sfx_id === 'dice_high' || sfx_id === 'dice_nat20') {
      const osc = ctx.createOscillator(); const g = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(sfx_id === 'dice_nat20' ? 880 : 660, now);
      osc.frequency.linearRampToValueAtTime(sfx_id === 'dice_nat20' ? 1320 : 880, now + 0.15);
      g.gain.setValueAtTime(vol * 0.2, now); g.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.connect(g); g.connect(dest); osc.start(now); osc.stop(now + 0.3);
      return;
    }
    if (sfx_id === 'dice_low' || sfx_id === 'dice_nat1') {
      const osc = ctx.createOscillator(); const g = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(sfx_id === 'dice_nat1' ? 220 : 330, now);
      osc.frequency.linearRampToValueAtTime(sfx_id === 'dice_nat1' ? 110 : 220, now + 0.2);
      g.gain.setValueAtTime(vol * 0.2, now); g.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.connect(g); g.connect(dest); osc.start(now); osc.stop(now + 0.35);
      return;
    }

    switch (sfx_id) {

      case 'clash':
      case 'sword_clash': {
        // Metallic impact: noise burst + dual chirp ring + short reverb
        const rev = this._makeConvolver(0.4); const revG = ctx.createGain(); revG.gain.value = 0.28;
        rev.connect(revG); revG.connect(dest);
        // Noise burst — metallic texture
        const noise = this._noiseSource(0.1, 'white');
        const nbp   = ctx.createBiquadFilter(); nbp.type = 'bandpass'; nbp.frequency.value = 3500; nbp.Q.value = 2.5;
        const nenv  = ctx.createGain();
        nenv.gain.setValueAtTime(vol * 0.9, now); nenv.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
        noise.connect(nbp); nbp.connect(nenv); nenv.connect(dest); nenv.connect(rev);
        noise.start(now); noise.stop(now + 0.08);
        // First ring: 900→250Hz
        const o1 = ctx.createOscillator(); const e1 = ctx.createGain();
        o1.type = 'triangle'; o1.frequency.setValueAtTime(900, now); o1.frequency.exponentialRampToValueAtTime(250, now + 0.09);
        e1.gain.setValueAtTime(vol * 0.55, now); e1.gain.exponentialRampToValueAtTime(0.001, now + 0.09);
        o1.connect(e1); e1.connect(dest); e1.connect(rev); o1.start(now); o1.stop(now + 0.10);
        // Second ring: 1400→400Hz (slight delay)
        const o2 = ctx.createOscillator(); const e2 = ctx.createGain();
        o2.type = 'triangle'; o2.frequency.setValueAtTime(1400, now + 0.01); o2.frequency.exponentialRampToValueAtTime(400, now + 0.10);
        e2.gain.setValueAtTime(vol * 0.35, now + 0.01); e2.gain.exponentialRampToValueAtTime(0.001, now + 0.10);
        o2.connect(e2); e2.connect(dest); e2.connect(rev); o2.start(now + 0.01); o2.stop(now + 0.11);
        break;
      }

      case 'fireball': {
        // Sub thump 50Hz
        const sub = ctx.createOscillator(); const senv = ctx.createGain();
        sub.type = 'sine'; sub.frequency.value = 50;
        senv.gain.setValueAtTime(vol * 0.75, now); senv.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
        sub.connect(senv); senv.connect(dest); sub.start(now); sub.stop(now + 0.20);
        // Pink noise swell with sweeping lowpass 4000→350Hz
        const flame = this._noiseSource(0.75, 'pink');
        const nlp   = ctx.createBiquadFilter(); nlp.type = 'lowpass';
        nlp.frequency.setValueAtTime(4000, now + 0.02); nlp.frequency.exponentialRampToValueAtTime(350, now + 0.70);
        const nenv  = ctx.createGain();
        nenv.gain.setValueAtTime(0, now); nenv.gain.linearRampToValueAtTime(vol * 0.95, now + 0.02); nenv.gain.exponentialRampToValueAtTime(0.001, now + 0.70);
        flame.connect(nlp); nlp.connect(nenv); nenv.connect(dest); flame.start(now); flame.stop(now + 0.74);
        // High crackle
        const crk = this._noiseSource(0.35, 'white');
        const chp = ctx.createBiquadFilter(); chp.type = 'highpass'; chp.frequency.value = 3000;
        const cenv = ctx.createGain();
        cenv.gain.setValueAtTime(vol * 0.25, now); cenv.gain.exponentialRampToValueAtTime(0.001, now + 0.30);
        crk.connect(chp); chp.connect(cenv); cenv.connect(dest); crk.start(now); crk.stop(now + 0.36);
        break;
      }

      case 'door':
      case 'door_creak': {
        // FM creak: carrier 200→80Hz modulated by 55Hz
        const carrier = ctx.createOscillator(); const modOsc = ctx.createOscillator(); const modG = ctx.createGain();
        carrier.type = 'sine'; carrier.frequency.setValueAtTime(200, now); carrier.frequency.exponentialRampToValueAtTime(80, now + 0.35);
        modOsc.frequency.value = 55; modG.gain.value = 45;
        modOsc.connect(modG); modG.connect(carrier.frequency);
        const cenv = ctx.createGain();
        cenv.gain.setValueAtTime(vol * 0.65, now); cenv.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        carrier.connect(cenv); cenv.connect(dest); carrier.start(now); carrier.stop(now + 0.37); modOsc.start(now); modOsc.stop(now + 0.37);
        // Squeak harmonic
        const sq = ctx.createOscillator(); const sqe = ctx.createGain();
        sq.type = 'sawtooth'; sq.frequency.setValueAtTime(400, now + 0.05); sq.frequency.exponentialRampToValueAtTime(150, now + 0.30);
        sqe.gain.setValueAtTime(0, now + 0.05); sqe.gain.linearRampToValueAtTime(vol * 0.15, now + 0.08); sqe.gain.exponentialRampToValueAtTime(0.001, now + 0.30);
        sq.connect(sqe); sqe.connect(dest); sq.start(now + 0.05); sq.stop(now + 0.31);
        // Thud on close
        const thud = this._noiseSource(0.15, 'brown');
        const tlp  = ctx.createBiquadFilter(); tlp.type = 'lowpass'; tlp.frequency.value = 200;
        const tenv = ctx.createGain();
        tenv.gain.setValueAtTime(vol * 0.75, now + 0.32); tenv.gain.exponentialRampToValueAtTime(0.001, now + 0.44);
        thud.connect(tlp); tlp.connect(tenv); tenv.connect(dest); thud.start(now + 0.32); thud.stop(now + 0.45);
        break;
      }

      case 'thunder': {
        // Sharp initial crack
        const crk = this._noiseSource(0.1, 'white');
        const cbp = ctx.createBiquadFilter(); cbp.type = 'bandpass'; cbp.frequency.value = 1200; cbp.Q.value = 0.8;
        const cenv = ctx.createGain();
        cenv.gain.setValueAtTime(vol * 0.6, now); cenv.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        crk.connect(cbp); cbp.connect(cenv); cenv.connect(dest); crk.start(now); crk.stop(now + 0.10);
        // Rolling rumble: 3 layered brown noise bursts
        [
          { delay: 0.04, dur: 1.8, g: vol * 0.85, pan: -0.3 + Math.random() * 0.6 },
          { delay: 0.12, dur: 1.5, g: vol * 0.55, pan: -0.4 + Math.random() * 0.8 },
          { delay: 0.28, dur: 1.2, g: vol * 0.30, pan: -0.5 + Math.random() * 1.0 },
        ].forEach(({ delay, dur, g, pan }) => {
          const n   = this._noiseSource(dur + 0.1, 'brown');
          const lp  = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 260;
          const env = ctx.createGain();
          env.gain.setValueAtTime(g, now + delay); env.gain.exponentialRampToValueAtTime(0.001, now + delay + dur);
          const pnr = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
          if (pnr) pnr.pan.value = pan;
          n.connect(lp); lp.connect(env);
          if (pnr) { env.connect(pnr); pnr.connect(dest); } else env.connect(dest);
          n.start(now + delay); n.stop(now + delay + dur + 0.05);
        });
        break;
      }

      case 'heal':
      case 'heal_chime': {
        // Ascending arpeggio C4→E4→G4→C5 (major chord, Pokemon-like) + reverb halo
        const rev = this._makeConvolver(0.9); const revG = ctx.createGain(); revG.gain.value = 0.3;
        rev.connect(revG); revG.connect(dest);
        [261.63, 329.63, 392.00, 523.25].forEach((freq, i) => {
          const t   = now + i * 0.095;
          const o1  = ctx.createOscillator(); const o2 = ctx.createOscillator(); const env = ctx.createGain();
          o1.type = 'triangle'; o1.frequency.value = freq;
          o2.type = 'sine'; o2.frequency.value = freq * 1.005;
          env.gain.setValueAtTime(0, t); env.gain.linearRampToValueAtTime(vol * 0.50, t + 0.012); env.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
          o1.connect(env); o2.connect(env); env.connect(dest); env.connect(rev);
          o1.start(t); o1.stop(t + 0.24); o2.start(t); o2.stop(t + 0.24);
        });
        break;
      }

      case 'trap':
      case 'trap_click': {
        // Mechanical click
        const clk = this._noiseSource(0.012, 'white'); const cenv = ctx.createGain();
        cenv.gain.setValueAtTime(vol * 0.95, now); cenv.gain.exponentialRampToValueAtTime(0.001, now + 0.008);
        clk.connect(cenv); cenv.connect(dest); clk.start(now); clk.stop(now + 0.013);
        // Spring snap: sawtooth glide 320→75Hz
        const saw = ctx.createOscillator(); const senv = ctx.createGain();
        saw.type = 'sawtooth'; saw.frequency.setValueAtTime(320, now + 0.006); saw.frequency.exponentialRampToValueAtTime(75, now + 0.22);
        senv.gain.setValueAtTime(vol * 0.55, now + 0.006); senv.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
        saw.connect(senv); senv.connect(dest); saw.start(now + 0.006); saw.stop(now + 0.23);
        // Trapdoor creak
        const cr = ctx.createOscillator(); const crenv = ctx.createGain();
        cr.type = 'sine'; cr.frequency.setValueAtTime(180, now + 0.22); cr.frequency.exponentialRampToValueAtTime(90, now + 0.40);
        crenv.gain.setValueAtTime(vol * 0.30, now + 0.22); crenv.gain.exponentialRampToValueAtTime(0.001, now + 0.40);
        cr.connect(crenv); crenv.connect(dest); cr.start(now + 0.22); cr.stop(now + 0.42);
        break;
      }

      case 'gasp':
      case 'crowd_gasp': {
        // Inhale: bandpass noise 800→2500Hz, rising envelope with LFO wobble
        const noise = this._noiseSource(0.55, 'white');
        const bp    = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 2.2;
        bp.frequency.setValueAtTime(800, now + 0.01); bp.frequency.exponentialRampToValueAtTime(2500, now + 0.15); bp.frequency.exponentialRampToValueAtTime(1200, now + 0.45);
        const env   = ctx.createGain();
        env.gain.setValueAtTime(0, now); env.gain.linearRampToValueAtTime(vol * 0.65, now + 0.015);
        env.gain.setValueAtTime(vol * 0.65, now + 0.03); env.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
        // LFO breathiness wobble
        const wob = ctx.createOscillator(); const wobG = ctx.createGain();
        wob.type = 'sine'; wob.frequency.value = 6; wobG.gain.value = 280;
        wob.connect(wobG); wobG.connect(bp.frequency); wob.start(now); wob.stop(now + 0.48);
        noise.connect(bp); bp.connect(env); env.connect(dest); noise.start(now); noise.stop(now + 0.50);
        break;
      }

      case 'viewer_power_fire': {
        const rev = this._makeConvolver(0.7); const revG = ctx.createGain(); revG.gain.value = 0.3;
        rev.connect(revG); revG.connect(dest);
        [440, 659.25, 880].forEach((freq, i) => {
          const t = now + i * 0.06;
          const osc = ctx.createOscillator(); const env = ctx.createGain();
          osc.type = 'sine'; osc.frequency.setValueAtTime(freq * 0.85, t); osc.frequency.exponentialRampToValueAtTime(freq, t + 0.12);
          env.gain.setValueAtTime(0, t); env.gain.linearRampToValueAtTime(vol * 0.45, t + 0.015); env.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
          osc.connect(env); env.connect(dest); env.connect(rev); osc.start(t); osc.stop(t + 0.26);
        });
        const shim = this._noiseSource(0.18, 'white');
        const sbp  = ctx.createBiquadFilter(); sbp.type = 'bandpass'; sbp.frequency.value = 6000; sbp.Q.value = 3;
        const senv = ctx.createGain();
        senv.gain.setValueAtTime(0, now + 0.04); senv.gain.linearRampToValueAtTime(vol * 0.25, now + 0.06); senv.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
        shim.connect(sbp); sbp.connect(senv); senv.connect(dest); senv.connect(rev); shim.start(now + 0.04); shim.stop(now + 0.23);
        const sub = ctx.createOscillator(); const sube = ctx.createGain();
        sub.type = 'sine'; sub.frequency.value = 70;
        sube.gain.setValueAtTime(vol * 0.5, now); sube.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
        sub.connect(sube); sube.connect(dest); sub.start(now); sub.stop(now + 0.19);
        break;
      }

      default:
        soundLog('warn', `sfx unknown id=${sfx_id}`);
    }
  }

  setMasterVolume(v) { this._vol.master = v; if (this._masterGain) this._masterGain.gain.value = v; }
  setAmbientVolume(v) { this._vol.ambient = v; if (this._ambientGain) this._ambientGain.gain.value = v * this._personalAmbient * this._ducking; }
  setSfxVolume(v) { this._vol.sfx = v; if (this._sfxGain) this._sfxGain.gain.value = v; }
  setPersonalAmbientVolume(v) { this._personalAmbient = v; if (this._ambientGain) this._ambientGain.gain.value = this._vol.ambient * v * this._ducking; }
  setAmbientDucking(multiplier = 1) {
    this._ducking = Math.max(0.15, Math.min(1, Number(multiplier || 1)));
    if (this._ambientGain && this._ctx) {
      const now = this._ctx.currentTime;
      this._ambientGain.gain.cancelScheduledValues(now);
      this._ambientGain.gain.setValueAtTime(this._ambientGain.gain.value, now);
      this._ambientGain.gain.linearRampToValueAtTime(this._vol.ambient * this._personalAmbient * this._ducking, now + 0.25);
    }
  }

  _updateIndicator(track) {
    const ind = document.getElementById('sound-indicator');
    if (!ind) return;
    const dot = ind.querySelector('.sound-ind-dot');
    const lbl = ind.querySelector('.sound-ind-label');
    if (track === 'silence') {
      ind.classList.remove('sound-ind-active');
      if (dot) dot.style.animation = 'none';
      if (lbl) lbl.textContent = '';
      ind.title = 'Ambient audio stopped';
      return;
    }
    ind.classList.add('sound-ind-active');
    if (dot) dot.style.animation = 'soundPulse 1.4s ease-in-out infinite';
    const suffix = this._currentPlaybackMode === 'procedural_fallback' ? ' (fallback)' : '';
    if (lbl) lbl.textContent = `${track}${suffix}`;
    ind.title = this._currentPlaybackMode === 'procedural_fallback'
      ? `Ambient track ${track} is using procedural fallback because no audio asset loaded.`
      : `Ambient track ${track} is playing from ${this._lastResolvedPath || 'bundled assets'}.`;
  }

  get currentTrack() { return this._currentTrack; }

  autoDetectFromMap() {
    if (typeof _editorLayersAll === 'undefined' || typeof _getCurrentMapContext === 'undefined') return 'silence';
    const layers = _editorLayersAll[_getCurrentMapContext()] || {};
    const terrainValues = Object.values(layers);
    if (!terrainValues.length) return 'silence';
    const counts = {};
    terrainValues.forEach((v) => { counts[v] = (counts[v] || 0) + 1; });
    const dominant = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0];
    const map = { '1': 'dungeon', '2': 'tavern', '3': 'forest', '4': 'forest', '5': 'forest', '6': 'dungeon', '7': 'forest', '8': 'forest', '9': 'forest', '10': 'dungeon', '11': 'forest', '12': 'forest', '13': 'battle' };
    return map[String(dominant)] || 'silence';
  }
}

window.SoundEngine = SoundEngine;

/* ─────────────────────────────────────────────────────────────────────────────
 * AudioManager — centralised audio facade (Task 1).
 *
 * RECONNAISSANCE NOTES (recorded here to avoid re-reading):
 *  • Static sounds dir:  /client/static/sounds/   (clack1-3.ogg already exist)
 *  • SFX .ogg files:     NOT yet present — engine falls back to synthesis.
 *  • Ambient .ogg files: NOT yet present — SoundEngine tries manifest .wav
 *                        then procedural synthesis.
 *  • WS msg types:       sound_play_sfx | sound_set_ambient | sound_stop_all
 *  • Broadcasting:       server/handlers/sound.py → manager.broadcast()
 *                        Now uses exclude_user so DM hears local play only.
 *
 * Responsibilities:
 *  - File-based SFX loading from /static/sounds/${key}.ogg (primary path).
 *  - Silent 404 / decode-error handling — zero console errors for missing files.
 *  - Buffer caching and background preloading.
 *  - DM broadcast of sound events via existing WS message types.
 *  - Volume control delegation to the underlying SoundEngine.
 * ─────────────────────────────────────────────────────────────────────────────
 */
class AudioManager {
  /**
   * @param {SoundEngine} soundEngine  The existing authoritative sound engine.
   */
  constructor(soundEngine) {
    /** @type {SoundEngine} */
    this._engine = soundEngine;

    /** @type {Map<string, AudioBuffer>} Decoded audio buffers keyed by cache key */
    this._bufferCache = new Map();

    /** @type {Set<string>} URLs that returned non-OK or failed to decode — silently skipped */
    this._missingFiles = new Set();

    /** @type {Map<string, Promise<void>>} In-flight fetch promises to prevent duplicate requests */
    this._loadPromises = new Map();

    /**
     * Maps the new short SFX keys (used in onclick attrs and .ogg filenames)
     * back to the legacy alias the SoundEngine's procedural synthesis recognises.
     * @type {Object<string,string>}
     */
    this._sfxAliases = {
      clash:    'sword_clash',
      door:     'door_creak',
      heal:     'heal_chime',
      trap:     'trap_click',
      gasp:     'crowd_gasp',
      fireball: 'fireball',
      thunder:  'thunder',
    };

    /** Set of SFX IDs the server whitelist accepts (mirrors server/handlers/sound.py). */
    this._validServerSfxIds = new Set([
      'sword_clash', 'fireball', 'door_creak', 'thunder',
      'heal_chime', 'trap_click', 'crowd_gasp',
    ]);
  }

  // ── Internal helpers ──────────────────────────────────────────────────────

  /**
   * Ensure the AudioContext is initialised and running.
   * Must be called inside a user-gesture handler on first use.
   * @private
   */
  _resume() {
    this._engine._init();
    const ctx = this._engine._ctx;
    if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /**
   * Preload an audio file into the buffer cache.
   * Silently ignores missing files (404) and decode errors.
   *
   * @param {string} key  Cache key, e.g. 'clash'
   * @param {string} url  Absolute path, e.g. '/static/sounds/clash.ogg'
   * @returns {Promise<void>}
   */
  async preload(key, url) {
    if (this._missingFiles.has(url)) return;
    if (this._bufferCache.has(key)) return;
    if (this._loadPromises.has(key)) return this._loadPromises.get(key);

    const promise = (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) { this._missingFiles.add(url); return; }
        const arrayBuffer = await res.arrayBuffer();
        this._engine._init(); // ensure AudioContext exists before decoding
        try {
          const decoded = await this._engine._ctx.decodeAudioData(arrayBuffer);
          this._bufferCache.set(key, decoded);
        } catch (_) {
          this._missingFiles.add(url);
        }
      } catch (_) {
        this._missingFiles.add(url);
      }
    })();

    this._loadPromises.set(key, promise);
    await promise;
    this._loadPromises.delete(key);
  }

  /**
   * Play a one-shot sound effect.
   * Primary path: /static/sounds/${key}.ogg decoded via Web Audio API.
   * Fallback: procedural synthesis via the underlying SoundEngine.
   * If the current role is 'dm', also broadcasts via WebSocket so players hear it.
   *
   * @param {string} key  Short SFX key, e.g. 'clash', 'fireball', 'clack1'
   * @returns {Promise<void>}
   */
  async playSFX(key) {
    // 1. Attempt file-based playback ----------------------------------------
    await this.preload(key, `/static/sounds/${key}.ogg`);
    const buf = this._bufferCache.get(key);
    if (buf) {
      this._resume();
      const ctx = this._engine._ctx;
      const source = ctx.createBufferSource();
      source.buffer = buf;
      source.connect(this._engine._sfxGain);
      source.start(0);
    } else {
      // 2. Fallback: procedural synthesis -----------------------------------
      const alias = this._sfxAliases[key] || key;
      this._engine.playSfx(alias);
    }

    // 3. DM broadcast — server handler now uses exclude_user so this client
    //    will NOT receive the echo and play the sound a second time.
    if (typeof window !== 'undefined' && window.ROLE === 'dm' && typeof sendWS === 'function') {
      const legacyId = this._sfxAliases[key] || key;
      if (this._validServerSfxIds.has(legacyId)) {
        sendWS({ type: 'sound_play_sfx', payload: { sfx_id: legacyId, volume: this._engine._vol.sfx } });
      }
    }
  }

  /**
   * Start (or crossfade to) a looping ambient track.
   * Delegates to SoundEngine which tries the asset manifest then procedural synthesis.
   * If the current role is 'dm', also broadcasts so players switch ambient.
   *
   * @param {string} key       Ambient key, e.g. 'tavern', 'battle'
   * @param {number} [fade_ms=1500]  Crossfade duration in milliseconds
   * @returns {Promise<void>}
   */
  async playAmbient(key, fade_ms = 1500) {
    const vol = this._engine._vol.ambient;
    await this._engine.setAmbient(key, vol, fade_ms);
    if (typeof window !== 'undefined' && window.ROLE === 'dm' && typeof sendWS === 'function') {
      sendWS({ type: 'sound_set_ambient', payload: { track: key, volume: vol, fade_ms } });
    }
  }

  /**
   * Stop the current ambient track with a fade-out.
   * If the current role is 'dm', broadcasts stop to all players.
   */
  stopAmbient() {
    this._engine.stopAll();
    if (typeof window !== 'undefined' && window.ROLE === 'dm' && typeof sendWS === 'function') {
      sendWS({ type: 'sound_stop_all', payload: {} });
    }
  }

  /**
   * Stop all audio (ambient + brief SFX silence), then broadcast if DM.
   * Used by the "Stop" SFX button.
   */
  stopAll() {
    this._engine.stopAll();
    if (this._engine._sfxGain && this._engine._ctx) {
      this._engine._sfxGain.gain.setValueAtTime(0, this._engine._ctx.currentTime);
      const sfxVol = this._engine._vol.sfx;
      setTimeout(() => { if (this._engine._sfxGain) this._engine._sfxGain.gain.value = sfxVol; }, 150);
    }
    if (typeof window !== 'undefined' && window.ROLE === 'dm' && typeof sendWS === 'function') {
      sendWS({ type: 'sound_stop_all', payload: {} });
    }
  }

  /**
   * Set master volume (0–1) and persist to localStorage.
   * @param {number} v
   */
  setMasterVol(v) {
    this._engine.setMasterVolume(v);
    try { localStorage.setItem('tavern_vol_master', String(v)); } catch (_) {}
  }

  /**
   * Set ambient track volume (0–1) and persist to localStorage.
   * @param {number} v
   */
  setAmbientVol(v) {
    this._engine.setAmbientVolume(v);
    try { localStorage.setItem('tavern_vol_ambient', String(v)); } catch (_) {}
  }

  /**
   * Set SFX volume (0–1) and persist to localStorage.
   * @param {number} v
   */
  setSFXVol(v) {
    this._engine.setSfxVolume(v);
    try { localStorage.setItem('tavern_vol_sfx', String(v)); } catch (_) {}
  }

  /** The current ambient track key (e.g. 'tavern', 'silence'). */
  get currentAmbientKey() { return this._engine.currentTrack; }
}

window.AudioManager = AudioManager;
