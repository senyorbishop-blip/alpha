/**
 * dice3d.js — Tavern Tabletop Dice System v2
 *
 * Architecture:
 *   DiceWorld    — Three.js scene + cannon-es world, camera, lights, renderer
 *   DiceFactory  — per-type geometry cache, mesh creation, settle detection
 *   PhysicsWorld — SAPBroadphase, contact materials, time-based step
 *   geometries/  — one file per die type
 *   materials/   — FaceMaterial (4-layer engraved), DiceMaterial (PBR config)
 *   physics/     — PhysicsWorld, BodyFactory
 *   ui/          — ResultOverlay, DiceTheme
 *   utils/       — geometry helpers, notation parser, audio unlock
 *
 * Public API: window.DicePhysics3D (backward-compatible with v1)
 */

import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// ── Sub-modules ────────────────────────────────────────────────────────
import { DiceWorld }                        from './DiceWorld.js';
import {
  spawnDie, syncMeshToBody, readDieResult,
  detectTopFace, isDieSettled, playSettlePulse,
  sweepExistingDice, rescueBody, computeD100Result,
  checkStuckDie, validateFaceAlignment, nudgeToFace,
}                                           from './DiceFactory.js';
import { world, resetStepTimer, setPhysicsBudgetForDiceCount }            from './physics/PhysicsWorld.js';
import {
  THEME_LIBRARY, DEFAULT_THEME_ID, ensureReadableTheme,
  buildTheme, getPlayerPrefs, setPlayerPrefs, getThemes,
  getCustomStyles, saveCustomStyle, deleteCustomStyle,
}                                           from './ui/DiceTheme.js';
import { showResultOverlay, removeResultOverlay } from './ui/ResultOverlay.js';
import { unlockAudio, playRollStart }      from './utils/audio.js';
import { parseNotation, applyKeepDrop }     from './utils/notation.js';

console.log('[DicePhysics3D] module loaded');

const LOG = '[DicePhysics3D]';
const MIN_DICE_OPACITY = 0.15;
const WORLD_UP = new THREE.Vector3(0, 1, 0);

// ── Debug mode — enable for face detection diagnostics ───────────────
// Set window.DICE_DEBUG = true in browser console to enable detailed
// logging of settle detection, face alignment, and result computation.
let _diceDebug = false;
Object.defineProperty(window, 'DICE_DEBUG', {
  get: () => _diceDebug,
  set: v => {
    _diceDebug = !!v;
    if (!_diceDebug) _clearAllDebugFaceMarkers();
    console.info(`${LOG} debug mode ${_diceDebug ? 'ENABLED' : 'DISABLED'}`);
  },
  configurable: true,
});

// ── Singleton world instance ─────────────────────────────────────────
const diceWorld = new DiceWorld();
let _prewarmDone = false;
let _prewarmStarted = false;


// ── Manager state ────────────────────────────────────────────────────
let activeDice     = [];
let rafHandle      = 0;
let isRendering    = false;
let hasFirstFrame  = false;
let _firstRenderDone = false;
let onSettledCb    = null;
let specialFxCb    = null;
let pendingTargets = [];   // server-provided target results for target-assist
let _rollStartTime = 0;    // performance.now() when current throw started
let _throwReplayCount = 0;
let _lastThrowContext = null;
let _rollFeatureFlags = {
  naturalTargetLanding: true,
  emergencyHardSnapFallback: false,
};
const _debugFaceMarkers = new Map();

function _clearAllDebugFaceMarkers() {
  _debugFaceMarkers.forEach(marker => diceWorld.remove(marker));
  _debugFaceMarkers.clear();
}

function _renderDebugTopFaceMarker(die, info) {
  if (!_diceDebug || !info?.topCentroidWorld) return;
  const markerPos = info.topCentroidWorld.clone();

  let marker = _debugFaceMarkers.get(die);
  if (!marker) {
    marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.08, 10, 10),
      new THREE.MeshBasicMaterial({ color: 0x30ff30 })
    );
    marker.renderOrder = 9999;
    _debugFaceMarkers.set(die, marker);
    diceWorld.add(marker);
  }
  marker.position.copy(markerPos);
}

// Max dice on mobile to maintain performance
const isMobile  = /Mobi|Android/i.test(navigator.userAgent);
const MAX_DICE  = isMobile ? 5 : 20;

