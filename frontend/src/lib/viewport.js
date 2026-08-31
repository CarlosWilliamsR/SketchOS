// Pure viewport-control helpers for the CAD/BIM GeometryScene.
//
// Everything in this module is a plain function or constant — no React, no
// R3F, no WebGL — so it can be unit-tested in isolation under jsdom. The
// GeometryScene component composes these helpers with @react-three/fiber glue.

import * as THREE from 'three';

/** Matte clay body color for the architectural clay render. */
export const CLAY_COLOR = '#94a3b8';

/** Edge-highlight stroke color overlaid on clay geometry. */
export const EDGE_COLOR = '#60a5fa';

/** PBR roughness for the matte (non-glossy) clay look. */
export const CLAY_ROUGHNESS = 0.85;

/** PBR metalness — 0 keeps the material dielectric/matte. */
export const CLAY_METALNESS = 0.0;

/** Per-frame lerp factor for smooth camera preset transitions. */
export const CAMERA_LERP_FACTOR = 0.08;

/** Placeholder shown for a metric when no geometry has been loaded. */
export const EMPTY_METRIC = '\u2014';

/** The four view presets, in display order. */
export const CAMERA_PRESETS = [
  { id: 'topDown', label: 'Top-Down Plan' },
  { id: 'front', label: 'Front Elevation' },
  { id: 'side', label: 'Side Elevation' },
  { id: 'isometric', label: 'Isometric' },
];

/**
 * Camera target position for a view preset.
 *
 * The camera is offset from the model center along the preset's axis; the
 * controls target stays at `center` so the camera looks at the model.
 *
 * @param {string} presetId One of `topDown` | `front` | `side` | `isometric`.
 * @param {THREE.Vector3} center Model bounding-box center.
 * @param {number} maxDim Model's largest bounding-box dimension.
 * @returns {THREE.Vector3} Absolute camera position for the preset.
 */
export function cameraPresetPosition(presetId, center, maxDim) {
  const distance = maxDim * 1.5;
  const { x, y, z } = center;
  switch (presetId) {
    case 'topDown':
      return new THREE.Vector3(x, y + distance, z);
    case 'front':
      return new THREE.Vector3(x, y, z + distance);
    case 'side':
      return new THREE.Vector3(x + distance, y, z);
    case 'isometric': {
      // Equal offset on every axis → a true 45° isometric corner.
      const k = distance / Math.sqrt(3);
      return new THREE.Vector3(x + k, y + k, z + k);
    }
    default:
      throw new Error(`Unknown camera preset: ${presetId}`);
  }
}

/**
 * Build the active clipping-plane array from two independent toggles.
 *
 * Three.js clipping is per-material, so the planes are concatenated here and
 * then assigned to each material's `clippingPlanes`. The concat form keeps the
 * two axes fully independent (Z only, Y only, both, or neither) — never a
 * scalar `'Z' | 'Y' | null` toggle.
 *
 * @param {{clipZ: boolean, clipY: boolean, zPlane: THREE.Plane, yPlane: THREE.Plane}} params
 * @returns {THREE.Plane[]}
 */
export function buildClippingPlanes({ clipZ = false, clipY = false, zPlane, yPlane }) {
  return (clipZ ? [zPlane] : []).concat(clipY ? [yPlane] : []);
}

/**
 * Format a stats object for the HUD status bar.
 *
 * A falsy `stats` (no `setStats` call yet) yields the em-dash empty state for
 * every metric — distinct from an explicit zero stats object, which renders
 * numeric `0`. This is the fix for the prior verify failure where the HUD
 * showed "0" instead of "—" before geometry loaded.
 *
 * @param {{triangles: number, objects: number, aabbMs: number}|null} stats
 * @returns {{triangles: string, objects: string, aabbMs: string}}
 */
export function formatMetrics(stats) {
  if (!stats) {
    return { triangles: EMPTY_METRIC, objects: EMPTY_METRIC, aabbMs: EMPTY_METRIC };
  }
  return {
    triangles: Number(stats.triangles).toLocaleString('en-US'),
    objects: String(stats.objects),
    aabbMs: `${stats.aabbMs}ms`,
  };
}

/**
 * Count meshes and triangles in an object hierarchy.
 *
 * Triangle count derives from the indexed geometry (index.count / 3) or falls
 * back to the position attribute count for non-indexed geometry.
 *
 * @param {THREE.Object3D} root Root of the geometry hierarchy.
 * @returns {{triangles: number, objects: number}}
 */
export function countMeshStats(root) {
  let triangles = 0;
  let objects = 0;
  root.traverse((obj) => {
    if (!obj.isMesh) return;
    objects += 1;
    const geometry = obj.geometry;
    if (!geometry) return;
    const count = geometry.index
      ? geometry.index.count
      : geometry.getAttribute('position').count;
    triangles += Math.floor(count / 3);
  });
  return { triangles, objects };
}
