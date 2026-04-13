import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import { world } from './physics/PhysicsWorld.js';
import { createDieBody, sweepBody } from './physics/BodyFactory.js';
import { planLaunchRecipe } from './physics/LaunchPlanner.js';
import { createAllFaceTextures } from './materials/FaceMaterial.js';
import { createDiceMaterials } from './materials/DiceMaterial.js';

// Geometry constructors
import { createD4Geometry,  createD4PhysicsShape, D4_FACE_VALUES, D4_FACE_VERTEX_TRIPLETS, D4_LOCAL_VERTICES, D4_VERTEX_VALUES } from './geometries/D4.js';
import { createD6Geometry,  createD6PhysicsShape,  D6_FACE_VALUES,  D6_FACE_NORMALS, D6_FACE_CENTERS } from './geometries/D6.js';
import { createD8Geometry,  createD8PhysicsShape,  D8_FACE_VALUES  } from './geometries/D8.js';
import { createD10Geometry, createD10PhysicsShape, D10_FACE_VALUES, D100_TENS_VALUES } from './geometries/D10.js';
import { createD12Geometry, createD12PhysicsShape, D12_FACE_VALUES } from './geometries/D12.js';
import { createD20Geometry, createD20PhysicsShape, D20_FACE_VALUES, D20_CANONICAL_FACES } from './geometries/D20.js';
import { computeD100Result } from './geometries/D100.js';

/**
 * DiceFactory — creates die meshes + physics bodies by type.
 * Caches geometries and physics shapes — expensive to rebuild per-roll.
 */

// ── Geometry + physics shape caches ──────────────────────────────────
const geometryCache    = new Map();
const physicsShapeCache = new Map();

function getGeometry(type) {
  if (!geometryCache.has(type)) {
    geometryCache.set(type, _buildGeometry(type));
  }
  return geometryCache.get(type).clone();  // clone supports future GPU instancing
}

function getPhysicsShape(type) {
  if (!physicsShapeCache.has(type)) {
    physicsShapeCache.set(type, _buildPhysicsShape(type));
  }
  return physicsShapeCache.get(type);  // physics shapes are safe to share (readonly)
}

function _buildGeometry(type) {
  switch (type) {
    case 'd4':   return createD4Geometry();
    case 'd6':   return createD6Geometry();
    case 'd8':   return createD8Geometry();
    case 'd10':  return createD10Geometry();
    case 'd12':  return createD12Geometry();
    case 'd20':  return createD20Geometry();
    case 'd100': return createD10Geometry();  // d100 uses d10 shape with different labels
    default: throw new Error(`Unknown die type: ${type}`);
  }
}

function _buildPhysicsShape(type) {
  switch (type) {
    case 'd4':   return createD4PhysicsShape();
    case 'd6':   return createD6PhysicsShape();
    case 'd8':   return createD8PhysicsShape();
    case 'd10':  return createD10PhysicsShape();
    case 'd12':  return createD12PhysicsShape();
    case 'd20':  return createD20PhysicsShape();
    case 'd100': return createD10PhysicsShape();
    default: throw new Error(`Unknown die type: ${type}`);
  }
}

// ── Face value lookup tables ──────────────────────────────────────────
const DIE_FACE_VALUES = {
  d4:   D4_FACE_VALUES,
  d6:   D6_FACE_VALUES,
  d8:   D8_FACE_VALUES,
  d10:  D10_FACE_VALUES,
  d12:  D12_FACE_VALUES,
  d20:  D20_FACE_VALUES,
  d100: D100_TENS_VALUES,
};

// ── Face label sets ───────────────────────────────────────────────────
// CRITICAL: labels MUST match DIE_FACE_VALUES so that the texture on each
// face shows the same number that readTopFaceResult() will return.
// Previously labels were sequential (['1','2','3',...]) while values used
// non-sequential ordering for opposite-face-sum conventions, causing the
// visual result to differ from the reported result on d6, d8, and d20.
function getFaceLabels(type) {
  const values = DIE_FACE_VALUES[type];
  if (!values || values.length === 0) return [];
  if (type === 'd4') {
    return D4_FACE_VERTEX_TRIPLETS.map(triplet => triplet.map(v => String(v)));
  }
  if (type === 'd20') {
    return D20_CANONICAL_FACES.map(face => String(face.value));
  }
  if (type === 'd10') {
    return values.map(v => String(v));
  }
  return values.map(v => String(v));
}

