import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import { deduplicateVertices } from '../utils/geometry.js';

/**
 * D20 — Regular Icosahedron (20 triangular faces)
 *
 * Canonical face definition table notes:
 * - We derive face normals + centroids from actual geometry triangles.
 * - We assign labels from a single value list, then compute opposite faces by
 *   centroid antipodal matching (most-negative centroid dot).
 * - The resulting table is exported and reused by geometry/material assignment,
 *   top-face detection, snap-to-result, and post-settle reading.
 */

const D20_VALUE_ORDER = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  20, 19, 18, 17, 16, 15, 14, 13, 12, 11,
];

function buildCanonicalD20FaceTable() {
  const raw = new THREE.IcosahedronGeometry(1, 0).toNonIndexed();
  const pos = raw.attributes.position;
  const faces = [];

  for (let i = 0; i < 20; i++) {
    const a = new THREE.Vector3(pos.getX(i * 3), pos.getY(i * 3), pos.getZ(i * 3));
    const b = new THREE.Vector3(pos.getX(i * 3 + 1), pos.getY(i * 3 + 1), pos.getZ(i * 3 + 1));
    const c = new THREE.Vector3(pos.getX(i * 3 + 2), pos.getY(i * 3 + 2), pos.getZ(i * 3 + 2));

    const centroid = a.clone().add(b).add(c).multiplyScalar(1 / 3).normalize();
    const normal = b.clone().sub(a).cross(c.clone().sub(a)).normalize();
    if (normal.dot(centroid) < 0) normal.multiplyScalar(-1);

    faces.push({
      faceIndex: i,
      value: D20_VALUE_ORDER[i],
      label: String(D20_VALUE_ORDER[i]),
      normal,
      centroid,
      oppositeFaceIndex: -1,
    });
  }

  for (const face of faces) {
    let bestIdx = -1;
    let bestDot = Infinity;
    for (const other of faces) {
      if (other.faceIndex === face.faceIndex) continue;
      const d = face.centroid.dot(other.centroid);
      if (d < bestDot) {
        bestDot = d;
        bestIdx = other.faceIndex;
      }
    }
    face.oppositeFaceIndex = bestIdx;
  }

  raw.dispose();
  return Object.freeze(faces.map(f => Object.freeze(f)));
}

export const D20_CANONICAL_FACES = buildCanonicalD20FaceTable();

export function createD20Geometry() {
  const base = new THREE.IcosahedronGeometry(1, 0);
  const geo  = base.toNonIndexed();  // 20 faces × 3 verts = 60 entries exactly

  const uvArray = new Float32Array(60 * 2);
  for (let f = 0; f < 20; f++) {
    const b = f * 6;
    uvArray[b]     = 0.5;  uvArray[b + 1] = 0.9;
    uvArray[b + 2] = 0.13; uvArray[b + 3] = 0.3;
    uvArray[b + 4] = 0.87; uvArray[b + 5] = 0.3;
  }
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvArray, 2));

  geo.clearGroups();
  for (const face of D20_CANONICAL_FACES) {
    geo.addGroup(face.faceIndex * 3, 3, face.faceIndex);
  }

  geo.userData.faceNormalsLocal = D20_CANONICAL_FACES.map(f => f.normal.clone());
  geo.userData.faceCenters = D20_CANONICAL_FACES.map(f => f.centroid.clone());
  geo.userData.canonicalFaces = D20_CANONICAL_FACES;

  base.dispose();
  return geo;
}

export function createD20PhysicsShape() {
  const base = new THREE.IcosahedronGeometry(1, 0);
  const { unique } = deduplicateVertices(base.attributes.position);
  base.dispose();
  const verts = unique.map(v => new CANNON.Vec3(v.x, v.y, v.z));
  const full = new THREE.IcosahedronGeometry(1, 0).toNonIndexed();
  const pos  = full.attributes.position;
  const seen = new Map();
  const keyFor = (x, y, z) => `${x.toFixed(5)}|${y.toFixed(5)}|${z.toFixed(5)}`;
  unique.forEach((v, i) => seen.set(keyFor(v.x, v.y, v.z), i));

  const faces = [];
  for (let i = 0; i < pos.count; i += 3) {
    const tri = [];
    for (let j = 0; j < 3; j++) {
      const x = pos.getX(i + j), y = pos.getY(i + j), z = pos.getZ(i + j);
      tri.push(seen.get(keyFor(x, y, z)) ?? 0);
    }
    if (tri[0] !== tri[1] && tri[1] !== tri[2] && tri[0] !== tri[2]) {
      faces.push(tri);
    }
  }
  full.dispose();
  return new CANNON.ConvexPolyhedron({ vertices: verts, faces });
}

/** Canonical D20 face values — one entry per face, covering every integer 1–20. */
export const D20_FACE_VALUES = [...D20_VALUE_ORDER];