// Maximum wall-clock time for a single throw before all remaining dice are
// force-settled.  Prevents the browser from freezing when rolling 20 dice
// with heavy physics (each die has ConvexPolyhedron collisions + 20 solver
// iterations).  14 s is generous but bounded.
const MAX_ROLL_DURATION_MS = 4800;

// ── Settle pulse helper (exported for external use) ──────────────────
function _playSettlePulse(mesh) {
  playSettlePulse(mesh);
}

// ────────────────────────────────────────────────────────────────────
// Core throw pipeline
// ────────────────────────────────────────────────────────────────────

/**
 * Throw dice based on an array of configs.
 *
 * @param {Array<{type:number, count:number}>} configs
 * @param {Function}  onSettled   Called with results array when all dice settle
 * @param {Object}    opts
 * @param {number}    [opts.seed]
 * @param {string}    [opts.themeId]
 * @param {Object}    [opts.themeOverrides]
 * @param {number[]}  [opts.targetResults]   Server-authoritative values for target-assist
 */
function throwDice(configs, onSettled, opts = {}) {
  // Safe mode disables the heavy 3D dice renderer; callers fall back to the
  // lightweight non-3D result path.
  if (window.AppSafeMode && window.AppSafeMode.disabled('dice3d')) {
    console.info(`${LOG} skipped — safe mode (dice3d disabled)`);
    return false;
  }
  const container = document.getElementById('dice-3d-wrap');
  if (!container) { console.warn(`${LOG} #dice-3d-wrap not found`); return false; }

  // Ensure renderer is initialised (the 3D engine is lazy: this only runs the
  // first time a roll is requested, never during the light player boot).
  if (!diceWorld.isReady) {
    if (window.AppBoot && typeof window.AppBoot.phase === 'function') window.AppBoot.phase('dice', 'start');
    diceWorld.init(container);
    const _r = diceWorld.renderer;
    if (_r) {
      const _sz = _r.getSize(new THREE.Vector2());
      console.log(`${LOG} renderer created, size=${_sz.x}x${_sz.y}`);
      const _cv = _r.domElement;
      console.log(`${LOG} canvas attached to body, zIndex=${_cv.style.zIndex}`);
    }
    if (window.AppBoot && typeof window.AppBoot.phase === 'function') window.AppBoot.phase('dice', 'end');
  } else {
    // Re-sync size in case container was display:none at init time
    diceWorld._onResize?.();
  }

  // Sweep any existing dice off screen before new roll
  if (activeDice.length > 0) {
    sweepExistingDice([...activeDice], diceWorld);
    activeDice = [];
  }

  // Stop any running animation loop
  cancelAnimationFrame(rafHandle);
  rafHandle = 0;
  isRendering = false;

  resetStepTimer();
  removeResultOverlay();
  _clearAllDebugFaceMarkers();

  // Normalise configs → flat die type array
  const expanded = [];
  (configs || []).forEach(cfg => {
    for (let i = 0; i < Math.max(1, Number(cfg.count || 1)); i++) {
      expanded.push(Number(cfg.type || 20));
    }
  });
  const clampedDice = expanded.slice(0, MAX_DICE);

  const hasProvidedSeed = Number.isFinite(Number(opts.seed)) && Number(opts.seed) > 0;
  const seed = hasProvidedSeed
    ? Math.floor(Number(opts.seed))
    : Math.floor((performance.now() * 1000) % 999_999_999) + 1;
  if (!hasProvidedSeed) {
    console.warn(`${LOG} throw() missing deterministic seed; using defensive fallback seed=${seed}`);
  }
  const themeId   = opts.themeId
    || (window.USER_ID ? getPlayerPrefs(window.USER_ID).themeId : null)
    || DEFAULT_THEME_ID;
  const theme     = buildTheme(themeId, opts.themeOverrides);

  console.debug(`${LOG} player prefs: themeId=${themeId}, opacity=${theme.opacity}`);

  pendingTargets = Array.isArray(opts.targetResults) ? opts.targetResults.slice() : [];
  _throwReplayCount = Number(opts._replayCount || 0);
  _lastThrowContext = {
    configs: JSON.parse(JSON.stringify(configs || [])),
    onSettled,
    opts: { ...(opts || {}) },
  };
  _rollFeatureFlags = {
    naturalTargetLanding: opts?.naturalTargetLanding !== false,
    emergencyHardSnapFallback: opts?.emergencyHardSnapFallback === true,
  };

  // Adjust camera + render/physics budget for dice count
  setPhysicsBudgetForDiceCount?.(clampedDice.length);
  diceWorld.setPerformanceForCount?.(clampedDice.length);
  diceWorld.setCameraForCount(clampedDice.length);

  // Spawn dice
  activeDice = clampedDice.map((sideCount, index) => {
    const type = `d${sideCount}`;
    const die  = spawnDie(type, diceWorld, theme, {
      index, totalCount: clampedDice.length, seed,
      targetValue: pendingTargets[index] ?? null,
    });
    die.quietSince    = null;
    die.settled       = false;
    die.result        = null;
    die.forcedValue   = pendingTargets[index] ?? null;
    die.targetAssistUsed = false;
    die.assistMatchSince = 0;
    die.spawnedAt     = performance.now();
    die.stuckNudges   = 0;
    die.lastNudgeAt   = 0;
    die.faceNudges    = 0;  // post-settle face alignment nudge counter
    die.correctedAfterSettle = false;
    die.settleGlint = clampedDice.length < 5;
    die.settleGlintCap = clampedDice.length >= 5 ? 0 : 0.04;
    die.mesh.castShadow = clampedDice.length < 5;
    die.mesh.receiveShadow = clampedDice.length < 5;
    return die;
  });

  onSettledCb   = onSettled;
  hasFirstFrame = false;
  _firstRenderDone = false;
  isRendering   = true;
  _rollStartTime = performance.now();

  playRollStart?.(clampedDice.length);

  // Start animation loop
  _animate();
  return true;
}


