// GeometryScene component tests — Canvas and drei are mocked so the HUD,
// camera presets, clip toggles, status bar, and pointer-events isolation can
// be asserted in jsdom without WebGL.
//
// The heavy math (preset positions, clip-plane concat) is unit-tested in
// viewport.test.js; here we verify the component renders the controls and the
// empty-state HUD, and isolates pointer events.

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as THREE from 'three';
import GeometryScene from './GeometryScene.jsx';
import { EMPTY_METRIC } from '../lib/viewport.js';

// Hoisted state so the OBJLoader mock can return a controllable group at
// parse time (parse runs during render, long after the hoisted mock factory).
const mockState = vi.hoisted(() => ({ objGroup: null }));

vi.mock('three/examples/jsm/loaders/OBJLoader.js', () => ({
  OBJLoader: class {
    parse() {
      return mockState.objGroup;
    }
  },
}));

vi.mock('@react-three/fiber', () => {
  const React = require('react');
  const position = {
    lerp: vi.fn(function () { return this; }),
    copy: vi.fn(function () { return this; }),
    add: vi.fn(function () { return this; }),
  };
  const target = {
    lerp: vi.fn(function () { return this; }),
    copy: vi.fn(function () { return this; }),
  };
  const state = {
    camera: { position, near: 0.1, far: 10000, fov: 45, updateProjectionMatrix: vi.fn() },
    controls: { target, update: vi.fn() },
    gl: { localClippingEnabled: false },
  };
  return {
    Canvas: ({ children }) => React.createElement('div', { 'data-testid': 'canvas' }, children),
    useThree: (selector) => (selector ? selector(state) : state),
    useFrame: () => {},
  };
});

vi.mock('@react-three/drei', () => {
  const React = require('react');
  return {
    OrbitControls: () => null,
    Grid: () => null,
    Edges: () => null,
    Html: ({ children, pointerEvents }) =>
      React.createElement(
        'div',
        { 'data-testid': 'hud-html', 'data-pointer-events': pointerEvents ?? null },
        children,
      ),
  };
});

beforeEach(() => {
  mockState.objGroup = new THREE.Group();
});

describe('GeometryScene canvas + HUD', () => {
  it('renders the (mocked) canvas container', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders the four camera preset buttons', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    expect(screen.getByRole('button', { name: /top-down plan/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /front elevation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /side elevation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /isometric/i })).toBeInTheDocument();
  });

  it('renders independent Z and Y clip toggles', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    expect(screen.getByRole('checkbox', { name: /z clip/i })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /y clip/i })).toBeInTheDocument();
  });

  it('shows the em dash for all metrics when no geometry is loaded', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    expect(screen.getByText(`Triangles: ${EMPTY_METRIC}`)).toBeInTheDocument();
    expect(screen.getByText(`Objects: ${EMPTY_METRIC}`)).toBeInTheDocument();
    expect(screen.getByText(`AABB: ${EMPTY_METRIC}`)).toBeInTheDocument();
  });
});

describe('GeometryScene pointer-events isolation', () => {
  it('sets pointerEvents none on the HUD wrapper', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    const hud = screen.getByTestId('hud-html');
    expect(hud).toHaveAttribute('data-pointer-events', 'none');
  });

  it('sets pointerEvents auto on interactive children (preset buttons)', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    const button = screen.getByRole('button', { name: /top-down plan/i });
    expect(button.style.pointerEvents).toBe('auto');
  });
});

describe('GeometryScene clip control interaction', () => {
  it('toggling the Z clip checkbox updates its checked state', () => {
    render(<GeometryScene objText="v 0 0 0" report={{}} />);
    const zCheckbox = screen.getByRole('checkbox', { name: /z clip/i });
    expect(zCheckbox).not.toBeChecked();
    zCheckbox.click();
    expect(zCheckbox).toBeChecked();
  });
});