// ── Die scale table ───────────────────────────────────────────────────
// D4 scale updated to 0.90 after normalising tetrahedron vertices to
// unit circumradius (previously ±1 → circumradius √3 ≈ 1.73 caused D4
// to appear ~47 % larger than D20 on screen).
const DIE_SCALES = { d4:0.90, d6:0.90, d8:0.88, d10:0.85, d12:0.95, d20:1.00, d100:0.85 };
const VISUAL_SCALE = 1.08;  // keep single-die size consistent even in larger pools

// ── Settle detection constants (time-based) ───────────────────────────
const SETTLE_SPEED_LINEAR  = 0.07;
const SETTLE_SPEED_ANGULAR = 0.10;
const SETTLE_DURATION_MS   = 540;   // shorter confirm window = tighter, less floaty settle

// ── Post-settle face alignment thresholds ──────────────────────────────
// When a die settles, verify it's actually resting on a face (not an edge/corner).
// If the top-face normal doesn't align well with +Y, the die is in an implausible
// state and needs a corrective nudge.
const MIN_FACE_DOT         = 0.84;  // minimum dot(faceNormal, +Y) for valid rest
const MIN_FACE_MARGIN      = 0.10;  // minimum gap between 1st and 2nd best face
const MAX_FACE_NUDGES      = 3;     // max corrective nudges before accepting position
const NUDGE_ANGULAR_XZ     = 2.5;   // angular impulse on X/Z axes (tipping axes)
const NUDGE_ANGULAR_Y      = 1.0;   // angular impulse on Y axis (spin — less important)
const NUDGE_LIFT_Y         = 0.3;   // vertical lift to reduce floor friction during nudge

// ── Stuck-die recovery constants ──────────────────────────────────────
const STUCK_TIMEOUT_MS     = 4000;  // consider die stuck after 4 s without settling
const STUCK_NUDGE_UP       = 1.8;   // upward impulse
const STUCK_NUDGE_LATERAL  = 1.2;   // lateral impulse
const STUCK_TORQUE         = 5.0;   // angular kick
const STUCK_MAX_RETRIES    = 3;     // max nudges before forced settle

const WORLD_UP = new THREE.Vector3(0, 1, 0);

function _getDiceCamera() {
  const cam = (typeof window !== 'undefined') ? window.__DICE_WORLD_CAMERA__ : null;
  return cam && cam.isPerspectiveCamera ? cam : null;
}

function _detectVisibleCameraFace(die) {
  const cam = _getDiceCamera();
  if (!cam || !die?.mesh) return null;
  const center = die.mesh.position.clone();
  const direction = center.clone().sub(cam.position).normalize();
  const ray = new THREE.Raycaster(cam.position, direction, 0, cam.position.distanceTo(center) + 8);
  const hits = ray.intersectObject(die.mesh, false);
  const hit = hits.find(entry => Number.isInteger(entry?.face?.materialIndex));
  if (!hit) return null;
  const faces = _getFaceEntries(die);
  const face = faces.find(f => f.faceIndex === hit.face.materialIndex) || faces[hit.face.materialIndex] || null;
  if (!face) return null;
  const worldQuat = new THREE.Quaternion(
    die.body.quaternion.x, die.body.quaternion.y,
    die.body.quaternion.z, die.body.quaternion.w
  );
  const scored = _scoreFaceForRead(die, face, worldQuat);
  return {
    faceIndex: face.faceIndex,
    value: face.value,
    dot: scored.dot,
    margin: 1,
    secondDot: -1,
    oppositeFaceIndex: face.oppositeFaceIndex ?? null,
    topCentroidLocal: face.centroid ? face.centroid.clone() : null,
    topCentroidWorld: face.centroid ? face.centroid.clone().applyQuaternion(worldQuat).add(new THREE.Vector3(die.body.position.x, die.body.position.y, die.body.position.z)) : null,
    secondFaceIndex: null,
    fromCamera: true,
  };
}