function _prewarmDiceWorld() {
  if (_prewarmDone || _prewarmStarted) return false;
  _prewarmStarted = true;
  try {
    const container = document.getElementById('dice-3d-wrap') || document.body;
    if (!diceWorld.isReady) diceWorld.init(container);
    diceWorld.setPerformanceForCount?.(5);
    diceWorld.setCameraForCount?.(5);
    const theme = buildTheme(DEFAULT_THEME_ID, null);
    const warmed = ['d20', 'd6', 'd8', 'd10'].map((type, index) => spawnDie(type, diceWorld, theme, {
      index,
      totalCount: 4,
      seed: 8675309 + index,
      spawnPos: { x: 1000 + index * 4, y: 1000, z: 1000 },
    }));
    warmed.forEach(die => {
      diceWorld.remove(die.mesh);
      if (die.body && typeof world.removeBody === 'function') world.removeBody(die.body);
      else if (die.body && typeof world.remove === 'function') world.remove(die.body);
    });
    diceWorld.render?.();
    _prewarmDone = true;
    console.debug(`${LOG} prewarmed renderer and common combat dice (d20,d6,d8,d10)`);
    return true;
  } catch (err) {
    console.debug(`${LOG} prewarm skipped`, err);
    _prewarmStarted = false;
    return false;
  }
}

function scheduleDicePrewarm() {
  const run = () => _prewarmDiceWorld();
  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(run, { timeout: 2500 });
  } else {
    window.setTimeout(run, 1200);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', scheduleDicePrewarm, { once: true });
} else {
  scheduleDicePrewarm();
}

function _normalizedForcedValue(die) {
  if (!die) return null;
  if (die.type === 'd100') {
    return typeof die.forcedValue === 'number'
      ? String(die.forcedValue).padStart(2, '0')
      : die.forcedValue;
  }
  if (die.type === 'd10') {
    const numeric = Number(die.forcedValue);
    if (numeric === 10) return 0;
    return Number.isNaN(numeric) ? die.forcedValue : numeric;
  }
  return Number.isNaN(Number(die.forcedValue)) ? die.forcedValue : Number(die.forcedValue);
}

function _snapDieToForcedValue(die) {
  if (!die || die.forcedValue == null) return false;
  const normalizedForced = _normalizedForcedValue(die);
  const targetFace = (die.faceDefinitions || []).find(f => String(f.value) === String(normalizedForced));
  const targetNormal = targetFace?.normal ?? null;
  if (!targetNormal) return false;

  const q = new THREE.Quaternion().setFromUnitVectors(
    targetNormal.clone().normalize(),
    new THREE.Vector3(0, 1, 0)
  );

  die.body.quaternion.set(q.x, q.y, q.z, q.w);
  die.body.velocity.setZero();
  die.body.angularVelocity.setZero();
  if (typeof die.body.sleep === 'function') die.body.sleep();
  syncMeshToBody(die);

  const confirmed = detectTopFace(die);
  die.result = confirmed.value ?? normalizedForced;
  die.targetAssistUsed = true;
  return true;
}

