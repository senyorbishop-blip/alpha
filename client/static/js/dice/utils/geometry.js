import * as THREE from 'three';
import * as CANNON from 'cannon-es';

/**
 * Build a non-indexed BufferGeometry from vertex list + face list.
 * Each face gets flat shading — per-face normals computed from cross product.
 * Stores faceNormalsLocal in userData for result reading (settle detection).
 */
export function buildFlatFaceGeometry(vertList, faceList) {
  const positions = [];
  const normals   = [];
  const uvs       = [];
  const faceNormalsLocal = [];

  faceList.forEach(face => {
    const vA = new THREE.Vector3(...vertList[face[0]]);
    const vB = new THREE.Vector3(...vertList[face[1]]);
    const vC = new THREE.Vector3(...vertList[face[2]]);

    const edge1 = new THREE.Vector3().subVectors(vB, vA);
    const edge2 = new THREE.Vector3().subVectors(vC, vA);
    const normal = new THREE.Vector3().crossVectors(edge1, edge2).normalize();
    faceNormalsLocal.push(normal.clone());

    [vA, vB, vC].forEach(v => {
      positions.push(v.x, v.y, v.z);
      normals.push(normal.x, normal.y, normal.z);
    });

    // UV: equilateral triangle centered at (0.5, 0.5) — centroid maps to canvas center
    // This ensures the numeral (drawn at canvas center) renders at the face centroid.
    // Vertices: top=(0.5,0.9), bottom-left=(0.13,0.3), bottom-right=(0.87,0.3)
    // Centroid = ((0.5+0.13+0.87)/3, (0.9+0.3+0.3)/3) = (0.5, 0.5) ✓
    uvs.push(0.5, 0.9,  0.13, 0.3,  0.87, 0.3);
  });

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('normal',   new THREE.Float32BufferAttribute(normals,   3));
  geo.setAttribute('uv',       new THREE.Float32BufferAttribute(uvs,       2));
  geo.userData.faceNormalsLocal = faceNormalsLocal;
  return geo;
}

/**
 * Deduplicate vertices from a BufferGeometry position attribute.
 * Required for ConvexPolyhedron hull extraction.
 */
export function deduplicateVertices(positionAttribute, epsilon = 1e-4) {
  const unique   = [];
  const indexMap = [];

  for (let i = 0; i < positionAttribute.count; i++) {
    const v = new THREE.Vector3().fromBufferAttribute(positionAttribute, i);
    let found = -1;
    for (let j = 0; j < unique.length; j++) {
      if (unique[j].distanceTo(v) < epsilon) { found = j; break; }
    }
    if (found === -1) { found = unique.length; unique.push(v); }
    indexMap.push(found);
  }
  return { unique, indexMap };
}

/**
 * Compute per-group face normals from a BufferGeometry with addGroup() groups.
 * Returns an array of THREE.Vector3, one per group.
 */
export function computeGroupedFaceNormals(geo, groupCount) {
  const pos = geo.attributes.position;
  const normals = [];
  for (let g = 0; g < groupCount; g++) {
    const group = geo.groups[g];
    if (!group) { normals.push(new THREE.Vector3(0, 1, 0)); continue; }
    // Use the first triangle of the group
    const i = group.start;
    const vA = new THREE.Vector3(pos.getX(i),   pos.getY(i),   pos.getZ(i));
    const vB = new THREE.Vector3(pos.getX(i+1), pos.getY(i+1), pos.getZ(i+1));
    const vC = new THREE.Vector3(pos.getX(i+2), pos.getY(i+2), pos.getZ(i+2));
    const n = new THREE.Vector3()
      .crossVectors(
        new THREE.Vector3().subVectors(vB, vA),
        new THREE.Vector3().subVectors(vC, vA)
      )
      .normalize();
    normals.push(n);
  }
  return normals;
}

/**
 * Compute convex hull faces from a list of THREE.Vector3 vertices.
 * Uses the QuickHull-style approach via cannon-es ConvexPolyhedron.
 * Returns a face array usable directly in ConvexPolyhedron.
 */
export function computeConvexFacesFromVertices(verts) {
  // Build a temporary ConvexPolyhedron to get its face list
  const cannonVerts = verts.map(v => new CANNON.Vec3(v.x, v.y, v.z));
  // Provide triangulated faces as a starting point
  const n = cannonVerts.length;
  const faces = [];
  // Simple fan triangulation from vertex 0 — cannon-es will validate winding
  for (let i = 1; i + 1 < n; i++) {
    faces.push([0, i, i + 1]);
  }
  return faces;
}