function _getFaceEntries(die) {
  if (Array.isArray(die.faceDefinitions) && die.faceDefinitions.length > 0) {
    return die.faceDefinitions;
  }
  return (die.faceNormals || []).map((normal, i) => ({
    faceIndex: i,
    value: die.faceValues?.[i] ?? null,
    normal,
    centroid: die.faceCenters?.[i] ?? null,
    oppositeFaceIndex: null,
  }));
}

/**
 * Spawn a single die: mesh + physics body.
 *
 * @param {string}   type       Die type: 'd4','d6','d8','d10','d12','d20','d100'
 * @param {DiceWorld} diceWorld  The Three.js + physics scene
 * @param {Object}   theme      Resolved theme object (from DiceTheme.js)
 * @param {Object}   opts
 * @param {number}   opts.index       Die index in throw (0-based)
 * @param {number}   opts.totalCount  Total dice count
 * @param {number}   opts.seed        Deterministic seed
 * @param {Object}   [opts.spawnPos]  Override spawn position {x,y,z}
 * @returns {Object}  { mesh, body, type, faceNormals, faceFaceValues }
 */
const EXPECTED_FACE_COUNTS = { d4: 4, d6: 6, d8: 8, d10: 10, d12: 12, d20: 20, d100: 10 };
const EXPECTED_VALUE_SETS = {
  d4: [1, 2, 3, 4],
  d6: [1, 2, 3, 4, 5, 6],
  d8: [1, 2, 3, 4, 5, 6, 7, 8],
  d10: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  d12: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  d20: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
  d100: ['00', '10', '20', '30', '40', '50', '60', '70', '80', '90'],
};

function validateFaceAudit(type, labels, faceValues, faceDefinitions, faceNormals) {
  const expectedCount = EXPECTED_FACE_COUNTS[type];
  if (expectedCount !== undefined) {
    if ((labels?.length || 0) !== expectedCount) console.error(`❌ ${type.toUpperCase()} label count mismatch: ${labels?.length || 0}/${expectedCount}`);
    if ((faceValues?.length || 0) !== expectedCount) console.error(`❌ ${type.toUpperCase()} face value count mismatch: ${faceValues?.length || 0}/${expectedCount}`);
    if ((faceDefinitions?.length || 0) !== expectedCount) console.error(`❌ ${type.toUpperCase()} face definition count mismatch: ${faceDefinitions?.length || 0}/${expectedCount}`);
    if ((faceNormals?.length || 0) !== expectedCount) console.error(`❌ ${type.toUpperCase()} face normal count mismatch: ${faceNormals?.length || 0}/${expectedCount}`);
  }
  const expectedValues = EXPECTED_VALUE_SETS[type];
  if (expectedValues) {
    const actual = [...(faceValues || [])].map(v => String(v)).sort();
    const expected = [...expectedValues].map(v => String(v)).sort();
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      console.error(`❌ ${type.toUpperCase()} face values failed audit.`, { actual, expected });
    }
  }
}

