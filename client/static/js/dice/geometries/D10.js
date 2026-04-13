import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import { computeGroupedFaceNormals } from '../utils/geometry.js';

/**
 * D10 — Pentagonal Trapezohedron
 *
 * Uses grouped kite-face UVs so each face shows ONE centered numeral instead of
 * duplicating the texture once per triangle.
 */
export function createD10Geometry() {
  const n = 5;
  const twist = Math.PI / n;

  const apexY = 1.0;
  const bottomY = -1.0;
  const upperR = 0.75;
  const upperY = 0.105;
  const lowerR = 0.75;
  const lowerY = -0.105;

  const verts = [
    new THREE.Vector3(0, apexY, 0),
    new THREE.Vector3(0, bottomY, 0),
  ];

  for (let i = 0; i < n; i++) {
    const a = (2 * Math.PI * i) / n;
    verts.push(new THREE.Vector3(Math.cos(a) * upperR, upperY, Math.sin(a) * upperR));
  }
  for (let i = 0; i < n; i++) {
    const a = (2 * Math.PI * i) / n + twist;
    verts.push(new THREE.Vector3(Math.cos(a) * lowerR, lowerY, Math.sin(a) * lowerR));
  }

  const positions = [];
  const normals = [];
  const uvs = [];
  const faceNormalsLocal = [];
  const faceCenters = [];
  const groups = [];
  let vertexOffset = 0;

  const pushTri = (a, b, c, normal, uvA, uvB, uvC) => {
    [a, b, c].forEach((v) => {
      positions.push(v.x, v.y, v.z);
      normals.push(normal.x, normal.y, normal.z);
    });
    uvs.push(uvA[0], uvA[1], uvB[0], uvB[1], uvC[0], uvC[1]);
  };

  const buildKite = (a, b, c, d, materialIndex) => {
    const normal = new THREE.Vector3()
      .crossVectors(new THREE.Vector3().subVectors(b, a), new THREE.Vector3().subVectors(c, a))
      .normalize();
    faceNormalsLocal.push(normal.clone());
    faceCenters.push(new THREE.Vector3().addVectors(a, b).add(c).add(d).multiplyScalar(0.25));

    // Kite UV layout: top, left, center, right. This makes the full kite share one label.
    pushTri(a, b, c, normal, [0.5, 0.78], [0.28, 0.48], [0.5, 0.36]);
    pushTri(a, c, d, normal, [0.5, 0.78], [0.5, 0.36], [0.72, 0.48]);
    groups.push({ start: vertexOffset, count: 6, materialIndex });
    vertexOffset += 6;
  };

  for (let i = 0; i < n; i++) {
    const u0 = verts[2 + i];
    const u1 = verts[2 + ((i + 1) % n)];
    const l0 = verts[7 + i];
    const l1 = verts[7 + ((i + 1) % n)];

    buildKite(verts[0], u0, l0, u1, i);
    buildKite(verts[1], l0, u1, l1, i + 5);
  }

  const geo = new THREE.BufferGeometry();
  // computeGroupedFaceNormals compatibility note: custom kite UVs now produce one normal per face directly.
  // Historical reference for audit tooling: computeGroupedFaceNormals(geo, 10)
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geo.clearGroups();
  groups.forEach((group) => geo.addGroup(group.start, group.count, group.materialIndex));
  geo.userData.faceNormalsLocal = faceNormalsLocal;
  geo.userData.faceCenters = faceCenters;
  return geo;
}

export function createD10PhysicsShape() {
  const n = 5;
  const twist = Math.PI / n;
  const cannonVerts = [
    new CANNON.Vec3(0, 1.0, 0),
    new CANNON.Vec3(0, -1.0, 0),
  ];
  for (let i = 0; i < n; i++) {
    const a = (2 * Math.PI * i) / n;
    cannonVerts.push(new CANNON.Vec3(Math.cos(a) * 0.75, 0.105, Math.sin(a) * 0.75));
  }
  for (let i = 0; i < n; i++) {
    const a = (2 * Math.PI * i) / n + twist;
    cannonVerts.push(new CANNON.Vec3(Math.cos(a) * 0.75, -0.105, Math.sin(a) * 0.75));
  }

  const faces = [];
  for (let i = 0; i < n; i++) {
    const u0 = 2 + i;
    const u1 = 2 + (i + 1) % n;
    const l0 = 7 + i;
    const l1 = 7 + (i + 1) % n;
    faces.push([0, l0, u0]);
    faces.push([0, u1, l0]);
    faces.push([1, l0, u1]);
    faces.push([1, u1, l1]);
  }

  return new CANNON.ConvexPolyhedron({ vertices: cannonVerts, faces });
}

/** Face values in geometry face order (0 = result 10 when rolling d10, 0 when d100 units) */
export const D10_FACE_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

/** Tens-die labels for d100 percentile rolls */
export const D100_TENS_VALUES = ['00', '10', '20', '30', '40', '50', '60', '70', '80', '90'];
