import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import { buildFlatFaceGeometry } from '../utils/geometry.js';

/**
 * D8 — Regular Octahedron
 */
export function createD8Geometry() {
  const r = 1;
  const vertices = [
    [ r, 0, 0], [-r, 0, 0],
    [ 0, r, 0], [ 0,-r, 0],
    [ 0, 0, r], [ 0, 0,-r],
  ];
  const faces = [
    [0,2,4],[0,4,3],[0,3,5],[0,5,2],
    [1,2,5],[1,5,3],[1,3,4],[1,4,2],
  ];
  const geo = buildFlatFaceGeometry(vertices, faces);
  // Each face = 1 triangle = 3 vertex slots — required for per-face material assignment
  geo.clearGroups();
  for (let i = 0; i < 8; i++) {
    geo.addGroup(i * 3, 3, i);
  }
  return geo;
}

export function createD8PhysicsShape() {
  const verts = [
    new CANNON.Vec3( 1, 0, 0), new CANNON.Vec3(-1, 0, 0),
    new CANNON.Vec3( 0, 1, 0), new CANNON.Vec3( 0,-1, 0),
    new CANNON.Vec3( 0, 0, 1), new CANNON.Vec3( 0, 0,-1),
  ];
  const faces = [
    [0,2,4],[0,4,3],[0,3,5],[0,5,2],
    [1,2,5],[1,5,3],[1,3,4],[1,4,2],
  ];
  return new CANNON.ConvexPolyhedron({ vertices: verts, faces });
}

/** Face values in geometry face order. Verified against standard d8 winding. */
export const D8_FACE_VALUES = [1, 2, 3, 4, 8, 7, 6, 5];
