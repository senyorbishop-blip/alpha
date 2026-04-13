import * as CANNON from 'cannon-es';

/**
 * AudioContext-based dice sound system.
 * AudioContext MUST be unlocked on first user interaction — not on first roll.
 * This module self-initialises on the first click/keydown event.
 */

let audioCtx    = null;
const clackBuffers = [];
let lastClackAt = 0;
let activeClacks = 0;
let recentImpactWindow = [];

/**
 * Call once on ANY user interaction (map click, UI button, keydown, etc.)
 * Safe to call multiple times — only initialises once.
 */
export function unlockAudio() {
  if (audioCtx) return;
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  } catch (e) {
    console.warn('[DiceAudio] AudioContext unavailable:', e);
    return;
  }

  // Preload clack sound variants
  ['clack1.ogg', 'clack2.ogg', 'clack3.ogg'].forEach(async (file, i) => {
    try {
      const res = await fetch(`/static/sounds/${file}`);
      if (!res.ok) return;
      const buf = await res.arrayBuffer();
      clackBuffers[i] = await audioCtx.decodeAudioData(buf);
    } catch (e) {
      // Sounds are optional — degrade gracefully
    }
  });
}

/**
 * Play a clack sound scaled by impact velocity.
 * @param {number} impactVelocity
 */
export function playClack(impactVelocity) {
  if (!audioCtx || clackBuffers.length === 0) return;
  if (!Number.isFinite(impactVelocity) || impactVelocity < 1.25) return;
  const buf = clackBuffers[Math.floor(Math.random() * clackBuffers.length)];
  if (!buf) return;

  const now = audioCtx.currentTime;
  recentImpactWindow = recentImpactWindow.filter(ts => (now - ts) < 0.14);
  const poolBusyFactor = recentImpactWindow.length;
  if ((now - lastClackAt) < (poolBusyFactor >= 4 ? 0.045 : 0.028)) return;
  if (activeClacks >= (poolBusyFactor >= 4 ? 3 : 5)) return;
  lastClackAt = now;
  recentImpactWindow.push(now);

  const source = audioCtx.createBufferSource();
  const gain   = audioCtx.createGain();
  const lowpass = audioCtx.createBiquadFilter();
  const panner = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;
  source.buffer = buf;
  source.playbackRate.value = 0.93 + (Math.random() * 0.08);
  lowpass.type = 'lowpass';
  lowpass.frequency.value = Math.max(980, 3200 - impactVelocity * 110);
  const peak = Math.min(0.62, 0.05 + impactVelocity * 0.03);
  gain.gain.value = 0.0001;
  gain.gain.linearRampToValueAtTime(peak, now + 0.006);
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, peak * 0.42), now + 0.065);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
  if (panner) panner.pan.value = (Math.random() - 0.5) * 0.35;
  source.connect(lowpass);
  if (panner) {
    lowpass.connect(panner);
    panner.connect(gain);
  } else {
    lowpass.connect(gain);
  }
  gain.connect(audioCtx.destination);
  activeClacks += 1;
  source.onended = () => { activeClacks = Math.max(0, activeClacks - 1); };
  source.start();
}

/**
 * Hook into a cannon-es world's postStep event to play clack sounds
 * when dice collide above a velocity threshold.
 * @param {CANNON.World} world
 */
export function hookPhysicsAudio(world) {
  world.addEventListener('postStep', () => {
    for (const contact of world.contacts) {
      const impact = Math.abs(contact.getImpactVelocityAlongNormal());
      // Legacy audit reference: impact > 2.1
      if (impact > 1.25) playClack(impact);
    }
  });
}

// Auto-unlock on first user interaction — globally, once per page load
if (typeof document !== 'undefined') {
  document.addEventListener('pointerdown', unlockAudio, { once: true });
  document.addEventListener('touchstart', unlockAudio, { once: true, passive: true });
  document.addEventListener('click',   unlockAudio, { once: true });
  document.addEventListener('keydown', unlockAudio, { once: true });
}


export function playRollStart(diceCount = 1) {
  if (!audioCtx) return;
  const now = audioCtx.currentTime;
  const duration = Math.min(0.36, 0.16 + Math.max(1, Number(diceCount) || 1) * 0.015);
  const bufferSize = Math.max(1, Math.floor(audioCtx.sampleRate * duration));
  const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < bufferSize; i++) {
    const t = i / bufferSize;
    const env = Math.pow(1 - t, 1.8);
    data[i] = (Math.random() * 2 - 1) * env * 0.16;
  }
  const source = audioCtx.createBufferSource();
  source.buffer = buffer;
  const bandpass = audioCtx.createBiquadFilter();
  bandpass.type = 'bandpass';
  bandpass.frequency.value = 540;
  bandpass.Q.value = 0.85;
  const lowpass = audioCtx.createBiquadFilter();
  lowpass.type = 'lowpass';
  lowpass.frequency.value = 1800;
  const gain = audioCtx.createGain();
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.linearRampToValueAtTime(0.12, now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  source.connect(bandpass);
  bandpass.connect(lowpass);
  lowpass.connect(gain);
  gain.connect(audioCtx.destination);
  source.start(now);
  source.stop(now + duration);
}
