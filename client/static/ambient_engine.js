/**
 * ambient_engine.js — compatibility/fallback procedural ambient synthesizer.
 *
 * Stage 2 note:
 * - `client/static/js/ui/sound_engine.js` is the authoritative live ambient engine.
 * - This file is preserved as a procedural fallback/compatibility layer while `play.html`
 *   still loads it. Do not treat it as a peer runtime authority.
 *
 * Zero audio files. Pure Web Audio API synthesis.
 * Scenes: tavern | dungeon | forest | battle | silence
 *
 * Public API:
 *   engine.setScene(name)
 *   engine.setAmbientVolume(0.0–1.0)
 *   engine.crossfadeTo(scene, durationSecs)
 *   engine.setIntensity(0.0–1.0)     // battle intensity
 *   engine.setAutoMode(bool)          // WebSocket-driven scene switching
 *
 * Global: window.tavernAmbient = new AmbientEngine()
 */

'use strict';

class AmbientEngine {
  constructor() {
    this._ctx            = null;
    this._masterGain     = null;
    this._ambientGain    = null;
    this._currentScene   = 'silence';
    this._previousScene  = 'silence';
    this._intensity      = 0.5;
    this._autoMode       = false;
    this._nodes          = [];        // active audio graph nodes
    this._scheduledIds   = [];        // setTimeout / setInterval IDs
    this._volume         = 0.7;
    this._crossfadeTimer = null;
    this._battleKick     = null;      // kick drum interval for battle
    this._drip           = null;      // drip scheduler for dungeon
    this._bird           = null;      // bird call scheduler for forest
  }

  // ── Init ─────────────────────────────────────────────────────────────────

  _init() {
    if (this._ctx) return;
    this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    this._masterGain  = this._ctx.createGain();
    this._ambientGain = this._ctx.createGain();
    this._masterGain.gain.value  = 1.0;
    this._ambientGain.gain.value = this._volume;
    this._ambientGain.connect(this._masterGain);
    this._masterGain.connect(this._ctx.destination);
  }

  // ── Public API ────────────────────────────────────────────────────────────

  setScene(name) {
    this.crossfadeTo(name, 3.0);
  }

  setAmbientVolume(v) {
    this._volume = Math.max(0, Math.min(1, v));
    if (this._ambientGain) {
      const now = this._ctx.currentTime;
      this._ambientGain.gain.cancelScheduledValues(now);
      this._ambientGain.gain.setValueAtTime(this._ambientGain.gain.value, now);
      this._ambientGain.gain.linearRampToValueAtTime(this._volume, now + 0.1);
    }
  }

  crossfadeTo(scene, durationSecs = 3.0) {
    this._init();
    if (scene === this._currentScene) return;
    const dur = Math.max(0.5, durationSecs);

    // Fade out current scene
    const now = this._ctx.currentTime;
    this._ambientGain.gain.cancelScheduledValues(now);
    this._ambientGain.gain.setValueAtTime(this._ambientGain.gain.value, now);
    this._ambientGain.gain.linearRampToValueAtTime(0, now + dur * 0.5);

    if (this._crossfadeTimer) clearTimeout(this._crossfadeTimer);
    this._crossfadeTimer = setTimeout(() => {
      this._stopAllNodes();
      this._previousScene = this._currentScene;
      this._currentScene  = scene;
      if (scene !== 'silence') {
        this._startScene(scene);
        const t = this._ctx.currentTime;
        this._ambientGain.gain.cancelScheduledValues(t);
        this._ambientGain.gain.setValueAtTime(0, t);
        this._ambientGain.gain.linearRampToValueAtTime(this._volume, t + dur * 0.5);
      }
    }, dur * 0.5 * 1000);
  }

  setIntensity(v) {
    this._intensity = Math.max(0, Math.min(1, v));
    // Will be picked up by battle scene on next node creation
  }

  setAutoMode(enabled) {
    this._autoMode = !!enabled;
  }

  get currentScene() { return this._currentScene; }

  // ── Internal scene dispatch ───────────────────────────────────────────────

  _startScene(name) {
    switch (name) {
      case 'tavern':  this._buildTavern();  break;
      case 'dungeon': this._buildDungeon(); break;
      case 'forest':  this._buildForest();  break;
      case 'battle':  this._buildBattle();  break;
      default: break; // silence
    }
  }

  _stopAllNodes() {
    this._scheduledIds.forEach(id => { clearTimeout(id); clearInterval(id); });
    this._scheduledIds = [];
    this._nodes.forEach(n => {
      try { n.stop?.(); }  catch {}
      try { n.disconnect?.(); } catch {}
    });
    this._nodes = [];
  }

  // ── Node factory helpers ──────────────────────────────────────────────────