// ── Animation loop ────────────────────────────────────────────────────
let _lastFrameTime = 0;

/** Stop a die's physics body and record its final result + settle pulse. */
function _forceSettleDie(die, opts = {}) {
  let forcedSnap = false;
  const allowHardSnap = opts.allowHardSnap === true;
  if (allowHardSnap && die.forcedValue != null) {
    forcedSnap = _snapDieToForcedValue(die);
  }
  die.body.velocity.setZero();
  die.body.angularVelocity.setZero();
  die.body.sleep();
  die.settled = true;
  die.result  = readDieResult(die);
  die.forcedSnapOccurred = forcedSnap;
  const debugInfo = detectTopFace(die);
  _renderDebugTopFaceMarker(die, debugInfo);
  if (_diceDebug) {
    console.info(
      `[DiceDebug] ${die.type} settle-check faceIndex=${debugInfo.faceIndex}` +
      ` value=${debugInfo.value} bestDot=${debugInfo.dot.toFixed(3)}` +
      ` secondDot=${debugInfo.secondDot.toFixed(3)} forcedSnap=${forcedSnap ? 'yes' : 'no'}`
    );
  }
  playSettlePulse(die.mesh, { glint: die.settleGlint !== false, glintCap: die.settleGlintCap ?? 0.04 });
}


function _applySoftTargetAssist(die, now) {
  if (!die || die.forcedValue == null || !_rollFeatureFlags.naturalTargetLanding) return;
  if (die.settled) return;
  if ((now - (die.spawnedAt || 0)) < 160) return;
  const speed = die.body.velocity.length();
  const angSpeed = die.body.angularVelocity.length();
  if (speed > 1.95 || angSpeed > 6.2) return;

  const normalizedForced = _normalizedForcedValue(die);
  const targetFace = (die.faceDefinitions || []).find(f => String(f.value) === String(normalizedForced));
  if (!targetFace?.normal) return;

  const current = detectTopFace(die);
  if (String(current?.value) === String(normalizedForced) && (current?.dot ?? 0) >= 0.93) return;

  const worldQuat = new THREE.Quaternion(
    die.body.quaternion.x,
    die.body.quaternion.y,
    die.body.quaternion.z,
    die.body.quaternion.w
  );
  const worldTargetNormal = targetFace.normal.clone().applyQuaternion(worldQuat).normalize();
  const alignment = Math.max(-1, Math.min(1, worldTargetNormal.dot(WORLD_UP)));
  const axis = new THREE.Vector3().crossVectors(worldTargetNormal, WORLD_UP);
  const axisLen = axis.length();
  if (axisLen < 1e-5) return;
  axis.normalize();

  const isNarrowFaceDie = die.type === 'd10' || die.type === 'd100';
  const dieTypeScale = isNarrowFaceDie ? 1.6 : 1.0;
  const strength = Math.min(isNarrowFaceDie ? 3.6 : 2.6, Math.max(0.55, (1 - alignment) * 2.15)) * dieTypeScale;
  die.body.wakeUp?.();
  die.body.angularVelocity.x += axis.x * strength;
  die.body.angularVelocity.y += axis.y * (strength * 0.22);
  die.body.angularVelocity.z += axis.z * strength;
  die.body.velocity.y += 0.012 * dieTypeScale;


  die.lastAssistAt = now;
}

function _animate() {
  cancelAnimationFrame(rafHandle);
  rafHandle = requestAnimationFrame(_tick);
}

