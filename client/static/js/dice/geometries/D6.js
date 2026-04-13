import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

/**
 * D6 — Rounded Cube
 * Uses RoundedBoxGeometry for a premium polished-resin look.
 * Three.js face order: +X=right, -X=left, +Y=top, -Y=bottom, +Z=front, -Z=back
 * Opposite faces sum to 7.
 */
export function createD6Geometry() {
  return new RoundedBoxGeometry(1.12, 1.12, 1.12, 4, 0.12);
}

export function createD6PhysicsShape() {
  return new CANNON.Box(new CANNON.Vec3(0.56, 0.56, 0.56));
}

/**
 * Face value lookup — Three.js BoxGeometry / RoundedBoxGeometry face order.
 * Index corresponds to material group index (0=+X, 1=-X, 2=+Y, 3=-Y, 4=+Z, 5=-Z).
 */
export const D6_FACE_VALUES = [2, 5, 1, 6, 3, 4];

/**
 * Face normals in local space — matches RoundedBoxGeometry material group order.
 */
export const D6_FACE_NORMALS = [
  new THREE.Vector3( 1,  0,  0),  // +X  → 2
  new THREE.Vector3(-1,  0,  0),  // -X  → 5
  new THREE.Vector3( 0,  1,  0),  // +Y  → 1 (top)
  new THREE.Vector3( 0, -1,  0),  // -Y  → 6 (bottom)
  new THREE.Vector3( 0,  0,  1),  // +Z  → 3
  new THREE.Vector3( 0,  0, -1),  // -Z  → 4
];

/**
 * Face center positions in local space (center of each face at half-size).
 */
export const D6_FACE_CENTERS = [
  new THREE.Vector3( 0.61,  0,     0  ),
  new THREE.Vector3(-0.61,  0,     0  ),
  new THREE.Vector3( 0,     0.61,  0  ),
  new THREE.Vector3( 0,    -0.61,  0  ),
  new THREE.Vector3( 0,     0,     0.61),
  new THREE.Vector3( 0,     0,    -0.61),
];