export function spawnDie(type, diceWorld, theme, opts = {}) {
  const { index = 0, totalCount = 1, seed = 1, spawnPos = null, targetValue = null } = opts;

  const geo     = getGeometry(type);
  const labels  = getFaceLabels(type);
  const textures = createAllFaceTextures(labels, theme.baseColor, theme.numeralColor, type);
  const materials = createDiceMaterials(textures, theme);

  // ── Validation: catch geometry/texture count mismatches early ────────
  const expected = EXPECTED_FACE_COUNTS[type];
  if (expected !== undefined) {
    // D6 uses RoundedBoxGeometry which may have extra rounded-edge groups — skip group check
    if (type !== 'd6' && geo.groups.length !== expected) {
      console.error(`❌ ${type.toUpperCase()} geometry has ${geo.groups.length} material groups, expected ${expected}. Numbers will be wrong or missing.`);
    }
    if (textures.length !== expected) {
      console.error(`❌ ${type.toUpperCase()} has ${textures.length} textures, expected ${expected}.`);
    }
  }

  // For D6, we need to set up face normals manually since RoundedBoxGeometry
  // doesn't give us faceNormalsLocal via buildFlatFaceGeometry
  if (type === 'd6') {
    geo.userData.faceNormalsLocal = D6_FACE_NORMALS.map(n => n.clone());
    geo.userData.faceCenters      = D6_FACE_CENTERS.map(c => c.clone());
  }

  const mesh = new THREE.Mesh(geo, materials.length > 1 ? materials : materials[0]);
  mesh.castShadow    = true;
  mesh.receiveShadow = true;
  // Keep dice at the same physical visual size regardless of pool count.
  // Large-pool performance is handled by physics/render budgets instead of shrinking dice.
  mesh.scale.setScalar((DIE_SCALES[type] ?? 0.90) * VISUAL_SCALE);

  // Random initial orientation — no die starts at rest orientation
  mesh.quaternion.set(
    Math.random() - 0.5,
    Math.random() - 0.5,
    Math.random() - 0.5,
    Math.random() - 0.5,
  ).normalize();

  diceWorld.add(mesh);

  // Store face normals for result reading.
  // BufferGeometry.clone() serialises userData via JSON round-trip, which converts
  // THREE.Vector3 instances to plain {x,y,z} objects.  Re-wrap them so that
  // readTopFaceResult() can call .clone()/.applyQuaternion() without crashing.
  const faceNormals = (geo.userData.faceNormalsLocal ?? []).map(
    n => n instanceof THREE.Vector3 ? n : new THREE.Vector3(n.x, n.y, n.z)
  );
  const faceValues  = DIE_FACE_VALUES[type] ?? [];
  const faceCenters = (geo.userData.faceCenters ?? []).map(
    c => c instanceof THREE.Vector3 ? c : new THREE.Vector3(c.x, c.y, c.z)
  );
  const faceDefinitions = type === 'd20'
    ? D20_CANONICAL_FACES.map(f => ({
        faceIndex: f.faceIndex,
        value: f.value,
        label: f.label,
        normal: f.normal.clone(),
        centroid: f.centroid.clone(),
        oppositeFaceIndex: f.oppositeFaceIndex,
      }))
    : faceNormals.map((normal, i) => ({
        faceIndex: i,
        value: faceValues[i] ?? null,
        normal,
        centroid: faceCenters[i] ?? null,
        oppositeFaceIndex: null,
      }));

  // Validate face normals count matches expected — mismatch causes silent result errors
  if (expected !== undefined && faceNormals.length !== expected) {
    console.error(`❌ ${type.toUpperCase()} has ${faceNormals.length} face normals, expected ${expected}. Result reading will be broken.`);
  }

  validateFaceAudit(type, labels, faceValues, faceDefinitions, faceNormals);

  const launchRecipe = planLaunchRecipe({
    dieType: type,
    targetValue,
    seed,
    index,
    totalCount,
    faceDefinitions,
    fallbackSpawn: spawnPos,
  });
  const physicsShape = getPhysicsShape(type);
  const body = createDieBody(physicsShape, type, index, totalCount, seed, spawnPos, launchRecipe);

  return { mesh, body, type, faceNormals, faceValues, faceCenters, faceDefinitions };
}

/**
 * Sync Three.js mesh position/rotation to physics body.
 * Must be called every animation frame AFTER physics.step().
 */
export function syncMeshToBody(die) {
  die.mesh.position.set(die.body.position.x, die.body.position.y, die.body.position.z);
  die.mesh.quaternion.set(die.body.quaternion.x, die.body.quaternion.y, die.body.quaternion.z, die.body.quaternion.w);
}

/**
 * Read the result from a settled die.
 * Most dice read from the face whose outward normal is most aligned with world +Y.
 * The d4 is the one exception: players read the upward point, so d4 results are
 * derived from the topmost vertex instead of the resting face normal.
 *
 * @param {Object} die   Die object from spawnDie()
 * @returns {number|string}  The face value showing upward
 */
export function readDieResult(die) {
  return readTopFaceResult(die);
}