function _tick(now) {
  if (!diceWorld.isReady) return;
  
  hasFirstFrame = true;
  if (!_firstRenderDone) {
    _firstRenderDone = true;
    console.log(`${LOG} first render complete`);
  }

  _lastFrameTime = now;

  // Advance physics
  diceWorld.tick(now);

  // Per-die: rescue + sync mesh
  activeDice.forEach(die => {
    rescueBody(die.body);
    _applySoftTargetAssist(die, now);
    syncMeshToBody(die);
  });

  // Check settle state — time-based physical-truth finalization
  let allSettled = activeDice.length > 0;

  // ── Global roll timeout ────────────────────────────────────────────
  // When rolling 20 dice the physics simulation can be CPU-intensive and
  // individual stuck-die timeouts can stack up to ~15 s each.  If the
  // entire throw has been running longer than MAX_ROLL_DURATION_MS, force-
  // settle every remaining die immediately so the result is always reported
  // and the browser never appears frozen.
  const rollElapsed = now - _rollStartTime;
  if (rollElapsed > MAX_ROLL_DURATION_MS) {
    activeDice.forEach(die => {
      if (!die.settled) {
        _forceSettleDie(die, { allowHardSnap: die.forcedValue != null, reason: 'global-timeout' });
        if (_diceDebug) console.warn(`[DiceDebug] ${die.type} GLOBAL-TIMEOUT force-settled`);
      }
    });
  }

  activeDice.forEach(die => {
    if (!die.settled) {
      checkStuckDie(die, now);
      if (isDieSettled(die, now)) {
        if (!validateFaceAlignment(die)) nudgeToFace(die);
        _forceSettleDie(die, { allowHardSnap: die.forcedValue != null, reason: 'natural-settle' });

        if (_diceDebug) {
          const info = detectTopFace(die);
          console.info(
            `[DiceDebug] ${die.type} SETTLED → face=${info.faceIndex} value=${die.result}` +
            ` dot=${info.dot.toFixed(3)} secondDot=${info.secondDot.toFixed(3)} margin=${info.margin.toFixed(3)}` +
            ` vel=${die.body.velocity.length().toFixed(4)} angVel=${die.body.angularVelocity.length().toFixed(4)}`
          );
        }
      } else {
        allSettled = false;
      }
    }
  });

  if (allSettled && activeDice.length > 0) {
    isRendering = false;
    // Collect results from physics — this is the single source of truth
    const results = activeDice.map(die => ({
      type:  die.type,
      value: die.result ?? readDieResult(die),
    }));

    if (_diceDebug) {
      console.info('[DiceDebug] All dice settled. Physics results:', results);
      activeDice.forEach(die => {
        const info = detectTopFace(die);
        console.info(
          `[DiceDebug]   ${die.type}: result=${die.result}` +
          ` faceIdx=${info.faceIndex} dot=${info.dot.toFixed(3)} margin=${info.margin.toFixed(3)}` +
          ` pos=(${die.body.position.x.toFixed(2)},${die.body.position.y.toFixed(2)},${die.body.position.z.toFixed(2)})`
        );
      });
    }

    onSettledCb?.(results);
    return;  // stop loop — dice are frozen
  }

  rafHandle = requestAnimationFrame(_tick);
}

// ────────────────────────────────────────────────────────────────────
// Preview renderer (dice theme preview in settings panel)
// ────────────────────────────────────────────────────────────────────
function createPreview(canvasEl, prefs) {
  const isMobilePreview = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  const renderer = new THREE.WebGLRenderer({ canvas: canvasEl, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobilePreview ? 1 : 2));
  renderer.setClearColor(0x000000, 0);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
  camera.position.set(0, 1.35, 6.8);
  camera.lookAt(0, 0, 0);

  const previewWorld = {
    add: (obj) => scene.add(obj),
    remove: (obj) => obj && scene.remove(obj),
    disposeGroup: () => {},
  };

  // Environment
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();

  const hemi  = new THREE.HemisphereLight(0xdbe8ff, 0x07080b, 1.2);
  scene.add(hemi);
  const light = new THREE.DirectionalLight(0xffffff, 1.8);
  light.position.set(3, 5, 2);
  scene.add(light);

  let previewDie = null;
  let previewMesh = null;
  let currentTheme = null;

  function disposeMaterial(material) {
    if (!material) return;
    Object.values(material).forEach((value) => {
      if (value && value.isTexture && typeof value.dispose === 'function') {
        value.dispose();
      }
    });
    if (typeof material.dispose === 'function') material.dispose();
  }

  function disposeMeshResources(mesh) {
    if (!mesh) return;
    if (Array.isArray(mesh.material)) mesh.material.forEach(disposeMaterial);
    else disposeMaterial(mesh.material);
    if (mesh.geometry && typeof mesh.geometry.dispose === 'function') mesh.geometry.dispose();
  }

  function syncSize() {
    const width = canvasEl.clientWidth || canvasEl.width || 140;
    const height = canvasEl.clientHeight || canvasEl.height || 140;
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  }

  function rebuildDie(themePrefs) {
    currentTheme = ensureReadableTheme({ ...THEME_LIBRARY[DEFAULT_THEME_ID], ...(themePrefs || {}) });
    if (previewDie?.mesh) {
      scene.remove(previewDie.mesh);
      disposeMeshResources(previewDie.mesh);
    }
    // Use d12 for preview to reduce face texture/memory pressure on phones.
    previewDie = spawnDie('d12', previewWorld, currentTheme, {});
    previewMesh = previewDie.mesh;
    previewMesh.scale.setScalar(1.22);
    previewMesh.position.set(0, -0.55, 0);
    previewMesh.rotation.set(-0.45, 0.5, 0.2);
  }

  syncSize();
  rebuildDie(prefs);

  let stopped = false;
  (function draw() {
    if (stopped) return;
    syncSize();
    if (previewMesh) {
      previewMesh.rotation.x += 0.01;
      previewMesh.rotation.y += 0.015;
    }
    renderer.render(scene, camera);
    requestAnimationFrame(draw);
  })();

  return {
    update: next => {
      rebuildDie(next);
    },
    stop: () => {
      stopped = true;
      if (previewDie?.mesh) {
        scene.remove(previewDie.mesh);
        disposeMeshResources(previewDie.mesh);
      }
      if (scene.environment && typeof scene.environment.dispose === 'function') {
        scene.environment.dispose();
      }
      renderer.dispose();
    },
  };
}

