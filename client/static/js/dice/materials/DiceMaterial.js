import * as THREE from 'three';

/**
 * DiceMaterial — MeshPhysicalMaterial config for premium polished-resin dice.
 *
 * @param {THREE.Texture[]}  faceTextures  One texture per face
 * @param {Object}           theme
 * @returns {THREE.MeshPhysicalMaterial[]}
 */
export function createDiceMaterials(faceTextures, theme) {
  return faceTextures.map(tex => new THREE.MeshPhysicalMaterial({
    map:              tex,
    color:            '#ffffff',
    roughness:        theme.roughness  ?? 0.65,
    metalness:        theme.metalness  ?? 0.08,
    emissive:         theme.emissive   ?? '#090909',
    emissiveIntensity: 0.012,
    transparent:      (theme.opacity ?? 1) < 0.99,
    opacity:          theme.opacity    ?? 1,
    transmission:     theme.transmission ?? 0,
    thickness:        theme.transmission ? 1.4 : 0,
    clearcoat:        0.0,
    clearcoatRoughness: 0.94,
    sheen:            0.0,
    sheenColor:       new THREE.Color(theme.edgeColor ?? '#5a5f70'),
    specularIntensity: 0.0,
    specularColor:    new THREE.Color(theme.edgeColor ?? '#5a5f70'),
    iridescence:      0.0,
    envMapIntensity:  0.0,
    side:             THREE.DoubleSide,
    flatShading:      true,  // crisp polygon edges — CRITICAL for die aesthetic
  }));
}

/**
 * Create a single MeshPhysicalMaterial (no face texture) for die body.
 * Used when no per-face textures are needed.
 */
export function createSingleDiceMaterial(theme) {
  return new THREE.MeshPhysicalMaterial({
    color:            '#ffffff',
    roughness:        theme.roughness  ?? 0.65,
    metalness:        theme.metalness  ?? 0.08,
    emissive:         theme.emissive   ?? '#090909',
    emissiveIntensity: 0.012,
    transparent:      (theme.opacity ?? 1) < 0.99,
    opacity:          theme.opacity    ?? 1,
    transmission:     theme.transmission ?? 0,
    thickness:        theme.transmission ? 1.4 : 0,
    clearcoat:        0.0,
    clearcoatRoughness: 0.9,
    envMapIntensity:  0.0,
    side:             THREE.DoubleSide,
    flatShading:      true,
  });
}