function _scoreFaceForRead(die, face, worldQuat) {
  const worldN = face.normal.clone().applyQuaternion(worldQuat).normalize();
  const centroidWorld = face.centroid
    ? face.centroid.clone().applyQuaternion(worldQuat)
    : new THREE.Vector3();
  const dot = worldN.dot(WORLD_UP);
  const centroidY = centroidWorld.y;
  const needsNarrowFaceRead = die?.type === 'd10' || die?.type === 'd100';
  if (!needsNarrowFaceRead) {
    return { dot, centroidY, score: dot };
  }

  const cam = _getDiceCamera();
  let facing = dot;
  if (cam) {
    const toCam = cam.position.clone().sub(centroidWorld).normalize();
    facing = worldN.dot(toCam);
  }
  const score = (centroidY * 1.05) + (facing * 0.72) + (dot * 0.08);
  return { dot, centroidY, facing, score };
}

// ── All dice: face whose normal most closely aligns with +Y ─────────
function _detectD4UpwardPoint(die, worldQuat) {
  let best = null;
  let second = null;
  D4_LOCAL_VERTICES.forEach((vertex, index) => {
    const worldVertex = new THREE.Vector3(vertex.x, vertex.y, vertex.z).applyQuaternion(worldQuat);
    const dot = worldVertex.dot(WORLD_UP);
    if (!best || dot > best.dot) {
      second = best;
      best = { index, dot };
    } else if (!second || dot > second.dot) {
      second = { index, dot };
    }
  });
  const topIndex = best?.index ?? 0;
  const bottomFaceIndex = [3, 1, 2, 0][topIndex] ?? 0;
  return {
    vertexIndex: topIndex,
    value: D4_VERTEX_VALUES[topIndex] ?? null,
    faceIndex: bottomFaceIndex,
    dot: best?.dot ?? -1,
    margin: (best?.dot ?? 0) - (second?.dot ?? 0),
    secondDot: second?.dot ?? -1,
    topCentroidLocal: new THREE.Vector3(
      D4_LOCAL_VERTICES[topIndex]?.x ?? 0,
      D4_LOCAL_VERTICES[topIndex]?.y ?? 0,
      D4_LOCAL_VERTICES[topIndex]?.z ?? 0
    ),
  };
}

function readTopFaceResult(die) {
  const worldQuat = new THREE.Quaternion(
    die.body.quaternion.x, die.body.quaternion.y,
    die.body.quaternion.z, die.body.quaternion.w
  );

  if (die?.type === 'd4') {
    return _detectD4UpwardPoint(die, worldQuat).value;
  }
  if (die?.type === 'd10' || die?.type === 'd100') {
    const visible = _detectVisibleCameraFace(die);
    if (visible?.value != null) return visible.value;
  }

  let bestScore = -Infinity;
  let bestFace = 0;
  const faces = _getFaceEntries(die);
  faces.forEach((face, i) => {
    const { score } = _scoreFaceForRead(die, face, worldQuat);
    if (score > bestScore) { bestScore = score; bestFace = i; }
  });

  return faces[bestFace]?.value ?? null;
}

/**
 * Detect the current top face (during animation — before settle).
 * Returns { face index, dot score, margin vs 2nd-best }.
 */