// ────────────────────────────────────────────────────────────────────
// Close / cleanup
// ────────────────────────────────────────────────────────────────────
function closeDice() {
  cancelAnimationFrame(rafHandle);
  rafHandle   = 0;
  isRendering = false;

  activeDice.forEach(die => {
    const marker = _debugFaceMarkers.get(die);
    if (marker) {
      diceWorld.remove(marker);
      _debugFaceMarkers.delete(die);
    }
    diceWorld.disposeGroup(die.mesh);
    world.removeBody(die.body);
  });
  activeDice = [];
  pendingTargets = [];
  _clearAllDebugFaceMarkers();
  removeResultOverlay();

  // Render one empty frame to clear canvas
  diceWorld.render();
}

// ────────────────────────────────────────────────────────────────────
// Percentile helper — expand d100 result to visual [tens, units] pair
// ────────────────────────────────────────────────────────────────────
function expandPercentileVisuals(rolls) {
  const visual = [];
  (rolls || []).forEach(value => {
    const numeric = Math.max(1, Math.min(100, parseInt(value, 10) || 100));
    const tens    = numeric === 100 ? '00' : String(Math.floor(numeric / 10) * 10).padStart(2, '0');
    const ones    = numeric === 100 ? 0    : numeric % 10;
    visual.push(tens, ones);
  });
  return visual;
}

function getCharacterModifierBundle() {
  const store = window.AppStore || window.AppStateStore;
  if (!store || typeof store.getCharacterModifiers !== 'function') return null;
  try {
    return store.getCharacterModifiers();
  } catch (_err) {
    return null;
  }
}

function resolveNamedModifier(modifierKey) {
  const mods = getCharacterModifierBundle();
  if (!mods) return { key: 'none', label: 'None', value: 0 };
  const key = String(modifierKey || '0').trim().toLowerCase();
  if (!key || key === '0' || key === 'none') return { key: 'none', label: 'None', value: 0 };
  if (key === 'prof') return { key, label: 'Proficiency', value: parseInt(mods.profBonus, 10) || 0 };
  if (Object.prototype.hasOwnProperty.call(mods, key)) {
    return { key, label: key.toUpperCase(), value: parseInt(mods[key], 10) || 0 };
  }
  if (mods.skills && Object.prototype.hasOwnProperty.call(mods.skills, key)) {
    return { key, label: key, value: parseInt(mods.skills[key], 10) || 0 };
  }
  return { key: 'none', label: 'None', value: 0 };
}

// ────────────────────────────────────────────────────────────────────
// collectResults — read current die faces (call after settle)
// ────────────────────────────────────────────────────────────────────
function collectResults() {
  return activeDice.map(die => {
    const detected = detectTopFace(die);
    return {
      type:     die.type,
      faceIndex: detected.faceIndex,
      value:    detected.value,
      score:    detected.dot,
      margin:   detected.margin,
      ambiguous: detected.margin <= 0.12 || detected.dot < 0.78,
      correctedAfterSettle: !!die.correctedAfterSettle,
      forcedSnapOccurred: !!die.forcedSnapOccurred,
      bodyQuaternion: {
        x: die.body.quaternion.x,
        y: die.body.quaternion.y,
        z: die.body.quaternion.z,
        w: die.body.quaternion.w,
      },
      meshQuaternion: {
        x: die.mesh.quaternion.x,
        y: die.mesh.quaternion.y,
        z: die.mesh.quaternion.z,
        w: die.mesh.quaternion.w,
      },
    };
  });
}

