import * as CANNON from 'cannon-es';
import { buildFlatFaceGeometry } from '../utils/geometry.js';

/**
 * D4 — Regular Tetrahedron
 *
 * Vertices are normalised to unit circumradius (same as D8/D20) so the die
 * appears at the correct scale on screen.  The raw ±1 tetrahedron has
 * circumradius √3 ≈ 1.73, making it ~47 % larger than a D20 at the same
 * DIE_SCALES factor — that is what caused the "D4 looks close to the screen"
 * visual issue.
 *
 * Result reading uses the same unified face-normal approach as all other dice.
 * The face whose outward normal is most aligned with world +Y is the result.
 * See readTopFaceResult() in DiceFactory.js.
 */

// Normalisation factor: 1 / √3 so that each vertex sits exactly 1 unit from origin.
const R = 1 / Math.sqrt(3);

/**
 * Face values in geometry face order.
 *
 * For a physical tetrahedral d4, the rolled value is the number at the upward
 * point. When the die rests on a face, that upward point is the vertex opposite
 * the resting face. So each face value is derived from the omitted/opposite
 * vertex label rather than the numbers printed on that face.
 */
export const D4_FACE_VALUES = [4, 2, 3, 1];

export function createD4Geometry() {
  const vertices = [
    [ R,  R,  R],
    [-R, -R,  R],
    [-R,  R, -R],
    [ R, -R, -R],
  ];
  // Each face shows the 3 values NOT associated with the opposite vertex
  const faces = [
    [2, 1, 0],
    [0, 3, 2],
    [1, 3, 0],
    [2, 3, 1],
  ];
  const geo = buildFlatFaceGeometry(vertices, faces);
  // Each face = 1 triangle = 3 vertex slots — required for per-face material assignment
  geo.clearGroups();
  for (let i = 0; i < 4; i++) {
    geo.addGroup(i * 3, 3, i);
  }
  return geo;
}

export function createD4PhysicsShape() {
  const verts = [
    new CANNON.Vec3( R,  R,  R),
    new CANNON.Vec3(-R, -R,  R),
    new CANNON.Vec3(-R,  R, -R),
    new CANNON.Vec3( R, -R, -R),
  ];
  const faces = [[2,1,0],[0,3,2],[1,3,0],[2,3,1]];
  return new CANNON.ConvexPolyhedron({ vertices: verts, faces });
}



/**
 * Physical-style D4 face markings.
 *
 * Each triangular face shows the three point labels that meet at that face's
 * corners rather than a single centered numeral. This makes the visible faces
 * around an upward point all show the same value near that point, which is how
 * players expect a real tetrahedral d4 to read.
 *
 * The ordering mirrors the face vertex winding above so the numerals can be
 * placed near each triangle corner in a stable layout.
 */
export const D4_FACE_VERTEX_TRIPLETS = [
  [3, 2, 1], // face 0 (result 4)
  [1, 4, 3], // face 1 (result 2)
  [2, 4, 1], // face 2 (result 3)
  [3, 4, 2], // face 3 (result 1)
];


/** Local tetrahedron vertices for physical point-up result reading. */
export const D4_LOCAL_VERTICES = [
  { x:  R, y:  R, z:  R },
  { x: -R, y: -R, z:  R },
  { x: -R, y:  R, z: -R },
  { x:  R, y: -R, z: -R },
];

/** Physical point values by vertex index. */
export const D4_VERTEX_VALUES = [1, 2, 3, 4];
