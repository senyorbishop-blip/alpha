import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import { deduplicateVertices, computeGroupedFaceNormals } from '../utils/geometry.js';

/**
 * D12 — Regular Dodecahedron (12 pentagonal faces)
 * Three.js DodecahedronGeometry triangulates each pentagon into 3 triangles.
 * We group every 3 triangles (9 vertex entries) as one material face.
 */
export function createD12Geometry() {
  const base = new THREE.DodecahedronGeometry(1, 0);
  const geo  = base.toNonIndexed();  // required for per-face flat shading + textures
  const pos  = geo.attributes.position;

  // Override spherical UVs: DodecahedronGeometry generates spherical-projection UVs
  // which do NOT center at (0.5, 0.5) per face.  Per-face material textures draw
  // the numeral at canvas center, so we project each pentagon's vertices onto a 2D
  // tangent frame centered at the face centroid, then map to UV space with the
  // centroid at (0.5, 0.5).
  const VERTS_PER_FACE = 9;  // 3 triangles × 3 verts per triangulated pentagon
  const uvArray = new Float32Array(pos.count * 2);

  for (let f = 0; f < 12; f++) {
    const start = f * VERTS_PER_FACE;

    // 1. Compute face centroid
    let cx = 0, cy = 0, cz = 0;
    for (let v = 0; v < VERTS_PER_FACE; v++) {
      cx += pos.getX(start + v);
      cy += pos.getY(start + v);
      cz += pos.getZ(start + v);
    }
    cx /= VERTS_PER_FACE; cy /= VERTS_PER_FACE; cz /= VERTS_PER_FACE;

    // 2. Compute face normal from first triangle
    const ax = pos.getX(start),     ay = pos.getY(start),     az = pos.getZ(start);
    const bx = pos.getX(start + 1), by = pos.getY(start + 1), bz = pos.getZ(start + 1);
    const cx2 = pos.getX(start + 2), cy2 = pos.getY(start + 2), cz2 = pos.getZ(start + 2);
    const e1x = bx - ax, e1y = by - ay, e1z = bz - az;
    const e2x = cx2 - ax, e2y = cy2 - ay, e2z = cz2 - az;
    let nx = e1y * e2z - e1z * e2y;
    let ny = e1z * e2x - e1x * e2z;
    let nz = e1x * e2y - e1y * e2x;
    const nLen = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
    nx /= nLen; ny /= nLen; nz /= nLen;

    // 3. Build 2D tangent frame on face plane
    let t1x = ax - cx, t1y = ay - cy, t1z = az - cz;
    const dot1 = t1x * nx + t1y * ny + t1z * nz;
    t1x -= dot1 * nx; t1y -= dot1 * ny; t1z -= dot1 * nz;
    const t1Len = Math.sqrt(t1x * t1x + t1y * t1y + t1z * t1z) || 1;
    t1x /= t1Len; t1y /= t1Len; t1z /= t1Len;
    const t2x = ny * t1z - nz * t1y;
    const t2y = nz * t1x - nx * t1z;
    const t2z = nx * t1y - ny * t1x;

    // 4. Find max projection extent for normalization
    let maxExt = 0;
    for (let v = 0; v < VERTS_PER_FACE; v++) {
      const dx = pos.getX(start + v) - cx;
      const dy = pos.getY(start + v) - cy;
      const dz = pos.getZ(start + v) - cz;
      const u = dx * t1x + dy * t1y + dz * t1z;
      const w = dx * t2x + dy * t2y + dz * t2z;
      maxExt = Math.max(maxExt, Math.abs(u), Math.abs(w));
    }

    // 5. Map to UV space centered at (0.5, 0.5) with margin
    const scale = 0.42 / Math.max(maxExt, 1e-6);
    for (let v = 0; v < VERTS_PER_FACE; v++) {
      const dx = pos.getX(start + v) - cx;
      const dy = pos.getY(start + v) - cy;
      const dz = pos.getZ(start + v) - cz;
      uvArray[(start + v) * 2]     = 0.5 + (dx * t1x + dy * t1y + dz * t1z) * scale;
      uvArray[(start + v) * 2 + 1] = 0.5 + (dx * t2x + dy * t2y + dz * t2z) * scale;
    }
  }

  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvArray, 2));

  geo.clearGroups();
  for (let i = 0; i < 12; i++) {
    geo.addGroup(i * 9, 9, i);  // 9 position entries per triangulated pentagon
  }
  geo.userData.faceNormalsLocal = computeGroupedFaceNormals(geo, 12);
  base.dispose();
  return geo;
}

export function createD12PhysicsShape() {
  const base = new THREE.DodecahedronGeometry(1, 0);
  const geo  = base.toNonIndexed();
  const pos  = geo.attributes.position;
  const { unique, indexMap } = deduplicateVertices(pos);
  base.dispose();

  const verts = unique.map(v => new CANNON.Vec3(v.x, v.y, v.z));

  // Build 12 pentagonal faces (not 36 triangles).
  // DodecahedronGeometry triangulates each pentagon as a fan: A-B-C, A-C-D, A-D-E.
  // We collect unique vertex indices per group of 9 vertex entries (3 tri × 3 verts)
  // in insertion order, which preserves the correct CCW winding from the fan.
  const faces = [];
  for (let f = 0; f < 12; f++) {
    const start = f * 9;  // 9 vertex entries per pentagon
    const ordered = [];
    const seen = new Set();
    for (let v = 0; v < 9; v++) {
      const idx = indexMap[start + v];
      if (!seen.has(idx)) {
        seen.add(idx);
        ordered.push(idx);
      }
    }
    faces.push(ordered);
  }

  geo.dispose();
  return new CANNON.ConvexPolyhedron({ vertices: verts, faces });
}

/** Face values in geometry group order. Standard d12 values 1–12. */
export const D12_FACE_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