// ────────────────────────────────────────────────────────────────────
// setResult — update pending target-assist values mid-roll
// ────────────────────────────────────────────────────────────────────
function setResult(values) {
  pendingTargets = Array.isArray(values) ? values.slice() : [];
  activeDice.forEach((die, i) => {
    die.forcedValue = pendingTargets[i] ?? null;
    die.assistMatchSince = 0;
  });
}

function hardSnapResults(values, reason = 'fallback') {
  pendingTargets = Array.isArray(values) ? values.slice() : [];
  let changed = false;
  activeDice.forEach((die, i) => {
    die.forcedValue = pendingTargets[i] ?? null;
    if (die.forcedValue == null) return;
    // Keep visual truth: do not hard-snap settled dice to target values.
    if (false && _snapDieToForcedValue(die)) {
      die.correctedAfterSettle = true;
      die.forcedSnapOccurred = true;
      changed = true;
    }
  });
  if (changed) diceWorld.forceRenderAfterSync?.();
  if (_diceDebug) console.warn(`[DiceDebug] hardSnapResults applied (${reason}) changed=${changed}`);
  return changed;
}

// ────────────────────────────────────────────────────────────────────
// Public API — window.DicePhysics3D
// Backward-compatible with v1 API that play.html depends on.
// ────────────────────────────────────────────────────────────────────
window.DicePhysics3D = Object.freeze({
  // Core throw
  throw: (configs, onSettled, opts = {}) => throwDice(configs, onSettled, opts),
  prewarm: () => _prewarmDiceWorld(),
  isPrewarmed: () => _prewarmDone,
  setResult,
  hardSnapResults,
  close:          closeDice,
  collectResults,

  // Status
  isReady:        () => diceWorld.isReady,
  isContextLost:  () => !!diceWorld.renderer?.contextLost,
  isRendering:    () => isRendering,
  hasFirstFrame:  () => hasFirstFrame,
  hasDice:        () => activeDice.length > 0,

  // Preview
  createPreview: (canvas, prefs) => createPreview(canvas, prefs),
  detectUpFace:  (die) => die ? detectTopFace(die) : null,

  // Theme / prefs
  setPlayerPrefs: (userId, prefs) => {
    if (prefs && prefs.opacity != null) prefs.opacity = Math.max(MIN_DICE_OPACITY, Math.min(1, prefs.opacity));
    return setPlayerPrefs(userId, prefs);
  },
  loadPlayerPrefs: (userId) => {
    const p = getPlayerPrefs(userId);
    if (p) p.opacity = Math.max(MIN_DICE_OPACITY, Math.min(1, p.opacity ?? 1));
    return p;
  },
  getPlayerPrefs:  (userId)       => getPlayerPrefs(userId),
  getThemes,
  getCustomStyles: (userId)       => getCustomStyles(userId),
  saveCustomStyle: (userId, name, style) => saveCustomStyle(userId, name, style),
  deleteCustomStyle: (userId, styleId)   => deleteCustomStyle(userId, styleId),

  // Special FX callbacks
  setOnSpecialFx:   cb => { specialFxCb = cb; },
  triggerSpecialFx: (fxType, result) => specialFxCb?.(fxType, result),

  // Notation parser (extended API)
  parseNotation,
  applyKeepDrop,

  // Percentile helper
  expandPercentileVisuals,
  getCharacterModifierBundle,
  resolveNamedModifier,

  // Debug tools
  getActiveDice:  () => activeDice.map(d => ({
    type: d.type, settled: d.settled, result: d.result,
    vel: d.body.velocity.length(), angVel: d.body.angularVelocity.length(),
    topFace: detectTopFace(d),
    pos: { x: d.body.position.x, y: d.body.position.y, z: d.body.position.z },
  })),
  setDebug: (v) => { _diceDebug = !!v; },
});

// Unlock AudioContext on first interaction (see utils/audio.js for listener registration)
// The document-level listeners are self-registered in audio.js on import.

console.info(`${LOG} v2 loaded — modular architecture, time-based settle, SAPBroadphase`);
