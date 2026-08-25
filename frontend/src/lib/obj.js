// Client-side OBJ analysis for the validator dashboard.
//
// The Go report exposes only a global AABB plus per-object measurements; it
// does not carry per-object bounding boxes. To color each wall green (pass) or
// red (violation) we re-read the uploaded OBJ text, group vertices by their
// `o`/`g` name, and build one THREE.Box3 per named object with
// `Box3.setFromPoints`.

import * as THREE from 'three';

/**
 * Group vertex positions by OBJ object (`o`) / group (`g`) name.
 *
 * A `v` line belongs to the most recently seen `o`/`g` name; vertices before
 * the first such line belong to the anonymous "" group. Malformed vertex lines
 * are skipped silently — the Go validator, not this helper, is the authority
 * on parse errors.
 *
 * @param {string} text Raw Wavefront OBJ text.
 * @returns {Map<string, THREE.Vector3[]>} Object name → vertex positions.
 */
export function groupVerticesByObject(text) {
  const groups = new Map();
  let current = '';

  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (line.startsWith('o ') || line.startsWith('g ')) {
      current = line.slice(2).trim();
      if (!groups.has(current)) groups.set(current, []);
      continue;
    }
    if (!line.startsWith('v ')) continue;

    const parts = line.slice(2).trim().split(/\s+/);
    const x = Number.parseFloat(parts[0]);
    const y = Number.parseFloat(parts[1]);
    const z = Number.parseFloat(parts[2]);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      continue;
    }
    if (!groups.has(current)) groups.set(current, []);
    groups.get(current).push(new THREE.Vector3(x, y, z));
  }

  return groups;
}

/**
 * Compute one bounding box per named object.
 *
 * Vertices are grouped by `o`/`g` name and each named group becomes a
 * THREE.Box3 via `Box3.setFromPoints`. When the OBJ has no object names at
 * all, the result falls back to a single box built from the report's global
 * `aabb` (Y-up maps directly to `Box3`; no axis swap). A missing/empty report
 * yields an empty array.
 *
 * @param {string} text Raw Wavefront OBJ text.
 * @param {{aabb?: {min?: {x:number,y:number,z:number}, max?: {x:number,y:number,z:number}}}} report
 * @returns {{name: (string|null), box: THREE.Box3}[]}
 */
export function computePerObjectAABBs(text, report) {
  const groups = groupVerticesByObject(text);
  const named = [...groups.entries()].filter(
    ([name, vertices]) => name !== '' && vertices.length > 0,
  );

  if (named.length === 0) {
    const aabb = report?.aabb;
    if (aabb?.min && aabb?.max) {
      return [
        {
          name: null,
          box: new THREE.Box3(
            new THREE.Vector3(aabb.min.x, aabb.min.y, aabb.min.z),
            new THREE.Vector3(aabb.max.x, aabb.max.y, aabb.max.z),
          ),
        },
      ];
    }
    return [];
  }

  return named.map(([name, vertices]) => ({
    name,
    box: new THREE.Box3().setFromPoints(vertices),
  }));
}

/** Overlay color for a passing object (no matching violation). */
export const PASS_COLOR = '#2e7d32';

/** Overlay color for an object that matches a reported violation. */
export const VIOLATION_COLOR = '#c62828';

/**
 * Map an AABB box to its overlay color.
 *
 * A named box is red when its name matches a reported violation, green
 * otherwise. The anonymous fallback box (`name === null`) has no name to match,
 * so it is red when ANY object violates and green when the report is clean.
 *
 * @param {(string|null)} name Object name, or null for the global fallback box.
 * @param {Set<string>} violatingObjects Names of objects with violations.
 * @returns {string} VIOLATION_COLOR or PASS_COLOR.
 */
export function colorForBox(name, violatingObjects) {
  const isViolation =
    name === null ? violatingObjects.size > 0 : violatingObjects.has(name);
  return isViolation ? VIOLATION_COLOR : PASS_COLOR;
}
