/**
 * sfx_engine.js — compatibility/fallback procedural SFX library.
 *
 * Stage 2 note:
 * - `client/static/js/ui/sound_engine.js` owns the live SFX facade used by `play.html`.
 * - This file exists to backstop missing asset cases and legacy compatibility while
 *   `play.html` still loads it. Do not treat it as a peer runtime authority.
 *
 * Zero audio files. Pure Web Audio API synthesis.
 * Respects SFX Vol slider. Never interrupts ambient audio.
 *
 * Supported SFX names:
 *   clash | fireball | door | thunder | heal | trap | gasp | stop
 *   (also accepts legacy IDs: sword_clash, fireball, door_creak,
 *    thunder, heal_chime, trap_click, crowd_gasp)
 *
 * Public API:
 *   sfx.play(name, volume)   // volume 0.0–1.0
 *   sfx.stop()               // silence all active SFX immediately
 *
 * Global: window.tavernSFX = new SFXEngine()
 */

'use strict';

// Normalise legacy IDs from existing button onclick handlers
const _SFX_ALIASES = {
  sword_clash: 'clash',
  door_creak:  'door',
  heal_chime:  'heal',
  trap_click:  'trap',
  crowd_gasp:  'gasp',
};

class SFXEngine {
  constructor(soundEngineRef) {
    // soundEngineRef: existing SoundEngine instance (for shared sfxGain)
    this._se         = soundEngineRef || null;
    this._ctx        = null;
    this._sfxGain    = null;
    this._masterGain = null;
    this._sfxVol     = 1.0;
    this._masterVol  = 1.0;
    this._activeNodes = [];
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  _init() {
    // Prefer the shared SoundEngine AudioContext if available
    if (this._se && this._se._ctx) {
      this._ctx        = this._se._ctx;
      this._sfxGain    = this._se._sfxGain;
      this._masterGain = this._se._masterGain;
      this._sfxVol     = this._se._vol?.sfx  ?? 1.0;
      this._masterVol  = this._se._vol?.master ?? 1.0;
      return;
    }
    // Standalone fallback
    if (!this._ctx) {
      this._ctx        = new (window.AudioContext || window.webkitAudioContext)();
      this._masterGain = this._ctx.createGain();
      this._sfxGain    = this._ctx.createGain();
      this._masterGain.gain.value = this._masterVol;
      this._sfxGain.gain.value   = this._sfxVol;
      this._sfxGain.connect(this._masterGain);
      this._masterGain.connect(this._ctx.destination);
    }
  }

  setSfxVolume(v)    { this._sfxVol    = Math.max(0, Math.min(1, v)); }
  setMasterVolume(v) { this._masterVol = Math.max(0, Math.min(1, v)); }

  // ── Public interface ──────────────────────────────────────────────────────

  play(name, volume = 1.0) {
    this._init();
    const normalised = _SFX_ALIASES[name] || name;
    const sfxVol     = this._sfxVol * this._masterVol * Math.max(0, Math.min(1, volume));

    switch (normalised) {
      case 'clash':    this._playClash(sfxVol);    break;
      case 'fireball': this._playFireball(sfxVol); break;
      case 'door':     this._playDoor(sfxVol);     break;
      case 'thunder':  this._playThunder(sfxVol);  break;
      case 'heal':     this._playHeal(sfxVol);     break;
      case 'trap':     this._playTrap(sfxVol);     break;
      case 'gasp':     this._playGasp(sfxVol);     break;
      case 'viewer_power_fire': this._playViewerPowerFire(sfxVol); break;
      case 'stop':     this.stop();                break;
      default:
        console.warn(`[SFXEngine] unknown SFX: "${name}"`);
    }
  }

  stop() {
    if (!this._sfxGain) return;
    const ctx = this._ctx;
    const now = ctx.currentTime;
    this._sfxGain.gain.cancelScheduledValues(now);
    this._sfxGain.gain.setValueAtTime(this._sfxGain.gain.value, now);
    this._sfxGain.gain.linearRampToValueAtTime(0, now + 0.01);
    setTimeout(() => {
      this._sfxGain.gain.setValueAtTime(this._sfxVol, now + 0.015);
    }, 20);
  }

  // ── SFX builders ─────────────────────────────────────────────────────────

  /** CLASH — White noise burst 50ms + sine chirp 800→200Hz 80ms + short reverb */
  _playClash(vol) {
    const ctx = this._ctx;
    const now = ctx.currentTime;
    const dest = this._sfxGain;

    // Short reverb
    const rev  = this._makeConvolver(0.4);
    const revG = ctx.createGain();
    revG.gain.value = 0.3;
    rev.connect(revG);
    revG.connect(dest);

    // Noise burst 50ms
    const noise = this._noiseSource(0.08);
    const npBP  = ctx.createBiquadFilter();
    npBP.type = 'bandpass'; npBP.frequency.value = 3000; npBP.Q.value = 2;
    const nEnv  = ctx.createGain();
    nEnv.gain.setValueAtTime(vol * 0.8, now);
    nEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
    noise.connect(npBP); npBP.connect(nEnv);
    nEnv.connect(dest); nEnv.connect(rev);
    noise.start(now); noise.stop(now + 0.06);

    // Chirp 800→200Hz
    const osc  = ctx.createOscillator();
    const oEnv = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(800, now);
    osc.frequency.exponentialRampToValueAtTime(200, now + 0.08);
    oEnv.gain.setValueAtTime(vol * 0.5, now);
    oEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
    osc.connect(oEnv); oEnv.connect(dest); oEnv.connect(rev);
    osc.start(now); osc.stop(now + 0.09);
  }

  /** FIREBALL — Pink noise swell + dynamic lowpass sweep + sub thump */
  _playFireball(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    // Pink noise swell: attack 20ms, release 600ms
    const noise = this._noiseSource(0.7);
    const nLP   = ctx.createBiquadFilter();
    nLP.type = 'lowpass'; nLP.frequency.value = 4000;
    // Dynamic lowpass sweep 4000→400Hz
    nLP.frequency.setValueAtTime(4000, now + 0.02);
    nLP.frequency.exponentialRampToValueAtTime(400, now + 0.62);

    const nEnv  = ctx.createGain();
    nEnv.gain.setValueAtTime(0, now);
    nEnv.gain.linearRampToValueAtTime(vol * 0.9, now + 0.02);
    nEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.62);
    noise.connect(nLP); nLP.connect(nEnv); nEnv.connect(dest);
    noise.start(now); noise.stop(now + 0.65);

    // Sub thump 50Hz 150ms
    const sub  = ctx.createOscillator();
    const sEnv = ctx.createGain();
    sub.type = 'sine'; sub.frequency.value = 50;
    sEnv.gain.setValueAtTime(vol * 0.7, now);
    sEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    sub.connect(sEnv); sEnv.connect(dest);
    sub.start(now); sub.stop(now + 0.16);
  }