  _noise(type = 'white', seconds = 12) {
    const sr  = this._ctx.sampleRate;
    const len = Math.ceil(sr * seconds);
    const buf = this._ctx.createBuffer(1, len, sr);
    const d   = buf.getChannelData(0);
    if (type === 'white') {
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
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
    } else if (type === 'brown') {
      let last = 0;
      for (let i = 0; i < len; i++) {
        const w = Math.random() * 2 - 1;
        last = (last + 0.02 * w) / 1.02;
        d[i] = last * 3.5;
      }
    }
    const src = this._ctx.createBufferSource();
    src.buffer = buf;
    src.loop   = true;
    this._nodes.push(src);
    return src;
  }

  _biquad(type, freq, Q = 1) {
    const f = this._ctx.createBiquadFilter();
    f.type            = type;
    f.frequency.value = freq;
    f.Q.value         = Q;
    this._nodes.push(f);
    return f;
  }

  _gain(val) {
    const g = this._ctx.createGain();
    g.gain.value = val;
    this._nodes.push(g);
    return g;
  }

  _osc(type, freq) {
    const o = this._ctx.createOscillator();
    o.type            = type;
    o.frequency.value = freq;
    this._nodes.push(o);
    return o;
  }

  _lfo(freq, min = 0, max = 1) {
    const lfo      = this._ctx.createOscillator();
    const lfoGain  = this._ctx.createGain();
    lfo.type            = 'sine';
    lfo.frequency.value = freq;
    lfoGain.gain.value  = (max - min) / 2;
    lfo.connect(lfoGain);
    lfo.start();
    this._nodes.push(lfo, lfoGain);
    return { lfo, gain: lfoGain };
  }

