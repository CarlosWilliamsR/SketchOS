// Pure-function tests for the viewport-control helpers in viewport.js.
//
// No Canvas/WebGL required: these are deterministic math + array + formatting
// functions. The clipping-plane concat and camera preset positions are the
// acceptance criteria for the "array not scalar" and "preset positions" spec
// scenarios.

import { describe, it, expect } from 'vitest';
import * as THREE from 'three';
import {
  CLAY_COLOR,
  EDGE_COLOR,
  CLAY_ROUGHNESS,
  CLAY_METALNESS,
  CAMERA_PRESETS,
  EMPTY_METRIC,
  cameraPresetPosition,
  buildClippingPlanes,
  formatMetrics,
  countMeshStats,
} from './viewport.js';

describe('clay material constants', () => {
  it('defines the matte clay color and PBR roughness/metalness', () => {
    expect(CLAY_COLOR).toBe('#94a3b8');
    expect(CLAY_ROUGHNESS).toBe(0.85);
    expect(CLAY_METALNESS).toBe(0.0);
  });

  it('defines the edge-highlight stroke color', () => {
    expect(EDGE_COLOR).toBe('#60a5fa');
  });
});

describe('CAMERA_PRESETS', () => {
  it('declares the four view presets in order with human labels', () => {
    expect(CAMERA_PRESETS.map((p) => p.id)).toEqual([
      'topDown',
      'front',
      'side',
      'isometric',
    ]);
    expect(CAMERA_PRESETS.map((p) => p.label)).toEqual([
      'Top-Down Plan',
      'Front Elevation',
      'Side Elevation',
      'Isometric',
    ]);
  });
});

describe('cameraPresetPosition', () => {
  const center = new THREE.Vector3(5, 2, 3);
  const maxDim = 10;
  const distance = maxDim * 1.5; // 15

  it('Top-Down Plan places the camera directly above the model center', () => {
    const p = cameraPresetPosition('topDown', center, maxDim);
    expect(p.x).toBe(5);
    expect(p.y).toBe(2 + distance);
    expect(p.z).toBe(3);
  });

  it('Front Elevation places the camera along +Z', () => {
    const p = cameraPresetPosition('front', center, maxDim);
    expect(p.x).toBe(5);
    expect(p.y).toBe(2);
    expect(p.z).toBe(3 + distance);
  });

  it('Side Elevation places the camera along +X', () => {
    const p = cameraPresetPosition('side', center, maxDim);
    expect(p.x).toBe(5 + distance);
    expect(p.y).toBe(2);
    expect(p.z).toBe(3);
  });

  it('Isometric offsets every axis equally (45° corner)', () => {
    const p = cameraPresetPosition('isometric', center, maxDim);
    const k = distance / Math.sqrt(3);
    expect(p.x).toBeCloseTo(5 + k);
    expect(p.y).toBeCloseTo(2 + k);
    expect(p.z).toBeCloseTo(3 + k);
    expect(p.x - 5).toBeCloseTo(p.y - 2);
    expect(p.y - 2).toBeCloseTo(p.z - 3);
  });

  it('throws for an unknown preset id', () => {
    expect(() => cameraPresetPosition('nope', center, maxDim)).toThrow(
      /Unknown camera preset/,
    );
  });
});

describe('buildClippingPlanes (independent Z + Y toggles)', () => {
  const zPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 5);
  const yPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 2);

  it('returns both planes when Z and Y are both enabled', () => {
    const planes = buildClippingPlanes({ clipZ: true, clipY: true, zPlane, yPlane });
    expect(planes).toHaveLength(2);
    expect(planes[0]).toBe(zPlane);
    expect(planes[1]).toBe(yPlane);
  });

  it('returns only [zPlane] when only Z is enabled', () => {
    const planes = buildClippingPlanes({ clipZ: true, clipY: false, zPlane, yPlane });
    expect(planes).toEqual([zPlane]);
  });

  it('returns only [yPlane] when only Y is enabled', () => {
    const planes = buildClippingPlanes({ clipZ: false, clipY: true, zPlane, yPlane });
    expect(planes).toEqual([yPlane]);
  });

  it('returns an empty array when neither is enabled', () => {
    const planes = buildClippingPlanes({ clipZ: false, clipY: false, zPlane, yPlane });
    expect(planes).toEqual([]);
  });
});

describe('formatMetrics (empty vs zero distinction)', () => {
  it('renders the em-dash empty state when stats is null', () => {
    expect(formatMetrics(null)).toEqual({
      triangles: EMPTY_METRIC,
      objects: EMPTY_METRIC,
      aabbMs: EMPTY_METRIC,
    });
  });

  it('formats loaded stats with thousands separators and ms unit', () => {
    expect(formatMetrics({ triangles: 15420, objects: 47, aabbMs: 3.2 })).toEqual({
      triangles: '15,420',
      objects: '47',
      aabbMs: '3.2ms',
    });
  });

  it('distinguishes an explicit zero stats object from the empty state', () => {
    expect(formatMetrics({ triangles: 0, objects: 0, aabbMs: 0 })).toEqual({
      triangles: '0',
      objects: '0',
      aabbMs: '0ms',
    });
  });
});

describe('countMeshStats', () => {
  it('counts triangles and objects across a group of meshes', () => {
    const group = new THREE.Group();
    // A BoxGeometry is 12 triangles (6 faces × 2).
    group.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1)));
    group.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1)));

    expect(countMeshStats(group)).toEqual({ triangles: 24, objects: 2 });
  });

  it('returns zero stats for an empty group', () => {
    expect(countMeshStats(new THREE.Group())).toEqual({ triangles: 0, objects: 0 });
  });
});
