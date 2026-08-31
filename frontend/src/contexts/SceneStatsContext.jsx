// Scene stats context for the HUD status bar.
//
// Exposes geometry metrics ({ triangles, objects, aabbMs }) to the HUD. The
// provider deliberately requires an explicit `setStats` call on geometry load —
// there is no implicit ref-to-state propagation (the prior verify failure was
// "statsRef never propagates to React context"). Until `setStats` is called,
// `stats` stays `null` so the HUD can render "—" instead of a misleading "0".

import { createContext, useContext, useMemo, useState } from 'react';
import { formatMetrics } from '../lib/viewport.js';

/** Zero-value stats shape, exported for callers/tests that need a fallback. */
export const DEFAULT_SCENE_STATS = Object.freeze({ triangles: 0, objects: 0, aabbMs: 0 });

// `null` default context value doubles as a sentinel: `useSceneStats` throws
// when consumed outside a `SceneStatsProvider`.
const SceneStatsContext = createContext(null);

export function SceneStatsProvider({ children }) {
  // `null` = "no geometry loaded yet" (empty state), not zero.
  const [stats, setStats] = useState(null);

  const value = useMemo(() => ({ stats, setStats }), [stats]);

  return <SceneStatsContext.Provider value={value}>{children}</SceneStatsContext.Provider>;
}

export function useSceneStats() {
  const context = useContext(SceneStatsContext);
  if (context === null) {
    throw new Error('useSceneStats must be used within a SceneStatsProvider');
  }
  return context;
}

/**
 * Bottom HUD status bar: three metrics (Triangles / Objects / AABB) in
 * JetBrains Mono with tabular-nums, announcing updates politely. Shows "—" for
 * every metric while no geometry has been loaded.
 */
export function SceneStatsBar() {
  const { stats } = useSceneStats();
  const metrics = formatMetrics(stats);

  return (
    <div className="hud-status-bar" aria-live="polite">
      <code>Triangles: {metrics.triangles}</code>
      <span className="hud-separator" aria-hidden="true">|</span>
      <code>Objects: {metrics.objects}</code>
      <span className="hud-separator" aria-hidden="true">|</span>
      <code>AABB: {metrics.aabbMs}</code>
    </div>
  );
}