export function detectTopFace(die) {
  const worldQuat = new THREE.Quaternion(
    die.body.quaternion.x, die.body.quaternion.y,
    die.body.quaternion.z, die.body.quaternion.w
  );

  if (die?.type === 'd4') {
    const topPoint = _detectD4UpwardPoint(die, worldQuat);
    const topCentroidWorld = topPoint.topCentroidLocal.clone().applyQuaternion(worldQuat).add(
      new THREE.Vector3(die.body.position.x, die.body.position.y, die.body.position.z)
    );
    return {
      faceIndex: topPoint.faceIndex,
      dot: topPoint.dot,
      margin: topPoint.margin,
      secondDot: topPoint.secondDot,
      value: topPoint.value,
      oppositeFaceIndex: null,
      topCentroidLocal: topPoint.topCentroidLocal.clone(),
      topCentroidWorld,
      secondFaceIndex: null,
    };
  }

  if (die?.type === 'd10' || die?.type === 'd100') {
    const visible = _detectVisibleCameraFace(die);
    if (visible) return visible;
  }

  const faces = _getFaceEntries(die);
  let best = null;
  let second = null;
  faces.forEach((face, i) => {
    const { dot, centroidY, score } = _scoreFaceForRead(die, face, worldQuat);
    if (!best || score > best.score)       { second = best; best   = { i, dot, centroidY, score }; }
    else if (!second || score > second.score) { second = { i, dot, centroidY, score }; }
  });

  const bestFace = faces[best?.i ?? 0] ?? null;
  const secondFace = faces[second?.i ?? 0] ?? null;
  let topCentroidWorld = null;
  if (bestFace?.centroid) {
    topCentroidWorld = bestFace.centroid.clone()
      .applyQuaternion(worldQuat)
      .add(new THREE.Vector3(
        die.body.position.x,
        die.body.position.y,
        die.body.position.z
      ));
  }

  return {
    faceIndex: bestFace?.faceIndex ?? 0,
    dot:       best?.dot ?? -1,
    margin:    (best?.dot ?? 0) - (second?.dot ?? 0),
    secondDot: second?.dot ?? -1,
    value:     bestFace?.value ?? null,
    oppositeFaceIndex: bestFace?.oppositeFaceIndex ?? null,
    topCentroidLocal: bestFace?.centroid ? bestFace.centroid.clone() : null,
    topCentroidWorld,
    secondFaceIndex: secondFace?.faceIndex ?? null,
  };
}

/**
 * Validate that a die is resting on a valid face (not an edge or corner).
 * Returns true if the face alignment is valid, false if the die needs nudging.
 *
 * @param {Object} die   Die object from spawnDie()
 * @returns {boolean}
 */
export function validateFaceAlignment(die) {
  const detected = detectTopFace(die);
  return detected.dot >= MIN_FACE_DOT && detected.margin >= MIN_FACE_MARGIN;
}

/**
 * Apply a small corrective nudge to a die that settled on an edge/corner.
 * @param {Object} die
 */
export function nudgeToFace(die) {
  const { body } = die;
  if (body.sleepState === CANNON.Body.SLEEPING) body.wakeUp();
  // Stabilization-only: never perform an outcome-changing flip/pop.
  body.angularVelocity.set(
    body.angularVelocity.x * 0.35,
    body.angularVelocity.y * 0.2,
    body.angularVelocity.z * 0.35
  );
  body.velocity.set(body.velocity.x * 0.2, Math.min(body.velocity.y, NUDGE_LIFT_Y * 0.1), body.velocity.z * 0.2);
}

/**
 * Check if a die is settled (time-based, not frame-based).
 *
 * @param {Object} die         Die object
 * @param {number} now         performance.now()
 * @returns {boolean}
 */
export function isDieSettled(die, now) {
  const { body } = die;
  const isQuiet =
    body.velocity.length()        < SETTLE_SPEED_LINEAR &&
    body.angularVelocity.length() < SETTLE_SPEED_ANGULAR;

  if (isQuiet) {
    if (die.quietSince === null || die.quietSince === undefined) die.quietSince = now;
    return (now - die.quietSince) >= SETTLE_DURATION_MS;
  } else {
    die.quietSince = null;  // reset if it moved again (bounced)
    return false;
  }
}

/**
 * Stuck-die detection and recovery.
 *
 * A die is "stuck" if it has been alive (spawnedAt set) for longer than
 * STUCK_TIMEOUT_MS without reaching a settled state.  When detected the
 * die receives a small physically-believable upward + lateral + angular
 * impulse to free it.  After STUCK_MAX_RETRIES nudges the die is force-
 * settled at its current orientation to prevent infinite loops.
 *
 * Call once per frame for every unsettled die.
 *
 * @param {Object} die   Die object (must have .body, .spawnedAt, .stuckNudges)
 * @param {number} now   performance.now()
 * @returns {boolean}     true if the die was force-settled
 */