  /** DOOR — FM sine 200→80Hz 300ms + brown noise thud 80ms */
  _playDoor(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    // FM creak: modulated sine
    const carrier = ctx.createOscillator();
    const modOsc  = ctx.createOscillator();
    const modGain = ctx.createGain();
    carrier.type = 'sine'; carrier.frequency.value = 200;
    carrier.frequency.exponentialRampToValueAtTime(80, now + 0.3);
    modOsc.frequency.value = 60; modGain.gain.value = 40;
    modOsc.connect(modGain); modGain.connect(carrier.frequency);
    const cEnv = ctx.createGain();
    cEnv.gain.setValueAtTime(vol * 0.6, now);
    cEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    carrier.connect(cEnv); cEnv.connect(dest);
    carrier.start(now); carrier.stop(now + 0.31);
    modOsc.start(now); modOsc.stop(now + 0.31);

    // Thud: brown noise
    const thud = this._noiseSource(0.12, 'brown');
    const tLP  = ctx.createBiquadFilter();
    tLP.type = 'lowpass'; tLP.frequency.value = 200;
    const tEnv = ctx.createGain();
    tEnv.gain.setValueAtTime(vol * 0.7, now + 0.28);
    tEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.36);
    thud.connect(tLP); tLP.connect(tEnv); tEnv.connect(dest);
    thud.start(now + 0.28); thud.stop(now + 0.37);
  }

  /** THUNDER — Layered brown noise bursts + random stereo panning */
  _playThunder(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    const layers = [
      { delay: 0,    dur: 1.6, gain: vol * 0.8, pan: -0.3 + Math.random() * 0.6 },
      { delay: 0.08, dur: 1.4, gain: vol * 0.5, pan: -0.4 + Math.random() * 0.8 },
      { delay: 0.22, dur: 1.2, gain: vol * 0.3, pan: -0.5 + Math.random() * 1.0 },
    ];

    layers.forEach(({ delay, dur, gain, pan }) => {
      const noise = this._noiseSource(dur + 0.1, 'brown');
      const lp    = ctx.createBiquadFilter();
      lp.type = 'lowpass'; lp.frequency.value = 280;
      const env   = ctx.createGain();
      env.gain.setValueAtTime(gain, now + delay);
      env.gain.exponentialRampToValueAtTime(0.001, now + delay + dur);

      const panner = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
      if (panner) panner.pan.value = pan;

      noise.connect(lp); lp.connect(env);
      if (panner) { env.connect(panner); panner.connect(dest); }
      else env.connect(dest);

      noise.start(now + delay);
      noise.stop(now + delay + dur + 0.05);
    });
  }

  /** HEAL — Ascending sine arpeggio C4→G4→C5 + soft reverb halo */
  _playHeal(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    const rev  = this._makeConvolver(0.8);
    const revG = ctx.createGain();
    revG.gain.value = 0.28;
    rev.connect(revG); revG.connect(dest);

    // C4=261.6, G4=392, C5=523.25
    const notes = [261.6, 392.0, 523.25];
    notes.forEach((freq, i) => {
      const t   = now + i * 0.085;
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type            = 'triangle';
      osc.frequency.value = freq;
      env.gain.setValueAtTime(0, t);
      env.gain.linearRampToValueAtTime(vol * 0.55, t + 0.01);
      env.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
      osc.connect(env);
      env.connect(dest); env.connect(rev);
      osc.start(t); osc.stop(t + 0.2);
    });
  }

  /** TRAP — White noise click 5ms + sawtooth 300→80Hz 200ms */
  _playTrap(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    // Mechanical click
    const click = this._noiseSource(0.01);
    const cEnv  = ctx.createGain();
    cEnv.gain.setValueAtTime(vol * 0.9, now);
    cEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.005);
    click.connect(cEnv); cEnv.connect(dest);
    click.start(now); click.stop(now + 0.01);

    // Mechanism snap: sawtooth glide
    const saw  = ctx.createOscillator();
    const sEnv = ctx.createGain();
    saw.type = 'sawtooth';
    saw.frequency.setValueAtTime(300, now + 0.005);
    saw.frequency.exponentialRampToValueAtTime(80, now + 0.2);
    sEnv.gain.setValueAtTime(vol * 0.5, now + 0.005);
    sEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
    saw.connect(sEnv); sEnv.connect(dest);
    saw.start(now + 0.005); saw.stop(now + 0.21);
  }

  /** GASP — Bandpass noise 1000–3000Hz + pitch wobble via LFO */
  _playGasp(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    const noise = this._noiseSource(0.5);
    const bp    = ctx.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.value = 2000; bp.Q.value = 2.5;
    const env   = ctx.createGain();
    env.gain.setValueAtTime(0, now);
    env.gain.linearRampToValueAtTime(vol * 0.6, now + 0.01);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

    // Pitch wobble: LFO at 6Hz modulating bandpass freq
    const wobble = ctx.createOscillator();
    const wobG   = ctx.createGain();
    wobble.type            = 'sine';
    wobble.frequency.value = 6;
    wobG.gain.value        = 300;
    wobble.connect(wobG); wobG.connect(bp.frequency);
    wobble.start(now); wobble.stop(now + 0.42);

    noise.connect(bp); bp.connect(env); env.connect(dest);
    noise.start(now); noise.stop(now + 0.42);
  }

  /** VIEWER POWER FIRE — Mystical chime: rising sine chord + shimmer noise + sub pulse */
  _playViewerPowerFire(vol) {
    const ctx  = this._ctx;
    const now  = ctx.currentTime;
    const dest = this._sfxGain;

    // Reverb tail
    const rev  = this._makeConvolver(0.7);
    const revG = ctx.createGain();
    revG.gain.value = 0.3;
    rev.connect(revG); revG.connect(dest);

    // Rising chord: A4=440, E5=659, A5=880
    const notes = [440, 659.25, 880];
    notes.forEach((freq, i) => {
      const t   = now + i * 0.06;
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq * 0.85, t);
      osc.frequency.exponentialRampToValueAtTime(freq, t + 0.12);
      env.gain.setValueAtTime(0, t);
      env.gain.linearRampToValueAtTime(vol * 0.45, t + 0.015);
      env.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
      osc.connect(env); env.connect(dest); env.connect(rev);
      osc.start(t); osc.stop(t + 0.26);
    });

    // Shimmer: short high-frequency noise burst
    const shimmer = this._noiseSource(0.18);
    const sBP = ctx.createBiquadFilter();
    sBP.type = 'bandpass'; sBP.frequency.value = 6000; sBP.Q.value = 3;
    const sEnv = ctx.createGain();
    sEnv.gain.setValueAtTime(0, now + 0.04);
    sEnv.gain.linearRampToValueAtTime(vol * 0.25, now + 0.06);
    sEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
    shimmer.connect(sBP); sBP.connect(sEnv); sEnv.connect(dest); sEnv.connect(rev);
    shimmer.start(now + 0.04); shimmer.stop(now + 0.23);

    // Sub pulse
    const sub  = ctx.createOscillator();
    const subE = ctx.createGain();
    sub.type = 'sine'; sub.frequency.value = 70;
    subE.gain.setValueAtTime(vol * 0.5, now);
    subE.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
    sub.connect(subE); subE.connect(dest);
    sub.start(now); sub.stop(now + 0.19);
  }

  // ── Audio building helpers ────────────────────────────────────────────────

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
}

// ---------------------------------------------------------------------------
// Singleton export
// ---------------------------------------------------------------------------

window.SFXEngine = SFXEngine;
