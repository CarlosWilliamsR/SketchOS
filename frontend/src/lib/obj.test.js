// Unit tests for the pure OBJ-analysis helpers in obj.js.
//
// No browser / DOM / WebGL required: THREE.Vector3 and THREE.Box3 are plain
// math objects that work fine under Vitest's Node environment.

import { describe, it, expect } from 'vitest';
import {
  groupVerticesByObject,
  computePerObjectAABBs,
  colorForBox,
  PASS_COLOR,
  VIOLATION_COLOR,
} from './obj.js';

describe('groupVerticesByObject', () => {
  it('groups vertices under the most recent o/g name', () => {
    const text = [
      'v 0 0 0',
      'v 1 0 0',
      'o wall_1',
      'v 0 0 0',
      'v 0 3 0',
      'g wall_2',
      'v 5 5 5',
    ].join('\n');

    const groups = groupVerticesByObject(text);

    expect(groups.size).toBe(3);
    expect(groups.get('').map((v) => v.toArray())).toEqual([
      [0, 0, 0],
      [1, 0, 0],
    ]);
    expect(groups.get('wall_1').map((v) => v.toArray())).toEqual([
      [0, 0, 0],
      [0, 3, 0],
    ]);
    expect(groups.get('wall_2').map((v) => v.toArray())).toEqual([[5, 5, 5]]);
  });

  it('skips malformed vertex lines (non-finite or missing coordinates)', () => {
    const text = 'v 1 2\nv a b c\no wall_1\nv 0 0 0';

    const groups = groupVerticesByObject(text);

    // The two malformed lines belong to the anonymous "" group but are skipped,
    // so that group is never created.
    expect(groups.has('')).toBe(false);
    expect(groups.get('wall_1')).toHaveLength(1);
    expect(groups.get('wall_1')[0].toArray()).toEqual([0, 0, 0]);
  });

  it('ignores non-vertex lines (faces, texture coords, normals, comments)', () => {
    const text = [
      '# a comment',
      'v 1 1 1',
      'vt 0.5 0.5',
      'vn 0 0 1',
      'f 1 2 3',
    ].join('\n');

    const groups = groupVerticesByObject(text);

    expect(groups.size).toBe(1);
    expect(groups.get('')).toHaveLength(1);
  });
});

describe('computePerObjectAABBs', () => {
  it('builds one box per named object from its vertices', () => {
    const text = [
      'o wall_1',
      'v 0 0 0',
      'v 0 3 0',
      'v 10 3 0',
      'v 10 0 0',
      'o wall_2',
      'v 0 0 0',
      'v 0 2 0',
      'v 5 2 0',
    ].join('\n');

    const boxes = computePerObjectAABBs(text, {});

    expect(boxes).toHaveLength(2);
    const wall1 = boxes.find((b) => b.name === 'wall_1');
    const wall2 = boxes.find((b) => b.name === 'wall_2');
    expect(wall1.box.min.toArray()).toEqual([0, 0, 0]);
    expect(wall1.box.max.toArray()).toEqual([10, 3, 0]);
    expect(wall2.box.min.toArray()).toEqual([0, 0, 0]);
    expect(wall2.box.max.toArray()).toEqual([5, 2, 0]);
  });

  it('falls back to the report global aabb when the OBJ has no names', () => {
    const text = 'v 0 0 0\nv 1 0 0\nv 1 1 0';
    const report = {
      aabb: {
        min: { x: 0, y: 0, z: 0 },
        max: { x: 10.25, y: 3, z: 5 },
      },
    };

    const boxes = computePerObjectAABBs(text, report);

    expect(boxes).toHaveLength(1);
    expect(boxes[0].name).toBeNull();
    expect(boxes[0].box.min.toArray()).toEqual([0, 0, 0]);
    expect(boxes[0].box.max.toArray()).toEqual([10.25, 3, 5]);
  });

  it('returns an empty array when no names and no global aabb exist', () => {
    expect(computePerObjectAABBs('v 0 0 0', {})).toEqual([]);
    expect(computePerObjectAABBs('', undefined)).toEqual([]);
  });
});

describe('colorForBox (violation → color mapping)', () => {
  it('colors a named object red when it matches a violation', () => {
    expect(colorForBox('wall_1', new Set(['wall_1', 'wall_3']))).toBe(
      VIOLATION_COLOR,
    );
  });

  it('colors a named object green when it has no matching violation', () => {
    expect(colorForBox('wall_2', new Set(['wall_1']))).toBe(PASS_COLOR);
  });

  it('colors the anonymous fallback box red when any object violates', () => {
    expect(colorForBox(null, new Set(['wall_1']))).toBe(VIOLATION_COLOR);
  });

  it('colors the anonymous fallback box green when the report is clean', () => {
    expect(colorForBox(null, new Set())).toBe(PASS_COLOR);
  });

  it('exposes distinct, stable pass and violation colors', () => {
    expect(PASS_COLOR).not.toBe(VIOLATION_COLOR);
    expect(PASS_COLOR).toBe('#2e7d32');
    expect(VIOLATION_COLOR).toBe('#c62828');
  });
});