export function checkStuckDie(die, now) {
  if (die.settled) return false;

  const elapsed = now - die.spawnedAt;
  if (elapsed < STUCK_TIMEOUT_MS) return false;  // not stuck yet

  // Minimum 1.5 s between nudges to let physics settle after each kick
  if (now - die.lastNudgeAt < 1500) return false;

  const { body } = die;

  // If retries exhausted → force-settle at current position
  if (die.stuckNudges >= STUCK_MAX_RETRIES) {
    console.warn('[DiceFactory] force-settling stuck die after', STUCK_MAX_RETRIES, 'nudges');
    body.velocity.setZero();
    body.angularVelocity.setZero();
    body.sleep();
    return true;  // caller should mark as settled
  }

  // Apply corrective impulse: small upward lift + random lateral push + spin
  die.stuckNudges++;
  die.lastNudgeAt = now;
  die.quietSince  = null;  // reset settle timer

  // Wake body if sleeping
  if (body.sleepState === CANNON.Body.SLEEPING) body.wakeUp();

  const lateralX = (Math.random() - 0.5) * STUCK_NUDGE_LATERAL * 2;
  const lateralZ = (Math.random() - 0.5) * STUCK_NUDGE_LATERAL * 2;
  body.velocity.set(lateralX, STUCK_NUDGE_UP, lateralZ);
  body.angularVelocity.set(
    (Math.random() - 0.5) * STUCK_TORQUE,
    (Math.random() - 0.5) * STUCK_TORQUE,
    (Math.random() - 0.5) * STUCK_TORQUE
  );

  // Reset stuck timer so the die gets another full timeout window
  die.spawnedAt = now;

  console.debug(`[DiceFactory] nudged stuck ${die.type} (attempt ${die.stuckNudges}/${STUCK_MAX_RETRIES})`);
  return false;
}

/**
 * Apply settle pulse animation to a mesh (scale pop + emissive glint).
 * @param {THREE.Mesh} mesh
 */
export function playSettlePulse(mesh) {
  const t0   = performance.now();
  const dur  = 350;
  const base = mesh.scale.clone();
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];

  // Emissive glint on settle
  mats.forEach(m => { m.emissive?.setHex(0x3a9e7e); m.emissiveIntensity = 0.45; });
  setTimeout(() => mats.forEach(m => { if (m.emissive) m.emissiveIntensity = 0.28; }), 220);

  // Scale pulse
  (function tick(now) {
    const progress = Math.min((now - t0) / dur, 1);
    const pulse    = 1 + 0.09 * Math.sin(progress * Math.PI) * (1 - progress * 0.6);
    mesh.scale.copy(base).multiplyScalar(pulse);
    if (progress < 1) requestAnimationFrame(tick);
    else mesh.scale.copy(base);
  })(performance.now());
}

/**
 * Apply sweep impulse to all active dice and remove them after 1.2 s.
 * @param {Array}     activeDice  Array of die objects
 * @param {DiceWorld} diceWorld
 */
export function sweepExistingDice(activeDice, diceWorld) {
  activeDice.forEach(die => {
    sweepBody(die.body);
    // Remove from scene after 1.2 s — they'll have flown off screen
    setTimeout(() => {
      diceWorld.disposeGroup(die.mesh);
      world.removeBody(die.body);
    }, 1200);
  });
}

/**
 * Boundary rescue — if a die escapes the physics tray, pop it back.
 * @param {CANNON.Body} body
 */
export function rescueBody(body) {
  if (body.position.y < -2) {
    body.position.y  = 1.5;
    body.velocity.y  = Math.abs(body.velocity.y) * 0.4;
  }
  const bx = Math.abs(body.position.x);
  if (bx > 9.5) {
    body.position.x *= 9.5 / bx;
    body.velocity.x *= -0.35;
  }
  if (body.position.z > 8.5)  { body.position.z =  8.5; body.velocity.z *= -0.35; }
  if (body.position.z < -6.5) { body.position.z = -6.5; body.velocity.z *= -0.35; }
}

/** Export computeD100Result for consumer use */
export { computeD100Result };

/** Export face alignment constants for consumer use */
export { MAX_FACE_NUDGES };
