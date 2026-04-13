import * as CANNON from 'cannon-es';

/**
 * PhysicsWorld — cannon-es world setup.
 *
 * Key choices vs original:
 * - SAPBroadphase (not NaiveBroadphase which is O(n²))
 * - Three separate contact materials (dice/floor/wall) for realistic feel
 * - Time-based physics step, not frame-counted
 */

export const world = new CANNON.World();
world.gravity.set(0, -32, 0);           // slightly heavier gravity = faster, table-like settle
world.broadphase   = new CANNON.SAPBroadphase(world);  // NOT NaiveBroadphase
world.allowSleep   = true;
world.solver.iterations = 12;           // balanced accuracy/perf; scaled further per pool size
let currentMaxSubsteps = 3;

// Three separate materials — different friction/restitution per surface type
export const diceMaterial  = new CANNON.Material('dice');
export const floorMaterial = new CANNON.Material('floor');
export const wallMaterial  = new CANNON.Material('wall');

world.addContactMaterial(new CANNON.ContactMaterial(diceMaterial, floorMaterial, {
  friction: 0.62, restitution: 0.14,  // floor: grounded settle closer to felt/wood tabletop
}));
world.addContactMaterial(new CANNON.ContactMaterial(diceMaterial, wallMaterial, {
  friction: 0.30, restitution: 0.24,  // walls: enough liveliness without arcade pinball rebounds
}));
world.addContactMaterial(new CANNON.ContactMaterial(diceMaterial, diceMaterial, {
  friction: 0.52, restitution: 0.16,  // dice-to-dice: weighty impacts, less endless jitter
}));

// ── Wall + floor bodies — sized from actual camera frustum ────────────

/**
 * Build/rebuild invisible boundary bodies from camera frustum dimensions.
 * Called on init and on window resize.
 * @param {THREE.PerspectiveCamera} camera
 */
export function buildWalls(camera) {
  // Remove old walls if rebuilding on resize
  world.bodies
    .filter(b => b._isBoundary)
    .forEach(b => world.removeBody(b));

  const fov   = camera.fov * (Math.PI / 180);
  const dist  = camera.position.y;
  const halfH = Math.tan(fov / 2) * dist;
  const halfW = halfH * camera.aspect;
  const T = 2;    // wall thickness
  const H = 25;   // wall height (well above any spawn point)

  const boundaries = [
    // [position,                                 halfExtents                         ]
    [new CANNON.Vec3(0,          H/2, -(halfH+T/2)), new CANNON.Vec3(halfW+T, H/2, T/2)   ],  // back
    [new CANNON.Vec3(0,          H/2,  (halfH+T/2)), new CANNON.Vec3(halfW+T, H/2, T/2)   ],  // front
    [new CANNON.Vec3(-(halfW+T/2), H/2,  0         ), new CANNON.Vec3(T/2, H/2, halfH+T)  ],  // left
    [new CANNON.Vec3( (halfW+T/2), H/2,  0         ), new CANNON.Vec3(T/2, H/2, halfH+T)  ],  // right
    [new CANNON.Vec3(0,          -0.5,  0           ), new CANNON.Vec3(halfW+T, 0.5, halfH+T)],  // floor
  ];

  boundaries.forEach(([pos, half], i) => {
    const body = new CANNON.Body({
      mass:     0,
      material: i === 4 ? floorMaterial : wallMaterial,
    });
    body.addShape(new CANNON.Box(half));
    body.position.copy(pos);
    body._isBoundary = true;  // flag for cleanup on resize
    world.addBody(body);
  });
}

// ── Fixed-step time-based physics advancement ─────────────────────────
const FIXED_STEP   = 1 / 60;
let   lastStepTime = null;

/**
 * Advance the physics simulation one tick.
 * Uses wall-clock time — safe across tab-backgrounding and variable framerates.
 * @param {number} now  performance.now() timestamp
 */
export function stepPhysics(now) {
  if (lastStepTime !== null) {
    // Cap dt to prevent spiral-of-death when tab is backgrounded
    const dt = Math.min((now - lastStepTime) / 1000, 0.05);
    world.step(FIXED_STEP, dt, currentMaxSubsteps);
  }
  lastStepTime = now;
}

/** Reset physics step timer (call when starting a new roll) */
export function resetStepTimer() {
  lastStepTime = null;
}


export function setPhysicsBudgetForDiceCount(count) {
  const clamped = Math.max(1, Math.min(Number(count) || 1, 20));
  if (clamped >= 16) {
    world.solver.iterations = 1;
    currentMaxSubsteps = 1;
  } else if (clamped >= 12) {
    world.solver.iterations = 1;
    currentMaxSubsteps = 1;
  } else if (clamped >= 8) {
    world.solver.iterations = 2;
    currentMaxSubsteps = 1;
  } else if (clamped >= 5) {
    world.solver.iterations = 4;
    currentMaxSubsteps = 1;
  } else {
    world.solver.iterations = 8;
    currentMaxSubsteps = 2;
  }
}