  _convolver(rt60Secs = 1.5) {
    const sr  = this._ctx.sampleRate;
    const len = Math.ceil(sr * rt60Secs);
    const buf = this._ctx.createBuffer(2, len, sr);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.2);
      }
    }
    const conv = this._ctx.createConvolver();
    conv.buffer = buf;
    this._nodes.push(conv);
    return conv;
  }

  _connect(...chain) {
    for (let i = 0; i < chain.length - 1; i++) {
      chain[i].connect(chain[i + 1]);
    }
  }

  // ── TAVERN ────────────────────────────────────────────────────────────────
  // Pink noise → bandpass 200–800Hz (crowd murmur)
  // Sine 55Hz (fireplace warmth)
  // Random wood creak clicks
  // High-shelf rolloff above 3kHz (muffled interior)
  // Two detuned oscillators ±8 cents (chorus depth)

  _buildTavern() {
    const dest = this._ambientGain;

    // Crowd murmur: pink noise through resonant bandpass
    const crowd = this._noise('pink', 8);
    const bp1   = this._biquad('bandpass', 400, 3.5);
    const bp2   = this._biquad('bandpass', 700, 2.0);
    const shelf = this._biquad('highshelf', 3000);
    shelf.gain.value = -18;
    const crowdGain = this._gain(0.28);
    this._connect(crowd, bp1, bp2, shelf, crowdGain, dest);
    crowd.start();

    // Fireplace warmth: low sine
    const fire = this._osc('sine', 55);
    const fireGain = this._gain(0.06);
    this._connect(fire, fireGain, dest);
    fire.start();

    // Chorus: two detuned oscillators at 110Hz ±8 cents
    const c1 = this._osc('sine', 110 * Math.pow(2, 8 / 1200));
    const c2 = this._osc('sine', 110 * Math.pow(2, -8 / 1200));
    const cg  = this._gain(0.04);
    c1.connect(cg); c2.connect(cg); cg.connect(dest);
    c1.start(); c2.start();

    // Murmur LFO modulation (0.12Hz subtle swell)
    const { gain: lfoG } = this._lfo(0.12, 0.22, 0.32);
    lfoG.connect(crowdGain.gain);

    // Wood creaks: random short click events
    const _scheduleCreak = () => {
      const delay = 4000 + Math.random() * 12000;
      const id = setTimeout(() => {
        if (this._currentScene !== 'tavern') return;
        this._playClick(220 + Math.random() * 110, 0.06 + Math.random() * 0.05, 0.12);
        _scheduleCreak();
      }, delay);
      this._scheduledIds.push(id);
    };
    _scheduleCreak();
  }

  // ── DUNGEON ───────────────────────────────────────────────────────────────
  // Brown noise → steep lowpass 120Hz (stone ambience)
  // Drip synth: Poisson-distributed triangle pings 440–880Hz
  // Generated convolver impulse (2.5s RT60 reverb)
  // Wind moan: sine LFO 0.1Hz modulating bandpass 80–160Hz Q=8

  _buildDungeon() {
    const dest = this._ambientGain;

    // Stone rumble: brown noise through steep lowpass
    const stone = this._noise('brown', 10);
    const lp    = this._biquad('lowpass', 120, 0.5);
    const stoneGain = this._gain(0.35);
    this._connect(stone, lp, stoneGain, dest);
    stone.start();

    // Reverb send for drips
    const rev     = this._convolver(2.5);
    const revGain = this._gain(0.22);
    rev.connect(revGain);
    revGain.connect(dest);

    // Wind moan: sine through modulated bandpass
    const wind    = this._osc('sine', 120);
    const windBP  = this._biquad('bandpass', 120, 8);
    const windGain= this._gain(0.09);
    this._connect(wind, windBP, windGain, dest);
    wind.start();
    // LFO sweeps bandpass freq between 80-160Hz at 0.1Hz
    const windLFO = this._ctx.createOscillator();
    const windLFOg= this._ctx.createGain();
    windLFO.type            = 'sine';
    windLFO.frequency.value = 0.1;
    windLFOg.gain.value     = 40;
    windLFO.connect(windLFOg);
    windLFOg.connect(windBP.frequency);
    windLFO.start();
    this._nodes.push(windLFO, windLFOg);

    // Drip scheduler: Poisson-distributed triangle pings
    const _scheduleDrip = () => {
      // Poisson: exponential inter-arrival, mean 4s
      const delay = -Math.log(1 - Math.random()) * 4000;
      const id = setTimeout(() => {
        if (this._currentScene !== 'dungeon') return;
        const freq = 440 + Math.random() * 440;  // 440–880Hz
        this._playDrip(freq, rev);
        _scheduleDrip();
      }, delay);
      this._scheduledIds.push(id);
    };
    _scheduleDrip();
    _scheduleDrip(); // Start two concurrent drip chains
  }

  _playDrip(freq, reverbNode) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const osc  = ctx.createOscillator();
    const env  = ctx.createGain();
    osc.type            = 'triangle';
    osc.frequency.value = freq;
    env.gain.setValueAtTime(0, now);
    env.gain.linearRampToValueAtTime(0.18, now + 0.001);   // 1ms attack
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.8); // 800ms decay
    osc.connect(env);
    if (reverbNode) env.connect(reverbNode);
    env.connect(this._ambientGain);
    osc.start(now);
    osc.stop(now + 0.85);
  }

  // ── FOREST ────────────────────────────────────────────────────────────────
  // White noise → dynamic bandpass sweep (LFO 0.3Hz, wind/leaves)
  // Bird calls: FM-modulated sine+triangle, random 4–20s intervals
  // Cricket layer: 6–8kHz AM noise at 3Hz, activates after 30s
  // Low-level pink noise bed (-30dB)

  _buildForest() {
    const dest = this._ambientGain;

    // Wind / leaves: white noise through sweeping bandpass
    const wind    = this._noise('white', 10);
    const windBP  = this._biquad('bandpass', 800, 1.8);
    const windGain= this._gain(0.15);
    this._connect(wind, windBP, windGain, dest);
    wind.start();
    // Bandpass sweep LFO (0.3Hz, 400–1200Hz)
    const swpLFO = this._ctx.createOscillator();
    const swpG   = this._ctx.createGain();
    swpLFO.frequency.value = 0.3;
    swpG.gain.value        = 400;
    swpLFO.connect(swpG);
    swpG.connect(windBP.frequency);
    swpLFO.start();
    this._nodes.push(swpLFO, swpG);

    // Pink noise bed (distant ambience, -30dB)
    const bed     = this._noise('pink', 12);
    const bedGain = this._gain(0.03);
    this._connect(bed, bedGain, dest);
    bed.start();

    // Bird call scheduler
    const _scheduleBird = () => {
      const delay = 4000 + Math.random() * 16000;
      const id = setTimeout(() => {
        if (this._currentScene !== 'forest') return;
        this._playBirdCall();
        _scheduleBird();
      }, delay);
      this._scheduledIds.push(id);
    };
    _scheduleBird();

    // Cricket layer — activates after 30s of forest
    const cricketTimer = setTimeout(() => {
      if (this._currentScene !== 'forest') return;
      this._buildCrickets();
    }, 30000);
    this._scheduledIds.push(cricketTimer);
  }

  _playBirdCall() {
    const ctx    = this._ctx;
    const now    = ctx.currentTime;
    const base   = 1200 + Math.random() * 800;
    const dur    = 0.08 + Math.random() * 0.12;
    const notes  = 2 + Math.floor(Math.random() * 3);

    for (let n = 0; n < notes; n++) {
      const t     = now + n * (dur + 0.04);
      const freq  = base * (1 + (Math.random() - 0.5) * 0.3);
      const osc1  = ctx.createOscillator();
      const osc2  = ctx.createOscillator();
      const env   = ctx.createGain();
      osc1.type            = 'sine';
      osc2.type            = 'triangle';
      osc1.frequency.value = freq;
      osc2.frequency.value = freq * 1.005;
      env.gain.setValueAtTime(0, t);
      env.gain.linearRampToValueAtTime(0.09, t + 0.01);
      env.gain.exponentialRampToValueAtTime(0.001, t + dur);
      osc1.connect(env); osc2.connect(env);
      env.connect(this._ambientGain);
      osc1.start(t); osc2.start(t);
      osc1.stop(t + dur + 0.01); osc2.stop(t + dur + 0.01);
    }
  }

  _buildCrickets() {
    const ctx    = this._ctx;
    const noise  = this._noise('white', 8);
    const hp     = this._biquad('highpass', 6000, 1.0);
    const lp     = this._biquad('lowpass', 8000, 1.0);
    const amGain = this._gain(0.12);

    // AM at 3Hz
    const amLFO  = ctx.createOscillator();
    const amLFOg = ctx.createGain();
    amLFO.type            = 'sine';
    amLFO.frequency.value = 3.0;
    amLFOg.gain.value     = 0.5;
    amLFO.connect(amLFOg);
    amLFOg.connect(amGain.gain);
    amLFO.start();
    this._nodes.push(amLFO, amLFOg);

    this._connect(noise, hp, lp, amGain, this._ambientGain);
    noise.start();
  }

  // ── BATTLE ────────────────────────────────────────────────────────────────
  // Two detuned sawtooths 110Hz ±3Hz → lowpass 400Hz
  // Kick drum synthesis at 120 BPM
  // Metallic shimmer: AM noise bursts at irregular intervals
  // Intensity float 0–1: scales gain + LFO speed

  _buildBattle() {
    const dest = this._ambientGain;
    const ints = this._intensity;

    // Detuned sawtooth drones
    const saw1 = this._osc('sawtooth', 110 + 3);
    const saw2 = this._osc('sawtooth', 110 - 3);
    const lp   = this._biquad('lowpass', 400, 1.0);
    const dGain= this._gain(0.12 + ints * 0.08);
    saw1.connect(lp); saw2.connect(lp);
    lp.connect(dGain);
    dGain.connect(dest);
    saw1.start(); saw2.start();

    // Kick drum at 120 BPM = 500ms per beat
    const bpm = 120;
    const beatMs = 60000 / bpm;
    const _kick = () => {
      if (this._currentScene !== 'battle') return;
      this._playKick();
    };
    const kickInt = setInterval(_kick, beatMs);
    this._scheduledIds.push(kickInt);
    _kick(); // immediate first beat

    // Metallic shimmer: irregular AM noise bursts
    const _shimmer = () => {
      const delay = 800 + Math.random() * 2200;
      const id = setTimeout(() => {
        if (this._currentScene !== 'battle') return;
        this._playShimmer();
        _shimmer();
      }, delay);
      this._scheduledIds.push(id);
    };
    _shimmer();
  }

  _playKick() {
    const ctx = this._ctx;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = 'sine';
    // Pitch envelope: 60→30Hz over 200ms
    osc.frequency.setValueAtTime(60, now);
    osc.frequency.exponentialRampToValueAtTime(30, now + 0.2);
    env.gain.setValueAtTime(0.55, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
    osc.connect(env);
    env.connect(this._ambientGain);
    osc.start(now);
    osc.stop(now + 0.25);
  }

  _playShimmer() {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dur  = 0.05 + Math.random() * 0.15;
    const freq = 3000 + Math.random() * 5000;
    const noise= ctx.createBufferSource();
    const sr   = ctx.sampleRate;
    const len  = Math.ceil(sr * 0.3);
    const buf  = ctx.createBuffer(1, len, sr);
    const d    = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    noise.buffer = buf;
    const bp   = ctx.createBiquadFilter();
    bp.type            = 'bandpass';
    bp.frequency.value = freq;
    bp.Q.value         = 8;
    const env  = ctx.createGain();
    env.gain.setValueAtTime(0, now);
    env.gain.linearRampToValueAtTime(0.08 + this._intensity * 0.06, now + 0.005);
    env.gain.exponentialRampToValueAtTime(0.001, now + dur);
    noise.connect(bp); bp.connect(env);
    env.connect(this._ambientGain);
    noise.start(now);
    noise.stop(now + dur + 0.01);
  }

  _playClick(freq, gain, dur) {
    const ctx = this._ctx;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type            = 'triangle';
    osc.frequency.value = freq;
    env.gain.setValueAtTime(gain, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + dur);
    osc.connect(env);
    env.connect(this._ambientGain);
    osc.start(now);
    osc.stop(now + dur + 0.01);
  }
}

// ---------------------------------------------------------------------------
// Singleton export
// ---------------------------------------------------------------------------

window.AmbientEngine = AmbientEngine;
