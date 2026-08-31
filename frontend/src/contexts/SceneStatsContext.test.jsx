// SceneStatsContext tests — context default, explicit setStats, and the HUD
// "—" empty-state vs loaded-state rendering.
//
// No Canvas/WebGL required: we exercise the provider, the useSceneStats hook,
// and the SceneStatsBar consumer directly.

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  SceneStatsProvider,
  useSceneStats,
  SceneStatsBar,
  DEFAULT_SCENE_STATS,
} from './SceneStatsContext.jsx';
import { EMPTY_METRIC } from '../lib/viewport.js';

// A raw consumer that surfaces the context value so tests can assert the
// default state and the effect of setStats directly.
function RawConsumer() {
  const { stats, setStats } = useSceneStats();
  return (
    <button
      onClick={() => setStats({ triangles: 15420, objects: 47, aabbMs: 3.2 })}
    >
      stats={stats === null ? 'null' : `${stats.triangles},${stats.objects},${stats.aabbMs}`}
    </button>
  );
}

function BareConsumer() {
  useSceneStats();
  return <div>ok</div>;
}

describe('SceneStatsContext', () => {
  it('exposes a null stats value before any setStats call', () => {
    render(
      <SceneStatsProvider>
        <RawConsumer />
      </SceneStatsProvider>,
    );
    expect(screen.getByRole('button').textContent).toBe('stats=null');
  });

  it('DEFAULT_SCENE_STATS is the zero-value shape', () => {
    expect(DEFAULT_SCENE_STATS).toEqual({ triangles: 0, objects: 0, aabbMs: 0 });
  });

  it('setStats updates the context and re-renders consumers', () => {
    render(
      <SceneStatsProvider>
        <RawConsumer />
      </SceneStatsProvider>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByRole('button').textContent).toBe('stats=15420,47,3.2');
  });

  it('throws when useSceneStats is used outside a provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<BareConsumer />)).toThrow(
      /useSceneStats must be used within a SceneStatsProvider/,
    );
    spy.mockRestore();
  });
});

describe('SceneStatsBar (HUD empty vs loaded)', () => {
  it('shows the em dash for every metric when setStats has not been called', () => {
    render(
      <SceneStatsProvider>
        <SceneStatsBar />
      </SceneStatsProvider>,
    );
    expect(screen.getByText(`Triangles: ${EMPTY_METRIC}`)).toBeInTheDocument();
    expect(screen.getByText(`Objects: ${EMPTY_METRIC}`)).toBeInTheDocument();
    expect(screen.getByText(`AABB: ${EMPTY_METRIC}`)).toBeInTheDocument();
  });

  it('shows formatted metrics after setStats is called', () => {
    function Harness() {
      const { setStats } = useSceneStats();
      return (
        <>
          <SceneStatsBar />
          <button onClick={() => setStats({ triangles: 15420, objects: 47, aabbMs: 3.2 })}>
            load
          </button>
        </>
      );
    }
    render(
      <SceneStatsProvider>
        <Harness />
      </SceneStatsProvider>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'load' }));

    expect(screen.getByText('Triangles: 15,420')).toBeInTheDocument();
    expect(screen.getByText('Objects: 47')).toBeInTheDocument();
    expect(screen.getByText('AABB: 3.2ms')).toBeInTheDocument();
  });

  it('announces metric updates politely for screen readers', () => {
    render(
      <SceneStatsProvider>
        <SceneStatsBar />
      </SceneStatsProvider>,
    );
    const bar = screen.getByText(`Triangles: ${EMPTY_METRIC}`).closest('.hud-status-bar');
    expect(bar).toHaveAttribute('aria-live', 'polite');
  });
});
